"""Carnival commands and their supporting helpers."""

from .common import *
        

@command_handler.Loop(hours=1)
async def fiftyfifty(client):
    import gspread
    import asyncio
    import time
    from google.oauth2.service_account import Credentials

    # Define scopes and authorize
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    x = gspread.authorize(creds)

    # Open the Google Sheet and get worksheets
    sheet = x.open_by_key("1LMePGWRj5x95Z6xvQvOfsJcjzj3pGqziQHiUNyohb4g")
    worksheet = sheet.worksheet("May 2026");
    
        # --- Get all values from a specific column ---
    column_letter = 'D'  # Change this to the desired column
    column_values = worksheet.col_values(ord(column_letter.upper()) - 64)

    # --- Convert to numbers and sum ---
    total = 0
    for value in column_values:
        try:
            total += float(value)
        except ValueError:
            continue  # Skip cells that don't contain numbers
        
    prev_total = remember("5050Total26");
    
    print(f"New total: {total}\nOld total: {prev_total}");
    
    if not prev_total:
        remember("5050Total26", 300)
        prev_total = 0;
    if not total - prev_total > 250:
        return
    remember("5050Total26", total);

    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(1234185689172807690);
    total = int(total);
    revenue = math.ceil(total / 2);
    prize = math.floor(total / 2);
    await channel.send(f"# New Total!\nThe 50/50 pot has reached {total} BEMs, wow!\n\nThat marks {prize} BEMs for the prize pool.\n<@&1181330910747054211> use <#1234185689172807690> to purchase raffle tickets.");

    
@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def carnival(activator: Neighbor, context: Context):
    from .members import set_nick
    await context.send("```You are now in the Carnival command operations environment. Type `help` if needed, or else get started. Type `exit` to leave the coe.```")
    coe_item = Item("Carnival COE", "coe", time.time() + 3600);
    activator.bestow_item(coe_item);
    await carnival_coe(context)
    await set_nick(await context.guild.fetch_member(activator.ID), context.guild)

    
@command_handler.Uncontested(type="MESSAGE")
async def carnival_coe(context: Context):
    from .members import set_nick
    neighbor = Neighbor(context.author.id, context.guild.id);
    if not neighbor.get_item_of_name("Carnival COE"): 
        return
    if context.content.startswith("$"):
        if len(context.args) > 0:
            cmd = context.args[0]
        else:
            return;
    else:
        cmd = context.tokens[0];
    actions = ["exit", "help", "tickets", "photos", "adjust", "admission"]
    # if cmd in actions:
    #     await context.send(f"`{cmd}`");
    # else:
    #     await context.react("⛔️")
        
    match cmd:
        case "exit":
            await context.send("```Exited coe```");
            neighbor.vacate_item(neighbor.get_item_of_name("Carnival COE"))
            await set_nick(await context.guild.fetch_member(neighbor.ID), context.guild)
        case "help":
            await context.send("```Sounds like you're ready to take admission for Carnival!\nLet's do it in two simple steps. 1. Perform `photos` to get a list of all photos submitted this week and check their validity. 2. Perform `admission` after validating submissions to confirm new tickets AND take admission from each person.\n\nAlso: `tickets`, `tickets @neighbor`, `tickets all`, `adjust @neighbor`, `adjust all`.```",  reply=True)
        case "photos":
            await carnival_photos(neighbor, context)
        case "admission":
            await carnival_admission(neighbor, context)

        
async def carnival_photos(activator: Neighbor, context: Context):
    from .community import get_photos
    messages = await get_photos(activator, context);
    for message in messages:
        link = f"https://discord.com/channels/{context.guild.id}/{message.channel.id}/{message.id}";
        await context.send(f"<@{message.author.id}> has submitted an image: {link}")
    
    await context.send("If you DO NOT WANT one of these linked messages to be counted for a ticket, (i.e. it is not a valid submission) you can either delete the linked message entirely or react to it with a ❌.");
    await context.send("Deleting or reacting to the link above will do nothing. You need to go to the linked message to see it and delete/react.")


async def carnival_admission(neighbor, context):

    import carnival_db as ffc
    
    ffc.init_db("carnival_tickets.db")
    FFC_ROLE_ID = 1342329111359656008
    
    # Check DB against current neighbors
    
    all_members = await context.guild.fetch_members()
    carnival_ids = []
    for member in all_members:
        if FFC_ROLE_ID in [role.id for role in member.roles]:
            carnival_ids.append(member.id)
            
    added_ids, removed_ids = ffc.sync_ids("carnival_tickets.db", carnival_ids);
    
    # Expire any old tickets
    for ffc_id in carnival_ids:
        tickets = ffc.retrieve_tickets("carnival_tickets.db", ffc_id)
        
        expired = int(tickets[0])


@command_handler.Uncontested(type="REACTION")
async def buy_set_two(context: Context):
    if context.message.id != 1386905977487626431:
        return;
    
    if not context.emoji is None:
        await context.message.remove_reaction(context.emoji, context.user);
        
    guild = context.guild;
    user = context.user;
    set_two_purchases = await guild.fetch_channel(1386906153593606256);
    await set_two_purchases.send(user.id);
    set_two_role = guild.get_role(1386907413852065884);
    await user.add_roles(set_two_role);


class Task():
    def __init__(self, guild, channel_ids, first_message_id, points: int, key, name):
        self.guild = guild;
        self.channel_ids = channel_ids;
        self.first_message_id = first_message_id;
        self.points = points;
        self.key = key;
        self.name = name;
        
    async def evaluate(self, ch_msg_ids: list, uid: int): 
        # from datetime import datetime, timezone

        cutoff_utc = datetime(2025, 7, 4, 3, 59, 0, tzinfo=timezone.utc)
        def on_time(message):
            ans = message.created_at <= cutoff_utc
            if not ans:
                print(f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}")
            return ans
        
        # ch_msg_ids = [x for x in ch_msg_ids if on_time(x[1])]
        
        new_lst = [];
        for x in ch_msg_ids:
            if on_time(x[1]):
                new_lst.append(x);
            else:
                break
        ch_msg_ids = new_lst
        
        print("called!")
        ans = await self.key([x[1] for x in ch_msg_ids], uid);
        
        if ans:
            item_type_lookup = {
                "Wheel": "emoji_task",
                "Horse": "emoji_task",
                "Juggler": "emoji_task",
                "Role": "role_task"
            }

            item_type = item_type_lookup.get(self.name)
            if item_type:
                neighbor = Neighbor(uid, 647883751853916162)
                item = Item(self.name, item_type, -1)
                neighbor.bestow_item(item)
                print(f"GIVEN!!!!! {item.name}")
        return ans;
    
    def get_channels_and_startmsgs(self, guild):
        cur_channel_ids = list(self.channel_ids) if isinstance(self.channel_ids, tuple) else [self.channel_ids]
        cur_msg_ids = list(self.first_message_id) if isinstance(self.first_message_id, tuple) else [self.first_message_id]
        return list(zip(cur_channel_ids, cur_msg_ids))

                
async def task_just1image(msg_list, uid):
    print(f"Evaluating {len(msg_list)} messages")
    for msg in msg_list:
        has_image = (
            any(att.content_type and att.content_type.startswith("image/") for att in msg.attachments) or
            any(embed.type == "image" or (embed.image and embed.image.url) for embed in msg.embeds)
        )
        if has_image:
            return True;
    return False;


async def task_2msg_300chars(msg_list, uid):
    print(f"Evaluating {len(msg_list)} messages")
    msg_count = 0;
    char_count = 0;
    for msg in msg_list:
        msg_count += 1;
        char_count += len(msg.content)
        if msg_count >= 2 and char_count >= 300:
            return True;
    return False;


async def task_3msgs(msg_list, uid):
    print(f"Evaluating {len(msg_list)} messages for task_3msgs")
    count = 0;
    for msg in msg_list:
        has_image = (
            any(att.content_type and att.content_type.startswith("image/") for att in msg.attachments) or
            any(embed.type == "image" or (embed.image and embed.image.url) for embed in msg.embeds)
        )
        if msg.author.id == 1211781489931452447 and str(uid) in msg.content:
            count += 1;
        elif has_image and msg.author.id == uid:
            count += 1;
        elif "Wordle" in msg.content and "/6" in msg.content and msg.author.id == uid:
            count += 1;
        if count >= 3:
            return True;
        print(count);
    return False;


async def bought_second_set(user_id, context):
    chan = await context.guild.fetch_channel(1386906153593606256)
    async for msg in chan.history(oldest_first=True, limit=None):
        if str(user_id) in msg.content:
            return True;
    return False;

        
async def bought_second_set(user_id, context):
    chan = await context.guild.fetch_channel(1386906153593606256)
    async for msg in chan.history(oldest_first=True, limit=None):
        if str(user_id) in msg.content:
            return True;
    return False;

        
async def count_tickets2(user_id, context):
    channels = [
        1387495669391954045, 1346890558869606400, 784150346397253682,
        (1386912469590605875, 1386912514478182450, 1386912565246038127,
        1386912639245881374, 1386912706296156301, 1386912757093503046),
        1386908794772000798, 1349747717580263524
        ]
    
    points = [3, 4, 3, 5, 2, 3]
    
    message_ids = [
        1387495676086059129, 1386916878273875979, 1385993874110943263,
        (1386912471910055987, 1386912517040635925, 1386912567582003363,
         1386912639245881374, 1386912708699488256, 1386912757093503046),
        1386908797666332727, 1350039683220115559
    ]   
    
    
    total_score = 0
    task_completion = [0] * len(channels)

    for i, chan_spec in enumerate(channels):
        if isinstance(chan_spec, tuple):
            cur_channels = [await context.guild.fetch_channel(cid) for cid in chan_spec]
            cur_msg_ids = message_ids[i]
        else:
            cur_channels = [await context.guild.fetch_channel(chan_spec)]
            cur_msg_ids = [message_ids[i]]

        task_completed = False

        for chan, msg_id in zip(cur_channels, cur_msg_ids):
            try:
                start_msg = await chan.fetch_message(msg_id)
            except Exception as e:
                print(f"Failed to fetch message {msg_id} in channel {chan.id}: {e}")
                continue

            try:
                # Special case: character-count channel
                if chan.id == 1179484606370689074:
                    total_chars = 0
                    message_count = 0
                    async for msg in chan.history(after=start_msg, oldest_first=True, limit=None):
                        if msg.author.id != user_id:
                            continue
                        total_chars += len(msg.content)
                        message_count += 1
                        print(f"[Char Task] +{len(msg.content)} chars from message — running total: {total_chars} chars in {message_count} messages")
                        if total_chars >= 300 and message_count >= 2:
                            task_completed = True
                            break

                # Standard case: image
                else:
                    async for msg in chan.history(after=start_msg, oldest_first=True, limit=None):
                        if msg.author.id != user_id:
                            continue

                        has_image = (
                            any(att.content_type and att.content_type.startswith("image/") for att in msg.attachments) or
                            any(embed.type == "image" or (embed.image and embed.image.url) for embed in msg.embeds)
                        )

                        if has_image:
                            dnc = False;
                            for reaction in msg.reactions:
                                if str(reaction.emoji) == "👻":
                                    dnc = True;
                            if dnc:
                                continue;
                            print(f"[Image Task] Image found from user {user_id} in channel {chan.id}")
                            task_completed = True
                            break

            except Exception as e:
                print(f"Error scanning channel {chan.id}: {e}")
                continue

            if task_completed:
                break  # No need to continue scanning fallback channels in this group

        if task_completed:
            total_score += points[i]
            task_completion[i] = 1

    return total_score, task_completion

            
async def count_tickets(user_id, context):
    channels = [
        654303369464119316, 1229456519712477184, 1071930737651097720,
        1384657180078244051, 1179484606370689074, 1384657963091755208,
        1148267353696653362, (1074453826834280508, 855938321497718814),
        1218621723591577800
    ]
    points = [5, 2, 2, 2, 4, 4, 3, 5, 3]
    message_ids = [
        1379257452607963258, 1382085102040911964, 1384609189262921929,
        1384657182318137374, 1382086425020993577, 1384657965998669920,
        1384568223227449468, (1259036334891208724, 1383965802281046168),
        1381083286704492544
    ]

    total_score = 0
    task_completion = [0] * len(channels)

    for i, chan_spec in enumerate(channels):
        if isinstance(chan_spec, tuple):
            cur_channels = [await context.guild.fetch_channel(cid) for cid in chan_spec]
            cur_msg_ids = message_ids[i]
        else:
            cur_channels = [await context.guild.fetch_channel(chan_spec)]
            cur_msg_ids = [message_ids[i]]

        task_completed = False

        for chan, msg_id in zip(cur_channels, cur_msg_ids):
            try:
                start_msg = await chan.fetch_message(msg_id)
            except Exception as e:
                print(f"Failed to fetch message {msg_id} in channel {chan.id}: {e}")
                continue

            try:
                # Special case: character-count channel
                if chan.id == 1179484606370689074:
                    total_chars = 0
                    message_count = 0
                    async for msg in chan.history(after=start_msg, oldest_first=True, limit=None):
                        if msg.author.id != user_id:
                            continue
                        total_chars += len(msg.content)
                        message_count += 1
                        print(f"[Char Task] +{len(msg.content)} chars from message — running total: {total_chars} chars in {message_count} messages")
                        if total_chars >= 300 and message_count >= 2:
                            task_completed = True
                            break

                # Standard case: image
                else:
                    async for msg in chan.history(after=start_msg, oldest_first=True, limit=None):
                        if msg.author.id != user_id:
                            continue

                        has_image = (
                            any(att.content_type and att.content_type.startswith("image/") for att in msg.attachments) or
                            any(embed.type == "image" or (embed.image and embed.image.url) for embed in msg.embeds)
                        )

                        if has_image:
                            dnc = False;
                            for reaction in msg.reactions:
                                if str(reaction.emoji) == "👻":
                                    dnc = True;
                            if dnc:
                                continue;
                            print(f"[Image Task] Image found from user {user_id} in channel {chan.id}")
                            task_completed = True
                            break

            except Exception as e:
                print(f"Error scanning channel {chan.id}: {e}")
                continue

            if task_completed:
                break  # No need to continue scanning fallback channels in this group

        if task_completed:
            total_score += points[i]
            task_completion[i] = 1

    return total_score, task_completion

