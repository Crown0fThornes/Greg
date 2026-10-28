from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

from commands.hk_reminders import DeliveryLog, HKReminders, NEIGHBORHOODS, SERVER_TIME, parse_task, payloads
from commands.hk_assignments import INSTRUCTIONS, assignees, initialize, publish, signup_pages, week_start


class AssignmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'assign.sqlite3'
        self.delivery=DeliveryLog(self.path)
        self.nh=next(iter(NEIGHBORHOODS))
        self.config={self.nh:NEIGHBORHOODS[self.nh]}
        self.posts={}
        async def send(content,**kwargs):
            message=NS(id=100+len(self.posts),content=content,add_reaction=AsyncMock(),reactions=[])
            self.posts[message.id]=message
            return message
        self.target=NS(send=AsyncMock(side_effect=send),fetch_message=AsyncMock(side_effect=lambda mid:self.posts[mid]))
        self.guild=NS(fetch_channel=AsyncMock(return_value=self.target))
        self.sunday=datetime(2026,10,25,8,tzinfo=SERVER_TIME)
        self.task=parse_task('New Joins / 👋 / Tuesday / 8:00 AM\nInstructions')
        self.message=NS(id=1)
        self.tasks=[(self.message,self.task,{self.nh})]

    async def test_sunday_publishes_seeds_and_restart_does_not_duplicate(self):
        await publish(self.guild,self.delivery,self.config,self.tasks,self.sunday)
        self.target.send.assert_awaited_once()
        post=next(iter(self.posts.values()))
        self.assertIn(INSTRUCTIONS,post.content)
        role_id=self.config[self.nh][1]
        self.assertTrue(post.content.startswith(f'<@&{role_id}>'))
        mentions=self.target.send.call_args.kwargs['allowed_mentions']
        self.assertEqual([role.id for role in mentions.roles],[role_id])
        self.assertFalse(mentions.everyone)
        self.assertFalse(mentions.users)
        self.assertIn('2026-10-27',post.content)
        self.assertIn('👋 **New Joins**',post.content)
        post.add_reaction.assert_awaited_with('👋')
        await publish(self.guild,DeliveryLog(self.path),self.config,self.tasks,self.sunday)
        self.assertEqual(self.target.send.await_count,1)

    async def test_individuals_bot_filter_and_reaction_removal(self):
        await publish(self.guild,self.delivery,self.config,self.tasks,self.sunday)
        post=next(iter(self.posts.values()))
        async def users():
            for uid,bot in [(9,False),(10,False),(11,True)]:
                yield NS(id=uid,bot=bot)
        post.reactions=[NS(emoji='👋',users=users)]
        tuesday=datetime(2026,10,27,8,tzinfo=SERVER_TIME)
        result=await assignees(self.guild,self.delivery,self.nh,self.config[self.nh][0],1,'👋',tuesday)
        self.assertEqual(result,[9,10])
        post.reactions=[]
        self.assertEqual(await assignees(self.guild,self.delivery,self.nh,self.config[self.nh][0],1,'👋',tuesday),[])

    async def test_sunday_and_monday_use_previous_assignment_week(self):
        await publish(self.guild,self.delivery,self.config,self.tasks,self.sunday)
        for date in [self.sunday,datetime(2026,10,26,8,tzinfo=SERVER_TIME)]:
            self.assertEqual(week_start(date),'2026-10-20')
            self.assertEqual(await assignees(self.guild,self.delivery,self.nh,self.config[self.nh][0],1,'👋',date),[])
        self.assertEqual(week_start(datetime(2026,10,27,0,tzinfo=SERVER_TIME)),'2026-10-27')
        self.assertEqual(week_start(datetime(2026,11,2,23,tzinfo=SERVER_TIME)),'2026-10-27')

    async def test_duplicate_identifiers_do_not_assign_two_tasks(self):
        second=parse_task('Another / 👋 / Wednesday / 8:00 AM')
        pages=signup_pages([(self.message,self.task),(NS(id=2),second)],'2026-10-27')
        self.assertEqual(pages[0][1],{})
        self.assertIn('unique emoji',pages[0][0])

    async def test_pagination_twenty_reactions_max(self):
        tasks=[(NS(id=i),parse_task(f'Task {i} / <:task{i}:{1000+i}> / Tuesday / 8:00 AM')) for i in range(25)]
        pages=signup_pages(tasks,'2026-10-27')
        self.assertEqual(len(pages),2)
        self.assertTrue(all(len(mapping)<=20 and len(content)<=2000 for content,mapping in pages))
        self.assertEqual(sum(len(mapping) for _,mapping in pages),25)

    async def test_multi_page_signup_pings_role_only_once(self):
        tasks=[(NS(id=i),parse_task(f'Task {i} / <:task{i}:{1000+i}> / Tuesday / 8:00 AM'),{self.nh}) for i in range(25)]
        await publish(self.guild,self.delivery,self.config,tasks,self.sunday)
        calls=self.target.send.call_args_list
        self.assertEqual(len(calls),2)
        self.assertTrue(calls[0].args[0].startswith('<@&'))
        self.assertNotIn('<@&',calls[1].args[0])
        self.assertEqual(calls[1].kwargs['allowed_mentions'].roles,[])

    async def test_dispatch_pings_assignees_and_not_council_role(self):
        await publish(self.guild,self.delivery,self.config,self.tasks,self.sunday)
        post=next(iter(self.posts.values()))
        async def users():
            yield NS(id=123,bot=False)
        post.reactions=[NS(emoji='👋',users=users)]
        self.message.content='New Joins / 👋 / Tuesday / 8:00 AM\nDo the task'
        self.message.reactions=[NS(emoji=NS(id=self.nh),count=1)]
        async def history(**kwargs):
            yield self.message
        signup=NS(history=history,fetch_message=AsyncMock(return_value=self.message))
        async def fetch(cid):
            return self.target if cid==self.config[self.nh][0] else signup
        self.guild.fetch_channel=AsyncMock(side_effect=fetch)
        self.target.send.reset_mock()
        await HKReminders(self.path).run(NS(get_guild=lambda gid:self.guild),now=datetime(2026,10,27,12,tzinfo=timezone.utc))
        sent=self.target.send.call_args
        self.assertTrue(sent.args[0].startswith('<@123>'))
        self.assertEqual(sent.kwargs['allowed_mentions'].roles,[])
        self.assertEqual([u.id for u in sent.kwargs['allowed_mentions'].users],[123])

    def test_parser_and_long_payloads(self):
        self.assertEqual(self.task.emoji,'👋')
        self.assertIsNone(parse_task('Task / word / Monday / 8:00 AM'))
        task=parse_task('Title / 👋 / Monday / 8:00 AM\n'+'x'*5000)
        messages=payloads(task,NS(id=1),77,range(100000000000000000,100000000000000100))
        self.assertTrue(all(len(m)<=2000 for m in messages))
        self.assertEqual(''.join(messages).count('x'),5000)
