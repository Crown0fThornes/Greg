"""Compatibility entry point and loader for GREG's categorized commands.

Existing callers may keep using ``commands.remember``, ``commands.set_nick``,
etc. Definitions live in category modules; this module forwards their names.
"""

from importlib import import_module, reload

import command_handler

from ._catalog import LEGACY_EXPORTS, REGISTRATION_ORDER


_CATEGORY_MODULES = (
    "common", "experience", "events", "support", "races", "deprecated",
    "members", "families", "administration", "carnival", "reminders",
    "derby", "economy", "community", "carnival_tickets", "giveaways", "rolodex",
)
_EXISTING_MODULES = ("harvest", "summer_fest", "minigames", "task_logs")


def load_commands(*, refresh=False):
    """Load every category and retain the original command/listener order."""
    if refresh:
        for kind in ("Command", "Uncontested", "Loop", "Scheduled", "Deprecated"):
            getattr(command_handler, kind).available_commands.clear()

    modules = {}
    for name in _CATEGORY_MODULES:
        module = import_module(f"commands.{name}")
        modules[name] = reload(module) if refresh else module

    # Grouping definitions must not reorder automatic message/reaction listeners.
    for kind, names in REGISTRATION_ORDER.items():
        registry = getattr(command_handler, kind).available_commands
        ordered = {name: registry[name] for name in names if name in registry}
        ordered.update(registry)
        registry.clear()
        registry.update(ordered)

    # These registered after commands.py historically, including name overrides.
    for name in _EXISTING_MODULES:
        module = import_module(f"commands.{name}")
        modules[name] = reload(module) if refresh else module
    return modules


def __getattr__(name):
    owner = LEGACY_EXPORTS.get(name, "common")
    module = globals().get("_modules", {}).get(owner)
    if module is not None and hasattr(module, name):
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(LEGACY_EXPORTS))


# importlib.reload(commands) reloads all categories, rather than only this facade.
_modules = load_commands(refresh="_modules" in globals())
