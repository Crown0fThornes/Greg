"""Check storage boundaries and transactions using temporary databases only."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from persistence.neighbor_db import connect, initialize_database


class NeighborSchemaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "neighbors.sqlite3"
        initialize_database(self.path)

    def add_inventory(self, connection):
        connection.execute("INSERT INTO neighbor (user_id, guild_id) VALUES (1, 10)")
        item_id = connection.execute(
            "INSERT INTO item (user_id, guild_id, name, type, inventory_position) "
            "VALUES (1, 10, 'Booster', 'xp', 0)"
        ).lastrowid
        connection.execute(
            "INSERT INTO item_attribute (item_id, name, value) VALUES (?, 'amount', '5')",
            (item_id,),
        )
        return item_id

    def test_initialization_is_idempotent_and_preserves_records(self):
        with connect(self.path) as connection:
            self.add_inventory(connection)
        initialize_database(self.path)
        with connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM neighbor").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM item").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT value FROM item_attribute").fetchone()[0], "5")

    def test_same_user_can_have_independent_server_progress(self):
        with connect(self.path) as connection:
            connection.executemany(
                "INSERT INTO neighbor (user_id, guild_id, xp) VALUES (?, ?, ?)",
                [(1, 10, 100), (1, 20, 200)],
            )
            self.assertEqual(
                [row[0] for row in connection.execute("SELECT xp FROM neighbor ORDER BY guild_id")],
                [100, 200],
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO neighbor (user_id, guild_id) VALUES (1, 10)")

    def test_items_require_the_correct_server_owner(self):
        with connect(self.path) as connection:
            connection.execute("INSERT INTO neighbor (user_id, guild_id) VALUES (1, 10)")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO item (user_id, guild_id, name, type, inventory_position) "
                    "VALUES (1, 20, 'Booster', 'xp', 0)"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO item_attribute (item_id, name, value) VALUES (999, 'amount', '5')"
                )

    def test_duplicate_item_names_have_separate_attributes_and_order(self):
        with connect(self.path) as connection:
            first = self.add_inventory(connection)
            second = connection.execute(
                "INSERT INTO item (user_id, guild_id, name, type, expiration, inventory_position) "
                "VALUES (1, 10, 'Booster', 'xp', 0, 1)"
            ).lastrowid
            connection.execute(
                "INSERT INTO item_attribute (item_id, name, value) VALUES (?, 'amount', '10')", (second,)
            )
            rows = connection.execute(
                "SELECT item.item_id, value FROM item JOIN item_attribute USING (item_id) "
                "ORDER BY inventory_position"
            ).fetchall()
            self.assertEqual([tuple(row) for row in rows], [(first, "5"), (second, "10")])
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO item_attribute (item_id, name, value) VALUES (?, 'amount', '20')", (first,)
                )

    def test_deleting_item_only_removes_its_own_attributes(self):
        with connect(self.path) as connection:
            item_id = self.add_inventory(connection)
            connection.execute("DELETE FROM item WHERE item_id = ?", (item_id,))
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM item_attribute").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM neighbor").fetchone()[0], 1)

    def test_deleting_neighbor_cascades_to_inventory_and_attributes(self):
        with connect(self.path) as connection:
            self.add_inventory(connection)
            connection.execute("DELETE FROM neighbor WHERE user_id = 1 AND guild_id = 10")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM item").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM item_attribute").fetchone()[0], 0)

    def test_failed_transaction_leaves_no_partial_player_data(self):
        with self.assertRaises(RuntimeError):
            with connect(self.path) as connection:
                self.add_inventory(connection)
                raise RuntimeError("Simulated failure during an inventory update")
        with connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM neighbor").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM item").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
