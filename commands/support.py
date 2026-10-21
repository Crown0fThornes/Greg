"""Support commands and their supporting helpers."""

from .common import *

@command_handler.Uncontested("Lets users select their own ticket type.", type="MESSAGE")
async def ticket_type(context: Context):
    if not context.channel.topic == str(context.author.id):
        return
    
    if not len(context.content) > 10:
        return
    
    new_tickets = remember("new_tickets")
    print(new_tickets)
    if context.channel.id in new_tickets:
        new_tickets.remove(context.channel.id)
        remember("new_tickets", new_tickets)
        
    else:
        return
    
    with open("lookups/ticket_types.json", "r") as f:
        ticket_types = json.load(f)
        
    res = "Hi there! Thanks for leaving a message. Do any of the following apply?\n"
    
    for ticket_type in ticket_types:
        res += f"{ticket_type["emoji"]} **{ticket_type["prompt"]}**.\n"
        if "examples" in ticket_type: 
            res += f"-# {ticket_type["examples"]}\n"
    
    res += "In any case, a Council Member will be with you when available."
    
    target_context = Context(await context.send(res));
    
    def key(ctx):
        return ctx.user.id == context.author.id
    
    ResponseRequest(sort_ticket, "ticket_type", type="REACTION",activation_context=context,response_context=target_context,timeout=time.time()+1200,key=key)
    
    for ticket_type in ticket_types:
        await target_context.react(ticket_type["emoji"])
    
    channel = await context.guild.fetch_channel(1468425305881448634)
    ping = FF.leaders_role
    target_context = Context(await channel.send(f"**Unresolved ticket from <@{context.author.id}> here: <#{context.channel.id}>**\n\nReact with ✅ to resolve; 🔄 to force reopen"))
    await target_context.react("✅")
    await target_context.react("🔄")

    open_tickets = remember("open_tickets") or {} #pull open_tickets list from db, or create new list if doesn't exist yet
    open_tickets[target_context.message.id] = context.channel.id #append new item
    remember("open_tickets", open_tickets) #push new list to db

     
async def sort_ticket(activator: Neighbor, context: Context, response: ResponsePackage):
        with open("lookups/ticket_types.json", "r") as f:
            ticket_types = json.load(f)
        
        chosen_type = None;
        for ticket_type in ticket_types:
            if str(response.content) == ticket_type["emoji"]:
                chosen_type = ticket_type
                await response.response_context.message.edit(content=f"Got it, you're interested in {chosen_type["prompt"]}! I'll let the Council know.")
                await response.response_context.message.clear_reactions()
                break
        else:
            return
        
        if chosen_type == "Other":
            return
        
        channel = await context.guild.fetch_channel(chosen_type["channel"])
        ping = chosen_type["ping"]
        target_context = Context(await channel.send(f"**{channel.name} -- unresolved ticket from <@{activator.ID}> here: <#{context.channel.id}>**\n\n<@&{ping}> react with ✅ to resolve; 🔄 to force reopen"))
        await target_context.react("✅")
        await target_context.react("🔄")
        
        open_tickets = remember("open_tickets") or {}
        open_tickets[target_context.message.id] = context.channel.id;
        remember("open_tickets", open_tickets)

        
        
        
@command_handler.Uncontested(type="REACTION", desc="Resolve or reopen support tickets")
async def resolve_tickets(context: Context):
    if not str(context.emoji) == "✅":
        return
    
    open_tickets = remember("open_tickets") or {}
    
    if context.message.id in open_tickets:
        ticket_to_resolve = open_tickets[context.message.id]
        del open_tickets[context.message.id]
    else:
        return
    
    await context.message.delete();
    
    to_delete = []
    for message_id, channel_id in open_tickets.items():
        if channel_id == ticket_to_resolve:
            to_delete.append(message_id)
            
    with open("lookups/ticket_types.json", "r") as f:
        ticket_types = json.load(f)
            
    for message_id in to_delete:
        for ticket_type in ticket_types:
            cur_channel = await context.guild.fetch_channel(ticket_type["channel"])
            try:
                message = await cur_channel.fetch_message(message_id)
                await message.delete()
            except:
                pass
        del open_tickets[message_id]
            
    remember("open_tickets", open_tickets)

    
@command_handler.Uncontested(type="REACTION",desc="Force reopen tickets with reaction")
async def force_reopen_ticket(context: Context):
    if not str(context.emoji) == "🔄":
        return

    
    open_tickets = remember("open_tickets") or {}
    
    if context.message.id in open_tickets:
        ticket_to_reopen = open_tickets[context.message.id]
    else:
        return
    
    channel = await context.guild.fetch_channel(ticket_to_reopen);
    user = await context.guild.fetch_member(int(channel.topic))
    
    await context.message.remove_reaction(context.emoji, user)
    
    from ticket_manager import open_ticket 

    return await open_ticket(None, user, context.guild, FF);

    
    

@command_handler.Loop(hours = 1)
async def publish_heart_react_msg(client):
    
    if remember("message_done"):
        return
    
    guild = client.get_guild(FF.guild)
    channel = await guild.fetch_channel(1218041302998974584)
    target_context = Context(await channel.send("# Valentine's Day Tag Surprise\nTo celebrate Valentine's day, react to this message to add one of any of the available LTO heart emojis to your server nickname <:pink_red_hearts:856202296823250964> <@&1181330910747054211>"))

    remember("heart_message_id", target_context.message.id);
    
    HEARTS = {"🩷","❤️","🧡","💛","💚","🩵","💙","💜","🖤","🩶","🤍","🤎"}
    
    for heart in HEARTS:
        try:
            await target_context.react(heart)
        except:
            pass
        
    remember("message_done", True)

        

@command_handler.Uncontested(type = "REACTION", desc = "Open a Greg Support ticket.")
async def support_ticket_reaction(context: Context):
    if context.message.id == 1033540464441303200:
        await open_ticket(context.emoji, context.user, context.guild);



async def open_ticket(emoji, user, guild):
    
    from ticket_manager import open_ticket 

    return await open_ticket(emoji, user, guild, FF);
    
    return; 
    
    target = user.id;
    name = user.display_name;
    name = name.replace(" ", "-")

    support_channel = await guild.fetch_channel(FF.support_request_channel);
    message = await support_channel.fetch_message(1033540464441303200);
    open_tickets_cat = await guild.fetch_channel(FF.open_tickets_category);
    closed_tickets_cat = await guild.fetch_channel(FF.closed_ticket_category);
    closed_tickets_cat_2 = await guild.fetch_channel(1183992886820343869);
    closed_tickets_cat_3 = await guild.fetch_channel(1201914070027219016);
    closed_tickets_cat_4 = await guild.fetch_channel(1224193594353516605);
    open_tickets = open_tickets_cat.channels;
    closed_tickets = closed_tickets_cat.channels;
    closed_tickets_2 = closed_tickets_cat_2.channels;
    closed_tickets_3 = closed_tickets_cat_3.channels;
    closed_tickets_4 = closed_tickets_cat_4.channels;
    mission_control = await guild.fetch_channel(FF.mission_control_channel);
    cm = guild.get_role(FF.leaders_role);
    rank1 = guild.get_role(1205232195703144488);

    if not emoji is None:
        await message.remove_reaction(emoji, user);

    for ticket in open_tickets:
        if ticket.topic == str(target):
            await ticket.edit(name = name);
            await ticket.send(f"Thank you for reaching out to the Council again. Your private ticket channel is located here <@{user.id}>. Drop a message letting us know what we can help you with!");
            return 0;

    for ticket in closed_tickets:
        if ticket.topic == str(target):
            await ticket.edit(name = name, category = open_tickets_cat);

            await ticket.set_permissions(guild.default_role, read_messages = False);
            await ticket.set_permissions(user, read_messages = True);
            await ticket.set_permissions(rank1, read_messages = True, send_messages = False);

            await ticket.send(f"Thank you for reaching out to the Council. Your private ticket channel has been unarchived for you and is located here <@{user.id}>. Drop a message letting us know what we can help you with!");
            await mission_control.send(f"<@&{FF.leaders_role}> **be advised**: <@{user.id}> has reopened a support ticket at <#{ticket.id}>");
            return 0;

    for ticket in closed_tickets_2:
        if ticket.topic == str(target):
            await ticket.edit(name = name, category = open_tickets_cat);

            await ticket.set_permissions(guild.default_role, read_messages = False);
            await ticket.set_permissions(user, read_messages = True);
            await ticket.set_permissions(rank1, read_messages = True, send_messages = False);

            await ticket.send(f"Thank you for reaching out to the Council. Your private ticket channel has been unarchived for you and is located here <@{user.id}>. Drop a message letting us know what we can help you with!");
            await mission_control.send(f"<@&{FF.leaders_role}> **be advised**: <@{user.id}> has reopened a support ticket at <#{ticket.id}>");
            return 0;

    for ticket in closed_tickets_3:
        if ticket.topic == str(target):
            await ticket.edit(name = name, category = open_tickets_cat);

            await ticket.set_permissions(guild.default_role, read_messages = False);
            await ticket.set_permissions(user, read_messages = True);
            await ticket.set_permissions(rank1, read_messages = True, send_messages = False);

            await ticket.send(f"Thank you for reaching out to the Council. Your private ticket channel has been unarchived for you and is located here <@{user.id}>. Drop a message letting us know what we can help you with!" );
            await mission_control.send(f"<@&{FF.leaders_role}> **be advised**: <@{user.id}> has reopened a support ticket at <#{ticket.id}>");
            return 0;

    for ticket in closed_tickets_4:
        if ticket.topic == str(target):
            await ticket.edit(name = name, category = open_tickets_cat);

            await ticket.set_permissions(guild.default_role, read_messages = False);
            await ticket.set_permissions(user, read_messages = True);
            await ticket.set_permissions(rank1, read_messages = True, send_messages = False);

            await ticket.send(f"Thank you for reaching out to the Council. Your private ticket channel has been unarchived for you and is located here <@{user.id}>. Drop a message letting us know what we can help you with!" );
            await mission_control.send(f"<@&{FF.leaders_role}> **be advised**: <@{user.id}> has reopened a support ticket at <#{ticket.id}>");
            return 0;

    ticket = await message.guild.create_text_channel(name = name, category = open_tickets_cat, topic = target);
    await ticket.set_permissions(guild.default_role, read_messages = False);
    await ticket.set_permissions(user, read_messages = True);
    await ticket.set_permissions(rank1, read_messages = True, send_messages = False);
    await ticket.send(f"Thank you for reaching out to the Council via Greg for the first time! Your private ticket channel is located here <@{user.id}>. Drop a message letting us know what we can help you with!");
    await mission_control.send(f"<@&{FF.leaders_role}> **be advised**: <@{user.id}> has opened a new support ticket at <#{ticket.id}>");


@command_handler.Loop(hours = 10, desc = "Transcriptifies old support tickets") 
async def transcript_support(client):
    guild = client.get_guild(647883751853916162);

    closed_tickets_cat_id = FF.closed_ticket_category
    closed_tickets_cat_2_id = (1183992886820343869);
    closed_tickets_cat_3_id = (1201914070027219016);
    closed_tickets_cat_4_id = (1224193594353516605);

    guild = client.get_guild(FF.guild);

    category = discord.utils.get(guild.categories, id=closed_tickets_cat_id);
    category1 = discord.utils.get(guild.categories, id=closed_tickets_cat_2_id);
    category2 = discord.utils.get(guild.categories, id=closed_tickets_cat_3_id);
    category3 = discord.utils.get(guild.categories, id=closed_tickets_cat_4_id);
    
    for channel in category.channels:
        if isinstance(channel, discord.TextChannel):
            last = [message async for message in channel.history(limit=1)][0];
            if last.created_at.timestamp() + 15770000 < time.time():
                await transcript(channel.id, guild)
                await channel.delete();
                
    for channel in category1.channels:
        if isinstance(channel, discord.TextChannel):
            last = [message async for message in channel.history(limit=1)][0];
            if last.created_at.timestamp() + 15770000 < time.time():
                await transcript(channel.id, guild)
                await channel.delete();
                
    for channel in category2.channels:
        if isinstance(channel, discord.TextChannel):
            last = [message async for message in channel.history(limit=1)][0];
            if last.created_at.timestamp() + 15770000 < time.time():
                await transcript(channel.id, guild)
                await channel.delete();

    for channel in category3.channels:
        if isinstance(channel, discord.TextChannel):
            last = [message async for message in channel.history(limit=1)][0];
            if last.created_at.timestamp() + 15770000 < time.time():
                await transcript(channel.id, guild)
                await channel.delete();

            
    
async def transcript(channel_id, guild):
    origin_channel = await guild.fetch_channel(channel_id)

    messages = []
    # Fetch messages from the channel
    async for message in origin_channel.history(limit=None):
        # Format each message and append to the list
        messages.append(f"{message.created_at} - {message.author.display_name}: {message.clean_content}")

    # Save messages to a .txt file
    transcript_file_name = f"transcript_of_{origin_channel.name}.txt"
    with open(transcript_file_name, 'w', encoding='utf-8') as file:
        file.write("\n".join(messages))

    # Send the file to the target channel
    target_channel = await guild.fetch_channel(1033544493728809000)
    if target_channel:
        await target_channel.send(file=discord.File(transcript_file_name))
        await target_channel.send(f"An old Greg support ticket, {origin_channel.name} has been transcribed and deleted (6 months+ no activity).")
        await target_channel.send(f"ID: {origin_channel.topic}");



@command_handler.Loop(hours = 6, desc = "Archive unused support channels") 
async def archive_support_tickets(client):

    category_id = FF.closed_ticket_category

    guild = client.get_guild(FF.guild);

    open_tickets_cat = await guild.fetch_channel(FF.open_tickets_category);
    closed_tickets_cat = await guild.fetch_channel(FF.closed_ticket_category);
    closed_tickets_cat_2 = await guild.fetch_channel(1183992886820343869);
    closed_tickets_cat_3 = await guild.fetch_channel(1201914070027219016);
    closed_tickets_cat_4 = await guild.fetch_channel(1224193594353516605);
    
    for category in [open_tickets_cat, closed_tickets_cat, closed_tickets_cat_2, closed_tickets_cat_3, closed_tickets_cat_4]:
        for channel in category.channels:
            if isinstance(channel, discord.TextChannel):
                try:
                    user_id = int(channel.topic)
                except:
                    continue;
                try:
                    await guild.fetch_member(user_id)
                except:
                    print(f'User not found for channel {channel.name}, deleting...')
                    await transcript(channel.id, guild)
                    await channel.delete()
    else:
        print(f'Category with ID {category_id} not found in the guild.')


    support_channel = await guild.fetch_channel(FF.support_request_channel);
    message = await support_channel.fetch_message(1033540464441303200);
    open_tickets_cat = await guild.fetch_channel(FF.open_tickets_category);
    closed_tickets_cat = await guild.fetch_channel(FF.closed_ticket_category);
    closed_tickets_cat_2 = await guild.fetch_channel(1183992886820343869);
    closed_tickets_cat_3 = await guild.fetch_channel(1201914070027219016);
    closed_tickets_cat_4 = await guild.fetch_channel(1224193594353516605);
    open_tickets = open_tickets_cat.channels;
    closed_tickets = closed_tickets_cat.channels;
    if len(closed_tickets) > 49:
        closed_tickets = closed_tickets_cat_2.channels;
        closed_tickets_cat = closed_tickets_cat;
    mission_control = await guild.fetch_channel(FF.mission_control_channel);
    cm = guild.get_role(FF.leaders_role);

    for ticket in open_tickets:
        if ticket.id == 1033544493728809000:
            continue;
        try:
            user = await guild.fetch_member(int(ticket.topic));
        except:
            try:
                await ticket.edit(category=closed_tickets_cat);
            except:
                try:
                    await ticket.edit(category=closed_tickets_cat_2);
                except:
                    try:
                        await ticket.edit(category=closed_tickets_cat_3);
                    except:
                        await ticket.edit(category=closed_tickets_cat_4);
            await ticket.set_permissions(user, read_messages = False);
        last = [message async for message in ticket.history(limit=1)][0];
        if last.content.lower() == "keep":
            continue;
        
        # Finish
        # async for message in mission_control.history(oldest_first=False, limit=None):
        #     if 
        
        if last.created_at.timestamp() + (2*86400) < time.time():
            try:
                await ticket.edit(category=closed_tickets_cat);
            except:
                try:
                    await ticket.edit(category=closed_tickets_cat_2);
                except:
                    try:
                        await ticket.edit(category=closed_tickets_cat_3);
                    except:
                        await ticket.edit(category=closed_tickets_cat_4);
            await ticket.set_permissions(user, read_messages = False);
            rank1 = guild.get_role(1205232195703144488);
            await ticket.set_permissions(rank1, read_messages = False);
            await ticket.send("This ticket has been archived. Neighbor will not see messages sent here until it is unarchived.\nThis ticket will be transcribed & deleted after 6 months of inactivity or upon the Neighbor leaving the server.");
            guild = client.get_guild(FF.guild)  # Replace with your guild/server ID
            mission_control = await guild.fetch_channel(1033544493728809000);
            await mission_control.send(f"A ticket from <@{user.id}> has been auto-archived: <#{ticket.id}>");


@command_handler.Command(AccessType.PRIVATE, desc = "Request a new feature. For example, `$request 10000xp for all neighbors` (don't actually say this).", generic = True)
async def request(activator: Neighbor, context: Context):
    if not len(context.args) > 0:
        raise CommandArgsError("You didn't request anything, silly!\nType `$request` followed by the feature you would like to request.");
    with open("data/requests.txt", "a") as fRequests:
        fRequests.write(context.author.display_name);
        fRequests.write(context.content[9:]);


@command_handler.Command(AccessType.PRIVATE, desc = "Report an issue. Please be detailed. For example, `$report When I bought the strawberry tag in the RSS, it said I don't have enough levels even though I do.`.", generic = True)
async def report(activator: Neighbor, context: Context):
    if not len(context.args) > 0:
        raise CommandArgsError("You didn't report anything, silly!\nType `$report` followed by the issue you would like to report. Send a message like this: `$report wordle gives an error when I type a 6 letter word`");
    await context.send(f'Your report has been logged: "{" ".join(context.args)}"');
    with open("data/reports.txt", "a") as fRequests:
        fRequests.write(context.author.display_name);
        fRequests.write("\n")
        fRequests.write(context.content[8:]);
        fRequests.write("\n")


@command_handler.Command(AccessType.PRIVILEGED, desc = "Opens a support ticket with a specific person.")
async def chat(activator: Neighbor, context: Context):
    if not len(context.args) > 0:
        raise CommandArgsError("`$chat` takes one argument: who to open a chat room with");
    try:
        id = parse_mention(context.args[0]);
    except ValueError:
        raise CommandArgsError("`$chat` please tag the person you would like to create a chat room for")

    user = await context.guild.fetch_member(id);

    await open_ticket(None, user, context.guild);

