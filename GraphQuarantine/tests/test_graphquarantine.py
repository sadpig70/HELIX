import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from graphquarantine import *  # noqa: E402,F403
from graphquarantine.samples import sample_case  # noqa: E402


class GraphQuarantineTests(unittest.TestCase):
    def test_baseline_digest_stable(self):
        case = sample_case()
        self.assertEqual(case["baseline_sha256"], baseline_digest(case["nodes"], case["edges"], case["contamination_sources"]))

    def test_quarantines_block_path_only(self):
        receipt = quarantine(sample_case())
        self.assertEqual("QUARANTINED", receipt["decision"])
        self.assertEqual(["derived-a", "derived-b"], receipt["quarantine_set"])
        self.assertEqual(["watch-only"], receipt["monitor_set"])
        self.assertIn("clean-sibling", receipt["clean_branches"])

    def test_clear_case(self):
        receipt = quarantine(sample_case("clear"))
        self.assertEqual("CLEAR", receipt["decision"])
        self.assertEqual([], receipt["quarantine_set"])

    def test_invalid_baseline(self):
        receipt = quarantine(sample_case("invalid-baseline"))
        self.assertEqual("INVALID", receipt["decision"])
        self.assertIn("BASELINE_HASH_MISMATCH", receipt["reasons"])

    def test_missing_source_invalid(self):
        case = sample_case()
        case["contamination_sources"] = ["missing"]
        case["baseline_sha256"] = baseline_digest(case["nodes"], case["edges"], case["contamination_sources"])
        self.assertEqual("INVALID", quarantine(case)["decision"])

    def test_ignore_edge_preserves_branch(self):
        receipt = quarantine(sample_case())
        self.assertNotIn("clean-sibling", receipt["quarantine_set"])
        self.assertNotIn("clean-sibling", receipt["monitor_set"])

    def test_receipt_deterministic_and_replayable(self):
        case = sample_case()
        receipt = quarantine(case)
        self.assertEqual(receipt, quarantine(case))
        self.assertTrue(verify_receipt(case, receipt))
        receipt["decision"] = "CLEAR"
        self.assertFalse(verify_receipt(case, receipt))

    def test_ledger_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ledger.jsonl")
            append_receipt(path, quarantine(sample_case()), "2026-07-15T23:45:00+09:00")
            self.assertEqual([], verify_ledger(path))
            self.assertEqual(1, ledger_report(path)["quarantined"])

    def test_ledger_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ledger.jsonl")
            append_receipt(path, quarantine(sample_case()), "2026-07-15T23:45:00+09:00")
            with open(path, encoding="utf-8") as handle:
                event = json.load(handle)
            event["receipt"]["decision"] = "CLEAR"
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(event, handle)
                handle.write("\n")
            self.assertTrue(verify_ledger(path))

    def test_cli_invalid_exit(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "case.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(sample_case("invalid-baseline"), handle)
            run = subprocess.run([sys.executable, "-m", "graphquarantine", "run", path], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(2, run.returncode)


if __name__ == "__main__":
    unittest.main()

