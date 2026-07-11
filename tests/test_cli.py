import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from sovereign_colony.cli import main
from sovereign_colony.persistence import SQLiteColonyStore


class OperatorCliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db = self.root / "colony.db"

    def tearDown(self):
        self.tempdir.cleanup()

    def _run(self, *arguments: str) -> dict:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(arguments))
        self.assertEqual(0, code)
        return json.loads(output.getvalue())

    def test_init_status_resume_and_pause_controls(self):
        initialized = self._run("init", "--db", str(self.db), "--seed", "20260711")
        self.assertEqual(0, initialized["colony_day"])
        self.assertTrue(initialized["paused"])

        resumed = self._run("resume", "--db", str(self.db))
        self.assertFalse(resumed["paused"])
        status = self._run("status", "--db", str(self.db))
        self.assertEqual(7, status["living_citizens"])
        self.assertFalse(status["paused"])

        paused = self._run("pause", "--db", str(self.db))
        self.assertTrue(paused["paused"])

    def test_prepare_creates_the_next_day_batch(self):
        self._run("init", "--db", str(self.db), "--seed", "20260711")
        self._run("resume", "--db", str(self.db))

        prepared = self._run(
            "prepare",
            "--db",
            str(self.db),
            "--batch-root",
            str(self.root / "batches"),
            "--model",
            "qwen2.5:1.5b",
        )

        self.assertEqual(1, prepared["target_day"])
        self.assertTrue(Path(prepared["batch_dir"]).is_dir())
        self.assertEqual(7, len(prepared["citizens"]))

    def test_emergency_pause_is_durable_and_audited(self):
        self._run("init", "--db", str(self.db), "--seed", "20260711")
        self._run("resume", "--db", str(self.db))

        result = self._run(
            "emergency-pause",
            "--db",
            str(self.db),
            "--reason",
            "sandbox boundary alarm",
        )

        store = SQLiteColonyStore(self.db)
        world = store.load()
        self.assertTrue(result["paused"])
        self.assertTrue(store.is_paused())
        self.assertEqual("creator.emergency_pause", world.ledger.events[-1].event_type)
        self.assertEqual("sandbox boundary alarm", world.ledger.events[-1].payload["reason"])

    def test_validate_response_checks_the_exact_decision_contract(self):
        response = self.root / "response.json"
        response.write_text(
            '{"action":"rest","reason":"Observe first."}', encoding="utf-8"
        )

        result = self._run("validate-response", "--file", str(response))

        self.assertTrue(result["valid"])
        self.assertEqual("rest", result["action"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
