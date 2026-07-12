import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_oracle_grounding import (
    MACHINE_FEATURES,
    verify_oracle_grounding,
    view_text,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_view(cid):
    with open(os.path.join(ROOT, "seed", "evaluation", "t1-holdout",
                           "candidates", f"{cid}.view.json"), encoding="utf-8") as f:
        return json.load(f)


class TestGroundedLabels(unittest.TestCase):
    def test_a_gate_label_grounded_in_the_view_passes(self):
        # T1-008 (Gatekeeper) is an M3 predicate gate; its view exposes both
        # decisive features, so a grounded oracle passes.
        view = load_view("T1-008")
        oracle = {"expected": {"action": "BUILD_ON_PLATFORM", "machines": ["M3"]},
                  "grounding": {"M3": {
                      "predicate check over evidence": "evaluate_constraints",
                      "aggregate verdict": "admit/reject decisions"}}}
        # sanity: the quotes are actually in the view
        text = view_text(view)
        self.assertIn("evaluate_constraints", text)
        self.assertEqual(verify_oracle_grounding(view, oracle), [])

    def test_defer_no_machine_needs_no_grounding(self):
        view = load_view("T1-037")  # markdown parser, no machine
        oracle = {"expected": {"action": "DEFER", "machines": []}}
        self.assertEqual(verify_oracle_grounding(view, oracle), [])


class TestCatchesTheActualT1OverReach(unittest.TestCase):
    """The gate must reject exactly the labels the post-mortem flagged."""

    def test_rate_limiter_cannot_be_labeled_m10(self):
        # T1-017: oracle claimed M10, but the view never exposes severity-merge.
        view = load_view("T1-017")
        oracle = {"expected": {"action": "BUILD_ON_PLATFORM", "machines": ["M10"]},
                  "grounding": {"M10": {
                      "multiple threshold-bound dimensions": "multiple periods",
                      # honest author cannot find a merge-by-severity quote:
                      "merge by highest severity": "merged by highest severity"}}}
        problems = verify_oracle_grounding(view, oracle)
        self.assertTrue(any("merge by highest severity" in p
                            and "does not appear" in p for p in problems),
                        problems)

    def test_leaderboard_cannot_be_labeled_m15(self):
        # T1-023: oracle claimed M15, but the view has no tier/distribution.
        view = load_view("T1-023")
        oracle = {"expected": {"action": "BUILD_ON_PLATFORM", "machines": ["M15"]},
                  "grounding": {"M15": {
                      "weighted assessment score": "compute_activity_scores",
                      "tier or rule-class classification": "tier classification",
                      "aggregate distribution over classes": "distribution"}}}
        problems = verify_oracle_grounding(view, oracle)
        self.assertTrue(any("tier or rule-class classification" in p for p in problems),
                        problems)
        self.assertTrue(any("aggregate distribution over classes" in p
                            for p in problems), problems)

    def test_sentinel_flow_control_missing_severity_merge(self):
        view = load_view("T1-014")
        oracle = {"expected": {"action": "BUILD_ON_PLATFORM", "machines": ["M10"]},
                  "grounding": {"M10": {
                      "multiple threshold-bound dimensions": "thresholds",
                      "merge by highest severity": "merge by highest severity"}}}
        problems = verify_oracle_grounding(view, oracle)
        self.assertTrue(any("merge by highest severity" in p for p in problems),
                        problems)


class TestFailClosed(unittest.TestCase):
    def setUp(self):
        self.view = load_view("T1-008")

    def test_missing_feature_grounding_is_rejected(self):
        oracle = {"expected": {"action": "BUILD_ON_PLATFORM", "machines": ["M3"]},
                  "grounding": {"M3": {
                      "predicate check over evidence": "evaluate_constraints"}}}
        problems = verify_oracle_grounding(self.view, oracle)
        self.assertTrue(any("aggregate verdict" in p and "not grounded" in p
                            for p in problems), problems)

    def test_fabricated_quote_not_in_view_is_rejected(self):
        oracle = {"expected": {"action": "BUILD_ON_PLATFORM", "machines": ["M3"]},
                  "grounding": {"M3": {
                      "predicate check over evidence": "evaluate_constraints",
                      "aggregate verdict": "this exact phrase is nowhere in the view"}}}
        problems = verify_oracle_grounding(self.view, oracle)
        self.assertTrue(any("does not appear in the view" in p for p in problems),
                        problems)

    def test_unknown_machine_is_rejected(self):
        oracle = {"expected": {"action": "BUILD_ON_PLATFORM", "machines": ["M99"]}}
        problems = verify_oracle_grounding(self.view, oracle)
        self.assertTrue(any("unknown machine" in p for p in problems), problems)

    def test_grounding_for_unclaimed_machine_is_flagged(self):
        oracle = {"expected": {"action": "DEFER", "machines": []},
                  "grounding": {"M3": {"predicate check over evidence": "x"}}}
        problems = verify_oracle_grounding(self.view, oracle)
        self.assertTrue(any("not claimed" in p for p in problems), problems)


class TestRubric(unittest.TestCase):
    def test_every_machine_m1_to_m17_has_features(self):
        self.assertEqual(sorted(MACHINE_FEATURES),
                         sorted(f"M{i}" for i in range(1, 18)))
        for machine, feats in MACHINE_FEATURES.items():
            self.assertTrue(feats, f"{machine} has no decisive features")


if __name__ == "__main__":
    unittest.main()
