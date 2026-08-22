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

@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def ticket_recount(activator: Neighbor, context: Context, month = None, day = None):
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
            await target_message.edit(content=f"Indexing {task["name"]}")
            
            num_pics = task["pic_count"]
            num_words = task["word_count"]
            num_messages = task["message_count"]
            
            needs_pics = num_pics > 0
            needs_messages = num_words > 0 or num_messages > 0
            
            start_month = month or task["start_month"]
            start_day = day or task["start_day"]
                    
            channels_to_search = task["submission_channel"]
            if not isinstance(channels_to_search, list):
                channels_to_search = [channels_to_search]
            
            await add_submissions_after_date(conn, guild, channels_to_search, i, needs_pics, needs_messages, start_month, start_day)
                
        # Validate task completion 
        for i, task in enumerate(task_info, start=1):
            await target_message.edit(content=f"Counting {task["name"]}")
            
            num_pics = task["pic_count"]
            num_words = task["word_count"]
            num_messages = task["message_count"]
            
            needs_pics = num_pics > 0
            needs_messages = num_words > 0 or num_messages > 0
            
            start_month = month or task["start_month"]
            start_day = day or task["start_day"]
                   
            member_ids = get_members_with_task_submissions(conn, i)
                    
            for member_id in member_ids:
                await add_task_completions(conn, guild, i, member_id, num_pics, num_words, num_messages, start_month, start_day)
        
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
    
@command_handler.Command(access_type=AccessType.PUBLIC)
async def tickets(activator: Neighbor, context: Context):
    
    date = commands.remember("tickets_last_counted_Fair_2026")
    month, day = (8, 22) if date is None else date
    
    task_db_path = BASE_DIR / "data" / "fair_task_submissions.db"
    # with sqlite3.connect(task_db_path) as conn:
    #     await ticket_recount(activator, context, month, day)
        
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
        
    with sqlite3.connect(task_db_path) as conn:
       
        # Check all tasks!
        for i, task in enumerate(task_info, start=1):
            set_num = int(task["set_number"])
            required_tickets = (set_num-1)*10
            if tickets_accumulated < required_tickets:
                print(tickets_accumulated)
                print(required_tickets)
                break;
            if set_num == 2:
                await target_member.add_roles(set2_role)
            if set_num == 3:
                await target_member.add_roles(set3_role)
            
            if is_task_complete(conn,target_member.id,i):
                final_report.append(1)
                tickets_accumulated += task["tickets"]
            else:
                channels_to_search = task["submission_channel"]
                if not isinstance(channels_to_search, list):
                    channels_to_search = [channels_to_search]
                    
                # cycle through submission channels
                for channel_id in channels_to_search:
                    cur_channel = await context.guild.fetch_channel(channel_id)
                    
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
    

    target_member = context.author if target is None else target
    target_is_author = True if target is None else False
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
    
    await context.send(res,reply=True)
    

# @command_handler.Command(access_type=AccessType.PUBLIC,desc="See your Fair progress!")
async def tickets(activator: Neighbor, context: Context):
    
    guild = context.guild
    
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
        set_num = int(task["set_number"])
        required_tickets = (set_num-1)*10
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
        
    # Send final message

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
    
    await context.send(res,reply=True)
         
                
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