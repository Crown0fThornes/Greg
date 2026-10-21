"""Retired commands: manual developer invocation only; never scheduled or listened to."""

from .common import *


# @command_handler.Uncontested(type="MESSAGE", desc="Updates cross country style scoring")
@command_handler.Deprecated(kind="Uncontested", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def update_xc_scoring(context: Context):
    from .families import get_family_from_user, get_neighborhood_from_user
    from .members import clean_nick
    if context.channel.id != 1203772906497380472:
        return;
    if context.author.id == 691338084444274728:
        return;
    
    channel = await context.guild.fetch_channel(1203772906497380472)
    
    import re
    import string
    from typing import Optional

    def first_int_word(s: str) -> Optional[int]:
        for token in s.split():
            # strip common edge punctuation: "(12)," -> "12"
            cleaned = token.strip(string.punctuation)
            if cleaned.isdigit():
                return int(cleaned)
        return None
    
        
    start_message = await channel.fetch_message(1468980801424330897);
    
    results = []
    async for message in channel.history(after=start_message, oldest_first=True, limit=None):
        
        if not get_neighborhood_from_user(message.author):
            continue;
        if get_neighborhood_from_user(message.author) == 'FFR':
            continue;
        
        if num_trucks := first_int_word(message.content):
            family = get_family_from_user(message.author)["name"]
            result = {
                "score": num_trucks,
                "family": family,
                "user": message.author
            }
            results.append(result)
            
            if message.id != context.message.id and message.author.id == context.author.id:
                target = await context.send("You've submitted previously! Be sure to delete your original submission unless it was for a different farm. This may affect leaderboard accuracy until the next time scores are updated..", reply=True)
                time.sleep(8)
                await target.delete();
            
    results.sort(key=lambda x: x["score"],reverse=True)
    
    family_scores = {
        "Bunny": [],
        "Cheetah": [],
        "Donkey": [],
        "Fox": [],
        "Giraffe": [],
        "Hippo": [],
        "Penguin": [],
    }
    family_emojis = {
        "Bunny": "🐰",
        "Cheetah": "🐆",
        "Donkey": "🫏",
        "Fox": "🦊",
        "Giraffe": "🦒",
        "Hippo": "🦛",
        "Penguin": "🐧",
    }
    emoji_placements = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }
    all_placements = []
    all_placements.append("# Placements\n")
    nxt = ""
    for i, result in enumerate(results, start=1):
        cur_family = result["family"]
        placement = emoji_placements[i] if i in emoji_placements else f"{str(i)}."
        family_emoji = family_emojis[cur_family]
        nick = await clean_nick(result["user"], context.guild)
        nxt += f"{placement} **{nick}** ({result["score"]} trucks)\n"
        
        
        if len(family_scores[cur_family]) >= 7:
            nxt += f"-# \tPlacing but not scoring for {cur_family} team\n"
            continue;
        else:
            nxt += f"-# \tScoring {i} points for {cur_family} team\n"
        family_scores[cur_family].append(i)
        
        if i % 15 == 0:
            all_placements.append(nxt)
            nxt = ""
    all_placements.append(nxt)
        
    for family in family_scores:
        for x in range(7-len(family_scores[family])):
            family_scores[family].append(len(results) + 1 + x)
            
    scores = {}
    for family, places in family_scores.items():
        # assumes len(places) == 7
        scores[family] = sum(places) 
        
    leaderboard = sorted(scores.items(), key=lambda kv: kv[1], reverse=False)
    leaderboard_order = [];
    res = "# Truck Competition Leaderboard\n"
    res += "This leaderboard will automatically update with every new truck submission to <#1203772906497380472> Remember, less points is better. Here are the current rankings!\n"
    for rank, (family, score) in enumerate(leaderboard, start=1):
        leaderboard_order.append(family);
        res += (
            f"**{rank}. {family}: {score}**\n"
            f"-# placements: {family_scores[family]}\n\n"
        )
        
    old_leaderboard_order = remember("truck_leaderboard")
    if old_leaderboard_order:
        for i, family in enumerate(old_leaderboard_order):
            if family != leaderboard_order[i]:
                await context.send(f"{leaderboard_order[i]} has risen above {family} on the leaderboard! Check it out: <#1024056209860468766>", reply=True)
                break
    remember("truck_leaderboard", leaderboard_order)
        
    announcement_channel = await context.guild.fetch_channel(1024056209860468766)
    c = 0;
    async for message in announcement_channel.history(oldest_first = False):
        content = message.content
        await message.delete();
        if "Leaderboard" in content:
            break
        
    await announcement_channel.send(res)
    for ct in all_placements:
        await announcement_channel.send(ct)


# @command_handler.Loop(hours=1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def free_money(client):
    guild = client.get_guild(647883751853916162)
    async for member in guild.fetch_members():
        neighbor = Neighbor(member.id, 647883751853916162)
        if neighbor.get_item_of_name("*Family Logo Tag* -- Best Seller") is None:
            item = Item("*Family Logo Tag* -- Best Seller", "family", int(time.time() + 604800))
            neighbor.bestow_item(item);
            print(member.display_name)


# @command_handler.Loop(hours = 1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def new_assign_families(client):
    
    from .families import load_points_txt
    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(FF.leaders_bot_channel);
    
    member_points = load_points_txt();
    
    families = {
        "bunnies": [316114265645776896, 660204032362545152, 312019945913319424],
        "cheetahs": [648229959973994506, 840077393683021824, 1282679887580102799, 795304848181821481],
        "donkeys": [605235104599769098, 1322905749139226656],
        "foxes": [220427859229933568, 793099607222648852, 430454367003475978, 863037754164903946],
        "giraffes": [160694804534132736, 374979463789805570, 374652286233870346],
        "hippos": [963533131854532638, 287705818462289922, 516969515486019604, 514413698761359400],
        "penguins": [355169964027805698, 987955038804639744, 443437059793879051, 1011941542287650856, 756594358127427685],
    }
    
    families_totals = {
        "bunnies": 0,
        "cheetahs": 0,
        "donkeys": 0,
        "foxes": 0,
        "giraffes": 0,
        "hippos": 0,
        "penguins": 0,
    }
    
    for family, members in families.items():
        for member in members:
            families_totals[family] += member_points[member];
            del member_points[member]
    
    neighbors_role = guild.get_role(1181330910747054211);
    while member_points:
        best_member, most_points = max(member_points.items(), key=lambda item: item[1])
        worst_family, least_points = min(families_totals.items(), key=lambda item: item[1])
        del member_points[best_member];
        
        user = await guild.fetch_member(best_member)
        if most_points == 0:
            print("skipped!")
            continue;
        
        # if most_points == 0:
        #     worst_family, least_points = random.choice(list(families_totals.items()))
        
        families_totals[worst_family] += most_points;
        families[worst_family].append(best_member);
        
    def write_families_to_file(families: dict[str, list[int]], path: str = "families.py"):
        """
        Writes a families dict to a Python file in literal form.
        """

        with open(path, "w", encoding="utf-8") as f:
            f.write("families = {\n")
            for family, members in families.items():
                f.write(f'    "{family}": {members},\n')
            f.write("}\n")
            
    write_families_to_file(families)
    
    for family, members in families.items():
        await channel.send(family);
        await channel.send(f"Has {families_totals[family]} total points")
        await channel.send(f"Has {len(members)} total members")
        await channel.send(" ".join(f"<@{uid}>" for uid in members))

        

# @command_handler.Loop(hours = 1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def family_points(client):
    
    from .families import count_family_messages, top_ten_percent_ids_percentile
    import csv
    # from datetime import datetime
    guild = client.get_guild(FF.guild)
    channel = await guild.fetch_channel(FF.bot_channel)
    MSG = await channel.send("Starting")

    # Update this if your bot saves it elsewhere
    TICKETS_CSV_PATH = "tickets_by_id.csv"

    print("[family_points] Starting")
    print(f"[family_points] Reading tickets from: {TICKETS_CSV_PATH}")

    # -----------------------------
    # Base points: event_emoji count
    # -----------------------------
    family_points = {}
    member_count = 0

    async for member in guild.fetch_members(limit=None):
        member_count += 1
        if member_count % 100 == 0:
            print(f"[family_points] Scanned {member_count} members for base points")

        neighbor = Neighbor(member.id, guild.id)
        item_count = 0
        items = neighbor.get_items_of_type("event_emoji");
        for item in items:
            if any(sub in item.name for sub in ["Fair", "fair", "horse", "wheel", "juggler"]):
                continue;
            else:
                item_count += 1;
        family_points[member.id] = item_count

    print(f"[family_points] Base points collected for {member_count} members")

    # -----------------------------
    # Special selections bonus
    # -----------------------------
    selected_special = [
        978586163147337728,
        1033786928279081061,
        1008544819733340160,
        749225745460625409,
        718586817204715690,
        757019298026881175,
        1243211103375196201,
        1011941542287650856,
        1152124518345756744,
        754000375274799196,
        680164335913664517,
        1250644488649441291,
        376343175863992320,
        203405042722668544,
        355169964027805698,
        1282679887580102799,
        648229959973994506,
        430454367003475978,
        987955038804639744,
        1322905749139226656,
        443437059793879051,
        220427859229933568,
        793099607222648852,
        840077393683021824,
        660204032362545152
    ]

    print(f"[family_points] Applying selected_special +5 to {len(selected_special)} ids")
    for uid in selected_special:
        family_points[uid] = family_points.get(uid, 0) + 5

    # -----------------------------
    # Message activity bonus (top 10%)
    # -----------------------------
    print("[family_points] Counting family messages...")
    messages_sent = await count_family_messages(client)

    print("[family_points] Computing top 10% message senders...")
    best = top_ten_percent_ids_percentile(messages_sent)

    print(f"[family_points] Applying top 10% +5 to {len(best)} ids")
    for uid in best:
        family_points[uid] = family_points.get(uid, 0) + 5

    # -----------------------------
    # Tickets bonus: + (tickets / 10)
    # -----------------------------
    tickets_by_id = {}
    try:
        with open(TICKETS_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    uid = int(row["user_id"])
                    tickets = float(row["tickets"])
                    tickets_by_id[uid] = tickets
                except (KeyError, ValueError, TypeError):
                    continue
        print(f"[family_points] Loaded tickets for {len(tickets_by_id)} users from CSV")
    except FileNotFoundError:
        print(f"[family_points] WARNING: tickets CSV not found at {TICKETS_CSV_PATH}. No ticket bonus applied.")
    except Exception as e:
        print(f"[family_points] WARNING: error reading tickets CSV: {e}. No ticket bonus applied.")

    applied_ticket_bonus = 0
    for uid, base in list(family_points.items()):
        tix = tickets_by_id.get(uid, 0)
        if tix:
            family_points[uid] = base + (tix / 10.0)
            applied_ticket_bonus += 1

    print(f"[family_points] Applied ticket bonus to {applied_ticket_bonus} users")

    # -----------------------------
    # Sort + write output file
    # -----------------------------
    sorted_items = sorted(family_points.items(), key=lambda x: x[1], reverse=True)

    out_path = "points.txt"
    print(f"[family_points] Writing output to {out_path}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Generated {datetime.utcnow().isoformat()}Z\n")
        f.write("# Format: user_id: points\n")
        for uid, pts in sorted_items:
            # Keeping your `- 3` behavior, but rounding for readability.
            f.write(f"{uid}: {round(pts, 2)}\n")

    await channel.send("Done!")
    print("[family_points] Done!")

    return sorted_items


# @command_handler.Loop(hours=1) 
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def fixing(client):

    guild = client.get_guild(FF.guild)
    channel = guild.get_channel(FF.bot_channel)
    start_message = await channel.fetch_message(1391207904786514061)

    pattern = re.compile(r"<@(\d+)> has dropped to level (\d+)")
    users_still_in_server = []
    users_gone = []
    to_fix = {};

    async for message in channel.history(after=start_message, oldest_first=True, limit=None):
        print(message.content)
        match = pattern.fullmatch(message.content.strip())
        if not match:
            print("🔴 Stopped: message did not match expected pattern.")
            print("Message content:")
            print(message.content)
            print("Message link:")
            print(f"https://discord.com/channels/{guild.id}/{channel.id}/{message.id}")
            break

        user_id_str, level_str = match.groups()
        user_id = int(user_id_str)
        level = int(level_str)
        try:
            member = await guild.fetch_member(user_id)
        except:
            member = None;

        user_entry = {
            "id": user_id,
            "level": level,
            "link": f"https://discord.com/channels/{guild.id}/{channel.id}/{message.id}"
        }

        if member is not None:
            user_entry["name"] = member.display_name
            users_still_in_server.append(user_entry)
            to_fix[user_id] = level;
        else:
            user_entry["name"] = f"<@{user_id}>"
            users_gone.append(user_entry)

    def write_to_file(filename, entries, title):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"{title}\n\n")
            for entry in sorted(entries, key=lambda x: x["level"], reverse=True):
                f.write(f"{entry['name']} (ID: {entry['id']}): Level {entry['level']}\n")
                f.write(f"Message: {entry['link']}\n\n")

    write_to_file("user_levels_present.txt", users_still_in_server, "Users still in server:")
    write_to_file("user_levels_gone.txt", users_gone, "Users who have left the server:")

    print("✅ Done. Files saved: user_levels_present.txt and user_levels_gone.txt")
    
    bot_channel = await guild.fetch_channel(784150346397253682)
    for cur_ID, cur_lvl in to_fix.items():
        cur_neighbor = Neighbor(cur_ID, FF.guild);
        present_XP = cur_neighbor.get_XP(); # amt of XP held currently 
        print(present_XP)
        present_XP = present_XP if present_XP > 10 else 10;
        old_xp = Neighbor.get_XP_for_level(cur_lvl); # amt of XP held post reckoning
        print(old_xp)
        pre_xp = Neighbor.get_XP_for_level(cur_lvl * 2) # amt of XP held pre reckoning
        print(pre_xp)
        lost_xp = pre_xp - old_xp;
        
        new_xp = pre_xp + Neighbor.get_XP_for_level(5);
        print(new_xp)
        cur_neighbor.set_XP(new_xp);
        new_lvl = Neighbor.get_level_for_XP(new_xp)
        # print(f"<@{cur_ID}> has been restored to level {new_lvl} sry.")
        await bot_channel.send(f"<@{cur_ID}> has been restored to level {new_lvl} sry.")

    
    
    # Add tickets for all new photos (up to 4 each) & 1 for any new players
    
    
    
    # Subtract 1 ticket from all 
    
    
    
    # Post current standings
            

# @command_handler.Command(access_type=AccessType.PRIVILEGED)
@command_handler.Deprecated(kind="Command", access_type=AccessType.PRIVILEGED, event_type="MESSAGE")
async def carnival_submission_counter(activator: Neighbor, context: Context):
    
    
    # if len(context.args) == 0 or context.args[0] == "info":
    #     await context.send("Sounds like you're ready to take admission for Carnival!\nLet's do it in two simple steps. 1. Perform `$carnival photos` to get a list of all photos submitted this week and check their validity. 2. Perform `$carnival admission` after validating submissions to confirm new tickets AND take admission from each person.\n\nAlso: `$carnival tickets`, `$carnival tickets @neighbor`, `$carnival tickets all` `",  reply=True)
    #     return;
    
    # if context.args[0] == "photos":
        
    #     messages = await get_photos(activator, context);
    #     for message in messages:
    #         link = f"https://discord.com/channels/{context.guild.id}/{message.channel.id}/{message.id}";
    #         await context.send(f"<@{message.author.id}> has submitted an image: {link}")
        
    #     await context.send("If you DO NOT WANT one of these linked messages to be counted for a ticket, (i.e. it is not a valid submission) you can either delete the linked message entirely or react to it with a ❌.");
    #     await context.send("Deleting or reacting to the link above will do nothing. You need to go to the linked message to see it and delete/react.")

    # elif context.args[0] == "cycle":
        
        from .community import get_photos
        await context.send("Starting...");
        
        # carnies is list of people currently with carnival role
        # current_tickets is dict of id: ticket count
        
        target = await context.send("Finding Carnies....");
        carnies = [];
        async for member in context.guild.fetch_members():
            if any(role.id == 1342329111359656008 for role in member.roles):
                carnies.append(member);
        await target.add_reaction("✅")
        
        target = await context.send("Finding photos....");
        messages = await get_photos(activator, context)
        valid_messages = [];
        await target.add_reaction("✅")
        
        target = await context.send("Counting tickets earned this week...")
        REVIEWER_ROLE_ID = 648188387836166168;
        for message in messages:
            is_valid = True
            for reaction in message.reactions:
                if str(reaction.emoji) == "❌":
                    users = [user async for user in reaction.users()]
                    for user in users:
                        member = await message.guild.fetch_member(user.id)
                        if member and any(role.id == REVIEWER_ROLE_ID for role in member.roles):
                            is_valid = False
                            break
                    break  # No need to check other reactions

            if is_valid:
                valid_messages.append(message)
                
        changes = {};
        for message in valid_messages:
            changes[message.author.id] = changes.get(message.author.id, 0) + 1
        await target.add_reaction("✅")
            
        target = await context.send("Taking admission...")
        msgs = [];
        tickets = remember("carnie_tickets") or {};
        for carnie in carnies:
            msg = f"<@{carnie.id}>\n"
            if not carnie.id in tickets:
                tickets[carnie.id] = 2;
                msg += f"• started with 2 tickets this week (awarded upon joining)\n"
            else:
                msg += f"• started with {tickets[carnie.id]} tickets this week\n"
            earned = changes.get(carnie.id, 0);
            if not earned:
                msg += f"• has not earned tickets this week\n"
            else:
                tickets[carnie.id] += earned;
                msg += f"• has earned {earned} tickets this week\n"
            tickets[carnie.id] -= 1;
            msg += f"• has had 1 ticket taken for admission\n"
            msg += f"• has ended the week with {tickets[carnie.id]}"
            msgs.append(msg);
            
        remember("carnie_tickets", tickets)
        await target.add_reaction("✅")
        await context.send("Done!");
        
        for msg in msgs:
            await context.send(msg);


# @command_handler.Command(access_type=AccessType.DEVELOPER)
@command_handler.Deprecated(kind="Command", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def derby(n, c):
    import gspread
    import asyncio
    import time
    from google.oauth2.service_account import Credentials

    # Define scopes and authorize
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    x = gspread.authorize(creds)

    # Open the Google Sheet and get worksheets
    sheet = x.open_by_key("1wfG1fo5ytFXmvvV5xAnmF_MO-5Te1zQdzeHv6PFSCh0")
    worksheets = [
        sheet.worksheet("Bees"), 
        sheet.worksheet("Cheetahs"), 
        sheet.worksheet("Frogs"), 
        sheet.worksheet("Goats"), 
        sheet.worksheet("Kittens"), 
        sheet.worksheet("Peacocks")
    ]

    guild = c.guild  

    def get_last_label_index(row, start_index):
        """Find the index of the last non-zero label."""
        for i, value in enumerate(row[start_index:], start=start_index):
            if value == 'a':
                return i
        return len(row)

    async def check_for_message(channel_id, user_id):
        """Check for a message in a channel with an attachment from a specific user."""
        channel = await guild.fetch_channel(channel_id)
        async for message in channel.history(limit=100):  # Limit to the last 100 messages for efficiency
            for attachment in message.attachments:
                if attachment.height is not None and message.author.id == user_id:
                    return True
        return False

    start_time = time.time()

    scores = {};

    for worksheet in worksheets:
        # Get all values starting from C4
        all_values = worksheet.get_all_values()

        # Find the end of the columns and rows
        row_end = 3  # Start just after C4
        while row_end < len(all_values) and all_values[row_end][2] != "END":
            row_end += 1

        col_end = 2  # Start just after C4
        while col_end < len(all_values[3]) and all_values[3][col_end] != "END":
            col_end += 1

        # Prepare to update the range
        cell_range = worksheet.range(5, 4, row_end, col_end)  # From C5 to the determined ends

        # Iterate over the defined chart range
        for row in range(4, row_end):  # Starting at row 5 (index 4)
            player_id = all_values[row][2]  # Column C (index 2)

            # Ensure player_id is a number
            if not player_id.isdigit():
                continue

            player_id = int(player_id)

            for col in range(3, col_end):  # Starting at column D (index 3)
                thread_id = all_values[3][col]  # Row 4 (index 3)

                # Skip columns without a thread ID
                if not thread_id.isdigit():
                    continue

                thread_id = int(thread_id)

                # Calculate the cell index in the range
                cell_index = (row - 4) * (col_end - 3) + (col - 3)
                
                # Check for the message
                is_complete = await check_for_message(thread_id, player_id)
                new_value = "Complete" if is_complete else "Incomplete"
                
                # print(f"Updating row {row}, column {col} with player ID {player_id} and thread ID {thread_id}")
                # print(f"Cell index: {cell_index}, New Value: {new_value}")

                # Update the cell value in the range
                cell_range[cell_index].value = new_value

        # Batch update the cells in the worksheet
        worksheet.update_cells(cell_range)
        
        scores[worksheet.title] = worksheet.acell("A1").value;
        
    
    elapsed_time = time.time() - start_time
    await c.send(f"Elapsed time: {round(elapsed_time, 2)} seconds")
    for fam, points in scores.items():
        await c.send(f"{fam}: {round(float(points))}p")
    await c.send("These scores are estimates based on my own tracking and are **not** official results. Please await the weekly newspaper for the next official leaderboard update. Check out <#1266758014921347082> to find more tasks to complete for your family.")

        

# @command_handler.Loop(hours = 1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def update_family_derby(client):
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    x = gspread.authorize(creds)
    
    sheet = x.open_by_key("1wfG1fo5ytFXmvvV5xAnmF_MO-5Te1zQdzeHv6PFSCh0")
    worksheets = [sheet.worksheet("Bees"), sheet.worksheet("Cheetahs"), sheet.worksheet("Frogs"), sheet.worksheet("Goats"), sheet.worksheet("Kittens"), sheet.worksheet("Peacocks")]
    guild = client.get_guild(647883751853916162)
    
    start_time = time.time()
    
    def get_last_label_index(row, start_index):
        for i, value in enumerate(row[start_index:], start=start_index):
            if value == '0':
                return i
        return len(row)

    async def check_for_message(channel_id, user_id):
        channel = await guild.fetch_channel(channel_id);
        async for message in channel.history(limit=None):
            for attachment in message.attachments:
                if attachment.height is not None:
                    if message.author.id == user_id:
                        return True;

    start_time = time.time()

    for worksheet in worksheets:
        # Get all values starting from C4
        all_values = worksheet.get_all_values()

        # Find the end of the columns and rows
        row_end = 3  # Start just after C4
        while row_end < len(all_values) and all_values[row_end][2] != "END":
            row_end += 1

        col_end = 2  # Start just after C4
        while col_end < len(all_values[3]) and all_values[3][col_end] != "END":
            col_end += 1

        # Prepare to update the range
        cell_range = worksheet.range(4, 3, row_end, col_end)  # From C5 to the determined ends

        # Iterate over the defined chart range
        for row in range(4, row_end):  # Starting at row 5 (index 4)
            player_id = all_values[row][2]  # Column C (index 2)

            # Ensure player_id is a number
            if not player_id.isdigit():
                continue

            player_id = int(player_id)

            for col in range(3, col_end):  # Starting at column D (index 3)
                thread_id = all_values[3][col]  # Row 4 (index 3)
                
                if thread_id == "":
                    continue;

                thread_id = int(thread_id)

                # Calculate the cell index in the range
                cell_index = (row - 4) * (col_end - 3) + (col - 3)

                # Check for the message
                is_complete = await check_for_message(thread_id, player_id)
                new_value = "Complete" if is_complete else "Incomplete"

                # Update the cell value in the range
                cell_range[cell_index].value = new_value

        # Batch update the cells in the worksheet
        worksheet.update_cells(cell_range)

    elapsed_time = time.time() - start_time
    await c.send(f"Elapsed time: {round(elapsed_time, 2)} seconds")
        
    c = await guild.fetch_channel(704366328089280623);

    # await c.send(f"I have just now updated the family derby tasks. It took me {round(time_taken)} seconds to do that. Wtf. F u all for making me do all this work.")

# @command_handler.Loop(hours=1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def score_introductions(client):
    from .families import has_role, pick_family
    guild = client.get_guild(FF.guild)
    channel = await guild.fetch_channel(783713419831279697)
    message = await channel.fetch_message(1454897846435319808)
    
    users = {};
    
    with open("lookups/families.json") as fFamilies:
        family_info = json.load(fFamilies)
        
    family_roles = {};
    for family in family_info:
        family_roles[family["role_id"]] = family["name"]
    
    async for message in channel.history(limit = None, oldest_first = True, after=message):
        user = message.author;
        user_id = message.author.id;
        content = message.content;
        
        if not user_id in users: 
            
            user_family = None;
            for family_role,name in family_roles.items():
                role = guild.get_role(family_role);
                if has_role(user, role):
                    user_family = name;
                    break;
            
            users[user_id] = {
                "introduction": False,
                "reply": False,
                "family": user_family,
            }
            
        if len(content) > 99 and "#" in content:
            if not users[user_id]["introduction"]:
                users[user_id]["introduction"] = True;
            else: users[user_id]["reply"] = True;
        elif len(content) > 9:
            users[user_id]["reply"] = True;
        
    family_scores = {
        "Bunny": 0,
        "Cheetah": 0,
        "Giraffe": 0,
        "Fox": 0,
        "Hippo": 0,
        "Donkey": 0,
        "Penguin": 0
    }    
    for user_id, user_scores in users.items():
        if user_scores["family"] is None:
            try:
                user = await guild.fetch_member(user_id)
            except:
                continue;
            new_family = await pick_family(user);
            print(f"<@{user_id}>: {new_family}")
            if not new_family in family_scores:
                continue;
            else:
                user_scores["family"] = new_family
        family_scores[user_scores["family"]] += 1 if user_scores["introduction"] else 0
        family_scores[user_scores["family"]] += 1 if user_scores["reply"] else 0    
        
    await channel.send(family_scores);   


# @command_handler.Loop(minutes = 5)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def update_tasks(client):
    import gspread
    from google.oauth2.service_account import Credentials
    
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    x = gspread.authorize(creds)

    # Open the Google Sheets file
    sheet = x.open_by_key("1MwBbJkxU0Fuvt9xpvyxE7Tk9xv5g_-VST9kC2Mu3qpo")
    worksheet = sheet.worksheet("Sheet2")
    
    guild = client.get_guild(647883751853916162)
    deco_book_values = {};
    misc_values = {};
    in_game_values = {};
    helps_values = {};
    other_games_values = {};
    introduction_values = {};
    
    # deco book
    async for member in guild.fetch_members():
        deco_book_values[member.id] = 0;
        misc_values[member.id] = 0;
        in_game_values[member.id] = 0;
        helps_values[member.id] = 0;
        other_games_values[member.id] = 0;
        introduction_values[member.id] = 0;
        
    # deco books
    deco_books_channel = await guild.fetch_channel(1251709328457601177);
    async for message in deco_books_channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.height is not None:
                cur = deco_book_values[message.author.id];
                if cur < 6:
                    deco_book_values[message.author.id] += 3;
                
    # deco books
    misc_channel = await guild.fetch_channel(1247611884920639621);
    async for message in misc_channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.height is not None:
                cur = misc_values[message.author.id];
                if cur < 2:
                    misc_values[message.author.id] += 1;
                    
    # in game 
    in_game_channel = await guild.fetch_channel(1247611653537796247);
    async for message in in_game_channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.height is not None:
                cur = in_game_values[message.author.id];
                if cur < 3:
                    in_game_values[message.author.id] += 1;
    
    # helps 
    helps_channel = await guild.fetch_channel(1247611725520437269);
    async for message in helps_channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.height is not None:
                cur = helps_values[message.author.id];
                if cur < 2:
                    helps_values[message.author.id] += 1;
                    
    # other games 
    other_games_channel = await guild.fetch_channel(1250117702559862928);
    async for message in other_games_channel.history(limit=None):
        for attachment in message.attachments:
            if attachment.height is not None:
                cur = other_games_values[message.author.id];
                if cur < 2:
                    other_games_values[message.author.id] += 1;
                
    # introductions  
    introduction_channel = await guild.fetch_channel(783713419831279697);
    async for message in introduction_channel.history(limit=None):
        for attachment in message.attachments:
            cur = introduction_values[message.author.id];
            if cur < 1:
                introduction_values[message.author.id] += 3;
            
    combined = {};
                
    for key, value in deco_book_values.items():
        combined[key] = value
    for key, value in misc_values.items():
        combined[key] += value
    for key, value in in_game_values.items():
        combined[key] += value
    for key, value in helps_values.items():
        combined[key] += value
    for key, value in other_games_values.items():
        combined[key] += value
    for key, value in introduction_values.items():
        combined[key] += value

    script_data = {key: value for key, value in combined.items() if value != 0}
    
    print(script_data)

    # Fetch existing data from the sheet
    existing_data = worksheet.get_all_records()

    # Create a dictionary to map existing IDs to their row indices
    id_to_row = {record['ID']: index + 2 for index, record in enumerate(existing_data)}  # +2 because rows in gspread are 1-indexed

    # Track rows to update and rows to append
    rows_to_update = []
    rows_to_append = []

    # Iterate over script data and update/add rows in the sheet
    for id, value in script_data.items():
        if id in id_to_row:
            # Update existing row
            row_index = id_to_row[id]
            rows_to_update.append({'row': row_index, 'id': id, 'value': value})
        else:
            # Add new row to append later
            rows_to_append.append({'id': id, 'value': value})

    # Update existing rows
    for row_data in rows_to_update:
        worksheet.update_cell(row_data['row'], 2, row_data['value'])  # Column B is 2

    # Append new rows at the end of existing data
    if rows_to_append:
        next_row_index = len(existing_data) + 2  # Start after existing data, 1-indexed
        for row_data in rows_to_append:
            worksheet.insert_row([str(row_data['id']), row_data['value']], next_row_index)
            next_row_index += 1

    
# @command_handler.Loop(days = 1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def beefamily(client):
    guild = client.get_guild(647883751853916162)
    channels = {
        1185653245415272518: 1175507670015422574,
        1185653319813824552: 1175507733500403824,
        1185653462957031475: 1175507776856920115,
        1185654026566635630: 1175507800697352273,
        1185654136587423814: 1175507823984132126,
        1185654247115730985: 1175507870431846460,
    }
 
    for channel_id, role_id in channels.items():
        channel = await guild.fetch_channel(channel_id);
        message = f"# Final reminder!\nHey <@&{role_id}>! If you completed bunny tasks this week, it's time to submit your task log screenshots to <#1203772906497380472>. Derby ends in about 7 hours; screenshots are due at that time. To see your task log, open the task board and scroll down. \n\nMake sure your screenshots include all your bunnies so you get the points for your family. If discord says your screenshots are 'too large', you may need to crop them to make them smaller.";
        await channel.send(message);


# @command_handler.Command(AccessType.PRIVILEGED, desc = "Show or edit Recruitment schedule")
@command_handler.Deprecated(kind="Command", access_type=AccessType.PRIVILEGED, event_type="MESSAGE")
async def recruitment(activator: Neighbor, context: Context):
    from .reminders import edit_schedule
    schedule = []
    with open("recruitment.txt") as fRecruit:
        for line in fRecruit.readlines():
            schedule.append(int(line[:-1]));
        
    res = "";
    for id in schedule:
        res += f"<@{id}>\n"
        
    await context.send(res, reply=True);
    
    target = await context.send("Type edit to edit schedule");
    
    def key(ctx):
        return ctx.message.content.lower() == "edit";
        
    ResponseRequest(edit_schedule, "EDIT", "MESSAGE", target, target, key=key);

    
    
# @command_handler.Scheduled("13:05")
@command_handler.Deprecated(kind="Scheduled", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def schedule_test(client):
    guild = client.get_guild(FF.guild);
    bc = await guild.fetch_channel(704366328089280623)
    await bc.send("This is a test of the new scheduled command system. This command was scheduled for 1:05pm");

        
# @command_handler.Loop(hours=1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def music_challenge(client):
    
    music_channel_id = 1179484606370689074;
    guild = client.get_guild(FF.guild)
    music_channel = await guild.fetch_channel(music_channel_id);
    bc = await guild.fetch_channel(704366328089280623)
    
    entries = {};
    counts = {};
    
    async def count_images(msg):
        c = 0;
        for att in msg.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                c += 1;
        return c;
    
    async for message in music_channel.history(limit=None, oldest_first=False):
        
        if message.id == 1445789515393274006:
            break;
        # print(message.content)
        cur_id = message.author.id;
        if not cur_id in entries:
            entries[cur_id] = 0;
            counts[cur_id] = 0;
            
        entries[cur_id] += await count_images(message) * 5
        
        for word in message.content.split():
            counts[cur_id] += 1;
            if counts[cur_id] > entries[cur_id]:
                print(f"Needed {counts[cur_id]} words for entry")
                
                entries[cur_id] += 1;
                counts[cur_id] = 0;
                
    for id, entry in entries.items():
        await bc.send(f"<@{id}>: {entry}")


# @command_handler.Uncontested(type = "EDIT", desc = "Alerts that a member left the server.", priority = 3)
@command_handler.Deprecated(kind="Uncontested", access_type=AccessType.DEVELOPER, event_type="EDIT")
async def on_edit(context: Context):

    similarity = difflib.SequenceMatcher(None, context.before.content, context.after.content).ratio();
    if similarity < .75:
        audit_channel = context.guild.fetch_channel(context.ID_bundle.audit_channel);
        before_content = convert_mentions_to_text(context, context.before.content);
        after_content = convert_mentions_to_text(context, context.after.content)
        text = f"*A message from <@{context.author_id}> ({context.author}) was edited:*\n> {before_content}\n\n> {after_content}";
        await audit_channel.send(text);


# @command_handler.Uncontested(type = "DELETE", desc = "Alerts that a member left the server.", priority = 3)
@command_handler.Deprecated(kind="Uncontested", access_type=AccessType.DEVELOPER, event_type="DELETE")
async def on_delete(context: Context):
    audit = await context.fetch_channel("audit_channel");
    text = f"*A message from <@{context.author_id}> ({context.author}) was deleted:*\n> {context.content}";
    await audit.send(text);

        
    
# @command_handler.Loop(minutes=60) ADD BACK
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def long_time_members(client):
    from .families import check_member
    guild = client.get_guild(647883751853916162);
    general = await guild.fetch_channel(FF.general_channel);
    
    role_5_years = guild.get_role(1242260564559007814);
    role_3_years = guild.get_role(1242260821657129101);
    role_1_year = guild.get_role(1242260896538169464);
    role_6_months = guild.get_role(1242260948971163718);
    role_3_months = guild.get_role(1242261007288762409);
    
    async for member in guild.fetch_members():
        if await check_member(member, 5*12):
            if role_5_years in member.roles:
                continue;
            else:
                print(member.display_name);


# @command_handler.Loop(hours=1)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def hospitality_tags(client):
    from .reminders import users_with_role
    guild = client.get_guild(647883751853916162)
    channel = await guild.fetch_channel(1095356264441188383)
    first = True;
    async for message in channel.history(limit=None, oldest_first=False):
        if message.author.id == 691338084444274728:
            
            if message.created_at.timestamp() + 57600 > time.time():
                break
            
            if first:
                first = not first;
                continue;
            
            for reaction in message.reactions:
                if str(reaction.emoji) == "✅":
                    user_ids = [user.id async for user in reaction.users()]
                    to_ping = [user.id for user in await users_with_role(guild, 1111174820072276063)]
                    
                    for id in to_ping:
                        if id in user_ids:
                            continue;
                        await message.reply(f"<@{id}> please complete this recent hospitality task and check react above. Thanks!")
                    
                    break
            break



# @command_handler.Loop(days = 1, desc = "Sorts the Neighbors text file in order of descending XP once per day.", priority = 4)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def database_mgmt():
    neighbors = Neighbor.read_all_neighbors();
    neighbors.sort(key=lambda x : x.get_XP());
    Neighbor.write_all_neighbors();


# @command_handler.Loop(hours = 12, desc = "Removes unneccesary members.")
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def remove_non_present_members(client):
    guild = client.get_guild(FF.guild);

    neighbors = Neighbor.read_all_neighbors();
    print("N:" + str(len(neighbors)))
    new_neighbors = [];
    i = 0;
    for neighbor in neighbors:
        i += 1
        if (i % 10 == 0):
            print(i)
        try:
            await guild.fetch_member(neighbor.ID)
            new_neighbors.append(neighbor);
        except:
            pass
    print("N:" + str(len(new_neighbors)))
    Neighbor.write_all_neighbors(new_neighbors);


# @command_handler.Loop(hours = 12, desc = "Rose theft!")
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def theft(client):
    guild = client.get_guild(FF.guild);

    if not chance(10):
        return

    neighbors = Neighbor.read_all_neighbors();
    thefted_from = [];
    i = 0;
    for neighbor in neighbors:
        perchance = 10
        if neighbor.get_item_of_name("SiloGuard(TM) Level 1 Security"):
            perchance = 20
        if neighbor.get_item_of_name("SiloGuard(TM) Level 2 Security"):
            perchance = 40
        if not chance(perchance):
            pass;
        thefted_from.append(neighbor);
        i += 1
        if (i % 10 == 0):
            print(i)
        silo_item: Item = neighbor.get_item_of_name("Silo")
        if silo_item:
            values = silo_item.values;
            for key, val in values.items():
                if not chance(10):
                    pass;
                new_val = str(int(int(val) * .9))
                silo_item.update_value(key, new_val);
            neighbor.update_item(silo_item);
    Neighbor.write_all_neighbors(neighbors);

    bc = await guild.fetch_channel(FF.bot_channel);
    res = "**Oh no! The silo thief!\n\n A small amount of crops have been thieved from the silos of some users.\n";
    # for neighbor in thefted_from:
    #     res += f"<@{neighbor.ID}> \n"
    res += "\nSorry about that! Use `$info thief` to learn more!";

    await bc.send(res);


# @command_handler.Loop(days = 1, desc = "On tuesdays and thursdays, a new channel called Farmerss Market appears that lets Neighbors sell crops to Greg for XP.")
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def farmers_market_mgmt(client):
            # Determine whether today is a Tuesday or Thursday

    is_today = random.choice([1]);
    if is_today == 2:
        is_today = random.choice([0,1]);

    # Get the server and the "Town Square" category
    guild = client.get_guild(FF.guild);
    town_square = await guild.fetch_channel(FF.town_square_category);

    # Look for the "farmers-market" channel in the server
    for channel in guild.channels:
        if channel.name == "\U0001F33Efarmers-market":
            farmers_market_channel = channel;
            await farmers_market_channel.delete();


    # # Get the server and the "Town Square" category
    # guild = client.get_guild(PHOENIX.guild);
    # town_square = await guild.fetch_channel(PHOENIX.general_category);

    # # Look for the "farmers-market" channel in the server
    # for channel in guild.channels:
    #     if channel.name == "\U0001F33Efarmers-market":
    #         farmers_market_channel = channel;
    #         await farmers_market_channel.delete();

    if not is_today:
        return;

    guild = client.get_guild(FF.guild);
    town_square = await guild.fetch_channel(FF.town_square_category);

    farmers_market_channel = None;

    # If it's a Tuesday or Thursday and the channel is not found, create it
    if is_today and farmers_market_channel is None:
        market = await guild.create_text_channel("\U0001F33Efarmers-market", category=town_square)

        crops_for_sale = random.sample(list(crops.items()), 5);

        boost_choice = random.choices([0, 1, 2], weights=[0.15,0.50,0.35])[0];

        options = [];

        res = "";

        for i, crop in enumerate(crops_for_sale):
            amt = random.randint(1, 10 ** (i + 1));
            factor = random.randint(6, 12);
            unit_price = crop[1] * factor + (i * random.randint(4, 6));
            if boost_choice == i:
                increase = random.choice([1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2]);
                # print("increase: " + str(increase));
                unit_price *= increase;
                amt *= increase;
                unit_price = round(unit_price);
                amt = round(amt);
            # print("amt: " + str(amt))
            # print("unit_price: " + str(unit_price))
            total_price = round((unit_price * amt) / 10)
            if i == 3 or i == 4:
                amt = 20;
                total_price = 20;
            options.append((crops_for_sale[i][0], amt, total_price));
            add = (f"{i}) {options[i][0]} -- offer is {options[i][1]} for {options[i][2]}xp");
            if boost_choice == i:
                add = "**" + add + "**"
            if i == 3 or i == 4:
                add = "*" + add + "*";
            res += "> " + add + "\n";

        await market.send(f"**Welcome to the Farmers Market!**\nFive crops are in demand today. To aceept a transaction, react with the number associated with that transaction. As you may be able to tell, crop #{boost_choice} is in particularly high demand today.")
        target = await market.send(res)

        fMarket = open("market.txt", "w");
        fMarket.write(str(target.channel.id) + "\n")
        fMarket.write(str(target.id) + "\n")
        for option in options:
            fMarket.write(str(option[0]) + "\n");
            fMarket.write(str(option[1]) + "\n");
            fMarket.write(str(option[2]) + "\n");
        fMarket.close();

        await target.add_reaction(unicodes[0]);
        await target.add_reaction(unicodes[1]);
        await target.add_reaction(unicodes[2]);
        await target.add_reaction(unicodes[3]);
        await target.add_reaction(unicodes[4]);
        await target.pin();


# @command_handler.Scheduled(time="04:01")
@command_handler.Deprecated(kind="Scheduled", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def start_farmmas_giveaway(client):
    
    from .derby import ordinal
    guild = client.get_guild(FF.guild);
    farmmas_channel = await guild.fetch_channel(784803565151453214)
    
    import json

    with open("farmmas.json", "r") as f:
        info = json.load(f)
        
    for gift in info:
        if "id" in gift: 
            continue
        
        msg = f"# 🎁 Day {gift["day"] - 8} — {gift["headline"]} ❄️\n"
        msg += f"On the {ordinal(gift["day"] - 8)} of Farmmas the Council gave to me...\n"
        for i, item in enumerate(gift["gifts"]):
            msg += f"> Gift {i + 1}. {item}\n"
        msg += "React to this message to enter the giveaway. For each gift above, a winner will be chosen at random from the entrants. @everyone"
        
        sent = await farmmas_channel.send(msg)
        await sent.add_reaction("<:giveaway:1067499350705582124>")
        
        gift["id"] = sent.id;
        
        break
    
    with open("farmmas.json", "w") as f:
        json.dump(info, f, indent=4)

        

    
# @command_handler.Scheduled(time="16:01")
@command_handler.Deprecated(kind="Scheduled", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def winners_farmmas_giveaway(client):
    
    from .community import get_users_who_reacted
    from .support import open_ticket
    guild = client.get_guild(FF.guild);
    farmmas_channel = await guild.fetch_channel(784803565151453214)
    
    import json

    with open("farmmas.json", "r") as f:
        info = json.load(f)
        
    winners_so_far = [];
    
    remember = None;
        
    for gift in info:
        if remember:
            remember = gift;
            break;
        
        if "id" in gift and "winners" in gift:
            winners_so_far.extend(int(id) for id in gift["winners"]);
            continue
        
        msg = await farmmas_channel.fetch_message(gift["id"]);
        entrants = await get_users_who_reacted(msg, "<:giveaway:1067499350705582124>")
        
        valid_entrant_ids = [];
        for entrant in entrants:
            role_ids = {role.id for role in entrant.roles}
            if not 1181330910747054211 in role_ids or 648188387836166168 in role_ids:
                continue;
            valid_entrant_ids.append(entrant.id)
            
        final_list = [];
        if len(valid_entrant_ids) < 6:
            final_list = [355169964027805698,355169964027805698,355169964027805698,355169964027805698,355169964027805698,355169964027805698]
        else:    
            limit = 0;
            while len(final_list) < (len(valid_entrant_ids) / 3):
                final_list = [];
                limit += 1;
                for entrant in valid_entrant_ids:
                    if winners_so_far.count(entrant) < limit:
                        final_list.append(entrant)
                        
        new_winners = random.sample(final_list, 6)
        gift["winners"] = [str(x) for x in new_winners];
        
        with open("farmmas.json", "w") as f:
            json.dump(info, f, indent=4)
                    
        msg = f"**Winners: Day {gift["day"] - 8} — {gift["headline"]}**\n"
        msg += f"Use a Council ticket to collect. <#1033207181857800242>\n"
        for i, item in enumerate(gift["gifts"]):
            msg += f"> Gift {i + 1}. **Winner: <@{new_winners[i]}>!! {item}** 🎉\n"
        msg += "Congrats!!"
        
        print(msg);
        sent = await farmmas_channel.send(msg)
        
        for i, winner in enumerate(new_winners):
            user = await guild.fetch_member(winner);
            ticket = await open_ticket(None, user, guild);
            item = gift["gifts"][i]
            host = gift["hosts"][i]
            await ticket.send(f"# Farmmas Gift\n**Hello {user.name}!** \nYou've won **{item}** from the Council for Day {gift["day"] - 8} of Farmmas! This gift is to be distributed to you by <@{host}>.\nPlease allow time for them to reach out to you, which they may do in DMs or this channel, so keep an eye out. They **will** use this channel to mark your gift as collected once it is so.\n\n🎁 **Happy Farmmas!!** ❄️");
        
        remember = True;
        
    if remember:
        # link = f"https://discord.com/channels/{guild.id}/{farmmas_channel.id}/{gift["id"]}"
        # await farmmas_channel.send(f"Farmmas results for Day {gift["day"] - 9} are in! See above. The giveaway for day {gift["day"] - 8} is still open; enter here: {link}\n\n@everyone")
        
        await farmmas_channel.send(f"Farmmas results for Day 12 are in! See above. That's it folks! I hope you enjoyed the Council's gifts this year.\n\nFarmmas may be over, but you can continue the giving spirit with my brand new `$give` command to start a giveaway of your own, available now! @everyone")
    
    with open("farmmas.json", "w") as f:
        json.dump(info, f, indent=4)

        

# @command_handler.Scheduled(time="16:01") 
@command_handler.Deprecated(kind="Scheduled", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def announce_last_farmmas2(client):
    from .community import get_users_who_reacted
    from .support import open_ticket
    guild = client.get_guild(FF.guild);
    farmmas_channel = await guild.fetch_channel(784803565151453214)
    
    import json

    with open("farmmas.json", "r") as f:
        info = json.load(f)
        
    gift = info[-1]
    winners = gift["winners"]
    
    msg = await farmmas_channel.fetch_message(gift["id"]);
    entrants = await get_users_who_reacted(msg, "<:giveaway:1067499350705582124>")
    
    valid_entrant_ids = [];
    for entrant in entrants:
        role_ids = {role.id for role in entrant.roles}
        if not 1181330910747054211 in role_ids:
            continue;
        valid_entrant_ids.append(entrant.id)
        
    tag_winner = random.choice(valid_entrant_ids);
        
    msg = f"**Winners: Day {gift["day"] - 8} — {gift["headline"]}**\n"
    msg += f"Use a Council ticket to collect. <#1033207181857800242>\n"
    for i, id in enumerate(winners):
        msg += f"> Gift {i + 1}. **Winner: <@{winners[i]}>!! {gift["gifts"][i]}** 🎉\n"
    msg += f"> Gift {7}. **Winner: <@{tag_winner}>!! {gift["gifts"][-1]}** 🎉\n"
    msg += "Congrats!!"
    
    print(msg);
    sent = await farmmas_channel.send(msg)
        
    for i, winner in enumerate(winners):
        user = await guild.fetch_member(winner);
        ticket = await open_ticket(None, user, guild);
        item = gift["gifts"][i]
        host = gift["hosts"][i]
        await ticket.send(f"# Farmmas Gift\n**Hello {user.name}!** \nYou've won **{item}** from the Council for Day {gift["day"] - 8} of Farmmas! This gift is to be distributed to you by <@{host}>.\nPlease allow time for them to reach out to you, which they may do in DMs or this channel, so keep an eye out. They **will** use this channel to mark your gift as collected once it is so.\n\n🎁 **Happy Farmmas!!** ❄️");
        
    user = await guild.fetch_member(tag_winner);
    ticket = await open_ticket(None, user, guild);
    item = gift["gifts"][6]
    host = gift["hosts"][6]
    await ticket.send(f"# Farmmas Gift\n**Hello {user.name}!** \nYou've won **{item}** from the Council for Day {gift["day"] - 8} of Farmmas! This gift is to be distributed to you by <@{host}>.\nPlease allow time for them to reach out to you, which they may do in DMs or this channel, so keep an eye out. They **will** use this channel to mark your gift as collected once it is so.\n\n🎁 **Happy Farmmas!!** ❄️");

    await farmmas_channel.send(f"Farmmas results for Day 12 are in! See above. That's it folks! I hope you enjoyed the Council's gifts this year.\n\nFarmmas may be over, but you can continue the giving spirit by using my brand new `$give` command in <#784150346397253682> to start a giveaway of your own, available now! @everyone")
























































# @command_handler.Loop(days = 1, desc = "On mondays, the council is asked to select what derby type is coming up.")
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def derby_channel_mgmt(client, selection = None):
    today = datetime.datetime.today()
    guild = client.get_guild(FF.guild);
    if selection is None and today.weekday() == 0:
        council_chat = await guild.fetch_channel(FF.leaders_bot_channel)
        target = await council_chat.send("It's that time of the week!\nPlease react for the derby type that is this week.");
        await target.add_reaction(unicodes["derby"]);
        await target.add_reaction(unicodes["muscle"])
        await target.add_reaction(unicodes["cat"])
        await target.add_reaction(unicodes["question"])
        await target.add_reaction(unicodes["flower"])
        await target.add_reaction(unicodes["target"])
        Expectation("Derby Type", "REACTION", time.time() + 72000, "derby_channel_mgmt", None, council_chat.id, target.id).persist();
    elif today.weekday() == 0:
        name = "derby-chat"
        if selection == unicodes["muscle"]:
            name = "power-derby-chat";
        elif selection == unicodes["cat"]:
            name = "chill-derby-chat";
        elif selection == unicodes["question"]:
            name = "mystery-derby-chat";
        elif selection == unicodes["flower"]:
            name = "blossom-derby-chat";
        elif selection == unicodes["target"]:
            name = "bingo-derby-chat";


# @command_handler.Loop(days = 1, desc = "Reminders!") 
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def reminders_mgmt(client):
    guild = client.get_guild(FF.guild);

    reminders = [];

    with open("reminders.txt", "r") as fReminders:
        for line in fReminders:
            data = line.split(":")
            reminders.append((data[0], data[1], data[2]));

    today = datetime.date.today().weekday();
    for reminder in reminders:
        if str(today) in reminder[0]:
            channel = await guild.fetch_channel(int(reminder[1]));
            await channel.send(reminder[2]);

            


# @command_handler.Loop(days = 1, desc = "From the second through fourth of each month, rss items are on sale. Also the 25th through the 28th")
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def sale_mgmt(client):
    choice = 0;
    with open("data/server_info.txt", "w") as fServer:
        if datetime.datetime.today() in [random.randint(1, 31), random.randint(1, 31)]:
            bot_channel = await client.get_guild(FF.guild).fetch_channel(FF.bot_channel);
            choice = random.choices([1, 2, 3], weights=[.9, 0.09, 0.01])[0];
            await bot_channel.send(f"It's your lucky day! Get up to {choice} level(s) off of your purchases in my $rss for the next 24 hours!!");
        else:
            choice = 0
        fServer.write(str(choice))


# @command_handler.Loop(days = 1, desc = "Updates swear_words list if necesary.")
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def swear_word_mgmt(client):
    swear_words.clear();
    with open("swearWords.txt") as fWords:
        for line in fWords.readlines():
            swear_words.append(line[:-1]);




# @command_handler.Loop(hours = 8, desc = "If a Neighbor has a passive XP item, the user receives free server XP once per hour.") # ADD BACK
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def passive_xp(client):
    # print("running passive");
    neighbors = Neighbor.read_all_neighbors();
    for neighbor in neighbors:
        neighbor.expire_items();
        passive_item = neighbor.get_item_of_name("Hire Rose and Earnest");
        if not passive_item is None:
            new_item = passive_item;
            if passive_item.expiration == -1:
                passive_item.expiration = int(time.time() + 604800);
                new_item.expiration = passive_item.expiration
            time_remaining = int(passive_item.expiration - time.time());

            passes_remaining = time_remaining / 28800;
            xp_accumulated = int(passive_item.get_value("so_far"));
            xp_needed = int(passive_item.get_value("needs"));
            if xp_needed < 0:
                continue;
            this_pass = (xp_needed - xp_accumulated) / passes_remaining;
            possibilities = [-.5, -.3, -.2, -.1, -0.09, -0.08, -0.07, -0.06, -0.05, -0.04, -0.03, -0.02 -0.01, 0];

            choice = int(this_pass + (this_pass * random.choice(possibilities)));
            if choice <= 0:
                continue;
            new_item.update_value("so_far", xp_accumulated + choice)
            neighbor.increase_XP(choice);
            neighbor.set_legacy_XP(neighbor.get_legacyXP() + choice);
            if time_remaining > 259200:
                new_item.expiration = int(time.time() + 345600);
            neighbor.update_item(new_item);

            guild = client.get_guild(neighbor.family);
            if guild.id == FF.guild:
                bot_channel = await guild.fetch_channel(FF.bot_channel);
            # else:
            #     bot_channel = await guild.fetch_channel(PHOENIX.bot_channel);

            if random.choice([0, 0, 0, 1]) and not neighbor.get_item_of_name("Pings Off"):
                await bot_channel.send(f"Rose and Earnest just harvested {choice}xp for <@{neighbor.ID}>");
            else:
                user = await guild.fetch_member(neighbor.ID)
                await bot_channel.send(f"Rose and Earnest just harvested {choice}xp for {user.display_name}");

    Neighbor.write_all_neighbors(neighbors);


# @command_handler.Loop(minutes = 10, desc = "The barn role icon is changed to a random barn.")
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def change_barn_role_icon(client):
    guild = client.get_guild(FF.guild);


# @command_handler.Command(AccessType.PUBLIC, desc = "Finds submission rates of all families")
@command_handler.Deprecated(kind="Command", access_type=AccessType.PUBLIC, event_type="MESSAGE")
async def survey(activator: Neighbor, context: Context):
        
    guild = context.guild;
    
    import gspread
    from google.oauth2.service_account import Credentials
    from collections import Counter

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet_id = "1rqghyBsahgmclDH6FAdVJB-jCUhcY35FzT33gpBqMr0"
    workbook = client.open_by_key(sheet_id)
    
    sheet = workbook.worksheet("Form Responses 1");
    
    vals = sheet.col_values(17)[1:];

    submission_counts = dict(Counter(vals));

    family_role_ids = {
        "Bees" : 1175507670015422574,
        "Cheetahs" : 1175507733500403824,
        "Frogs" : 1175507776856920115,
        "Goats" : 1175507800697352273,
        "Kittens" : 1175507823984132126,
        "Peacocks" : 1175507870431846460,
    }
    
    family_channel_ids = {
        "Bees" : 1185653245415272518,
        "Cheetahs" : 1185653319813824552,
        "Frogs" : 1185653462957031475,
        "Goats" : 1185654026566635630,
        "Kittens" : 1185654136587423814,
        "Peacocks" : 1185654247115730985,
    }

    player_counts = {
        "Bees" : sum(1 for member in guild.members if guild.get_role(1175507670015422574) in member.roles),
        "Cheetahs" : sum(1 for member in guild.members if guild.get_role(1175507733500403824) in member.roles),
        "Frogs" : sum(1 for member in guild.members if guild.get_role(1175507776856920115) in member.roles),
        "Goats" : sum(1 for member in guild.members if guild.get_role(1175507800697352273) in member.roles),
        "Kittens" : sum(1 for member in guild.members if guild.get_role(1175507823984132126) in member.roles),
        "Peacocks" : sum(1 for member in guild.members if guild.get_role(1175507870431846460) in member.roles),
    }
    
    submission_rates = {
        "Bees" : submission_counts["Bees"] / player_counts["Bees"],
        "Cheetahs" : submission_counts["Cheetahs"] / player_counts["Cheetahs"],
        "Frogs" : submission_counts["Frogs"] / player_counts["Frogs"],
        "Goats" : submission_counts["Goats"] / player_counts["Goats"],
        "Kittens" : submission_counts["Kittens"] / player_counts["Kittens"],
        "Peacocks" : submission_counts["Peacocks"] / player_counts["Peacocks"],
    }
    
    sorted_families = sorted(submission_rates, key=submission_rates.get);

    string = f" **Leaderboard**\n1. {sorted_families[5]} [Submission Rate: {submission_rates[sorted_families[5]] * 100:.2f}%]\n2. {sorted_families[4]} [Submission Rate: {submission_rates[sorted_families[4]] * 100:.2f}%]\n3. {sorted_families[3]} [Submission Rate: {submission_rates[sorted_families[3]] * 100:.2f}%]\n4. {sorted_families[2]} [Submission Rate: {submission_rates[sorted_families[2]] * 100:.2f}%]\n5. {sorted_families[1]} [Submission Rate: {submission_rates[sorted_families[1]] * 100:.2f}%]\n6. {sorted_families[0]} [Submission Rate: {submission_rates[sorted_families[0]] * 100:.2f}%]\n\nhttps://forms.gle/64fnpC9rfjCaDCnu9"
    
    await context.send(string);


# @command_handler.Command(AccessType.PUBLIC)
@command_handler.Deprecated(kind="Command", access_type=AccessType.PUBLIC, event_type="MESSAGE")
async def tickets(activator: Neighbor, context: Context):
    
    # FIRST SET OF TASKS
    from .carnival import Task, bought_second_set, task_2msg_300chars, task_3msgs, task_just1image
    tasks = []

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
    
    task_names = ["Wheel", "1", "2", "3", "Horse", "Juggler", "6", "7", "8", "9"]
    

    for i, ch in enumerate(channels):
        if not i == 4:
            task = Task(context.guild, ch, message_ids[i], points[i], task_just1image, task_names[i])
        else:
            task = Task(context.guild, ch, message_ids[i], points[i], task_2msg_300chars, task_names[i])
        tasks.append(task)
    
    # SECOND SET OF TASKS    
    tasks2 = []

    channels2 = [
        1387495669391954045, 1346890558869606400, 784150346397253682,
        (1386912469590605875, 1386912514478182450, 1386912565246038127,
         1386912639245881374, 1386912706296156301, 1386912757093503046),
        1386908794772000798, 1349747717580263524
    ]
    points2 = [3, 4, 3, 5, 2, 3]
    message_ids2 = [
        1387495676086059129, 1386917932453335122, 1386492537996574815,
        (1386912471910055987, 1386912517040635925, 1386912567582003363,
        1386912643503231096, 1386912708699488256, 1386912766144679978),
        1386908797666332727, 1351385836045996062
    ]

    for i, ch in enumerate(channels2):
        if not i == 1:
            if i == 3:
                task2 = Task(context.guild, ch, message_ids2[i], points2[i], task_just1image, "Role")
            else:
                task2 = Task(context.guild, ch, message_ids2[i], points2[i], task_just1image, str(i))
        else:
            task2 = Task(context.guild, ch, message_ids2[i], points2[i], task_3msgs, str(i))
        tasks2.append(task2)

    if len(context.args) > 0 and context.args[0] == "family":
        family_role_ids = [
            1328866582327332955, 1328866706294046720, 1328866759654248651,
            1328866832500658360, 1328866921185153085, 1328867017901477970
        ]
        family_names = ["Butterflies", "Cows", "Guinea Pigs", "Puppies", "Squirrels", "Zebras"]
        family_totals = [0 for _ in family_names]
        family_roles = [context.guild.get_role(x) for x in family_role_ids]
        role_id_to_index = {role.id: i for i, role in enumerate(family_roles)}

        gold_ids = {
            355169964027805698, 316114265645776896, 979407900801892383,
            648229959973994506, 398604838872809472, 1250644488649441291,
            935098241089929216, 240899039749603328, 969072183114625026,
            795304848181821481, 443437059793879051, 430454367003475978,
            220427859229933568, 874303613684580392
        }

        target_messge = await context.send("Counting family tickets...")

        player_msgs = {}  # user_id -> [ [ (ch_id, msg_id), ... ] per task ]

        all_tasks = tasks + tasks2
        total_task_count = len(all_tasks)

        for task_index, task in enumerate(all_tasks):
            for ch_id, msg_id in task.get_channels_and_startmsgs(context.guild):
                channel = await context.guild.fetch_channel(ch_id)
                start_message = await channel.fetch_message(msg_id)
                async for msg in channel.history(after=start_message, oldest_first=True, limit=None):
                    if any(str(reaction.emoji) == "👻" for reaction in msg.reactions):
                        continue
                    uid = msg.author.id
                    if uid not in player_msgs:
                        player_msgs[uid] = [[] for _ in range(total_task_count)]
                    player_msgs[uid][task_index].append((channel, msg))
            await target_messge.edit(content=f"Counting family tickets... {task_index}/16")

        for uid, task_msg_lists in player_msgs.items():
            member = context.guild.get_member(uid)
            if member is None:
                continue

            role_ids = {role.id for role in member.roles}
            family_indices = [role_id_to_index[rid] for rid in role_ids if rid in role_id_to_index]
            if not family_indices:
                continue

            total = 0
            has_second = await bought_second_set(uid, context)
            available_tasks = tasks + (tasks2 if has_second else [])

            for i, task in enumerate(available_tasks):
                ch_msg_ids = task_msg_lists[i]
                if i == 3:
                    ch_msg_ids.extend(player_msgs[1211781489931452447][3])
                if not ch_msg_ids:
                    continue
                if await task.evaluate(ch_msg_ids, uid):
                    total += task.points
                    for fam_index in family_indices:
                        family_totals[fam_index] += task.points

            if uid in gold_ids:
                total += 5

            if total >= 30:
                for fam_index in family_indices:
                    family_totals[fam_index] += 5  # family bonus

        result = ""
        for name, total in zip(family_names, family_totals):
            result += f"{name} have {total} <:blue_carnival_ticket:1246080867114422335>!\n"
        await target_messge.edit(content=result)
        return
    
    target_msg = await context.send("Counting your tickets...", reply=True)

    # INDIVIDUAL
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
    
    completed = [False] * len(tasks)
    total_points = 0
    
    for i, task in enumerate(tasks):
        for channel_id, msg_id in task.get_channels_and_startmsgs(context.guild):
            channel = await context.guild.fetch_channel(channel_id)
            start_message = await channel.fetch_message(msg_id)
            ch_msg_ids = []
            async for msg in channel.history(after=start_message, oldest_first=True, limit=None):
                if msg.author.id == target_member.id:
                    if any(str(reaction.emoji) == "👻" for reaction in msg.reactions):
                        continue
                    ch_msg_ids.append((channel, msg))
                    if await task.evaluate(ch_msg_ids, target_member.id):
                        completed[i] = True
                        total_points += task.points
                        break
            if completed[i]:
                break
        await target_msg.edit(content=f"Counting your tickets... {i}/10")
            
    has_second_set = await bought_second_set(target_member.id, context);
    
    completed2 = [False] * len(tasks2)
    if has_second_set:
        completed2 = [False] * len(tasks2)
        total_points -= 5;
        
        for i, task2 in enumerate(tasks2):
            for channel_id, msg_id in task2.get_channels_and_startmsgs(context.guild):
                channel = await context.guild.fetch_channel(channel_id)
                start_message = await channel.fetch_message(msg_id)
                ch_msg_ids = []
                async for msg in channel.history(after=start_message, oldest_first=True, limit=None):
                    if msg.author.id == target_member.id or msg.author.id == 1211781489931452447:
                        if any(str(reaction.emoji) == "👻" for reaction in msg.reactions):
                            continue
                        ch_msg_ids.append((channel, msg))
                        if await task2.evaluate(ch_msg_ids, target_member.id):
                            completed2[i] = True
                            total_points += task2.points
                            break
                if completed2[i]:
                    break
            await target_msg.edit(content=f"Counting your tickets... {i + 10}/16")
        
    # return total_points;
        
    result = f"{target_member.display_name} has earned {total_points} <:blue_carnival_ticket:1246080867114422335>!\n"
    gold_ids = {
        355169964027805698, 316114265645776896, 979407900801892383,
        648229959973994506, 398604838872809472, 1250644488649441291,
        935098241089929216, 240899039749603328, 969072183114625026,
        795304848181821481, 443437059793879051, 430454367003475978,
        220427859229933568, 874303613684580392
    }
    if target_member.id in gold_ids:
        result += "Plus 5 <:golden_carnival_ticket:1246080949620441190> (Thank you 🥰🏳️‍🌈)\n"

    result += "# The Fair has ended!\n"
    result += "# Prizes \n"
    result += "BEM prizes can be collected **now**! Please open a ticket <#1033207181857800242>\n"
    
    amt = total_points + (5 if target_member.id in gold_ids else 0);
    if amt >= 45:
        result += ":star: You've earned a full set of BEMs!\n"
    elif amt >= 30:
        result += ":star: You've earned 40 BEMs!\n"
        result += f":star: Next BEM prize: Earn {45 - amt} more tickets for a full BEM set!\n"
    elif amt >= 20:
        result += ":star: You've earned 20 BEMs!\n"
        result += f":star: Next BEM prize: Earn {30 - amt} more tickets for 40 BEMs!\n"
    elif amt >= 2:
        result += f":star: You've earned {amt} BEMs!\n"
        result += f":star: Next BEM prize: Earn any more tickets to earn more BEMs!\n"
    else: 
        result += f":star: Next BEM prize: Earn {2-amt} more tickets to earn more BEMs!\n"
    
    if any([completed[0], completed[4], completed[5], completed2[3]]):
        result += f":star: You've earned discord perks:\n"
        if completed[0]:
            result += "> 🎡\n"
        if completed[4]:
            result += "> 🎠\n"
        if completed[5]:
            result += "> 🤹\n"
        if completed2[3]:
            result += ">  Glowing role\n"
            # glowing = context.guild.get_role(1389339824972103790)
            # await target_member.add_roles(glowing);

    result += "# Set 1\n"
    for i, success in enumerate(completed):
        result += f"Task {i + 1}: {'✅' if success else '❌'}\n"

    result += f"Task 10: {'✅' if (target_member.id in gold_ids) else '❌'}\n"
    result += ":arrow_right: See the task board: <#1384644404408487956>\n"
    
    result += "# Set 2\n"
    if has_second_set:
        for i, success in enumerate(completed2):
            result += f"Task {i + 1}: {'✅' if success else '❌'}\n"
        result += ":arrow_right: See the task board: <#1386484938643341414>\n"
    else: 
        result += ":arrow_right: Buy the second set of tasks here: https://discord.com/channels/647883751853916162/1384642555425198080/1386905977487626431 \n" 
    
    result += "\n:arrow_right: **Tasks due <t:1751601540:R>**"

    await target_msg.edit(content=result)

            






# @command_handler.Loop(hours = 6)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def survey_lowest(client):
    
    guild = client.get_guild(647883751853916162)
    
    import gspread
    from google.oauth2.service_account import Credentials
    from collections import Counter

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet_id = "1rqghyBsahgmclDH6FAdVJB-jCUhcY35FzT33gpBqMr0"
    workbook = client.open_by_key(sheet_id)
    
    sheet = workbook.worksheet("Form Responses 1");
    
    vals = sheet.col_values(17)[1:];

    submission_counts = dict(Counter(vals));

    family_role_ids = {
        "Bees" : 1175507670015422574,
        "Cheetahs" : 1175507733500403824,
        "Frogs" : 1175507776856920115,
        "Goats" : 1175507800697352273,
        "Kittens" : 1175507823984132126,
        "Peacocks" : 1175507870431846460,
    }
    
    family_channel_ids = {
        "Bees" : 1185653245415272518,
        "Cheetahs" : 1185653319813824552,
        "Frogs" : 1185653462957031475,
        "Goats" : 1185654026566635630,
        "Kittens" : 1185654136587423814,
        "Peacocks" : 1185654247115730985,
    }

    player_counts = {
        "Bees" : sum(1 for member in guild.members if guild.get_role(1175507670015422574) in member.roles),
        "Cheetahs" : sum(1 for member in guild.members if guild.get_role(1175507733500403824) in member.roles),
        "Frogs" : sum(1 for member in guild.members if guild.get_role(1175507776856920115) in member.roles),
        "Goats" : sum(1 for member in guild.members if guild.get_role(1175507800697352273) in member.roles),
        "Kittens" : sum(1 for member in guild.members if guild.get_role(1175507823984132126) in member.roles),
        "Peacocks" : sum(1 for member in guild.members if guild.get_role(1175507870431846460) in member.roles),
    }
    
    submission_rates = {
        "Bees" : submission_counts["Bees"] / player_counts["Bees"],
        "Cheetahs" : submission_counts["Cheetahs"] / player_counts["Cheetahs"],
        "Frogs" : submission_counts["Frogs"] / player_counts["Frogs"],
        "Goats" : submission_counts["Goats"] / player_counts["Goats"],
        "Kittens" : submission_counts["Kittens"] / player_counts["Kittens"],
        "Peacocks" : submission_counts["Peacocks"] / player_counts["Peacocks"],
    }
    
    sorted_families = sorted(submission_rates, key=submission_rates.get);
    loser = sorted_families[0]
    
    message = f"Oh no! The {loser} currently have the lowest submission rate of the June survey!\n\nSubmission Rate: {submission_rates[loser] * 100:.2f}%\nRaw Submission Count: {submission_counts[loser]}\n\nThe survey is due on June 10th. I am pinging the lowest family every 6 hours until then. Submit the survey if you have not yet in order to 1) help your family win trophies 2) get 3 blue carnival tickets 3) help FF reach our goal of 100 submissions 4) stop my annoying pings!\n<@&{family_role_ids[loser]}> https://forms.gle/64fnpC9rfjCaDCnu9";
    
    channel = await guild.fetch_channel(family_channel_ids[loser]);
    await channel.send(message);
    await channel.send("**Tip!** If you are struggling with the event-ranking section, remember each event should get a different number. Try rotating your phone sideways to see more options.")

     
# @command_handler.Loop(hours = 12)
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def survey_second_lowest(client):
    
    guild = client.get_guild(647883751853916162)
    
    import gspread
    from google.oauth2.service_account import Credentials
    from collections import Counter

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet_id = "1rqghyBsahgmclDH6FAdVJB-jCUhcY35FzT33gpBqMr0"
    workbook = client.open_by_key(sheet_id)
    
    sheet = workbook.worksheet("Form Responses 1");
    
    vals = sheet.col_values(17)[1:];

    submission_counts = dict(Counter(vals));

    family_role_ids = {
        "Bees" : 1175507670015422574,
        "Cheetahs" : 1175507733500403824,
        "Frogs" : 1175507776856920115,
        "Goats" : 1175507800697352273,
        "Kittens" : 1175507823984132126,
        "Peacocks" : 1175507870431846460,
    }
    
    family_channel_ids = {
        "Bees" : 1185653245415272518,
        "Cheetahs" : 1185653319813824552,
        "Frogs" : 1185653462957031475,
        "Goats" : 1185654026566635630,
        "Kittens" : 1185654136587423814,
        "Peacocks" : 1185654247115730985,
    }

    player_counts = {
        "Bees" : sum(1 for member in guild.members if guild.get_role(1175507670015422574) in member.roles),
        "Cheetahs" : sum(1 for member in guild.members if guild.get_role(1175507733500403824) in member.roles),
        "Frogs" : sum(1 for member in guild.members if guild.get_role(1175507776856920115) in member.roles),
        "Goats" : sum(1 for member in guild.members if guild.get_role(1175507800697352273) in member.roles),
        "Kittens" : sum(1 for member in guild.members if guild.get_role(1175507823984132126) in member.roles),
        "Peacocks" : sum(1 for member in guild.members if guild.get_role(1175507870431846460) in member.roles),
    }
    
    submission_rates = {
        "Bees" : submission_counts["Bees"] / player_counts["Bees"],
        "Cheetahs" : submission_counts["Cheetahs"] / player_counts["Cheetahs"],
        "Frogs" : submission_counts["Frogs"] / player_counts["Frogs"],
        "Goats" : submission_counts["Goats"] / player_counts["Goats"],
        "Kittens" : submission_counts["Kittens"] / player_counts["Kittens"],
        "Peacocks" : submission_counts["Peacocks"] / player_counts["Peacocks"],
    }
    
    sorted_families = sorted(submission_rates, key=submission_rates.get);
    loser = sorted_families[1]
    
    message = f"Oh no! The {loser} currently have the second lowest submission rate of the June survey!\n\nSubmission Rate: {submission_rates[loser] * 100:.2f}%\nRaw Submission Count: {submission_counts[loser]}\n\nThe survey is due on June 10th. I am pinging the lowest family every 12 hours until then. Submit the survey if you have not yet in order to 1) help your family win trophies 2) get 3 blue carnival tickets 3) help FF reach our goal of 100 submissions 4) stop my annoying pings!\n<@&{family_role_ids[loser]}> https://forms.gle/64fnpC9rfjCaDCnu9";
    
    channel = await guild.fetch_channel(family_channel_ids[loser]);
    await channel.send(message);
    await channel.send("**Tip!** If you are struggling with the event-ranking section, remember each event should get a different number. Try rotating your phone sideways to see more options.")



# @command_handler.Command(AccessType.PRIVATE, desc = "Displays all crops a Neighbor has in their silo.", generic = True)
@command_handler.Deprecated(kind="Command", access_type=AccessType.PRIVATE, event_type="MESSAGE")
async def silo(activator: Neighbor, context: Context):

    if chance(10):
        await context.send("Did you know? Whoops, `$sell` doen't exist anymore my bad.", reply = True);

    silo_item = activator.get_item_of_name("Silo");
    res = "Your silo:\n";
    if silo_item is None:
        res += "Empty!";
    else:
        current_silo = silo_item.values;
        sorted_names = sorted(current_silo.keys())
        sorted_vals = [];
        for i in range(len(sorted_names)):
            sorted_vals.append(current_silo[sorted_names[i]]);
        for i in range(len(sorted_names)):
            name = sorted_names[i];
            val = sorted_vals[i];
            if not int(val) == 0:
                res += f"> {name}: {val}\n";
    target = await context.send(res);

    if activator.get_item_of_name("SiloGuard(TM) Level 2 Security"):
        await target.add_reaction("<:Strongman:1158159363828101232>");


# @command_handler.Command(AccessType.PRIVATE, desc = "Withdraw levels from your GregBanking(TM) savings account. Use `$info bank` to learn more.")
@command_handler.Deprecated(kind="Command", access_type=AccessType.PRIVATE, event_type="MESSAGE")
async def withdraw(activator: Neighbor, context: Context):
    from .experience import inc_xp
    bank_item = activator.get_item_of_name("GregBanking(TM)");
    if bank_item is None:
        await context.send("I'm sorry! You do not yet have a savings account open at GregBanking(TM). Please open an account using `$rss`.", reply = True);
    else:
        if len(context.args) < 1:
            raise CommandArgsError("`$deposit` expects one argument: amount of xp to deposit");
        amount_to_withdrawal = int(context.args[0]);
        if amount_to_withdrawal >= int(bank_item.get_value("xp")):
            await context.send("Whoops! You're too poor to withdraw that much XP! (If you are trying to withdraw all of your xp, use `$close_account`)");
        else:
            if len(context.args) < 1:
                raise CommandArgsError("`$deposit` expects one argument: amount of xp to deposit");
            new_bank_item = bank_item;
            new_bank_item.update_value("xp", str(int(bank_item.get_value("xp")) - int(amount_to_withdrawal)));
            activator.update_item(new_bank_item);
            await inc_xp(activator, int(amount_to_withdrawal * 0.75), context)
            await context.send(f"Done! {amount_to_withdrawal}xp has been withdrawn from your account. After taxes, {int(amount_to_withdrawal * 0.75)}xp was applied to your profile");


# @command_handler.Command(AccessType.PRIVATE, desc = "Close your GregBanking(TM) savings account, if you have one. Use `$info bank` to learn more.")
@command_handler.Deprecated(kind="Command", access_type=AccessType.PRIVATE, event_type="MESSAGE")
async def close_account(activator: Neighbor, context: Context):
    from .experience import inc_xp
    bank_item = activator.get_item_of_name("GregBanking(TM)");
    if bank_item is None:
        await context.send("I'm sorry! You do not yet have a savings account open at GregBanking(TM). Please open an account using `$rss`.", reply = True);
    else:
        XP = int(bank_item.get_value("xp"));
        activator.vacate_item(bank_item);
        await inc_xp(activator, int(XP * 0.75), context)
        await context.send(f"Done! {XP}xp has been withdrawn from your account. After taxes, {int(XP * 0.75)}xp was applied to your profile.");
        await context.send("Your GregBanking(TM) Savings Account has been successfully closed");


# @command_handler.Loop(minutes = 20) 
@command_handler.Deprecated(kind="Loop", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def players_sort(client):

    # Fetch all members with any of the specified roles
    guild = client.guilds[0]  # Assuming the bot is in one guild, adjust accordingly
    TARGET_ROLE_IDS = [FF.p_neighbors_role, FF.neighbors_role, FF.j_neighbors_role, FF.g_neighbors_role, FF.r_neighbors_role];
    players = [member for member in guild.members if any(role.id in TARGET_ROLE_IDS for role in member.roles)]

    players_data = []
    for member in players:
        classes = [str(role.id) for role in member.roles if role.id in TARGET_ROLE_IDS]
        class_names = [role.name for role in member.roles if role.id in TARGET_ROLE_IDS]
        joined_at_utc = member.joined_at.replace(tzinfo=datetime.timezone.utc)
        experience = (datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - joined_at_utc).total_seconds()

        player_info = {
            "name": member.display_name,
            "id": member.id,
            "class": classes,
            "NH": class_names,
            "activity": 0,
            "level": 0,
            "experience": experience
        }

        players_data.append(player_info)

    # Output the list to a JSON file
    with open('players_list.json', 'w') as file:
        json.dump(players_data, file, indent=2)

    print(f'Player list has been generated and saved to players_list.json')

# )
@command_handler.Deprecated(kind="Uncontested", access_type=AccessType.DEVELOPER, event_type="MESSAGE")
async def assign_family(context: Context):
    from .families import get_family_from_user, get_neighborhood_from_user, pick_family
    print("[assign_family] triggered")

    TARGET_CHANNEL_ID = 783713419831279697
    cutoff_utc = datetime.datetime(2025, 12, 25, 0, 0, 0, tzinfo=datetime.timezone.utc)

    # Must be in the right channel
    if context.channel.id != TARGET_CHANNEL_ID:
        return

    # Must be eligible
    if get_neighborhood_from_user(context.author) is None:
        return
    if get_family_from_user(context.author) != None:
        return

    uid = context.author.id

    # Requirements:
    # - At least 2 messages from this user in this channel since cutoff
    #   where len(content) > 10
    # - AND at least ONE message since cutoff where (len(content) > 99 AND '#' in content)
    qualifying_count = 0
    has_special = False

    # Include the current message in the evaluation (history may not include it yet)
    content = context.content or ""
    if len(content) > 10:
        qualifying_count += 1
        if len(content) > 99 and "#" in content:
            has_special = True

    # Scan backwards from newest to oldest since cutoff, stop early when done
    current_msg_id = getattr(getattr(context, "message", None), "id", None)

    async for msg in context.channel.history(after=cutoff_utc, oldest_first=False, limit=None):
        if msg.author.id != uid:
            continue
        if current_msg_id is not None and msg.id == current_msg_id:
            continue

        txt = msg.content or ""
        if len(txt) > 10:
            qualifying_count += 1
            if len(txt) > 99 and "#" in txt:
                has_special = True

        # Early exit as soon as we satisfy both conditions
        if qualifying_count >= 2 and has_special:
            break

    print(f"[assign_family] uid={uid} qualifying_count={qualifying_count} has_special={has_special}")

    if qualifying_count < 2 or not has_special:
        return

    await pick_family(context.author)


# Archived sketches below are preserved as comments; some are incomplete.

# @command_handler.Loop(minutes = 20)
# async def role_sweep(client):
#     print("Role sweep")

#     guild = client.get_guild(FF.guild);
#     NH_roles = [FF.p_neighbors_role, FF.neighbors_role, FF.j_neighbors_role, FF.g_neighbors_role, FF.r_neighbors_role]
#     family_roles = [1175507670015422574, 1175507733500403824, 1175507776856920115, 1175507800697352273, 1175507823984132126, 1175507870431846460]

#     async for member in guild.fetch_members():
#         role_ids = [role.id for role in member.roles];

#         if (set(NH_roles) & set(role_ids)) and not (set(family_roles) & set(role_ids)):
#             await pick_family(member);
#             print("Picked for " + str(member.display_name))

#         if len((set(family_roles) & set(role_ids))) > 1:
#             print("Two fams: " + str(member.display_name))


# @command_handler.Loop(hours = 24, desc = "")
# async def now(client):
#     guild = client.get_guild(FF.guild);
#     current_time = datetime.datetime.now()
#     current_day = current_time.day
#     if current_day == 2:
#         guild = client.get_guild(FF.guild);
#         bc = await guild.fetch_channel(FF.bot_channel);
#         # guild = client.get_guild(PHOENIX.guild);
#         # pbc = await guild.fetch_channel(PHOENIX.bot_channel);
#         await bc.send("It's about that time!");
#         # await pbc.send("It's about that time!");
#         for i in range(5):
#             print(f"{5-i}...");
#             time.sleep(1);
#         neighbors = Neighbor.read_all_neighbors();
#         for readNeighbor in neighbors:
#             neighbor = Neighbor(readNeighbor.ID, readNeighbor.family);
#             cur_level = neighbor.get_level();
#             strip(neighbor, levels = int(cur_level / 2));
#             if int(neighbor.get_family()) == FF.guild:
#                 if neighbor.get_item_of_name("Pings Off"):
#                     pass;
#                 else:
#                     await bc.send(f"<@{neighbor.ID}> has dropped to level {neighbor.get_level()}");
#             elif int(neighbor.get_family() == PHOENIX.guild):
#                 pass;
#                 # if neighbor.get_item_of_name("Pings Off"):
#                 #     pass;
#                 # else:
#                 #     await pbc.send(f"<@{neighbor.ID}> has dropped to level {neighbor.get_level()}");
#             best_this_month = neighbor.get_item_of_name("Best Level This Month");
#             if best_this_month:
#                 neighbor.vacate_item(best_this_month);
#         Neighbor.write_all_neighbors(neighbors);

# @command_handler.Loop(minutes = 10, desc = "")
# async def pbc(client):
#         guild = client.get_guild(PHOENIX.guild);
#         pbc = await guild.fetch_channel(PHOENIX.bot_channel);
#         await pbc.send("@everyone--the reckoning is upon you!")
#         await pbc.send("Below is the discord leaderboard for the top 10 members of the server in the past month!")
#         await pbc.send("In one day, the reckoning will ensue. To level the playing field without making everyone start from scratch, each person's level is cut in half at the beginning of each month.")
#         await pbc.send("If you intend/ed to spend or deposit your levels before the reset, you have approx 24 hours to do so. Use $rss to spend those levels baby!")
#         target = await pbc.send("$leaderboard");
#         await leaderboard(Neighbor(691338084444274728, 1008089618090049678), Context(target));


# @command_handler.Scheduled(time="16:01")
# async def winners_farmmas_giveaway2(client):
    
#     guild = client.get_guild(FF.guild);
#     farmmas_channel = await guild.fetch_channel(784803565151453214)
    
#     import json

#     with open("farmmas.json", "r") as f:
#         info = json.load(f)
        
#     winners_so_far = [];
    
#     remember = None;
        
#     for gift in info:
#         if remember:
#             remember = gift;
#             break;
        
#         if "id" in gift and "winners" in gift:
#             winners_so_far.extend(int(id) for id in gift["winners"]);
            
#             for i, winner in enumerate(gift["winners"]):
#                 user = await guild.fetch_member(int(winner));
#                 ticket = await open_ticket(None, user, guild);
#                 item = gift["gifts"][i]
#                 host = gift["hosts"][i]
#                 await ticket.send(f"**Hello {user.name}!** You've won **{item}** from the Council for Day {gift["day"] - 8} of Farmmas! This gift is to be distributed to you by <@{host}>. Please allow time for them to reach out to you, which they may do in DMs or this channel, so keep an eye out. They **will** use this channel to mark your gift as collected once it is so.\n\n🎁 Happy Farmmas!! ❄️");
        
            
#             remember = True;
        
#     if remember:
#         link = f"https://discord.com/channels/{guild.id}/{farmmas_channel.id}/{gift["id"]}"
#         await farmmas_channel.send(f"Farmmas results for Day {gift["day"] - 9} are in! See above. The giveaway for day {gift["day"] - 8} is still open; enter here: {link}\n\n@everyone")
        



# @command_handler.Loop(days = 1, desc = "Silo thief")
# async def thief(client, n: Neighbor):
#     if chance(10):
#         options = [0,1,2,3,4,5,6,7,8,9];
#         victim_id = random.choice(options);
#         victims = [x for x in Neighbor.read_all_neighbors() if x.ID % 10 == victim_id and x.get_item_of_name("Silo")];
#         for v in victims:
#             neighbor = Neighbor(v.ID, v.family);
#             silo = n.get_item_of_name("Silo");




# @command_handler.Command(AccessType.PRIVILEGED, desc = "Give or take tickets")
# async def tickets(activator: Neighbor, context: Context):
    
#     remember 

# @command_handler.Command(AccessType.DEVELOPER, desc = "Updates a Neighbor of given ID with a given XP amt and a given # of each crop")
# async def start(activator: Neighbor, context: Context):
#     if len(context.args) < 4:
#         raise CommandArgsError("`$start` expects 3 arguemnts: the id of the player whose profile needs updating, the xp to give them, and the # of each crop to give them.")
#     id = int(context.args[1]);
#     xp = int(context.args[2]);
#     num_crops = int(context.args[3]);

#     to_update = Neighbor(id, FF.guild);
#     to_update.

# async def assign_family(client, before, after):
#     guild = before.guild;
#     targetAF = await guild.fetch_channel(FF.assign_family_channel);
#     targetBC = await guild.fetch_channel(FF.bot_channel);

#     name = after.display_name;

#     neighborhood_before = get_neighborhood_from_user(before);
#     neighborhood_after = get_neighborhood_from_user(after);
#     # print(neighborhood_after);

#     family_before = get_family_from_user(before);
#     family_after = get_family_from_user(after);

#     # print(neighborhood_after);
#     if not neighborhood_after is None and family_after == "0":
#         # print("here");
#         await pick_family(after);
#     else:
#         return 0;

