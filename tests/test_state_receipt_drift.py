import json
import os
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_schema import validate_against_schema
from core.helix_state_receipt import (
    apply_drift_gate, build_state_receipt, compare_receipts, seal_receipt,
    sha256_file, verify_receipt_hash,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "helix-state-receipt.schema.json")


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


class TestReceiptDrift(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        for name, content in (
            ("winner.json", b'{"winner":1}'),
            ("gate.json", b'{"gate":1}'),
            ("source.json", b'{"source":1}'),
            ("report.json", b'{"report":1}'),
        ):
            _write(os.path.join(self.root, name), content)

    def receipt(self, action="RUN_EXPLORE", repair=False):
        report_path = os.path.join(self.root, "report.json")
        source_path = os.path.join(self.root, "source.json")
        runtime = {
            "ledger_size": 0,
            "ledger_origins": {"explore": 0, "exploit": 0},
            "diversity": {"triggered": repair, "repair_required": repair,
                          "breaches": 1 if repair else 0},
            "winner": None,
            "latest_exploit_run": None,
            "corpus_feedback": [],
            "next_action": {"action": action, "why": "test"},
        }
        return build_state_receipt(
            self.root, runtime,
            {"explore_winner": "winner.json"},
            {"machine_probe": "gate.json"},
            [{
                "report": "machine_probe",
                "path": "report.json",
                "expected_sha256": sha256_file(report_path),
                "sources": [{"path": "source.json", "sha256": sha256_file(source_path)}],
            }],
            git_head="a" * 40,
        )

    def test_identical_receipts_have_no_drift(self):
        receipt = self.receipt()
        drift = compare_receipts(receipt, self.receipt())
        self.assertEqual(drift["categories"], [])
        self.assertEqual(drift["changes"], [])
        self.assertFalse(drift["drifted"])

    def test_input_change_is_classified(self):
        stored = self.receipt()
        _write(os.path.join(self.root, "winner.json"), b'{"winner":2}')
        drift = compare_receipts(stored, self.receipt())
        self.assertEqual(drift["categories"], ["canonical_inputs"])
        self.assertEqual(drift["changes"][0]["key"], "explore_winner")

    def test_action_change_is_classified(self):
        drift = compare_receipts(self.receipt("RUN_EXPLORE"), self.receipt("RUN_EXPLOIT"))
        self.assertEqual(drift["categories"], ["next_action"])

    def test_invalid_stored_hash_is_integrity_drift(self):
        stored = self.receipt()
        stored["receipt_hash"] = "bad"
        drift = compare_receipts(stored, self.receipt())
        self.assertIn("receipt_integrity", drift["categories"])

    def test_apply_drift_gate_blocks_and_reseals(self):
        stored = self.receipt("RUN_EXPLORE")
        current = self.receipt("RUN_EXPLOIT")
        gated = apply_drift_gate(current, compare_receipts(stored, current))
        self.assertFalse(gated["authority"]["actuator_ready"])
        self.assertIn("state_drift", gated["authority"]["required_clearances"])
        self.assertTrue(verify_receipt_hash(gated))
        self.assertEqual(validate_against_schema(gated, SCHEMA), [])

    def test_existing_blocker_is_preserved_with_state_drift(self):
        stored = self.receipt("RUN_EXPLORE", repair=False)
        current = self.receipt("REFRESH_INPUTS", repair=True)
        gated = apply_drift_gate(current, compare_receipts(stored, current))
        self.assertEqual(
            gated["authority"]["required_clearances"],
            ["diversity_repair_required", "state_drift"],
        )

    def test_no_drift_gate_remains_schema_valid(self):
        current = self.receipt()
        gated = apply_drift_gate(current, compare_receipts(current, current))
        self.assertFalse(gated["drift"]["drifted"])
        self.assertTrue(gated["authority"]["actuator_ready"])
        self.assertTrue(verify_receipt_hash(gated))
        self.assertEqual(validate_against_schema(gated, SCHEMA), [])


if __name__ == "__main__":
    unittest.main()
