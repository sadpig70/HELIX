import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

import tests._path  # noqa: F401
from scripts.condense.machine_probe_dataset import build_dataset, main, required_platforms_available


@unittest.skipUnless(required_platforms_available(), "live -stra platform repos are not vendored in this checkout")
class TestMachineProbeDataset(unittest.TestCase):
    def test_live_stra_pack_samples_match_implemented_probes(self):
        dataset = build_dataset()
        self.assertEqual(dataset["errors"], [])
        self.assertEqual(dataset["total_platform_packs"], 56)
        self.assertEqual(dataset["implemented_probe_cases"], 95)
        self.assertEqual(dataset["agreement"]["scored_claims"], 95)
        self.assertEqual(dataset["agreement"]["matched_claims"], 95)
        self.assertEqual(dataset["agreement"]["agreement"], 1.0)

    def test_unimplemented_machine_claims_are_explicitly_skipped(self):
        dataset = build_dataset()
        skipped = {}
        for row in dataset["skipped_claims"]:
            skipped[row["machine"]] = skipped.get(row["machine"], 0) + 1
        self.assertEqual(skipped, {})

    def test_main_writes_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.json")
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--out", out]), 0)
            with open(out, "r", encoding="utf-8") as f:
                report = json.load(f)
        self.assertEqual(report["agreement"]["agreement"], 1.0)
        self.assertEqual(report["implemented_probe_cases"], 95)


if __name__ == "__main__":
    unittest.main()
