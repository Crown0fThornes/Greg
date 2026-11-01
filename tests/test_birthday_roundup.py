from datetime import datetime, timezone
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

import discord
from commands.birthday_roundup import month_number,collect,roundup_messages


class BirthdayRoundupTests(unittest.TestCase):
    def test_month_names_numbers_and_previous_month_default(self):
        for value in ['October','oct','10']:
            self.assertEqual(month_number(value),10)
        self.assertEqual(month_number(now=datetime(2026,11,1,tzinfo=timezone.utc)),10)
        self.assertEqual(month_number(now=datetime(2027,1,1,tzinfo=timezone.utc)),12)
        with self.assertRaises(ValueError):
            month_number('13')

    def test_roundup_preserves_original_style_and_splits(self):
        pages=roundup_messages(10,[(i,(10,15)) for i in range(200)])
        self.assertTrue(pages[0].startswith("**Let's celebrate all of our October Birthdays one more time!**"))
        self.assertIn('<@1> (October 15)',''.join(pages))
        self.assertTrue(pages[-1].endswith('@everyone'))
        self.assertTrue(all(len(page)<2000 for page in pages))


class CollectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_newest_valid_submission_wins_and_departed_members_excluded(self):
        data=[(1,'11/3'),(1,'10/1'),(2,'invalid'),(2,'10/15'),(3,'10/2'),(4,'10/8')]
        async def history(**kwargs):
            self.assertEqual(kwargs,dict(limit=None,oldest_first=False))
            for uid,content in data:
                yield NS(author=NS(id=uid,bot=uid==4),content=content)
        channel=NS(history=history)
        async def fetch(uid):
            raise discord.NotFound(NS(status=404,reason='Not found'),'Left guild')
        guild=NS(fetch_channel=AsyncMock(return_value=channel),
                 get_member=lambda uid:NS(id=uid,bot=False) if uid!=3 else None,
                 fetch_member=AsyncMock(side_effect=fetch))
        def normalize(content):
            return tuple(map(int,content.split('/'))) if '/' in content else None
        self.assertEqual(await collect(guild,10,normalize),[(2,(10,15))])
