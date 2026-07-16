import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from proofescrow import (append_receipt, digest, evaluate, sign_step,  # noqa: E402
                         verify_ledger, verify_receipt, verify_step_signature)
from proofescrow.ledger import ledger_report  # noqa: E402
from proofescrow.samples import sample_bundle  # noqa: E402


class ProofEscrowTests(unittest.TestCase):
    def setUp(self):
        bundle = sample_bundle()
        self.request = bundle["request"]
        self.trust = bundle["trust_store"]

    def test_canonical_digest_is_order_independent(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))

    def test_sign_and_verify_step(self):
        step = sign_step({"step_id": "s", "command": ["x"], "materials": [], "products": [], "signer": "a"}, "k")
        self.assertTrue(verify_step_signature(step, "k"))
        self.assertFalse(verify_step_signature(step, "wrong"))

    def test_valid_request_is_released(self):
        self.assertEqual("RELEASED", evaluate(self.request, self.trust)["decision"])

    def test_receipt_is_deterministic(self):
        self.assertEqual(evaluate(self.request, self.trust), evaluate(self.request, self.trust))

    def test_receipt_replay_and_tamper_detection(self):
        receipt = evaluate(self.request, self.trust)
        self.assertTrue(verify_receipt(self.request, self.trust, receipt))
        receipt["decision"] = "HELD"
        self.assertFalse(verify_receipt(self.request, self.trust, receipt))

    def test_tampered_step_is_held(self):
        self.request["artifact"]["steps"][0]["command"] = ["tampered"]
        receipt = evaluate(self.request, self.trust)
        self.assertEqual("HELD", receipt["decision"])
        self.assertIn("INVALID_STEP_SIGNATURE", {item["code"] for item in receipt["reasons"]})

    def test_untrusted_signer_is_held(self):
        receipt = evaluate(self.request, {})
        self.assertIn("UNTRUSTED_SIGNER", {item["code"] for item in receipt["reasons"]})

    def test_missing_steps_is_held(self):
        self.request["artifact"]["steps"] = []
        self.assertEqual("HELD", evaluate(self.request, self.trust)["decision"])

    def test_final_product_must_be_bound(self):
        step = self.request["artifact"]["steps"][0]
        step["products"] = ["e" * 64]
        self.request["artifact"]["steps"][0] = sign_step(step, self.trust["builder-1"])
        receipt = evaluate(self.request, self.trust)
        self.assertIn("FINAL_PRODUCT_NOT_BOUND", {item["code"] for item in receipt["reasons"]})

    def test_unapproved_baseline_is_held(self):
        self.request["behavior"]["baseline_sha256"] = "e" * 64
        self.request["behavior"]["observed_sha256"] = "e" * 64
        receipt = evaluate(self.request, self.trust)
        self.assertIn("UNAPPROVED_BASELINE", {item["code"] for item in receipt["reasons"]})

    def test_behavior_drift_is_held(self):
        self.request["behavior"]["observed_sha256"] = "e" * 64
        receipt = evaluate(self.request, self.trust)
        self.assertIn("BEHAVIOR_DRIFT", {item["code"] for item in receipt["reasons"]})

    def test_tests_must_pass(self):
        self.request["behavior"]["tests_passed"] = False
        receipt = evaluate(self.request, self.trust)
        self.assertIn("TESTS_NOT_PASSED", {item["code"] for item in receipt["reasons"]})

    def test_behavior_must_be_deterministic(self):
        self.request["behavior"]["deterministic"] = False
        receipt = evaluate(self.request, self.trust)
        self.assertIn("NONDETERMINISTIC_BEHAVIOR", {item["code"] for item in receipt["reasons"]})

    def test_ledger_chain_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.jsonl")
            append_receipt(path, evaluate(self.request, self.trust), "2026-07-15T22:00:00+09:00")
            held = copy.deepcopy(self.request)
            held["behavior"]["tests_passed"] = False
            append_receipt(path, evaluate(held, self.trust), "2026-07-15T22:00:01+09:00")
            self.assertEqual([], verify_ledger(path))
            self.assertEqual({"released": 1, "held": 1}, {k: ledger_report(path)[k] for k in ("released", "held")})

    def test_ledger_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.jsonl")
            append_receipt(path, evaluate(self.request, self.trust), "2026-07-15T22:00:00+09:00")
            with open(path, encoding="utf-8") as handle:
                event = json.load(handle)
            event["receipt"]["decision"] = "HELD"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(event) + "\n")
            self.assertTrue(verify_ledger(path))

    def test_cli_sample_and_held_exit_code(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        sample = subprocess.run([sys.executable, "-m", "proofescrow", "sample"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(0, sample.returncode)
        self.assertIn("PE-DEMO-001", sample.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            request_path = os.path.join(tmp, "request.json")
            trust_path = os.path.join(tmp, "trust.json")
            held = sample_bundle("held-behavior")
            for path, value in ((request_path, held["request"]), (trust_path, held["trust_store"])):
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(value, handle)
            run = subprocess.run([sys.executable, "-m", "proofescrow", "run", request_path, "--trust-store", trust_path], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(2, run.returncode)
            self.assertIn('"decision": "HELD"', run.stdout)


if __name__ == "__main__":
    unittest.main()
