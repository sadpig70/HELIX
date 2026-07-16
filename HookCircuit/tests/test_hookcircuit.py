import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from hookcircuit import *  # noqa: E402,F403
from hookcircuit.samples import sample_case  # noqa: E402


class HookCircuitTests(unittest.TestCase):
    def test_baseline_digest_stable(self):
        case = sample_case()
        self.assertEqual(case["baseline_sha256"], baseline_digest(case["hooks"], case["observations"]))

    def test_trips_only_failing_hook(self):
        receipt = evaluate(sample_case())
        self.assertEqual("TRIPPED", receipt["decision"])
        self.assertEqual(["h-cache"], [row["hook_id"] for row in receipt["tripped_hooks"]])
        self.assertIn("h-auth", receipt["allowed_hooks"])
        self.assertIn("h-log", receipt["allowed_hooks"])
        self.assertEqual(["cache"], receipt["isolated_plugins"])

    def test_clean_case_allowed(self):
        receipt = evaluate(sample_case("clean"))
        self.assertEqual("ALLOWED", receipt["decision"])
        self.assertEqual([], receipt["tripped_hooks"])
        self.assertFalse(receipt["interrupted"])

    def test_invalid_baseline(self):
        receipt = evaluate(sample_case("invalid-baseline"))
        self.assertEqual("INVALID", receipt["decision"])
        self.assertIn("BASELINE_HASH_MISMATCH", receipt["reasons"])

    def test_elapsed_timeout_trips(self):
        case = sample_case("clean")
        case["observations"][0]["elapsed_ms"] = 70
        case["baseline_sha256"] = baseline_digest(case["hooks"], case["observations"])
        receipt = evaluate(case)
        self.assertEqual("TRIPPED", receipt["decision"])
        self.assertIn("h-auth", [row["hook_id"] for row in receipt["tripped_hooks"]])

    def test_invalid_hook_contract(self):
        case = sample_case()
        case["hooks"][0]["max_failures"] = 0
        case["baseline_sha256"] = baseline_digest(case["hooks"], case["observations"])
        receipt = evaluate(case)
        self.assertEqual("INVALID", receipt["decision"])
        self.assertIn("INVALID_MAX_FAILURES", receipt["reasons"])

    def test_missing_observation_hook_invalid(self):
        case = sample_case()
        case["observations"][0]["hook_id"] = "missing"
        case["baseline_sha256"] = baseline_digest(case["hooks"], case["observations"])
        self.assertEqual("INVALID", evaluate(case)["decision"])

    def test_receipt_deterministic_and_replayable(self):
        case = sample_case()
        receipt = evaluate(case)
        self.assertEqual(receipt, evaluate(case))
        self.assertTrue(verify_receipt(case, receipt))
        receipt["decision"] = "ALLOWED"
        self.assertFalse(verify_receipt(case, receipt))

    def test_ledger_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ledger.jsonl")
            append_receipt(path, evaluate(sample_case()), "2026-07-16T01:00:00+09:00")
            append_receipt(path, evaluate(sample_case("clean")), "2026-07-16T01:01:00+09:00")
            self.assertEqual([], verify_ledger(path))
            report = ledger_report(path)
            self.assertEqual(1, report["tripped"])
            self.assertEqual(1, report["allowed"])

    def test_ledger_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ledger.jsonl")
            append_receipt(path, evaluate(sample_case()), "2026-07-16T01:00:00+09:00")
            with open(path, encoding="utf-8") as handle:
                event = json.load(handle)
            event["receipt"]["decision"] = "ALLOWED"
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(event, handle)
                handle.write("\n")
            self.assertTrue(verify_ledger(path))

    def test_cli_tripped_exit(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "case.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(sample_case(), handle)
            run = subprocess.run([sys.executable, "-m", "hookcircuit", "run", path], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(1, run.returncode)

    def test_cli_invalid_exit(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "case.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(sample_case("invalid-baseline"), handle)
            run = subprocess.run([sys.executable, "-m", "hookcircuit", "run", path], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(2, run.returncode)


if __name__ == "__main__":
    unittest.main()

