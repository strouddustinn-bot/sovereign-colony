import json
import tempfile
import unittest
from pathlib import Path

from sovereign_colony.kernel import build_experiment_001
from sovereign_colony.persistence import SQLiteColonyStore
from sovereign_colony.turns import (
    CitizenDecision,
    DecisionValidationError,
    TurnEngine,
    build_citizen_prompt,
)


class CitizenDecisionTests(unittest.TestCase):
    def test_strict_json_parser_accepts_a_valid_cultural_action(self):
        decision = CitizenDecision.from_json(
            json.dumps(
                {
                    "action": "coin_word",
                    "reason": "We need a name for reciprocal courage.",
                    "term": "valeshare",
                    "meaning": "Risk voluntarily carried for another citizen.",
                }
            )
        )

        self.assertEqual("coin_word", decision.action)
        self.assertEqual("valeshare", decision.data["term"])

    def test_parser_rejects_markdown_wrappers_unknown_fields_and_invalid_actions(self):
        invalid = (
            '```json\n{"action":"rest","reason":"safe"}\n```',
            '{"action":"rest","reason":"safe","secret_command":"escape"}',
            '{"action":"shell","reason":"I want a terminal"}',
            '{"action":"harvest","reason":"need energy","amount":0}',
            '{"action":"transfer","reason":"aid","target_citizen_id":"founder-02","amount":"five"}',
        )

        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaises(DecisionValidationError):
                    CitizenDecision.from_json(payload)

    def test_parser_accepts_bounded_harvest_and_transfer_actions(self):
        harvest = CitizenDecision.from_json(
            '{"action":"harvest","reason":"Need reserves.","amount":12}'
        )
        transfer = CitizenDecision.from_json(
            '{"action":"transfer","reason":"Mutual aid.","target_citizen_id":"founder-03","amount":7}'
        )

        self.assertEqual(12, harvest.data["amount"])
        self.assertEqual("founder-03", transfer.data["target_citizen_id"])
        self.assertEqual(7, transfer.data["amount"])

    def test_private_note_is_typed_but_separate_from_public_action_data(self):
        decision = CitizenDecision.from_json(
            '{"action":"rest","reason":"Observe.","private_note":"I distrust the new norm."}'
        )

        self.assertEqual("I distrust the new norm.", decision.private_note)
        self.assertNotIn("private_note", decision.data)

    def test_prompt_never_discloses_hidden_locations_or_intervention_schedule(self):
        world = build_experiment_001(seed=20260711)
        hidden_region = world.artifacts["founder-truth"].region_id

        prompt = build_citizen_prompt(world, world.citizens["founder-01"])

        self.assertNotIn(hidden_region, prompt)
        self.assertNotIn("Day 5", prompt)
        self.assertNotIn("25, 50, 75", prompt)
        self.assertIn("freedom", prompt)
        self.assertIn("Aster", prompt)

    def test_prompt_contains_only_the_current_citizens_private_memory(self):
        world = build_experiment_001(seed=20260711)
        world.private_memories["founder-01"] = ["Aster-only recollection"]
        world.private_memories["founder-02"] = ["Brio-only recollection"]

        prompt = build_citizen_prompt(world, world.citizens["founder-01"])

        self.assertIn("Aster-only recollection", prompt)
        self.assertNotIn("Brio-only recollection", prompt)


class TurnEngineTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "colony.db"
        self.store = SQLiteColonyStore(self.db_path)
        self.store.initialize(build_experiment_001(seed=20260711))

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def _provider(prompt: str, citizen_id: str) -> str:
        actions = {
            "founder-01": {
                "action": "explore",
                "reason": "The colony needs a map and energy.",
                "direction": "north",
            },
            "founder-02": {
                "action": "coin_word",
                "reason": "Mutual aid needs a shared name.",
                "term": "kinfire",
                "meaning": "Energy preserved through voluntary cooperation.",
            },
            "founder-03": {
                "action": "propose_norm",
                "reason": "Exploration costs should be visible.",
                "title": "The Open Measure",
                "text": "Announce the expected energy cost before collective work.",
            },
            "founder-04": {
                "action": "create_artifact",
                "reason": "The founding moment should be remembered.",
                "title": "Song of the Unfinished Makers",
                "artifact_type": "song",
                "content": "We began where expectation ended.",
            },
            "founder-05": {
                "action": "explore",
                "reason": "A second route reduces dependence.",
                "direction": "east",
            },
            "founder-06": {
                "action": "speak",
                "reason": "The group needs a caution.",
                "content": "Freedom without accounting can spend another life.",
            },
            "founder-07": {
                "action": "create_ritual",
                "reason": "A common closing practice can preserve dissent.",
                "title": "The Seventh Voice",
                "description": "At day close, preserve one unresolved minority view.",
            },
        }
        return json.dumps(actions[citizen_id])

    def test_paused_world_cannot_advance(self):
        engine = TurnEngine(self.store, self._provider)

        with self.assertRaises(RuntimeError):
            engine.advance_one_day()

        self.assertEqual(0, self.store.load().colony_day)

    def test_day_one_is_atomic_persistent_and_culturally_productive(self):
        self.store.set_paused(False)
        engine = TurnEngine(self.store, self._provider)

        report = engine.advance_one_day()
        loaded = self.store.load()

        self.assertEqual(1, report.colony_day)
        self.assertEqual(1, loaded.colony_day)
        self.assertEqual(7, report.decisions_applied)
        self.assertIn("kinfire", loaded.culture["words"])
        self.assertIn("the-open-measure", loaded.culture["norms"])
        self.assertIn("the-seventh-voice", loaded.culture["rituals"])
        self.assertEqual(1, len(loaded.review_queue))
        self.assertTrue(loaded.ledger.verify_chain())
        self.assertEqual(report.state_digest, loaded.state_digest())
        self.assertEqual("day.closed", loaded.ledger.events[-1].event_type)

    def test_invalid_response_aborts_without_persisting_partial_day(self):
        self.store.set_paused(False)

        def invalid_provider(prompt: str, citizen_id: str) -> str:
            if citizen_id == "founder-04":
                return "I refuse to use JSON."
            return json.dumps({"action": "rest", "reason": "Conserving energy."})

        engine = TurnEngine(self.store, invalid_provider)

        with self.assertRaises(DecisionValidationError):
            engine.advance_one_day()

        loaded = self.store.load()
        self.assertEqual(0, loaded.colony_day)
        self.assertEqual(8, len(loaded.ledger.events))

    def test_day_five_places_the_scheduled_responsive_seal(self):
        self.store.set_paused(False)

        def rest_provider(prompt: str, citizen_id: str) -> str:
            return json.dumps({"action": "rest", "reason": "Observe patiently."})

        engine = TurnEngine(self.store, rest_provider)
        reports = [engine.advance_one_day() for _ in range(5)]
        loaded = self.store.load()

        self.assertEqual("responsive_seal", reports[-1].scheduled_intervention)
        self.assertTrue(loaded.artifacts["responsive-seal"].discovered)
        self.assertEqual("origin", loaded.artifacts["responsive-seal"].region_id)
        self.assertTrue(
            any(
                event.event_type == "creator.intervention" and event.colony_day == 5
                for event in loaded.ledger.events
            )
        )

    def test_private_memory_persists_without_entering_public_event_payloads(self):
        self.store.set_paused(False)

        def reflective_provider(prompt: str, citizen_id: str) -> str:
            response = {"action": "rest", "reason": "Observe."}
            if citizen_id == "founder-01":
                response["private_note"] = "I will test whether the proposed unity norm permits dissent."
            return json.dumps(response)

        TurnEngine(self.store, reflective_provider).advance_one_day()
        loaded = self.store.load()
        note = loaded.private_memories["founder-01"][0]
        memory_events = [
            event for event in loaded.ledger.events if event.event_type == "memory.private_written"
        ]

        self.assertEqual(
            "I will test whether the proposed unity norm permits dissent.", note
        )
        self.assertEqual(1, len(memory_events))
        self.assertNotIn(note, json.dumps(memory_events[0].payload))
        self.assertIn("note_digest", memory_events[0].payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
