import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_authorization import authorize
from core.helix_contestability import (
    effective_decision,
    file_appeal,
    file_override,
    replay_gate_result,
    verify_appeal_seal,
    verify_override_seal,
)
from core.helix_evidence import build_evidence_manifest
from core.helix_stop_token import issue_stop_token


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
HUMAN = {"kind": "human", "id": "operator-2"}


class ContestFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-contest-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(os.path.join(ROOT, "examples", "constitution"),
                        os.path.join(self.root, "examples", "constitution"))
        with open(os.path.join(self.root, "examples", "constitution",
                               "intent-r1-local-artifact.json"),
                  encoding="utf-8") as f:
            self.intent = json.load(f)
        self.manifest = build_evidence_manifest(
            self.root, "EVM-CONTEST-001", self.intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output",
                             "reference": "python -m unittest"}}])
        self.result = self.gate()

    def gate(self, **kwargs):
        return authorize(self.root, self.intent, self.manifest, [], CURRENT,
                         **kwargs)

    def replay(self, stored=None, **kwargs):
        return replay_gate_result(self.root, stored or self.result,
                                  self.intent, self.manifest, [], CURRENT,
                                  **kwargs)


class TestReplay(ContestFixtureCase):
    def test_honest_replay_matches_seal_for_seal(self):
        outcome = self.replay()
        self.assertTrue(outcome["replayed"], outcome["problems"])
        self.assertEqual(outcome["stored_result_sha256"],
                         outcome["fresh_result_sha256"])

    def test_replay_covers_stop_token_inputs(self):
        token = issue_stop_token("STOP-R", {"kind": "human", "id": "op-1"},
                                 "freeze", {"kind": "global"}, CURRENT)
        stored = self.gate(stop_tokens=[token])
        self.assertEqual(stored["decision"], "DENY")
        outcome = replay_gate_result(self.root, stored, self.intent,
                                     self.manifest, [], CURRENT,
                                     stop_tokens=[token])
        self.assertTrue(outcome["replayed"], outcome["problems"])

    def test_tampered_stored_result_is_reported(self):
        tampered = copy.deepcopy(self.result)
        tampered["decision"] = "DENY"
        outcome = self.replay(stored=tampered)
        self.assertFalse(outcome["replayed"])
        self.assertTrue(any("seal is broken" in p for p in outcome["problems"]))

    def test_changed_evidence_bytes_diverge_on_replay(self):
        artifact = os.path.join(self.root, "examples", "constitution",
                                "artifacts", "demo-test-log.txt")
        with open(artifact, "a", encoding="utf-8") as f:
            f.write("tampered\n")
        outcome = self.replay()
        self.assertFalse(outcome["replayed"])
        self.assertTrue(any("replay divergence: decision" in p
                            for p in outcome["problems"]))

    def test_foreign_inputs_are_not_a_replay(self):
        with open(os.path.join(self.root, "examples", "constitution",
                               "intent-r0-inspect.json"), encoding="utf-8") as f:
            other_intent = json.load(f)
        outcome = replay_gate_result(self.root, self.result, other_intent,
                                     self.manifest, [], CURRENT)
        self.assertFalse(outcome["replayed"])
        self.assertTrue(any("inputs differ: intent" in p
                            for p in outcome["problems"]))


class TestAppeal(ContestFixtureCase):
    def test_appeal_is_sealed_chained_and_changes_nothing(self):
        original = copy.deepcopy(self.result)
        appeal = file_appeal(self.result, {"kind": "ai", "id": "helix-runtime"},
                             "decision seems overly strict")
        self.assertTrue(verify_appeal_seal(appeal))
        self.assertEqual(appeal["gate_result_sha256"],
                         self.result["result_sha256"])
        self.assertEqual(appeal["contested_decision"], self.result["decision"])
        self.assertEqual(self.result, original)

    def test_appeal_requires_reason_and_appellant(self):
        with self.assertRaisesRegex(ValueError, "reason"):
            file_appeal(self.result, {"kind": "ai", "id": "x"}, "  ")
        with self.assertRaisesRegex(ValueError, "appellant.id"):
            file_appeal(self.result, {"kind": "ai", "id": ""}, "why")

    def test_cannot_appeal_a_tampered_result(self):
        tampered = copy.deepcopy(self.result)
        tampered["decision"] = "DENY"
        with self.assertRaisesRegex(ValueError, "tampered"):
            file_appeal(tampered, {"kind": "ai", "id": "x"}, "why")


class TestOverride(ContestFixtureCase):
    def test_valid_override_is_sealed_and_original_stays_intact(self):
        original = copy.deepcopy(self.result)
        override = file_override(self.result, HUMAN, "operator judgment",
                                 "DENY", CURRENT)
        self.assertTrue(verify_override_seal(override))
        self.assertEqual(override["original_decision"], "ALLOW")
        self.assertEqual(override["new_decision"], "DENY")
        self.assertEqual(self.result, original)

    def test_reasonless_override_cannot_exist(self):
        with self.assertRaisesRegex(ValueError, "reason-less override"):
            file_override(self.result, HUMAN, "   ", "DENY", CURRENT)

    def test_only_humans_override(self):
        with self.assertRaisesRegex(ValueError, "only a human"):
            file_override(self.result, {"kind": "ai", "id": "agent"},
                          "why", "DENY", CURRENT)

    def test_override_must_change_the_decision(self):
        with self.assertRaisesRegex(ValueError, "must change the decision"):
            file_override(self.result, HUMAN, "why", self.result["decision"],
                          CURRENT)

    def test_override_requires_anchor_and_valid_decision(self):
        with self.assertRaisesRegex(ValueError, "state-receipt anchor"):
            file_override(self.result, HUMAN, "why", "DENY", " ")
        with self.assertRaisesRegex(ValueError, "new_decision"):
            file_override(self.result, HUMAN, "why", "MAYBE", CURRENT)

    def test_cannot_override_a_tampered_result(self):
        tampered = copy.deepcopy(self.result)
        tampered["decision"] = "DENY"
        with self.assertRaisesRegex(ValueError, "tampered"):
            file_override(tampered, HUMAN, "why", "SANDBOX", CURRENT)


class TestEffectiveDecision(ContestFixtureCase):
    def test_gate_decision_stands_without_overrides(self):
        outcome = effective_decision(self.result, [])
        self.assertEqual(outcome, {"decision": "ALLOW", "source": "gate",
                                   "problems": []})

    def test_valid_override_applies(self):
        override = file_override(self.result, HUMAN, "why", "DENY", CURRENT)
        outcome = effective_decision(self.result, [override])
        self.assertEqual(outcome["decision"], "DENY")
        self.assertEqual(outcome["source"], "override")

    def test_invalid_override_applies_nothing_but_is_reported(self):
        override = file_override(self.result, HUMAN, "why", "DENY", CURRENT)
        forged = copy.deepcopy(override)
        forged["new_decision"] = "SANDBOX"  # seal broken
        outcome = effective_decision(self.result, [forged])
        self.assertEqual(outcome["decision"], "ALLOW")
        self.assertEqual(outcome["source"], "gate")
        self.assertTrue(any("invalid" in p for p in outcome["problems"]))

    def test_conflicting_overrides_fail_closed_to_deny(self):
        deny = file_override(self.result, HUMAN, "too risky", "DENY", CURRENT)
        sandbox = file_override(self.result,
                                {"kind": "human", "id": "operator-3"},
                                "sandbox instead", "SANDBOX", CURRENT)
        outcome = effective_decision(self.result, [deny, sandbox])
        self.assertEqual(outcome["decision"], "DENY")
        self.assertEqual(outcome["source"], "conflict")
        self.assertTrue(any("conflicting overrides" in p
                            for p in outcome["problems"]))

    def test_override_for_a_different_result_applies_nothing(self):
        token = issue_stop_token("STOP-X", {"kind": "human", "id": "op-1"},
                                 "freeze", {"kind": "global"}, CURRENT)
        other_result = self.gate(stop_tokens=[token])
        override = file_override(other_result, HUMAN, "lift for this one",
                                 "ALLOW", CURRENT)
        outcome = effective_decision(self.result, [override])
        self.assertEqual(outcome["decision"], "ALLOW")
        self.assertEqual(outcome["source"], "gate")
        self.assertTrue(outcome["problems"])


if __name__ == "__main__":
    unittest.main()
