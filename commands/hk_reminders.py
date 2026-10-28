"""Reaction-selected weekly HK tasks, scheduled in fixed UTC-4 server time."""
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import re
import sqlite3

import discord
import emoji

from .hk_assignments import publish, assignees, week_start

log = logging.getLogger(__name__)
GUILD_ID = 647883751853916162
SIGNUP_CHANNEL = 1553522822263869600
SERVER_TIME = timezone(timedelta(hours=-4))
DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'hk_reminders.sqlite3'
# Emoji ID -> (Council channel ID, Council role ID)
NEIGHBORHOODS = {
    1111011980061462538: (1558858396004917298,1102411249502920755),
    1111011971953872976: (1558858338262065172,1102411158029340803),
    1111011976320122880: (1558861126333374515,1102411328129335316),
    1173332572642754560: (1558861204473122916,1184035613008216105),
    1342333117607710741: (1558861299138699285,1342329281015058442),
}
DAYS = {name.lower():i for i,name in enumerate(
    ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'))}
HEADER = re.compile(r'^(.*?)\s*/\s*([A-Za-z]+)\s*/\s*(\d{1,2}):(\d{2})\s*(AM|PM)?\s*(?:\(ST\)|ST)?$',re.I)


@dataclass(frozen=True)
class Task:
    title: str
    weekday: int
    hour: int
    minute: int
    body: str
    emoji: str = None


def parse_task(content):
    lines = content.strip().splitlines()
    if not lines:
        return None
    heading=lines[0].strip(' #*_`\t')
    fields=heading.split('/')
    task_emoji=None
    if len(fields)==4:
        task_emoji=fields[1].strip()
        if not (emoji.is_emoji(task_emoji) or re.fullmatch(r'<a?:\w+:\d+>',task_emoji)):
            return None
        heading='/'.join([fields[0],*fields[2:]])
    match = HEADER.fullmatch(heading)
    if not match or not match[1].strip() or len(match[1])>200 or match[2].lower() not in DAYS:
        return None
    hour,minute = int(match[3]),int(match[4])
    if minute>59 or (match[5] and not 1<=hour<=12) or (not match[5] and hour>23):
        return None
    if match[5]:
        hour = hour%12+(12 if match[5].upper()=='PM' else 0)
    return Task(match[1].strip(),DAYS[match[2].lower()],hour,minute,'\n'.join(lines[1:]).strip(),task_emoji)


def due(task, now):
    if now.tzinfo is None:
        raise ValueError('HK reminder time must include a timezone')
    local = now.astimezone(SERVER_TIME)
    scheduled = local.replace(hour=task.hour,minute=task.minute,second=0,microsecond=0)
    return local.weekday()==task.weekday and timedelta(0)<=local-scheduled<timedelta(minutes=10)


def subscribed(message):
    # Anyone's reaction counts; Unicode reactions and other custom emojis do not.
    return {reaction.emoji.id for reaction in message.reactions
            if getattr(reaction.emoji,'id',None) in NEIGHBORHOODS and reaction.count>0}


class DeliveryLog:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS delivery '
                       '(message_id INTEGER,emoji_id INTEGER,week TEXT,part INTEGER,'
                       'status TEXT NOT NULL,discord_message_id INTEGER,'
                       'PRIMARY KEY(message_id,emoji_id,week,part))')

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def claim(self,key):
        with self.connection() as db:
            return db.execute("INSERT OR IGNORE INTO delivery VALUES (?,?,?,?,'pending',NULL)",key).rowcount==1

    def finish(self,key,message_id):
        with self.connection() as db:
            db.execute("UPDATE delivery SET status='sent',discord_message_id=? WHERE message_id=? AND emoji_id=? AND week=? AND part=?",(message_id,*key))

    def rejected(self,key):
        with self.connection() as db:
            db.execute('DELETE FROM delivery WHERE message_id=? AND emoji_id=? AND week=? AND part=?',key)


def payloads(task,message,role,users=()):
    # Bound all messages even when many people volunteer for one task.
    mentions=[f'<@{user}>' for user in users] if users else [f'<@&{role}>']
    groups=[]
    current=''
    for mention in mentions:
        if len(current)+len(mention)+1>1000:
            groups.append(current)
            current=''
        current+=((' ' if current else '')+mention)
    groups.append(current)
    footer=f'\n\nSignup: https://discord.com/channels/{GUILD_ID}/{SIGNUP_CHANNEL}/{message.id}'
    content=task.body or 'Time for this week’s task.'
    result=[]
    for index,ping in enumerate(groups):
        header=f'**{task.title}**\n{ping}\n'
        capacity=1950-len(header)-len(footer)
        chunk=content[:capacity] if index==0 else ''
        if index==0:
            content=content[capacity:]
        result.append(header+chunk+footer)
    while content:
        header=f'**{task.title}** (continued)\n'
        capacity=1950-len(header)-len(footer)
        result.append(header+content[:capacity]+footer)
        content=content[capacity:]
    return result


class HKReminders:
    def __init__(self,path=DB_PATH):
        self.path=path
        self.messages=[]
        self.refreshed=None
        self.lock=asyncio.Lock()

    async def publish_current(self,guild,*,now=None):
        async with self.lock:
            if guild.id!=GUILD_ID:
                raise ValueError('HK signup is only available in FF.')
            local=(now or datetime.now(timezone.utc)).astimezone(SERVER_TIME)
            week=week_start(local)
            channel=await guild.fetch_channel(SIGNUP_CHANNEL)
            tasks=[]
            async for message in channel.history(limit=None,oldest_first=True):
                task=parse_task(message.content)
                if task:
                    tasks.append((message,task,subscribed(message)))
            delivery=DeliveryLog(self.path)
            from .hk_assignments import initialize
            initialize(delivery)
            with delivery.connection() as db:
                before=db.execute('SELECT COUNT(*) FROM assignment_post WHERE week=? AND message_id IS NOT NULL',(week,)).fetchone()[0]
            failures=[]
            for nh,config in NEIGHBORHOODS.items():
                try:
                    await publish(guild,delivery,{nh:config},tasks,local,week=week)
                except discord.HTTPException:
                    log.exception('Manual HK signup failed for NH %s',nh)
                    failures.append(config[0])
            with delivery.connection() as db:
                sent=db.execute('SELECT COUNT(*) FROM assignment_post WHERE week=? AND message_id IS NOT NULL',(week,)).fetchone()[0]
                pending=db.execute('SELECT COUNT(*) FROM assignment_post WHERE week=? AND message_id IS NULL',(week,)).fetchone()[0]
            return week,sent-before,before,pending,failures

    async def run(self,client,*,now=None):
        async with self.lock:
            now=now or datetime.now(timezone.utc)
            guild=client.get_guild(GUILD_ID)
            if guild is None:
                return
            channel=await guild.fetch_channel(SIGNUP_CHANNEL)
            if self.refreshed is None or now-self.refreshed>=timedelta(minutes=5):
                # Publish cache only after a complete scan; failed scans retry next minute.
                messages=[m async for m in channel.history(limit=None,oldest_first=True)
                          if parse_task(m.content)]
                self.messages=messages
                self.refreshed=now
            delivery=DeliveryLog(self.path)
            local=now.astimezone(SERVER_TIME)
            if local.weekday()==6 and local.hour==8 and local.minute<10:
                weekly=[]
                for cached in self.messages:
                    try:
                        fresh=await channel.fetch_message(cached.id)
                    except discord.NotFound:
                        continue
                    task=parse_task(fresh.content)
                    if task:
                        weekly.append((fresh,task,subscribed(fresh)))
                for nh,config in NEIGHBORHOODS.items():
                    try:
                        await publish(guild,delivery,{nh:config},weekly,local)
                    except discord.HTTPException:
                        log.exception('HK weekly assignment post failed for NH %s',nh)
            for cached in self.messages:
                task=parse_task(cached.content)
                if not task or not due(task,now):
                    continue
                try:
                    # Confirm current wording/reactions/deletion immediately before sending.
                    message=await channel.fetch_message(cached.id)
                except discord.NotFound:
                    continue
                task=parse_task(message.content)
                if not task or not due(task,now):
                    continue
                local=now.astimezone(SERVER_TIME)
                week=week_start(local)
                for emoji_id in sorted(subscribed(message)):
                    target_id,role_id=NEIGHBORHOODS[emoji_id]
                    try:
                        target=await guild.fetch_channel(target_id)
                        if delivery is None:
                            delivery=DeliveryLog(self.path)
                        users=await assignees(guild,delivery,emoji_id,target_id,message.id,task.emoji,local)
                        for part,content in enumerate(payloads(task,message,role_id,users)):
                            key=(message.id,emoji_id,week,part)
                            if not delivery.claim(key):
                                continue
                            try:
                                sent=await target.send(content,allowed_mentions=discord.AllowedMentions(
                                    everyone=False,users=[discord.Object(id=user) for user in users],
                                    roles=[] if users else [discord.Object(id=role_id)],replied_user=False))
                            except (discord.Forbidden,discord.NotFound):
                                delivery.rejected(key)
                                raise
                            except Exception:
                                # Delivery may have succeeded despite a timeout. Retain pending
                                # rather than automatically pinging the Council twice.
                                log.exception('HK delivery uncertain; review delivery row %r',key)
                                break
                            delivery.finish(key,sent.id)
                    except discord.HTTPException:
                        log.exception('HK reminder failed for signup %s, emoji %s',message.id,emoji_id)


reminders=HKReminders()


async def run_hk_reminders(client):
    # A read/permission/network failure should not stop Greg's other scheduled jobs.
    try:
        await reminders.run(client)
    except Exception:
        log.exception('HK signup reminder scan failed')
