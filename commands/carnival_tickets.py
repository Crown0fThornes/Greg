"""Carnival tickets commands and their supporting helpers."""

from .common import *
            
        

@command_handler.Command(AccessType.PUBLIC)
async def tickets_dict(activator: Neighbor, context: Context):
    """
    Builds a dict of {user_id: tickets} for every member in the guild,
    writes results to CSV + TXT, uploads both, logs progress,
    and ignores messages after a fixed UTC cutoff.
    """
    from .carnival import Task, bought_second_set, task_2msg_300chars, task_3msgs, task_just1image
    
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

                        
        

@command_handler.Command(AccessType.DEVELOPER, desc="Find out how many tickets you've earned!")
async def tickets_done(activator: Neighbor, context: Context):
    
    from .carnival import count_tickets, count_tickets2
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

