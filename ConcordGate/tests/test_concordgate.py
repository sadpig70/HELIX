import copy
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import concordgate as cg


def att(aid, org, subject="S1", **claims):
    return cg.seal_attestation({"attester": {"id": aid, "org": org},
                                "subject_id": subject, "claims": claims})


class TestAttestation(unittest.TestCase):
    def test_seal_is_deterministic(self):
        a = att("alice", "AuditCo", sha256="abc", signed=True)
        b = att("alice", "AuditCo", sha256="abc", signed=True)
        self.assertEqual(a["attestation_sha256"], b["attestation_sha256"])
        self.assertTrue(cg.verify_attestation_seal(a))

    def test_missing_org_rejected(self):
        with self.assertRaisesRegex(ValueError, "org"):
            cg.seal_attestation({"attester": {"id": "x", "org": ""},
                                 "subject_id": "S1", "claims": {"k": 1}})

    def test_empty_claims_rejected(self):
        with self.assertRaisesRegex(ValueError, "claims"):
            cg.seal_attestation({"attester": {"id": "x", "org": "O"},
                                 "subject_id": "S1", "claims": {}})

    def test_tampered_attestation_fails_seal(self):
        a = copy.deepcopy(att("alice", "AuditCo", sha256="abc"))
        a["claims"]["sha256"] = "def"
        self.assertFalse(cg.verify_attestation_seal(a))


class TestReconcile(unittest.TestCase):
    def test_two_independent_orgs_agree_is_concordant(self):
        rec = cg.reconcile([att("alice", "AuditCo", sha256="abc", signed=True),
                            att("bob", "ReproLab", sha256="abc", signed=True)])
        self.assertEqual(rec["verdict"], "CONCORDANT")
        self.assertEqual(rec["independent_source_count"], 2)
        self.assertEqual(rec["conflicts"], [])
        self.assertTrue(cg.verify_reconciliation_seal(rec))

    def test_cross_source_disagreement_is_split(self):
        rec = cg.reconcile([att("alice", "AuditCo", sha256="abc"),
                            att("bob", "ReproLab", sha256="def")])
        self.assertEqual(rec["verdict"], "SPLIT")
        self.assertTrue(any(c["kind"] == "cross-source" and c["field"] == "sha256"
                            for c in rec["conflicts"]))

    def test_single_org_repeated_is_insufficient(self):
        # two attestations, same org -> one independent source
        rec = cg.reconcile([att("alice", "AuditCo", sha256="abc"),
                            att("alice2", "AuditCo", sha256="abc")])
        self.assertEqual(rec["verdict"], "INSUFFICIENT")
        self.assertEqual(rec["independent_source_count"], 1)

    def test_same_org_self_contradiction_is_split(self):
        # one org, two members disagreeing -> same-source split (still <quorum, but
        # conflict is surfaced); use quorum=1 so verdict resolves to SPLIT
        rec = cg.reconcile([att("alice", "AuditCo", sha256="abc"),
                            att("alice2", "AuditCo", sha256="def")], quorum=1)
        self.assertEqual(rec["verdict"], "SPLIT")
        self.assertTrue(any(c["kind"] == "same-source" for c in rec["conflicts"]))

    def test_quorum_of_three_reached(self):
        rec = cg.reconcile([att("a", "O1", k=1), att("b", "O2", k=1),
                            att("c", "O3", k=1)], quorum=3)
        self.assertEqual(rec["verdict"], "CONCORDANT")
        self.assertEqual(rec["independent_source_count"], 3)

    def test_broken_seal_is_excluded(self):
        good = att("a", "O1", k=1)
        bad = copy.deepcopy(att("b", "O2", k=1))
        bad["claims"]["k"] = 2  # tamper without resealing
        rec = cg.reconcile([good, bad])
        self.assertEqual(rec["attestations_considered"], 1)
        self.assertTrue(any("seal is broken" in p for p in rec["problems"]))
        self.assertEqual(rec["verdict"], "INSUFFICIENT")

    def test_foreign_subject_is_excluded(self):
        rec = cg.reconcile([att("a", "O1", subject="S1", k=1),
                            att("b", "O2", subject="S2", k=1)], subject_id="S1")
        self.assertEqual(rec["attestations_considered"], 1)
        self.assertTrue(any("not 'S1'" in p or "not \'S1\'" in p
                            for p in rec["problems"]))

    def test_multiple_subjects_without_scope_is_refused(self):
        rec = cg.reconcile([att("a", "O1", subject="S1", k=1),
                            att("b", "O2", subject="S2", k=1)])
        self.assertTrue(any("multiple subjects" in p for p in rec["problems"]))
        self.assertEqual(rec["verdict"], "INSUFFICIENT")

    def test_partial_field_overlap_concordant_on_shared(self):
        rec = cg.reconcile([att("a", "O1", sha256="abc", signed=True),
                            att("b", "O2", sha256="abc")])
        self.assertEqual(rec["verdict"], "CONCORDANT")

    def test_reconcile_is_deterministic(self):
        atts = [att("a", "O1", k=1), att("b", "O2", k=1)]
        self.assertEqual(cg.reconcile(atts), cg.reconcile(atts))


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="concord-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ledger = "_cg/ledger.jsonl"

    def test_append_and_verify_roundtrip(self):
        for shas in (("abc", "abc"), ("abc", "def")):
            rec = cg.reconcile([att("a", "O1", sha256=shas[0]),
                                att("b", "O2", sha256=shas[1])])
            cg.append_ledger(self.root, self.ledger, rec)
        self.assertEqual(len(cg.read_ledger(self.root, self.ledger)), 2)
        self.assertEqual(cg.verify_ledger(self.root, self.ledger), [])

    def test_tampered_ledger_line_is_detected(self):
        rec = cg.reconcile([att("a", "O1", k=1), att("b", "O2", k=1)])
        cg.append_ledger(self.root, self.ledger, rec)
        path = os.path.join(self.root, "_cg", "ledger.jsonl")
        data = open(path, encoding="utf-8").read().replace("CONCORDANT", "SPLIT")
        open(path, "w", encoding="utf-8", newline="\n").write(data)
        self.assertTrue(cg.verify_ledger(self.root, self.ledger))


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="concord-cli-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_sample_run_report_roundtrip(self):
        import json
        sample = cg._sample()
        p = os.path.join(self.root, "atts.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(sample, f)
        # sample has a cross-source split on sha256 -> exit 3
        rc = cg.main(["--root", self.root, "run", "--attestations", p,
                      "--ledger", "_cg/l.jsonl"])
        self.assertEqual(rc, 3)
        rc_report = cg.main(["--root", self.root, "report", "--ledger", "_cg/l.jsonl"])
        self.assertEqual(rc_report, 0)


if __name__ == "__main__":
    unittest.main()
