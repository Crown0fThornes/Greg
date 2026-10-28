import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

from persistence.rolodex import FF_GUILD, Rolodex


class RolodexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'rolodex.sqlite3'
        self.db = Rolodex(self.path)
        self.join = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.now = datetime(2026, 10, 25, tzinfo=timezone.utc)

    def member(self, roles=(), nick='Lincoln', **changes):
        data = dict(id=123, name='lincoln', global_name='Lincoln', nick=nick,
                    guild=NS(id=FF_GUILD, name='Farm Friends'), bot=False,
                    joined_at=self.join, roles=[NS(id=r) for r in roles])
        data.update(changes)
        return NS(**data)

    def history(self):
        return self.db.history(123)

    def test_baseline_is_idempotent_and_preserves_unknown_role_start(self):
        member = self.member([1024052938752151552, 1454590623532191774])
        self.db.observe_member(member, at=self.now)
        self.db = Rolodex(self.path)
        self.db.observe_member(member, at=self.now)
        rows = self.history()['membership']
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['started_at'], None)
        self.assertEqual(rows[-1]['started_at'], self.join.isoformat())
        family = next(r for r in rows if r['kind'] == 'family')
        self.assertEqual((family['label'], family['season']), ('Penguin', 2026))
        self.assertEqual(len(self.history()['name_history']), 3)

    def test_role_transfer_and_nickname_clear(self):
        before = self.member([1024052938752151552, 1454590623532191774])
        after = self.member([1034248720058945577, 1454593861643931684], nick=None)
        self.db.member_updated(before, after, at=self.now)
        rows = self.history()['membership']
        closed = [r for r in rows if r['end_observed_at']]
        self.assertEqual({r['label'] for r in closed}, {'FFP', 'Penguin'})
        self.assertTrue(all(r['ended_at'] == self.now.isoformat() for r in closed))
        opened = [r for r in rows if r['kind'] != 'server' and not r['end_observed_at']]
        self.assertEqual({r['label'] for r in opened}, {'FFR', 'Hippo'})
        self.assertTrue(all(r['started_at'] == self.now.isoformat() for r in opened))
        self.assertIsNone(self.history()['name_history'][-1]['value'])

    def test_leave_rejoin_preserves_both_stays(self):
        member = self.member([1024052938752151552])
        self.db.member_left(member, at=self.now)
        self.db.member_left(member, at=self.now)  # Duplicate leave should not invent a stay.
        rows = self.history()['membership']
        self.assertEqual(len(rows), 2)
        rejoin = datetime(2026, 10, 26, tzinfo=timezone.utc)
        self.db.observe_member(self.member(joined_at=rejoin), at=rejoin, source='gateway')
        self.assertEqual(len(self.history()['membership']), 3)

    def test_downtime_changes_have_unknown_dates(self):
        self.db.observe_member(self.member([1024052938752151552]), at=self.now)
        self.db.observe_member(self.member([1034248720058945577]), at=self.now)
        old = self.history()['membership'][0]
        self.assertIsNone(old['ended_at'])
        self.assertEqual(old['end_source'], 'observation')

    def test_username_history_and_honorary_roles(self):
        before = self.member([1454590623532191774, 1454590996699545741])
        self.db.observe_member(before, at=self.now)
        self.db.user_updated(before, self.member(name='newname'), at=self.now)
        names = [r['value'] for r in self.history()['name_history'] if r['kind'] == 'username']
        self.assertEqual(names, ['lincoln', 'newname'])
        families = [r for r in self.history()['membership'] if r['kind'] == 'family']
        self.assertEqual({r['honorary'] for r in families}, {0, 1})

    def test_server_scope_and_new_stay_during_downtime(self):
        self.db.observe_member(self.member([1024052938752151552]), at=self.now)
        later = datetime(2026, 10, 26, tzinfo=timezone.utc)
        self.db.observe_member(self.member([1024052938752151552], joined_at=later), at=later)
        rows = self.history()['membership']
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r['end_source'] == 'observation' for r in rows[:2]))
        self.db.observe_member(self.member(guild=NS(id=999, name='Other')), at=later)
        self.assertEqual(len(self.history()['membership']), 5)
