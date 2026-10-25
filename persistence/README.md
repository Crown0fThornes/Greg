# Rolling Neighbor storage migration

`Neighbor` keeps its existing constructor and command-facing methods. Its default
storage is now SQLite, with ongoing writes to the original text shards.

## Access and migration

- `Neighbor(user_id, guild_id)` immediately loads that user/server pair. If it is
  absent from SQLite, only its matching text record is imported, including XP,
  legacy XP, inventory order, duplicate items, expirations, and attributes.
  Existing jobs that construct linked Neighbors, such as nickname maintenance,
  also migrate the players they access; no separate migration job is added.
- A genuinely new player starts with zero XP and an empty inventory in both
  stores. An existing SQL row always takes precedence over text.
- Legacy server ID `0` and an omitted server argument resolve to FF's server ID,
  `647883751853916162`. The database identifies neighbors by user AND server.
- `Neighbor.decode()` and construction with `link=False` create detached objects
  without importing records. Detached getters/setters remain in memory.
- Explicit `pull()` or `push()` accesses persistence, even on a detached object.
- `read_all_neighbors()` returns detached snapshots. It merges text-only records
  with authoritative SQL records, without enrolling every text-only player.
- `write_all_neighbors()` retains its full-snapshot replacement semantics. It
  updates/deletes already-enrolled SQL records and rewrites text shards, but does
  not enroll the remaining text-only records merely because of a bulk write.

The schema initializes automatically on the first persistence access. There is
no startup import of all players and no change to the existing RSS/event command
interfaces. The three tables are `neighbor`, `item`, and `item_attribute`.

The default database is `data/neighbors.sqlite3`, relative to the project root.
Text shard paths are also anchored to the project root. Override the SQL path
with `GREG_NEIGHBOR_DB` when running an isolated instance or tests. Importing the
Python modules does not open a database.

## Writes and failures

Linked methods use a serialized read/modify/write session. Nested methods share
the same loaded snapshot instead of pulling again and discarding in-progress
changes. SQLite foreign keys protect ownership; surviving items retain their
SQL IDs when inventory is updated or reordered. Attribute values load as strings,
matching the previous text decoder.

The session holds a SQLite write transaction while replacing text shards through
temporary files and atomic renames. A normal SQL, text, or method failure rolls
back SQL and restores any text files already replaced. SQL failures are surfaced;
they never silently substitute stale text data. A record that cannot round-trip
through the old text encoding is rejected rather than producing an unusable
rollback copy. Malformed matching legacy records raise an error, not a zero-XP
replacement.

SQLite and separate text files cannot share a single crash-atomic transaction.
Abrupt process termination or power loss between replacement and SQL commit can
leave a text mirror ahead of SQL. SQLite remains authoritative, and that player's
next successful access repairs its mirror. Keep existing backups during rollout.

## Rollback

Restart with this environment setting to use only the maintained text copies:

```sh
GREG_NEIGHBOR_STORAGE=text
```

`sqlite` is the default. Text mode does not read, initialize, or update SQLite.
You can also revert to the earlier code: the text records retain the old format.

If the bot has made changes in text-only mode, do not simply reactivate an old SQL
database: its records will be stale. Use a fresh database path to roll forward
again on access, or reconcile the databases before switching back. Stop other bot
instances before switching storage modes.

## Verification

From the repository root:

```sh
python -m unittest discover -s tests
```

Migration tests use temporary databases and shards. They cover SQL precedence,
rolling enrollment, bulk compatibility, rollback, item metadata/order, legacy
server IDs, and concurrent updates. They do not migrate live player records.
