"""Families commands and their supporting helpers."""

from .common import *

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

    
@command_handler.Loop(hours=3)
async def assign_some_families(client):
    # if not chance(5):
    #     return
    # today = datetime.datetime.now().date()
    # first_of_month = (today.month, 1)
    guild = client.get_guild(647883751853916162)
    members = guild.members;
    for assignee in members:
        print(f"Trying: {assignee.name}")
        answer = await pick_family(assignee)
        if not answer in ["Alrdy has family", "FFJ2", "No NH"]:
            return
            pass

        
        
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


@command_handler.Uncontested(type="MESSAGE")
async def treasure_hunt(context: Context):
    if (context.channel.id != 1472265286475317302):
        return
    if (context.author_id == 355169964027805698):
        return;
    
    if not len(context.content) == 2:
        target = await context.send("Claim a spot on the treasure map by sending the grid spot in [Capital Letter][Number] format!\nEx: A1 or F8", reply=True)
        time.sleep(5);
        await context.message.delete();
        await target.delete();
        return
        
        
    letters = ["A", "B", "C", "D", "E", "F"]
    numbers = ["1", "2", "3", "4", "5", "6", "7", "8"]
    if not context.content[0] in letters or not context.content[1] in numbers:
        target = await context.send("Claim a spot on the treasure map by sending the grid spot in [Capital Letter][Number] format, between A1 and F8!\nEx: B2 or E7", reply=True)
        time.sleep(8);
        await context.message.delete();
        await target.delete();
        return
        
    claimed = remember("chosen_squares") or []
    spots_taken = [spot[0] for spot in claimed]
    if context.content in spots_taken:
        target = await context.send("That spot is already claimed! Pick something else.", reply=True)
        time.sleep(8);
        await context.message.delete();
        await target.delete();
        return
    
    authors_taken = [spot[1] for spot in claimed]
    if context.author_id in authors_taken:
        target = await context.send("You've already claimed a spot!", reply=True)
        time.sleep(8);
        await context.message.delete();
        await target.delete();
        return
    
    claimed.append((context.content, context.author_id))
    target = await context.send("Spot claimed!", reply=True)
    remember("chosen_squares", claimed)























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



async def load_families(guild):
    families = {
        "bunnies": [],
        "cheetahs": [],
        "donkeys": [],
        "foxes": [],
        "giraffes": [],
        "hippos": [],
        "penguins": [],
    }
    
    bunny_role = guild.get_role(1454591136860471346)
    cheetah_role = guild.get_role(1454590857591132314)
    donkey_role = guild.get_role(1454591042278920304)
    fox_role = guild.get_role(1342333037509214259)
    giraffe_role = guild.get_role(1454591075757985853)
    hippo_role = guild.get_role(1454593861643931684)
    penguin_role = guild.get_role(1454590623532191774)
    
    async for member in guild.fetch_members():
        if has_role(member, bunny_role):
            families["bunnies"].append(member.id)
        if has_role(member, cheetah_role):
            families["cheetahs"].append(member.id)
        if has_role(member, donkey_role):
            families["donkeys"].append(member.id)
        if has_role(member, fox_role):
            families["foxes"].append(member.id)
        if has_role(member, giraffe_role):
            families["giraffes"].append(member.id)
        if has_role(member, hippo_role):
            families["hippos"].append(member.id)
        if has_role(member, penguin_role):
            families["penguins"].append(member.id)
            
    return families

    


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
    
    member_ids = list(set(member_ids))
    
    count = 0;
    for id in member_ids:
        try:
            cur_member = await guild.fetch_member(id);
        except:
            continue;
        if nh_role:
            if has_role(cur_member, neighbors_role) and has_role(cur_member, nh_role):
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
            if nh_role and has_role(cur_member, neighbors_role) and has_role (cur_member, nh_role):
                count += 1;
            elif has_role(cur_member, neighbors_role) and not has_role(cur_member, resort_role):
                count += 1;
        return count


async def pick_family(after):
    from .community import info
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
            with open("lookups/families.json") as fFamilies:
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
                await targetAF.send(f"Family '{family_name}' not found in lookups/families.json for <@{after.id}>.")
            return "Hardcoded";   
        
    with open("lookups/families.json") as fFamilies:
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
    already_picked = await load_families(guild)
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
                                f"dj{dj} = nj{nj}/7 - fj{fj}\n"
                                f"dt{dt} = nt{nt} - 25/7 - ft{ft}");
            
            
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
    
    # write_families_py_exec(already_picked);

    role_id = next((family["role_id"] for family in family_info if family["name"] == family_decision), None)
    honorary_role_id = next((family["honorary_role_id"] for family in family_info if family["name"] == family_decision), None)
    if role_id:
        role = guild.get_role(int(role_id))
        if neighborhood_after == "ffr":
            role = guild.get_role(int(honorary_role_id))
    
    # return;
    
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

    with open("lookups/families.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for family in data:
        main_role = guild.get_role(family["role_id"])
        honorary_role = guild.get_role(family["honorary_role_id"])
        
        if has_role(user, main_role) or has_role(user, honorary_role):
            return family;

    return None;

