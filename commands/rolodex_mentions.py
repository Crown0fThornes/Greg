"""Names independent of Discord's mention cache, with clickable IDs retained."""
import re
import discord

MENTION=re.compile(r'<@!?(\d+)>')


def display_name(member):
    for field in ('display_name','global_name','name'):
        value=getattr(member,field,None)
        if isinstance(value,str) and value.strip():
            return discord.utils.escape_mentions(discord.utils.escape_markdown(value.replace('\n',' ')[:80]))
    return None


async def prepare_mentions(guild,content):
    names={}
    for user_id in dict.fromkeys(int(match[1]) for match in MENTION.finditer(content)):
        try:
            member=await guild.fetch_member(user_id)
        except (discord.NotFound,discord.Forbidden,discord.HTTPException):
            # A fetch cannot force the reader's Discord client to resolve mentions.
            # Use a cached readable name if available; always retain the numeric ID.
            member=guild.get_member(user_id) if hasattr(guild,'get_member') else None
        names[str(user_id)]=display_name(member)
    def replace(match):
        uid=match[1]
        suffix=f' ({uid})'
        mention=match[0] if content[match.end():].startswith(suffix) else match[0]+suffix
        prefix=f'{names[uid]} — ' if names[uid] else ''
        if prefix and content[:match.start()].endswith(prefix):
            prefix=''
        return prefix+mention
    return MENTION.sub(replace,content)
