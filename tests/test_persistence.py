from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sovereign_colony.kernel import build_experiment_001
from sovereign_colony.persistence import IntegrityError, SQLiteColonyStore


class SQLiteColonyStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "colony.db"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_initialize_and_load_preserve_state_and_hash_chain(self):
        original = build_experiment_001(seed=20260711)
        store = SQLiteColonyStore(self.db_path)

        store.initialize(original)
        loaded = store.load()

        self.assertEqual(original.state_digest(), loaded.state_digest())
        self.assertEqual(8, len(loaded.ledger.events))
        self.assertTrue(loaded.ledger.verify_chain())
        self.assertEqual(0, loaded.colony_day)

    def test_initialize_is_idempotent_and_never_duplicates_genesis(self):
        world = build_experiment_001(seed=20260711)
        store = SQLiteColonyStore(self.db_path)

        store.initialize(world)
        store.initialize(world)

        with closing(sqlite3.connect(self.db_path)) as connection:
            count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        self.assertEqual(8, count)

    def test_save_appends_only_new_events_and_updates_snapshot_atomically(self):
        world = build_experiment_001(seed=20260711)
        store = SQLiteColonyStore(self.db_path)
        store.initialize(world)

        world.colony_day = 1
        world.explore("founder-01", direction="north")
        store.save(world)
        loaded = store.load()

        self.assertEqual(1, loaded.colony_day)
        self.assertEqual(world.state_digest(), loaded.state_digest())
        self.assertEqual(len(world.ledger.events), len(loaded.ledger.events))
        self.assertTrue(loaded.ledger.verify_chain())

    def test_load_fails_closed_when_persisted_event_is_tampered(self):
        world = build_experiment_001(seed=20260711)
        store = SQLiteColonyStore(self.db_path)
        store.initialize(world)

        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                "UPDATE events SET payload_json = ? WHERE sequence = 2",
                ('{"citizen_id":"impostor"}',),
            )
            connection.commit()

        with self.assertRaises(IntegrityError):
            store.load()

    def test_pause_state_defaults_true_and_is_durable(self):
        world = build_experiment_001(seed=20260711)
        store = SQLiteColonyStore(self.db_path)
        store.initialize(world)

        self.assertTrue(store.is_paused())
        store.set_paused(False)

        reopened = SQLiteColonyStore(self.db_path)
        self.assertFalse(reopened.is_paused())


if __name__ == "__main__":
    unittest.main(verbosity=2)
