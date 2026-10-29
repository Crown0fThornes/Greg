from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

import discord
from commands.personal_reminders import parse_reminder, ReminderRunner, ReminderStore, create_reminder, GUILD_ID

NOW=datetime(2026,10,28,12,tzinfo=timezone.utc)


class ParsingTests(unittest.TestCase):
    def test_default_time_and_preserved_colons(self):
        when,body=parse_reminder('$remindme 10/29/2026: Check this: the signup',NOW)
        self.assertEqual(when.astimezone(timezone.utc).isoformat(),'2026-10-29T12:00:00+00:00')
        self.assertEqual(body,'Check this: the signup')

    def test_explicit_clock_and_fixed_offset_winter(self):
        when,_=parse_reminder('$remindme 1/5/2027 12:30 AM: text',NOW)
        self.assertEqual(when.astimezone(timezone.utc).hour,4)
        when,_=parse_reminder('$remindme 10/29/2026 12:30 PM: text',NOW)
        self.assertEqual(when.astimezone(timezone.utc).hour,16)

    def test_invalid_dates_times_past_missing_colon_text(self):
        for content in ['$remindme 2/30/2027: text','$remindme 10/29/2026 13:00 PM: text',
                        '$remindme 10/29/2026 9:60 AM: text','$remindme 10/27/2026: text',
                        '$remindme 10/29/2026 text','$remindme 10/29/2026: ',
                        '$remindme 10/29/2026: '+'x'*1501]:
            with self.subTest(content=content[:80]),self.assertRaises(ValueError):
                parse_reminder(content,NOW)


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/'reminders.sqlite3'
        self.store=ReminderStore(self.path)
        self.user=NS(send=AsyncMock())
        self.channel=NS(guild=NS(id=GUILD_ID),send=AsyncMock())
        self.client=NS(get_user=lambda uid:self.user,get_channel=lambda cid:self.channel)
        self.when,_=parse_reminder('$remindme 10/29/2026: text',NOW)
        self.store.add(123,GUILD_ID,'https://example.test/message',self.when,'Check the signups @everyone <@999>')

    async def test_deliver_both_restart_no_duplicates_and_mentions_scoped(self):
        await ReminderRunner(self.path).run(self.client,now=self.when)
        self.user.send.assert_awaited_once()
        self.channel.send.assert_awaited_once()
        self.assertIn('<@123>',self.channel.send.call_args.args[0])
        mentions=self.channel.send.call_args.kwargs['allowed_mentions']
        self.assertFalse(mentions.everyone)
        self.assertFalse(mentions.roles)
        self.assertEqual([user.id for user in mentions.users],[123])
        await ReminderRunner(self.path).run(self.client,now=self.when)
        self.assertEqual(self.user.send.await_count,1)
        self.assertEqual(self.channel.send.await_count,1)
        self.assertEqual(self.store.due(self.when),[])

    async def test_not_before_due_but_overdue_delivers(self):
        await ReminderRunner(self.path).run(self.client,now=NOW)
        self.user.send.assert_not_awaited()
        later=datetime(2026,11,1,tzinfo=timezone.utc)
        await ReminderRunner(self.path).run(self.client,now=later)
        self.user.send.assert_awaited_once()

    async def test_closed_dm_does_not_block_server_ping(self):
        self.user.send.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'DM closed')
        with self.assertLogs('commands.personal_reminders',level='WARNING'):
            await ReminderRunner(self.path).run(self.client,now=self.when)
        self.channel.send.assert_awaited_once()
        with self.store.connection() as db:
            row=db.execute('SELECT * FROM reminder').fetchone()
            self.assertEqual((row['dm_status'],row['server_status']),('blocked','sent'))

    async def test_uncertain_dm_not_repeated_server_still_sent(self):
        self.user.send.side_effect=TimeoutError('uncertain delivery')
        with self.assertLogs('commands.personal_reminders',level='ERROR'):
            await ReminderRunner(self.path).run(self.client,now=self.when)
        await ReminderRunner(self.path).run(self.client,now=self.when)
        self.assertEqual(self.user.send.await_count,1)
        self.channel.send.assert_awaited_once()

    async def test_create_records_requester_and_reacts_without_reply(self):
        context=NS(content='$remindme 10/30/2026: More tasks',author_id=456,
                   guild=NS(id=GUILD_ID),channel=NS(id=77,send=AsyncMock()),message=NS(id=88,add_reaction=AsyncMock()))
        await create_reminder(context,store=self.store,now=NOW)
        with self.store.connection() as db:
            row=db.execute('SELECT * FROM reminder WHERE user_id=456').fetchone()
            self.assertEqual(row['body'],'More tasks')
            self.assertTrue(row['source_url'].endswith('/77/88'))
        context.message.add_reaction.assert_awaited_once_with('✅')
        context.channel.send.assert_not_awaited()
