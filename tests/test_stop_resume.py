import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_authorization import authorize
from core.helix_evidence import build_evidence_manifest
from core.helix_stop_token import (
    active_stops,
    blocking_stops,
    issue_resume_receipt,
    issue_stop_token,
    verify_resume_receipt_seal,
    verify_stop_token_seal,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
ISSUER = {"kind": "human", "id": "operator-1"}


def resume_approval(approver_id, anchor=CURRENT):
    return {"approver_id": approver_id, "kind": "human",
            "anchor": {"state_receipt_hash": anchor}}


def global_stop(token_id="STOP-001", issuer=None):
    return issue_stop_token(token_id, issuer or ISSUER,
                            "diversity breach under investigation",
                            {"kind": "global"}, CURRENT)


def path_stop(prefixes, token_id="STOP-P-001"):
    return issue_stop_token(token_id, ISSUER, "scoped freeze",
                            {"kind": "path_prefix", "prefixes": prefixes},
                            CURRENT)


def write_intent(paths=("out/report.json",), publish=False, remote=False):
    return {
        "schema": "helix-action-intent/1.0",
        "intent_id": "INT-STOP-TEST", "title": "test write",
        "proposer": {"kind": "ai", "id": "helix-runtime"},
        "risk_class": "R2",
        "scope": {"write_paths": list(paths), "remote_mutation": remote,
                  "publish": publish},
        "impact": {"authority": False, "economic": False, "physical": False,
                   "broad_public": False},
        "reversibility": {"reversible": False, "rollback_plan": None},
        "budget": {"max_files": 5, "max_bytes": 1024},
        "justification": "stop/resume integration test",
    }


def read_only_intent():
    intent = write_intent(paths=())
    intent["risk_class"] = "R0"
    intent["reversibility"] = {"reversible": True,
                               "rollback_plan": "read-only"}
    intent["budget"] = {"max_files": 0, "max_bytes": 0}
    return intent


class TestIssue(unittest.TestCase):
    def test_issued_token_is_sealed(self):
        token = global_stop()
        self.assertTrue(verify_stop_token_seal(token))
        self.assertEqual(token["scope"], {"kind": "global", "prefixes": None})

    def test_issue_refuses_malformed_inputs(self):
        cases = (
            (lambda: issue_stop_token(" ", ISSUER, "r", {"kind": "global"}, CURRENT),
             "token_id"),
            (lambda: issue_stop_token("T", {"id": ""}, "r", {"kind": "global"}, CURRENT),
             "issuer.id"),
            (lambda: issue_stop_token("T", ISSUER, "  ", {"kind": "global"}, CURRENT),
             "reason"),
            (lambda: issue_stop_token("T", ISSUER, "r", {"kind": "global"}, ""),
             "anchor"),
            (lambda: issue_stop_token("T", ISSUER, "r", {"kind": "everything"}, CURRENT),
             "scope.kind"),
            (lambda: issue_stop_token("T", ISSUER, "r",
                                      {"kind": "path_prefix", "prefixes": []}, CURRENT),
             "prefixes"),
            (lambda: issue_stop_token("T", ISSUER, "r",
                                      {"kind": "global", "prefixes": ["x"]}, CURRENT),
             "must not carry prefixes"),
        )
        for factory, message in cases:
            with self.subTest(message=message), \
                    self.assertRaisesRegex(ValueError, message):
                factory()


class TestBlocking(unittest.TestCase):
    def test_global_stop_blocks_any_side_effect(self):
        token = global_stop()
        for intent in (write_intent(), write_intent(paths=(), publish=True),
                       write_intent(paths=(), remote=True)):
            self.assertEqual(len(blocking_stops(intent, [token], [])), 1)

    def test_read_only_intent_passes_even_under_global_stop(self):
        self.assertEqual(blocking_stops(read_only_intent(), [global_stop()], []),
                         [])

    def test_path_prefix_stop_blocks_matching_writes_only(self):
        token = path_stop(["seed/evaluation/"])
        hit = write_intent(paths=("seed/evaluation/t1-holdout-registry.json",))
        miss = write_intent(paths=("_workspace/notes.md",))
        self.assertEqual(len(blocking_stops(hit, [token], [])), 1)
        self.assertEqual(blocking_stops(miss, [token], []), [])

    def test_path_prefix_stop_does_not_block_remote_or_publish(self):
        token = path_stop(["seed/"])
        intent = write_intent(paths=(), publish=True)
        self.assertEqual(blocking_stops(intent, [token], []), [])

    def test_tampered_token_keeps_blocking(self):
        token = dict(global_stop())
        token["reason"] = "softened after the fact"  # seal now broken
        self.assertFalse(verify_stop_token_seal(token))
        self.assertEqual(len(blocking_stops(write_intent(), [token], [])), 1)


class TestResume(unittest.TestCase):
    def setUp(self):
        self.token = global_stop()

    def test_separate_authority_resume_lifts_the_stop(self):
        receipt = issue_resume_receipt(self.token, [resume_approval("operator-2")],
                                       "incident resolved", CURRENT)
        self.assertTrue(verify_resume_receipt_seal(receipt))
        self.assertEqual(receipt["stop_token_sha256"], self.token["token_sha256"])
        self.assertEqual(active_stops([self.token], [receipt]), [])
        self.assertEqual(blocking_stops(write_intent(), [self.token], [receipt]),
                         [])

    def test_issuer_cannot_resume_their_own_stop(self):
        with self.assertRaisesRegex(ValueError, "cannot resume their own stop"):
            issue_resume_receipt(self.token, [resume_approval("operator-1")],
                                 "self resume", CURRENT)
        with self.assertRaisesRegex(ValueError, "cannot resume their own stop"):
            issue_resume_receipt(
                self.token,
                [resume_approval("operator-2"), resume_approval("operator-1")],
                "issuer among approvers", CURRENT)

    def test_resume_approval_rules_are_fail_closed(self):
        cases = (
            ([], "insufficient resume approvals"),
            ([resume_approval("  ")], "approver_id"),
            ([{"approver_id": "op-2", "kind": "ai",
               "anchor": {"state_receipt_hash": CURRENT}}], "only humans"),
            ([resume_approval("op-2"), resume_approval("op-2")], "duplicate"),
            ([resume_approval("op-2", anchor="b" * 64)], "anchored to the current"),
        )
        for approvals, message in cases:
            with self.subTest(message=message), \
                    self.assertRaisesRegex(ValueError, message):
                issue_resume_receipt(self.token, approvals, "r", CURRENT)

    def test_resume_requires_a_reason(self):
        with self.assertRaisesRegex(ValueError, "reason"):
            issue_resume_receipt(self.token, [resume_approval("op-2")], " ",
                                 CURRENT)

    def test_two_party_resume_when_required(self):
        with self.assertRaisesRegex(ValueError, "insufficient resume approvals"):
            issue_resume_receipt(self.token, [resume_approval("op-2")], "r",
                                 CURRENT, required_approvals=2)
        receipt = issue_resume_receipt(
            self.token, [resume_approval("op-2"), resume_approval("op-3")],
            "r", CURRENT, required_approvals=2)
        self.assertEqual(active_stops([self.token], [receipt]), [])

    def test_tampered_token_cannot_be_resumed(self):
        tampered = dict(self.token)
        tampered["scope"] = {"kind": "path_prefix", "prefixes": ["nowhere/"]}
        with self.assertRaisesRegex(ValueError, "tampered stop"):
            issue_resume_receipt(tampered, [resume_approval("op-2")], "r", CURRENT)

    def test_tampered_resume_receipt_lifts_nothing(self):
        receipt = issue_resume_receipt(self.token, [resume_approval("op-2")],
                                       "r", CURRENT)
        forged = copy.deepcopy(receipt)
        forged["reason"] = "edited"
        self.assertEqual(active_stops([self.token], [forged]), [self.token])

    def test_resume_for_another_token_lifts_nothing(self):
        other = global_stop(token_id="STOP-OTHER")
        receipt = issue_resume_receipt(other, [resume_approval("op-2")], "r",
                                       CURRENT)
        self.assertEqual(active_stops([self.token], [receipt]), [self.token])


class TestGateIntegration(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-stopgate-")
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
            self.root, "EVM-STOP-001", self.intent,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output",
                             "reference": "python -m unittest"}}])

    def gate(self, tokens=None, receipts=None, intent=None):
        return authorize(self.root, intent or self.intent, self.manifest, [],
                         CURRENT, stop_tokens=tokens, resume_receipts=receipts)

    def test_stop_turns_an_allow_into_deny(self):
        self.assertEqual(self.gate()["decision"], "ALLOW")
        result = self.gate(tokens=[global_stop()])
        self.assertEqual(result["decision"], "DENY")
        self.assertTrue(any("stopped: token STOP-001" in r
                            for r in result["reasons"]))

    def test_read_only_intent_still_allows_under_stop(self):
        with open(os.path.join(self.root, "examples", "constitution",
                               "intent-r0-inspect.json"), encoding="utf-8") as f:
            r0 = json.load(f)
        manifest = build_evidence_manifest(
            self.root, "EVM-STOP-R0", r0,
            {"kind": "system", "id": "helix-runtime"},
            [{"role": "test_log",
              "path": "examples/constitution/artifacts/demo-test-log.txt",
              "provenance": {"origin": "command_output",
                             "reference": "python -m unittest"}}])
        result = authorize(self.root, r0, manifest, [], CURRENT,
                           stop_tokens=[global_stop()])
        self.assertEqual(result["decision"], "ALLOW")

    def test_resume_restores_allow(self):
        token = global_stop()
        receipt = issue_resume_receipt(token, [resume_approval("operator-2")],
                                       "resolved", CURRENT)
        result = self.gate(tokens=[token], receipts=[receipt])
        self.assertEqual(result["decision"], "ALLOW")

    def test_unrelated_path_stop_does_not_deny(self):
        token = path_stop(["seed/evaluation/"])
        self.assertEqual(self.gate(tokens=[token])["decision"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
