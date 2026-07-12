import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_authorization import authorize
from core.helix_evidence import build_evidence_manifest
from core.helix_execution_plan import (
    build_execution_plan,
    verify_execution_plan,
    verify_plan_seal,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
SNAPSHOT_DIR = "_snapshots"


class PlanFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-plan-")
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
            "intent_id": "INT-PLAN-001",
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
            "justification": "execution plan fixture",
        }
        manifest = build_evidence_manifest(
            self.root, "EVM-PLAN-001", self.intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output",
                             "reference": "python -m unittest"}}])
        self.gate = authorize(self.root, self.intent, manifest, [], CURRENT)
        self.assertEqual(self.gate["decision"], "ALLOW")

    def build(self, effects, intent=None, gate=None):
        return build_execution_plan(
            self.root, "PLAN-001", intent if intent is not None else self.intent,
            gate if gate is not None else self.gate, effects, SNAPSHOT_DIR)

    def default_effects(self):
        return [{"path": "data/new.json", "op": "create", "planned_bytes": 64},
                {"path": "data/existing.json", "op": "modify",
                 "planned_bytes": 128}]


class TestBuild(PlanFixtureCase):
    def test_sealed_plan_with_scope_budget_and_rollback(self):
        plan = self.build(self.default_effects())
        self.assertTrue(verify_plan_seal(plan))
        self.assertEqual(plan["gate_result_sha256"], self.gate["result_sha256"])
        self.assertEqual(plan["budget_check"],
                         {"files": 2, "max_files": 3, "bytes": 192,
                          "max_bytes": 4096})
        rollback = {entry["path"]: entry for entry in plan["rollback"]}
        self.assertIsNone(rollback["data/new.json"]["pre_sha256"])
        modify = rollback["data/existing.json"]
        self.assertIsNotNone(modify["pre_sha256"])
        snapshot_full = os.path.join(self.root, *modify["snapshot_path"].split("/"))
        self.assertTrue(os.path.isfile(snapshot_full))
        self.assertEqual(verify_execution_plan(self.root, plan, self.intent,
                                               self.gate), [])

    def test_build_is_deterministic(self):
        first = self.build(self.default_effects())
        second = self.build(self.default_effects())
        self.assertEqual(first, second)

    def test_no_gate_no_plan(self):
        with self.assertRaisesRegex(ValueError, "no plan without a sealed gate"):
            self.build(self.default_effects(), gate={})
        tampered = copy.deepcopy(self.gate)
        tampered["decision"] = "ALLOW" if tampered["decision"] != "ALLOW" else "SANDBOX"
        with self.assertRaisesRegex(ValueError, "no plan without a sealed gate"):
            self.build(self.default_effects(), gate=tampered)

    def test_non_actuating_gate_decisions_refuse_planning(self):
        with open(os.path.join(self.root, "examples", "constitution",
                               "intent-r2-publish.json"), encoding="utf-8") as f:
            r2 = json.load(f)
        manifest = build_evidence_manifest(
            self.root, "EVM-PLAN-R2", r2, {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output", "reference": "x"}}])
        human_gate = authorize(self.root, r2, manifest, [], CURRENT)
        self.assertEqual(human_gate["decision"], "HUMAN")
        with self.assertRaisesRegex(ValueError, "does not authorize actuation"):
            build_execution_plan(self.root, "PLAN-X", r2, human_gate,
                                 [{"path": ".git/x", "op": "create",
                                   "planned_bytes": 1}], SNAPSHOT_DIR)

    def test_gate_for_another_intent_is_refused(self):
        with open(os.path.join(self.root, "examples", "constitution",
                               "intent-r0-inspect.json"), encoding="utf-8") as f:
            other = json.load(f)
        with self.assertRaisesRegex(ValueError, "different intent"):
            self.build(self.default_effects(), intent=other)

    def test_out_of_scope_path_fails_fast(self):
        with self.assertRaisesRegex(ValueError, "outside the intent"):
            self.build([{"path": "schemas/evil.json", "op": "create",
                         "planned_bytes": 1}])

    def test_budget_overruns_fail_fast(self):
        too_many = [{"path": f"data/f{i}.json", "op": "create",
                     "planned_bytes": 1} for i in range(4)]
        with self.assertRaisesRegex(ValueError, "max_files"):
            self.build(too_many)
        with self.assertRaisesRegex(ValueError, "max_bytes"):
            self.build([{"path": "data/big.json", "op": "create",
                         "planned_bytes": 5000}])

    def test_dry_run_preconditions_fail_fast(self):
        with self.assertRaisesRegex(ValueError, "create but the path exists"):
            self.build([{"path": "data/existing.json", "op": "create",
                         "planned_bytes": 1}])
        for op in ("modify", "delete"):
            with self.subTest(op=op), \
                    self.assertRaisesRegex(ValueError, "path is missing"):
                self.build([{"path": "data/absent.json", "op": op,
                             "planned_bytes": 0}])

    def test_duplicate_paths_and_bad_ops_fail_fast(self):
        with self.assertRaisesRegex(ValueError, "duplicate effect path"):
            self.build([{"path": "data/a.json", "op": "create", "planned_bytes": 1},
                        {"path": "data/a.json", "op": "create", "planned_bytes": 1}])
        with self.assertRaisesRegex(ValueError, "unknown op"):
            self.build([{"path": "data/a.json", "op": "truncate",
                         "planned_bytes": 1}])


class TestVerify(PlanFixtureCase):
    def setUp(self):
        super().setUp()
        self.plan = self.build(self.default_effects())

    def test_tampered_plan_breaks_the_seal(self):
        tampered = copy.deepcopy(self.plan)
        tampered["effects"][0]["path"] = "schemas/evil.json"
        problems = verify_execution_plan(self.root, tampered, self.intent,
                                         self.gate)
        self.assertTrue(any("seal is broken" in p for p in problems), problems)

    def test_missing_or_tampered_snapshot_is_detected(self):
        snapshot_rel = next(e["snapshot_path"] for e in self.plan["rollback"]
                            if e["snapshot_path"])
        snapshot_full = os.path.join(self.root, *snapshot_rel.split("/"))
        with open(snapshot_full, "a", encoding="utf-8") as f:
            f.write("tampered\n")
        problems = verify_execution_plan(self.root, self.plan)
        self.assertTrue(any("snapshot bytes" in p for p in problems), problems)
        os.remove(snapshot_full)
        problems = verify_execution_plan(self.root, self.plan)
        self.assertTrue(any("snapshot missing" in p for p in problems), problems)

    def test_precondition_drift_is_detected_before_actuation(self):
        self.assertEqual(verify_execution_plan(
            self.root, self.plan, check_preconditions=True), [])
        with open(os.path.join(self.root, "data", "existing.json"), "a",
                  encoding="utf-8") as f:
            f.write("drift\n")
        problems = verify_execution_plan(self.root, self.plan,
                                         check_preconditions=True)
        self.assertTrue(any("target bytes changed" in p for p in problems),
                        problems)
        with open(os.path.join(self.root, "data", "new.json"), "w",
                  encoding="utf-8") as f:
            f.write("appeared early\n")
        problems = verify_execution_plan(self.root, self.plan,
                                         check_preconditions=True)
        self.assertTrue(any("create target already exists" in p
                            for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
