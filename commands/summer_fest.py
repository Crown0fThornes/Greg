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

import json
BASE_DIR = Path(__file__).resolve().parent.parent

@command_handler.Command(access_type=AccessType.PUBLIC,desc="See your Fair progress!")
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
        
    # Check all tasks!
    for task in task_info:
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
    
    res += "\n:arrow_right: See the task board: ⁠<#1533137141498908875>\n"
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
