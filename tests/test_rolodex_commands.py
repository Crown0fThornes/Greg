import importlib
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

import command_handler
from persistence.import_membership_history import HistoryImporter, JOINLIST
from persistence.neighbor_db import connect
from persistence.rolodex import FF_GUILD, Rolodex
from persistence.rolodex_records import add_event, edit_record, records
from datetime import datetime, timezone


class RolodexCorrectionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Rolodex(Path(tmp.name) / 'test.sqlite3')
        self.importer = HistoryImporter(self.store, 999)
        self.message = NS(id=456, guild=NS(id=FF_GUILD), channel=NS(id=JOINLIST),
                          author=NS(id=999), content='Fancy has joined ffc',
                          created_at=datetime(2026,10,25,tzinfo=timezone.utc))
        self.importer.ingest(self.message)

    def rows(self):
        with connect(self.store.path) as db:
            return records(db)

    def test_link_survives_reimport_and_reset_preserves_evidence(self):
        edit_record(self.store, 'event', '456:1:0', 'user_id', '123', 88, 'Confirmed by Council')
        self.importer.ingest(self.message)
        self.assertEqual(self.rows()['event'][0]['user_id'], 123)
        with connect(self.store.path) as db:
            self.assertIsNone(db.execute('SELECT user_id FROM membership_event').fetchone()[0])
            audit = db.execute('SELECT * FROM rolodex_edit').fetchone()
            self.assertEqual(audit['actor_id'], 88)
            self.assertEqual(audit['reason'], 'Confirmed by Council')
        edit_record(self.store, 'event', '456:1:0', 'user_id', None, 88, 'Mistaken identity', reset=True)
        self.assertIsNone(self.rows()['event'][0]['user_id'])

    def test_manual_add_corrections_and_exclusions(self):
        key = add_event(self.store, 123, 'join', 'ffg', '2026-10-25', 88, 'Ticket evidence')
        self.assertEqual(self.rows()['manual'][0]['occurred_at'], '2026-10-25T04:00:00+00:00')
        edit_record(self.store, 'manual', str(key), 'excluded', 'true', 88, 'Duplicate')
        self.assertTrue(self.rows()['manual'][0]['excluded'])
        edit_record(self.store, 'manual', str(key), 'excluded', None, 88, 'Restore evidence', reset=True)
        self.assertFalse(self.rows()['manual'][0]['excluded'])

    def test_validation_and_rejected_edit_has_no_audit(self):
        for field, value in [('user_id','-1'), ('action','maybe'), ('label','NOPE'), ('occurred_at','bad-date'), ('excluded','perhaps')]:
            with self.assertRaises(ValueError):
                edit_record(self.store,'event','456:1:0',field,value,88,'Reason')
        with self.assertRaises(ValueError):
            edit_record(self.store,'event','456:1:0','label','FFJ',88,'')
        with connect(self.store.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rolodex_edit').fetchone()[0], 0)

    def test_normal_display_transfer_and_reversal_raw_keeps_all(self):
        module = importlib.import_module('commands.rolodex')
        add_event(self.store, 123, 'leave','FFC','2026-10-25',88,'Evidence')
        add_event(self.store, 123, 'join','FFG','2026-10-25',88,'Evidence')
        add_event(self.store, 123, 'leave','FFJ','2026-10-24',88,'Evidence')
        add_event(self.store, 123, 'join','FFJ','2026-10-24',88,'Evidence')
        rendered = '\n'.join(module.profile_lines(self.rows(),123))
        self.assertIn('Switched from FFC to FFG',rendered)
        self.assertNotIn('Previously left FFJ',rendered)
        raw = module.profile_lines(self.rows(),123,raw=True)
        self.assertEqual(len(raw),4)


class RolodexCommandAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_user_cannot_open_or_edit_database(self):
        module = importlib.import_module('commands.rolodex')
        # Loading the facade is the supported registration path (including reloads).
        import commands.commands
        context = NS(guild=NS(id=FF_GUILD), access_type=command_handler.AccessType.PUBLIC,
                     send=AsyncMock(), args=['edit','event','456:1:0','user_id','123','Reason'])
        with patch.object(module,'Rolodex') as constructor:
            await command_handler.Command.available_commands['rolodex'].run(None,context)
            constructor.assert_not_called()
        context.send.assert_awaited_once()

    async def test_privileged_lookup_never_pings(self):
        module = importlib.import_module('commands.rolodex')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = Rolodex(Path(tmp.name)/'test.sqlite3')
        context = NS(guild=NS(id=FF_GUILD,get_member=lambda uid: None),
                     access_type=command_handler.AccessType.PRIVILEGED,
                     channel=NS(send=AsyncMock()), args=['123'],author_id=88)
        with patch.object(module,'Rolodex',return_value=store), patch.object(module,'find_introduction',new=AsyncMock(return_value='Not found.')):
            await module.rolodex(None,context)
        context.channel.send.assert_awaited_once()
        kwargs = context.channel.send.call_args.kwargs
        self.assertFalse(kwargs['allowed_mentions'].users)
        self.assertIn('No names recorded',kwargs['content'])
