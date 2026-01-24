import custom_types
import old_neighbor

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
    "bell peper" : 7,
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
}

for i in range(10):
    with open('data/neighbors' + str(i) + ".txt", 'w') as f:
        pass

print("Startin");
for neighbor in old_neighbor.Neighbor.readNeighbors():
    new_neighbor = custom_types.Neighbor(neighbor.ID);
    new_neighbor.set_XP(neighbor.XP);
    new_neighbor.set_legacy_XP(neighbor.legacyXP);
    for item in neighbor.inventory:
        if item.name == "Crops":
            crop_vals = item.values
            new_vals = {};
            for i, key in enumerate(list(crops)):
                new_vals[key] = crop_vals[i]
            give = custom_types.Item("Silo", "silo", -1, **new_vals);
            new_neighbor.bestow_item(give);
            
        if item.name == "Seasonal Tag":
            give = custom_types.Item("Seasonal Tag", item.type, item.expiration, month = item.values[0]);
            new_neighbor.bestow_item(give);
            
        if item.name == "Higher XP I":
            give = custom_types.Item("Higher XP I", "expand", item.expiration, val = 11);
            new_neighbor.bestow_item(give);
            
        if item.name == "Higher XP II":
            give = custom_types.Item("Higher XP II", "expand", item.expiration, val = 12);
            new_neighbor.bestow_item(give);
            
        if item.name == "Family Emoji":
            give = custom_types.Item("*Family Logo Tag* -- Best Seller", "tag", item.expiration);
            new_neighbor.bestow_item(give);
            
        if item.name == "Rainbow Role":
            give = custom_types.Item("*Rainbow Role* -- Best Seller", "role", item.expiration);
            new_neighbor.bestow_item(give);
            
        