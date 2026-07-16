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
        self.assertEqual(dashboard["summary"]["valid"], 12)
        self.assertEqual(dashboard["summary"]["blocked"], 4)
        self.assertEqual(dashboard["summary"]["pending"], 46)
        self.assertEqual(dashboard["summary"]["coverage_percent"], 19.35)
        self.assertEqual(dashboard["latest_batch"]["completed"], 3)
        self.assertEqual(dashboard["latest_batch"]["problems"], [])
        self.assertEqual(
            [item["pack"] for item in dashboard["latest_batch"]["promotions"]],
            ["delegation", "drift-isolator", "gen-cert"],
        )
        self.assertEqual(len(dashboard["platforms"]), 5)
        self.assertEqual(len(dashboard["blocked"]), 4)
        self.assertTrue(dashboard["next_candidates"])


if __name__ == "__main__":
    unittest.main()
