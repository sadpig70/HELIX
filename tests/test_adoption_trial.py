import copy
import unittest

import tests._path  # noqa: F401
from core.helix_adoption_trial import (
    aggregate_adoption,
    build_adoption_receipt,
    validate_persona,
    verify_adoption_seal,
)


def persona(pid="ops-lead", interest="minimize regulatory compliance cost "
            "while keeping deploy velocity high"):
    return {"persona_id": pid, "interest_function": interest,
            "constraints": ["small team", "audited quarterly"]}


SIM = {"grade": "simulated_unverified", "attested_by": None, "stakes": "simulated"}


class TestPersonaIndependence(unittest.TestCase):
    def test_wedge_independent_interest_is_valid(self):
        self.assertEqual(validate_persona(persona()), [])

    def test_interest_mentioning_the_wedge_is_rejected(self):
        for coupled in ("I want to adopt the wedge",
                        "loves the helix admission gate",
                        "needs audit-handback tooling"):
            with self.subTest(coupled=coupled):
                problems = validate_persona(persona(interest=coupled))
                self.assertTrue(any("independently of the wedge" in p
                                    for p in problems), problems)

    def test_empty_interest_is_rejected(self):
        self.assertTrue(any("interest_function" in p
                            for p in validate_persona(persona(interest="  "))))


class TestReceipt(unittest.TestCase):
    def test_reject_is_a_valid_sealed_judgment(self):
        judgment = {"decision": "reject",
                    "reasons": ["too much packet-authoring overhead for my team"],
                    "defects_found": ["trace.digest contract is unintuitive"]}
        r = build_adoption_receipt(persona(), judgment, SIM)
        self.assertEqual(r["decision"], "reject")
        self.assertEqual(r["provenance"]["grade"], "simulated_unverified")
        self.assertTrue(verify_adoption_seal(r))

    def test_judgment_without_reasons_is_refused(self):
        with self.assertRaisesRegex(ValueError, "without reasons"):
            build_adoption_receipt(persona(), {"decision": "adopt", "reasons": []},
                                   SIM)

    def test_bad_decision_and_grade_are_refused(self):
        with self.assertRaisesRegex(ValueError, "decision must be"):
            build_adoption_receipt(persona(), {"decision": "maybe",
                                               "reasons": ["x"]}, SIM)
        with self.assertRaisesRegex(ValueError, "grade must be"):
            build_adoption_receipt(persona(), {"decision": "adopt",
                                               "reasons": ["x"]},
                                   {"grade": "totally_real"})

    def test_non_simulated_grade_requires_an_attester(self):
        with self.assertRaisesRegex(ValueError, "named attester"):
            build_adoption_receipt(persona(), {"decision": "adopt",
                                               "reasons": ["x"]},
                                   {"grade": "fidelity_attested",
                                    "attested_by": ""})
        r = build_adoption_receipt(
            persona(), {"decision": "adopt", "reasons": ["fits my workflow"]},
            {"grade": "fidelity_attested", "attested_by": "dev-x", "stakes": "simulated"})
        self.assertEqual(r["provenance"]["attested_by"], "dev-x")

    def test_persona_mentioning_wedge_cannot_get_a_receipt(self):
        with self.assertRaisesRegex(ValueError, "invalid persona"):
            build_adoption_receipt(persona(interest="wants the wedge"),
                                   {"decision": "adopt", "reasons": ["x"]}, SIM)


class TestAggregationHonesty(unittest.TestCase):
    def receipts(self, specs):
        out = []
        for pid, decision, grade, attester in specs:
            prov = {"grade": grade, "attested_by": attester,
                    "stakes": "real" if grade == "real_owned_stakes" else "simulated"}
            out.append(build_adoption_receipt(
                persona(pid=pid), {"decision": decision,
                                   "reasons": [f"{pid} reason"],
                                   "defects_found": (["d"] if decision == "reject"
                                                     else [])}, prov))
        return out

    def test_simulated_only_is_not_a_t4_verdict(self):
        rs = self.receipts([("a", "adopt", "simulated_unverified", None),
                            ("b", "adopt", "simulated_unverified", None),
                            ("c", "reject", "simulated_unverified", None)])
        agg = aggregate_adoption(rs)
        self.assertEqual(agg["total_personas"], 3)
        self.assertEqual(agg["by_decision"]["adopt"], 2)
        self.assertEqual(agg["rejections"], 1)
        self.assertFalse(agg["verdict"]["is_t4_utility"])
        self.assertEqual(agg["verdict"]["kind"], "conditional_adoption_simulated")
        self.assertEqual(agg["utility_eligible_receipts"], 0)

    def test_rejections_surface_defects(self):
        rs = self.receipts([("a", "reject", "simulated_unverified", None)])
        agg = aggregate_adoption(rs)
        self.assertEqual(agg["defects_found"], [{"persona": "a", "defect": "d"}])

    def test_real_owned_stakes_makes_it_utility_eligible(self):
        rs = self.receipts([("a", "adopt", "real_owned_stakes", "external-team-1")])
        agg = aggregate_adoption(rs)
        self.assertTrue(agg["verdict"]["is_t4_utility"])
        self.assertEqual(agg["verdict"]["kind"], "utility_candidate")

    def test_tampered_receipt_is_excluded(self):
        rs = self.receipts([("a", "adopt", "simulated_unverified", None)])
        tampered = copy.deepcopy(rs[0])
        tampered["decision"] = "reject"
        agg = aggregate_adoption([tampered])
        self.assertEqual(agg["total_personas"], 0)
        self.assertTrue(agg["problems"])


if __name__ == "__main__":
    unittest.main()
