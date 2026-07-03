#!/usr/bin/env python3
"""Stdlib-only tests for the standalone MineralShock package."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from MineralShock.core import (  # noqa: E402
    price_refusal_option,
    price_reserve_right,
    simulate_shock,
)
from MineralShock.samples import samples  # noqa: E402


class TestReserveRight(unittest.TestCase):
    def test_deterministic_values(self):
        result = price_reserve_right("test", 1000, 0.5, 10)
        self.assertEqual(result["coverage_days"], 100.0)
        self.assertAlmostEqual(result["scarcity_premium"], 0.005)
        self.assertAlmostEqual(result["right_price"], 502.5)

    def test_repeated_run_is_identical(self):
        a = price_reserve_right("lithium", 12000, 0.92, 40)
        b = price_reserve_right("lithium", 12000, 0.92, 40)
        self.assertEqual(a, b)

    def test_zero_demand_is_infinite_coverage(self):
        result = price_reserve_right("ghost", 100, 0.5, 0)
        self.assertEqual(result["coverage_days"], float("inf"))
        self.assertEqual(result["scarcity_premium"], 0.0)


class TestRefusalOption(unittest.TestCase):
    def test_option_premium(self):
        result = price_refusal_option(200, 0.5, 10)
        self.assertEqual(result["option_premium"], 100.0)

    def test_zero_threat_is_zero_premium(self):
        result = price_refusal_option(500, 0.0, 30)
        self.assertEqual(result["option_premium"], 0.0)


class TestSimulateShock(unittest.TestCase):
    def test_single_mineral_shock(self):
        scenario = {"name": "test", "demand_spiup_pct": 0.5, "supply_disruption_pct": 0.25}
        reserves = [{"mineral": "x", "stockpile_tonnes": 1000, "daily_demand": 10}]
        result = simulate_shock(scenario, reserves)
        self.assertEqual(result["scenario_name"], "test")
        self.assertEqual(result["total_shortfall_tonnes"], 250.0)
        self.assertEqual(result["affected_minerals"], ["x"])
        self.assertEqual(result["survival_days"], 50.0)

    def test_survival_days_is_bottleneck(self):
        scenario = {"name": "bottleneck", "demand_spiup_pct": 0.0, "supply_disruption_pct": 0.5}
        reserves = [
            {"mineral": "a", "stockpile_tonnes": 100, "daily_demand": 1},
            {"mineral": "b", "stockpile_tonnes": 50, "daily_demand": 5},
        ]
        result = simulate_shock(scenario, reserves)
        self.assertEqual(result["survival_days"], 5.0)

    def test_no_disruption_no_shortfall(self):
        scenario = {"name": "mild", "demand_spiup_pct": 0.2, "supply_disruption_pct": 0.0}
        reserves = [{"mineral": "z", "stockpile_tonnes": 100, "daily_demand": 2}]
        result = simulate_shock(scenario, reserves)
        self.assertEqual(result["total_shortfall_tonnes"], 0.0)
        self.assertEqual(result["affected_minerals"], [])


class TestSamples(unittest.TestCase):
    def test_samples_have_three_minerals_and_two_scenarios(self):
        docs = samples()
        for mineral in ("lithium", "cobalt", "rare_earth"):
            self.assertIn(mineral, docs)
        for scenario in ("trade_war", "blockade"):
            self.assertIn(scenario, docs)
        self.assertEqual(len(docs["trade_war"]["reserves"]), 3)


class TestCLI(unittest.TestCase):
    def test_sample_price_shock_report(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.check_output(
                [sys.executable, "-m", "MineralShock", "sample", "--out", d],
                cwd=ROOT,
                text=True,
            )

            priced = json.loads(subprocess.check_output(
                [sys.executable, "-m", "MineralShock", "price",
                 "--input", os.path.join(d, "lithium.json")],
                cwd=ROOT,
                text=True,
            ))
            self.assertEqual(priced["mineral"], "lithium")
            self.assertGreater(priced["right_price"], 0)

            shock_path = os.path.join(d, "shock.json")
            subprocess.check_output(
                [sys.executable, "-m", "MineralShock", "shock",
                 "--input", os.path.join(d, "trade_war.json"), "--out", shock_path],
                cwd=ROOT,
                text=True,
            )
            with open(shock_path, "r", encoding="utf-8") as f:
                shock = json.load(f)
            self.assertEqual(shock["scenario_name"], "trade-war-2026")
            self.assertGreater(shock["total_shortfall_tonnes"], 0)
            self.assertEqual(len(shock["affected_minerals"]), 3)

            report = subprocess.check_output(
                [sys.executable, "-m", "MineralShock", "report", "--input", shock_path],
                cwd=ROOT,
                text=True,
            )
            self.assertIn("# MineralShock Report", report)
            self.assertIn("trade-war-2026", report)


if __name__ == "__main__":
    unittest.main()
