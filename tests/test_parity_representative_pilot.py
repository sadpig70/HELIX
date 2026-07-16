import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from scripts.corpus.parity_evidence_builder import DEFAULT_PACKS, build_bundle
from scripts.corpus.parity_representative_pilot import build_pilot


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "seed", "corpus", "phase3-2026-01-experiments.json")
CORPUS_ROOT = os.path.join(ROOT, "seed", "corpus")
NOW = "2026-07-16T00:00:00Z"


class TestParityRepresentativePilot(unittest.TestCase):
    def test_builds_five_pack_registry_with_honest_status(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            build_bundle(ROOT, REGISTRY, CORPUS_ROOT, tmp, packs=DEFAULT_PACKS, now=NOW)
            report, problems = build_pilot(ROOT, tmp, NOW)
            self.assertEqual(report["counts"], {"packs": 5, "valid": 1, "blocked": 4})
            self.assertTrue(problems)
            self.assertTrue(any("unsupported pack" in problem for problem in problems))
            self.assertTrue(os.path.exists(os.path.join(tmp, "evidence-registry.json")))

    def test_real_seed_pilot_is_replayable_when_present(self):
        root = os.path.join(ROOT, "seed", "parity-provenance")
        if not os.path.exists(os.path.join(root, "build-report.json")):
            self.skipTest("seed parity-provenance build report is not present")
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            shutil.copytree(root, tmp, dirs_exist_ok=True)
            report, _ = build_pilot(ROOT, tmp, NOW)
            self.assertEqual(report["counts"]["packs"], 5)


if __name__ == "__main__":
    unittest.main()
