# HK signup reminders

The main `greg3.py` scheduler checks `commands/hk_reminders.py` once per minute while
`RUN_AUTO_COMMANDS` is enabled. Signups live in channel `1553522822263869600`.
Each task must be its own message, starting with:

```text
New Joins / 👋 / Tuesday / 8:00 AM

Your reminder instructions here.
```

Bold headings and heading markers are supported, as are 24-hour times and an
optional `(ST)` suffix. Days must be full English names. Task titles are limited
to 200 characters. Unrecognized messages are ignored. Instructions beneath the
heading become the reminder text; long bodies are split into multiple messages.
Each reminder includes a link to the original task post. The emoji must be one
Unicode emoji (including variants) or a Discord custom emoji in `<:name:id>` /
`<a:name:id>` format. Older three-field headings continue to send Council-role
reminders, but cannot offer individual assignments.

ST is fixed **UTC−4** throughout the year, without daylight-saving adjustments.
For example, 8 AM ST always means 12:00 UTC. This is independent of the Carnival
inactivity report's own schedule.

| NH | Logo ID | Destination Council channel | Role ping |
| --- | --- | --- | --- |
| Pro | 1111011980061462538 | 1558858396004917298 | 1102411249502920755 |
| Main | 1111011971953872976 | 1558858338262065172 | 1102411158029340803 |
| Junior | 1111011976320122880 | 1558861126333374515 | 1102411328129335316 |
| Garden | 1173332572642754560 | 1558861204473122916 | 1184035613008216105 |
| Carnival | 1342333117607710741 | 1558861299138699285 | 1342329281015058442 |

Any person's logo reaction on the central task post signs that NH up. Remove **all** reactions of that
logo to unsubscribe the NH. Other emojis do not count. Reaction authors are
intentionally unrestricted. At reminder time only the task's selected users may be pinged, or that NH's
Council role when nobody selected it. Other mentions in copied instructions
cannot ping.
Greg needs channel history/read access, send access at destinations, and
permission to mention those Council roles.

The entire signup history is refreshed every five minutes. Before a due reminder
is sent Greg fetches the post again, checking for edits, deletion and changed
reactions. Edited/new schedules are discovered within five minutes. Deleting the
post cancels it. An edit does not send a second reminder for the same message/NH
in the same server-time assignment week (Tuesday through Monday). Multiple task messages
remain independent.

Reminders may catch up for up to ten minutes after their scheduled time. Older
missed reminders are skipped. This prevents an outage from causing a backlog of
staff pings. Keep the bot running for delivery.

`data/hk_reminders.sqlite3` records delivery per signup message, NH, week and body
part. Successful delivery IDs survive restarts. A pending claim is written before
sending: if a timeout or crash makes delivery uncertain, Greg logs the affected
key and does **not** automatically retry it, avoiding repeat pings. Check the
Council channel before manually clearing that pending row for a retry. Definite
Forbidden/NotFound send rejections release the claim so permissions can be fixed
and retried within the catch-up window. There is no claim of exactly-once delivery
across Discord and local SQLite; ambiguous sends require manual review.

This feature does not alter the older hard-coded hospitality reminders. Restart
Greg after deploying the new module and scheduler hook. Offline tests run with
`python -m unittest discover -s tests -p test_hk_reminders.py`.


## Sunday individual assignments

Every Sunday at **8 AM ST (12:00 UTC)**, within the same ten-minute catch-up
window, Greg posts a signup in each of the five Council channels. Each post uses:

**Good morning and happy weekend! Please react to the tasks you're responsible for *next week*, or would otherwise like to be pinged for.**

The first page pings only that NH’s Council role; continuation pages do not
ping it again. It lists the names/emojis of that NH’s selected central tasks and seeds all of
those task reactions. The signup covers the Tuesday two days later through the
following Monday. Sunday and Monday reminders continue using the previous
assignment week's post. For example, Sunday's October 25 signup applies starting
Tuesday October 27; Monday October 26 still uses the October 20 assignment week.

The original central NH-logo reactions determine which NHs receive each task.
The individual task-emoji reactions on a Council signup determine **who** gets
pinged for that week. All non-bot reactors are eligible, with no additional
Council-role check. Reactions are read at reminder time: adding/removing them
changes the next due reminder. Greg's own seed reaction never counts as a signup.
If no people selected the task, the post is missing/deleted/unavailable by ID,
or the task was added/changed after the Sunday snapshot, the reminder uses the
NH Council-role fallback. A permission/API error reading an existing post is
logged and skips that attempt rather than guessing the assignees; later polls
can retry within the catch-up window.

Task emoji IDs must be unique within an NH's selected task list. Tasks with a
missing or duplicate identifier are excluded from individual signup options and
continue with the Council-role fallback; the Sunday post explains this. Custom
emoji names may change while their stable IDs continue matching. Sunday pages
are split to respect Discord's 20-reaction and message-length limits.

`assignment_post` in `data/hk_reminders.sqlite3` stores the NH, Tuesday week date,
page, Council post ID and the task-message-ID-to-emoji snapshot. Restarts reuse
that post rather than sending another. Bot reaction seeding is retried during
the Sunday catch-up window. A deleted post is not automatically recreated.
Pending uncertain post deliveries remain logged and need review before retrying,
just like uncertain task-reminder deliveries. Keep this database in backups.

Greg needs Add Reactions / Read Message History in each Council channel, and
access to custom task emojis, in addition to its existing send/mention permissions.
