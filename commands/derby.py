"""Derby commands and their supporting helpers."""

from .common import *
    
@command_handler.Command(access_type=AccessType.PRIVATE)
async def bunny_count(activator: Neighbor, context: Context):
    from .families import get_family_from_user
    final_msg = await context.send("Counting...")
    
    totals = {
        'B': 0,
        'C': 0,
        'G': 0,
        'P': 0,
        'S': 0,
        'Z': 0
    }
    
    def first_number(s: str):
        match = re.search(r'\d+(\.\d+)?', s)  # matches integers or decimals
        if match:
            return float(match.group()) if '.' in match.group() else int(match.group())
        return None
    
    bunny_channel = await context.guild.fetch_channel(1203772906497380472);
    done = False;
    async for msg in bunny_channel.history(limit=None, oldest_first=False):
        if msg.id == 1416127796136120472:
            done = True
            
        fam = get_family_from_user(msg.author)
        if fam == '0':
            continue;
        
        totals[fam] += first_number(msg.content) or 0;
            
        if done:
            break
        
    await final_msg.edit(content=str(totals))





















@command_handler.Command(access_type=AccessType.PRIVATE)
async def points_double_check(activator: Neighbor, context: Context):
    """
    Sender = message.author (Member)
    Receiver = first user mention in message.content (reply-mentions ignored)

    Scoring:
      - Only the first @mention in content counts
      - Same-family: 0 points; does NOT mark 'already received'
      - Cross-family (counted): sender +3; receiver +1 (first counted) else +2
      - Per-sender cap: only first TWO counted sends award points
      - 'Already received' is based ONLY on prior COUNTED receives

    Output per family:
      - Total points
      - Unique Sender # (≥1 counted send)
      - Total Sender # (counted sends)
      - Unique Receiver # (≥1 counted receive, i.e., receivers in that family)
      - Total Receiver # (counted receives for that family)
      - Unique Targets # (distinct users this family sent counted notes to)
      - Then a separate line per family listing their targets as <@id>×count
      - Final line: total number of multiple-mention messages in content (no notices sent)
    """
    from .families import get_family_from_user
    import re

    DEFAULT_CHANNEL_ID = 1403141598300082317
    STOP_AT_ID = 1404676398232113212  # stop when this message is reached (exclusive)
    chan_id = None

    # Optional arg: channel id or channel mention; else default
    if getattr(context, "args", None):
        raw = str(context.args[0]).strip()
        try:
            if raw.startswith("<#") and raw.endswith(">"):
                chan_id = int(raw[2:-1])
            else:
                chan_id = int(raw)
        except Exception:
            chan_id = None
    chan_id = chan_id or DEFAULT_CHANNEL_ID

    channel = await context.guild.fetch_channel(chan_id)
    final_msg = await context.send(f"Double-checking notes in <#{chan_id}>…")

    # --- Scoreboards ---
    fam_points = {"B": 0, "C": 0, "G": 0, "P": 0, "S": 0, "Z": 0}
    names = {
        "B": "Butterflies",
        "C": "Cows",
        "G": "Guinea Pigs",
        "P": "Puppies",
        "S": "Squirrels",
        "Z": "Zebras",
    }

    # Per-family counted breakdowns
    fam_total_sends = {k: 0 for k in fam_points}            # counted sends by family
    fam_total_receives = {k: 0 for k in fam_points}         # counted receives by family
    fam_unique_senders = {k: set() for k in fam_points}     # users with ≥1 counted send
    fam_unique_receivers = {k: set() for k in fam_points}   # users with ≥1 counted receive (in that family)
    fam_unique_targets = {k: set() for k in fam_points}     # distinct receiver IDs this family sent to
    fam_target_counts = {k: {} for k in fam_points}         # receiver_id -> times targeted by this family

    # Global per-user trackers (COUNTED-only)
    sent_counts_counted = {}   # user_id -> counted sends so far (enforce cap)
    received_counted = {}      # user_id -> counted receives so far (drives +2 for repeats)

    USER_MENTION_RE = re.compile(r"<@!?(\d+)>")

    def first_user_mention_from_content(text: str):
        if not text:
            return None, 0
        all_ids = USER_MENTION_RE.findall(text)
        if not all_ids:
            return None, 0
        return int(all_ids[0]), len(all_ids)

    # Diagnostics (summary only; no notices)
    multi_mention_count = 0

    # ---- scoring helper ----
    def score_pair(sender_member, receiver_member):
        nonlocal fam_points, fam_total_sends, fam_total_receives
        nonlocal fam_unique_senders, fam_unique_receivers, fam_unique_targets, fam_target_counts
        nonlocal sent_counts_counted, received_counted

        sender_id = sender_member.id
        receiver_id = receiver_member.id

        send_fam = get_family_from_user(sender_member)
        recv_fam = get_family_from_user(receiver_member)
        send_fam = send_fam if send_fam and send_fam != "0" else None
        recv_fam = recv_fam if recv_fam and recv_fam != "0" else None
        if not send_fam or not recv_fam:
            return  # skip silently

        if send_fam == recv_fam:
            return  # same-family: no score, no history mark

        if sent_counts_counted.get(sender_id, 0) >= 2:
            return  # sender over cap

        sender_points = 3
        receiver_points = 2 if received_counted.get(receiver_id, 0) >= 1 else 1

        fam_points[send_fam] += sender_points
        fam_points[recv_fam] += receiver_points

        fam_total_sends[send_fam] += 1
        fam_unique_senders[send_fam].add(sender_id)
        fam_unique_targets[send_fam].add(receiver_id)
        fam_target_counts[send_fam][receiver_id] = fam_target_counts[send_fam].get(receiver_id, 0) + 1

        fam_total_receives[recv_fam] += 1
        fam_unique_receivers[recv_fam].add(receiver_id)

        sent_counts_counted[sender_id] = sent_counts_counted.get(sender_id, 0) + 1
        received_counted[receiver_id] = received_counted.get(receiver_id, 0) + 1

    # ---- 1) Manual pairs FIRST ----
    manual_pairs = [
        (963533131854532638, 516969515486019604),
        (1340578790690132061, 648229959973994506),
        (338436753771724810, 987955038804639744),
        (1156012904869527602, 430454367003475978),
        (863037754164903946, 648229959973994506),
        (1218778118630670376, 843118864379543562),
    ]

    for sid, rid in manual_pairs:
        try:
            sender_member = context.guild.get_member(sid) or await context.guild.fetch_member(sid)
            receiver_member = context.guild.get_member(rid) or await context.guild.fetch_member(rid)
        except Exception:
            continue
        if not sender_member or not receiver_member:
            continue
        score_pair(sender_member, receiver_member)

    # ---- 2) Scrape channel until STOP_AT_ID (exclusive) ----
    async for message in channel.history(limit=None, oldest_first=True):
        if message.id == STOP_AT_ID:
            break  # stop scraping when this message is reached (do not process it or anything older)

        # Ensure Member
        sender_member = message.guild.get_member(message.author.id)
        if sender_member is None:
            try:
                sender_member = await context.guild.fetch_member(message.author.id)
            except Exception:
                continue  # skip silently

        # First user mention in CONTENT only
        receiver_id, mention_count = first_user_mention_from_content(message.content or "")
        if receiver_id is None:
            continue  # no user mention in content

        if mention_count > 1:
            multi_mention_count += 1  # just count; no notice

        # Resolve receiver as Member
        try:
            receiver_member = message.guild.get_member(receiver_id) or await context.guild.fetch_member(receiver_id)
        except Exception:
            continue
        if not receiver_member:
            continue

        score_pair(sender_member, receiver_member)

    # Final output scoreboard
    lines = []
    for code in ["B", "C", "G", "P", "S", "Z"]:
        total_pts = fam_points[code]
        uniq_send = len(fam_unique_senders[code])
        tot_send = fam_total_sends[code]
        uniq_recv = len(fam_unique_receivers[code])
        tot_recv = fam_total_receives[code]
        uniq_targets = len(fam_unique_targets[code])

        lines.append(
            f"{names[code]}: {total_pts} — "
            f"Unique Senders #: {uniq_send} | Total Notes Sent #: {tot_send} | "
            f"Unique Receivers #: {uniq_recv} | Total Notes Received #: {tot_recv} | "
            f"Unique Note Targets #: {uniq_targets}"
        )

    # lines.append(f"(Multiple-mention messages in content: {multi_mention_count})")
    await final_msg.edit(content="\n".join(lines)[:1999])


    # # Then print per-family target lists as mentions with counts
    # for code in ["B", "C", "G", "P", "S", "Z"]:
    #     targets = fam_target_counts[code]
    #     if not targets:
    #         await context.send(f"Targets for {names[code]}: (none)")
    #         continue
    #     # Build " <@id>×n " list
    #     parts = [f"<@{rid}>×{cnt}" for rid, cnt in targets.items()]
    #     text = ", ".join(parts)
    #     # If it's long, Discord will split automatically; we can chunk if needed, but try once first:
    #     header = f"Targets for {names[code]}:"
    #     payload = f"{header} {text}"
    #     if len(payload) <= 1999:
    #         await context.send(payload)
    #     else:
    #         # Chunk conservatively
    #         await context.send(header)
    #         chunk = ""
    #         for seg in parts:
    #             seg2 = (seg + ", ")
    #             if len(chunk) + len(seg2) > 1990:
    #                 await context.send(chunk.rstrip(", "))
    #                 chunk = seg2
    #             else:
    #                 chunk += seg2
    #         if chunk:
    #             await context.send(chunk.rstrip(", "))

@command_handler.Command(access_type=AccessType.PRIVATE)
async def points(activator: Neighbor, context: Context):
    
    from .families import get_family_from_user, has_role
    final_msg = await context.send("Scoring...");
    
    NOTES = True if context.author.id == 355169964027805698 and not len(context.args) > 0 else False;

    fam_points = {
        "B": 0,
        "C": 0,
        "G": 0,
        "P": 0,
        "S": 0,
        "Z": 0,
    }

    names = {
        "B": "Butterflies",
        "C": "Cows",
        "G": "Guinea Pigs",
        "P": "Puppies",
        "S": "Squirrels",
        "Z": "Zebras",
    }

    # Per-family breakdown of points sources
    fam_breakdown = {
        "B": {"sent": 0, "received": 0},
        "C": {"sent": 0, "received": 0},
        "G": {"sent": 0, "received": 0},
        "P": {"sent": 0, "received": 0},
        "S": {"sent": 0, "received": 0},
        "Z": {"sent": 0, "received": 0},
    }

    # Track participation counts (identical logic to original list.count(...) behavior)
    sent_counts = {}      # user_id -> times sent so far
    received_counts = {}  # user_id -> times received so far

    channel = await context.guild.fetch_channel(1403141598300082317)
    council_role = context.guild.get_role(648188387836166168)

    async for message in channel.history(limit=None, oldest_first=True):
        parts = message.content.split(":", 1)
        sender_id = int(parts[0])  # keep identical behavior: let this raise if malformed

        try:
            receiver_id = parse_mention(parts[1])
        except Exception:
            continue

        # Keep the exact same filter
        # if len(parts[1]) < 100:
        # if NOTES:
        #     await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; too short.")
            # continue

        sender = await context.guild.fetch_member(sender_id)
        receiver = await context.guild.fetch_member(receiver_id)

        send_fam = get_family_from_user(sender)
        receive_fam = get_family_from_user(receiver)

        # Preserve exact treatment of '0' as None
        send_fam = send_fam if send_fam != "0" else None
        receive_fam = receive_fam if receive_fam != "0" else None

        if not send_fam or not receive_fam:
            if NOTES:
                await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; no family")
            continue

        # ---- Point allocation (exact logic) ----
        sender_points_earned = 3
        receiver_points_earned = 1

        # Receiver gets +1 if they've received at least once before
        if received_counts.get(receiver_id, 0) >= 1:
            receiver_points_earned += 1

        # Same-family penalty: receiver gets negative of sender's earned points
        if send_fam == receive_fam:
            if NOTES:
                await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; sam family")
            continue
        
        # Cap after two sends (on the third and beyond, sender earns 0)
        if sent_counts.get(sender_id, 0) >= 2:
            if NOTES:
                await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; more than 2 notes from sender")
            continue

        # Update totals
        fam_points[send_fam] += sender_points_earned
        fam_points[receive_fam] += receiver_points_earned
        council_role = context.guild.get_role(648188387836166168)
        if has_role(sender, council_role):
            await context.send(f"<@{sender_id}>")

        # Update breakdown logs
        fam_breakdown[send_fam]["sent"] += sender_points_earned
        fam_breakdown[receive_fam]["received"] += receiver_points_earned

        # Update participation counts AFTER computing this message's points
        sent_counts[sender_id] = sent_counts.get(sender_id, 0) + 1
        received_counts[receiver_id] = received_counts.get(receiver_id, 0) + 1
        
        if NOTES:
            await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nSender gets {sender_points_earned}; Receicer gets {receiver_points_earned}")

    # Format output with breakdown
    lines = []
    for fam_code in ["B", "C", "G", "P", "S", "Z"]:
        total = fam_points[fam_code]
        sent_from_notes = fam_breakdown[fam_code]["sent"]
        received_from_notes = fam_breakdown[fam_code]["received"]
        lines.append(
            f"{names[fam_code]}: {total} "
            # f"({sent_from_notes} from notes sent; {received_from_notes} from notes received)"
        )

    formatted = "\n".join(lines)
    await final_msg.edit(content=formatted[:1999])

            

def build_fixed_triplet_weights_pp(
    total_rounds: int,
    start: float = 1.00,      # 100%
    drop_pp: float = 0.06,    # 6 percentage points per tier
    group_size: int = 3,
    min_weight: float = 0.0   # clamp at 0 once it would go negative
) -> list[float]:
    """
    Build weights (oldest -> newest) where each 3-round tier drops by a fixed
    number of percentage points from the starting weight.

    Example (start=1.00, drop_pp=0.06):
      newest 3 rounds: 1.00
      prev   3 rounds: 0.94
      prev   3 rounds: 0.88
      ...

    We clamp at min_weight to avoid negative weights.
    """
    if total_rounds <= 0:
        return []
    weights = [0.0] * total_rounds
    idx = total_rounds - 1   # fill from most recent backwards
    tier = 0
    while idx >= 0:
        w = max(min_weight, start - tier * drop_pp)
        for _ in range(group_size):
            if idx < 0:
                break
            weights[idx] = w
            idx -= 1
        tier += 1
    return weights


# --- pro_leaderboard: all Pro members ranked ---

@command_handler.Command(access_type=AccessType.PUBLIC)
async def pro_leaderboard(activator: Neighbor, context: Context):
    """
    Pro leaderboard over most recent N rounds (default 18), with:
      - Fixed-triplet recency weights: last 3 @ 100%, previous 3 @ 94%, then 88%, 82%, ...
        (each tier is 6 percentage points lower, clamped at 0)
      - 'Drop worst' rule: for each user, the single worst raw round is set to 0 BEFORE weighting
      - Scoring per round:
          * If mess-ups present: (#participants + 1 + mess_ups)
          * Else if posted: average of their (position indices + 1)
          * Else: (#participants + 1)
    Output is ranked ascending (lower total is better).
    """
    from .families import has_role
    from .races import fetch_images_by_rounds, fetch_mess_ups, get_recent_complete_rounds, strip_emojis

    # --- Args / Defaults ---
    if len(context.args) > 0 and context.args[0].isnumeric():
        n_rounds = int(context.args[0])
    else:
        n_rounds = 18  # default

    FINAL_msg = await context.send("Scoring...")

    # --- Data Fetch ---
    image_channel = await context.guild.fetch_channel(1167152706230681670)
    # Expected ordering: oldest -> newest. If your helper returns newest -> oldest, reverse it here.
    image_messages_by_round = await fetch_images_by_rounds(image_channel, n_rounds)
    rounds = get_recent_complete_rounds(n_rounds)  # aligned to same indexing as image_messages_by_round
    mess_up_map = await fetch_mess_ups(context, rounds)
    role = context.guild.get_role(1024052938752151552)

    # --- Initialize Pro members ---
    pro_member_ids: set[int] = set()
    async for member in context.guild.fetch_members(limit=None):
        if has_role(member, role):
            pro_member_ids.add(member.id)

    # --- Build fixed-triplet weights with -6pp per tier ---
    total_rounds = len(image_messages_by_round)
    weights = build_fixed_triplet_weights_pp(
        total_rounds,
        start=1.00,
        drop_pp=1/3,
        group_size=6,
        min_weight=0.0
    )

    # --- Compute per-user, per-round RAW scores (unweighted) ---
    # user_round_scores[user_id] -> list[float] of length total_rounds
    user_round_scores: dict[int, list[float]] = {uid: [] for uid in pro_member_ids}

    for i, round_messages in enumerate(image_messages_by_round):
        # Build author -> list of positions (+1) for this round
        author_positions: dict[int, list[int]] = {}
        for idx, msg in enumerate(round_messages):
            author_positions.setdefault(msg.author.id, []).append(idx + 1)

        total_participants = len(round_messages)
        base_penalty = total_participants + 1

        # Per-round mess-ups (assumed dict keyed by round index -> {member_id: mess_up_count})
        round_mess_ups = mess_up_map.get(i, {}) if isinstance(mess_up_map, dict) else {}

        for member_id in pro_member_ids:
            if member_id in round_mess_ups:
                num_mess_ups = round_mess_ups[member_id]
                score = base_penalty + num_mess_ups
            elif member_id in author_positions:
                positions = author_positions[member_id]
                score = sum(positions) / len(positions)
            else:
                score = base_penalty
            user_round_scores[member_id].append(score)

    # --- Apply 'drop worst' per user (set worst RAW to 0 BEFORE weighting) ---
    dropped_index_by_user: dict[int, int | None] = {}
    for member_id, scores in user_round_scores.items():
        if scores:
            worst_idx = max(range(len(scores)), key=lambda k: scores[k])
            dropped_index_by_user[member_id] = worst_idx
            scores[worst_idx] = 0.0
        else:
            dropped_index_by_user[member_id] = None

    # --- Accumulate weighted totals (ceil per round) ---
    totals: dict[int, float] = {uid: 0.0 for uid in pro_member_ids}
    for i in range(total_rounds):
        w = weights[i] if i < len(weights) else 1.0
        for member_id in pro_member_ids:
            if i < len(user_round_scores[member_id]):
                totals[member_id] += math.ceil(user_round_scores[member_id][i] * w)

    # --- Sort and format leaderboard ---
    sorted_members = sorted(totals.items(), key=lambda x: x[1])  # ascending total
    leaderboard_lines = []
    medals = ["🥇", "🥈", "🥉"]

    for rank, (member_id, score) in enumerate(sorted_members, start=1):
        member = context.guild.get_member(member_id)
        raw_name = member.display_name if member else f"User {member_id}"
        display_name = strip_emojis(raw_name)
        rank_label = medals[rank - 1] if rank <= 3 else f"{rank}."
        leaderboard_lines.append(f"{rank_label} {display_name}: {round(score)}")

    leaderboard_output = "\n".join(leaderboard_lines)
    await FINAL_msg.edit(content=leaderboard_output)


def ordinal(n: int) -> str:
    """Returns ordinal string for a given integer: 1 → '1st', 2 → '2nd', etc."""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


# ----- pro_score: single member, stylized by 3-round batches -----

@command_handler.Command(access_type=AccessType.PUBLIC)
async def pro_score(activator: Neighbor, context: Context):
    """
    Show one member's recency-weighted score over the most recent 18 rounds.

    Changes:
      - Fixed triplet weights at -6 percentage points per tier:
          newest 3: 100% (1.00), then 94% (0.94), then 88% (0.88), ...
      - 'Drop worst raw round' before weighting (set to 0 only for scoring).
      - Output grouped in triplets. For each group, print:
          • the 3 round lines,
          • then a batch footer:
               Batch raw = <sum raw in group after drop>
               Weight    = <weight for that group>
               Batch weighted = <sum ceil(raw_i * weight) across the 3 rounds>
      - End with:  Final score: a + b + c + ... = total

    Raw per-round scoring (before weighting):
      - If user has mess-ups: (#participants + 1 + mess_ups)
      - Else if user posted: average of their (position indices + 1)
      - Else: (#participants + 1)
    """
    from .races import fetch_images_by_rounds, fetch_mess_ups, get_recent_complete_rounds, strip_emojis

    # --- Resolve target member (mention, id, or fuzzy by display name / username) ---
    if len(context.args) > 0:
        try:
            target = await context.guild.fetch_member(int(parse_mention((context.args[0]))))
        except:
            candidates = [x.nick for x in context.guild.members if x.nick is not None]
            candidates.extend([x.name for x in context.guild.members if (x.nick is None) or (x.nick != x.name)])
            name, confidence = best_string_match(context.args[0], [str(x) for x in candidates])
            target = discord.utils.get(context.guild.members, display_name=name)
            target = target if target is not None else discord.utils.get(context.guild.members, name=name)
    else:
        target = None

    target_member = context.author if target is None else target
    member_id = target_member.id

    FINAL_msg = await context.send("Scoring...")

    # --- Config ---
    N_ROUNDS    = 18
    GROUP_SIZE  = 6
    START_W     = 1.00   # 100%
    DROP_PP     = 1/3   # 6 percentage points per tier
    MIN_WEIGHT  = 0.0

    # --- Fetch rounds & mess-ups ---
    channel = await context.guild.fetch_channel(1167152706230681670)
    rounds = await fetch_images_by_rounds(channel, n_rounds=N_ROUNDS)  # expected: oldest -> newest
    round_windows = get_recent_complete_rounds(N_ROUNDS)               # aligned to same indexing
    mess_up_map = await fetch_mess_ups(context, round_windows)

    # --- Build weights ---
    total_rounds = len(rounds)
    weights = build_fixed_triplet_weights_pp(
        total_rounds,
        start=START_W,
        drop_pp=DROP_PP,
        group_size=GROUP_SIZE,
        min_weight=MIN_WEIGHT
    )

    # --- Compute RAW per-round scores for the target (unweighted) ---
    raw_scores: list[float] = []
    round_labels: list[str] = []

    for i, round_messages in enumerate(rounds):
        # Label from message date if present, else from window start
        if round_messages:
            # If your created_at is timezone-aware, keep it; otherwise handle LOCAL_TZ
            round_date = getattr(round_messages[0].created_at, "date", None)
            if round_date is not None:
                round_start = round_messages[0].created_at.date()
            else:
                # Fallback if needed
                round_start = round_windows[i][0].date()
        else:
            round_start = round_windows[i][0].date()
        round_labels.append(f"Derby of {round_start.strftime('%B')} {round_start.day}")

        # Build author -> list of positions (+1)
        author_positions: dict[int, list[int]] = {}
        for idx, msg in enumerate(round_messages):
            author_positions.setdefault(msg.author.id, []).append(idx + 1)

        total_participants = len(round_messages)
        base_penalty = total_participants + 1

        # Mess-up override
        round_mess_ups = mess_up_map.get(i, {}) if isinstance(mess_up_map, dict) else {}
        if member_id in round_mess_ups:
            mess_ups = round_mess_ups[member_id]
            raw_score = base_penalty + mess_ups
        elif member_id in author_positions:
            positions = author_positions[member_id]
            raw_score = sum(positions) / len(positions)
        else:
            raw_score = base_penalty

        raw_scores.append(raw_score)

    # --- Drop worst raw round (set to 0 for scoring, keep original for display) ---
    raw_scores_orig = raw_scores[:]
    dropped_index = None
    if raw_scores:
        dropped_index = max(range(len(raw_scores)), key=lambda k: raw_scores[k])
        raw_scores[dropped_index] = 0.0

    # --- Build grouped breakdown (triplets) and compute totals ---
    header_name = strip_emojis(target_member.display_name if target_member else f"User {member_id}")
    lines: list[str] = []
    lines.append(f"**Pro Score for {header_name}**")
    lines.append(f"_Last {total_rounds} derbies · Worst score dropped_")
    lines.append("")

    batch_weighted_totals: list[int] = []
    overall_total = 0

    # Determine number of triplets (ceil)
    num_batches = (total_rounds + GROUP_SIZE - 1) // GROUP_SIZE

    # We present batches from **newest to oldest** to match intuition:
    #   Batch 1 = newest 3, Batch 2 = previous 3, etc.
    # Our arrays are oldest->newest, so compute indices accordingly.
    for batch_idx_from_newest in range(num_batches):
        # Compute inclusive range [start_i, end_i] for this batch in oldest->newest indexing
        # newest batch covers the last 3 indices
        end_i = total_rounds - 1 - batch_idx_from_newest * GROUP_SIZE
        start_i = max(0, end_i - (GROUP_SIZE - 1))
        batch_indices = list(range(start_i, end_i + 1))

        # Weight for this batch: all 3 share the same value in our scheme; just read weight at end_i
        batch_weight = weights[end_i] if end_i < len(weights) else 1.0

        # Header
        human_batch_num = batch_idx_from_newest + 1
        weight_pct = f"{round(batch_weight * 100)}%"
        lines.append(f"__Batch {human_batch_num} (most recent {GROUP_SIZE}): weight {weight_pct}__")

        # Per-round lines inside the batch
        batch_raw_sum = 0.0
        batch_weighted_sum = 0
        for i in batch_indices:
            label = round_labels[i] if i < len(round_labels) else f"Round {i+1}"

            # Determine display type and points
            # We recompute author_positions for display tag
            author_positions = {}
            for idx, msg in enumerate(rounds[i]):
                author_positions.setdefault(msg.author.id, []).append(idx + 1)

            round_mess_ups = mess_up_map.get(i, {}) if isinstance(mess_up_map, dict) else {}

            # Display classification
            if dropped_index is not None and i == dropped_index:
                classification = "Dropped worst round"
            elif member_id in round_mess_ups:
                classification = f"Mess up ({round_mess_ups[member_id]})"
            elif member_id in author_positions:
                positions = author_positions[member_id]
                avg_pos = sum(positions) / len(positions)
                classification = f"{ordinal(round(avg_pos))} poster"
            else:
                classification = "No post"

            # Raw (for scoring) uses dropped version; for display we still show classification above
            raw_for_scoring = raw_scores[i]
            cur_weighted = math.ceil(raw_for_scoring * batch_weight)
            batch_raw_sum += raw_for_scoring
            batch_weighted_sum += cur_weighted

            # Round line
            lines.append(f"• {label}: {classification} — {cur_weighted} points")

        # Batch footer
        # Keep raw shown with up to 2 decimals (your preference: you can also round int if always int-like)
        batch_raw_disp = f"{batch_raw_sum:.2f}".rstrip('0').rstrip('.')  # trim trailing zeros
        lines.append(f"_Batch {human_batch_num} summary:_ raw **{batch_raw_disp}** · weight **{weight_pct}** · weighted **{batch_weighted_sum}**")
        lines.append("")

        # Accumulate
        batch_weighted_totals.append(batch_weighted_sum)
        overall_total += batch_weighted_sum

    # Final line: "Final score: a + b + c + ... = total"
    parts = " + ".join(str(x) for x in batch_weighted_totals)
    lines.append(f"**Final score:** {parts} = **{overall_total}**")

    # Dropped round note
    if dropped_index is not None and 0 <= dropped_index < len(round_labels):
        lines.append(f"_Dropped worst raw round:_ **{round_labels[dropped_index]}** (from {raw_scores_orig[dropped_index]} to 0)")

    await FINAL_msg.edit(content="\n".join(lines))


@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def derbylottery(activator: Neighbor, context: Context):
    from .families import has_role
    guild = context.guild;
    lottery_chat = await guild.fetch_channel(1117840455648948255);
    
    pro_members = [];
    pro_role = guild.get_role(1024052938752151552)
    main_members = [];
    main_role = guild.get_role(656112994392080384)
    junior_members = [];
    junior_role = guild.get_role(689928709683150909)
    junior2_members = [];
    junior2_role = guild.get_role(1334660124639236267)
    garden_members = [];
    garden_role = guild.get_role(1173325157767589988)
    
    async for member in guild.fetch_members():
        if has_role(member, pro_role):
            pro_members.append(member);
        if has_role(member, main_role):
            main_members.append(member);
        if has_role(member, junior_role):
            junior_members.append(member);
        if has_role(member, junior2_role):
            junior2_members.append(member);
        if has_role(member, garden_role):
            garden_members.append(member);
    
    
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=int(context.args[0]))
    
    async for message in lottery_chat.history(limit=None, oldest_first=False):
        if message.created_at < cutoff:
            break
        
        if not "lottery" in message.content and "dice" in message.content:
            continue;
        
        
        pro_members = [pro_member for pro_member in pro_members if not str(pro_member.id) in message.content];
        main_members = [main_member for main_member in main_members if not str(main_member.id) in message.content];
        junior_members = [junior_member for junior_member in junior_members if not str(junior_member.id) in message.content];
        junior2_members = [junior2_member for junior2_member in junior2_members if not str(junior2_member.id) in message.content];
        garden_members = [garden_member for garden_member in garden_members if not str(garden_member.id) in message.content];
        
    await context.send(''.join(f"<@{pro_member.id}>\n" for pro_member in pro_members))
    await context.send(''.join(f"<@{main_member.id}>\n" for main_member in main_members))
    await context.send(''.join(f"<@{junior_member.id}>\n" for junior_member in junior_members))
    await context.send(''.join(f"<@{junior2_member.id}>\n" for junior2_member in junior2_members))
    await context.send(''.join(f"<@{garden_member.id}>\n" for garden_member in garden_members))

    # await birthdays(client, guild, est_time)
    
# Derby knockout

task_sets = [
    [
        "Catch fish with lures",
        "Collect wool",
        "Complete truck deliveries",
        "Produce & collect mixed smoothie",
        "Serve town visitors in Beach Café",
        "Harvest cucumber fields",
    ],
    [
        "Harvest chili pepper fields",
        "Complete and send off boats",
        "Feed animals",
        "Produce & collect yogurt smoothie",
        "Harvest indigo fields",
        "Harvest wheat fields",
    ],
    [
        "Harvest wheat fields",
        "Catch fish with lures",
        "Basket: Apple juice, carrot cake, feta pie",
        "Excavate ores from the mine",
        "Fully serve visitors in your town",
        "Produce & collect roasted tomatoes",
    ],
    [
        "Produce & collect raspberry muffin",
        "Produce & collect mushroom salad",
        "Complete truck deliveries",
        "Fully serve visitors in your town",
        "Produce & collect bacon and eggs",
        "Produce & collect pumpkin pie",
    ],
    [
        "Serve town visitors in Gift Shop",
        "Harvest cotton fields",
        "Catch fish with lures",
        "Collect milk",
        "Collect bacon",
        "Basket: Strongmen, bacon and eggs, ores",
    ],
    [
        "Catch fish with lures",
        "Complete and send off boats",
        "Harvest grape fields",
        "Help other farmers",
        "Feed animals",
        "Produce & collect fancy cake",
    ],
    [
        "Fully serve visitors in your town",
        "Catch fish with lures",
        "Produce & collect plum smoothie",
        "Collect goat milk",
        "Basket: Ice cream, red berry cake, cotton shirts",
        "Feed animals",
    ],
    [
        "Collect milk",
        "Produce & collect chickpea stew",
        "Fully serve visitors in your town",
        "Basket: Olive oil, goat cheese, strawberry candles",
        "Feed animals",
        "Produce & collect chili poppers",
    ],
    [
        "Produce & collect tomato juice",
        "Fully serve mechanic",
        "Produce & collect blue woolly hat",
        "Complete truck deliveries",
        "Excavate ores from the mine",
        "Basket: Apple juice, carrot cake, feta pie",
    ],
    [
        "Catch fish with lures",
        "Fully serve strongman",
        "Collect bacon",
        "Basket: Wool, raspberry candles, pumpkins",
        "Complete and send off boats",
        "Collect wool",
    ],
    [
        "Serve town visitors in Beach Café",
        "Fully serve visitors in your town",
        "Help other farmers",
        "Harvest sunflower fields",
        "Produce & collect blue woolly hat",
        "Basket: Milk, eggs, bacon",
    ],
    [
        "Complete truck deliveries",
        "Feed animals",
        "Complete and send off boats",
        "Fully serve cowboy",
        "Basket: Wool, raspberry candles, pumpkins",
        "Fully serve visitors in your town",
    ],
]


async def announce_task_bounty(slot: int, bounty_channel):
    from datetime import datetime, date, timedelta
    from zoneinfo import ZoneInfo

    DERBY_START = date(2026, 10, 6)
    DERBY_TIMEZONE = ZoneInfo("America/New_York")

    # slot 0 = morning; slot 1 = evening
    if slot not in (0, 1):
        raise ValueError("slot must be 0 or 1")

    now = datetime.now(DERBY_TIMEZONE)
    day_index = (now.date() - DERBY_START).days
    set_index = day_index * 2 + slot

    # Don't announce before the start or after the final set.
    if day_index < 0 or set_index >= len(task_sets):
        return

    tasks = task_sets[set_index]
    day_number = day_index + 1
    part_number = slot + 1
    expires_at = int((now + timedelta(hours=24)).timestamp())

    message = f"**Day {day_number} Bounties Pt {part_number}**\n\n<@&1181330910747054211>\n"

    if slot == 1:
        message += (
            f"If you have already completed a day {day_number} bounty, "
            "you can skip these.\n\n"
        )

    message += "\n".join(f"• {task}" for task in tasks)
    
    await bounty_channel.send(message)

    message = (
        f"\n\nThese bounties expire in 24 hours (<t:{expires_at}:R>)"
        "\n\n**Reminders:**"
        "\n• Post a screenshot after you have started "
        "(don't need to finish) any one of these derby tasks."
        f"\n• You can only get credit for any 1 of all of the day "
        f"{day_number} bounties in either part."
        "\n• The same task can't count on two different days "
        "unless you actually take that task twice."
        "\n• If you took one of these tasks before the bounty was announced, you can still submit it."
    )

    await bounty_channel.send(message)



@command_handler.Scheduled(time="8:00")
async def announce_task_bounty_part1(client):
    guild = client.get_guild(FF.guild)
    channel = await guild.fetch_channel(1203772906497380472)
    await announce_task_bounty(slot=0,bounty_channel=channel)



@command_handler.Scheduled(time="20:00")
async def announce_task_bounty_part2(client):
    guild = client.get_guild(FF.guild)
    channel = await guild.fetch_channel(1203772906497380472)
    await announce_task_bounty(slot=1,bounty_channel=channel)


@command_handler.Command(AccessType.PUBLIC, desc = "Calculates the BEM penalty for a neighbor of a certain level and number of missed tasks. For example, `$penalty 50 5` calculates the BEMs required of a level 50 player who misses 5 tasks.")
async def penalty(activator: Neighbor, context: Context):
    from .economy import real_round
    try:
        level = int(context.args[0]);
        tasks_missed = int(context.args[1]);
    except:
        raise CommandArgsError("`penalty` expects two arguments: player level and # of tasks missed");

    penalty_per_task = int(level / 10);

    total_penalty = penalty_per_task * tasks_missed;
    penalty = min(total_penalty, int(level / 2));
    power_derby_penalty = min(real_round(total_penalty / 2), int(level / 2))

    await context.send(f"A level {level} player who misses {tasks_missed} tasks owes **{penalty} BEMs** in normal derby!!", reply = True)
    await context.send(f"However, this player would only owe *{power_derby_penalty}* during a power derby.")
    await context.send(f"||During code gold, they owe {penalty * 2} BEMs during non-power derbies, and {power_derby_penalty * 2} during power derby. Please check with a council member or the announcements channel to see if this week is a code gold week.||");

