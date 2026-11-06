fNeighbors_names = ["data/neighbors0.txt", "data/neighbors1.txt", "data/neighbors2.txt", "data/neighbors3.txt", "data/neighbors4.txt", "data/neighbors5.txt", "data/neighbors6.txt", "data/neighbors7.txt", "data/neighbors8.txt", "data/neighbors9.txt"]
fOriginalNeighbors_name = "data/neighbors.txt";
fExpectations_name = "data/expectations.txt";
fReminders_name = "data/reminders.txt";
fGiveaways_name = "data/giveaways.txt";
fPolls_name = "data/polls.txt";
fOffers_name = "data/offers.txt";

from datetime import timedelta
from functools import wraps
from pathlib import Path
from persistence.neighbor_store import get_store
import time
import difflib

_PROJECT_ROOT = Path(__file__).resolve().parent
fNeighbors_names = [str(_PROJECT_ROOT / filename) for filename in fNeighbors_names]
_DEFAULT_GUILD_ID = 647883751853916162


def _guild_id(value):
    value = _DEFAULT_GUILD_ID if value is None or value in (0, "0") else int(value)
    if value <= 0:
        raise ValueError("A Neighbor needs a positive Discord server ID")
    return value


def _text_identity(line):
    try:
        fields = line.split(":", 2)
        return int(fields[0]), _guild_id(fields[1])
    except (ValueError, IndexError):
        return None

class Neighbor:
    """Player record with rolling SQLite migration and legacy text mirrors.

    Linked construction/access enrolls only this user/server pair. SQL is the
    source of truth thereafter. Every successful write also updates the original
    text shard for rollback. Detached objects and text decoding stay in memory;
    bulk reads prefer enrolled SQL rows without importing everybody else.
    """
    def __init__(self, id: int = 0, family: int = None, link=True):
        self.ID = int(id)
        if self.ID < 0:
            raise ValueError("A Neighbor needs a nonnegative Discord user ID")
        self.family = _guild_id(family)
        self.XP = 0
        self.legacyXP = 0
        self.inventory = []
        self.secure = link
        self._sync_depth = 0
        if link and self.ID != 0:
            self.pull()

    
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
        
    @staticmethod
    def decode(data: str):
        """Decode a detached text snapshot; parsing must never migrate a player."""
        fields = data.rstrip("\r\n").split(":")
        while fields and fields[-1] == "":
            fields.pop()
        if len(fields) < 4:
            raise ValueError("Incomplete Neighbor text record")
        result = Neighbor(int(fields[0]), _guild_id(fields[1]), link=False)
        result.XP = int(fields[2])
        result.legacyXP = int(fields[3])
        result.inventory = [Item.decode(value) for value in fields[4:]]
        return result


    def appropriate_file(self):
        """
        All Neighbor info is stored in a text file data base using decode, encode, pull, and push.
        To make this process more efficient, Neighbor data is split between 10 files.
        
        All Neighbors with IDs ending in 0, are stored in neighbors0.txt, and so on.
        """
        return fNeighbors_names[self.ID % 10];

    def _record(self):
        return dict(user_id=self.ID, guild_id=_guild_id(self.family),
                    xp=0 if self.XP is None else self.XP,
                    legacy_xp=0 if self.legacyXP is None else self.legacyXP,
                    items=[dict(item_id=getattr(item, "_sqlite_item_id", None), name=item.name,
                                type=item.type, expiration=item.expiration, values=dict(item.values))
                           for item in (self.inventory or [])])

    def _apply_record(self, record):
        self.family = record["guild_id"]
        self.XP = record["xp"]
        self.legacyXP = record["legacy_xp"]
        self.inventory = []
        for saved in record["items"]:
            item = Item(saved["name"], saved["type"], saved["expiration"], **saved["values"])
            if "awarded_at" not in saved["values"]:
                item.values.pop("awarded_at", None)
            item._sqlite_item_id = saved.get("item_id")
            self.inventory.append(item)

    def _read_text(self):
        path = Path(self.appropriate_file())
        if not path.exists():
            return None
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            if _text_identity(line) != (self.ID, self.family):
                # An unparseable server ID for this user is not an empty record.
                if line.split(":", 1)[0] == str(self.ID) and _text_identity(line) is None:
                    raise ValueError(f"Invalid Neighbor record in {path.name}, line {number}")
                continue
            try:
                return Neighbor.decode(line)._record()
            except (ValueError, IndexError, TypeError) as error:
                raise ValueError(f"Invalid Neighbor record in {path.name}, line {number}") from error
        return None

    def _validated_text_encoding(self):
        # The rollback copy must remain readable by the previous implementation.
        try:
            decoded = Neighbor.decode(self.encode())._record()
            original = self._record()
            for item in decoded["items"]:
                item.pop("item_id", None)
            for item in original["items"]:
                item.pop("item_id", None)
                item["values"] = {str(key): str(value) for key, value in item["values"].items()}
            if decoded != original:
                raise ValueError("Text round trip changed the Neighbor record")
        except (ValueError, IndexError, TypeError) as error:
            raise ValueError("Neighbor data cannot be represented safely in the legacy text backup") from error
        return self.encode()

    def _mirror_text(self, session):
        encoded = self._validated_text_encoding()
        path = Path(self.appropriate_file())
        existing = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
        other_lines = [line for line in existing if _text_identity(line) != (self.ID, self.family)]
        contents = encoded + "\n" + "".join(other_lines)
        session.mirror(path, contents.encode("utf-8"))

    def _pull_in_session(self, session):
        self.family = _guild_id(self.family)
        saved = session.load(self.ID, self.family)
        if saved is None:
            saved = self._read_text()
            if saved is None:
                saved = dict(user_id=self.ID, guild_id=self.family, xp=0, legacy_xp=0, items=[])
            ids = session.save(saved)
            for item, item_id in zip(saved["items"], ids):
                item["item_id"] = item_id
        self._apply_record(saved)
        self._mirror_text(session)

    def _push_in_session(self, session):
        self.family = _guild_id(self.family)
        ids = session.save(self._record())
        for item, item_id in zip(self.inventory or [], ids):
            item._sqlite_item_id = item_id
        self._mirror_text(session)

    def pull(self):
        """Load SQL first, importing only this player's text record if absent."""
        if self.ID == 0:
            return
        with get_store().transaction() as session:
            self._pull_in_session(session)

        
    def push(self):
        """Save SQL and its legacy text mirror together, or text only in rollback mode."""
        if self.ID == 0:
            return
        with get_store().transaction() as session:
            self._push_in_session(session)

    @staticmethod
    def read_all_neighbors():
        """Read detached snapshots, preferring SQL without migrating text-only players."""
        with get_store().transaction() as session:
            neighbors = {}
            sql_records = {}
            for uid, gid in sorted(session.keys()):
                record = Neighbor(uid, gid, link=False)
                record._apply_record(session.load(uid, gid))
                sql_records[(uid, gid)] = record
            for filename in fNeighbors_names:
                path = Path(filename)
                if not path.exists():
                    continue
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    record = sql_records.get(_text_identity(line))
                    if record is None:
                        record = Neighbor.decode(line)
                    if record.ID:
                        neighbors.setdefault((record.ID, record.family), record)
            neighbors.update(sql_records)
            return list(neighbors.values())

        
    @staticmethod
    def write_all_neighbors(neighbors):
        """Replace bulk snapshots; update/delete enrolled rows without eager enrollment."""
        neighbors = [neighbor for neighbor in neighbors if neighbor.ID != 0]
        records = {}
        for neighbor in neighbors:
            neighbor.family = _guild_id(neighbor.family)
            key = (neighbor.ID, neighbor.family)
            if key in records:
                raise ValueError(f"Duplicate Neighbor in bulk write: {key}")
            records[key] = neighbor
        with get_store().transaction() as session:
            enrolled = session.keys()
            for key in enrolled - records.keys():
                session.delete(*key)
            for key, neighbor in records.items():
                if key in enrolled:
                    ids = session.save(neighbor._record())
                    for item, item_id in zip(neighbor.inventory or [], ids):
                        item._sqlite_item_id = item_id
            shards = {str(Path(path)): [] for path in fNeighbors_names}
            for neighbor in neighbors:
                shards[str(Path(neighbor.appropriate_file()))].append(neighbor._validated_text_encoding() + "\n")
            for filename, contents in shards.items():
                session.mirror(filename, "".join(contents).encode("utf-8"))


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
        """Serialize a linked read/modify/write; nested methods share its snapshot."""
        def wrapper(func):
            @wraps(func)
            def wrapped_func(self, *args, **kwargs):
                if not self.secure or self.ID == 0:
                    return func(self, *args, **kwargs)
                snapshot = None
                owns_snapshot = False
                try:
                    with get_store().transaction() as session:
                        if self._sync_depth:
                            return func(self, *args, **kwargs)
                        self._pull_in_session(session)
                        snapshot = self._record()
                        owns_snapshot = True
                        self._sync_depth = 1
                        result = func(self, *args, **kwargs)
                        self._push_in_session(session)
                    return result
                except BaseException:
                    if snapshot is not None:
                        self._apply_record(snapshot)
                    raise
                finally:
                    if owns_snapshot:
                        self._sync_depth = 0
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
            self.inventory = [item for item in self.inventory if not item.is_expired()]
        # print("End exp" + str(self.XP));use 

class Item:
    def __init__(self, name: str, type: str, expiration: int, **values):
        self.name = name;
        self.type = type;
        self.expiration = int(expiration);
        self.values = {} if values is None else values;
        if self.type == "event_emoji":
            self.values.setdefault("awarded_at", int(time.time()))

    def __str__(self):
        name = self.name
        if self.type in {"custom_nickname_emoji", "trex_auction"}:
            emoji = self.values.get("emoji", "🦖" if self.type == "trex_auction" else "")
            name = f"{emoji} {name}".strip()
        if self.expiration == -1:
            res = f"{name}; expires never... probably";
        else:
            res = f"{name}; expires in {timedelta(seconds=round(self.expiration - time.time()))}";
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
        values = {} if len(fields) < 4 or fields[3] == "" else {
            key: str(value) for key, value in (item.split("=") for item in fields[3].split(","))
        }
        res = Item(fields[0], fields[1], int(fields[2]), **values)
        # Loading old inventory must not restart an emoji's automatic window.
        if "awarded_at" not in values:
            res.values.pop("awarded_at", None)
        return res;

    def should_display_event_emoji(self, now=None):
        """Honor manual choices; otherwise display for 45 days after award."""
        if self.type != "event_emoji":
            return False
        now = time.time() if now is None else now
        if self.expiration > 0 and now >= self.expiration:
            return False
        preference = str(self.values.get("display", "None"))
        if preference != "None":
            return preference == "True"

        awarded_at = self.values.get("awarded_at")
        if awarded_at is None:
            # Older records have no award timestamp. Recover it from the
            # lifetimes used by the original award code, without editing data.
            if self.expiration <= 0:
                return False
            lifetime = {
                "Birthday tag": 90 * 86400,
                "April Fools": 30 * 86400,
            }.get(self.name, 21086592)
            awarded_at = self.expiration - lifetime
        try:
            age = now - float(awarded_at)
        except (TypeError, ValueError):
            return False
        return 0 <= age < 45 * 86400
    
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
