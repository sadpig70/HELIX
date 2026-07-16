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

from authorityarbiter import (append_receipt, arbitrate, digest, evaluate_condition,  # noqa: E402
                              resolve_fact, verify_ledger, verify_receipt)
from authorityarbiter.ledger import ledger_report  # noqa: E402
from authorityarbiter.samples import sample_request  # noqa: E402


class AuthorityArbiterTests(unittest.TestCase):
    def setUp(self):
        self.request = sample_request("allow")

    def test_digest_is_order_independent(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))

    def test_resolve_nested_fact(self):
        self.assertEqual((True, "low"), resolve_fact(self.request["facts"], "risk.level"))
        self.assertEqual((False, None), resolve_fact(self.request["facts"], "risk.missing"))

    def test_condition_operators(self):
        facts = {"n": 3, "kind": "a"}
        self.assertTrue(evaluate_condition({"field": "n", "operator": "gte", "value": 3}, facts))
        self.assertTrue(evaluate_condition({"field": "kind", "operator": "in", "value": ["a", "b"]}, facts))
        self.assertFalse(evaluate_condition({"field": "n", "operator": "eval", "value": "code"}, facts))

    def test_higher_authority_allows(self):
        receipt = arbitrate(self.request)
        self.assertEqual("ARBITRATED_ALLOW", receipt["decision"])
        self.assertEqual("platform-owner", receipt["selected_authority"])

    def test_higher_authority_denies(self):
        receipt = arbitrate(sample_request("deny"))
        self.assertEqual("ARBITRATED_DENY", receipt["decision"])
        self.assertEqual("service-owner", receipt["selected_authority"])

    def test_equal_precedence_conflict_escalates(self):
        receipt = arbitrate(sample_request("tie"))
        self.assertEqual("ESCALATE", receipt["decision"])
        self.assertIn("TIED_CONFLICT", {row["code"] for row in receipt["reasons"]})

    def test_action_outside_delegation_escalates(self):
        self.request["action"] = "delete_agent"
        self.assertIn("ACTION_NOT_DELEGATED", {r["code"] for r in arbitrate(self.request)["reasons"]})

    def test_custody_sender_mismatch_escalates(self):
        self.request["custody"]["from_actor"] = "other"
        self.assertIn("CUSTODY_SENDER_MISMATCH", {r["code"] for r in arbitrate(self.request)["reasons"]})

    def test_custody_return_mismatch_escalates(self):
        self.request["custody"]["to_actor"] = "other"
        self.assertIn("CUSTODY_RETURN_MISMATCH", {r["code"] for r in arbitrate(self.request)["reasons"]})

    def test_unconfirmed_handback_escalates(self):
        self.request["custody"]["handback_confirmed"] = False
        self.assertEqual("ESCALATE", arbitrate(self.request)["decision"])

    def test_route_mismatch_escalates(self):
        self.request["route"]["actual_route_id"] = "side-route"
        self.assertIn("ROUTE_MISMATCH", {r["code"] for r in arbitrate(self.request)["reasons"]})

    def test_untraced_authority_escalates(self):
        self.request["delegation"]["authority_chain"].remove("service-owner")
        self.assertIn("UNTRACED_AUTHORITY", {r["code"] for r in arbitrate(self.request)["reasons"]})

    def test_no_matching_policy_escalates(self):
        self.request["facts"]["risk"]["level"] = "medium"
        self.request["facts"]["environment"] = "production"
        self.assertIn("NO_MATCHING_POLICY", {r["code"] for r in arbitrate(self.request)["reasons"]})

    def test_receipt_is_deterministic_and_replayable(self):
        receipt = arbitrate(self.request)
        self.assertEqual(receipt, arbitrate(self.request))
        self.assertTrue(verify_receipt(self.request, receipt))
        receipt["decision"] = "ESCALATE"
        self.assertFalse(verify_receipt(self.request, receipt))

    def test_ledger_chain_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.jsonl")
            append_receipt(path, arbitrate(self.request), "2026-07-15T22:00:00+09:00")
            append_receipt(path, arbitrate(sample_request("tie")), "2026-07-15T22:00:01+09:00")
            self.assertEqual([], verify_ledger(path))
            report = ledger_report(path)
            self.assertEqual(1, report["decisions"]["ARBITRATED_ALLOW"])
            self.assertEqual(1, report["decisions"]["ESCALATE"])

    def test_ledger_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.jsonl")
            append_receipt(path, arbitrate(self.request), "2026-07-15T22:00:00+09:00")
            with open(path, encoding="utf-8") as handle:
                event = json.load(handle)
            event["receipt"]["decision"] = "ARBITRATED_DENY"
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(event, handle)
                handle.write("\n")
            self.assertTrue(verify_ledger(path))

    def test_cli_sample_and_tie_exit_code(self):
        env = dict(os.environ, PYTHONPATH=SRC)
        sample = subprocess.run([sys.executable, "-m", "authorityarbiter", "sample"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(0, sample.returncode)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tie.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(sample_request("tie"), handle)
            run = subprocess.run([sys.executable, "-m", "authorityarbiter", "run", path], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(3, run.returncode)
            self.assertEqual("ESCALATE", json.loads(run.stdout)["decision"])


if __name__ == "__main__":
    unittest.main()
