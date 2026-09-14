from math import floor
from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
from custom_types import Neighbor, Item
from responses import ResponsePackage, ResponseRequest
import commands.commands as commands
import time
import random
import sqlite3
import json
import password_manager
import math
import discord
import difflib
from pathlib import Path
import datetime
LOCAL_UTC_OFFSET = -4  # EDT
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=LOCAL_UTC_OFFSET))

# Exclusive end: September 2, 2026 at 00:00 EDT.
FAIR_CUTOFF_UTC = datetime.datetime(2026, 9, 2, 4, tzinfo=datetime.timezone.utc)


def fair_message_time(message):
    timestamp = message.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
    return timestamp.astimezone(datetime.timezone.utc)


def fair_bem_prize(blue_tickets, golden_tickets):
    if golden_tickets >= 3:
        return 267
    if blue_tickets >= 60:
        return 178
    if blue_tickets >= 40:
        return 89
    return max(0, blue_tickets)


BASE_DIR = Path(__file__).resolve().parent.parent

def is_task_complete(conn, member_id, task_num):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM fair_task_completions
        WHERE member_id = ?
          AND task_num = ?
        LIMIT 1
        """,
        (member_id, task_num)
    )

    return cursor.fetchone() is not None

def insert_submission(conn, member_id, task_num, channel_id, message_id):
    """
    Record a Discord message as evidence for a member's task submission.

    Returns True if a new row was inserted.
    Returns False if that exact submission already existed.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO fair_task_submissions (
            member_id,
            task_num,
            channel_id,
            message_id
        )
        VALUES (?, ?, ?, ?)
        """,
        (member_id, task_num, channel_id, message_id)
    )

    return cursor.rowcount > 0


def insert_task_complete(conn, member_id, task_num):
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO fair_task_completions (
            member_id,
            task_num
        )
        VALUES (?, ?)
        """,
        (member_id, task_num)
    )

    return cursor.rowcount > 0

def remove_task_complete(conn, member_id, task_num):
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM fair_task_completions
        WHERE member_id = ?
          AND task_num = ?
        """,
        (member_id, task_num)
    )

    return cursor.rowcount > 0

def is_submission_in_table(conn, channel_id, message_id):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM fair_task_submissions
        WHERE channel_id = ?
          AND message_id = ?
        LIMIT 1
        """,
        (channel_id, message_id,)
    )

    return cursor.fetchone() is not None

def get_task_submissions(conn, member_id, task_num):
    """
    Returns all submissions for a member and task as dictionaries.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT channel_id, message_id
        FROM fair_task_submissions
        WHERE member_id = ?
          AND task_num = ?
        """,
        (member_id, task_num)
    )

    return [
        {
            "channel_id": channel_id,
            "message_id": message_id
        }
        for channel_id, message_id in cursor.fetchall()
    ]

def get_ticket_counts(conn, member_ids, task_info):
    if not member_ids:
        return {
            "total": 0,
            "members": {}
        }
    
    placeholders = ",".join("?" for _ in member_ids)
    
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT member_id, task_num
        FROM fair_task_completions
        WHERE member_id IN ({placeholders})
        """,
        member_ids
    )
    
    completions = {
        member_id: set()
        for member_id in member_ids
    }
    
    for member_id, task_num in cursor.fetchall():
        completions[member_id].add(task_num)
    
    member_totals = {}
    
    for member_id in member_ids:
        tickets_accumulated = 0
        
        for task_num, task in enumerate(task_info, start=1):
            set_num = task["set_number"]
            if set_num == "Bonus":
                required_tickets = 60
            else:
                required_tickets = (set_num - 1) * 10
            
            if tickets_accumulated < required_tickets:
                continue
            
            if task_num in completions[member_id]:
                tickets_accumulated += task["tickets"]
        
        member_totals[member_id] = tickets_accumulated
    
    return {
        "total": sum(member_totals.values()),
        "members": member_totals
    }
    
@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def ticket_recount(activator: Neighbor, context: Context, month=None, day=None):
    task_db_path = BASE_DIR / "data" / "fair_task_submissions.db"
    
    create_fair_task_tables(task_db_path)
    
    with sqlite3.connect(task_db_path) as conn:
        guild = context.guild
        
        task_info_path = BASE_DIR / "lookups" / "fair_tasks.json"
        with task_info_path.open("r", encoding="utf-8") as f:
            task_info = json.load(f)
            
        target_message = await context.send("Indexing")
            
        # Index all submissions
        for i, task in enumerate(task_info, start=1):
            await target_message.edit(content=f"Indexing {task['name']}")
            
            num_pics = task["pic_count"]
            num_words = task["word_count"]
            num_messages = task["message_count"]
            
            needs_pics = num_pics > 0
            needs_messages = num_words > 0 or num_messages > 0
            
            start_month = month or task["start_month"]
            start_day = day or task["start_day"]
            start_time = datetime.datetime(2026, start_month, start_day, tzinfo=LOCAL_TZ)
                    
            channels_to_search = task["submission_channel"]
            if not isinstance(channels_to_search, list):
                channels_to_search = [channels_to_search]
            
            await add_submissions_after_date(conn, guild, channels_to_search, i, needs_pics, needs_messages, start_time)
                
        # Validate task completion
        for i, task in enumerate(task_info, start=1):
            await target_message.edit(content=f"Counting {task['name']}")
            
            num_pics = task["pic_count"]
            num_words = task["word_count"]
            num_messages = task["message_count"]
            
            member_ids = get_members_with_task_submissions(conn, i)
                    
            for member_id in member_ids:
                await add_task_completions(
                    conn,
                    guild,
                    i,
                    member_id,
                    num_pics,
                    num_words,
                    num_messages,
                    task["start_month"],
                    task["start_day"]
                )
        
        await target_message.edit(content="Done!")
        
def get_members_with_task_submissions(conn, task_num):
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT member_id
        FROM fair_task_submissions
        WHERE task_num = ?
        """,
        (task_num,)
    )

    return [row[0] for row in cursor.fetchall()]
        
async def add_task_completions(conn, guild, task_num, member_id, num_pics, num_words, num_messages, start_month, start_day):
    
    async def has_ghost_reaction_from_role(message, role_id):
        for reaction in message.reactions:
            if str(reaction.emoji) != "👻":
                continue

            async for user in reaction.users():
                if isinstance(user, discord.Member):
                    if any(role.id == role_id for role in user.roles):
                        return True
        return False
    
    # does member exist?
    try:
        member = await guild.fetch_member(member_id)
    except:
        return
    
    # get submission links from db
    submissions = get_task_submissions(conn, member_id, task_num)
    
    pic_count = 0
    word_count = 0
    message_count = 0
    
    for submission in submissions:        
        # try to find message (may have been deleted since indexing)
        try:
            channel = await guild.fetch_channel(submission["channel_id"])
            message = await channel.fetch_message(submission["message_id"])
        except:
            continue
        
        # Stored submissions must obey the deadline too.
        if fair_message_time(message) >= FAIR_CUTOFF_UTC:
            continue

        # check if message has been invalidated with 👻
        if await has_ghost_reaction_from_role(message, 648188387836166168):
            continue
        
        message_count += 1
        word_count += len(message.content.split())
        has_image = sum(att.content_type and att.content_type.startswith("image/") for att in message.attachments)
        pic_count += has_image
        
    # add or remove completion
    if pic_count >= num_pics and word_count >= num_words and message_count >= num_messages:
        insert_task_complete(conn,member_id,task_num)
    else:
        remove_task_complete(conn,member_id,task_num)
                    
async def add_submissions_after_date(conn, guild, channel_ids, task_num, needs_pics, needs_messages, start_month, start_day):
    # cycle through submission channels
    for channel_id in channel_ids:
        cur_channel = await guild.fetch_channel(channel_id)
        async for message in cur_channel.history(limit=None,oldest_first=False):
            # end search if message too old
            if fair_message_time(message) >= FAIR_CUTOFF_UTC:
                continue
            msg_time = message.created_at
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
            msg_time = msg_time.astimezone(LOCAL_TZ)
            month = msg_time.month
            day = msg_time.day
            if month < start_month:
                break
            if day < start_day:
                break
            
            # determine if message worth saving & save
            if needs_messages:
                insert_submission(conn, message.author.id, task_num, channel_id, message.id)
                    
            elif needs_pics and any(att.content_type and att.content_type.startswith("image/") for att in message.attachments):
                insert_submission(conn, message.author.id, task_num, channel_id, message.id)
    
async def update_fair_data(conn, guild, task_info, last_counted, progress=None):
    # Discord snowflakes encode UTC creation time. Revalidate previously indexed
    # late evidence even when there are no new submissions after the event.
    cutoff_id = discord.utils.time_snowflake(FAIR_CUTOFF_UTC)
    affected = set(conn.execute(
        "SELECT DISTINCT member_id, task_num FROM fair_task_submissions WHERE message_id >= ?",
        (cutoff_id,)
    ).fetchall())

    scan_started = datetime.datetime.now(LOCAL_TZ)
    
    if progress:
        await progress("Indexing Fair submissions...", force=True)

    # Index new submissions
    for i, task in enumerate(task_info, start=1):
        if progress:
            await progress(f"Indexing submissions — task {i}/{len(task_info)}: {task['name']}")
        num_pics = task["pic_count"]
        num_words = task["word_count"]
        num_messages = task["message_count"]
        
        needs_pics = num_pics > 0
        needs_messages = num_words > 0 or num_messages > 0
        
        channels_to_search = task["submission_channel"]
        if not isinstance(channels_to_search, list):
            channels_to_search = [channels_to_search]
        
        task_start = datetime.datetime(
            2026,
            task["start_month"],
            task["start_day"],
            tzinfo=LOCAL_TZ
        )
        
        start_time = max(last_counted, task_start)
        
        new_affected = await add_submissions_after_date(
            conn,
            guild,
            channels_to_search,
            i,
            needs_pics,
            needs_messages,
            start_time
        )
        
        affected.update(new_affected)
    
    # Recalculate pairs with new submissions or stored post-cutoff evidence
    if progress:
        await progress(f"Checking task completions — {len(affected)} to review...", force=True)
    for index, (member_id, task_num) in enumerate(affected, start=1):
        task = task_info[task_num - 1]
        if progress:
            await progress(f"Checking completion {index}/{len(affected)}: {task['name']}")
        
        await add_task_completions(
            conn,
            guild,
            task_num,
            member_id,
            task["pic_count"],
            task["word_count"],
            task["message_count"],
            task["start_month"],
            task["start_day"]
        )
    
    return scan_started

async def add_submissions_after_date(conn, guild, channel_ids, task_num, needs_pics, needs_messages, start_time):
    affected = set()
    if start_time >= FAIR_CUTOFF_UTC:
        return affected

    for channel_id in channel_ids:
        ("Next channel")
        cur_channel = await guild.fetch_channel(channel_id)
        
        async for message in cur_channel.history(limit=None, oldest_first=False):
            if fair_message_time(message) >= FAIR_CUTOFF_UTC:
                continue
            msg_time = message.created_at
            
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
            
            msg_time = msg_time.astimezone(LOCAL_TZ)
            
            if msg_time < start_time:
                break
            
            inserted = False
            
            if needs_messages:
                inserted = insert_submission(
                    conn,
                    message.author.id,
                    task_num,
                    channel_id,
                    message.id
                )
                
            elif needs_pics and any(
                att.content_type
                and att.content_type.startswith("image/")
                for att in message.attachments
            ):
                inserted = insert_submission(
                    conn,
                    message.author.id,
                    task_num,
                    channel_id,
                    message.id
                )
            
            if inserted:
                affected.add(
                    (
                        message.author.id,
                        task_num
                    )
                )
    
    return affected
    
@command_handler.Command(access_type=AccessType.PUBLIC)
async def tickets(activator: Neighbor, context: Context):
    if commands.chance(5):
        target_message = await context.send("Hmm, let me think on that one.", reply=True)
    else:
        target_message = await context.send("Thinking...", reply=True)
    
    last_progress_edit = 0.0

    async def progress(content, force=False):
        nonlocal last_progress_edit
        # Limit loop updates so large recounts do not flood Discord with edits.
        if not force and time.monotonic() - last_progress_edit < 2.0:
            return
        await target_message.edit(content=content)
        last_progress_edit = time.monotonic()

    await progress("Loading Fair tasks and finding the member...", force=True)
    guild = context.guild
    
    task_db_path = BASE_DIR / "data" / "fair_task_submissions.db"
    create_fair_task_tables(task_db_path)
    
    task_info_path = BASE_DIR / "lookups" / "fair_tasks.json"
    with task_info_path.open("r", encoding="utf-8") as f:
        task_info = json.load(f)
    
    # Find target member
    if len(context.args) > 0:
        try:
            target = await guild.fetch_member(int(parse_mention(context.args[0])))
        except:
            candidates = [x.nick for x in guild.members if x.nick is not None]
            candidates.extend([x.name for x in guild.members if not x.nick or x.nick != x.name])
            
            name, _ = best_string_match(context.args[0], [str(x) for x in candidates])
            target = discord.utils.get(guild.members, display_name=name) or discord.utils.get(guild.members, name=name)
    else:
        target = None
        
    target_member = context.author if target is None else target
    target_is_author = target is None
    
    # Fair 2026 has ended: display saved completions without scanning Discord.
    # Use $ticket_recount to refresh evidence. Keep update_fair_data and the
    # submission-indexing helpers available for future live events.
    with sqlite3.connect(task_db_path) as conn:
        await progress("Calculating blue tickets, golden tickets, and prizes...", force=True)

        # Build report
        final_report = {
            "total": 0,
            "sets": {
                1: {
                    "total": 0,
                    "tasks": []
                },
                2: {
                    "total": 0,
                    "tasks": []
                },
                3: {
                    "total": 0,
                    "tasks": []
                },
                "Bonus": {
                    "total": 0,
                    "tasks": []
                }
            }
        }
        
        tickets_accumulated = 0
        
        for i, task in enumerate(task_info, start=1):
            set_num = task["set_number"]
            if set_num == "Bonus":
                required_tickets = 60
            else:
                required_tickets = (set_num - 1) * 10
            
            # Tasks only count if their set has been unlocked
            if tickets_accumulated < required_tickets:
                completed = False
            else:
                completed = is_task_complete(conn, target_member.id, i)
            
            final_report["sets"][set_num]["tasks"].append({
                "task_num": i,
                "name": task["name"],
                "completed": completed,
                "tickets": task["tickets"]
            })
            
            if completed:
                tickets_accumulated += task["tickets"]
                final_report["sets"][set_num]["total"] += task["tickets"]
        
        final_report["total"] = tickets_accumulated
        task_ids = {task["name"]: i for i, task in enumerate(task_info, start=1)}
        bonus_task_ids = {
            i for i, task in enumerate(task_info, start=1)
            if task["set_number"] == "Bonus"
        }
        completed_task_ids = {
            task["task_num"]
            for task_set in final_report["sets"].values()
            for task in task_set["tasks"] if task["completed"]
        }
        golden_tickets = (
            min(4, len(completed_task_ids & bonus_task_ids))
            if tickets_accumulated >= 60 else 0
        )
        final_report["golden"] = golden_tickets
        final_report["bems"] = fair_bem_prize(tickets_accumulated, golden_tickets)
        science_task_id = task_ids.get("Citizen Scientist", task_ids.get("Citizen Science"))
        final_report["emoji_prizes"] = [
            {"name": "3+ golden tickets", "emoji": "🎟️", "earned": golden_tickets >= 3},
            {"name": "Copy Cats", "emoji": "🤹", "earned": task_ids.get("Copy Cats") in completed_task_ids},
            {"name": "Fair Vendor", "emoji": "🎪", "earned": task_ids.get("Fair Vendor") in completed_task_ids},
            {"name": "Citizen Scientist", "emoji": "🎡", "earned": science_task_id in completed_task_ids},
        ]

    await progress("Awarding earned nickname emojis...", force=True)
    neighbor = Neighbor(target_member.id, guild.id)
    for prize in final_report["emoji_prizes"]:
        item_name = f"Fair 2026 {prize['name']} nickname emoji"
        if prize["earned"] and not neighbor.get_item_of_name(item_name):
            item = Item(item_name, "event_emoji", time.time() + 21086592,
                        emoji=prize["emoji"], display="None")
            neighbor.bestow_item(item)

    await progress("Updating task board roles...", force=True)

    # Give task board roles
    set2_role = guild.get_role(1539861798960767027)
    set3_role = guild.get_role(1539861822461579264)
    setbonus_role = guild.get_role(1541628029514817616)
    
    if final_report["total"] >= 10 and set2_role not in target_member.roles:
        try:
            await target_member.add_roles(set2_role)
        except (discord.Forbidden, discord.HTTPException):
            pass
        
    if final_report["total"] >= 20 and set3_role not in target_member.roles:
        try:
            await target_member.add_roles(set3_role)
        except (discord.Forbidden, discord.HTTPException):
            pass
                    
    if final_report["total"] >= 60 and setbonus_role not in target_member.roles:
        try:
            await target_member.add_roles(setbonus_role)
        except (discord.Forbidden, discord.HTTPException):
            pass
                    
    await tickets_message(activator,context,target_message=target_message,target_member=target_member,target_is_author=target_is_author,final_report=final_report)
    
async def tickets_message(activator: Neighbor, context: Context, response: ResponsePackage=None, target_message=None, target_member=None, target_is_author=None, final_report=None):
    
    if response:
        target_message      =response.values["target_message"]
        target_member       =response.values["target_member"]
        target_is_author    =response.values["target_is_author"]
        final_report        =response.values["final_report"]
        page_num            =response.content.name
        
        emoji_to_digit = {
                "🎁": "Prizes",
                "1️⃣": 1,
                "2️⃣": 2,
                "3️⃣": 3,
                "✨": "Bonus"
            }

        page_num = emoji_to_digit[page_num]
    else:
        page_num = "Prizes"

    await target_message.clear_reactions()
        
    task_info_path = BASE_DIR / "lookups" / "fair_tasks.json"
    with task_info_path.open("r", encoding="utf-8") as f:
        task_info = json.load(f)
    
    member_suffix = f" ({target_member.display_name})" if target_member.id != context.author.id else ""
    if page_num == "Prizes":
        res = f"## FF Fair Prizes{member_suffix}\n"
    else:
        res = f"# FF Fair Progress (Task Set {page_num}){member_suffix}\n"

    res += f"**{final_report['total']} <:blue_carnival_ticket:1246080867114422335> earned!**\n"
    if final_report["total"] >= 60:
        res += f"**{final_report['golden']}/4 <:golden_carnival_ticket:1246080949620441190> earned!**\n"
    res += "\n"

    if page_num == "Prizes":
        bems = final_report["bems"]
        if bems in (89, 178, 267):
            sets = bems // 89
            bem_prize = f"{sets} BEM {'Set' if sets == 1 else 'Sets'} ({bems} BEMs)"
        else:
            bem_prize = f"{bems} {'BEM' if bems == 1 else 'BEMs'}"
        res += f"**BEMs won: {bem_prize}**\n"
        earned_emojis = " ".join(prize["emoji"] for prize in final_report["emoji_prizes"] if prize["earned"])
        if earned_emojis:
            res += f"**Emojis won:** {earned_emojis}\n"
        res += "\n➡️ Open a ticket to collect: <#1033207181857800242>"
    else:
        if page_num == "Bonus":
            res += "**Wow! You've tackled everything the FF Fair has thrown at you, but now you've found the secret Bonus Tasks. Do you have what it takes to conquer these extra-hard challenges?**\n\n"

        cur_report = final_report["sets"][page_num]
    
        for task in cur_report["tasks"]:
            if task["completed"]:
                reward = "1 <:golden_carnival_ticket:1246080949620441190>" if page_num == "Bonus" else f"{task['tickets']} <:blue_carnival_ticket:1246080867114422335>"
                res += f"✅ **{task['name']}** — {reward}\n"
            else:
                res += f"❌ {task['name']}\n"

        if final_report["total"] < 30:
            res += f"\n:arrow_right: Unlock more tasks with {10 - (final_report["total"] % 10)} more tickets.\n"
    
        task_set_links = {
            1: 1533137141498908875,
            2: 1533137175774756874,
            3: 1533137197702713558,
            "Bonus": 1540733835774402600,
        }
    
        res += f"\n:arrow_right: Link to this set's task board: <#{task_set_links[page_num]}>"
    
    await target_message.edit(content=res)
    
    total_tickets = final_report["total"]
    
    await target_message.add_reaction("🎁")
    await target_message.add_reaction("1️⃣")
    if total_tickets >= 10:
        await target_message.add_reaction("2️⃣")
    if total_tickets >= 20:
        await target_message.add_reaction("3️⃣")
    if total_tickets >= 60:
        await target_message.add_reaction("✨")
        
    def key(ctx):
        if not ctx.message.id == target_message.id:
            return False;
        if not ctx.emoji.name in ["🎁","1️⃣","2️⃣","3️⃣","✨"]:
            return False;
        return True;
    
    ResponseRequest(tickets_message, name="next_page",type="REACTION",activation_context=context,response_context=target_message,key=key,target_message=target_message,target_member=target_member,target_is_author=target_is_author,final_report=final_report)

@command_handler.Command(access_type=AccessType.PUBLIC)
async def tickets_family(activator: Neighbor, context: Context):
    
    target_message = await context.send("Let's see...")
   
    task_info_path = BASE_DIR / "lookups" / "fair_tasks.json"
    with task_info_path.open("r", encoding="utf-8") as f:
        task_info = json.load(f)
        
    families_info_path = BASE_DIR / "lookups" / "families.json"
    with families_info_path.open("r", encoding="utf-8") as f:
        families_info = json.load(f)
        
    task_db_path = BASE_DIR / "data" / "fair_task_submissions.db"
    create_fair_task_tables(task_db_path)
    
    with sqlite3.connect(task_db_path) as conn:
        res = "# Family Fair Progress\n"
        
        for family in families_info:
            name = family["name"]
            emoji = family["emoji"]
            role_id = family["role_id"]
            
            role = context.guild.get_role(role_id)
            
            if role is None:
                continue
            
            member_ids = [member.id for member in role.members]
            
            ticket_report = get_ticket_counts(conn, member_ids, task_info)
            total_tickets = ticket_report["total"]
            member_reports = ticket_report["members"]
            
            res += f"**{name}** {emoji}: {total_tickets} <:blue_carnival_ticket:1246080867114422335>\n"
        
    await target_message.edit(content=res)

# @command_handler.Command(access_type=AccessType.PUBLIC,desc="See your Fair progress!")
async def tickets(activator: Neighbor, context: Context):
    
    guild = context.guild
    
    if commands.chance(5):
        target_message = await context.send("Hmm, let me think on that one.")
    else:
        target_message = await context.send("Thinking...", reply=True)
    
    if len(context.args) > 0:
        try:
            target = await context.guild.fetch_member(int(parse_mention((context.args[0]))))
        except:
            candidates = [x.nick for x in context.guild.members if x.nick is not None]
            candidates.extend([x.name for x in context.guild.members if not x.nick or x.nick != x.name])
            name, _ = best_string_match(context.args[0], [str(x) for x in candidates])
            target = discord.utils.get(context.guild.members, display_name=name) or \
                     discord.utils.get(context.guild.members, name=name)
    else:
        target = None

    target_member = context.author if target is None else target
    target_is_author = True if target is None else False

    task_info_path = BASE_DIR / "lookups" / "fair_tasks.json"
    with task_info_path.open("r", encoding="utf-8") as f:
        task_info = json.load(f)
        
    final_report = []
    tickets_accumulated = 0;
    
    set2_role = context.guild.get_role(1539861798960767027)
    set3_role = context.guild.get_role(1539861822461579264)
        
    # Check all tasks!
    for task in task_info:
        set_num = task["set_number"]
        if set_num == "Bonus":
            required_tickets = 60
        else:
            required_tickets = (set_num - 1) * 10
        if tickets_accumulated < required_tickets:
            break;
        if set_num == 2:
            await target_member.add_roles(set2_role)
        if set_num == 3:
            await target_member.add_roles(set3_role)
        
        channels_to_search = task["submission_channel"]
        if not isinstance(channels_to_search, list):
            channels_to_search = [channels_to_search]
            
        # cycle through submission channels
        for channel_id in channels_to_search:
            cur_channel = await guild.fetch_channel(channel_id)
            
            pic_count = 0;
            word_count = 0;
            message_count = 0;
            
            # check all messages
            async for message in cur_channel.history(limit=None,oldest_first=False):
                
                # end search if message too old
                msg_time = message.created_at
                if msg_time.tzinfo is None:
                    msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
                msg_time = msg_time.astimezone(LOCAL_TZ)
                month = msg_time.month
                if month <= 7:
                    break
                
                # skip if wrong author
                if message.author.id != target_member.id:
                    continue;
                
                # up counts
                message_count += 1;
                word_count += len(message.content.split())
                has_image = sum(att.content_type and att.content_type.startswith("image/") for att in message.attachments)
                pic_count += has_image
                
            if pic_count >= task["pic_count"] and word_count >= task["word_count"] and message_count >= task["message_count"]:
                final_report.append(1)
                tickets_accumulated += task["tickets"]
                break
        else:
            final_report.append(0)

    res = "# FF Fair Progress\n"
    if target_is_author:
        res += f"**You have collected {tickets_accumulated} <:blue_carnival_ticket:1246080867114422335>!**\n\n"
    else:
        res += f"{target_member.display_name} has collected {tickets_accumulated} <:blue_carnival_ticket:1246080867114422335>!\n\n"

    for i,is_task_completed in enumerate(final_report):
        task = task_info[i]
        res += f"Task {i+1}: {task["name"]} {"✅" if is_task_completed else "❌"}\n"
    
    res += "\n:arrow_right: See the set 1 task board: ⁠<#1533137141498908875>\n"
    if i > 16:
        res += "\n:arrow_right: See the set 2 task board: ⁠<#1533137175774756874>\n"
        res += ":arrow_right: See the set 3 task board: ⁠<#1533137197702713558>\n"

    elif i > 8:
        res += "\n:arrow_right: See the set 2 task board: ⁠<#1533137175774756874>\n"
        res += f"Unlock more tasks with {20 - tickets_accumulated} more tickets!\n"

    else:
        res += f"Unlock more tasks with {10 - tickets_accumulated} more tickets!\n"
    res += "\n:arrow_right: Tasks due <t:1788235140:R>"
    
    await target_message.edit(content=res)    
           
def build_tickets_stats(conn, task_info):
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT member_id, task_num
        FROM fair_task_completions
        """
    )
    
    rows = cursor.fetchall()
    
    completions_by_member = {}
    
    for member_id, task_num in rows:
        if member_id not in completions_by_member:
            completions_by_member[member_id] = set()
            
        completions_by_member[member_id].add(task_num)
    
    task_stats = {}
    
    for i, task in enumerate(task_info, start=1):
        task_stats[i] = {
            "task_num": i,
            "name": task["name"],
            "set_number": task["set_number"],
            "tickets": task["tickets"],
            "completions": 0,
            "ticket_completions": 0,
            "tickets_generated": 0
        }
    
    # Raw task completions
    for member_id, completed_tasks in completions_by_member.items():
        for task_num in completed_tasks:
            if task_num in task_stats:
                task_stats[task_num]["completions"] += 1
    
    member_totals = {}
    member_earned_tasks = {}
    
    # Determine which completions actually earned tickets
    for member_id, completed_tasks in completions_by_member.items():
        tickets_accumulated = 0
        earned_tasks = []
        
        for task_num, task in enumerate(task_info, start=1):
            set_num = task["set_number"]
            if set_num == "Bonus":
                required_tickets = 60
            else:
                required_tickets = (set_num - 1) * 10
            
            if tickets_accumulated < required_tickets:
                continue
            
            if task_num in completed_tasks:
                tickets_accumulated += task["tickets"]
                earned_tasks.append(task_num)
                
                task_stats[task_num]["ticket_completions"] += 1
                task_stats[task_num]["tickets_generated"] += task["tickets"]
        
        member_totals[member_id] = tickets_accumulated
        member_earned_tasks[member_id] = earned_tasks
    
    sets = {}
    
    for task in task_stats.values():
        set_num = task["set_number"]
        
        if set_num not in sets:
            sets[set_num] = {
                "completions": 0,
                "ticket_completions": 0,
                "tickets_generated": 0,
                "participants": set()
            }
        
        sets[set_num]["completions"] += task["completions"]
        sets[set_num]["ticket_completions"] += task["ticket_completions"]
        sets[set_num]["tickets_generated"] += task["tickets_generated"]
    
    for member_id, earned_tasks in member_earned_tasks.items():
        participated_sets = set()
        
        for task_num in earned_tasks:
            participated_sets.add(task_stats[task_num]["set_number"])
        
        for set_num in participated_sets:
            sets[set_num]["participants"].add(member_id)
    
    for set_num in sets:
        sets[set_num]["participants"] = len(sets[set_num]["participants"])
    
    tasks_by_set = {}
    
    for task in task_stats.values():
        set_num = task["set_number"]
        
        if set_num not in tasks_by_set:
            tasks_by_set[set_num] = []
        
        tasks_by_set[set_num].append(task)
    
    tasks_by_completions = {}
    tasks_by_ticket_impact = {}
    
    for set_num, tasks in tasks_by_set.items():
        tasks_by_completions[set_num] = sorted(
            tasks,
            key=lambda x: (-x["completions"], x["task_num"])
        )
        
        tasks_by_ticket_impact[set_num] = sorted(
            tasks,
            key=lambda x: (-x["tickets_generated"], -x["ticket_completions"], x["task_num"])
        )
    
    top_members = sorted(
        member_totals.items(),
        key=lambda x: (-x[1], x[0])
    )[:20]
    
    participants = [
        member_id
        for member_id, total in member_totals.items()
        if total > 0
    ]
    
    bonus_task_ids = {
        i for i, task in enumerate(task_info, start=1)
        if task["set_number"] == "Bonus"
    }
    total_bems = sum(
        fair_bem_prize(
            blue_tickets,
            min(4, len(set(member_earned_tasks[member_id]) & bonus_task_ids))
            if blue_tickets >= 60 else 0
        )
        for member_id, blue_tickets in member_totals.items()
    )
    total_tickets = sum(member_totals.values())
    total_raw_completions = sum(task["completions"] for task in task_stats.values())
    total_ticket_completions = sum(task["ticket_completions"] for task in task_stats.values())
    
    most_completed_task = max(
        task_stats.values(),
        key=lambda x: x["completions"],
        default=None
    )
    
    biggest_ticket_task = max(
        task_stats.values(),
        key=lambda x: x["tickets_generated"],
        default=None
    )
    
    return {
        "tasks_by_completions": tasks_by_completions,
        "tasks_by_ticket_impact": tasks_by_ticket_impact,
        "top_members": top_members,
        "sets": sets,
        "total_tickets": total_tickets,
        "total_bems": total_bems,
        "total_raw_completions": total_raw_completions,
        "total_ticket_completions": total_ticket_completions,
        "participant_count": len(participants),
        "average_tickets": total_tickets / len(participants) if participants else 0,
        "most_completed_task": most_completed_task,
        "biggest_ticket_task": biggest_ticket_task
    }


@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def tickets_stats(activator: Neighbor, context: Context):
    target_message = await context.send("Crunching Fair numbers...")
    
    guild = context.guild
    
    task_info_path = BASE_DIR / "lookups" / "fair_tasks.json"
    with task_info_path.open("r", encoding="utf-8") as f:
        task_info = json.load(f)
    
    task_db_path = BASE_DIR / "data" / "fair_task_submissions.db"
    create_fair_task_tables(task_db_path)
    
    # Catch database up before calculating stats
    last_counted = commands.remember("tickets_last_counted_Fair_2026")
    
    if last_counted is None:
        last_counted = datetime.datetime(2026, 8, 22, tzinfo=LOCAL_TZ)
        
    elif isinstance(last_counted, tuple):
        if len(last_counted) == 2:
            month, day = last_counted
            last_counted = datetime.datetime(2026, month, day, tzinfo=LOCAL_TZ)
        else:
            last_counted = datetime.datetime(*last_counted, tzinfo=LOCAL_TZ)
    
    with sqlite3.connect(task_db_path) as conn:
        new_last_counted = await update_fair_data(conn, guild, task_info, last_counted)
        commands.remember("tickets_last_counted_Fair_2026", new_last_counted)
        
        stats_report = build_tickets_stats(conn, task_info)
    
    await tickets_stats_message(activator, context, target_message=target_message, stats_report=stats_report)


async def tickets_stats_message(activator: Neighbor, context: Context, response: ResponsePackage=None, target_message=None, stats_report=None):
    
    if response:
        target_message = response.values["target_message"]
        stats_report = response.values["stats_report"]
        page_num = response.content.name
        
        emoji_to_digit = {
            "🎪": 1,
            "🏆": 2,
            "🎟️": 3,
            "👑": 4,
            "📊": 5
        }
        
        page_num = emoji_to_digit[page_num]
    else:
        page_num = 1
    
    await target_message.clear_reactions()
    
    if page_num == 1:
        res = "# 🎪 Fair Stats — Overview\n\n"
        
        res += f"**Participating Farmers:** {stats_report['participant_count']}\n"
        res += f"**Tickets Awarded:** {stats_report['total_tickets']} 🎟️\n"
        res += f"**Total BEMs Earned:** {stats_report['total_bems']:,}\n"
        res += f"**Recorded Task Completions:** {stats_report['total_raw_completions']}\n"
        res += f"**Ticket-Earning Completions:** {stats_report['total_ticket_completions']}\n"
        res += f"**Average Tickets per Farmer:** {stats_report['average_tickets']:.1f}\n"
        
        most_completed = stats_report["most_completed_task"]
        biggest_ticket = stats_report["biggest_ticket_task"]
        
        if most_completed is not None:
            res += f"\n**Most Completed Task:** {most_completed['name']} ({most_completed['completions']}x)\n"
        
        if biggest_ticket is not None:
            res += f"**Biggest Ticket Generator:** {biggest_ticket['name']} ({biggest_ticket['tickets_generated']} 🎟️)\n"
    
    elif page_num == 2:
        res = "# 🏆 Fair Stats — Task Popularity\n"
        res += "*Sorted by completions.*\n\n"
        
        for set_num, tasks in stats_report["tasks_by_completions"].items():
            res += f"**Set {set_num}**\n"
            
            for i, task in enumerate(tasks, start=1):
                res += f"{i}. **{task['name']}** — {task['completions']}x\n"
            
            res += "\n"
    
    elif page_num == 3:
        res = "# 🎟️ Fair Stats — Ticket Impact\n"
        res += "*Tickets generated (ticket-earning completions).*\n\n"
        
        for set_num, tasks in stats_report["tasks_by_ticket_impact"].items():
            res += f"**Set {set_num}**\n"
            
            for i, task in enumerate(tasks, start=1):
                res += f"{i}. **{task['name']}** — {task['tickets_generated']}🎟️ ({task['ticket_completions']}x)\n"
            
            res += "\n"
    
    elif page_num == 4:
        res = "# 👑 Fair Stats — Top 20 Farmers\n\n"
        
        for rank, (member_id, tickets) in enumerate(stats_report["top_members"], start=1):
            member = context.guild.get_member(member_id)
            name = member.display_name if member is not None else f"Unknown Farmer ({member_id})"
            
            res += f"**{rank}. {name}** — {tickets} 🎟️\n"
    
    elif page_num == 5:
        res = "# 📊 Fair Stats — Task Sets\n\n"
        
        for set_num, set_stats in stats_report["sets"].items():
            res += f"## Set {set_num}\n"
            res += f"**Participants:** {set_stats['participants']}\n"
            res += f"**Recorded Completions:** {set_stats['completions']}\n"
            res += f"**Ticket-Earning Completions:** {set_stats['ticket_completions']}\n"
            res += f"**Tickets Awarded:** {set_stats['tickets_generated']} 🎟️\n\n"
    
    await target_message.edit(content=res)
    
    await target_message.add_reaction("🎪")
    await target_message.add_reaction("🏆")
    await target_message.add_reaction("🎟️")
    await target_message.add_reaction("👑")
    await target_message.add_reaction("📊")
    
    def key(ctx):
        if ctx.message.id != target_message.id:
            return False;
        if ctx.emoji.name not in ["🎪", "🏆", "🎟️", "👑", "📊"]:
            return False;
        return True;
    
    ResponseRequest(
        tickets_stats_message,
        name="stats_page",
        type="REACTION",
        activation_context=context,
        response_context=target_message,
        key=key,
        target_message=target_message,
        stats_report=stats_report
    )
           
def parse_mention(content):
    start = content.find("<@")
    end = content.find(">", start)
    if start == -1 or end == -1:
        raise ValueError("Not an ID")
    id_str = content[start+2:end]
    if id_str.startswith("!"):
        id_str = id_str[1:]
    if not id_str.isdigit():
        raise ValueError("Not an ID")
    return int(id_str)

def best_string_match(target, candidates):
    def similarity(x):
        return difflib.SequenceMatcher(None, x, target, autojunk=False).ratio()

    target_lower = target.lower()
    word_matches = [c for c in candidates if target_lower in c.lower().split()]
    substring_matches = [c for c in candidates if target_lower in c.lower()]

    if word_matches:
        best_match = max(word_matches, key=similarity)
    elif substring_matches:
        best_match = max(substring_matches, key=similarity)
    else:
        best_match = max(candidates, key=similarity)
        
    return best_match, similarity(best_match);

def convert_mentions_to_text(context: Context, str):
    role_id = "";
    start_pos = 0;
    end_pos = 0;
    for letter, i in enumerate(str):
        if letter == "<" and str[i + 1] == "@":
            start_pos = i;
            for ii in range(i + 2, len(str), 1):
                if not str[ii] == ">":
                    role_id += str[ii];
                else:
                    end_pos == ii;
                    break;
            break;
    try:
        role = context.guild.get_role(int(role_id));
        name = role.name;
        str = str[0:i] + "@" + name + str[ii + 1:];
        return str;
    except:
        pass;

import sqlite3

def create_fair_task_tables(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fair_task_completions (
                member_id INTEGER NOT NULL,
                task_num INTEGER NOT NULL,

                PRIMARY KEY (member_id, task_num)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fair_task_submissions (
                member_id INTEGER NOT NULL,
                task_num INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,

                PRIMARY KEY (
                    member_id,
                    task_num,
                    channel_id,
                    message_id
                )
            )
            """
        )