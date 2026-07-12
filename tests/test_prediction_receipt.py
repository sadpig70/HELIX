import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_holdout import validate_registry
from core.helix_prediction import (
    apply_prediction_receipt,
    apply_reveal_receipt,
    build_prediction_receipt,
    build_reveal_receipt,
    verify_receipt_chain,
    verify_trial_receipt_seal,
)
from core.helix_schema import schema_features
from scripts.evaluate.build_synthetic_holdout import generate


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "helix-trial-receipt.schema.json")
PREDICTION = {"outcome": "PREDICT", "action": "BUILD_ON_PLATFORM", "machines": ["M2"]}
APPROVALS = [{"approver_id": "approver-1", "role": "reveal_approver"}]


class PredictionFixtureCase(unittest.TestCase):
    """Locked live-size registry in a temp tree, plus the trial-receipt schema."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-prediction-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("helix-holdout-registry", "helix-trial-receipt"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        self.registry = generate(self.root)
        self.cid = "SYN-001"

    def sealed(self, prediction=None, cid=None):
        cid = cid or self.cid
        receipt = build_prediction_receipt(
            self.root, self.registry, cid, prediction or PREDICTION)
        rel = f"_holdout/predictions/{cid}.json"
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            json.dump(receipt, f, ensure_ascii=False, indent=2)
        updated = apply_prediction_receipt(self.registry, receipt, rel)
        return receipt, updated


class TestPredictionSeal(PredictionFixtureCase):
    def test_same_input_produces_the_same_seal(self):
        first = build_prediction_receipt(self.root, self.registry, self.cid, PREDICTION)
        second = build_prediction_receipt(self.root, self.registry, self.cid, PREDICTION)
        self.assertEqual(first, second)
        self.assertTrue(verify_trial_receipt_seal(first))

    def test_receipt_is_chained_to_the_cohort_commitment_and_view_hash(self):
        receipt, _ = self.sealed()
        commitment = self.registry["cohort"]["commitment_sha256"]
        candidate = next(c for c in self.registry["candidates"]
                         if c["candidate_id"] == self.cid)
        self.assertEqual(receipt["cohort_commitment_sha256"], commitment)
        self.assertEqual(receipt["parent_receipt_sha256"], commitment)
        self.assertEqual(receipt["prediction"]["candidate_view_sha256"],
                         candidate["candidate_view"]["sha256"])

    def test_sealing_updates_the_registry_without_breaking_the_lock(self):
        receipt, updated = self.sealed()
        candidate = next(c for c in updated["candidates"]
                         if c["candidate_id"] == self.cid)
        self.assertEqual(candidate["prediction_receipt"]["status"], "sealed")
        self.assertEqual(candidate["prediction_receipt"]["sha256"],
                         receipt["receipt_sha256"])
        self.assertEqual(validate_registry(self.root, updated), [])

    def test_double_seal_is_refused(self):
        receipt, updated = self.sealed()
        with self.assertRaisesRegex(ValueError, "already sealed"):
            build_prediction_receipt(self.root, updated, self.cid, PREDICTION)
        with self.assertRaisesRegex(ValueError, "already sealed"):
            apply_prediction_receipt(updated, receipt, "_holdout/predictions/x.json")

    def test_excluded_candidate_cannot_be_predicted(self):
        with self.assertRaisesRegex(ValueError, "excluded"):
            build_prediction_receipt(self.root, self.registry,
                                     "SYN-KNOWN-HASH", PREDICTION)

    def test_prediction_after_reveal_is_refused(self):
        doc = copy.deepcopy(self.registry)
        candidate = next(c for c in doc["candidates"]
                         if c["candidate_id"] == self.cid)
        candidate["oracle_commitment"]["access"] = "revealed"
        with self.assertRaisesRegex(ValueError, "would not be blind"):
            build_prediction_receipt(self.root, doc, self.cid, PREDICTION)

    def test_tampered_registry_cannot_seal_predictions(self):
        doc = copy.deepcopy(self.registry)
        doc["cohort"]["selection_rule"] = "changed after lock"
        with self.assertRaisesRegex(ValueError, "commitment mismatch"):
            build_prediction_receipt(self.root, doc, self.cid, PREDICTION)

    def test_drifted_candidate_view_is_refused(self):
        candidate = next(c for c in self.registry["candidates"]
                         if c["candidate_id"] == self.cid)
        view_full = os.path.join(self.root,
                                 *candidate["candidate_view"]["path"].split("/"))
        with open(view_full, "a", encoding="utf-8") as f:
            f.write("drift\n")
        with self.assertRaisesRegex(ValueError, "drifted"):
            build_prediction_receipt(self.root, self.registry, self.cid, PREDICTION)

    def test_abstain_is_an_explicit_sealed_outcome_without_labels(self):
        receipt, updated = self.sealed(
            {"outcome": "ABSTAIN", "action": None, "machines": None})
        self.assertEqual(receipt["prediction"]["outcome"], "ABSTAIN")
        self.assertIsNone(receipt["prediction"]["action"])
        self.assertEqual(validate_registry(self.root, updated), [])
        with self.assertRaisesRegex(ValueError, "must not carry"):
            build_prediction_receipt(
                self.root, self.registry, "SYN-002",
                {"outcome": "ABSTAIN", "action": "DEFER", "machines": None})

    def test_predict_requires_action_and_machines(self):
        for bad in ({"outcome": "PREDICT", "action": None, "machines": ["M1"]},
                    {"outcome": "PREDICT", "action": "DEFER", "machines": None},
                    {"outcome": "SURE", "action": "DEFER", "machines": []}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build_prediction_receipt(self.root, self.registry, self.cid, bad)


class TestRevealApproval(PredictionFixtureCase):
    def test_reveal_before_sealed_prediction_is_refused(self):
        with self.assertRaisesRegex(ValueError, "reveal before sealed prediction"):
            build_reveal_receipt(self.root, self.registry, self.cid, APPROVALS)

    def test_reveal_requires_enough_distinct_allowed_approvers(self):
        _, updated = self.sealed()
        with self.assertRaisesRegex(ValueError, "insufficient reveal approvals"):
            build_reveal_receipt(self.root, updated, self.cid, [])
        with self.assertRaisesRegex(ValueError, "cannot approve"):
            build_reveal_receipt(self.root, updated, self.cid,
                                 [{"approver_id": "p-1", "role": "predictor"}])
        with self.assertRaisesRegex(ValueError, "duplicate approver"):
            build_reveal_receipt(self.root, updated, self.cid, APPROVALS + APPROVALS)

    def test_reveal_is_denied_when_oracle_drifts_from_commitment(self):
        _, updated = self.sealed()
        candidate = next(c for c in updated["candidates"]
                         if c["candidate_id"] == self.cid)
        oracle_full = os.path.join(self.root,
                                   *candidate["oracle_commitment"]["path"].split("/"))
        with open(oracle_full, "a", encoding="utf-8") as f:
            f.write("post-hoc oracle edit\n")
        with self.assertRaisesRegex(ValueError, "reveal denied"):
            build_reveal_receipt(self.root, updated, self.cid, APPROVALS)

    def test_approved_reveal_chains_to_the_sealed_prediction(self):
        prediction_receipt, updated = self.sealed()
        reveal_receipt = build_reveal_receipt(self.root, updated, self.cid, APPROVALS)
        self.assertEqual(reveal_receipt["parent_receipt_sha256"],
                         prediction_receipt["receipt_sha256"])
        self.assertTrue(verify_trial_receipt_seal(reveal_receipt))
        revealed = apply_reveal_receipt(updated, reveal_receipt)
        candidate = next(c for c in revealed["candidates"]
                         if c["candidate_id"] == self.cid)
        self.assertEqual(candidate["reveal"]["status"], "revealed")
        self.assertEqual(candidate["oracle_commitment"]["access"], "revealed")
        self.assertEqual(candidate["reveal"]["authorized_by"], ["approver-1"])
        self.assertEqual(validate_registry(self.root, revealed), [])


class TestReceiptChainVerification(PredictionFixtureCase):
    def make_chain(self):
        prediction_receipt, updated = self.sealed()
        reveal_receipt = build_reveal_receipt(self.root, updated, self.cid, APPROVALS)
        revealed = apply_reveal_receipt(updated, reveal_receipt)
        return prediction_receipt, reveal_receipt, revealed

    def test_honest_chain_verifies(self):
        prediction_receipt, reveal_receipt, revealed = self.make_chain()
        self.assertEqual(verify_receipt_chain(
            self.root, revealed, prediction_receipt, reveal_receipt), [])

    def test_tampered_prediction_content_breaks_the_seal(self):
        prediction_receipt, reveal_receipt, revealed = self.make_chain()
        tampered = copy.deepcopy(prediction_receipt)
        tampered["prediction"]["action"] = "CONDENSE"
        problems = verify_receipt_chain(self.root, revealed, tampered, reveal_receipt)
        self.assertTrue(any("seal is broken" in p for p in problems), problems)

    def test_reveal_from_another_prediction_breaks_the_chain(self):
        prediction_receipt, reveal_receipt, revealed = self.make_chain()
        foreign = copy.deepcopy(reveal_receipt)
        foreign["parent_receipt_sha256"] = "0" * 64
        foreign["reveal"]["prediction_receipt_sha256"] = "0" * 64
        from core.helix_prediction import seal_trial_receipt
        foreign = seal_trial_receipt(foreign)
        problems = verify_receipt_chain(self.root, revealed, prediction_receipt, foreign)
        self.assertTrue(any("not chained to the sealed prediction" in p
                            for p in problems), problems)

    def test_registry_revealed_without_receipt_is_flagged(self):
        prediction_receipt, reveal_receipt, revealed = self.make_chain()
        problems = verify_receipt_chain(self.root, revealed, prediction_receipt)
        self.assertTrue(any("no reveal receipt given" in p for p in problems), problems)

    def test_schema_stays_in_stdlib_subset_and_accepts_receipts(self):
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema_features(schema), {"in_subset": True, "unsupported": []})
        prediction_receipt, reveal_receipt, revealed = self.make_chain()
        self.assertEqual(verify_receipt_chain(
            self.root, revealed, prediction_receipt, reveal_receipt), [])


if __name__ == "__main__":
    unittest.main()
