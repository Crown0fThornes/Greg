# Personal reminders

Available to everyone in FF:

```text
$remindme 10/29/2026 9:30 AM: Check the HK signups
$remindme 10/29/2026: Check the HK signups
```

The separator colon after the date/time is required. Omitting the time uses
8:00 AM. Dates use month/day/four-digit-year; explicit times use a 12-hour clock
with AM/PM. Times are fixed server time, UTC−4 year-round. Past dates, invalid
times and empty text are rejected. Text may contain additional colons and is
limited to 1,500 characters. The reminder belongs to the person who invokes the
command; mentions in the text do not change its recipient.

At the due time Greg sends a DM and a reminder with the requester's user ping in
channel `784150346397253682`. Titles precede pings. The original request is linked
in both messages. Other user/role/everyone mentions in the copied text cannot
ping. Successful scheduling is acknowledged with a ✅ reaction on the request, without
a confirmation reply. Invalid requests retain the existing CommandArgsError reply.
DMs must be open to Greg. Closed DMs or a failed DM
do not suppress the independent server reminder.

`commands/personal_reminders.py` stores reminders in
`data/personal_reminders.sqlite3`. The main one-minute scheduler in `greg3.py`
runs deliveries while `RUN_AUTO_COMMANDS` is enabled. Restart Greg to register
`$remindme`. Reminders survive restarts, and overdue reminders are sent when Greg
returns. They are one-shot; there is no recurring/list/cancel syntax yet.

Each destination independently progresses waiting → pending → sent, or blocked
for definite Forbidden/NotFound failures. Resolving a destination may retry on
later polls after transient read failures. A send timeout or abrupt shutdown
can leave a pending status: check delivery before manually resetting it to
waiting. Such ambiguous sends are logged and not automatically retried, to avoid
duplicate pings. A blocked destination is logged for review. Successful delivery
to the other destination still proceeds. Keep the ignored data database in
normal server backups; no live Discord requests are made by tests.
