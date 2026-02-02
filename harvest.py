from math import floor
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
    
    max_fields = 1 if not has_expanded_fields else 3;
    if len(planted) < max_fields:
        for _ in range(len(planted), max_fields):
            item = Item(f"Crops Planted! {len(planted)}", "crops planted", -1,ready=str(time.time() + 3600))
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
    
    create_silo_table();
    
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
            update_silo(activator.ID,crop_to_harvest,amt_to_harvest)
                
            res = await context.send(f"Wohoo! You harvested {amt_to_harvest} {crop_to_harvest}",reply=True);
            await res.add_reaction(crop_info[crop_to_harvest]["emoji"])
        
        else:
            await context.send("Patience is key! Crops don't grow overnight you know! Well...", reply=True)
        
@command_handler.Command(access_type=AccessType.PRIVATE, desc="View my silo!")
async def silo(activator: Neighbor, context: Context):
    try:
        create_silo_table();
        
        with sqlite3.connect("data/silo.db") as conn:            
            conn.row_factory = sqlite3.Row;
            cursor = conn.cursor();
            
            cursor.execute("SELECT * FROM silo WHERE neighbor_ID = ?", (activator.ID,))
            row = cursor.fetchone()
            if row:
                record = dict(row);
                
                output = "Your silo: \n"
                for crop_count in list(record.items())[1:]:
                    if crop_count[1] < 3:
                        continue;
                    else:
                        output += f"> {crop_count[0]}: {crop_count[1]}\n"
            else:     
                output = "Your silo: \n"
                output += f"> Empty!\n"
                output += f"Try `$plant`ing some crops to fill your silo! & `$info harvest` to learn more!"
            target = Context(await context.send(output, reply=True));
            
            if activator.get_item_of_name("Silo Security Lvl 1"):
                await target.react("<:strongman2:1248819697747497042>")
                ResponseRequest(strongman,"strongman","REACTION",context,target)
            
            # sorted_crops_by_count = sorted(list(record.items()),key=lambda x: x[1])
    except ConnectionError:
        raise ConnectionError("Could not connect to databse")
    
async def strongman(activator: Neighbor, context: Context, responsePackage: ResponsePackage):
    await context.send("The Strongman is guarding this silo from The Silo Thief! <:strongman2:1248819697747497042>")
    
        
def update_silo(neighbor_ID, crop_to_update, change: int):
    try:
        create_silo_table();
        
        with sqlite3.connect("data/silo.db") as conn:
            cursor = conn.cursor();
            
            cursor.execute("INSERT OR IGNORE INTO silo (neighbor_ID) VALUES (?)", (neighbor_ID,));
            
            cursor.execute(f"UPDATE silo SET \"{crop_to_update}\" = \"{crop_to_update}\" + ? WHERE neighbor_ID = ?", (change,neighbor_ID,))
            
    except:
        raise ConnectionError("Could not connect to databse")
    
def check_silo(neighbor_ID, crop_to_check):
    try:
        create_silo_table();
        
        with sqlite3.connect("data/silo.db") as conn:
            cursor = conn.cursor();
            
            cursor.execute(f'SELECT "{crop_to_check}" FROM silo WHERE neighbor_ID = ?', (neighbor_ID,))
            row = cursor.fetchone()

            return row[0] if row is not None else 0;      
    except:
        raise ConnectionError("Could not connect to databse")
    

def create_silo_table():
    with open("lookups/harvest_json/crop_info_completed.json", "r") as f:
        crop_info = json.load(f)
    
    crop_names = list(crop_info.keys());
    
    try:
        with sqlite3.connect("data/silo.db") as conn:
            print("Opened")
            cursor = conn.cursor();
            
            sql_statement = """CREATE TABLE IF NOT EXISTS silo (\nneighbor_ID INTEGER PRIMARY KEY"""
            
            for crop in crop_names:
                sql_statement += ",\n"
                sql_statement += f"\"{crop}\" INTEGER NOT NULL DEFAULT 0"
                
            sql_statement += "\n);"
            
            cursor.execute(sql_statement)
    except:
        raise ConnectionError("Could not connect to databse")
    
    
# @command_handler.Command(access_type=AccessType.DEVELOPER)
# @command_handler.Scheduled("20:00", day_of_week=5)
@command_handler.Command(access_type=AccessType.DEVELOPER)
async def open_farmers_market(activator, context):
    
    guild = context.guild;
    # guild = client.get_guild(647883751853916162)
    town_square = await guild.fetch_channel(648223363600351263);
    # guild = context.guild;
    
    market_channel = await guild.create_text_channel('🚜farmers-market', category=town_square)
    await market_channel.send("# 🚜 Welcome to the farmers market! 🌾")
    await market_channel.send("Here, farmers are buying crops you've `$harvest`ed in exchange for XP. The farmers market comes to town every sunday trading 5 select crops, so don't miss out.")
    await market_channel.send("Look below at the offerings and react accoringly to sell your stock if you like the price. Partials not accepted, but you can make the same sale multiple times.")
    await market_channel.send("Not sure what you have in stock? Check `$silo` in <#784150346397253682>")
    
    with open("lookups/harvest_json/crop_info_completed.json", "r") as f:
        crop_info = json.load(f)
        
    crop_names = list(crop_info.keys())
    crops_demanded = random.sample(crop_names, 5)
    demand_quantity = [random.randint(1,10), random.randint(1,10), random.randint(1,100),random.randint(1,100),random.randint(1,500)]
    demand_price_per_crop = [random.uniform(1,3), random.uniform(1,3),random.uniform(1,5),random.uniform(1,5),random.uniform(1,10)]
    demand_price = [];
    res = ""
    
    market = {
        "market_channel_id": market_channel.id
    }
    
    for i, _ in enumerate(demand_quantity):
        demand_price.append(round(demand_quantity[i] * demand_price_per_crop[i]))
        
        res += f"Offer {i+1}: {demand_quantity[i]} {crops_demanded[i]} for {demand_price[i]}xp\n"
        market[f"Offer {i+1}"] = {
            "crop": crops_demanded[i],
            "quantity": demand_quantity[i],
            "price": demand_price[i]
        }
    
    target = Context(await market_channel.send(res));
    
    market["market_message_id"] = target.message.id;
        
    with open("data/farmers_market.json", "w") as f:
            json.dump(market, f, indent=4)
        
    for crop in crops_demanded:
        await target.react(crop_info[crop]["emoji"])
        
@command_handler.Scheduled("20:00", day_of_week=0)
async def close_farmers_market(client):
    guild = client.get_guild(647883751853916162)
    
    with open("data/farmers_market.json", "r") as f:
        market_info = json.load();
        
    channel_id = market_info["market_channel_id"]
    await guild.delete_channel(channel_id);
    
    
@command_handler.Uncontested(type="REACTION", desc="Grants farmers market trades")
async def sell_at_farmers_market(context: Context):
    with open("lookups/harvest_json/crop_info_completed.json", "r") as f:
        crop_info = json.load(f)
        
    with open("data/farmers_market.json", "r") as f:
        market_info = json.load(f)
        
    intended_channel = market_info["market_channel_id"]
    intended_message = market_info["market_message_id"]
    
    if not context.message.channel.id == intended_channel:
        print("Wrong channel")
        return False;
    
    if not context.message.id == intended_message:
        print("Wrong message")
        return False;
    
    purchase = None
    for i in range(0,5):
        cur_offer = f"Offer {i+1}"
        cur_offer_emoji = crop_info[market_info[cur_offer]["crop"]]["emoji"];
        if str(context.emoji) == cur_offer_emoji:
            purchase = market_info[cur_offer]
            break;
        
    if not purchase: # user selected 1 of 5 offers?
        await context.message.remove_reaction(context.emoji, context.user);
        return False;
    
    crop = purchase["crop"]
    quantity = purchase["quantity"]
    price = purchase["price"]
    
    if check_silo(context.user.id, crop) >= quantity: # user has enough to sell?
        update_silo(context.user.id, crop, -quantity)
        await commands.inc_xp(Neighbor(context.user.id,647883751853916162),price,context)
    
    
    await context.message.remove_reaction(context.emoji, context.user);
    
@command_handler.Scheduled("16:00")
async def silo_thief(client):
    # guild = context.guild;
    guild = client.get_guild(647883751853916162)
    bot_channel = await guild.fetch_channel(784150346397253682);
    try:
        with sqlite3.connect("data/silo.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor();
    
            cursor.execute("SELECT neighbor_ID FROM silo")
            neighbor_ids = [row[0] for row in cursor.fetchall()]
            
            ten_percent = floor(len(neighbor_ids)/10) + 1;
            
            neighbors_to_steal_from = random.sample(neighbor_ids, ten_percent)
            
            for neighbor_id in neighbors_to_steal_from:
                cursor.execute("SELECT * FROM silo WHERE neighbor_ID = ?", (neighbor_id,))
                row = cursor.fetchone()
                record = dict(row);
                del record["neighbor_ID"]
                
                for crop_name, quantity in record.items():
                    if not quantity > 0:
                        continue;
                    neighbor = Neighbor(neighbor_id,647883751853916162);
                    has_security = False;
                    if neighbor.get_item_of_name("Silo Security Lvl 1"):
                        has_security = True;
                    
                    if has_security:
                        quantity_to_take = round(quantity/1.5)
                    else:
                        quantity_to_take = round(quantity/3)
                        
                    
                    update_silo(neighbor_id, crop_name,-quantity_to_take)
                    # taken.append(f"{quantity_to_take} {crop_name}")
                    # cursor.execute(f"UPDATE silo SET \"{crop_name}\" = \"{crop_name}\" + ? WHERE neighbor_ID = ?", (-quantity_to_take,neighbor_id,))
                
                if has_security:
                    await bot_channel.send(f"The thief has come to town and taken 17% of <@{neighbor_id}>'s crops!")
                else:
                    await bot_channel.send(f"The thief has come to town and taken 33% of <@{neighbor_id}>'s crops!")
    except:
        raise ConnectionError("Could not connect to databse")