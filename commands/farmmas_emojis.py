"""Reconcile the Farmmas 2026 emoji inventory against its signup reactions."""
import datetime
import logging

import discord

from custom_types import Item, Neighbor


MESSAGE_ID = 1569805095821115413
CHANNEL_ID = 1218041302998974584
EMOJIS = ("❄️", "☃️", "🎄", "✨", "🎀")
log = logging.getLogger(__name__)


async def reconcile(message, set_nick, *, now=None):
    now = now or datetime.datetime.now()
    expiration = now.replace(year=2027, month=1, day=9, hour=23, minute=59,
                             second=59, microsecond=0)
    if now >= expiration:
        return

    # Finish reading every reaction before changing inventory. An API failure
    # must not turn a partial response into a list of withdrawn reactions.
    selected = {emoji: set() for emoji in EMOJIS}
    for reaction in message.reactions:
        emoji = str(reaction.emoji)
        if emoji in selected:
            async for user in reaction.users(limit=None):
                if not user.bot:
                    selected[emoji].add(user.id)

    guild = message.guild
    ids = set().union(*selected.values())
    for saved in Neighbor.read_all_neighbors():
        if int(saved.get_family()) == guild.id and any(
            saved.get_item_of_name(f"Farmmas emoji {emoji}") for emoji in EMOJIS
        ):
            ids.add(saved.ID)

    for uid in sorted(ids):
        neighbor = Neighbor(uid, guild.id)
        member = None
        if any(uid in users for users in selected.values()):
            member = guild.get_member(uid)
            if member is None:
                try:
                    member = await guild.fetch_member(uid)
                except discord.NotFound:
                    continue
        changed = False
        for emoji, users in selected.items():
            name = f"Farmmas emoji {emoji}"
            existing = neighbor.get_item_of_name(name)
            if uid in users:
                # Awards stop at the end of 2026, just like the live handler.
                if existing is None and now.year <= 2026:
                    neighbor.bestow_item(Item(name, "event_emoji", expiration.timestamp(),
                                              emoji=emoji, display="True"))
                    changed = True
            elif existing is not None:
                neighbor.vacate_item(existing)
                changed = True
        if changed:
            if member is None:
                member = guild.get_member(uid)
                if member is None:
                    try:
                        member = await guild.fetch_member(uid)
                    except discord.NotFound:
                        continue
            try:
                await set_nick(member, guild)
            except discord.Forbidden:
                log.warning("Cannot update Farmmas nickname for %s", uid)
