from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock
import discord
from commands.rolodex_mentions import prepare_mentions


class MentionTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetches_each_account_and_keeps_numeric_fallback(self):
        guild=NS(fetch_member=AsyncMock())
        result=await prepare_mentions(guild,'Is this <@123>? Also <@123> or <@456> (456)')
        self.assertEqual(result,'Is this <@123> (123)? Also <@123> (123) or <@456> (456)')
        self.assertEqual(guild.fetch_member.await_count,2)

    async def test_departed_account_still_shows_id(self):
        guild=NS(fetch_member=AsyncMock(side_effect=discord.NotFound(NS(status=404,reason='Not Found'),'Unknown member')))
        self.assertEqual(await prepare_mentions(guild,'<@123>'),' <@123> (123)'.lstrip())

    async def test_plain_name_is_present_even_if_discord_shows_unknown_mention(self):
        guild=NS(fetch_member=AsyncMock(return_value=NS(display_name='[P] Lauren',name='lauren')))
        result=await prepare_mentions(guild,'Is this <@123>?')
        self.assertIn('Lauren',result)
        self.assertIn('<@123> (123)',result)
        self.assertTrue(result.startswith('Is this '))
        self.assertEqual(await prepare_mentions(guild,result),result)

    async def test_failed_fetch_uses_cached_name_without_losing_id(self):
        guild=NS(fetch_member=AsyncMock(side_effect=discord.NotFound(NS(status=404,reason='Not Found'),'Unknown member')),
                 get_member=lambda uid:NS(display_name='Known neighbor'))
        self.assertEqual(await prepare_mentions(guild,'<@123>'),'Known neighbor — <@123> (123)')
