# Dynamic ticket categories

`ticket_manager.py` reconciles saved IDs against `guild.fetch_channels()` before
listing or allocating ticket space. Deleted IDs are pruned; absence of an archive
category does not prevent opening a ticket. The old archive IDs are migration
hints rather than mandatory fetch targets. Matching `closed-tickets-N` and
`open-tickets-N` overflow categories are discovered automatically.

Ticket opening/reopening scans every active open category and closed category,
then chooses an open category with room. Archived tickets reuse any closed
category with fewer than 50 child channels. A new overflow category is created
only when necessary and copies the existing ticket-category overwrites. If all
categories of that kind are missing, the other ticket category type supplies the
permission template. If neither private ticket category exists, Greg raises a
clear error instead of creating a category with unspecified permissions.

Creation/restoration, archive moves and empty-category cleanup are coordinated
with a per-guild lock. Cleanup uses fresh channel listings, checks emptiness again
immediately before deletion and removes only managed overflow categories. It
retains one base category of each type as a permission template. Any child channel,
not just text channels, prevents deletion. Missing categories are tolerated;
cleanup permission failures do not make an already-opened ticket fail. New ticket
channels receive the private default-role/user overwrites at creation time.

The six-hour archive and ten-hour transcript jobs now enumerate live categories.
Archive behavior remains two days of inactivity (unless the last message is
`keep`). A missing user is transcribed/deleted only after an actual Discord
NotFound response; permission/network failures do not imply departure. Existing
six-month transcription behavior remains. Empty message histories are safe.
Cleanup also runs after ticket openings/restorations and maintenance.

No channels/categories are changed merely by editing or testing the code. Restart
Greg to load it. Manage Channels and the existing ticket permissions are required.

## Unsupported Discord channel types

If `guild.fetch_channels()` raises `discord.InvalidData` because of an unknown
channel type, ticket discovery retries the same HTTP endpoint and constructs
supported channels individually using the installed library's channel factory.
Unsupported channels remain lightweight occupancy entries with their IDs and
parent category IDs. They count toward the 50-child capacity limit and prevent
their parent category from being deleted as empty. Unsupported channels are not
omitted from occupancy checks. Other errors, including permission/network errors
and failures parsing supported channel payloads, still propagate. Cleanup uses
the same compatible fetch for its immediate pre-delete check. This change is
confined to the ticket manager; it does not patch discord.py or core bot types.

## Missed reaction recovery

`recover_support_ticket_requests` uses the existing background-job framework
with a 24-hour interval. Its initial pass runs when those jobs start after Greg
comes online; later passes retry missed requests once per day. It reads all non-bot reactions on support
message `1033540464441303200` in the configured support request channel, matching
the live handler's behavior. Multiple reactions from one user are consolidated.

Users with no open ticket receive a new one or have their archived ticket
restored. The normal per-guild ticket lock and topic-based lookup prevent
duplicate channels, including races with live reactions. Existing open tickets
are acknowledged without repeated welcome messages or Council notifications.
Request reactions are removed only after successful opening/restoration; an
opening error leaves the request for a subsequent retry. One failed request
does not stop recovery for other users. Bots are ignored; users who have left
the server are skipped. Failure to remove a reaction does not report an already
opened ticket as failed.
