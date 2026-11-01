"""Month selection and collection for the manual birthday roundup."""
import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord

BIRTHDAYS_CHANNEL=1392147228684058644
GENERAL_CHANNEL=648223397205114910


def month_number(value=None,now=None):
    if value is None:
        today=(now or datetime.now(ZoneInfo('America/New_York'))).date()
        return (today.replace(day=1)-timedelta(days=1)).month
    value=value.strip().lower()
    for month in range(1,13):
        if value in (str(month),str(month).zfill(2),calendar.month_name[month].lower(),calendar.month_abbr[month].lower()):
            return month
    raise ValueError('Use $birthdays October (or $birthdays 10). With no month, the previous month is used.')


async def collect(guild,month,normalize):
    channel=await guild.fetch_channel(BIRTHDAYS_CHANNEL)
    seen=set()
    result=[]
    async for message in channel.history(limit=None,oldest_first=False):
        if message.author.bot or message.author.id in seen:
            continue
        birthday=normalize(message.content)
        if not birthday:
            continue
        try:
            datetime(2000,*birthday)
        except (ValueError,TypeError):
            continue
        seen.add(message.author.id)
        if birthday[0]!=month:
            continue
        member=guild.get_member(message.author.id)
        if member is None:
            try:
                member=await guild.fetch_member(message.author.id)
            except discord.NotFound:
                continue
        if not member.bot:
            result.append((member.id,birthday))
    return sorted(result,key=lambda row:(row[1][1],row[0]))


def roundup_messages(month,birthdays):
    name=calendar.month_name[month]
    lines=[f"**Let's celebrate all of our {name} Birthdays one more time!**\nWe have had:\n"]
    lines.extend(f'<@{user_id}> ({name} {birthday[1]})' for user_id,birthday in birthdays)
    pages=[]
    current=''
    for line in lines:
        if len(current)+len(line)+1>1800:
            pages.append(current)
            current=f'**{name} Birthdays (continued)**\n'
        current+=line+'\n'
    pages.append(current+'\n@everyone')
    return pages
