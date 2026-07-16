import json
import os
import shutil
import subprocess
import tempfile
import unittest

from core.helix_corpus_supply import digest, manifest_digest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _manifest(corpus_id="HC-RUNBOOK-001", revision=1, supersedes=None,
              evidence=False):
    doc = {
        "schema": "helix-corpus-manifest/1.0",
        "corpus_id": corpus_id,
        "revision": revision,
        "name": "RunbookFixture",
        "summary": "A fixture that exercises the corpus operator runbook.",
        "origin": {
            "kind": "external_repo",
            "locator": "example/runbook-fixture",
            "revision": "b" * 40,
            "license": "MIT",
            "license_verified": True,
            "license_evidence": "LICENSE",
            "license_evidence_sha256": digest("MIT license bytes"),
            "source_evidence": "source.snapshot.json",
            "source_sha256": digest("source snapshot bytes"),
        },
        "character": {
            "domain": "operations",
            "primary_verb": "admit",
            "input_shape": "manifest",
            "output_shape": "ledger_event",
        },
        "genes": ["operator_runbook"],
        "dependencies": [],
        "restrictions": [],
        "machine": {
            "status": "substantiated" if evidence else "hypothesis",
            "label": "single-writer-admission-ledger",
            "evidence": ["tests/fixture.py:run"] if evidence else [],
        },
        "verification": {
            "reproducible": evidence,
            "tests_passed": evidence,
            "deterministic": evidence,
            "parity_available": False,
            "reproduction_command": "python -m unittest" if evidence else "",
            "behavior_sha256": digest("behavior") if evidence else "",
            "supporting_files": ["tests/fixture.py"] if evidence else [],
            "supporting_symbols": ["run"] if evidence else [],
        },
        "safety": {
            "secret_scan_passed": True,
            "pii_scan_passed": True,
            "malware_scan_passed": True,
            "execution_isolated": True,
        },
        "provenance": ["fixture:corpus-operator-runbook"],
    }
    if revision > 1:
        doc["supersedes_manifest_sha256"] = supersedes or "0" * 64
    return doc


def _review_for(manifest):
    return {
        "schema": "helix-corpus-review-receipt/1.0",
        "corpus_id": manifest["corpus_id"],
        "manifest_sha256": manifest_digest(manifest),
        "reviewer": {"kind": "human", "id": "reviewer-1"},
        "verdict": "approved",
        "reviewed_at": "2026-07-16T16:00:00+09:00",
        "notes": "Runbook fixture evidence inspected.",
    }


class CorpusOperatorRunbookCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="helix-corpus-runbook-")
        self.corpus = os.path.join(self.tmp, "corpus")
        self.evidence = os.path.join(self.tmp, "evidence")
        os.makedirs(self.evidence, exist_ok=True)
        self._write_text(os.path.join(self.evidence, "LICENSE"),
                         "MIT license bytes")
        self._write_text(os.path.join(self.evidence, "source.snapshot.json"),
                         "source snapshot bytes")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write_text(self, path, text):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def _write_json(self, name, value):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True)
        return path

    def _corpus(self, *args, expected=0):
        completed = subprocess.run(
            ["python", "helix.py", "corpus", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            expected, completed.returncode,
            completed.stderr or completed.stdout,
        )
        return json.loads(completed.stdout)

    def test_documented_operator_sequence_admits_and_promotes(self):
        generative = _manifest()
        generative_path = self._write_json("candidate-v1.json", generative)

        validate = self._corpus("validate", "--manifest", generative_path)
        self.assertTrue(validate["valid"])

        intake = self._corpus(
            "intake", "--manifest", generative_path, "--root", self.corpus)
        self.assertEqual("INTAKEN", intake["status"])

        fingerprint = self._corpus(
            "fingerprint", "--id", generative["corpus_id"],
            "--root", self.corpus)
        self.assertEqual(generative["corpus_id"], fingerprint["corpus_id"])

        admitted = self._corpus(
            "admit", "--id", generative["corpus_id"], "--root", self.corpus,
            "--evidence-root", self.evidence,
            "--now", "2026-07-16T16:01:00+09:00")
        self.assertEqual("ADMITTED", admitted["decision"]["decision"])

        evidence = _manifest(
            revision=2,
            supersedes=admitted["event"]["manifest_sha256"],
            evidence=True,
        )
        evidence_path = self._write_json("candidate-v2.json", evidence)
        review_path = self._write_json("human-review.json", _review_for(evidence))

        self.assertTrue(
            self._corpus("validate", "--manifest", evidence_path)["valid"])
        self.assertEqual(
            "INTAKEN",
            self._corpus(
                "intake", "--manifest", evidence_path,
                "--root", self.corpus)["status"],
        )

        promoted = self._corpus(
            "promote", "--id", evidence["corpus_id"], "--root", self.corpus,
            "--review", review_path,
            "--evidence-root", self.evidence,
            "--now", "2026-07-16T16:02:00+09:00")
        self.assertEqual("ADMITTED", promoted["decision"]["decision"])

        self.assertTrue(
            self._corpus("verify-ledger", "--root", self.corpus)["valid"])
        health = self._corpus("health", "--root", self.corpus)
        self.assertTrue(health["ledger_valid"])
        self.assertEqual(1, health["counts"]["items"])
        self.assertEqual(1, health["counts"]["generative_admitted"])
        self.assertEqual(1, health["counts"]["evidence_admitted"])
        self.assertEqual(0, health["counts"]["quarantined"])

        status = self._corpus("status", "--root", self.corpus)
        self.assertEqual(2, status["event_count"])
        self.assertEqual("ADMITTED", status["items"][0]["generative"])
        self.assertEqual("ADMITTED", status["items"][0]["evidence"])


if __name__ == "__main__":
    unittest.main()
