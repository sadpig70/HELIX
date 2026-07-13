import copy
import unittest

import tests._path  # noqa: F401
from core.helix_adoption_trial import aggregate_adoption, build_adoption_receipt
from core.helix_owned_stakes import (
    attest_owned_stakes,
    earn_owned_provenance,
    owned_stakes_grade,
    verify_owned_stakes_attestation,
)


AUTHOR = "jung-wook-yang"
HEX = "c" * 64


def operator(oid="external-team-acme", org="Acme Corp"):
    return {"id": oid, "org": org}


def real_work(count=12, simulated=False):
    return {"ledger_ref": "acme/prod-handbacks-week1",
            "ledger_head_sha256": HEX, "decision_count": count,
            "simulated": simulated}


def outcomes(replay=True):
    return {"prevented_invalid": 3, "admitted": 8, "excluded": 3,
            "replay_verified": replay}


def attest(**kw):
    params = dict(operator=operator(), wedge_author_id=AUTHOR,
                  real_work=real_work(), outcomes=outcomes(),
                  stakes_owned="blocked a real invalid deploy handback in prod")
    params.update(kw)
    return attest_owned_stakes(**params)


def persona(pid="external-ops"):
    return {"persona_id": pid,
            "interest_function": "keep production deploys reversible with low "
                                 "operational toil",
            "constraints": ["regulated environment"]}


class TestIndependence(unittest.TestCase):
    def test_operator_equal_to_author_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "independent of the wedge author"):
            attest(operator=operator(oid=AUTHOR))

    def test_empty_operator_rejected(self):
        with self.assertRaisesRegex(ValueError, "operator.id"):
            attest(operator=operator(oid="  "))

    def test_missing_author_rejected(self):
        with self.assertRaisesRegex(ValueError, "wedge_author_id"):
            attest(wedge_author_id="")


class TestRealWork(unittest.TestCase):
    def test_simulated_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not simulated"):
            attest(real_work=real_work(simulated=True))

    def test_zero_decisions_rejected(self):
        with self.assertRaisesRegex(ValueError, "decision_count"):
            attest(real_work=real_work(count=0))

    def test_bad_ledger_head_rejected(self):
        rw = real_work()
        rw["ledger_head_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "ledger head"):
            attest(real_work=rw)


class TestOutcomes(unittest.TestCase):
    def test_replay_not_verified_rejected(self):
        with self.assertRaisesRegex(ValueError, "replay_verified"):
            attest(outcomes=outcomes(replay=False))

    def test_sentiment_only_outcomes_rejected(self):
        with self.assertRaisesRegex(ValueError, "objective measure"):
            attest(outcomes={"felt_great": True, "replay_verified": True})

    def test_negative_measure_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            attest(outcomes={"prevented_invalid": -1, "replay_verified": True})

    def test_empty_stakes_rejected(self):
        with self.assertRaisesRegex(ValueError, "stakes_owned"):
            attest(stakes_owned="  ")


class TestGrading(unittest.TestCase):
    def test_valid_independent_earns_real_owned_stakes(self):
        a = attest()
        self.assertTrue(verify_owned_stakes_attestation(a))
        self.assertEqual(owned_stakes_grade(a), "real_owned_stakes")

    def test_tampered_earns_nothing(self):
        a = copy.deepcopy(attest())
        a["outcomes"]["prevented_invalid"] = 999  # tamper without resealing
        self.assertEqual(owned_stakes_grade(a), "simulated_unverified")

    def test_earn_provenance_has_real_stakes(self):
        prov = earn_owned_provenance(attest())
        self.assertEqual(prov["grade"], "real_owned_stakes")
        self.assertEqual(prov["stakes"], "real")
        self.assertEqual(prov["attested_by"], "external-team-acme")


class TestIntegrationWithAdoptionTrial(unittest.TestCase):
    def setUp(self):
        self.att = attest()
        self.prov = earn_owned_provenance(self.att)

    def receipt(self):
        return build_adoption_receipt(
            persona(), {"decision": "adopt",
                        "reasons": ["cut our handback review time materially"]},
            self.prov)

    def test_backed_claim_is_t4_utility_eligible(self):
        agg = aggregate_adoption([self.receipt()], attestations=[self.att])
        self.assertEqual(agg["by_provenance_grade"]["real_owned_stakes"], 1)
        self.assertTrue(agg["verdict"]["is_t4_utility"])
        self.assertEqual(agg["verdict"]["kind"], "utility_candidate")
        self.assertEqual(agg["problems"], [])

    def test_unbacked_claim_is_downgraded_and_not_utility(self):
        agg = aggregate_adoption([self.receipt()], attestations=[])
        self.assertEqual(agg["by_provenance_grade"]["real_owned_stakes"], 0)
        self.assertEqual(agg["by_provenance_grade"]["simulated_unverified"], 1)
        self.assertFalse(agg["verdict"]["is_t4_utility"])
        self.assertTrue(any("fabricate a T4 utility signal" in p
                            for p in agg["problems"]))

    def test_none_attestations_keeps_recorded_grade(self):
        agg = aggregate_adoption([self.receipt()])  # backward compatible
        self.assertTrue(agg["verdict"]["is_t4_utility"])


if __name__ == "__main__":
    unittest.main()
