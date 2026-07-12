"""End-to-end CLI tests for the wedge integration kit (P5_2).

Drives ``python helix.py audit-handback`` as a real subprocess against the
committed sample packets, asserting the operator-facing contract: verdicts,
exit codes, ledger recording, and third-party replay via the printed command.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_actuator import verify_actuation_chain, verify_actuation_ledger


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR = "a" * 64


class WedgeCliCase(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp(prefix="helix-wedge-cli-")
        self.addCleanup(shutil.rmtree, self.workdir, ignore_errors=True)
        self.ledger = os.path.join(self.workdir, "ledger.jsonl")
        self.packets = os.path.join(self.workdir, "packets")

    def cli(self, packet_rel, extra=()):
        argv = [sys.executable, "helix.py", "audit-handback",
                "--packet", packet_rel,
                "--state-receipt-hash", ANCHOR,
                "--operator", "operator-e2e",
                "--ledger", self.ledger,
                "--packets-dir", self.packets] + list(extra)
        return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)

    def test_sample_packets_produce_the_documented_verdicts_and_exit_codes(self):
        cases = (("examples/wedge/valid-packet.json", "valid", "ADMIT", 0),
                 ("examples/wedge/thin-packet.json", "thin", "SANDBOX_ONLY", 3),
                 ("examples/wedge/breach-packet.json", "breach", "EXCLUDED", 4))
        for packet, verdict, admission, code in cases:
            with self.subTest(packet=packet):
                proc = self.cli(packet)
                self.assertEqual(proc.returncode, code, proc.stderr)
                self.assertIn(f"verdict:     {verdict}", proc.stdout)
                self.assertIn(f"admission:   {admission}", proc.stdout)
                self.assertIn("replay check: REPRODUCED", proc.stdout)

    def test_json_output_carries_the_sealed_decision(self):
        proc = self.cli("examples/wedge/valid-packet.json", extra=["--json"])
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["decision"]["admission"], "ADMIT")
        self.assertEqual(doc["decision"]["metric"]["counts_toward"],
                         "weekly_real_admission_decisions")
        self.assertEqual(doc["replay_problems"], [])

    def test_decisions_land_in_a_verifiable_ledger(self):
        self.cli("examples/wedge/valid-packet.json")
        self.cli("examples/wedge/breach-packet.json")
        self.assertEqual(verify_actuation_ledger(ROOT, self.ledger), [])
        self.assertEqual(verify_actuation_chain(ROOT, self.ledger), [])
        with open(self.ledger, encoding="utf-8") as f:
            kinds = [json.loads(line)["kind"] for line in f if line.strip()]
        self.assertEqual(kinds, ["gate", "wedge_decision",
                                 "gate", "wedge_decision"])

    def test_printed_replay_command_reproduces_the_decision(self):
        proc = self.cli("examples/wedge/valid-packet.json", extra=["--json"])
        decision = json.loads(proc.stdout)["decision"]
        stored_packet = decision["packet_path"]
        replay = self.cli(stored_packet, extra=["--json"])
        self.assertEqual(replay.returncode, 0, replay.stderr)
        replayed = json.loads(replay.stdout)["decision"]
        self.assertEqual(replayed["receipt_sha256"], decision["receipt_sha256"])

    def test_usage_error_without_packet(self):
        proc = subprocess.run([sys.executable, "helix.py", "audit-handback"],
                              cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
