"""Resolve member mentions before rendering, retaining readable numeric fallbacks."""
import re
import discord

MENTION=re.compile(r'<@!?(\d+)>')


async def prepare_mentions(guild,content):
    for user_id in dict.fromkeys(int(match[1]) for match in MENTION.finditer(content)):
        try:
            await guild.fetch_member(user_id)
        except (discord.NotFound,discord.Forbidden,discord.HTTPException):
            # Former members may be unavailable; the ID must still be visible.
            pass
    def replace(match):
        uid=match[1]
        suffix=f' ({uid})'
        return match[0] if content[match.end():].startswith(suffix) else match[0]+suffix
    return MENTION.sub(replace,content)
