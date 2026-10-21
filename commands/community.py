"""Community commands and their supporting helpers."""

from .common import *

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
    from .families import has_role
    if not "<@&1181330910747054211>" in context.message.content:
        return
    
    council_role = context.guild.get_role(648188387836166168)
    if not has_role(context.author, council_role):
        return;
    
    announcements_channel = await context.guild.fetch_channel(648218302321131540)
    link = f"https://discord.com/channels/{context.guild.id}/{context.channel.id}/{context.message.id}"
    first_line = first_line_or_period(context.message.content.replace("<@&1181330910747054211>", ""))
    await announcements_channel.send(f"# {first_line}\n<@{context.author.id}> made an announcement here: {link}\n\n{context.message.content.replace("<@&1181330910747054211>", "")}")

    
@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def add_emoji(activator: Neighbor, context: Context):
    pass


@command_handler.Loop(hours=1)
async def check_emojis(client):
    from .families import has_role
    guild = client.get_guild(FF.guild);
    async for member in guild.fetch_members():
        neighbor = Neighbor(member.id, guild.id)
        role = guild.get_role(1024052938752151552)
        if has_role(member, role):
            if neighbor.get_item_of_name("Maple tag nurture event"):
                continue;
            item = Item("Maple tag nurture event", "event_emoji", time.time() + 21086592, emoji="🍁", display="None")
            neighbor.bestow_item(item);

                       
            
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
    from .members import set_nick
    guild = client.get_guild(FF.guild);
    deco_comp_channel = await guild.fetch_channel(654303369464119316)
       
    LOCAL_UTC_OFFSET = -4  # EDT
    LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=LOCAL_UTC_OFFSET))
    
    news_stand_channel = await guild.fetch_channel(1218041302998974584);    
    
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
        
        if month == 3:
            break;
            
        if month == 4: 
            neighbor = Neighbor(message.author.id, message.guild.id)
            if neighbor.get_item_of_name("Easter Apr deco comp"):
                continue;
            item = Item("Easter Apr deco comp", "event_emoji", time.time() + 21086592, emoji="🐇", display="None")
            neighbor.bestow_item(item)  
        
        if month == 5: 
            neighbor = Neighbor(message.author.id, message.guild.id)
            if neighbor.get_item_of_name("Spring time May deco comp"):
                continue;
            item = Item("Spring time May deco comp", "event_emoji", time.time() + 21086592, emoji="🌷", display="None")
            neighbor.bestow_item(item)  
        
        if month == 6: 
            neighbor = Neighbor(message.author.id, message.guild.id)
            if neighbor.get_item_of_name("Wedding June deco comp"):
                continue;
            item = Item("Wedding June deco comp", "event_emoji", time.time() + 21086592, emoji="💍", display="None")
            neighbor.bestow_item(item)  
        
        if month == 7: 
            neighbor = Neighbor(message.author.id, message.guild.id)
            if neighbor.get_item_of_name("Yee haw July deco comp"):
                continue;
            item = Item("Yee haw July deco comp", "event_emoji", time.time() + 21086592, emoji="🤠", display="None")
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
    from .members import set_nick
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
    
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")

    # try:
    giphy_api_key = os.environ["GIPHY"] 

    if not giphy_api_key:
        await context.send("Darn! The GIPHY API key has not been configured 😕", reply=True)
        return

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
            
    patch = not res;    
    if not res:
        url = "https://api.giphy.com/v2/search"
        params = {
            "q": search_term,
            "key": giphy_api_key,
            "limit": 10,
            "media_filter": "gif",
            "contentfilter": "medium",
        }
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        print(
                            f"GIPHY request failed with status "
                            f"{response.status}: {response_text}"
                        )
                        res = "Darn! Failed to fetch GIFs 😕\nMaybe try again idk"
                    else:
                        data = await response.json()
                        results = data.get("results", [])
                        if not results:
                            res = "Darn! No GIFs found!"
                        else:
                            random_gif = random.choice(results)
                            media_formats = random_gif.get("media_formats", {})
                            gif_data = media_formats.get("gif", {})
                            res = gif_data.get("url")
                            if not res:
                                res = "Darn! That GIF did not have a usable URL 😕"

        except:
            res = "Whelp this is awkward. It didn't work. Try again later?"

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
            "Trust no one!! I recommend purchasing upgraded security for your Silo (which I happen to be selling at `$rss`).\n\n"
            "*According to data gathered in the nearest town o'er, the thief seems to break into 10% of silos each day, taking about one third of the crops in each."
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
            try:
                message = await channel.fetch_message(bestv['id']);
            except:
                message = ""
            res = ""
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
    from .families import get_role_count
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
    
    from .races import IMAGE_EXTS
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


@command_handler.Command(AccessType.PUBLIC, desc = "Find a segment of the Constitution!")
async def constitution(activator: Neighbor, context: Context):
    
    final_answer_msg = await context.send("Reading the constitution...")
    
    import json
    import numpy as np

    from helper_embedding import embed
    
    if not len(context.args) > 0:
        raise CommandArgsError("`$constitution` requires one argument: what to search for in the Constitution")

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

