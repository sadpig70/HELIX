#!/usr/bin/env python3
"""Smoke test: close-loop --packet end-to-end via the CLI.

Runs the actual `python helix.py close-loop ...` command against the shipped
demo fixtures, verifying both the valid (admit) and breach (abort) paths.
This doubles as a CI smoke test for the HELIX write path.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINNER = os.path.join(ROOT, "examples", "close_loop_demo", "winner.json")
VALID_PACKET = os.path.join(ROOT, "examples", "exploit_state", "handback_packet.json")
BREACH_PACKET = os.path.join(ROOT, "ActionHandbackVerifier", "examples", "breach.json")


def _run(args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, "helix.py"] + args,
        cwd=cwd, text=True, capture_output=True)


class TestCloseLoopDemoSmoke(unittest.TestCase):

    def test_valid_handback_closes_loop(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.json")
            corpus = os.path.join(d, "corpus.json")
            proc = _run([
                "close-loop",
                "--winner", WINNER,
                "--ledger", ledger,
                "--corpus", corpus,
                "--packet", VALID_PACKET,
                "--now", "2026-07-02T00:00:00+00:00",
            ])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result["status"], "closed")
            self.assertEqual(result["handback"]["verdict"], "valid")
            # ledger entry carries the handback verdict
            with open(ledger, encoding="utf-8") as f:
                led = json.load(f)
            self.assertTrue(led["consumed"])
            self.assertEqual(led["consumed"][0]["handback_verdict"], "valid")

    def test_breach_handback_aborts_write(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.json")
            corpus = os.path.join(d, "corpus.json")
            proc = _run([
                "close-loop",
                "--winner", WINNER,
                "--ledger", ledger,
                "--corpus", corpus,
                "--packet", BREACH_PACKET,
                "--now", "2026-07-02T00:00:00+00:00",
            ])
            self.assertEqual(proc.returncode, 1, proc.stdout)
            result = json.loads(proc.stdout)
            self.assertEqual(result["status"], "handback_breach")
            self.assertEqual(result["handback"]["verdict"], "breach")
            # nothing was written — no ledger file created
            self.assertFalse(os.path.exists(ledger))

    def test_no_packet_backward_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = os.path.join(d, "ledger.json")
            corpus = os.path.join(d, "corpus.json")
            proc = _run([
                "close-loop",
                "--winner", WINNER,
                "--ledger", ledger,
                "--corpus", corpus,
                "--now", "2026-07-02T00:00:00+00:00",
            ])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result["status"], "closed")
            self.assertNotIn("handback", result)


if __name__ == "__main__":
    unittest.main()
