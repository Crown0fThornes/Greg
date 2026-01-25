import asyncio
import math
import re
import shelve
import string
import traceback
from typing import Counter
from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
import random
from custom_types import Neighbor, Item
from responses import ResponseRequest, ResponsePackage
from id_bundle import FF
from phoenix_bundle import PHOENIX
import difflib
import discord
import json
import datetime
import time
from PIL import Image
import requests
import os
import wordle_helper

VERSION = "3.x";

swear_words = [];
xp_gained = 0;
xp_happy_hour = 1;
last_profitable_message_author_id = 0;

unicodes = {
    0 : "\U00000030\U0000FE0F\U000020E3",
    1 : "\U00000031\U0000FE0F\U000020E3",
    2 : "\U00000032\U0000FE0F\U000020E3",
    3 : "\U00000033\U0000FE0F\U000020E3",
    4 : "\U00000034\U0000FE0F\U000020E3",
    5 : "\U00000035\U0000FE0F\U000020E3",
    6 : "\U00000036\U0000FE0F\U000020E3",
    7 : "\U00000037\U0000FE0F\U000020E3",
    8 : "\U00000038\U0000FE0F\U000020E3",
    9 : "\U00000039\U0000FE0F\U000020E3",
    "boost" : "\U0001F4B0",
    "perk" : "\U0001F5FF",
    "tag" : "\U0001F996",
    "icon" : "\U0001F48E",
    "mail" : "\U00002709",
    "rice" : "\U0001F33E",
    "rainbow" : "\U0001F308",
    "bee" : "\U0001F41D",
    "mushroom" : "\U0001F344",
    "selfie" : "\U0001F933",
    "crown" : "\U0001F451",
    "fox" : "\U0001F98A",
    "snowflake" : "\U00002744",
    "fries" : "\U0001F35F",
    "red_heart" : "\U00002764",
    "blueberry" : "\U0001FAD0",
    "strawberry" : "\U0001F353",
    "coffee" : "\U00002615",
    "t_rex" : "\U0001F996",
    "chicken" : "\U0001F414",
    "coin" : "\U0001FA99",
    "diamond" : "\U0001F48E",
    "crayon" : "\U0001F58D",
    "robot" : "\U0001F916",
    "nails" : "\U0001F485",
    "bank" : "\U0001F3E6",
    "check" : "\U00002705",
    "bot" : "\U0001F916",
    "ant" : "\U0001FAB3",
    "ghost" : "\U0001F47B",
    "back" : "\U000023CF",
    "butterfly" : "\U0001F98B",
    "cheetah" : "\U0001F406",
    "fox" : "\U0001F98A",
    "horse" : "\U0001F40E",
    "puppy" : "\U0001F436",
    "cabinet" : "\U0001F5C4",
    "trophy" : "\U0001F3C6",
    "first" : "\U0001F947",
    "second" : "\U0001F948",
    "third" : "\U0001F949",
    "clover" : "\U00001F34",
    "locked" : "🔒",
    "unlocked" : "🔓",
    "letters" : "\U0001F520",
    "gift" : "\U0001F381",
    "fire" : "\U0001F525",
    "star" : "\U00002B50",
    "anger" : "\U0001F620",
    "bee" : "\U0001F41D",
    "frog" : "\U0001F438",
    "goat" : "\U0001F410",
    "kitten" : "\U0001F408",
    "peacock" : "\U0001F99A",
}

red_wordle_emojis = {
    0: "<:0_a:1117155743754354829>",
    1: "<:0_b:1117155746182869162>",
    2: "<:0_c:1117155748372299877>",
    3: "<:0_d:1117155751329284166>",
    4: "<:0_e:1117155753338359808>",
    5: "<:0_f:1117155755653603339>",
    6: "<:0_g:1117155757931114697>",
    7: "<:0_h:1117155759847899176>",
    8: "<:0_i:1117155761794060389>",
    9: "<:0_j:1117155764054798526>",
    10: "<:0_k:1117155766659465276>",
    11: "<:0_l:1117155768827924651>",
    12: "<:0_m:1117155771440963654>",
    13: "<:0_n:1117155773454233692>",
    14: "<:0_o:1117155775568158845>",
    15: "<:0_p:1117156672889172009>",
    16: "<:0_q:1117156676131377243>",
    17: "<:0_r:1117156678241095731>",
    18: "<:0_s:1117156680904486942>",
    19: "<:0_t:1117156683228139630>",
    20: "<:0_u:1117156685866352813>",
    21: "<:0_v:1117156687774765097>",
    22: "<:0_w:1117156690333274162>",
    23: "<:0_x:1117156692312993833>",
    24: "<:0_y:1117156694837952603>",
    25: "<:0_z:1117156697258086431>"
}

yellow_wordle_emojis = {
    0: "<:1_a:1117151655343955988>",
    1: "<:1_b:1117151657940226138>",
    2: "<:1_c:1117151659534057593>",
    3: "<:1_d:1117151662902083694>",
    4: "<:1_e:1117151664701444216>",
    5: "<:1_f:1117151667037679677>",
    6: "<:1_g:1117151668715389038>",
    7: "<:1_h:1117151670644781086>",
    8: "<:1_i:1117151673173946468>",
    9: "<:1_j:1117151675141079110>",
    10: "<:1_k:1117151677288562688>",
    11: "<:1_l:1117151684423077998>",
    12: "<:1_m:1117151686251786341>",
    13: "<:1_n:1117151687820451880>",
    14: "<:1_o:1117151690014081066>",
    15: "<:1_p:1117151692165750834>",
    16: "<:1_q:1117151694585872527>",
    17: "<:1_r:1117155116135497808>",
    18: "<:1_s:1117151697576411359>",
    19: "<:1_t:1117155118484303872>",
    20: "<:1_u:1117151701112213504>",
    21: "<:1_v:1117155120422068234>",
    22: "<:1_w:1117151704656396338>",
    23: "<:1_x:1117155122238210148>",
    24: "<:1_y:1117151709270118460>",
    25: "<:1_z:1117151711522459649>"
}

green_wordle_emojis = {
    0: "<:2_a:1117132571369816185>",
    1: "<:2_b:1117132573949296762>",
    2: "<:2_c:1117132575677354014>",
    3: "<:2_d:1117132577736765510>",
    4: "<:2_e:1117132584665755779>",
    5: "<:2_f:1117132588964909187>",
    6: "<:2_g:1117132591380836412>",
    7: "<:2_h:1117132601417801840>",
    8: "<:2_i:1117132604202811442>",
    9: "<:2_j:1117132605838602260>",
    10: "<:2_k:1117132609030471761>",
    11: "<:2_l:1117132611228278805>",
    12: "<:2_m:1117132614533398538>",
    13: "<:2_n:1117132616810909786>",
    14: "<:2_o:1117132619121950741>",
    15: "<:2_p:1117133811432570940>",
    16: "<:2_q:1117133815580725441>",
    17: "<:2_r:1117133818487382066>",
    18: "<:2_s:1117133820769095830>",
    19: "<:2_t:1117133824262934628>",
    20: "<:2_u:1117133829031874721>",
    21: "<:2_v:1117133831405850714>",
    22: "<:2_w:1117133833796587671>",
    23: "<:2_x:1117133836355109004>",
    24: "<:2_y:1117133838162874470>",
    25: "<:2_z:1117133841119846410>"
}

purple_wordle_emojis = {
    0: "<:3_a:1129837059624947723>",
    1: "<:3_b:1129837062107963483>",
    2: "<:3_c:1129837064129609940>",
    3: "<:3_d:1129837066319056969>",
    4: "<:3_e:1129837069057921116>",
    5: "<:3_f:1129837071012479076>",
    6: "<:3_g:1129837072904093928>",
    7: "<:3_h:1129837079011004416>",
    8: "<:3_i:1129837081535987853>",
    9: "<:3_j:1129837084128071790>",
    10: "<:3_k:1129837086996971571>",
    11: "<:3_l:1129837088896979015>",
    12: "<:3_m:1129837090977353799>",
    13: "<:3_n:1129837092529254541>",
    14: "<:3_o:1129837095112945694>",
    15: "<:3_p:1129837097470132254>",
    16: "<:3_q:1129837099550527570>",
    17: "<:3_r:1129837504527339670>",
    18: "<:3_s:1129837102486528101>",
    19: "<:3_t:1129837507337531422>",
    20: "<:3_u:1129837509027827712>",
    21: "<:3_v:1129837106051682365>",
    22: "<:3_w:1129837658122752131>",
    23: "<:3_x:1129837109335838770>",
    24: "<:3_y:1129837510667800697>",
    25: "<:3_z:1129837113005842432>",
}

swear_words = [];
test_list = ["some value"];
active_expectations = [];

# If value given, stores to DB. If value None, retrieves data.
def remember(key, value=Ellipsis, delete=False):
    with shelve.open("data/persistentdata") as db:
        if value is not None and value is not Ellipsis:
            db[key] = value
            return value;
        elif value is None or delete:
            return db.pop(key, None)
        else:
            return db.get(key)

# @command_handler.Loop(hours=1)
async def free_money(client):
    guild = client.get_guild(647883751853916162)
    async for member in guild.fetch_members():
        neighbor = Neighbor(member.id, 647883751853916162)
        if neighbor.get_item_of_name("*Family Logo Tag* -- Best Seller") is None:
            item = Item("*Family Logo Tag* -- Best Seller", "family", int(time.time() + 604800))
            neighbor.bestow_item(item);
            print(member.display_name)

async def count_family_messages(client):
    channel_ids = [1328867512045142107, 1328867719071666288, 1328867809081692332, 1328869197463420978, 1328869403034521692, 1328869590758981713];
    

    guild = client.get_guild(FF.guild);
    channels = [await guild.fetch_channel(id) for id in channel_ids]
    messages_sent = {};
    
    for channel in channels: 
        async for message in channel.history(oldest_first=True, limit=None):
            if message.author.id in messages_sent:
                messages_sent[message.author.id] += 1;
            else:
                messages_sent[message.author.id] = 1;
    
    return messages_sent;

import math

def top_ten_percent_ids_percentile(d):
    if not d:
        return []

    values = sorted(d.values())
    n = len(values)

    # Index of the 90th percentile (nearest-rank method)
    idx = math.ceil(0.8 * n) - 1
    cutoff_value = values[idx]

    return [k for k, v in d.items() if v >= cutoff_value]

def load_points_txt(path: str = "points.txt") -> dict[int, float]:
    """
    Reads a points.txt file and returns {user_id: points}.

    Expected line format:
        user_id: points

    Lines starting with '#' are ignored.
    Malformed lines are skipped safely.
    """
    points_by_id: dict[int, float] = {}

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            # Skip blanks and comments
            if not line or line.startswith("#"):
                continue

            if ":" not in line:
                continue

            left, right = line.split(":", 1)

            try:
                uid = int(left.strip())
                pts = float(right.strip())
            except ValueError:
                # Skip malformed rows
                continue

            points_by_id[uid] = pts

    return points_by_id

def calculate_totals(families_dict, points_dict):
    families_totals = {
        "bunnies": 0,
        "cheetahs": 0,
        "donkeys": 0,
        "foxes": 0,
        "giraffes": 0,
        "hippos": 0,
        "penguins": 0,
    }
    
    for family, members in families_dict.items():
        for member in family:
            families_totals[family] += points_dict[member];
    
    return families_totals;

# @command_handler.Loop(hours = 1)
async def new_assign_families(client):
    
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
async def family_points(client):
    
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
        

# @command_handler.Loop(hours=1)
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
    sheet = x.open_by_key("1XxS6KMpyVbK5N87jJO_suiNHTjOgDctrcztzd2_ZgTI")
    worksheet = sheet.worksheet("May 2025");
    
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
        
    prev_total = remember("5050Total");
    
    print(f"New total: {total}\nOld total: {prev_total}");
    
    if not prev_total:
        remember("5050Total", 300)
        prev_total = 0;
    if not total - prev_total > 250:
        return
    remember("5050Total", total);

    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(1234185689172807690);
    total = int(total);
    revenue = math.ceil(total / 2);
    prize = math.floor(total / 2);
    await channel.send(f"# New Total!\nThe 50/50 pot has reached {total} BEMs, wow!\n\nThat marks {prize} BEMs for the prize pool.\n<@&1181330910747054211> use <#1234185689172807690> to purchase raffle tickets.");
    
@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def carnival(activator: Neighbor, context: Context):
    await context.send("```You are now in the Carnival command operations environment. Type `help` if needed, or else get started. Type `exit` to leave the coe.```")
    coe_item = Item("Carnival COE", "coe", time.time() + 3600);
    activator.bestow_item(coe_item);
    await carnival_coe(context)
    await set_nick(await context.guild.fetch_member(activator.ID), context.guild)
    
@command_handler.Uncontested(type="MESSAGE")
async def carnival_coe(context: Context):
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
    
    
    # Add tickets for all new photos (up to 4 each) & 1 for any new players
    
    
    
    # Subtract 1 ticket from all 
    
    
    
    # Post current standings
            

# @command_handler.Command(access_type=AccessType.PRIVILEGED)
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
    
@command_handler.Command(access_type=AccessType.DEVELOPER)
async def test(activator: Neighbor, context: Context):
    await context.send("Testing, 1 2, testing!", reply=True)

# @command_handler.Command(access_type=AccessType.DEVELOPER)
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
async def score_introductions(client):
    guild = client.get_guild(FF.guild)
    channel = await guild.fetch_channel(783713419831279697)
    message = await channel.fetch_message(1454897846435319808)
    
    users = {};
    
    with open("families.json") as fFamilies:
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
    
# @command_handler.Loop(hours=3)
async def assign_some_families(client):
    # if not chance(5):
    #     return
    # today = datetime.datetime.now().date()
    # first_of_month = (today.month, 1)
    guild = client.get_guild(647883751853916162)
    members = guild.members;
    for assignee in members:
        print(f"Trying: {assignee.username}")
        answer = await pick_family(assignee)
        if not answer in ["Alrdy has family", "FFJ2", "No NH"]:
            return
    
# @command_handler.Loop(days = 1)
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
        
# p/q probability of returning True
def chance(q, p = 1):
    """
    p/q chance of returing True
    """
    possibilities = [0] * (q - p) + [1] * p
    return random.choice(possibilities);

# @command_handler.Command(AccessType.PRIVILEGED, desc = "Show or edit Recruitment schedule")
async def recruitment(activator: Neighbor, context: Context):
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
        
async def edit_schedule(activator: Neighbor, context: Context, response: ResponsePackage):
    class AdminCustomizationError(ValueError):
        pass;
 
    if response.name == "EDIT":
        target = await context.send("Please type out full schedule in the format it was presented before. \n\n@monday_poster\n@tuesday_poster\n...\n@sunday_poster");
        ResponseRequest(edit_schedule, "SCHEDULE", "MESSAGE", target, target);
    else:
        schedule_mentions = response.content.split("/n");
        if len(schedule_mentions) != 7:
            raise AdminCustomizationError("Please @mention 7 people seperated by new lines. Try again by re-running the command.")
        
        schedule_ids = [];
        for i, mention in enumerate(schedule_mentions):
            try: 
                cur_id = parse_mention(mention)
            except ValueError:
                raise AdminCustomizationError(f"Could not identify @mention on line {i+1}. Try again by re-running the command.");
            schedule_ids.append(str(cur_id));
   
        with open("recruitment.txt", "w") as fRecruit:
            fRecruit.writelines(schedule_ids)
    
@command_handler.Command(access_type=AccessType.PRIVATE)
async def bunny_count(activator: Neighbor, context: Context):
    final_msg = await context.send("Counting...")
    
    totals = {
        'B': 0,
        'C': 0,
        'G': 0,
        'P': 0,
        'S': 0,
        'Z': 0
    }
    
    def first_number(s: str):
        match = re.search(r'\d+(\.\d+)?', s)  # matches integers or decimals
        if match:
            return float(match.group()) if '.' in match.group() else int(match.group())
        return None
    
    bunny_channel = await context.guild.fetch_channel(1203772906497380472);
    done = False;
    async for msg in bunny_channel.history(limit=None, oldest_first=False):
        if msg.id == 1416127796136120472:
            done = True
            
        fam = get_family_from_user(msg.author)
        if fam == '0':
            continue;
        
        totals[fam] += first_number(msg.content) or 0;
            
        if done:
            break
        
    await final_msg.edit(content=str(totals))
    
@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def treasury(activator: Neighbor, context: Context):
    
    import gspread
    from google.oauth2.service_account import Credentials
    from collections import Counter

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet_id = "1v5wq4m-2SFBaQHLjyo0njGTtg-h8mof-i8cn8wBaSp8"
    workbook = client.open_by_key(sheet_id)
    
    if (len(context.args)) > 0 and context.args[0].lower() == "total":
        
        sheet = workbook.worksheet("Totals");
        
        look_for = (await context.guild.fetch_member(activator.ID)).name
        
        def lookup_row_values(sheet, search_term):
            col_a = sheet.col_values(1)  # Get all values in column A
            for i, val in enumerate(col_a):
                if val == search_term:
                    row_index = i + 1  # gspread is 1-indexed
                    values = sheet.row_values(row_index)
                    return values[1:5]  # B = index 1, C = 2, D = 3
            return None  # Not found
        
        target_results = lookup_row_values(sheet, look_for)
        all_results = lookup_row_values(sheet, "Total")
        
        if target_results:
            await context.send(f"**You** have: {target_results[0]} bolts, {target_results[1]} planks, {target_results[2]} duct tape. For a total of {target_results[3]} BEMs!\n\n" + 
                f"**The Council** has: {all_results[0]} bolts, {all_results[1]} planks, {all_results[2]} duct tape. For a total of {all_results[3]} BEMs!")
        else: 
            await context.send(f"**The Council** has: {all_results[0]} bolts, {all_results[1]} planks, {all_results[2]} duct tape. For a total of {all_results[3]} BEMs!")
        
        return;
    
    if (len(context.args)) < 4:
        raise CommandArgsError("Please run the command with 4 arguments:\n\n1) # of bolts 2) # of planks 3) # of duct tapes 4) reason \nExample: `$treasury -30 -30 -29 Jenny for Fair` or with 1 argument: 1) 'total'")
    
    member = await context.guild.fetch_member(activator.ID)
    
    bolts = int(context.args[0])
    planks = int(context.args[1])
    duct_tapes = int(context.args[2])
    reason = " ".join(context.args[3:])
    
    sheet = workbook.worksheet("Form Responses");
    
    column_b = sheet.col_values(2) 
    next_row = len(column_b) + 1
    sheet.update_cell(next_row, 2, member.name)
    
    column_c = sheet.col_values(3) 
    next_row = len(column_c) + 1
    sheet.update_cell(next_row, 3, bolts)
    
    column_d = sheet.col_values(4) 
    next_row = len(column_d) + 1
    sheet.update_cell(next_row, 4, planks)
    
    column_e = sheet.col_values(5) 
    next_row = len(column_e) + 1
    sheet.update_cell(next_row, 5, duct_tapes)
    
    column_f = sheet.col_values(7) 
    next_row = len(column_f) + 1
    sheet.update_cell(next_row, 7, reason)

    await context.send(f"I have sent in your treasury record update with:\n{bolts} bolts\n{planks} planks\n{duct_tapes} duct tape\nFor the following reason: {reason}", reply=True)
    
    
@command_handler.Scheduled("13:05")
async def schedule_test(client):
    guild = client.get_guild(FF.guild);
    bc = await guild.fetch_channel(704366328089280623)
    await bc.send("This is a test of the new scheduled command system. This command was scheduled for 1:05pm");

@command_handler.Uncontested(type = "MESSAGE", desc = "If a message contains the word greg, Greg will react with an emoji", priority = 2, generic = True)
async def greg_react(context: Context):
    neighbor = Neighbor(context.author.id, context.guild.id);
    if unicodes["star"] in context.content.lower():
        await context.react(unicodes["star"]);
    if "rose" in context.content.lower() or "159985870458322944" in context.content:
        neighbor = Neighbor(context.author.id, context.guild.id);
        if not neighbor.get_item_of_name("Hype Man"):
            await context.react("\U0001F92C");
        else:
            await context.react("\U0001F615");
    elif "greg" in context.content.lower() or "691338084444274728" in context.content:
        neighbor = Neighbor(context.author.id, context.guild.id);
        if not neighbor.get_item_of_name("Hype Man"):
            await context.react("\U0001F914");
        else:
            await context.react("\U00002764");
    if chance(50000):
        await context.react("🐄")
        def key(ctx):
            if not ctx.message.id == context.message.id:
                return False;
            if not ctx.emoji.name == "🐄":
                return False;
            return True;
        ResponseRequest(special_reaction, "cow", "REACTION", context, context, key);
    elif chance(50000):
        await context.react("🪵")
        def key(ctx):
            if not ctx.message.id == context.message.id:
                return False;
            if not ctx.emoji.name == "🐄":
                return False;
            return True;
        ResponseRequest(special_reaction, "cow", "REACTION", context, context, key);

    if "greg greg greg" in context.content.lower():
        await context.send("I've been summoned!", reply = True);
        
    if chance(5000):
        if chance(25):
            await context.send("Hm... I was going to send a gif for y'all to enjoy but I don't feel you've been grateful of my antics recently.\nReflect on that.")
        else:
            import re

            def last_word_alpha(s: str) -> str | None:
                # Returns the last "word" made of letters/numbers/underscore.
                m = re.findall(r"\b\w+\b", s)
                return m[-1] if m else None
            keyword = last_word_alpha(context.content)
            target = await context.send(f"$gif {keyword}")
            await gif(Neighbor(691338084444274728), Context(target))
            
    if any(x in set(["67", "6️⃣7", "67️⃣", "6️⃣7️⃣", "6 7", "6️⃣ 7️⃣", ":six::seven:", ":six: :seven:", "6 :seven:", ":six: 7", ":six:7", "6:seven:"]) for x in context.content.lower().split()):
        await context.react("🤷‍♂️")
        
    if chance(10000):
        if chance(25):
            await context.send("Hm... I was going to send a meme for y'all to enjoy but I don't feel you've been grateful of my antics recently.\nReflect on that.")
        else:
            await context.send("Hi, enjoy this meme 🙂")
            target = await context.send("$meme")
            await meme(Neighbor(691338084444274728), Context(target))

@command_handler.Uncontested(type = "MESSAGE")
async def waitlist_name_replacement(context: Context):
    if context.channel.id in [1101572888437477427, 932008962809794620, 1072605841267626025, 1172210561644232794, 1072605891431514203, 1334666607246708776, 1342334582963568661]:
        candidates = [x.nick for x in context.guild.members if not x.nick is None];
        candidates.extend([x.name for x in context.guild.members if (x.nick is None) or (not x.nick == x.name)]);

        name, confidence = best_string_match(context.tokens[0], [str(x) for x in candidates]);
        # print(name);
        target = discord.utils.get(context.guild.members, display_name = name);
        target = target if not target is None else discord.utils.get(context.guild.members, name = name);
    
        await context.send(f"{context.content}\n\n-# added by <@{context.author_id}>\n-# *{context.tokens[0]} might refer to: <@{target.id}> (confidence: {(confidence * 100): .2f}%)*")
        await context.message.delete();
        #        await context.send(f"{context.content}\n\nAdded by: <@{context.author_id}>\n*{context.content.split()[0]} might refer to: <@{target.id}> (confidence: {(confidence * 100): .2f}%)*")


@command_handler.Command(AccessType.PRIVILEGED, desc = "Get all messages that fit a particular criteria")
async def get(activator: Neighbor, context: Context):
    
    if context.args[0] == "msg":
    
        has = False;
        channel = False;
        author = False;
        count = False;
        author_role = False;
        
        if "has" in context.args:
            has = context.args[context.args.index("has")+1]
        
        if "in" in context.args:
            channel = int(context.args[context.args.index("in")+1])
        
        if "by" in context.args:
            author = int(context.args[context.args.index("by")+1])
            
        if "with" in context.args:
            author_role = int(context.args[context.args.index("with")+1])
        
        if "-" in context.args:
            count = int(context.args[context.args.index("-")+1])
        
        if "all" in context.args:
            count = 99;
        
        guild = context.guild;
        
        matching_messages = []
        
        if not guild:
            return []  # Guild not found
        
        channels = [guild.get_channel(channel)] if channel else guild.text_channels
        
        for channel in channels:
            # Ensure the channel is a text channel where messages can be searched
            if isinstance(channel, discord.TextChannel):
                try:
                    # Asynchronously fetch messages from the channel
                    async for message in channel.history(limit=10 if count is False else count):
                        # Check if the message fits all provided criteria
                        if has and has not in message.content:
                            continue
                        if author and message.author.id != author: # and not any(role for role in author.roles if role.id == author_role):
                            continue
                        
                        matching_messages.append(message)
                except discord.Forbidden:
                    # The bot lacks permissions to read message history in this channel
                    continue

        res = "";
        for i, message in enumerate(matching_messages):
            res += f"<@{message.author.id}>. {message.content}\n";
            
        await context.send(res);
    

@command_handler.Command(AccessType.PRIVATE, desc = "Find someone's tag")
async def find(activator: Neighbor, context: Context):

    target = context.args[0]

    candidates = [x.nick for x in context.guild.members if not x.nick is None];
    candidates.extend([x.name for x in context.guild.members if (x.nick is None) or (not x.nick == x.name)]);

    name, confidence = best_string_match(context.args[0], [str(x) for x in candidates]);
    # print(name);
    target = discord.utils.get(context.guild.members, display_name = name);
    target = target if not target is None else discord.utils.get(context.guild.members, name = name);

    await context.send(f"{context.args[0]} might refer to: <@{target.id}> (confidence: {(confidence * 100): .2f}%)")


@command_handler.Uncontested(type="MESSAGE", desc="counting game")
async def counting_game(context: Context):
    channel_game_state = {};
    
    # Ensure the game only runs in the designated channel
    if context.channel.id != 1184669547505131641:
        return

    # Prevent the bot itself from participating
    if context.message.author.id == 691338084444274728:
        return

    # Initialize the game state for the channel if not already present
    if context.channel.id not in channel_game_state:
        last = [message async for message in context.channel.history(limit=1)][0];
        try:
            last = int(last.content)
            channel_game_state[context.channel.id] = {"expected_number": last + 1, "last_author_id": None}
        except (ValueError, IndexError):
            channel_game_state[context.channel.id] = {"expected_number": 1, "last_author_id": None}


    # Retrieve the current state for the channel
    state = channel_game_state[context.channel.id]

    try:
        # Parse the user's message as an integer
        current_number = int(context.message.content)

        # Check if the number is out of sequence or the same user posted consecutively
        if current_number != state["expected_number"] or context.message.author.id == state["last_author_id"]:
            await context.send("Whoops! Someone messed up. Gonna have to start over. #sorrynotsorry")
            await context.send("1")
            state["expected_number"] = 2  # Reset the counter to the next number
            state["last_author_id"] = None  # Reset the last user
        else:
            # Update the state with the next expected number and the current author
            state["expected_number"] += 1
            state["last_author_id"] = context.message.author.id
    except ValueError:
        # If the message isn't a valid number, delete it
        await context.message.delete()



@command_handler.Uncontested(type = "MESSAGE", desc = "whatever", generic = True)
async def handle_message_requests(context: Context):
    await ResponseRequest.fulfill_message_requests(context.message, context, Neighbor(context.author.id, context.guild.id));

@command_handler.Uncontested(type = "REACTION", desc = "whatever", generic = True)
async def handle_reaction_requests(context: Context):
    await ResponseRequest.fulfill_reaction_requests(context.reaction, context, Neighbor(context.user.id, context.guild.id));

@command_handler.Uncontested(type = "MESSAGE", desc = "Uses stored expectations to appropriately respond to user messages and reactions.", priority = 1, generic=True)
async def handle_message_expectations(context: Context):
    global active_expectations;
    active_expectations = [x for x in active_expectations if not x.is_expired()];
    expectations_met = [x for x in active_expectations if x.is_match("MESSAGE", context)];
    for expectation in expectations_met:
        kwargs = expectation.values.copy();
        kwargs[expectation.fulfills] = (context.content, expectation);
        await expectation.func(Neighbor(context.author_id, context.guild.id), expectation.activation_context, **kwargs);

@command_handler.Uncontested(type = "REACTION", desc = "Uses stored expectations to appropriately respond to user messages and reactions.", priority = 1, generic=True)
async def handle_reaction_expectations(context: Context):
    global active_expectations;
    active_expectations = [x for x in active_expectations if not x.is_expired()];
    expectations_met = [x for x in active_expectations if x.is_match("REACTION", context)];
    for expectation in expectations_met:
        kwargs = expectation.values.copy();
        kwargs[expectation.fulfills] = (context.emoji, expectation);
        if expectation.func.__name__ == "on_member_join":
            await expectation.func(member=expectation.activation_context.author, **kwargs)
        else:
            await expectation.func(Neighbor(expectation.activation_context.author_id, expectation.activation_context.guild.id), expectation.activation_context, **kwargs);

@command_handler.Uncontested(type = "MESSAGE", desc = "Removes bad words.", priority = 1)
async def handle_bad_words(context: Context):
    detected = [x for x in context.content.split() if x in swear_words];
    if len(detected) > 0:
        audit_channel = await context.guild.fetch_channel(FF.audit_channel);
        await audit_channel.send(f"<@&{FF.leaders_role}> Be advised: a message from <@{context.author_id}> was deleted:")
        await audit_channel.send(f'"{context.content}"');
        await context.message.delete();

@command_handler.Uncontested(type = "MESSAGE", desc = "Incrememnts a Neighbor's server XP each time they send a message.", priority = 2, generic = True)
async def message_xp(context: Context):

    neighbor = Neighbor(context.author_id, context.guild.id);

    neighbor.expire_items();
    if neighbor.get_item_of_name("Message XP Cooldown"):
        return;

    if neighbor.get_item_of_name("Tracker"):
        tracker_item = neighbor.get_item_of_name("Tracker");
        neighbor.vacate_item(tracker_item);

    if neighbor.get_item_of_name("Activity-Streak XP Boost"):
        booster = neighbor.get_item_of_name("Activity-Streak XP Boost");
        last_updated = int(booster.get_value("last"));
        if time.time() > last_updated + 86400 and time.time() < last_updated + 86400 * 2:
            current_value = int(booster.get_value("val"));
            new_booster = booster;
            new_booster.update_value("val", (current_value + 1) if current_value < 6 else 6);
            new_booster.update_value("last", int(time.time()));
            neighbor.update_item(new_booster);
        elif time.time() > last_updated + 86400:
            new_booster = booster;
            new_booster.update_value("val", 0);
            new_booster.update_value("last", int(time.time()));
            neighbor.update_item(new_booster);
    else:
        booster = Item("Activity-Streak XP Boost", "retract", -1, last = int(time.time()), val = 0, hidden = "True");
        neighbor.bestow_item(booster);

    list_of_possibilites = [];

    for i in range(1, 11):
        for ii in range(i):
            list_of_possibilites.append(i * 10);

    # print(list_of_possibilites);
    choice = random.choice(list_of_possibilites);

    add = 0;
    for booster in neighbor.get_items_of_type("multiplier"):
        mult = int(booster.get_values("multiplier"));
        add += mult * choice;

    if neighbor.get_item_of_name("Higher XP I"):
        add += choice * 1.25;

    if neighbor.get_item_of_name("Higher XP II"):
        add += choice * 1.5;

    if neighbor.get_item_of_name("Higher XP III"):
        add += choice * 1.75;

    if neighbor.get_item_of_name("Higher XP IV"):
        add += choice * 2;

    milestone_boost = neighbor.get_item_of_name("Milestone Boost");
    if milestone_boost:
        add += choice * (int(milestone_boost.get_value("boost")) / 100);

    choice += add;
    global xp_gained
    if xp_happy_hour != 1:

        choice *= xp_happy_hour;
        xp_gained += choice;

    # spam prevention:
    try:
        with open("last_sender.txt", "r") as fLast:
            last_sender = fLast.readline();
            if str(context.author_id) in last_sender:
                choice *= .5;
    except:
        print("couldn't read file");

    if len(context.content) < 10:
        choice *= len(context.content) / 3
    # elif len(context.args) < 3:
    #     choice *= len(context.args) / 1.5

    with open("recent_messages.txt", 'r') as fRecent:
        # Read all lines of the file into a list
        lines = fRecent.readlines()

        # Join the lines into a single string and replace new line characters with spaces
        text = ' '.join([line.strip() for line in lines])

    if context.content in text:
        choice *= .5

    while choice > 275:
        choice -= 50;

    if choice < 1:
        return

    print("Message gets: " + str(choice));
    await inc_xp(neighbor, int(choice), context);

    try:
        family_info = {
            "butterflies": 0,
            "cheetahs": 0,
            "foxes": 0,
            "horses": 0,
            "puppies": 0};
        with open('families.txt', 'r') as fFams:
            lines = fFams.readlines();
            family_info["butterflies"] = int(lines[0][:-1]);
            family_info["cheetahs"] = int(lines[1][:-1]);
            family_info["foxes"] = int(lines[2][:-1]);
            family_info["horses"] = int(lines[3][:-1]);
            family_info["puppies"] = int(lines[4][:-1]);

        member = await context.guild.fetch_member(neighbor.ID);
        fam = get_family_from_user(member)
        if fam == '0':
            pass;
        elif fam == 'B':
            family_info["butterflies"] = family_info["butterflies"] + int(choice);
        elif fam == 'C':
            family_info["cheetahs"] = family_info["cheetahs"] + int(choice);
        elif fam == 'F':
            family_info["foxes"] = family_info["foxes"] + int(choice);
        elif fam == 'H':
            family_info["horses"] = family_info["horses"] + int(choice);
        elif fam == 'P':
            family_info["puppies"] = family_info["puppies"] + int(choice);

        with open("families.txt", "w") as fFams:
            fFams.write(str(family_info["butterflies"]) + "\n");
            fFams.write(str(family_info["cheetahs"]) + "\n");
            fFams.write(str(family_info["foxes"]) + "\n");
            fFams.write(str(family_info["horses"]) + "\n");
            fFams.write(str(family_info["puppies"]) + "\n");
    except Exception as e:
        traceback.print_exc();


    neighbor.bestow_item(Item("Message XP Cooldown", "XP Cooldown", int(time.time() + 60)));
    with open("last_sender.txt", "w") as fLast:
        fLast.write(str(context.author_id));

    with open("recent_messages.txt", 'a') as fRecent:
        # Append the string to the file
        fRecent.write(" " + context.content);

    with open("recent_messages.txt", 'r') as fRecent:
        # Read the file contents into a list of words
        words = fRecent.read().split()

    if len(words) > 1000:
        words = words[-1000:]
        with open("recent messages", 'w') as file:
            file.write(' '.join(words))

    best_this_month = neighbor.get_item_of_name("Best Level This Month");
    if best_this_month:
        if neighbor.get_level() > int(best_this_month.get_value("level")):
            best_this_month.update_value("level", neighbor.get_level());
            try:
                free_count = best_this_month.get_value("free_count");
            except:
                best_this_month.add_value("free_count", 0);
            neighbor.update_item(best_this_month);
    else:
        best_this_month = Item("Best Level This Month", "monthly", -1, level = neighbor.get_level(), free_count = 0, hidden = "true");
        neighbor.bestow_item(best_this_month);

@command_handler.Uncontested(type = "REACTION", desc = "Incrememnts a Neighbor's server XP each time they send a reaction.", priority = 2, generic = True)
async def reaction_xp(context: Context):

    neighbor = Neighbor(context.author_id, context.guild.id);

    neighbor.expire_items();
    if neighbor.get_item_of_name("Reaction XP Cooldown"):
        print("Stopping you from react xp")
        return;

    if neighbor.get_item_of_name("Activity-Streak XP Boost"):
        booster = neighbor.get_item_of_name("Activity-Streak XP Boost");
        last_updated = int(booster.get_value("last"));
        if time.time() > last_updated + 86400 and time.time() < last_updated + 86400 * 2:
            current_value = int(booster.get_value("val"));
            new_booster = booster;
            new_booster.update_value("val", (current_value + 1) if current_value < 6 else 1);
            new_booster.update_value("last", int(time.time()));
            neighbor.update_item(new_booster);
        elif time.time() > last_updated + 86400:
            new_booster = booster;
            new_booster.update_value("val", 0);
            new_booster.update_value("last", int(time.time()));
            neighbor.update_item(new_booster);
    else:
        booster = Item("Activity-Streak XP Boost", "retract", -1, last = int(time.time()), val = 0);
        neighbor.bestow_item(booster);

    list_of_possibilites = [];

    for i in range(1, 11):
        for ii in range(i):
            list_of_possibilites.append(i);

    # print(list_of_possibilites);
    choice = random.choice(list_of_possibilites);

    add = 0;
    for booster in neighbor.get_items_of_type("multiplier"):
        mult = int(booster.get_values("multiplier"));
        add += mult * choice;

    choice += add;
    global xp_gained
    if xp_happy_hour != 1:

        choice *= xp_happy_hour;
        xp_gained += choice;

    # print(choice)

    await inc_xp(neighbor, int(choice), context);
    print("Reaction gets: " + str(choice));

    neighbor.bestow_item(Item("Reaction XP Cooldown", "XP Cooldown", int(time.time() + 60)));

@command_handler.Uncontested(type = "MESSAGE", desc = "Incrememnts a Neighbor's server XP each time they send a celebrate or welcome.", priority = 2, generic = True)
async def celebrate_xp(context: Context):

    if not (context.content.startswith("$celebrate") or context.content.startswith("$welcome")):
        return;

    neighbor = Neighbor(context.author_id, context.guild.id);

    neighbor.expire_items();
    if neighbor.get_item_of_name("Celebrate XP Cooldown"):
        print("Stopping you from celebrate xp")
        return;

    if neighbor.get_item_of_name("Activity-Streak XP Boost"):
        booster = neighbor.get_item_of_name("Activity-Streak XP Boost");
        last_updated = int(booster.get_value("last"));
        if time.time() > last_updated + 86400 and time.time() < last_updated + 86400 * 2:
            current_value = int(booster.get_value("val"));
            new_booster = booster;
            new_booster.update_value("val", (current_value + 1) if current_value < 6 else 1);
            new_booster.update_value("last", int(time.time()));
            neighbor.update_item(new_booster);
        elif time.time() > last_updated + 86400:
            new_booster = booster;
            new_booster.update_value("val", 0);
            new_booster.update_value("last", int(time.time()));
            neighbor.update_item(new_booster);
    else:
        booster = Item("Activity-Streak XP Boost", "retract", -1, last = int(time.time()), val = 0);
        neighbor.bestow_item(booster);

    list_of_possibilites = [];

    for i in range(1, 11):
        for ii in range(i):
            list_of_possibilites.append(i);

    # print(list_of_possibilites);
    choice = random.choice(list_of_possibilites);

    add = 0;
    for booster in neighbor.get_items_of_type("multiplier"):
        mult = int(booster.get_values("multiplier"));
        add += mult * choice;

    choice += add;
    global xp_gained
    if xp_happy_hour != 1:

        choice *= xp_happy_hour;
        xp_gained += choice;

    # print(choice)

    await inc_xp(neighbor, int(choice), context);
    print("Celebrate gets: " + str(choice));

    neighbor.bestow_item(Item("Celebrate XP Cooldown", "XP Cooldown", int(time.time() + 3600)));

@command_handler.Uncontested(type = "MESSAGE")
async def blincoln(context: Context):
    if "blincoln" in context.content.lower():
        await context.message.delete();
        await context.send("stop that");

async def harvest_xp(context: Context):

    if not context.content.startswith("$harvest"):
        return;

    neighbor = Neighbor(context.author_id, context.guild.id);

    neighbor.expire_items();

    list_of_possibilites = [];

    for i in range(1, 11):
        for ii in range(i):
            list_of_possibilites.append(i);

    # for booster in neighbor.get_items_of_type("expand"):
    #     val = int(booster.get_value("val"));
    #     for i in range(11, val + 1):
    #         for ii in range(i):
    #             list_of_possibilites.append(i);

    for booster in neighbor.get_items_of_type("retract"):
        val = int(booster.get_value("val"));
        for i in range(val):
            list_of_possibilites = list_of_possibilites[1:];

    # print(list_of_possibilites);
    choice = random.choice(list_of_possibilites);

    add = 0;
    for booster in neighbor.get_items_of_type("multiplier"):
        mult = int(booster.get_values("multiplier"));
        add += mult * choice;

    choice += add;
    global xp_gained
    if xp_happy_hour != 1:

        choice *= xp_happy_hour;
        xp_gained += choice;

    print("Harvest gets: " + str(choice))

    await inc_xp(neighbor, int(choice), context);

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

@command_handler.Uncontested(type = "MESSAGE", desc = "If a Neighbor has the Hype Man item, which can be purchased in the rss, then Greg will react to the Neighbor's messages with an emoji.", priority = 2)
async def hype_man_responses(context: Context):
    neighbor = Neighbor(context.author_id, context.guild.id);
    neighbor.expire_items();
    if not neighbor.get_item_of_name("Hype Man"):
        return;

    if random.choices([True, False], weights=[0.01, 0.99])[0]:
        target = await context.send(f"$celebrate <@{context.author.id}>");
        celebrate_context = Context(message = target);
        await celebrate(neighbor, celebrate_context);
    elif random.choices([True, False], weights=[0.02, 0.98])[0]:
        await context.send(f"Yeah, listen to what <@{context.author_id}> said! They're the real deal!")
    elif random.choices([True, False], weights=[0.02, 0.98])[0]:
        await context.send(f"Listen up!! Da real <@{context.author_id}> is in the chat!")
    elif random.choices([True, False], weights=[0.05, 0.95])[0]:
        await context.react("\U0001F973");
    elif random.choices([True, False], weights=[0.02, 0.98])[0]:
        await context.send(f"Sup <@{context.author_id}>! You know I love ya!")
    elif random.choices([True, False], weights=[0.05, 0.95])[0]:
        await context.react("\U0001F64C");
    elif random.choices([True, False], weights=[0.05, 0.95])[0]:
        await context.react("\U0001F44F");

async def special_reaction(neighbor, context, response: ResponsePackage):
    if response.name == "cow":
        await context.send("Omg! Thank you so much :) You found my lost cow. I've been looking for her for a long time. For your kindess, resilience, and bravery, enjoy this prize of 5k xp");

        await inc_xp(neighbor, 5000, context);

@command_handler.Uncontested(type = "MESSAGE", desc = "Junior")
async def junior_requirement(context: Context):
    if context.channel.id == 704366328089280623:
        try:
            level = int(context.message.content)
            req = level * 40
            await context.send(f"{req}", reply = True);
        except:
            print("not a number");

# @command_handler.Loop(hours=1)
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
        
            
        


@command_handler.Uncontested(type = "REACTION", desc = "Market", generic = True)
async def farmers_market_reaction(context: Context):
    print("at market")
    #phoenix_market
    if context.guild.id == FF.guild:
        with open("market.txt", "r") as fMarket:
            market_channel_id = int(fMarket.readline());
            # print(market_channel_id);
            if context.channel.id != market_channel_id:
                print("not matching id");
                return;
            message_id = int(fMarket.readline());
            # print(message_id);
            if context.message.id != message_id:
                print("not matching message")
                return;

            options = [];
            lines = fMarket.readlines();
            for i, line in enumerate(lines):
                print(f"{i}: {line}");
                if not i % 3 == 0:
                    continue;
                name = line[:-1];
                amt = int(lines[i + 1][:-1]);
                price = int(lines[i + 2][:-1]);
                option = (name, amt, price);
                print(option);
                options.append((name, amt, price));

        print([f"{option[0]} {option[1]} {option[2]}" for option in options]);
        choice = -1;
        emoji = str(context.emoji)
        if emoji == unicodes[0]:
            choice = 0;
        elif emoji == unicodes[1]:
            choice = 1;
        elif emoji == unicodes[2]:
            choice = 2
        elif emoji == unicodes[3]:
            choice = 3
        elif emoji == unicodes[4]:
            choice = 4

        print("User chose: " + str(choice));
        if choice > -1 and choice < 5:
            pass;
        else:
            return;

        neighbor = Neighbor(context.user.id, context.guild.id);
        silo_item = neighbor.get_item_of_name("Silo");
        sale = options[choice];
        name = sale[0];
        amt = sale[1];
        price = sale[2];
        cur_amt = int(silo_item.get_value(name));
        if int(cur_amt) >= amt:
            silo_item.update_value(name, cur_amt - amt);
            neighbor.update_item(silo_item);
            await inc_xp(neighbor, price, context);
            bc = await context.guild.fetch_channel(FF.bot_channel);
            if neighbor.get_item_of_name("Pings Off"):
                await bc.send("Someone just sold {amt} {name}(s)? for {price}xp at the farmers market!");
            else:
                await bc.send(f"<@{neighbor.ID}> just sold {amt} {name}(s)? for {price}xp at the farmers market!");
        else:
            bc = await context.guild.fetch_channel(FF.bot_channel);
            if neighbor.get_item_of_name("Pings Off"):
                await bc.send(f"Whoops! Someone just attempted to sell {amt} {name}(s)? for {price}xp at the farmers market! But Failed!");
            else:
                await bc.send(f"Whoops! <@{neighbor.ID}> just attempted to sell {amt} {name}(s)? for {price}xp at the farmers market! But Failed!");

    elif context.guild.id == PHOENIX.guild:
        with open("phoenix_market.txt", "r") as fMarket:
            market_channel_id = int(fMarket.readline());
            # print(market_channel_id);
            if context.channel.id != market_channel_id:
                return;
            message_id = int(fMarket.readline());
            # print(message_id);
            if context.message.id != message_id:
                return;

            options = [];
            lines = fMarket.readlines();
            for i, line in enumerate(lines):
                print(f"{i}: {line}");
                if not i % 3 == 0:
                    continue;
                name = line[:-1];
                amt = int(lines[i + 1][:-1]);
                price = int(lines[i + 2][:-1]);
                option = (name, amt, price);
                print(option);
                options.append((name, amt, price));

        print([f"{option[0]} {option[1]} {option[2]}" for option in options]);
        choice = -1;
        emoji = str(context.emoji)
        if emoji == unicodes[0]:
            choice = 0;
        elif emoji == unicodes[1]:
            choice = 1
        elif emoji == unicodes[2]:
            choice = 2
        elif emoji == unicodes[3]:
            choice = 3
        elif emoji == unicodes[4]:
            choice = 4

        print("choice was " + str(choice));
        if choice > -1 and choice < 5:
            pass;
        else:
            return;

        neighbor = Neighbor(context.user.id, context.guild.id);
        silo_item = neighbor.get_item_of_name("Silo");
        sale = options[choice];
        name = sale[0];
        amt = sale[1];
        price = sale[2];
        cur_amt = int(silo_item.get_value(name));
        if int(cur_amt) >= amt:
            silo_item.update_value(name, cur_amt - amt);
            neighbor.update_item(silo_item);
            await inc_xp(neighbor, price, context);
            bc = await context.guild.fetch_channel(PHOENIX.bot_channel);
            await bc.send(f"<@{neighbor.ID}> just sold {amt} {name}(s)? for {price}xp at the farmers market!");
        else:
            bc = await context.guild.fetch_channel(PHOENIX.bot_channel);
            await bc.send(f"Whoops! <@{neighbor.ID}> just attempted to sell {amt} {name}(s)? for {price}xp at the farmers market! But Failed!");

# @command_handler.Uncontested(type = "EDIT", desc = "Alerts that a member left the server.", priority = 3)
async def on_edit(context: Context):

    similarity = difflib.SequenceMatcher(None, context.before.content, context.after.content).ratio();
    if similarity < .75:
        audit_channel = context.guild.fetch_channel(context.ID_bundle.audit_channel);
        before_content = convert_mentions_to_text(context, context.before.content);
        after_content = convert_mentions_to_text(context, context.after.content)
        text = f"*A message from <@{context.author_id}> ({context.author}) was edited:*\n> {before_content}\n\n> {after_content}";
        await audit_channel.send(text);

# @command_handler.Uncontested(type = "DELETE", desc = "Alerts that a member left the server.", priority = 3)
async def on_delete(context: Context):
    audit = await context.fetch_channel("audit_channel");
    text = f"*A message from <@{context.author_id}> ({context.author}) was deleted:*\n> {context.content}";
    await audit.send(text);

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


@command_handler.Command(access_type=AccessType.PRIVATE)
async def points_double_check(activator: Neighbor, context: Context):
    """
    Sender = message.author (Member)
    Receiver = first user mention in message.content (reply-mentions ignored)

    Scoring:
      - Only the first @mention in content counts
      - Same-family: 0 points; does NOT mark 'already received'
      - Cross-family (counted): sender +3; receiver +1 (first counted) else +2
      - Per-sender cap: only first TWO counted sends award points
      - 'Already received' is based ONLY on prior COUNTED receives

    Output per family:
      - Total points
      - Unique Sender # (≥1 counted send)
      - Total Sender # (counted sends)
      - Unique Receiver # (≥1 counted receive, i.e., receivers in that family)
      - Total Receiver # (counted receives for that family)
      - Unique Targets # (distinct users this family sent counted notes to)
      - Then a separate line per family listing their targets as <@id>×count
      - Final line: total number of multiple-mention messages in content (no notices sent)
    """
    import re

    DEFAULT_CHANNEL_ID = 1403141598300082317
    STOP_AT_ID = 1404676398232113212  # stop when this message is reached (exclusive)
    chan_id = None

    # Optional arg: channel id or channel mention; else default
    if getattr(context, "args", None):
        raw = str(context.args[0]).strip()
        try:
            if raw.startswith("<#") and raw.endswith(">"):
                chan_id = int(raw[2:-1])
            else:
                chan_id = int(raw)
        except Exception:
            chan_id = None
    chan_id = chan_id or DEFAULT_CHANNEL_ID

    channel = await context.guild.fetch_channel(chan_id)
    final_msg = await context.send(f"Double-checking notes in <#{chan_id}>…")

    # --- Scoreboards ---
    fam_points = {"B": 0, "C": 0, "G": 0, "P": 0, "S": 0, "Z": 0}
    names = {
        "B": "Butterflies",
        "C": "Cows",
        "G": "Guinea Pigs",
        "P": "Puppies",
        "S": "Squirrels",
        "Z": "Zebras",
    }

    # Per-family counted breakdowns
    fam_total_sends = {k: 0 for k in fam_points}            # counted sends by family
    fam_total_receives = {k: 0 for k in fam_points}         # counted receives by family
    fam_unique_senders = {k: set() for k in fam_points}     # users with ≥1 counted send
    fam_unique_receivers = {k: set() for k in fam_points}   # users with ≥1 counted receive (in that family)
    fam_unique_targets = {k: set() for k in fam_points}     # distinct receiver IDs this family sent to
    fam_target_counts = {k: {} for k in fam_points}         # receiver_id -> times targeted by this family

    # Global per-user trackers (COUNTED-only)
    sent_counts_counted = {}   # user_id -> counted sends so far (enforce cap)
    received_counted = {}      # user_id -> counted receives so far (drives +2 for repeats)

    USER_MENTION_RE = re.compile(r"<@!?(\d+)>")

    def first_user_mention_from_content(text: str):
        if not text:
            return None, 0
        all_ids = USER_MENTION_RE.findall(text)
        if not all_ids:
            return None, 0
        return int(all_ids[0]), len(all_ids)

    # Diagnostics (summary only; no notices)
    multi_mention_count = 0

    # ---- scoring helper ----
    def score_pair(sender_member, receiver_member):
        nonlocal fam_points, fam_total_sends, fam_total_receives
        nonlocal fam_unique_senders, fam_unique_receivers, fam_unique_targets, fam_target_counts
        nonlocal sent_counts_counted, received_counted

        sender_id = sender_member.id
        receiver_id = receiver_member.id

        send_fam = get_family_from_user(sender_member)
        recv_fam = get_family_from_user(receiver_member)
        send_fam = send_fam if send_fam and send_fam != "0" else None
        recv_fam = recv_fam if recv_fam and recv_fam != "0" else None
        if not send_fam or not recv_fam:
            return  # skip silently

        if send_fam == recv_fam:
            return  # same-family: no score, no history mark

        if sent_counts_counted.get(sender_id, 0) >= 2:
            return  # sender over cap

        sender_points = 3
        receiver_points = 2 if received_counted.get(receiver_id, 0) >= 1 else 1

        fam_points[send_fam] += sender_points
        fam_points[recv_fam] += receiver_points

        fam_total_sends[send_fam] += 1
        fam_unique_senders[send_fam].add(sender_id)
        fam_unique_targets[send_fam].add(receiver_id)
        fam_target_counts[send_fam][receiver_id] = fam_target_counts[send_fam].get(receiver_id, 0) + 1

        fam_total_receives[recv_fam] += 1
        fam_unique_receivers[recv_fam].add(receiver_id)

        sent_counts_counted[sender_id] = sent_counts_counted.get(sender_id, 0) + 1
        received_counted[receiver_id] = received_counted.get(receiver_id, 0) + 1

    # ---- 1) Manual pairs FIRST ----
    manual_pairs = [
        (963533131854532638, 516969515486019604),
        (1340578790690132061, 648229959973994506),
        (338436753771724810, 987955038804639744),
        (1156012904869527602, 430454367003475978),
        (863037754164903946, 648229959973994506),
        (1218778118630670376, 843118864379543562),
    ]

    for sid, rid in manual_pairs:
        try:
            sender_member = context.guild.get_member(sid) or await context.guild.fetch_member(sid)
            receiver_member = context.guild.get_member(rid) or await context.guild.fetch_member(rid)
        except Exception:
            continue
        if not sender_member or not receiver_member:
            continue
        score_pair(sender_member, receiver_member)

    # ---- 2) Scrape channel until STOP_AT_ID (exclusive) ----
    async for message in channel.history(limit=None, oldest_first=True):
        if message.id == STOP_AT_ID:
            break  # stop scraping when this message is reached (do not process it or anything older)

        # Ensure Member
        sender_member = message.guild.get_member(message.author.id)
        if sender_member is None:
            try:
                sender_member = await context.guild.fetch_member(message.author.id)
            except Exception:
                continue  # skip silently

        # First user mention in CONTENT only
        receiver_id, mention_count = first_user_mention_from_content(message.content or "")
        if receiver_id is None:
            continue  # no user mention in content

        if mention_count > 1:
            multi_mention_count += 1  # just count; no notice

        # Resolve receiver as Member
        try:
            receiver_member = message.guild.get_member(receiver_id) or await context.guild.fetch_member(receiver_id)
        except Exception:
            continue
        if not receiver_member:
            continue

        score_pair(sender_member, receiver_member)

    # Final output scoreboard
    lines = []
    for code in ["B", "C", "G", "P", "S", "Z"]:
        total_pts = fam_points[code]
        uniq_send = len(fam_unique_senders[code])
        tot_send = fam_total_sends[code]
        uniq_recv = len(fam_unique_receivers[code])
        tot_recv = fam_total_receives[code]
        uniq_targets = len(fam_unique_targets[code])

        lines.append(
            f"{names[code]}: {total_pts} — "
            f"Unique Senders #: {uniq_send} | Total Notes Sent #: {tot_send} | "
            f"Unique Receivers #: {uniq_recv} | Total Notes Received #: {tot_recv} | "
            f"Unique Note Targets #: {uniq_targets}"
        )

    # lines.append(f"(Multiple-mention messages in content: {multi_mention_count})")
    await final_msg.edit(content="\n".join(lines)[:1999])

    # # Then print per-family target lists as mentions with counts
    # for code in ["B", "C", "G", "P", "S", "Z"]:
    #     targets = fam_target_counts[code]
    #     if not targets:
    #         await context.send(f"Targets for {names[code]}: (none)")
    #         continue
    #     # Build " <@id>×n " list
    #     parts = [f"<@{rid}>×{cnt}" for rid, cnt in targets.items()]
    #     text = ", ".join(parts)
    #     # If it's long, Discord will split automatically; we can chunk if needed, but try once first:
    #     header = f"Targets for {names[code]}:"
    #     payload = f"{header} {text}"
    #     if len(payload) <= 1999:
    #         await context.send(payload)
    #     else:
    #         # Chunk conservatively
    #         await context.send(header)
    #         chunk = ""
    #         for seg in parts:
    #             seg2 = (seg + ", ")
    #             if len(chunk) + len(seg2) > 1990:
    #                 await context.send(chunk.rstrip(", "))
    #                 chunk = seg2
    #             else:
    #                 chunk += seg2
    #         if chunk:
    #             await context.send(chunk.rstrip(", "))

@command_handler.Command(access_type=AccessType.PRIVATE)
async def points(activator: Neighbor, context: Context):
    
    final_msg = await context.send("Scoring...");
    
    NOTES = True if context.author.id == 355169964027805698 and not len(context.args) > 0 else False;

    fam_points = {
        "B": 0,
        "C": 0,
        "G": 0,
        "P": 0,
        "S": 0,
        "Z": 0,
    }

    names = {
        "B": "Butterflies",
        "C": "Cows",
        "G": "Guinea Pigs",
        "P": "Puppies",
        "S": "Squirrels",
        "Z": "Zebras",
    }

    # Per-family breakdown of points sources
    fam_breakdown = {
        "B": {"sent": 0, "received": 0},
        "C": {"sent": 0, "received": 0},
        "G": {"sent": 0, "received": 0},
        "P": {"sent": 0, "received": 0},
        "S": {"sent": 0, "received": 0},
        "Z": {"sent": 0, "received": 0},
    }

    # Track participation counts (identical logic to original list.count(...) behavior)
    sent_counts = {}      # user_id -> times sent so far
    received_counts = {}  # user_id -> times received so far

    channel = await context.guild.fetch_channel(1403141598300082317)
    council_role = context.guild.get_role(648188387836166168)

    async for message in channel.history(limit=None, oldest_first=True):
        parts = message.content.split(":", 1)
        sender_id = int(parts[0])  # keep identical behavior: let this raise if malformed

        try:
            receiver_id = parse_mention(parts[1])
        except Exception:
            continue

        # Keep the exact same filter
        # if len(parts[1]) < 100:
        # if NOTES:
        #     await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; too short.")
            # continue

        sender = await context.guild.fetch_member(sender_id)
        receiver = await context.guild.fetch_member(receiver_id)

        send_fam = get_family_from_user(sender)
        receive_fam = get_family_from_user(receiver)

        # Preserve exact treatment of '0' as None
        send_fam = send_fam if send_fam != "0" else None
        receive_fam = receive_fam if receive_fam != "0" else None

        if not send_fam or not receive_fam:
            if NOTES:
                await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; no family")
            continue

        # ---- Point allocation (exact logic) ----
        sender_points_earned = 3
        receiver_points_earned = 1

        # Receiver gets +1 if they've received at least once before
        if received_counts.get(receiver_id, 0) >= 1:
            receiver_points_earned += 1

        # Same-family penalty: receiver gets negative of sender's earned points
        if send_fam == receive_fam:
            if NOTES:
                await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; sam family")
            continue
        
        # Cap after two sends (on the third and beyond, sender earns 0)
        if sent_counts.get(sender_id, 0) >= 2:
            if NOTES:
                await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nNot counted; more than 2 notes from sender")
            continue

        # Update totals
        fam_points[send_fam] += sender_points_earned
        fam_points[receive_fam] += receiver_points_earned
        council_role = context.guild.get_role(648188387836166168)
        if has_role(sender, council_role):
            await context.send(f"<@{sender_id}>")

        # Update breakdown logs
        fam_breakdown[send_fam]["sent"] += sender_points_earned
        fam_breakdown[receive_fam]["received"] += receiver_points_earned

        # Update participation counts AFTER computing this message's points
        sent_counts[sender_id] = sent_counts.get(sender_id, 0) + 1
        received_counts[receiver_id] = received_counts.get(receiver_id, 0) + 1
        
        if NOTES:
            await context.send(f"<@{sender_id}> send a note to <@{receiver_id}>\nSender gets {sender_points_earned}; Receicer gets {receiver_points_earned}")

    # Format output with breakdown
    lines = []
    for fam_code in ["B", "C", "G", "P", "S", "Z"]:
        total = fam_points[fam_code]
        sent_from_notes = fam_breakdown[fam_code]["sent"]
        received_from_notes = fam_breakdown[fam_code]["received"]
        lines.append(
            f"{names[fam_code]}: {total} "
            # f"({sent_from_notes} from notes sent; {received_from_notes} from notes received)"
        )

    formatted = "\n".join(lines)
    await final_msg.edit(content=formatted[:1999])
    

@command_handler.Uncontested(type="MESSAGE")
async def family_event(context: Context):
    if context.channel.id == 1402734412793122919:
        channel = await context.guild.fetch_channel(1403141598300082317);
        await channel.send(f"{context.author.id}: {context.message.content}")
        
    
# @command_handler.Loop(minutes=60) ADD BACK
async def long_time_members(client):
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
                # await member.add_roles(role_5_years);
                # await general.send(f"<@{member.id}> has been with FF over 5 years! Now that's serious dedication!!");
                # continue;
            
        # if check_member(member, 3*12):
        #     if role_3_years in member.roles:
        #         continue;
        #     else:
        #         await member.add_roles(role_3_years);
        #         await general.send(f"<@{member.id}> has been with FF over 3 years! Players such as yourself are central to who & what FF is! Love to have you and hope to keep you for more years to come :)");
        #         continue;
            
        # if check_member(member, 12):
        #     if role_1_year in member.roles:
        #         continue;
        #     else:
        #         await member.add_roles(role_1_year);
        #         await general.send(f"<@{member.id}> has been with FF over 1 year! FF veteran status for sure!");
        #         continue;
            
        # if check_member(member, 6):
        #     if role_6_months in member.roles:
        #         continue;
        #     else:
        #         await member.add_roles(role_6_months);
        #         await general.send(f"<@{member.id}> has been with FF over 6 months! Where would we be with you??");
        #         continue;
        
        # if check_member(member, 3):
        #     if role_3_months in member.roles:
        #         continue;
        #     else:
        #         await member.add_roles(role_3_months);
        #         await general.send(f"<@{member.id}> has been with FF over 3 months! You're still on the newer side but you know the ropes by now. We're glad to have you and hope you're glad to have us!");
        #         continue;
        
        
        
import datetime
import discord
import time
import re

# CONFIGURATION
LOCAL_UTC_OFFSET = -4  # EDT
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=LOCAL_UTC_OFFSET))
IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
DEBUG = True  # Enable debug print statements

def strip_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002500-\U00002BEF"
        "\U0001F191-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()

def get_recent_complete_rounds(n_rounds=12):
    now = datetime.datetime.now(LOCAL_TZ)
    weekday = now.weekday()  # Monday = 0
    days_since_monday = (weekday - 0) % 7
    last_monday = now - datetime.timedelta(days=days_since_monday)
    last_monday = last_monday.replace(hour=23, minute=59, second=59, microsecond=999999)

    rounds = []
    for i in range(n_rounds):
        round_end = last_monday - datetime.timedelta(weeks=i)
        round_start = round_end - datetime.timedelta(days=6)
        round_start = round_start.replace(hour=0, minute=0, second=0, microsecond=0)
        rounds.append((round_start, round_end))

    rounds = rounds[::-1]

    if DEBUG:
        print("📆 Generated Round Windows:")
        for idx, (start, end) in enumerate(rounds):
            print(f"  Round {idx+1}: {start} → {end}")

    return rounds

async def fetch_images_by_rounds(channel, n_rounds=12):
    rounds = get_recent_complete_rounds(n_rounds)
    results = [[] for _ in rounds]

    oldest_time = rounds[0][0]
    newest_time = rounds[-1][1] + datetime.timedelta(seconds=1)

    if DEBUG:
        print(f"⏱ Fetching messages between {oldest_time} and {newest_time}")

    start_timer = time.time()
    async for message in channel.history(limit=None, oldest_first=True, before=newest_time):
        msg_time = message.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
        msg_time = msg_time.astimezone(LOCAL_TZ)

        if msg_time < oldest_time:
            continue

        if any(att.filename.lower().endswith(IMAGE_EXTS) for att in message.attachments):
            for i, (start, end) in enumerate(rounds):
                if start <= msg_time <= end:
                    results[i].append(message)
                    break

    if DEBUG:
        print(f"✅ Finished fetching in {time.time() - start_timer:.2f} seconds")

    return results

async def fetch_mess_ups(context, rounds):
    channel = await context.guild.fetch_channel(1403092988925575249)
    mess_up_map = {i: {} for i in range(len(rounds))}

    async for msg in channel.history(limit=None, oldest_first=True):
        parts = msg.content.strip().split()
        if len(parts) != 2:
            if DEBUG:
                print(f"❌ Invalid format: {msg.content}")
            continue

        try:
            member_id = int(parts[0])
            count = int(parts[1])
        except ValueError:
            if DEBUG:
                print(f"❌ Non-integer mess-up entry: {msg.content}")
            continue

        msg_time = msg.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
        msg_time = msg_time.astimezone(LOCAL_TZ)

        assigned = False
        if msg_time.weekday() == 0:  # Monday → current round
            for i, (start, end) in enumerate(rounds):
                if start <= msg_time <= end:
                    mess_up_map[i][member_id] = mess_up_map[i].get(member_id, 0) + count
                    assigned = True
                    break
        else:
            # Go to previous full round
            days_since_monday = (msg_time.weekday() - 0) % 7
            last_monday = msg_time - datetime.timedelta(days=days_since_monday)
            last_monday = last_monday.replace(hour=23, minute=59, second=59, microsecond=999999)

            for i, (start, end) in enumerate(rounds):
                if end == last_monday:
                    mess_up_map[i][member_id] = mess_up_map[i].get(member_id, 0) + count
                    assigned = True
                    break

        if DEBUG and not assigned:
            print(f"❓ Could not assign mess-up from {msg_time}: {msg.content}")

    if DEBUG:
        print("📉 Mess-Up Mapping:")
        for i, m in mess_up_map.items():
            if m:
                print(f"  Round {i+1}: {m}")
    return mess_up_map

@command_handler.Command(access_type=AccessType.PRIVATE)
async def ab_race(activator:Neighbor, context: Context):
    
    final_msg = await context.send("Scoring...", reply=True);
    
    channel = await context.guild.fetch_channel(1203772906497380472)
    message = await channel.fetch_message(1422340225035800626);
    
    position = 1;
    butterflies = [];
    cows = [];
    
    async for msg in channel.history(after=message,oldest_first=True, limit=None):
        if len(butterflies)==10 and len(cows)==10:
            break
        
        has_image = (
            any(att.content_type and att.content_type.startswith("image/") for att in msg.attachments) or
            any(embed.type == "image" or (embed.image and embed.image.url) for embed in msg.embeds)
        )
        
        if not has_image:
            continue;
        
        family = get_family_from_user(msg.author)
        
        if family == "B":
            if len(butterflies) < 10:
                butterflies.append(position);
            position+=1;
        if family == "C":
            if len(cows) < 10:
                cows.append(position);
            position+=1;
            
    butterflies_before_padding = sum(butterflies) + 7;
    cows_before_padding = sum(cows) + 8;
            
    while len(butterflies) < 10:
        butterflies.append(position)
        
    while len(cows) < 10:
        cows.append(position);
        
    butterflies_score = sum(butterflies) + 7
    cows_score = sum(cows) + 8
    
    result = "# A&B Race Scores!\n**Remember: Less Points = Better**\n\n"
    result += f"**Butterflies:** {str(butterflies_score)}pts\n";
    if butterflies_before_padding != butterflies_score:
        result += f"-# Only {butterflies_before_padding}pts are locked in. Final score will be *at least* {butterflies_score}pts\n";
    result += f"\n**Cows:** {str(cows_score)}pts\n";
    if cows_before_padding != cows_score:
        result += f"-# Only {cows_before_padding}pts are locked in. Final score will be *at least* {cows_score}pts";
        
    if butterflies_score == butterflies_before_padding and butterflies_score < cows_score:
        result += "\n# Projected Winners: Butterflies!!"
    elif cows_score == cows_before_padding and cows_score < butterflies_score:
        result += "\n# Projected Winners: Cows!!"
    else:
        result += "\n# Butterflies in the lead!" if butterflies_score < cows_score else "\n# Cows in the lead!" if cows_score < butterflies_score else "Tied so far!"
        
    result += "\n**Results are not official until submissions reviewed for legitimacy and points reviewed for accuracy. Greg can only know so much.**"
        
    await final_msg.edit(content=result)
            

def build_fixed_triplet_weights_pp(
    total_rounds: int,
    start: float = 1.00,      # 100%
    drop_pp: float = 0.06,    # 6 percentage points per tier
    group_size: int = 3,
    min_weight: float = 0.0   # clamp at 0 once it would go negative
) -> list[float]:
    """
    Build weights (oldest -> newest) where each 3-round tier drops by a fixed
    number of percentage points from the starting weight.

    Example (start=1.00, drop_pp=0.06):
      newest 3 rounds: 1.00
      prev   3 rounds: 0.94
      prev   3 rounds: 0.88
      ...

    We clamp at min_weight to avoid negative weights.
    """
    if total_rounds <= 0:
        return []
    weights = [0.0] * total_rounds
    idx = total_rounds - 1   # fill from most recent backwards
    tier = 0
    while idx >= 0:
        w = max(min_weight, start - tier * drop_pp)
        for _ in range(group_size):
            if idx < 0:
                break
            weights[idx] = w
            idx -= 1
        tier += 1
    return weights

# --- pro_leaderboard: all Pro members ranked ---

@command_handler.Command(access_type=AccessType.PUBLIC)
async def pro_leaderboard(activator: Neighbor, context: Context):
    """
    Pro leaderboard over most recent N rounds (default 18), with:
      - Fixed-triplet recency weights: last 3 @ 100%, previous 3 @ 94%, then 88%, 82%, ...
        (each tier is 6 percentage points lower, clamped at 0)
      - 'Drop worst' rule: for each user, the single worst raw round is set to 0 BEFORE weighting
      - Scoring per round:
          * If mess-ups present: (#participants + 1 + mess_ups)
          * Else if posted: average of their (position indices + 1)
          * Else: (#participants + 1)
    Output is ranked ascending (lower total is better).
    """

    # --- Args / Defaults ---
    if len(context.args) > 0 and context.args[0].isnumeric():
        n_rounds = int(context.args[0])
    else:
        n_rounds = 18  # default

    FINAL_msg = await context.send("Scoring...")

    # --- Data Fetch ---
    image_channel = await context.guild.fetch_channel(1167152706230681670)
    # Expected ordering: oldest -> newest. If your helper returns newest -> oldest, reverse it here.
    image_messages_by_round = await fetch_images_by_rounds(image_channel, n_rounds)
    rounds = get_recent_complete_rounds(n_rounds)  # aligned to same indexing as image_messages_by_round
    mess_up_map = await fetch_mess_ups(context, rounds)
    role = context.guild.get_role(1024052938752151552)

    # --- Initialize Pro members ---
    pro_member_ids: set[int] = set()
    async for member in context.guild.fetch_members(limit=None):
        if has_role(member, role):
            pro_member_ids.add(member.id)

    # --- Build fixed-triplet weights with -6pp per tier ---
    total_rounds = len(image_messages_by_round)
    weights = build_fixed_triplet_weights_pp(
        total_rounds,
        start=1.00,
        drop_pp=1/3,
        group_size=6,
        min_weight=0.0
    )

    # --- Compute per-user, per-round RAW scores (unweighted) ---
    # user_round_scores[user_id] -> list[float] of length total_rounds
    user_round_scores: dict[int, list[float]] = {uid: [] for uid in pro_member_ids}

    for i, round_messages in enumerate(image_messages_by_round):
        # Build author -> list of positions (+1) for this round
        author_positions: dict[int, list[int]] = {}
        for idx, msg in enumerate(round_messages):
            author_positions.setdefault(msg.author.id, []).append(idx + 1)

        total_participants = len(round_messages)
        base_penalty = total_participants + 1

        # Per-round mess-ups (assumed dict keyed by round index -> {member_id: mess_up_count})
        round_mess_ups = mess_up_map.get(i, {}) if isinstance(mess_up_map, dict) else {}

        for member_id in pro_member_ids:
            if member_id in round_mess_ups:
                num_mess_ups = round_mess_ups[member_id]
                score = base_penalty + num_mess_ups
            elif member_id in author_positions:
                positions = author_positions[member_id]
                score = sum(positions) / len(positions)
            else:
                score = base_penalty
            user_round_scores[member_id].append(score)

    # --- Apply 'drop worst' per user (set worst RAW to 0 BEFORE weighting) ---
    dropped_index_by_user: dict[int, int | None] = {}
    for member_id, scores in user_round_scores.items():
        if scores:
            worst_idx = max(range(len(scores)), key=lambda k: scores[k])
            dropped_index_by_user[member_id] = worst_idx
            scores[worst_idx] = 0.0
        else:
            dropped_index_by_user[member_id] = None

    # --- Accumulate weighted totals (ceil per round) ---
    totals: dict[int, float] = {uid: 0.0 for uid in pro_member_ids}
    for i in range(total_rounds):
        w = weights[i] if i < len(weights) else 1.0
        for member_id in pro_member_ids:
            if i < len(user_round_scores[member_id]):
                totals[member_id] += math.ceil(user_round_scores[member_id][i] * w)

    # --- Sort and format leaderboard ---
    sorted_members = sorted(totals.items(), key=lambda x: x[1])  # ascending total
    leaderboard_lines = []
    medals = ["🥇", "🥈", "🥉"]

    for rank, (member_id, score) in enumerate(sorted_members, start=1):
        member = context.guild.get_member(member_id)
        raw_name = member.display_name if member else f"User {member_id}"
        display_name = strip_emojis(raw_name)
        rank_label = medals[rank - 1] if rank <= 3 else f"{rank}."
        leaderboard_lines.append(f"{rank_label} {display_name}: {round(score)}")

    leaderboard_output = "\n".join(leaderboard_lines)
    await FINAL_msg.edit(content=leaderboard_output)

def ordinal(n: int) -> str:
    """Returns ordinal string for a given integer: 1 → '1st', 2 → '2nd', etc."""
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# ----- pro_score: single member, stylized by 3-round batches -----

@command_handler.Command(access_type=AccessType.PUBLIC)
async def pro_score(activator: Neighbor, context: Context):
    """
    Show one member's recency-weighted score over the most recent 18 rounds.

    Changes:
      - Fixed triplet weights at -6 percentage points per tier:
          newest 3: 100% (1.00), then 94% (0.94), then 88% (0.88), ...
      - 'Drop worst raw round' before weighting (set to 0 only for scoring).
      - Output grouped in triplets. For each group, print:
          • the 3 round lines,
          • then a batch footer:
               Batch raw = <sum raw in group after drop>
               Weight    = <weight for that group>
               Batch weighted = <sum ceil(raw_i * weight) across the 3 rounds>
      - End with:  Final score: a + b + c + ... = total

    Raw per-round scoring (before weighting):
      - If user has mess-ups: (#participants + 1 + mess_ups)
      - Else if user posted: average of their (position indices + 1)
      - Else: (#participants + 1)
    """

    # --- Resolve target member (mention, id, or fuzzy by display name / username) ---
    if len(context.args) > 0:
        try:
            target = await context.guild.fetch_member(int(parse_mention((context.args[0]))))
        except:
            candidates = [x.nick for x in context.guild.members if x.nick is not None]
            candidates.extend([x.name for x in context.guild.members if (x.nick is None) or (x.nick != x.name)])
            name, confidence = best_string_match(context.args[0], [str(x) for x in candidates])
            target = discord.utils.get(context.guild.members, display_name=name)
            target = target if target is not None else discord.utils.get(context.guild.members, name=name)
    else:
        target = None

    target_member = context.author if target is None else target
    member_id = target_member.id

    FINAL_msg = await context.send("Scoring...")

    # --- Config ---
    N_ROUNDS    = 18
    GROUP_SIZE  = 6
    START_W     = 1.00   # 100%
    DROP_PP     = 1/3   # 6 percentage points per tier
    MIN_WEIGHT  = 0.0

    # --- Fetch rounds & mess-ups ---
    channel = await context.guild.fetch_channel(1167152706230681670)
    rounds = await fetch_images_by_rounds(channel, n_rounds=N_ROUNDS)  # expected: oldest -> newest
    round_windows = get_recent_complete_rounds(N_ROUNDS)               # aligned to same indexing
    mess_up_map = await fetch_mess_ups(context, round_windows)

    # --- Build weights ---
    total_rounds = len(rounds)
    weights = build_fixed_triplet_weights_pp(
        total_rounds,
        start=START_W,
        drop_pp=DROP_PP,
        group_size=GROUP_SIZE,
        min_weight=MIN_WEIGHT
    )

    # --- Compute RAW per-round scores for the target (unweighted) ---
    raw_scores: list[float] = []
    round_labels: list[str] = []

    for i, round_messages in enumerate(rounds):
        # Label from message date if present, else from window start
        if round_messages:
            # If your created_at is timezone-aware, keep it; otherwise handle LOCAL_TZ
            round_date = getattr(round_messages[0].created_at, "date", None)
            if round_date is not None:
                round_start = round_messages[0].created_at.date()
            else:
                # Fallback if needed
                round_start = round_windows[i][0].date()
        else:
            round_start = round_windows[i][0].date()
        round_labels.append(f"Derby of {round_start.strftime('%B')} {round_start.day}")

        # Build author -> list of positions (+1)
        author_positions: dict[int, list[int]] = {}
        for idx, msg in enumerate(round_messages):
            author_positions.setdefault(msg.author.id, []).append(idx + 1)

        total_participants = len(round_messages)
        base_penalty = total_participants + 1

        # Mess-up override
        round_mess_ups = mess_up_map.get(i, {}) if isinstance(mess_up_map, dict) else {}
        if member_id in round_mess_ups:
            mess_ups = round_mess_ups[member_id]
            raw_score = base_penalty + mess_ups
        elif member_id in author_positions:
            positions = author_positions[member_id]
            raw_score = sum(positions) / len(positions)
        else:
            raw_score = base_penalty

        raw_scores.append(raw_score)

    # --- Drop worst raw round (set to 0 for scoring, keep original for display) ---
    raw_scores_orig = raw_scores[:]
    dropped_index = None
    if raw_scores:
        dropped_index = max(range(len(raw_scores)), key=lambda k: raw_scores[k])
        raw_scores[dropped_index] = 0.0

    # --- Build grouped breakdown (triplets) and compute totals ---
    header_name = strip_emojis(target_member.display_name if target_member else f"User {member_id}")
    lines: list[str] = []
    lines.append(f"**Pro Score for {header_name}**")
    lines.append(f"_Last {total_rounds} derbies · Worst score dropped_")
    lines.append("")

    batch_weighted_totals: list[int] = []
    overall_total = 0

    # Determine number of triplets (ceil)
    num_batches = (total_rounds + GROUP_SIZE - 1) // GROUP_SIZE

    # We present batches from **newest to oldest** to match intuition:
    #   Batch 1 = newest 3, Batch 2 = previous 3, etc.
    # Our arrays are oldest->newest, so compute indices accordingly.
    for batch_idx_from_newest in range(num_batches):
        # Compute inclusive range [start_i, end_i] for this batch in oldest->newest indexing
        # newest batch covers the last 3 indices
        end_i = total_rounds - 1 - batch_idx_from_newest * GROUP_SIZE
        start_i = max(0, end_i - (GROUP_SIZE - 1))
        batch_indices = list(range(start_i, end_i + 1))

        # Weight for this batch: all 3 share the same value in our scheme; just read weight at end_i
        batch_weight = weights[end_i] if end_i < len(weights) else 1.0

        # Header
        human_batch_num = batch_idx_from_newest + 1
        weight_pct = f"{round(batch_weight * 100)}%"
        lines.append(f"__Batch {human_batch_num} (most recent {GROUP_SIZE}): weight {weight_pct}__")

        # Per-round lines inside the batch
        batch_raw_sum = 0.0
        batch_weighted_sum = 0
        for i in batch_indices:
            label = round_labels[i] if i < len(round_labels) else f"Round {i+1}"

            # Determine display type and points
            # We recompute author_positions for display tag
            author_positions = {}
            for idx, msg in enumerate(rounds[i]):
                author_positions.setdefault(msg.author.id, []).append(idx + 1)

            round_mess_ups = mess_up_map.get(i, {}) if isinstance(mess_up_map, dict) else {}

            # Display classification
            if dropped_index is not None and i == dropped_index:
                classification = "Dropped worst round"
            elif member_id in round_mess_ups:
                classification = f"Mess up ({round_mess_ups[member_id]})"
            elif member_id in author_positions:
                positions = author_positions[member_id]
                avg_pos = sum(positions) / len(positions)
                classification = f"{ordinal(round(avg_pos))} poster"
            else:
                classification = "No post"

            # Raw (for scoring) uses dropped version; for display we still show classification above
            raw_for_scoring = raw_scores[i]
            cur_weighted = math.ceil(raw_for_scoring * batch_weight)
            batch_raw_sum += raw_for_scoring
            batch_weighted_sum += cur_weighted

            # Round line
            lines.append(f"• {label}: {classification} — {cur_weighted} points")

        # Batch footer
        # Keep raw shown with up to 2 decimals (your preference: you can also round int if always int-like)
        batch_raw_disp = f"{batch_raw_sum:.2f}".rstrip('0').rstrip('.')  # trim trailing zeros
        lines.append(f"_Batch {human_batch_num} summary:_ raw **{batch_raw_disp}** · weight **{weight_pct}** · weighted **{batch_weighted_sum}**")
        lines.append("")

        # Accumulate
        batch_weighted_totals.append(batch_weighted_sum)
        overall_total += batch_weighted_sum

    # Final line: "Final score: a + b + c + ... = total"
    parts = " + ".join(str(x) for x in batch_weighted_totals)
    lines.append(f"**Final score:** {parts} = **{overall_total}**")

    # Dropped round note
    if dropped_index is not None and 0 <= dropped_index < len(round_labels):
        lines.append(f"_Dropped worst raw round:_ **{round_labels[dropped_index]}** (from {raw_scores_orig[dropped_index]} to 0)")

    await FINAL_msg.edit(content="\n".join(lines))
        
        
async def check_member(member: discord.Member, months: int):
    # Calculate the duration in days
    duration_days = months * 30  # Approximate each month as 30 days
    now = datetime.datetime.utcnow()
    join_date = member.joined_at
    
    print(join_date);

    if join_date is None:
        return False;

    days_in_server = (now - join_date).days

    if days_in_server > duration_days:
        return True;
    else:
        return False;

import re, datetime

def normalize_birthday(input_str):
    input_str = input_str.lower().strip()

    month_map = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    input_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', input_str)

    for name, number in month_map.items():
        if name in input_str:
            match = re.search(rf'{name}\s+(\d+)', input_str)
            if match:
                try:
                    day = int(match.group(1))
                    datetime.date(2000, number, day)
                    return number, day
                except ValueError:
                    return None

    nums = list(map(int, re.findall(r'\b\d{1,2}\b', input_str)))
    if len(nums) >= 2:
        try:
            datetime.date(2000, nums[0], nums[1])
            return nums[0], nums[1]
        except ValueError:
            return None

    return None

@command_handler.Command(access_type=AccessType.DEVELOPER)
async def popularity(activator: Neighbor, context: Context):
    """
    Count the number of messages in every channel in the past 3 months and
    post a ranking to the invoking channel.

    Notes:
    - Aggregates messages posted directly in a text/forum channel AND inside its threads.
    - Skips channels the bot can't read.
    - Automatically chunks output to respect Discord's 2000-char limit.
    """
    import asyncio
    import datetime
    import discord
    from discord.utils import utcnow, snowflake_time

    # --- config --------------------------------------------------------------
    DAYS = 90  # "past 3 months" approximation
    INCLUDE_THREADS = True  # set False to only count top-level channel messages
    # -------------------------------------------------------------------------

    guild = context.guild
    if guild is None:
        # Fallback: try the message's guild
        guild = getattr(getattr(context, "message", None), "guild", None)
    if guild is None:
        return  # can't proceed outside a guild

    # send target
    send_channel = getattr(context, "channel", None)
    if send_channel is None:
        send_channel = getattr(getattr(context, "message", None), "channel", None)
    if send_channel is None:
        return  # nowhere to send

    cutoff = utcnow() - datetime.timedelta(days=DAYS)

    # Build the set of parent channels we care about (Text + Forum).
    # We'll aggregate thread messages under their parent channel.
    parent_channels: list[discord.abc.GuildChannel] = [
        ch for ch in guild.channels
        if isinstance(ch, (discord.TextChannel, discord.ForumChannel))
    ]

    # id -> stats
    stats: dict[int, dict] = {}

    async def count_channel(parent: discord.abc.GuildChannel) -> tuple[int, int]:
        """Return (direct_count, threads_count) for messages on/under this parent since cutoff."""
        direct = 0
        threads_total = 0

        # Quick skip if nothing recent (based on last_message_id timestamp)
        def looks_recent(obj) -> bool:
            lm_id = getattr(obj, "last_message_id", None)
            if lm_id is None:
                return False
            try:
                return snowflake_time(lm_id) >= cutoff
            except Exception:
                return True  # if unsure, check history

        # Count direct messages in the parent channel
        if looks_recent(parent):
            try:
                async for _ in parent.history(limit=None, after=cutoff, oldest_first=False):
                    direct += 1
            except (discord.Forbidden, discord.HTTPException):
                # Can't read or other API error: treat as zero for robustness
                direct = 0

        if INCLUDE_THREADS:
            # Collect active + archived threads under this parent
            thread_objs = []
            if hasattr(parent, "threads"):
                thread_objs.extend(list(parent.threads))

            # Public archived threads
            for private_flag in (False, True):
                try:
                    async for th in parent.archived_threads(limit=None, private=private_flag):
                        thread_objs.append(th)
                except (discord.Forbidden, discord.HTTPException, AttributeError):
                    # No access or not supported on this channel type
                    pass

            # Deduplicate by id
            seen = set()
            uniq_threads = []
            for th in thread_objs:
                if th.id not in seen:
                    seen.add(th.id)
                    uniq_threads.append(th)

            # Count messages in each thread
            for th in uniq_threads:
                if not looks_recent(th):
                    continue
                try:
                    async for _ in th.history(limit=None, after=cutoff, oldest_first=False):
                        threads_total += 1
                except (discord.Forbidden, discord.HTTPException):
                    # Skip inaccessible threads
                    continue

        return direct, threads_total

    # Iterate over parent channels and collect stats
    for ch in parent_channels:
        # Ensure we can at least view the channel; skip if not
        perms = ch.permissions_for(guild.me) if hasattr(guild, "me") else None
        if perms and not perms.read_message_history:
            continue

        direct, threads_cnt = await count_channel(ch)
        total = direct + threads_cnt
        stats[ch.id] = {
            "name": f"#{ch.name}",
            "direct": direct,
            "threads": threads_cnt,
            "total": total,
        }
        # yield to the loop periodically
        await asyncio.sleep(0)

    # Sort by total messages desc
    ranked = sorted(stats.values(), key=lambda r: r["total"], reverse=True)

    # Build output lines
    header = f"**Message activity in the last {DAYS} days** (as of {utcnow().strftime('%Y-%m-%d %H:%M UTC')})"
    if INCLUDE_THREADS:
        sub = "_Counts include messages in threads under each channel._"
    else:
        sub = "_Threads excluded._"

    lines = [header, sub]
    if not ranked:
        lines.append("No readable channels or no messages found in the period.")
    else:
        for i, row in enumerate(ranked, start=1):
            lines.append(
                f"{i}. {row['name']}: **{row['total']}**  "
                f"(direct {row['direct']}, threads {row['threads']})"
            )

    # Send in chunks (Discord 2000 char limit)
    msg = "\n".join(lines)
    if len(msg) <= 1900:
        await send_channel.send(msg)
    else:
        chunk = [lines[0], lines[1]]
        cur_len = sum(len(x) for x in chunk) + len(chunk)  # rough newline count
        for line in lines[2:]:
            if cur_len + len(line) + 1 > 1900:
                await send_channel.send("\n".join(chunk))
                chunk = [lines[0], lines[1]]  # repeat header for readability
                cur_len = sum(len(x) for x in chunk) + len(chunk)
            chunk.append(line)
            cur_len += len(line) + 1
        if chunk:
            await send_channel.send("\n".join(chunk))
    

def is_today_birthday(bday_tuple, est_time=None):
    today = datetime.datetime.now(datetime.timezone.utc)
    if est_time:
        today = today.astimezone(est_time)

    if bday_tuple is None:
        return False

    month, day = bday_tuple
    return today.month == month and today.day == day

@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def derbylottery(activator: Neighbor, context: Context):
    guild = context.guild;
    lottery_chat = await guild.fetch_channel(1117840455648948255);
    
    pro_members = [];
    pro_role = guild.get_role(1024052938752151552)
    main_members = [];
    main_role = guild.get_role(656112994392080384)
    junior_members = [];
    junior_role = guild.get_role(689928709683150909)
    junior2_members = [];
    junior2_role = guild.get_role(1334660124639236267)
    garden_members = [];
    garden_role = guild.get_role(1173325157767589988)
    
    async for member in guild.fetch_members():
        if has_role(member, pro_role):
            pro_members.append(member);
        if has_role(member, main_role):
            main_members.append(member);
        if has_role(member, junior_role):
            junior_members.append(member);
        if has_role(member, junior2_role):
            junior2_members.append(member);
        if has_role(member, garden_role):
            garden_members.append(member);
    
    
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=int(context.args[0]))
    
    async for message in lottery_chat.history(limit=None, oldest_first=False):
        if message.created_at < cutoff:
            break
        
        if not "lottery" in message.content and "dice" in message.content:
            continue;
        
        
        pro_members = [pro_member for pro_member in pro_members if not str(pro_member.id) in message.content];
        main_members = [main_member for main_member in main_members if not str(main_member.id) in message.content];
        junior_members = [junior_member for junior_member in junior_members if not str(junior_member.id) in message.content];
        junior2_members = [junior2_member for junior2_member in junior2_members if not str(junior2_member.id) in message.content];
        garden_members = [garden_member for garden_member in garden_members if not str(garden_member.id) in message.content];
        
    await context.send(''.join(f"<@{pro_member.id}>\n" for pro_member in pro_members))
    await context.send(''.join(f"<@{main_member.id}>\n" for main_member in main_members))
    await context.send(''.join(f"<@{junior_member.id}>\n" for junior_member in junior_members))
    await context.send(''.join(f"<@{junior2_member.id}>\n" for junior2_member in junior2_members))
    await context.send(''.join(f"<@{garden_member.id}>\n" for garden_member in garden_members))


def first_line_or_period(s: str) -> str:
    """Return up to the first newline (excluded) or the first period (included)."""
    if not s:
        return ""
    i_nl = s.find("\n")
    i_dot = s.find(".")
    # choose the earliest index that exists
    idxs = [i for i in (i_nl, i_dot) if i != -1]
    if not idxs:
        return s.strip()
    i = min(idxs)
    end = i + 1 if s[i] == "." else i
    return s[:end].strip()

@command_handler.Uncontested(type="MESSAGE")
async def announcements(context: Context):
    if not "<@&1181330910747054211>" in context.message.content:
        return
    
    council_role = context.guild.get_role(648188387836166168)
    if not has_role(context.author, council_role):
        return;
    
    announcements_channel = await context.guild.fetch_channel(648218302321131540)
    link = f"https://discord.com/channels/{context.guild.id}/{context.channel.id}/{context.message.id}"
    first_line = first_line_or_period(context.message.content.replace("<@&1181330910747054211>", ""))
    await announcements_channel.send(f"# {first_line}\n<@{context.author.id}> made an announcement here: {link}\n\n{context.message.content.replace("<@&1181330910747054211>", "")}")


@command_handler.Loop(minutes = 10)
async def set_time(client):
    guild = client.get_guild(FF.guild);
    vc = await guild.fetch_channel(1092957590427815966);
    current_time_utc = time.time()

    # convert UTC to Eastern Standard Time (EST)
    est_offset = datetime.timedelta(hours=-4)
    est_time = datetime.datetime.fromtimestamp(current_time_utc, datetime.timezone.utc) + est_offset

    # round the minute to the nearest 5
    est_minute = est_time.minute
    import math
    est_minute_rounded = 10 * math.floor(est_minute/10)
    est_time = est_time.replace(minute=est_minute_rounded)

    # format the time as a string with AM/PM marker
    est_time_str = est_time.strftime("It's %I:%M%p server time");
    await vc.edit(name=est_time_str)
    
    # channel = await guild.fetch_channel(704366328089280623);
    # await channel.send("<@355169964027805698>")
    # await channel.send(est_time_str);

    # await xp_reset(client, est_time)
    await personalized_recruitment_reminder(client, guild, est_time);
    await pro_reminders(client, guild, est_time);
    await carnival_reminders(client, guild, est_time);
    await newspaper_reminders(client, guild, est_time)
    await hospitality_reminders(client, guild, est_time)
    await recruitment_reminders(client, guild, est_time)
    await lotteries_reminders(client, guild, est_time)
    await hk_reminders(client, guild, est_time)
    await compliance(client, guild, est_time);
    await guests(client, guild, est_time);
    await derby_reminder(client, guild, est_time);
    await trade_reminder(client, guild, est_time);
    # await birthdays(client, guild, est_time)
    
@command_handler.Scheduled(time="4:00")
async def birthdays(client):

    guild = client.get_guild(FF.guild)
    current_time_utc = time.time()
    est_offset = datetime.timedelta(hours=-4)
    est_time = datetime.datetime.fromtimestamp(current_time_utc, datetime.timezone.utc) + est_offset

    def is_last_day(dt):
        return (dt + datetime.timedelta(days=1)).day == 1
    
    birthdays_channel = await guild.fetch_channel(1392147228684058644);
    council_role = guild.get_role(648188387836166168)
    general_channel = await guild.fetch_channel(648223397205114910);
    this_month_birthdays = []
    today_bdays = []
    today_council_bdays = []
    
    async for message in birthdays_channel.history(limit=None, oldest_first=False):
        bday = normalize_birthday(message.content)
        if not bday:
            continue
        elif (is_today_birthday(bday)):
            if has_role(message.author, council_role):
                today_council_bdays.append(message.author.id)
            else:
                today_bdays.append(message.author.id)
        if is_last_day(est_time):
            if bday[0] == est_time.month:
                this_month_birthdays.append((message.author.id,bday));
    
    if today_bdays:
        for bday in today_bdays:
            await general_channel.send(f"Happy Birthday <@{bday}>!!")
            target = await general_channel.send("$celebrate")
            await celebrate(Neighbor(691338084444274728, 1008089618090049678), Context(target));
            
        
    if today_council_bdays:
        for bday in today_council_bdays:
            await general_channel.send(f"Let's celebrate our Council Member <@{bday}>'s birthday!! @everyone")
            target = await general_channel.send("$celebrate")
            await celebrate(Neighbor(691338084444274728, 1008089618090049678), Context(target));
            
    if is_last_day(est_time):
        month_map = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        this_month = month_map[est_time.month]
        res = f"**Let's celebrate all of our {this_month} Birthdays one more time!**\nWe have had:\n\n"
        for player, bday in this_month_birthdays:
            res += f"<@{player}> ({this_month} {bday[1]})\n"
        res += "\n@everyone"
        await general_channel.send(res)
        target = await general_channel.send("$celebrate")
        await celebrate(Neighbor(691338084444274728, 1008089618090049678), Context(target));
            
    
async def trade_reminder(client, guild, est_time):
    if est_time.hour == 12 and est_time.minute == 0 and chance(7):
        trading_channel = await guild.fetch_channel(1099888905265881210);
        general = await guild.fetch_channel(648223397205114910);
        
        await trading_channel.send("**Need to even out your BEMs?**\nIf you're lacking one BEM type but have surplus of another, you can trade to even out your supplies! You can:\n\n1) **Trade with Neighbors** right here in this channel\n2) Trade with other players in the **r/HD server**\n3) Or trade with the **FF Treasury** itself! The Treasury has virtually unlimited supplies to make trades with you, and will do so at a 2:3 ratio (favorable to the Treasury). Discounts for full sets. Open a ticket to make an offer: <#1033207181857800242>")
        await general.send("**Need to even out your BEMs?**\n Do you have too many planks but too few duct tape? or too many bolts but too few planks? or whatever?\n\n=Check out <#1099888905265881210>")
    
    elif est_time.hour == 12 and est_time.minute == 0 and chance(7):
        trading_channel = await guild.fetch_channel(1099888905265881210);
        general = await guild.fetch_channel(648223397205114910);
        
        await trading_channel.send("**Low on barn stock?**\nThe Council mass produces certain items, like dairy, sugar, fish, and honey, and will trade them for BEMs at **better than market** prices.\nOpen a ticket to see what we have in stock: <#1033207181857800242>")
        await general.send("**Low on barn stock?**\nThe Council can help. \n\n Check out <#1409602006712062022>")
    
    
async def derby_reminder(client, guild, est_time):
    pro = await guild.fetch_channel(1101572607372951694)
    main = await guild.fetch_channel(1062523480739938324)
    juniors = [await guild.fetch_channel(x) for x in [1062523541691584522, 1334660540294893609]]
    garden = await guild.fetch_channel(1177325611266605157)
    carnival = await guild.fetch_channel(1342333687429070918)
    targets = []
    if est_time.hour == 8 and est_time.minute == 0 and est_time.weekday() == 5:
        targets.append(await pro.send("Hey gang! It's Saturday! We should be wrapping things up with derby. Let your neighbors know if you need help!\nYou may want to check in game that your tasks are done. <@&1024052938752151552>\nWe got this!"))
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 6:
        targets.append(await main.send("Hey gang! It's Sunday! We should be wrapping things up with derby. Let your neighbors know if you need help!\nYou may want to check in game that your tasks are done.\nAll non diamond tasks! <@&656112994392080384>\nWe got this!"))
        targets.append(await juniors[0].send("Hey gang! It's Sunday! We should be wrapping things up with derby. Let your neighbors know if you need help!\nYou may want to check in game that your tasks are done.\nIf you need help calculating your requirement, let the leaders know. <@&689928709683150909>\nWe got this!"))
        targets.append(await juniors[1].send("Hey gang! It's Sunday! We should be wrapping things up with derby. Let your neighbors know if you need help!\nYou may want to check in game that your tasks are done.\nIf you need help calculating your requirement, let the leaders know. <@&1334660124639236267>\nWe got this!"))
        targets.append(await garden.send("Hey gang! It's Sunday! Check to make sure you've got 600 points done in derby for the week <@&1173325157767589988>\nWe got this!"))
   
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 5:
        targets.append(await carnival.send("Hey Carnies! It's Saturday! Just a little reminder (again) to submit your screenshot for the week. <@&1342329111359656008>\nWe got this!"))

    for target in targets:
        new_context = Context(target)
        await new_context.send("$meme");
        await meme(Neighbor(691338084444274728), Context(target))
    
@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def add_emoji(activator: Neighbor, context: Context):
    pass

@command_handler.Loop(hours=1)
async def check_emojis(client):
    guild = client.get_guild(FF.guild);
    async for member in guild.fetch_members():
        neighbor = Neighbor(member.id, guild.id)
        
        if neighbor.ID in [220427859229933568, 430454367003475978, 1116699416389226577, 793099607222648852, 355169964027805698, 648230625966293002] and not neighbor.get_item_of_name("January Book Club"):
            item = Item("January Book Club", "event_emoji", time.time() + 21086592, emoji="📚", display="None")
            neighbor.bestow_item(item)   
        
        ls_pro_voters = [1322905749139226656,316114265645776896,430454367003475978,424503695674441728,1129393963430846595,220427859229933568,978586163147337728,1327592356542681109,312019945913319424,987955038804639744,648229959973994506,1116699416389226577,913823853787119639,1011941542287650856]
        ls_main_voters = [376343175863992320,240899039749603328,1250644488649441291,404421544979464192,648229959973994506,963533131854532638,987955038804639744,1440021025843839026,863037754164903946]
        ls_junior_voters = [816303446512369675,713227411927335012,398518029027377163,287705818462289922,793099607222648852,702140318115692634,680164335913664517,1282679887580102799,795304848181821481]
        ls_garden_voters = [1033786928279081061,160694804534132736,1386052757147877513,300463822991392769,516969515486019604,648229959973994506,660204032362545152,220427859229933568,374979463789805570,749225745460625409]
        ls_carnival_voters = [315947587024715776,1368089663910187118,844975416938856448,1286932135084687401,304579655489421312,1328004699672154194,715484789485994064,648229959973994506,514413698761359400,1322905749139226656,750373365927379044,754000375274799196]
        
        ls_all_voters = ls_pro_voters;
        ls_all_voters.extend(ls_main_voters)
        ls_all_voters.extend(ls_junior_voters)
        ls_all_voters.extend(ls_garden_voters);
        ls_all_voters.extend(ls_carnival_voters);
        if neighbor.ID in ls_all_voters and not neighbor.get_item_of_name("I Voted! sticker"):
            item = Item("I Voted! sticker", "event_emoji", time.time() + 21086592, emoji="🗳️", display="None")
            neighbor.bestow_item(item)   
        
        cow_role = guild.get_role(1328866706294046720)
        if has_role(member, cow_role) and not neighbor.get_item_of_name("2025 Family Winners!"):
            item = Item("2025 Family Winners!", "event_emoji", time.time() + 21086592, emoji="👑", display="None")
            neighbor.bestow_item(item)   
        neighbor_role = guild.get_role(1181330910747054211);
        
        while item := neighbor.get_item_of_name("2025 Farmmas Treasure!"):
            neighbor.vacate_item(item);
            
        if neighbor.ID == 374979463789805570:
            item = Item("2025 Farmmas Treasure!", "event_emoji", time.time() + 21086592, emoji="🔎", display="None")
            neighbor.bestow_item(item)   
        
        if has_role(member, neighbor_role) and not neighbor.get_item_of_name("Fair_Wheel"):
            item = Item("Fair_Wheel", "event_emoji", time.time() + 7776000, emoji="🎡", display="None")
            neighbor.bestow_item(item) 
        if has_role(member, neighbor_role) and not neighbor.get_item_of_name("Fair_Horse"):
            item = Item("Fair_Horse", "event_emoji$inv", time.time() + 7776000, emoji="🎠", display="None")
            neighbor.bestow_item(item) 
        if has_role(member, neighbor_role) and not neighbor.get_item_of_name("Fair_Juggler"):
            item = Item("Fair_Juggler", "event_emoji", time.time() + 7776000, emoji="🤹", display="None")
            neighbor.bestow_item(item) 
            
        if item := neighbor.get_item_of_name("Cactus tag Oct deco comp"):
            item.update_value("emoji", "🌵")
            neighbor.update_item(item)
            
            
        while item := neighbor.get_item_of_name("Juggler"):
            neighbor.vacate_item(item);
            
        while item := neighbor.get_item_of_name("Wheel"):
            neighbor.vacate_item(item);
            
        while item := neighbor.get_item_of_name("Horse"):
            neighbor.vacate_item(item);
            
        while item := neighbor.get_item_of_name("Role"):
            neighbor.vacate_item(item);
            
        item_to_keep = neighbor.get_item_of_name("Earth_Day")

        while (item := neighbor.get_item_of_name("Earth_Day")):
            neighbor.vacate_item(item)

        if item_to_keep is not None:
            neighbor.bestow_item(item_to_keep)
            
            
async def get_users_who_reacted(message, target_emoji):
    users = []

    for reaction in message.reactions:
        # Match either unicode emoji ("👍") or custom emoji (<:name:id>)
        if str(reaction.emoji) == target_emoji:
            async for user in reaction.users():
                users.append(user)

    return users

@command_handler.Loop(hours=1) 
async def event_emojis(client):
    guild = client.get_guild(FF.guild);
    deco_comp_channel = await guild.fetch_channel(654303369464119316)
       
    LOCAL_UTC_OFFSET = -4  # EDT
    LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=LOCAL_UTC_OFFSET))
    
    news_stand_channel = await guild.fetch_channel(1218041302998974584);
    farmmas_message = await news_stand_channel.fetch_message(1445532298685452470);
    
    farmmas1 = await get_users_who_reacted(farmmas_message, "❄️")
    farmmas2 = await get_users_who_reacted(farmmas_message, "⛄️")
    
    for user in farmmas1:
        neighbor = Neighbor(user.id, guild.id)
        if neighbor.get_item_of_name("Farmmas1 tag"):
            continue;
        item = Item("Farmmas1 tag", "event_emoji", time.time() + 5184000, emoji="❄️", display=True)
        neighbor.bestow_item(item) 
        await set_nick(user, guild) 
        
    for user in farmmas2:
        neighbor = Neighbor(user.id, guild.id)
        if neighbor.get_item_of_name("Farmmas2 tag"):
            continue;
        item = Item("Farmmas2 tag", "event_emoji", time.time() + 5184000, emoji="⛄️", display=True)
        neighbor.bestow_item(item)  
        await set_nick(user, guild)
    
    
    async for message in deco_comp_channel.history(limit=None, oldest_first=False):
        msg_time = message.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
        msg_time = msg_time.astimezone(LOCAL_TZ)
        
        month = msg_time.month
            
        has_image = (
            any(att.content_type and att.content_type.startswith("image/") for att in message.attachments) or
            any(embed.type == "image" or (embed.image and embed.image.url) for embed in message.embeds)
        )
        if not has_image:
            continue;
        
        if month == 12:
            break;
            
        if month == 1: 
            neighbor = Neighbor(message.author.id, message.guild.id)
            if neighbor.get_item_of_name("Fireworks tag Jan deco comp"):
                continue;
            item = Item("Fireworks tag Jan deco comp", "event_emoji", time.time() + 21086592, emoji="🎇", display=True)
            neighbor.bestow_item(item)  
            
        await set_nick(message.author, message.guild)
        print(message.author.display_name);
        
    
@command_handler.Command(access_type=AccessType.PUBLIC)
async def emojis(activator: Neighbor, context: Context):
    
    result = "# Customize your nickname\n"
    result += "If you have earned LTO emojis from FF events, you can now pick and choose which emojis show up in your nickname.\n\n"
    
    event_emojis = activator.get_items_of_type("event_emoji");
    if event_emojis:
        result += "You have:\n";
    for item in event_emojis:
        result += f"{item.get_value("emoji")}: {item.name}\n";
    if event_emojis:
        result += "\n"
    
    result += "**Instructions**\n"
    result += "Add a reaction to the emojis you'd like to show up in your nickname, then react with a ✅ to finalize your choices.\n"
    result += "-# LTO emojis eventually expire."
    result += "\n-# You can only have any given 3 of your LTO emojis displaying at once."
    target = await context.send(result, reply=True)
    
    for item in activator.get_items_of_type("event_emoji"):
        await target.add_reaction(item.get_value("emoji"))
        # item.update_value("display", False);
        # activator.update_item(item);
        
    await target.add_reaction("✅")
    
    def key(ctx):
        if not ctx.message.id == target.id:
            return False;
        if not ctx.user.id == activator.ID:
            return False;
        if not ctx.emoji.name == "✅":
            return False;
        return True;
    ResponseRequest(adjust_emojis, "confirm", "REACTION", Context(target), Context(target), key=key)
    
async def adjust_emojis(activator: Neighbor, context: Context, confirm: ResponsePackage):
    msg = await context.channel.fetch_message(confirm.activation_context.message.id)
    
    print(f"msg.id {msg.id}");
    print(f"activator.id {activator.ID}")
    
    ls_reactions = []
    for reaction in msg.reactions:
        user_ids = [user.id async for user in reaction.users(limit=None)]
        if activator.ID in user_ids:
            print(f"Trying: {reaction.emoji}")
            ls_reactions.append(reaction.emoji);
            
    result = "Got it, I'll display:\n";
    for item in activator.get_items_of_type("event_emoji"):
        print(item.get_value("emoji"))
        if item.get_value("emoji") in ls_reactions:
            print(f"Found: {item.get_value("emoji")}")
            item.update_value("display", True);
            activator.update_item(item);
            result += item.get_value("emoji");
        else:
            item.update_value("display", False);
            activator.update_item(item);
            
    await context.send(result);
        
    await set_nick(await context.guild.fetch_member(activator.ID), context.guild)
            
    
@command_handler.Command(access_type=AccessType.PUBLIC, generic=True)
async def gif(activator: Neighbor, context: Context):
    import aiohttp
    
    if len(context.args) == 0:
        member = await context.guild.fetch_member(activator.ID);
        search_term = member.name;
    else:
        search_term = " ".join(context.args).lower();
    
    TENOR_API_KEY = "AIzaSyDyMfrO4f61lFkCkP58g-NmN7dPRizNgNI"
    url = f"https://tenor.googleapis.com/v2/search?q={search_term}&key={TENOR_API_KEY}&limit=10"
    
    channel = await context.guild.fetch_channel(1391837239679385741)
    
    # CHECK CACHE
    res = None 
    cache = remember("gif_cache")
    if cache and search_term in cache:
        try:
            message = await channel.fetch_message(cache[search_term]["id"])
        except:
            message = ""
        
        if message and ":" in message.content:
            raw_keywords, *content_parts = message.content.split(':')
            content = ":".join(content_parts).strip()
            keywords = [kw.strip().lower() for kw in raw_keywords.split(" or ")]
            
            if search_term in keywords:
                res = content;
                print("Found in cache")
                
    patch = not res
    if not res:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    res = ("Darn! Failed to fetch GIFs 😕\nMaybe try again idk")
                    return
                data = await response.json()
                results = data.get("results")
                if not results:
                    res = ("Darn! No GIFs found!")
                    return
                random_gif = random.choice(results)
                res = random_gif["media_formats"]["gif"]["url"]
          
    target = await context.send(res, reply=True) 
                
    # PATCH CACHE
    if patch:
        cache = remember("gif_cache") or {}
        if search_term in cache:
            del cache[search_term]

        async for message in channel.history(limit=None):
            if ':' not in message.content:
                continue  # Skip malformed messages

            # Split once per line into keyword and content
            raw_keywords, *content_parts = message.content.split(':')
            cur_content = ":".join(content_parts).strip()
            cur_keywords = [kw.strip().lower() for kw in raw_keywords.split(" or ")]

            for kw in cur_keywords:
                if kw in cache and cache[kw]['id'] == message.id:
                    continue;
                else:
                    cache[kw] = {}
                    cache[kw]['id'] = message.id

                if kw == search_term:
                    res = cur_content;
            
        remember("gif_cache", cache)

# Example token setup
# bot.run("YOUR_DISCORD_BOT_TOKEN")
    
async def farmmas(client, guild, est_time):
    if est_time.hour == 14 and est_time.minute == 10:
        farmmas_chat = 784803565151453214
        channel = await guild.fetch_channel(farmmas_chat)
        await channel.send("Day 12 results!\nThese are the results for yesterday's giveaway. Today's giveaway is still open above.\nGift 1. <@913823853787119639>\nGift 2. <@734811131054391396>\nGift 3. <@406079744539623424>\nGift 4. <@607199947279826966>\n\nCongrats all!\n<@&1181330910747054211>\nIf you won something, use <#1033207181857800242> to collect!\nThat's all for Farmmas. Thanks everyone!");
   
async def hk_reminders(client, guild, est_time):
    hk_chat_ids = [1137251818515214397, 1066850141648199841, 1066850208073383936, 1173336119111336097, 1066850244173758524, 1334661096069660672, 1342334494048387082];
    hosp_chats = [(await guild.fetch_channel(id)) for id in hk_chat_ids];
    hk_role_ids = [1161310740502806568, 1111174280261148685, 1111174397626167296, 1204058075720327200, 1111174489661780009, 1334659966287478784, 1342329493720928376];
    
    for i in range(len(hk_chat_ids)):
        cur_chat = hosp_chats[i];
        cur_role = hk_role_ids[i];
        if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 4:
            await cur_chat.send(f"Good afternoon! It's Friday already! Please discuss a plan for Monday, e.g. will be doing this week's tasks.");
        if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 6:
            await cur_chat.send(f"Good afternoon! It's Sunday! Please post here who will be doing HK, and who will be doing OB if separate. <@&{cur_role}>");
        if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 5:
            await cur_chat.send(f"Good afternoon! PREHKWLMGMT! It's the weekend. Please DM everyone on the waitlists, and update the waitlists by Monday to reflect who is still interested in joining. <@&{cur_role}>\nReact to this message to confirm job done for this week.");        
        if est_time.hour == 12 and est_time.minute == 20 and est_time.weekday() == 0:
            await cur_chat.send(f"Good afternoon! It's Monday! Here's a checklist: \n1. HK Log \n2. Kicks/demotions/promotions\n3. Onboarding\n4. Message kicks/demotions\n5. Update roles!\n<@&{cur_role}> Please react or respond when done. Feel free to split up work amongst multiple people.");

async def hospitality_reminders(client, guild, est_time):
    hosp_chat_id = 1095356264441188383;
    hosp_chat = await guild.fetch_channel(hosp_chat_id);

    target = None

    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 1:
        target = await hosp_chat.send("Good afternoon! It's Tuesday! Let's check in with players who joined yesterday.\n1. Introduce yourself & ask if any questions or concerns.\n2. Send the video for the NH, even if you think they may have received it already.\n3. Suggest writing an introduction that includes a farm tag in order to get a family assignment.\n<@&1111174820072276063> React to this message to confirm job done for this week.");
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 2:
        target = await hosp_chat.send("Good afternoon! It's Wednesday! Let's check in with players who joined two weeks ago.\nJust ask how they're doing, how they like the NH, and whether they have questions or concerns. Maybe, check on their derby performance the past two week and comment on that or offer suggestions.\n<@&1111174820072276063> React to this message to confirm job done for this week.");
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 3:
        target = await hosp_chat.send("Good afternoon! It's Thursday! **Let's check in with any Neighbor.** \n1. Pick someone arbitrary from the NH to check in with, whom you haven't talked to recently.\n-# The goal is to check in with ALL neighbors on a somewhat regular basis; 30 Neighbors / 1 Neighbor per week = Each player gets a DM like this once every ~30 weeks. It's not terribly often but it's something.\n2. Message them. There are many ways you could attempt to strike conversation or just show them you notice their \"work\".\n-# Ex: compliment recent derby performance, comment on their farm design, appreciate their participation in a recent FF event, simply ask if they have any issues or ideas for improvment in the NH, bring something up from their IRL life they recently posted about (recent vacation? hobby?), or any other ideas you have.\n3. Proceed with the convo.\n-# If they reply and attempt to further conversation, have a good, casual non-managerial convo with them! If they don't reply or just say something conversation-ending, that is okay too.\nThis does require paying some attention to your Neighbors, their performance, the stuff they post in NH chat or discord, and so on, so you know what to talk about.\n<@&1111174820072276063> React to this message to confirm job done for this week.");
    #     options = ["Good afternoon! It's Thursday! Time for a random task. **Let's check in with a veteran. Do NOT complete if you completed this same task last week (free day instead).** \n1. Pick someone arbitrary from the NH to check in with. The goal is to check-in with our players that have flown under the radar, every once in a while.\n2. Message them.\n3. There are many ways you could attempt to strike conversation: compliment recent derby performance, comment on their farm design, appreciate their participation in a recent FF event, simply ask if they have any issues or ideas of improvment in the NH, bring something up from their IRL life they recently posted about like asking how a recent vacation went, or any other ideas you have.\n<@&1111174820072276063> React to this message to confirm job done for this week.",
    #             "Good afternoon! It's Thursday! Time for a random task. **Let's write a note of appreciation. Do NOT complete if you completed this same task last week (free day instead).** \nHead over to the notes-of-appreciation channel and write a note for anyone in the server (in or out of your Neighborhood). Be sure to ping them!",
    #             "Good afternoon! It's Thursday! Time for a random task. **Let's get an in-game chat going! Do NOT complete if you completed this same task last week (free day instead).** \nDedicate 10-15 minutes to starting up and carrying a chat within your in-game NH chat. This makes it feel more homey, even for those who don't participate.",
    #             "Good afternoon! It's Thursday! Time for a random task. **Let's get a discord chat going! Do NOT complete if you completed this same task last week (free day instead).** \nDedicate 10-15 minutes to starting up and carrying a chat in the #general server on discord. This makes it feel more homey, even for those who don't participate.", 
    #             "Good afternoon! It's Thursday! Time for a random task. **Let's make sure no one is burning themselves out. Do NOT complete if you completed this same task last week (free day instead).** \nCheck to see if any player has been opted in for a longg time without a break. DM them to offer appreciation for their dedication and suggest opting out for a week if needed for a well deserved break.",
    #             "Good afternoon! It's Thursday! Time for a random task. **Let's write a shout out! Do NOT complete if you completed this same task last week (free day instead).** \nPick someone in your Neighborhood to write a public shout out for. Write and post it in your NH's discord chat. Tag whole Neighborhood. (Best if not a current FARMS nominee please)",
    #             "Good afternoon! It's Thursday! Time for a random task. **Let's share some pics! Do NOT complete if you completed this same task last week (free day instead).** \nChallenge your Neighbors in your NH's discord chat to send pics within a specific theme. Pet pics, hobbies, pretty flower or landscape, anything. 'How many different kinds of flowers can the NH get pics of?' Just for funsies. Be sure to share your own!",
    #             "Good afternoon! It's Thursday! Time for a random task. **Let's get some discord action going! Do NOT complete if you completed this same task last week (free day instead).** \nContribute something to any of the 'random' side-chats in the discord server. Think #pet-pics, #irl-pics, #sports, #kitchen, etc.",
    #             "Good afternoon! It's Thursday! Time for a random task. **Actually, let's not!**\n No need to complete anything this time around. Thanks for your hard work!"
    #     ]
        
    #     target = await hosp_chat.send(random.choice(options));
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 4:
        target = await hosp_chat.send("Good afternoon! It's Friday! Today's a good day to check in with Neighbors who are currently underperforming in derby.\n<@&1111174820072276063> React to this message to confirm job done for this week.");
    
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 5:
        target = await hosp_chat.send("Good afternoon! It's the weekend! No tasks today :) (But I'm sure some of y'all on HK committees have PREHKWLMGMT to do...)")

    if target: 
        await target.add_reaction("✅")

# @command_handler.Loop(hours=1)
async def hospitality_tags(client):
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
                    
                    
async def users_with_role(guild, role_id):
    role = guild.get_role(role_id)

    members = []
    async for member in guild.fetch_members(limit=None):
        if role in member.roles:
            members.append(member)

    return members;

async def newspaper_reminders(client, guild, est_time):
    comms_chat_id = 1095356370557075487;
    comms_chat = await guild.fetch_channel(comms_chat_id);
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 4:
        await comms_chat.send("Good afternoon! It's Friday already! Now is a great time to begin trying to find someone to write the story and someone to make the puzzle for Monday's newspaper edition. <@&1111173789179453451>")
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 6:
        await comms_chat.send("Good afternoon! It's Sunday! Ideally, the story and puzzle for this Monday's newspaper edition should be finalized by now. <@&1111173789179453451>")
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 0:
        await comms_chat.send("Good afternoon! It's go time! Ideally, today's newspaper edition should be finalized and posted by now. <@&1111173789179453451>")
        
async def pro_reminders(client, guild, est_time):
    if est_time.hour == 20 and est_time.minute == 40 and est_time.weekday() == 0:
            pro_chat_id = 1101572607372951694 
            pro_chat = await guild.fetch_channel(pro_chat_id)
            await pro_chat.send("Good evening! It's 8:40 PM server time on Monday. This is a test of my ability to send reminders at a specific time!\nMake sure you're prepared to begin derby tomorrow!")

    if est_time.hour == 7 and est_time.minute == 30 and est_time.weekday() == 1:
            pro_chat_id = 1101572607372951694 
            pro_chat = await guild.fetch_channel(pro_chat_id)
            await pro_chat.send("In 30 minutes you may begin taking tasks!\nGood morning Pro Neighbors, it's currently 7:30am S.T. Our derby start time is at 8:00am S.T. If I forget to send an announcement you can go ahead and start at that time.\n<@&1024052938752151552> @everyone")

    if est_time.hour == 8 and est_time.minute == 0 and est_time.weekday() == 1:
            pro_chat_id = 1101572607372951694 
            pro_chat = await guild.fetch_channel(pro_chat_id)
            await pro_chat.send("You may now begin taking tasks!!\nGood morning Pro Neighbors, it's currently 8:00am S.T. Our derby start time is... now! We're off to the races!\n<@&1024052938752151552> @everyone")

    if est_time.hour == 16 and est_time.minute == 0 and est_time.weekday() == 4:
        pro_chat_id = 1167152706230681670
        pro_chat = await guild.fetch_channel(pro_chat_id)
        await pro_chat.send("Remember to post your personal task log! Logs are due in this channel in 4 hours for A&B derby lottery prize qualification! <@&1024052938752151552> @everyone")
        
    if est_time.hour == 20 and est_time.minute == 0 and est_time.weekday() == 4:
        pro_chat_id = 1167152706230681670
        pro_chat = await guild.fetch_channel(pro_chat_id)
        await pro_chat.send("Derby logs are now past due for A&B derby lottery prize qualification.")
        
    if est_time.hour == 0 and est_time.minute == 0 and est_time.weekday() == 0:
        pro_chat_id = 1167152706230681670
        pro_chat = await guild.fetch_channel(pro_chat_id)
        await pro_chat.send("Derby logs are due in this channel in 4 hours! (Also derby ends in 4 hours make sure your tasks are done) <@&1024052938752151552> @everyone")
        
    if est_time.hour == 4 and est_time.minute == 0 and est_time.weekday() == 0:
        pro_chat_id = 1167152706230681670
        pro_chat = await guild.fetch_channel(pro_chat_id)
        await pro_chat.send("Derby logs are now past due.")
        

async def carnival_reminders(client, guild, est_time):
    if est_time.hour == 8 and est_time.minute == 0 and est_time.weekday() == 1:
            pro_chat_id = 1342333687429070918 
            pro_chat = await guild.fetch_channel(pro_chat_id)
            await pro_chat.send("Good morning Carnival Neighbors, it's a new week! Remember to get in the game this week to accomplish something you're proud of, then post a screenshot here.\n<@&1342329111359656008> @everyone")

    if est_time.hour == 16 and est_time.minute == 0 and est_time.weekday() == 4:
        pro_chat_id = 1342333687429070918
        pro_chat = await guild.fetch_channel(pro_chat_id)
        await pro_chat.send("Remember to post your proud-moment screenshot here if you have one! There's still a few days left; I will give one more reminder on Sunday!\n<@&1342329111359656008> @everyone")
        
    if est_time.hour == 0 and est_time.minute == 0 and est_time.weekday() == 0:
        pro_chat_id = 1342333687429070918
        pro_chat = await guild.fetch_channel(pro_chat_id)
        await pro_chat.send("Final reminder to post your proud-moment screenshot here if you have one! The Council will begin tallying up the screenshots in 4 hours.\n<@&1342329111359656008> @everyone")

async def lotteries_reminders(client, guild, est_time):
    lott_chat_id = 1073421104057684058;
    lott_chat = await guild.fetch_channel(lott_chat_id);
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 2:
        target = await lott_chat.send("Good afternoon! It's Wednesday! Lotto for last week is due today. <@&1111174094965178468>");
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 6:
        target = await lott_chat.send("Good afternoon! Please roll the lottos with the bot before derby ends. <@&1111174094965178468>");

async def recruitment_reminders(client, guild, est_time):
    ad_chat_id = 792497521259315200
    ad_chat = await guild.fetch_channel(ad_chat_id)
    
    if not chance(3):
        return
    
    recruitment_peeps = [user.id for user in await users_with_role(guild, 1111174586030100552)]
    high_rank_peeps  = [user.id for user in await users_with_role(guild, 1198350047759319131)]
    high_rank_peeps.extend([user.id for user in await users_with_role(guild, 1198349892419072050)]);
    
    to_ping = random.choice(list(set(recruitment_peeps) & set(high_rank_peeps)))
    
    if est_time.hour == 12 and est_time.minute == 0:
        await ad_chat.send(f"<@{to_ping}> I've chosen you at random! If you get a chance, check r/HD #seeking-neighborhood for a couple people to message.\nWhen you do, react to their msg with the fox.\n\nI recommend you introduce yourself, lead with which NH you think they'd be a good fit for and why. Wait til they reply, then send our server link to prevent getting flagged for spam. Maybe ping them in server to check DMs too.")        

async def personalized_recruitment_reminder(client, guild, est_time):
    ad_chat_id = 792497521259315200
    ad_chat = await guild.fetch_channel(ad_chat_id)
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = days[est_time.weekday()]
    
    pins = await ad_chat.pins()
    latest_pin = pins[0].content if pins else ""
    
    todays_poster = None
    for line in latest_pin.split("\n"):
        if line.startswith(day_name):
            todays_poster = parse_mention(line)
    
    if est_time.hour < 9:
        for k in ["post_9am", "post_10am", "post_2pm", "post_6pm", "post_7pm"]:
            remember(k, None)
    
    if todays_poster is None:
        return  # can't do anything without a poster

    # 9am Reminder
    if est_time.hour >= 9 and est_time.minute >= 0 and remember("post_9am") is None:
        msg = await ad_chat.send(f"Now is the beginning of the acceptable ad-posting window. If you are able to wait 1 more hour to post, please do wait. If not, post now. <@{todays_poster}>\nCheck react this message when done.")
        if chance(7,3):
            await ad_chat.send(f"Also today is a Clover Day. pls post in Clover <@1282679887580102799>")
        await msg.add_reaction("✅")
        remember("post_9am", msg.id)

    # 10am Reminder
    elif est_time.hour >= 10 and est_time.minute >= 0 and remember("post_10am") is None:
        post_9am_id = remember("post_9am")
        if post_9am_id:
            post_9am = await ad_chat.fetch_message(post_9am_id)
            for r in post_9am.reactions:
                if str(r.emoji) == "✅" and r.count > 1:
                    return
        msg = await ad_chat.send(f"Now is the beginning of the **preferred** ad-posting window. Please try to post in the next 8 hours. <@{todays_poster}>\nCheck react this message when done.")
        await msg.add_reaction("✅")
        remember("post_10am", msg.id)
        
    # 2pm Reminder
    elif est_time.hour >= 14 and est_time.minute >= 0 and remember("post_2pm") is None:
        for key in ["post_9am", "post_10am"]:
            msg_id = remember(key)
            if msg_id:
                msg = await ad_chat.fetch_message(msg_id)
                for r in msg.reactions:
                    if str(r.emoji) == "✅" and r.count > 1:
                        return
        msg = await ad_chat.send(f"I don't think an ad has been posted yet, this is your midday reminder <@{todays_poster}> <@&1111174586030100552>.\nCheck react this message when done.")
        await msg.add_reaction("✅")
        remember("post_2pm", msg.id)

    # 6pm Reminder
    elif est_time.hour >= 18 and est_time.minute >= 0 and remember("post_6pm") is None:
        for key in ["post_9am", "post_10am", "post_2pm"]:
            msg_id = remember(key)
            if msg_id:
                msg = await ad_chat.fetch_message(msg_id)
                for r in msg.reactions:
                    if str(r.emoji) == "✅" and r.count > 1:
                        return
        msg = await ad_chat.send(f"Now is the end of the **preferred** ad-posting window. Please try to post in the next 1 hours if you have not yet. <@&{1111174586030100552}>\nCheck react this message when done.")
        await msg.add_reaction("✅")
        remember("post_6pm", msg.id)

    # 7pm Reminder
    elif est_time.hour >= 19 and est_time.minute >= 0 and remember("post_7pm") is None:
        for key in ["post_9am", "post_10am", "post_2pm", "post_6pm"]:
            msg_id = remember(key)
            if msg_id:
                msg = await ad_chat.fetch_message(msg_id)
                for r in msg.reactions:
                    if str(r.emoji) == "✅" and r.count > 1:
                        return
        msg = await ad_chat.send(f"Now is the end of the acceptable ad-posting window. If you have not posted yet, please do not. <@&{1111174586030100552}>\nCheck react this message when done.")
        await msg.add_reaction("✅")
        remember("post_7pm", msg.id)
        
@command_handler.Command(access_type=AccessType.PUBLIC, desc = "Trade your BEMs with the Council Treasury!")
async def trade(activator: Neighbor, context: Context):
    # if len(context.args) < 2:
    #     raise CommandArgsError("Uses\n1) 2 arguments expected. 1: ['give'/'get'] 2: [amt]\n2) 4 Arguments expected. 1: 'even' 2) [#bolts] [#planks] [#tapes]")

    mode = context.args[0]
    amt = int(context.args[1])

    if mode == "give":
        gives = amt
        result = 0

        while amt >= 89:
            amt -= 89
            result += 65

        while amt >= 3:
            amt -= 3
            result += 2

        residual = int((amt / 3) * 2)
        result += residual

        await context.send(f"If the Neighbor gives {gives}, the Treasury can give {result}.", reply=True)

        if 0 < amt < 3:
            needed = 3 - amt
            improved_result = result - residual + 2
            await context.send(
                f"But for a slightly better deal, if the Neighbor gives {gives + needed}, "
                f"the Treasury can give {improved_result}.",
                reply=False
            )

    elif mode == "get":
        target = amt
        gives = 0

        while True:
            test_amt = gives
            remaining = test_amt
            result = 0

            while remaining >= 89:
                remaining -= 89
                result += 65

            while remaining >= 3:
                remaining -= 3
                result += 2

            residual = int((remaining / 3) * 2)
            result += residual

            if result >= target:
                await context.send(
                    f"To receive {target} from the Treasury, the Neighbor must give {gives}.",
                    reply=True
                )

                if 0 < remaining < 3:
                    needed = 3 - remaining
                    improved_result = result - residual + 2
                    await context.send(
                        f"But for a slightly better deal, the Treasury can give {improved_result}, "
                        f"if the Neighbor gives {gives + needed}.",
                        reply=False
                    )
                break

            gives += 1
    elif mode == 'even' and len(context.args) > 3:
        pass
    
    else:
        if len(context.args) < 2:
            raise CommandArgsError("Uses\n1) Two arguments expected. 1: ['give'/'get'] 2: [amt]\n2) 4 Arguments expected. 1: 'even' 2) [#bolts] [#planks] [#tapes]")
    
    # ANY INVALID TRADES?
        
    import gspread
    from google.oauth2.service_account import Credentials
    from collections import Counter

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet_id = "1v5wq4m-2SFBaQHLjyo0njGTtg-h8mof-i8cn8wBaSp8"
    workbook = client.open_by_key(sheet_id)
        
    sheet = workbook.worksheet("Totals");

    def lookup_row_values(sheet, search_term):
        col_a = sheet.col_values(1)  # Get all values in column A
        for i, val in enumerate(col_a):
            if val == search_term:
                row_index = i + 1  # gspread is 1-indexed
                values = sheet.row_values(row_index)
                return values[1:5]  # B = index 1, C = 2, D = 3
        return None  # Not found
    
    all_results = lookup_row_values(sheet, "Total")
    # await context.send(f"**The Council** has: {all_results[0]} bolts, {all_results[1]} planks, {all_results[2]} duct tape. For a total of {all_results[3]} BEMs!")

    # Unpack raw results (assumed order: Bolts, Planks, Tapes)
    print("DEBUG: raw all_results =", all_results)

    try:
        bolts = all_results[0]
        planks = all_results[1]
        tapes = all_results[2]
    except Exception as e:
        print("❌ Failed to unpack all_results!")
        print("❌ Error:", e)
        await context.send("Internal error: Could not read treasury values. Please report this.")
        return

    items = {
        "Bolts": int(bolts),
        "Planks": int(planks),
        "Tapes": int(tapes)
    }

    # Show parsed item values
    print("🔍 Treasury Inventory Parsed:")
    for k, v in items.items():
        print(f" - {k}: {v}")
    print()

    # Begin trade blocking logic
    for offered in items:
        for requested in items:
            if offered == requested:
                continue

            offered_amt = items[offered]
            requested_amt = items[requested]

            # Debug each comparison
            print(f"🔧 Checking trade: Offer {offered_amt} {offered}, Request {requested_amt} {requested}")
            print(f"🔧 Condition: {requested_amt} * 2 <= {offered_amt} → {requested_amt * 2 <= offered_amt}")

            if requested_amt * 2 <= offered_amt:
                msg = (
                    f"Unfortunately, the Treasury cannot currently give {requested} "
                    f"in exchange for {offered} due to stock. Please check back another time."
                )
                print("🚫 BLOCKED:", msg)
                await context.send(msg)
async def compliance(client, guild, est_time):
    if est_time.hour == 12 and est_time.minute == 40 and est_time.weekday() == 1:
        compliance_chat_id = 1257136669660811284
        compliance = await guild.fetch_channel(compliance_chat_id)

        await compliance.send(
            "Hello! <@&1257138773603647538>! I have chosen the below tasks at random to be completed this week. "
            "Please, ensure they are done, address issues, and post results here."
        )

        # Define possible NH and Family roles
        NH_roles = ["FFP", "FFM", "FFJ", "FFJ2", "FFG", "FFC"]
        Family_roles = ["Butterfly", "Cow", "Guinea Pig", "Puppy", "Squirrel", "Zebra"]

        # Templates (do NOT mutate these)
        task_templates = [
            *[
                "{NH} HK Log FORMAT Grading -- Please grade the most recent {NH} HK Log on a scale of 5 points.\n\n"
                "• Dock 1 point for any and each of the following requirements not met: 1) Headlined with derby type & Date of derby's start "
                "2) Points for all players marked 3) Status marked 4) Action marked, separately from status 5) Opt outs listed.\n\n"
                "• Dock .5 points for any and each aspect of the log that hurt a viewer's ability to interpret it. I.e., If something is confusing "
                "or action markings are not detailed enough."
            ] * 10,
            *[
                "{NH} HK ACCURACY Check -- Check the most recent {NH} HK log for **accuracy** against the real derby log and in-game neighbors. "
                "1) Are the scores listed correctly? 1) Were the correct people actually kicked or demoted in game? Promoted? "
                "2) Evaluate whether or not passes were given. If there were, valid? If there weren't, valid? "
                "3) Are sufficient notes included?"
            ] * 10,
            *[
                "{NH} Role check! Check that everyone with the {NH} role is in {NH} in-game, and make sure that everyone in the corresponding "
                "in-game group has the {NH} role. Are a lot of issues coming up? Remind council about role policies."
            ] * 10,
            *[
                "{Family} Role check! Check that everyone with the {Family} role is meant to have it. No one outside of a NH or in Resort should "
                "have it! No one should have two family roles!"
            ] * 10,
            "{Family} Role check! Check that everyone with the {Family} role is meant to have it. No one outside of a NH or in Resort should have it! No one should have two family roles!",
            "Council Role check! Check that everyone has the correct Rank role, the correct committee Roles, and the correct NH-Council roles.",
            "Hospitality tasks check! Make sure that the past week's worth of hospitality tasks have been marked as complete for all NHs and logged in respective threads.",
            "Reach out to any Council Member to compliment something they've done recently.",
            "Find *something* that can be improved or fixed up in any committee, any process, any system, any Neighborhood, and add it to the Council backburner or bring it up to the Council",
            "Joinlist check. Compare the last ~3 weeks of the joinlist with the HK logs. Make sure everyone is listed as they are meant to be.",
            "Leavelist check. Compare the last ~3 weeks of the leavelist with the HK logs. Make sure everyone is listed as they are meant to be AND a list is provided for leaving.",
            "Check to make sure lotteries were posted for the most recent 4 derbies. Make sure they were done correctly.",
            "Check the past ~3 weeks of #due-penalties. Anyone overdue? Any penalties not listed?",
            "Look at the past week of recruitment ads. Find a way to compliment the recruitment committee, and a way to suggest an improvement. Good variability? Good visuals? Easy to read/look at? **Are invite links working?**",
            "Look at the past ~3 weeks of TikTok posts. Make sure there are posts. Find a way to compliment the posters, and a way to suggest an improvement.",
            *["Resolve any un'check'ed tickets from the past couple weeks in <#1033544493728809000>."] * 10,
            "Check that there are NH-chat announcements for each Neighborhood posted for this week.",
            "Pick out the best NH-chat announcement posted this week, and make an example out of it in Council chat. 'Best' may include: intro to upcoming derby, review of previous derby, introduction of new neighbors, and perhaps some endearing, community engaged quality",
            "Check that two Council meetings -- once voice and one chat -- are occuring each month. Begin scheduling if needed.",
            "Pick out the best ad posted this week and make an expample of it for the recruitment commmittee.",
            "Check in with 3 committee chairs to ask what they need to improve the function or experience of their committee. Raise the matter to Council.",
            "Red tide!",
            "Pick one thing off the Council backburner to complete",
            "Ask 3 committee chairs if there is a good balance of workload between members. If not, see to it that the issue is resolved.",
            "Double check that HK committees are keeping up on people who are opted out long term. Maybe point out anyone who's at 4 weeks or more.",
            "Ping each Rank role separately in different messages (1 - 2 - 3) and remind them to / ask if they have gone through their rank's instructions. Link the #council-rank-instructions channel!",
        ]

        role_check_templates = [
            "{NH} Role check! Check that everyone with the {NH} role is in {NH} in-game, and make sure that everyone in the corresponding in-game group has the {NH} role. Are a lot of issues coming up? Remind council about role policies.",
            ]

        def instantiate(template: str) -> str:
            return (
                template.replace("{NH}", random.choice(NH_roles))
                        .replace("{Family}", random.choice(Family_roles))
            )

        compliance_peeps = [user.id for user in await users_with_role(guild, 1257138773603647538)]
        if not compliance_peeps:
            return

        chosen = []

        # GUARANTEE: at least one Role Check task is assigned,
        # and the assignee is uniformly random across all compliance_peeps.
        guaranteed_assignee = random.choice(compliance_peeps)
        guaranteed_task = instantiate(random.choice(role_check_templates))

        chosen.append(guaranteed_task)

        await compliance.send(
            f"Item 1: Assigned to <@{guaranteed_assignee}> (Please complete or get someone else to)"
        )
        target = await compliance.send(guaranteed_task + "\n\nAdd your check reaction once complete")
        await target.add_reaction("✅")

        # Remaining items (keep your original behavior: random assignee each item, tasks unique)
        for i in range(1, len(compliance_peeps)):
            # Pick a unique instantiated task
            choice = instantiate(random.choice(task_templates))
            while choice in chosen:
                choice = instantiate(random.choice(task_templates))
            chosen.append(choice)

            to_ping = random.choice(compliance_peeps)

            await compliance.send(
                f"Item {(i + 1)}: Assigned to <@{to_ping}> (Please complete or get someone else to)"
            )
            target = await compliance.send(choice + "\n\nAdd your check reaction once complete")
            await target.add_reaction("✅")
            
async def guests(client, guild, est_time):
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 6:
            general_chat_id = 648223397205114910 
            general = await guild.fetch_channel(general_chat_id)
            await general.send("**Action Required -- Check DMs**\n\nHello! <@&1154908058540052571>! My spidey senses tell me that you're sitting on the waitlist to join an FF Neighborhood. We can't wait to have you! If you believe this is an error, contact our leaders using: <#1033207181857800242>\n\nIf you are waiting to join, please check your DMs and DM requests as you likely have received a message from one of our leaders regarding the status of the waitlist. If you did, please acknowledge the info provided and answer any questions asked. If not, no action is required at this time.");


# @command_handler.Loop(days = 1, desc = "Sorts the Neighbors text file in order of descending XP once per day.", priority = 4)
async def database_mgmt():
    neighbors = Neighbor.read_all_neighbors();
    neighbors.sort(key=lambda x : x.get_XP());
    Neighbor.write_all_neighbors();

# @command_handler.Loop(hours = 12, desc = "Removes unneccesary members.")
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

# @command_handler.Loop(days = 1, desc = "On tuesdays and thursdays, a new channel called Farmerss Market appears that lets Neighbors sell crops to Greg for XP.")
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

        # guild = client.get_guild(PHOENIX.guild);
        # town_square = await guild.fetch_channel(PHOENIX.general_category);
        # market = await guild.create_text_channel("\U0001F33Efarmers-market", category=town_square)
        # await market.send(f"**Welcome to the Farmers Market!**\nFive crops are in demand today. To aceept a transaction, react with the number associated with that transaction. As you may be able to tell, crop #{boost_choice} is in particularly high demand today.")
        # target = await market.send(res)

        # fMarket = open("phoenix_market.txt", "w");
        # fMarket.write(str(target.channel.id) + "\n")
        # fMarket.write(str(target.id) + "\n")
        # for option in options:
        #     fMarket.write(str(option[0]) + "\n");
        #     fMarket.write(str(option[1]) + "\n");
        #     fMarket.write(str(option[2]) + "\n");
        # fMarket.close();

        # await target.add_reaction(unicodes[0]);
        # await target.add_reaction(unicodes[1]);
        # await target.add_reaction(unicodes[2]);
        # await target.add_reaction(unicodes[3]);
        # await target.add_reaction(unicodes[4]);
        # await target.pin();

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


@command_handler.Scheduled(time="00:01", day_of_month=1, desc="Reckoning warning")
async def reckoning_warning(client):
    guild = client.get_guild(FF.guild)
    bc = await guild.fetch_channel(FF.bot_channel)

    message = (
        "⚠️ **ATTENTION, FARMERS.** ⚠️\n\n"
        "The month turns. The clock resets. The paperwork is filed.\n\n"
        "**The Reckoning** arrives in **24 hours**.\n\n"
        "At that time, all players’ **server levels will be cleanly cut in half**, "
        "resulting in a dramatic reduction in XP.\n\n"
        "Of course, this event is *completely outside my control* and definitely not "
        "the result of a scheduled process that runs with impeccable timing every month, so take any complaints up with the universe itself.\n\n"
        "…Unrelated, my `$rss` shop remains fully stocked: rain or shine, reckoning or no; "
        "should anyone feel an urge to convert levels into tangible rewards before destiny intervenes please make a visit.\n\n"
    )

    target = await bc.send(message)
    await leaderboard(
        Neighbor(691338084444274728, 647883751853916162),
        Context(target)
    )

@command_handler.Scheduled(time="00:01", day_of_month=2, desc="Monthly XP reset")
async def xp_reset(client):
    # if not est_time.hour == 0 or not est_time.minute == 0:
    #     return;
    print('xp reset!');
    guild = client.get_guild(FF.guild);
    # current_time = datetime.datetime.now()
    # current_day = current_time.day
    # if current_day == 1:
    bc = await guild.fetch_channel(FF.bot_channel);
    # await bc.send("@everyone--the reckoning is upon you!")
    # await bc.send("Below is the discord leaderboard for the top 10 members of the server in the past month!")
    # await bc.send("In one day, the reckoning will ensue. To level the playing field without making everyone start from scratch, each person's level is reduced at the beginning of each month.")
    # await bc.send("If you intend/ed to spend your levels before the reset, you have approx 24 hours to do so. Use $rss to spend those levels baby!")
    # target = await bc.send("$leaderboard");
    # await leaderboard(Neighbor(691338084444274728, 647883751853916162), Context(target));
    # if current_day == 2:
    ff_guild = client.get_guild(FF.guild);
    guild = client.get_guild(FF.guild);
    await bc.send("It's about that time!");
    for i in range(5):
        await bc.send(f"{5-i}...");
        time.sleep(5);
    neighbors = Neighbor.read_all_neighbors();
    for readNeighbor in neighbors:
        neighbor = Neighbor(readNeighbor.ID, readNeighbor.family);
        cur_level = neighbor.get_level();
        strip(neighbor, levels = int(cur_level / 2));
        if int(neighbor.get_family()) == FF.guild:
            await bc.send(f"<@{neighbor.ID}> has dropped to level {neighbor.get_level()}");
        best_this_month = neighbor.get_item_of_name("Best Level This Month");
        if best_this_month:
            neighbor.vacate_item(best_this_month);
    await bc.send("That feels much better! All done. #sorrynotsorry")

# @command_handler.Scheduled(time="04:01")
async def start_farmmas_giveaway(client):
    
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
async def winners_farmmas_giveaway(client):
    
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
async def announce_last_farmmas2(client):
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




# @command_handler.Loop(days = 1, desc = "On mondays, the council is asked to select what derby type is coming up.")
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
            


# @command_handler.Loop(days = 1, desc = "From the second through fourth of each month, rss items are on sale. Also the 25th through the 28th")
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
async def swear_word_mgmt(client):
    swear_words.clear();
    with open("swearWords.txt") as fWords:
        for line in fWords.readlines():
            swear_words.append(line[:-1]);



# @command_handler.Loop(hours = 8, desc = "If a Neighbor has a passive XP item, the user receives free server XP once per hour.") # ADD BACK
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

# @command_handler.Loop(minutes = 20, desc = "Takes away rss roles if necessary")
async def role_mgmt(client):
    guild = client.get_guild(FF.guild);
    for member in guild.members:
        await set_roles(member, guild);

    guild = client.get_guild(PHOENIX.guild);
    for member in guild.members:
        await set_roles(member, guild);

# @command_handler.Loop(minutes = 10, desc = "The barn role icon is changed to a random barn.")
async def change_barn_role_icon(client):
    guild = client.get_guild(FF.guild);

@command_handler.Loop(hours = 8, desc = "Nick management")
async def nick_mgmt(client):
    guild = client.get_guild(FF.guild);
    async for member in guild.fetch_members():
        try:
            await set_nick(member, guild)
        except:
            pass

# @command_handler.Loop(minutes = 5, desc = "The rainbow role color is changed to a random color.")
async def change_rainbow_role_color(client):
    guild = client.get_guild(FF.guild);
    rainbow_role = guild.get_role(1055882917429137479);
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)

    # Convert the integers to hexadecimal strings
    r_hex = hex(r)[2:]  # slice off the "0x" prefix
    g_hex = hex(g)[2:]
    b_hex = hex(b)[2:]

    # Pad the strings with leading zeros if necessary
    r_hex = r_hex.rjust(2, '0')
    g_hex = g_hex.rjust(2, '0')
    b_hex = b_hex.rjust(2, '0')

    # Combine the strings into a single hex code string
    hex_v = f'#{r_hex}{g_hex}{b_hex}'
    await rainbow_role.edit(color=discord.Colour.from_str(hex_v));
    await guild.get_role(FF.blueberry_role).edit(color=discord.Colour.from_str("#01cdfe"));
    await guild.get_role(FF.strawberry_role).edit(color=discord.Colour.from_str("#ff71ce"));
    # guild = client.get_guild(PHOENIX.guild);
    # rainbow_role = guild.get_role(PHOENIX.rainbow_role);
    # await rainbow_role.edit(color=discord.Colour.from_str(hex_v));
    # await guild.get_role(PHOENIX.blueberry_role).edit(color=discord.Colour.from_str("#01cdfe"));
    # await guild.get_role(PHOENIX.strawberry_role).edit(color=discord.Colour.from_str("#ff71ce"));

@command_handler.Command(AccessType.DEVELOPER)
async def jointimeswithrange(activator: Neighbor, context: Context):
    # Argument parsing
    if len(context.args) >= 2:
        day_cutoff_start = int(context.args[0])  # e.g. 0 = now
        day_cutoff_end = int(context.args[1])    # e.g. 365 = 1 year ago
    elif len(context.args) == 1:
        day_cutoff_start = int(context.args[0])
        day_cutoff_end = 1095  # Default: 3 years
    else:
        day_cutoff_start = 0   # Default: now
        day_cutoff_end = 1095
        
    target = await context.send("Starting")

    # Calculate cutoffs
    now = datetime.datetime.now(datetime.timezone.utc)
    start_cutoff = now - datetime.timedelta(days=day_cutoff_start)
    end_cutoff = now - datetime.timedelta(days=day_cutoff_end)
    year_cutoff = now - datetime.timedelta(days=730)

    # Initialize
    channel = await context.guild.fetch_channel(648223397205114910)
    hour_counter = Counter()
    weekday_counter = Counter()
    month_counter = Counter()
    counter = 0
    i = 0
    
    total_range = (start_cutoff - end_cutoff).total_seconds()
    thresholds = [end_cutoff + datetime.timedelta(seconds=total_range * (p / 100)) for p in range(5, 101, 5)]
    threshold_index = 0

    # Message scanning
    async for msg in channel.history(limit=None, oldest_first=False):
        i += 1
        if msg.created_at < end_cutoff:
            break  # messages older than the end range
        if msg.created_at >= start_cutoff:
            continue  # skip too recent

        if i % 10000 == 0:
            await context.send(f"{counter} found")
            link = f"https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"
            await context.send(link)
            await asyncio.sleep(10)
            
        while threshold_index < len(thresholds) and msg.created_at < thresholds[threshold_index]:
            await context.send(f"{counter} found ({(threshold_index + 1) * 5}% through time range)")
            link = f"https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"
            await context.send(link)
            await asyncio.sleep(2)
            threshold_index += 1

        if msg.author.id == 691338084444274728 and "welcome to town" in msg.content.lower() or msg.type == discord.MessageType.new_member:
            counter += 1
            utc_time = msg.created_at.replace(tzinfo=datetime.timezone.utc)
            timestamp = utc_time + datetime.timedelta(hours=-4)  # Adjust for server time (e.g., EDT)
            hour_counter[timestamp.hour] += 1
            weekday_counter[timestamp.weekday()] += 1
            if msg.created_at >= year_cutoff:
                month_counter[timestamp.month] += 1

    # Output
    await context.send("Most common hours (ST): " + str(hour_counter.most_common()))
    await context.send("Most common weekdays: " + str(weekday_counter.most_common()))
    await context.send("Most common months: " + str(month_counter.most_common()))

    plot_histogram(hour_counter, "Hour of Day (ST)", "Joins", "joins_by_hour.png")
    plot_histogram(weekday_counter, "Day of Week (0=Mon)", "Joins", "joins_by_weekday.png")
    plot_histogram(month_counter, "Month of Year (1=Jan)", "Joins", "joins_by_month.png")

    await context.channel.send("Here's the join breakdown by hour:", file=discord.File("joins_by_hour.png"))
    await context.channel.send("Here's the join breakdown by weekday:", file=discord.File("joins_by_weekday.png"))
    await context.channel.send("Here's the join breakdown by month:", file=discord.File("joins_by_month.png"))

@command_handler.Command(AccessType.DEVELOPER)
async def jointimes(activator: Neighbor, context: Context):
    
    if len(context.args) > 1:
        day_cutoff_num = int(context.args[0])
        year_cutoff_num = int(context.args[1])
    else:
        day_cutoff_num = 1095
        year_cutoff = 730
    
    channel = await context.guild.fetch_channel(648223397205114910);

    hour_counter = Counter()
    weekday_counter = Counter()
    month_counter = Counter()
    counter = 0;

    day_cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=day_cutoff_num)
    year_cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=year_cutoff_num)

    i=0;
    async for msg in channel.history(limit=None, oldest_first=False):
        i += 1
        if msg.created_at < day_cutoff:
            break

        if i % 10000 == 0:
            await context.send(f"{counter} found")
            link = f"https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"
            await context.send(link)
            await asyncio.sleep(10)

        if msg.author.id == 691338084444274728 and "welcome to town" in msg.content.lower():
            counter += 1
            utc_time = msg.created_at.replace(tzinfo=datetime.timezone.utc)
            timestamp = utc_time + datetime.timedelta(hours=-4)
            hour_counter[timestamp.hour] += 1
            weekday_counter[timestamp.weekday()] += 1
            if not msg.created_at < year_cutoff:
                month_counter[timestamp.month] += 1

    await context.send("Most common hours (ST): " + str(hour_counter.most_common()))
    await context.send("Most common weekdays: " + str(weekday_counter.most_common()))
    await context.send("Most common months: " + str(month_counter.most_common()))

    plot_histogram(hour_counter, "Hour of Day (ST)", "Joins", "joins_by_hour.png")
    plot_histogram(weekday_counter, "Day of Week (0=Mon)", "Joins", "joins_by_weekday.png")
    plot_histogram(month_counter, "Month of Year (1=Jan)", "Joins", "joins_by_month.png")

    # Optional: upload to channel
    await context.channel.send("Here's the join breakdown by hour:", file=discord.File("joins_by_hour.png"))
    await context.channel.send("Here's the join breakdown by weekday:", file=discord.File("joins_by_weekday.png"))
    await context.channel.send("Here's the join breakdown by month:", file=discord.File("joins_by_month.png"))

def plot_histogram(counter, xlabel, ylabel, filename):
    import matplotlib.pyplot as plt

    keys = sorted(counter.keys())
    values = [counter[k] for k in keys]

    plt.figure()
    plt.bar(keys, values)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(f"{ylabel} by {xlabel}")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# @command_handler.Command(AccessType.PUBLIC, desc = "Finds submission rates of all families")
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

@command_handler.Command(AccessType.PUBLIC, desc="Provides information about Greg and various topics. Example: `$info blossom`.", generic=True)
async def info(activator: Neighbor, context: Context, keyword=None):
    
    final_answer_msg = await context.send("Searching...", reply=True)
    
    from helper_embedding import embed;
    
    keyword = keyword or " ".join(context.args).strip().lower();
    
    res = None;

    if keyword == "":
        res = (
            f"**Hi! my name is Greg :wave:**\n"
            f"I was created by Lincoln's Farm, & currently running Version {VERSION}.\n"
            f"I can do lots of things; use `$help` to find out more.\n"
            f"Version 3.0 comes with a more structured code base that makes me easier to maintain and update without any downtime blah blah blah. "
            f"3.0 also comes with new features including: reminders, giveaways, polls, and over 10 new RSS items to purchase!\n\n"
            f"If you care less about me and more about other stuff (ouch), you can use `$info` to obtain info about derby types (`$info blossom`), our neighborhoods (`$info FF`), and more! "
            f"See a list with (`$help info`)."
        )
    elif keyword == "thief":
        # Send image first
        with open("thief.png", 'rb') as file:
            await context.send(file=discord.File(file))

        res = (
            "Can you believe it! A silo thief on this side of the Mississippi!\n\n"
            "Eye witnesses have spotted this suspect breaking into silos in OUR TOWN!!! Unfortunately, due to their mask, it is impossible to identify the suspect. "
            "I recommend purchasing upgraded security for your Silo (which I happen to be selling at `$rss`). Trust no one!!\n\n"
            "*According to data gathered in the nearest town East, the thief seems to break into 10% of silos on 10% of days. "
            "From those silos, the thief takes 10% of the stock of 10% of its crops.*"
        )
    else:
        
        # Pull blurbs from the designated channel
        channel = await context.guild.fetch_channel(1173372758332276737)
        
        # CHECK CACHE
        
        cache = remember("info_blurb_cache")
        if cache and keyword in cache:
            try:
                message = await channel.fetch_message(cache[keyword]["id"])
            except:
                message = ""
            
            if message and ":" in message.content:
                raw_keywords, *content_parts = message.content.split(':')
                content = ":".join(content_parts).strip()
                keywords = [kw.strip().lower() for kw in raw_keywords.split(" or ")]
                
                if keyword in keywords:
                    res = content;
                    print("Found in cache")
                    
        # PATCH CACHE
        
        if not res:
            cache = remember("info_blurb_cache") or {}
            if keyword in cache:
                del cache[keyword]

            async for message in channel.history(limit=None):
                if ':' not in message.content:
                    continue  # Skip malformed messages

                # Split once per line into keyword and content
                raw_keywords, *content_parts = message.content.split(':')
                cur_content = ":".join(content_parts).strip()
                cur_keywords = [kw.strip().lower() for kw in raw_keywords.split(" or ")]

                for kw in cur_keywords:
                    if kw in cache and cache[kw]['id'] == message.id:
                        continue;
                    else:
                        cache[kw] = {}
                        cache[kw]['id'] = message.id
                        cache[kw]['embedding'] = embed(cur_content)
                    if kw == keyword:
                        res = cur_content;
                
            remember("info_blurb_cache", cache)
        
        # BEST GUESS (needs work)
            
        if not res:            
            query_embedding = embed(keyword)

            cache = remember("info_blurb_cache")
            
            blurb_embeddings = [v['embedding'] for v in cache.values()]

            from numpy import dot
            from numpy.linalg import norm

            def cosine_similarity(a, b):
                return dot(a, b) / (norm(a) * norm(b))

            # Compute similarity between query and each clause
            scores = [cosine_similarity(query_embedding, emb) for emb in blurb_embeddings]

            # Rank and return
            ranked_blurbs = sorted(zip(cache.items(), scores), key=lambda x: x[1], reverse=True)
            
            bestkw, bestv = ranked_blurbs[0][0]
            message = await channel.fetch_message(bestv['id']);
            if message and ":" in message.content:
                # Split once per line into keyword and content
                raw_keywords, *content_parts = message.content.split(':')
                content = ":".join(content_parts).strip()
                keywords = [kw.strip().lower() for kw in raw_keywords.split(" or ")]
                if bestkw in keywords:
                    res = content + f"\n-# I didn't have an exact match for {keyword}. This is for `{bestkw}`. Did you mean `{ranked_blurbs[1][0][0]}` or `{ranked_blurbs[2][0][0]}`?"

    # Apply formatting replacements
    for code, replacement in get_code_replacement("", True).items():
        res = res.replace(code, replacement)

    await final_answer_msg.edit(content=res)

async def get_help(neighbor, context, response: ResponsePackage):
    if response.name == "help":
        name = response.values["target_command"];
        res = command_handler.Command.generate_help_str(name);
        await context.send(res);

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

@command_handler.Command(AccessType.PRIVILEGED)
async def bems(activator: Neighbor, context: Context):
    if len(context.args) > 0:
        to_add = int(context.args[0])
    else:
        raise CommandArgsError()

    # Retrieve existing total or default to 0
    total_bems = remember("total_bems") or 0

    # Add the new amount
    total_bems += to_add

    # Store the new total
    remember("total_bems", total_bems)

    await context.send(f"✅ Added {to_add} BEM. New total is {total_bems}.", reply=True)


@command_handler.Command(AccessType.PUBLIC)
async def tickets_dict(activator: Neighbor, context: Context):
    """
    Builds a dict of {user_id: tickets} for every member in the guild,
    writes results to CSV + TXT, uploads both, logs progress,
    and ignores messages after a fixed UTC cutoff.
    """
    
    # from datetime import datetime, timezone

    cutoff_utc = datetime(2025, 7, 4, 3, 59, 0, tzinfo=timezone.utc)

    print("[tickets_dict] Starting ticket computation")
    print(f"[tickets_dict] Message cutoff set to {cutoff_utc.isoformat()}")

    # --------------------------
    # FIRST SET OF TASKS
    # --------------------------
    print("[tickets_dict] Building first task set")
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

    task_names = ["Wheel", "1", "2", "3", "Horse", "Juggler", "6", "7", "8"]

    for i, ch in enumerate(channels):
        if i != 4:
            task = Task(context.guild, ch, message_ids[i], points[i], task_just1image, task_names[i])
        else:
            task = Task(context.guild, ch, message_ids[i], points[i], task_2msg_300chars, task_names[i])
        tasks.append(task)

    print(f"[tickets_dict] First task set built ({len(tasks)} tasks)")

    # --------------------------
    # SECOND SET OF TASKS
    # --------------------------
    print("[tickets_dict] Building second task set")
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
        if i != 1:
            if i == 3:
                task2 = Task(context.guild, ch, message_ids2[i], points2[i], task_just1image, "Role")
            else:
                task2 = Task(context.guild, ch, message_ids2[i], points2[i], task_just1image, str(i))
        else:
            task2 = Task(context.guild, ch, message_ids2[i], points2[i], task_3msgs, str(i))
        tasks2.append(task2)

    print(f"[tickets_dict] Second task set built ({len(tasks2)} tasks)")

    # --------------------------
    # CONFIG
    # --------------------------
    gold_ids = {
        355169964027805698, 316114265645776896, 979407900801892383,
        648229959973994506, 398604838872809472, 1250644488649441291,
        935098241089929216, 240899039749603328, 969072183114625026,
        795304848181821481, 443437059793879051, 430454367003475978,
        220427859229933568, 874303613684580392
    }

    INJECT_UID = 1211781489931452447
    INJECT_TASK_INDEX = 3

    status = await context.send("Counting tickets for all members...")

    # --------------------------
    # Collect messages
    # --------------------------
    all_tasks = tasks + tasks2
    total_task_count = len(all_tasks)

    print(f"[tickets_dict] Scanning messages for {total_task_count} tasks (cutoff enforced)")

    player_msgs = {}

    for task_index, task in enumerate(all_tasks):
        print(f"[tickets_dict] Scanning task {task_index + 1}/{total_task_count}")

        for ch_id, msg_id in task.get_channels_and_startmsgs(context.guild):
            channel = await context.guild.fetch_channel(ch_id)
            start_message = await channel.fetch_message(msg_id)

            async for msg in channel.history(
                after=start_message,
                before=cutoff_utc,
                oldest_first=True,
                limit=None
            ):
                if any(str(r.emoji) == "👻" for r in msg.reactions):
                    continue

                uid = msg.author.id
                if uid not in player_msgs:
                    player_msgs[uid] = [[] for _ in range(total_task_count)]
                player_msgs[uid][task_index].append((channel, msg))

        print(f"[tickets_dict] Finished task {task_index + 1} — users so far: {len(player_msgs)}")
        await status.edit(content=f"Counting tickets... {task_index + 1}/{total_task_count}")

    # --------------------------
    # Score everyone
    # --------------------------
    members = context.guild.members
    tickets_by_id = {m.id: 0 for m in members}

    print(f"[tickets_dict] Scoring {len(members)} members")

    for idx, uid in enumerate(tickets_by_id):
        if idx % 25 == 0:
            print(f"[tickets_dict] Scoring member {idx}/{len(tickets_by_id)}")

        total = 0
        has_second = await bought_second_set(uid, context)
        available_tasks = tasks + (tasks2 if has_second else [])

        task_msg_lists = player_msgs.get(uid, [[] for _ in range(total_task_count)])

        for i, task in enumerate(available_tasks):
            ch_msg_ids = list(task_msg_lists[i])

            if i == INJECT_TASK_INDEX:
                injected = player_msgs.get(INJECT_UID)
                if injected:
                    ch_msg_ids.extend(injected[INJECT_TASK_INDEX])

            if ch_msg_ids and await task.evaluate(ch_msg_ids, uid):
                total += task.points

        if uid in gold_ids:
            total += 5

        tickets_by_id[uid] = total

    print("[tickets_dict] Scoring complete")

    # --------------------------
    # Write files
    # --------------------------
    sorted_rows = sorted(tickets_by_id.items(), key=lambda x: x[1], reverse=True)

    csv_path = "/tmp/tickets_by_id.csv"
    txt_path = "/tmp/tickets_by_id.txt"

    print("[tickets_dict] Writing CSV")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("user_id,tickets\n")
        for uid, t in sorted_rows:
            f.write(f"{uid},{t}\n")

    print("[tickets_dict] Writing TXT")
    with open(txt_path, "w", encoding="utf-8") as f:
        for uid, t in sorted_rows:
            f.write(f"{uid}: {t}\n")

    # --------------------------
    # Upload
    # --------------------------
    print("[tickets_dict] Uploading files")
    await context.send(
        content="Ticket totals for all members:",
        files=[
            discord.File(csv_path),
            discord.File(txt_path)
        ]
    )

    await status.edit(content="Ticket counting complete.")
    print("[tickets_dict] Finished successfully")

    return tickets_by_id

@command_handler.Command(AccessType.PUBLIC)
async def tickets(activator: Neighbor, context: Context):
    
    # FIRST SET OF TASKS
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
                        
        

@command_handler.Command(AccessType.DEVELOPER, desc="Find out how many tickets you've earned!")
async def tickets_done(activator: Neighbor, context: Context):
    
    if len(context.args) > 0 and context.args[0] == "family":
                
        target_msg = await context.send("Counting tickets...", reply=True)

        remember("task1_users", [])
        remember("task5_users", [])
        remember("task6_users", [])

        family_role_ids = [
            1328866582327332955, 1328866706294046720, 1328866759654248651,
            1328866832500658360, 1328866921185153085, 1328867017901477970
        ]
        family_names = ["Butterflies", "Cows", "Guinea Pigs", "Puppies", "Squirrels", "Zebras"]
        family_totals = [0 for _ in family_names]
        family_roles = [context.guild.get_role(x) for x in family_role_ids]
        role_id_to_index = {role.id: i for i, role in enumerate(family_roles)}

        user_to_family = {}
        async for member in context.guild.fetch_members(limit=None):
            for role in member.roles:
                if role.id in role_id_to_index:
                    user_to_family[member.id] = role_id_to_index[role.id]
                    break

        user_ticket_totals = {}
        bonus_contributors = {i: [] for i in range(len(family_names))}

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
        
        task_completions = [];

        for i, chan_spec in enumerate(channels):
            if isinstance(chan_spec, tuple):
                chan_ids = chan_spec
                msg_ids = message_ids[i]
            else:
                chan_ids = [chan_spec]
                msg_ids = [message_ids[i]]

            user_char_data = {} if chan_ids[0] == 1179484606370689074 else None

            for chan_id, msg_id in zip(chan_ids, msg_ids):
                try:
                    channel = await context.guild.fetch_channel(chan_id)
                    start_msg = await channel.fetch_message(msg_id)
                except Exception as e:
                    print(f"Skipping channel {chan_id} due to error: {e}")
                    continue

                credited_users = set()

                try:
                    async for msg in channel.history(after=start_msg, oldest_first=True, limit=None):
                        author_id = msg.author.id
                        if author_id in credited_users or author_id not in user_to_family:
                            continue

                        family_index = user_to_family[author_id]

                        if chan_id == 1179484606370689074:
                            if author_id not in user_char_data:
                                user_char_data[author_id] = {'chars': 0, 'msgs': 0}

                            user_char_data[author_id]['chars'] += len(msg.content)
                            user_char_data[author_id]['msgs'] += 1

                            print(f"[CHAR LOG] +{len(msg.content)} chars from user {author_id} "
                                f"(total: {user_char_data[author_id]['chars']} chars in "
                                f"{user_char_data[author_id]['msgs']} msgs)")

                            if user_char_data[author_id]['chars'] >= 300 and user_char_data[author_id]['msgs'] >= 2:
                                family_totals[family_index] += points[i]
                                user_ticket_totals[author_id] = user_ticket_totals.get(author_id, 0) + points[i]
                                if i in [0, 4, 5]:
                                    task_key = f"task{i+1}_users"
                                    current_list = remember(task_key)
                                    if author_id not in current_list:
                                        current_list.append(author_id)
                                        remember(task_key, current_list)
                                        print(f"Remembered {author_id} in {task_key}. Current list length: {len(remember(task_key))}")
                                credited_users.add(author_id)
                                print(f"> Credited user {author_id} for channel {chan_id} (char-based)")

                        else:
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
                                family_totals[family_index] += points[i]
                                user_ticket_totals[author_id] = user_ticket_totals.get(author_id, 0) + points[i]
                                if i in [0, 4, 5]:
                                    task_key = f"task{i+1}_users"
                                    current_list = remember(task_key)
                                    if author_id not in current_list:
                                        current_list.append(author_id)
                                        remember(task_key, current_list)
                                        print(f"Remembered {author_id} in {task_key}. Current list length: {len(remember(task_key))}")
                                credited_users.add(author_id)
                                print(f"> Credited user {author_id} for channel {chan_id} (image-based)")

                except discord.DiscordServerError as e:
                    print(f"Error scanning channel {chan_id}: {e}")
                    continue

        # 🎯 Bonus Ticket Logic
        donations = [935098241089929216, 1250644488649441291, 398604838872809472,
                    648229959973994506, 355169964027805698, 316114265645776896,
                    979407900801892383, 969072183114625026]

        for user_id, total in user_ticket_totals.items():
            if total >= 30 or (total >= 25 and user_id in donations):
                family_index = user_to_family[user_id]
                family_totals[family_index] += 5
                bonus_contributors[family_index].append(user_id)
                print(f"[BONUS] +5 bonus tickets to {family_names[family_index]} from user {user_id} (total: {total})")

        # 📦 Final Output Formatting
        result_lines = [
            f"{family_names[i]} have {family_totals[i]} <:blue_carnival_ticket:1246080867114422335>!"
            for i in range(len(family_names))
        ]

        for i, user_ids in bonus_contributors.items():
            if user_ids:
                names = []
                for uid in user_ids:
                    member = context.guild.get_member(uid)
                    if member:
                        names.append(member.display_name)
                if names:
                    result_lines.append(f"-# {family_names[i]} have gained bonus tickets from {', '.join(names)}")

        result = "\n".join(result_lines)
        await target_msg.edit(content=result)
    else:
        
        if len(context.args) > 0:
            try:
                target = await context.guild.fetch_member(int(parse_mention((context.args[0]))));
            except:
                candidates = [x.nick for x in context.guild.members if not x.nick is None];
                candidates.extend([x.name for x in context.guild.members if (x.nick is None) or (not x.nick == x.name)]);

                name, confidence = best_string_match(context.args[0], [str(x) for x in candidates]);
                # print(name);
                target = discord.utils.get(context.guild.members, display_name = name);
                target = target if not target is None else discord.utils.get(context.guild.members, name = name);
        else:
            target = None;

        target_member = context.author if target is None else target;
        target_neighbor = Neighbor(target_member.id, context.guild.id);
    
        target_msg = await context.send("Counting your tickets...", reply=True)

        total_score = await count_tickets(target_neighbor.ID, context);

        task_breakdown = "\n".join(
            f"Task {i+1}: {'✅' if completed else '❌'}"
            for i, completed in enumerate(total_score[1])
        )
        
        task_breakdown = "# Set 1\n" + task_breakdown;
        task_breakdown += "\nTask 10: This task is counted separately."
        task_breakdown += "\nSee the task board: <#1384644404408487956>"
        async def bought_second_set(user_id, context):
            chan = await context.guild.fetch_channel(1386906153593606256)
            async for msg in chan.history(oldest_first=True, limit=None):
                if str(user_id) in msg.content:
                    return True;
            return False;
        if await bought_second_set(target_neighbor.ID, context):
            task_breakdown += "\n# Set 2"
            task_breakdown += "\n-# Please note that task 2 is not yet being counted properly."
            total_score2 = await count_tickets2(target_neighbor.ID, context);
            task_breakdown2 = "\n".join(
                f"Task {i+1}: {'✅' if completed else '❌'}"
                for i, completed in enumerate(total_score2[1])
            )
            task_breakdown2 += "\nSee the task board: <#1386484938643341414>"
            
            donations = [935098241089929216, 1250644488649441291, 398604838872809472, 648229959973994506, 355169964027805698, 316114265645776896, 979407900801892383, 969072183114625026, 240899039749603328]
        
            await target_msg.edit(content=(
                f"{target_member.display_name} has earned {total_score[0] + total_score2[0] - 5} " +
                "<:blue_carnival_ticket:1246080867114422335>!\n" +
                ("Plus 5 <:golden_carnival_ticket:1246080949620441190> (Thank you 🥰🏳️‍🌈)\n" if target_neighbor.ID in donations else "") +
                f"{task_breakdown}\n" +
                f"{task_breakdown2}\n" + 
                "**Tasks due <t:1751342340:R>**"
            ))
            
            return;
            

        donations = [935098241089929216, 1250644488649441291, 398604838872809472, 648229959973994506, 355169964027805698, 316114265645776896, 979407900801892383, 969072183114625026, 240899039749603328]
        
        await target_msg.edit(content=(
            f"{target_member.display_name} has earned {total_score[0]} " +
            "<:blue_carnival_ticket:1246080867114422335>!\n" +
            ("Plus 5 <:golden_carnival_ticket:1246080949620441190> (Thank you 🥰🏳️‍🌈)\n" if target_neighbor.ID in donations else "") +
            f"{task_breakdown}\n" +
            f"Buy the second set of tasks here: https://discord.com/channels/647883751853916162/1384642555425198080/1386905977487626431 \n" +
            "**Tasks due <t:1751342340:R>**"
        ))
        
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
            

# @command_handler.Command(AccessType.PRIVILEGED, desc = "Give or take tickets")
# async def tickets(activator: Neighbor, context: Context):
    
#     remember 

# @command_handler.Loop(hours = 6)
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

     
@command_handler.Uncontested(type="MESSAGE")
async def help_in_context(context: Context):
    if (context.content.startswith("$")):
        return;
    for name in command_handler.Command.available_commands.keys():
        if f"${name}" in context.content:
            await context.react("❓")
            def key(ctx):
                if not ctx.message.id == context.message.id:
                    return False;
                if not ctx.emoji.name == "❓":
                    return False;
                return True;
            ResponseRequest(get_help, "help", "REACTION", context, context, key, target_command=name);

@command_handler.Command(AccessType.PUBLIC, desc = "Provides a list of available commands, or alternatively describes the function of a particular command. For example, `$help help`", generic = True)
async def help(activator: Neighbor, context: Context):
    if len(context.args) > 0:
        res = command_handler.Command.generate_help_str(context.args[0]);
    else:
        res = command_handler.Command.generate_help_str(None, context.guild.id == FF.guild);
    await context.send(res);

@command_handler.Command(AccessType.PUBLIC, desc = "Welcome to Greg!")
async def hello(activator: Neighbor, context: Context):
    await context.send("**Hello, I am Greg!**\n\nI am a Bot, and I do most of the work around here :rolling_eyes:\n\nI was programmed by one of our Council Members <@355169964027805698>, and I have two main purposes:\n> 1. For fun! I control our server's level system. You can chat anywhere in the server to level up, then spend your levels on cool discord perks. For example: special role colors, role icons, nickname tags, and more.\n> 2. For business! I control our server's modmail system in <#1033207181857800242>, our reminders, our welcome messages, and more.\n\nYou're going to get to know me very well!\n\nAnd oh yeah, Rose is my mortal enemy.", reply = True);

@command_handler.Command(AccessType.PUBLIC, desc="Gets video link for video")
async def video(activator: Neighbor, context: Context):
    if len(context.args) < 1:
        raise CommandArgsError("`$video` expects 1 argument: the name of the neighborhood to display the video for")
    else:
        match context.args[0].lower():
            case "ffp" | "pro":
                res = "https://youtu.be/LIn8YGXMBE8?si=WJsu0h2dOupuigRN"
            case "ff" | "main":
                res = "https://youtu.be/4gJZS0lnERg?si=CdNv0WbWjgY43WSE"
            case "ffj" | "junior":
                res = "https://youtu.be/1RAj4UbPePw?si=uHqrqlU2qc3QBTdg"
            case "ffg" | "garden":
                res = "https://youtu.be/1RAj4UbPePw?si=uHqrqlU2qc3QBTdg"
            case "ffc" | "carnival":
                res = "https://youtu.be/jZnVF8oYMg8"
            case "ffr" | "resort":
                res = "Not available"
            case _:
                raise CommandArgsError("That's not one of the FF neighborhoods, or I don't have a video for it!");
        await context.send(res, reply = True);

@command_handler.Command(AccessType.PUBLIC, desc="Get space info about an NH")
async def space(activator: Neighbor, context: Context): 
    if len(context.args) < 1:
        raise CommandArgsError("`$tag` expects 1 argument: the name of the neighborhood to display the tag of")
    else:
        nh_name = context.args[0].lower()
        match nh_name:
            case "ffp" | "pro":
                rl = 1024052938752151552
                cl = 1101572888437477427
            case "ff" | "main":
                rl = 656112994392080384
                cl = 932008962809794620
            case "ffj" | "junior":
                rl = 689928709683150909
                cl = 1072605841267626025
            case "ffj2" | "junior2":
                rl = 1334660124639236267
                cl = 1334666607246708776
            case "ffg" | "garden":
                rl = 1173325157767589988
                cl = 1172210561644232794
            case "ffc" | "carnival":
                rl = 1342329111359656008
                cl = 1342334582963568661
            case "ffr" | "resort":
                rl = 1034248720058945577
                cl = 1072605891431514203
            case _:
                raise CommandArgsError("That's not one of the FF neighborhoods!");
        
        nh_count = await get_role_count(context.guild, rl);
        nh_count += 1 if nh_name == "ffj" else 0;
        channel = await context.guild.fetch_channel(cl)
        wl_count = 0
        async for _ in channel.history(limit=None):
            wl_count += 1;
            
        wl_count = int(wl_count) - 1
            
        if nh_count > 29:
            await context.send(f"It looks like {nh_name} **is full**!\nWith {nh_count} Neighbors and ~{wl_count} WLed players, it looks liked no one can be onboarded.",reply=True)
        elif nh_count + wl_count > 29:
            await context.send(f"It looks like {nh_name} **may be full**!\nWith {nh_count} Neighbors and ~{wl_count} WLed players, it looks like the NH should be full after WLed players onboarded.",reply=True)
        elif nh_count + wl_count < 30 and wl_count > 0:
            await context.send(f"It looks like {nh_name} **may have space**!\nWith {nh_count} Neighbors and ~{wl_count} WLed players, it looks like the NH should have space after WLed players onboarded.",reply=True)
        elif nh_count + wl_count < 30:
            await context.send(f"It looks like {nh_name} **has space**!\nWith {nh_count} Neighbors and ~{wl_count} WLed players, it looks like someone can be added now.",reply=True)
        

@command_handler.Command(AccessType.DEVELOPER, desc = "Set your tags and perks")
async def perks(activator: Neighbor, context: Context):
    await context.send("Discord perks given by Greg can include nickname emoji tags, and roles. Here, you can select which of your current perks are being displayed.\nFor example, if you have too many, turn some off. Or just switch things up.\nOften, perks earned from events will be applied automatically for a month, then unapplied for a couple months before they finally expire. ")

@command_handler.Command(AccessType.PUBLIC, desc = "Get the tag of an FF Neighborhood with `$tag FFP`, `$tag FF`, `$tag FFJ`, or `$tag FFR`")
async def tag(activator: Neighbor, context: Context):
    if len(context.args) < 1:
        raise CommandArgsError("`$tag` expects 1 argument: the name of the neighborhood to display the tag of")
    else:
        match context.args[0].lower():
            case "ffp" | "pro":
                res = "#LQVJ9QVR"
            case "ff" | "main":
                res = "#9UPRVCUR"
            case "ffj" | "junior":
                res = "#PC8VCJ8Q"
            case "ffj2" | "junior2":
                res = "#RGP8J9GP"
            case "ffg" | "garden":
                res = "#QP8JURUC"
            case "ffc" | "carnival":
                res = "#G8P8YGPG"                
            case "ffr" | "resort":
                res = "#L92LUVQJ"
            case _:
                raise CommandArgsError("That's not one of the FF neighborhoods!");
        await context.send(res, reply = True);

@command_handler.Command(AccessType.PUBLIC, desc = "Invites greg to celebrate an event or achievement", generic = True)
async def celebrate(activator: Neighbor, context: Context):
    if context.guild.id == 647883751853916162:
        first = ['Congratulations!',
            'Yay!! <:blue_red_hearts:856202113339490304>',
            'Wohoo!!',
            'Amazing!!',
            'Celebration time!!',
            'Let\'s goooo!',
            ':star_struck::star_struck:',
            'I\'ve taken a quick break from my chores on the farm to say…',
            ':raised_hands: :raised_hands:',
            ':smiley_cat: :smile_cat: :smirk_cat:',
            ':tada::tada::tada:',
            'slay !!',
            'Hey, don\'t start the party without ~~Rose, your favorite FF Helper!~~ Greg, your *favorite* FF Helper.',
            ':men_with_bunny_ears_partying::people_with_bunny_ears_partying::women_with_bunny_ears_partying:',
            'Greg ~~V2.0~~ **V3.0** is here, we should be celebrating *that*!! But if you insist...',
            'I\'ve been waiting for this one!',
            'Let\'s celebrate!!'
            ':butterfly: On behalf of the butterfly family...',
            ':leopard: On behalf of the cheetah family...',
            ':fox: Oxn behalf of the fox family...',
            ':horse_racing: On behalf of the horse family...',
            ':dog: On behalf of the puppy family...',
            'The Neighbors of the FFP, FF, FFJ, FFJ2, FFC, FFG and FFR family want you to know...',
            'Greg, at your service! One day closer to replacing Rose every day!',
            '<:ff_logo:1111011971953872976><:ff_logo:1111011971953872976><:ff_logo:1111011971953872976>',
            '<:ffp_logo:1111011980061462538><:ff_logo:1111011971953872976><:ffj_logo:1111011976320122880><:ffg_logo:1173332572642754560><:ffr_logo:1111011982787743866>',
            '<:ffr_logo:1111011982787743866><:ffr_logo:1111011982787743866><:ffr_logo:1111011982787743866>',
            '<:ffp_logo:1111011980061462538><:ffp_logo:1111011980061462538><:ffp_logo:1111011980061462538>',
            '<:ffp_logo:1111011980061462538><:ffp_logo:1111011980061462538><:ffp_logo:1111011980061462538>',
            '<:ffj_logo:1111011976320122880><:ffj_logo:1111011976320122880><:ffj_logo:1111011976320122880>',
            '<:ffg_logo:1173332572642754560><:ffg_logo:1173332572642754560><:ffg_logo:1173332572642754560>',
            '<:ffj2_logo:1335746631236194344><:ffj2_logo:1335746631236194344><:ffj2_logo:1335746631236194344>',
            '<:ffc_logo:1342333117607710741><:ffc_logo:1342333117607710741><:ffc_logo:1342333117607710741>',
            'Drum roll please...',
            'You summoned me... for this?',
            ];

        second = ['~~Wait, what happened? I missed it :grimacing:~~ \nJust kidding. Rose would have missed it, but I could never!',
            'https://tenor.com/view/snoop-dogg-rap-hip-hop-west-coast-crips-gif-24898891',
            'https://tenor.com/view/celebrate-weekend-vibe-friday-be-like-gif-4811973',
            'https://tenor.com/view/baby-yoda-babyyoda-gif-20491479',
            'https://tenor.com/view/schitts-creek-david-i-feel-like-that-needs-to-be-celebrated-gif-13054100',
            'https://tenor.com/view/%E0%A4%B0%E0%A4%BE%E0%A4%A7%E0%A4%BE%E0%A4%B8%E0%A5%8D%E0%A4%B5%E0%A4%BE%E0%A4%AE%E0%A5%80-fire-works-celebrate-gif-12772532',
            'https://tenor.com/view/cookie-monster-dancing-swag-ernie-sesame-street-gif-23523854',
            'https://tenor.com/view/leonardo-dicaprio-cheers-%C5%9Ferefe-celebration-celebrating-gif-20368613',
            'https://tenor.com/view/madagascar-zuba-this-calls-for-a-celebration-celebration-celebrate-gif-22777408',
            'https://tenor.com/view/dace-gif-25608746'
            'https://tenor.com/view/fortnite-dance-fortnite-emote-default-dance-meme-school-background-gif-26343206',
            'https://tenor.com/view/omg-schock-cat-gif-20299170',
            'https://tenor.com/view/omg-wow-really-surprised-feeling-it-gif-15881647',
            'https://www.youtube.com/watch?v=HPuD7w_TbSc',
            'https://tenor.com/view/bb13-big-brother13-lawon-exum-bblawon-bb13lawon-gif-14741549',
            'https://tenor.com/view/yeah-yeaa-yippie-yippi-happy-gif-23469210',
            'https://tenor.com/view/trump-shuffle-gif-19016904',
            'https://tenor.com/view/excited-hive-hivechat-community-blockchain-gif-18465569',
            'https://tenor.com/view/excited-so-gif-23170060',
            'https://tenor.com/view/abbott-elementary-hyped-turnt-lit-turn-up-gif-25388930',
            'Sorry, no gif today kid. You know how it is. Supply chain issues, inflation, etc etc',
            'https://tenor.com/view/nice-clap-hand-gif-23085040',
            'https://tenor.com/view/iconic-rupaul-rupauls-drag-race-all-stars-legendary-show-stopping-gif-26155592',];
    else:
        first = ['Congratulations!',
            'Yay!! <:blue_red_hearts:856202113339490304>',
            'Wohoo!!',
            'Amazing!!',
            'Celebration time!!',
            'Let\'s goooo!',
            ':star_struck::star_struck:',
            'I\'ve taken a quick break from my chores on the farm to say…',
            ':raised_hands: :raised_hands:',
            ':smiley_cat: :smile_cat: :smirk_cat:',
            ':tada::tada::tada:',
            'slay !!',
            'Hey, don\'t start the party without ~~Rose, your favorite FF Helper!~~ Greg, your *favorite* FF Helper.',
            ':men_with_bunny_ears_partying::people_with_bunny_ears_partying::women_with_bunny_ears_partying:',
            'Greg ~~V2.0~~ **V3.0** is here, we should be celebrating *that*!! But if you insist...',
            'I\'ve been waiting for this one!',
            'Let\'s celebrate!!'
            'Greg, at your service! One day closer to replacing Rose every day!',
            'You summoned me... for this?']

        second = ['~~Wait, what happened? I missed it :grimacing:~~ \nJust kidding. Rose would have missed it, but I could never!',
            'https://tenor.com/view/snoop-dogg-rap-hip-hop-west-coast-crips-gif-24898891',
            'https://tenor.com/view/celebrate-weekend-vibe-friday-be-like-gif-4811973',
            'https://tenor.com/view/baby-yoda-babyyoda-gif-20491479',
            'https://tenor.com/view/schitts-creek-david-i-feel-like-that-needs-to-be-celebrated-gif-13054100',
            'https://tenor.com/view/%E0%A4%B0%E0%A4%BE%E0%A4%A7%E0%A4%BE%E0%A4%B8%E0%A5%8D%E0%A4%B5%E0%A4%BE%E0%A4%AE%E0%A5%80-fire-works-celebrate-gif-12772532',
            'https://tenor.com/view/cookie-monster-dancing-swag-ernie-sesame-street-gif-23523854',
            'https://tenor.com/view/leonardo-dicaprio-cheers-%C5%9Ferefe-celebration-celebrating-gif-20368613',
            'https://tenor.com/view/madagascar-zuba-this-calls-for-a-celebration-celebration-celebrate-gif-22777408',
            'https://tenor.com/view/dace-gif-25608746'
            'https://tenor.com/view/fortnite-dance-fortnite-emote-default-dance-meme-school-background-gif-26343206',
            'https://tenor.com/view/omg-schock-cat-gif-20299170',
            'https://tenor.com/view/omg-wow-really-surprised-feeling-it-gif-15881647',
            'https://www.youtube.com/watch?v=HPuD7w_TbSc',
            'https://tenor.com/view/bb13-big-brother13-lawon-exum-bblawon-bb13lawon-gif-14741549',
            'https://tenor.com/view/yeah-yeaa-yippie-yippi-happy-gif-23469210',
            'https://tenor.com/view/trump-shuffle-gif-19016904',
            'https://tenor.com/view/excited-hive-hivechat-community-blockchain-gif-18465569',
            'https://tenor.com/view/excited-so-gif-23170060',
            'https://tenor.com/view/abbott-elementary-hyped-turnt-lit-turn-up-gif-25388930',
            'Sorry, no gif today kid. You know how it is. Supply chain issues, inflation, etc etc'];

    await context.send(random.choice(first), reply = True);
    await context.send(random.choice(second));

@command_handler.Command(AccessType.PUBLIC, desc = "Invites greg to welcome a user to the server.", generic = True)
async def welcome(activator: Neighbor, context: Context):
    choices = [
        'https://tenor.com/view/welcome-gif-23701526',
        'https://tenor.com/view/come-hello-welcome-gif-25024386',
        'https://tenor.com/view/welcome-welcome-to-the-team-minions-gif-21749603',
        'https://tenor.com/view/baby-yoda-welcome-gif-22416975',
        'https://tenor.com/view/welcome-gif-24657148',
        'https://tenor.com/view/simpson-gif-25340727',
        'https://tenor.com/view/welcome-gif-26452760',
    ]

    await context.send(random.choice(choices));

@command_handler.Command(AccessType.PUBLIC, desc = "Displays a top-10 leaderboard of the Neighbors with the most XP, or other leaderboards with an argument.", generic = True)
async def leaderboard(activator: Neighbor, context: Context):

    configure = None if not len(context.args) > 0 else context.args[0];

    if configure == "tickets":
        
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
        client = gspread.authorize(creds)

        # Open the Google Sheets file
        sheet = client.open_by_key("1MwBbJkxU0Fuvt9xpvyxE7Tk9xv5g_-VST9kC2Mu3qpo")
        worksheet = sheet.worksheet("Sheet1")
            
        records = worksheet.get_all_records()

        # Dictionary to store aggregated data
        user_data = {}

        # Aggregate data by ID
        for record in records:
            user_id = record['Member']
            value = int(record['Amt'])  # Assuming 'Value' column contains numeric values
            
            if user_id in user_data:
                user_data[user_id] += value
            else:
                user_data[user_id] = value
                
        worksheet = sheet.worksheet("Sheet2")
            
        records = worksheet.get_all_records()
        # Aggregate data by ID
        for record in records:
            user_id = record['ID']
            value = int(record['Value'])  # Assuming 'Value' column contains numeric values
            
            if user_id in user_data:
                user_data[user_id] += value
            else:
                user_data[user_id] = value
        
        for id in user_data:
            total_amt = user_data[id];
            
            total_amt += 10;
        
            level_ten = [969072183114625026, 540254243374891018, 355169964027805698, 991065750003413053, 324879796612104192, 324879796612104192, 963533131854532638, 718586817204715690, 987955038804639744, 930879531122847774, 648229959973994506, 516969515486019604, 796827295260213318, 527633575655243796, 160694804534132736, 774352602678558790, 383316515098984448, 514413698761359400];
            if id in level_ten:
                total_amt += 3;
            
            quiz = [783068480190414868, 374979463789805570, 296100775795621888, 346934600007811073, 1133914166772649984, 964990145835204608, 336806742610411522];
            if id in quiz:
                total_amt += 1;
            bonus_tickets_1 = [774352602678558790, 660204032362545152, 346934600007811073, 528379103007735809, 964990145835204608, 167006983986085888, 316114265645776896,1236505424258400301, 653329917836263443, 712392530750341150];
            if id in bonus_tickets_1:
                total_amt += 1;
            bonus_tickets_2 = [374979463789805570, 660204032362545152, 316114265645776896, 799819969503428659, 712392530750341150, 516969515486019604, 774352602678558790, 346934600007811073, 167006983986085888, 964990145835204608];
            if id in bonus_tickets_2:
                total_amt += 2;
            bonus_tickets_3 = [361834124060655616, 167006983986085888, 774352602678558790, 528379103007735809, 660204032362545152, 964990145835204608, 799819969503428659, 346934600007811073, 718404913331306508, 712392530750341150];
            if id in bonus_tickets_3:
                total_amt += 3;
                
            user_data[id] = total_amt;
        
        # Sort dictionary by values in descending order
        sorted_user_data = dict(sorted(user_data.items(), key=lambda item: item[1], reverse=True))
        
        result = "";
        for user_id, total_value in sorted_user_data.items():
            result += f"<@{user_id}>: {total_value} blue tickets\n"
        await context.send(result);
        return;
        
    if configure == "families":
        family_info = {
            "butterflies": 0,
            "cheetahs": 0,
            "foxes": 0,
            "horses": 0,
            "puppies": 0};
        with open('families.txt', 'r') as fFams:
            lines = fFams.readlines();
            family_info["butterflies"] = lines[0];
            family_info["cheetahs"] = lines[1];
            family_info["foxes"] = lines[2];
            family_info["horses"] = lines[3];
            family_info["puppies"] = lines[4];

        res = "";
        for key, val in family_info.items():
            res += f"**{key}:** {val}"
        await context.send(res);
        return

    neighbors = Neighbor.read_all_neighbors();
    neighbors = sorted(neighbors, key=lambda x: (x.XP if not configure == "legacy" else x.legacyXP))[::-1];
    neighbors = [x for x in neighbors if (int(x.get_family()) == context.guild.id)]

    length = len(neighbors) if configure == "all" else (10 if (configure is None or not configure.isnumeric()) else int(configure));

    leaderboard_neighbors = [x for x in neighbors if (not context.guild.get_member(x.ID) is None and not context.guild.get_member(x.ID).bot)][:length];

    if configure is None:
        res = "**Official Discord Leaderboard!**\nThe following users are the top 10 members with the most xp.\n";
    elif configure == "all":
        res = "**Discord Leaderboard!**\nAll users in server listed in order of xp.\n";
    elif configure == "legacy":
        res = "**Legacy Discord Leaderboard!**\nIn an alternate universe, in which XP is never reset nor used to buy things in my rss...\nAka: Top 10 XP earners of all time:\n"
    else:
        res = "**Discord Leaderboard!**\nTop " + str(length) + " users in server listed in order of xp.\n";

    list = "";
    c = 1;
    i = 0;

    while c < length + 1 and i < len(neighbors):
        cur = context.guild.get_member(neighbors[i].ID);
        if not cur is None:
            name = cur.display_name;
            XP = neighbors[i].XP if not configure == "legacy" else neighbors[i].legacyXP
            if neighbors[i] in leaderboard_neighbors:
                list += f"{c}) **{name}** (XP: {XP})\n";
                c += 1;
            else:
                list += f"{c - 0.5}) *{name}* (XP: {XP})\n";
        i += 1;

    await context.send(res + list);

@command_handler.Command(AccessType.PUBLIC, desc = "Display's a Neighbor's profile.", generic = True)
async def profile(activator: Neighbor, context: Context):
    if len(context.args) > 0:
        try:
            target = await context.guild.fetch_member(int(parse_mention((context.args[0]))));
        except:
            candidates = [x.nick for x in context.guild.members if not x.nick is None];
            candidates.extend([x.name for x in context.guild.members if (x.nick is None) or (not x.nick == x.name)]);

            name, confidence = best_string_match(context.args[0], [str(x) for x in candidates]);
            # print(name);
            target = discord.utils.get(context.guild.members, display_name = name);
            target = target if not target is None else discord.utils.get(context.guild.members, name = name);
    else:
        target = None;

    target_member = context.author if target is None else target;
    target_neighbor = Neighbor(target_member.id, context.guild.id);

    target_neighbor.expire_items();

    pretty_profile = target_neighbor.get_item_of_name("Prettier Profile");

    nick = context.guild.get_member(target_member.id);
    XP = target_neighbor.get_XP();

    current_lvl = target_neighbor.get_level();
    next_lvl = current_lvl + 1;

    xp_toward_next_lvl = XP - Neighbor.get_XP_for_level(current_lvl);
    xp_for_next_lvl = Neighbor.get_XP_for_level(next_lvl) - Neighbor.get_XP_for_level(current_lvl);

    progress = xp_toward_next_lvl / xp_for_next_lvl;
    progress_bar = "\U000025FB" * int(progress * 10)
    progress_bar += "\U000025FC" * int(10 - len(progress_bar));

    if not context.guild.id == FF.guild:
        neighborhood = "";
        user_role_ids = [role.id for role in target_member.roles];
        if context.ID_bundle.main_nh in user_role_ids:
            neighborhood += " PR";
        if context.ID_bundle.baby_nh in user_role_ids:
            neighborhood += " BP"
        profile = f"**{target_member.display_name}**\n";
        profile += f"**Level: {current_lvl}**\tXP: {XP}\n";
        profile += progress_bar + "\n";
        # if not neighborhood is None and not family is None:
        profile += f"NH: {neighborhood}\n";
        profile += "\nExpiring Soon:\n";
        inventory = target_neighbor.get_inventory();
        original_len = len(inventory);
        inventory = [x for x in inventory if x.expiration != -1]
        displayed = 0;
        if len(inventory) == 0:
            profile += "> None!\n";
        else:
            inventory.sort(key = lambda x : 10000000000 if x.expiration == -1 else x.expiration);
            for i, item in enumerate(inventory):
                displayed += 1;
                if i > 4:
                    break;
                profile += "> " + str(item) + "\n";
        if original_len > displayed:
            profile += "*Use `$inventory` to view full inventory*";
        await context.send(profile);
    elif pretty_profile is None:
        neighborhood = get_neighborhood_from_user(target_member);
        family = get_family_from_user(target_member)['name'].upper();
        profile = f"**{target_member.display_name}**\n";
        profile += f"**Level: {current_lvl}**\tXP: {XP}\n";
        profile += progress_bar + "\n";
        # if not neighborhood is None and not family is None:
        profile += f"NH: {neighborhood}\n";
        profile += f"Family: {family}\n";
        
        introductions_channel = await context.guild.fetch_channel(783713419831279697)
        
        introduction_link = None;
        async for message in introductions_channel.history(oldest_first=False,limit=1000):
            if message.author.id == target_member.id:
                if "#" in message.content and len(message.content) > 99:
                    introduction_link = f"https://discord.com/channels/{context.guild.id}/{message.channel.id}/{message.id}";
                    profile += f"Introduction: {introduction_link}\n"
                    break;
        if not introduction_link:
            profile += f"No recent introduction (with farm tag) written yet: <#783713419831279697>\n"
        
        # else:
        #     profile += "Guest\n";

        # RE-ADD this 
        # profile += "\nExpiring Soon:\n";
        # inventory = target_neighbor.get_inventory();
        # original_len = len(inventory);
        # inventory = [x for x in inventory if x.expiration != -1]
        # displayed = 0;
        # if len(inventory) == 0:
        #     profile += "> None!\n";
        # else:
        #     inventory.sort(key = lambda x : 10000000000 if x.expiration == -1 else x.expiration);
        #     for i, item in enumerate(inventory):
        #         displayed += 1;
        #         if i > 4:
        #             break;
        #         profile += "> " + str(item) + "\n";
        # if original_len > displayed:
        #     profile += "*Use `$inventory` to view full inventory*";
            
    #     import gspread
    #     from google.oauth2.service_account import Credentials
        
    #     scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    #     creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
    #     client = gspread.authorize(creds)

    #     # Open the Google Sheets file
    #     sheet = client.open_by_key("1MwBbJkxU0Fuvt9xpvyxE7Tk9xv5g_-VST9kC2Mu3qpo")
    #     worksheet = sheet.worksheet("Sheet1")

    #     # Find the last row with data
    #     records = worksheet.get_all_values()

    #     # Calculate the sum of amounts for the specified member
    #     total_amt = sum(int(record[1]) for record in records if record[0] == str(target_member.id));
        
    #     worksheet = sheet.worksheet("Sheet2")

    #     # Find the last row with data
    #     records = worksheet.get_all_values()

    #     # Calculate the sum of amounts for the specified member
    #     total_amt += sum(int(record[1]) for record in records if record[0] == str(target_member.id));

    #     total_amt += 10;
        
    #     level_ten = [969072183114625026, 540254243374891018, 355169964027805698, 991065750003413053, 324879796612104192, 324879796612104192, 963533131854532638, 718586817204715690, 987955038804639744, 930879531122847774, 648229959973994506, 516969515486019604, 796827295260213318, 527633575655243796, 160694804534132736, 774352602678558790, 383316515098984448, 514413698761359400, 346934600007811073];
    #     if target_member.id in level_ten:
    #         total_amt += 3;
        
    #     quiz = [783068480190414868, 374979463789805570, 296100775795621888, 346934600007811073, 1133914166772649984, 964990145835204608, 336806742610411522];
    #     if target_member.id in quiz:
    #         total_amt += 1;
    #     bonus_tickets_1 = [774352602678558790, 660204032362545152, 346934600007811073, 528379103007735809, 964990145835204608, 167006983986085888, 316114265645776896,1236505424258400301, 653329917836263443, 712392530750341150];
    #     if target_member.id in bonus_tickets_1:
    #         total_amt += 1;
    #     bonus_tickets_2 = [374979463789805570, 660204032362545152, 316114265645776896, 799819969503428659, 712392530750341150, 516969515486019604, 774352602678558790, 346934600007811073, 167006983986085888, 964990145835204608];
    #     if target_member.id in bonus_tickets_2:
    #         total_amt += 2;
    #     bonus_tickets_3 = [361834124060655616, 167006983986085888, 774352602678558790, 528379103007735809, 660204032362545152, 964990145835204608, 799819969503428659, 346934600007811073, 718404913331306508, 712392530750341150];
    #     if target_member.id in bonus_tickets_3:
    #         total_amt += 3;

    #     profile += f"\n\n**Ticket inventory:**\n";
    #     profile += f"> {total_amt} <:blue_carnival_ticket:1246080867114422335>\n"
    #     profile += f"> 0 <:golden_carnival_ticket:1246080949620441190>"
            
        await context.send(profile);
    # else:
    #     neighborhood = get_neighborhood_from_user(target_member);
    #     family = get_family_from_user(target_member);
    #     embed = discord.Embed(title=f"**{nick}**", color=target_member.color)
    #     embed.add_field(name="XP", value=f"{XP}", inline=True)
    #     embed.add_field(name="Level", value=f"{current_lvl}", inline=True)
    #     embed.add_field(name="Progress", value=f"{progress_bar}", inline=False)

    #     if not neighborhood is None and not (family == 0 or family == "0"):
    #         embed.add_field(name="Neighborhood", value=f"{neighborhood}", inline=True)
    #         embed.add_field(name="Family", value=f"{family}", inline=True)
    #     else:
    #         embed.add_field(name="Status", value="Guest", inline=False)
    #     embed.set_thumbnail(url=target_member.display_avatar.url)
    #     embed.set_footer(text = "Prettier Profile");
        # target = await context.channel.send(embed = embed);


@command_handler.Command(AccessType.PUBLIC, desc = "Profile that shows all inventory items.", generic = True)
async def inventory(activator: Neighbor, context: Context):
    if len(context.args) > 0:
        try:
            target = await context.guild.fetch_member(int(parse_mention((context.args[0]))));
        except:
            candidates = [x.nick for x in context.guild.members if not x.nick is None];
            candidates.extend([x.name for x in context.guild.members if (x.nick is None) or (not x.nick == x.name)]);

            name, confidence = best_string_match(context.args[0], [str(x) for x in candidates]);
            # print(name);
            target = discord.utils.get(context.guild.members, display_name = name);
            target = target if not target is None else discord.utils.get(context.guild.members, name = name);
    else:
        target = None;

    target_member = context.author if target is None else target;
    target_neighbor = Neighbor(target_member.id, context.guild.id);

    target_neighbor.expire_items();

    pretty_profile = target_neighbor.get_item_of_name("Prettier Profile");

    profile = "\nFull Inventory:\n";
    inventory =  target_neighbor.get_inventory();
    if len(inventory) == 0:
        profile += "> Empty!";
    else:
        inventory.sort(key = lambda x : 10000000000 if x.expiration == -1 else x.expiration);
        for item in inventory:
            profile += "> " + str(item) + "\n";

    await context.send(profile);

@command_handler.Command(AccessType.PUBLIC, desc = "Displays how much server XP it takes to achieve a level.", generic = True)
async def level(activator: Neighbor, context: Context):
    if len(context.args) > 0:
        if not context.args[0].isnumeric() or int(context.args[0]) < 1 or int(context.args[0]) > 999999:
            raise CommandArgsError("When passed with an argument, `level` expects a number between 1 and 999999.")
        level = int(context.args[0]);
        await context.send(f"It takes **{Neighbor.get_XP_for_level(level)}xp** to reach level {level}");
    else:
        await context.send(f"You need **{activator.get_XP_for_next_level()}xp** to reach your next level");

@command_handler.Command(AccessType.PRIVILEGED, desc = "", generic = True)
async def invis(activator: Neighbor, context: Context):
    role = context.guild.get_role(1084644944431554570);
    new_color = discord.Colour(int('36393f', 16));
    await role.edit(color = new_color)
    1084644944431554570

@command_handler.Command(AccessType.PUBLIC, desc = "Calculates the BEM penalty for a neighbor of a certain level and number of missed tasks. For example, `$penalty 50 5` calculates the BEMs required of a level 50 player who misses 5 tasks.")
async def penalty(activator: Neighbor, context: Context):
    try:
        level = int(context.args[0]);
        tasks_missed = int(context.args[1]);
    except:
        raise CommandArgsError("`penalty` expects two arguments: player level and # of tasks missed");

    penalty_per_task = int(level / 10);

    total_penalty = penalty_per_task * tasks_missed;
    penalty = min(total_penalty, int(level / 2));
    power_derby_penalty = min(real_round(total_penalty / 2), int(level / 2))

    await context.send(f"A level {level} player who misses {tasks_missed} tasks owes **{penalty} BEMs** in normal derby!!", reply = True)
    await context.send(f"However, this player would only owe *{power_derby_penalty}* during a power derby.")
    await context.send(f"||During code gold, they owe {penalty * 2} BEMs during non-power derbies, and {power_derby_penalty * 2} during power derby. Please check with a council member or the announcements channel to see if this week is a code gold week.||");

def real_round(x):
    decimal = x - int(x);
    if decimal >= .5:
        return int(x) + 1;
    else:
        return int(x);


#  Note to self: fix best_this_month: Actually update special offer count & check before showing category

@command_handler.Command(AccessType.PRIVATE, desc = "Allows Neighbors to purchase discord perks like special roles using server XP", generic = True, active=False)
async def rss(activator: Neighbor, context: Context, response: ResponsePackage = None):

    if activator.ID == 355169964027805698:
        with open('indev_rss.json') as fRSS:
            rss_info = json.load(fRSS)
    else:
        with open('rss.json') as fRSS:
            rss_info = json.load(fRSS)

    # if activator.get_level() < 3:
    #     await context.send("Whoops! You're too poor to access my RSS. Try again at level 3!");
    #     return;

    best_this_month = activator.get_item_of_name("Best Level This Month");

    if not response or response.name == "main":
        res = "**Welcome to Greg's Roadside Shop!**\n";
        res += "Here, you can buy an assortment of items with your server xp levels.\n"
        res += "Below are the several categories of items I offer. React with the emoji that corresponds to the one you would like to open.\n\n";

        locked = False;
        category_emojis = []
        for category in rss_info:
            if category["name"] == "Special Offers":
                if activator.get_level() > 5 or activator.get_level() < 5:
                    continue;
            if category["name"] == "Icons":
                if context.guild.id != FF.guild:
                    continue;
            if int(best_this_month.get_value("level")) < category['unlock']:
                res += f"> {category['emoji']} *Unlocks at level {category['unlock']}* {unicodes['locked']}\n";
                locked = True;
            else:
                res += f"> {category['emoji']} {category['name']}\n";
                category_emojis.append(category['emoji']);
        if locked:
            res += "\n" + unicodes['unlocked'] + "*To unlock a category, you must attain a certain level. Once you unlock a category, it will be available until the next __reckoning__.*";

        if response is None:
            target = await context.send(res);
            target_context = Context(target);
        else:
            target_context = response.response_context;
            target = target_context.message;
            await target.clear_reactions();
            await target.edit(content = res);

        def key(context):
            if not context.message.id == target.id:
                return False;
            if not context.user.id == activator.ID:
                return False;
            if not context.emoji.name in category_emojis:
                return False;
            return True;
        ResponseRequest(rss, "category", "REACTION", context, target_context, key)

        for emoji in category_emojis:
            await target.add_reaction(emoji);

    elif response.name == "category" or response.name == "re-category":
        activation_context = response.activation_context;
        target_context = response.response_context;
        target = target_context.message;
        await target.clear_reactions();

        if response.name == "category":
            chosen_category = None;
            for category in rss_info:
                print(category['emoji']);
                if response.content.name == category['emoji']:
                    chosen_category = category;
        else:
            chosen_category = response.values["category"];

        item_emojis = [];
        res = f"**Greg's Roadside Shop: {chosen_category['name']}**\n";
        res += chosen_category['description'] + "\n\n";
        for item in chosen_category['items']:
            #check if correct server
            if item["name"] == "*Family Logo Tag* -- Best Seller":
                if context.guild.id != FF.guild:
                    continue;
            if item["name"] == "Phoenix Merch":
                if context.guild.id != PHOENIX.guild:
                    continue;
            item_emojis.append(item['emoji']);
            res += f"> {item['emoji']} {item['name']}\n";
        res += f"*You are viewing category: {chosen_category['name']}. React with {unicodes['back']} to select a different category*";

        await target.edit(content = res);

        item_emojis.append(unicodes['back'])
        def key(context):
            if not context.user.id == activator.ID:
                return False;
            if not context.emoji.name in item_emojis:
                return False;
            if not context.message.id == target.id:
                return False;
            return True;
        ResponseRequest(rss, "item", "REACTION", context, target_context, key, category = chosen_category)

        for emoji in item_emojis:
            await target.add_reaction(emoji);

    elif response.name == "item":

        activation_context = response.activation_context;
        target_context = response.response_context;
        target = target_context.message;
        await target.clear_reactions();
        chosen_category = response.values["category"];
        chosen_item = None;

        for item in chosen_category['items']:
            if response.content.name == item['emoji']:
                chosen_item = item;
                break;
        else:
            response.name = "main";
            await rss(activator, context, response);
            return;

        res = f"**{chosen_item['name']}**\n";
        res += f"{chosen_item['description']}\n"
        bank = False;
        if 'warning' in chosen_item:
            res += f"> Warning: {chosen_item['warning']}\n"
        if 'cost' in chosen_item:
            cost = int(chosen_item['cost']);
            if activator.get_level() >= cost:
                xp_conversion = Neighbor.get_XP_for_level(activator.get_level()) - Neighbor.get_XP_for_level(activator.get_level() - cost);
                res += f"> Cost: {cost} levels [xp conversion ≈ {xp_conversion}xp]\n";
            else:
                res += f"> Cost: {cost} levels [xp conversion ≈ {Neighbor.get_XP_for_level(cost)}]\n";
            if activator.get_item_of_name("GregBanking(TM)"):
                res += f"> Bank xp cost: " + str(int(Neighbor.get_XP_for_level(int(chosen_item['cost'])) * 1.25)) + "xp\n"
                bank = True;
        else:
            if chosen_item['name'] == "Highest Bidder":
                with open("data/trex_cost.txt", "r") as fRex:
                    cost = int(fRex.readline());
                    label = cost
                    res += f"> Cost: {cost} levels\n"
            else:
                res += f"> Cost: **{int(chosen_item['min_cost'])}-{int(chosen_item['max_cost'])}**\n"
        res += f"> Lasts: {chosen_item['duration_label']}\n"
        res += f"*React with {unicodes['check']} to confirm purchase*";
        confirmation_emojis = [];
        confirmation_emojis.append(unicodes['check']);
        if bank:
            res += f"\n*React with {unicodes['bank']} to purchase this item with xp in your GregBanking account.*"
            confirmation_emojis.append(unicodes['bank'])
        confirmation_emojis.append(unicodes['back']);

        await target.edit(content = res);

        def key(context):
            if not context.user.id == activator.ID:
                return False;
            if not context.emoji.name in confirmation_emojis:
                return False;
            if not context.message.id == target.id:
                return False;
            return True;
        ResponseRequest(rss, "confirmation", "REACTION", context, target_context, key, category = chosen_category, item = chosen_item)

        await target.add_reaction(unicodes['check']);
        if activator.get_item_of_name("GregBanking(TM)"):
            await target.add_reaction(unicodes['bank']);
        await target.add_reaction(unicodes['back']);

    elif response.name == "confirmation":
        activation_context = response.activation_context;
        target_context = response.response_context;
        target = target_context.message;
        chosen_category = response.values["category"];
        chosen_item = response.values["item"];

        cost = int(chosen_item["cost"])
        xp_cost = int(Neighbor.get_XP_for_level(int(chosen_item['cost'])) * 1.25);
        if response.content.name == unicodes['check']:
            if not activator.get_level() >= int(chosen_item["cost"]):
                await context.send("Whoops! You're too poor for this item.")
                ResponseRequest(rss, "confirmation", "REACTION", context, target_context, response.key, category = chosen_category, item = chosen_item)
                return;
            else:
                if not activator.get_item_of_name(chosen_item["name"]):
                    strip(activator, levels = cost);
                else:
                    await context.send("You already have this item!");
                    return;
        elif response.content.name == unicodes['bank']:
            bank_item = activator.get_item_of_name("GregBanking(TM)")
            if not int(bank_item.get_value("xp")) >= xp_cost:
                await context.send("Whoops! You're too poor for this item.")
                ResponseRequest(rss, "confirmation", "REACTION", context, target_context, response.key, category = chosen_category, item = chosen_item)
                return;
            else:
                if not activator.get_item_of_name(chosen_item):
                    xp = int(bank_item.get_value("xp"));
                    xp -= xp_cost;
                    bank_item.update_value("xp", xp);
                    activator.update_item(bank_item);
                else:
                    await context.send("You already have this item!");
                    return;
        elif response.content.name == unicodes['back']:
            response.name = "re-category";
            response.content = chosen_category['emoji']
            await rss(activator, context, response);
            return;

        if 'duration' in chosen_item:
            duration = int(time.time()) + int(chosen_item['duration']);
        else:
            duration = -1;

        item = chosen_item;

        match item['type']:
            case "passive":
                give = Item(item['name'], item['type'], duration, needs = Neighbor.get_XP_for_level(cost + 2), so_far = 0);
            case "bank":
                give = Item(item['name'], item['type'], duration, opened = int(time.time()), xp = 10000, interest = 0);
            case "tag":
                give = Item(item['name'], item['type'], duration, val = datetime.datetime.now().month - 1)
            case "role_upgrade":
                user = await context.guild.fetch_member(activator.ID)
                give = Item(item['name'], item['type'], duration);
                if item['name'] == "Upgraded NH Role":
                    NH = get_neighborhood_from_user(user);
                    if has_role(user, context.guild.get_role(648188387836166168)):
                        to_give_role = context.guild.get_role(1390807436583239781);
                        await user.add_roles(to_give_role);
                    match NH:
                        case "FFP":
                            to_give_role = context.guild.get_role(1390751487327604776);
                        case "FF":
                            to_give_role = context.guild.get_role(1390751659424223343);
                        case "FFJ":
                            to_give_role = context.guild.get_role(1390751653036294194);
                        case "FFJ2":
                            to_give_role = context.guild.get_role(1390752478496034826);
                        case "FFG":
                            to_give_role = context.guild.get_role(1390753599453270168);
                        case "FFC":
                            to_give_role = context.guild.get_role(1390752595207000216);                            
                    await user.add_roles(to_give_role);
                                                        
                elif item['name'] == "Holographic Role":
                    glowing = context.guild.get_role(1452414125006262375)
                    await user.add_roles(glowing);
            case _:
                give = Item(item['name'], item['type'], duration);

        if 'special_offer' in chosen_item:
            best_this_month = activator.get_item_of_name("Best Level This Month");
            free_count_so_far = int(best_this_month.get_value("free_count"));
            best_this_month.update_value("free_count", free_count_so_far + 1);
            activator.update_item(best_this_month);

        await context.send(f"Congrats! Your new item: {item['name']} has been applied!");
        await context.send(f"Your new level: {activator.get_level()}");
        activator.bestow_item(give);
        user = await context.guild.fetch_member(activator.ID);
        await set_nick(user, context.guild);
        await set_roles(user, context.guild);


@command_handler.Command(AccessType.PRIVATE, desc = "Turn off Greg pings with `$pings off` or back on with `$pings on`", generic = True)
async def pings(activator: Neighbor, context: Context, choice = None):
    if len(context.args) < 1:
        raise CommandArgsError("`$pings` expects one argument: `on` or `off`");
    match context.args[0].lower():
        case "on":
            ping_item = activator.get_item_of_name("Pings Off");
            activator.vacate_item(ping_item);
            await context.send("Pings... back on!")
        case "off":
            ping_item = activator.get_item_of_name("Pings Off");
            if ping_item:
                await context.send("Already have pings off!");
                return;
            else:
                ping_item = Item("Pings Off", "pings", -1);
                activator.bestow_item(ping_item);
                await context.send("Pings have been turned off! You should only recieve a ping from greg at the very end of each month and when you open a Greg ticket. If you get any other pings, contact Lincoln or use $report.\n\nUse `$pings on` to get pings back");
                return;
        case _:
            raise CommandArgsError("`$pings` expects one argument: `on` or `off`");

async def get_photos(activator: Neighbor, context: Context):
    today = datetime.datetime.now();
    # today.weekday(): Monday is 0, Sunday is 6
    offset = today.weekday()  # how many days since last Monday
    if not offset:
        offset = 7;
    most_recent_monday = today - datetime.timedelta(days=offset)
    monday = most_recent_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    channel = await context.guild.fetch_channel(1342333687429070918);

    messages = []
    async for message in channel.history(after=monday, oldest_first=True, limit=None):
        messages.append(message)
        
    def has_attachment(message):
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                return True;
        return False;

    image_messages = []
    for message in messages:
        if has_attachment(message):
            image_messages.append(message);
            
    return image_messages;
            
@command_handler.Command(AccessType.PUBLIC, desc = "Send a meme!", generic = True)
async def meme(activator: Neighbor, context: Context):
    
    if chance(2):
    
        image_directory = './memes'  # change this to the directory containing your images
        image_list = os.listdir(image_directory)
        random_image = random.choice(image_list)
        image_path = os.path.join(image_directory, random_image)

        with open(image_path, 'rb') as f:
            picture = discord.File(f)
            await context.send(content="-# Courtesy of Hay Day instagram", file=picture, reply = True);
            
    else:
        meme_channel = await context.guild.fetch_channel(1403415307736846468)
        image_list = [];
        
        async for message in meme_channel.history(limit = None):
            has_image = (
            any(att.content_type and att.content_type.startswith("image/") for att in message.attachments) or
            any(embed.type == "image" or (embed.image and embed.image.url) for embed in message.embeds)
            )
            
            if has_image:
                image_list.append(message)
                
        
        files: list[discord.File] = []

        for att in random.choice(image_list).attachments:
            # Filter to images (by content_type when available, else by extension)
            is_image = (att.content_type or "").startswith("image/") or att.filename.lower().endswith(IMAGE_EXTS)
            if not is_image:
                continue

            # Convert to a discord.File without writing to disk
            # (downloads the bytes from Discord’s CDN under the hood)
            f = await att.to_file(
                filename=att.filename,        # preserve the original name
                spoiler=False,      # preserve spoiler flag
                use_cached=True,            # optional (discord.py ≥2.1): avoid re-fetch if cached
            )
            files.append(f)

        if not files:
            return  # nothing to send

        # Discord hard limit: max 10 files per message
        await context.send(files=files)
        
        
            

# @command_handler.Command(AccessType.PRIVATE, desc = "Lets a Neighbor harvest crops.", generic = True, active=False)
async def harvest(activator: Neighbor, context: Context, response: ResponsePackage = None):

    raise PardonOurDustError();

    if response is None:
        if chance(10):
            await context.send("Did you know? Try `$sell` to sell the entire contents of your silo! Or wait for the farmers market channel to appear for potentially much higher returns.", reply = True);

        activator.expire_items();

        GMO_item = activator.get_item_of_name("GMO Crops");

        if activator.get_item_of_name("Harvest Cooldown") and not activator.get_item_of_name("HarvestNow(TM) Fertilizer"):

            await context.send(f"Whoops! You've already harvested in the past hour. Crops don't grow overnight you know! Well...");
            return;
        elif activator.get_item_of_name("Harvest Cooldown") and activator.get_item_of_name("HarvestNow(TM) Fertilizer"):
            await context.send("Your HarvestNow(TM) Fertilizer is being used now.")
            harvest_block_item = activator.get_item_of_name("Harvest Cooldown");
            fertilizer_item = activator.get_item_of_name("HarvestNow(TM) Fertilizer");
            activator.vacate_item(harvest_block_item);
            activator.vacate_item(fertilizer_item);
            activator.bestow_item(Item("HarvestNowBlock", "block", time.time() + 3600));
        cur = time.time();
        # print(activator.get_inventory());
        new_bock = Item("Harvest Cooldown", "harvest", (cur + 3600));
        activator.bestow_item(new_bock);
        # print(activator.get_inventory());

        silo_item = activator.get_item_of_name("Silo");
        if silo_item is None:
            current_silo = {name: 0 for name, val in crops.items()};
            temp = Item("Silo", "silo", -1, **current_silo);
            activator.bestow_item(temp);

        else:
            old_silo = {name: int(val) for name, val in silo_item.values.items()}
            old_values = list(old_silo.values());

            current_silo = {name: 0 for name, val in crops.items()};
            for i, key in enumerate(current_silo.keys()):
                if i < len(old_values):
                    current_silo[key] = old_values[i]


        list_crops = list(crops.items());
        list_with_probabilities = [];
        for crop in list_crops:
            for i in range(int((50 - crop[1]) ** 1.5)):
                list_with_probabilities.append(crop);

        to_harvest, xp_per_harvest = random.choice(list_with_probabilities);

        amt_to_harvest = random.randint(1, 100);

        if GMO_item:
            amt_to_harvest *= 2;
            if amt_to_harvest > 100:
                amt_to_harvest -= random.randint(0,100);

        current_silo[to_harvest] += amt_to_harvest;


        new_silo_item = Item("Silo", "silo", -1, **current_silo);
        activator.update_item(new_silo_item)

        res = f"Wohoo! You harvested {amt_to_harvest} {to_harvest}"
        target = await context.send(res);

        random_key = random.choice(list(crop_emojis.keys()))
        random_value = crop_emojis[random_key];
        await target.add_reaction(random_value);
        if to_harvest == random_key:
            def key(ctx):
                if not ctx.message.id == target.id:
                    return False;
                if not ctx.emoji.name == random_value:
                    return False;
                return True;
            ResponseRequest(harvest, "crop", "REACTION", context, Context(target), key);
        await harvest_xp(context);
    else:
        await context.send("It's a perfect match! Enjoy 1000xp as your reward.");
        await inc_xp(activator, 1000, context);


async def wordle_easy(activator: Neighbor, context: Context, response: ResponsePackage = None):
    
    with open("words.txt", "r") as fWords:
        words = [line.strip() for line in fWords.readlines()]
    with open("answers.txt", "r") as fAnswers:
        answers = [line.strip() for line in fAnswers.readlines()]
    answers = answers[0:1499]

    if response is None:
        daily_limit_hit = False;
    
        # ── DAILY WORDLE XP RESET & CHECK ──────────────────────────────────────────────
        daily_limit = Neighbor.get_XP_for_level(3)
        today_str   = datetime.date.today().isoformat()
        cap_item = activator.get_item_of_name("Wordle Daily XP")
        if cap_item:
            # if the stored date isn't today, reset
            if cap_item.get_value("date") != today_str:
                cap_item.update_value("date", today_str)
                cap_item.update_value("xp",   0)
                activator.update_item(cap_item)
            xp_today = int(cap_item.get_value("xp"))
        else:
            # first play today: create tracking item
            cap_item = Item("Wordle Daily XP", "xp_daily", -1,
                        date=today_str, xp=0, hidden="true")
            activator.bestow_item(cap_item)
            xp_today = 0

        # if they've already hit the cap, bail out
        if xp_today >= daily_limit:
            daily_limit_hit = True;
        # ───────────────────────────────────────────────────────────────────────────────
        
        res = "**Welcome to Greg's ";
        res += green_wordle_emojis[22] + yellow_wordle_emojis[14] + green_wordle_emojis[17] + green_wordle_emojis[3] + red_wordle_emojis[11] + green_wordle_emojis[4];
        res += "!**\n\nI have already selected a word! Guess valid 5-letter words in this channel and I will give clues toward the answer. If you write a message that is not a valid 5 letter word in my dictionary, I will just ignore it. You have two minutes to make each guess.\n\n**Scoring:** Tom will also play alongside you and I will reveal his guesses once you have successfully guessed the word. You will get XP based on how many guesses it takes you to get the word. If you get the word in fewer guesses than Tom, you will get double XP! Let's begin, guess your first word!\n\n**Note:** Different forms of words are fair game. For example, plural words may be chosen as the Wordle and may be guessed.";
        target = await context.send(res, reply = True);
        response_context = Context(message = target)
        answer = random.choice(answers);
        # await context.send(answer);
        def key(context):
            print("key activated")
            print(context.content.lower())
            print(answer);
            if not context.content.lower() in words:
                print("returning false")
                return False;
            print("returning true")
            return True;
        ResponseRequest(wordle_easy, "guess", "MESSAGE", context, response_context, answer = answer, key = key, guesses = [], daily_limit_hit = daily_limit_hit)
        
    else:
        print("here! wordle")
        guess_list = response.values["guesses"];
        answer = response.values["answer"];
        dlh = response.values["daily_limit_hit"]
        candidate = response.content.lower();
        guess_list.append(candidate);
        response = wordle_helper.get_response(answer, candidate);
        if len(guess_list) == 1:
            await context.send("Red: This letter is not in the word.\nYellow: This letter is in the word in a different position (careful, this is slightly different from NYT Wordle mechanics)\nGreen: This letter is in the word in this position\nPurple: Easy Mode Only, This letter is in the word in this position AND another position")
        if not "0" in response and not "1" in response:
            # correct!
            res = "**You got it!!**\n\n";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "3":
                        res += purple_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);

            res = "**Let's see how Tom did!**\n\n";
            word_info = wordle_helper.WordInfo();
            tom_guesses = [];
            while not word_info.is_word_complete():
                possible = word_info.cleanse(words);
                if len(possible) == 0 or len(tom_guesses) > 15:
                    await context.send("Uh oh! Something has gone wrong on my end.");
                    return
                sorted = wordle_helper.sort_by_letter_frequency(possible);
                difficulty = int(len(possible) / 2);
                if difficulty == 0:
                    difficulty += 1;
                if len(sorted) > difficulty:
                    next_guess = random.choice(sorted[:difficulty]);
                else:
                    next_guess = random.choice(sorted);
                tom_guesses.append(next_guess);
                response = wordle_helper.get_response(answer, next_guess);
                word_info.register_guess(next_guess, response)
                for i, char in enumerate(next_guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "3":
                        res += purple_wordle_emojis[ord(char) - 97];
                res += "\n";
            await context.send(res);
            num_guesses = len(guess_list);
            num_tom_guesses = len(tom_guesses);
            try:
                if num_guesses < 9:
                    xp = 25 * (9 - len(guess_list));
                    if len(guess_list) < len(tom_guesses):
                        await context.send(f"Wow! You beat tom by {len(tom_guesses) - len(guess_list)} guesses!\n\nYou get {xp}xp for getting the word in {len(guess_list)}, doubled for beating Tom! {xp * 2}xp total!");
                        xp *= 2;
                    else:
                        await context.send(f"Unfortunately you did not beat tom!!\n\nHowever, you get {xp}xp for getting the word in {len(guess_list)}!");
                    if dlh:
                        await context.send("You've actually hit the daily limit for earning XP with Wordle, so no XP for this round. However, you can continue to play for fun!")
                    else:
                        await inc_xp(activator, xp, context)
                        cap_item.update_value("xp", int(cap_item.get_value("xp")) + xp)
                        activator.update_item(cap_item)
                else:
                    await context.send(f"Unfortunately, {len(guess_list)} guesses is too many to earn XP! Good job getting the Wordle though, better luck next time!");
            except:
                pass
            import requests

            def get_definition(word):
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                res = requests.get(url).json()
                canonical_word = res[0]["word"]
                return canonical_word, res[0]["meanings"][0]["definitions"][0]["definition"]

            definiton = get_definition(answer)
            await context.send(f"**Definition**\n{definiton[0]}: {definiton[1]}")
        else:
            res = "";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "3":
                        res += purple_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);
            response_context = Context(message = target);
            def key(context):
                if not context.content.lower() in words:
                    return False;
                return True;
            ResponseRequest(wordle_easy, "guess", "MESSAGE", context, response_context, answer = answer, key = key, guesses = guess_list, daily_limit_hit=dlh)


async def wordle_hard(activator: Neighbor, context: Context, response: ResponsePackage = None):
        
    daily_limit_hit = False;
    
    # ── DAILY WORDLE XP RESET & CHECK ──────────────────────────────────────────────
    daily_limit = Neighbor.get_XP_for_level(6)
    today_str   = datetime.date.today().isoformat()
    cap_item = activator.get_item_of_name("Wordle Daily XP")
    if cap_item:
        # if the stored date isn't today, reset
        if cap_item.get_value("date") != today_str:
            cap_item.update_value("date", today_str)
            cap_item.update_value("xp",   0)
            activator.update_item(cap_item)
        xp_today = int(cap_item.get_value("xp"))
    else:
        # first play today: create tracking item
        cap_item = Item("Wordle Daily XP", "xp_daily", -1,
                    date=today_str, xp=0, hidden="true")
        activator.bestow_item(cap_item)
        xp_today = 0

    # if they've already hit the cap, bail out
    if xp_today >= daily_limit:
        daily_limit_hit = True;
    # ───────────────────────────────────────────────────────────────────────────────
    
    with open("words.txt", "r") as fWords:
        words = [line.strip() for line in fWords.readlines()]
    with open("answers.txt", "r") as fAnswers:
        answers = [line.strip() for line in fAnswers.readlines()]
    answers = answers[0:3499]

    if response is None:
        res = "**Welcome to Greg's ";
        res += green_wordle_emojis[22] + yellow_wordle_emojis[14] + green_wordle_emojis[17] + green_wordle_emojis[3] + red_wordle_emojis[11] + green_wordle_emojis[4];
        res += " HARD MODE!**\n\nYou know the drill! Hard mode wordle works the same as regular mode with a few changes. Firstly, there are 1500 more possible Wordles. Secondly, you play against Rose instead of Tom, who is better at guessing. Thirdly, more XP is available to be won but you must get the word in 6 guesses or less instead of 8 to earn any. Finally, no purple letters will be shown.\n\n**Scoring:** Rose will also play alongside you and I will reveal her guesses once you have successfully guessed the word. You will get XP based on how many guesses it takes you to get the word. If you get the word in fewer guesses than Rose, you will get double XP! Let's begin, guess your first word!\n\n**Note:** Different forms of words are fair game. For example, plural words may be chosen as the Wordle and may be guessed.";
        target = await context.send(res, reply = True);
        response_context = Context(message = target)
        answer = random.choice(answers);
        # answer = "dived"
        # await context.send(answer);
        def key(context):
            if not context.content.lower() in words:
                return False;
            return True;
        ResponseRequest(wordle_hard, "guess", "MESSAGE", context, response_context, answer = answer, key = key, guesses = [], daily_limit_hit=daily_limit_hit)
    else:
        guess_list = response.values["guesses"];
        answer = response.values["answer"];
        dlh = response.values["daily_limit_hit"]
        candidate = response.content.lower();
        guess_list.append(candidate);
        response = wordle_helper.get_response(answer, candidate);
        if len(guess_list) == 1:
            await context.send("Red: This letter is not in the word.\nYellow: This letter is in the word in a different position (careful, this is slightly different from NYT Wordle mechanics)\nGreen: This letter is in the word in this position\n~~Purple: Easy Mode Only, This letter is in the word in this position AND another position~~")
        if not "0" in response and not "1" in response:
            # correct!
            res = "**You got it!!**\n\n";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2" or response[i] == "3":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);

            res = "**Let's see how Rose did!**\n\n";
            word_info = wordle_helper.WordInfo();
            tom_guesses = [];
            choices = [i + 1 for i in range(5)];
            difficulty = random.choice(choices)
            while not word_info.is_word_complete():
                possible = word_info.cleanse(words);
                if len(possible) == 0 or len(tom_guesses) > 15:
                    await context.send("Uh oh! Something has gone wrong on my end.");
                    return
                sorted = wordle_helper.sort_by_letter_frequency(possible);
                if len(sorted) > difficulty:
                    next_guess = random.choice(sorted[:difficulty]);
                else:
                    next_guess = random.choice(sorted);
                tom_guesses.append(next_guess);
                response = wordle_helper.get_response(answer, next_guess);
                word_info.register_guess(next_guess, response)
                for i, char in enumerate(next_guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2" or response[i] == "3":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            await context.send(res);
            num_guesses = len(guess_list);
            num_tom_guesses = len(tom_guesses);
            try:
                if num_guesses < 7:
                    xp = 85 * (7 - len(guess_list));
                    if len(guess_list) < len(tom_guesses):
                        await context.send(f"Wow! You beat Rose by {len(tom_guesses) - len(guess_list)} guesses!\n\nYou get {xp}xp for getting the word in {len(guess_list)}, doubled for beating Rose! {xp * 2}xp total!");
                        xp *= 2;
                    else:
                        await context.send(f"Unfortunately you did not beat Rose!!\n\nHowever, you get {xp}xp for getting the word in {len(guess_list)}!");
                    if dlh:
                        await context.send("You've actually hit the daily limit for earning XP with Wordle, so no XP for this round. However, you can continue to play for fun!")
                    else:
                        await inc_xp(activator, xp, context)
                        cap_item.update_value("xp", int(cap_item.get_value("xp")) + xp)
                        activator.update_item(cap_item)
                else:
                    await context.send(f"Unfortunately, {len(guess_list)} guesses is too many to earn XP! Good job getting the Wordle though, better luck next time!");
            except:
                pass
            import requests

            def get_definition(word):
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                res = requests.get(url).json()
                canonical_word = res[0]["word"]
                return canonical_word, res[0]["meanings"][0]["definitions"][0]["definition"]

            definiton = get_definition(answer)
            await context.send(f"**Definition**\n{definiton[0]}: {definiton[1]}")
        else:
            res = "";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2" or response[i] == "3":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);
            response_context = Context(message = target);
            def key(context):
                if not context.content.lower() in words:
                    return False;
                return True;
            ResponseRequest(wordle_hard, "guess", "MESSAGE", context, response_context, key = key, answer = answer, guesses = guess_list, daily_limit_hit=dlh)

@command_handler.Command(AccessType.PRIVATE, desc = "Play Wordle!", generic=True)
async def wordle(activator: Neighbor, context: Context, answer = None, guesses = None):

    with open("words.txt", "r") as fWords:
        words = [line.strip() for line in fWords.readlines()]

    with open("answers.txt", "r") as fWords:
        answers = [line.strip() for line in fWords.readlines()]
    answers = answers[0:99]

    if guesses is None:
        if not activator.get_item_of_name("Greg Wordle Minigame") and not activator.get_item_of_name("Wordle 2 (Hard Mode)") and not activator.ID == 355169964027805698:
            await context.send("Whoops! Looks like you haven't purchased the Wordle minigame from my rss yet!\n\nPlay with someone else or buy it for yourself by calling $rss. #sorrynotsorry");
            return;
        if activator.get_item_of_name("Wordle 2 (Hard Mode)"):
            await wordle_hard(activator, context);
            return;
        else:
            await wordle_easy(activator, context);
            return;
        res = "**Welcome to Greg's ";
        res += green_wordle_emojis[22] + yellow_wordle_emojis[14] + green_wordle_emojis[17] + green_wordle_emojis[3] + red_wordle_emojis[11] + green_wordle_emojis[4];
        res += "!**\n\nI have already selected a word! Guess valid 5-letter words in this channel and I will give clues toward the answer. If you write a message that is not a valid 5 letter word in my dictionary, I will just ignore it. You have two minutes to make each guess.\n\n**Scoring:** Tom will also play alongside you and I will reveal his guesses once you have successfully guessed the word. You will get XP based on how many guesses it takes you to get the word. If you get the word in fewer guesses than Tom, you will get double XP! Let's begin, guess your first word!\n\n**Note:** Different forms of words are fair game. For example, plural words may be chosen as the Wordle and may be guessed.";
        target = await context.send(res, reply = True);
        response_context = Context(message = target)
        answer = random.choice(answers);
        # answer = "dived"
        # await context.send(answer);
        active_expectations.append(Expectation("wordle", "MESSAGE", int(time.time() + 300), wordle, fulfills="guesses",activation_context=context,response_context=response_context, answer = answer, guesses = []));
    else:
        candidate = guesses[0].lower();
        if not candidate in words:
            return
        answer = guesses[1].values["answer"];
        guess_list = guesses[1].values["guesses"];
        guesses[1].meet()
        guess_list.append(candidate);
        response = wordle_helper.get_response(answer, candidate);
        if response == "22222":
            # correct!
            res = "**You got it!!**\n\n";
            for guess in guess_list:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);

            res = "**Let's see how Tom did!**\n\n";
            word_info = wordle_helper.WordInfo();
            tom_guesses = [];
            choices = [i + 1 for i in range(20)];
            difficulty = random.choice(choices)
            while not word_info.is_word_complete():
                possible = word_info.cleanse(words);
                if len(possible) == 0 or len(tom_guesses) > 15:
                    await context.send("Uh oh! Something has gone wrong on my end.");
                    return
                sorted = wordle_helper.sort_by_letter_frequency(possible);
                if len(sorted) > difficulty:
                    next_guess = random.choice(sorted[:difficulty]);
                else:
                    next_guess = random.choice(sorted);
                tom_guesses.append(next_guess);
                response = wordle_helper.get_response(answer, next_guess);
                word_info.register_guess(next_guess, response)
                for i, char in enumerate(next_guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            await context.send(res);
            if len(guess_list) < 8:
                xp = 50 * (7 - len(guess_list));
                if len(guess_list) < len(tom_guesses):
                    await context.send(f"Wow! You beat tom by {len(tom_guesses) - len(guess_list)} guesses!\n\nYou get {xp}xp for getting the word in {len(guess_list)}, doubled for beating Tom! {xp * 2}xp total!");
                    xp *= 2;
                else:
                    await context.send(f"Unfortunately you did not beat tom!!\n\nHowever, you get {xp}xp for getting the word in {len(guess_list)}!");
                await inc_xp(activator, xp, context);
            else:
                await context.send(f"Unfortunately, {len(guess_list)} guesses is too many to earn XP! Good job getting the Wordle though, better luck next time!");
        else:
            res = "";
            for guess in guess_list:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);
            response_context = Context(message = target);
            active_expectations.append(Expectation("wordle", "MESSAGE", int(time.time() + 300), wordle, fulfills="guesses",activation_context=context,response_context=response_context, answer = answer, guesses = guess_list))

@command_handler.Command(AccessType.DEVELOPER, desc = "This is a test of sync")
async def run(activator: Neighbor, context: Context):
    await context.send("Works!", reply = True);

@command_handler.Command(AccessType.PRIVATE, desc = "Play hangman!", generic=True)
async def hangman(activator: Neighbor, context: Context, response: ResponsePackage = None):
    with open("hangman.txt", "r") as fAnswers:
        answers = [line.strip() for line in fAnswers.readlines()]

    def remove_superfluous_characters(s):
        res = "";
        for c in s:
            if c in "abcdefghijklmnopqrstuvwxyz ":
                res += c;
        return res;

    if response is None:
        res = "**Welcome to Greg's Hangman!**\n\nGuess singular letters or words until you can confidently guess the phrase.\n\nYou can make 10 mistakes. Letters cost 1 mistake each, words 3. I have already chosen a phrase, you may begin guessing. Good luck!";
        answer = random.choice(answers).lower();
        target = await context.send(res);
        so_far = "";
        for ch in answer:
            if ch in "abcdefghijklmnopqrstuvwxyz":
                so_far += "_"
            else:
                so_far += ch;
        await context.send(f"`{so_far}`");
        real = remove_superfluous_characters(answer)
        words = real.split(" ");
        lengths = [len(word) for word in words];
        lengths.append(1);
        print(answer);
        def key(c):
            return len(c.content) == 1 or len(c.content) == len(answer) or len(c.content) in [len(x) for x in words];
        ResponseRequest(hangman, "guess", "MESSAGE", context, Context(target), key, guessed = [], answer = answer, so_far = so_far, wrong  = 0);
    else:
        guessed = response.values["guessed"];
        answer = response.values["answer"];
        so_far = response.values["so_far"];
        wrong = response.values["wrong"];

        correct_letters = [c.lower() for c in answer if c.lower() in "abcdefghiklmnopqrstuvwxyz"];
        correct_words = [word for word in answer.split(" ")] + [word for word in remove_superfluous_characters(answer).split(" ")];

        guess = response.content.lower();

        if guess in correct_letters:
            await context.send("Correct!");
        if guess in correct_words:
            await context.send("Correct!");
        if guess == answer or remove_superfluous_characters(guess) == remove_superfluous_characters(answer):
            await context.send("Correct!");

        guessed.append(guess);
        if wrong >= 10:
            await context.send("Sorry, no more guesses!");
            await context.send(answer);
            return;

        real = remove_superfluous_characters(answer)
        words = real.split(" ");
        lengths = [len(word) for word in words];
        lengths.append(1);
        print(answer);
        def key(c):
            return len(c.content) == 1 or len(c.content) == len(answer) or len(c.content) in [len(x) for x in words];

        ResponseRequest(hangman, "guess", "MESSAGE", context, Context(target), key, guessed = guessed, answer = answer, so_far = new, wrong = wrong);


@command_handler.Command(AccessType.PRIVATE, desc = "Displays all crops a Neighbor has in their silo.", generic = True)
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

@command_handler.Command(AccessType.PRIVATE, desc = "Sell your entire silo!", generic = True)
async def sell(activator: Neighbor, context: Context, response: ResponsePackage = None):
    silo_item = activator.get_item_of_name("Silo");
    if not silo_item:
        await context.send("You don't have a silo silly!");
        return;

    if response is None:
        rates = [0.63467546, 0.872456, 0.900124323, 0.9578765, 0.52332, 0.5111, 1.1344, 0.6333, 0.7555, 0.768794, 0.60987, 0.79023938, 0.510203, 0.9203904957, 0.77473, 0.891920, 0.5, 0.6230, 0.920, 1.10029, 0.7002235, 0.601234, 0.50123, 1.034, 0.91340, 0.65431, 0.6230, 0.71029, 0.9192, 0.712, 0.99999999999]
        rate = rates[datetime.datetime.now().day];
        current_silo = silo_item.values.items();
        total_value = 0;
        for crop, amt in current_silo:
            total_value += int(amt) * crops[crop]

        offer = int(rate * total_value);
        offer = int(.6666667 * offer);

        target = await context.send(f"Today, I would be willing to purchase your entire silo for {offer}xp. If you like this offer, react to accept. If you don't like this offer, check back another day!");

        def key(context):
            if not context.message.id == target.id:
                return False;
            if not context.user.id == activator.ID:
                return False;
            if not context.emoji.name == unicodes["check"]:
                return False;
            return True;
        ResponseRequest(sell, "confirmation", "REACTION", context, Context(target), key, offer = offer);

        await target.add_reaction(unicodes['check']);
    else:
        offer = response.values["offer"];
        await inc_xp(activator, offer, context);
        await context.send(f"It's done! Your silo is now empty and I have given you {offer}xp in exchange.");
        activator.vacate_item(silo_item);


import json
import os
import re
# from datetime import datetime, timedelta, timezone

GIVEAWAYS_JSON_PATH = "giveaways.json"


def _round_dt_to_nearest_hour(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("dt must be timezone-aware")
    discard = datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    dt_floor = dt - discard
    if dt.minute >= 30:
        dt_floor += datetime.timedelta(hours=1)
    return dt_floor


def _load_giveaways_json(path: str) -> dict:
    if not os.path.exists(path):
        return {"giveaways": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "giveaways" not in data or not isinstance(data["giveaways"], list):
            return {"giveaways": []}
        return data
    except Exception:
        return {"giveaways": []}


def _save_giveaways_json(path: str, data: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


@command_handler.Command(
    AccessType.PRIVATE,
    desc="Automatically host a giveaway.\n"
         "Examples:\n"
         "  `$give 89 BEMs`\n"
         "  `$give 89 BEMs -3w` (3 winners)\n"
         "  `$give 89 BEMs -12h` (12 hours, 1–36)\n"
         "  `$give 89 BEMs -784803565151453214c` (council only: post in channel id)"
)
async def give(activator: Neighbor, context: Context):
    if len(context.args) < 1:
        raise CommandArgsError("`$give` needs to know what you want to give away! Try $help give")

    raw = context.content

    # --- Council membership check (assumed correct per your note) ---
    council_role = context.guild.get_role(648188387836166168)
    is_council = has_role(context.author, council_role)

    # --- Parse flags ---
    winners = 1
    hours = 24

    w_match = re.search(r'-(\d+)w\b', raw)
    if w_match:
        winners = max(1, int(w_match.group(1)))

    h_match = re.search(r'-(\d+)h\b', raw)
    if h_match:
        hours = int(h_match.group(1))
        if hours < 0:
            hours = 0
        elif hours > 36:
            hours = 36

    # Optional channel override for council: -<#id>c
    channel_override_id: int | None = None
    c_match = re.search(r'-(\d+)c\b', raw)
    if c_match and is_council:
        channel_override_id = int(c_match.group(1))

    # Clean message text shown to users by stripping flags
    cleaned = re.sub(r'\s*-\d+[whc]\b', '', raw).strip()
    cleaned = cleaned.split(" ", 1)[1]

    # --- Build message ---
    res = "__**New Giveaway**__\n"
    res += f"> **{cleaned}**"
    res += f"\n> Hosted generously by <@{activator.ID}>"
    if winners > 1:
        res += f"\n> Winners: {winners}"
    res += f"\n<@&827634110238556160> this giveaway ends in {hours}H!"
    res += "\nReact with <:giveaway:1067499350705582124> to enter!"

    # --- Choose channel ---
    post_channel_id = context.ID_bundle.giveaway_channel
    if channel_override_id is not None:
        post_channel_id = channel_override_id

    gc = await context.guild.fetch_channel(post_channel_id)
    target = await gc.send(res)
    await target.add_reaction("<:giveaway:1067499350705582124>")

    # --- Compute end time in UTC (rounded to nearest hour) ---
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    end_dt_rounded = _round_dt_to_nearest_hour(now_utc + datetime.timedelta(hours=hours))

    # --- Persist to JSON (save BOTH message_id and channel_id) ---
    data = _load_giveaways_json(GIVEAWAYS_JSON_PATH)
    data["giveaways"].append({
        "message_id": str(target.id),
        "channel_id": str(gc.id),            # <- actual posting channel
        "guild_id": str(context.guild.id),
        "host_id": str(activator.ID),
        "winners": int(winners),
        "duration_hours": int(hours),
        "created_utc": now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "end_utc": end_dt_rounded.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "end_epoch": int(end_dt_rounded.timestamp()),
        "prize_text": cleaned,
        "used_channel_override": bool(channel_override_id is not None),
    })
    _save_giveaways_json(GIVEAWAYS_JSON_PATH, data)
    
import random
import json
import os
import re
import datetime

GIVEAWAYS_JSON_PATH = "giveaways.json"
CLOSED_GIVEAWAYS_JSON_PATH = "closed_giveaways.json"

GIVEAWAY_EMOJI = "<:giveaway:1067499350705582124>"
REROLL_EMOJI = "<:reroll:1060038218113888266>"


def _round_dt_to_nearest_hour(dt: datetime.datetime) -> datetime.datetime:
    if dt.tzinfo is None:
        raise ValueError("dt must be timezone-aware")
    discard = datetime.timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    dt_floor = dt - discard
    if dt.minute >= 30:
        dt_floor += datetime.timedelta(hours=1)
    return dt_floor


def _load_giveaways_json(path: str) -> dict:
    if not os.path.exists(path):
        return {"giveaways": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "giveaways" not in data or not isinstance(data["giveaways"], list):
            return {"giveaways": []}
        return data
    except Exception:
        return {"giveaways": []}


def _save_giveaways_json(path: str, data: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


import random
import datetime

GIVEAWAYS_JSON_PATH = "giveaways.json"
CLOSED_GIVEAWAYS_JSON_PATH = "closed_giveaways.json"

GIVEAWAY_EMOJI = "<:giveaway:1067499350705582124>"
REROLL_EMOJI = "<:reroll:1060038218113888266>"


@command_handler.Loop(
    minutes=5,
    desc="Check to see if any giveaway from json has past its end time but hasn't been closed yet."
)
async def close_giveaways(client):
    """
    1) Close any giveaways that need to be closed
    2) Pick random winner(s) from those who reacted with GIVEAWAY_EMOJI
    3) Announce winners in the giveaway channel (with reroll reaction)
    4) Edit the ORIGINAL giveaway message to show it is closed + display winner(s)
    5) Move closed giveaway to CLOSED_GIVEAWAYS_JSON_PATH with winner_announce_message_id
    """
    now_epoch = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    open_data = _load_giveaways_json(GIVEAWAYS_JSON_PATH)
    closed_data = _load_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH)

    open_giveaways = open_data.get("giveaways", [])
    if not open_giveaways:
        return

    still_open = []
    newly_closed = []

    for g in open_giveaways:
        # Skip if not ready
        try:
            end_epoch = int(g.get("end_epoch", 0))
        except Exception:
            end_epoch = 0

        if end_epoch > now_epoch:
            still_open.append(g)
            continue

        # Parse required fields
        try:
            guild_id = int(g["guild_id"])
            channel_id = int(g["channel_id"])
            message_id = int(g["message_id"])
            host_id = int(g.get("host_id", 0))
            winners_needed = max(1, int(g.get("winners", 1)))
        except Exception:
            still_open.append(g)
            continue

        # Get guild (cache miss fallback)
        guild = client.get_guild(guild_id)
        if guild is None:
            try:
                guild = await client.fetch_guild(guild_id)
            except Exception:
                still_open.append(g)
                continue

        # Fetch channel + original giveaway message
        try:
            channel = await guild.fetch_channel(channel_id)
            giveaway_message = await channel.fetch_message(message_id)
        except Exception:
            still_open.append(g)
            continue

        # If it already looks closed, don't double-close (extra guard)
        try:
            if giveaway_message.content and "__**CLOSED**__" in giveaway_message.content:
                # Treat it as already closed; move it out of open JSON to prevent repeats.
                # (If you *don't* want this, delete this block.)
                closed_entry = dict(g)
                closed_entry["closed_utc"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                closed_entry.setdefault("winner_ids", [])
                closed_entry.setdefault("winner_announce_message_id", None)
                newly_closed.append(closed_entry)
                continue
        except Exception:
            pass

        # Entrants from reaction
        try:
            entrants = await get_users_who_reacted(giveaway_message, GIVEAWAY_EMOJI)
        except Exception:
            entrants = []

        entrant_ids = []
        seen = set()
        for u in entrants:
            try:
                if getattr(u, "bot", False):
                    continue
                uid = int(u.id)
                if uid in seen:
                    continue
                seen.add(uid)
                entrant_ids.append(uid)
            except Exception:
                continue

        # Pick winner(s)
        winner_ids = []
        if entrant_ids:
            k = min(winners_needed, len(entrant_ids))
            winner_ids = random.sample(entrant_ids, k)

        # Winner text for both announcement + original edit
        if not winner_ids:
            winners_line = "Winners: *(none — no valid entrants)*"
            announce_text = (
                "**Giveaway ended!**\n"
                "No valid entrants were found for this giveaway. 😭"
            )
        else:
            winners_ping = ", ".join(f"<@{wid}>" for wid in winner_ids)
            winners_line = f"Winners: {winners_ping}"
            announce_text = (
                "**Giveaway ended!**\n"
                f"Congrats {winners_ping}! 🎉\n"
                f"Message <@{host_id}> to claim your prize.\n\n"
                f"React with {REROLL_EMOJI} to reroll this giveaway."
            )

        # Announce and add reroll reaction
        try:
            announce_msg = await channel.send(announce_text)
            await announce_msg.add_reaction(REROLL_EMOJI)
        except Exception:
            still_open.append(g)
            continue

        # Edit ORIGINAL giveaway message to mark closed + show winners
        try:
            original_content = giveaway_message.content or ""
            closed_stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            edited_content = (
                f"{original_content}\n\n"
                f"__**CLOSED**__ ({closed_stamp})\n"
                f"> {winners_line}\n"
                f"> Announcement: {announce_msg.jump_url}"
            )
            await giveaway_message.edit(content=edited_content)
        except Exception:
            # Even if edit fails, we still consider it closed (you already announced)
            pass

        # Move to closed JSON
        closed_entry = dict(g)
        closed_entry["closed_utc"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        closed_entry["winner_ids"] = [str(w) for w in winner_ids]
        closed_entry["winner_announce_message_id"] = str(announce_msg.id)

        newly_closed.append(closed_entry)

    # Persist
    if newly_closed:
        open_data["giveaways"] = still_open
        closed_data.setdefault("giveaways", [])
        closed_data["giveaways"].extend(newly_closed)

        _save_giveaways_json(GIVEAWAYS_JSON_PATH, open_data)
        _save_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH, closed_data)

import random
import datetime

CLOSED_GIVEAWAYS_JSON_PATH = "closed_giveaways.json"
GIVEAWAY_EMOJI = "<:giveaway:1067499350705582124>"
REROLL_EMOJI = "<:reroll:1060038218113888266>"


@command_handler.Uncontested(type="REACTION")
async def reroll_giveaway(context: Context):
    emoji = str(context.emoji)
    if emoji != REROLL_EMOJI:
        print(emoji)
        return

    # We only reroll when reacting to the *announcement* message
    reacted_message_id = str(context.message.id)

    closed_data = _load_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH)
    closed_list = closed_data.get("giveaways", [])

    giveaway = None
    for g in closed_list:
        if str(g.get("winner_announce_message_id")) == reacted_message_id:
            giveaway = g
            break

    if giveaway is None:
        return

    # Permission: council OR original host
    council_role = context.guild.get_role(648188387836166168)
    is_council = has_role(context.author, council_role)

    try:
        is_host = int(giveaway.get("host_id", 0)) == int(context.author.id)
    except Exception:
        is_host = False

    if not (is_council or is_host):
        return

    # Fetch original giveaway message to determine entrants
    try:
        channel_id = int(giveaway["channel_id"])
        message_id = int(giveaway["message_id"])
        channel = await context.guild.fetch_channel(channel_id)
        giveaway_message = await channel.fetch_message(message_id)
    except Exception:
        return

    # Entrants are anyone who reacted with the giveaway emoji
    try:
        entrants = await get_users_who_reacted(giveaway_message, GIVEAWAY_EMOJI)
    except Exception:
        entrants = []

    entrant_ids = []
    seen = set()
    for u in entrants:
        try:
            if getattr(u, "bot", False):
                continue
            uid = int(u.id)
            if uid in seen:
                continue
            seen.add(uid)
            entrant_ids.append(uid)
        except Exception:
            continue

    if not entrant_ids:
        msg = await channel.send("**Reroll failed:** No valid entrants were found for this giveaway. 😭")
        await msg.add_reaction(REROLL_EMOJI)
        return

    # Don’t pick someone who already won previously if possible
    prior_winners = set()
    try:
        prior_winners.update(int(x) for x in giveaway.get("winner_ids", []) if str(x).isdigit())
    except Exception:
        pass

    eligible = [uid for uid in entrant_ids if uid not in prior_winners]
    if not eligible:
        eligible = entrant_ids  # everyone already won; allow repeats

    # Number of winners for reroll: same as original winners
    winners_needed = max(1, int(giveaway.get("winners", 1)))
    k = min(winners_needed, len(eligible))
    new_winner_ids = random.sample(eligible, k)

    winners_ping = ", ".join(f"<@{wid}>" for wid in new_winner_ids)
    host_id = int(giveaway.get("host_id", 0))

    reroll_text = (
        "**Giveaway rerolled!**\n"
        f"New winner(s): {winners_ping} 🎉\n"
        f"Message <@{host_id}> to claim your prize.\n\n"
        f"React with {REROLL_EMOJI} to reroll this giveaway again."
    )

    new_announce = await channel.send(reroll_text)
    await new_announce.add_reaction(REROLL_EMOJI)

    # Update closed_giveaways:
    # - store latest announce message id so future rerolls work
    # - append new winners to winner_ids (audit trail + helps avoid repeats)
    giveaway["winner_announce_message_id"] = str(new_announce.id)
    existing = [str(x) for x in giveaway.get("winner_ids", [])]
    for wid in new_winner_ids:
        existing.append(str(wid))
    giveaway["winner_ids"] = existing
    giveaway["last_reroll_utc"] = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    _save_giveaways_json(CLOSED_GIVEAWAYS_JSON_PATH, closed_data)
        

@command_handler.Command(AccessType.PRIVATE, desc = "Open your bank profile, if you have a GregBanking(TM) savings account. Use `$info bank` to learn more.")
async def bank(activator: Neighbor, context: Context):
    bank_item = activator.get_item_of_name("GregBanking(TM)");
    if bank_item is None:
        await context.send("I'm sorry! You do not yet have a savings account open at GregBanking(TM). Please open an account using `$rss`.", reply = True);
    else:
        opened = int(bank_item.get_value("opened"));
        interest = int(bank_item.get_value("interest"));
        XP = int(bank_item.get_value("xp"));
        user = await context.guild.fetch_member(activator.ID);

        res = f"**{user.display_name}'s GregBanking(TM) Account**\n";
        res += f"Account open since {datetime.datetime.fromtimestamp(opened)}\n\n";
        res += f"Balance: {XP}xp\n";
        res += f"Interest rate: 5%\n";
        res += f"Interest accumulated so far: {interest}xp\n\n";
        res += f"Use `$deposit` to make a deposit\n";
        res += f"Use `$close_account` to close your account and withdraw the full balance.";

        target = await context.send(res);

@command_handler.Command(AccessType.PRIVATE, desc = "Deposit levels into your GregBanking(TM) savings account. Use `$info bank` to learn more.")
async def deposit(activator: Neighbor, context: Context):
    bank_item = activator.get_item_of_name("GregBanking(TM)");
    if bank_item is None:
        await context.send("I'm sorry! You do not yet have a savings account open at GregBanking(TM). Please open an account using `$rss`.", reply = True);
    else:
        if len(context.args) < 1:
            raise CommandArgsError("`$deposit` expects one argument: amount of xp to deposit");
        amount_to_deposit = int(context.args[0]);
        if amount_to_deposit < 1001:
            await context.send("Whoops! You can't deposit that few XP.");
        elif amount_to_deposit > activator.get_XP():
            await context.send("Whoops! You're too poor to deposit that much XP.");
        else:
            new_bank_item = bank_item;
            new_bank_item.update_value("xp", str(int(bank_item.get_value("xp")) + int(amount_to_deposit) - 1000));
            activator.update_item(new_bank_item);
            strip(activator, xp = amount_to_deposit);
            await context.send(f"Done! {amount_to_deposit - 1000}xp was deposited into your account after fees were applied.")

# @command_handler.Command(AccessType.PRIVATE, desc = "Withdraw levels from your GregBanking(TM) savings account. Use `$info bank` to learn more.")
async def withdraw(activator: Neighbor, context: Context):
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
async def close_account(activator: Neighbor, context: Context):
    bank_item = activator.get_item_of_name("GregBanking(TM)");
    if bank_item is None:
        await context.send("I'm sorry! You do not yet have a savings account open at GregBanking(TM). Please open an account using `$rss`.", reply = True);
    else:
        XP = int(bank_item.get_value("xp"));
        activator.vacate_item(bank_item);
        await inc_xp(activator, int(XP * 0.75), context)
        await context.send(f"Done! {XP}xp has been withdrawn from your account. After taxes, {int(XP * 0.75)}xp was applied to your profile.");
        await context.send("Your GregBanking(TM) Savings Account has been successfully closed");

@command_handler.Command(AccessType.PUBLIC, desc = "Find a segment of the Constitution!")
async def constitution(activator: Neighbor, context: Context):
    
    final_answer_msg = await context.send("Reading the constitution...")
    
    import json
    import numpy as np

    from helper_embedding import embed

    query = context.args[0];
    with open("constitution_enc.json", "r") as f:
        clauses = json.load(f)
    
    if query == "section":
        clause_texts = [f"**Section {c['section_encoding']}**```{c['text']}```" for c in clauses if c['section_encoding'].startswith(context.args[1])]

        for clause in clause_texts:
            await context.send(clause)
    else:
        query_embedding = embed(query)

        print("Embedding shape:", query_embedding.shape)
        print("First 5 dims:", np.round(query_embedding[:5], 4))
            
        clause_embeddings = [c['embedding'] for c in clauses];
        clause_texts = [f"**Section {c['section_encoding']}**```{c['text']}```" for c in clauses]

        from numpy import dot
        from numpy.linalg import norm

        def cosine_similarity(a, b):
            return dot(a, b) / (norm(a) * norm(b))

        # Compute similarity between query and each clause
        scores = [cosine_similarity(query_embedding, emb) for emb in clause_embeddings]

        # Rank and return
        ranked = sorted(zip(clause_texts, scores), key=lambda x: x[1], reverse=True)
        
        await final_answer_msg.edit(content=f"I think these are the most helpful pieces of the Constitution for \"{context.args[0]}\"")
        for clause, score in ranked[0:5]:
            print(f"{score:.3f} - {clause}")
            await context.send(clause)
    
@command_handler.Command(AccessType.PRIVATE, desc = "Steal from another user, if you have Hire Alfred from the rss.")
async def steal(activator: Neighbor, context: Context):
    if not activator.get_item_of_name("Hire Alfred"):
        context.send("Whoops! You need to purchase Alfred's loyalty from my RSS. Use `$rss` to purchase.")
    else:
        if len(context.args) < 1:
            raise CommandArgsError("`$steal` expects one argument: @mention of user to steal from.");
        else:
            id = context.args[0][2:-1];
            try:
                member = await context.guild.fetch_member(id);
            except:
                raise CommandArgsError("`$steal` expects one argument: @mention of user to steal from.")
            neighbor = Neighbor(id, context.guild.id);

            possibilities = [-.1, -0.09, -0.08, -0.07, -0.06, -0.05, -0.04, -0.03, -0.02 -0.01, 0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1];
            choice = 2000 + 2000 * random.choice(possibilities);
            choice = choice if neighbor.XP >= choice else neighbor.XP;

            await inc_xp(activator, choice, context);
            neighbor.strip(xp=choice);
            await context.send(f"Alfred has stolen {choice} from <@{id}>");
            activator.vacate_item(activator.get_item_of_name("Hire Alfred"));

@command_handler.Command(AccessType.PRIVATE, desc = "Turn on or off your invisibility cloak, if you have one.")
async def cloak(activator: Neighbor, context: Context):
    cloak_item = activator.get_item_of_name("Invisibility Cloak");
    if cloak_item is None:
        await context.send("I'm sorry! You do not yet have an invisibility cloak. Use `$rss` to purchase one!", reply = True);
    else:
        if len(context.args) < 1 or not context.args[0] in ["on", "off"]:
            raise CommandArgsError("`$cloak` expects one argument: 'on' to put on cloak or 'off' to take off cloak");
        role = context.guild.get_role(FF.invisibility_role);
        user = await context.guild.fetch_member(activator.ID);
        if context.args[0] == "on":
            await user.add_roles(role)
        elif context.args[0] == "off":
            await user.remove_roles(role);

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


@command_handler.Command(AccessType.PRIVILEGED, desc = "Changes the prefix for Greg's commands.")
async def prefix(activator: Neighbor, context: Context, new = ""):
    old = command_handler.Command.prefix;
    command_handler.Command.set_prefix(new);
    # print("changin prefix");
    await context.send(f"Wow! My prefix has been changed from `{old}` to `{new}`\n*Members should now use `{new}help` instead of `{old}help` to access the help command, for example.*")

@command_handler.Command(AccessType.PRIVILEGED, desc = "Set a role to have the trophy tag.")
async def trophy(activator: Neighbor, context: Context):
    if not len(context.args) > 0:
        raise CommandArgsError("`$trophy` expects at least one argument: @mentions for the roles to give trophy tags");
    with open("trophy.txt", "w") as fTrophy:
        fTrophy.write("");
    with open("trophy.txt", "w") as fTrophy:
        for i, arg in enumerate(context.args):
            if i == 0:
                continue;
            try:
                id = parse_mention(arg);
                fTrophy.write(str(id) + "\n");
            except:
                raise CommandArgsError("`$trophy` only accepts mentions as arguments")

@command_handler.Command(AccessType.PRIVILEGED, desc = "Kicks a member quietly.")
async def remove(activator: Neighbor, context: Context, target, reason = None):
    to_kick = await context.guild.fetch_member(int(target[2:-1]));
    await to_kick.kick(reason=reason);
    pass

@command_handler.Command(AccessType.PRIVILEGED, desc = "Kicks a member with theatrics.")
async def kick(activator: Neighbor, context: Context, reason = None):
    if len(context.args) < 1:
        raise CommandArgsError("Need to @mention someone to kick");
    else:
        target = context.args[0];
    general = await context.guild.fetch_channel(FF.general_channel);
    audit = await context.guild.fetch_channel(FF.audit_channel);
    await general.send(f"{target} has been kicked! https://tenor.com/view/the-wheel-of-time-wheel-of-time-saidar-one-power-true-source-gif-26196681");
    to_kick = await context.guild.fetch_member(int(target[2:-1]));
    await to_kick.kick(reason=reason);
    await audit.send(to_kick.name + " has been kicked.")

@command_handler.Command(AccessType.PRIVILEGED, desc = "Kicks a member with theatrics.")
async def remove(activator: Neighbor, context: Context, reason = None):
    if len(context.args) < 1:
        raise CommandArgsError("Need to @mention someone to kick");
    else:
        target = context.args[0];
    general = await context.guild.fetch_channel(FF.general_channel);
    audit = await context.guild.fetch_channel(FF.audit_channel);
    await general.send(f"{target} has been kicked! https://tenor.com/view/thor-avenger-chris-hemsworth-mjolnir-gif-13624915");
    to_kick = await context.guild.fetch_member(int(target[2:-1]));
    await to_kick.kick(reason=reason);
    await audit.send(to_kick.name + " has been kicked.")

@command_handler.Command(AccessType.PRIVILEGED, desc = "Kicks a member with theatrics.")
async def erase(activator: Neighbor, context: Context):
    if len(context.args) < 1:
        raise CommandArgsError("Need to @mention someone to kick");
    else:
        target = context.args[0];
    general = await context.guild.fetch_channel(FF.general_channel);
    audit = await context.guild.fetch_channel(FF.audit_channel);
    await general.send(f"{target} has been kicked! https://tenor.com/view/thor-avenger-chris-hemsworth-mjolnir-gif-13624915");
    to_kick = await context.guild.fetch_member(int(target[2:-1]));
    await to_kick.kick(reason=reason);
    await audit.send(to_kick.name + " has been kicked.")

@command_handler.Command(AccessType.PRIVILEGED, desc = "Kicks a member with theatrics.")
async def impale(activator: Neighbor, context: Context, reason = None):
    if len(context.args) < 1:
        raise CommandArgsError("Need to @mention someone to kick");
    else:
        target = context.args[0];
    general = await context.guild.fetch_channel(FF.general_channel);
    audit = await context.guild.fetch_channel(FF.audit_channel);
    await general.send(f"{target} has been kicked! https://tenor.com/view/the-wheel-of-time-wheel-of-time-saidar-one-power-true-source-gif-26196681");
    to_kick = await context.guild.fetch_member(int(target[2:-1]));
    await to_kick.kick(reason=reason);
    await audit.send(to_kick.name + " has been kicked.")

@command_handler.Command(AccessType.PRIVILEGED, desc = "Kicks a member with theatrics.")
async def delete(activator: Neighbor, context: Context, reason = None):
    if len(context.args) < 1:
        raise CommandArgsError("Need to @mention someone to kick");
    else:
        target = context.args[0];
    general = await context.guild.fetch_channel(FF.general_channel);
    audit = await context.guild.fetch_channel(FF.audit_channel);
    await general.send(f"{target} has been kicked! https://tenor.com/view/thor-avenger-chris-hemsworth-mjolnir-gif-13624915");
    to_kick = await context.guild.fetch_member(int(target[2:-1]));
    await to_kick.kick(reason=reason);
    await audit.send(to_kick.name + " has been kicked.")

@command_handler.Command(AccessType.PRIVILEGED, desc = "Bans a member with theatrics.")
async def ban(activator: Neighbor, context: Context, reason = None):
    general = await context.guild.fetch_channel(context.ID_bundle.general_channel);
    audit = await context.guild.fetch_channel(FF.audit_channel.value);
    await general.send(f"{target} has been banned! https://tenor.com/view/bongocat-banhammer-ban-hammer-bongo-gif-18219363");
    to_ban = await context.guild.fetch_member(int(target[2:-1]));
    await to_ban.ban(reason=reason);
    await audit.send(to_ban.name + " has been banned.")


@command_handler.Command(AccessType.PRIVILEGED, desc = "Mutes a member.")
async def mute(activator: Neighbor, context: Context, reason = None):
    general = await context.guild.fetch_channel(context.ID_bundle.general_channel);
    await general.send("This feature has not been implemented.")

# @command_handler.Command(AccessType.DEVELOPER, desc = "Updates a Neighbor of given ID with a given XP amt and a given # of each crop")
# async def start(activator: Neighbor, context: Context):
#     if len(context.args) < 4:
#         raise CommandArgsError("`$start` expects 3 arguemnts: the id of the player whose profile needs updating, the xp to give them, and the # of each crop to give them.")
#     id = int(context.args[1]);
#     xp = int(context.args[2]);
#     num_crops = int(context.args[3]);

#     to_update = Neighbor(id, FF.guild);
#     to_update.

@command_handler.Command(AccessType.DEVELOPER, desc = "Overrides all cooldown items.")
async def override(activator: Neighbor, context: Context):
    if not len(context.args) > 0:
        raise CommandArgsError("```override``` expectes 1 argument: the id of the player whose cooldowns need overridden")
    id = int(context.args[0]);
    neighbor = Neighbor(id, FF.guild);
    inventory = neighbor.get_inventory();
    for item in inventory:
        if "cooldown" in item.name.lower():
            neighbor.vacate_item(item);
            await context.send(f"`item: {item.name} overriden for player with id: {id}`");

# @command_handler.Loop(minutes = 20) 
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

async def set_nick(user, guild, was_changed = False):

    member = guild.get_member(user.id)
    if member is None:
        return

    neighbor = Neighbor(user.id, guild.id);
    user_role_ids = [role.id for role in user.roles];

    name = user.display_name;

    new_nick = name;

    with open('families.json') as fFamilies:
        families = json.load(fFamilies)
    with open("rss.json") as fRSS:
        rss = json.load(fRSS);

    tags = [x["tag"] for x in families];

    for tag in tags:
        new_nick = new_nick.replace(tag, "");

    old_tags = [x["old_tag"] for x in families]

    new_nick = re.sub(r'\[.*?\]', '', new_nick)

    for old_tag in old_tags:
        new_nick = new_nick.replace(old_tag, "");

    new_nick = new_nick.replace("❤", "");
    new_nick = new_nick.replace("{CM} ", "");
    new_nick = new_nick.replace(" {CM}", "");
    new_nick = new_nick.replace("[??] ", "");
    new_nick = new_nick.replace("[??]", "");
    new_nick = new_nick.replace("[coe] ", "");

    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                        "]+", re.UNICODE)

    new_nick = re.sub(emoj, '', new_nick)

    new_nick = new_nick.strip();

    if not neighbor.get_item_of_name("Invisibility Cloak"):

        # if 648188387836166168 in user_role_ids:
        #     new_nick = new_nick + " {CM}";

        for family in families:
            if family["role_id"] in user_role_ids or family["honorary_role_id"] in user_role_ids:
                if neighbor.get_item_of_name("*Family Logo Tag* -- Best Seller") is None:
                    new_nick = family["old_tag"] + " " + new_nick;
                    # new_nick = "[" + random.choice(string.ascii_uppercase) + "] " + new_nick;
                else:
                    new_nick = family["emoji"] + new_nick;

        tag_items = neighbor.get_items_of_type("tag");


        for tag_item in tag_items:
            if tag_item.name == "*Family Logo Tag* -- Best Seller":
                continue;
            cur = None;
            for category in rss:
                if not cur is None:
                    break;
                if category["name"] == "Tags":
                    if not cur is None:
                        break;
                    for item in category["items"]:
                        try:
                            if item["name"] == tag_item.name:
                                emojis = None;
                                values = None;
                                emoji = None;
                                try:
                                    emojis = item["emojis"];
                                except:
                                    try:
                                        values = item["values"];
                                    except:
                                        emoji = item["emoji"];
                                if not emojis is None:
                                    cur = random.choice(emojis);
                                    cur = chr(int(cur, 16));
                                elif not values is None:
                                    cur = values[int(tag_item.get_value("val"))]
                                    cur = chr(int(cur, 16));
                                else:
                                    cur = unicodes[emoji];
                        except:
                            print("Issue with " + tag_item.name);
                            continue;
            new_nick = cur + new_nick;        

        with open("crown.txt", "r") as fTrophy:
            for line in fTrophy.readlines():
                if int(line) in user_role_ids:
                    new_nick = unicodes["crown"] + new_nick;

        with open("trophy.txt", "r") as fTrophy:
            for line in fTrophy.readlines():
                if int(line) in user_role_ids:
                    new_nick = unicodes["trophy"] + new_nick;

        with open("top_3.txt", "r") as fTop:
            for i, line in enumerate(fTop.readlines()):
                if int(line) == user.id:
                    if i == 0:
                        new_nick = unicodes["first"] + new_nick;
                    if i == 1:
                        new_nick = unicodes["second"] + new_nick;
                    if i == 2:
                        new_nick = unicodes["third"] + new_nick;

        # target_channel_id = 648218302321131540  
        # target_message_id = 1312483232272482325

        # target_emojis = ['❄️', '☃️', '🌨️', '🥶']

        # channel = await guild.fetch_channel(target_channel_id)
        # message = await channel.fetch_message(target_message_id)

        # # Dictionary to store user IDs by emoji
        # reactions_by_emoji = {emoji: [] for emoji in target_emojis}

        # # Iterate through the reactions
        # for reaction in message.reactions:
        #     emoji = str(reaction.emoji)
        #     if emoji in target_emojis:
        #         # Fetch the users who reacted with this emoji
        #         async for userx in reaction.users():
        #             reactions_by_emoji[emoji].append(userx.id)

        # Output the results
        # for emoji, user_ids in reactions_by_emoji.items():
        #     if neighbor.ID in user_ids:
        #         new_nick = emoji + new_nick;
        
        if neighbor.ID == 788800859101331519 or neighbor.ID == 756594358127427685 or neighbor.ID == 799819969503428659 or neighbor.ID == 240899039749603328:
            if not neighbor.get_item_of_name("Exclusive Farmmas Tag!"):
                item = Item("Exclusive Farmmas Tag!", "event_emoji", -1, emoji="🎁", display="None")
                neighbor.bestow_item(item)   
            
        # if neighbor.ID in [749225745460625409, 987955038804639744, 648229959973994506, 1340578790690132061, 1196537397920415846, 374979463789805570, 86972918415781888, 1357263923409059901, 355169964027805698, 793099607222648852, 1282679887580102799, 969072183114625026]:
        #     new_nick = "🌍" + new_nick;
            
        # if 656112994392080384 in user_role_ids:
        #     new_nick = "🐰" + new_nick;
            
        # if 1024052938752151552 in user_role_ids:
        #     new_nick = "💕" + new_nick;
        
        counter = 0;
        ls_already = [];
        to_add = []
        for item in neighbor.get_items_of_type("event_emoji"):
            print(f"checking: {item.get_value("emoji")}")
            print(item.get_value("display"))
            display = False;
            if item.get_value("display") == "True":
                display = True;
            elif item.get_value("display") == "None":
                if item.expiration - time.time() < 17280000 and item.get_value("display") == "None":
                    display = False;
                else:
                    display = True;
                    
            if display:
                emoji = item.get_value("emoji");
                ls_already.append(emoji)
                to_add.append(item);
                
        to_add.sort(key=lambda x: x.expiration, reverse=True);
                
        for item in to_add:
            if counter < 3:
                counter += 1;
                emoji = item.get_value("emoji");
                print(f"found this emoji activated!")
                new_nick = item.get_value("emoji") + new_nick
            
        # donated_channel_id = 1367560282519507004
        # donated_channel = await guild.fetch_channel(donated_channel_id);
        # async for message in donated_channel.history(oldest_first=True, limit=None):
        #     if str(user.id) in message.content:
        #         new_nick = "⚓️" + new_nick
        #         break;
        
        # wheel = neighbor.get_item_of_name("Wheel")
        # horse = neighbor.get_item_of_name("Horse")
        # juggler = neighbor.get_item_of_name("Juggler")
        
        # if wheel:
        #     new_nick = "🎡" + new_nick
        # if horse:
        #     new_nick = "🎠" + new_nick
        # if juggler:
        #     new_nick = "🤹" + new_nick
        
        # if neighbor.ID in [648229959973994506,374979463789805570]:
        #     new_nick = "💍" + new_nick;
            
            
        if neighbor.get_items_of_type("coe"):
            new_nick = "[coe] " + name;
        
    # print(new_nick)
    if new_nick != name:
        try:
            if new_nick != "":
                await user.edit(nick = new_nick[0:32]);
                print(new_nick);
            else:
                await user.edit(nick=user.name)
        except Exception as e:
            traceback.print_exc();
            print(new_nick);
            if was_changed:
                pass
                # await user.send(f"Hi! Greg here. It looks like you changed your nickname to {user.nick} although it should be {new_nick} to be in line with Greg's monopoly. I tried to change it for you but for some reason I was unsuccessful, probably because I do not have permission to.")


async def set_roles(user, guild):
    if guild.id == FF.guild:
        role_ids = [FF.strawberry_role, FF.blueberry_role, FF.chicken_icon, FF.coin_icon, FF.diamond_icon, FF.barn_icon, FF.greg_icon, FF.rainbow_role, FF.invisibility_role];
    else:
        role_ids = [PHOENIX.strawberry_role, PHOENIX.blueberry_role, "", "", "", "", "", PHOENIX.rainbow_role, PHOENIX.invisibility_role];
    names = ["Strawberry Tag", "Blueberry Tag", "Hay Day Chicken", "Hay Day Coin", "Hay Day Diamond", "The Barns of Friendly Farmers Collection", "Hay Day Greg", "*Rainbow Role* -- Best Seller", "Invisibility Cloak"];

    user_role_ids = [role.id for role in user.roles];

    neighbor = Neighbor(user.id, guild.id);
    neighbor.expire_items();
    for i, id in enumerate(role_ids):
        item = neighbor.get_item_of_name(names[i]);
        if item is None and id in user_role_ids:
            role = guild.get_role(id);
            await user.remove_roles(role);
        elif not item is None and not id in user_role_ids:
            role = guild.get_role(id);
            await user.add_roles(role);

def strip(neighbor, levels: int = None, xp: int = None):
    if not xp is None:
        neighbor.set_XP(neighbor.get_XP() - xp);
    elif not levels is None:
        cur_level = neighbor.get_level();
        distance_to_next_level = Neighbor.get_XP_for_level(cur_level + 1) - Neighbor.get_XP_for_level(cur_level);
        percent_progress_to_next_level = neighbor.get_XP_for_next_level() / distance_to_next_level;

        new_level = cur_level - levels;
        neighbor.set_XP(Neighbor.get_XP_for_level(new_level));
        new_distance_to_next_level = Neighbor.get_XP_for_level(new_level + 1) - Neighbor.get_XP_for_level(new_level);
        add = int(new_distance_to_next_level * percent_progress_to_next_level);
        neighbor.increase_XP(add);

async def inc_xp(neighbor: Neighbor, amount, context=None):
    member = await context.guild.fetch_member(neighbor.ID);
    name = member.display_name;
    cur_lvl = neighbor.get_level();
    neighbor.increase_XP(amount);
    new_lvl = neighbor.get_level();

    if new_lvl > cur_lvl:
        best_this_month = neighbor.get_item_of_name("Best Level This Month");
        best_this_month = int(best_this_month.get_value("level"))
        if new_lvl > best_this_month:
            best_this_month = new_lvl;

        target = await context.guild.fetch_channel(context.ID_bundle.bot_channel);

        if not neighbor.get_item_of_name("Hype Man") is None:
            await target.send("<@" + str(member.id) + "> has advanced to level " + str(new_lvl) + "!\nKeep it up, I have always believed in you! <3 :)");
        elif neighbor.get_item_of_name("Pings Off"):
            await target.send(name + " has advanced to level " + str(new_lvl) + "!");
        # elif new_lvl == 3:
        #     await target.send("<@" + str(member.id) + "> has advanced to level " + str(new_lvl) + "!" + "\n*You can now access my roadside shop! Try it out with $rss!*");
        # elif new_lvl == 5 and best_this_month == 5:
        #     await target.send("<@" + str(member.id) + "> has advanced to level " + str(new_lvl) + "!" + "\n*You have unlocked a few special offers in my roadside shop! Try it out with $rss!*");
        elif (new_lvl > 4 and chance(5)) or new_lvl % 10 == 0:
            choices = ["Fantastic! And when you reach a milestone level you can get a free 3 day booster. Not bad, eh?", "Did you know? Use $rss to spend your levels on cool items!", "Wohoo! Thanks for being active!", "Beware! At the beginning of each month, the __reckoning__ halves all players' levels! Don't worry though, I will send a reminder before it happens.", "Remember! As you begin to level up more, items in the $rss become comparatively more expensive because they cost a constant number of levels!", "Great job! Rose is jealous for sure!", "Nice! If you're looking for more ways to earn XP, try $harvest once per hour then sell your crops at the farmers market!", "Ping! Annoyed with my pings? Try `$pings off`", "P.S. The boosters category of my roadside shop can make you much richer. Try `$rss`!", "Use $profile to see your current level!", "Try `$emojis` to customize your server nickname!"];
            await target.send("<@" + str(member.id) + "> has advanced to level " + str(new_lvl) + "!" + "\n*" + random.choice(choices) + "*");
        else:
            await target.send(name + " has advanced to level " + str(new_lvl) + "!");

        if (new_lvl == 5 or new_lvl == 10 or new_lvl == 20 or new_lvl == 30 or new_lvl == 50 or new_lvl == 100) and best_this_month == new_lvl:
            await target.send("You have also reached a milestone level for the first time this month! Congratulations.")
            await target.send(f"You reached level {new_lvl} so you will get {new_lvl}% extra xp per message for 72 hours.")
            boost = Item("Milestone Boost", "milestone_boost", int(time.time() + 259200), boost = new_lvl);
            neighbor.bestow_item(boost);


@command_handler.Scheduled(time="12:00",day_of_month=10)
async def election_reminder(client):
    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(648227629811630098)
    
    await channel.send("Elections must start today! <@&1198350179141693500>")
    
@command_handler.Scheduled(time="12:00",day_of_month=25)
async def election_reminder1(client):
    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(648227629811630098)
    
    await channel.send("Elections must start today! <@&1198350179141693500>")
    
    
@command_handler.Scheduled(time="12:00",day_of_month=5)
async def nomination_reminder(client):
    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(648227629811630098)
    
    await channel.send("Begin gathering election nominees! 5 day warning. <@&1198350179141693500>")
    
@command_handler.Scheduled(time="12:00",day_of_month=20)
async def nomination_reminder1(client):
    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(648227629811630098)
    
    await channel.send("Begin gathering election nominees! 5 day warning. <@&1198350179141693500>")

@command_handler.Scheduled(time="12:00",day_of_week=1)
async def commerce_reminder(client):
    guild = client.get_guild(FF.guild);
    channel = await guild.fetch_channel(1394752421820891156)
    
    if remember("commerce_reminders") == "Produce":
        await channel.send(f"<@&1253899618719367279> hello all, this is your reminder that it's a trading week!\nRemember to log those trades! Thank you for your hard work!")
        remember("commerce_reminders", "Trade")
    elif remember("commerce_reminders") == "Trade":
        await channel.send(f"<@&1253899618719367279> hello all, congrats on a well-earned off week.\nSee you next week for production!")
        remember("commerce_reminders", "Off")
    else: 
        await channel.send(f"<@&1253899618719367279> hello all, this is your reminder it's a production week!")
        remember("commerce_reminders", "Produce")
        

# from datetime import datetime, timezone



# @command_handler.Uncontested(
    type="MESSAGE",
    desc="Assigns a family if user has enough qualifying messages in the channel",
    priority=2,
    generic=True
# )
async def assign_family(context: Context):
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

async def get_role_count(guild, *ids: int):
    # returns true if all roles belong to the member
    count = 0;
    async for member in guild.fetch_members():
        role_ids = [role.id for role in member.roles];
        flag = True;
        for id in ids:
            if not id in role_ids:
                flag = False;
        if flag:
            count += 1;
    return count;

def get_neighborhood_from_user(user):
    guild = user.guild;
    if has_role(user, guild.get_role(FF.p_neighbors_role)):
        return "FFP";
    if has_role(user, guild.get_role(FF.neighbors_role)):
        return "FF";
    if has_role(user, guild.get_role(FF.j_neighbors_role)):
        return "FFJ";
    # if has_role(user, guild.get_role(1334660124639236267)):
    #     return "FFJ2"
    if has_role(user, guild.get_role(FF.g_neighbors_role)):
        return "FFG"; 
    if has_role(user, guild.get_role(1342329111359656008)):
        return "FFC"; 
    if has_role(user, guild.get_role(FF.r_neighbors_role)):
        return "FFR";
    return None;

def load_families_py_exec(path: str = "families.py") -> dict:
    namespace = {}
    with open(path, "r", encoding="utf-8") as f:
        exec(f.read(), namespace)

    if "families" not in namespace:
        raise ValueError("families.py does not define 'families'")

    return namespace["families"]

def write_families_py_exec(families: dict, path: str = "families.py"):
    """
    Writes a families dict to a Python file that defines:
        families = {...}
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write("families = {\n")
        for family, members in families.items():
            f.write(f'    "{family}": {members},\n')
        f.write("}\n")

async def count_family(guild, member_ids, nh = None):
    # guild = client.get_guild(FF.guild);
    neighbors_role = guild.get_role(1181330910747054211);
    nh_role = guild.get_role(nh) if nh else None;
    
    resort = nh == 1034248720058945577;
    resort_role = guild.get_role(1034248720058945577);
    
    count = 0;
    for id in member_ids:
        try:
            cur_member = await guild.fetch_member(id);
        except:
            continue;
        if nh_role and has_role(cur_member, neighbors_role) and has_role(cur_member, nh_role):
            count += 1;
        elif has_role(cur_member, neighbors_role) and not has_role(cur_member, resort_role):
            count += 1;
    return count

async def count_all(client, families_ids, nh = None):
    guild = client.get_guild(FF.guild);
    neighbors_role = guild.get_role(1181330910747054211);
    nh_role = guild.get_role(nh) if nh else None;

    resort_role = guild.get_role(1034248720058945577);
    
    count = 0;
    for family, member_ids in families_ids.items():
        for id in member_ids:
            cur_member = await guild.fetch_member(id);
            if nh_role and has_role(cur_member, neighbors_role, nh_role):
                count += 1;
            elif has_role(cur_member, neighbors_role) and not has_role(cur_member, resort_role):
                count += 1;
        return count

async def pick_family(after):
    guild = after.guild;
    targetAF = await guild.fetch_channel(FF.assign_family_channel);
    targetBC = await guild.fetch_channel(704366328089280623);

    # await targetAF.send("While I would love to assign this player a family, this feature is currently under construction. Please pardon my dust. This player will be assigned a family soon.")
    # return 0;

    neighborhood_after = get_neighborhood_from_user(after);
    if neighborhood_after is None:
        return "No NH";
    neighborhood_after = neighborhood_after.lower();
    # if neighborhood_after == "ffj2":
    #     return "FFJ2";
    
    if not get_family_from_user(after) is None:
        print(get_family_from_user(after))
        return "Alrdy has family";

    # Hardcoded ID-to-family mapping
    families_hardcoded = {
        "Bunny": [316114265645776896, 660204032362545152, 312019945913319424],
        "Cheetah": [648229959973994506, 840077393683021824, 1282679887580102799, 795304848181821481],
        "Donkey": [605235104599769098, 1322905749139226656],
        "Fox": [220427859229933568, 793099607222648852, 430454367003475978, 863037754164903946],
        "Giraffe": [160694804534132736, 374979463789805570, 374652286233870346],
        "Hippo": [963533131854532638, 287705818462289922, 516969515486019604, 514413698761359400],
        "Penguin": [355169964027805698, 987955038804639744, 443437059793879051, 1011941542287650856, 756594358127427685],
    }
    
    for family_name, members in families_hardcoded.items():
        if after.id in members:
            with open("families.json") as fFamilies:
                family_info = json.load(fFamilies)
                
            role_id = next((family["role_id"] for family in family_info if family["name"] == family_name), None)
            honorary_role_id = next((family["honorary_role_id"] for family in family_info if family["name"] == family_name), None)
            if role_id:
                role = guild.get_role(int(role_id))
                if neighborhood_after == "ffr":
                    role = guild.get_role(int(honorary_role_id))
                await after.add_roles(role)
                await targetAF.send(f"In 2026, <@{after.id}> will be part of the {family_name} family!")
            else:
                await targetAF.send(f"Family '{family_name}' not found in families.json for <@{after.id}>.")
            return "Hardcoded";   
        
    with open("families.json") as fFamilies:
        family_info = json.load(fFamilies);
        
    matchup = {
        "bunnies": "Bunny",
        "cheetahs": "Cheetah",
        "donkeys": "Donkey",
        "foxes": "Fox",
        "giraffes": "Giraffe",
        "hippos": "Hippo",
        "penguins": "Penguin"
    }
    
    new_family_name = None
    already_picked = load_families_py_exec()
    for family_name, members in already_picked.items():
        if after.id in members:
            new_family_name = matchup[family_name]

    votes = {};

    if neighborhood_after == "ffp":
        nh_role = 1024052938752151552;
    elif neighborhood_after == "ff":
        nh_role = 656112994392080384;
    elif neighborhood_after == "ffj":
        nh_role = 689928709683150909;
    elif neighborhood_after == "ffj2":
        nh_role = 1334660124639236267;
    elif neighborhood_after == "ffg":
        nh_role = 1173325157767589988;
    elif neighborhood_after == "ffc":
        nh_role = 1342329111359656008
    elif neighborhood_after == "ffr":
        nh_role = 1034248720058945577
    
    if not new_family_name:
        
        nj = await get_role_count(guild, nh_role); # disparity for joining neighborhood 
        nt = await get_role_count(guild, 1181330910747054211); # disparity for total neighbors
        
        for family in family_info:
            
            family_in_dict = next(k for k, v in matchup.items() if v == family["name"])
        
            # fj = await get_role_count(guild, family["role_id"], nh_role);
            fj = await count_family(guild, already_picked[family_in_dict], nh_role) # disparity for joining neighborhood family only
            # ft = await get_role_count(guild, family["role_id"]);
            ft = await count_family(guild, already_picked[family_in_dict]) # disparity for total neighbors family only
            
            dj = max(int(nj/7) - fj, 0);
            dt = max(int((nt - 25)/7) - ft, 0);
            r = (dj ** 2 + dt + 1) ** 2
            
            votes[family['name']] = {'weight': r, 'role_id': family['role_id'], "dj": dj, "dt": dt};
            
            await targetBC.send(f"{family["name"]}: {r}\n"
                                "dj{dj} = nj{nj}/7 - fj{fj}\n"
                                "dt{dt} = nt{nt} - 25/7 - ft{ft}");
            
            
        await targetBC.send(f"<@{after.id}> was assigned according to the following weights:")
        # Create a string with family names and their weights
        votes_summary = "\n".join([f"{family}: {info['weight']}; joining disparity: {info["dj"]}; total disparity: {info["dt"]}" for family, info in votes.items()])

        # Send the formatted string to the target channel
        # await targetBC.send(votes_summary)
    else:
        await targetBC.send(f"<@{after.id}>'s family was predestined.")

    family_decision = new_family_name or random.choices(
        population=list(votes.keys()),  # Family names
        weights=[v['weight'] for v in votes.values()],  # Corresponding weights
        k=1  # Pick one
    )[0]
    
    family_in_dict = next(k for k, v in matchup.items() if v == family_decision)
    
    already_picked[family_in_dict].append(after.id)
    
    write_families_py_exec(already_picked);

    role_id = next((family["role_id"] for family in family_info if family["name"] == family_decision), None)
    honorary_role_id = next((family["honorary_role_id"] for family in family_info if family["name"] == family_decision), None)
    if role_id:
        role = guild.get_role(int(role_id))
        if neighborhood_after == "ffr":
            role = guild.get_role(int(honorary_role_id))
    
    return;
    
    # tg_msg = await targetAF.send(f"In 2025, <@{after.id}> will be part of the {family_decision} family!")
    # await tg_msg.add_reaction() #add reaction 

    codes = get_code_replacement(None, True);
    await targetAF.send(f"{codes['&FFP_LOGO']}{codes['&FF_LOGO']}{codes['&FFJ_LOGO']}{codes['&FFG_LOGO']}{codes['&FFC_LOGO']}" + f"\n**Welcome to Friendly Farmers!** <@{after.id}>")
    await targetAF.send('It\'s time for you to be assigned a Family :butterfly::leopard::fox::racehorse::dog:!')
    await targetAF.send('Give me just a moment to consider to which you belong.')
    time.sleep(9.5);

    while True:
        time.sleep(3.0);
        candidate = random.choice(family_info);
        if candidate["name"] == family_decision and chance(2):
            await targetAF.send('Alright, I think I\'ve got it!')
            target = await targetAF.send("Congratulations!" + ' you are now a member of the **' + candidate["name"] + ' Family** ' + candidate["emoji"]);
            # await targetAF.send('"' + candidate["description"] + '"');
            await target.add_reaction(candidate["emoji"])
            time.sleep(1.5);
            target_msg = await targetAF.send(f"$info {candidate['name'].lower()}");
            await info(Neighbor(691338084444274728, 647883751853916162), Context(target_msg), candidate['name'].lower());
            
            with open(f"{candidate['name']}.png", 'rb') as file:
                await targetAF.send(file=discord.File(file))
                
            options = ["<:cutefrog:1060011712453025872>", "<:yayy:1060019006112796772>", "<:luv:1174714431847014400>", "<:catexcited:1190103204076199946>", "<:dittoshocked:1189348081116913807>"]
            chosen_emoji = random.choice(options);
            family_chat = await guild.fetch_channel(candidate['chat'])
            await family_chat.send(f"**Attention <@&{candidate['role_id']}>!**\nWe have a new {candidate['name']}!! {chosen_emoji}\nPlease welcome... <@{after.id}>!")
            
            break;
        else:
            if chance(3):
                continue;
            await targetAF.send('Hmm... does the ' + candidate["name"] + ' Family sound right?');
            await targetAF.send("No, no I don't think so.");
            
    await after.add_roles(role)
    return candidate["name"] if not neighborhood_after == "ffr" else False;

def has_role(user, role):
    return role == user.get_role(role.id);

def get_family_from_user(user):
    guild = user.guild;
    
    import json

    with open("families.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for family in data:
        main_role = guild.get_role(family["role_id"])
        honorary_role = guild.get_role(family["honorary_role_id"])
        
        if has_role(user, main_role) or has_role(user, honorary_role):
            return family;

    return None;

def get_code_replacement(str = None, all = None):
    if is_within_dates((11,9),(12,31)):
        codes = {
            "&FFP_LOGO": "<:farmmas_ffp_logo:1170071905089368075>",
            "&FF_LOGO": "<:farmmas_ff_logo:1170071779037945907>",
            "&FFJ_LOGO": "<:farmmas_ffj_logo:1170071826517467136>",
            "&FFG_LOGO": "<:farmmas_ffg_logo:1173333335876050985>",
            "&FFR_LOGO": "<:farmmas_ffr_logo:1170071889029386404>",
            "&FFC_LOGO": "<:farmmas_ffc_logo:1454605765330341999>",
            "&FFP_TAG": "#L92LUVQJ",
            "&FF_TAG": "#9UPRVCUR",
            "&FFJ_TAG": "#PC8VCJ8Q",
            "&FFG_TAG": "#QP8JURUC",
            "&FFJ2_TAG": "#RGP8J9GP",
            "&FFR_TAG": "#L92LUVQJ",
        }
    else:
        codes = {
            "&FFP_LOGO": "<:ffp_logo:1111011980061462538>",
            "&FF_LOGO": "<:ff_logo:1111011971953872976>",
            "&FFJ_LOGO": "<:ffj_logo:1111011976320122880>",
            "&FFJ2_LOGO": "<:ffj2_logo:1335746631236194344>",
            "&FFG_LOGO": "<:ffg_logo:1173332572642754560>",
            "&FFC_LOGO": "<:ffc_logo:1342333117607710741>",
            "&FFR_LOGO": "<:ffr_logo:1111011982787743866>",
            "&FFP_TAG": "#L92LUVQJ",
            "&FF_TAG": "#9UPRVCUR",
            "&FFJ_TAG": "#PC8VCJ8Q",
            "&FFG_TAG": "#QP8JURUC",
            "&FFJ2_TAG": "#RGP8J9GP",
            "&FFC_TAG": "#G8P8YGPG",
            "&FFR_TAG": "#L92LUVQJ",
        }
    if all:
        return codes;
    return codes[str];

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
