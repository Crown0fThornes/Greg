from datetime import datetime,timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from persistence.rolodex import Rolodex,FF_GUILD
from persistence.sqlite_db import connect
from persistence.import_membership_history import HistoryImporter,JOINLIST
from persistence.rolodex_records import records
from persistence.rolodex_identities import change_identity
from commands.rolodex_provisional import profile_matches,suggestion_lines


class ProvisionalTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store=Rolodex(Path(tmp.name)/'profile.sqlite3')
        self.store.observe_user(NS(id=123,name='graytr',global_name='Graytr Grayn'))
        self.importer=HistoryImporter(self.store,999)

    def add(self,name,mid):
        self.importer.ingest(NS(id=mid,guild=NS(id=FF_GUILD),channel=NS(id=JOINLIST),author=NS(id=999),
                                content=name+' has joined ffc',created_at=datetime(2026,10,25,tzinfo=timezone.utc)))

    def matches(self):
        with connect(self.store.path) as db:
            return profile_matches(db,records(db),{123})

    def test_near_matches_visible_without_becoming_confirmed_history(self):
        self.add('[B] Graytr Grain',1)
        matches=self.matches()
        self.assertEqual(len(matches),1)
        lines,choices=suggestion_lines(matches)
        self.assertIn('needs Council confirmation','\n'.join(lines))
        self.assertTrue(choices)
        with connect(self.store.path) as db:
            self.assertIsNone(records(db)['event'][0]['user_id'])

    def test_confirmed_other_person_and_unrelated_names_not_suggested(self):
        self.add('Graytr Grayn',1)
        self.add('Entirely Different',2)
        matches=self.matches()
        self.assertEqual(len(matches),1)
        change_identity(self.store,'link',matches[0]['group']['id'],456,88,'Confirmed different account')
        self.assertEqual(self.matches(),[])

    def test_confirming_provisional_group_moves_records_to_real_profile_and_scores(self):
        self.add('Graytr Grayn',1)
        self.add('[B] Graytr Grayn',2)
        match=self.matches()[0]
        change_identity(self.store,'link',match['group']['id'],123,88,'Confirmed from profile')
        self.assertEqual(self.matches(),[])
        with connect(self.store.path) as db:
            self.assertEqual({r['user_id'] for r in records(db)['event']},{123})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rolodex_review_point WHERE actor_id=88').fetchone()[0],2)
