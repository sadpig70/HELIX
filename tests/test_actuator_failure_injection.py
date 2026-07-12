"""Adversarial failure injection against the actuation pipeline (P4_6).

Every injection must end in either ZERO side effects or an HONEST record —
the pre-verification of the T3 gate criteria: ungated admission 0, writes
after stop 0, bypass 0, rollback failures never recorded as success.
"""

import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_actuator import (
    append_actuation_ledger,
    read_actuation_ledger,
    run_admission,
    verify_actuation_chain,
    verify_actuation_ledger,
)
from core.helix_authorization import authorize
from core.helix_evidence import build_evidence_manifest
from core.helix_execution_plan import build_execution_plan
from core.helix_holdout import canonical_json_bytes
from core.helix_impact_handback import build_impact_handback, perform_rollback
from core.helix_side_effect_guard import guard_side_effects
from core.helix_state_receipt import sha256_file
from core.helix_stop_token import issue_resume_receipt, issue_stop_token


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
DRIFTED = "b" * 64
LEDGER = "_actuation/ledger.jsonl"
SNAPSHOTS = "_actuation/snapshots"


def forge_seal(doc, seal_key="receipt_sha256"):
    """What an attacker can always do: recompute a canonical seal."""
    forged = {k: v for k, v in doc.items() if k != seal_key}
    forged[seal_key] = hashlib.sha256(canonical_json_bytes(forged)).hexdigest()
    return forged


class InjectionFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-inject-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result",
                     "impact-handback"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(os.path.join(ROOT, "examples", "constitution"),
                        os.path.join(self.root, "examples", "constitution"))
        os.makedirs(os.path.join(self.root, "data"))
        self.write("data/existing.json", '{"state": "before"}\n')
        self.intent = {
            "schema": "helix-action-intent/1.0",
            "intent_id": "INT-INJ-001",
            "title": "actuate data artifacts",
            "proposer": {"kind": "ai", "id": "helix-runtime"},
            "risk_class": "R1",
            "scope": {"write_paths": ["data/"], "remote_mutation": False,
                      "publish": False},
            "impact": {"authority": False, "economic": False,
                       "physical": False, "broad_public": False},
            "reversibility": {"reversible": True,
                              "rollback_plan": "restore data/ from snapshots"},
            "budget": {"max_files": 3, "max_bytes": 4096},
            "justification": "failure injection fixture",
        }
        self.manifest = build_evidence_manifest(
            self.root, "EVM-INJ-001", self.intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output",
                             "reference": "python -m unittest"}}])

    def write(self, rel, text):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def request(self, effects=None):
        return {"request_id": "REQ-INJ", "intent": self.intent,
                "evidence_manifest": self.manifest, "approvals": [],
                "effects": effects if effects is not None else [
                    {"path": "data/new.json", "op": "create",
                     "content": '{"state": "created"}\n'}]}

    def gate(self, anchor=CURRENT, **kwargs):
        return authorize(self.root, self.intent, self.manifest, [], anchor,
                         **kwargs)

    def plan(self, gate, effects=None):
        return build_execution_plan(
            self.root, "PLAN-INJ", self.intent, gate,
            effects or [{"path": "data/new.json", "op": "create",
                         "planned_bytes": 32},
                        {"path": "data/existing.json", "op": "modify",
                         "planned_bytes": 32}], SNAPSHOTS)


class TestBypassAttempts(InjectionFixtureCase):
    def test_forged_guard_handback_is_caught_by_the_ledger_audit(self):
        result = run_admission(self.root, self.request(), CURRENT, LEDGER,
                               SNAPSHOTS)
        self.assertTrue(result["consumable"])
        # Attacker forges a guard that never ran and a handback over it,
        # then appends the handback as a second "run" without gate/plan/guard.
        forged_guard = forge_seal({**result["guard"], "cleared": True})
        forged_handback = forge_seal({**result["handback"],
                                      "handback_id": "HB-FORGED",
                                      "guard_receipt_sha256":
                                          forged_guard["receipt_sha256"]})
        append_actuation_ledger(self.root, LEDGER, "handback", "REQ-FORGED",
                                forged_handback)
        problems = verify_actuation_chain(self.root, LEDGER)
        self.assertTrue(any("ungated admission" in p for p in problems),
                        problems)

    def test_handback_over_a_never_ledgered_guard_is_a_bypass(self):
        gate = self.gate()
        append_actuation_ledger(self.root, LEDGER, "gate", "REQ-X", gate)
        plan = self.plan(gate)
        append_actuation_ledger(self.root, LEDGER, "plan", "REQ-X", plan)
        # skip the guard entirely; forge one just to build the handback
        rogue_guard = forge_seal({
            "schema": "helix-side-effect-guard/1.0",
            "plan_sha256": plan["plan_sha256"],
            "gate_result_sha256": gate["result_sha256"],
            "intent_digest": plan["intent_digest"],
            "state_receipt_hash": CURRENT,
            "blocking_stops": [], "problems": [], "cleared": True})
        self.write("data/new.json", '{"state": "created"}\n')
        self.write("data/existing.json", '{"state": "after"}\n')
        handback = build_impact_handback(self.root, "HB-X", plan, rogue_guard)
        append_actuation_ledger(self.root, LEDGER, "handback", "REQ-X", handback)
        problems = verify_actuation_chain(self.root, LEDGER)
        self.assertTrue(any("guard bypass" in p for p in problems), problems)

    def test_execution_receipts_after_a_human_gate_are_ungated_admission(self):
        intent = copy.deepcopy(self.intent)
        intent["risk_class"] = "R2"
        intent["scope"]["publish"] = True
        manifest = build_evidence_manifest(
            self.root, "EVM-INJ-R2", intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output", "reference": "x"}}])
        human_gate = authorize(self.root, intent, manifest, [], CURRENT)
        self.assertEqual(human_gate["decision"], "HUMAN")
        append_actuation_ledger(self.root, LEDGER, "gate", "REQ-H", human_gate)
        append_actuation_ledger(self.root, LEDGER, "plan", "REQ-H",
                                {"gate_result_sha256":
                                 human_gate["result_sha256"]})
        problems = verify_actuation_chain(self.root, LEDGER)
        self.assertTrue(any("non-actuating gate" in p for p in problems),
                        problems)

    def test_execution_after_a_plan_refusal_is_caught(self):
        result = run_admission(self.root, self.request(effects=[
            {"path": "schemas/evil.json", "op": "create", "content": "x"}]),
            CURRENT, LEDGER, SNAPSHOTS)
        self.assertEqual(result["stage"], "plan")
        append_actuation_ledger(self.root, LEDGER, "handback", "REQ-INJ",
                                {"guard_receipt_sha256": "0" * 64})
        problems = verify_actuation_chain(self.root, LEDGER)
        self.assertTrue(any("after a plan refusal" in p for p in problems),
                        problems)

    def test_rollback_without_deviation_is_caught(self):
        run_admission(self.root, self.request(), CURRENT, LEDGER, SNAPSHOTS)
        append_actuation_ledger(self.root, LEDGER, "rollback", "REQ-INJ",
                                {"recovered": True})
        problems = verify_actuation_chain(self.root, LEDGER)
        self.assertTrue(any("without a deviated handback" in p
                            for p in problems), problems)

    def test_honest_ledgers_pass_the_audit(self):
        run_admission(self.root, self.request(), CURRENT, LEDGER, SNAPSHOTS)
        deviated = self.request(effects=[
            {"path": "data/existing.json", "op": "modify",
             "content": '{"state": "before"}\n'}])
        deviated["request_id"] = "REQ-DEV"
        run_admission(self.root, deviated, CURRENT, LEDGER, SNAPSHOTS)
        self.assertEqual(verify_actuation_chain(self.root, LEDGER), [])


class TestExpiryAndStopInjection(InjectionFixtureCase):
    def test_state_drift_between_gate_and_execution_blocks(self):
        gate = self.gate(anchor=CURRENT)
        plan = self.plan(gate)
        guard = guard_side_effects(self.root, self.intent, gate, plan, DRIFTED)
        self.assertFalse(guard["cleared"])
        self.assertTrue(any("authority expired" in p
                            for p in guard["problems"]))
        with self.assertRaisesRegex(ValueError, "did not clear"):
            build_impact_handback(self.root, "HB-X", plan, guard)

    def test_stop_issued_after_gate_blocks_execution_until_resumed(self):
        gate = self.gate()
        plan = self.plan(gate)
        token = issue_stop_token("STOP-INJ", {"kind": "human", "id": "op-1"},
                                 "late freeze", {"kind": "global"}, CURRENT)
        guard = guard_side_effects(self.root, self.intent, gate, plan, CURRENT,
                                   stop_tokens=[token])
        self.assertFalse(guard["cleared"])
        self.assertFalse(os.path.exists(
            os.path.join(self.root, "data", "new.json")))
        resume = issue_resume_receipt(
            token, [{"approver_id": "op-2", "kind": "human",
                     "anchor": {"state_receipt_hash": CURRENT}}],
            "resolved", CURRENT)
        cleared = guard_side_effects(self.root, self.intent, gate, plan,
                                     CURRENT, stop_tokens=[token],
                                     resume_receipts=[resume])
        self.assertTrue(cleared["cleared"], cleared["problems"])


class TestRollbackFailureInjection(InjectionFixtureCase):
    def test_snapshot_poisoning_is_neutralized_at_plan_time(self):
        pre_digest = sha256_file(
            os.path.join(self.root, "data", "existing.json"))
        poison_rel = f"{SNAPSHOTS}/{pre_digest}.bin"
        self.write(poison_rel, "poisoned snapshot content\n")
        plan = self.plan(self.gate())
        entry = next(e for e in plan["rollback"]
                     if e["path"] == "data/existing.json")
        snapshot_full = os.path.join(self.root, *entry["snapshot_path"].split("/"))
        self.assertEqual(sha256_file(snapshot_full), pre_digest)

    def test_corrupted_snapshot_after_plan_is_caught_by_the_guard(self):
        gate = self.gate()
        plan = self.plan(gate)
        entry = next(e for e in plan["rollback"] if e["snapshot_path"])
        self.write(entry["snapshot_path"], "corrupted after plan\n")
        guard = guard_side_effects(self.root, self.intent, gate, plan, CURRENT)
        self.assertFalse(guard["cleared"])
        self.assertTrue(any("snapshot" in p for p in guard["problems"]))

    def test_failed_recovery_is_never_recorded_as_success(self):
        gate = self.gate()
        plan = self.plan(gate)
        guard = guard_side_effects(self.root, self.intent, gate, plan, CURRENT)
        self.assertTrue(guard["cleared"])
        self.write("data/new.json", '{"state": "created"}\n')
        # deviation: modify never applied; and the snapshot gets corrupted
        entry = next(e for e in plan["rollback"] if e["snapshot_path"])
        self.write(entry["snapshot_path"], "corrupted after guard\n")
        handback = build_impact_handback(self.root, "HB-INJ", plan, guard)
        self.assertEqual(handback["verdict"], "deviated")
        self.assertFalse(handback["rollback_ready"])
        report = perform_rollback(self.root, plan)
        self.assertTrue(report["problems"])
        recovered = not report["problems"]
        self.assertFalse(recovered)


class TestLedgerAttacks(InjectionFixtureCase):
    def mutate_ledger(self, mutate):
        full = os.path.join(self.root, *LEDGER.split("/"))
        with open(full, encoding="utf-8") as f:
            lines = [line for line in f.read().splitlines() if line]
        lines = mutate(lines)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")

    def test_deleting_an_entry_breaks_the_chain(self):
        run_admission(self.root, self.request(), CURRENT, LEDGER, SNAPSHOTS)
        self.mutate_ledger(lambda lines: lines[:1] + lines[2:])
        problems = verify_actuation_ledger(self.root, LEDGER)
        self.assertTrue(any("parent chain broken" in p for p in problems)
                        or any("seq" in p for p in problems), problems)

    def test_reordering_entries_breaks_the_chain(self):
        run_admission(self.root, self.request(), CURRENT, LEDGER, SNAPSHOTS)
        self.mutate_ledger(lambda lines: [lines[0], lines[2], lines[1],
                                          lines[3]])
        problems = verify_actuation_ledger(self.root, LEDGER)
        self.assertTrue(any("parent chain broken" in p for p in problems),
                        problems)


if __name__ == "__main__":
    unittest.main()
