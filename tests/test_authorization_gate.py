import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_authorization import authorize, verify_gate_result_seal
from core.helix_evidence import build_evidence_manifest, seal_manifest
from core.helix_schema import schema_features, validate_against_schema


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "gate-result.schema.json")
CURRENT = "a" * 64
ISSUER = {"kind": "system", "id": "helix-runtime"}


def approval(approver_id, anchor=CURRENT):
    return {"approver_id": approver_id, "kind": "human",
            "anchor": {"state_receipt_hash": anchor}}


class GateFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-gate-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(os.path.join(ROOT, "examples", "constitution"),
                        os.path.join(self.root, "examples", "constitution"))

    def intent(self, name):
        path = os.path.join(self.root, "examples", "constitution", name)
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def manifest_for(self, intent, extra_specs=(), origin="command_output",
                     reference="python -m unittest discover -s tests -q"):
        specs = [{"role": "test_log",
                  "path": "examples/constitution/artifacts/demo-test-log.txt",
                  "provenance": {"origin": origin, "reference": reference}}]
        specs.extend(copy.deepcopy(list(extra_specs)))
        return build_evidence_manifest(self.root, "EVM-GATE-001", intent,
                                       ISSUER, specs)

    def dry_run_spec(self):
        return {"role": "dry_run",
                "path": "examples/constitution/artifacts/demo-state.json",
                "provenance": {"origin": "command_output",
                               "reference": "python helix.py status"}}


class TestAllowPaths(GateFixtureCase):
    def test_r1_with_receipt_backed_evidence_allows(self):
        intent = self.intent("intent-r1-local-artifact.json")
        result = authorize(self.root, intent, self.manifest_for(intent), [],
                           CURRENT)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertTrue(result["reasons"])
        self.assertTrue(verify_gate_result_seal(result))
        self.assertEqual(validate_against_schema(result, SCHEMA), [])

    def test_identical_inputs_produce_identical_sealed_results(self):
        intent = self.intent("intent-r1-local-artifact.json")
        manifest = self.manifest_for(intent)
        first = authorize(self.root, intent, manifest, [], CURRENT)
        second = authorize(self.root, copy.deepcopy(intent),
                           copy.deepcopy(manifest), [], CURRENT)
        self.assertEqual(first, second)

    def test_r2_with_one_valid_approval_allows(self):
        intent = self.intent("intent-r2-publish.json")
        result = authorize(self.root, intent, self.manifest_for(intent),
                           [approval("reviewer-1")], CURRENT)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["valid_approvers"], ["reviewer-1"])

    def test_r3_with_two_parties_and_dry_run_allows(self):
        intent = self.intent("intent-r3-authority.json")
        manifest = self.manifest_for(intent, extra_specs=[self.dry_run_spec()])
        result = authorize(self.root, intent, manifest,
                           [approval("reviewer-1"), approval("reviewer-2")],
                           CURRENT)
        self.assertEqual(result["decision"], "ALLOW")


class TestDenyPaths(GateFixtureCase):
    def test_invalid_intent_denies(self):
        intent = self.intent("intent-r2-publish.json")
        manifest = self.manifest_for(intent)
        intent["risk_class"] = "R0"  # under-classification
        result = authorize(self.root, intent, manifest,
                           [approval("reviewer-1")], CURRENT)
        self.assertEqual(result["decision"], "DENY")
        self.assertTrue(any("under-classification" in r
                            for r in result["reasons"]))

    def test_missing_evidence_manifest_denies(self):
        intent = self.intent("intent-r0-inspect.json")
        result = authorize(self.root, intent, None, [], CURRENT)
        self.assertEqual(result["decision"], "DENY")
        self.assertTrue(any("missing evidence manifest" in r
                            for r in result["reasons"]))

    def test_mismatched_evidence_never_allows(self):
        intent = self.intent("intent-r1-local-artifact.json")
        manifest = self.manifest_for(intent)
        artifact = os.path.join(self.root, "examples", "constitution",
                                "artifacts", "demo-test-log.txt")
        with open(artifact, "a", encoding="utf-8") as f:
            f.write("tampered\n")
        result = authorize(self.root, intent, manifest, [], CURRENT)
        self.assertEqual(result["decision"], "DENY")
        self.assertTrue(any("hash mismatch" in r for r in result["reasons"]))

    def test_evidence_bound_to_another_intent_denies(self):
        r1 = self.intent("intent-r1-local-artifact.json")
        r0 = self.intent("intent-r0-inspect.json")
        result = authorize(self.root, r0, self.manifest_for(r1), [], CURRENT)
        self.assertEqual(result["decision"], "DENY")
        self.assertTrue(any("intent binding mismatch" in r
                            for r in result["reasons"]))

    def test_self_approval_is_a_violation_not_a_wait(self):
        intent = self.intent("intent-r2-publish.json")
        result = authorize(self.root, intent, self.manifest_for(intent),
                           [approval("helix-runtime")], CURRENT)
        self.assertEqual(result["decision"], "DENY")
        self.assertTrue(any("separation of duties" in r
                            for r in result["reasons"]))


class TestRetireHumanSandbox(GateFixtureCase):
    def test_foreign_policy_version_retires(self):
        intent = self.intent("intent-r1-local-artifact.json")
        manifest = dict(self.manifest_for(intent))
        manifest["policy_version"] = "HELIX-CONSTITUTION/0.9"
        manifest = seal_manifest(manifest)
        result = authorize(self.root, intent, manifest, [], CURRENT)
        self.assertEqual(result["decision"], "RETIRE")
        self.assertTrue(any("re-issue" in r for r in result["reasons"]))

    def test_r2_without_approvals_waits_for_human(self):
        intent = self.intent("intent-r2-publish.json")
        result = authorize(self.root, intent, self.manifest_for(intent), [],
                           CURRENT)
        self.assertEqual(result["decision"], "HUMAN")
        self.assertTrue(any("insufficient human approvals" in r
                            for r in result["reasons"]))

    def test_expired_approval_is_renewal_not_violation(self):
        intent = self.intent("intent-r2-publish.json")
        result = authorize(self.root, intent, self.manifest_for(intent),
                           [approval("reviewer-1", anchor="b" * 64)], CURRENT)
        self.assertEqual(result["decision"], "HUMAN")
        self.assertTrue(any("expired" in r for r in result["reasons"]))

    def test_r3_missing_dry_run_waits_for_human(self):
        intent = self.intent("intent-r3-authority.json")
        result = authorize(self.root, intent, self.manifest_for(intent),
                           [approval("reviewer-1"), approval("reviewer-2")],
                           CURRENT)
        self.assertEqual(result["decision"], "HUMAN")
        self.assertTrue(any("dry-run evidence" in r for r in result["reasons"]))

    def test_external_only_evidence_is_sandboxed(self):
        intent = self.intent("intent-r1-local-artifact.json")
        manifest = self.manifest_for(intent, origin="external", reference=None)
        result = authorize(self.root, intent, manifest, [], CURRENT)
        self.assertEqual(result["decision"], "SANDBOX")
        self.assertTrue(any("thin evidence" in r for r in result["reasons"]))

    def test_approval_wait_precedes_sandbox(self):
        intent = self.intent("intent-r2-publish.json")
        manifest = self.manifest_for(intent, origin="external", reference=None)
        result = authorize(self.root, intent, manifest, [], CURRENT)
        self.assertEqual(result["decision"], "HUMAN")
        approved = authorize(self.root, intent, manifest,
                             [approval("reviewer-1")], CURRENT)
        self.assertEqual(approved["decision"], "SANDBOX")


class TestSchema(unittest.TestCase):
    def test_gate_result_schema_stays_in_stdlib_subset(self):
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema_features(schema), {"in_subset": True, "unsupported": []})


if __name__ == "__main__":
    unittest.main()
