# Weekly recruitment review

`weekly_recruitment_review` runs every Monday at 8:00 AM fixed server time
(UTC−4), in channel `792497521259315200`. It reviews the previous Monday
00:00 through the following Monday 00:00, excluding that final boundary.

It scans general (`648223397205114910`) for messages authored by Greg beginning
with `Welcome to Town, <@ID>!`. Each welcome message counts as a server join;
rejoins count again. Duplicate message IDs are ignored. Messages from other
authors and other kinds of greetings do not count. Missing/deleted welcome
messages and joins for which Greg was offline cannot be reconstructed this way.

The first pinned message containing a weekday schedule supplies poster mentions,
using the same `Monday: @person` format as the existing recruitment reminders.
Multiple people on a day are supported. This is credit for the scheduled ad,
not verification that the ad was posted or that it caused those joins. The pin
is read at review time and its parsed schedule is retained with that report.

Each report includes the total joins and the busiest day(s), congratulating
their scheduled posters. After four previous weeks have been recorded, the
first highlight is the day(s) with the largest positive difference between
their join count and the historical average for that weekday. Their scheduled
posters receive the first congratulations. Weekly totals are also compared with
the historical weekly average, including percentage difference when the
baseline is nonzero. Ties receive equal recognition. A day winning both
highlights is congratulated once. Differences are measured in join counts,
not percentage lift, so a zero historical average is supported.

`commands/recruitment_review.py` saves weekly counts, schedule, rendered report,
and delivery status in `data/recruitment_review.sqlite3`. Baselines use only
previous recorded weeks, excluding the week being scored. No historical
baseline is invented for weeks not yet scanned. Repeated execution of an
already posted week does not post again. A completed scan survives a send
failure. Uncertain or partially delivered sends remain `pending` for inspection
instead of automatically risking duplicate announcements. Long reports are
split into Discord-sized messages. Only congratulated users are pinged.

The existing scheduler handles restarts and can run later on the same Monday
if 8 AM was missed; it does not run a missed Monday on a later day.

## Import the initial baseline

Council can run `$recruitmentbaseline` to scan general's past 12 calendar months
in the background. Only complete Monday–Sunday weeks inside that range are
included; the current unfinished week is excluded. The command uses the same
Greg-authored welcome-message recognition as the weekly report and does not
try to reconstruct historical ad assignments from today's pinned schedule.

The progress message updates about every 30 seconds with messages scanned,
recruits found, date reached, and the number of weeks in the scan. Use
`$recruitmentbaseline status` to check it, or `$recruitmentbaseline stop` to
pause. Run `$recruitmentbaseline` again to resume a paused or interrupted scan.
After completion, running it again starts a fresh scan of the current
12-month window. Only one scan runs at a time.

History is fetched 100 messages at a time, with a short pause between pages.
Each page saves its cursor and counts in the same database. Only a completely
finished scan publishes its totals to `baseline_week`; partial imports cannot
skew the averages. Reimports replace each week's imported total, avoiding
double counting. A week already recorded by an ordinary Monday report takes
precedence over the imported copy. Historical scans do not post retroactive
weekly reviews. Completed baseline weeks are available to the next Monday
review immediately, without waiting four new weeks.
