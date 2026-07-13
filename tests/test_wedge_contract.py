import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_actuator import (
    read_actuation_ledger,
    verify_actuation_chain,
    verify_actuation_ledger,
)
from core.helix_admission import issue_migration_flag
from core.helix_wedge import (
    audit_handback,
    verify_wedge_decision,
    verify_wedge_seal,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
LEDGER = "_wedge/ledger.jsonl"
PACKETS = "_wedge/packets"
OPERATOR = {"kind": "human", "id": "operator-1"}


def load_packet():
    with open(os.path.join(ROOT, "examples", "exploit_state",
                           "handback_packet.json"), encoding="utf-8") as f:
        return json.load(f)


class WedgeFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-wedge-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        # the wedge re-verifies packets with the vendored AHV from the repo root
        shutil.copytree(os.path.join(ROOT, "ActionHandbackVerifier", "src"),
                        os.path.join(self.root, "ActionHandbackVerifier", "src"))
        self.packet = load_packet()

    def audit(self, packet=None, operator=None, migration=None,
              evidence_root=None, evidence_required=False,
              provenance_class="real"):
        return audit_handback(self.root,
                              packet if packet is not None else self.packet,
                              operator or OPERATOR, CURRENT, LEDGER, PACKETS,
                              migration=migration, evidence_root=evidence_root,
                              evidence_required=evidence_required,
                              provenance_class=provenance_class)


class TestWedgeDecision(WedgeFixtureCase):
    def test_valid_packet_is_admitted_with_a_full_receipt_chain(self):
        result = self.audit()
        decision = result["decision"]
        self.assertEqual(decision["handback_verdict"], "valid")
        self.assertEqual(decision["admission"], "ADMIT")
        self.assertEqual(decision["gate_decision"], "SANDBOX")  # external packet
        self.assertEqual(decision["gate_result_sha256"],
                         result["gate"]["result_sha256"])
        self.assertEqual(decision["admission_receipt_sha256"],
                         result["admission_receipt"]["receipt_sha256"])
        self.assertTrue(verify_wedge_seal(decision))
        self.assertEqual(verify_wedge_decision(self.root, decision), [])

    def test_thin_packet_is_sandboxed(self):
        packet = copy.deepcopy(self.packet)
        del packet["trace"]
        decision = self.audit(packet)["decision"]
        self.assertEqual(decision["handback_verdict"], "thin")
        self.assertEqual(decision["admission"], "SANDBOX_ONLY")

    def test_breach_packet_is_excluded(self):
        packet = copy.deepcopy(self.packet)
        del packet["custody"]
        decision = self.audit(packet)["decision"]
        self.assertEqual(decision["handback_verdict"], "breach")
        self.assertEqual(decision["admission"], "EXCLUDED")

    def test_decision_is_deterministic_for_the_same_packet(self):
        first = self.audit()["decision"]
        second = self.audit()["decision"]
        self.assertEqual(first, second)

    def test_packet_is_stored_content_addressed(self):
        decision = self.audit()["decision"]
        full = os.path.join(self.root, *decision["packet_path"].split("/"))
        self.assertTrue(os.path.isfile(full))
        self.assertIn(decision["packet_sha256"], decision["packet_path"])

    def test_metric_marker_counts_toward_the_north_star(self):
        decision = self.audit()["decision"]
        self.assertEqual(decision["metric"],
                         {"kind": "admission_decision",
                          "counts_toward": "weekly_real_admission_decisions"})

    def test_refuses_empty_packet_and_blank_operator(self):
        with self.assertRaisesRegex(ValueError, "requires a submitted"):
            self.audit(packet={})
        with self.assertRaisesRegex(ValueError, "operator.id"):
            self.audit(operator={"kind": "human", "id": "  "})

    def test_provenance_is_sealed_and_fails_closed(self):
        real = self.audit(provenance_class="real")["decision"]
        self.assertEqual(real["provenance_class"], "real")
        self.assertEqual(real["metric"]["counts_toward"],
                         "weekly_real_admission_decisions")

        synthetic = self.audit(provenance_class="synthetic")["decision"]
        self.assertEqual(synthetic["provenance_class"], "synthetic")
        self.assertIsNone(synthetic["metric"]["counts_toward"])
        self.assertEqual(synthetic["metric"]["excluded_reason"],
                         "provenance:synthetic")

        unclassified = self.audit(provenance_class=None)["decision"]
        self.assertEqual(unclassified["provenance_class"], "unclassified")
        self.assertIsNone(unclassified["metric"]["counts_toward"])
        with self.assertRaisesRegex(ValueError, "provenance_class"):
            self.audit(provenance_class="external")

    def test_migration_flag_is_irrelevant_for_submitted_packets(self):
        flag = issue_migration_flag("legacy grace", CURRENT, "op-1")
        packet = copy.deepcopy(self.packet)
        del packet["custody"]
        decision = self.audit(packet, migration=flag)["decision"]
        self.assertEqual(decision["admission"], "EXCLUDED")


class TestEvidenceTruth(WedgeFixtureCase):
    """Persona-trial fix: a 'valid' packet whose evidence does not exist must
    not silently earn ADMIT when evidence verification is required."""

    def write_evidence(self, packet):
        """Materialize every cited evidence file under an evidence root."""
        root = os.path.join(self.root, "_evidence")
        for pred in ("delegation", "custody", "route", "rollback", "trace"):
            path = (packet.get(pred) or {}).get("evidence_path")
            if not path:
                continue
            full = os.path.join(root, *path.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write("{}\n")
        return "_evidence"

    def test_present_evidence_keeps_admit(self):
        evroot = self.write_evidence(self.packet)
        result = self.audit(evidence_root=evroot, evidence_required=True)
        d = result["decision"]
        self.assertEqual(d["evidence_check"]["status"], "verified")
        self.assertEqual(d["admission"], "ADMIT")
        self.assertFalse(d["evidence_check"]["downgraded"])
        self.assertEqual(verify_wedge_decision(self.root, d), [])

    def test_missing_evidence_downgrades_admit_to_sandbox(self):
        # valid packet, but no evidence files exist -> unverified -> SANDBOX
        result = self.audit(evidence_root="_evidence_absent",
                            evidence_required=True)
        d = result["decision"]
        self.assertEqual(d["handback_verdict"], "valid")
        self.assertEqual(d["effective_verdict"], "thin")
        self.assertEqual(d["evidence_check"]["status"], "unverified")
        self.assertTrue(d["evidence_check"]["downgraded"])
        self.assertEqual(d["admission"], "SANDBOX_ONLY")
        self.assertEqual(verify_wedge_decision(self.root, d), [])

    def test_unverified_without_required_flag_stays_admit_but_recorded(self):
        result = self.audit(evidence_root="_evidence_absent",
                            evidence_required=False)
        d = result["decision"]
        self.assertEqual(d["evidence_check"]["status"], "unverified")
        self.assertFalse(d["evidence_check"]["downgraded"])
        self.assertEqual(d["admission"], "ADMIT")  # opt-in; recorded not forced

    def test_no_evidence_root_is_honestly_not_provided(self):
        d = self.audit()["decision"]  # backward-compatible default
        self.assertEqual(d["evidence_check"]["status"], "not_provided")
        self.assertEqual(d["admission"], "ADMIT")


class TestWedgeLedger(WedgeFixtureCase):
    def test_every_audit_lands_in_the_chained_ledger(self):
        self.audit()
        thin = copy.deepcopy(self.packet)
        del thin["trace"]
        self.audit(thin)
        entries = read_actuation_ledger(self.root, LEDGER)
        self.assertEqual([e["kind"] for e in entries],
                         ["gate", "wedge_decision", "gate", "wedge_decision"])
        self.assertEqual(verify_actuation_ledger(self.root, LEDGER), [])
        self.assertEqual(verify_actuation_chain(self.root, LEDGER), [])


class TestReplay(WedgeFixtureCase):
    def test_tampered_decision_breaks_the_seal(self):
        decision = self.audit()["decision"]
        forged = copy.deepcopy(decision)
        forged["admission"] = "ADMIT"
        forged["handback_verdict"] = "valid"
        forged["decision_id"] = "WD-FORGED"
        problems = verify_wedge_decision(self.root, forged)
        self.assertTrue(any("seal is broken" in p for p in problems), problems)

    def test_tampered_stored_packet_is_not_replayable(self):
        decision = self.audit()["decision"]
        full = os.path.join(self.root, *decision["packet_path"].split("/"))
        with open(full, "a", encoding="utf-8") as f:
            f.write("tampered\n")
        problems = verify_wedge_decision(self.root, decision)
        self.assertTrue(any("do not match" in p for p in problems), problems)

    def test_laundered_verdict_fails_the_replay(self):
        packet = copy.deepcopy(self.packet)
        del packet["custody"]  # breach
        decision = self.audit(packet)["decision"]
        laundered = {k: v for k, v in decision.items() if k != "receipt_sha256"}
        laundered["handback_verdict"] = "valid"
        laundered["admission"] = "ADMIT"
        import hashlib
        from core.helix_holdout import canonical_json_bytes
        laundered["receipt_sha256"] = hashlib.sha256(
            canonical_json_bytes(laundered)).hexdigest()
        problems = verify_wedge_decision(self.root, laundered)
        self.assertTrue(any("verdict does not replay" in p for p in problems),
                        problems)

    def test_provenance_metric_mismatch_fails_replay(self):
        decision = self.audit(provenance_class="real")["decision"]
        forged = {k: v for k, v in decision.items() if k != "receipt_sha256"}
        forged["provenance_class"] = "synthetic"
        import hashlib
        from core.helix_holdout import canonical_json_bytes
        forged["receipt_sha256"] = hashlib.sha256(
            canonical_json_bytes(forged)).hexdigest()
        self.assertIn("metric marker does not match provenance_class",
                      verify_wedge_decision(self.root, forged))


if __name__ == "__main__":
    unittest.main()
