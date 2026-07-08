import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

import tests._path  # noqa: F401
from scripts.condense.collect_forward_candidates import collect_manifest, main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERED_CORPUS = os.path.join(ROOT, "seed", "condense", "layered-corpus.json")
ARTIFACT_CATALOG = os.path.join(ROOT, "seed", "condense", "forward-candidate-artifacts.json")


class TestForwardCandidateManifest(unittest.TestCase):
    def _load_layered_corpus(self):
        with open(LAYERED_CORPUS, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_artifact_catalog(self):
        with open(ARTIFACT_CATALOG, "r", encoding="utf-8") as f:
            return json.load(f)["artifacts"]

    def test_collects_live_unresolved_deferred_and_future_candidates(self):
        manifest = collect_manifest(self._load_layered_corpus(), layered_corpus_path=LAYERED_CORPUS)
        self.assertEqual(manifest["schema"], "helix-forward-predict-manifest/1.0")
        self.assertEqual(manifest["count"], 10)
        self.assertEqual(manifest["status_counts"], {"deferred": 2, "future": 8})
        names = {candidate["name"] for candidate in manifest["candidates"]}
        self.assertIn("RouteSentinel", names)
        self.assertIn("EndowFront", names)
        self.assertIn("ADPR", names)
        self.assertNotIn("LoopKit", names)
        self.assertTrue(all(candidate["missing_artifact"] for candidate in manifest["candidates"]))

    def test_collect_applies_live_artifact_catalog(self):
        manifest = collect_manifest(
            self._load_layered_corpus(),
            layered_corpus_path=LAYERED_CORPUS,
            artifact_catalog=self._load_artifact_catalog(),
        )
        self.assertEqual(manifest["artifact_counts"], {"available": 10, "missing": 0})
        by_name = {candidate["name"]: candidate for candidate in manifest["candidates"]}
        self.assertEqual(by_name["ADPR"]["candidate"],
                         "examples/condense/candidate-adpr-m4.json")
        self.assertEqual(by_name["AgentPACT"]["candidate"],
                         "examples/condense/candidate-agentpact-m1.json")
        self.assertEqual(by_name["GPOA"]["candidate"],
                         "examples/condense/candidate-gpoa-m15.json")
        self.assertEqual(by_name["MLX"]["candidate"],
                         "examples/condense/candidate-mlx-m3.json")
        self.assertEqual(by_name["PnR"]["candidate"],
                         "examples/condense/candidate-pnr-m15.json")
        self.assertEqual(by_name["QVeil"]["candidate"],
                         "examples/condense/candidate-qveil-m3.json")
        self.assertEqual(by_name["Qvidence"]["candidate"],
                         "examples/condense/candidate-qvidence-m4.json")
        self.assertEqual(by_name["RouteSentinel"]["candidate"],
                         "examples/condense/candidate-routesentinel-m16.json")
        self.assertEqual(by_name["EndowFront"]["candidate"],
                         "examples/condense/candidate-endowfront-m17.json")
        self.assertEqual(by_name["WattMesh"]["candidate"],
                         "examples/condense/candidate-wattmesh-m9.json")
        self.assertNotIn("missing_artifact", by_name["AgentPACT"])
        self.assertNotIn("missing_artifact", by_name["ADPR"])
        self.assertNotIn("missing_artifact", by_name["GPOA"])
        self.assertNotIn("missing_artifact", by_name["MLX"])
        self.assertNotIn("missing_artifact", by_name["PnR"])
        self.assertNotIn("missing_artifact", by_name["QVeil"])
        self.assertNotIn("missing_artifact", by_name["Qvidence"])
        self.assertNotIn("missing_artifact", by_name["RouteSentinel"])
        self.assertNotIn("missing_artifact", by_name["EndowFront"])
        self.assertNotIn("missing_artifact", by_name["WattMesh"])

    def test_include_resolved_keeps_stale_marker_audit_trail(self):
        manifest = collect_manifest(
            self._load_layered_corpus(),
            layered_corpus_path=LAYERED_CORPUS,
            include_resolved=True,
        )
        self.assertEqual(manifest["count"], 14)
        resolved = {candidate["name"] for candidate in manifest["candidates"]
                    if candidate.get("resolved")}
        self.assertTrue({"LoopKit", "ForgeQuarantine", "LazarettoStage"} <= resolved)

    def test_cli_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "live-manifest.json")
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--layered-corpus", LAYERED_CORPUS,
                                       "--out", out_path,
                                       "--json"]), 0)
            with open(out_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        self.assertEqual(manifest["count"], 10)
        self.assertEqual(manifest["status_counts"]["future"], 8)
        self.assertEqual(manifest["artifact_counts"], {"available": 10, "missing": 0})


if __name__ == "__main__":
    unittest.main()
