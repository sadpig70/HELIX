import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_authorization import authorize
from core.helix_evidence import build_evidence_manifest
from core.helix_execution_plan import build_execution_plan
from core.helix_impact_handback import (
    build_impact_handback,
    perform_rollback,
    snapshot_scope,
    verify_handback_seal,
    verify_impact_handback,
)
from core.helix_schema import schema_features, validate_against_schema
from core.helix_side_effect_guard import guard_side_effects
from core.helix_state_receipt import sha256_file


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "impact-handback.schema.json")
CURRENT = "a" * 64


class HandbackFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-handback-")
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
        self.write("data/doomed.json", "to be deleted\n")
        self.intent = {
            "schema": "helix-action-intent/1.0",
            "intent_id": "INT-HB-001",
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
            "justification": "impact handback fixture",
        }
        manifest = build_evidence_manifest(
            self.root, "EVM-HB-001", self.intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output",
                             "reference": "python -m unittest"}}])
        gate = authorize(self.root, self.intent, manifest, [], CURRENT)
        self.plan = build_execution_plan(
            self.root, "PLAN-HB-001", self.intent, gate,
            [{"path": "data/new.json", "op": "create", "planned_bytes": 32},
             {"path": "data/existing.json", "op": "modify", "planned_bytes": 32},
             {"path": "data/doomed.json", "op": "delete", "planned_bytes": 0}],
            "_snapshots")
        self.guard = guard_side_effects(self.root, self.intent, gate,
                                        self.plan, CURRENT)
        self.assertTrue(self.guard["cleared"])
        self.pre_scope = snapshot_scope(self.root, self.intent)

    def write(self, rel, text):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def execute_plan(self):
        self.write("data/new.json", '{"state": "created"}\n')
        self.write("data/existing.json", '{"state": "after"}\n')
        os.remove(os.path.join(self.root, "data", "doomed.json"))

    def handback(self, with_scope=True, handback_id="HB-001"):
        post = snapshot_scope(self.root, self.intent) if with_scope else None
        return build_impact_handback(
            self.root, handback_id, self.plan, self.guard,
            pre_scope=self.pre_scope if with_scope else None, post_scope=post)


class TestCleanHandback(HandbackFixtureCase):
    def test_faithful_execution_seals_clean(self):
        self.execute_plan()
        handback = self.handback()
        self.assertEqual(handback["verdict"], "clean")
        self.assertEqual(handback["problems"], [])
        self.assertTrue(handback["budget_ok"])
        self.assertTrue(handback["rollback_ready"])
        self.assertTrue(handback["undeclared"]["checked"])
        self.assertEqual(handback["undeclared"]["changes"], [])
        statuses = {o["path"]: o["status"] for o in handback["outcomes"]}
        self.assertEqual(set(statuses.values()), {"applied"})
        self.assertTrue(verify_handback_seal(handback))
        self.assertEqual(validate_against_schema(handback, SCHEMA), [])
        self.assertEqual(verify_impact_handback(self.root, handback,
                                                self.plan, self.guard), [])

    def test_trace_chain_is_complete(self):
        self.execute_plan()
        handback = self.handback()
        self.assertEqual(handback["plan_sha256"], self.plan["plan_sha256"])
        self.assertEqual(handback["guard_receipt_sha256"],
                         self.guard["receipt_sha256"])
        self.assertEqual(handback["gate_result_sha256"],
                         self.plan["gate_result_sha256"])
        self.assertEqual(handback["intent_digest"], self.plan["intent_digest"])

    def test_schema_stays_in_stdlib_subset(self):
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema_features(schema), {"in_subset": True, "unsupported": []})


class TestDeviations(HandbackFixtureCase):
    def test_no_handback_without_a_cleared_guard(self):
        blocked = copy.deepcopy(self.guard)
        blocked["cleared"] = False
        with self.assertRaisesRegex(ValueError, "sealed guard"):
            build_impact_handback(self.root, "HB-X", self.plan, blocked)
        honest_blocked = guard_side_effects(self.root, self.intent,
                                            {"result_sha256": "x"}, self.plan,
                                            CURRENT)
        self.assertFalse(honest_blocked["cleared"])
        with self.assertRaisesRegex(ValueError, "did not clear"):
            build_impact_handback(self.root, "HB-X", self.plan, honest_blocked)

    def test_guard_for_another_plan_is_refused(self):
        foreign = dict(self.guard)
        foreign["plan_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sealed guard"):
            build_impact_handback(self.root, "HB-X", self.plan, foreign)

    def test_unapplied_effects_are_recorded_not_hidden(self):
        self.write("data/new.json", '{"state": "created"}\n')  # only 1 of 3
        handback = self.handback(with_scope=False)
        self.assertEqual(handback["verdict"], "deviated")
        self.assertTrue(any("bytes are unchanged" in p
                            for p in handback["problems"]))
        self.assertTrue(any("still exists" in p for p in handback["problems"]))
        statuses = {o["path"]: o["status"] for o in handback["outcomes"]}
        self.assertEqual(statuses["data/new.json"], "applied")
        self.assertEqual(statuses["data/existing.json"], "not_applied")
        self.assertEqual(statuses["data/doomed.json"], "not_applied")

    def test_real_budget_overrun_is_reported(self):
        self.execute_plan()
        self.write("data/new.json", "x" * 5000)  # blow the byte budget
        handback = self.handback(with_scope=False)
        self.assertEqual(handback["verdict"], "deviated")
        self.assertFalse(handback["budget_ok"])
        self.assertTrue(any("budget exceeded in reality" in p
                            for p in handback["problems"]))

    def test_undeclared_in_scope_changes_are_violations(self):
        self.execute_plan()
        self.write("data/sneaky.json", "undeclared write\n")
        handback = self.handback()
        self.assertEqual(handback["verdict"], "deviated")
        self.assertIn({"path": "data/sneaky.json", "kind": "created"},
                      handback["undeclared"]["changes"])

    def test_without_scope_snapshot_the_check_is_honestly_unchecked(self):
        self.execute_plan()
        self.write("data/sneaky.json", "undeclared write\n")
        handback = self.handback(with_scope=False)
        self.assertFalse(handback["undeclared"]["checked"])
        self.assertEqual(handback["verdict"], "clean")

    def test_post_handback_drift_is_detected_by_verification(self):
        self.execute_plan()
        handback = self.handback()
        self.write("data/new.json", "changed after handback\n")
        problems = verify_impact_handback(self.root, handback)
        self.assertTrue(any("drifted after handback" in p for p in problems),
                        problems)


class TestRollback(HandbackFixtureCase):
    def test_rollback_restores_and_proves_the_pre_state(self):
        pre_existing = sha256_file(
            os.path.join(self.root, "data", "existing.json"))
        pre_doomed = sha256_file(os.path.join(self.root, "data", "doomed.json"))
        self.execute_plan()
        report = perform_rollback(self.root, self.plan)
        self.assertEqual(report["problems"], [])
        self.assertEqual(len(report["restored"]), 3)
        self.assertFalse(os.path.exists(
            os.path.join(self.root, "data", "new.json")))
        self.assertEqual(sha256_file(
            os.path.join(self.root, "data", "existing.json")), pre_existing)
        self.assertEqual(sha256_file(
            os.path.join(self.root, "data", "doomed.json")), pre_doomed)

    def test_corrupt_snapshot_makes_rollback_unprovable(self):
        self.execute_plan()
        snapshot_rel = next(e["snapshot_path"] for e in self.plan["rollback"]
                            if e["path"] == "data/existing.json")
        with open(os.path.join(self.root, *snapshot_rel.split("/")), "a",
                  encoding="utf-8") as f:
            f.write("corrupted\n")
        report = perform_rollback(self.root, self.plan)
        self.assertTrue(any("snapshot bytes are corrupt" in p
                            for p in report["problems"]))

    def test_tampered_plan_refuses_rollback(self):
        tampered = copy.deepcopy(self.plan)
        tampered["rollback"][0]["path"] = "schemas/evil.json"
        report = perform_rollback(self.root, tampered)
        self.assertEqual(report["restored"], [])
        self.assertTrue(any("refusing" in p for p in report["problems"]))


if __name__ == "__main__":
    unittest.main()
