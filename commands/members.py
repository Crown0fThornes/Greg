"""Members commands and their supporting helpers."""

from .common import *
    
@command_handler.Uncontested(type="REACTION", desc="Add heart LTO emoji to nickname")
async def add_hearts(context: Context):
    if not context.message.id == int(remember("heart_message_id")):
        return
    
    HEARTS = {"🩷","❤️","🧡","💛","💚","🩵","💙","💜","🖤","🩶","🤍","🤎"}
    if str(context.emoji) not in HEARTS:
        return

    now = datetime.datetime.now()

    end_of_feb21 = now.replace(month=2, day=21, hour=23, minute=59, second=59, microsecond=0)

    # If it's already past Feb 21 this year, use next year
    if now > end_of_feb21:
        end_of_feb21 = end_of_feb21.replace(year=now.year + 1)

    seconds_left = int((end_of_feb21 - now).total_seconds())
    
    neighbor = Neighbor(context.user.id, FF.guild)
    
    while item := neighbor.get_item_of_name("Valentine's Heart"):
        neighbor.vacate_item(item);
        
    item = Item("Valentine's Heart", "event_emoji", time.time() + seconds_left, emoji=str(context.emoji), display="True")
    neighbor.bestow_item(item)


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


@command_handler.Uncontested(type = "MESSAGE", desc = "Junior")
async def junior_requirement(context: Context):
    if context.channel.id == 704366328089280623:
        try:
            level = int(context.message.content)
            req = level * 40
            await context.send(f"{req}", reply = True);
        except:
            print("not a number");


@command_handler.Command(access_type=AccessType.PUBLIC)
async def requirement(activator: Neighbor, context: Context):
    if len(context.args) < 1:
        raise CommandArgsError("`requirement` expects 1 argument: your farm level!\nFor example: $requirement 40")
    
    try:
        level = int(context.args[0])
    except:
        raise CommandArgsError("`requirement` expects 1 argument: your farm level!\nFor example: $requirement 40")
        
    normal_derby = min(level * 30, 2560)
    power_derby = min(level * 50, 5440)
    other_derby = min(level * 35, 3200)
    
    await context.send(
    f"🌾 **FFJ Derby Requirement for Level {level}**\n"
    f"• **Normal Derby:** {normal_derby} points\n"
    f"• Power Derby: {power_derby}p\n"
    f"• \"400p Derbies\" (Blossom/Mystery/Etc): {other_derby}p\n"
    f"• Chill Derby: 0p\n"
    f"• Derbies with no effect on task points or availability fall under Normal requirements (bunny/bingo/etc)",
    reply=True
    )

    

@command_handler.Loop(minutes = 10)
async def set_time(client):
    from .reminders import carnival_reminders, compliance, derby_reminder, guests, hk_reminders, hospitality_reminders, lotteries_reminders, main_reminders, newspaper_reminders, personalized_recruitment_reminder, pro_reminders, recruitment_reminders, trade_reminder
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
    await main_reminders(client, guild, est_time);
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

        

@command_handler.Command(AccessType.DEVELOPER, desc = "Set your tags and perks")
async def perks(activator: Neighbor, context: Context):
    await context.send("Discord perks given by Greg can include nickname emoji tags, and roles. Here, you can select which of your current perks are being displayed.\nFor example, if you have too many, turn some off. Or just switch things up.\nOften, perks earned from events will be applied automatically for a month, then unapplied for a couple months before they finally expire. ")


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


async def clean_nick(user, guild):
    neighbor = Neighbor(user.id, guild.id);
    user_role_ids = [role.id for role in user.roles];

    name = user.display_name;

    new_nick = name;

    with open('lookups/families.json') as fFamilies:
        families = json.load(fFamilies)
    with open("lookups/rss.json") as fRSS:
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
    
    return new_nick


async def set_nick(user, guild, was_changed = False):
    member = guild.get_member(user.id)
    if member is None:
        return

    neighbor = Neighbor(user.id, guild.id);
    user_role_ids = [role.id for role in user.roles];

    name = user.display_name;

    new_nick = name;

    with open('lookups/families.json') as fFamilies:
        families = json.load(fFamilies)
    with open("lookups/rss.json") as fRSS:
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

        if 1492436522228781106 in user_role_ids:
            new_nick = "🂡" + new_nick

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
                
        to_add.sort(key=lambda x: x.expiration, reverse=False);
                
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
    with open('lookups/rss.json') as fRSS:
        rss_info = json.load(fRSS)
        
    neighbor = Neighbor(user.id, guild.id)
    neighbor.expire_items()
        
    for catergory in rss_info:
        for item in catergory["items"]:
            if "role_id" in item:
                if not neighbor.get_item_of_name(item["name"]):
                    role = guild.get_role(item["role_id"])
                    if role:
                        await user.remove_roles(role)
            if "role_ids" in item:
                if not neighbor.get_item_of_name(item["name"]):
                    for role_id in item["role_ids"]:
                        role = guild.get_role(role_id)
                        if role:
                            await user.remove_roles(role)

