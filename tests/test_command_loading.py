"""Offline checks for command loading, reloads, and manual retired entry points.

Run from the repository root with:
    python -m unittest discover -s tests
"""

import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import command_handler
import commands.commands as commands


KINDS = ("Command", "Uncontested", "Loop", "Scheduled", "Deprecated")


def registry_names():
    return {kind: list(getattr(command_handler, kind).available_commands) for kind in KINDS}


class CommandLoadingTests(unittest.TestCase):
    def test_compatibility_helpers_point_to_their_new_modules(self):
        from commands.common import chance, remember
        from commands.experience import inc_xp
        from commands.families import get_family_from_user
        from commands.members import set_nick
        for name, function in locals().copy().items():
            if name != "self":
                self.assertIs(getattr(commands, name), function)

    def test_mutable_legacy_state_is_forwarded(self):
        from commands import experience
        previous = experience.xp_gained
        try:
            experience.xp_gained = 123
            self.assertEqual(commands.xp_gained, 123)
        finally:
            experience.xp_gained = previous

    def test_reload_keeps_all_registrations_and_order(self):
        expected = registry_names()
        importlib.reload(command_handler)
        importlib.reload(commands)
        self.assertEqual(registry_names(), expected)
        for kind in KINDS:
            cls = getattr(command_handler, kind)
            self.assertTrue(all(isinstance(command, cls) for command in cls.available_commands.values()))

    def test_retired_commands_are_not_live_commands_or_jobs(self):
        retired = command_handler.Deprecated.available_commands
        self.assertIn("update_xc_scoring", retired)
        self.assertIn("survey", retired)
        self.assertIn("withdraw", retired)
        for kind in KINDS[:-1]:
            # A live replacement can share a name (e.g. harvest's silo).
            for live in getattr(command_handler, kind).available_commands.values():
                wrapped = [cell.cell_contents for cell in (live.run.__closure__ or ())]
                for entry in retired.values():
                    self.assertNotIn(entry.func, wrapped)


class DeprecatedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.retired = command_handler.Deprecated
        self.client = self.retired.client
        self.context = SimpleNamespace(
            content="$deprecated sample 'two words'",
            tokens=["$deprecated", "sample", "two words"],
            args=["sample", "two words"],
            access_type=command_handler.AccessType.DEVELOPER,
            guild=SimpleNamespace(id=command_handler.FF.guild),
            send=AsyncMock(), type="MESSAGE",
        )

    def tearDown(self):
        self.retired.available_commands.pop("sample", None)
        self.retired.client = self.client

    async def test_legacy_arguments_and_original_context_are_preserved(self):
        calls = []

        @self.retired()
        async def sample(activator, context):
            calls.append((activator, context))

        activator = object()
        self.assertTrue(await self.retired.execute(activator, self.context))
        self.assertIs(calls[0][0], activator)
        passed = calls[0][1]
        self.assertEqual(passed.content, "$sample 'two words'")
        self.assertEqual(passed.args, ["two words"])
        self.assertEqual(passed.tokens, ["$sample", "two words"])
        self.assertEqual(self.context.args, ["sample", "two words"])
        self.assertEqual(self.context.content, "$deprecated sample 'two words'")
        self.assertIs(sample, self.retired.available_commands["sample"].func)

    async def test_access_and_server_restrictions(self):
        called = AsyncMock()
        called.__name__ = "sample"
        self.retired()(called)
        self.context.access_type = command_handler.AccessType.PUBLIC
        await self.retired.execute(object(), self.context)
        called.assert_not_awaited()
        self.context.access_type = command_handler.AccessType.DEVELOPER
        self.context.guild.id = 1
        await self.retired.execute(object(), self.context)
        called.assert_not_awaited()

    async def test_retired_job_runs_once_with_the_client(self):
        called = AsyncMock()
        called.__name__ = "sample"
        self.retired(kind="Loop")(called)
        self.retired.client = object()
        await self.retired.execute(object(), self.context)
        called.assert_awaited_once_with(self.retired.client)
        self.assertNotIn("sample", command_handler.Loop.available_commands)

    async def test_message_listener_receives_only_context(self):
        called = AsyncMock()
        called.__name__ = "sample"
        self.retired(kind="Uncontested")(called)
        await self.retired.execute(object(), self.context)
        called.assert_awaited_once()
        self.assertEqual(called.await_args.args[0].args, ["two words"])

    async def test_other_commands_are_not_consumed(self):
        self.context.tokens = ["$help"]
        self.assertFalse(await self.retired.execute(object(), self.context))
        self.context.send.assert_not_awaited()

    async def test_live_dispatch_routes_deprecated_command(self):
        called = AsyncMock()
        called.__name__ = "sample"
        self.retired()(called)
        await command_handler.Command.execute(object(), self.context)
        called.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
