from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

from persistence.rolodex import Rolodex, FF_GUILD
from persistence.rolodex_records import add_event, records
from persistence.neighbor_db import connect
from persistence.rolodex_people import linked_accounts, link_accounts, notes, save_note
from commands.rolodex_display import name_history, neighborhood_history, compact_profile, find_introduction, pretty_date


class PeopleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Rolodex(Path(tmp.name)/'test.sqlite3')

    def test_link_chain_unlink_and_original_ownership(self):
        add_event(self.store,123,'join','FFC','2025-01-01',88,'Evidence')
        link_accounts(self.store,123,456,88,'Lincoln','Confirmed switch')
        link_accounts(self.store,456,789,88,'Lincoln','Next switch')
        with connect(self.store.path) as db:
            self.assertEqual(linked_accounts(db,789),{123,456,789})
            self.assertEqual(db.execute('SELECT user_id FROM rolodex_manual_event').fetchone()[0],123)
        with self.assertRaises(ValueError):
            link_accounts(self.store,789,123,88,'Lincoln','Cycle')
        link_accounts(self.store,123,456,88,'Lincoln','Mistaken account',active=False)
        with connect(self.store.path) as db:
            self.assertEqual(linked_accounts(db,789),{456,789})
            self.assertEqual(linked_accounts(db,123),{123})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rolodex_account_link').fetchone()[0],3)

    def test_note_revisions_deletion_restore_and_linked_visibility(self):
        key=save_note(self.store,123,'Needs derby help',88,'Lincoln')
        link_accounts(self.store,123,456,88,'Lincoln','Confirmed')
        save_note(self.store,None,'Has completed training',99,'Fancy',note_id=key,reason='Updated')
        with connect(self.store.path) as db:
            row=notes(db,linked_accounts(db,456))[0]
            self.assertEqual(row['body'],'Has completed training')
            self.assertEqual(row['added_by'],'Lincoln')
            self.assertEqual(row['actor_id'],99)
        save_note(self.store,None,'',99,'Fancy',note_id=key,reason='Obsolete',deleted=True)
        with connect(self.store.path) as db:
            self.assertEqual(notes(db,{123}),[])
        save_note(self.store,None,'Restored note',88,'Lincoln',note_id=key,reason='Restore')
        with connect(self.store.path) as db:
            self.assertEqual(len(notes(db,{123})),1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rolodex_note_revision').fetchone()[0],4)

    def test_compact_timeline_order_transfer_parallel_and_same_day_mistake(self):
        for action,nh,date in [('join','FFM','2025-01-01'),('leave','FFM','2025-02-01'),
                               ('join','FFJ','2025-02-01'),('leave','FFJ','2025-03-01'),
                               ('join','FFC','2025-04-01'),('join','FFG','2025-04-02'),
                               ('leave','FFC','2025-05-01'),('join','FFC','2025-05-01')]:
            add_event(self.store,123,action,nh,date,88,'Evidence')
        with connect(self.store.path) as db:
            result=compact_profile(records(db),{123},[])
        joined='\n'.join(result)
        self.assertIn('Switched from FFM to FFJ on 1st February, 2025',joined)
        self.assertIn('Previously left FFJ on 1st March, 2025',joined)
        self.assertIn('In FFC since 1st April, 2025',joined)
        self.assertIn('In FFG since 2nd April, 2025',joined)
        self.assertNotIn('1st May',joined)
        self.assertLess(joined.index('February'),joined.index('March'))
        self.assertNotIn('Historical reports',joined)

    def test_unknown_baseline_never_invents_start(self):
        selected={'event':[],'manual':[],'membership':[dict(kind='neighborhood',label='FF',
                  started_at=None,first_observed_at='2026-10-25T12:00:00+00:00',
                  ended_at=None,end_observed_at=None)]}
        self.assertEqual(neighborhood_history(selected),['• In FFM (start date unknown)'])

    def test_names_ignore_cosmetic_differences_only_in_display(self):
        rows=[dict(id=i,observed_at=f'2026-10-{20+i:02d}T12:00:00+00:00',value=value)
              for i,value in enumerate(['🐧[P] Lincoln','[P] LINCOLN!','Lincoln’s Farm'])]
        rendered=name_history(rows)
        self.assertEqual(rendered.count('→'),1)
        self.assertIn('Farm',rendered)
        self.assertEqual(len(rows),3)
        self.assertEqual(pretty_date('2026-10-21'),'21st October, 2026')
        self.assertEqual(pretty_date('2026-10-11'),'11th October, 2026')


class IntroductionTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_criteria_searches_linked_ids(self):
        messages=[NS(author=NS(id=999),content='#'+'x'*110,id=1),
                  NS(author=NS(id=123),content='hello',id=2),
                  NS(author=NS(id=123),content='#'+'x'*110,id=3)]
        async def history(**kwargs):
            self.assertEqual(kwargs,dict(oldest_first=False,limit=1000))
            for message in messages:
                yield message
        channel=NS(id=783713419831279697,history=history)
        guild=NS(id=FF_GUILD,fetch_channel=AsyncMock(return_value=channel))
        result=await find_introduction(guild,{123,456})
        self.assertTrue(result.endswith('/3'))

    async def test_note_and_link_commands_are_privileged(self):
        import command_handler
        import commands.commands
        import importlib
        module=importlib.import_module('commands.rolodex')
        for args in (['note','123','secret'],['link','123','456','reason']):
            ctx=NS(guild=NS(id=FF_GUILD),access_type=command_handler.AccessType.PUBLIC,
                   args=args,send=AsyncMock())
            with patch.object(module,'Rolodex') as database:
                await command_handler.Command.available_commands['rolodex'].run(None,ctx)
                database.assert_not_called()

    async def test_council_can_add_note_link_accounts_and_view_combined_profile(self):
        import command_handler
        import commands.commands
        import importlib
        module=importlib.import_module('commands.rolodex')
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store=Rolodex(Path(tmp.name)/'commands.sqlite3')
        ctx=NS(guild=NS(id=FF_GUILD,get_member=lambda uid:NS(display_name='New Farm')),
               access_type=command_handler.AccessType.PRIVILEGED,author_id=88,
               author=NS(display_name='Lincoln'),channel=NS(send=AsyncMock()),
               args=['note','123','Helped with derby'])
        with patch.object(module,'Rolodex',return_value=store), patch.object(module,'find_introduction',new=AsyncMock(return_value='https://example.test/intro')):
            await module.rolodex(None,ctx)
            ctx.args=['link','123','456','Confirmed account switch']
            await module.rolodex(None,ctx)
            ctx.args=['456']
            await module.rolodex(None,ctx)
        body=ctx.channel.send.call_args.kwargs['content']
        self.assertTrue(body.startswith('# New Farm Rolodex'))
        self.assertIn('Helped with derby [added by Lincoln]',body)
        self.assertIn('https://example.test/intro',body)
        with connect(store.path) as db:
            self.assertEqual(notes(db,{123})[0]['user_id'],123)
