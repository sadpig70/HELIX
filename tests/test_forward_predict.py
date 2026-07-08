import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

import tests._path  # noqa: F401
from scripts.condense.forward_predict import (
    build_manifest_report, build_report, main, predict_candidate,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples", "condense")
LAYERED_CORPUS = os.path.join(ROOT, "seed", "condense", "layered-corpus.json")
FORWARD_GATE = os.path.join(ROOT, "seed", "condense", "forward-predict-gate.json")

LC = {
    "layer1_platforms": [
        {"name": "Attestra", "kernel_machines": ["M1", "M2", "M3", "M4", "M14"]},
        {"name": "Scorestra", "kernel_machines": ["M15"]},
    ],
}

M15_CANDIDATE = {
    "id": "new-score-pack",
    "expected": ["M15"],
    "artifact": {
        "operation": "assessment_scoring",
        "weights": {"impact": 0.7, "risk": 0.3},
        "bands": [{"min": 0.8, "tier": "high"}, {"min": 0.0, "tier": "low"}],
        "scored": [{"id": "x", "score": 0.9, "tier": "high"}],
        "count_by_tier": {"high": 1, "low": 0},
    },
}

M13_CANDIDATE = {
    "id": "new-gap-machine",
    "expected": ["M13"],
    "artifact": {
        "operation": "compatibility_gap_scoring",
        "pairs": [
            {"source": "a", "target": "adapter", "compatibility_score": 0.7, "gap_score": 0.3},
            {"source": "b", "target": "adapter", "compatibility_score": 0.5, "gap_score": 0.5},
        ],
        "summary": {"pair_count": 2, "mean_compatibility": 0.6, "mean_gap": 0.4},
    },
}


class TestForwardPredict(unittest.TestCase):
    def _load_candidate(self, name):
        with open(os.path.join(EXAMPLES, name), "r", encoding="utf-8") as f:
            return json.load(f)

    def test_predicts_existing_platform_pack_growth(self):
        result = predict_candidate(M15_CANDIDATE, LC, pack_rows=[])
        self.assertEqual(result["probe"]["matched"], ["M15"])
        self.assertEqual(result["prediction"]["action"], "BUILD_ON_PLATFORM")
        self.assertEqual(result["prediction"]["platform"], "Scorestra")

    def test_predicts_defer_for_uncovered_machine_below_threshold(self):
        candidate = {**M13_CANDIDATE, "substantiated_count": 1}
        result = predict_candidate(candidate, LC, pack_rows=[])
        self.assertEqual(result["probe"]["matched"], ["M13"])
        self.assertEqual(result["prediction"]["action"], "DEFER")

    def test_predicts_condense_for_uncovered_machine_at_threshold(self):
        candidate = {**M13_CANDIDATE, "substantiated_count": 5}
        result = predict_candidate(candidate, LC, pack_rows=[])
        self.assertEqual(result["prediction"]["action"], "CONDENSE")

    def test_cli_writes_json_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_path = os.path.join(tmp, "layered.json")
            out_path = os.path.join(tmp, "prediction.json")
            with open(corpus_path, "w", encoding="utf-8") as f:
                json.dump(LC, f)
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--candidate", os.path.join(EXAMPLES, "candidate-scorestra-m15.json"),
                                       "--layered-corpus", corpus_path,
                                       "--out", out_path,
                                       "--json"]), 0)
            with open(out_path, "r", encoding="utf-8") as f:
                result = json.load(f)
        self.assertEqual(result["prediction"]["action"], "BUILD_ON_PLATFORM")

    def test_example_candidate_files_regression(self):
        cases = [
            ("candidate-adpr-m4.json", "BUILD_ON_PLATFORM", "Attestra"),
            ("candidate-agentpact-m1.json", "BUILD_ON_PLATFORM", "Attestra"),
            ("candidate-gpoa-m15.json", "BUILD_ON_PLATFORM", "Scorestra"),
            ("candidate-mlx-m3.json", "BUILD_ON_PLATFORM", "Attestra"),
            ("candidate-pnr-m15.json", "BUILD_ON_PLATFORM", "Scorestra"),
            ("candidate-qveil-m3.json", "BUILD_ON_PLATFORM", "Attestra"),
            ("candidate-qvidence-m4.json", "BUILD_ON_PLATFORM", "Attestra"),
            ("candidate-scorestra-m15.json", "BUILD_ON_PLATFORM", "Scorestra"),
            ("candidate-wattmesh-m9.json", "BUILD_ON_PLATFORM", "Routestra"),
            ("candidate-m13-defer.json", "DEFER", None),
            ("candidate-m13-condense.json", "CONDENSE", None),
            ("candidate-routesentinel-m16.json", "DEFER", None),
            ("candidate-endowfront-m17.json", "DEFER", None),
        ]
        for filename, action, platform in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                out_path = os.path.join(tmp, "prediction.json")
                with redirect_stdout(StringIO()):
                    self.assertEqual(main(["--candidate", os.path.join(EXAMPLES, filename),
                                           "--layered-corpus", LAYERED_CORPUS,
                                           "--out", out_path,
                                           "--json"]), 0)
                with open(out_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
                self.assertEqual(result["prediction"]["action"], action)
                if platform:
                    self.assertEqual(result["prediction"]["platform"], platform)
                self.assertEqual(result["probe"]["agreement"], 1.0)

    def test_adpr_m4_routes_to_existing_platform(self):
        candidate = self._load_candidate("candidate-adpr-m4.json")
        with open(LAYERED_CORPUS, "r", encoding="utf-8") as f:
            layered_corpus = json.load(f)
        result = predict_candidate(candidate, layered_corpus, pack_rows=[])
        self.assertEqual(result["probe"]["matched"], ["M4"])
        self.assertEqual(result["prediction"]["action"], "BUILD_ON_PLATFORM")
        self.assertEqual(result["prediction"]["platform"], "Attestra")

    def test_remaining_live_candidates_route_to_existing_platforms(self):
        cases = [
            ("candidate-agentpact-m1.json", ["M1"], "Attestra"),
            ("candidate-gpoa-m15.json", ["M15"], "Scorestra"),
            ("candidate-mlx-m3.json", ["M3"], "Attestra"),
            ("candidate-pnr-m15.json", ["M15"], "Scorestra"),
            ("candidate-qveil-m3.json", ["M3"], "Attestra"),
            ("candidate-qvidence-m4.json", ["M4"], "Attestra"),
            ("candidate-wattmesh-m9.json", ["M9"], "Routestra"),
        ]
        with open(LAYERED_CORPUS, "r", encoding="utf-8") as f:
            layered_corpus = json.load(f)
        for filename, matched, platform in cases:
            with self.subTest(filename=filename):
                result = predict_candidate(self._load_candidate(filename), layered_corpus, pack_rows=[])
                self.assertEqual(result["probe"]["matched"], matched)
                self.assertEqual(result["prediction"]["action"], "BUILD_ON_PLATFORM")
                self.assertEqual(result["prediction"]["platform"], platform)

    def test_route_sentinel_m16_is_uncovered_forward_prediction(self):
        candidate = self._load_candidate("candidate-routesentinel-m16.json")
        with open(LAYERED_CORPUS, "r", encoding="utf-8") as f:
            layered_corpus = json.load(f)
        result = predict_candidate(candidate, layered_corpus, pack_rows=[])
        self.assertEqual(result["probe"]["matched"], ["M16"])
        self.assertEqual(result["prediction"]["action"], "DEFER")
        self.assertEqual(result["prediction"]["uncovered_machines"], ["M16"])

    def test_endowfront_m17_is_uncovered_forward_prediction(self):
        candidate = self._load_candidate("candidate-endowfront-m17.json")
        with open(LAYERED_CORPUS, "r", encoding="utf-8") as f:
            layered_corpus = json.load(f)
        result = predict_candidate(candidate, layered_corpus, pack_rows=[])
        self.assertEqual(result["probe"]["matched"], ["M17"])
        self.assertEqual(result["prediction"]["action"], "DEFER")
        self.assertEqual(result["prediction"]["uncovered_machines"], ["M17"])

    def test_build_report_from_gate(self):
        report = build_report(FORWARD_GATE, layered_corpus_path=LAYERED_CORPUS)
        self.assertTrue(report["all_ok"])
        self.assertEqual(report["count"], 3)
        self.assertEqual(report["summary"], {"BUILD_ON_PLATFORM": 1, "CONDENSE": 1, "DEFER": 1})

    def test_build_manifest_report_accepts_files_and_inline_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_path = os.path.join(tmp, "layered.json")
            candidate_path = os.path.join(tmp, "score.json")
            manifest_path = os.path.join(tmp, "manifest.json")
            with open(corpus_path, "w", encoding="utf-8") as f:
                json.dump(LC, f)
            with open(candidate_path, "w", encoding="utf-8") as f:
                json.dump(M15_CANDIDATE, f)
            manifest = {
                "schema": "helix-forward-predict-manifest/1.0",
                "layered_corpus": "layered.json",
                "candidates": [
                    {"candidate": "score.json"},
                    {**M13_CANDIDATE, "substantiated_count": 5},
                ],
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            report = build_manifest_report(manifest_path)
        self.assertTrue(report["all_ok"])
        self.assertEqual(report["count"], 2)
        self.assertEqual(report["summary"], {"BUILD_ON_PLATFORM": 1, "CONDENSE": 1})
        self.assertEqual(report["rows"][0]["expectation"], "none")
        self.assertEqual(report["rows"][1]["actual_action"], "CONDENSE")

    def test_build_manifest_report_skips_missing_artifact_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_path = os.path.join(tmp, "layered.json")
            manifest_path = os.path.join(tmp, "manifest.json")
            with open(corpus_path, "w", encoding="utf-8") as f:
                json.dump(LC, f)
            manifest = {
                "schema": "helix-forward-predict-manifest/1.0",
                "layered_corpus": "layered.json",
                "candidates": [
                    {
                        "id": "layered-deferred-routesentinel",
                        "name": "RouteSentinel",
                        "status": "deferred",
                        "reason": "simulation-engine",
                        "missing_artifact": True,
                    }
                ],
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            report = build_manifest_report(manifest_path)
        self.assertTrue(report["all_ok"])
        self.assertEqual(report["summary"], {"MISSING_ARTIFACT": 1})
        self.assertEqual(report["rows"][0]["expectation"], "missing_artifact")
        self.assertEqual(report["rows"][0]["actual_action"], "MISSING_ARTIFACT")

    def test_cli_writes_gate_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "u9-report.json")
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--gate", FORWARD_GATE,
                                       "--layered-corpus", LAYERED_CORPUS,
                                       "--out", out_path,
                                       "--json"]), 0)
            with open(out_path, "r", encoding="utf-8") as f:
                report = json.load(f)
        self.assertTrue(report["all_ok"])
        self.assertEqual(report["count"], 3)
        self.assertEqual(report["summary"]["BUILD_ON_PLATFORM"], 1)

    def test_cli_writes_manifest_report(self):
        manifest_path = os.path.join(EXAMPLES, "forward-predict-manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "manifest-report.json")
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--manifest", manifest_path,
                                       "--out", out_path,
                                       "--json"]), 0)
            with open(out_path, "r", encoding="utf-8") as f:
                report = json.load(f)
        self.assertTrue(report["all_ok"])
        self.assertEqual(report["summary"], {"BUILD_ON_PLATFORM": 1, "CONDENSE": 1, "DEFER": 1})
        self.assertEqual({row["expectation"] for row in report["rows"]}, {"none"})


if __name__ == "__main__":
    unittest.main()
