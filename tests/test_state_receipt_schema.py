import copy
import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_schema import schema_features, validate_against_schema
from core.helix_state_receipt import verify_receipt_hash


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "schemas", "helix-state-receipt.schema.json")
EXAMPLE_PATH = os.path.join(ROOT, "examples", "state-receipt", "receipt.json")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestStateReceiptSchema(unittest.TestCase):
    def setUp(self):
        self.schema = _load(SCHEMA_PATH)
        self.example = _load(EXAMPLE_PATH)

    def test_schema_stays_in_stdlib_validator_subset(self):
        self.assertEqual(schema_features(self.schema), {"in_subset": True, "unsupported": []})

    def test_canonical_example_matches_schema(self):
        self.assertEqual(validate_against_schema(self.example, self.schema), [])
        self.assertTrue(verify_receipt_hash(self.example))

    def test_all_authority_fields_are_required(self):
        for key in ("actuator_ready", "basis", "required_clearances"):
            with self.subTest(key=key):
                doc = copy.deepcopy(self.example)
                del doc["authority"][key]
                problems = validate_against_schema(doc, self.schema)
                self.assertTrue(any(f"missing required key '{key}'" in p for p in problems))

    def test_missing_gate_hash_is_not_representable_as_present(self):
        doc = copy.deepcopy(self.example)
        doc["gate_hashes"][0]["sha256"] = None
        doc["gate_hashes"][0]["status"] = "absent"
        problems = validate_against_schema(doc, self.schema)
        self.assertTrue(any("$.gate_hashes[0].status" in p for p in problems), problems)

    def test_unknown_action_is_rejected(self):
        doc = copy.deepcopy(self.example)
        doc["next_action"]["action"] = "RUN_ANYTHING"
        problems = validate_against_schema(doc, self.schema)
        self.assertTrue(any("$.next_action.action" in p for p in problems), problems)

    def test_replay_command_is_argv_not_shell_text(self):
        doc = copy.deepcopy(self.example)
        doc["replay_command"]["argv"] = "python helix.py status"
        problems = validate_against_schema(doc, self.schema)
        self.assertTrue(any("$.replay_command.argv" in p for p in problems), problems)

    def test_wall_clock_metadata_is_not_part_of_contract(self):
        self.assertNotIn("generated_at", self.schema["properties"])
        self.assertNotIn("timestamp", self.schema["properties"])


if __name__ == "__main__":
    unittest.main()
