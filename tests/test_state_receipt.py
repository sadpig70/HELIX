import os
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_schema import validate_against_schema
from core.helix_state_receipt import (
    assess_report_freshness, build_state_receipt, seal_receipt, sha256_file,
    verify_receipt_hash,
)


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


class TestReportFreshness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.report = os.path.join(self.tmp.name, "report.json")
        self.source_a = os.path.join(self.tmp.name, "a.json")
        self.source_b = os.path.join(self.tmp.name, "b.json")
        _write(self.report, b'{"result":"ok"}')
        _write(self.source_a, b'{"a":1}')
        _write(self.source_b, b'{"b":2}')

    def bindings(self):
        return [
            {"path": self.source_b, "sha256": sha256_file(self.source_b)},
            {"path": self.source_a, "sha256": sha256_file(self.source_a)},
        ]

    def assess(self, expected_report=None, bindings=None, path=None):
        return assess_report_freshness(
            "machine_probe",
            path or self.report,
            expected_report if expected_report is not None else sha256_file(self.report),
            self.bindings() if bindings is None else bindings,
        )

    def test_all_content_hashes_match_is_fresh(self):
        result = self.assess()
        self.assertEqual(result["status"], "fresh")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["source_paths"], sorted([self.source_a, self.source_b]))

    def test_mtime_changes_do_not_affect_freshness(self):
        report_hash = sha256_file(self.report)
        source_hash = sha256_file(self.source_a)
        os.utime(self.report, (1, 1))
        os.utime(self.source_a, (2, 2))
        result = self.assess(
            expected_report=report_hash,
            bindings=[{"path": self.source_a, "sha256": source_hash}],
        )
        self.assertEqual(result["status"], "fresh")

    def test_report_content_change_is_stale(self):
        sealed = sha256_file(self.report)
        _write(self.report, b'{"result":"no"}')
        result = self.assess(expected_report=sealed)
        self.assertEqual(result["status"], "stale")
        self.assertIn("report_hash_mismatch", result["reasons"])

    def test_source_content_change_is_stale(self):
        bindings = self.bindings()
        _write(self.source_a, b'{"a":9}')
        result = self.assess(bindings=bindings)
        self.assertEqual(result["status"], "stale")
        self.assertIn(f"source_hash_mismatch:{self.source_a}", result["reasons"])

    def test_missing_report_is_missing(self):
        path = os.path.join(self.tmp.name, "absent.json")
        result = self.assess(path=path)
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["reasons"], ["report_missing"])
        self.assertIsNone(result["sha256"])

    def test_absent_source_bindings_are_unverifiable(self):
        result = self.assess(bindings=[])
        self.assertEqual(result["status"], "unverifiable")
        self.assertIn("source_bindings_absent", result["reasons"])

    def test_unbound_report_hash_is_unverifiable(self):
        result = assess_report_freshness("machine_probe", self.report, None, self.bindings())
        self.assertEqual(result["status"], "unverifiable")
        self.assertIn("report_hash_unbound", result["reasons"])

    def test_missing_source_is_unverifiable(self):
        missing = os.path.join(self.tmp.name, "missing-source.json")
        result = self.assess(bindings=[{"path": missing, "sha256": "a" * 64}])
        self.assertEqual(result["status"], "unverifiable")
        self.assertIn(f"source_missing:{missing}", result["reasons"])

    def test_stale_takes_precedence_over_unverifiable(self):
        sealed = sha256_file(self.report)
        _write(self.report, b'{"result":"changed"}')
        result = self.assess(expected_report=sealed, bindings=[])
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["reasons"], ["report_hash_mismatch", "source_bindings_absent"])

    def test_duplicate_source_binding_is_rejected(self):
        binding = {"path": self.source_a, "sha256": sha256_file(self.source_a)}
        with self.assertRaisesRegex(ValueError, "duplicate source binding"):
            self.assess(bindings=[binding, binding])


class TestReceiptBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.winner = os.path.join(self.root, "winner.json")
        self.registry = os.path.join(self.root, "registry.json")
        self.gate = os.path.join(self.root, "gate.json")
        self.source = os.path.join(self.root, "source.json")
        self.report = os.path.join(self.root, "report.json")
        _write(self.winner, b'{"winner":"x"}')
        _write(self.registry, b'{"registry":[]}')
        _write(self.gate, b'{"policy":1}')
        _write(self.source, b'{"source":1}')
        _write(self.report, b'{"result":"ok"}')
        self.schema = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "helix-state-receipt.schema.json")

    def runtime_report(self, repair_required=False):
        return {
            "ledger_size": 2,
            "ledger_origins": {"explore": 0, "exploit": 2},
            "diversity": {
                "triggered": repair_required,
                "repair_required": repair_required,
                "breaches": 1 if repair_required else 0,
            },
            "winner": None,
            "latest_exploit_run": {"phase": "completed"},
            "corpus_feedback": [],
            "next_action": {
                "action": "REFRESH_INPUTS" if repair_required else "RUN_EXPLORE",
                "why": "repair" if repair_required else "balance",
            },
        }

    def kwargs(self, repair_required=False):
        return {
            "root": self.root,
            "runtime_report": self.runtime_report(repair_required),
            "input_paths": {
                "exploit_registry": "registry.json",
                "explore_winner": "winner.json",
            },
            "gate_paths": {"machine_probe": "gate.json"},
            "report_bindings": [{
                "report": "machine_probe",
                "path": "report.json",
                "expected_sha256": sha256_file(self.report),
                "sources": [{"path": "source.json", "sha256": sha256_file(self.source)}],
            }],
            "git_head": "a" * 40,
            "replay_argv": ["python", "helix.py", "status"],
        }

    def test_builder_output_matches_schema_and_hash(self):
        receipt = build_state_receipt(**self.kwargs())
        self.assertEqual(validate_against_schema(receipt, self.schema), [])
        self.assertTrue(verify_receipt_hash(receipt))
        self.assertTrue(receipt["authority"]["actuator_ready"])
        self.assertEqual(receipt["report_freshness"][0]["status"], "fresh")

    def test_same_inputs_produce_identical_receipt(self):
        first = build_state_receipt(**self.kwargs())
        second = build_state_receipt(**self.kwargs())
        self.assertEqual(first, second)

    def test_mapping_and_binding_order_do_not_change_hash(self):
        args = self.kwargs()
        args["input_paths"] = {
            "explore_winner": "winner.json",
            "exploit_registry": "registry.json",
        }
        second_source = os.path.join(self.root, "second.json")
        _write(second_source, b'{"source":2}')
        args["report_bindings"][0]["sources"].append(
            {"path": "second.json", "sha256": sha256_file(second_source)})
        first = build_state_receipt(**args)
        args["report_bindings"][0]["sources"].reverse()
        args["input_paths"] = dict(reversed(list(args["input_paths"].items())))
        second = build_state_receipt(**args)
        self.assertEqual(first["receipt_hash"], second["receipt_hash"])

    def test_source_change_marks_stale_and_blocks_authority(self):
        args = self.kwargs()
        _write(self.source, b'{"source":9}')
        receipt = build_state_receipt(**args)
        self.assertEqual(receipt["report_freshness"][0]["status"], "stale")
        self.assertFalse(receipt["authority"]["actuator_ready"])
        self.assertIn("stale_report", receipt["authority"]["required_clearances"])

    def test_missing_gate_blocks_authority(self):
        args = self.kwargs()
        args["gate_paths"] = {"machine_probe": "missing-gate.json"}
        receipt = build_state_receipt(**args)
        self.assertFalse(receipt["authority"]["actuator_ready"])
        self.assertIn("missing_gate", receipt["authority"]["required_clearances"])

    def test_diversity_repair_blocks_authority(self):
        receipt = build_state_receipt(**self.kwargs(repair_required=True))
        self.assertEqual(receipt["next_action"]["action"], "REFRESH_INPUTS")
        self.assertIn("diversity_repair_required",
                      receipt["authority"]["required_clearances"])

    def test_mutation_invalidates_receipt_hash(self):
        receipt = build_state_receipt(**self.kwargs())
        receipt["next_action"]["why"] = "tampered"
        self.assertFalse(verify_receipt_hash(receipt))

    def test_seal_ignores_existing_receipt_hash(self):
        receipt = build_state_receipt(**self.kwargs())
        receipt["receipt_hash"] = "bad"
        resealed = seal_receipt(receipt)
        self.assertTrue(verify_receipt_hash(resealed))
        self.assertNotEqual(resealed["receipt_hash"], "bad")


if __name__ == "__main__":
    unittest.main()
