"""Giveaways commands and their supporting helpers."""

from .common import *
# from datetime import datetime, timedelta, timezone

GIVEAWAYS_JSON_PATH = "giveaways.json"



def _round_dt_to_nearest_hour(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("dt must be timezone-aware")
    discard = datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    dt_floor = dt - discard
    if dt.minute >= 30:
        dt_floor += datetime.timedelta(hours=1)
    return dt_floor



def _load_giveaways_json(path: str) -> dict:
    if not os.path.exists(path):
        return {"giveaways": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "giveaways" not in data or not isinstance(data["giveaways"], list):
            return {"giveaways": []}
        return data
    except Exception:
        return {"giveaways": []}



def _save_giveaways_json(path: str, data: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)



@command_handler.Command(
    AccessType.PRIVATE,
    desc="Automatically host a giveaway.\n"
         "Examples:\n"
         "  `$give 89 BEMs`\n"
         "  `$give 89 BEMs -3w` (3 winners)\n"
         "  `$give 89 BEMs -12h` (12 hours, 1–36)\n"
         "  `$give 89 BEMs -784803565151453214c` (council only: post in channel id)"
)
async def give(activator: Neighbor, context: Context):
    from .families import has_role
    if len(context.args) < 1:
        raise CommandArgsError("`$give` needs to know what you want to give away! Try $help give")

    raw = context.content

    # --- Council membership check (assumed correct per your note) ---
    council_role = context.guild.get_role(648188387836166168)
    is_council = has_role(context.author, council_role)

    # --- Parse flags ---
    winners = 1
    hours = 24

    w_match = re.search(r'-(\d+)w\b', raw)
    if w_match:
        winners = max(1, int(w_match.group(1)))

    h_match = re.search(r'-(\d+)h\b', raw)
    if h_match:
        hours = int(h_match.group(1))
        if hours < 0:
            hours = 0
        elif hours > 36:
            hours = 36

    # Optional channel override for council: -<#id>c
    channel_override_id: int | None = None
    c_match = re.search(r'-(\d+)c\b', raw)
    if c_match and is_council:
        channel_override_id = int(c_match.group(1))

    # Clean message text shown to users by stripping flags
    cleaned = re.sub(r'\s*-\d+[whc]\b', '', raw).strip()
    cleaned = cleaned.split(" ", 1)[1]

    # --- Build message ---
    res = "__**New Giveaway**__\n"
    res += f"> **{cleaned}**"
    res += f"\n> Hosted generously by <@{activator.ID}>"
    if winners > 1:
        res += f"\n> Winners: {winners}"
    res += f"\n<@&827634110238556160> this giveaway ends in {hours}H!"
    res += "\nReact with <:giveaway:1067499350705582124> to enter!"

    # --- Choose channel ---
    post_channel_id = context.ID_bundle.giveaway_channel
    if channel_override_id is not None:
        post_channel_id = channel_override_id

    gc = await context.guild.fetch_channel(post_channel_id)
    target = await gc.send(res)
    await target.add_reaction("<:giveaway:1067499350705582124>")

    # --- Compute end time in UTC (rounded to nearest hour) ---
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    end_dt_rounded = _round_dt_to_nearest_hour(now_utc + datetime.timedelta(hours=hours))

    # --- Persist to JSON (save BOTH message_id and channel_id) ---
    data = _load_giveaways_json(GIVEAWAYS_JSON_PATH)
    data["giveaways"].append({
        "message_id": str(target.id),
        "channel_id": str(gc.id),            # <- actual posting channel
        "guild_id": str(context.guild.id),
        "host_id": str(activator.ID),
        "winners": int(winners),
        "duration_hours": int(hours),
        "created_utc": now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "end_utc": end_dt_rounded.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "end_epoch": int(end_dt_rounded.timestamp()),
        "prize_text": cleaned,
        "used_channel_override": bool(channel_override_id is not None),
    })
    _save_giveaways_json(GIVEAWAYS_JSON_PATH, data)


GIVEAWAYS_JSON_PATH = "giveaways.json"

CLOSED_GIVEAWAYS_JSON_PATH = "closed_giveaways.json"


GIVEAWAY_EMOJI = "<:giveaway:1067499350705582124>"

REROLL_EMOJI = "<:reroll:1060038218113888266>"



def _round_dt_to_nearest_hour(dt: datetime.datetime) -> datetime.datetime:
    if dt.tzinfo is None:
        raise ValueError("dt must be timezone-aware")
    discard = datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    dt_floor = dt - discard
    if dt.minute >= 30:
        dt_floor += datetime.timedelta(hours=1)
    return dt_floor



def _load_giveaways_json(path: str) -> dict:
    if not os.path.exists(path):
        return {"giveaways": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "giveaways" not in data or not isinstance(data["giveaways"], list):
            return {"giveaways": []}
        return data
    except Exception:
        return {"giveaways": []}



def _save_giveaways_json(path: str, data: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


GIVEAWAYS_JSON_PATH = "giveaways.json"

CLOSED_GIVEAWAYS_JSON_PATH = "closed_giveaways.json"


GIVEAWAY_EMOJI = "<:giveaway:1067499350705582124>"

REROLL_EMOJI = "<:reroll:1060038218113888266>"



@command_handler.Loop(
    minutes=5,
    desc="Check to see if any giveaway from json has past its end time but hasn't been closed yet."
)
async def close_giveaways(client):
    """
    1) Close any giveaways that need to be closed
    2) Pick random winner(s) from those who reacted with GIVEAWAY_EMOJI
    3) Announce winners in the giveaway channel (with reroll reaction)
    4) Edit the ORIGINAL giveaway message to show it is closed + display winner(s)
    5) Move closed giveaway to CLOSED_GIVEAWAYS_JSON_PATH with winner_announce_message_id
    """
    from .community import get_users_who_reacted
    now_epoch = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    open_data = _load_giveaways_json(GIVEAWAYS_JSON_PATH)
    closed_data = _load_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH)

    open_giveaways = open_data.get("giveaways", [])
    if not open_giveaways:
        return

    still_open = []
    newly_closed = []

    for g in open_giveaways:
        # Skip if not ready
        try:
            end_epoch = int(g.get("end_epoch", 0))
        except Exception:
            end_epoch = 0

        if end_epoch > now_epoch:
            still_open.append(g)
            continue

        # Parse required fields
        try:
            guild_id = int(g["guild_id"])
            channel_id = int(g["channel_id"])
            message_id = int(g["message_id"])
            host_id = int(g.get("host_id", 0))
            winners_needed = max(1, int(g.get("winners", 1)))
        except Exception:
            still_open.append(g)
            continue

        # Get guild (cache miss fallback)
        guild = client.get_guild(guild_id)
        if guild is None:
            try:
                guild = await client.fetch_guild(guild_id)
            except Exception:
                still_open.append(g)
                continue

        # Fetch channel + original giveaway message
        try:
            channel = await guild.fetch_channel(channel_id)
            giveaway_message = await channel.fetch_message(message_id)
        except Exception:
            still_open.append(g)
            continue

        # If it already looks closed, don't double-close (extra guard)
        try:
            if giveaway_message.content and "__**CLOSED**__" in giveaway_message.content:
                # Treat it as already closed; move it out of open JSON to prevent repeats.
                # (If you *don't* want this, delete this block.)
                closed_entry = dict(g)
                closed_entry["closed_utc"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                closed_entry.setdefault("winner_ids", [])
                closed_entry.setdefault("winner_announce_message_id", None)
                newly_closed.append(closed_entry)
                continue
        except Exception:
            pass

        # Entrants from reaction
        try:
            entrants = await get_users_who_reacted(giveaway_message, GIVEAWAY_EMOJI)
        except Exception:
            entrants = []

        entrant_ids = []
        seen = set()
        for u in entrants:
            try:
                if getattr(u, "bot", False):
                    continue
                uid = int(u.id)
                if uid in seen:
                    continue
                seen.add(uid)
                entrant_ids.append(uid)
            except Exception:
                continue

        # Pick winner(s)
        winner_ids = []
        if entrant_ids:
            k = min(winners_needed, len(entrant_ids))
            winner_ids = random.sample(entrant_ids, k)

        # Winner text for both announcement + original edit
        if not winner_ids:
            winners_line = "Winners: *(none — no valid entrants)*"
            announce_text = (
                "**Giveaway ended!**\n"
                "No valid entrants were found for this giveaway. 😭"
            )
        else:
            winners_ping = ", ".join(f"<@{wid}>" for wid in winner_ids)
            winners_line = f"Winners: {winners_ping}"
            announce_text = (
                "**Giveaway ended!**\n"
                f"Congrats {winners_ping}! 🎉\n"
                f"Message <@{host_id}> to claim your prize.\n\n"
                f"React with {REROLL_EMOJI} to reroll this giveaway."
            )

        # Announce and add reroll reaction
        try:
            announce_msg = await channel.send(announce_text)
            await announce_msg.add_reaction(REROLL_EMOJI)
        except Exception:
            still_open.append(g)
            continue

        # Edit ORIGINAL giveaway message to mark closed + show winners
        try:
            original_content = giveaway_message.content or ""
            closed_stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            edited_content = (
                f"{original_content}\n\n"
                f"__**CLOSED**__ ({closed_stamp})\n"
                f"> {winners_line}\n"
                f"> Announcement: {announce_msg.jump_url}"
            )
            await giveaway_message.edit(content=edited_content)
        except Exception:
            # Even if edit fails, we still consider it closed (you already announced)
            pass

        # Move to closed JSON
        closed_entry = dict(g)
        closed_entry["closed_utc"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        closed_entry["winner_ids"] = [str(w) for w in winner_ids]
        closed_entry["winner_announce_message_id"] = str(announce_msg.id)

        newly_closed.append(closed_entry)

    # Persist
    if newly_closed:
        open_data["giveaways"] = still_open
        closed_data.setdefault("giveaways", [])
        closed_data["giveaways"].extend(newly_closed)

        _save_giveaways_json(GIVEAWAYS_JSON_PATH, open_data)
        _save_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH, closed_data)


CLOSED_GIVEAWAYS_JSON_PATH = "closed_giveaways.json"

GIVEAWAY_EMOJI = "<:giveaway:1067499350705582124>"

REROLL_EMOJI = "<:reroll:1060038218113888266>"



@command_handler.Uncontested(type="REACTION")
async def reroll_giveaway(context: Context):
    from .community import get_users_who_reacted
    from .families import has_role
    emoji = str(context.emoji)
    if emoji != REROLL_EMOJI:
        print(emoji)
        return

    # We only reroll when reacting to the *announcement* message
    reacted_message_id = str(context.message.id)

    closed_data = _load_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH)
    closed_list = closed_data.get("giveaways", [])

    giveaway = None
    for g in closed_list:
        if str(g.get("winner_announce_message_id")) == reacted_message_id:
            giveaway = g
            break

    if giveaway is None:
        return

    # Permission: council OR original host
    council_role = context.guild.get_role(648188387836166168)
    is_council = has_role(context.author, council_role)

    try:
        is_host = int(giveaway.get("host_id", 0)) == int(context.author.id)
    except Exception:
        is_host = False

    if not (is_council or is_host):
        return

    # Fetch original giveaway message to determine entrants
    try:
        channel_id = int(giveaway["channel_id"])
        message_id = int(giveaway["message_id"])
        channel = await context.guild.fetch_channel(channel_id)
        giveaway_message = await channel.fetch_message(message_id)
    except Exception:
        return

    # Entrants are anyone who reacted with the giveaway emoji
    try:
        entrants = await get_users_who_reacted(giveaway_message, GIVEAWAY_EMOJI)
    except Exception:
        entrants = []

    entrant_ids = []
    seen = set()
    for u in entrants:
        try:
            if getattr(u, "bot", False):
                continue
            uid = int(u.id)
            if uid in seen:
                continue
            seen.add(uid)
            entrant_ids.append(uid)
        except Exception:
            continue

    if not entrant_ids:
        msg = await channel.send("**Reroll failed:** No valid entrants were found for this giveaway. 😭")
        await msg.add_reaction(REROLL_EMOJI)
        return

    # Don’t pick someone who already won previously if possible
    prior_winners = set()
    try:
        prior_winners.update(int(x) for x in giveaway.get("winner_ids", []) if str(x).isdigit())
    except Exception:
        pass

    eligible = [uid for uid in entrant_ids if uid not in prior_winners]
    if not eligible:
        eligible = entrant_ids  # everyone already won; allow repeats

    # Number of winners for reroll: same as original winners
    winners_needed = max(1, int(giveaway.get("winners", 1)))
    k = min(winners_needed, len(eligible))
    new_winner_ids = random.sample(eligible, k)

    winners_ping = ", ".join(f"<@{wid}>" for wid in new_winner_ids)
    host_id = int(giveaway.get("host_id", 0))

    reroll_text = (
        "**Giveaway rerolled!**\n"
        f"New winner(s): {winners_ping} 🎉\n"
        f"Message <@{host_id}> to claim your prize.\n\n"
        f"React with {REROLL_EMOJI} to reroll this giveaway again."
    )

    new_announce = await channel.send(reroll_text)
    await new_announce.add_reaction(REROLL_EMOJI)

    # Update closed_giveaways:
    # - store latest announce message id so future rerolls work
    # - append new winners to winner_ids (audit trail + helps avoid repeats)
    giveaway["winner_announce_message_id"] = str(new_announce.id)
    existing = [str(x) for x in giveaway.get("winner_ids", [])]
    for wid in new_winner_ids:
        existing.append(str(wid))
    giveaway["winner_ids"] = existing
    giveaway["last_reroll_utc"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    _save_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH, closed_data)

