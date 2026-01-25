from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
from custom_types import Neighbor, Item
from responses import ResponsePackage, ResponseRequest
import commands
import time
import random

unicodes = {
    0 : "\U00000030\U0000FE0F\U000020E3",
    1 : "\U00000031\U0000FE0F\U000020E3",
    2 : "\U00000032\U0000FE0F\U000020E3",
    3 : "\U00000033\U0000FE0F\U000020E3",
    4 : "\U00000034\U0000FE0F\U000020E3",
    5 : "\U00000035\U0000FE0F\U000020E3",
    6 : "\U00000036\U0000FE0F\U000020E3",
    7 : "\U00000037\U0000FE0F\U000020E3",
    8 : "\U00000038\U0000FE0F\U000020E3",
    9 : "\U00000039\U0000FE0F\U000020E3",
    "boost" : "\U0001F4B0",
    "perk" : "\U0001F5FF",
    "tag" : "\U0001F996",
    "icon" : "\U0001F48E",
    "mail" : "\U00002709",
    "rice" : "\U0001F33E",
    "rainbow" : "\U0001F308",
    "bee" : "\U0001F41D",
    "mushroom" : "\U0001F344",
    "selfie" : "\U0001F933",
    "crown" : "\U0001F451",
    "fox" : "\U0001F98A",
    "snowflake" : "\U00002744",
    "fries" : "\U0001F35F",
    "red_heart" : "\U00002764",
    "blueberry" : "\U0001FAD0",
    "strawberry" : "\U0001F353",
    "coffee" : "\U00002615",
    "t_rex" : "\U0001F996",
    "chicken" : "\U0001F414",
    "coin" : "\U0001FA99",
    "diamond" : "\U0001F48E",
    "crayon" : "\U0001F58D",
    "robot" : "\U0001F916",
    "nails" : "\U0001F485",
    "bank" : "\U0001F3E6",
    "check" : "\U00002705",
    "bot" : "\U0001F916",
    "ant" : "\U0001FAB3",
    "ghost" : "\U0001F47B",
    "back" : "\U000023CF",
    "butterfly" : "\U0001F98B",
    "cheetah" : "\U0001F406",
    "fox" : "\U0001F98A",
    "horse" : "\U0001F40E",
    "puppy" : "\U0001F436",
    "cabinet" : "\U0001F5C4",
    "trophy" : "\U0001F3C6",
    "first" : "\U0001F947",
    "second" : "\U0001F948",
    "third" : "\U0001F949",
    "clover" : "\U00001F34",
    "locked" : "🔒",
    "unlocked" : "🔓",
    "letters" : "\U0001F520",
    "gift" : "\U0001F381",
    "fire" : "\U0001F525",
    "star" : "\U00002B50",
    "anger" : "\U0001F620",
    "bee" : "\U0001F41D",
    "frog" : "\U0001F438",
    "goat" : "\U0001F410",
    "kitten" : "\U0001F408",
    "peacock" : "\U0001F99A",
}

crops = {
   "wheat" : 1,
    "corn" : 1,
    "soybean" : 2,
    "sugarcane" : 3,
    "carrot" : 1,
    "indigo" : 5,
    "pumpkin" : 6,
    "cotton" : 6,
    "chilli pepper" : 7,
    "tomato" : 8,
    "strawberry" : 10,
    "potato" : 7,
    "sesame" : 4,
    "pineapple" : 3,
    "lily" : 5,
    "rice" : 3,
    "lettuce" : 7,
    "garlic" : 3,
    "sunflower" : 5,
    "cabbage" : 3,
    "onion" : 8,
    "cucumber" : 3,
    "beetroot" : 3,
    "bell pepper" : 7,
    "ginger" : 6,
    "tea leaf" : 9,
    "peony" : 7,
    "broccoli" : 4,
    "grapes" : 6,
    "mint" : 6,
    "mushroom" : 2,
    "eggplant" : 3,
    "watermelon" : 8,
    "clay" : 5,
    "chickpea" : 4,
    "apple" : 7,
    "raspberry" : 9,
    "cherry" : 13,
    "blackberry" : 16,
    "cacao" : 16,
    "coffee beans" : 12,
    "olive" : 17,
    "lemon" : 18,
    "orange" : 19,
    "peach" : 20,
    "banana" : 20,
    "passion fruit" : 4,
    "plum" : 16,
    "mango" : 20,
    "coconut" : 21,
    "guava" : 22,
    "pomegranate" : 22,
}

crop_emojis = {
    "wheat" : unicodes["bot"],
    "corn" : "<:Corn:1106752626382618644>",
    "soybean" : "<:Soybean:1106753002615865364>",
    "sugarcane" : "<:Sugarcane:1106753005237325824>",
    "carrot" : "<:Carrot:1106752384778117231>",
    "indigo" : "<:Indigo:1106752701590675496>",
    "pumpkin" : "<:Pumpkin:1106752899184349224>",
    "cotton" : "<:Cotton:1106752627330531338>",
    "chilli pepper" : "<:Chili_Pepper:1106752487865716838>",
    "tomato" : "<:Tomato:1106753009607774330>",
    "strawberry" : "<:Strawberry:1106753004209709219>",
    "potato" : "<:Potato:1106752897959596052>",
    "sesame" : "<:Sesame:1106753001303052399>",
    "pineapple" : "<:Pineapple:1106752893975015494>",
    "lily" : "<:Lily:1106752640945246278>",
    "rice" : "<:Rice:1106752999428198470>",
    "lettuce" : "<:Lettuce:1106752702865744013>",
    "garlic" : "<:Garlic:1106752631298338846>",
    "sunflower" : "<:Sunflower:1106753005983899730>",
    "cabbage" : "<:Cabbage:1106752382039228496>",
    "onion" : "<:Onion:1106752786584055809>",
    "cucumber" : "<:Cucumber:1106752628735627344>",
    "beetroot" : "<:Beetroot:1106752376783786094>",
    "bell pepper" : unicodes["bot"],
    "ginger" : "<:Ginger:1106752632267223060>",
    "tea leaf" : "<:Tea_Leaf:1106753007758082058>",
    "peony" : "<:Peony:1106752791524937758>",
    "broccoli" : "<:Broccoli:1106752380814491689>",
    "grapes" : "<:Grapes:1106752700114280488>",
    "mint" : "<:Mint:1106752782322630756>",
    "mushroom" : "<:Mushroom:1106752783333478511>",
    "eggplant" : "<:Eggplant:1106752630354608158>",
    "watermelon" : unicodes["bot"],
    "clay" : "<:Clay:1106752387135320134>",
    "chickpea" : "<:Chickpea:1106752447692677240>",
    "apple" : "<:Apple:1106752372790788156>",
    "raspberry" : "<:Raspberry:1106752997922439178>",
    "cherry" : "<:Cherry:1106752487010082846>",
    "blackberry" : "<:Blackberry:1106752379405213820>",
    "cacao" : "<:Cacao:1106752383612112907>",
    "coffee beans" : "<:Coffee_Bean:1106752625229180959>",
    "olive" : "<:Olive:1106752784906334289>",
    "lemon" : "<:Lemon:1106752639468847142>",
    "orange" : "<:Orange:1106752787615850506>",
    "peach" : "<:Peach:1106752790061137991>",
    "banana" : "<:Banana:1106752375164764200>",
    "passion fruit" : unicodes["bot"],
    "plum" : "<:Plum:1106752793974419456>",
    "mango" : "<:Mango:1106752779793465524>",
    "coconut" : "<:Coconut:1106752623421440001>",
    "guava" : "<:Guava:1106752635656216656>",
    "pomegranate" : "<:Pomegranate:1106752896462237706>",
}

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