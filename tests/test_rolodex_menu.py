import contextlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock,patch

from command_handler import Context
from id_bundle import FF
from responses import ResponseRequest
from commands import rolodex_menu as menu
from persistence.rolodex import Rolodex,FF_GUILD


class MenuTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store=Rolodex(Path(temp.name)/'menu.sqlite3')
        self.before=list(ResponseRequest.active_requests)
        self.addCleanup(lambda: setattr(ResponseRequest,'active_requests',self.before))
        ResponseRequest.active_requests=[]
        self.owner=NS(id=123,roles=[NS(id=FF.leaders_role)],display_name='Council',bot=False)
        self.bot=NS(id=999,roles=[],display_name='Greg',bot=True)
        self.guild=NS(id=FF_GUILD,get_member=lambda uid:self.owner if uid==123 else None)
        self.messages=[]
        self.channel=NS(id=77,send=AsyncMock(side_effect=self.send))
        self.context=self.context_for(self.owner,'$rolodex',1)

    def context_for(self,author,content,mid,reference=None):
        message=NS(id=mid,author=author,guild=self.guild,channel=self.channel,content=content,
                   reference=reference,clear_reactions=AsyncMock(),edit=AsyncMock(),add_reaction=AsyncMock())
        with contextlib.redirect_stdout(io.StringIO()):
            return Context(message)

    async def send(self,content,**kwargs):
        message=self.context_for(self.bot,content,100+len(self.messages)).message
        self.messages.append(message)
        return message

    async def react(self,emoji,user=None):
        request=next(r for r in ResponseRequest.active_requests if r.type=='REACTION')
        context=self.context_for(self.bot,'menu',request.activation_context.message.id)
        context.user=user or self.owner
        context.emoji=emoji
        with contextlib.redirect_stdout(io.StringIO()):
            await ResponseRequest.fulfill_reaction_requests(NS(emoji=emoji),context,None)

    async def reply(self,body,reference_id=None):
        request=next(r for r in ResponseRequest.active_requests if r.type=='MESSAGE')
        ctx=self.context_for(self.owner,body,900,NS(message_id=reference_id or request.response_context.message.id))
        await ResponseRequest.fulfill_message_requests(ctx.message,ctx,None)

    async def test_note_wizard_uses_framework_and_requires_confirmation(self):
        await menu.open_menu(self.context,self.store)
        self.assertIn('📝', [call.args[0] for call in self.messages[0].add_reaction.await_args_list])
        await self.react('📝')
        await self.react('📝')
        await self.reply('<@456>')
        with patch.object(menu,'invoke',new=AsyncMock()) as invoke:
            await self.reply('Helped with derby')
            invoke.assert_not_awaited()
            await self.react('✅')
            invoke.assert_awaited_once()
            self.assertEqual(invoke.call_args.args[1],['note','456','Helped with derby'])

    async def test_other_people_cannot_control_menu_even_with_council_role(self):
        await menu.open_menu(self.context,self.store)
        request=ResponseRequest.active_requests[0]
        other=NS(id=456,roles=self.owner.roles,bot=False)
        await self.react('📝',other)
        self.assertIn(request,ResponseRequest.active_requests)
        self.assertEqual(len(self.messages),1)

    async def test_reply_to_wrong_prompt_is_not_consumed_and_cancel_clears_requests(self):
        await menu.open_menu(self.context,self.store)
        await self.react('🔗')
        await self.react('🔗')
        request=next(r for r in ResponseRequest.active_requests if r.type=='MESSAGE')
        await self.reply('456',reference_id=123456)
        self.assertIn(request,ResponseRequest.active_requests)
        await self.react('❌')
        self.assertEqual(ResponseRequest.active_requests,[])

    async def test_permission_revocation_prevents_callback(self):
        await menu.open_menu(self.context,self.store)
        self.owner.roles=[]
        request=ResponseRequest.active_requests[0]
        await self.react('📝')
        self.assertIn(request,ResponseRequest.active_requests)
        self.assertEqual(len(self.messages),1)

    async def test_empty_review_keeps_navigation_and_does_not_crash(self):
        await menu.open_menu(self.context,self.store,review_mode=True)
        self.assertIn('No identities',self.messages[0].content)
        await self.react('📚')
        self.assertEqual(len(ResponseRequest.active_requests),1)


    async def test_review_match_is_one_click_without_reason_and_advances(self):
        from datetime import datetime,timezone
        from persistence.import_membership_history import HistoryImporter,JOINLIST
        from persistence.sqlite_db import connect
        from persistence.rolodex_records import records
        source=NS(id=456,guild=self.guild,channel=NS(id=JOINLIST),author=self.owner,
                  content='Fancy has joined ffc',created_at=datetime(2026,10,25,tzinfo=timezone.utc))
        importer=HistoryImporter(self.store,999)
        importer.add_member(NS(id=456789,name='Fancy',global_name=None,nick=None,display_name='Fancy'))
        importer.ingest(source)
        await menu.open_menu(self.context,self.store,review_mode=True)
        self.assertIn('<@456789>',self.messages[0].content)
        request=ResponseRequest.active_requests[0]
        self.assertLessEqual(len(request.values['menu_session']['choices']),6)
        await self.react('✅')
        with connect(self.store.path) as db:
            self.assertEqual(records(db)['event'][0]['user_id'],456789)
            self.assertEqual(db.execute('SELECT actor_id FROM historical_identity_revision').fetchone()[0],123)
        self.assertFalse(any(r.type=='MESSAGE' for r in ResponseRequest.active_requests))
        self.messages[0].edit.assert_awaited()
        self.assertIn('No identities',self.messages[0].edit.call_args.kwargs['content'])

    async def test_manual_match_accepts_normal_message_without_reason_prompt(self):
        from datetime import datetime,timezone
        from persistence.import_membership_history import HistoryImporter,JOINLIST
        from persistence.sqlite_db import connect
        from persistence.rolodex_records import records
        source=NS(id=456,guild=self.guild,channel=NS(id=JOINLIST),author=self.owner,
                  content='Fancy has joined ffc',created_at=datetime(2026,10,25,tzinfo=timezone.utc))
        HistoryImporter(self.store,999).ingest(source)
        await menu.open_menu(self.context,self.store,review_mode=True)
        await self.react('🔗')
        await self.react('➕')
        ctx=self.context_for(self.owner,'<@456789>',900)
        await ResponseRequest.fulfill_message_requests(ctx.message,ctx,None)
        with connect(self.store.path) as db:
            self.assertEqual(records(db)['event'][0]['user_id'],456789)

    async def test_main_menu_uses_small_submenus(self):
        await menu.open_menu(self.context,self.store)
        state=ResponseRequest.active_requests[0].values['menu_session']
        self.assertLessEqual(len(state['choices']),7)
        await self.react('📥')
        self.assertEqual(state['screen'],'section')
        self.assertLessEqual(len(state['choices']),6)
