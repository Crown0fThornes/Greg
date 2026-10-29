from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

import discord
from commands.hk_reminders import DeliveryLog, parse_task, send_task_dms


class TaskDMTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/'hk.sqlite3'
        self.log=DeliveryLog(self.path)
        self.task=parse_task('New Joins / 👋 / Tuesday / 8:00 AM\nCheck in with new players.')
        self.message=NS(id=123)
        self.users={uid:NS(send=AsyncMock(return_value=NS(id=uid+1000))) for uid in [1,2]}
        self.client=NS(get_user=lambda uid:self.users[uid])

    async def test_dm_each_volunteer_once_across_restarts_and_no_mentions(self):
        await send_task_dms(self.client,self.log,self.task,self.message,[1,2],'2026-10-27')
        await send_task_dms(self.client,DeliveryLog(self.path),self.task,self.message,[1,2],'2026-10-27')
        for user in self.users.values():
            user.send.assert_awaited_once()
            self.assertTrue(user.send.call_args.args[0].startswith('**New Joins**'))
            self.assertIn('Check in with new players.',user.send.call_args.args[0])
            self.assertNotIn('<@&',user.send.call_args.args[0])
            self.assertFalse(user.send.call_args.kwargs['allowed_mentions'].users)

    async def test_role_fallback_has_no_dm(self):
        await send_task_dms(self.client,self.log,self.task,self.message,[],'2026-10-27')
        for user in self.users.values():
            user.send.assert_not_awaited()

    async def test_closed_dm_does_not_block_other_volunteer(self):
        self.users[1].send.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'DM closed')
        with self.assertLogs('commands.hk_reminders',level='WARNING'):
            await send_task_dms(self.client,self.log,self.task,self.message,[1,2],'2026-10-27')
        self.users[2].send.assert_awaited_once()
        with self.log.connection() as db:
            self.assertEqual(db.execute('SELECT status FROM dm_delivery WHERE user_id=1').fetchone()[0],'blocked')

    async def test_new_week_delivers_again(self):
        for week in ['2026-10-27','2026-11-03']:
            await send_task_dms(self.client,self.log,self.task,self.message,[1],week)
        self.assertEqual(self.users[1].send.await_count,2)
