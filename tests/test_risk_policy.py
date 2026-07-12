import copy
import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_risk_policy import (
    DRY_RUN_ROLE,
    effective_risk_class,
    evaluate_risk_policy,
    policy_matrix,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples", "constitution")
CURRENT = "a" * 64
STALE = "b" * 64


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as f:
        return json.load(f)


def approval(approver_id, kind="human", anchor=CURRENT):
    doc = {"approver_id": approver_id, "kind": kind}
    if anchor is not None:
        doc["anchor"] = {"state_receipt_hash": anchor}
    return doc


def dry_run_manifest():
    return {"artifacts": [{"role": DRY_RUN_ROLE,
                           "path": "_workspace/dry-run.json",
                           "sha256": "c" * 64, "bytes": 10,
                           "provenance": {"origin": "command_output",
                                          "reference": "python helix.py status"}}]}


class TestMatrix(unittest.TestCase):
    def test_matrix_values_match_the_process_plan(self):
        self.assertEqual(policy_matrix(), {
            "R0": {"human_approvals": 0, "dry_run_required": False},
            "R1": {"human_approvals": 0, "dry_run_required": False},
            "R2": {"human_approvals": 1, "dry_run_required": False},
            "R3": {"human_approvals": 2, "dry_run_required": True},
        })

    def test_effective_risk_never_trusts_a_low_label(self):
        intent = _load("intent-r1-local-artifact.json")
        self.assertEqual(effective_risk_class(intent), "R1")
        intent["scope"]["publish"] = True  # derived R2, declared R1
        self.assertEqual(effective_risk_class(intent), "R2")
        intent["risk_class"] = "R3"  # over-declaration wins upward
        self.assertEqual(effective_risk_class(intent), "R3")


class TestLowRisk(unittest.TestCase):
    def test_r0_and_r1_are_satisfied_without_approvals(self):
        for name in ("intent-r0-inspect.json", "intent-r1-local-artifact.json"):
            with self.subTest(intent=name):
                result = evaluate_risk_policy(_load(name), [], CURRENT)
                self.assertTrue(result["satisfied"], result["problems"])
                self.assertEqual(result["valid_approvers"], [])

    def test_an_invalid_approval_poisons_even_a_low_risk_evaluation(self):
        intent = _load("intent-r0-inspect.json")
        result = evaluate_risk_policy(
            intent, [approval("helix-runtime")], CURRENT)  # self-approval
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("separation of duties" in p
                            for p in result["problems"]))


class TestR2Approvals(unittest.TestCase):
    def setUp(self):
        self.intent = _load("intent-r2-publish.json")

    def test_one_distinct_human_approval_satisfies_r2(self):
        result = evaluate_risk_policy(self.intent, [approval("reviewer-1")],
                                      CURRENT)
        self.assertTrue(result["satisfied"], result["problems"])
        self.assertEqual(result["valid_approvers"], ["reviewer-1"])

    def test_no_approvals_is_insufficient(self):
        result = evaluate_risk_policy(self.intent, [], CURRENT)
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("insufficient human approvals" in p
                            for p in result["problems"]))

    def test_non_human_approval_cannot_grant_authority(self):
        result = evaluate_risk_policy(self.intent,
                                      [approval("agent-1", kind="ai")], CURRENT)
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("cannot approve" in p for p in result["problems"]))

    def test_proposer_cannot_approve_their_own_action(self):
        result = evaluate_risk_policy(self.intent,
                                      [approval("helix-runtime")], CURRENT)
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("separation of duties" in p
                            for p in result["problems"]))

    def test_stale_anchor_means_expired_approval(self):
        result = evaluate_risk_policy(self.intent,
                                      [approval("reviewer-1", anchor=STALE)],
                                      CURRENT)
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("expired" in p for p in result["problems"]))

    def test_missing_anchor_is_rejected(self):
        result = evaluate_risk_policy(self.intent,
                                      [approval("reviewer-1", anchor=None)],
                                      CURRENT)
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("missing state-receipt anchor" in p
                            for p in result["problems"]))

    def test_blank_approver_id_is_rejected(self):
        result = evaluate_risk_policy(self.intent, [approval("  ")], CURRENT)
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("approver_id" in p for p in result["problems"]))


class TestR3TwoParty(unittest.TestCase):
    def setUp(self):
        self.intent = _load("intent-r3-authority.json")
        self.two = [approval("reviewer-1"), approval("reviewer-2")]

    def test_two_humans_plus_dry_run_satisfy_r3(self):
        result = evaluate_risk_policy(self.intent, self.two, CURRENT,
                                      dry_run_manifest())
        self.assertTrue(result["satisfied"], result["problems"])
        self.assertEqual(result["valid_approvers"], ["reviewer-1", "reviewer-2"])

    def test_r3_without_dry_run_evidence_is_not_satisfied(self):
        result = evaluate_risk_policy(self.intent, self.two, CURRENT)
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("dry-run evidence" in p for p in result["problems"]))

    def test_one_approval_is_insufficient_for_r3(self):
        result = evaluate_risk_policy(self.intent, [approval("reviewer-1")],
                                      CURRENT, dry_run_manifest())
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("insufficient human approvals" in p
                            for p in result["problems"]))

    def test_duplicate_approver_cannot_stand_in_for_two_parties(self):
        result = evaluate_risk_policy(
            self.intent, [approval("reviewer-1"), approval("reviewer-1")],
            CURRENT, dry_run_manifest())
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("duplicate approver" in p for p in result["problems"]))

    def test_proposer_among_two_parties_poisons_the_set(self):
        result = evaluate_risk_policy(
            self.intent, [approval("reviewer-1"), approval("operator-1")],
            CURRENT, dry_run_manifest())
        self.assertFalse(result["satisfied"])
        self.assertTrue(any("separation of duties" in p
                            for p in result["problems"]))

    def test_evaluation_is_deterministic(self):
        first = evaluate_risk_policy(self.intent, copy.deepcopy(self.two),
                                     CURRENT, dry_run_manifest())
        second = evaluate_risk_policy(self.intent, copy.deepcopy(self.two),
                                      CURRENT, dry_run_manifest())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
