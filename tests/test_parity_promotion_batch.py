import os
import unittest

import tests._path  # noqa: F401


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "seed", "parity-provenance")


class TestParityPromotionBatch(unittest.TestCase):
    def test_tracked_batch_report_exists_after_stage9(self):
        path = os.path.join(SEED, "promotion-batch-report.json")
        if not os.path.exists(path):
            self.skipTest("Stage9 tracked batch report has not been generated")
        import json
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
        self.assertEqual(report["schema"], "helix-parity-promotion-batch-report/1.0")
        self.assertEqual(report["completed"], len(report["promotions"]))
        self.assertEqual(report["problems"], [])


if __name__ == "__main__":
    unittest.main()
