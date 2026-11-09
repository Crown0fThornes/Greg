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
