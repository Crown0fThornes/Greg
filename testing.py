import asyncio
import datetime
import difflib
import random
import threading
import discord
import custom_types;
from discord.ext import tasks
import commands
import command_handler
from command_handler import Context, Command, Uncontested, Loop, Scheduled
from custom_types import Neighbor
import commands as commands
from importlib import reload as sync
from id_bundle import FF
from phoenix_bundle import PHOENIX
import time

"""
Greg 3.0!
Author: Lincoln Edsall

This script serves as the overhead controller for the client. 
It sets up the intents, listens for events, and prepares the command file.

persistent_types.py defines types such as Neighbor, Item, and Expectation
	which Greg relies on to allow information to persist
command_handler.py is where commands are wrapped, and run based off listeners events here
commands.py is where all commands are defined
id_bundle.py provides a list of role, channel, and other relevant ids for FF discord server
"""

# meta data and intents _____
version = "3.2"
intents = discord.Intents.all();
intents.message_content = True;
intents.members = True;
playing = discord.Game(name="$harvest once per hour!")
client = discord.Client(intents=intents,activity = playing);
RUN_LOOP_COMMANDS = False;
RUN_SCHEDULED_COMMANDS = False;
# ___________________________

# loop = asyncio.get_event_loop();
# loop.create_task(command_handler.handle_response_queue());
# loop.run_forever();
# response_thread = threading.Thread(target=command_handler.handle_response_queue)
# response_thread.start();
# asyncio.run(command_handler.handle_response_queue());

#Written with assistance from chatGPT
def is_within_dates(start_date, end_date=None):
    current_date = datetime.datetime.now().date()
    start_date = datetime.datetime(current_date.year, *start_date).date() if len(start_date) == 2 else datetime.datetime(*start_date).date()
    if end_date:
        end_date = datetime.datetime(current_date.year, *end_date).date() if len(end_date) == 2 else datetime.datetime(*end_date).date();

    if end_date:
        return start_date <= current_date <= end_date
    else:
        return current_date >= start_date

if is_within_dates((11,9),(12,31)):
    codes = {
        "&FFP_LOGO": "<:farmmas_ffp_logo:1170071905089368075>",
        "&FF_LOGO": "<:farmmas_ff_logo:1170071779037945907>",
        "&FFJ_LOGO": "<:farmmas_ffj_logo:1170071826517467136>",
        "&FFG_LOGO": "<:farmmas_ffg_logo:1173333335876050985>",
        "&FFR_LOGO": "<:farmmas_ffr_logo:1170071889029386404>",
        "&FFP_TAG": "{codes['&FFR_TAG']}",
        "&FF_TAG": "#9UPRVCUR",
        "&FFJ_TAG": "#PC8VCJ8Q",
        "&FFG_TAG": "TBD",
        "&FFR_TAG": "#L92LUVQJ",
    }
else:
    codes = {
        "&FFP_LOGO": "<:ff_logo:1111011971953872976>",
        "&FF_LOGO": "<:ff_logo:1111011971953872976>",
        "&FFJ_LOGO": "<:ffj_logo:1111011976320122880>",
        "&FFG_LOGO": "<:ffg_logo:1173332572642754560>",
        "&FFR_LOGO": "#L92LUVQJ",
        "&FFP_TAG": "{codes['&FFR_TAG']}",
        "&FF_TAG": "#9UPRVCUR",
        "&FFJ_TAG": "#PC8VCJ8Q",
        "&FFG_TAG": "TBD",
        "&FFR_TAG": "{codes['&FFR_TAG']}",
    }

# This listener is called when the client becomes "ready". Unfortunately, this is called when the code is first run but can also be called
    # randomly based on stuff happening behind the scenes in the Discord api. So, it's not a great way of doing something every time the bot comes online
@client.event
async def on_ready():
    print("All systems go!");
    
    if RUN_LOOP_COMMANDS and not manage_timed_commands.is_running():
        manage_timed_commands.start();
        
    if RUN_SCHEDULED_COMMANDS and not manage_scheduled_commands.is_running():
        manage_scheduled_commands.start();
    for guild in client.guilds:
        if guild.id == 647883751853916162:
            await guild.get_member(client.user.id).edit(nick=f"Greg Testing");
            print("now")

        print(f'Logged in as {client.user.name} ({client.user.id})')
        

@client.event
async def on_message(message):
    if message.content == "$sync" and message.author.id == 355169964027805698:
        sync(custom_types)
        sync(command_handler);
        sync(commands);
        await message.channel.send("Done! Modules synced");
    
    if message.author.bot:
        return;
    # if not message.guild.id == 647883751853916162:
    #     return;
    context = Context(message=message);
    neighbor = Neighbor(message.author.id, message.guild.id);
    await Command.execute(neighbor, context);
    await Uncontested.execute(context);
            
@client.event
async def on_raw_reaction_add(reaction):
    if reaction.member.bot:
        return;
    if not reaction.event_type == "REACTION_ADD":
        return;
    context = Context();
    context.type = "REACTION";
    context.guild = client.get_guild(reaction.guild_id);
    context.channel = await context.guild.fetch_channel(reaction.channel_id);
    context.message = await context.channel.fetch_message(reaction.message_id);
    context.author = context.message.author;
    context.user = reaction.member;
    context.ID_bundle = FF if context.guild.id == FF.guild else PHOENIX;
    context.emoji = reaction.emoji;
    context.author_id = context.message.author.id;
    context.author_role_ids = [role.id for role in context.message.author.roles];
    context.reaction = reaction;
    context.set_access_type();
    await Uncontested.execute(context);
    
# @client.event
async def on_member_update(before, after):
    if after.bot:
        return 0;
    
    if after.display_name != before.display_name:
        await commands.set_nick(after, after.guild, True);
        
    if after.guild.id == 647883751853916162:
        # await commands.assign_family(client, before, after);
        
        current_date = datetime.date.today()
        target_date = datetime.date(current_date.year, 10, 2)
        
        
        before_role_ids = [x.id for x in before.roles];
        after_role_ids = [x.id for x in after.roles];
        NH_roles = {
            FF.p_neighbors_role : "ffp",
            FF.neighbors_role : "ff",
            FF.j_neighbors_role : "ffj",
            1334660124639236267: "ffj2",
            FF.g_neighbors_role : "ffg", 
            1342329111359656008: "ffc", 
            FF.r_neighbors_role : "ffr"}
        joinlist = await after.guild.fetch_channel(943263445724311572);
        leavelist = await after.guild.fetch_channel(1138557740185305169)

        before_nh_roles = set(before_role_ids) & set(NH_roles.keys())
        after_nh_roles = set(after_role_ids) & set(NH_roles.keys())
        if len(after_nh_roles - before_nh_roles) > 0:
            NH = NH_roles[(set(after_role_ids) - set(before_role_ids)).pop()];
            await joinlist.send(after.display_name + " has joined " + NH)
            
        if len(before_nh_roles - after_nh_roles) > 0:
            NH = NH_roles[(set(before_role_ids) - set(after_role_ids)).pop()];
            await leavelist.send(after.display_name + " has left " + NH)
            
        if len(after_nh_roles) > 0:
            await after.add_roles(after.guild.get_role(1181330910747054211));
        else:
            await after.remove_roles(after.guild.get_role(1181330910747054211))
            
        
            
            
        
        # rp_channel = await after.guild.fetch_channel(1156989701518020609);
        
        # if bool(set(role_ids) & set(neighbor_roles)) and not bool(set(role_ids) & set(family_roles)):
        #     await rp_channel.send(f"It seems like <@{after.id}> has a Neighbor role, but no Family role! That doesn't seem right 🤨");
        # if not bool(set(role_ids) & set(neighbor_roles)) and bool(set(role_ids) & set(family_roles)):
        #     await rp_channel.send(f"It seems like <@{after.id}> has a family role, but no Family role! I don't think it works like that 🫠");
        
        # role = discord.utils.get(after.guild.roles, id=1024052938752151552)
        # count = sum(1 for member in after.guild.members if role in member.roles)
        # if count > 30:
        #     await rp_channel.send(f"Wow! There are {count} members with the Pro Neighbor role! I didn't know that was possible! 😀")
        
        # role = discord.utils.get(after.guild.roles, id=656112994392080384)
        # count = sum(1 for member in after.guild.members if role in member.roles)
        # if count > 30:
        #     await rp_channel.send(f"Wow! There are {count} members with the Main Neighbor role! That's... cool... 🥹")
            
        # role = discord.utils.get(after.guild.roles, id=689928709683150909)
        # count = sum(1 for member in after.guild.members if role in member.roles)
        # if count > 30:
        #     await rp_channel.send(f"Wow! There are {count} members with the Junior Neighbor role! How'd you manage that? 🤨")
            
        # role = discord.utils.get(after.guild.roles, id=1034248720058945577)
        # count = sum(1 for member in after.guild.members if role in member.roles)
        # if count > 30:
        #     await rp_channel.send(f"Wow! There are {count} members with the Resort Neighbor role! Maybe fix it? 😗")
            
        # role = discord.utils.get(after.guild.roles, id=1173325157767589988)
        # count = sum(1 for member in after.guild.members if role in member.roles)
        # if count > 30:
        #     await rp_channel.send(f"Wow! There are {count} members with the Garden Neighbor role! Who let that happen? Wasn't me 😊")

    
# @client.event
async def on_member_join(member, NH = None):
    if (member.guild.id != 647883751853916162):
        return 0;
    
    if NH is None:
        guild = client.get_guild(FF.guild);
        general = await guild.fetch_channel(FF.general_channel); 
        target = await general.send(f"**Welcome to Town, <@{str(member.id)}>!\nWe're happy to see you.**\n\nIf you're looking for a Neighborhood, please:\n1) Check out <#648257841064574986> to learn about our NHs, then\n2) Open a ticket <#1033207181857800242> to chat with leaders.\n-# *Please do not try to join in the game before speaking to a Council Member to help you, or else it may be declined. In the meantime, make sure your server nickname matches your farm name!*");
        with open("welcome_town.png", 'rb') as file:
            await general.send(file=discord.File(file))
   
   
# @client.event
async def on_member_remove(member):
    if (member.guild.id != 647883751853916162):
        return 0;
    
    guild = client.get_guild(FF.guild);
    general = await guild.fetch_channel(FF.general_channel);  
    await general.send(member.name + " has left Town."); 
    with open("leaving_town.png", 'rb') as file:
            await general.send(file=discord.File(file))

# @client.event
async def on_message_edit(before, after):
    if (after.guild.id != 647883751853916162):
        try:
            audit = await after.guild.fetch_channel(PHOENIX.audit_channel);
        except Exception as e:
            pass;
    else:
        audit = await after.guild.fetch_channel(FF.audit_channel);
    
    if after.author.bot:
        return 0;

    # context = Context(before = before, after = after, message = after);

    # similarity = difflib.SequenceMatcher(None, context.before.content, context.after.content).ratio();
    # if similarity < .75:
    #     audit_channel = await context.guild.fetch_channel(736279745150320688);
    #     before_content = convert_mentions_to_text(context, context.before.content);
    #     after_content = convert_mentions_to_text(context, context.after.content)
    #     text = f"*A message from <@{context.author_id}> ({context.author}) was edited:*\n> {before_content}\n\n> {after_content}";
    #     await audit_channel.send(text);

    matcher = difflib.SequenceMatcher(None, before.content, after.content)

    # Get the percentage of similarity between the strings
    similarity = matcher.ratio()

    flag = False;
    if (similarity < .95):
        flag = True;

    if flag:
        await audit.send(f"{before.author} edited a message.");
        await audit.send(f"{before.content}");
        await audit.send(f"{after.content}");

@client.event
async def on_message_delete(message):
    try:
        audit = await message.guild.fetch_channel(FF.audit_channel);

        await audit.send(f"A message from {message.author} was deleted.");
        await audit.send(f"{message.content}");
    except:
        print("Error with delete!");
    
@tasks.loop(minutes=1)
async def manage_scheduled_commands():
    print("scheduler")
    await Scheduled.execute(client)

@tasks.loop(minutes=5)
async def manage_timed_commands():
    print("here");
    await Loop.execute(client);

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the same directory as this file
load_dotenv(Path(__file__).resolve().parent / ".env")

# try:
BOT_TOKEN = os.environ["BOT_TOKEN"] 
client.run(BOT_TOKEN, reconnect=True);
# except:
#     print("Get development bot token from Lincoln & set env variable")
    
