import json
import os
import unittest

import tests._path  # noqa: F401


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_ROOT = os.path.join(ROOT, "seed", "parity-provenance")


class TestParityFinalClosure(unittest.TestCase):
    def test_final_closure_report_matches_dashboard(self):
        with open(os.path.join(EVIDENCE_ROOT, "coverage-dashboard.json"), encoding="utf-8") as handle:
            dashboard = json.load(handle)
        with open(os.path.join(EVIDENCE_ROOT, "final-closure-report.json"), encoding="utf-8") as handle:
            report = json.load(handle)
        self.assertEqual(report["schema"], "helix-parity-provenance-final-closure-report/1.0")
        self.assertEqual(report["summary"], dashboard["summary"])
        self.assertEqual(report["summary"]["pending"], 0)
        self.assertEqual(report["summary"]["valid"], 58)
        self.assertEqual(report["summary"]["blocked"], 4)
        self.assertEqual(report["verdict"], "ACTIONABLE_PENDING_EXHAUSTED_BLOCKED_FAIL_CLOSED")
        self.assertEqual(
            sorted((item["platform"], item["pack"]) for item in report["remaining_blocked"]),
            [
                ("Attestra", "authority-arbiter"),
                ("Attestra", "graph-quarantine"),
                ("Attestra", "hook-circuit"),
                ("Routestra", "contract-relay"),
            ],
        )
        self.assertTrue(report["policy"]["no_synthetic_upgrade"])


if __name__ == "__main__":
    unittest.main()
