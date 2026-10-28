"""Sunday Council signup posts and Tuesday-to-Monday task assignees."""
from datetime import date, timedelta
import json
import logging
import re

import discord

log = logging.getLogger(__name__)
INSTRUCTIONS = "**Good morning and happy weekend! Please react to the tasks you're responsible for *next week*, or would otherwise like to be pinged for.**"


def week_start(local):
    return (local.date()-timedelta(days=(local.weekday()-1)%7)).isoformat()


def emoji_key(value):
    custom=re.fullmatch(r'<a?:\w+:(\d+)>',str(value))
    return custom[1] if custom else str(value).replace('\ufe0f','')


def initialize(delivery):
    with delivery.connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS assignment_post '
                   '(nh INTEGER,week TEXT,part INTEGER,message_id INTEGER,tasks TEXT NOT NULL,'
                   'PRIMARY KEY(nh,week,part))')


def signup_pages(tasks,week,*,current_week=False):
    # A Discord message permits at most 20 distinct reaction emojis.
    counts={}
    for message,task in tasks:
        if task.emoji:
            key=emoji_key(task.emoji)
            counts[key]=counts.get(key,0)+1
    entries=[]
    invalid=[]
    for message,task in tasks:
        if not task.emoji or counts[emoji_key(task.emoji)]!=1:
            invalid.append(task.title)
            continue
        entries.append((message,task))
    entries.sort(key=lambda pair: ((pair[1].weekday-1)%7,pair[1].hour,pair[1].minute,pair[0].id))
    pages=[]
    current=[]
    size=0
    for message,task in entries:
        ping_date=date.fromisoformat(week)+timedelta(days=(task.weekday-1)%7)
        line=f'{task.emoji} **{discord.utils.escape_mentions(discord.utils.escape_markdown(task.title))}** ({ping_date.month}/{ping_date.day})'
        if len(current)==20 or size+len(line)>1150:
            pages.append(current)
            current=[]
            size=0
        current.append((message,task,line))
        size+=len(line)+1
    pages.append(current)
    result=[]
    for i,page in enumerate(pages):
        instructions=INSTRUCTIONS.replace('Good morning and happy weekend! ', '').replace('*next week*','*this week*') if current_week else INSTRUCTIONS
        headline="**This week's HK sign ups!**" if current_week else "**Next week's HK sign ups!**"
        start=date.fromisoformat(week)
        date_label=f'{start.month}/{start.day}'
        content=headline+'\n\n'+instructions+f'\n\n**Week beginning Tuesday, {date_label} (ST)**\nTuesday through Monday.\n\n'
        content+='\n'.join(line for _,_,line in page) or 'No tasks with unique emojis are available for signup.'
        content+='\n\nYou can change what tasks your Neighborhood is registered for in <#1553522822263869600>'
        if invalid and i==0:
            content+='\n\nSome tasks lack a unique emoji and will use the Council role until corrected.'
        mapping={str(message.id):task.emoji for message,task,_ in page}
        result.append((content,mapping))
    return result


async def publish(guild,delivery,neighborhoods,tasks,local,*,week=None):
    initialize(delivery)
    # Sunday's signup applies to the Tuesday two days later, not to Sunday/Monday now.
    current=week is not None
    week=week or (local.date()+timedelta(days=2)).isoformat()
    for nh,(channel_id,role_id) in neighborhoods.items():
        selected=[(m,t) for m,t,logos in tasks if nh in logos]
        target=await guild.fetch_channel(channel_id)
        pages=signup_pages(selected,week,current_week=current)
        for part,(content,mapping) in enumerate(pages):
            with delivery.connection() as db:
                inserted=db.execute('INSERT OR IGNORE INTO assignment_post VALUES (?,?,?,NULL,?)',
                                    (nh,week,part,json.dumps(mapping))).rowcount
                row=db.execute('SELECT * FROM assignment_post WHERE nh=? AND week=? AND part=?',
                               (nh,week,part)).fetchone()
            message_id=row[3]
            if inserted:
                try:
                    first_line,rest=content.split('\n',1)
                    post_content=first_line+(f'\n<@&{role_id}>' if part==0 else '')+'\n'+rest
                    message=await target.send(post_content,
                                              allowed_mentions=discord.AllowedMentions(
                                                  everyone=False,users=False,
                                                  roles=[discord.Object(id=role_id)] if part==0 else [],
                                                  replied_user=False))
                except (discord.Forbidden,discord.NotFound):
                    with delivery.connection() as db:
                        db.execute('DELETE FROM assignment_post WHERE nh=? AND week=? AND part=?',(nh,week,part))
                    log.exception('HK weekly signup rejected for NH %s',nh)
                    break
                except Exception:
                    log.exception('HK weekly signup delivery uncertain for NH %s, week %s, part %s; review before retrying',nh,week,part)
                    break
                with delivery.connection() as db:
                    db.execute('UPDATE assignment_post SET message_id=? WHERE nh=? AND week=? AND part=?',
                               (message.id,nh,week,part))
            elif message_id:
                try:
                    message=await target.fetch_message(message_id)
                except discord.NotFound:
                    # A deleted assignment post falls back to Council, rather than reposting.
                    continue
            else:
                continue
            # Persisted snapshot wins on retries: seed the exact emojis from the published post.
            for value in dict.fromkeys(json.loads(row[4]).values()):
                try:
                    await message.add_reaction(value)
                except discord.HTTPException:
                    log.exception('Cannot seed HK task reaction %s on %s',value,message.id)


async def assignees(guild,delivery,nh,channel_id,task_id,task_emoji,local):
    initialize(delivery)
    with delivery.connection() as db:
        rows=db.execute('SELECT message_id,tasks FROM assignment_post WHERE nh=? AND week=? ORDER BY part',
                        (nh,week_start(local))).fetchall()
    for message_id,mapping_json in rows:
        mapping=json.loads(mapping_json)
        value=mapping.get(str(task_id))
        if not value or not task_emoji or emoji_key(value)!=emoji_key(task_emoji) or not message_id:
            continue
        channel=await guild.fetch_channel(channel_id)
        try:
            message=await channel.fetch_message(message_id)
        except discord.NotFound:
            continue
        for reaction in message.reactions:
            if emoji_key(reaction.emoji)==emoji_key(value):
                return sorted({user.id async for user in reaction.users() if not user.bot})
    return []
