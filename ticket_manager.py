import os
import shelve
from discord import TextChannel

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

def get_archive_categories():
    return remember("archive_categories") or [1033247090282856509, 1183992886820343869, 1201914070027219016, 1224193594353516605]

def save_archive_categories(categories):
    remember("archive_categories", categories)

async def ensure_category_capacity(guild):
    categories = get_archive_categories()
    latest_cat = await guild.fetch_channel(categories[-1]) if categories else None

    if not latest_cat or len(latest_cat.channels) >= 50:
        new_cat = await guild.create_category_channel(name=f"closed-tickets-{len(categories)+1}")
        categories.append(new_cat.id)
        save_archive_categories(categories)

# ──────── CLOSED TICKETS ACCESS ─────────────────────────────────────

async def get_all_closed_tickets(guild):
    channels = []
    for cat_id in get_archive_categories():
        category = await guild.fetch_channel(cat_id)
        channels.extend(category.channels)
    return channels

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

async def open_ticket(emoji, user, guild, FF):
    target = str(user.id)
    name = user.display_name.replace(" ", "-")

    await ensure_category_capacity(guild)

    support_channel = await guild.fetch_channel(FF.support_request_channel)
    message = await support_channel.fetch_message(1033540464441303200)
    open_tickets_cat = await guild.fetch_channel(FF.open_tickets_category)
    mission_control = await guild.fetch_channel(FF.mission_control_channel)
    rank1 = guild.get_role(1205232195703144488)

    if emoji:
        await message.remove_reaction(emoji, user)

    for ticket in open_tickets_cat.channels:
        if ticket.topic == target:
            await ticket.edit(name=name)
            await ticket.send(f"Thank you for reaching out to the Council again. Your private ticket channel is located here <@{user.id}>. Drop a message letting us know what we can help you with!")
            return ticket;

    for ticket in await get_all_closed_tickets(guild):
        if ticket.topic == target:
            await restore_ticket(ticket, user, name, open_tickets_cat, guild, rank1, mission_control)
            return ticket;

    ticket = await guild.create_text_channel(name=name, category=open_tickets_cat, topic=target)
    await ticket.set_permissions(guild.default_role, read_messages=False)
    await ticket.set_permissions(user, read_messages=True)
    await ticket.set_permissions(rank1, read_messages=True, send_messages=False)
    await ticket.send(f"Thank you for reaching out to the Council via Greg for the first time! Your private ticket channel is located here <@{user.id}>. Drop a message letting us know what we can help you with!")
    await mission_control.send(f"<@&{648188387836166168}> **be advised**: <@{user.id}> has opened a new support ticket at <#{ticket.id}>")
    new_tickets = remember("new_tickets") or []
    new_tickets.append(ticket.id);
    remember("new_tickets", new_tickets)
    return ticket;