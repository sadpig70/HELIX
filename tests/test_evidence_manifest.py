import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_evidence import (
    build_evidence_manifest,
    seal_manifest,
    verify_evidence_manifest,
    verify_manifest_seal,
)
from core.helix_schema import schema_features


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "evidence-manifest.schema.json")
EXAMPLES = os.path.join(ROOT, "examples", "constitution")
INTENT_NAME = "intent-r1-local-artifact.json"
MANIFEST_NAME = "evidence-r1-local-artifact.json"
ARTIFACT_SPECS = [
    {"role": "test_log",
     "path": "examples/constitution/artifacts/demo-test-log.txt",
     "provenance": {"origin": "command_output",
                    "reference": "python -m unittest discover -s tests -q"}},
    {"role": "state_snapshot",
     "path": "examples/constitution/artifacts/demo-state.json",
     "provenance": {"origin": "state_receipt", "reference": "8ea2534e"}},
]
ISSUER = {"kind": "system", "id": "helix-runtime"}


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as f:
        return json.load(f)


class EvidenceFixtureCase(unittest.TestCase):
    """Temp copy of repo fixtures so tests can tamper with artifact bytes."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-evidence-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("evidence-manifest", "action-intent"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        shutil.copytree(EXAMPLES, os.path.join(self.root, "examples",
                                               "constitution"))
        self.intent = _load(INTENT_NAME)
        self.manifest = build_evidence_manifest(
            self.root, "EVM-TEST-001", self.intent, ISSUER,
            copy.deepcopy(ARTIFACT_SPECS))

    def artifact_full(self, index=0):
        rel = self.manifest["artifacts"][index]["path"]
        return os.path.join(self.root, *rel.split("/"))


class TestBuildAndSeal(EvidenceFixtureCase):
    def test_build_is_deterministic(self):
        again = build_evidence_manifest(self.root, "EVM-TEST-001", self.intent,
                                        ISSUER, copy.deepcopy(ARTIFACT_SPECS))
        self.assertEqual(again, self.manifest)
        self.assertTrue(verify_manifest_seal(self.manifest))

    def test_built_manifest_verifies_with_intent_binding(self):
        self.assertEqual(
            verify_evidence_manifest(self.root, self.manifest, self.intent), [])

    def test_build_fails_fast_on_missing_artifact(self):
        specs = copy.deepcopy(ARTIFACT_SPECS)
        specs[0]["path"] = "examples/constitution/artifacts/absent.txt"
        with self.assertRaisesRegex(ValueError, "artifact missing"):
            build_evidence_manifest(self.root, "EVM-X", self.intent, ISSUER, specs)

    def test_build_rejects_empty_specs_and_duplicates(self):
        with self.assertRaisesRegex(ValueError, "at least one artifact"):
            build_evidence_manifest(self.root, "EVM-X", self.intent, ISSUER, [])
        specs = copy.deepcopy(ARTIFACT_SPECS)
        specs.append(copy.deepcopy(ARTIFACT_SPECS[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_evidence_manifest(self.root, "EVM-X", self.intent, ISSUER, specs)

    def test_build_requires_reference_for_receipt_origins(self):
        specs = copy.deepcopy(ARTIFACT_SPECS)
        specs[1]["provenance"]["reference"] = None
        with self.assertRaisesRegex(ValueError, "requires a reference"):
            build_evidence_manifest(self.root, "EVM-X", self.intent, ISSUER, specs)


class TestFailClosedVerification(EvidenceFixtureCase):
    def test_missing_artifact_on_disk_denies(self):
        os.remove(self.artifact_full(0))
        problems = verify_evidence_manifest(self.root, self.manifest, self.intent)
        self.assertTrue(any("missing on disk" in p and "DENY" in p
                            for p in problems), problems)

    def test_tampered_artifact_bytes_deny(self):
        with open(self.artifact_full(0), "a", encoding="utf-8") as f:
            f.write("tampered\n")
        problems = verify_evidence_manifest(self.root, self.manifest, self.intent)
        self.assertTrue(any("hash mismatch" in p and "DENY" in p
                            for p in problems), problems)

    def test_tampered_manifest_content_breaks_the_seal(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["artifacts"][0]["sha256"] = "0" * 64
        problems = verify_evidence_manifest(self.root, tampered, self.intent)
        self.assertTrue(any("seal is broken" in p for p in problems), problems)

    def test_reseal_after_tamper_still_fails_on_bytes(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["artifacts"][0]["sha256"] = "0" * 64
        tampered = seal_manifest(tampered)
        problems = verify_evidence_manifest(self.root, tampered, self.intent)
        self.assertTrue(any("hash mismatch" in p for p in problems), problems)

    def test_empty_artifact_list_can_never_authorize(self):
        empty = seal_manifest({**copy.deepcopy(self.manifest), "artifacts": []})
        problems = verify_evidence_manifest(self.root, empty, self.intent)
        self.assertTrue(any("empty evidence" in p for p in problems), problems)

    def test_intent_binding_mismatch_is_detected(self):
        other_intent = _load("intent-r2-publish.json")
        problems = verify_evidence_manifest(self.root, self.manifest, other_intent)
        self.assertTrue(any("intent binding mismatch" in p for p in problems),
                        problems)

    def test_receipt_origin_without_reference_is_rejected(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["artifacts"][1]["provenance"]["reference"] = None
        tampered = seal_manifest(tampered)
        problems = verify_evidence_manifest(self.root, tampered, self.intent)
        self.assertTrue(any("requires a reference" in p for p in problems),
                        problems)

    def test_blank_issuer_is_rejected(self):
        tampered = copy.deepcopy(self.manifest)
        tampered["issuer"]["id"] = "  "
        tampered = seal_manifest(tampered)
        problems = verify_evidence_manifest(self.root, tampered, self.intent)
        self.assertTrue(any("issuer.id" in p for p in problems), problems)


class TestRepoExample(unittest.TestCase):
    def test_schema_stays_in_stdlib_subset(self):
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema_features(schema), {"in_subset": True, "unsupported": []})

    def test_committed_example_verifies_against_real_bytes(self):
        manifest = _load(MANIFEST_NAME)
        intent = _load(INTENT_NAME)
        self.assertEqual(verify_evidence_manifest(ROOT, manifest, intent), [])


if __name__ == "__main__":
    unittest.main()
