import hashlib
import json
import os
import tempfile
import unittest

from core.helix_condense_acceptance import (evaluate_condense_proposal,
                                             verify_condense_receipt)
from core.helix_holdout import canonical_json_bytes
from core.helix_internal_metrics import aggregate_internal_metrics
from core.helix_platform_composition import build_stage, compose
from core.helix_provisioning import provisioning_report
from core.helix_transaction import (new_transaction, record_admission_result,
                                    transition, verify_transaction)
from core.helix_actuator import append_actuation_ledger
from core.helix_stop_token import (issue_resume_receipt, issue_stop_token,
                                   active_stops,
                                   verify_resume_receipt_seal,
                                   verify_stop_token_seal)
from engines.transaction_store import load_transaction, save_transaction


class TransactionTests(unittest.TestCase):
    def test_happy_path_replays_and_duplicate_event_is_idempotent(self):
        tx = new_transaction("TX-1", "intent-hash")
        events = ("authorize", "apply", "applied", "verify", "verified",
                  "handback", "replay")
        for index, event in enumerate(events):
            tx = transition(tx, f"E-{index}", event)
        self.assertEqual(tx["state"], "REPLAYABLE")
        self.assertEqual(verify_transaction(tx), [])
        self.assertIs(transition(tx, "E-6", "replay"), tx)

    def test_illegal_transition_and_tampering_fail_closed(self):
        tx = new_transaction("TX-2", "intent-hash")
        with self.assertRaises(ValueError):
            transition(tx, "E-1", "apply")
        tx["state"] = "REPLAYABLE"
        self.assertTrue(verify_transaction(tx))
        with self.assertRaises(ValueError):
            transition(tx, "E-2", "authorize")

    def test_hmac_requires_key(self):
        tx = new_transaction("TX-3", "intent-hash", signing_key="secret")
        self.assertTrue(verify_transaction(tx))
        self.assertEqual(verify_transaction(tx, "secret"), [])

    def test_atomic_store_refuses_existing_lock(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "tx.json")
            tx = new_transaction("TX-4", "intent-hash")
            save_transaction(path, tx)
            self.assertEqual(load_transaction(path), tx)
            open(path + ".lock", "w").close()
            with self.assertRaises(RuntimeError):
                save_transaction(path, tx)

    def test_admission_result_bridge_is_idempotent(self):
        tx = new_transaction("TX-5", "intent-hash")
        result = {
            "request_id": "R-5", "executed": True,
            "gate": {"decision": "ALLOW", "result_sha256": "gate"},
            "plan": {"plan_sha256": "plan"},
            "guard": {"receipt_sha256": "guard"},
            "handback": {"verdict": "clean", "handback_sha256": "hb"},
        }
        tx = record_admission_result(tx, result)
        self.assertEqual(tx["state"], "REPLAYABLE")
        self.assertEqual(record_admission_result(tx, result), tx)

    def test_admission_refusal_blocks_without_execution(self):
        tx = new_transaction("TX-6", "intent-hash")
        result = {"request_id": "R-6", "executed": False,
                  "gate": {"decision": "DENY", "result_sha256": "gate"}}
        tx = record_admission_result(tx, result)
        self.assertEqual(tx["state"], "BLOCKED")


class CondenseAcceptanceTests(unittest.TestCase):
    def test_accepts_hashed_probe_and_parity_without_kernel_change(self):
        with tempfile.TemporaryDirectory() as root:
            evidence = {}
            for role in ("probe", "parity"):
                path = os.path.join(root, role + ".json")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(role)
                evidence[role] = {"path": path, "passed": True,
                                  "sha256": hashlib.sha256(
                                      role.encode()).hexdigest()}
            receipt = evaluate_condense_proposal(root, {
                "proposal_id": "P-1", "action": "BUILD_ON_PLATFORM",
                "machine": "M1", "target": "Attestra/test-pack",
                "kernel_changes": [], "evidence": evidence})
            self.assertEqual(receipt["decision"], "ACCEPT")
            self.assertTrue(verify_condense_receipt(receipt))

    def test_rejects_ai_claim_without_evidence_and_kernel_mutation(self):
        receipt = evaluate_condense_proposal(".", {
            "proposal_id": "P-2", "action": "BUILD_ON_PLATFORM",
            "machine": "M1", "target": "Attestra/test-pack",
            "kernel_changes": ["kernel.py"], "evidence": {}})
        self.assertEqual(receipt["decision"], "REJECT")
        self.assertGreaterEqual(len(receipt["problems"]), 3)


class CompositionTests(unittest.TestCase):
    def _chain(self, transaction_id="TX-C"):
        initial = {"request": "x"}
        parent = hashlib.sha256(canonical_json_bytes(initial)).hexdigest()
        stages = []
        for name in ("route", "clear", "certify", "attest", "score"):
            stage = build_stage(name, transaction_id, parent, {"ok": name})
            stages.append(stage)
            parent = stage["receipt_sha256"]
        return initial, stages

    def test_five_stage_chain_passes(self):
        initial, stages = self._chain()
        result = compose("TX-C", initial, stages)
        self.assertEqual(result["status"], "passed")

    def test_failure_isolates_later_stages(self):
        initial, stages = self._chain()
        failed = build_stage("clear", "TX-C", stages[0]["receipt_sha256"],
                             {"ok": False}, status="failed")
        result = compose("TX-C", initial, [stages[0], failed, *stages[2:]])
        self.assertEqual(result["status"], "failed")
        self.assertIn("later stages must not execute after a failure",
                      result["problems"])

    def test_final_score_failure_is_not_success(self):
        initial, stages = self._chain()
        stages[-1] = build_stage("score", "TX-C",
                                 stages[-2]["receipt_sha256"], {}, "failed")
        self.assertEqual(compose("TX-C", initial, stages)["status"], "failed")


class MetricsAndProvisioningTests(unittest.TestCase):
    def test_metrics_are_explicitly_not_t4(self):
        tx = transition(new_transaction("TX-M", "i"), "E", "block")
        report = aggregate_internal_metrics([tx, {"bad": True}])
        self.assertFalse(report["is_t4_utility"])
        self.assertFalse(report["is_product_claim"])
        self.assertEqual(report["counts"]["blocked"], 1)
        self.assertEqual(report["counts"]["invalid"], 1)

    def test_provisioning_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            report = provisioning_report(root)
            self.assertFalse(report["ready"])
            self.assertTrue(report["projects"][0]["missing"])

    def test_actuation_append_refuses_lock_collision(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = os.path.join("state", "ledger.jsonl")
            full = os.path.join(root, ledger)
            os.makedirs(os.path.dirname(full))
            open(full + ".lock", "w").close()
            with self.assertRaises(RuntimeError):
                append_actuation_ledger(root, ledger, "gate", "R-1", {})

    def test_signed_stop_and_resume_require_their_keys(self):
        anchor = "a" * 64
        token = issue_stop_token("S-1", {"id": "issuer"}, "stop",
                                 {"kind": "global"}, anchor,
                                 signing_key="stop-secret")
        self.assertFalse(verify_stop_token_seal(token))
        self.assertTrue(verify_stop_token_seal(token, "stop-secret"))
        receipt = issue_resume_receipt(
            token, [{"approver_id": "reviewer", "kind": "human",
                     "anchor": {"state_receipt_hash": anchor}}],
            "resume", anchor, token_signing_key="stop-secret",
            signing_key="resume-secret")
        self.assertFalse(verify_resume_receipt_seal(receipt))
        self.assertTrue(verify_resume_receipt_seal(receipt, "resume-secret"))
        self.assertEqual(active_stops([token], [receipt]), [token])
        self.assertEqual(active_stops([token], [receipt], "stop-secret",
                                      "resume-secret"), [])


if __name__ == "__main__":
    unittest.main()
