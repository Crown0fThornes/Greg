from datetime import datetime,timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from persistence.import_membership_history import HistoryImporter,JOINLIST
from persistence.sqlite_db import connect
from persistence.rolodex import Rolodex,FF_GUILD
from persistence.rolodex_identities import change_identity,groups
from persistence.rolodex_records import records,edit_record
from persistence.rolodex_scoring import leaderboard


class ScoringTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store=Rolodex(Path(tmp.name)/'points.sqlite3')
        self.importer=HistoryImporter(self.store,999)

    def add(self,name,mid):
        self.importer.ingest(NS(id=mid,guild=NS(id=FF_GUILD),channel=NS(id=JOINLIST),author=NS(id=999),
                                content=name+' has joined ffc',created_at=datetime(2026,10,25,tzinfo=timezone.utc)))

    def identities(self):
        with connect(self.store.path) as db:
            return groups(db,records(db)['event'])

    def scores(self):
        with connect(self.store.path) as db:
            return {r['actor_id']:r['points'] for r in leaderboard(db)}

    def test_two_records_linked_as_one_person_earn_two_not_one(self):
        self.add('Cam',1)
        self.add('[H] Cam',2)
        change_identity(self.store,'link',self.identities()[0]['id'],123,88,'Confirmed')
        self.assertEqual(self.scores(),{88:2})
        self.add('Cam',1)
        self.assertEqual(self.scores(),{88:2})

    def test_unknown_counts_and_reopening_does_not_double_credit(self):
        self.add('Cam',1)
        key=self.identities()[0]['id']
        change_identity(self.store,'unknown',key,None,88,'Confirmed unknown account')
        self.assertEqual(self.scores(),{88:1})
        change_identity(self.store,'reopen',key,None,99,'Review again')
        change_identity(self.store,'link',key,123,99,'Confirmed account')
        self.assertEqual(self.scores(),{88:1})

    def test_unresolved_merge_scores_only_when_the_records_are_cleared(self):
        self.add('Cam',1)
        self.add('Cams Farm',2)
        a,b=[g['id'] for g in self.identities()]
        merged=change_identity(self.store,'merge',a,b,88,'Same person')
        self.assertEqual(self.scores(),{})
        change_identity(self.store,'unknown',merged,None,99,'Confirmed person')
        self.assertEqual(self.scores(),{99:2})

    def test_merge_into_confirmed_person_scores_only_new_records(self):
        self.add('Cam',1)
        self.add('Cams Farm',2)
        a,b=[g['id'] for g in self.identities()]
        change_identity(self.store,'link',a,123,88,'Confirmed')
        change_identity(self.store,'merge',b,a,99,'Same person')
        self.assertEqual(self.scores(),{88:1,99:1})

    def test_individual_clearance_and_hide_each_count_once(self):
        self.add('Cam',1)
        self.add('[H] Cam',2)
        edit_record(self.store,'event','1:1:0','user_id',123,88,'Confirmed')
        edit_record(self.store,'event','2:1:0','excluded','true',99,'Mistaken report')
        change_identity(self.store,'link',self.identities()[0]['id'],123,88,'Confirmed group')
        self.assertEqual(self.scores(),{88:1,99:1})

    def test_invalid_decision_does_not_award_points(self):
        self.add('Cam',1)
        key=self.identities()[0]['id']
        with self.assertRaises(ValueError):
            change_identity(self.store,'link',key,0,88,'Invalid account')
        self.assertEqual(self.scores(),{})


class LeaderboardCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_standings_are_clickable_without_notifications(self):
        import importlib
        from unittest.mock import AsyncMock,patch
        import command_handler
        import commands.commands
        module=importlib.import_module('commands.rolodex')
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store=Rolodex(Path(tmp.name)/'points.sqlite3')
        with connect(store.path) as db:
            db.execute("INSERT INTO rolodex_review_point VALUES (1,1,0,88,'identity link','2026-11-06')")
            db.execute("INSERT INTO rolodex_review_point VALUES (2,1,0,88,'identity link','2026-11-06')")
        guild=NS(id=FF_GUILD,fetch_member=AsyncMock())
        context=NS(guild=guild,args=['leaderboard'],author_id=88,
                   access_type=command_handler.AccessType.PRIVILEGED,channel=NS(send=AsyncMock()))
        with patch.object(module,'Rolodex',return_value=store):
            await module.rolodex(None,context)
        content=context.channel.send.call_args.kwargs['content']
        self.assertIn('<@88> (88)',content)
        self.assertIn('**2** points',content)
        self.assertFalse(context.channel.send.call_args.kwargs['allowed_mentions'].users)
        guild.fetch_member.assert_awaited_once_with(88)
