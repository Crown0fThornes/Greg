"""Economy commands and their supporting helpers."""

from .common import *
    
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
        raise CommandArgsError("Please run the command with 4 arguments:\n\n1) # of bolts 2) # of planks 3) # of duct tapes 4) reason \nExample: `$treasury -30 -30 -29 Jenny for Fair`\nor with 1 argument: 1) 'total'")
    
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


@command_handler.Uncontested(type = "MESSAGE")
async def blincoln(context: Context):
    if "blincoln" in context.content.lower():
        await context.message.delete();
        await context.send("stop that");

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
        
        
@command_handler.Scheduled("08:00", day_of_month=1)
async def open_barn_sale(client):
    guild = client.get_guild(647883751853916162)
    if guild is None:
        return

    town_square = await guild.fetch_channel(648223363600351263)

    barn_sale_channel = await guild.create_text_channel(
        "🪧neighborhood-barn-sale",
        category=town_square
    )

    await barn_sale_channel.send("# 🪧 Neighborhood Barn Sale! 🌾")
    
    await barn_sale_channel.send("<@&1181330910747054211>")

    await barn_sale_channel.send(
        "A strong flow of goods and coins is crucial for a strong Neighborhood economy. "
        "Hosting a barn sale is a great way to earn yourself some coins and help your "
        "Neighbors with valuable items."
    )

    await barn_sale_channel.send(
        "You are encouraged to host a barn sale whenever you like! But today I'm "
        "challenging as many people as possible to all host one & help us start the "
        "new month off right."
    )

    await barn_sale_channel.send("# Instructions")

    await barn_sale_channel.send(
        "1. **For my challenge, put up as many barn items in your RSS as your farm level!** "
        "For example, a level 20 player should sell at least 20 items; a level 100 player "
        "should sell at least 100. Max price is fine."
    )

    await barn_sale_channel.send(
        "2. **Don't put a newspaper ad on your shop.** Instead, post in your NH chat "
        "(on Discord or in-game) that you're hosting a barn sale."
    )

    await barn_sale_channel.send(
        "3. **Take before & after pictures** showing your RSS before Neighbors start "
        "buying things up, then again afterward (before you collect the coins)."
    )

    await barn_sale_channel.send(
        "4. **Post your screenshots below!** A lucky poster will win 20 BEMs tomorrow!"
    )

    remember("barn_sale_channel_id", barn_sale_channel.id)

    gc = await guild.fetch_channel(648223397205114910)

    await gc.send(
        f"A new month is here; start it off right with a barn sale! "
        f"There's even a chance to earn **20 BEMs!!** <#{barn_sale_channel.id}>"
    )



@command_handler.Scheduled("20:00", day_of_month=2)
async def choose_barn_sale_winner(client):
    guild = client.get_guild(647883751853916162)
    if guild is None:
        return

    barn_sale_channel_id = remember("barn_sale_channel_id")
    if barn_sale_channel_id is None:
        return

    try:
        barn_sale_channel = await guild.fetch_channel(barn_sale_channel_id)
    except discord.NotFound:
        return

    participants = set()

    async for message in barn_sale_channel.history(
        limit=None,
        oldest_first=True
    ):
        if message.author.bot:
            continue

        has_image = any(
            attachment.content_type
            and attachment.content_type.startswith("image/")
            for attachment in message.attachments
        )

        if has_image:
            participants.add(message.author.id)

    if not participants:
        await barn_sale_channel.send(
            "**Looks like nobody entered this month's Barn Sale Day drawing!** 😔\n"
            "We'll try again next month!"
        )
        return

    winner = random.choice(tuple(participants))

    await barn_sale_channel.send(
        f"**Thanks all for participating!** We have a winner! It's <@{winner}>! "
        "Open a ticket at <#1033207181857800242> to claim your 20 BEMs!"
    )

    possible_messages = [
        "<:yayy:1060019006112796772><:yayy:1060019006112796772><:yayy:1060019006112796772>",
        "<:cutefrog:1060011712453025872><:cutefrog:1060011712453025872><:cutefrog:1060011712453025872>",
        "Nothing like some good ole artificial economic stimulation! "
        "<:ff_logo:1111011971953872976> That's the FF Difference",
        "But you're all winners in my heart",
        "When will I win anything <:cry:1159831384676909186>",
        "<:strongman2:1248819697747497042><:strongman2:1248819697747497042><:strongman2:1248819697747497042>"
    ]

    await barn_sale_channel.send(random.choice(possible_messages))
    await barn_sale_channel.send(
        "Come back next month for another chance at BEMs!"
    )
    
    gc = await guild.fetch_channel(648223397205114910)
    await gc.send(f"Barn sale day is over. This month we had {len(participants)} participants! Let's go!! <#{barn_sale_channel.id}")



@command_handler.Scheduled("20:00", day_of_month=3)
async def close_barn_sale(client):
    guild = client.get_guild(647883751853916162)
    if guild is None:
        return

    barn_sale_channel_id = remember("barn_sale_channel_id")
    if barn_sale_channel_id is None:
        return

    try:
        barn_sale_channel = await guild.fetch_channel(barn_sale_channel_id)
    except discord.NotFound:
        remember("barn_sale_channel_id", None)
        return

    await barn_sale_channel.delete()
    remember("barn_sale_channel_id", None)

        
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


def real_round(x):
    decimal = x - int(x);
    if decimal >= .5:
        return int(x) + 1;
    else:
        return int(x);



#  Note to self: fix best_this_month: Actually update special offer count & check before showing category

@command_handler.Command(AccessType.PRIVATE, desc = "Allows Neighbors to purchase discord perks like special roles using server XP", generic = True, active=False)
async def rss(activator: Neighbor, context: Context, response: ResponsePackage = None):

    # if activator.ID == 355169964027805698:
    #     with open('indev_rss.json') as fRSS:
    #         rss_info = json.load(fRSS)
    # else:
    from .experience import strip
    from .families import get_neighborhood_from_user, has_role
    from .members import set_nick, set_roles
    with open('lookups/rss.json') as fRSS:
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
                    
                elif item['name'] == "Rainbow Role!":
                    rainbow = context.guild.get_role(1055882917429137479)
                    await user.add_roles(rainbow);
                    
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


@command_handler.Command(AccessType.PRIVATE, desc = "Sell your entire silo!", generic = True)
async def sell(activator: Neighbor, context: Context, response: ResponsePackage = None):
    
    from .experience import inc_xp
    raise PardonOurDustError()

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
    from .experience import strip
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

    
@command_handler.Command(AccessType.PRIVATE, desc = "Steal from another user, if you have Hire Alfred from the rss.")
async def steal(activator: Neighbor, context: Context):
    from .experience import inc_xp
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

