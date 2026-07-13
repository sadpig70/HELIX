import copy
import unittest

import tests._path  # noqa: F401
from core.helix_adoption_trial import aggregate_adoption, build_adoption_receipt
from core.helix_fidelity import (
    attest_fidelity,
    attestation_grade,
    build_persona_source,
    capture_reproduction,
    earn_provenance,
    verify_attestation,
    verify_sample,
    verify_source,
)


def persona(pid="dev-ari", interest="ship reliable services with a small on-call "
            "rotation and low review overhead"):
    return {"persona_id": pid, "interest_function": interest,
            "constraints": ["two-person team"]}


def judgment(decision="reject"):
    return {"decision": decision,
            "reasons": ["packet authoring costs more than it saves my team"],
            "defects_found": (["trace.digest contract unintuitive"]
                              if decision == "reject" else [])}


def source(pid="dev-ari"):
    return build_persona_source(pid, [
        {"ref": "decision-log-2026Q2", "sha256": "a" * 64},
        {"ref": "stated-priority-oncall", "sha256": "b" * 64},
    ])


AGENT = "ai-runtime-subagent-7"


class TestPersonaSource(unittest.TestCase):
    def test_seal_is_deterministic(self):
        self.assertEqual(source()["source_sha256"], source()["source_sha256"])
        self.assertTrue(verify_source(source()))

    def test_empty_refs_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            build_persona_source("dev-ari", [])

    def test_ref_missing_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "ref and sha256"):
            build_persona_source("dev-ari", [{"ref": "x", "sha256": ""}])


class TestReproduction(unittest.TestCase):
    def test_capture_and_verify(self):
        s = capture_reproduction(persona(), judgment(), AGENT)
        self.assertTrue(verify_sample(s))
        self.assertEqual(s["reproduction_agent"], AGENT)
        self.assertEqual(s["decision"], "reject")

    def test_reproduction_needs_reasons(self):
        with self.assertRaisesRegex(ValueError, "not reviewable"):
            capture_reproduction(persona(), {"decision": "adopt", "reasons": []},
                                 AGENT)

    def test_reproduction_needs_agent(self):
        with self.assertRaisesRegex(ValueError, "reproduction_agent"):
            capture_reproduction(persona(), judgment(), "  ")


class TestAttestation(unittest.TestCase):
    def setUp(self):
        self.src = source()
        self.sample = capture_reproduction(persona(), judgment(), AGENT)
        self.attester = {"id": "jung-wook-yang", "role": "the real developer"}

    def attest(self, verdict="faithful", **kw):
        return attest_fidelity(self.src, self.sample, self.attester, verdict, **kw)

    def test_faithful_attestation_verifies(self):
        a = self.attest()
        self.assertTrue(verify_attestation(a))
        self.assertEqual(a["verdict"], "faithful")
        self.assertEqual(a["sample_sha256"], self.sample["sample_sha256"])

    def test_attester_cannot_be_reproduction_agent(self):
        self.attester = {"id": AGENT, "role": "self"}
        with self.assertRaisesRegex(ValueError, "own reproduction"):
            self.attest()

    def test_bad_verdict_rejected(self):
        with self.assertRaisesRegex(ValueError, "verdict must be"):
            self.attest(verdict="mostly")

    def test_empty_attester_rejected(self):
        self.attester = {"id": "  ", "role": "x"}
        with self.assertRaisesRegex(ValueError, "named real person"):
            self.attest()

    def test_source_sample_persona_mismatch_rejected(self):
        other = capture_reproduction(persona(pid="someone-else"), judgment(), AGENT)
        with self.assertRaisesRegex(ValueError, "different personas"):
            attest_fidelity(self.src, other, self.attester, "faithful")

    def test_conflict_of_interest_is_recorded(self):
        a = self.attest(conflict_of_interest="attester is the wedge author (dogfooding)")
        self.assertIn("dogfooding", a["conflict_of_interest"])


class TestGrading(unittest.TestCase):
    def setUp(self):
        self.src = source()
        self.sample = capture_reproduction(persona(), judgment(), AGENT)
        self.attester = {"id": "jung-wook-yang", "role": "real developer"}

    def test_faithful_earns_fidelity_attested(self):
        a = attest_fidelity(self.src, self.sample, self.attester, "faithful")
        self.assertEqual(attestation_grade(self.sample, a), "fidelity_attested")

    def test_partial_earns_nothing(self):
        a = attest_fidelity(self.src, self.sample, self.attester, "partial")
        self.assertEqual(attestation_grade(self.sample, a), "simulated_unverified")

    def test_tampered_attestation_earns_nothing(self):
        a = attest_fidelity(self.src, self.sample, self.attester, "faithful")
        a = copy.deepcopy(a)
        a["verdict"] = "faithful"  # unchanged, but reseal not recomputed below
        a["reservations"] = ["secretly injected"]  # tamper without resealing
        self.assertEqual(attestation_grade(self.sample, a), "simulated_unverified")

    def test_attestation_for_a_different_sample_earns_nothing(self):
        a = attest_fidelity(self.src, self.sample, self.attester, "faithful")
        other = capture_reproduction(persona(), judgment("adopt"), AGENT)
        self.assertEqual(attestation_grade(other, a), "simulated_unverified")


class TestIntegrationWithAdoptionTrial(unittest.TestCase):
    def setUp(self):
        self.src = source()
        self.sample = capture_reproduction(persona(), judgment("adopt"), AGENT)
        self.attester = {"id": "jung-wook-yang", "role": "real developer"}
        self.att = attest_fidelity(self.src, self.sample, self.attester, "faithful",
                                   conflict_of_interest="wedge author (dogfooding)")

    def receipt(self):
        prov = earn_provenance(self.sample, self.att)
        return build_adoption_receipt(
            persona(), {"decision": "adopt", "reasons": ["fits my workflow"]}, prov)

    def test_earned_receipt_carries_binding_and_grade(self):
        r = self.receipt()
        self.assertEqual(r["provenance"]["grade"], "fidelity_attested")
        self.assertEqual(r["provenance"]["sample_sha256"],
                         self.sample["sample_sha256"])
        self.assertEqual(r["provenance"]["attestation_sha256"],
                         self.att["attestation_sha256"])

    def test_aggregate_honors_backed_claim(self):
        agg = aggregate_adoption([self.receipt()], attestations=[self.att])
        self.assertEqual(agg["by_provenance_grade"]["fidelity_attested"], 1)
        self.assertEqual(agg["problems"], [])

    def test_aggregate_downgrades_unbacked_claim(self):
        # a receipt claiming fidelity_attested but no attestation supplied
        agg = aggregate_adoption([self.receipt()], attestations=[])
        self.assertEqual(agg["by_provenance_grade"]["fidelity_attested"], 0)
        self.assertEqual(agg["by_provenance_grade"]["simulated_unverified"], 1)
        self.assertTrue(any("downgraded" in p for p in agg["problems"]))

    def test_fidelity_attested_is_still_not_t4_utility(self):
        agg = aggregate_adoption([self.receipt()], attestations=[self.att])
        self.assertFalse(agg["verdict"]["is_t4_utility"])
        self.assertEqual(agg["verdict"]["kind"], "conditional_adoption_simulated")
        self.assertEqual(agg["utility_eligible_receipts"], 0)

    def test_none_attestations_keeps_recorded_grade(self):
        agg = aggregate_adoption([self.receipt()])  # backward-compatible path
        self.assertEqual(agg["by_provenance_grade"]["fidelity_attested"], 1)


if __name__ == "__main__":
    unittest.main()
