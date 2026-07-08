import unittest

import tests._path  # noqa: F401
from core.helix_router import (
    machines_from_probe_row,
    pack_machine_index,
    platform_machine_index,
    route_machine_claim,
    route_probe_rows,
)
from scripts.condense.machine_probe_dataset import build_dataset


LC = {
    "layer1_platforms": [
        {"name": "Attestra", "kernel_machines": ["M1", "M2", "M3", "M4", "M14"]},
        {"name": "Clearstra", "kernel_machines": ["M1", "M5", "M6", "M7", "M8"]},
        {"name": "Routestra", "kernel_machines": ["M1", "M4", "M9", "M10"]},
        {"name": "Certstra", "kernel_machines": ["M1", "M2", "M4", "M12"]},
        {"name": "Scorestra", "kernel_machines": ["M15"]},
    ],
}


class TestRouter(unittest.TestCase):
    def test_machine_index_is_deterministic(self):
        index = platform_machine_index(LC)
        self.assertEqual(index["M15"], ["Scorestra"])
        self.assertEqual(index["M2"], ["Attestra", "Certstra"])

    def test_extracts_probe_positive_machines_from_matched(self):
        self.assertEqual(machines_from_probe_row({"matched": ["M2(foo)", "M3+bar"]}), ["M2", "M3"])

    def test_routes_single_platform_covered_claim_to_pack_growth(self):
        decision = route_machine_claim(LC, {"id": "pqc", "matched": ["M2", "M3"]})
        self.assertEqual(decision["action"], "BUILD_ON_PLATFORM")
        self.assertEqual(decision["platform"], "Attestra")

    def test_routes_cross_platform_covered_claim_to_split_pack_growth(self):
        decision = route_machine_claim(LC, {"id": "compat", "matched": ["M6", "M10"]})
        self.assertEqual(decision["action"], "SPLIT_BUILD_ON_PLATFORM")
        self.assertEqual(decision["routes"], {"M10": "Routestra", "M6": "Clearstra"})

    def test_routes_novel_machine_to_condense_only_at_threshold(self):
        low = route_machine_claim(LC, {"id": "sim", "matched": ["M16"], "substantiated_count": 4})
        high = route_machine_claim(LC, {"id": "sim", "matched": ["M16"], "substantiated_count": 5})
        self.assertEqual(low["action"], "DEFER")
        self.assertEqual(high["action"], "CONDENSE")

    def test_routes_empty_probe_result_to_defer(self):
        decision = route_machine_claim(LC, {"id": "unknown", "matched": []})
        self.assertEqual(decision["action"], "DEFER")

    def test_routes_pack_level_machine_without_kernel_promotion(self):
        rows = [{"platform": "Attestra", "pack": "policy-drift", "matched": ["M11"]}]
        index = pack_machine_index(LC, rows)
        self.assertEqual(index, {"M11": ["Attestra"]})
        decision = route_machine_claim(LC, {"id": "drift", "matched": ["M11"]}, pack_index=index)
        self.assertEqual(decision["action"], "BUILD_ON_PLATFORM")
        self.assertEqual(decision["platform"], "Attestra")
        self.assertEqual(decision["coverage_scope"], "pack_evidence")
        self.assertNotIn("M11", platform_machine_index(LC))

    def test_live_probe_rows_route_without_human_cluster_names(self):
        dataset = build_dataset()
        self.assertEqual(dataset["agreement"]["rows"][0]["platform"], "Attestra")
        report = route_probe_rows(LC, dataset["agreement"]["rows"])
        self.assertEqual(report["summary"], {"BUILD_ON_PLATFORM": 94, "DEFER": 1})


if __name__ == "__main__":
    unittest.main()
