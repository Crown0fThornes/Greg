import asyncio
import datetime
import difflib
import random
import threading
import discord
import custom_types;
from discord.ext import tasks
import commands.commands as commands
import command_handler
from command_handler import Context, Command, Uncontested, Loop, Scheduled
from custom_types import Neighbor
from importlib import reload as sync
from id_bundle import FF
from phoenix_bundle import PHOENIX
import time
from persistence.rolodex import Rolodex

rolodex = None

def get_rolodex():
    global rolodex
    if rolodex is None:
        rolodex = Rolodex()
    return rolodex


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

version = "3.2"
intents = discord.Intents.all();
intents.message_content = True;
intents.members = True;
playing = discord.Game(name="$harvest once per hour!")
client = discord.Client(intents=intents,activity = playing);
command_handler.Deprecated.client = client
RUN_AUTO_COMMANDS = True;


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

# Discord can emit ready again after reconnecting; keep initialization repeatable.
@client.event
async def on_ready():
    print("All systems go!");
    # Repeated ready events reconcile cached members without duplicating history.
    # Absence from a cache is not proof that someone left.
    for guild in client.guilds:
        for member in guild.members:
            get_rolodex().observe_member(member)
    if not manage_timed_commands.is_running():
        manage_timed_commands.start();
    if not manage_scheduled_commands.is_running():
        manage_scheduled_commands.start();
    for guild in client.guilds:
        if guild.id == 647883751853916162:
            await guild.get_member(client.user.id).edit(nick=f"Greg");
            print("now")

            farmmas = await guild.fetch_channel(784803565151453214);


        print(f'Logged in as {client.user.name} ({client.user.id})')


    print('Search complete')

@client.event
async def on_message(message):
    global Context, Command, Uncontested, Loop, Scheduled
    if message.content == "$sync" and message.author.id == 355169964027805698:
        sync(custom_types)
        sync(command_handler);
        sync(commands);
        Context = command_handler.Context
        Command = command_handler.Command
        Uncontested = command_handler.Uncontested
        Loop = command_handler.Loop
        Scheduled = command_handler.Scheduled
        command_handler.Deprecated.client = client
        await message.channel.send("Done! Modules synced");

    if message.author.bot:
        return;
    context = Context(message=message);
    neighbor = Neighbor(message.author.id, message.guild.id);

    # if production bot running, don't reply in testing channel
    # if testing bot, don't reply in regular bot channel
    if message.channel.id == CHANNEL_ID_DONT_RESPOND:
        return

    await Command.execute(neighbor, context);
    await Uncontested.execute(context);

@client.event
async def on_raw_reaction_add(reaction):

    # if production bot running, don't reply in testing channel
    # if testing bot, don't reply in regular bot channel
    if reaction.channel_id == CHANNEL_ID_DONT_RESPOND:
        return

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

@client.event
async def on_user_update(before, after):
    if not after.bot:
        get_rolodex().user_updated(before, after)


@client.event
async def on_member_update(before, after):
    get_rolodex().member_updated(before, after)
    if after.bot:
        return 0;

    if after.display_name != before.display_name:
        await commands.set_nick(after, after.guild, True);

    if after.guild.id == 647883751853916162:
        # Automatic family assignment is intentionally disabled; revisit for future seasons.

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
        for role_id in sorted(after_nh_roles - before_nh_roles):
            NH = NH_roles[role_id];
            await joinlist.send(f"{after.display_name} ({after.mention}) has joined {NH}")

        for role_id in sorted(before_nh_roles - after_nh_roles):
            NH = NH_roles[role_id];
            await leavelist.send(f"{after.display_name} ({after.mention}) has left {NH}")

        if len(after_nh_roles) > 0:
            await after.add_roles(after.guild.get_role(1181330910747054211));
        else:
            await after.remove_roles(after.guild.get_role(1181330910747054211))


@client.event
async def on_member_join(member, NH = None):
    get_rolodex().observe_member(member, source="gateway")
    if (member.guild.id != 647883751853916162):
        return 0;

    if NH is None:
        guild = client.get_guild(FF.guild);
        general = await guild.fetch_channel(FF.general_channel); 
        target = await general.send(f"**Welcome to Town, <@{str(member.id)}>!\nWe're happy to see you.**\n\nIf you're looking for a Neighborhood, please let us know! You can learn more about us here: <#648257841064574986>");
        with open("welcome_town.png", 'rb') as file:
            await general.send(file=discord.File(file))
        await general.send("<@&1550347140503568465> we have a visitor! 🥳")


@client.event
async def on_member_remove(member):
    get_rolodex().member_left(member)
    if (member.guild.id != 647883751853916162):
        return 0;

    guild = client.get_guild(FF.guild);
    general = await guild.fetch_channel(FF.general_channel);  
    await general.send(member.name + " has left Town."); 
    with open("leaving_town.png", 'rb') as file:
            await general.send(file=discord.File(file))

@client.event
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
    if not RUN_AUTO_COMMANDS:
        return;
    await Scheduled.execute(client)

@tasks.loop(minutes=5)
async def manage_timed_commands():
    print("here");
    if not RUN_AUTO_COMMANDS:
        return;
    await Loop.execute(client);

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the same directory as this file
load_dotenv(Path(__file__).resolve().parent / ".env")
BOT_TOKEN = os.environ["BOT_TOKEN"] 
CHANNEL_ID_DONT_RESPOND = int(os.environ["CHANNEL_ID_DONT_RESPOND"])
print(f"Don't respond to: {CHANNEL_ID_DONT_RESPOND}")
client.run(BOT_TOKEN, reconnect=True);
