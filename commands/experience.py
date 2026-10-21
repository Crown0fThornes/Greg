"""Experience commands and their supporting helpers."""

from .common import *
xp_gained = 0;

xp_happy_hour = 1;

last_profitable_message_author_id = 0;


@command_handler.Uncontested(type = "MESSAGE", desc = "Incrememnts a Neighbor's server XP each time they send a message.", priority = 2, generic = True)
async def message_xp(context: Context):

    from .families import get_family_from_user
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


@command_handler.Uncontested(type = "MESSAGE", desc = "If a Neighbor has the Hype Man item, which can be purchased in the rss, then Greg will react to the Neighbor's messages with an emoji.", priority = 2)
async def hype_man_responses(context: Context):
    from .community import celebrate
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

















































@command_handler.Scheduled(time="00:01", day_of_month=1, desc="Reckoning warning")
async def reckoning_warning(client):
    guild = client.get_guild(FF.guild)
    bc = await guild.fetch_channel(FF.bot_channel)

    message = (
        "**The reckoning is upon you!**\n"
        "In one day's time, all Neighbors' server levels are to be cut in half!\n"
        "This is a disastrous act of nature, which I cannot prevent and have no control over.\n"
        "You all are best off accepting its coming!\n"
        "It may be wise to spend those levels before the reckoning, and I have plenty of great deals in my `$rss`!\n\n"
        "-# Notably, a reduction in half of one's levels results in a much worse reduction in XP, since each level up is worth more XP than the last."
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
    from .families import get_family_from_user, get_neighborhood_from_user
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

