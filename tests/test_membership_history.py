from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from persistence.import_membership_history import HistoryImporter, JOINLIST, LEAVELIST
from persistence.neighbor_db import connect
from persistence.rolodex import FF_GUILD, Rolodex


class MembershipHistoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Rolodex(Path(tmp.name) / 'history.sqlite3')
        self.importer = HistoryImporter(self.store, 999)
        self.importer.add_member(NS(id=123, name='lincoln', global_name='Lincoln',
                                    nick='[P] Lincoln', display_name='[P] Lincoln'))

    def message(self, content, mid=1, author=999, channel=JOINLIST):
        return NS(id=mid, guild=NS(id=FF_GUILD), channel=NS(id=channel),
                  author=NS(id=author), content=content,
                  created_at=datetime(2026, 10, 25, tzinfo=timezone.utc))

    def events(self, uid=123):
        return self.store.history(uid)['membership_event']

    def test_mentions_multiple_neighborhoods_and_same_day_events_are_preserved(self):
        self.importer.ingest(self.message('[P] Lincoln (<@123>) has joined ffp\n'
                                          '[P] Lincoln (<@123>) has joined ff'))
        self.importer.ingest(self.message('<@!123> has left ffp', mid=2, channel=LEAVELIST))
        self.importer.ingest(self.message('<@123> has joined ffp', mid=3))
        self.assertEqual([(r['action'],r['label']) for r in self.events()],
                         [('join','FFP'), ('join','FF'), ('leave','FFP'), ('join','FFP')])
        self.assertEqual(self.store.history(123)['membership'], [])

    def test_even_unique_display_names_need_confirmation(self):
        self.importer.ingest(self.message('[P] Lincoln has joined ffc'))
        self.assertEqual(self.events(), [])
        review = self.importer.review()['unresolved'][0]
        self.assertEqual(review['candidates'], '[123]')
        self.assertIsNone(review['user_id'])
        self.importer.overrides = {'1:1': 123}
        self.importer.ingest(self.message('[P] Lincoln has joined ffc'))
        self.assertEqual(self.events()[0]['resolution'], 'manual')
        self.assertEqual(self.importer.review()['unresolved'], [])

    def test_human_report_server_departure_and_unparsed_waitlist(self):
        self.importer.ingest(self.message('Knister has left FFJ and the server', author=10))
        self.assertEqual(len(self.importer.review()['unresolved']), 2)
        self.importer.ingest(self.message('Removed Alaska from Junior waitlist, staying in Carnival', mid=2))
        self.assertEqual(len(self.importer.review()['unparsed']), 1)

    def test_repeat_import_and_message_edit_replace_evidence(self):
        message = self.message('<@123> has joined ffg')
        self.importer.ingest(message)
        self.importer.ingest(message)
        self.assertEqual(len(self.events()), 1)
        self.importer.ingest(self.message('<@123> has left ffg'))
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.events()[0]['action'], 'leave')

    def test_ambiguous_mentions_and_names_are_unresolved(self):
        self.importer.add_member(NS(id=456, name='lincoln', global_name=None,
                                    nick=None, display_name='Someone'))
        self.importer.ingest(self.message('lincoln has joined ffr'))
        self.assertEqual(self.importer.review()['unresolved'][0]['candidates'], '[123, 456]')
        self.importer.ingest(self.message('<@123> and <@456> has left ff', mid=2))
        self.assertEqual(self.events(), [])

    def test_upgrade_retains_existing_rows(self):
        self.importer.ingest(self.message('<@123> has joined ff'))
        with connect(self.store.path) as db:
            db.execute('PRAGMA user_version=1')
        Rolodex(self.store.path)
        self.assertEqual(len(self.events()), 1)
        with connect(self.store.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 4)


if __name__ == '__main__':
    unittest.main()
