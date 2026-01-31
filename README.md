# "Greg"
Custom Discord Bot for Friendly Farmers discord server

greg3.py is the "main" script which activates the bot and intercepts events on the server, sending them to:

command_handler.py processes events and distributes them to the correct command in:

commands.py consists of all commands, uncontested commands, loop commands, and now scheduled commands for greg!

- Commands are run when a user calls them by name with the $ prefix. For example, the info() command function is run when a user in the server types "$info". Greg implements minimal typo detection as well: if a user's command call is within 75% accurate of the actual spelling, the command will call nontheless, e.g. "$infp" calls info.
<img width="942" alt="Screenshot 2024-08-30 at 8 15 23 AM" src="https://github.com/user-attachments/assets/f03c0479-8b07-4f20-9ee2-d8073cf2574b">

- Uncontested commands fall into two categories: reaction responses and message responses. These functions run on every reaction or every message respectively. An example would be the XP incrementer command function message_xp() runs every time a message is sent in the server in order to increment the XP of the associated member.
<img width="368" alt="Screenshot 2024-08-30 at 8 12 08 AM" src="https://github.com/user-attachments/assets/2dad399c-7182-4b1e-b84e-a27e4bcec49e">
<img width="681" alt="Screenshot 2024-08-30 at 8 12 32 AM" src="https://github.com/user-attachments/assets/a8c32f3b-00ee-4cb2-8bab-946e162c6334">

- Loop commands fall into two categories: timed and daily. These functions run on a timed interval from when the bot begins running or at approximately 6pm EST (+/- 5 minutes) each day respectively.
<img width="781" alt="Screenshot 2024-08-30 at 8 13 26 AM" src="https://github.com/user-attachments/assets/320507f0-a85f-47f2-9d7b-2998e9ea1ea8">
<img width="542" alt="Screenshot 2024-08-30 at 8 14 03 AM" src="https://github.com/user-attachments/assets/4cbfbc3e-316a-45ab-8cd8-fc7b223482a4">

# Types

- A Neighbor object represents a member of the server. It is linked to a .txt "database" such that no call on or access of a Neighbor object will not be up to date with the latest information.

- A Context object represents the context in which a Command command is run. It contains valuable information about the channel, message, and author of a command.