from types import SimpleNamespace as NS
import ast
import datetime
from pathlib import Path
import unittest
from unittest.mock import AsyncMock,patch

import ticket_manager as tickets


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ff=NS(guild=1,support_request_channel=10,mission_control_channel=11)
        self.users={uid:NS(id=uid,bot=False,display_name=f'User {uid}') for uid in (1,2)}
        self.message=NS(reactions=[],remove_reaction=AsyncMock(),add_reaction=AsyncMock())
        self.channel=NS(fetch_message=AsyncMock(return_value=self.message))
        self.guild=NS(id=1,fetch_channel=AsyncMock(return_value=self.channel),
                      get_member=lambda uid:self.users.get(uid),fetch_member=AsyncMock())
        self.client=NS(get_guild=lambda gid:self.guild)

    def reaction(self,emoji,users):
        async def iterate(**kwargs):
            for user in users:
                yield user
        return NS(emoji=emoji,users=iterate)

    async def test_catches_missed_requests_deduplicates_users_and_ignores_bots(self):
        bot=NS(id=99,bot=True)
        self.message.reactions=[self.reaction('🎟️',[bot,self.users[1],self.users[2]]),
                                self.reaction('👋',[self.users[1]])]
        with patch.object(tickets,'open_ticket',new=AsyncMock()) as open_ticket:
            await tickets.recover_support_requests(self.client,self.ff)
        self.assertEqual(open_ticket.await_count,2)
        self.assertEqual([call.args[1].id for call in open_ticket.call_args_list],[1,2])
        self.assertFalse(open_ticket.call_args.kwargs['notify_existing'])
        self.message.remove_reaction.assert_awaited_once_with('👋',self.users[1])

    async def test_one_failed_request_does_not_discard_it_or_stop_other_users(self):
        self.message.reactions=[self.reaction('🎟️',list(self.users.values()))]
        with patch.object(tickets,'open_ticket',new=AsyncMock(side_effect=[RuntimeError('temporary failure'),None])) as opening:
            with self.assertLogs('ticket_manager',level='ERROR'):
                await tickets.recover_support_requests(self.client,self.ff)
        self.assertEqual(opening.await_count,2)
        self.message.remove_reaction.assert_not_awaited()

    async def test_reaction_is_only_removed_after_successful_open(self):
        async def open_success(*args,**kwargs):
            self.message.remove_reaction.assert_not_awaited()
            return NS(id=123)
        with patch.object(tickets,'_open_ticket',new=AsyncMock(side_effect=open_success)), \
             patch.object(tickets,'cleanup_ticket_categories',new=AsyncMock()):
            await tickets.open_ticket('🎟️',self.users[1],self.guild,self.ff)
        self.message.remove_reaction.assert_awaited_once_with('🎟️',self.users[1])

    async def test_failed_open_leaves_reaction_available_for_retry(self):
        with patch.object(tickets,'_open_ticket',new=AsyncMock(side_effect=RuntimeError('failed'))):
            with self.assertRaises(RuntimeError):
                await tickets.open_ticket('🎟️',self.users[1],self.guild,self.ff)
        self.message.remove_reaction.assert_not_awaited()

    async def test_already_open_ticket_is_not_renotified_during_recovery(self):
        self.guild.get_role=lambda rid:None
        # A real type check is part of the existing ticket lookup.
        from unittest.mock import Mock
        import discord
        existing=Mock(spec=discord.TextChannel,id=123,topic='1',category_id=tickets.BASE_OPEN,
                      edit=AsyncMock(),send=AsyncMock())
        with patch.object(tickets,'category_snapshot',new=AsyncMock(return_value=([NS(id=tickets.BASE_OPEN)],[existing]))):
            result=await tickets._open_ticket('🎟️',self.users[1],self.guild,self.ff,notify_existing=False)
        self.assertIs(result,existing)
        existing.edit.assert_not_awaited()
        existing.send.assert_not_awaited()

    async def test_seasonal_logo_is_added_and_only_gregs_old_seed_is_removed(self):
        import discord
        regular=discord.PartialEmoji.from_str(tickets.FF_LOGO)
        farmmas=discord.PartialEmoji.from_str(tickets.FARMMAS_FF_LOGO)
        self.guild.me=NS(id=99,bot=True)
        self.message.reactions=[NS(emoji=regular,me=True)]
        await tickets.ensure_support_logo(self.message,self.guild,tickets.FARMMAS_FF_LOGO)
        self.message.add_reaction.assert_awaited_once_with(tickets.FARMMAS_FF_LOGO)

        self.message.remove_reaction.assert_awaited_once_with(regular,self.guild.me)
        self.message.add_reaction.reset_mock()
        self.message.remove_reaction.reset_mock()
        self.message.reactions=[NS(emoji=regular,me=False),NS(emoji=farmmas,me=True)]
        await tickets.ensure_support_logo(self.message,self.guild,tickets.FARMMAS_FF_LOGO)
        self.message.add_reaction.assert_not_awaited()
        self.message.remove_reaction.assert_not_awaited()

    async def test_both_logo_reactions_recover_tickets(self):
        import discord
        self.message.reactions=[self.reaction(discord.PartialEmoji.from_str(tickets.FF_LOGO),[self.users[1]]),
                                self.reaction(discord.PartialEmoji.from_str(tickets.FARMMAS_FF_LOGO),[self.users[2]])]
        for reaction in self.message.reactions:
            reaction.me=False
        with patch.object(tickets,'open_ticket',new=AsyncMock()) as opening:
            await tickets.recover_support_requests(self.client,self.ff,logo=tickets.FARMMAS_FF_LOGO)
        self.assertEqual([call.args[1].id for call in opening.call_args_list],[1,2])
        self.message.add_reaction.assert_awaited_once_with(tickets.FARMMAS_FF_LOGO)


class SeasonalTests(unittest.TestCase):
    def test_support_seed_matches_existing_seasonal_date_boundaries(self):
        source=Path(__file__).resolve().parents[1]/'commands/commands.py'
        tree=ast.parse(source.read_text())
        functions=[node for node in tree.body if getattr(node,'name',None) in ('get_code_replacement','is_within_dates')]
        for month,day,expected in ((11,8,tickets.FF_LOGO),(11,9,tickets.FARMMAS_FF_LOGO),
                                   (12,31,tickets.FARMMAS_FF_LOGO),(1,1,tickets.FF_LOGO)):
            class Clock(datetime.datetime):
                @classmethod
                def now(cls):
                    return cls(2026,month,day)
            env=dict(datetime=NS(datetime=Clock))
            exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),env)
            self.assertEqual(env['get_code_replacement']('&FF_LOGO'),expected)
