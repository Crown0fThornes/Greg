import datetime
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

from commands import farmmas_emojis as farmmas


class FarmmasTests(unittest.IsolatedAsyncioTestCase):
    async def test_reconciles_missed_and_removed_reactions_without_resetting_preferences(self):
        inventories = {
            1: {"Farmmas emoji 🎄": NS(name="Farmmas emoji 🎄", display="False")},
            2: {"Farmmas emoji ✨": NS(name="Farmmas emoji ✨")},
        }
        neighbors = {}
        for uid, items in inventories.items():
            neighbor = Mock(ID=uid)
            neighbor.get_family.return_value = 10
            neighbor.get_item_of_name.side_effect = lambda name, items=items: items.get(name)
            neighbor.bestow_item.side_effect = lambda item, items=items: items.update({item.name: item})
            neighbor.vacate_item.side_effect = lambda item, items=items: items.pop(item.name)
            neighbors[uid] = neighbor
        async def users(**kwargs):
            yield NS(id=1, bot=False)
            yield NS(id=999, bot=True)
        reactions = [NS(emoji=emoji, users=users) for emoji in ("🎄", "❄️")]
        guild = NS(id=10, get_member=lambda uid: NS(id=uid))
        message = NS(guild=guild, reactions=reactions)
        set_nick = AsyncMock()
        factory = Mock(side_effect=lambda uid, gid: neighbors[uid])
        factory.read_all_neighbors.return_value = list(neighbors.values())
        original = inventories[1]["Farmmas emoji 🎄"]
        with patch.object(farmmas, "Neighbor", factory):
            await farmmas.reconcile(message, set_nick, now=datetime.datetime(2026,12,5))
            await farmmas.reconcile(message, set_nick, now=datetime.datetime(2026,12,6))
        self.assertIs(inventories[1]["Farmmas emoji 🎄"], original)
        self.assertIn("Farmmas emoji ❄️", inventories[1])
        self.assertEqual(inventories[2], {})
        self.assertEqual(set_nick.await_count, 2)
        self.assertEqual(inventories[1]["Farmmas emoji ❄️"].expiration,
                         int(datetime.datetime(2027,1,9,23,59,59).timestamp()))

    async def test_failed_reaction_read_does_not_modify_inventory(self):
        async def users(**kwargs):
            yield NS(id=1, bot=False)
            raise RuntimeError("interrupted")
        with patch.object(farmmas, "Neighbor") as neighbors:
            with self.assertRaises(RuntimeError):
                await farmmas.reconcile(NS(reactions=[NS(emoji="🎄", users=users)]),
                                        AsyncMock(), now=datetime.datetime(2026,12,5))
            neighbors.assert_not_called()
            neighbors.read_all_neighbors.assert_not_called()

    async def test_january_does_not_award_new_items(self):
        async def users(**kwargs):
            yield NS(id=1, bot=False)
        neighbor = Mock(ID=1)
        neighbor.get_item_of_name.return_value = None
        factory = Mock(return_value=neighbor)
        factory.read_all_neighbors.return_value = []
        guild = NS(id=10, get_member=lambda uid: NS(id=uid))
        with patch.object(farmmas, "Neighbor", factory):
            await farmmas.reconcile(NS(guild=guild,reactions=[NS(emoji="🎄",users=users)]),
                                    AsyncMock(), now=datetime.datetime(2027,1,2))
        neighbor.bestow_item.assert_not_called()
