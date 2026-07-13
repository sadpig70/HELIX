import unittest

import tests._path  # noqa: F401
from core.helix_owned_stakes import attest_owned_stakes
from core.helix_t4 import t4_verdict, verify_t4_seal
from core.helix_wedge_metrics import aggregate_pilot
from tests.test_pilot_aggregate import PilotFixtureCase


AUTHOR = "jung-wook-yang"


def owned_att(operator_id, org, ledger_head, count):
    return attest_owned_stakes(
        {"id": operator_id, "org": org}, AUTHOR,
        {"ledger_ref": f"{operator_id}/prod-handbacks",
         "ledger_head_sha256": ledger_head, "decision_count": count,
         "simulated": False},
        {"prevented_invalid": 1, "admitted": 2, "replay_verified": True},
        "bore real deploy-gate consequences on production handbacks")


PASSING_PERIOD = {"weeks": 0.25}  # 7 decisions / 0.25 = 28 >= 20
PASSING_SIDECAR = {"false_admits": {"team-a": 0, "team-b": 0, "team-c": 0},
                   "retained": ["team-a", "team-b"]}


class T4Fixture(PilotFixtureCase):
    def heads_and_counts(self, ledgers):
        rep = aggregate_pilot(self.root, ledgers)
        return {pid: (rep["per_participant"][pid]["ledger_head_sha256"],
                      rep["per_participant"][pid]["decisions_total"])
                for pid in ledgers}

    def independent_attestations(self, ledgers):
        hc = self.heads_and_counts(ledgers)
        orgs = {"team-a": ("op-a", "Acme"), "team-b": ("op-b", "Beacon"),
                "team-c": ("op-c", "Cobalt")}
        return {pid: owned_att(orgs[pid][0], orgs[pid][1], hc[pid][0], hc[pid][1])
                for pid in ledgers}

    def verdict(self, ledgers, attestations, **kw):
        params = dict(period=PASSING_PERIOD, sidecar=PASSING_SIDECAR)
        params.update(kw)
        return t4_verdict(self.root, ledgers, attestations, AUTHOR, **params)


class TestT4Passes(T4Fixture):
    def test_passes_when_metrics_and_independent_provenance_both_hold(self):
        ledgers = self.three_participants()
        v = self.verdict(ledgers, self.independent_attestations(ledgers))
        self.assertEqual(v["verdict"], "passed")
        self.assertEqual(v["metrics_verdict"], "passed")
        self.assertTrue(v["provenance_gate"]["pass"])
        self.assertEqual(v["provenance_gate"]["verified_independent"], 3)
        self.assertEqual(v["gaps"], [])
        self.assertTrue(verify_t4_seal(v))

    def test_deterministic_and_sealed(self):
        ledgers = self.three_participants()
        atts = self.independent_attestations(ledgers)
        self.assertEqual(self.verdict(ledgers, atts), self.verdict(ledgers, atts))


class TestT4FailsClosed(T4Fixture):
    def test_no_attestations_blocks_pass(self):
        ledgers = self.three_participants()
        v = self.verdict(ledgers, {})
        self.assertEqual(v["verdict"], "not_passed")
        self.assertEqual(v["provenance_gate"]["verified_independent"], 0)
        self.assertTrue(any("provenance" in g for g in v["gaps"]))

    def test_metrics_pass_but_provenance_missing_is_not_passed(self):
        # metrics gate would pass, but only one participant has an attestation
        ledgers = self.three_participants()
        atts = self.independent_attestations(ledgers)
        v = self.verdict(ledgers, {"team-a": atts["team-a"]})
        self.assertEqual(v["metrics_verdict"], "passed")
        self.assertEqual(v["verdict"], "not_passed")
        self.assertEqual(v["provenance_gate"]["verified_independent"], 1)

    def test_self_dealing_operator_is_rejected(self):
        # The attestation lies about who the author is (a decoy) so it builds and
        # grades real_owned_stakes, but the operator IS the real wedge author.
        # T4 cross-checks against the caller's TRUSTED author id and catches it.
        ledgers = self.three_participants()
        hc = self.heads_and_counts(ledgers)
        atts = self.independent_attestations(ledgers)
        atts["team-a"] = attest_owned_stakes(
            {"id": AUTHOR, "org": "Insider"}, "decoy-author",
            {"ledger_ref": "insider/prod", "ledger_head_sha256": hc["team-a"][0],
             "decision_count": hc["team-a"][1], "simulated": False},
            {"prevented_invalid": 1, "admitted": 2, "replay_verified": True},
            "insider self-use dressed up as owned stakes")
        v = self.verdict(ledgers, atts)
        self.assertFalse(v["provenance_gate"]["per_participant"]["team-a"]["verified"])
        self.assertTrue(any("self-dealing" in r for r in
                            v["provenance_gate"]["per_participant"]["team-a"]["reasons"]))

    def test_shared_operator_disqualifies_both(self):
        ledgers = self.three_participants()
        hc = self.heads_and_counts(ledgers)
        atts = self.independent_attestations(ledgers)
        # team-a and team-b are the SAME operator masquerading as two
        atts["team-a"] = owned_att("op-dup", "DupCo", hc["team-a"][0], hc["team-a"][1])
        atts["team-b"] = owned_att("op-dup", "DupCo", hc["team-b"][0], hc["team-b"][1])
        v = self.verdict(ledgers, atts)
        self.assertEqual(v["provenance_gate"]["verified_independent"], 1)  # only team-c
        self.assertEqual(v["verdict"], "not_passed")

    def test_ledger_head_binding_mismatch_is_rejected(self):
        ledgers = self.three_participants()
        hc = self.heads_and_counts(ledgers)
        atts = self.independent_attestations(ledgers)
        # team-c attests against team-a's ledger head -> not bound to its own work
        atts["team-c"] = owned_att("op-c", "Cobalt", hc["team-a"][0], hc["team-c"][1])
        v = self.verdict(ledgers, atts)
        self.assertFalse(v["provenance_gate"]["per_participant"]["team-c"]["verified"])
        self.assertTrue(any("real ledger head" in r for r in
                            v["provenance_gate"]["per_participant"]["team-c"]["reasons"]))

    def test_metrics_failure_blocks_pass_even_with_provenance(self):
        ledgers = self.three_participants()
        atts = self.independent_attestations(ledgers)
        # high false-admit -> metrics gate fails
        v = self.verdict(ledgers, atts,
                         sidecar={"false_admits": {"team-a": 3},
                                  "retained": ["team-a", "team-b"]})
        self.assertEqual(v["metrics_verdict"], "failed")
        self.assertEqual(v["verdict"], "not_passed")
        self.assertTrue(any("metrics" in g for g in v["gaps"]))

    def test_fewer_than_three_participants_cannot_pass(self):
        three = self.three_participants()
        two = {k: three[k] for k in ("team-a", "team-b")}
        atts = self.independent_attestations(two)
        v = self.verdict(two, atts, sidecar={"false_admits": {}, "retained": [
            "team-a", "team-b"]}, period={"weeks": 0.1})
        self.assertEqual(v["verdict"], "not_passed")
        self.assertFalse(v["provenance_gate"]["pass"])  # participants < 3


class TestT4Contract(T4Fixture):
    def test_wedge_author_id_is_required(self):
        ledgers = self.three_participants()
        with self.assertRaisesRegex(ValueError, "wedge_author_id"):
            t4_verdict(self.root, ledgers, {}, "  ")


if __name__ == "__main__":
    unittest.main()
