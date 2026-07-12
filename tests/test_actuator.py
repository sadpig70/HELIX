import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_actuator import (
    read_actuation_ledger,
    run_admission,
    verify_actuation_ledger,
)
from core.helix_evidence import build_evidence_manifest
from core.helix_state_receipt import sha256_file
from core.helix_stop_token import issue_stop_token


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
LEDGER = "_actuation/ledger.jsonl"
SNAPSHOTS = "_actuation/snapshots"


class ActuatorFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-actuator-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result",
                     "impact-handback"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(os.path.join(ROOT, "examples", "constitution"),
                        os.path.join(self.root, "examples", "constitution"))
        os.makedirs(os.path.join(self.root, "data"))
        with open(os.path.join(self.root, "data", "existing.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write('{"state": "before"}\n')

    def make_intent(self, risk="R1", publish=False):
        return {
            "schema": "helix-action-intent/1.0",
            "intent_id": "INT-ACT-001",
            "title": "actuate data artifacts",
            "proposer": {"kind": "ai", "id": "helix-runtime"},
            "risk_class": risk,
            "scope": {"write_paths": ["data/"], "remote_mutation": False,
                      "publish": publish},
            "impact": {"authority": False, "economic": False,
                       "physical": False, "broad_public": False},
            "reversibility": {"reversible": True,
                              "rollback_plan": "restore data/ from snapshots"},
            "budget": {"max_files": 3, "max_bytes": 4096},
            "justification": "unified command fixture",
        }

    def make_manifest(self, intent, origin="command_output",
                      reference="python -m unittest"):
        return build_evidence_manifest(
            self.root, "EVM-ACT-001", intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": origin, "reference": reference}}])

    def request(self, intent=None, effects=None, approvals=None,
                manifest=None):
        intent = intent or self.make_intent()
        return {
            "request_id": "REQ-001",
            "intent": intent,
            "evidence_manifest": manifest or self.make_manifest(intent),
            "approvals": approvals or [],
            "effects": effects if effects is not None else [
                {"path": "data/new.json", "op": "create",
                 "content": '{"state": "created"}\n'},
                {"path": "data/existing.json", "op": "modify",
                 "content": '{"state": "after"}\n'},
            ],
        }

    def admit(self, request=None, **kwargs):
        return run_admission(self.root, request or self.request(), CURRENT,
                             LEDGER, SNAPSHOTS, **kwargs)

    def data_file(self, name):
        return os.path.join(self.root, "data", name)


class TestCleanLoop(ActuatorFixtureCase):
    def test_full_loop_executes_and_ledgers_the_whole_chain(self):
        result = self.admit()
        self.assertTrue(result["executed"])
        self.assertEqual(result["stage"], "complete")
        self.assertEqual(result["handback"]["verdict"], "clean")
        self.assertTrue(result["consumable"])
        self.assertFalse(result["rolled_back"])
        self.assertTrue(os.path.isfile(self.data_file("new.json")))
        entries = read_actuation_ledger(self.root, LEDGER)
        self.assertEqual([e["kind"] for e in entries],
                         ["gate", "plan", "guard", "handback"])
        self.assertEqual(verify_actuation_ledger(self.root, LEDGER), [])

    def test_chain_links_receipts_to_each_other(self):
        result = self.admit()
        self.assertEqual(result["plan"]["gate_result_sha256"],
                         result["gate"]["result_sha256"])
        self.assertEqual(result["guard"]["plan_sha256"],
                         result["plan"]["plan_sha256"])
        self.assertEqual(result["handback"]["guard_receipt_sha256"],
                         result["guard"]["receipt_sha256"])

    def test_consecutive_runs_extend_one_chained_ledger(self):
        self.admit()
        second = self.request()
        second["request_id"] = "REQ-002"
        second["effects"] = [{"path": "data/second.json", "op": "create",
                              "content": "second\n"}]
        second["intent"]["intent_id"] = "INT-ACT-002"
        second["evidence_manifest"] = self.make_manifest(second["intent"])
        run_admission(self.root, second, CURRENT, LEDGER, SNAPSHOTS)
        entries = read_actuation_ledger(self.root, LEDGER)
        self.assertEqual(len(entries), 8)
        self.assertEqual([e["seq"] for e in entries], list(range(8)))
        self.assertEqual(verify_actuation_ledger(self.root, LEDGER), [])


class TestRefusalsAreEffectFree(ActuatorFixtureCase):
    def assert_no_side_effects(self):
        self.assertFalse(os.path.exists(self.data_file("new.json")))
        self.assertEqual(sha256_file(self.data_file("existing.json")),
                         sha256_file(self.data_file("existing.json")))
        with open(self.data_file("existing.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"state": "before"}\n')

    def test_human_gate_stops_before_any_effect(self):
        intent = self.make_intent(risk="R2", publish=True)
        result = self.admit(self.request(intent=intent))
        self.assertFalse(result["executed"])
        self.assertEqual(result["stage"], "gate")
        self.assertEqual(result["gate"]["decision"], "HUMAN")
        self.assert_no_side_effects()
        entries = read_actuation_ledger(self.root, LEDGER)
        self.assertEqual([e["kind"] for e in entries], ["gate"])

    def test_stop_token_stops_before_any_effect(self):
        token = issue_stop_token("STOP-A", {"kind": "human", "id": "op-1"},
                                 "freeze", {"kind": "global"}, CURRENT)
        result = self.admit(stop_tokens=[token])
        self.assertFalse(result["executed"])
        self.assertEqual(result["stage"], "gate")
        self.assert_no_side_effects()

    def test_plan_refusal_is_ledgered_and_effect_free(self):
        request = self.request(effects=[
            {"path": "schemas/evil.json", "op": "create", "content": "x"}])
        result = self.admit(request)
        self.assertFalse(result["executed"])
        self.assertEqual(result["stage"], "plan")
        self.assertIn("outside the intent", result["why"])
        entries = read_actuation_ledger(self.root, LEDGER)
        self.assertEqual([e["kind"] for e in entries], ["gate", "plan_refusal"])
        self.assert_no_side_effects()

    def test_budget_overrun_refuses_at_plan(self):
        request = self.request(effects=[
            {"path": "data/big.json", "op": "create", "content": "x" * 5000}])
        result = self.admit(request)
        self.assertEqual(result["stage"], "plan")
        self.assertIn("max_bytes", result["why"])
        self.assert_no_side_effects()


class TestDeviationAndSandbox(ActuatorFixtureCase):
    def test_deviated_run_rolls_back_with_proof_and_is_not_consumable(self):
        # planned modify writes identical bytes -> honest deviation
        request = self.request(effects=[
            {"path": "data/new.json", "op": "create",
             "content": '{"state": "created"}\n'},
            {"path": "data/existing.json", "op": "modify",
             "content": '{"state": "before"}\n'},
        ])
        result = self.admit(request)
        self.assertTrue(result["executed"])
        self.assertEqual(result["handback"]["verdict"], "deviated")
        self.assertTrue(result["rolled_back"])
        self.assertEqual(result["rollback_report"]["problems"], [])
        self.assertFalse(result["consumable"])
        self.assertFalse(os.path.exists(self.data_file("new.json")))
        entries = read_actuation_ledger(self.root, LEDGER)
        self.assertEqual([e["kind"] for e in entries],
                         ["gate", "plan", "guard", "handback", "rollback"])
        self.assertTrue(entries[-1]["receipt"]["recovered"])

    def test_sandbox_run_executes_but_is_never_consumable(self):
        intent = self.make_intent()
        manifest = self.make_manifest(intent, origin="external", reference=None)
        result = self.admit(self.request(intent=intent, manifest=manifest))
        self.assertEqual(result["gate"]["decision"], "SANDBOX")
        self.assertTrue(result["executed"])
        self.assertEqual(result["handback"]["verdict"], "clean")
        self.assertFalse(result["consumable"])
        self.assertIn("never consumed", result["why"])


class TestLedgerIntegrity(ActuatorFixtureCase):
    def test_tampered_ledger_line_breaks_the_chain(self):
        self.admit()
        full = os.path.join(self.root, *LEDGER.split("/"))
        with open(full, encoding="utf-8") as f:
            lines = f.read().splitlines()
        doc = json.loads(lines[1])
        doc["kind"] = "guard"
        lines[1] = json.dumps(doc, ensure_ascii=False, sort_keys=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        problems = verify_actuation_ledger(self.root, LEDGER)
        self.assertTrue(any("entry seal broken" in p for p in problems),
                        problems)


if __name__ == "__main__":
    unittest.main()
