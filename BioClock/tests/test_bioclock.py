#!/usr/bin/env python3
"""Stdlib-only tests for the standalone BioClock package."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import copy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from BioClock.core import track_drift, certify_bio_clock, render_report  # noqa: E402
from BioClock.samples import (  # noqa: E402
    samples,
    VALID_PROTOCOL,
    VALID_EVIDENCE,
    VALID_QUARANTINE,
    DRIFT_PROTOCOL,
    DRIFT_EVIDENCE,
    DRIFT_QUARANTINE,
)


def _drift(magnitude):
    """Build a drift report with a fixed effect-size delta and zero sample gap."""
    protocol = copy.deepcopy(VALID_PROTOCOL)
    evidence = copy.deepcopy(VALID_EVIDENCE)
    protocol["target_effect_size"] = 1.0
    evidence["observed_effect_size"] = 1.0 - magnitude
    evidence["actual_samples"] = protocol["required_samples"]
    return track_drift(protocol, evidence)


class TestTrackDriftDeterminism(unittest.TestCase):
    def test_none_severity(self):
        report = _drift(0.0)
        self.assertEqual(report["drift_severity"], "none")
        self.assertTrue(report["protocol_compliant"])
        self.assertEqual(report["sample_gap"], 0)

    def test_none_boundary(self):
        # magnitude just below 0.1 is still none
        report = _drift(0.099)
        self.assertEqual(report["drift_severity"], "none")

    def test_moderate_severity(self):
        report = _drift(0.2)
        self.assertEqual(report["drift_severity"], "moderate")
        self.assertFalse(report["protocol_compliant"])

    def test_severe_severity(self):
        report = _drift(0.4)
        self.assertEqual(report["drift_severity"], "severe")
        self.assertFalse(report["protocol_compliant"])

    def test_severe_boundary(self):
        # magnitude of exactly 0.3 is severe (>= 0.3)
        report = _drift(0.3)
        self.assertEqual(report["drift_severity"], "severe")

    def test_sample_gap_capped_at_zero(self):
        protocol = copy.deepcopy(VALID_PROTOCOL)
        evidence = copy.deepcopy(VALID_EVIDENCE)
        evidence["actual_samples"] = protocol["required_samples"] + 50
        report = track_drift(protocol, evidence)
        self.assertEqual(report["sample_gap"], 0)

    def test_sample_gap_positive(self):
        protocol = copy.deepcopy(DRIFT_PROTOCOL)
        evidence = copy.deepcopy(DRIFT_EVIDENCE)
        report = track_drift(protocol, evidence)
        self.assertEqual(report["drift_severity"], "severe")
        self.assertEqual(report["sample_gap"], 40)

    def test_deterministic_repeated_run(self):
        report_a = _drift(0.2)
        report_b = _drift(0.2)
        self.assertEqual(report_a, report_b)


class TestCertifyBioClock(unittest.TestCase):
    def test_certified(self):
        drift_report = track_drift(VALID_PROTOCOL, VALID_EVIDENCE)
        cert = certify_bio_clock(drift_report, VALID_QUARANTINE)
        self.assertEqual(cert["certification"], "certified")
        self.assertTrue(cert["quarantine_complete"])
        self.assertTrue(cert["bio_clock_valid"])

    def test_revoked_on_severe_drift(self):
        drift_report = track_drift(DRIFT_PROTOCOL, DRIFT_EVIDENCE)
        cert = certify_bio_clock(drift_report, DRIFT_QUARANTINE)
        self.assertEqual(cert["certification"], "revoked")
        self.assertFalse(cert["bio_clock_valid"])

    def test_revoked_on_failed_quarantine_with_none_drift(self):
        drift_report = track_drift(VALID_PROTOCOL, VALID_EVIDENCE)
        cert = certify_bio_clock(drift_report, DRIFT_QUARANTINE)
        # none drift but quarantine incomplete -> revoked
        self.assertEqual(cert["certification"], "revoked")
        self.assertFalse(cert["quarantine_complete"])
        self.assertFalse(cert["bio_clock_valid"])

    def test_conditional_on_moderate_drift(self):
        drift_report = _drift(0.2)
        cert = certify_bio_clock(drift_report, VALID_QUARANTINE)
        self.assertEqual(cert["certification"], "conditional")
        self.assertFalse(cert["bio_clock_valid"])

    def test_render_report_contains_sections(self):
        drift_report = track_drift(VALID_PROTOCOL, VALID_EVIDENCE)
        cert = certify_bio_clock(drift_report, VALID_QUARANTINE)
        text = render_report(cert)
        self.assertIn("# BioClock Report", text)
        self.assertIn("certification", text)
        self.assertIn("certified", text)


class TestSampleFixtures(unittest.TestCase):
    def test_sample_fixtures_deterministic(self):
        docs = samples()
        self.assertEqual(len(docs), 6)
        # valid path is drift-free
        valid_drift = track_drift(docs["valid_protocol"], docs["valid_evidence"])
        self.assertEqual(valid_drift["drift_severity"], "none")
        self.assertTrue(valid_drift["protocol_compliant"])
        # drift path is severe
        drift_drift = track_drift(docs["drift_protocol"], docs["drift_evidence"])
        self.assertEqual(drift_drift["drift_severity"], "severe")


class TestCLI(unittest.TestCase):
    def test_cli_sample_track_certify(self):
        with tempfile.TemporaryDirectory() as d:
            # emit fixtures
            sample_out = subprocess.check_output(
                [sys.executable, "-m", "BioClock", "sample", "--out", d],
                cwd=ROOT,
                text=True,
            )
            written = json.loads(sample_out)["written"]
            self.assertEqual(len(written), 6)

            # track (valid -> none)
            drift_path = os.path.join(d, "valid_drift.json")
            track_out = subprocess.check_output(
                [
                    sys.executable, "-m", "BioClock", "track",
                    "--protocol", written["valid_protocol"],
                    "--evidence", written["valid_evidence"],
                    "--out", drift_path,
                ],
                cwd=ROOT,
                text=True,
            )
            with open(drift_path, "r", encoding="utf-8") as f:
                drift = json.load(f)
            self.assertEqual(drift["drift_severity"], "none")
            self.assertTrue(drift["protocol_compliant"])

            # certify (valid -> certified)
            cert_out = subprocess.check_output(
                [
                    sys.executable, "-m", "BioClock", "certify",
                    "--drift", drift_path,
                    "--quarantine", written["valid_quarantine"],
                ],
                cwd=ROOT,
                text=True,
            )
            cert = json.loads(cert_out)
            self.assertEqual(cert["certification"], "certified")
            self.assertTrue(cert["bio_clock_valid"])

    def test_cli_drift_scenario_revoked(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.check_output(
                [sys.executable, "-m", "BioClock", "sample", "--out", d],
                cwd=ROOT,
                text=True,
            )
            drift_path = os.path.join(d, "drift_drift.json")
            subprocess.check_output(
                [
                    sys.executable, "-m", "BioClock", "track",
                    "--protocol", os.path.join(d, "drift_protocol.json"),
                    "--evidence", os.path.join(d, "drift_evidence.json"),
                    "--out", drift_path,
                ],
                cwd=ROOT,
                text=True,
            )
            cert_out = subprocess.check_output(
                [
                    sys.executable, "-m", "BioClock", "certify",
                    "--drift", drift_path,
                    "--quarantine", os.path.join(d, "drift_quarantine.json"),
                ],
                cwd=ROOT,
                text=True,
            )
            cert = json.loads(cert_out)
            self.assertEqual(cert["certification"], "revoked")
            self.assertEqual(cert["drift_severity"], "severe")

    def test_cli_report(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.check_output(
                [sys.executable, "-m", "BioClock", "sample", "--out", d],
                cwd=ROOT,
                text=True,
            )
            drift_path = os.path.join(d, "valid_drift.json")
            subprocess.check_output(
                [
                    sys.executable, "-m", "BioClock", "track",
                    "--protocol", os.path.join(d, "valid_protocol.json"),
                    "--evidence", os.path.join(d, "valid_evidence.json"),
                    "--out", drift_path,
                ],
                cwd=ROOT,
                text=True,
            )
            report = subprocess.check_output(
                [
                    sys.executable, "-m", "BioClock", "report",
                    "--input", drift_path,
                ],
                cwd=ROOT,
                text=True,
            )
            self.assertIn("# BioClock Report", report)
            self.assertIn("Drift Dossier", report)


if __name__ == "__main__":
    unittest.main()
