import copy
import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_admission import (
    admit_projects,
    build_admission_receipt,
    classify_admission,
    issue_migration_flag,
    verify_admission_receipt_seal,
)
from engines.exploit.adapter import registry_admissions, registry_to_ledger


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
STALE = "b" * 64


def migration_flag(anchor=CURRENT):
    return issue_migration_flag("legacy entries pending handback backfill",
                                anchor, "operator-1")


class TestClassification(unittest.TestCase):
    def test_verdicts_map_fail_closed(self):
        cases = (("valid", "ADMIT"), ("thin", "SANDBOX_ONLY"),
                 ("breach", "EXCLUDED"), (None, "QUARANTINE"),
                 ("weird", "QUARANTINE"))
        for verdict, expected in cases:
            with self.subTest(verdict=verdict):
                decision = classify_admission(verdict)
                self.assertEqual(decision["admission"], expected)
                self.assertFalse(decision["migration_applied"])

    def test_absent_without_flag_is_unconditionally_quarantined(self):
        decision = classify_admission(None, migration=None,
                                      current_state_receipt_hash=CURRENT)
        self.assertEqual(decision["admission"], "QUARANTINE")
        self.assertIn("fail_closed", decision["basis"])


class TestMigrationFlag(unittest.TestCase):
    def test_live_flag_grants_legacy_admit_for_absent_only(self):
        flag = migration_flag()
        absent = classify_admission(None, flag, CURRENT)
        self.assertEqual(absent["admission"], "ADMIT")
        self.assertTrue(absent["migration_applied"])
        for verdict, expected in (("thin", "SANDBOX_ONLY"),
                                  ("breach", "EXCLUDED")):
            with self.subTest(verdict=verdict):
                decision = classify_admission(verdict, flag, CURRENT)
                self.assertEqual(decision["admission"], expected)
                self.assertFalse(decision["migration_applied"])

    def test_state_drift_expires_the_flag(self):
        flag = migration_flag(anchor=STALE)
        decision = classify_admission(None, flag, CURRENT)
        self.assertEqual(decision["admission"], "QUARANTINE")

    def test_tampered_flag_grants_nothing(self):
        flag = dict(migration_flag())
        flag["reason"] = "edited after issue"  # seal broken
        decision = classify_admission(None, flag, CURRENT)
        self.assertEqual(decision["admission"], "QUARANTINE")

    def test_flag_issue_is_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "reason"):
            issue_migration_flag(" ", CURRENT, "op-1")
        with self.assertRaisesRegex(ValueError, "anchor"):
            issue_migration_flag("r", "", "op-1")
        with self.assertRaisesRegex(ValueError, "issuer"):
            issue_migration_flag("r", CURRENT, " ")


class TestReceipts(unittest.TestCase):
    def test_receipt_is_sealed_and_deterministic(self):
        first = build_admission_receipt("ProjA", "valid",
                                        current_state_receipt_hash=CURRENT)
        second = build_admission_receipt("ProjA", "valid",
                                         current_state_receipt_hash=CURRENT)
        self.assertEqual(first, second)
        self.assertTrue(verify_admission_receipt_seal(first))
        self.assertEqual(first["admission"], "ADMIT")
        tampered = copy.deepcopy(first)
        tampered["admission"] = "EXCLUDED"
        self.assertFalse(verify_admission_receipt_seal(tampered))

    def test_migration_receipt_records_the_flag_chain(self):
        flag = migration_flag()
        receipt = build_admission_receipt("Legacy", None, flag, CURRENT)
        self.assertEqual(receipt["admission"], "ADMIT")
        self.assertTrue(receipt["migration_applied"])
        self.assertEqual(receipt["migration_flag_sha256"], flag["flag_sha256"])

    def test_admit_projects_summary(self):
        result = admit_projects({"A": "valid", "B": "thin", "C": "breach",
                                 "D": None}, None, CURRENT)
        self.assertEqual(result["summary"],
                         {"ADMIT": 1, "SANDBOX_ONLY": 1, "QUARANTINE": 1,
                          "EXCLUDED": 1})
        self.assertEqual(result["receipts"]["D"]["admission"], "QUARANTINE")


class TestAdapterIntegration(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "examples", "exploit_state",
                               "registry.json"), encoding="utf-8") as f:
            self.registry = json.load(f)

    def test_absent_legacy_entry_is_quarantined_without_flag(self):
        result = registry_admissions(self.registry,
                                     current_state_receipt_hash=CURRENT)
        receipt = result["receipts"]["WithheldActionWitness"]
        self.assertEqual(receipt["admission"], "QUARANTINE")
        self.assertIsNone(receipt["handback_verdict"])

    def test_migration_flag_temporarily_admits_the_same_entry(self):
        result = registry_admissions(self.registry, migration_flag(), CURRENT)
        receipt = result["receipts"]["WithheldActionWitness"]
        self.assertEqual(receipt["admission"], "ADMIT")
        self.assertTrue(receipt["migration_applied"])

    def test_persisted_verdicts_flow_through(self):
        registry = copy.deepcopy(self.registry)
        gp = registry["generated_projects"]
        gp["BreachedProj"] = {"status": "implemented",
                              "handback_verdict": "breach"}
        gp["ThinProj"] = {"status": "implemented", "handback_verdict": "thin"}
        result = registry_admissions(registry,
                                     current_state_receipt_hash=CURRENT)
        self.assertEqual(result["receipts"]["BreachedProj"]["admission"],
                         "EXCLUDED")
        self.assertEqual(result["receipts"]["ThinProj"]["admission"],
                         "SANDBOX_ONLY")
        self.assertEqual(result["summary"]["QUARANTINE"], 1)

    def test_existing_ledger_path_is_unchanged(self):
        # The documented backward-compatible fail-open ledger behavior stays
        # as-is until P4_5 switches consumption to admission classes: the
        # absent-verdict legacy entry is still consumed, with no gate count.
        ledger = registry_to_ledger(self.registry)
        titles = [e["title"] for e in ledger["consumed"]]
        self.assertIn("WithheldActionWitness", titles)
        self.assertEqual(ledger["_handback_gate"],
                         {"checked": 0, "passed": 0, "excluded": 0})


if __name__ == "__main__":
    unittest.main()
