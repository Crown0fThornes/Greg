"""Annual November 1–9 Farmmas season announcements."""
from datetime import datetime,timedelta,timezone

import discord

GUILD_ID=647883751853916162
GENERAL_CHANNEL=648223397205114910
LOGO_ID=1170071779037945907
SERVER_TIME=timezone(timedelta(hours=-4))
INFO='Use `$info farmmas` in <#784150346397253682> to learn more.'


def season_messages(today,logo):
    if today.month!=11 or not 1<=today.day<=9:
        return []
    if today.day==9:
        return ["# Farmmas season has arrived!!\n\n"
                "May the festivities begin! Let's hang the lights, switch to Farmmas colors, and get into the giving spirit!\n\n"
                "**We've only got 1 month to wait before the best FF holiday begins!**\n\n"
                +INFO+"\n\n@everyone", ' '.join([str(logo)]*3)]
    days=9-today.day
    return [f"# Farmmas season arrives in {days} {"day" if days==1 else "days"}!!\n\n"
            "Farmmas is FF's annual winter holiday taking place from December 9th to 20th. The festivities begin soon!\n\n"
            +INFO+"\n\n@everyone"]


async def announce(client,*,now=None):
    today=(now or datetime.now(timezone.utc)).astimezone(SERVER_TIME).date()
    logo=client.get_emoji(LOGO_ID) or discord.PartialEmoji(name='farmmas_ff_logo',id=LOGO_ID)
    messages=season_messages(today,logo)
    if not messages:
        return
    guild=client.get_guild(GUILD_ID)
    if guild is None:
        return
    channel=await guild.fetch_channel(GENERAL_CHANNEL)
    for content in messages:
        await channel.send(content,allowed_mentions=discord.AllowedMentions(
            everyone='@everyone' in content,users=False,roles=False,replied_user=False))
