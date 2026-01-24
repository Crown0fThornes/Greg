fNeighbors_names = ["data/neighbors0.txt", "data/neighbors1.txt", "data/neighbors2.txt", "data/neighbors3.txt", "data/neighbors4.txt", "data/neighbors5.txt", "data/neighbors6.txt", "data/neighbors7.txt", "data/neighbors8.txt", "data/neighbors9.txt"]
fOriginalNeighbors_name = "data/neighbors.txt";
fExpectations_name = "data/expectations.txt";
fReminders_name = "data/reminders.txt";
fGiveaways_name = "data/giveaways.txt";
fPolls_name = "data/polls.txt";
fOffers_name = "data/offers.txt";

from datetime import timedelta
import time
import difflib

class Neighbor:
    """
    This new version of the Neighbor class allows for compatiability with the old format with relatively few issues,
    while also providing more secure updates to the neighbors.txt data files.
    The secure_sync wrapper pulls a Neighbor's most recent data, runs the wrapped function,
    and pushes the updated Neighbor back to the text file. This ensures that we don't have to worry
    about pulling or pushing a Neighbor when updating it outside of this class.
    
    A Neighbor object, perhaps instantiated with `neighbor = Neighbor(691338084444274728)`, essentially
    acts as a link between a discord member and their information stored in the neighbors text files.
    Functions can then be run on this Neighbor, `neighbor.increment_XP()`, and the necessary file updates are
    automatically made for us. Notably, this method means that most-recent data is not stored "on-site" of a Neighbor object;
    getters must be used. If this must be avoided, i.e. to directly set a Neighbor's xp, use the method below.
    
    
    When updating or accessing several Neighbors at once, it can be useful to use 
    read_all_neighbors() and write_all_neighbors() in conjunction with one another. 
    First, use read_all_neighbors() to obtain a list of all neighbors and their information. 
    After any/all edits to these objects that need to be saved, use write_all_neighbors() and pass it a list of all of the 
    Neighbor objects. The Neighbor objects returned by read_all_neighbors() will not automatically have edits saved to the data files.
    The advantages of this method include: fewer data-file updates when editing many Neighbors at once, and the ability to alter 
    the order in which the Neighbors appear in the file. 
    Another use of read_all_neighbors(), is to get a list of all Neighbor IDs that can be used to instantiate a list of "regular" Neighbor
    objects. In this case it would be unnecessary (apart from unhelpful and potentially unsafe) to use write_all_neighbors().
    As an example:
    neighbor_ids = [neighbor.ID for neighbor in Neighbor.read_all_neighbors()]
    for id in neighbor_id:
        cur = Neighbor(id);
        #act on cur object
    #no need to write all here
    """
    def __init__(self, id: int = 0, family: int = None, link = True):
        """
        A Neighbor is constructed with an ID. The Neighbor class deals with the rest.
        A Neighbor initated with an ID of 0 is understood to be a "dud" that doesn't get saved
        
        When the `link` parameter is False, secure_sync() will not attempt to update the neighbors text files with
        recent changes. Proceed with caution.
        """
        
        self.ID = id;
        self.family = family;
        self.XP = None;
        self.legacyXP = None;
        self.inventory = None;
        self.secure = link;
    
    def __str__(self):
        """
        Returns a string representation of the Neighbor object.
        """
        return f"{self.ID}: {self.XP}";

    def copy(self, to_copy):
        """
        Copies info from a Neighbor to_copy, to self.
        """
        self.family = to_copy.family;
        if self.family == 0:
            self.family = 647883751853916162;
        elif self.family == "0":
            self.family = 647883751853916162;
        self.XP = to_copy.XP;
        self.legacyXP = to_copy.legacyXP;
        self.inventory = to_copy.inventory;

    def clean(self):
        """
        Cleans a Neighbor object of all info other than ID.
        """
        self.family = None;
        self.XP = None;
        self.legacyXP = None;
        self.inventory = None;

    def encode(self):
        """
        Encodes a Neighbor object into String format.
        """
        res = str(self.ID) + ":";
        res = res + str(self.family if not self.family is None else 0) + ":";
        res = res + str(self.XP if not self.XP is None else 0) + ":";
        res = res + str(self.legacyXP if not self.legacyXP is None else 0) + ":";
        if not self.inventory is None:
            for item in self.inventory:
                res = res + item.encode() + ":";
        return res;
        
    def decode(data: str):
        """
        Decodes a Neighbor object from String format.
        """
        fields = data.split(":");
        res = Neighbor(int(fields[0]));
        res.family = int(fields[1]);
        res.XP = int(fields[2]);
        res.legacyXP = int(fields[3]);
        res.inventory = [Item.decode(data) for data in fields[4:]];
        return res;

    def appropriate_file(self):
        """
        All Neighbor info is stored in a text file data base using decode, encode, pull, and push.
        To make this process more efficient, Neighbor data is split between 10 files.
        
        All Neighbors with IDs ending in 0, are stored in neighbors0.txt, and so on.
        """
        return fNeighbors_names[self.ID % 10];

    def pull(self):
        """
        A Neighbor's info is pulled from its respesctive data file by searching for its ID in the file and decoding that line of text.
        """
        neighbor = None;
        with open(self.appropriate_file(), "r") as fNeighbors:
            lines = fNeighbors.readlines()
            for line in lines:
                neighbor = Neighbor.decode(line[:-2]);
                if neighbor.ID == self.ID:
                    if neighbor.family == self.family or (neighbor.family == 0 and self.family == 647883751853916162):
                        self.copy(neighbor);
                        break;
        if self.family == "0":
            raise ValueError("Family can't be 0");
        if self.family == 0:
            raise ValueError("Family can't be 0");
        if neighbor is None or not neighbor.ID == self.ID: 
            self.XP = 0;
            self.legacyXP = 0;
            self.inventory = [];
        
    def push(self):
        """
        A Neighbor's info is pushed to its respective data file by searching for and replacing its line using encode.
        """
        neighbors_to_write = [];
        neighbors_to_write.append(self);
        with open(self.appropriate_file(), "r") as fNeighbors:
            lines = fNeighbors.readlines();
            for line in lines:
                neighbor = Neighbor.decode(line[:-2]);
                if neighbor.ID == self.ID and ((neighbor.family == self.family) or (neighbor.family == 0 and self.family == 647883751853916162)):
                    continue;
                else:
                    neighbors_to_write.append(neighbor);
        with open(self.appropriate_file(), "w") as fNeighbors:
            for neighbor in neighbors_to_write:
                fNeighbors.write(neighbor.encode() + "\n");     
    def read_all_neighbors():
        """
        Pulls info for all saved Neighbors from every text file and returns a list.
        This function bypasses the secure_sync wrapper, so it should always be used in conjunction with
        write_all_neighbors after all edits are done being made, etc."""
        neighbors = [];
        for file in fNeighbors_names:
            with open(file, "r") as fNeighbors_cur:
                for line in fNeighbors_cur:
                    cur = Neighbor(int(line.split(":")[0]), int(line.split(":")[1]), False);
                    if cur.family == 0:
                        cur.family = 647883751853916162;
                    elif cur.family == "0":
                        cur.family = 647883751853916162;
                    cur.pull();
                    neighbors.append(cur);
        return neighbors;
        
    def write_all_neighbors(neighbors):
        """
        Pushes a list of Neighbors to the 10 text files.
        This function bypasses the secure_sync wrapper, just like read_all_neighbors.
        Whenever read_all_neighbors is called, this function should be called after any edits are made
        if those edits should need to be saved.
        """
        for fNeighbors_name in fNeighbors_names:
            with open(fNeighbors_name, "w") as fNeighbors:
                 fNeighbors.write("");
        for neighbor in neighbors:
            neighbor.push();

    def get_XP_for_level(target):
        total = 0;
        for i in range(target + 1):
            total += int((i ** 2.4) + (i * 70));
        return total;

    def get_level_for_XP(target):
        XP = target;
        level = 1;
        while XP > 0:
            XP -= int((level ** 2.4) + (level * 70));
            level += 1;
        return level - 1;

    def secure_sync():
        """
        The secure_sync() decorator wraps every Neighbor method from here on out.
        The goal of this decorator is to ensure data consistency and ease of use.
        With the help of secure_sync(), no data is kept "on site" of a Neighbor object to avoid accessing information
        that may not be up to date.
        All Neighbor info is pulled before a method is run, then immediately pushed thereafter. 
        Exceptions apply.    
        """
        def wrapper(func):
            def wrapped_func(self, *args, **kwargs):
                if self.secure == False:
                    return func(self, *args, **kwargs);
                Neighbor.pull(self);
                # print("Before func: " + str(self.XP));
                res = func(self, *args, **kwargs);
                # print("After func: " + str(self.XP));
                Neighbor.push(self)
                return res;
            return wrapped_func
        return wrapper

    @secure_sync()
    def get_family(self):
        """
        Since data is not kept 'on-site' of a Neighbor object, this method can be used to access a Neighbor's family.
        """
        return self.family;

    @secure_sync()
    def get_XP(self):
        """
        Since data is not kept 'on-site' of a Neighbor object, this method can be used to access a Neighbor's XP count.
        """
        return self.XP;

    @secure_sync()
    def get_legacyXP(self):
        """
        Since data is not kept 'on-site' of a Neighbor object, this method can be used to access a Neighbor's legacy XP count.
        """
        return self.legacyXP;
    
    @secure_sync()
    def get_inventory(self):
        """
        Since data is not kept 'on-site' of a Neighbor object, this method can be used to access a Neighbor's inventory.
        """
        return self.inventory;
    
    @secure_sync()
    def get_level(self):
        """
        Use Neighbor's XP count to calculate their level
        """
        temp = self.XP;
        c = 1;

        while (True):
            temp -= int((c ** 2.4) + (c * 70));
            # temp -= int((c  ** 2.5) + (c * (c + 100)));
            if (temp <= 0):
                return c - 1;
            c += 1;
            
    @secure_sync()
    def get_legacy_level(self):
        """
        Use Neighbor's legacy XP count to calculate their legacy level
        """
        temp = self.legacyXP;
        c = 1;

        while (True):
            temp -= int((c ** 2.4) + (c * 70));
            # temp -= int((c  ** 2.5) + (c * (c + 100)));
            if (temp <= 0):
                return c - 1;
            c += 1;
    
    @secure_sync()
    def get_XP_for_next_level(self):
        return Neighbor.get_XP_for_level(self.get_level() + 1) - self.XP;
    
    @secure_sync()
    def increase_XP(self, xp: int):
        """
        Increases a neighbor's xp by xp
        """
        self.XP += xp;

    @secure_sync()
    def get_item_of_name(self, name):
        """
        Returns the item in a Neighbor's inventory with a given name. None if the Neighbor doesn't have it.
        """
        if not self.inventory is None:
            for item in self.inventory:
                if item.name == name:
                    return item;
        return None;

    @secure_sync()
    def get_items_of_type(self, type):
        """
        Returns a list of all items in a Neighbor's inventory that match a given type. Empty list if the Neighbor doesn't have any.
        """
        res = [];
        if not self.inventory is None:
            for item in self.inventory:
                if item.type == type:
                    res.append(item);
        return res;
    
    @secure_sync()
    def set_XP(self, xp: int):
        self.XP = xp;
        
    @secure_sync()
    def set_legacy_XP(self, legacy_XP: int):
        self.legacyXP = legacy_XP;
            
    @secure_sync()
    def bestow_item(self, item_to_bestow):
        """
        Adds an Item object to a Neighbor's inventory.
        """
        self.inventory.append(item_to_bestow);
        
    @secure_sync()
    def update_item(self, updated_item):
        """
        Replaces an Item object in a Neighbor's inventory.
        """
        for item in self.inventory:
            if item.name == updated_item.name:
                self.inventory.remove(item);
                self.inventory.append(updated_item);

    @secure_sync()
    def vacate_item(self, item_to_vacate):
        """
        Removes an Item object from a Neighbor's inventory.
        """
        # print("Beg vacate:" + str(self.XP));
        for item in self.inventory:
            if item.name == item_to_vacate.name:
                self.inventory.remove(item);
        # print("End vacate:" + str(self.XP));        
        
    @secure_sync()
    def expire_items(self):
        """
        Vacates all expired Items from a Neighbor's inventory.
        """
        # print("beg exp:" + str(self.XP));
        if not self.inventory is None:
            for item in self.inventory:
                if item.is_expired():
                    self.vacate_item(item);
        # print("End exp" + str(self.XP));

class Item:
    def __init__(self, name: str, type: str, expiration: int, **values):
        self.name = name;
        self.type = type;
        self.expiration = int(expiration);
        self.values = {} if values is None else values;

    def __str__(self):
        if self.expiration == -1:
            res = f"{self.name}; expires never... probably";
        else:
            res = f"{self.name}; expires in {timedelta(seconds=round(self.expiration - time.time()))}";
        # res = self.name + "self.type + "* [expires in: " + str(timedelta(seconds=round(self.expiration - time.time()))) + "]";
        return res;
    
    def is_expired(self):
        return time.time() > self.expiration and self.expiration > 0;

    def encode(self):
        value_concat = "";
        for key, value in self.values.items():
            value_concat += str(key) + "=" + str(value) + ",";
        res = f"{self.name};{self.type};{str(self.expiration)};{value_concat[:-1]}";
        res.replace("'", "");
        res.replace('"', "");
        return res;

    def decode(data: str):
        fields = data.split(";")
        if len(fields) < 4 or fields[3] == "":
            res = Item(fields[0],fields[1],int(fields[2]));
        else:
            res = Item(fields[0],fields[1],int(fields[2]),**{key: str(value) for key, value in (item.split("=") for item in fields[3].split(","))});
        return res;
    
    def get_value(self, attribute: str):
        if attribute in self.values.keys():
            return self.values[attribute];
        
        alternate_candidates = [x for x in self.values.keys() if difflib.SequenceMatcher(None, x, attribute).ratio() > .5];
        raise KeyError(f"Attribute '{attribute}' not present in Item values." + ("" if not alternate_candidates else " Could you have meant: " + str(alternate_candidates) + "?"));
    
    def update_value(self, attribute: str, new_val: str):
        if attribute in self.values.keys():
            self.values[attribute] = new_val;
            return;
        
        alternate_candidates = [x for x in self.values.keys() if difflib.SequenceMatcher(None, x, attribute).ratio() > .5];
        raise KeyError(f"Attribute '{attribute}' not present in Item values." + ("" if not alternate_candidates else " Could you have meant: " + str(alternate_candidates) + "?"));

    def add_value(self, attribute: str, val: str):
        self.values[attribute] = val;
