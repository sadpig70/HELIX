import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_validate import (
    validate_ledger, validate_diversity_report, validate_loop_action, validate_project,
)
from core.helix_diversity import measure_diversity
from core.helix_loop import next_action

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestValidate(unittest.TestCase):
    def test_example_ledger_valid(self):
        with open(os.path.join(ROOT, "examples", "consumed_ledger.json"), encoding="utf-8") as f:
            ledger = json.load(f)
        self.assertEqual(validate_ledger(ledger), [])

    def test_bad_ledger_detected(self):
        problems = validate_ledger({"consumed": [{"title": "no id"}]})
        self.assertTrue(any("idea_id" in p for p in problems))

    def test_diversity_report_shape_valid(self):
        rep = measure_diversity([{"title": "a b", "domains": ["x", "y"]}], sim=None)
        self.assertEqual(validate_diversity_report(rep), [])

    def test_loop_action_shape_valid(self):
        self.assertEqual(validate_loop_action(next_action({"corpus_size": 0})), [])

    def test_invalid_loop_action_detected(self):
        problems = validate_loop_action({"action": "NONSENSE"})
        self.assertTrue(problems)

    def test_project_structure_valid(self):
        # the shipped project must validate cleanly
        self.assertEqual(validate_project(ROOT), [])


if __name__ == "__main__":
    unittest.main()
