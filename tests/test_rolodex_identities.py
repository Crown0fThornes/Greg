from datetime import datetime,timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from persistence.import_membership_history import HistoryImporter,JOINLIST
from persistence.sqlite_db import connect
from persistence.rolodex import Rolodex,FF_GUILD
from persistence.rolodex_identities import groups,change_identity,similar_groups,stripped_name
from persistence.rolodex_records import records,edit_record


class IdentityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store=Rolodex(Path(tmp.name)/'test.sqlite3')
        self.importer=HistoryImporter(self.store,999)

    def ingest(self,name,mid):
        message=NS(id=mid,guild=NS(id=FF_GUILD),channel=NS(id=JOINLIST),author=NS(id=999),
                   content=name+' has joined ffc',created_at=datetime(2026,10,25,tzinfo=timezone.utc))
        self.importer.ingest(message)

    def data(self):
        with connect(self.store.path) as db:
            event_rows=records(db)['event']
            return groups(db,event_rows),event_rows

    def test_normalized_variants_group_once_and_bulk_link_survives_reimport(self):
        for i,name in enumerate(['🐧[P] Lincoln','{P} Lincoln 🎂','LINCOLN'],1):
            self.ingest(name,i)
        groups_,events=self.data()
        self.assertEqual(len(groups_),1)
        key=groups_[0]['id']
        self.assertEqual(len(groups_[0]['events']),3)
        change_identity(self.store,'link',key,123,88,'Confirmed')
        self.ingest('🐧[P] Lincoln',1)
        self.assertEqual({r['user_id'] for r in self.data()[1]},{123})
        with connect(self.store.path) as db:
            self.assertIsNone(db.execute('SELECT user_id FROM membership_event LIMIT 1').fetchone()[0])

    def test_confirm_unknown_merge_and_later_attach_id(self):
        self.ingest('Lincoln',1)
        self.ingest('Lincolns Farm',2)
        a,b=[g['id'] for g in self.data()[0]]
        change_identity(self.store,'unknown',a,None,88,'Same person, departed account unknown')
        change_identity(self.store,'merge',b,a,88,'Same player')
        merged=self.data()[0]
        self.assertEqual(len(merged),1)
        self.assertTrue(merged[0]['confirmed'])
        self.assertIsNone(merged[0]['user_id'])
        change_identity(self.store,'link',a,123,88,'Found account ID')
        self.assertEqual({r['user_id'] for r in self.data()[1]},{123})

    def test_fuzzy_suggestions_never_auto_merge(self):
        self.ingest("Lincoln's Farm",1)
        self.ingest('Lincolns Farm',2)
        found=self.data()[0]
        self.assertEqual(len(found),2)
        self.assertEqual(similar_groups(found[0],found)[0][1]['id'],found[1]['id'])
        self.assertTrue(all(r['user_id'] is None for r in self.data()[1]))

    def test_split_and_individual_overrides_survive_reimport(self):
        self.ingest('[P] Lincoln',1)
        self.ingest('Lincoln',2)
        key=self.data()[0][0]['id']
        change_identity(self.store,'link',key,123,88,'Confirmed')
        other=change_identity(self.store,'split','1:1:0',None,88,'Different person reused name')
        self.ingest('[P] Lincoln',1)
        event={r['record_key']:r for r in self.data()[1]}
        self.assertEqual(event['1:1:0']['identity_id'],other)
        self.assertIsNone(event['1:1:0']['user_id'])
        edit_record(self.store,'event','2:1:0','user_id','456',88,'Account correction')
        self.assertEqual({r['record_key']:r for r in self.data()[1]}['2:1:0']['user_id'],456)

    def test_short_or_empty_names_stay_separate_and_cycles_rejected(self):
        self.ingest('A',1)
        self.ingest('A',2)
        self.assertEqual(len(self.data()[0]),2)
        a,b=[g['id'] for g in self.data()[0]]
        change_identity(self.store,'merge',a,b,88,'Verified same person')
        with self.assertRaises(ValueError):
            change_identity(self.store,'merge',b,a,88,'Cycle')

    def test_known_id_conflicts_require_account_linking(self):
        self.ingest('Lincoln',1)
        self.ingest('Lincolns Farm',2)
        a,b=[g['id'] for g in self.data()[0]]
        change_identity(self.store,'link',a,123,88,'Confirmed')
        change_identity(self.store,'link',b,456,88,'Confirmed')
        with self.assertRaises(ValueError):
            change_identity(self.store,'merge',a,b,88,'Switch accounts')

    def test_new_reused_name_with_conflicting_candidate_stays_unknown(self):
        self.ingest('Lincoln',1)
        identity=self.data()[0][0]['id']
        change_identity(self.store,'link',identity,123,88,'Confirmed old reports')
        self.importer.add_member(NS(id=456,name='Lincoln',global_name=None,nick=None,display_name='Lincoln'))
        self.ingest('Lincoln',2)
        events={r['message_id']:r for r in self.data()[1]}
        self.assertEqual(events[1]['user_id'],123)
        self.assertIsNone(events[2]['user_id'])
        self.assertNotEqual(events[1]['identity_id'],events[2]['identity_id'])

    def test_explained_suggestions_use_confirmation_and_report_conflicts(self):
        from persistence.rolodex_identities import richer_suggestions
        self.ingest("Lincoln's Farm",1)
        self.ingest('Lincolns Farm',2)
        found=self.data()[0]
        change_identity(self.store,'link',found[0]['id'],123,88,'Confirmed farm owner')
        found=self.data()[0]
        unreviewed=next(g for g in found if not g['confirmed'])
        with connect(self.store.path) as db:
            suggestions=richer_suggestions(db,unreviewed,found)
        self.assertEqual(suggestions[0]['user_id'],123)
        self.assertTrue(any('Council-confirmed' in reason for reason in suggestions[0]['reasons']))
        self.assertTrue(any('shared neighborhood' in reason for reason in suggestions[0]['reasons']))
        self.assertTrue(suggestions[0]['sources'])
        self.assertIsNone(next(g for g in self.data()[0] if g['id']==unreviewed['id'])['user_id'])
        # A different account's recorded name supplies contradictory identity evidence.
        self.store.observe_user(NS(id=456,name='Lincolns Farm',global_name=None))
        with connect(self.store.path) as db:
            suggestions=richer_suggestions(db,unreviewed,found)
        self.assertEqual({s['user_id'] for s in suggestions},{123,456})
        self.assertTrue(all(s['conflicts'] for s in suggestions))

    def test_explicit_mention_is_explained_as_identity_evidence(self):
        from persistence.rolodex_identities import richer_suggestions
        self.ingest('Lincoln (<@123>)',1)
        self.ingest('[P] Lincoln',2)
        found=self.data()[0]
        with connect(self.store.path) as db:
            suggestions=richer_suggestions(db,found[0],found)
        self.assertEqual(suggestions[0]['user_id'],123)
        self.assertTrue(any('Discord mention' in reason for reason in suggestions[0]['reasons']))
