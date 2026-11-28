"""Transactional counting scores; inventory mirrors and reactions stay off the fast path."""
import asyncio
import calendar
from datetime import datetime, timezone
import json
import logging
import random
import secrets
import time

import discord

GUILD_ID=647883751853916162
NEIGHBORS_ROLE=1181330910747054211
ANNOUNCEMENTS=784150346397253682
ITEM_NAME='Counting Game Score'
ITEM_TYPE='counting_score'
log=logging.getLogger(__name__)
monthly_lock=asyncio.Lock()


def milestone(value):
    if value in {10,50,100,250,500,600,700,800,900}:
        return True
    return value>=1000 and value%(10**(len(str(value))-1))==0


def event(message,kind,*,value=0,expected=0):
    if kind=='valid':
        points=(100 if milestone(value) else 10)+value
    elif kind=='deleted':
        points=-10
    else:
        points=-(10+abs(value)+expected)
    created=getattr(message,'created_at',None) or discord.utils.snowflake_time(message.id)
    return dict(message_id=message.id,user_id=message.author.id,delta=points,
                occurred=created.timestamp(),milestone=kind=='valid' and milestone(value))


def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS counting_event ('
               'message_id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,delta TEXT NOT NULL,occurred REAL NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS counting_event_user ON counting_event(user_id,occurred)')
    db.execute('CREATE TABLE IF NOT EXISTS counting_score ('
               'user_id INTEGER PRIMARY KEY,points TEXT NOT NULL,played INTEGER NOT NULL,dirty INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS counting_reaction ('
               'message_id INTEGER PRIMARY KEY,emoji TEXT,status TEXT NOT NULL,next_attempt REAL NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS counting_month ('
               'period TEXT PRIMARY KEY,cutoff REAL NOT NULL UNIQUE,snapshot TEXT NOT NULL,status TEXT NOT NULL,'
               'nonce TEXT NOT NULL,message_id INTEGER)')


def balance(db,uid,*,before=None):
    events=[(row[1],int(row[0])) for row in db.execute('SELECT delta,occurred FROM counting_event WHERE user_id=? '
        'ORDER BY occurred,message_id',(uid,)) if before is None or row[1]<before]
    cutoffs=[row[0] for row in db.execute('SELECT cutoff FROM counting_month ORDER BY cutoff')
             if before is None or row[0]<before]
    points=0
    index=0
    for cutoff in cutoffs:
        while index<len(events) and events[index][0]<cutoff:
            points+=events[index][1]
            index+=1
        points//=2
    return points+sum(delta for _,delta in events[index:])


def record(db,score_event):
    if score_event is None:
        return
    e=score_event
    inserted=db.execute('INSERT OR IGNORE INTO counting_event VALUES (?,?,?,?)',
        (e['message_id'],e['user_id'],str(e['delta']),e['occurred'])).rowcount
    if not inserted:
        return
    previous=db.execute('SELECT points FROM counting_score WHERE user_id=?',(e['user_id'],)).fetchone()
    last_cutoff=db.execute('SELECT MAX(cutoff) FROM counting_month').fetchone()[0]
    points=balance(db,e['user_id']) if last_cutoff is not None and e['occurred']<last_cutoff else \
        (int(previous[0]) if previous else 0)+e['delta']
    db.execute('INSERT INTO counting_score VALUES (?,?,1,1) ON CONFLICT(user_id) DO UPDATE SET '
               'points=excluded.points,played=1,dirty=1',(e['user_id'],str(points)))
    if e['milestone']:
        db.execute("INSERT OR IGNORE INTO counting_reaction VALUES (?,NULL,'waiting',0)",(e['message_id'],))


def score(store,uid):
    with store.connect() as db:
        row=db.execute('SELECT points FROM counting_score WHERE user_id=?',(uid,)).fetchone()
    return int(row[0]) if row else 0


def display(points):
    text=str(abs(points))
    if len(text)>80:
        return ('−' if points<0 else '')+text[:6]+'… ('+str(len(text))+' digits)'
    return f'{points:,}'


def mirror(neighbor,points):
    from custom_types import Item
    item=neighbor.get_item_of_name(ITEM_NAME)
    if item is None:
        neighbor.bestow_item(Item(ITEM_NAME,ITEM_TYPE,-1,points=points))
    elif item.type!=ITEM_TYPE or str(item.values.get('points'))!=str(points):
        neighbor.update_item(Item(ITEM_NAME,ITEM_TYPE,-1,points=points))


def sync_profile(neighbor,*,store=None):
    if store is None:
        from commands.counting_game import CountingStore
        store=CountingStore()
    points=score(store,neighbor.ID)
    mirror(neighbor,points)
    return points


class CountingEffects:
    def __init__(self,channel,store):
        self.channel,self.store=channel,store
        self.task=None

    def start(self):
        if self.task is None or self.task.done():
            self.task=asyncio.create_task(self.run())

    async def sync(self):
        from custom_types import Neighbor
        with self.store.connect() as db:
            dirty=list(db.execute('SELECT user_id,points FROM counting_score WHERE dirty=1 LIMIT 100'))
        # Neighbor's existing text-file writes stay on the main thread and are
        # absolute mirrors, never additive awards that a retry could duplicate.
        for uid,points in dirty:
            mirror(Neighbor(uid,GUILD_ID),int(points))
            with self.store.connect() as db:
                db.execute('UPDATE counting_score SET dirty=0 WHERE user_id=? AND points=?',(uid,points))
            await asyncio.sleep(0)

    async def reactions(self):
        with self.store.connect() as db:
            pending=list(db.execute("SELECT message_id,emoji FROM counting_reaction WHERE status='waiting' AND next_attempt<=? LIMIT 20",(time.time(),)))
        if not pending:
            return
        from commands.commands import _load_hype_emojis
        pool=await _load_hype_emojis(self.channel.guild)
        if not pool:
            return
        for mid,emoji in pending:
            if emoji is None:
                emoji=random.choice(pool)
                with self.store.connect() as db:
                    db.execute('UPDATE counting_reaction SET emoji=? WHERE message_id=?',(emoji,mid))
            try:
                await self.channel.get_partial_message(mid).add_reaction(emoji)
            except discord.NotFound:
                status='gone'
            except discord.HTTPException:
                with self.store.connect() as db:
                    db.execute('UPDATE counting_reaction SET next_attempt=? WHERE message_id=?',(time.time()+300,mid))
                continue
            else:
                status='done'
            with self.store.connect() as db:
                db.execute('UPDATE counting_reaction SET status=? WHERE message_id=?',(status,mid))

    async def run(self):
        while True:
            delay=1
            try:
                await self.sync()
                await self.reactions()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                log.error('Counting score display/reaction retry needed (%s)',type(error).__name__)
                delay=30
            await asyncio.sleep(delay)

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task,return_exceptions=True)


def cutoffs(now):
    # Match the existing reckoning scheduler's local date/time exactly.
    local=now.astimezone()
    year,month=2027,1
    while (year,month)<=(local.year,local.month):
        boundary=datetime(year,month,2,0,1).astimezone()
        if boundary<=local:
            yield f'{year:04d}-{month:02d}',boundary
        year,month=(year+1,1) if month==12 else (year,month+1)


def roll(store,period,boundary):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM counting_month WHERE period=?',(period,)).fetchone():
            return
        players=list(db.execute('SELECT user_id,played FROM counting_score'))
        snapshot=[(uid,balance(db,uid,before=boundary.timestamp())) for uid,played in players if played]
        snapshot.sort(key=lambda entry:(-entry[1],entry[0]))
        db.execute("INSERT INTO counting_month VALUES (?,?,?,'ready',?,NULL)",
                   (period,boundary.timestamp(),json.dumps(snapshot),secrets.token_hex(12)))
        for uid,_ in players:
            db.execute('UPDATE counting_score SET points=?,dirty=1 WHERE user_id=?',(str(balance(db,uid)),uid))


async def monthly_rewards(client,*,store=None,now=None):
    from commands.counting_game import CountingStore, _games, CHANNEL_ID
    store=store or CountingStore()
    now=now or datetime.now(timezone.utc)
    due=list(cutoffs(now))
    if not due:
        return
    guild=client.get_guild(GUILD_ID)
    if guild is None:
        return
    async with monthly_lock:
        game=_games.get((CHANNEL_ID,client.user.id))
        if game is not None:
            # Finish startup/offline replay and queued decisions before drawing.
            await asyncio.wait_for(game.barrier(),timeout=60)
        for period,boundary in due:
            await asyncio.to_thread(roll,store,period,boundary)
        with store.connect() as db:
            pending=list(db.execute("SELECT period,cutoff,snapshot,status,nonce FROM counting_month WHERE status!='sent' ORDER BY period"))
        if not pending:
            return
        target=await guild.fetch_channel(ANNOUNCEMENTS)
        for period,cutoff,snapshot,status,nonce in pending:
            year,month=map(int,period.split('-'))
            previous_year,previous_month=(year-1,12) if month==1 else (year,month-1)
            header=f'# Counting Game Leaderboard\n**{calendar.month_name[previous_month]} {previous_year}**'
            if status=='pending':
                found=None
                async for message in target.history(limit=None,after=datetime.fromtimestamp(cutoff,timezone.utc),oldest_first=True):
                    if message.author.id==client.user.id and message.content.startswith(header):
                        found=message
                        break
                if found is not None:
                    with store.connect() as db:
                        db.execute("UPDATE counting_month SET status='sent',message_id=? WHERE period=?",(found.id,period))
                    continue
            lines=[header,'']
            for uid,points in json.loads(snapshot):
                member=guild.get_member(uid)
                if member is None:
                    try:
                        member=await guild.fetch_member(uid)
                    except discord.NotFound:
                        continue
                if member.bot:
                    continue
                label=discord.utils.escape_mentions(discord.utils.escape_markdown(member.display_name.replace('\n',' ')[:70]))
                lines.append(f"{len(lines)-1}. **{label}** — {display(points)}")
                if len(lines)==12:
                    break
            if len(lines)==2:
                lines.append('No counting-game players recorded for this month.')
            lines += ['', 'Scores shown are before the monthly halving. Your carried score has been halved and rounded down. Keep counting!',
                      '',f'<@&{NEIGHBORS_ROLE}>']
            with store.connect() as db:
                db.execute("UPDATE counting_month SET status='pending' WHERE period=?",(period,))
            posted=await target.send('\n'.join(lines),nonce=nonce,allowed_mentions=discord.AllowedMentions(
                everyone=False,users=False,roles=[discord.Object(id=NEIGHBORS_ROLE)],replied_user=False))
            with store.connect() as db:
                db.execute("UPDATE counting_month SET status='sent',message_id=? WHERE period=?",(posted.id,period))
