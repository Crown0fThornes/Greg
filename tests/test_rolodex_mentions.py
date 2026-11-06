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
