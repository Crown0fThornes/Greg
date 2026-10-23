import ast
import datetime
import json
from pathlib import Path
import time
from types import SimpleNamespace as NS
import unicodedata
import unittest
from unittest.mock import AsyncMock

import discord
from custom_types import Item, Neighbor

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'lookups/rss.json').read_text())
FAMILIES = json.loads((ROOT / 'lookups/families.json').read_text())
RESERVED = json.loads((ROOT / 'lookups/nickname_emoji_reserved.json').read_text())['reserved']
CATEGORY = next(c for c in CATALOG if c['name'] == 'Server Perks')
PRODUCT = next(i for i in CATEGORY['items'] if i['type'] == 'custom_nickname_emoji')
TREE = ast.parse((ROOT / 'commands/commands.py').read_text())
NODES = [node for node in TREE.body if getattr(node, 'name', None) in {'rss', '_rss_item_cost', '_custom_nickname_emoji_error'}]
for node in NODES:
    if isinstance(node, ast.AsyncFunctionDef):
        node.decorator_list = []
UNICODES = dict(check='✅', back='⏏', bank='🏦', locked='🔒', unlocked='🔓')


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(unicodedata=unicodedata, unicodes=UNICODES,
                        Neighbor=Neighbor, Context=object, ResponsePackage=object)
        exec(compile(ast.Module(body=NODES, type_ignores=[]), 'commands.py', 'exec'), self.env)

    def error(self, emoji, catalog=CATALOG):
        return self.env['_custom_nickname_emoji_error'](emoji, FAMILIES, catalog, RESERVED)

    def test_hearts_families_and_reserved_variants_are_blocked(self):
        for emoji in ('❤️', '❤', '🩵', '💕', '😍', '🫶🏾', '❤️‍🔥', '😘', '💌', '🦖', '👑', '🏆', '🦛', '🐧', '🦊'):
            with self.subTest(emoji=emoji):
                self.assertIsNotNone(self.error(emoji))

    def test_event_emoji_overlap_is_allowed(self):
        for emoji in ('🎂', '🍁', '🐲', '🍂', '🎃', '🎡', '👩‍🌾', '1️⃣'):
            self.assertIsNone(self.error(emoji), emoji)
        events = [{'items': [{'type': 'event_emoji', 'emoji': '🦄'}]}]
        self.assertIsNone(self.error('🦄', events))

    def test_existing_shop_tag_emojis_are_reserved_dynamically(self):
        catalog = [{'items': [{'type': 'tag', 'emoji': '🦄', 'values': ['1F680']}]}]
        self.assertIsNotNone(self.error('🦄', catalog))
        self.assertIsNotNone(self.error('🚀', catalog))

    def test_custom_discord_emojis_and_whitespace_are_rejected(self):
        for emoji in ('', '<:frog:12345>', '🌷 🎃', '🌷\n🎃'):
            self.assertIsNotNone(self.error(emoji))


class PurchaseTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.items = []
        self.level = 25
        self.requests = []
        self.deductions = []
        self.target = NS(edit=AsyncMock(), clear_reactions=AsyncMock(), add_reaction=AsyncMock(), id=456)
        self.context = NS(guild=NS(id=1, fetch_member=AsyncMock(return_value=NS(id=123))),
                          channel=NS(id=2), send=AsyncMock())
        self.target_context = NS(message=self.target)
        self.activator = NS(ID=123, get_level=lambda: self.level,
                            get_item_of_name=lambda name: next((i for i in self.items if i.name == name), None),
                            bestow_item=lambda item: self.items.append(item),
                            expire_items=lambda: self.items.__setitem__(slice(None), [i for i in self.items if not i.is_expired()]))
        def request(func, name, kind, activation, response, key=None, **values):
            self.requests.append(NS(func=func, name=name, key=key, values=values,
                                    activation_context=activation, response_context=response))
        def strip(activator, levels):
            self.deductions.append(levels)
            self.level -= levels
        self.env = dict(json=json, time=time, datetime=datetime, discord=discord,
                        unicodedata=unicodedata, unicodes=UNICODES, Neighbor=Neighbor,
                        Context=object, ResponsePackage=object, ResponseRequest=request,
                        strip=strip, Item=Item, set_nick=AsyncMock(), set_roles=AsyncMock())
        exec(compile(ast.Module(body=NODES, type_ignores=[]), 'commands.py', 'exec'), self.env)

    async def call(self, name, content, item=None, key=None):
        response = NS(name=name, content=content, activation_context=self.context,
                      response_context=self.target_context, key=key,
                      values=dict(category=CATEGORY, item=dict(PRODUCT) if item is None else item))
        await self.env['rss'](self.activator, self.context, response)
        return response

    async def choose(self, emoji):
        await self.call('item', NS(name=PRODUCT['emoji']))
        self.assertEqual(self.requests[-1].name, 'custom_emoji_choice')
        self.assertEqual(self.deductions, [])
        await self.call('custom_emoji_choice', emoji, key=self.requests[-1].key)

    async def test_full_purchase_requires_choice_then_confirmation(self):
        await self.choose('🦄')
        self.assertEqual(self.requests[-1].name, 'confirmation')
        self.assertEqual(self.deductions, [])
        self.assertNotIn('🏦', self.target.add_reaction.await_args_list[-1].args)
        before = time.time()
        await self.call('confirmation', NS(name='✅'), self.requests[-1].values['item'])
        self.assertEqual(self.deductions, [20])
        self.assertEqual(self.level, 5)
        self.assertEqual(len(self.items), 1)
        item = self.items[0]
        self.assertEqual(item.type, 'custom_nickname_emoji')
        self.assertEqual(item.get_value('emoji'), '🦄')
        self.assertTrue(before + 28*86400 - 1 <= item.expiration <= time.time() + 28*86400)
        self.env['set_nick'].assert_awaited_once()

    async def test_owner_can_test_at_zero_levels_without_any_deduction(self):
        self.activator.ID = 355169964027805698
        self.level = 0
        await self.choose('🦄')
        self.assertIn('Cost: 0 levels (developer testing)', self.target.edit.await_args.kwargs['content'])
        await self.call('confirmation', NS(name='✅'), self.requests[-1].values['item'])
        self.assertEqual(self.deductions, [])
        self.assertEqual(self.level, 0)
        self.assertEqual(len(self.items), 1)

    async def test_free_testing_is_scoped_to_owner_and_custom_emoji_only(self):
        price = self.env['_rss_item_cost']
        self.assertEqual(price(PRODUCT, 123), 20)
        self.assertEqual(price(PRODUCT, 355169964027805698), 0)
        self.assertEqual(price(dict(type='trex_auction', cost=7), 355169964027805698), 7)
        self.assertEqual(price(dict(type='tag', cost=5), 355169964027805698), 5)

    async def test_reserved_choice_does_not_charge_and_allows_retry(self):
        await self.choose('🦖')
        self.assertEqual(self.requests[-1].name, 'custom_emoji_choice')
        self.assertEqual(self.deductions, [])
        self.assertEqual(self.items, [])
        key = self.requests[-1].key
        self.assertTrue(key(NS(author_id=123, channel=NS(id=2))))
        self.assertFalse(key(NS(author_id=999, channel=NS(id=2))))

    async def test_invalid_reaction_is_not_purchased(self):
        await self.call('item', NS(name=PRODUCT['emoji']))
        self.target.add_reaction.side_effect = discord.HTTPException(NS(status=400, reason='Bad Request'), 'Unknown emoji')
        await self.call('custom_emoji_choice', 'notemoji', key=self.requests[-1].key)
        self.assertEqual(self.requests[-1].name, 'custom_emoji_choice')
        self.assertEqual(self.deductions, [])

    async def test_duplicate_purchase_is_not_charged(self):
        self.items.append(Item(PRODUCT['name'], PRODUCT['type'], int(time.time())+100, emoji='🦄'))
        await self.choose('🚀')
        await self.call('confirmation', NS(name='✅'), self.requests[-1].values['item'])
        self.assertEqual(self.deductions, [])
        self.assertEqual(len(self.items), 1)

    async def test_expired_custom_emoji_can_be_bought_again(self):
        self.items.append(Item(PRODUCT['name'], PRODUCT['type'], 1, emoji='🦄'))
        await self.choose('🚀')
        await self.call('confirmation', NS(name='✅'), self.requests[-1].values['item'])
        self.assertEqual(self.deductions, [20])
        self.assertEqual(len(self.items), 1)
        self.assertEqual(self.items[0].get_value('emoji'), '🚀')

    async def test_insufficient_levels_do_not_grant_or_charge(self):
        self.level = 19
        await self.choose('🦄')
        await self.call('confirmation', NS(name='✅'), self.requests[-1].values['item'])
        self.assertEqual(self.items, [])
        self.assertEqual(self.deductions, [])

    async def test_bank_payment_is_not_available_for_custom_emoji(self):
        await self.call('confirmation', NS(name='🏦'), dict(PRODUCT, selected_emoji='🦄'))
        self.assertEqual(self.items, [])
        self.assertEqual(self.deductions, [])

    async def test_trex_menu_quotes_current_price_and_uses_exclusive_purchase(self):
        trex = next(item for item in CATEGORY['items'] if item['type'] == 'trex_auction')
        self.env['FF'] = NS(guild=1)
        self.env['_trex_quote'] = AsyncMock(return_value=dict(month='2026-10', next_cost=3, owner_id=999))
        self.env['_trex_purchase'] = AsyncMock(return_value=dict(status='purchased', cost=3, next_cost=4))
        await self.call('item', NS(name='🦖'))
        quoted = self.requests[-1].values['item']
        self.assertEqual(quoted['cost'], 3)
        self.assertEqual(quoted['auction_month'], '2026-10')
        self.assertNotIn('🏦', [call.args[0] for call in self.target.add_reaction.await_args_list])
        await self.call('confirmation', NS(name='✅'), quoted)
        self.env['_trex_purchase'].assert_awaited_once_with(self.activator, self.context.guild, 3, '2026-10')
        self.assertEqual(self.deductions, [])  # The auction helper owns charging/transfer.

    async def test_trex_changed_price_refreshes_offer_instead_of_charging(self):
        trex = next(item for item in CATEGORY['items'] if item['type'] == 'trex_auction')
        self.env['FF'] = NS(guild=1)
        self.env['_trex_quote'] = AsyncMock(return_value=dict(month='2026-10', next_cost=2, owner_id=999))
        self.env['_trex_purchase'] = AsyncMock(return_value=dict(status='price_changed', cost=2))
        await self.call('confirmation', NS(name='✅'), dict(trex, cost=1, auction_month='2026-10'))
        self.assertEqual(self.requests[-1].name, 'confirmation')
        self.assertEqual(self.requests[-1].values['item']['cost'], 2)
        self.assertEqual(self.deductions, [])


class InventoryDisplayTests(unittest.TestCase):
    def test_custom_emoji_is_visible_without_changing_stored_name(self):
        item = Item('Custom Nickname Emoji', 'custom_nickname_emoji', -1, emoji='🦄')
        self.assertTrue(str(item).startswith('🦄 Custom Nickname Emoji;'))
        self.assertEqual(item.name, 'Custom Nickname Emoji')
        self.assertTrue(Item.decode(item.encode()).get_value('emoji') == '🦄')

    def test_trex_is_visible_in_inventory(self):
        item = Item('Highest Bidder', 'trex_auction', int(time.time()) + 86400, emoji='🦖')
        self.assertTrue(str(item).startswith('🦖 Highest Bidder; expires in'))


if __name__ == '__main__':
    unittest.main()
