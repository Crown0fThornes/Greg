"""Administration commands and their supporting helpers."""

from .common import *
        
@command_handler.Command(access_type=AccessType.DEVELOPER)
async def april_fools(activator: Neighbor, context: Context):
    
    with open("lookups/emojis.txt", "r", encoding="utf-8") as f:
        emojis = f.read()
        
    emoji_list = emojis.split()
    
    async for member in context.guild.fetch_members():
        neighbor = Neighbor(member.id, context.guild.id)
        neighbor.expire_items()
        
        if neighbor.get_item_of_name("April Fools"):
                continue;
        item = Item("April Fools", "event_emoji", time.time() + 2592000, emoji=random.choice(emoji_list), display="True")
        neighbor.bestow_item(item);
        
        while valentines_item := neighbor.get_item_of_name("Valentine's Heart"):
            neighbor.vacate_item(valentines_item);

    
@command_handler.Command(access_type=AccessType.DEVELOPER)
async def test(activator: Neighbor, context: Context):
    await context.send("Testing, 1 2, testing!", reply=True)


@command_handler.Uncontested(type = "MESSAGE", desc = "If a message contains the word greg, Greg will react with an emoji", priority = 2, generic = True)
async def greg_react(context: Context):
    from .community import gif, meme
    from .experience import special_reaction
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


@command_handler.Command(AccessType.PRIVILEGED)
async def update_reaction_roles(activator: Neighbor, context: Context):
    guild = context.guild
    role_get_channel = await guild.fetch_channel(827632354365014036)
    role_set_channel = await guild.fetch_channel(1531039785047687299)
    
    async for message in role_set_channel.history(limit=None):
        message_id, emoji, role_id = message.content.split()
        
        set_message = await role_get_channel.fetch_message(int(message_id))
        
        for reaction in set_message.reactions:
            if str(reaction.emoji) == str(emoji):
                user_ids = [user.id async for user in reaction.users(limit=None)]
                break
            
        role = guild.get_role(int(role_id))
        for user_id in user_ids:
            try:
                member = await guild.fetch_member(user_id)
            except:
                continue;
            await member.add_roles(role, reason="reaction role")
            
    await context.send("Done!", reply=True);


@command_handler.Command(AccessType.PRIVILEGED, desc = "", generic = True)
async def invis(activator: Neighbor, context: Context):
    role = context.guild.get_role(1084644944431554570);
    new_color = discord.Colour(int('36393f', 16));
    await role.edit(color = new_color)
    1084644944431554570

        
@command_handler.Command(AccessType.DEVELOPER, desc = "This is a test of sync")
async def run(activator: Neighbor, context: Context):
    await context.send("Works!", reply = True);



@command_handler.Command(AccessType.PRIVILEGED, desc = "Changes the prefix for Greg's commands.")
async def prefix(activator: Neighbor, context: Context, new = ""):
    old = command_handler.Command.prefix;
    command_handler.Command.set_prefix(new);
    # print("changin prefix");
    await context.send(f"Wow! My prefix has been changed from `{old}` to `{new}`\n*Members should now use `{new}help` instead of `{old}help` to access the help command, for example.*")


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

