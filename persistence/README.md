# Rolodex persistence

Neighbor XP and inventories continue using their existing text files.
The Neighbor SQLite migration remains on indev and is not enabled on main.

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

## Reaction-based Council menus

`$rolodex` or `$rolodex menu` opens the interactive main menu. `$rolodex review`
opens the historical report queue. Both use the existing `ResponseRequest`
REACTION and MESSAGE request framework in `responses.py`; no independent event
listener or `wait_for` loop is added.

React to choose profile lookup, notes, account connections, corrections, missing
events, resets or audit/help. Guided questions ask for individual values; **reply
to the specific prompt message**, rather than sending an unthreaded answer.
A final ✅ confirms the selection before mutations are passed through the same
privileged command/audit path. Home/cancel discards unsaved answers. Notes can
also be edited/restored or deleted from the menu.

The historical review menu has previous/next navigation, original-evidence
inspection, identity-link prompts, field selection and a hide-with-reason action.
Cycle views to browse unresolved, all parsed, or unparsed historical reports.
Unparsed reports offer guided event creation with the source link retained.
Suggestions never silently become confirmed identities.

Menus are bound to their initiating Council member, guild, channel and exact
menu/prompt message. Access is rechecked on every callback, including after a
role is removed. Response requests expire after ten minutes of inactivity and
are in-memory: reopening the menu is necessary after a bot restart. Sessions
retain no database transaction while awaiting responses. Greg needs Add Reactions;
Manage Messages lets it clear old reactions on navigation. If clearing is denied,
a new menu message replaces the old active prompt. Existing argument commands
remain available; `$rolodex help` displays syntax and `$rolodex review 1` gives
plain text review output instead of starting the interactive queue.

## Grouped historical identities and paced imports (schema version 5)

Historical display-name reports now belong to provisional people in
`historical_identity`, rather than requiring one identity decision per event.
`historical_identity_event` maps stable message/line/event keys to those people.
Original names, source messages and individual events remain untouched.

Grouping uses `rolodex_identities.stripped_name()`: remove Discord custom emojis,
Unicode emojis and bracket/brace tags; normalize Unicode, case, punctuation and
spacing. This follows `clean_nick()`'s intent without importing command execution
or modifying live nicknames. Empty/very short cleaned names stay separated by
source message/line. Normalized matches create provisional groups, **not automatic
Discord-account matches**. Newly imported reports with account suggestions that
conflict with a group's confirmed ID are kept in a separate group. Existing
assignments remain stable across reimports.

`$rolodex review` now browses people: original name variants, event counts, sample
reports, suggested account IDs, and up to five similar-name groups. Near-match
suggestions use a similarity threshold of 85% and exclude short names; they are
never merged automatically. Council can:

- 🔗 Link all reports to a known Discord account in one confirmed action.
- ❔ Confirm one person while leaving their Discord ID unknown. This removes
  the identity from the unreviewed queue without inventing a Discord ID.
- 🔀 Merge differently named historical groups after confirming they are one
  person. Confirmed known IDs are retained; conflicting IDs require correcting
  the attribution or using the existing account-link feature for account switches.
- 🔍 Browse individual reports; ✂️ separates a mistaken event into another
  identity. Splits survive reimports and can subsequently be merged or linked.
- ↩️ Reopen an identity for review. All decisions remain in the audit.

`$rolodex identity ID` displays a historical person even without an account.
Equivalent privileged argument controls:

```text
$rolodex identity link ID @user "Confirmed identity"
$rolodex identity unknown ID "Confirmed person, account ID unavailable"
$rolodex identity merge SOURCE_ID TARGET_ID "Same person"
$rolodex identity split MESSAGE:LINE:EVENT "Different person reused the name"
$rolodex identity reopen ID "Needs another review"
```

Identity resolution is an overlay: per-event corrections take precedence. No
old name is silently promoted to authoritative Discord name history. Account
links remain separate, reversible and non-destructive: profiles combine all
linked accounts' resolved historical groups without moving XP or inventory.

### Start imports from Discord

```text
$rolodex import
$rolodex import status
$rolodex import stop
$rolodex import full
```

The main reaction menu also offers start/resume, status and stop. All require
existing Privileged access. Start/resume reads both historical channels in a
background task, oldest first. It uses existing name history and cached current
members for candidate suggestions, sends progress updates by editing a status
message every 30 seconds, and reports completion/failure/stop. Progress is a
message count, not a percentage: Discord history has no known total in advance.

Each message is processed off the event loop using a worker thread, followed by
a 0.2-second yield (at most five messages/second, slower under API/SQLite load).
There is one active in-server import job per guild. A checkpoint per channel
commits after each successfully imported message. Stop/restart resumes from those
checkpoints; committed messages and group decisions are not lost. An interrupted
in-flight message may be replayed safely. Bot restart ends the background job;
start the command again to resume. The prior progress message may remain stale
if the process exits abruptly, while checkpoints stay on disk.

Normal resume skips older messages, including edits to already imported posts.
`import full` deliberately rescans all history to pick up those edits; source-key
corrections, confirmed identities, manual splits and merges remain preserved.
A materially changed source name can change an automatically grouped event's
identity, so inspect edited historical evidence when appropriate. Import does
not post to the source channels or DM/ping members. It only writes the invoking
channel's progress messages and local SQLite records.

The standalone importer remains available. Its review JSON now includes grouped
`identities` as well as raw unresolved event evidence and unparsed lines.

### Trial batches and explained suggestions

`$rolodex import test` imports at most **25 newest messages from each source
channel (50 total)**. It keeps normal pacing and progress updates. Trial records
are saved in the real Rolodex for inspection, but production import checkpoints
are neither read nor advanced. Repeating a trial updates the same evidence
idempotently. `$rolodex import full` then scans all history; `$rolodex import`
continues to mean checkpointed start/resume. The main reaction menu includes a
🧪 trial action with confirmation.

On an identity-review card, 💡 explains account suggestions. Equivalent command:
`$rolodex suggest ID [page]`. Reasons distinguish recorded name observations,
explicit mention/per-message identity evidence, exact aliases from Council-confirmed
people, and spelling similarity to a confirmed person. Suggested matches can
include source links, shared neighborhoods and overlapping report-date ranges.
Contextual overlap is supporting evidence only, never identity proof. Spelling
percentages describe name similarity, not a probability that people are identical.

Competing account candidates are explicitly flagged unless they are already part
of the same confirmed account-link group. Suggestions are ranked by evidence and
limited to five accounts; no account link, identity resolution or group merge is
performed by viewing them. Newly confirmed people automatically become evidence
for subsequent suggestions; original records remain unchanged.
