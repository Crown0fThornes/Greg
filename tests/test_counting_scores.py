import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock, patch

import discord

from commands import counting_scores as scores
from commands.counting_game import CountingStore, CHANNEL_ID
from tests.test_counting_game import Channel, CountingGame


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=CountingStore(Path(self.tmp.name)/'scores.sqlite3')
        self.boundary=datetime(2027,1,2,0,1).astimezone()
        self.state=dict(channel_id=CHANNEL_ID,value=42,last_user=1,cursor=123)

    def tearDown(self):
        self.tmp.cleanup()

    def award(self,mid,uid,delta,when=None,bonus=False):
        self.store.save(self.state,score_event=dict(message_id=mid,user_id=uid,delta=delta,
            occurred=(when or self.boundary-timedelta(days=1)).timestamp(),milestone=bonus))

    def test_milestones_follow_each_magnitude(self):
        for value in [10,50,100,250,500,600,700,800,900,1000,2000,9000,10000,
                      20000,90000,100000,200000,1000000,9000000,10000000]:
            self.assertTrue(scores.milestone(value),value)
        for value in [-1000,0,2,200,300,400,999,1500,11000,99000,110000,1100000]:
            self.assertFalse(scores.milestone(value),value)

    def test_awards_and_penalties(self):
        message=NS(id=1,author=NS(id=2),created_at=self.boundary)
        for kind,value,expected,want in [('valid',2,0,12),('valid',10,0,110),
                ('valid',2000,0,2100),('deleted',0,0,-10),('ended',5,3,-18),
                ('ended',-50,3,-63),('ended',3,3,-16)]:
            self.assertEqual(scores.event(message,kind,value=value,expected=expected)['delta'],want)

    def test_duplicate_delivery_does_not_double_points_or_reactions(self):
        self.award(1,2,110,bonus=True)
        self.award(1,2,110,bonus=True)
        self.assertEqual(scores.score(self.store,2),110)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM counting_reaction').fetchone()[0],1)

    def test_failed_score_write_rolls_back_game_cursor(self):
        self.store.save(self.state)
        with patch.object(scores,'record',side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                self.store.save(dict(self.state,cursor=999),score_event={})
        self.assertEqual(self.store.load(CHANNEL_ID)['cursor'],123)

    def test_monthly_floor_and_idempotence_preserve_round(self):
        self.award(1,1,25)
        self.award(2,2,-5)
        scores.roll(self.store,'2027-01',self.boundary)
        scores.roll(self.store,'2027-01',self.boundary)
        self.assertEqual(scores.score(self.store,1),12)
        self.assertEqual(scores.score(self.store,2),-3)
        self.assertEqual(self.store.load(CHANNEL_ID),self.state)

    def test_posts_after_cutoff_are_not_halved(self):
        self.award(1,1,20)
        self.award(2,1,6,self.boundary+timedelta(hours=1))
        scores.roll(self.store,'2027-01',self.boundary)
        self.assertEqual(scores.score(self.store,1),16)
        self.award(3,1,6,self.boundary-timedelta(hours=1))
        self.assertEqual(scores.score(self.store,1),19)

    def test_missed_months_apply_each_halving_once(self):
        self.award(1,1,101)
        for period,cutoff in scores.cutoffs(datetime(2027,3,3,tzinfo=timezone.utc)):
            scores.roll(self.store,period,cutoff)
        self.assertEqual(scores.score(self.store,1),12)

    def test_inventory_mirror_is_permanent_and_updates_single_item(self):
        neighbor=Mock(ID=1)
        neighbor.get_item_of_name.return_value=None
        scores.sync_profile(neighbor,store=self.store)
        item=neighbor.bestow_item.call_args.args[0]
        self.assertEqual((item.type,item.expiration,item.values['points']),('counting_score',-1,0))
        neighbor.get_item_of_name.return_value=item
        self.award(1,1,12)
        scores.sync_profile(neighbor,store=self.store)
        self.assertEqual(neighbor.update_item.call_args.args[0].values['points'],12)
        neighbor.bestow_item.assert_called_once()


class AsyncScoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=CountingStore(Path(self.tmp.name)/'scores.sqlite3')
        self.boundary=datetime(2027,1,2,0,1).astimezone()
        self.state=dict(channel_id=CHANNEL_ID)

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_game_replay_awards_once_and_charges_deletion_and_failure(self):
        channel=Channel()
        channel.add('1',99,True)
        channel.add('2',1)
        channel.add('hello',2)
        channel.add('3',2)
        channel.add('4',2)  # Same author ends round: -(10+4+4).
        game=CountingGame(channel,99,self.store)
        try:
            await game.recover()
            await game.recover()
            self.assertEqual(scores.score(self.store,1),12)
            self.assertEqual(scores.score(self.store,2),-15)
        finally:
            await game.shutdown()

    async def test_milestone_reaction_uses_hype_pool_and_does_not_repeat(self):
        self.store.save(self.state,score_event=dict(message_id=5,user_id=1,delta=110,
            occurred=self.boundary.timestamp(),milestone=True))
        partial=NS(add_reaction=AsyncMock())
        channel=NS(guild=object(),get_partial_message=Mock(return_value=partial))
        effects=scores.CountingEffects(channel,self.store)
        loader=AsyncMock(return_value=['🔥'])
        with patch.dict('sys.modules',{'commands.commands':NS(_load_hype_emojis=loader)}):
            await effects.reactions()
            await effects.reactions()
        partial.add_reaction.assert_awaited_once_with('🔥')
        self.assertEqual(scores.score(self.store,1),110)

    async def test_monthly_post_to_bot_commands_mentions_only_neighbors_and_is_once(self):
        for uid in range(1,13):
            self.store.save(self.state,score_event=dict(message_id=uid,user_id=uid,delta=100+uid,
                occurred=(self.boundary-timedelta(days=1)).timestamp(),milestone=False))
        target=NS(send=AsyncMock(return_value=NS(id=900)))
        guild=NS(fetch_channel=AsyncMock(return_value=target),
                 get_member=lambda uid:NS(display_name=f'Player {uid}',bot=False))
        client=NS(get_guild=lambda gid:guild,user=NS(id=99))
        with patch('commands.counting_game._games',{}):
            await scores.monthly_rewards(client,store=self.store,now=self.boundary+timedelta(hours=1))
            await scores.monthly_rewards(client,store=self.store,now=self.boundary+timedelta(hours=1))
        guild.fetch_channel.assert_awaited_once_with(784150346397253682)
        target.send.assert_awaited_once()
        text=target.send.call_args.args[0]
        self.assertIn('**December 2026**',text)
        self.assertIn('1. **Player 12** — 112',text)
        self.assertIn('10. **Player 3**',text)
        self.assertNotIn('Player 2**',text)
        self.assertIn(f'<@&{scores.NEIGHBORS_ROLE}>',text)
        self.assertFalse(target.send.call_args.kwargs['allowed_mentions'].users)
        self.assertEqual(scores.score(self.store,12),56)

    async def test_uncertain_announcement_is_recovered_without_reposting_or_rehalving(self):
        self.store.save(self.state,score_event=dict(message_id=1,user_id=1,delta=25,
            occurred=(self.boundary-timedelta(days=1)).timestamp(),milestone=False))
        sent=[]
        async def uncertain_send(content,**kwargs):
            sent.append(NS(id=900,content=content,author=NS(id=99)))
            raise OSError('connection lost after Discord accepted message')
        async def history(**kwargs):
            for message in sent:
                yield message
        target=NS(send=AsyncMock(side_effect=uncertain_send),history=history)
        guild=NS(fetch_channel=AsyncMock(return_value=target),
                 get_member=lambda uid:NS(display_name='Player',bot=False))
        client=NS(get_guild=lambda gid:guild,user=NS(id=99))
        with patch('commands.counting_game._games',{}):
            with self.assertRaises(OSError):
                await scores.monthly_rewards(client,store=self.store,now=self.boundary)
            await scores.monthly_rewards(client,store=self.store,now=self.boundary)
        target.send.assert_awaited_once()
        self.assertEqual(scores.score(self.store,1),12)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM counting_month').fetchone()[0],'sent')

    async def test_restrict_at_minus_1000_and_restore_only_posting_at_new_month(self):
        member=NS(id=1)
        overwrite=discord.PermissionOverwrite(read_message_history=True)
        async def set_permissions(target,*,overwrite: object,reason):
            channel.current=overwrite or discord.PermissionOverwrite()
        channel=NS(current=overwrite,guild=NS(get_member=lambda uid:member),
                   overwrites_for=lambda target:channel.current,
                   set_permissions=AsyncMock(side_effect=set_permissions))
        effects=scores.CountingEffects(channel,self.store)
        def penalty(mid,delta):
            self.store.save(self.state,score_event=dict(message_id=mid,user_id=1,delta=delta,
                occurred=datetime(2026,11,28,tzinfo=timezone.utc).timestamp(),milestone=False))
        with patch.object(scores,'permission_month',return_value='2026-11'):
            penalty(1,-999)
            await effects.permissions()
            channel.set_permissions.assert_not_awaited()
            penalty(2,-1)
            await effects.permissions()
            self.assertFalse(channel.current.send_messages)
            self.assertTrue(channel.current.read_message_history)
            await effects.permissions()
            channel.set_permissions.assert_awaited_once()
        with patch.object(scores,'permission_month',return_value='2026-12'):
            await effects.permissions()
            self.assertIsNone(channel.current.send_messages)
            self.assertTrue(channel.current.read_message_history)
            await effects.permissions()
        self.assertEqual(channel.set_permissions.await_count,2)
        self.assertEqual(scores.score(self.store,1),-1000)

    async def test_permission_restore_survives_restart_and_retains_previous_allow(self):
        member=NS(id=1)
        channel=NS(current=discord.PermissionOverwrite(send_messages=True),
                   guild=NS(get_member=lambda uid:member))
        channel.overwrites_for=lambda target:channel.current
        async def set_permissions(target,*,overwrite,reason):
            channel.current=overwrite or discord.PermissionOverwrite()
        channel.set_permissions=AsyncMock(side_effect=set_permissions)
        with self.store.connect() as db:
            db.execute("INSERT INTO counting_restriction VALUES (1,'2026-11','new',NULL)")
        with patch.object(scores,'permission_month',return_value='2026-11'):
            await scores.CountingEffects(channel,self.store).permissions()
        self.assertFalse(channel.current.send_messages)
        with patch.object(scores,'permission_month',return_value='2026-12'):
            await scores.CountingEffects(channel,self.store).permissions()
        self.assertTrue(channel.current.send_messages)

    async def test_permission_failure_retries_without_losing_original_overwrite(self):
        member=NS(id=1)
        channel=NS(guild=NS(get_member=lambda uid:member),
                   overwrites_for=lambda target:discord.PermissionOverwrite(),
                   set_permissions=AsyncMock(side_effect=[OSError('offline'),None]))
        with self.store.connect() as db:
            db.execute("INSERT INTO counting_restriction VALUES (1,'2026-11','new',NULL)")
        with patch.object(scores,'permission_month',return_value='2026-11'):
            with self.assertRaises(OSError):
                await scores.CountingEffects(channel,self.store).permissions()
            await scores.CountingEffects(channel,self.store).permissions()
        with self.store.connect() as db:
            row=db.execute('SELECT state,previous_send FROM counting_restriction').fetchone()
        self.assertEqual(row,('active',None))

    async def test_permission_month_uses_fixed_server_time(self):
        before=datetime(2026,12,1,3,59,tzinfo=timezone.utc).timestamp()
        after=datetime(2026,12,1,4,0,tzinfo=timezone.utc).timestamp()
        self.assertEqual(scores.permission_month(before),'2026-11')
        self.assertEqual(scores.permission_month(after),'2026-12')

    async def test_no_rollover_before_january(self):
        client=Mock()
        await scores.monthly_rewards(client,store=self.store,now=datetime(2026,12,31,tzinfo=timezone.utc))
        client.get_guild.assert_not_called()

    async def test_counting_messages_cannot_award_neighbor_xp_even_directly(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'commands/commands.py').read_text())
        handler=next(node for node in tree.body if getattr(node,'name',None)=='message_xp')
        handler.decorator_list=[]
        namespace={'Context':object,'Neighbor':Mock(side_effect=AssertionError('XP path entered'))}
        exec(compile(ast.Module(body=[handler],type_ignores=[]),'<message_xp>','exec'),namespace)
        await namespace['message_xp'](NS(channel=NS(id=CHANNEL_ID)))
        namespace['Neighbor'].assert_not_called()
