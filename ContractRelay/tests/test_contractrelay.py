import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from contractrelay import *  # noqa: E402,F403
from contractrelay.samples import sample_case  # noqa: E402


class ContractRelayTests(unittest.TestCase):
    def test_baseline_digest_stable(self):
        case = sample_case()
        self.assertEqual(case["baseline_sha256"], baseline_digest(case["source"], case["target"], case["contract"], case["payload"], case["custody"]))

    def test_relays_valid_case(self):
        receipt = relay(sample_case())
        self.assertEqual("RELAYED", receipt["decision"])
        self.assertFalse(receipt["fail_closed"])
        self.assertEqual([], receipt["errors"])
        self.assertEqual(64, len(receipt["relay_token"]))

    def test_blocks_contract_and_custody_failures(self):
        receipt = relay(sample_case("blocked"))
        self.assertEqual("BLOCKED", receipt["decision"])
        self.assertTrue(receipt["fail_closed"])
        codes = [error["code"] for error in receipt["errors"]]
        self.assertIn("MISSING_FIELD", codes)
        self.assertIn("TYPE_MISMATCH", codes)
        self.assertIn("CUSTODY_TARGET_MISMATCH", codes)
        self.assertIn("HANDOFF_UNCONFIRMED", codes)

    def test_invalid_baseline(self):
        receipt = relay(sample_case("invalid-baseline"))
        self.assertEqual("INVALID", receipt["decision"])
        self.assertIn("BASELINE_HASH_MISMATCH", receipt["reasons"])

    def test_unknown_type_blocks(self):
        case = sample_case()
        case["contract"]["field_types"]["subject.id"] = "uuid"
        case["baseline_sha256"] = baseline_digest(case["source"], case["target"], case["contract"], case["payload"], case["custody"])
        receipt = relay(case)
        self.assertEqual("BLOCKED", receipt["decision"])
        self.assertIn("UNKNOWN_TYPE", [error["code"] for error in receipt["errors"]])

    def test_bool_is_not_number(self):
        case = sample_case()
        case["payload"]["subject"]["score"] = True
        case["baseline_sha256"] = baseline_digest(case["source"], case["target"], case["contract"], case["payload"], case["custody"])
        receipt = relay(case)
        self.assertEqual("BLOCKED", receipt["decision"])
        self.assertIn("TYPE_MISMATCH", [error["code"] for error in receipt["errors"]])

    def test_source_target_authority(self):
        case = sample_case()
        case["source"] = "system-x"
        case["custody"]["from_actor"] = "system-x"
        case["baseline_sha256"] = baseline_digest(case["source"], case["target"], case["contract"], case["payload"], case["custody"])
        receipt = relay(case)
        self.assertIn("SOURCE_NOT_ALLOWED", [error["code"] for error in receipt["errors"]])

    def test_receipt_deterministic_and_replayable(self):
        case = sample_case()
        receipt = relay(case)
        self.assertEqual(receipt, relay(case))
        self.assertTrue(verify_receipt(case, receipt))
        receipt["decision"] = "BLOCKED"
        self.assertFalse(verify_receipt(case, receipt))

    def test_ledger_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ledger.jsonl")
            append_receipt(path, relay(sample_case()), "2026-07-16T00:30:00+09:00")
            append_receipt(path, relay(sample_case("blocked")), "2026-07-16T00:31:00+09:00")
            self.assertEqual([], verify_ledger(path))
            report = ledger_report(path)
            self.assertEqual(1, report["relayed"])
            self.assertEqual(1, report["blocked"])

    def test_ledger_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ledger.jsonl")
            append_receipt(path, relay(sample_case()), "2026-07-16T00:30:00+09:00")
            with open(path, encoding="utf-8") as handle:
                event = json.load(handle)
            event["receipt"]["decision"] = "BLOCKED"
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(event, handle)
                handle.write("\n")
            self.assertTrue(verify_ledger(path))

    def test_cli_blocked_exit(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "case.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(sample_case("blocked"), handle)
            run = subprocess.run([sys.executable, "-m", "contractrelay", "run", path], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(1, run.returncode)

    def test_cli_invalid_exit(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "case.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(sample_case("invalid-baseline"), handle)
            run = subprocess.run([sys.executable, "-m", "contractrelay", "run", path], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(2, run.returncode)


if __name__ == "__main__":
    unittest.main()

