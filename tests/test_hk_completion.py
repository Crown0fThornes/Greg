from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

from commands.hk_completion import completion_followups
from commands.hk_reminders import DeliveryLog,NEIGHBORHOODS


class CompletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/'hk.sqlite3'
        self.delivery=DeliveryLog(self.path)
        self.now=datetime(2026,11,1,12,tzinfo=timezone.utc)
        self.nh=next(iter(NEIGHBORHOODS))
        self.config={self.nh:NEIGHBORHOODS[self.nh]}
        self.key=(123,self.nh,'2026-10-27',0)
        self.delivery.claim(self.key)
        self.delivery.finish(self.key,456,sent_at=self.now.timestamp())
        self.people=[NS(id=999,bot=True)]
        async def users():
            for user in self.people:
                yield user
        self.message=NS(content='**Check waitlist**\n<@123>',reactions=[NS(emoji='✅',users=users)])
        self.channel=NS(fetch_message=AsyncMock(return_value=self.message),send=AsyncMock(return_value=NS(id=789)))
        self.guild=NS(id=647883751853916162,fetch_channel=AsyncMock(return_value=self.channel))

    async def test_waits_full_24_hours_then_role_only_once_even_after_restart(self):
        await completion_followups(self.guild,self.delivery,self.config,self.now+timedelta(hours=24,seconds=-1))
        self.channel.send.assert_not_awaited()
        await completion_followups(self.guild,self.delivery,self.config,self.now+timedelta(hours=24))
        self.channel.send.assert_awaited_once()
        body=self.channel.send.call_args.args[0]
        self.assertTrue(body.startswith('**HK task follow-up**'))
        self.assertIn(f'<@&{self.config[self.nh][1]}>',body)
        self.assertNotIn('<@123>',body)
        allowed=self.channel.send.call_args.kwargs['allowed_mentions']
        self.assertFalse(allowed.users)
        self.assertFalse(allowed.everyone)
        self.assertEqual([r.id for r in allowed.roles],[self.config[self.nh][1]])
        await completion_followups(self.guild,DeliveryLog(self.path),self.config,self.now+timedelta(days=2))
        self.channel.send.assert_awaited_once()

    async def test_any_human_checkmark_counts_not_only_assignee(self):
        self.people.append(NS(id=777,bot=False))
        await completion_followups(self.guild,self.delivery,self.config,self.now+timedelta(days=1))
        self.channel.send.assert_not_awaited()
        with self.delivery.connection() as db:
            self.assertEqual(db.execute('SELECT status FROM completion_followup').fetchone()[0],'completed')

    async def test_no_check_reaction_triggers_followup(self):
        self.message.reactions=[]
        await completion_followups(self.guild,self.delivery,self.config,self.now+timedelta(days=1))
        self.channel.send.assert_awaited_once()

    async def test_timeout_is_not_repeated(self):
        self.channel.send.side_effect=TimeoutError('uncertain')
        with self.assertLogs('commands.hk_completion',level='ERROR'):
            await completion_followups(self.guild,self.delivery,self.config,self.now+timedelta(days=1))
        await completion_followups(self.guild,self.delivery,self.config,self.now+timedelta(days=2))
        self.channel.send.assert_awaited_once()
