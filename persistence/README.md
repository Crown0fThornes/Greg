# Neighbor SQLite storage

This is the schema foundation only. `custom_types.Neighbor` and the commands
still use their existing text files. Initialization does not import player data
or modify those files.

Initialize the empty database from the repository root:

```sh
python -m persistence.neighbor_db
```

The database is `data/neighbors.sqlite3`, located relative to the project rather
than the current working directory. Data files are already excluded from Git;
the schema and initialization code can be committed as source.

| Table | Identity | Contents |
| --- | --- | --- |
| `neighbor` | `(user_id, guild_id)` | Current XP and legacy XP for one Discord user in one server |
| `item` | `item_id` | Owning neighbor, name, type, expiration, and inventory position |
| `item_attribute` | `(item_id, name)` | One text value per named attribute on an item instance |

`guild_id` replaces the old storage field named `family`; it does not represent
Hippo/Penguin/Fox membership. Existing legacy server IDs will need normalization
during the future data migration. XP may be negative, matching the current model.

Identically named items remain separate instances. Inventory positions preserve
the old list order and are unique within each neighbor's inventory. Expiration
is a Unix timestamp; nonpositive values mean no expiration. Attribute values are
text, matching `Item.decode()` today; typed attribute values can be designed in a
later schema version.

Use `connect()` from `persistence.neighbor_db` for database access. It enables
foreign keys on each connection, commits successful transactions, rolls back on
exceptions, and closes the connection. Removing a neighbor cascades to their
items and attributes; removing an item cascades only to its attributes. Code that
deletes inventory should therefore explicitly choose the intended owner or item.

Initialization is atomic and repeatable, retains existing records, and records
schema version 1 with SQLite's `user_version`. No extra metadata table is needed.
