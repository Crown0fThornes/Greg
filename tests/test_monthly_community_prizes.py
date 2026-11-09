from datetime import datetime,timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock,patch

import discord
from commands import monthly_community_prizes as prizes


class PrizeTests(unittest.TestCase):
    def test_previous_month_and_host_only_not_winner(self):
        start,end=prizes.previous_month(datetime(2027,1,2,18,tzinfo=timezone.utc))
        self.assertEqual((start.month,start.day,end.month,end.day),(12,1,1,1))
        embed=discord.Embed(title='20 Bolts',description='Hosted by: <@123>\nWinners: <@456>')
        self.assertEqual(prizes.giveaway_host(embed),123)
        embed=discord.Embed().add_field(name='Hosted by',value='<@!789>')
        self.assertEqual(prizes.giveaway_host(embed),789)
        self.assertIsNone(prizes.giveaway_host(discord.Embed(description='Winners: <@456>')))


class AnnouncementTests(unittest.IsolatedAsyncioTestCase):
    async def test_attached_image_prizes_and_separate_claim_message_once(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path=Path(tmp.name)/'prizes.sqlite3'
        file=NS(close=lambda:None)
        attachment=NS(id=55,to_file=AsyncMock(return_value=file))
        source=NS(fetch_message=AsyncMock(return_value=NS(attachments=[attachment])))
        target=NS(send=AsyncMock(return_value=NS(id=999)))
        guild=NS(fetch_channel=AsyncMock(side_effect=lambda cid:target if cid==prizes.ANNOUNCEMENTS else source))
        client=NS(get_guild=lambda uid:guild)
        result=dict(host=123,giveaway=dict(prize='20 Bolts',message_id=44),image=dict(user_id=456,channel_id=prizes.PARK[0],message_id=66,attachment_id=55))
        with patch.object(prizes,'draw',new=AsyncMock(return_value=result)) as draw:
            for _ in range(2):
                await prizes.announce(client,now=datetime(2026,12,2,18,tzinfo=timezone.utc),path=path)
            draw.assert_awaited_once()
        self.assertEqual(target.send.await_count,2)
        first,second=target.send.call_args_list
        self.assertIn('<@123>',first.args[0])
        self.assertIn('<@456>',first.args[0])
        self.assertIn('Who gave away: 20 Bolts',first.args[0])
        self.assertIs(first.kwargs['file'],file)
        self.assertTrue(first.kwargs['allowed_mentions'].everyone)
        self.assertEqual(second.args[0],'Open a ticket here to claim your prize: <#1033207181857800242>')
        self.assertFalse(second.kwargs['allowed_mentions'].everyone)

    async def test_distinct_hosts_have_equal_entries_and_only_previous_month_images(self):
        start,end=prizes.previous_month(datetime(2026,12,2,18,tzinfo=timezone.utc))
        def giveaway(mid,host):
            return NS(id=mid,author=NS(id=prizes.GIVEAWAYBOT),created_at=start,application_id=None,
                      embeds=[discord.Embed(title='Bolts',description=f'Hosted by: <@{host}>')])
        giveaways=[giveaway(1,1),giveaway(2,1),giveaway(3,2)]
        image=NS(id=9,author=NS(id=2,bot=False),created_at=start,
                 attachments=[NS(id=10,content_type='image/png',filename='image.png')])
        def channel(cid):
            async def history(**kwargs):
                for message in giveaways if cid==prizes.GIVEAWAYS else [image] if cid==prizes.PARK[0] else []:
                    yield message
            return NS(history=history)
        guild=NS(fetch_channel=AsyncMock(side_effect=channel),
                 get_member=lambda uid:NS(bot=False,roles=[NS(id=1181330910747054211)]))
        with patch.object(prizes.random,'choice',side_effect=lambda values:values[0]) as choice:
            result=await prizes.draw(guild,start,end)
        self.assertEqual(choice.call_args_list[0].args[0],[1,2])
        self.assertEqual(result['host'],1)
        self.assertEqual(result['image']['user_id'],2)
