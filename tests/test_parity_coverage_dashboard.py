import os
import unittest

import tests._path  # noqa: F401
from scripts.corpus.parity_coverage_dashboard import build_dashboard, validate_dashboard


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_ROOT = os.path.join(ROOT, "seed", "parity-provenance")
NOW = "2026-07-16T00:00:00Z"


class TestParityCoverageDashboard(unittest.TestCase):
    def test_builds_stage10_dashboard_from_tracked_evidence(self):
        dashboard = build_dashboard(EVIDENCE_ROOT, NOW)
        self.assertEqual(validate_dashboard(dashboard), [])
        self.assertEqual(dashboard["schema"], "helix-parity-coverage-dashboard/1.0")
        self.assertEqual(dashboard["summary"]["packs"], 62)
        self.assertEqual(dashboard["summary"]["valid"], 58)
        self.assertEqual(dashboard["summary"]["blocked"], 4)
        self.assertEqual(dashboard["summary"]["pending"], 0)
        self.assertEqual(dashboard["summary"]["coverage_percent"], 93.55)
        self.assertEqual(dashboard["latest_batch"]["completed"], 43)
        self.assertEqual(dashboard["latest_batch"]["problems"], [])
        self.assertEqual(dashboard["latest_batch"]["promotions"][0]["pack"], "repro-dossier")
        self.assertEqual(dashboard["latest_batch"]["promotions"][-1]["pack"], "pqc-exposure")
        self.assertEqual(len(dashboard["platforms"]), 5)
        self.assertEqual(len(dashboard["blocked"]), 4)
        self.assertEqual(dashboard["next_candidates"], [])


if __name__ == "__main__":
    unittest.main()
