from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

from commands import recruitment_review as review


class ReviewTests(unittest.TestCase):
    def test_previous_week_uses_fixed_server_time_across_year_boundary(self):
        start, end = review.previous_week(datetime(2027,1,4,12,tzinfo=timezone.utc))
        self.assertEqual(start.isoformat(), '2026-12-28T00:00:00-04:00')
        self.assertEqual(end.isoformat(), '2027-01-04T00:00:00-04:00')
        # It is still Sunday ST: the current incomplete week is not included.
        start, end = review.previous_week(datetime(2027,1,4,3,tzinfo=timezone.utc))
        self.assertEqual(end.day, 28)

    def test_schedule_parses_reminder_format_and_multiple_posters(self):
        schedule = review.parse_schedule('**Schedule**\nMonday: <@123>\n**Tuesday** — <@!456>, <@789>\nSunday: <@&99>')
        self.assertEqual(schedule, {'0':[123], '1':[456,789]})

    def test_lift_is_first_and_congratulates_its_poster_not_just_busiest_day(self):
        start, _ = review.previous_week(datetime(2026,11,16,12,tzinfo=timezone.utc))
        text = review.report(start, [10,7,1,0,0,0,0], {'0':[123],'1':[456]},
                             [[9,1,1,0,0,0,0]]*4)
        self.assertLess(text.index('Biggest lift'), text.index('Most recruits'))
        self.assertLess(text.index('<@456>'), text.index('<@123>'))
        self.assertIn('**+6.0**', text)
        self.assertIn('**Total recruits: 18**', text)
        self.assertIn('average week of 11.0', text)
        self.assertIn('**+7.0 recruits (+64%)**', text)

    def test_ties_and_zero_baselines(self):
        start, _ = review.previous_week(datetime(2026,11,16,12,tzinfo=timezone.utc))
        text = review.report(start, [2,2,0,0,0,0,0], {'0':[123],'1':[456]}, [[0]*7]*4)
        self.assertEqual(text.count('<@123>'), 1)
        self.assertEqual(text.count('<@456>'), 1)
        self.assertIn('**+2.0** above its usual 0.0', text)
        self.assertNotIn('inf', text)
        text = review.report(start, [0]*7, {'0':[123]}, [])
        self.assertNotIn('<@123>', text)
        self.assertIn('No server joins', text)
        self.assertIn('(0 so far)', text)

    def test_long_reports_fit_discord_messages(self):
        text = ('Long report line\n'*400)
        pages = list(review.pages(text))
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page)<=1900 for page in pages))
        self.assertEqual(''.join(page.replace('\n','') for page in pages), text.replace('\n',''))


class AsyncReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_counts_only_greg_welcomes_with_correct_st_dates_and_boundaries(self):
        start, end = review.previous_week(datetime(2026,11,16,12,tzinfo=timezone.utc))
        def message(mid, time, author=99, content='**Welcome to Town, <@123>!**'):
            return NS(id=mid, created_at=time, author=NS(id=author), content=content)
        messages = [message(1,start), message(1,start), message(2,end),
                    message(3,start,author=123), message(4,start,content='Happy Birthday <@123>'),
                    message(5,datetime(2026,11,10,2,tzinfo=timezone.utc)),
                    message(6,datetime(2026,11,10,5,tzinfo=timezone.utc))]
        async def history(**kwargs):
            for item in messages:
                yield item
        counts = await review.count_joins(NS(history=history),99,start,end)
        # Rejoining users count again; duplicate message IDs do not.
        self.assertEqual(counts, [2,1,0,0,0,0,0])

    async def test_saved_weeks_are_baseline_and_repeat_runs_do_not_post_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'review.sqlite3'
            target = NS(pins=AsyncMock(return_value=[NS(content='Monday: <@123>')]),
                        send=AsyncMock(return_value=NS(id=999)))
            guild = NS(fetch_channel=AsyncMock(side_effect=lambda cid:target if cid==review.RECRUITMENT else NS()))
            client = NS(get_guild=lambda gid:guild,user=NS(id=99))
            with patch.object(review,'count_joins',new=AsyncMock(return_value=[3,0,0,0,0,0,0])) as count:
                for _ in range(2):
                    await review.review(client,now=datetime(2026,11,16,12,tzinfo=timezone.utc),path=path)
                count.assert_awaited_once()
            target.send.assert_awaited_once()
            self.assertIn('<@123>',target.send.call_args.args[0])
            self.assertFalse(target.send.call_args.kwargs['allowed_mentions'].everyone)
            with review.connect(path) as db:
                self.assertEqual(db.execute('SELECT status FROM week').fetchone()[0], 'sent')
