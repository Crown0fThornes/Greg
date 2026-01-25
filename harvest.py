from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
from custom_types import Neighbor, Item
from responses import ResponsePackage, ResponseRequest
import commands
import time
import random

@command_handler.Command(AccessType.PRIVATE, desc = "Lets a Neighbor harvest crops.", generic = True, active=False)
async def harvest(activator: Neighbor, context: Context, response: ResponsePackage = None):

    if response is None:
        if commands.chance(10):
            await context.send("Did you know? Try `$sell` to sell the entire contents of your silo! Or wait for the farmers market channel to appear for potentially much higher returns.", reply = True);

        activator.expire_items();

        GMO_item = activator.get_item_of_name("GMO Crops");
        
        activator.vacate_item(activator.get_item_of_name("Harvest Cooldown"))

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
        await commands.harvest_xp(context);
    else:
        await context.send("It's a perfect match! Enjoy 1000xp as your reward.");
        await commands.inc_xp(activator, 1000, context);