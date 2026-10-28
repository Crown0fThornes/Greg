import datetime as dt
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

from commands.hk_reminders import HKReminders, NEIGHBORHOODS, SERVER_TIME, due, parse_task, subscribed


class ParsingTests(unittest.TestCase):
    def test_markdown_am_pm_24_hour_and_invalid(self):
        task=parse_task('**New Joins / Tuesday / 8:00 AM**\n\nCheck the new neighbors.')
        self.assertEqual((task.weekday,task.hour,task.minute,task.body),(1,8,0,'Check the new neighbors.'))
        self.assertEqual(parse_task('Task / Monday / 12:00 AM').hour,0)
        self.assertEqual(parse_task('Task / Monday / 12:00 PM').hour,12)
        self.assertEqual(parse_task('Task / Friday / 23:59 (ST)').hour,23)
        for content in ['Instructions:', 'Task / Someday / 8:00 AM','Task / Monday / 13:00 PM','Task / Monday / 24:00','Task / Monday / 8:70']:
            self.assertIsNone(parse_task(content))

    def test_fixed_offset_winter_and_summer_and_grace(self):
        task=parse_task('Task / Tuesday / 8:00 AM')
        for month,day in [(1,6),(10,27)]:
            now=dt.datetime(2026,month,day,12,0,tzinfo=dt.timezone.utc)
            self.assertTrue(due(task,now))
            self.assertFalse(due(task,now-dt.timedelta(seconds=1)))
            self.assertTrue(due(task,now+dt.timedelta(minutes=9,seconds=59)))
            self.assertFalse(due(task,now+dt.timedelta(minutes=10)))
        self.assertEqual(SERVER_TIME.utcoffset(None),dt.timedelta(hours=-4))

    def test_logos_only(self):
        logo=next(iter(NEIGHBORHOODS))
        message=NS(reactions=[NS(emoji=NS(id=logo),count=1),NS(emoji='⏰',count=10),NS(emoji=NS(id=999),count=2)])
        self.assertEqual(subscribed(message),{logo})


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'hk.sqlite3'
        self.now=dt.datetime(2026,10,27,12,0,tzinfo=dt.timezone.utc)
        self.logos=list(NEIGHBORHOODS)[:2]
        self.message=NS(id=123,content='New Joins / Tuesday / 8:00 AM\nCheck in. @everyone <@123>',
                        reactions=[NS(emoji=NS(id=x),count=1) for x in self.logos])
        async def history(**kwargs):
            self.assertIsNone(kwargs['limit'])
            yield self.message
        self.signup=NS(history=history,fetch_message=AsyncMock(return_value=self.message))
        self.targets={value[0]:NS(send=AsyncMock(return_value=NS(id=999))) for value in NEIGHBORHOODS.values()}
        async def fetch(cid):
            return self.targets[cid] if cid in self.targets else self.signup
        self.guild=NS(fetch_channel=AsyncMock(side_effect=fetch))
        self.client=NS(get_guild=lambda gid:self.guild)

    async def test_dispatch_destinations_scoped_mentions_restart_no_duplicate(self):
        await HKReminders(self.path).run(self.client,now=self.now)
        for logo in self.logos:
            channel,role=NEIGHBORHOODS[logo]
            target=self.targets[channel]
            target.send.assert_awaited_once()
            self.assertIn(f'<@&{role}>',target.send.call_args.args[0])
            mentions=target.send.call_args.kwargs['allowed_mentions']
            self.assertFalse(mentions.everyone)
            self.assertFalse(mentions.users)
            self.assertEqual([r.id for r in mentions.roles],[role])
        await HKReminders(self.path).run(self.client,now=self.now+dt.timedelta(minutes=1))
        self.assertTrue(all(self.targets[NEIGHBORHOODS[x][0]].send.await_count==1 for x in self.logos))

    async def test_fresh_reaction_removal_and_edited_schedule_cancel(self):
        self.signup.fetch_message.return_value=NS(id=123,content=self.message.content,reactions=[])
        await HKReminders(self.path).run(self.client,now=self.now)
        self.assertTrue(all(t.send.await_count==0 for t in self.targets.values()))
        self.signup.fetch_message.return_value=NS(id=123,content='Task / Wednesday / 8:00 AM',reactions=self.message.reactions)
        await HKReminders(self.path).run(self.client,now=self.now)
        self.assertTrue(all(t.send.await_count==0 for t in self.targets.values()))

    async def test_no_early_or_old_delivery(self):
        for now in [self.now-dt.timedelta(minutes=1),self.now+dt.timedelta(minutes=10)]:
            await HKReminders(self.path).run(self.client,now=now)
        self.assertTrue(all(t.send.await_count==0 for t in self.targets.values()))

    async def test_next_week_is_delivered(self):
        runner=HKReminders(self.path)
        await runner.run(self.client,now=self.now)
        await runner.run(self.client,now=self.now+dt.timedelta(days=7))
        self.assertTrue(all(self.targets[NEIGHBORHOODS[x][0]].send.await_count==2 for x in self.logos))

    async def test_uncertain_delivery_does_not_reping_on_restart(self):
        target=self.targets[NEIGHBORHOODS[self.logos[0]][0]]
        target.send.side_effect=TimeoutError('uncertain')
        with self.assertLogs('commands.hk_reminders',level='ERROR'):
            await HKReminders(self.path).run(self.client,now=self.now)
        await HKReminders(self.path).run(self.client,now=self.now+dt.timedelta(minutes=1))
        self.assertEqual(target.send.await_count,1)
