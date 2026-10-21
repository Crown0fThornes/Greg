"""Events commands and their supporting helpers."""

from .common import *
active_expectations = [];



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

        
            
        


@command_handler.Uncontested(type = "REACTION", desc = "Market", generic = True)
async def farmers_market_reaction(context: Context):
    from .experience import inc_xp
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

    

@command_handler.Uncontested(type="MESSAGE")
async def family_event(context: Context):
    if context.channel.id == 1402734412793122919:
        channel = await context.guild.fetch_channel(1403141598300082317);
        await channel.send(f"{context.author.id}: {context.message.content}")

