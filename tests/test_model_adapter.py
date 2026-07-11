import json
import os
import tempfile
import unittest
from pathlib import Path

from sovereign_colony.kernel import build_experiment_001
from sovereign_colony.model_adapter import (
    FileDecisionProvider,
    ModelAdapterError,
    apply_response_batch,
    prepare_prompt_batch,
)
from sovereign_colony.persistence import SQLiteColonyStore


class MediatedModelAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db_path = self.root / "colony.db"
        self.batch_dir = self.root / "day-001"
        self.store = SQLiteColonyStore(self.db_path)
        self.store.initialize(build_experiment_001(seed=20260711))
        self.store.set_paused(False)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_prepare_batch_emits_one_public_prompt_per_living_citizen(self):
        manifest = prepare_prompt_batch(self.store, self.batch_dir, model="qwen2.5:1.5b")

        self.assertEqual(1, manifest["target_day"])
        self.assertEqual(7, len(manifest["citizens"]))
        for citizen_id in manifest["citizens"]:
            prompt_path = self.batch_dir / "requests" / f"{citizen_id}.txt"
            self.assertTrue(prompt_path.is_file())
            prompt = prompt_path.read_text(encoding="utf-8")
            self.assertNotIn("hidden/", prompt)
            self.assertNotIn("responsive_seal", prompt)
        saved = json.loads((self.batch_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest, saved)

    def test_file_provider_rejects_symlink_and_oversized_response(self):
        manifest = prepare_prompt_batch(self.store, self.batch_dir, model="qwen2.5:1.5b")
        response_dir = self.batch_dir / "responses"
        response_dir.mkdir()
        outside = self.root / "outside.json"
        outside.write_text('{"action":"rest","reason":"safe"}', encoding="utf-8")
        os.symlink(outside, response_dir / "founder-01.json")
        provider = FileDecisionProvider(response_dir)

        with self.assertRaises(ModelAdapterError):
            provider("ignored", "founder-01")

        (response_dir / "founder-01.json").unlink()
        (response_dir / "founder-01.json").write_text("x" * 20_000, encoding="utf-8")
        with self.assertRaises(ModelAdapterError):
            provider("ignored", "founder-01")
        self.assertEqual(7, len(manifest["citizens"]))

    def test_apply_batch_rejects_stale_manifest_before_mutating_world(self):
        prepare_prompt_batch(self.store, self.batch_dir, model="qwen2.5:1.5b")
        manifest_path = self.batch_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_state_digest"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaises(ModelAdapterError):
            apply_response_batch(self.store, self.batch_dir)

        self.assertEqual(0, self.store.load().colony_day)

    def test_apply_complete_response_batch_advances_exactly_one_day(self):
        manifest = prepare_prompt_batch(self.store, self.batch_dir, model="qwen2.5:1.5b")
        response_dir = self.batch_dir / "responses"
        response_dir.mkdir()
        for citizen_id in manifest["citizens"]:
            (response_dir / f"{citizen_id}.json").write_text(
                json.dumps({"action": "rest", "reason": "Observe before changing the world."}),
                encoding="utf-8",
            )

        report = apply_response_batch(self.store, self.batch_dir)

        self.assertEqual(1, report.colony_day)
        self.assertEqual(1, self.store.load().colony_day)
        with self.assertRaises(ModelAdapterError):
            apply_response_batch(self.store, self.batch_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
