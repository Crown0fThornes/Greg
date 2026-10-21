"""Races commands and their supporting helpers."""

from .common import *

_ab_race_lock = asyncio.Lock()

_AB_RACE_CHANNEL_ID = 1203772906497380472

_AB_RACE_START_MESSAGE_ID = 1562014317749075980

_AB_RACE_TITLE = "# A&B Race Update"



def _ab_race_has_image(message):
    image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".avif")
    return any(
        (attachment.content_type or "").startswith("image/")
        or (not attachment.content_type and attachment.filename.lower().endswith(image_extensions))
        for attachment in message.attachments
    ) or any(
        embed.type == "image" or (embed.image and embed.image.url)
        for embed in message.embeds
    )



def _ab_race_summary(latest_submissions, family_names):
    """All family players place; only each family's first ten score."""
    placements = {name: [] for name in family_names}
    for place, (_, family_name) in enumerate(sorted(latest_submissions.values()), start=1):
        placements[family_name].append(place)

    total_players = len(latest_submissions)
    lines = [_AB_RACE_TITLE]
    for family_name, places in placements.items():
        score = sum(places[:10])
        needed = max(0, 10 - len(places))
        # Assume this family's missing scorers take all the next available places.
        projected = score + sum(range(total_players + 1, total_players + needed + 1))
        lines.extend([
            "",
            f"{family_name}:",
            f"> Current score: {score}",
            ">",
            f"> {needed} more submission{'s' if needed != 1 else ''} needed to lock in score",
            ">",
            f"> Projected minimum score: {projected}",
        ])
    return "\n".join(lines)



def _ab_race_overtakes(previous_summary, current_summary):
    """Compare projected scores, which include each family's missing scorers."""
    def scores(summary):
        return {
            name: int(score)
            for name, score in re.findall(
                r"^([^\n:]+):\n> Current score: \d+\n>\n"
                r"> \d+ more submissions? needed to lock in score\n>\n"
                r"> Projected minimum score: (\d+)$",
                summary, re.MULTILINE,
            )
        }

    previous = scores(previous_summary)
    current = scores(current_summary)
    return [
        f"**{family} has overtaken {other}!**"
        for family in current
        for other in current
        if family in previous and other in previous
        and previous[family] > previous[other]
        and current[family] < current[other]
    ]



@command_handler.Uncontested(type="MESSAGE", desc="Updates A&B race scores after image submissions")
async def update_ab_race_scoring(context: Context):
    from .families import get_family_from_user
    if (context.channel.id != _AB_RACE_CHANNEL_ID
            or context.author.bot
            or context.message.id <= _AB_RACE_START_MESSAGE_ID
            or not _ab_race_has_image(context.message)):
        return

    async with _ab_race_lock:
        with open("lookups/families.json", encoding="utf-8") as family_file:
            families = json.load(family_file)
        family_names = [family["name"] for family in families]

        latest_submissions = {}
        previous_summaries = []
        bot_id = context.guild.me.id
        # No limit: reconstruct both standings and our previous update after restarts.
        async for message in context.channel.history(
                after=discord.Object(id=_AB_RACE_START_MESSAGE_ID),
                oldest_first=True, limit=None):
            if message.author.id == bot_id:
                if message.content.split("\n", 1)[0] == _AB_RACE_TITLE:
                    previous_summaries.append(message)
                continue
            if message.author.bot or not _ab_race_has_image(message):
                continue
            member = message.author
            if not isinstance(member, discord.Member):
                member = context.guild.get_member(member.id)
                if member is None:
                    try:
                        member = await context.guild.fetch_member(message.author.id)
                    except discord.NotFound:
                        continue
            family = get_family_from_user(member)
            if family is None or family["name"] not in family_names:
                continue
            # Snowflake order is submission time, including a deterministic tie break.
            latest_submissions[member.id] = (message.id, family["name"])

        summary = _ab_race_summary(latest_submissions, family_names)
        overtakes = _ab_race_overtakes(previous_summaries[-1].content, summary) if previous_summaries else []
        ping_roles = []
        if overtakes:
            ping_roles = [discord.Object(id=family["role_id"]) for family in families
                          if family["name"] in {"Penguin", "Hippo", "Fox"}]
            notes = "\n".join(overtakes)
            pings = " ".join(f"<@&{role.id}>" for role in ping_roles)
            summary = summary.replace(_AB_RACE_TITLE, f"{_AB_RACE_TITLE}\n\n{notes}\n{pings}", 1)
        # Send first so a failed send leaves the existing standings visible.
        await context.channel.send(summary, allowed_mentions=discord.AllowedMentions(
            everyone=False, users=False, roles=ping_roles, replied_user=False))
        for previous_summary in previous_summaries:
            try:
                await previous_summary.delete()
            except discord.NotFound:
                pass


# CONFIGURATION
LOCAL_UTC_OFFSET = -4  # EDT

LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=LOCAL_UTC_OFFSET))

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')

DEBUG = True  # Enable debug print statements


def strip_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002500-\U00002BEF"
        "\U0001F191-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()


def get_recent_complete_rounds(n_rounds=12):
    now = datetime.datetime.now(LOCAL_TZ)
    weekday = now.weekday()  # Monday = 0
    days_since_monday = (weekday - 0) % 7
    last_monday = now - datetime.timedelta(days=days_since_monday)
    last_monday = last_monday.replace(hour=23, minute=59, second=59, microsecond=999999)

    rounds = []
    for i in range(n_rounds):
        round_end = last_monday - datetime.timedelta(weeks=i)
        round_start = round_end - datetime.timedelta(days=6)
        round_start = round_start.replace(hour=0, minute=0, second=0, microsecond=0)
        rounds.append((round_start, round_end))

    rounds = rounds[::-1]

    if DEBUG:
        print("📆 Generated Round Windows:")
        for idx, (start, end) in enumerate(rounds):
            print(f"  Round {idx+1}: {start} → {end}")

    return rounds


async def fetch_images_by_rounds(channel, n_rounds=12):
    rounds = get_recent_complete_rounds(n_rounds)
    results = [[] for _ in rounds]

    oldest_time = rounds[0][0]
    newest_time = rounds[-1][1] + datetime.timedelta(seconds=1)

    if DEBUG:
        print(f"⏱ Fetching messages between {oldest_time} and {newest_time}")

    start_timer = time.time()
    async for message in channel.history(limit=None, oldest_first=True, before=newest_time):
        msg_time = message.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
        msg_time = msg_time.astimezone(LOCAL_TZ)

        if msg_time < oldest_time:
            continue

        if any(att.filename.lower().endswith(IMAGE_EXTS) for att in message.attachments):
            for i, (start, end) in enumerate(rounds):
                if start <= msg_time <= end:
                    results[i].append(message)
                    break

    if DEBUG:
        print(f"✅ Finished fetching in {time.time() - start_timer:.2f} seconds")

    return results


async def fetch_mess_ups(context, rounds):
    channel = await context.guild.fetch_channel(1403092988925575249)
    mess_up_map = {i: {} for i in range(len(rounds))}

    async for msg in channel.history(limit=None, oldest_first=True):
        parts = msg.content.strip().split()
        if len(parts) != 2:
            if DEBUG:
                print(f"❌ Invalid format: {msg.content}")
            continue

        try:
            member_id = int(parts[0])
            count = int(parts[1])
        except ValueError:
            if DEBUG:
                print(f"❌ Non-integer mess-up entry: {msg.content}")
            continue

        msg_time = msg.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
        msg_time = msg_time.astimezone(LOCAL_TZ)

        assigned = False
        if msg_time.weekday() == 0:  # Monday → current round
            for i, (start, end) in enumerate(rounds):
                if start <= msg_time <= end:
                    mess_up_map[i][member_id] = mess_up_map[i].get(member_id, 0) + count
                    assigned = True
                    break
        else:
            # Go to previous full round
            days_since_monday = (msg_time.weekday() - 0) % 7
            last_monday = msg_time - datetime.timedelta(days=days_since_monday)
            last_monday = last_monday.replace(hour=23, minute=59, second=59, microsecond=999999)

            for i, (start, end) in enumerate(rounds):
                if end == last_monday:
                    mess_up_map[i][member_id] = mess_up_map[i].get(member_id, 0) + count
                    assigned = True
                    break

        if DEBUG and not assigned:
            print(f"❓ Could not assign mess-up from {msg_time}: {msg.content}")

    if DEBUG:
        print("📉 Mess-Up Mapping:")
        for i, m in mess_up_map.items():
            if m:
                print(f"  Round {i+1}: {m}")
    return mess_up_map


@command_handler.Command(access_type=AccessType.PRIVATE)
async def ab_race(activator:Neighbor, context: Context):
    
    from .families import get_family_from_user
    final_msg = await context.send("Scoring...", reply=True);
    
    channel = await context.guild.fetch_channel(1203772906497380472)
    message = await channel.fetch_message(1422340225035800626);
    
    position = 1;
    butterflies = [];
    cows = [];
    
    async for msg in channel.history(after=message,oldest_first=True, limit=None):
        if len(butterflies)==10 and len(cows)==10:
            break
        
        has_image = (
            any(att.content_type and att.content_type.startswith("image/") for att in msg.attachments) or
            any(embed.type == "image" or (embed.image and embed.image.url) for embed in msg.embeds)
        )
        
        if not has_image:
            continue;
        
        family = get_family_from_user(msg.author)
        
        if family == "B":
            if len(butterflies) < 10:
                butterflies.append(position);
            position+=1;
        if family == "C":
            if len(cows) < 10:
                cows.append(position);
            position+=1;
            
    butterflies_before_padding = sum(butterflies) + 7;
    cows_before_padding = sum(cows) + 8;
            
    while len(butterflies) < 10:
        butterflies.append(position)
        
    while len(cows) < 10:
        cows.append(position);
        
    butterflies_score = sum(butterflies) + 7
    cows_score = sum(cows) + 8
    
    result = "# A&B Race Scores!\n**Remember: Less Points = Better**\n\n"
    result += f"**Butterflies:** {str(butterflies_score)}pts\n";
    if butterflies_before_padding != butterflies_score:
        result += f"-# Only {butterflies_before_padding}pts are locked in. Final score will be *at least* {butterflies_score}pts\n";
    result += f"\n**Cows:** {str(cows_score)}pts\n";
    if cows_before_padding != cows_score:
        result += f"-# Only {cows_before_padding}pts are locked in. Final score will be *at least* {cows_score}pts";
        
    if butterflies_score == butterflies_before_padding and butterflies_score < cows_score:
        result += "\n# Projected Winners: Butterflies!!"
    elif cows_score == cows_before_padding and cows_score < butterflies_score:
        result += "\n# Projected Winners: Cows!!"
    else:
        result += "\n# Butterflies in the lead!" if butterflies_score < cows_score else "\n# Cows in the lead!" if cows_score < butterflies_score else "Tied so far!"
        
    result += "\n**Results are not official until submissions reviewed for legitimacy and points reviewed for accuracy. Greg can only know so much.**"
        
    await final_msg.edit(content=result)

