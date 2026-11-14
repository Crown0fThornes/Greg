from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock,patch

import ticket_manager as tickets


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ff=NS(guild=1,support_request_channel=10,mission_control_channel=11)
        self.users={uid:NS(id=uid,bot=False,display_name=f'User {uid}') for uid in (1,2)}
        self.message=NS(reactions=[],remove_reaction=AsyncMock())
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
