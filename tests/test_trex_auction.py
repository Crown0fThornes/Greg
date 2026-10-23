import ast
import asyncio
from copy import deepcopy
import datetime
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import discord
from custom_types import Item

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT/'commands/commands.py').read_text())
NAMES = {'_trex_calendar', '_is_trex_item', '_trex_state', '_trex_refresh_nicknames',
         '_trex_quote', '_trex_purchase', 'reset_trex_auction'}
NODES = [node for node in TREE.body if getattr(node, 'name', None) in NAMES]
for node in NODES:
    if isinstance(node, ast.AsyncFunctionDef):
        node.decorator_list = []
OCTOBER = datetime.datetime(2026, 10, 22, 12, tzinfo=ZoneInfo('America/New_York'))
NOVEMBER = datetime.datetime(2026, 11, 1, 0, tzinfo=ZoneInfo('America/New_York'))


class TrexAuctionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.accounts = {(1, 10): (20, []), (2, 10): (20, []), (3, 10): (20, [])}
        self.state = {}
        self.fail_write = False
        accounts = self.accounts
        class Neighbor:
            def __init__(self, uid, gid):
                self.ID, self.family = uid, gid
                self.pull()
            def pull(self):
                xp, inventory = accounts.get((self.ID, self.family), (0, []))
                self.XP, self.inventory = xp, list(inventory)
            def push(self):
                accounts[(self.ID, self.family)] = self.XP, list(self.inventory)
            def get_level(self):
                self.pull()
                return self.XP
            @staticmethod
            def read_all_neighbors():
                return [NS(ID=uid, family=gid, inventory=list(inv)) for (uid,gid),(xp,inv) in accounts.items()]
        self.Neighbor = Neighbor
        def remember(key, value=Ellipsis):
            if value is Ellipsis:
                return deepcopy(self.state.get(key))
            if self.fail_write and value.get('owner_id'):
                raise OSError('Simulated state write failure')
            self.state[key] = deepcopy(value)
            return value
        def strip(owner, levels):
            owner.pull()
            owner.XP -= levels
            owner.push()
        self.guild = NS(id=10, get_member=lambda uid: NS(id=uid), fetch_member=AsyncMock())
        self.refresh = AsyncMock()
        self.env = dict(datetime=datetime, ZoneInfo=ZoneInfo, asyncio=asyncio,
                        _trex_auction_lock=asyncio.Lock(), Neighbor=Neighbor, Item=Item,
                        remember=remember, strip=strip, set_nick=self.refresh, discord=discord,
                        FF=NS(guild=10))
        exec(compile(ast.Module(body=NODES, type_ignores=[]), 'commands.py', 'exec'), self.env)

    async def buy(self, uid, cost, month='2026-10', now=OCTOBER):
        return await self.env['_trex_purchase'](self.Neighbor(uid,10), self.guild, cost, month, now)

    def holders(self):
        return [uid for (uid,gid),(xp,items) in self.accounts.items() if gid==10 and any(i.type=='trex_auction' for i in items)]

    async def test_price_increases_and_ownership_transfers(self):
        first = await self.buy(1, 1)
        self.assertEqual(first['status'], 'purchased')
        self.assertEqual(self.holders(), [1])
        self.assertEqual(self.accounts[(1,10)][0], 19)
        second = await self.buy(2, 2)
        self.assertEqual(second['status'], 'purchased')
        self.assertEqual(self.holders(), [2])
        self.assertEqual(self.accounts[(1,10)][0], 19)  # No refund to the previous owner.
        self.assertEqual(self.accounts[(2,10)][0], 18)
        self.assertEqual(self.state['trex_auction_10']['next_cost'], 3)
        self.assertEqual(self.accounts[(2,10)][1][0].expiration, int(NOVEMBER.timestamp()))
        self.assertEqual({call.args[0].id for call in self.refresh.await_args_list}, {1,2})

    async def test_stale_price_requires_new_confirmation_without_charging(self):
        await self.buy(1,1)
        result = await self.buy(2,1)
        self.assertEqual(result['status'], 'price_changed')
        self.assertEqual(result['cost'], 2)
        self.assertEqual(self.accounts[(2,10)][0], 20)
        self.assertEqual(self.holders(), [1])

    async def test_simultaneous_confirmations_cannot_both_buy_at_the_same_price(self):
        results = await asyncio.gather(self.buy(1,1), self.buy(2,1))
        self.assertEqual(sorted(r['status'] for r in results), ['price_changed','purchased'])
        self.assertEqual(len(self.holders()), 1)
        self.assertEqual(sum(self.accounts[(uid,10)][0] for uid in (1,2)), 39)

    async def test_existing_owner_and_insufficient_levels_do_not_increase_price(self):
        await self.buy(1,1)
        self.assertEqual((await self.buy(1,2))['status'], 'already_owner')
        self.accounts[(2,10)] = (1, [])
        self.assertEqual((await self.buy(2,2))['status'], 'insufficient_levels')
        self.assertEqual(self.state['trex_auction_10']['next_cost'], 2)
        self.assertEqual(self.holders(), [1])

    async def test_month_reset_removes_item_and_resets_price_without_changing_xp(self):
        await self.buy(1,1)
        state = await self.env['_trex_quote'](self.guild, NOVEMBER)
        self.assertEqual(state, dict(month='2026-11', next_cost=1, owner_id=None))
        self.assertEqual(self.holders(), [])
        self.assertEqual(self.accounts[(1,10)][0], 19)
        await self.buy(2,1,month='2026-11',now=NOVEMBER)
        await self.env['_trex_quote'](self.guild, NOVEMBER)
        self.assertEqual(self.holders(), [2])  # Repeated reset is idempotent.

    async def test_previous_month_offer_is_rejected_even_if_price_is_the_same(self):
        result = await self.buy(1,1,month='2026-09')
        self.assertEqual(result['status'], 'price_changed')
        self.assertEqual(self.accounts[(1,10)][0], 20)
        self.assertEqual(self.holders(), [])

    async def test_lazy_reset_catches_up_if_bot_missed_the_first(self):
        await self.buy(1,1)
        later = NOVEMBER + datetime.timedelta(days=5)
        result = await self.buy(2,1,month='2026-11',now=later)
        self.assertEqual(result['status'], 'purchased')
        self.assertEqual(self.holders(), [2])
        self.assertEqual(self.state['trex_auction_10']['next_cost'], 2)

    async def test_initialization_clears_legacy_items_only_in_this_server(self):
        old = Item('Highest Bidder','tag',-1)
        other = Item('Keep me','perk',-1)
        self.accounts[(1,10)] = (20, [old,other])
        self.accounts[(99,20)] = (20, [old])
        await self.env['_trex_quote'](self.guild, OCTOBER)
        self.assertEqual(self.accounts[(1,10)][1], [other])
        self.assertEqual(self.accounts[(99,20)][1], [old])

    async def test_write_failure_restores_levels_and_inventory(self):
        await self.env['_trex_quote'](self.guild, OCTOBER)
        self.fail_write = True
        with self.assertRaises(OSError):
            await self.buy(1,1)
        self.assertEqual(self.accounts[(1,10)], (20, []))
        self.assertEqual(self.state['trex_auction_10']['next_cost'], 1)

    async def test_calendar_uses_eastern_month_boundary(self):
        before = NOVEMBER.astimezone(datetime.timezone.utc) - datetime.timedelta(seconds=1)
        self.assertEqual(self.env['_trex_calendar'](before)[0], '2026-10')
        self.assertEqual(self.env['_trex_calendar'](NOVEMBER)[0], '2026-11')


if __name__ == '__main__':
    unittest.main()
