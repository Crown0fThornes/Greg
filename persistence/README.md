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

## Rolodex history

`persistence.rolodex.Rolodex` initializes a separate `data/rolodex.sqlite3`
on Greg's first ready/member event. It does not change Neighbor, XP, inventory,
or text-file writes. The main entry point `greg3.py` records cached members on
ready, then listens for joins, leaves, member updates and global user updates.
The deliberately disabled membership listeners in `testing.py` remain disabled.

Tables:

- `person`: stable Discord user IDs. Renaming never changes identity.
- `name_history`: username, global display name and server nickname observations.
  Nickname clearing is stored as NULL. Unchanged names don't create extra rows.
- `membership`: separate server stays, neighborhood role intervals and annual
  family role intervals. Rejoining creates another stay. Honorary assignments
  are separate from regular assignments; simultaneous roles are preserved.

All times are timezone-aware UTC ISO timestamps. `started_at` is known only
from Discord's server `joined_at` or a live join/role event. Existing role
assignments have an unknown start and a `first_observed_at` date. Changes found
on reconnect have an unknown `ended_at` and an `end_observed_at` date; live
changes set both. Gateway times are receipt times, not audit-log timestamps.
A leave closes all open memberships in that server. History survives departure.

Ready reconciliation examines cached members only and never declares that an
absent member left: an incomplete cache must not create false departures.
Consequently people who leave entirely while Greg is offline can retain open
records until further evidence is available. Historical reconstruction and a
complete offline reconciliation process are future work. Treat open intervals
as last known state, not proof of present membership. Names changed during
outages are likewise observations, not exact change dates. No account linking
is inferred from similar names.

FF neighborhood role IDs are configured in `rolodex.py`. Animal-family roles
are explicitly pinned to their **2026 season** in `lookups/rolodex_families.json`,
matching the current family assignment command. Update that configuration when
seasons change; do not derive season from the computer's current year. Other
servers currently record server and name history only. Old database rows keep
their labels, season and role IDs when configuration changes.

`Rolodex.history(user_id)` returns the two ordered histories as plain records for
a future command. The privileged `$rolodex` command displays these records; council notes, tickets
and account linking are not implemented. Historical channel imports are described below. Database files are ignored
by Git and need to be included in the server's normal data backups. Run tests
with `python -m unittest discover -s tests` without connecting to Discord.

## Import historical neighborhood logs

Run this one-time reader from the project root (with the usual `.env`):

```sh
python -m persistence.import_membership_history
```

It reads **every message** in joinlist `943263445724311572` and leavelist
`1138557740185305169`. It needs View Channel and Read Message History plus the
usual member/message-content intents. It does not post Discord messages. Run
separately from the main bot; importing does not require starting `greg3.py`.
The importer is explicit, not an automatic startup job.

Schema version 2 adds `membership_log_message` (original content, author, channel,
message ID and posting date) and `membership_event` (one join/leave per parsed
line/target). `Rolodex.history(user_id)` includes linked historical events.
These reports are kept separate from live membership intervals, so old reports
cannot overwrite today's observed role state. Posting time is evidence of the
reported change, not a guaranteed exact time of the underlying event. Historical
reports may overlap live observations; future command presentation should merge
that evidence rather than blindly counting both.

Only a single user mention in the subject automatically links to a user ID.
**Display names are never sufficient for automatic attribution**, even if they
currently match only one account. Exact current/historical names are suggestions
only; no fuzzy/shorthand guesses or emoji/tag stripping are performed. Posting
a report does not mean its author is the subject. Ambiguous reports stay stored
with a NULL user ID until reviewed. Old reports do not become authoritative name
history merely by being imported.

The review report defaults to `data/rolodex_import_review.json`. It contains
unresolved parsed reports and unparsed lines, including shorthand and waitlist
notes. For confirmed matches create a private JSON file such as
`data/rolodex_overrides.json`:

```json
{"123456789012345678:1": 355169964027805698}
```

Keys are `message_id:line_number` (lines start at 1), values are confirmed Discord
user IDs. Rerun with `--overrides data/rolodex_overrides.json`. Keep using the same
mapping on subsequent imports; reparsing replaces that message's prior evidence,
including manual resolutions. `--db` and `--review` can target alternate files.
A failure preserves already imported messages; a rerun reads all messages again
without duplicating events. Edited messages are reparsed; deleted source messages
remain preserved from earlier imports. Review files contain member information
and belong in the ignored data directory.

Multiple simultaneous neighborhoods, same-day joins/leaves, transfers, repeated
reports and a first report that is a leave are all retained. Nothing is discarded
as a presumed role mistake. The future `$rolodex` display can interpret those
patterns. Unsupported wording remains in the source-message table/review report
rather than being turned into an invented event. No historical server departure
is inferred unless explicitly reported (e.g. "has left FFJ and the server").

New Greg neighborhood notices include both the display name and a user mention,
so future reports carry a stable ID even after renaming.

## Council Rolodex command and corrections

`$rolodex @user` or `$rolodex USER_ID` displays a compact neighborhood timeline,
name history, introduction link and Council notes. Raw view retains server and
family records as well as all original neighborhood/name evidence.
This command uses existing **PRIVILEGED** access (FF Council/leaders role or the
configured developer) and is restricted to FF. All subcommands share that access
check. Replies suppress mentions. They appear in the invoking channel: Council
should use an appropriately restricted channel. The command does not fetch or
invent missing records. Use `$rolodex help` (and `$rolodex help 2` if paginated).

- `$rolodex raw USER_ID` includes suppressed/excluded records and their edit keys.
- `$rolodex review` lists unresolved historical identities with source links and
  suggested IDs, plus unparsed messages. Resolve each event with an explicit
  `user_id` correction; no automatic name matching is introduced.
- `$rolodex inspect TYPE KEY` displays effective and original records; historical
  events include the full original message and source link.
- `$rolodex edit TYPE KEY FIELD "value" "reason"` overlays a correction.
- `$rolodex reset TYPE KEY FIELD "reason"` removes that field's overlay.
- `$rolodex add USER_ID join FFC 2026-10-25 "reason / source link"` records a
  missing neighborhood event. `leave` is also supported. Use this for unparsed
  human reports after confirming the person and meaning; the original unparsed
  message remains available in review as evidence.
- `$rolodex audit` lists edits, original/effective values, editor IDs, dates and
  reasons, as well as manual additions. Read views accept a final page number.

Record types: `name`, `membership`, `event`, `manual`. Numeric keys identify name,
observed membership and manual event records. Historical event keys are stable
`MESSAGE_ID:LINE_NUMBER:EVENT_NUMBER` (line starts at 1, event starts at 0).
Stable source keys keep corrections attached even if the history importer is
rerun. Review each event separately when one line reports both neighborhood and
server departures. Reinterpreting/rewriting source text may change what a key
means, so inspect corrected messages after edits to their Discord source.

Schema version 3 adds append-only `rolodex_edit` and `rolodex_manual_event` tables.
Every edit requires a reason and stores the acting Discord ID and UTC time.
Original records are not rewritten. Reset is itself audited. `excluded=true`
hides erroneous evidence without deleting it. These corrections affect only the
Council-facing Rolodex view, not live Discord roles or Neighbor XP. Internal
`Rolodex.history()` and the importer JSON review remain raw evidence APIs;
`rolodex_records.records()` applies corrections for Council views.

The compact display combines live neighborhood observations and historical
reports by New York calendar day, suppresses same-neighborhood same-day
reversals, and describes different-neighborhood leave/join pairs as switches. That is a presentation heuristic, not proof of a
real transfer. Raw view retains every event and parallel membership. Server and family intervals remain available through raw view. Neighborhood
state is last known from the available evidence; old reports do not modify live
membership tables. Exact gateway dates, unknown
baseline starts, offline-observed absences, and last-known active records remain
distinguishable. Corrections should not claim more precision than their evidence.

## Compact profiles, notes and account switches (schema version 4)

Profiles use `# NAME Rolodex`, followed by Neighborhood History (oldest first,
last-known active neighborhoods last), one-line Name History, Link to introduction,
and Council Notes. `FF` is displayed as **FFM**; both `FF` and `FFM` are accepted
for neighborhood corrections/manual additions. Dates use ordinal days and New
York calendar time. Unknown membership starts remain explicitly unknown; no
observed baseline date is presented as a join date. Current means last known
from recorded evidence, especially for people who depart during downtime.
Overlapping neighborhoods remain separate. Same-day reversal filtering is
presentation-only and retains a previously known continuous start where possible.

Name history ignores consecutive differences in case, punctuation, whitespace,
emojis and one-letter family tags. Actual stored names are untouched. That
normalization never participates in historical identity resolution.

Introductions use the same channel (`783713419831279697`) and criteria as
`$profile`: newest matching author among the latest 1,000 messages, with `#` in
the content and more than 99 characters. All confirmed linked accounts qualify.
A missing match or inaccessible channel is stated rather than inventing a link.

Council commands (same Privileged access as all Rolodex commands):

```text
$rolodex note @user "Helped them finish derby training."
$rolodex note edit 3 "Completed derby training." "Updated after follow-up"
$rolodex note delete 3 "No longer relevant"
$rolodex link @old_account @new_account "Account switch confirmed with member"
$rolodex accounts @user
$rolodex unlink @old_account @new_account "Mistaken link"
```

`rolodex_note_revision` is an append-only note version history. Profiles display
active notes with their original author's name and a note ID; audit also includes
later editors, deleted text, reasons and timestamps. Editing a deleted note
restores it. Author IDs are retained even if their names change later.

`rolodex_account_link` is an append-only link/unlink log, with acting Council ID,
name, reason and time. Connected accounts form a group, and querying either
account shows the combined history, notes and introductions. Chained switches
are supported; already-connected/cyclic links and self-links are rejected.
Unlink uses the original old/new order; the accounts command lists those edges.
After unlink, each account's original records and notes remain attached to its
own ID. Links do not transfer XP, inventory, permissions or Discord roles, and
no records are relabeled to the new account. The audit retains past links.
