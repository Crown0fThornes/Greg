from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
from custom_types import Neighbor, Item
from responses import ResponsePackage, ResponseRequest
import commands
import time
import random
import sqlite3
import json

def random_crop_amt(mu: int, highend_of_range: int):
    '''
    Generates a random number of crops to harvest between 1 and high-end,
    with a distribution centered close to mu (tends to be slightly higher than mu due to method used)
    '''
    
    lowend = mu * 2 if mu * 2 < 100 else 100
    mid = mu * 4 if mu * 4 < 100 else 100
    highend = 100;
    
    # 3/6 chance that lowend bucket is chosen (1 - 2mu range; mu average)
    # 2/6 chance that mid bucket is chosen (1-4mu range; 2mu average)
    # 1/6 chance that highend bucket is chosen (1-100 range; 50 average)
    bucket = random.choice([lowend, lowend, lowend, mid, mid, highend]) 
        
    return(random.randint(1, bucket))
        
@command_handler.Command(AccessType.DEVELOPER, desc = "give yourself an item")
async def give(activator: Neighbor, context: Context):
    if int(context.args[2]) == -1:
        expiration = -1
    else:
        expiration = time.time() + int(context.args[2])
    
    item = Item(context.args[0], context.args[1], expiration)
    activator.bestow_item(Item())

@command_handler.Command(AccessType.DEVELOPER, desc = "Clear inventory")
async def clear(activator: Neighbor, context: Context):
    while (item := activator.get_item_of_name(context.args[0])):
        activator.vacate_item(item)
        
    for item in activator.get_items_of_type(context.args[0]):
        activator.vacate_item(item);

@command_handler.Command(AccessType.PRIVATE, desc = "Plant crops to harvest later!")
async def plant(activator: Neighbor, context: Context):
    
    activator.expire_items();
    
    planted = activator.get_items_of_type("crops planted");
    has_expanded_fields = activator.get_item_of_name("Expanded Fields")
    
    if len(planted) == 0 or has_expanded_fields and len(planted) < 3:
        item = Item(f"Crops Planted! {len(planted)}", "crops planted", -1,ready=str(time.time() + 0))
        activator.bestow_item(item);
        await context.send("Your crops are planted! Come back in one hour to $harvest!", reply=True)
    else:
        await context.send("Hmm... short term memory loss? You've already got crops planted.",reply=True)
        for planted_item in planted:
            expiration = float(planted_item.get_value("ready"))
            if time.time() > expiration:
                await context.send("In fact, you've got crops ready to $harvest!")
                break
        

@command_handler.Command(AccessType.PRIVATE, desc = "Lets a Neighbor harvest crops.", generic = True, active=False)
async def harvest(activator: Neighbor, context: Context, response: ResponsePackage = None):
    
    with open("lookups/harvest_json/crop_info_completed.json", "r") as f:
        crop_info = json.load(f)

    activator.expire_items();
    planted = activator.get_items_of_type("crops planted");
    
    if not planted:
        await context.send("You can't reap what you sow, if you don't sow first buddy. Use $plant to plant some crops.")
        return
    for planted_item in planted:
        expiration = float(planted_item.get_value("ready"))
        print(expiration);
        print(time.time());
        if time.time() > expiration:
            activator.vacate_item(planted_item)
            crop_to_harvest = random.choice(list(crop_info.keys()));
            rarity_score = crop_info[crop_to_harvest]["xp"]
            # mu = round(50 / rarity_score)
            
            # if activator.get_item_of_name("GMO Crops"):
            #     amt_to_harvest = random_crop_amt(4 * mu, 400)
            # else:
            #     amt_to_harvest = random_crop_amt(2*mu, 200);
            
            amt_to_harvest = random.randint(1, 100);
                
            res = await context.send(f"Wohoo! You harvested {amt_to_harvest} {crop_to_harvest}",reply=True);
            await res.add_reaction(crop_info[crop_to_harvest]["emoji"])
        
        else:
            await context.send("Patience is key! Crops don't grow overnight you know! Well...", reply=True)
            

    # if response is None:
    #     if commands.chance(10):
    #         await context.send("Did you know? Try `$sell` to sell the entire contents of your silo! Or wait for the farmers market channel to appear for potentially much higher returns.", reply = True);

    #     activator.expire_items();

    #     GMO_item = activator.get_item_of_name("GMO Crops");
        
    #     activator.vacate_item(activator.get_item_of_name("Harvest Cooldown"))

    #     if activator.get_item_of_name("Harvest Cooldown") and not activator.get_item_of_name("HarvestNow(TM) Fertilizer"):

    #         await context.send(f"Whoops! You've already harvested in the past hour. Crops don't grow overnight you know! Well...");
    #         return;
    #     elif activator.get_item_of_name("Harvest Cooldown") and activator.get_item_of_name("HarvestNow(TM) Fertilizer"):
    #         await context.send("Your HarvestNow(TM) Fertilizer is being used now.")
    #         harvest_block_item = activator.get_item_of_name("Harvest Cooldown");
    #         fertilizer_item = activator.get_item_of_name("HarvestNow(TM) Fertilizer");
    #         activator.vacate_item(harvest_block_item);
    #         activator.vacate_item(fertilizer_item);
    #         activator.bestow_item(Item("HarvestNowBlock", "block", time.time() + 3600));
    #     cur = time.time();
    #     # print(activator.get_inventory());
    #     new_bock = Item("Harvest Cooldown", "harvest", (cur + 3600));
    #     activator.bestow_item(new_bock);
    #     # print(activator.get_inventory());

    #     silo_item = activator.get_item_of_name("Silo");
    #     if silo_item is None:
    #         current_silo = {name: 0 for name, val in crops.items()};
    #         temp = Item("Silo", "silo", -1, **current_silo);
    #         activator.bestow_item(temp);

    #     else:
    #         old_silo = {name: int(val) for name, val in silo_item.values.items()}
    #         old_values = list(old_silo.values());

    #         current_silo = {name: 0 for name, val in crops.items()};
    #         for i, key in enumerate(current_silo.keys()):
    #             if i < len(old_values):
    #                 current_silo[key] = old_values[i]


    #     list_crops = list(crops.items());
    #     list_with_probabilities = [];
    #     for crop in list_crops:
    #         for i in range(int((50 - crop[1]) ** 1.5)):
    #             list_with_probabilities.append(crop);

    #     to_harvest, xp_per_harvest = random.choice(list_with_probabilities);

    #     amt_to_harvest = random.randint(1, 100);

    #     if GMO_item:
    #         amt_to_harvest *= 2;
    #         if amt_to_harvest > 100:
    #             amt_to_harvest -= random.randint(0,100);

    #     current_silo[to_harvest] += amt_to_harvest;


    #     new_silo_item = Item("Silo", "silo", -1, **current_silo);
    #     activator.update_item(new_silo_item)

    #     res = f"Wohoo! You harvested {amt_to_harvest} {to_harvest}"
    #     target = await context.send(res);

    #     random_key = random.choice(list(crop_emojis.keys()))
    #     random_value = crop_emojis[random_key];
    #     await target.add_reaction(random_value);
    #     if to_harvest == random_key:
    #         def key(ctx):
    #             if not ctx.message.id == target.id:
    #                 return False;
    #             if not ctx.emoji.name == random_value:
    #                 return False;
    #             return True;
    #         ResponseRequest(harvest, "crop", "REACTION", context, Context(target), key);
    #     await commands.harvest_xp(context);
    # else:
    #     await context.send("It's a perfect match! Enjoy 1000xp as your reward.");
    #     await commands.inc_xp(activator, 1000, context);
        
async def update_silo(member_id, crop_to_update, change: int):
    try:
        with sqlite3.connect("silo.db") as conn:
            
            print("Opened")
    except:
        raise ConnectionError("Could not connect to databse")
