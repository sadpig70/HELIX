import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_holdout import validate_registry
from core.helix_prediction import score_cohort, verify_receipt_chain
from scripts.evaluate.blind_machine_trial import (
    abstain_baseline,
    constant_baseline,
    run_blind_trial,
    run_trial,
)
from scripts.evaluate.build_synthetic_holdout import generate


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPROVALS = [{"approver_id": "approver-test-1", "role": "reveal_approver"}]


def perfect_predictor(view):
    """Test scaffolding: reproduces the synthetic oracle rule from the view id."""
    index = int(view["candidate_id"].split("-")[1])
    return {"outcome": "PREDICT",
            "action": "BUILD_ON_PLATFORM" if index % 2 else "DEFER",
            "machines": [f"M{(index % 15) + 1}"]}


class BlindRunnerCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-blind-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("helix-holdout-registry", "helix-trial-receipt",
                     "helix-reduction-receipt"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        self.registry = generate(self.root)

    def run_system(self, predictor, receipts_rel="_trial/receipts"):
        revealed, chains = run_trial(self.root, self.registry, predictor,
                                     APPROVALS, receipts_rel)
        return revealed, chains, score_cohort(self.root, revealed, chains)


class TestScoring(BlindRunnerCase):
    def test_perfect_predictor_passes_both_gates(self):
        revealed, _, metrics = self.run_system(perfect_predictor)
        self.assertEqual(metrics["denominator"], 20)
        self.assertEqual(metrics["counts"]["exact"], 20)
        self.assertEqual(metrics["coverage"], 1.0)
        self.assertEqual(metrics["macro_f1"], 1.0)
        self.assertTrue(metrics["gates"]["coverage_pass"])
        self.assertTrue(metrics["gates"]["macro_f1_pass"])
        self.assertEqual(validate_registry(self.root, revealed), [])

    def test_constant_baseline_reports_honest_failure(self):
        _, _, metrics = self.run_system(constant_baseline)
        self.assertEqual(metrics["denominator"], 20)
        self.assertEqual(metrics["coverage"], 1.0)
        self.assertLess(metrics["counts"]["exact"], 3)
        self.assertFalse(metrics["gates"]["macro_f1_pass"])

    def test_abstain_gets_zero_coverage_and_zero_credit(self):
        _, _, metrics = self.run_system(abstain_baseline)
        self.assertEqual(metrics["counts"]["abstain"], 20)
        self.assertEqual(metrics["coverage"], 0.0)
        self.assertEqual(metrics["success_rate"], 0.0)
        self.assertEqual(metrics["denominator"], 20)
        self.assertFalse(metrics["gates"]["coverage_pass"])

    def test_missing_artifact_stays_in_the_denominator(self):
        victim = next(c for c in self.registry["candidates"]
                      if c["status"] != "excluded")
        os.remove(os.path.join(self.root,
                               *victim["candidate_view"]["path"].split("/")))
        _, _, metrics = self.run_system(perfect_predictor)
        self.assertEqual(metrics["denominator"], 20)
        self.assertEqual(metrics["counts"]["missing_artifact"], 1)
        self.assertEqual(metrics["counts"]["exact"], 19)
        self.assertEqual(metrics["coverage"], 19 / 20)

    def test_protocol_violation_stays_in_the_denominator(self):
        revealed, chains, _ = self.run_system(perfect_predictor)
        tampered = copy.deepcopy(chains)
        victim = sorted(tampered)[0]
        tampered[victim]["prediction"]["prediction"]["action"] = "CONDENSE"
        metrics = score_cohort(self.root, revealed, tampered)
        self.assertEqual(metrics["denominator"], 20)
        self.assertEqual(metrics["counts"]["protocol_violation"], 1)
        self.assertEqual(metrics["counts"]["exact"], 19)

    def test_missing_prediction_chain_is_counted_not_dropped(self):
        revealed, chains, _ = self.run_system(perfect_predictor)
        victim = sorted(chains)[0]
        del chains[victim]
        metrics = score_cohort(self.root, revealed, chains)
        self.assertEqual(metrics["denominator"], 20)
        self.assertEqual(metrics["counts"]["missing_prediction"], 1)


class TestHarness(BlindRunnerCase):
    def test_trial_is_deterministic(self):
        report_a = run_blind_trial(self.root, self.registry,
                                   {"perfect": perfect_predictor,
                                    "baseline-abstain": abstain_baseline},
                                   APPROVALS, "_trial/run-a")
        report_b = run_blind_trial(self.root, self.registry,
                                   {"perfect": perfect_predictor,
                                    "baseline-abstain": abstain_baseline},
                                   APPROVALS, "_trial/run-b")
        self.assertEqual(json.dumps(report_a, sort_keys=True),
                         json.dumps(report_b, sort_keys=True))

    def test_systems_are_compared_on_the_same_locked_cohort(self):
        report = run_blind_trial(self.root, self.registry,
                                 {"perfect": perfect_predictor,
                                  "baseline-constant": constant_baseline},
                                 APPROVALS, "_trial/compare")
        self.assertEqual(report["cohort_commitment_sha256"],
                         self.registry["cohort"]["commitment_sha256"])
        self.assertEqual(set(report["systems"]), {"perfect", "baseline-constant"})
        denominators = {m["denominator"] for m in report["systems"].values()}
        self.assertEqual(denominators, {20})
        self.assertGreater(report["systems"]["perfect"]["macro_f1"],
                           report["systems"]["baseline-constant"]["macro_f1"])

    def test_predictor_never_sees_oracle_material(self):
        seen = []

        def spy_predictor(view):
            seen.append(view)
            return abstain_baseline(view)

        self.run_system(spy_predictor)
        self.assertEqual(len(seen), 20)
        forbidden = set(self.registry["leakage_control"]["forbidden_candidate_fields"])
        for view in seen:
            dump = json.dumps(view)
            self.assertNotIn("oracle", dump)
            self.assertFalse(forbidden & set(view),
                             f"leaked labels in view: {forbidden & set(view)}")

    def test_written_receipts_verify_against_the_registry(self):
        revealed, chains, _ = self.run_system(perfect_predictor,
                                              receipts_rel="_trial/receipts")
        cid = sorted(chains)[0]
        with open(os.path.join(self.root, "_trial", "receipts",
                               f"{cid}.prediction.json"), encoding="utf-8") as f:
            prediction_receipt = json.load(f)
        with open(os.path.join(self.root, "_trial", "receipts",
                               f"{cid}.reveal.json"), encoding="utf-8") as f:
            reveal_receipt = json.load(f)
        self.assertEqual(verify_receipt_chain(
            self.root, revealed, prediction_receipt, reveal_receipt), [])

    def test_report_is_written_to_the_out_dir(self):
        run_blind_trial(self.root, self.registry, {"baseline-abstain": abstain_baseline},
                        APPROVALS, "_trial/out")
        report_path = os.path.join(self.root, "_trial", "out",
                                   "blind-trial-report.json")
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report["schema"], "helix-blind-trial-report/1.0")
        self.assertIn("baseline-abstain", report["systems"])


if __name__ == "__main__":
    unittest.main()
