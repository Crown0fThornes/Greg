import asyncio
import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import discord

from commands.counting_game import CountingGame, CountingStore, CHANNEL_ID, GUILD_ID, number, route_message


class Message:
    def __init__(self,channel,mid,content,uid,bot=False):
        self.id,self.content,self.channel=mid,content,channel
        self.author=NS(id=uid,bot=bot)
        self.guild=NS(id=GUILD_ID,me=NS(id=99))
        self.attachments=[]
        self.stickers=[]
        self.removed=False

    async def delete(self):
        if self.channel.delete_error:
            raise self.channel.delete_error
        if self.removed:
            raise discord.NotFound(NS(status=404,reason='Not Found'),'gone')
        self.removed=True


class Channel:
    def __init__(self):
        self.id=CHANNEL_ID
        self.messages=[]
        self.history_calls=[]
        self.sent=[]
        self.nonces={}
        self.delete_error=None
        self.send_hook=None

    def add(self,content,uid,bot=False):
        message=Message(self,max([m.id for m in self.messages]+[100])+1,content,uid,bot)
        self.messages.append(message)
        return message

    async def history(self,*,limit=None,after=None,before=None,oldest_first=False):
        self.history_calls.append((limit,getattr(after,'id',None),getattr(before,'id',None)))
        messages=sorted((message for message in self.messages if not message.removed
                         and (after is None or message.id>after.id)
                         and (before is None or message.id<before.id)),key=lambda message:message.id,reverse=not oldest_first)
        for message in messages if limit is None else messages[:limit]:
            yield message

    async def send(self,content,**kwargs):
        nonce=kwargs.get('nonce')
        if nonce in self.nonces:
            return self.nonces[nonce]
        message=self.add(content,99,True)
        self.sent.append(content)
        self.nonces[nonce]=message
        if self.send_hook:
            self.send_hook(message)
        return message

    def get_partial_message(self,mid):
        return next(message for message in self.messages if message.id==mid)


class GameTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=CountingStore(Path(self.tmp.name)/'count.sqlite3')
        self.channel=Channel()
        self.games=[]

    async def asyncTearDown(self):
        for game in self.games:
            await game.shutdown()
        self.tmp.cleanup()

    def game(self):
        game=CountingGame(self.channel,99,self.store,batch_delay=0.01,retry_delay=0.02)
        self.games.append(game)
        return game

    async def active(self):
        self.channel.add('1',99,True)
        game=self.game()
        await game.recover()
        return game

    async def test_empty_channel_starts_with_gregs_one(self):
        game=self.game()
        await game.recover()
        self.assertEqual(self.channel.sent,['1'])
        self.assertEqual(game.state['value'],1)
        self.assertIsNone(game.state['last_user'])
        self.assertEqual(len(game.state['seed_nonce']),24)

    async def test_bootstrap_recovers_existing_round_and_last_player(self):
        self.channel.add('1',99,True)
        self.channel.add('2',1)
        last=self.channel.add('3',2)
        game=self.game()
        await game.recover()
        self.assertEqual((game.state['value'],game.state['last_user'],game.state['cursor']),(3,2,last.id))
        self.assertEqual(self.channel.sent,[])

    async def test_valid_numbers_do_not_read_history_or_send_replies(self):
        game=await self.active()
        self.channel.history_calls.clear()
        for value in range(2,102):
            await game.apply(self.channel.add(str(value),value%2+1))
        self.assertEqual(game.state['value'],101)
        self.assertEqual(self.store.load(self.channel.id)['value'],101)
        self.assertEqual(self.channel.history_calls,[])
        self.assertEqual(self.channel.sent,[])

    async def test_rapid_events_are_sorted_and_deduplicated_by_one_worker(self):
        game=await self.active()
        game.wake()
        await asyncio.wait_for(game.queue.join(),2)
        self.channel.history_calls.clear()
        messages=[self.channel.add(str(value),value%2+1) for value in range(2,202)]
        for message in reversed(messages):
            game.enqueue(message)
            game.enqueue(message)
        await asyncio.wait_for(game.queue.join(),5)
        self.assertEqual(game.state['value'],201)
        self.assertEqual(game.state['cursor'],messages[-1].id)
        self.assertEqual(self.channel.sent,[])
        self.assertEqual(self.channel.history_calls,[])

    async def test_apparent_mistake_recovers_earlier_delayed_event_before_resetting(self):
        game=await self.active()
        await game.apply(self.channel.add('2',1))
        delayed=self.channel.add('3',2)
        fourth=self.channel.add('4',1)
        await game.apply(fourth)
        await game.apply(delayed)
        self.assertEqual(game.state['value'],4)
        self.assertEqual(self.channel.sent,[])

    async def test_same_player_twice_ends_round_even_with_non_number_between(self):
        game=await self.active()
        await game.apply(self.channel.add('2',1))
        text=self.channel.add('hello',2)
        await game.apply(text)
        await game.apply(self.channel.add('3',1))
        await game.delete_task
        self.assertTrue(text.removed)
        self.assertEqual(game.state['value'],1)
        self.assertIsNone(game.state['last_user'])
        self.assertIn('same person',self.channel.sent[0])
        self.assertEqual(self.channel.sent[-1],'1')

    async def test_non_numbers_are_deleted_without_affecting_progress(self):
        game=await self.active()
        await game.apply(self.channel.add('2',1))
        text=self.channel.add('hello',2)
        await game.apply(text)
        self.assertEqual((game.state['value'],game.state['last_user']),(2,1))
        await game.apply(self.channel.add('3',2))
        await game.delete_task
        self.assertTrue(text.removed)
        self.assertEqual(game.state['value'],3)

    async def test_restart_catches_up_offline_numbers_and_preserves_turn_order(self):
        game=await self.active()
        await game.apply(self.channel.add('2',1))
        await game.shutdown()
        self.channel.add('3',2)
        self.channel.add('4',1)
        recovered=self.game()
        await recovered.recover()
        self.assertEqual((recovered.state['value'],recovered.state['last_user']),(4,1))
        await recovered.apply(self.channel.add('5',1))
        self.assertEqual(recovered.state['value'],1)
        self.assertIn('same person',self.channel.sent[0])

    async def test_offline_mistake_creates_one_reset_not_a_cascade(self):
        game=await self.active()
        await game.apply(self.channel.add('2',1))
        await game.shutdown()
        self.channel.add('3',2)
        self.channel.add('5',1)
        self.channel.add('6',2)
        self.channel.add('7',1)
        recovered=self.game()
        await recovered.recover()
        self.assertEqual(recovered.state['value'],1)
        self.assertEqual(len(self.channel.sent),2)
        self.assertEqual(self.channel.sent[-1],'1')

    async def test_messages_posted_before_new_seed_cannot_enter_new_round(self):
        game=await self.active()
        premature=[]
        def during_reset(message):
            if message.content!='1':
                premature.extend([self.channel.add('2',1),self.channel.add('3',2),self.channel.add('wait',1)])
        self.channel.send_hook=during_reset
        await game.apply(self.channel.add('9',1))
        for message in premature:
            await game.apply(message)
        await game.delete_task
        self.assertEqual(game.state['value'],1)
        self.assertEqual(len(self.channel.sent),2)
        self.assertTrue(premature[-1].removed)
        await game.apply(self.channel.add('2',1))
        self.assertEqual(game.state['value'],2)

    async def test_crash_after_sending_seed_recovers_it_without_duplicate_one(self):
        game=await self.active()
        original=self.store.save
        def fail_seed_commit(state,delete_id=None,score_event=None):
            if state['phase']=='active' and state['seed_id']!=game.state['seed_id']:
                raise RuntimeError('simulated crash after send')
            original(state,delete_id,score_event)
        with patch.object(self.store,'save',side_effect=fail_seed_commit):
            with self.assertRaises(RuntimeError):
                await game.apply(self.channel.add('9',1))
        self.assertEqual(self.store.load(self.channel.id)['phase'],'reset')
        self.assertEqual(len(self.channel.sent),2)
        recovered=self.game()
        await recovered.recover()
        self.assertEqual(recovered.state['value'],1)
        self.assertEqual(len(self.channel.sent),2)

    async def test_uncertain_send_is_reconciled_from_discord_on_restart(self):
        game=await self.active()
        def uncertain(message):
            if message.content=='1':
                raise RuntimeError('response lost after Discord accepted it')
        self.channel.send_hook=uncertain
        with self.assertRaises(RuntimeError):
            await game.apply(self.channel.add('8',1))
        self.channel.send_hook=None
        recovered=self.game()
        await recovered.recover()
        self.assertEqual(len(self.channel.sent),2)
        self.assertEqual(recovered.state['phase'],'active')

    async def test_failed_checkpoint_does_not_advance_memory_and_replay_recovers(self):
        game=await self.active()
        message=self.channel.add('2',1)
        with patch.object(self.store,'save',side_effect=RuntimeError('disk unavailable')):
            with self.assertRaises(RuntimeError):
                await game.apply(message)
        self.assertEqual(game.state['value'],1)
        recovered=self.game()
        await recovered.recover()
        self.assertEqual(recovered.state['value'],2)

    async def test_failed_deletion_retries_without_blocking_numbers(self):
        game=await self.active()
        self.channel.delete_error=discord.Forbidden(NS(status=403,reason='Forbidden'),'blocked')
        message=self.channel.add('hello',1)
        with self.assertLogs('commands.counting_game',level='WARNING'):
            await game.apply(message)
            await game.delete_task
        self.assertEqual(self.store.deletions(self.channel.id),[message.id])
        await game.apply(self.channel.add('2',1))
        self.assertEqual(game.state['value'],2)
        self.channel.delete_error=None
        recovered=self.game()
        await recovered.recover()
        await recovered.delete_task
        self.assertTrue(message.removed)
        self.assertEqual(self.store.deletions(self.channel.id),[])

    async def test_attachment_message_is_deleted_without_counting_its_number(self):
        game=await self.active()
        message=self.channel.add('2',1)
        message.attachments=[NS(filename='image.png')]
        await game.apply(message)
        await game.delete_task
        self.assertTrue(message.removed)
        self.assertEqual(game.state['value'],1)
        self.assertEqual(self.channel.sent,[])

    async def test_crash_after_failure_notice_does_not_repeat_it(self):
        game=await self.active()
        original=self.store.save
        def fail_notice_commit(state,delete_id=None,score_event=None):
            if state['phase']=='reset' and state['notice_id'] is not None:
                raise RuntimeError('crashed after notice send')
            original(state,delete_id,score_event)
        with patch.object(self.store,'save',side_effect=fail_notice_commit):
            with self.assertRaises(RuntimeError):
                await game.apply(self.channel.add('9',1))
        self.assertEqual(len(self.channel.sent),1)
        recovered=self.game()
        await recovered.recover()
        self.assertEqual(len(self.channel.sent),2)
        self.assertEqual(self.channel.sent[-1],'1')

    async def test_worker_retries_after_checkpoint_failure_without_losing_message(self):
        game=await self.active()
        game.wake()
        await asyncio.wait_for(game.queue.join(),2)
        original=self.store.save
        failed=False
        def temporary_failure(state,delete_id=None,score_event=None):
            nonlocal failed
            if state['value']==2 and not failed:
                failed=True
                raise RuntimeError('temporary disk failure')
            original(state,delete_id,score_event)
        with patch.object(self.store,'save',side_effect=temporary_failure):
            with self.assertLogs('commands.counting_game',level='ERROR'):
                game.enqueue(self.channel.add('2',1))
                async with asyncio.timeout(2):
                    while not failed or game.state['value']!=2:
                        await asyncio.sleep(0.01)
        self.assertEqual(self.store.load(self.channel.id)['value'],2)
        self.assertEqual(self.channel.sent,[])


class RouteTests(unittest.TestCase):
    def test_route_enqueues_before_any_generic_handler_and_filters_other_channels(self):
        message=Message(Channel(),123,'2',1)
        runtime=Mock()
        with patch('commands.counting_game.game_for',return_value=runtime):
            self.assertTrue(route_message(message))
            runtime.enqueue.assert_called_once_with(message)
            message.channel.id=0
            self.assertFalse(route_message(message))

    def test_integer_parsing(self):
        for text in ('hello','2 hello','2.0','1_000',''):
            self.assertIsNone(number(text))
        self.assertEqual(number(' 2 '),2)
        self.assertEqual(number('-1'),-1)

    def test_greg_routes_counting_before_constructing_neighbor_or_awaiting(self):
        source=Path(__file__).resolve().parents[1]/'greg3.py'
        tree=ast.parse(source.read_text())
        handler=next(node for node in tree.body if getattr(node,'name',None)=='on_message')
        first=handler.body[0]
        self.assertIsInstance(first,ast.If)
        self.assertIn('route_counting_message',ast.unparse(first.test))
        self.assertIsInstance(first.body[0],ast.Return)
