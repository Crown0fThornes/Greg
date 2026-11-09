"""Monthly community prizes, drawn from the previous ST calendar month."""
import asyncio
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import json
import logging
from pathlib import Path
import random
import re
import sqlite3

import discord

GUILD_ID=647883751853916162
ANNOUNCEMENTS=1218041302998974584
GIVEAWAYS=697450038359621693
GIVEAWAYBOT=294882584201003009
PARK=(1403415307736846468,1257522038982049902,1108132919324717116,1071930737651097720,1148267353696653362)
NH_ROLES={1181330910747054211,1024052938752151552,656112994392080384,689928709683150909,
          1334660124639236267,1173325157767589988,1342329111359656008,1034248720058945577}
ST=timezone(timedelta(hours=-4))
PATH=Path(__file__).resolve().parent.parent/'data/monthly_community_prizes.sqlite3'
lock=asyncio.Lock()
log=logging.getLogger(__name__)


def previous_month(now):
    end=now.astimezone(ST).replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    start=(end-timedelta(days=1)).replace(day=1)
    return start,end


def giveaway_host(embed):
    parts=[embed.description or '']
    parts.extend(f'{field.name}: {field.value}' for field in embed.fields)
    text='\n'.join(parts).replace('**','').replace('__','')
    match=re.search(r'Hosted\s+by\s*:\s*<@!?(\d+)>',text,re.I)
    return int(match[1]) if match else None


def is_image(attachment):
    return ((attachment.content_type or '').startswith('image/') or
            attachment.filename.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp')))


async def draw(guild,start,end):
    cache={}
    async def eligible(uid):
        if uid not in cache:
            member=guild.get_member(uid)
            if member is None:
                try:
                    member=await guild.fetch_member(uid)
                except discord.NotFound:
                    member=None
            cache[uid]=bool(member and not member.bot and any(role.id in NH_ROLES for role in member.roles))
        return cache[uid]
    hosts={}
    channel=await guild.fetch_channel(GIVEAWAYS)
    async for message in channel.history(limit=None,after=start-timedelta(microseconds=1),before=end,oldest_first=True):
        if not start<=message.created_at<end:
            continue
        if message.author.id!=GIVEAWAYBOT and getattr(message,'application_id',None)!=GIVEAWAYBOT:
            continue
        for embed in message.embeds:
            uid=giveaway_host(embed)
            if uid and await eligible(uid):
                hosts.setdefault(uid,[]).append(dict(prize=(embed.title or 'a giveaway prize')[:200],message_id=message.id))
    host=random.choice(sorted(hosts)) if hosts else None
    giveaway=random.choice(hosts[host]) if host else None
    winner=None
    count=0
    for cid in PARK:
        channel=await guild.fetch_channel(cid)
        async for message in channel.history(limit=None,after=start-timedelta(microseconds=1),before=end,oldest_first=True):
            if not start<=message.created_at<end or message.author.bot or message.author.id==host:
                continue
            if not await eligible(message.author.id):
                continue
            for attachment in message.attachments:
                if is_image(attachment):
                    count+=1
                    if random.randrange(count)==0:
                        winner=dict(user_id=message.author.id,channel_id=cid,message_id=message.id,attachment_id=attachment.id)
    return dict(host=host,giveaway=giveaway,image=winner)


def announcement(result):
    lines=["**Happy New-month all! I have prizes to announce!**",
           "Let's start the new month on a positive note by granting two Neighbors a special prize for their contributions to the community last month.",
           '', '1️⃣ Hosting giveaways in <#697450038359621693> is a great way to help out your fellow Neighbors with goods. One random giveaway host from last month is winning 20 BEMs!!','']
    if result['host']:
        prize=discord.utils.escape_mentions(discord.utils.escape_markdown(result['giveaway']['prize'])).replace('\n',' ')
        lines += [f"**That winner is... Drum roll please... <@{result['host']}>!**",'Who gave away: '+prize]
    else:
        lines += ['No eligible giveaway hosts were found for last month.']
    lines += ['', '2️⃣ Sharing images in our Town Park channels is a great way to build community. One random image from last month is winning 20 BEMs!!','']
    image=result['image']
    if image:
        lines += [f"**That winner is... Drum roll please... <@{image['user_id']}>!**",
                  f"Who posted the attached image here: https://discord.com/channels/{GUILD_ID}/{image['channel_id']}/{image['message_id']}"]
    else:
        lines += ['No eligible images from another Neighbor were found for last month.']
    lines += ['','@everyone']
    return '\n'.join(lines)


@contextmanager
def connect(path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS prize (month TEXT PRIMARY KEY,result TEXT NOT NULL,status TEXT NOT NULL,message_id INTEGER)')
            yield db
    finally:
        db.close()


async def announce(client,*,now=None,path=PATH):
    async with lock:
        guild=client.get_guild(GUILD_ID)
        if guild is None:
            return
        start,end=previous_month(now or datetime.now(timezone.utc))
        key=start.strftime('%Y-%m')
        with connect(path) as db:
            saved=db.execute('SELECT result,status FROM prize WHERE month=?',(key,)).fetchone()
        if saved and saved[1]=='announced':
            target=await guild.fetch_channel(ANNOUNCEMENTS)
            await claim_notice(target,path,key)
            return
        if saved and saved[1]!='ready':
            return
        result=json.loads(saved[0]) if saved else await draw(guild,start,end)
        if not saved:
            with connect(path) as db:
                db.execute("INSERT OR IGNORE INTO prize VALUES (?,?,'ready',NULL)",(key,json.dumps(result)))
        file=None
        image=result['image']
        if image:
            channel=await guild.fetch_channel(image['channel_id'])
            original=await channel.fetch_message(image['message_id'])
            attachment=next(a for a in original.attachments if a.id==image['attachment_id'])
            file=await attachment.to_file()
        target=await guild.fetch_channel(ANNOUNCEMENTS)
        recipients=[uid for uid in (result['host'],image['user_id'] if image else None) if uid]
        with connect(path) as db:
            claimed=db.execute("UPDATE prize SET status='pending' WHERE month=? AND status='ready'",(key,)).rowcount
        if not claimed:
            if file:
                file.close()
            return
        try:
            kwargs=dict(allowed_mentions=discord.AllowedMentions(everyone=True,roles=False,
                        users=[discord.Object(id=uid) for uid in recipients],replied_user=False))
            if file:
                kwargs['file']=file
            posted=await target.send(announcement(result),**kwargs)
        except (discord.Forbidden,discord.NotFound):
            with connect(path) as db:
                db.execute("UPDATE prize SET status='ready' WHERE month=?",(key,))
            raise
        except Exception:
            log.exception('Monthly community prize delivery uncertain for %s; inspect pending row before retrying',key)
            raise
        else:
            with connect(path) as db:
                db.execute("UPDATE prize SET status='announced',message_id=? WHERE month=?",(posted.id,key))
        finally:
            if file:
                file.close()
        await claim_notice(target,path,key)


async def claim_notice(channel,path,key):
    with connect(path) as db:
        claimed=db.execute("UPDATE prize SET status='notice_pending' WHERE month=? AND status='announced'",(key,)).rowcount
    if not claimed:
        return
    try:
        await channel.send("Open a ticket here to claim your prize: <#1033207181857800242>",
                           allowed_mentions=discord.AllowedMentions.none())
    except (discord.Forbidden,discord.NotFound):
        with connect(path) as db:
            db.execute("UPDATE prize SET status='announced' WHERE month=?",(key,))
        raise
    else:
        with connect(path) as db:
            db.execute("UPDATE prize SET status='sent' WHERE month=?",(key,))
