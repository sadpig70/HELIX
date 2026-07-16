import json
import os
import shutil
import subprocess
import tempfile
import unittest

from core.helix_corpus_supply import (
    admit_item,
    corpus_cli,
    corpus_health,
    corpus_status,
    decide_admission,
    digest,
    intake_manifest,
    manifest_digest,
    migrate_legacy_project_list,
    revision_path,
    validate_manifest,
    verify_ledger,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def manifest(corpus_id="HC-TEST-001", revision=1, source="source-a",
             evidence=False, supersedes=None):
    doc = {
        "schema": "helix-corpus-manifest/1.0",
        "corpus_id": corpus_id,
        "revision": revision,
        "name": "ExampleProject",
        "summary": "A deterministic example project.",
        "origin": {
            "kind": "external_repo",
            "locator": "owner/repo",
            "revision": "a" * 40,
            "license": "MIT",
            "license_verified": True,
            "license_evidence": "LICENSE",
            "license_evidence_sha256": digest("MIT license bytes"),
            "source_evidence": source + ".bin",
            "source_sha256": digest(source),
        },
        "character": {
            "domain": "migration",
            "primary_verb": "transform",
            "input_shape": "dependency_graph",
            "output_shape": "staged_plan",
        },
        "genes": ["dependency_closure"],
        "dependencies": [],
        "restrictions": [],
        "machine": {
            "status": "substantiated" if evidence else "hypothesis",
            "label": "state-transition-planner",
            "evidence": ["src/core.py:plan"] if evidence else [],
        },
        "verification": {
            "reproducible": evidence,
            "tests_passed": evidence,
            "deterministic": evidence,
            "parity_available": False,
            "reproduction_command": "python -m unittest" if evidence else "",
            "behavior_sha256": digest("fixture-output") if evidence else "",
            "supporting_files": ["src/core.py"] if evidence else [],
            "supporting_symbols": ["plan"] if evidence else [],
        },
        "safety": {
            "secret_scan_passed": True,
            "pii_scan_passed": True,
            "malware_scan_passed": True,
            "execution_isolated": True,
        },
        "provenance": ["repository:owner/repo", "commit:" + "a" * 40],
    }
    if revision > 1:
        doc["supersedes_manifest_sha256"] = supersedes or "0" * 64
    return doc


def review_for(doc, verdict="approved"):
    return {
        "schema": "helix-corpus-review-receipt/1.0",
        "corpus_id": doc["corpus_id"],
        "manifest_sha256": manifest_digest(doc),
        "reviewer": {"kind": "human", "id": "reviewer-1"},
        "verdict": verdict,
        "reviewed_at": "2026-07-15T10:00:00+09:00",
        "notes": "Evidence inspected.",
    }


class CorpusSupplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="helix-corpus-")
        self.corpus = os.path.join(self.tmp, "corpus")
        for name in ("source-a", "different", "same"):
            with open(os.path.join(self.tmp, name + ".bin"), "w", encoding="utf-8") as handle:
                handle.write(name)
        with open(os.path.join(self.tmp, "LICENSE"), "w", encoding="utf-8") as handle:
            handle.write("MIT license bytes")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_json(self, name, value):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle)
        return path

    def test_manifest_contract_and_safe_id(self):
        self.assertEqual([], validate_manifest(ROOT, manifest()))
        bad = manifest(corpus_id="../escape")
        self.assertIn("corpus_id: must match HC-[A-Z0-9-]+",
                      validate_manifest(ROOT, bad))

    def test_intake_is_idempotent_and_revisions_are_immutable(self):
        first = manifest()
        result = intake_manifest(ROOT, self.corpus, first)
        self.assertEqual("INTAKEN", result["status"])
        self.assertTrue(os.path.exists(revision_path(self.corpus, first["corpus_id"], 1)))
        self.assertEqual("EXISTS", intake_manifest(ROOT, self.corpus, first)["status"])
        changed_same_revision = manifest(source="different")
        with self.assertRaisesRegex(ValueError, "higher revision"):
            intake_manifest(ROOT, self.corpus, changed_same_revision)
        second = manifest(revision=2, source="different", evidence=True)
        self.assertEqual("INTAKEN", intake_manifest(ROOT, self.corpus, second)["status"])
        self.assertTrue(os.path.exists(revision_path(self.corpus, second["corpus_id"], 2)))

    def test_generative_admission_is_hash_chained_and_idempotent(self):
        doc = manifest()
        intake_manifest(ROOT, self.corpus, doc)
        first = admit_item(ROOT, self.corpus, doc["corpus_id"], "generative",
                           "2026-07-15T10:01:00+09:00", evidence_root=self.tmp)
        self.assertEqual("ADMITTED", first["decision"]["decision"])
        replay = admit_item(ROOT, self.corpus, doc["corpus_id"], "generative",
                            "2026-07-15T11:01:00+09:00", evidence_root=self.tmp)
        self.assertFalse(replay["added"])
        self.assertEqual(first["event"]["event_id"], replay["event"]["event_id"])
        ledger = os.path.join(self.corpus, "evidence", "admission-ledger.jsonl")
        self.assertEqual([], verify_ledger(ROOT, ledger))

    def test_duplicate_source_is_quarantined(self):
        first = manifest(corpus_id="HC-DUP-001", source="same")
        intake_manifest(ROOT, self.corpus, first)
        admitted = admit_item(ROOT, self.corpus, first["corpus_id"], "generative",
                              "2026-07-15T10:00:00+09:00", evidence_root=self.tmp)
        self.assertEqual("ADMITTED", admitted["decision"]["decision"])
        second = manifest(corpus_id="HC-DUP-002", source="same")
        intake_manifest(ROOT, self.corpus, second)
        refused = admit_item(ROOT, self.corpus, second["corpus_id"], "generative",
                             "2026-07-15T10:02:00+09:00", evidence_root=self.tmp)
        self.assertEqual("QUARANTINED", refused["decision"]["decision"])
        self.assertTrue(any(reason.startswith("duplicate_source:")
                            for reason in refused["decision"]["reasons"]))

    def test_evidence_promotion_requires_prior_admission_and_bound_review(self):
        evidence_doc = manifest(revision=2, evidence=True)
        intake_manifest(ROOT, self.corpus, evidence_doc)
        no_prior = decide_admission(ROOT, self.corpus, evidence_doc, "evidence",
                                    review_for(evidence_doc), self.tmp)
        self.assertIn("prior_generative_admission_required", no_prior["reasons"])

        other_root = os.path.join(self.tmp, "second")
        generative = manifest()
        intake_manifest(ROOT, other_root, generative)
        generative_event = admit_item(
            ROOT, other_root, generative["corpus_id"], "generative",
            "2026-07-15T10:00:00+09:00", evidence_root=self.tmp)
        evidence_doc["supersedes_manifest_sha256"] = generative_event["event"]["manifest_sha256"]
        intake_manifest(ROOT, other_root, evidence_doc)
        promoted = admit_item(ROOT, other_root, evidence_doc["corpus_id"], "evidence",
                              "2026-07-15T10:03:00+09:00", review_for(evidence_doc), self.tmp)
        self.assertEqual("ADMITTED", promoted["decision"]["decision"])
        status = corpus_status(ROOT, other_root)
        self.assertEqual("ADMITTED", status["items"][0]["generative"])
        self.assertEqual("ADMITTED", status["items"][0]["evidence"])

    def test_review_hash_mismatch_fails_closed(self):
        doc = manifest()
        intake_manifest(ROOT, self.corpus, doc)
        generative_event = admit_item(
            ROOT, self.corpus, doc["corpus_id"], "generative",
            "2026-07-15T10:00:00+09:00", evidence_root=self.tmp)
        evidence_doc = manifest(revision=2, evidence=True)
        evidence_doc["supersedes_manifest_sha256"] = generative_event["event"]["manifest_sha256"]
        intake_manifest(ROOT, self.corpus, evidence_doc)
        review = review_for(evidence_doc)
        review["manifest_sha256"] = "0" * 64
        result = decide_admission(ROOT, self.corpus, evidence_doc, "evidence", review, self.tmp)
        self.assertEqual("QUARANTINED", result["decision"])
        self.assertIn("review_manifest_hash_mismatch", result["reasons"])

    def test_declared_hash_without_matching_bytes_fails_closed(self):
        doc = manifest()
        doc["origin"]["source_sha256"] = "f" * 64
        intake_manifest(ROOT, self.corpus, doc)
        result = decide_admission(
            ROOT, self.corpus, doc, "generative", evidence_root=self.tmp)
        self.assertEqual("QUARANTINED", result["decision"])
        self.assertIn("source_evidence_hash_mismatch", result["reasons"])

    def test_evidence_path_cannot_escape_injected_root(self):
        doc = manifest()
        doc["origin"]["source_evidence"] = "../outside.bin"
        intake_manifest(ROOT, self.corpus, doc)
        result = decide_admission(
            ROOT, self.corpus, doc, "generative", evidence_root=self.tmp)
        self.assertEqual("QUARANTINED", result["decision"])
        self.assertIn("source_evidence_path_escape", result["reasons"])

    def test_evidence_revision_must_bind_prior_generative_manifest(self):
        doc = manifest()
        intake_manifest(ROOT, self.corpus, doc)
        admit_item(ROOT, self.corpus, doc["corpus_id"], "generative",
                   "2026-07-15T10:00:00+09:00", evidence_root=self.tmp)
        evidence_doc = manifest(revision=2, evidence=True, supersedes="0" * 64)
        intake_manifest(ROOT, self.corpus, evidence_doc)
        result = decide_admission(
            ROOT, self.corpus, evidence_doc, "evidence",
            review_for(evidence_doc), self.tmp)
        self.assertEqual("QUARANTINED", result["decision"])
        self.assertIn("prior_manifest_binding_mismatch", result["reasons"])

    def test_tampered_ledger_is_detected_and_blocks_append(self):
        doc = manifest()
        intake_manifest(ROOT, self.corpus, doc)
        admit_item(ROOT, self.corpus, doc["corpus_id"], "generative",
                   "2026-07-15T10:00:00+09:00", evidence_root=self.tmp)
        ledger = os.path.join(self.corpus, "evidence", "admission-ledger.jsonl")
        with open(ledger, "r", encoding="utf-8") as handle:
            row = json.loads(handle.readline())
        row["decision"] = "QUARANTINED"
        with open(ledger, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        self.assertTrue(verify_ledger(ROOT, ledger))
        with self.assertRaisesRegex(ValueError, "ledger invalid"):
            admit_item(ROOT, self.corpus, doc["corpus_id"], "generative",
                       "2026-07-15T10:01:00+09:00", evidence_root=self.tmp)

    def test_legacy_migration_is_honest_and_does_not_admit(self):
        source = os.path.join(self.tmp, "project_list.md")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write("# Project List\n\n- **Alpha** (alpha): First project.\n")
        rows = migrate_legacy_project_list(source)
        self.assertEqual(1, len(rows))
        self.assertEqual("hypothesis", rows[0]["machine"]["status"])
        self.assertFalse(rows[0]["origin"]["license_verified"])
        self.assertEqual([], validate_manifest(ROOT, rows[0]))
        self.assertIn("license_unverified", decide_admission(
            ROOT, self.corpus, rows[0], "generative", evidence_root=self.tmp)["reasons"])
        self.assertFalse(os.path.exists(os.path.join(
            self.corpus, "evidence", "admission-ledger.jsonl")))

    def test_health_reports_dual_tier_counts(self):
        doc = manifest()
        intake_manifest(ROOT, self.corpus, doc)
        admit_item(ROOT, self.corpus, doc["corpus_id"], "generative",
                   "2026-07-15T10:00:00+09:00", evidence_root=self.tmp)
        report = corpus_health(ROOT, self.corpus)
        self.assertTrue(report["ledger_valid"])
        self.assertEqual(1, report["counts"]["generative_admitted"])
        self.assertEqual(0, report["counts"]["evidence_admitted"])

    def test_cli_validate_intake_admit_and_status(self):
        doc = manifest()
        path = self.write_json("manifest.json", doc)
        code, payload = corpus_cli(["validate", "--manifest", path], ROOT)
        self.assertEqual(0, code, payload)
        code, payload = corpus_cli(
            ["intake", "--manifest", path, "--root", self.corpus], ROOT)
        self.assertEqual(0, code, payload)
        code, payload = corpus_cli([
            "admit", "--id", doc["corpus_id"], "--root", self.corpus,
            "--now", "2026-07-15T10:00:00+09:00",
            "--evidence-root", self.tmp], ROOT)
        self.assertEqual(0, code, payload)
        completed = subprocess.run(
            ["python", "helix.py", "corpus", "status", "--root", self.corpus],
            cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual("ADMITTED", output["items"][0]["generative"])


if __name__ == "__main__":
    unittest.main()
