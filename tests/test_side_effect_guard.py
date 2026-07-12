import copy
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_authorization import authorize
from core.helix_evidence import build_evidence_manifest
from core.helix_execution_plan import build_execution_plan
from core.helix_side_effect_guard import (
    guard_side_effects,
    verify_guard_receipt_seal,
)
from core.helix_stop_token import (
    issue_resume_receipt,
    issue_stop_token,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
DRIFTED = "b" * 64


class GuardFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-guard-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(os.path.join(ROOT, "examples", "constitution"),
                        os.path.join(self.root, "examples", "constitution"))
        os.makedirs(os.path.join(self.root, "data"))
        with open(os.path.join(self.root, "data", "existing.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write('{"state": "before"}\n')
        self.intent = {
            "schema": "helix-action-intent/1.0",
            "intent_id": "INT-GUARD-001",
            "title": "write data artifacts",
            "proposer": {"kind": "ai", "id": "helix-runtime"},
            "risk_class": "R1",
            "scope": {"write_paths": ["data/"], "remote_mutation": False,
                      "publish": False},
            "impact": {"authority": False, "economic": False,
                       "physical": False, "broad_public": False},
            "reversibility": {"reversible": True,
                              "rollback_plan": "restore data/ from snapshots"},
            "budget": {"max_files": 3, "max_bytes": 4096},
            "justification": "side effect guard fixture",
        }
        manifest = build_evidence_manifest(
            self.root, "EVM-GUARD-001", self.intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output",
                             "reference": "python -m unittest"}}])
        self.gate = authorize(self.root, self.intent, manifest, [], CURRENT)
        self.assertEqual(self.gate["decision"], "ALLOW")
        self.plan = build_execution_plan(
            self.root, "PLAN-GUARD-001", self.intent, self.gate,
            [{"path": "data/new.json", "op": "create", "planned_bytes": 64},
             {"path": "data/existing.json", "op": "modify",
              "planned_bytes": 128}], "_snapshots")

    def guard(self, current=CURRENT, tokens=None, receipts=None,
              gate=None, plan=None, intent=None):
        return guard_side_effects(
            self.root, intent if intent is not None else self.intent,
            gate if gate is not None else self.gate,
            plan if plan is not None else self.plan,
            current, stop_tokens=tokens, resume_receipts=receipts)


class TestClearedPath(GuardFixtureCase):
    def test_intact_chain_at_current_state_clears(self):
        receipt = self.guard()
        self.assertTrue(receipt["cleared"], receipt["problems"])
        self.assertEqual(receipt["problems"], [])
        self.assertEqual(receipt["plan_sha256"], self.plan["plan_sha256"])
        self.assertEqual(receipt["gate_result_sha256"],
                         self.gate["result_sha256"])
        self.assertTrue(verify_guard_receipt_seal(receipt))

    def test_guard_is_deterministic_and_never_executes(self):
        first = self.guard()
        second = self.guard()
        self.assertEqual(first, second)
        self.assertFalse(os.path.exists(
            os.path.join(self.root, "data", "new.json")))

    def test_unrelated_path_stop_does_not_block(self):
        token = issue_stop_token("STOP-P", {"kind": "human", "id": "op-1"},
                                 "scoped freeze",
                                 {"kind": "path_prefix",
                                  "prefixes": ["seed/"]}, CURRENT)
        receipt = self.guard(tokens=[token])
        self.assertTrue(receipt["cleared"], receipt["problems"])


class TestBlockedPaths(GuardFixtureCase):
    def test_state_drift_expires_plan_authority(self):
        receipt = self.guard(current=DRIFTED)
        self.assertFalse(receipt["cleared"])
        self.assertTrue(any("authority expired" in p
                            for p in receipt["problems"]))

    def test_active_stop_blocks_at_execution_time(self):
        token = issue_stop_token("STOP-G", {"kind": "human", "id": "op-1"},
                                 "incident freeze", {"kind": "global"}, CURRENT)
        receipt = self.guard(tokens=[token])
        self.assertFalse(receipt["cleared"])
        self.assertEqual(len(receipt["blocking_stops"]), 1)
        self.assertTrue(any("stopped: token STOP-G" in p
                            for p in receipt["problems"]))

    def test_resume_restores_clearance(self):
        token = issue_stop_token("STOP-G", {"kind": "human", "id": "op-1"},
                                 "incident freeze", {"kind": "global"}, CURRENT)
        resume = issue_resume_receipt(
            token, [{"approver_id": "op-2", "kind": "human",
                     "anchor": {"state_receipt_hash": CURRENT}}],
            "incident resolved", CURRENT)
        receipt = self.guard(tokens=[token], receipts=[resume])
        self.assertTrue(receipt["cleared"], receipt["problems"])

    def test_precondition_drift_blocks(self):
        with open(os.path.join(self.root, "data", "existing.json"), "a",
                  encoding="utf-8") as f:
            f.write("drift\n")
        receipt = self.guard()
        self.assertFalse(receipt["cleared"])
        self.assertTrue(any("target bytes changed" in p
                            for p in receipt["problems"]))

    def test_tampered_plan_blocks(self):
        tampered = copy.deepcopy(self.plan)
        tampered["effects"][0]["path"] = "schemas/evil.json"
        receipt = self.guard(plan=tampered)
        self.assertFalse(receipt["cleared"])
        self.assertTrue(any("seal is broken" in p for p in receipt["problems"]))

    def test_tampered_gate_blocks(self):
        tampered = copy.deepcopy(self.gate)
        tampered["decision"] = "SANDBOX"
        receipt = self.guard(gate=tampered)
        self.assertFalse(receipt["cleared"])
        self.assertTrue(any("gate result seal is broken" in p
                            for p in receipt["problems"]))

    def test_gate_for_another_intent_blocks(self):
        import json
        with open(os.path.join(self.root, "examples", "constitution",
                               "intent-r0-inspect.json"), encoding="utf-8") as f:
            other = json.load(f)
        receipt = self.guard(intent=other)
        self.assertFalse(receipt["cleared"])
        self.assertTrue(any("different intent" in p
                            for p in receipt["problems"]))

    def test_multiple_failures_are_all_reported(self):
        token = issue_stop_token("STOP-G", {"kind": "human", "id": "op-1"},
                                 "freeze", {"kind": "global"}, CURRENT)
        receipt = self.guard(current=DRIFTED, tokens=[token])
        self.assertFalse(receipt["cleared"])
        self.assertTrue(any("authority expired" in p
                            for p in receipt["problems"]))
        self.assertTrue(any("stopped: token STOP-G" in p
                            for p in receipt["problems"]))


if __name__ == "__main__":
    unittest.main()
