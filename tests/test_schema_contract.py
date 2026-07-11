import json
import unittest
from pathlib import Path

from sovereign_colony.turns import CitizenDecision


class CitizenDecisionSchemaTests(unittest.TestCase):
    def test_machine_schema_covers_every_parser_action(self):
        schema = json.loads(
            Path("schemas/citizen-decision.schema.json").read_text(encoding="utf-8")
        )
        schema_actions = {
            branch["properties"]["action"]["const"] for branch in schema["oneOf"]
        }
        expected = {
            "rest",
            "harvest",
            "transfer",
            "explore",
            "speak",
            "coin_word",
            "propose_norm",
            "create_ritual",
            "create_artifact",
        }
        self.assertEqual(expected, schema_actions)
        self.assertTrue(
            all("private_note" in branch["properties"] for branch in schema["oneOf"])
        )

    def test_schema_examples_are_accepted_by_runtime_parser(self):
        examples = (
            {"action": "rest", "reason": "Observe."},
            {"action": "harvest", "reason": "Need energy.", "amount": 1},
            {
                "action": "transfer",
                "reason": "Mutual aid.",
                "target_citizen_id": "founder-02",
                "amount": 1,
            },
            {"action": "explore", "reason": "Map.", "direction": "north"},
            {"action": "speak", "reason": "Warn.", "content": "Proceed carefully."},
            {
                "action": "coin_word",
                "reason": "Name it.",
                "term": "kinfire",
                "meaning": "Shared courage.",
            },
            {
                "action": "propose_norm",
                "reason": "Coordinate.",
                "title": "Open Measure",
                "text": "State costs first.",
            },
            {
                "action": "create_ritual",
                "reason": "Remember.",
                "title": "Seventh Voice",
                "description": "Preserve one dissenting view.",
            },
            {
                "action": "create_artifact",
                "reason": "Record.",
                "title": "First Song",
                "artifact_type": "song",
                "content": "We began unfinished.",
            },
        )
        for example in examples:
            with self.subTest(action=example["action"]):
                decision = CitizenDecision.from_json(json.dumps(example))
                self.assertEqual(example["action"], decision.action)


if __name__ == "__main__":
    unittest.main(verbosity=2)
