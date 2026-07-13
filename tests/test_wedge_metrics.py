import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_actuator import append_actuation_ledger
from core.helix_contestability import file_appeal, file_override
from core.helix_holdout import canonical_json_bytes
from core.helix_wedge import audit_handback
from core.helix_wedge_metrics import verify_metrics_seal, wedge_metrics


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRENT = "a" * 64
LEDGER = "_wedge/ledger.jsonl"
PACKETS = "_wedge/packets"
OPERATOR = {"kind": "human", "id": "operator-1"}


def load_packet(name="valid-packet.json"):
    with open(os.path.join(ROOT, "examples", "wedge", name),
              encoding="utf-8") as f:
        return json.load(f)


class MetricsFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-metrics-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("action-intent", "evidence-manifest", "gate-result"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(os.path.join(ROOT, "ActionHandbackVerifier", "src"),
                        os.path.join(self.root, "ActionHandbackVerifier", "src"))
        self.results = {}
        for name in ("valid-packet.json", "thin-packet.json",
                     "breach-packet.json"):
            self.results[name] = audit_handback(
                self.root, load_packet(name), OPERATOR, CURRENT, LEDGER,
                PACKETS, provenance_class="real")

    def metrics(self, **kwargs):
        return wedge_metrics(self.root, LEDGER, **kwargs)


class TestCounts(MetricsFixtureCase):
    def test_totals_distributions_and_prevented(self):
        report = self.metrics()
        self.assertTrue(report["metrics_valid"])
        self.assertEqual(report["decisions_total"], 3)
        self.assertEqual(report["by_admission"],
                         {"ADMIT": 1, "SANDBOX_ONLY": 1, "QUARANTINE": 0,
                          "EXCLUDED": 1})
        self.assertEqual(report["by_verdict"],
                         {"breach": 1, "thin": 1, "valid": 1})
        self.assertEqual(report["prevented_invalid_handbacks"], 1)
        self.assertEqual(report["distinct_operators"], ["operator-1"])
        self.assertEqual(report["gate_refusals"], 0)
        self.assertEqual(report["replay"],
                         {"verified": 3, "total": 3, "rate": 1.0,
                          "failures": []})
        self.assertTrue(verify_metrics_seal(report))

    def test_same_ledger_reproduces_the_same_sealed_report(self):
        first = self.metrics()
        second = self.metrics()
        self.assertEqual(first, second)
        self.assertIsNotNone(first["ledger_head_sha256"])

    def test_gate_refusals_are_counted_from_gate_only_requests(self):
        refusal_gate = {"result_sha256": "f" * 64, "decision": "HUMAN"}
        append_actuation_ledger(self.root, LEDGER, "gate", "REQ-REFUSED",
                                refusal_gate)
        report = self.metrics()
        self.assertEqual(report["gate_refusals"], 1)
        self.assertEqual(report["decisions_total"], 3)

    def test_period_injection_yields_the_weekly_north_star_rate(self):
        report = self.metrics(period={"weeks": 1.5, "label": "pilot week 1-1.5"})
        self.assertEqual(report["north_star"]["weekly_rate"], 2.0)
        self.assertFalse(report["latency_cost"]["measured"])

    def test_synthetic_and_unclassified_are_visible_but_not_real_metrics(self):
        audit_handback(self.root, load_packet(), OPERATOR, CURRENT, LEDGER,
                       PACKETS, provenance_class="synthetic")
        audit_handback(self.root, load_packet(), OPERATOR, CURRENT, LEDGER,
                       PACKETS)
        report = self.metrics(period={"weeks": 1})
        self.assertEqual(report["decisions_total"], 5)
        self.assertEqual(report["real_decisions_total"], 3)
        self.assertEqual(report["provenance_counts"],
                         {"real": 3, "synthetic": 1, "unclassified": 1})
        self.assertEqual(report["north_star"]["decisions"], 3)
        self.assertEqual(report["north_star"]["excluded_by_provenance"], 2)
        self.assertEqual(report["north_star"]["weekly_rate"], 3.0)


class TestHonesty(MetricsFixtureCase):
    def test_corrupt_ledger_invalidates_the_metrics(self):
        full = os.path.join(self.root, *LEDGER.split("/"))
        with open(full, encoding="utf-8") as f:
            lines = f.read().splitlines()
        doc = json.loads(lines[1])
        doc["kind"] = "gate"
        lines[1] = json.dumps(doc, ensure_ascii=False, sort_keys=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        report = self.metrics()
        self.assertFalse(report["metrics_valid"])
        self.assertTrue(report["problems"])

    def test_laundered_decision_drags_replay_below_100(self):
        full = os.path.join(self.root, *LEDGER.split("/"))
        with open(full, encoding="utf-8") as f:
            lines = f.read().splitlines()
        entries = [json.loads(line) for line in lines]
        # launder the breach decision to ADMIT with fresh seals + fresh chain
        for entry in entries:
            if (entry["kind"] == "wedge_decision"
                    and entry["receipt"]["handback_verdict"] == "breach"):
                receipt = {k: v for k, v in entry["receipt"].items()
                           if k != "receipt_sha256"}
                receipt["admission"] = "ADMIT"
                receipt["receipt_sha256"] = hashlib.sha256(
                    canonical_json_bytes(receipt)).hexdigest()
                entry["receipt"] = receipt
        parent = None
        rebuilt = []
        for index, entry in enumerate(entries):
            body = {k: v for k, v in entry.items() if k != "entry_sha256"}
            body["seq"] = index
            body["parent_sha256"] = parent
            body["entry_sha256"] = hashlib.sha256(
                canonical_json_bytes(body)).hexdigest()
            parent = body["entry_sha256"]
            rebuilt.append(body)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            for entry in rebuilt:
                f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True)
                        + "\n")
        report = self.metrics()
        self.assertTrue(report["metrics_valid"])  # chain was fully rebuilt...
        self.assertLess(report["replay"]["rate"], 1.0)  # ...but replay catches it
        self.assertTrue(any("admission does not replay" in p
                            for f in report["replay"]["failures"]
                            for p in f["problems"]))


class TestInterventions(MetricsFixtureCase):
    def test_verified_appeals_and_overrides_count(self):
        gate = self.results["breach-packet.json"]["gate"]
        appeal = file_appeal(gate, {"kind": "human", "id": "operator-2"},
                             "disputes the breach classification")
        override = file_override(gate, {"kind": "human", "id": "operator-3"},
                                 "operator judgment", "DENY", CURRENT)
        report = self.metrics(appeals=[appeal], overrides=[override])
        self.assertEqual(report["intervention"]["count"], 2)
        self.assertAlmostEqual(report["intervention"]["rate"], 2 / 3)

    def test_unverifiable_or_foreign_receipts_are_reported_not_counted(self):
        gate = self.results["valid-packet.json"]["gate"]
        appeal = file_appeal(gate, {"kind": "human", "id": "operator-2"}, "x")
        forged = copy.deepcopy(appeal)
        forged["reason"] = "edited"  # seal broken
        foreign = copy.deepcopy(appeal)
        foreign["gate_result_sha256"] = "0" * 64
        foreign = {k: v for k, v in foreign.items() if k != "receipt_sha256"}
        foreign["receipt_sha256"] = hashlib.sha256(
            canonical_json_bytes(foreign)).hexdigest()
        report = self.metrics(appeals=[forged, foreign])
        self.assertEqual(report["intervention"]["count"], 0)
        self.assertEqual(len(report["problems"]), 2)


if __name__ == "__main__":
    unittest.main()
