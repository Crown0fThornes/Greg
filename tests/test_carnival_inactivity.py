import ast
import datetime
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo
import asyncio
import traceback

import discord

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'commands' / 'commands.py'
TREE = ast.parse(SOURCE.read_text())
NAMES = {'_carnival_inactivity_messages', 'carnival_inactivity_review', '_ab_race_has_image'}
NODES = [node for node in TREE.body if getattr(node, 'name', None) in NAMES or
         isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and
         t.id.startswith('_CARNIVAL_') for t in node.targets)]
for node in NODES:
    if isinstance(node, ast.AsyncFunctionDef):
        node.decorator_list = []
ENV = dict(datetime=datetime, discord=discord, FF=NS(guild=1))
exec(compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE), 'exec'), ENV)
NOW = datetime.datetime(2026, 10, 26, 16, tzinfo=datetime.timezone.utc)


def member(uid, joined_days=100):
    return NS(id=uid, bot=False, roles=[NS(id=1342329111359656008)],
              joined_at=NOW-datetime.timedelta(days=joined_days))


class ReportTests(unittest.TestCase):
    def test_week_boundaries_are_exclusive_groups(self):
        members = [member(i) for i in range(1, 7)]
        days = [6, 7, 13, 14, 21, 28]
        last = {m.id: NOW-datetime.timedelta(days=d) for m, d in zip(members, days)}
        text = '\n'.join(ENV['_carnival_inactivity_messages'](members, last, NOW))
        self.assertNotIn('<@1>', text)
        for uid in range(2, 7):
            self.assertEqual(text.count(f'<@{uid}>'), 1)
        self.assertIn('1 week — potentially DM warning\n- <@3>', text)
        self.assertIn('2 weeks — consider for demotion\n- <@4>', text)
        self.assertIn('3 weeks — consider for kick if member\n- <@5>', text)
        self.assertIn('4+ weeks — ALERT: extended inactivity\n- <@6>', text)

    def test_no_submission_uses_join_date_with_grace_period(self):
        members = [member(1, 6), member(2, 14)]
        text = '\n'.join(ENV['_carnival_inactivity_messages'](members, {}, NOW))
        self.assertNotIn('<@1>', text)
        self.assertIn('no submission found; joined 14 days ago', text)
        self.assertIn('2 weeks — consider for demotion', text)

    def test_unknown_join_date_does_not_invent_duration(self):
        person = member(1)
        person.joined_at = None
        text = '\n'.join(ENV['_carnival_inactivity_messages']([person], {}, NOW))
        self.assertIn('duration unknown', text)
        self.assertNotIn('4+ weeks', text)

    def test_reports_fit_discord_and_ping_role_once(self):
        people = [member(i, 100) for i in range(1, 501)]
        reports = ENV['_carnival_inactivity_messages'](people, {}, NOW)
        self.assertGreater(len(reports), 1)
        self.assertTrue(all(len(text) <= 1900 for text in reports))
        self.assertEqual(sum(text.count('<@&1342329281015058442>') for text in reports), 1)
        for person in people:
            self.assertEqual(sum(text.count(f'<@{person.id}>') for text in reports), 1)


class ReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_image_and_current_role_membership(self):
        people = [member(1), member(2), member(3)]
        people[2].roles = []
        actual_now = datetime.datetime.now(datetime.timezone.utc)
        def message(uid, days, image):
            return NS(author=NS(id=uid), created_at=actual_now-datetime.timedelta(days=days),
                      attachments=[NS(content_type='image/png', filename='test.png')] if image else [], embeds=[])
        messages = [message(1, 1, False), message(2, 2, True), message(3, 15, True),
                    message(1, 15, True), message(2, 25, True), message(1, 30, True)]
        class ImageChannel:
            async def history(self, **kwargs):
                self_kwargs = kwargs
                assert self_kwargs == dict(limit=None, oldest_first=False)
                for entry in messages:
                    yield entry
        review_channel = NS(send=AsyncMock())
        class Guild:
            async def fetch_members(self, limit):
                assert limit is None
                for person in people:
                    yield person
            async def fetch_channel(self, cid):
                return ImageChannel() if cid == 1342333687429070918 else review_channel
        await ENV['carnival_inactivity_review'](NS(get_guild=lambda _: Guild()))
        review_channel.send.assert_awaited_once()
        args = review_channel.send.await_args
        text = args.args[0]
        self.assertIn('<@1>', text)
        self.assertNotIn('<@2>', text)
        self.assertNotIn('<@3>', text)
        self.assertIn('2 weeks — consider for demotion', text)
        self.assertFalse(args.kwargs['allowed_mentions'].users)
        self.assertFalse(args.kwargs['allowed_mentions'].everyone)
        self.assertEqual([role.id for role in args.kwargs['allowed_mentions'].roles], [1342329281015058442])


class SchedulerTimezoneTests(unittest.IsolatedAsyncioTestCase):
    def scheduler(self, instant):
        class FixedDateTime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
        tree = ast.parse((ROOT / 'command_handler.py').read_text())
        node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Scheduled')
        env = dict(datetime=NS(datetime=FixedDateTime, time=datetime.time, date=datetime.date),
                   ZoneInfo=ZoneInfo, asyncio=NS(sleep=AsyncMock()), traceback=traceback)
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'command_handler.py', 'exec'), env)
        scheduled = env['Scheduled']
        scheduled._state_loaded = True
        scheduled._save_state = classmethod(lambda cls: None)
        return scheduled

    async def test_eastern_monday_when_server_clock_is_already_tuesday(self):
        instant = datetime.datetime(2026, 10, 27, 1, tzinfo=datetime.timezone.utc)
        scheduled = self.scheduler(instant)
        calls = []
        async def eastern(client):
            calls.append('eastern')
        async def legacy(client):
            calls.append('legacy')
        scheduled(time='12:00', day_of_week=0, timezone='America/New_York')(eastern)
        scheduled(time='00:00', day_of_week=1)(legacy)
        await scheduled.execute(object())
        await scheduled.execute(object())
        self.assertEqual(calls, ['eastern', 'legacy'])
        self.assertEqual(scheduled._state['eastern'], '2026-10-26')
        self.assertEqual(scheduled._state['legacy'], '2026-10-27')

    async def test_eastern_job_waits_until_noon(self):
        scheduled = self.scheduler(datetime.datetime(2026, 10, 26, 15, 59, tzinfo=datetime.timezone.utc))
        called = AsyncMock()
        called.__name__ = 'eastern'
        scheduled(time='12:00', day_of_week=0, timezone='America/New_York')(called)
        await scheduled.execute(object())
        called.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
