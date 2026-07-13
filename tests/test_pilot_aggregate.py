import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_wedge import audit_handback
from core.helix_wedge_metrics import aggregate_pilot


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64


def load_packet(name):
    with open(os.path.join(ROOT, "examples", "wedge", name),
              encoding="utf-8") as f:
        return json.load(f)


class PilotFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-pilot-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(os.path.join(ROOT, "ActionHandbackVerifier", "src"),
                        os.path.join(self.root, "ActionHandbackVerifier", "src"))

    def participant(self, pid, packets, provenance_class="real"):
        ledger = f"_pilot/{pid}.jsonl"
        packets_dir = f"_pilot/{pid}-packets"
        for name in packets:
            audit_handback(self.root, load_packet(name),
                           {"kind": "human", "id": pid}, CURRENT, ledger,
                           packets_dir, provenance_class=provenance_class)
        return ledger

    def three_participants(self):
        return {
            "team-a": self.participant("team-a", ["valid-packet.json",
                                                  "valid-packet.json",
                                                  "breach-packet.json"]),
            "team-b": self.participant("team-b", ["valid-packet.json",
                                                  "thin-packet.json"]),
            "team-c": self.participant("team-c", ["breach-packet.json",
                                                  "valid-packet.json"]),
        }


class TestAggregation(PilotFixtureCase):
    def test_combines_per_participant_ledgers(self):
        report = aggregate_pilot(self.root, self.three_participants())
        self.assertEqual(report["participants"], 3)
        # a: valid,valid,breach; b: valid,thin; c: breach,valid  -> 7 decisions
        self.assertEqual(report["combined"]["decisions_total"], 7)
        self.assertEqual(report["combined"]["admitted"], 4)   # 4 valid
        self.assertEqual(report["combined"]["prevented_invalid_handbacks"], 2)  # 2 breach
        self.assertEqual(set(report["per_participant"]), {"team-a", "team-b", "team-c"})

    def test_weekly_north_star_from_period(self):
        report = aggregate_pilot(self.root, self.three_participants(),
                                 period={"weeks": 0.5})
        self.assertEqual(report["combined"]["weekly_rate"], 14.0)
        self.assertEqual(report["north_star"]["value"], 14.0)

    def test_report_is_deterministic_and_sealed(self):
        ledgers = self.three_participants()
        first = aggregate_pilot(self.root, ledgers)
        second = aggregate_pilot(self.root, ledgers)
        self.assertEqual(first, second)
        self.assertIn("report_sha256", first)


class TestT4Gate(PilotFixtureCase):
    def test_unmeasured_criteria_yield_incomplete(self):
        report = aggregate_pilot(self.root, self.three_participants())
        gate = report["t4_gate"]
        self.assertIsNone(gate["throughput"]["pass"])   # no period
        self.assertIsNone(gate["false_admit"]["pass"])  # no sidecar
        self.assertIsNone(gate["adoption"]["pass"])     # no retained
        self.assertTrue(gate["replay"]["pass"])
        self.assertEqual(gate["verdict"], "incomplete")

    def test_full_sidecar_can_pass(self):
        report = aggregate_pilot(
            self.root, self.three_participants(),
            period={"weeks": 0.25},  # 7/0.25 = 28 >= 20
            sidecar={"false_admits": {"team-a": 0, "team-b": 0, "team-c": 0},
                     "retained": ["team-a", "team-b"]})
        gate = report["t4_gate"]
        self.assertTrue(gate["throughput"]["pass"])
        self.assertTrue(gate["false_admit"]["pass"])
        self.assertTrue(gate["adoption"]["pass"])
        self.assertEqual(gate["verdict"], "passed")

    def test_false_admit_over_one_percent_fails(self):
        report = aggregate_pilot(
            self.root, self.three_participants(),
            period={"weeks": 0.25},
            sidecar={"false_admits": {"team-a": 1}, "retained": ["team-a", "team-b"]})
        gate = report["t4_gate"]
        self.assertFalse(gate["false_admit"]["pass"])  # 1/4 = 0.25 > 0.01
        self.assertEqual(gate["verdict"], "failed")

    def test_review_time_reduction_is_an_alternative_throughput_path(self):
        report = aggregate_pilot(
            self.root, self.three_participants(),
            sidecar={"false_admits": {}, "retained": ["team-a", "team-b"],
                     "manual_review_baseline_minutes": {"team-a": 600},
                     "wedge_review_minutes": {"team-a": 120}})  # 80% cut
        gate = report["t4_gate"]
        self.assertTrue(gate["throughput"]["pass"])
        self.assertEqual(gate["throughput"]["review_time_reduction"], 0.8)

    def test_fewer_than_three_participants_fails_adoption(self):
        two = {k: v for k, v in list(self.three_participants().items())[:2]}
        report = aggregate_pilot(
            self.root, two, period={"weeks": 0.1},
            sidecar={"false_admits": {}, "retained": ["team-a", "team-b"]})
        self.assertFalse(report["t4_gate"]["adoption"]["pass"])

    def test_synthetic_participants_cannot_enter_real_metrics(self):
        ledgers = {
            pid: self.participant(pid, ["valid-packet.json"] * 7,
                                  provenance_class="synthetic")
            for pid in ("sim-a", "sim-b", "sim-c")
        }
        report = aggregate_pilot(
            self.root, ledgers, period={"weeks": 1},
            sidecar={"false_admits": {}, "retained": list(ledgers),
                     "manual_review_baseline_minutes": {pid: 100 for pid in ledgers},
                     "wedge_review_minutes": {pid: 10 for pid in ledgers}})
        self.assertEqual(report["combined"]["decisions_total"], 21)
        self.assertEqual(report["combined"]["real_decisions_total"], 0)
        self.assertEqual(report["combined"]["excluded_by_provenance"], 21)
        self.assertEqual(report["real_participants"], 0)
        self.assertFalse(report["t4_gate"]["throughput"]["pass"])
        self.assertFalse(report["t4_gate"]["adoption"]["pass"])
        self.assertEqual(report["t4_gate"]["verdict"], "failed")


if __name__ == "__main__":
    unittest.main()
