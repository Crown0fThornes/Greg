"""Persistent, one-shot personal reminders in fixed UTC-4 server time."""
import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import re
import sqlite3

import discord

GUILD_ID = 647883751853916162
CHANNEL_ID = 784150346397253682
SERVER_TIME = timezone(timedelta(hours=-4))
DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'personal_reminders.sqlite3'
log = logging.getLogger(__name__)
SYNTAX = 'Use $remindme month/day/year [hour:minute AM/PM]: reminder text. Times use ST (UTC−4); default 8:00 AM.'
PATTERN = re.compile(r'^\S+\s+(\d{1,2}/\d{1,2}/\d{4})(?:\s+(\d{1,2}):(\d{2})\s*(AM|PM))?\s*:\s*(.+)$', re.I|re.S)


def parse_reminder(content, now=None):
    match = PATTERN.fullmatch(content.strip())
    if not match:
        raise ValueError(SYNTAX)
    month,day,year=map(int,match[1].split('/'))
    hour,minute=8,0
    if match[2] is not None:
        hour,minute=int(match[2]),int(match[3])
        if not 1<=hour<=12 or not 0<=minute<=59:
            raise ValueError('Invalid time. '+SYNTAX)
        hour=hour%12+(12 if match[4].upper()=='PM' else 0)
    try:
        when=datetime(year,month,day,hour,minute,tzinfo=SERVER_TIME)
    except ValueError as error:
        raise ValueError('Invalid calendar date. '+SYNTAX) from error
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Current time must include a timezone.')
    if when<=now:
        raise ValueError('Choose a date/time in the future. '+SYNTAX)
    body=match[5].strip()
    if not body or len(body)>1500:
        raise ValueError('Reminder text must contain 1–1500 characters.')
    return when,body


class ReminderStore:
    def __init__(self,path=DB_PATH):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS reminder ('
                       'id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,guild_id INTEGER NOT NULL,'
                       'source_url TEXT NOT NULL,due_at REAL NOT NULL,body TEXT NOT NULL,'
                       "dm_status TEXT NOT NULL DEFAULT 'waiting',server_status TEXT NOT NULL DEFAULT 'waiting')")

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self,user_id,guild_id,source_url,when,body):
        with self.connection() as db:
            return db.execute('INSERT INTO reminder(user_id,guild_id,source_url,due_at,body) VALUES (?,?,?,?,?)',
                              (user_id,guild_id,source_url,when.timestamp(),body)).lastrowid

    def due(self,now):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM reminder WHERE due_at<=? AND (dm_status='waiting' OR server_status='waiting') ORDER BY due_at,id LIMIT 100",(now.timestamp(),))]

    def claim(self,key,kind):
        assert kind in ('dm','server')
        with self.connection() as db:
            return db.execute(f"UPDATE reminder SET {kind}_status='pending' WHERE id=? AND {kind}_status='waiting'",(key,)).rowcount==1

    def finish(self,key,kind,status):
        assert kind in ('dm','server')
        with self.connection() as db:
            db.execute(f'UPDATE reminder SET {kind}_status=? WHERE id=?',(status,key))


async def create_reminder(context,*,store=None,now=None):
    when,body=parse_reminder(context.content,now)
    store=store or ReminderStore()
    source=f'https://discord.com/channels/{context.guild.id}/{context.channel.id}/{context.message.id}'
    store.add(context.author_id,context.guild.id,source,when,body)
    await context.message.add_reaction('✅')


class ReminderRunner:
    def __init__(self,path=DB_PATH):
        self.path=path
        self.lock=asyncio.Lock()

    async def run(self,client,*,now=None):
        async with self.lock:
            # Don't initialize a data file until someone creates the first reminder.
            if not Path(self.path).exists():
                return
            store=ReminderStore(self.path)
            for row in store.due(now or datetime.now(timezone.utc)):
                if row['guild_id']!=GUILD_ID:
                    continue
                for kind in ('dm','server'):
                    if row[kind+'_status']!='waiting':
                        continue
                    try:
                        # Resolve the target before claiming; read failures can safely retry.
                        if kind=='dm':
                            target=client.get_user(row['user_id']) or await client.fetch_user(row['user_id'])
                        else:
                            target=client.get_channel(CHANNEL_ID) or await client.fetch_channel(CHANNEL_ID)
                            if target.guild.id!=row['guild_id']:
                                raise ValueError('Reminder destination is in the wrong server')
                    except (discord.Forbidden,discord.NotFound):
                        store.finish(row['id'],kind,'blocked')
                        log.warning('Personal reminder %s %s target unavailable',row['id'],kind)
                        continue
                    except Exception:
                        log.exception('Could not resolve personal reminder %s %s target; retrying later',row['id'],kind)
                        continue
                    if not store.claim(row['id'],kind):
                        continue
                    body=f"⏰ **Reminder**\n"+(f"<@{row['user_id']}>\n" if kind=='server' else '')+row['body']+f"\n\nOriginal request: {row['source_url']}"
                    try:
                        await target.send(body,allowed_mentions=discord.AllowedMentions(
                            everyone=False,roles=False,
                            users=[discord.Object(id=row['user_id'])] if kind=='server' else False,
                            replied_user=False))
                    except (discord.Forbidden,discord.NotFound):
                        store.finish(row['id'],kind,'blocked')
                        log.warning('Personal reminder %s %s rejected',row['id'],kind)
                    except Exception:
                        # A timeout may have delivered: preserve pending instead of duplicating.
                        log.exception('Personal reminder %s %s delivery uncertain; review pending row',row['id'],kind)
                    else:
                        store.finish(row['id'],kind,'sent')


runner=ReminderRunner()


async def run_personal_reminders(client):
    try:
        await runner.run(client)
    except Exception:
        log.exception('Personal reminder scheduler failed')
