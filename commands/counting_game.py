"""One ordered, restart-safe counting worker, isolated from general bot commands.

State and pending non-number deletions live in data/counting_game.sqlite3.
On first use the latest Greg-authored `1` anchors the existing round; subsequent
restarts replay only messages after the saved cursor. An accepted turn is not
undone by later edits/deletions. Other bots do not participate. Greg needs Read
Message History, Send Messages and Manage Messages in the configured channel.
"""
import asyncio
from contextlib import contextmanager
import json
import logging
from pathlib import Path
import re
import secrets
import sqlite3

import discord
from commands import counting_scores

GUILD_ID = 647883751853916162
CHANNEL_ID = 1184669547505131641
PATH = Path(__file__).resolve().parent.parent/'data/counting_game.sqlite3'
log = logging.getLogger(__name__)
_RECOVER = object()
_TICK = object()
_games = {}


def number(content):
    text = content.strip()
    return int(text) if re.fullmatch(r'[+-]?[0-9]+',text) else None


def is_non_number(message):
    return number(message.content) is None or bool(getattr(message,'attachments',[]) or getattr(message,'stickers',[]))


class CountingStore:
    def __init__(self,path=PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS game (channel_id INTEGER PRIMARY KEY,state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS deletion ('
                       'channel_id INTEGER NOT NULL,message_id INTEGER NOT NULL,PRIMARY KEY(channel_id,message_id))')
            counting_scores.schema(db)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path,timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def load(self,channel_id):
        with self.connect() as db:
            row = db.execute('SELECT state FROM game WHERE channel_id=?',(channel_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self,state,delete_id=None,score_event=None):
        with self.connect() as db:
            db.execute('INSERT INTO game VALUES (?,?) ON CONFLICT(channel_id) DO UPDATE SET state=excluded.state',
                       (state['channel_id'],json.dumps(state)))
            if delete_id is not None:
                db.execute('INSERT OR IGNORE INTO deletion VALUES (?,?)',(state['channel_id'],delete_id))
            counting_scores.record(db,score_event)

    def deletions(self,channel_id):
        with self.connect() as db:
            return [row[0] for row in db.execute('SELECT message_id FROM deletion WHERE channel_id=? ORDER BY message_id LIMIT 100',
                                               (channel_id,))]

    def deleted(self,channel_id,message_id):
        with self.connect() as db:
            db.execute('DELETE FROM deletion WHERE channel_id=? AND message_id=?',(channel_id,message_id))


class CountingGame:
    def __init__(self,channel,bot_id,store,*,batch_delay=0.05,retry_delay=30):
        self.channel = channel
        self.bot_id = bot_id
        self.store = store
        self.state = None
        self.ready = False
        self.queue = asyncio.Queue()
        self.task = None
        self.delete_task = None
        self.delete_dirty = False
        self.delete_checked = 0
        self.batch_delay = batch_delay
        self.retry_delay = retry_delay
        self.effects = None

    async def checkpoint(self,state,delete_id=None,score_event=None):
        # Publish in-memory state only after its durable transaction succeeds.
        await asyncio.to_thread(self.store.save,state,delete_id,score_event)
        self.state = state

    async def latest_id(self):
        async for message in self.channel.history(limit=1):
            return message.id
        return 0

    async def recover(self):
        self.state = await asyncio.to_thread(self.store.load,self.channel.id)
        if self.state and self.state['bot_id']!=self.bot_id:
            raise RuntimeError('This counting channel is owned by a different bot account')
        if self.state is None:
            latest = await self.latest_id()
            seed = None
            options = dict(limit=None,oldest_first=False)
            if latest:
                options['before'] = discord.Object(id=latest+1)
            async for message in self.channel.history(**options):
                if message.author.id==self.bot_id and message.content.strip()=='1':
                    seed = message
                    break
            state = dict(channel_id=self.channel.id,bot_id=self.bot_id,value=1,last_user=None,
                         cursor=seed.id if seed else latest,seed_id=seed.id if seed else None,
                         phase='active' if seed else 'reset',reason='start',
                         notice_id=None,seed_nonce=secrets.token_hex(12),notice_nonce=secrets.token_hex(12))
            await self.checkpoint(state)
        if self.state['phase']=='reset':
            await self.seed(reconcile=True)
        upper = await self.latest_id()
        await self.replay(upper)
        self.ready = True
        self.start_deletions()

    async def replay(self,upper):
        if upper<=self.state['cursor']:
            return
        async for message in self.channel.history(limit=None,after=discord.Object(id=self.state['cursor']),
                                                  before=discord.Object(id=upper+1),oldest_first=True):
            await self.apply(message,verify=False)

    async def seed(self,*,reconcile=False):
        """Resume a saved reset, including a send that succeeded before a crash."""
        if reconcile:
            async for message in self.channel.history(limit=None,after=discord.Object(id=self.state['cursor']),oldest_first=True):
                if message.author.id!=self.bot_id:
                    continue
                if message.content.strip()=='1':
                    await self.activate_seed(message)
                    return
                if message.content==self.failure_text() and self.state['notice_id'] is None:
                    await self.checkpoint(dict(self.state,notice_id=message.id))
        if self.state['reason']!='start' and self.state['notice_id'] is None:
            notice = await self.channel.send(self.failure_text(),nonce=self.state['notice_nonce'],
                                             allowed_mentions=discord.AllowedMentions.none())
            await self.checkpoint(dict(self.state,notice_id=notice.id))
        # The installed discord.py sends enforce_nonce=True for explicit nonces.
        # History reconciliation also handles retries after Discord's nonce window.
        message = await self.channel.send('1',nonce=self.state['seed_nonce'],allowed_mentions=discord.AllowedMentions.none())
        await self.activate_seed(message)

    def failure_text(self):
        if self.state['reason']=='repeat':
            return 'Whoops! The same person counted twice in a row. Let’s start over. #sorrynotsorry'
        return 'Whoops! Someone missed the next number. Let’s start over. #sorrynotsorry'

    async def activate_seed(self,message):
        await self.checkpoint(dict(self.state,value=1,last_user=None,cursor=message.id,
                                   seed_id=message.id,phase='active',notice_id=None))

    async def apply(self,message,*,verify=True):
        if message.id<=self.state['cursor']:
            if not message.author.bot and is_non_number(message):
                await self.checkpoint(dict(self.state),delete_id=message.id,score_event=counting_scores.event(message,'deleted'))
                self.start_deletions()
            return
        if self.state['phase']=='reset':
            await self.seed(reconcile=True)
            if message.id<=self.state['cursor']:
                return
        if message.author.bot:
            if message.author.id==self.bot_id and message.content.strip()=='1':
                await self.activate_seed(message)
            else:
                await self.checkpoint(dict(self.state,cursor=message.id))
            return
        value = number(message.content)
        if value is None or getattr(message,'attachments',[]) or getattr(message,'stickers',[]):
            await self.checkpoint(dict(self.state,cursor=message.id),delete_id=message.id,score_event=counting_scores.event(message,'deleted'))
            self.start_deletions()
            return
        wrong = value!=self.state['value']+1
        repeat = message.author.id==self.state['last_user']
        if (wrong or repeat) and verify:
            # An earlier count may be in Discord history but its event delayed.
            # Reconcile only on apparent errors, not on every accepted number.
            await self.replay(message.id)
            if message.id<=self.state['cursor']:
                return
            wrong = value!=self.state['value']+1
            repeat = message.author.id==self.state['last_user']
        if wrong or repeat:
            await self.checkpoint(dict(self.state,cursor=message.id,phase='reset',
                reason='repeat' if repeat else 'number',notice_id=None,
                seed_nonce=secrets.token_hex(12),notice_nonce=secrets.token_hex(12)),
                score_event=counting_scores.event(message,'ended',value=value,expected=self.state['value']+1))
            await self.seed()
        else:
            await self.checkpoint(dict(self.state,cursor=message.id,value=value,last_user=message.author.id),
                                  score_event=counting_scores.event(message,'valid',value=value))

    def start_deletions(self):
        self.delete_dirty = True
        if self.delete_task is None or self.delete_task.done():
            self.delete_checked = asyncio.get_running_loop().time()
            self.delete_task = asyncio.create_task(self.drain_deletions())

    async def drain_deletions(self):
        try:
            while True:
                self.delete_dirty = False
                pending = await asyncio.to_thread(self.store.deletions,self.channel.id)
                if not pending:
                    if self.delete_dirty:
                        continue
                    return
                for mid in pending:
                    try:
                        await self.channel.get_partial_message(mid).delete()
                    except discord.NotFound:
                        pass
                    except discord.HTTPException:
                        log.warning('Cannot delete non-number message %s from counting channel; will retry',mid)
                        return
                    await asyncio.to_thread(self.store.deleted,self.channel.id,mid)
        except Exception as error:
            log.error('Counting-game deletion worker failed (%s); deletions retained for retry',type(error).__name__)

    def enqueue(self,message):
        self.ensure_task()
        self.queue.put_nowait(message)

    def wake(self):
        self.ensure_task()
        self.queue.put_nowait(_RECOVER)

    def ensure_task(self):
        if self.task is None or self.task.done():
            self.ready = False
            self.task = asyncio.create_task(self.run())
        if self.effects is not None:
            self.effects.start()

    async def barrier(self):
        self.ensure_task()
        future=asyncio.get_running_loop().create_future()
        self.queue.put_nowait(future)
        await future

    async def run(self):
        while True:
            batch = []
            try:
                try:
                    item = await asyncio.wait_for(self.queue.get(),timeout=self.retry_delay)
                    batch.append(item)
                except asyncio.TimeoutError:
                    item = _TICK
                if item is not _TICK:
                    await asyncio.sleep(self.batch_delay)
                    while not self.queue.empty():
                        batch.append(self.queue.get_nowait())
                barriers=[item for item in batch if isinstance(item,asyncio.Future)]
                if _RECOVER in batch or barriers:
                    self.ready = False
                if not self.ready:
                    await self.recover()
                messages = {message.id:message for message in batch if message is not _RECOVER and message is not _TICK
                            and not isinstance(message,asyncio.Future)}
                for mid in sorted(messages):
                    await self.apply(messages[mid])
                if asyncio.get_running_loop().time()-self.delete_checked>=self.retry_delay:
                    self.start_deletions()
                for future in barriers:
                    if not future.done():
                        future.set_result(None)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.ready = False
                for item in batch:
                    if isinstance(item,asyncio.Future) and not item.done():
                        item.set_exception(error)
                log.error('Counting game paused after %s; replaying saved history on retry',type(error).__name__)
                await asyncio.sleep(self.retry_delay)
            finally:
                for _ in batch:
                    self.queue.task_done()

    async def shutdown(self):
        if self.effects is not None:
            await self.effects.stop()
        for task in (self.task,self.delete_task):
            if task is not None:
                task.cancel()
        await asyncio.gather(*(task for task in (self.task,self.delete_task) if task is not None),return_exceptions=True)


def game_for(channel,bot_id):
    key = (channel.id,bot_id)
    if key not in _games:
        _games[key] = CountingGame(channel,bot_id,CountingStore())
        _games[key].effects = counting_scores.CountingEffects(channel,_games[key].store)
    return _games[key]


def route_message(message):
    """Called before any general handlers; enqueuing never waits for network I/O."""
    if message.guild is None or message.guild.id!=GUILD_ID or message.channel.id!=CHANNEL_ID:
        return False
    if message.author.bot:
        return True
    member = message.guild.me
    if member is not None:
        game_for(message.channel,member.id).enqueue(message)
    return True


async def start_counting_game(client):
    try:
        guild = client.get_guild(GUILD_ID)
        if guild is None:
            return
        channel = guild.get_channel(CHANNEL_ID) or await guild.fetch_channel(CHANNEL_ID)
        game_for(channel,client.user.id).wake()
    except Exception as error:
        log.error('Counting-game startup could not initialize (%s); next message can retry',type(error).__name__)
