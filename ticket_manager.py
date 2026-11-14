import os
import copy
import logging
import shelve
import asyncio
import re
from types import SimpleNamespace
import discord
from discord import TextChannel
from discord.channel import _guild_channel_factory

# ──────── REMEMBER SYSTEM ───────────────────────────────────────────

# If value given, stores to DB. If value None, retrieves data.
def remember(key, value=Ellipsis, delete=False):
    with shelve.open("data/persistentdata") as db:
        if value is not None and value is not Ellipsis:
            db[key] = value
            return value;
        elif value is None or delete:
            return db.pop(key, None)
        else:
            return db.get(key)

# ──────── CATEGORY MANAGEMENT ───────────────────────────────────────

BASE_OPEN=1033246546986291260
BASE_CLOSED=1033247090282856509
LEGACY_CLOSED=[BASE_CLOSED,1183992886820343869,1201914070027219016,1224193594353516605]
_locks={}
_unknown_channel_types=set()
SUPPORT_MESSAGE_ID=1033540464441303200
_recovery_lock=asyncio.Lock()


def ticket_lock(guild):
    return _locks.setdefault(guild.id,asyncio.Lock())


def get_archive_categories():
    saved=remember("archive_categories")
    return LEGACY_CLOSED if saved is None else saved


def save_archive_categories(categories):
    remember("archive_categories",categories)


async def fetch_ticket_channels(guild):
    """Keep ticket discovery working when Discord introduces a channel type."""
    try:
        return await guild.fetch_channels()
    except discord.InvalidData:
        # discord.py 2.6.4 rejects the whole response if one type is unknown.
        # Use the same endpoint and constructors, tolerating only unknown
        # types. HTTP/permission failures still propagate rather than using a
        # potentially stale cache for capacity checks or category deletion.
        data=await guild._state.http.get_all_guild_channels(guild.id)
        channels=[]
        for payload in data:
            factory,_=_guild_channel_factory(payload['type'])
            if factory is not None:
                channels.append(factory(guild=guild,state=guild._state,data=payload))
                continue
            parent=payload.get('parent_id')
            channels.append(SimpleNamespace(id=int(payload['id']),
                category_id=int(parent) if parent is not None else None,
                type=payload['type'],name=payload.get('name','')))
            identity=(guild.id,payload['type'])
            if identity not in _unknown_channel_types:
                logging.getLogger(__name__).warning(
                    'Ticket discovery is retaining occupancy for unsupported channel type %s in guild %s',
                    payload['type'],guild.id)
                _unknown_channel_types.add(identity)
        return channels


async def category_snapshot(guild,kind='closed'):
    channels=await fetch_ticket_channels(guild)
    key=f'ticket_categories:{guild.id}:{kind}'
    saved=remember(key)
    ids=set(saved or [])
    ids.update(get_archive_categories() if kind=='closed' else [BASE_OPEN])
    prefix=kind+'-tickets'
    categories=[c for c in channels if isinstance(c,discord.CategoryChannel) and
                (c.id in ids or re.fullmatch(re.escape(prefix)+r'(?:-\d+)?',c.name.lower()))]
    categories.sort(key=lambda c:(c.id!=(BASE_CLOSED if kind=='closed' else BASE_OPEN),c.position,c.id))
    remember(key,[c.id for c in categories])
    if kind=='closed':
        save_archive_categories([c.id for c in categories])
    return categories,channels


async def ensure_category_capacity(guild,kind='closed'):
    categories,channels=await category_snapshot(guild,kind)
    for category in categories:
        if sum(c.category_id==category.id for c in channels if not isinstance(c,discord.CategoryChannel))<50:
            return category
    template=categories[0] if categories else None
    if template is None:
        other,_=await category_snapshot(guild,'open' if kind=='closed' else 'closed')
        template=other[0] if other else None
    if template is None:
        raise RuntimeError('No ticket category permission template exists; restore a private base ticket category first.')
    used={c.name for c in categories}
    number=1
    while f'{kind}-tickets-{number}' in used:
        number+=1
    category=await guild.create_category_channel(name=f'{kind}-tickets-{number}',overwrites=template.overwrites,
                                                reason='Additional ticket capacity')
    categories.append(category)
    remember(f'ticket_categories:{guild.id}:{kind}',[c.id for c in categories])
    if kind=='closed':
        save_archive_categories([c.id for c in categories])
    return category


async def get_all_closed_tickets(guild):
    categories,channels=await category_snapshot(guild)
    ids={c.id for c in categories}
    return [c for c in channels if isinstance(c,discord.TextChannel) and c.category_id in ids]


async def cleanup_ticket_categories(guild):
    async with ticket_lock(guild):
        for kind in ('closed','open'):
            categories,channels=await category_snapshot(guild,kind)
            # Keep one base category as a permission template and a ready landing area.
            for category in categories[1:]:
                if not any(getattr(c,'category_id',None)==category.id for c in channels):
                    fresh=await fetch_ticket_channels(guild)
                    if not any(getattr(c,'category_id',None)==category.id for c in fresh):
                        try:
                            await category.delete(reason='Empty ticket overflow category')
                        except discord.NotFound:
                            pass
                        except discord.Forbidden:
                            logging.getLogger(__name__).warning("Cannot remove empty ticket category %s",category.id)
            await category_snapshot(guild,kind)


async def archive_ticket(guild,ticket):
    async with ticket_lock(guild):
        destination=await ensure_category_capacity(guild)
        await ticket.edit(category=destination)

# ──────── TICKET RESTORATION ────────────────────────────────────────

async def restore_ticket(ticket: TextChannel, user, name, open_category, guild, rank1, mission_control):
    await ticket.edit(name=name, category=open_category)
    await ticket.set_permissions(guild.default_role, read_messages=False)
    await ticket.set_permissions(user, read_messages=True)
    await ticket.set_permissions(rank1, read_messages=True, send_messages=False)
    await ticket.send(f"Thank you for reaching out to the Council. Your private ticket channel has been unarchived for you and is located here <@{user.id}>. Drop a message letting us know what we can help you with!")
    await mission_control.send(f"<@&{648188387836166168}> **be advised**: <@{user.id}> has reopened a support ticket at <#{ticket.id}>")
    new_tickets = remember("new_tickets") or []
    new_tickets.append(ticket.id);
    remember("new_tickets", new_tickets)

# ──────── OPEN TICKET LOGIC ─────────────────────────────────────────

async def _open_ticket(emoji, user, guild, FF, *, notify_existing=True):
    target = str(user.id)
    name = user.display_name.replace(" ", "-")


    open_categories,all_channels=await category_snapshot(guild,"open")
    open_ids={category.id for category in open_categories}
    mission_control = await guild.fetch_channel(FF.mission_control_channel)
    rank1 = guild.get_role(1205232195703144488)

    for ticket in all_channels:
        if not isinstance(ticket,TextChannel) or ticket.category_id not in open_ids:
            continue
        if ticket.topic == target:
            if notify_existing:
                await ticket.edit(name=name)
                await ticket.send(f"Thank you for reaching out to the Council again. Your private ticket channel is located here <@{user.id}>. Drop a message letting us know what we can help you with!")
            return ticket;

    for ticket in await get_all_closed_tickets(guild):
        if ticket.topic == target:
            open_tickets_cat=await ensure_category_capacity(guild,"open")
            await restore_ticket(ticket, user, name, open_tickets_cat, guild, rank1, mission_control)
            return ticket;

    open_tickets_cat=await ensure_category_capacity(guild,"open")
    overwrites=dict(open_tickets_cat.overwrites)
    everyone=copy.copy(overwrites.get(guild.default_role,discord.PermissionOverwrite()))
    everyone.view_channel=False
    overwrites[guild.default_role]=everyone
    user_access=copy.copy(overwrites.get(user,discord.PermissionOverwrite()))
    user_access.view_channel=True
    overwrites[user]=user_access
    ticket = await guild.create_text_channel(name=name, category=open_tickets_cat, topic=target,overwrites=overwrites)
    await ticket.set_permissions(guild.default_role, read_messages=False)
    await ticket.set_permissions(user, read_messages=True)
    await ticket.set_permissions(rank1, read_messages=True, send_messages=False)
    await ticket.send(f"Thank you for reaching out to the Council via Greg for the first time! Your private ticket channel is located here <@{user.id}>. Drop a message letting us know what we can help you with!")
    await mission_control.send(f"<@&{648188387836166168}> **be advised**: <@{user.id}> has opened a new support ticket at <#{ticket.id}>")
    new_tickets = remember("new_tickets") or []
    new_tickets.append(ticket.id);
    remember("new_tickets", new_tickets)
    return ticket;

async def clear_support_reaction(guild,FF,emoji,user,*,message=None):
    try:
        if message is None:
            channel=await guild.fetch_channel(FF.support_request_channel)
            message=await channel.fetch_message(SUPPORT_MESSAGE_ID)
        await message.remove_reaction(emoji,user)
    except discord.HTTPException:
        logging.getLogger(__name__).warning('Ticket opened, but could not clear support reaction for %s',user.id)


async def open_ticket(emoji,user,guild,FF,*,notify_existing=True):
    async with ticket_lock(guild):
        ticket=await _open_ticket(emoji,user,guild,FF,notify_existing=notify_existing)
        # A failed open must leave the request available for startup recovery.
        if emoji:
            await clear_support_reaction(guild,FF,emoji,user)
    try:
        await cleanup_ticket_categories(guild)
    except discord.HTTPException:
        logging.getLogger(__name__).exception("Ticket opened, but category cleanup failed")
    return ticket


async def recover_support_requests(client,FF):
    """Reconcile queued reactions on the initial startup maintenance pass and retries."""
    guild=client.get_guild(FF.guild)
    if guild is None:
        return
    async with _recovery_lock:
        channel=await guild.fetch_channel(FF.support_request_channel)
        message=await channel.fetch_message(SUPPORT_MESSAGE_ID)
        pending={}
        # Match the live reaction handler: any non-bot reaction requests a ticket.
        # Read all users before making changes; a partial read is not a request list.
        for reaction in message.reactions:
            async for user in reaction.users(limit=None):
                if not user.bot:
                    pending.setdefault(user.id,[]).append(reaction.emoji)
        for uid,emojis in pending.items():
            try:
                user=guild.get_member(uid) or await guild.fetch_member(uid)
                if user.bot:
                    continue
                await open_ticket(emojis[0],user,guild,FF,notify_existing=False)
                for emoji in emojis[1:]:
                    await clear_support_reaction(guild,FF,emoji,user,message=message)
            except discord.NotFound:
                # Someone who left the server cannot be given a ticket.
                logging.getLogger(__name__).warning('Cannot recover support request for missing member/channel %s',uid)
            except Exception:
                # Leave this user's reaction intact and continue other requests.
                logging.getLogger(__name__).exception('Support request recovery failed for %s; will retry',uid)
