# Command layout

`greg3.py` creates a `Context` for each Discord event and calls the registries in
`command_handler.py`. Importing this package loads `commands.py`, which registers
the category modules and then the existing harvest, fair, minigame, and task-log
modules. Command implementations live in these files:

| File | Main contents |
| --- | --- |
| `administration.py` | Moderation, diagnostics, and server administration |
| `carnival.py` | Carnival operations and task helpers |
| `carnival_tickets.py` | Carnival ticket calculations |
| `community.py` | Public information, greetings, media, and community utilities |
| `derby.py` | Derby points, leaderboards, and task bounties |
| `economy.py` | Treasury, trading, shop, banking, and sales |
| `events.py` | Message/reaction dispatch, expectations, and ongoing activities |
| `experience.py` | XP, profiles, inventory, and monthly resets |
| `families.py` | Family membership and assignment helpers |
| `giveaways.py` | Hosting, closing, and rerolling giveaways |
| `members.py` | Nicknames, tags, roles, and member requirements |
| `races.py` | A&B race submissions, standings, and summaries |
| `reminders.py` | Scheduled notices and recurring server maintenance |
| `support.py` | Support tickets, transcripts, and requests |
| `common.py` | Shared imports, constants, storage, and small helpers |
| `deprecated.py` | Retired entry points and commented historical sketches |

The existing `harvest.py`, `summer_fest.py`, `minigames.py`, and `task_logs.py`
keep their previous responsibilities.

## Dependencies and loading

Existing imports such as `import commands.commands as commands` still work:
`commands.remember`, `commands.set_nick`, and the other old names forward to their
new modules. New code can import helpers directly from their category. Imports
inside functions resolve dependencies between categories without circular imports.

`_catalog.py` records the original registration order and old name locations.
This preserves listener sequencing, help order, and existing duplicate-name
replacement behavior. It is not a second list of command implementations. New
commands in an existing category register through their decorators normally;
add a new category to `_CATEGORY_MODULES` in `commands.py` if needed.

The developer `$sync` path reloads every category and existing command module,
and refreshes the listener's references to the handler classes. Restart the bot
once when first installing this reorganization so that the updated sync path is
loaded.

## Retired commands

Retired entry points use `@command_handler.Deprecated`, which keeps them out of
normal help, normal command dispatch, automatic listeners, and schedules. The
decorator returns the original function, preserving any existing internal calls.

Only developer access in the FF server can invoke them:

```text
$deprecated list
$deprecated survey
$deprecated recruitment [original arguments]
```

A retired `Command` receives the activator and a copied context with the original
command name/arguments. A retired message listener receives that context. A
retired `Loop` or `Scheduled` function receives the bot client and runs once.
Archived edit/delete/reaction listeners require their original event payload and
cannot be invoked from a message. Entirely commented sketches remain comments;
they include unfinished code and are preserved rather than repaired or enabled.

## Offline checks

Run from the repository root using the project's Python environment:

```sh
python -m unittest discover -s tests
```
