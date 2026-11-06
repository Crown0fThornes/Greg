from datetime import date,datetime,timezone
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

from commands.farmmas_season import season_messages,announce,LOGO_ID


class SeasonTests(unittest.TestCase):
    def test_countdown_dates_and_exact_copy(self):
        self.assertIn('arrives in 8 days!!',season_messages(date(2026,11,1),'logo')[0])
        self.assertIn('arrives in 1 day!!',season_messages(date(2026,11,8),'logo')[0])
        for day in range(1,9):
            messages=season_messages(date(2026,11,day),'logo')
            self.assertEqual(len(messages),1)
            self.assertIn('December 9th to 20th',messages[0])
            self.assertTrue(messages[0].endswith('@everyone'))
            self.assertIn('Use `$info farmmas` in <#784150346397253682>',messages[0])

    def test_arrival_and_no_posts_outside_window(self):
        messages=season_messages(date(2026,11,9),'<:farmmas_ff_logo:1170071779037945907>')
        self.assertTrue(messages[0].startswith('# Farmmas season has arrived!!'))
        self.assertIn("**We've only got 1 month to wait before the best FF holiday begins!**",messages[0])
        self.assertTrue(messages[0].endswith('@everyone'))
        self.assertNotIn('@everyone',messages[1])
        self.assertEqual(messages[1].count(str(LOGO_ID)),3)
        for today in [date(2026,10,31),date(2026,11,10),date(2026,12,9)]:
            self.assertEqual(season_messages(today,'logo'),[])


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_november_ninth_sends_two_separate_messages(self):
        channel=NS(send=AsyncMock())
        guild=NS(fetch_channel=AsyncMock(return_value=channel))
        client=NS(get_guild=lambda uid:guild,get_emoji=lambda uid:None)
        await announce(client,now=datetime(2026,11,9,16,tzinfo=timezone.utc))
        self.assertEqual(channel.send.await_count,2)
        self.assertTrue(channel.send.call_args_list[0].kwargs['allowed_mentions'].everyone)
        self.assertFalse(channel.send.call_args_list[1].kwargs['allowed_mentions'].everyone)
        self.assertEqual(channel.send.call_args_list[1].args[0], ' '.join(['<:farmmas_ff_logo:1170071779037945907>']*3))
