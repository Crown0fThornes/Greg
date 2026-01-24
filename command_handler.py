import asyncio
import datetime
import difflib
import queue
import threading
import time
import traceback
import discord
from enum import Enum
import random
import discord
import commands as commands
from custom_types import Neighbor
from importlib import reload as sync
import inspect
from id_bundle import FF
from phoenix_bundle import PHOENIX
import shlex
import re

"""
Greg 3.0!
Author: Lincoln Edsall

This script serves as the overhead controller for the client, aka Greg. 
It sets up the intents, listens for events, and prepares the command file.

This script was combined with command_handler.py, where commands are wrapped, and run based off listener events.

persistent_types.py defines types such as Neighbor, Item, and Expectation
	which Greg relies on to allow information to persist
commands.py is where all commands are defined
id_bundle.py provides a list of role, channel, and other relevant ids for the FF discord server
"""

# meta data and intents _____
version = "3.0";
maintenance = True;
# ___________________________

class CommandArgsError(ValueError, TypeError):
    pass

class PardonOurDustError(ValueError):
    pass

class UncaughtResponseError(ValueError):
    pass;

# The AccessType enum creates specific levels of access for different members of a server. 
class AccessType(Enum):
    PUBLIC = 0;          # public commands can be accessed by anyone
    PRIVATE = 1;         # private commands can be accessed by anyone with a neighbors role
    PRIVILEGED = 2;      # privileged commands can be accessed by anyone with a council role
    DEVELOPER = 3;       # developer commands can be accessed by admin

active_expectations = [];

def safe_tokenize(text: str):
    try:
        lexer = shlex.shlex(text, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ''
        return list(lexer)
    except ValueError:
        # Fallback: rudimentary split, keeping quoted groups if closed
        # Also tolerate stuff like it's, don't treat single quote as quote unless paired
        tokens = re.findall(r'''(?:[^\s"']+|"(?:\\.|[^"])*"|'(?:\\.|[^'])*')+''', text)
        return [t.strip('"').strip("'") for t in tokens]

# A context object is constructed when a message is sent or reaction is added in the server. 
#   The context object creates an intuitive way of accessing information about an event.
#   Additionally, the .send() and .react() methods allow for a message or reaction respectively
#   to be sent by Greg into the appropriate context. 
#   This is a mandatory parameter for every textual command created using the Command class
class Context:
    def __init__(self, message: discord.message = None, reaction: discord.reaction = None, user = None):
        if not message is None:
            self.type = "MESSAGE";
            self.guild = message.guild;
            self.channel = message.channel;
            self.author = message.author;
            self.message = message;
            self.content = message.content;
            self.author_id = message.author.id;
            self.author_role_ids = [role.id for role in message.author.roles];
            
            self.content = self.content.strip()
            self.tokens = safe_tokenize(self.content)
            self.args = self.tokens[1:] if len(self.tokens) > 1 else [];
            
            if self.guild.id == FF.guild:
                self.ID_bundle = FF;
            elif self.guild.id == PHOENIX.guild:
                self.ID_bundle = PHOENIX;
            self.set_access_type()
        elif not reaction is None:
            #code here
            self.type = "REACTION";
            self.message = reaction.message;
            self.guild = self.message.guild;
            self.channel = self.message.channel;
            self.author = reaction.message.author;
            self.reaction = reaction;
            self.emoji = reaction.emoji;
            self.author_id = self.message.author.id;
            self.user = user;
            self.author_role_ids = [role.id for role in self.message.author.roles];
            if self.guild.id == FF.guild:
                self.ID_bundle = FF;
            elif self.guild.id == PHOENIX.guild:
                self.ID_bundle = PHOENIX;
            self.set_access_type()
        else:
            self.type = None;
            self.message = None;
            self.guild = None;
            self.channel = None;
            self.author = None;
            self.emoji = None;
            self.author_id = None;
            self.user = None;
            self.author_role_ids = None;
            self.reaction = None;
    
    def __str__(self):
        return f"{self.author.display_name} said: {self.content}";
    def __eq__(self, other):
        if isinstance(other, Context):
            same = True;
            if self.guild.id != other.guild.id:
                same = False;
            if self.channel.id != other.channel.id:
                same = False;
            return same;
        return False
    def set_access_type(self):
        print(FF.leaders_role);
        if self.author_id == 355169964027805698:
            self.access_type = AccessType.DEVELOPER;
        elif FF.leaders_role in self.author_role_ids or self.author_id == 355169964027805698:
            self.access_type = AccessType.PRIVILEGED;
        elif set([FF.p_neighbors_role, FF.neighbors_role, FF.j_neighbors_role, FF.g_neighbors_role, FF.r_neighbors_role, 1334660124639236267, 1342329111359656008, 1101303009641779280]).intersection(set(self.author_role_ids)):
            self.access_type = AccessType.PRIVATE;
        else:
            self.access_type = AccessType.PUBLIC;
    async def send(self, text: str = None, reply: bool = False, ephemeral: bool = False, *args, **kwargs):
        msg = "";
        if not text is None:
            if reply:
                while text:
                    msg = await self.message.reply(text[:1999])
                    text = text[1999:]
            else:
                while text:
                    msg = await self.channel.send(text[:1999])
                    text = text[1999:]
        else:
            msg = await self.channel.send(*args, **kwargs);
        return msg;
    async def edit(self, text: str):
        await self.message.edit(content=text);
    async def react(self, emoji: str):
        await self.message.add_reaction(emoji);
    async def fetch_channel(self, channel_name):
        await self.guild.fetch_channel(int(self.ID_bundle.__members__[channel_name].value));
    async def fetch_role(self, role_name):
        await self.guild.fetch_role(int(self.ID_bundle.__members__[role_name].value));

# Regular commands, which can be called by anyone with the correct access type using "$" + command name
#   Commands are registered using the Command(access_type, desc) decorator
class Command:
    available_commands = {};
    prefix = None;
    def __init__(self, access_type: AccessType, desc: str = None, priority = 10, generic = False, accessible = False, active=True):
        self.access_type = access_type;
        self.desc = desc;
        self.priority = priority;
        self.generic = generic;
        self.accessible = accessible
        self.active = active
        
    def __call__(self, func):
        self.name = func.__name__;
        Command.available_commands[func.__name__] = self;

        async def wrapper(activator: Neighbor, context: Context, *args, **kwargs):
            if context.access_type.value < self.access_type.value:
                await context.send(f"You do not meet the necessary AccessType for command `{self.name}`: `{self.access_type.name}`.");
                return;
            try:   
                await func(activator, context, *args, **kwargs);
            except PardonOurDustError as e:
                traceback.print_exc();
                await context.send(f"`{type(e).__name__}` <:devastating:1172617060208087100> This command is currently down for maintenance. Sorry!\n\n{str(e)}");
            except CommandArgsError as e:
                traceback.print_exc();
                await context.send(f"`{type(e).__name__}` <:devastating:1172617060208087100> {str(e)}");
            except Exception as e:
                traceback.print_exc();
                res = f"{type(e).__name__}: {str(e)}\n";
                res += "\nIf you are so inclined, submit a bug report using $report.\n"
                if context.guild.id == FF.guild:
                    res += "\n<@355169964027805698> ur bot broke fix it\n";
                res += random.choice(["https://tenor.com/view/bruh-be-bruh-beluga-gif-25964074", "https://tenor.com/view/facepalm-really-stressed-mad-angry-gif-16109475", "https://tenor.com/view/yikes-david-rose-david-dan-levy-schitts-creek-gif-20850879", "https://tenor.com/view/disappointed-disappointed-fan-seriously-what-are-you-doing-judging-you-gif-17485289"])
                await context.send(res);        
        self.run = wrapper;
        return wrapper
    
    async def execute(activator: Neighbor, context: Context, *args):
        if Command.prefix is None:
            raise ValueError("Prefix not set. Please define with Command.set_prefix(new: str)") 
        if context.content.startswith(Command.prefix):
            target = context.content.split(" ")[0][1:];
            for name, command in Command.available_commands.items():
                if name == target:
                    print(f"The guild id is: {context.guild.id}");
                    if context.guild.id != 647883751853916162 and not command.generic:
                        await context.send("Whoops! That command is not available in this server yet.")
                        continue;
                    await command.run(activator, context, *args);
                    break;
            else:
                best_matches = difflib.get_close_matches(target, Command.available_commands.keys(), n=1, cutoff=0.75)
                if best_matches:
                    if context.guild.id != 647883751853916162:
                        if not Command.available_commands[best_matches[0]].generic:
                            return
                    await Command.available_commands[best_matches[0]].run(activator, context, *args)
    def set_prefix(new: str):
        Command.prefix = new;
    def generate_help_str(target: str = None, FF = True):
        res = "";
        if not target is None:
            for name, command in Command.available_commands.items():
                if name == target:
                    res += f"**{Command.prefix}{name}** | *{command.access_type.name}* | {command.desc}"
            if res == "":
                raise CommandArgsError("`target` is not a valid command!")
        else:
            res += "**The following commands are available:**\n";
            res += "A command can be called by typing `" + Command.prefix + "` + `command name` + `argument(s), if any`\n";
            res += "For example, `$help` is a command call with no arguments that generates a list of available commands, while `$help help` is a command call with the additional argument `help` that generates a description of the 'help' command.\n\n"

            for name, command in Command.available_commands.items():
                if FF or command.generic:
                    res += f"> **{Command.prefix}{name}** | *{command.access_type.name}*\n";
        return res;
    
# Uncontested commands are not like regular commands. These commands are run every time someone sends
#   a message, adds a reaction, etc. This is useful, for example, when you need to incrememnt someone's
#   server xp every time they send a message. This means the bot should look for all messages sent,
#   instead of any particular command call
class Uncontested:
    available_commands = {};
    def __init__(self, desc: str = None, type: str = "MESSAGE", priority = 10, generic = False):
        self.type = type;
        self.desc = desc;
        self.priority = priority;
        self.generic = generic;
    def __call__(self, func):
        self.name = func.__name__;
        Uncontested.available_commands[func.__name__] = self;

        async def wrapper(context: Context):
            try:
                await func(context);
            except Exception as e:
                traceback.print_exc();
                # res = "Runtime error:\n";
                # res += str(e);
                # if context.guild.id == FF.guild:
                #     res += "\n<@355169964027805698> ur bot broke fix it\n";
                # else:
                #     res += "\nIf you are so inclined, submit a bug report using $report.\n"
                # res += random.choice(["https://tenor.com/view/bruh-be-bruh-beluga-gif-25964074", "https://tenor.com/view/facepalm-really-stressed-mad-angry-gif-16109475", "https://tenor.com/view/yikes-david-rose-david-dan-levy-schitts-creek-gif-20850879", "https://tenor.com/view/disappointed-disappointed-fan-seriously-what-are-you-doing-judging-you-gif-17485289"])
                # await context.send(res);
            
        self.run = wrapper;
        return wrapper
    async def execute(context: Context):
        for name, command in Uncontested.available_commands.items():
            if command.type == context.type:
                if context.guild.id != 647883751853916162 and not command.generic:
                        continue;
                await command.run(context);
                await asyncio.sleep(.1);
    def set_prefix(new: str):
        Command.prefix = new;
    def generate_help_str(target: str = None):
        res = "";
        if not target is None:
            for name, command in Command.available_commands.items():
                if name == target:
                    res += f"**{Command.prefix}{name}** | *{command.access_type.name}* | {command.desc}"
        else:
            res += "**The following commands are available:**\n";
            res += "A command can be called by typing `" + Command.prefix + "` + `command name` + `argument(s), if any`\n";
            res += "For example, `$help` is a command call with no arguments that generates a list of available commands, while `$help help` is a command call with the additional argument `help` that generates a description of the 'help' command.\n\n"

            for name, command in Command.available_commands.items():
                res += f"> **{Command.prefix}{name}**\t| *{command.access_type.name}*\n";
        return res;

# InLine commands are also not like regular commands. InLine provides more customizable commands for
#   leaders. For example, a InLine command might be used to set up or edit reminders (bot messages sent on regular intervals)
#   InLine executes automatically in specific channels with messages that begin with the prefix "%"
#   The InLine can also be ented/exited in any channel with $cmdl enter and $cmd exit
#   All InLine commands require PRIVILEGED access.
#   Example usage:
#   $cmd enter
#   % cmd_name arg_name1=arg_val1 arg_name2=arg_val2
#   $cmd exit
#
#   These commands are useful for commands that may require communication back and forth with the caller.
class InLine: 
    available_commands = {};
    def __init__(self, desc: str = None, type: str = "MESSAGE"):
        self.type = type;
        self.desc = desc;
    def __call__(self, func):
        self.name = func.__name__;
        InLine.available_commands[func.__name__] = self;

        async def wrapper(activator: Neighbor, context: Context, *args, **kwargs):
            if context.access_type.value < AccessType.PRIVILEGED:
                await context.send(f"You do not meet the necessary AccessType for command `{self.name}`: `{self.access_type.name}`.");
                return;
            try:   
                await func(activator, context, *args, **kwargs);
            except PardonOurDustError as e:
                traceback.print_exc();
                await context.send(f"`{type(e).__name__}` <:devastating:1172617060208087100> This command is currently down for maintenance. Sorry!");
            except CommandArgsError as e:
                traceback.print_exc();
                await context.send(f"`{type(e).__name__}` <:devastating:1172617060208087100> {str(e)}");
            except Exception as e:
                traceback.print_exc();
                res = f"{type(e).__name__}: {str(e)}\n";
                res += "\nIf you are so inclined, submit a bug report using $report.\n"
                if context.guild.id == FF.guild:
                    res += "\n<@355169964027805698> ur bot broke fix it\n";
                res += random.choice(["https://tenor.com/view/bruh-be-bruh-beluga-gif-25964074", "https://tenor.com/view/facepalm-really-stressed-mad-angry-gif-16109475", "https://tenor.com/view/yikes-david-rose-david-dan-levy-schitts-creek-gif-20850879", "https://tenor.com/view/disappointed-disappointed-fan-seriously-what-are-you-doing-judging-you-gif-17485289"])
                await context.send(res);        
        self.run = wrapper;
        return wrapper
    
    async def execute(activator: Neighbor, context: Context, *args):
        if context.content.startswith(Command.prefix):
            target = context.content.split(" ")[0][1:];
            for name, command in Command.available_commands.items():
                if name == target:
                    print(f"The guild id is: {context.guild.id}");
                    if context.guild.id != 647883751853916162 and not command.generic:
                        await context.send("Whoops! That command is not available in this server yet.")
                        continue;
                    await command.run(activator, context, *args);
                    break;
            else:
                best_matches = difflib.get_close_matches(target, Command.available_commands.keys(), n=1, cutoff=0.75)
                if best_matches:
                    if context.guild.id != 647883751853916162:
                        if not Command.available_commands[best_matches[0]].generic:
                            return
                    await Command.available_commands[best_matches[0]].run(activator, context, *args)
    def set_prefix(new: str):
        Command.prefix = new;
    def generate_help_str(target: str = None, FF = True):
        res = "";
        if not target is None:
            for name, command in Command.available_commands.items():
                if name == target:
                    res += f"**{Command.prefix}{name}** | *{command.access_type.name}* | {command.desc}"
            if res == "":
                raise CommandArgsError("`target` is not a valid command!")
        else:
            res += "**The following commands are available:**\n";
            res += "A command can be called by typing `" + Command.prefix + "` + `command name` + `argument(s), if any`\n";
            res += "For example, `$help` is a command call with no arguments that generates a list of available commands, while `$help help` is a command call with the additional argument `help` that generates a description of the 'help' command.\n\n"

            for name, command in Command.available_commands.items():
                if FF or command.generic:
                    res += f"> **{Command.prefix}{name}** | *{command.access_type.name}*\n";
        return res;

        

# Some maitenance and management duties need to be performed on a time interval, instead of in response
#   to a user action. For example, a loop command may run every 10 minutes, or every 24 hours.
#   Notably, Greg only checks to run these loop commands every 5 minutes, so this is the minimum loop time.
#   Again, since Greg only runs these once every 5 minutes, setting a loop to run every x minutes will be most accurate
#   if x is a multiple of 5.
class Loop:
    available_commands = {};

    def __init__(self, minutes: int = None, hours: int = None, days: int = None, desc: str = "", priority = 10):
        total = 0;
        if not minutes is None:
            total += minutes * 60;
        if not hours is None:
            total += hours * 60 * 60;

        self.total = total if days is None else -1;
        self.timer = 0;
        self.last_run_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def __call__(self, func):
        self.name = func.__name__;
        Loop.available_commands[func.__name__] = self;

        async def wrapper(client):
            try:
                await func(client);
            except Exception as e:
                traceback.print_exc();
                
        self.run = wrapper;
        return wrapper
    async def execute(client):
        print("running");
        for name, command in Loop.available_commands.items():
            if command.total > 0: 
                command.timer -= 300;
                print(f"{name}: {command.timer}")
                if command.timer <= 0:
                    await command.run(client);
                    command.timer = command.total;
            else: 
                current_time = datetime.datetime.now()
                if (current_time - command.last_run_time).total_seconds() >= 86400: #86400:
                    await command.run(client)
                    command.last_run_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            await asyncio.sleep(.1);
    

    
class Dev:    
    available_commands = {};
    prefix = None;
    def __init__(self, access_type: AccessType, desc: str = None, priority = 10, generic = False):
        self.access_type = access_type;
        self.desc = desc;
        self.priority = priority;
        self.generic = generic;
    def __call__(self, func):
        
        self.name = func.__name__;
        Command.available_commands[func.__name__] = self;

        async def wrapper(activator: Neighbor, context: Context, *args, **kwargs):
            if activator.ID != 355169964027805698:
                await context.send(f"Command `${self.name}` is currently in developer-access mode for testing.");
                return;
            try:
                await func(activator, context, *args, **kwargs);
            except Exception as e:
                traceback.print_exc();
                res = f"{type(e).__name__}: {str(e)}\n";
                await context.send(res);
        self.run = wrapper;
        return wrapper
    async def execute(activator: Neighbor, context: Context, *args):
        if Command.prefix is None:
            raise ValueError("Prefix not set. Please define with Command.set_prefix(new: str)") 
        if context.content.startswith(Command.prefix):
            target = context.content.split(" ")[0][1:];
            for name, command in Command.available_commands.items():
                if name == target:
                    await command.run(activator, context, *args);
                    break;
    def set_prefix(new: str):
        Command.prefix = new;
    def generate_help_str(target: str = None, FF = True):
        res = "";
        if not target is None:
            for name, command in Command.available_commands.items():
                if name == target:
                    res += f"**{Command.prefix}{name}** | *{command.access_type.name}* | {command.desc}"
            if res == "":
                raise CommandArgsError("`target` is not a valid command!")
        else:
            res += "**The following commands are available:**\n";
            res += "A command can be called by typing `" + Command.prefix + "` + `command name` + `argument(s), if any`\n";
            res += "For example, `$help` is a command call with no arguments that generates a list of available commands, while `$help help` is a command call with the additional argument `help` that generates a description of the 'help' command.\n\n"

            for name, command in Command.available_commands.items():
                if FF or command.generic:
                    res += f"> **{Command.prefix}{name}** | *{command.access_type.name}*\n";
        return res; 
    
import json   
import os
    
# Scheduled commands are run at a specific time of day, optionally restricted to a
# specific day-of-week (weekly) or day-of-month (monthly).
#
# - If only `time` is provided: runs once per day at that time.
# - If `day_of_week` is provided: runs once per week on that weekday at that time.
#   (Uses Python's datetime.weekday(): Monday=0 ... Sunday=6.)
# - If `day_of_month` is provided: runs once per month on that calendar day at that time.
#
# The scheduler's `execute` method is expected to be called externally every 60 seconds.
# It is robust to minor delays: if the exact scheduled minute is missed, the command
# will still run later that same day as soon as `execute` sees that the scheduled time
# has passed and it has not yet run today. If an entire eligible day passes without
# running (e.g., bot was down all day), that missed run is skipped; there is no catch-up.
#
# To be robust to restarts, run history is persisted to a JSON file keyed by command name.
class Scheduled:
    available_commands = {};
    _state_file = "scheduled_state.json";
    _state_loaded = False;
    _state = {};

    def __init__(self, time, day_of_month: int = None, day_of_week: int = None, desc: str = "", priority: int = 10):
        if day_of_month is not None and day_of_week is not None:
            raise ValueError("Scheduled commands should specify at most one of day_of_month or day_of_week.");

        # Normalize time argument
        if isinstance(time, datetime.time):
            self.time = time;
        elif isinstance(time, str):
            # Expect "HH:MM" or "HH:MM:SS"
            try:
                if len(time.split(":")) == 2:
                    self.time = datetime.datetime.strptime(time, "%H:%M").time();
                else:
                    self.time = datetime.datetime.strptime(time, "%H:%M:%S").time();
            except ValueError:
                raise ValueError("time must be a datetime.time or a string in 'HH:MM' or 'HH:MM:SS' format.");
        else:
            raise TypeError("time must be a datetime.time or a string.");

        self.day_of_month = day_of_month;  # 1–31, if monthly
        self.day_of_week = day_of_week;    # 0=Monday ... 6=Sunday, if weekly
        self.desc = desc;
        self.priority = priority;

        # last_run_date is a datetime.date or None
        self.last_run_date = None;

    @classmethod
    def _ensure_state_loaded(cls):
        if cls._state_loaded:
            return;
        if os.path.exists(cls._state_file):
            try:
                with open(cls._state_file, "r") as f:
                    data = json.load(f);
                if isinstance(data, dict):
                    cls._state = data;
            except Exception:
                traceback.print_exc();
                cls._state = {};
        else:
            cls._state = {};
        cls._state_loaded = True;

    @classmethod
    def _save_state(cls):
        # Best-effort persistence; failures won't crash the scheduler
        try:
            with open(cls._state_file, "w") as f:
                json.dump(cls._state, f);
        except Exception:
            traceback.print_exc();

    def __call__(self, func):
        self.name = func.__name__;
        Scheduled.available_commands[func.__name__] = self;

        # Load persisted state and restore last_run_date for this command, if present
        Scheduled._ensure_state_loaded();
        stored_date_str = Scheduled._state.get(self.name);
        if stored_date_str:
            try:
                self.last_run_date = datetime.date.fromisoformat(stored_date_str);
            except Exception:
                traceback.print_exc();
                self.last_run_date = None;

        async def wrapper(client):
            try:
                await func(client);
            except Exception as e:
                traceback.print_exc();

        self.run = wrapper;
        return wrapper;

    async def execute(client):
        """
        Called externally (e.g., by a task) roughly every 60 seconds.

        For each Scheduled command:
        - Determine whether today is an "eligible" day (daily / weekly / monthly).
        - If eligible, and the current time is at/after the scheduled time,
          and the command has not yet run today, run it once.
        - If a prior eligible day was missed entirely, it is simply skipped,
          because we only ever look at *today* relative to last_run_date.
        """
        Scheduled._ensure_state_loaded();

        now = datetime.datetime.now();
        today = now.date();

        # Insertion order is maintained by dicts in modern Python. You can
        # sort by priority here if you ever want a strict order.
        for name, command in Scheduled.available_commands.items():
            # Skip if already run today
            if command.last_run_date == today:
                continue;

            # Check whether today is an eligible day for this command
            # Monthly: specific calendar day
            if command.day_of_month is not None:
                if today.day != command.day_of_month:
                    continue;

            # Weekly: specific weekday
            if command.day_of_week is not None:
                if now.weekday() != command.day_of_week:
                    continue;

            # Daily: both day_of_month and day_of_week are None, so every day is eligible

            # Compute today's scheduled datetime
            scheduled_dt = datetime.datetime.combine(today, command.time);

            # If we are at or past the scheduled time and haven't run yet today,
            # we should run now. This covers both "on time" and "a bit late".
            if now >= scheduled_dt:
                await command.run(client);
                command.last_run_date = today;

                # Persist updated last_run_date
                Scheduled._state[name] = today.isoformat();
                Scheduled._save_state();

                # Small delay between commands
                await asyncio.sleep(0.1);
    
Command.set_prefix("$");

print(Command.available_commands);