"""Reminders commands and their supporting helpers."""

from .common import *
        
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

    

def is_today_birthday(bday_tuple, est_time=None):
    today = datetime.datetime.now(datetime.timezone.utc)
    if est_time:
        today = today.astimezone(est_time)

    if bday_tuple is None:
        return False

    month, day = bday_tuple
    return today.month == month and today.day == day

    
@command_handler.Scheduled(time="12:00")
async def birthdays(client):
    from .community import celebrate
    from .families import get_neighborhood_from_user
    import calendar
    from zoneinfo import ZoneInfo

    guild = client.get_guild(FF.guild)
    if guild is None:
        return

    eastern = ZoneInfo("America/New_York")
    est_time = datetime.datetime.now(eastern)
    current_time_utc = est_time.timestamp()
    tag_duration = 90 * 24 * 60 * 60

    def is_last_day(dt):
        return (dt + datetime.timedelta(days=1)).day == 1

    def birthday_datetime(year, month, day):
        if month == 2 and day == 29 and not calendar.isleap(year):
            day = 28
        return datetime.datetime(year, month, day, tzinfo=eastern)

    birthdays_channel = await guild.fetch_channel(1392147228684058644)
    council_role = guild.get_role(648188387836166168)
    general_channel = await guild.fetch_channel(648223397205114910)
    this_month_birthdays = []
    today_bdays = []
    today_council_bdays = []
    seen_users = set()

    async for message in birthdays_channel.history(limit=None, oldest_first=False):
        bday = normalize_birthday(message.content)
        if not bday:
            await message.add_reaction("🤷‍♂️")
            await message.add_reaction("❌")
            continue

        month, day = bday
        try:
            datetime.date(2000, month, day)
            birthday_this_year = birthday_datetime(est_time.year, month, day)
        except (TypeError, ValueError):
            await message.add_reaction("🤷‍♂️")
            await message.add_reaction("❌")
            continue

        user_id = message.author.id
        if user_id in seen_users:
            continue
        seen_users.add(user_id)

        if birthday_this_year.date() == est_time.date():
            member = guild.get_member(user_id)
            if member is None:
                member = await guild.fetch_member(user_id)
            if council_role is not None and council_role in member.roles:
                today_council_bdays.append(user_id)
            else:
                today_bdays.append(user_id)

        if is_last_day(est_time) and month == est_time.month:
            this_month_birthdays.append((user_id, bday))

        # Keep late-year birthdays eligible during the following year.
        most_recent_birthday = birthday_this_year
        if most_recent_birthday > est_time:
            most_recent_birthday = birthday_datetime(est_time.year - 1, month, day)

        timestamp = most_recent_birthday.timestamp()
        expires_at = timestamp + tag_duration
        if not timestamp <= current_time_utc < expires_at:
            continue

        neighbor = Neighbor(user_id, guild.id)
        if not neighbor.get_item_of_name("Birthday tag"):
            item = Item("Birthday tag", "event_emoji", expires_at, emoji="🎂", display="None")
            neighbor.bestow_item(item)

    if today_bdays:
        for bday in today_bdays:
            member = await guild.fetch_member(bday)
            
            nh = (get_neighborhood_from_user(member) or "").lower()
            nh_role = None;
            
            if nh == "ffp":
                nh_role = 1024052938752151552;
            elif nh == "ff":
                nh_role = 656112994392080384;
            elif nh == "ffj":
                nh_role = 689928709683150909;
            elif nh == "ffj2":
                nh_role = 1334660124639236267;
            elif nh == "ffg":
                nh_role = 1173325157767589988;
            elif nh == "ffc":
                nh_role = 1342329111359656008
            elif nh == "ffr":
                nh_role = 1034248720058945577
                
            if nh_role:
                await general_channel.send(f"<@&{nh_role}> it's our neighbor's birthday!")
                
            else:
                await general_channel.send("It's our friend's birthday!")
                
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
        
        await trading_channel.send("**Low on barn stock?**\nThe Council does not currently keep stock of in-game items for trading, but it may be able to take orders in advance for certain items (basics like dairy, sugar, fish, or food items like cakes or sushi) and will trade them for BEMs often at **better than market** prices.\nOpen a ticket to see if we can do what you need: <#1033207181857800242>")
        await general.send("**Low on barn stock?**\nThe Council can help. \n\n Check out <#1409602006712062022>")

    
    
async def derby_reminder(client, guild, est_time):
    from .community import gif, meme
    pro = await guild.fetch_channel(1101572607372951694)
    main = await guild.fetch_channel(1062523480739938324)
    juniors = [await guild.fetch_channel(x) for x in [1062523541691584522, 1334660540294893609]]
    garden = await guild.fetch_channel(1177325611266605157)
    carnival = await guild.fetch_channel(1342333687429070918)
    targets = []
    if est_time.hour == 8 and est_time.minute == 0 and est_time.weekday() == 5:
        targets.append(await pro.send("Hey gang! It's Saturday and this is your Check-In reminder! If you're not done with derby yet, please post a status update and plan in this chat by this time tomorrow! <@&1024052938752151552>\nWe got this!"))
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 6:
        targets.append(await main.send("Hey gang! It's Sunday! We should be wrapping things up with derby. Let your neighbors know if you need help!\nYou may want to check in game that your tasks are done.\nAll non diamond tasks! <@&656112994392080384>\nWe got this!"))
        targets.append(await juniors[0].send("Hey gang! It's Sunday! We should be wrapping things up with derby. Let your neighbors know if you need help!\nYou may want to check in game that your tasks are done.\nIf you need help calculating your requirement, let the leaders know. <@&689928709683150909>\nWe got this!"))
        targets.append(await juniors[1].send("Hey gang! It's Sunday! We should be wrapping things up with derby. Let your neighbors know if you need help!\nYou may want to check in game that your tasks are done.\nIf you need help calculating your requirement, let the leaders know. <@&1334660124639236267>\nWe got this!"))
        targets.append(await garden.send("Hey gang! It's Sunday! Check to make sure you've got 600 points done in derby for the week <@&1173325157767589988>\nWe got this!"))
   
    if est_time.hour == 12 and est_time.minute == 0 and est_time.weekday() == 5:
        targets.append(await carnival.send("Hey Carnies! It's Saturday! Just a little reminder (again) to submit your screenshot for the week. <@&1342329111359656008>\nWe got this!"))

    for target in targets:
        if chance(3):
            new_context = Context(target)
            cmd_msg = await new_context.send("$meme");
            await meme(Neighbor(691338084444274728), Context(cmd_msg))
        else:
            new_context = Context(target)
            gif_type = random.choice(["", "let's do it", "you got this", "team work", "derby", "race", "let's go", "good luck", "strong", "I believe in you"])
            cmd_msg = await new_context.send(f"$gif {gif_type}");
            await gif(Neighbor(691338084444274728), Context(cmd_msg))


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

        
async def main_reminders(client, guild, est_time):
    if est_time.hour == 16 and est_time.minute == 0 and est_time.weekday() == 4:
        main_chat_id = 1490688573836623994
        main_chat = await guild.fetch_channel(main_chat_id)
        await main_chat.send("Remember to post your personal task log! Logs would be due in 4 hours for A&B derby lottery prize qualification in our Pro Neighborhood! <@&656112994392080384> @everyone")
        
    if est_time.hour == 0 and est_time.minute == 0 and est_time.weekday() == 0:
        main_chat_id = 1490688573836623994
        main_chat = await guild.fetch_channel(main_chat_id)
        await main_chat.send("Final reminder to post your personal task logs! (Also derby ends in 4 hours make sure your tasks are done) <@&656112994392080384> @everyone")


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

async def compliance(client, guild, est_time):
    if est_time.hour == 12 and est_time.minute == 40 and est_time.weekday() == 1:
        compliance_chat_id = 1257136669660811284
        compliance = await guild.fetch_channel(compliance_chat_id)

        await compliance.send(
            "Hello! <@&1257138773603647538>! I have chosen the below tasks at random to be completed this week. "
            "Please, ensure they are done, address issues, and post results here."
        )

        NH_roles = ["FFP", "FFM", "FFJ", "FFG", "FFC"]
        Family_roles = ["Fox", "Donkey", "Penguin", "Cheetah", "Bunny", "Hippo", "Giraffe"]
        
        task_templates = [
            *[
                "**{NH} HK Log FORMAT Grading** -- Please grade the most recent {NH} HK Log on a scale of 5 points.\n\n"
                "• Dock 1 point for any and each of the following requirements not met: 1) Headlined with derby type & Date of derby's start "
                "2) Points for all players marked 3) Status marked 4) Action marked, separately from status 5) Opt outs listed.\n\n"
                "• Dock .5 points for any and each aspect of the log that hurt a viewer's ability to interpret it. I.e., If something is confusing "
                "or action markings are not detailed enough."
            ] * 7,
            *[
                "**{NH} HK ACCURACY Check** -- Check the most recent {NH} HK log for **accuracy** against the real derby log and in-game neighbors. "
                "1) Are the scores listed correctly? 1) Were the correct people actually kicked or demoted in game? Promoted? "
                "2) Evaluate whether or not passes were given. If there were, valid? If there weren't, valid? "
                "3) Are sufficient notes included?"
            ] * 7,
            *[
                "**{NH} Role check**! Check that everyone with the {NH} role is in {NH} in-game, and make sure that everyone in the corresponding "
                "in-game group has the {NH} role. Are a lot of issues coming up? Remind council about role policies."
            ] * 7,
            *[
                "**{Family} Role check**! Check that everyone with the {Family} role is meant to have it. No one outside of a NH or in Resort should "
                "have it! No one should have two family roles!"
            ] * 7,
            "**Council Role check!** Check that everyone has the correct Rank role, the correct committee Roles, and the correct NH-Council roles.",
            "**Hospitality tasks check!** Make sure that the past week's worth of hospitality tasks have been marked as complete for all NHs and logged in respective threads.",
            "**Reach out to any Council Member** to compliment something they've done recently.",
            "**Find *something* that can be improved or fixed up in any committee**, any process, any system, any Neighborhood, and add it to the Council backburner or bring it up to the Council",
            "**Joinlist check**. Compare the last ~3 weeks of the joinlist with the HK logs. Make sure everyone is listed as they are meant to be.",
            "**Leavelist check**. Compare the last ~3 weeks of the leavelist with the HK logs. Make sure everyone is listed as they are meant to be AND a list is provided for leaving.",
            "**Check to make sure lotteries** were posted for the most recent 4 derbies. Make sure they were done correctly.",
            "**Check the past ~3 weeks of #due-penalties**. Anyone overdue? Any penalties not listed?",
            "**Look at the past week of recruitment ads**. Find a way to compliment the recruitment committee, and a way to suggest an improvement. Good variability? Good visuals? Easy to read/look at? **Are invite links working?**",
            "**Look at the past ~3 weeks of TikTok posts**. Make sure there are posts. Find a way to compliment the posters, and a way to suggest an improvement.",
            *["**Resolve any un'check'ed tickets** from the past ~3 weeks in <#1033544493728809000>."] * 5,
            "**Check that there are NH-chat announcements** for each Neighborhood posted for this week.",
            "**Pick out the best NH-chat announcement posted this week**, and make an example out of it in Council chat. 'Best' may include: intro to upcoming derby, review of previous derby, introduction of new neighbors, and perhaps some endearing, community engaged quality",
            "**Check that two Council meetings** -- once voice and one chat -- are occuring each month. Begin scheduling if needed.",
            "**Pick out the best ad posted this week** and make an expample of it for the recruitment commmittee.",
            "**Check in with 3 committee chairs** to ask what they need to improve the function or experience of their committee. Raise the matter to Council.",
            "**Red tide!** (Tell Lincoln)",
            "**Pick one thing off the Council backburner** to complete",
            "**Ask 3 committee chairs if there is a good balance of workload** between members. If not, see to it that the issue is resolved.",
            "**Double check that HK committees are keeping up on people who are opted out long term**. Maybe point out anyone who's at 4 weeks or more.",
            "**Ping each Rank role separately in different messages** (1 - 2 - 3) and remind them to / ask if they have gone through their rank's instructions. Link the #council-rank-instructions channel!",
            "**Audit #meet-the-councill** checking that 1) All members are represented 2) all term end dates are correct (determine last term-start date, add # of months for their rank to get term end)",
            "Hospitality help: **Post a pet pic** to #pet-pics if you have one and reply to someone else's post",
            "Hospitality help: **Post an irl pic** to #irl-pics and reply to someone else's post",
            "Hospitality help: **Post a note of appreciation** in #notes-of-appreciation for any one neighbor; DM any one council member to ask them to do the same for a different neighbor",
            "Hospitality help: **Hype up every family!** Post something in each family chat & ping them all to fire up some excitement or drama",
            "**Think up something to ask the advisory boards about**, or just ping them to check in and see what they think about the state of their neighborhood. Engage them in some way!",
            "**Think outside the box!** What's one thing that can improve Council life? DM your idea to Theresa.",
            "**The Discord server is a mess,** think of one idea to clean things up. If it's simple enough go ahead and do it; else ask in council chat if others would be okay with it."
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


@command_handler.Loop(minutes = 5, desc = "The rainbow role color is changed to a random color.")
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

@command_handler.Loop(days = 1, desc = "Takes away rss roles if necessary")
async def role_mgmt(client):
    from .members import set_roles
    guild = client.get_guild(FF.guild);
    for member in guild.members:
        await set_roles(member, guild);


@command_handler.Loop(hours = 8, desc = "Nick management")
async def nick_mgmt(client):
    from .members import set_nick
    guild = client.get_guild(FF.guild);
    async for member in guild.fetch_members():
        try:
            await set_nick(member, guild)
        except:
            pass



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

