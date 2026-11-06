"""Rolling migration tests. All SQL databases and text shards are temporary."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import custom_types
from custom_types import Item, Neighbor
from persistence import neighbor_db, neighbor_store

FF = 647883751853916162


class NeighborSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.db_path = root/'neighbors.sqlite3'
        self.files = [root/f'neighbors{i}.txt' for i in range(10)]
        self.addCleanup(patch.stopall)
        patch.object(custom_types, 'fNeighbors_names', [str(path) for path in self.files]).start()
        patch.dict(os.environ, GREG_NEIGHBOR_DB=str(self.db_path), GREG_NEIGHBOR_STORAGE='sqlite').start()

    def legacy(self, uid, gid=FF, xp=100, legacy_xp=200, items=(), newline='\n', zero_guild=False):
        record = Neighbor(uid, gid, link=False)
        record.XP, record.legacyXP, record.inventory = xp, legacy_xp, list(items)
        line = record.encode()
        if zero_guild:
            line = line.replace(f':{FF}:', ':0:', 1)
        path = self.files[uid % 10]
        with path.open('a', encoding='utf-8') as output:
            output.write(line + newline)
        return record

    def row(self, uid, gid=FF):
        with neighbor_db.connect(self.db_path) as db:
            row = db.execute('SELECT * FROM neighbor WHERE user_id=? AND guild_id=?',(uid,gid)).fetchone()
            return dict(row) if row else None

    def count(self):
        with neighbor_db.connect(self.db_path) as db:
            return db.execute('SELECT COUNT(*) FROM neighbor').fetchone()[0]

    def text_record(self, uid, gid=FF):
        matches = [Neighbor.decode(line) for line in self.files[uid%10].read_text().splitlines()
                   if line.strip() and custom_types._text_identity(line)==(uid,gid)]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_constructor_migrates_only_requested_player_with_full_inventory(self):
        items = [Item('Booster','perk',-1, boost='5', label='🌷'),
                 Item('Booster','perk',1700000000, boost='10'),
                 Item('LTO','event_emoji',1900000000, emoji='🎂',display='None',awarded_at='1700000000')]
        self.legacy(101,xp=1234,legacy_xp=5678,items=items)
        self.legacy(202,xp=999)
        neighbor = Neighbor(101,FF)
        self.assertEqual((neighbor.XP,neighbor.legacyXP),(1234,5678))
        self.assertEqual([item.encode() for item in neighbor.inventory],[item.encode() for item in items])
        self.assertEqual(self.count(),1)
        self.assertIsNone(self.row(202))
        self.assertEqual(self.text_record(101).XP,1234)
        with neighbor_db.connect(self.db_path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM item').fetchone()[0],3)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_sql_is_authoritative_and_repairs_stale_text_on_access(self):
        self.legacy(101,xp=100)
        Neighbor(101,FF)
        with neighbor_db.connect(self.db_path) as db:
            db.execute('UPDATE neighbor SET xp=777 WHERE user_id=101')
        neighbor = Neighbor(101,FF)
        self.assertEqual(neighbor.get_XP(),777)
        self.assertEqual(self.text_record(101).XP,777)
        self.assertEqual(self.count(),1)

    def test_sql_only_record_is_loaded_and_mirrored(self):
        neighbor_db.initialize_database(self.db_path)
        with neighbor_db.connect(self.db_path) as db:
            db.execute('INSERT INTO neighbor VALUES (101,?,444,555)',(FF,))
        neighbor = Neighbor(101,FF)
        self.assertEqual(neighbor.XP,444)
        self.assertEqual(self.text_record(101).legacyXP,555)

    def test_new_player_starts_empty_in_both_stores(self):
        neighbor = Neighbor(101,FF)
        self.assertEqual((neighbor.XP,neighbor.legacyXP,neighbor.inventory),(0,0,[]))
        self.assertEqual(self.row(101)['xp'],0)
        self.assertEqual(self.text_record(101).inventory,[])

    def test_same_user_is_independent_in_each_server(self):
        self.legacy(101,FF,xp=100)
        self.legacy(101,20,xp=200)
        main = Neighbor(101,FF)
        other = Neighbor(101,20)
        main.increase_XP(5)
        self.assertEqual(other.get_XP(),200)
        self.assertEqual(self.row(101)['xp'],105)
        self.assertEqual(self.text_record(101,20).XP,200)
        self.assertEqual(self.count(),2)

    def test_legacy_zero_server_is_normalized_without_duplicates(self):
        self.legacy(101,xp=999,zero_guild=True)
        self.assertEqual(Neighbor(101,0).get_XP(),999)
        self.assertEqual(Neighbor(101).get_family(),FF)
        self.assertEqual(self.count(),1)
        self.assertEqual(self.text_record(101).family,FF)

    def test_line_endings_and_missing_final_newline_are_supported(self):
        for uid,newline in ((101,'\n'),(202,'\r\n'),(303,'')):
            self.legacy(uid,xp=123,newline=newline)
            self.assertEqual(Neighbor(uid,FF).get_XP(),123)

    def test_getters_mutations_expiration_and_items_dual_write(self):
        neighbor = Neighbor(101,FF)
        neighbor.increase_XP(1000)
        neighbor.set_legacy_XP(222)
        neighbor.bestow_item(Item('Custom Nickname Emoji','custom_nickname_emoji',-1,emoji='🦄'))
        neighbor.bestow_item(Item('Expired','perk',1))
        item = neighbor.get_item_of_name('Custom Nickname Emoji')
        item.update_value('emoji','🚀')
        neighbor.update_item(item)
        neighbor.expire_items()
        self.assertEqual(self.row(101)['xp'],1000)
        self.assertEqual(self.row(101)['legacy_xp'],222)
        self.assertEqual([item.get_value('emoji') for item in Neighbor(101,FF).get_inventory()],['🚀'])
        self.assertEqual(self.text_record(101).get_inventory()[0].get_value('emoji'),'🚀')
        neighbor.vacate_item(neighbor.get_item_of_name('Custom Nickname Emoji'))
        self.assertEqual(self.text_record(101).inventory,[])

    def test_item_ids_survive_updates_and_reordering(self):
        neighbor = Neighbor(101,FF)
        neighbor.bestow_item(Item('One','perk',-1,amount='1'))
        neighbor.bestow_item(Item('Two','perk',-1,amount='2'))
        old = {item.name:item._sqlite_item_id for item in neighbor.get_inventory()}
        neighbor.pull()
        neighbor.inventory.reverse()
        neighbor.push()
        reloaded = Neighbor(101,FF).get_inventory()
        self.assertEqual([item.name for item in reloaded],['Two','One'])
        self.assertEqual({item.name:item._sqlite_item_id for item in reloaded},old)

    def test_detached_construction_decoding_and_dummy_do_not_touch_storage(self):
        self.legacy(101)
        detached = Neighbor.decode(self.files[1].read_text())
        detached.increase_XP(5)
        dummy = Neighbor()
        dummy.increase_XP(5)
        self.assertFalse(self.db_path.exists())
        self.assertEqual(self.text_record(101).XP,100)
        self.assertEqual(detached.XP,105)

    def test_bulk_read_prefers_sql_but_does_not_enroll_text_only_players(self):
        self.legacy(101)
        self.legacy(202)
        Neighbor(101,FF).set_XP(555)
        # Deliberately stale text must not become authoritative through bulk reads.
        self.files[1].write_text(self.legacy_line(101,xp=1))
        rows = Neighbor.read_all_neighbors()
        self.assertEqual({n.ID:n.XP for n in rows},{101:555,202:100})
        self.assertTrue(all(not n.secure for n in rows))
        self.assertEqual(self.count(),1)

    def test_first_bulk_read_creates_no_player_rows(self):
        self.legacy(101)
        self.legacy(202)
        self.assertEqual(len(Neighbor.read_all_neighbors()),2)
        self.assertEqual(self.count(),0)

    def test_bulk_read_uses_sql_even_when_its_text_mirror_is_malformed(self):
        Neighbor(101,FF).set_XP(42)
        self.files[1].write_text(f'101:{FF}:broken:0:\n')
        self.assertEqual([(n.ID,n.XP) for n in Neighbor.read_all_neighbors()],[(101,42)])

    def legacy_line(self, uid, xp=100):
        record = Neighbor(uid,FF,link=False)
        record.XP=xp
        return record.encode()+'\n'

    def test_bulk_read_includes_sql_only_players(self):
        Neighbor(101,FF).set_XP(12)
        self.files[1].unlink()
        self.assertEqual([(n.ID,n.XP) for n in Neighbor.read_all_neighbors()],[(101,12)])

    def test_bulk_write_updates_enrolled_and_text_only_without_eager_migration(self):
        self.legacy(101)
        self.legacy(202)
        Neighbor(101,FF)
        rows = Neighbor.read_all_neighbors()
        for neighbor in rows:
            neighbor.increase_XP(5)
        Neighbor.write_all_neighbors(rows)
        self.assertEqual(self.row(101)['xp'],105)
        self.assertIsNone(self.row(202))
        self.assertEqual(self.text_record(202).XP,105)
        self.assertEqual(Neighbor(202,FF).get_XP(),105)
        self.assertEqual(self.count(),2)

    def test_bulk_deletion_cascades_and_does_not_resurrect_removed_player(self):
        first = Neighbor(101,FF)
        first.bestow_item(Item('Tag','perk',-1,emoji='🌷'))
        Neighbor(202,FF)
        rows = [row for row in Neighbor.read_all_neighbors() if row.ID!=101]
        Neighbor.write_all_neighbors(rows)
        self.assertIsNone(self.row(101))
        self.assertEqual([row.ID for row in Neighbor.read_all_neighbors()],[202])
        with neighbor_db.connect(self.db_path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM item').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM item_attribute').fetchone()[0],0)

    def test_malformed_matching_record_fails_without_overwriting_or_importing(self):
        bad='101:'+str(FF)+':not-an-integer:200:\n'
        self.files[1].write_text(bad)
        with self.assertRaises(ValueError):
            Neighbor(101,FF)
        self.assertEqual(self.files[1].read_text(),bad)
        self.assertIsNone(self.row(101))

    def test_other_shard_records_are_preserved_byte_for_byte(self):
        self.legacy(111,xp=99)
        original=self.files[1].read_bytes()
        Neighbor(101,FF).set_XP(55)
        self.assertTrue(self.files[1].read_bytes().endswith(original))
        self.assertIsNone(self.row(111))

    def test_sql_failure_does_not_fall_back_to_stale_text(self):
        Neighbor(101,FF).set_XP(100)
        with patch.object(neighbor_store.Session,'load',side_effect=sqlite3.OperationalError('broken SQL')):
            with self.assertRaises(sqlite3.OperationalError):
                Neighbor(101,FF)
        self.assertEqual(self.row(101)['xp'],100)
        self.assertEqual(self.text_record(101).XP,100)

    def test_text_write_failure_rolls_back_sql_and_object(self):
        neighbor=Neighbor(101,FF)
        before=self.files[1].read_bytes()
        with patch.object(neighbor_store,'_atomic_replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                neighbor.increase_XP(5)
        self.assertEqual(self.row(101)['xp'],0)
        self.assertEqual(self.files[1].read_bytes(),before)
        self.assertEqual(neighbor.XP,0)

    def test_failed_constructor_backup_does_not_partially_enroll_player(self):
        self.legacy(101,xp=123,zero_guild=True)
        before=self.files[1].read_bytes()
        with patch.object(neighbor_store,'_atomic_replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                Neighbor(101,FF)
        self.assertIsNone(self.row(101))
        self.assertEqual(self.files[1].read_bytes(),before)

    def test_attributes_that_break_legacy_format_are_rejected_without_losing_data(self):
        neighbor=Neighbor(101,FF)
        before=self.files[1].read_bytes()
        with self.assertRaisesRegex(ValueError,'legacy text backup'):
            neighbor.bestow_item(Item('Bad','perk',-1,value='cannot:roundtrip'))
        self.assertEqual(self.files[1].read_bytes(),before)
        self.assertEqual(neighbor.get_inventory(),[])
        with neighbor_db.connect(self.db_path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM item').fetchone()[0],0)

    def test_commit_failure_restores_text_and_sql(self):
        neighbor=Neighbor(101,FF)
        before=self.files[1].read_bytes()
        real_connect=neighbor_db.connect
        @contextmanager
        def failed_commit(path):
            with real_connect(path) as db:
                yield db
                raise sqlite3.OperationalError('simulated commit failure')
        with patch.object(neighbor_db,'connect',failed_commit):
            with self.assertRaises(sqlite3.OperationalError):
                neighbor.increase_XP(5)
        self.assertEqual(self.files[1].read_bytes(),before)
        self.assertEqual(self.row(101)['xp'],0)

    def test_multi_file_bulk_failure_restores_already_written_shards(self):
        Neighbor(101,FF).set_XP(100)
        Neighbor(202,FF).set_XP(200)
        rows=Neighbor.read_all_neighbors()
        for row in rows: row.increase_XP(1)
        before={path:path.read_bytes() for path in self.files if path.exists()}
        replace=neighbor_store._atomic_replace
        def fail_second(path,content):
            if Path(path)==self.files[2]: raise OSError('disk full')
            replace(path,content)
        with patch.object(neighbor_store,'_atomic_replace',fail_second):
            with self.assertRaises(OSError): Neighbor.write_all_neighbors(rows)
        self.assertEqual({path:path.read_bytes() for path in self.files if path.exists()},before)
        self.assertEqual(self.row(101)['xp'],100)
        self.assertEqual(self.row(202)['xp'],200)

    def test_nested_methods_share_snapshot_and_failed_method_does_not_save(self):
        neighbor=Neighbor(101,FF)
        @Neighbor.secure_sync()
        def change_then_read(self):
            self.XP+=42
            return self.get_XP()
        self.assertEqual(change_then_read(neighbor),42)
        self.assertEqual(self.row(101)['xp'],42)
        @Neighbor.secure_sync()
        def change_then_fail(self):
            self.increase_XP(100)
            raise RuntimeError('failed operation')
        with self.assertRaises(RuntimeError): change_then_fail(neighbor)
        self.assertEqual(self.row(101)['xp'],42)
        self.assertEqual(self.text_record(101).XP,42)
        self.assertEqual(neighbor.XP,42)

    def test_threaded_increments_do_not_lose_updates(self):
        Neighbor(101,FF)
        def increment(_):
            Neighbor(101,FF).increase_XP(1)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(increment,range(40)))
        self.assertEqual(self.row(101)['xp'],40)
        self.assertEqual(self.text_record(101).XP,40)

    def test_shared_instance_threaded_increments_are_also_serialized(self):
        neighbor=Neighbor(101,FF)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _:neighbor.increase_XP(1),range(40)))
        self.assertEqual(self.row(101)['xp'],40)
        self.assertEqual(self.text_record(101).XP,40)

    def test_explicit_text_rollback_mode_does_not_read_or_modify_sql(self):
        Neighbor(101,FF).set_XP(100)
        with patch.dict(os.environ,GREG_NEIGHBOR_STORAGE='text'):
            neighbor=Neighbor(101,FF)
            neighbor.increase_XP(5)
            self.assertEqual(neighbor.get_XP(),105)
            self.assertEqual(self.text_record(101).XP,105)
        self.assertEqual(self.row(101)['xp'],100)


if __name__=='__main__':
    unittest.main()
