import json
import os
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_schema import schema_path, validate_against_schema
from scripts.corpus.parity_evidence_builder import DEFAULT_PACKS, build_bundle


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "seed", "corpus", "phase3-2026-01-experiments.json")
CORPUS_ROOT = os.path.join(ROOT, "seed", "corpus")
NOW = "2026-07-16T00:00:00Z"


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class TestParityEvidenceBuilder(unittest.TestCase):
    def test_builds_representative_source_locks_and_machine_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            report, problems = build_bundle(
                ROOT, REGISTRY, CORPUS_ROOT, tmp, packs=DEFAULT_PACKS, now=NOW)
            self.assertIsNotNone(report)
            self.assertEqual(len(report["packs"]), 5)
            self.assertTrue(problems)
            self.assertTrue(any("machine_status_not_substantiated" in p for p in problems))

            for pack in report["packs"]:
                self.assertEqual(len(pack["source_locks"]), 2, pack)
                self.assertEqual(len(pack["machine_evidence"]), 2, pack)
                for rel in pack["source_locks"]:
                    doc = load_json(os.path.join(tmp, rel))
                    self.assertEqual(
                        validate_against_schema(doc, schema_path(ROOT, "source-lock")),
                        [],
                    )
                    self.assertEqual(doc["captured_at"], NOW)
                for rel in pack["machine_evidence"]:
                    doc = load_json(os.path.join(tmp, rel))
                    self.assertEqual(
                        validate_against_schema(doc, schema_path(ROOT, "machine-evidence")),
                        [],
                    )
                    self.assertEqual(doc["source_lock_id"].replace("source:", "machine:"), doc["evidence_id"])

    def test_refuses_nondeterministic_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build_bundle(ROOT, REGISTRY, CORPUS_ROOT, tmp, packs=DEFAULT_PACKS, now=None)


if __name__ == "__main__":
    unittest.main()
