"""Exercise nickname rendering offline, without importing bot registrations."""
import ast
import io
import json
from pathlib import Path
import re
import time
import traceback
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from custom_types import Item, Neighbor


SOURCE = Path(__file__).resolve().parents[1] / "commands" / "commands.py"
TREE = ast.parse(SOURCE.read_text())
NODES = [node for node in TREE.body if getattr(node, "name", None) in
         {"_nickname_with_event_emojis", "set_nick"}]


class NicknameTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.items = []
        self.neighbor = Mock(ID=123)
        self.neighbor.get_item_of_name.side_effect = lambda name: next(
            (item for item in self.items if item.name == name), None)
        self.neighbor.get_items_of_type.side_effect = lambda kind: [
            item for item in self.items if item.type == kind]
        self.neighbor.expire_items.side_effect = lambda: self.items.__setitem__(
            slice(None), [item for item in self.items if not item.is_expired()])
        self.user = SimpleNamespace(id=123, display_name="Lincoln", name="Lincoln",
                                    roles=[SimpleNamespace(id=100)], edit=AsyncMock())
        self.guild = SimpleNamespace(id=10, get_member=lambda uid: self.user)
        self.env = dict(Neighbor=lambda *args: self.neighbor, Item=Item,
                        re=re, json=json, time=time, traceback=traceback,
                        unicodes={"star": "⭐"})
        exec(compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE), "exec"), self.env)

    def reward(self, emoji, expiration=None, display="True"):
        item = Item(emoji, "event_emoji", int(time.time()) + 86400 if expiration is None else expiration,
                    emoji=emoji, display=display)
        self.items.append(item)
        return item

    async def render(self):
        family = dict(name="Penguin", tag="{P}", old_tag="[P]", role_id=100,
                      honorary_role_id=101, emoji="🐧")
        def files(path, *args, **kwargs):
            if path == "lookups/families.json":
                return io.StringIO(json.dumps([family]))
            if path == "lookups/rss.json":
                return io.StringIO(json.dumps([{"name": "Tags", "items": [
                    {"name": "Star", "emoji": "star"}]}]))
            if path in {"crown.txt", "trophy.txt", "top_3.txt"}:
                return io.StringIO("")
            raise AssertionError(path)
        with patch("builtins.open", side_effect=files), patch("builtins.print"):
            await self.env["set_nick"](self.user, self.guild)
        return self.user.edit.await_args.kwargs["nick"] if self.user.edit.await_args else self.user.display_name

    async def test_family_and_shop_tags_left_event_emojis_right(self):
        self.items.append(Item("Star", "tag", -1))
        self.reward("🌷")
        self.assertEqual(await self.render(), "⭐[P] Lincoln 🌷")

    async def test_long_name_is_shortened_to_preserve_complete_suffix(self):
        self.user.display_name = "A" * 32
        self.reward("👩‍🌾")
        self.reward("🎂")
        nick = await self.render()
        self.assertEqual(len(nick), 32)
        self.assertTrue(nick.startswith("[P] "))
        self.assertTrue(nick.endswith(" 🎂👩‍🌾"))

    async def test_only_three_selected_event_emojis_are_displayed(self):
        for emoji in ("🎂", "🌷", "🎁", "🐇"):
            self.reward(emoji)
        nick = await self.render()
        self.assertEqual(nick, "[P] Lincoln 🎁🌷🎂")

    async def test_expiration_happens_before_any_inventory_read(self):
        self.reward("🎂", expiration=int(time.time()) - 1)
        self.reward("🌷")
        self.assertEqual(await self.render(), "[P] Lincoln 🌷")
        self.assertEqual(self.neighbor.mock_calls[0][0], "expire_items")
        self.assertEqual([item.name for item in self.items], ["🌷"])

    async def test_existing_suffix_is_not_duplicated_on_refresh(self):
        self.reward("🌷")
        self.user.display_name = await self.render()
        self.user.edit.reset_mock()
        self.assertEqual(await self.render(), "[P] Lincoln 🌷")
        self.user.edit.assert_not_awaited()

    async def test_invisibility_and_manual_hide_still_apply(self):
        self.reward("🌷", display="False")
        self.assertEqual(await self.render(), "[P] Lincoln")
        self.items.append(Item("Invisibility Cloak", "perk", -1))
        self.reward("🎂")
        self.user.display_name = "[P] Lincoln"
        self.user.edit.reset_mock()
        self.assertEqual(await self.render(), "Lincoln")

    async def test_coe_prefix_does_not_duplicate_an_old_event_suffix(self):
        self.items.append(Item("Carnival COE", "coe", -1))
        self.reward("🌷")
        self.user.display_name = "[coe] [P] Lincoln 🌷"
        self.assertEqual(await self.render(), "[coe] [P] Lincoln 🌷")


class ExpirationTests(unittest.TestCase):
    def test_expire_items_keeps_unexpired_duplicates_and_removes_adjacent_expired_items(self):
        neighbor = Neighbor(123, 10, link=False)
        live = Item("Booster", "perk", -1)
        neighbor.inventory = [Item("Booster", "perk", 1), Item("Booster", "perk", 2), live]
        neighbor.expire_items()
        self.assertEqual(neighbor.inventory, [live])


if __name__ == "__main__":
    unittest.main()
