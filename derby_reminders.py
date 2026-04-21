from math import floor
from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
from custom_types import Neighbor, Item
from responses import ResponsePackage, ResponseRequest
import commands
import time
import random
import sqlite3
import json
import password_manager
import math
import discord
import difflib


with open('lookups/families.json') as fFamilies:
    FAMILIES_JSON = json.load(fFamilies)

# Animal Week

@command_handler.Scheduled(time="12:00", day_of_month=14)   #8am
async def animal_tasks_reminder_tuesday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# The Animal tasks week has begun \nHey <@&{cur_role_id}>, the derby has begun and we need to crush some Animal tasks this week! Remember, you have until Saturday at 8am Server time (exactly 4 days from now) to take as many egg, milk, bacon, wool, goat milk, or feed tasks as possible and submit screenshots to <#1203772906497380472> with a number indicating how many you completed in the message."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
@command_handler.Scheduled(time="12:00", day_of_month=16)   #8am
async def animal_tasks_reminder_thursday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# Two day warning \nHey <@&{cur_role_id}>, the derby is underway! Remember, you have until Saturday at 8am Server time (exactly 2 days from now) to take as many egg, milk, bacon, wool, goat milk, or feed tasks as possible."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])     
@command_handler.Scheduled(time="12:00", day_of_month=17)   #8am
async def animal_tasks_reminder_friday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# One day warning \nHey <@&{cur_role_id}>, the derby is underway! Remember, you have until Saturday at 8am Server time (exactly 1 day from now) to take as many egg, milk, bacon, wool, goat milk, or feed tasks as possible."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
        
    
    submission_channel = await guild.fetch_channel(1203772906497380472)
    await submission_channel.send("Submissions of persontal task log screenshots for the Animal tasks week of Get Down With Derby are now open. Include the number of tasks in the Animal category that you completed in the text part of your message so Greg (I) can count them. Basket tasks count in partials (.33 if 1 part was animal; .67 if 2 parts were animal; 1 if all 3 were animal)")
@command_handler.Scheduled(time="00:00", day_of_month=18)   # 8pm
async def animal_tasks_reminder_friday_final_warning(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# It's time to submit! \nHey <@&{cur_role_id}>, this week's Animal task challnege is coming to an end in 12 hours! You need to submit screenshots of your personal task log to <#1203772906497380472> with a number indicating how many you completed in the message within 12 hours in order for your points to count."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
@command_handler.Scheduled(time="12:00", day_of_month=18)   #8am
async def animal_tasks_reminder_saturday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# The Animal tasks week is now over \nWell done team!"
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
        
    submission_channel = await guild.fetch_channel(1203772906497380472)
    await submission_channel.send("Submissions are now closed for the Animal tasks week of Get Down With Derby. For the rest of this derby, it's \"back to normal\". Go back to using regular task trashing guidelines and finish up your requirements. Great work everyone!")



# Town Week




@command_handler.Scheduled(time="12:00", day_of_month=28)   #8am
async def town_tasks_reminder_tuesday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# The Town tasks week has begun \nHey <@&{cur_role_id}>, the derby has begun and we need to crush some Town tasks this week! Remember, you have until Saturday at 8am Server time (exactly 4 days from now) to take as many full train, townie, or building tasks as possible and submit screenshots to <#1203772906497380472> with a number indicating how many you completed in the message."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
@command_handler.Scheduled(time="12:00", day_of_month=30)   #8am
async def town_tasks_reminder_thursday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# Two day warning \nHey <@&{cur_role_id}>, the derby is underway! Remember, you have until Saturday at 8am Server time (exactly 2 days from now) to take as many full train, townie, or building tasks as possible."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])     
@command_handler.Scheduled(time="12:00", day_of_month=1)   #8am
async def town_tasks_reminder_friday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# One day warning \nHey <@&{cur_role_id}>, the derby is underway! Remember, you have until Saturday at 8am Server time (exactly 1 day from now) to take as many full train, townie, or building tasks as possible."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
        
    
    submission_channel = await guild.fetch_channel(1203772906497380472)
    await submission_channel.send("Submissions of persontal task log screenshots for the Town tasks week of Get Down With Derby are now open. Include the number of tasks in the Town category that you completed in the text part of your message so Greg (I) can count them. Basket tasks count in partials (.33 if 1 part was town; .67 if 2 parts were town; 1 if all 3 were town)")
@command_handler.Scheduled(time="00:00", day_of_month=2)   # 8pm
async def town_tasks_reminder_friday_final_warning(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# It's time to submit! \nHey <@&{cur_role_id}>, this week's Town task challnege is coming to an end in 12 hours! You need to submit screenshots of your personal task log to <#1203772906497380472> with a number indicating how many you completed in the message within 12 hours in order for your points to count."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
@command_handler.Scheduled(time="12:00", day_of_month=2)   #8am
async def town_tasks_reminder_saturday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# The Town tasks week is now over \nWell done team!"
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
        
    submission_channel = await guild.fetch_channel(1203772906497380472)
    await submission_channel.send("Submissions are now closed for the Town tasks week of Get Down With Derby. For the rest of this derby, it's \"back to normal\". Go back to using regular task trashing guidelines and finish up your requirements. Great work everyone!")
    
    
    
    
# Production Week




@command_handler.Scheduled(time="12:00", day_of_month=5)   #8am
async def production_tasks_reminder_tuesday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# The Production tasks week has begun \nHey <@&{cur_role_id}>, the derby has begun and we need to crush some Production tasks this week! Remember, you have until Saturday at 8am Server time (exactly 4 days from now) to take as many production tasks as possible and submit screenshots to <#1203772906497380472> with a number indicating how many you completed in the message."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
@command_handler.Scheduled(time="12:00", day_of_month=7)   #8am
async def production_tasks_reminder_thursday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# Two day warning \nHey <@&{cur_role_id}>, the derby is underway! Remember, you have until Saturday at 8am Server time (exactly 2 days from now) to take as many production tasks as possible."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])     
@command_handler.Scheduled(time="12:00", day_of_month=8)   #8am
async def production_tasks_reminder_friday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# One day warning \nHey <@&{cur_role_id}>, the derby is underway! Remember, you have until Saturday at 8am Server time (exactly 1 day from now) to take as many production tasks as possible."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
        
    
    submission_channel = await guild.fetch_channel(1203772906497380472)
    await submission_channel.send("Submissions of persontal task log screenshots for the Production tasks week of Get Down With Derby are now open. Include the number of tasks in the Production category that you completed in the text part of your message so Greg (I) can count them. Basket tasks count in partials (.33 if 1 part was production; .67 if 2 parts were production; 1 if all 3 were production)")
@command_handler.Scheduled(time="00:00", day_of_month=2)   # 8pm
async def producton_tasks_reminder_friday_final_warning(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# It's time to submit! \nHey <@&{cur_role_id}>, this week's Production task challnege is coming to an end in 12 hours! You need to submit screenshots of your personal task log to <#1203772906497380472> with a number indicating how many you completed in the message within 12 hours in order for your points to count."
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
@command_handler.Scheduled(time="12:00", day_of_month=9)   #8am
async def town_tasks_reminder_saturday(client):
    guild = client.get_guild(647883751853916162)
    
    for family in FAMILIES_JSON:
        cur_role_id = family["role_id"]
        cur_chat_id = family["chat"]
        
        cur_chat = await guild.fetch_channel(cur_chat_id)
        
        msg = f"# The Production tasks week is now over \nWell done team!"
        target_context = Context(await cur_chat.send(msg))
        await target_context.react(family["emoji"])
        
    submission_channel = await guild.fetch_channel(1203772906497380472)
    await submission_channel.send("Submissions are now closed for the Production tasks week of Get Down With Derby. For the rest of this derby, it's \"back to normal\". Go back to using regular task trashing guidelines and finish up your requirements. Great work everyone!")