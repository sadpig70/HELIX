import json
import os
import shutil
import tempfile
import unittest

from core.helix_corpus_supply import admit_item, digest, intake_manifest
from scripts.corpus.build_snapshot import build_snapshot, write_snapshot
from scripts.corpus.pilot_registry import registry_template, validate_registry
from scripts.corpus.pilot_report import build_report, markdown
from tests.test_corpus_supply import manifest, review_for


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGIN_KIND = {
    "external_oss": "external_repo",
    "helix_generated": "helix_generated",
    "operational_problem": "operational_problem",
    "failure_refutation": "failure",
    "research_mechanism": "research",
}


class CorpusPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="helix-corpus-pilot-")
        self.corpus = os.path.join(self.tmp, "corpus")
        with open(os.path.join(self.tmp, "LICENSE"), "w", encoding="utf-8") as handle:
            handle.write("MIT license bytes")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_registry_template_freezes_exact_source_mix(self):
        registry = registry_template()
        self.assertEqual([], validate_registry(ROOT, registry))
        self.assertEqual(24, len(registry["slots"]))
        registry["slots"].pop()
        problems = validate_registry(ROOT, registry)
        self.assertTrue(any("slot count must be 24" in problem for problem in problems))
        self.assertTrue(any("missing fixed slots" in problem for problem in problems))

    def test_registry_rejects_candidate_substitution_and_duplicates(self):
        registry = registry_template()
        first, second = registry["slots"][:2]
        for slot in (first, second):
            slot["status"] = "selected"
            slot["candidate"] = {
                "name": slot["corpus_id"],
                "locator": "owner/repo",
                "revision": "a" * 40,
                "evidence_root": ".helix/evidence",
            }
        second["corpus_id"] = "HC-PILOT-EXT-999"
        problems = validate_registry(ROOT, registry)
        self.assertTrue(any("unexpected fixed slots" in problem for problem in problems))
        self.assertTrue(any("duplicate candidate" in problem for problem in problems))

    def test_source_snapshot_is_deterministic_and_excludes_runtime_files(self):
        source = os.path.join(self.tmp, "source")
        os.makedirs(os.path.join(source, ".git"))
        os.makedirs(os.path.join(source, "src"))
        with open(os.path.join(source, "src", "b.txt"), "w", encoding="utf-8") as handle:
            handle.write("B")
        with open(os.path.join(source, "a.txt"), "w", encoding="utf-8") as handle:
            handle.write("A")
        with open(os.path.join(source, ".git", "HEAD"), "w", encoding="utf-8") as handle:
            handle.write("ignored")
        first = build_snapshot(source, "a" * 40)
        second = build_snapshot(source, "a" * 40)
        self.assertEqual(first, second)
        self.assertEqual(["a.txt", "src/b.txt"], [row["path"] for row in first["files"]])
        out1 = os.path.join(self.tmp, "one.json")
        out2 = os.path.join(self.tmp, "two.json")
        self.assertEqual(write_snapshot(out1, first), write_snapshot(out2, second))

    def test_report_reaches_phase3_gate_from_ledger_truth(self):
        registry = registry_template()
        generative_events = {}
        for index, slot in enumerate(registry["slots"]):
            source = f"source-{index:02d}"
            with open(os.path.join(self.tmp, source + ".bin"), "w", encoding="utf-8") as handle:
                handle.write(source)
            slot["status"] = "selected"
            slot["candidate"] = {
                "name": slot["corpus_id"],
                "locator": f"pilot/{index:02d}",
                "revision": f"{index + 1:040x}",
                "evidence_root": self.tmp,
            }
            doc = manifest(corpus_id=slot["corpus_id"], source=source)
            doc["origin"]["kind"] = ORIGIN_KIND[slot["source_class"]]
            doc["origin"]["locator"] = slot["candidate"]["locator"]
            doc["origin"]["revision"] = slot["candidate"]["revision"]
            doc["provenance"] = [
                "pilot:" + registry["pilot_id"],
                "revision:" + slot["candidate"]["revision"],
            ]
            intake_manifest(ROOT, self.corpus, doc)
            if index < 12:
                result = admit_item(
                    ROOT, self.corpus, slot["corpus_id"], "generative",
                    f"2026-07-15T10:{index:02d}:00+09:00", evidence_root=self.tmp)
                generative_events[slot["corpus_id"]] = result["event"]

        for index, slot in enumerate(registry["slots"][:5]):
            source = f"source-{index:02d}"
            evidence_doc = manifest(
                corpus_id=slot["corpus_id"], revision=2, source=source, evidence=True,
                supersedes=generative_events[slot["corpus_id"]]["manifest_sha256"])
            evidence_doc["origin"]["kind"] = ORIGIN_KIND[slot["source_class"]]
            evidence_doc["origin"]["locator"] = slot["candidate"]["locator"]
            evidence_doc["origin"]["revision"] = slot["candidate"]["revision"]
            evidence_doc["provenance"] = ["pilot:" + registry["pilot_id"]]
            intake_manifest(ROOT, self.corpus, evidence_doc)
            admit_item(
                ROOT, self.corpus, slot["corpus_id"], "evidence",
                f"2026-07-15T11:{index:02d}:00+09:00",
                review_for(evidence_doc), self.tmp)

        report = build_report(ROOT, registry, self.corpus)
        self.assertEqual("READY_FOR_PHASE_3", report["verdict"])
        self.assertEqual(24, report["counts"]["provenance_bound"])
        self.assertEqual(12, report["counts"]["generative_admitted"])
        self.assertEqual(5, report["counts"]["evidence_admitted"])
        self.assertEqual(17, report["counts"]["decision_events"])
        self.assertEqual({}, report["decision_reason_counts"])
        self.assertIn("Diversity baseline", markdown(report))

    def test_report_fails_closed_on_tampered_ledger(self):
        registry = registry_template()
        os.makedirs(os.path.join(self.corpus, "evidence"), exist_ok=True)
        ledger = os.path.join(self.corpus, "evidence", "admission-ledger.jsonl")
        with open(ledger, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"bad": True}) + "\n")
        report = build_report(ROOT, registry, self.corpus)
        self.assertEqual("PILOT_FAILED", report["verdict"])
        self.assertFalse(report["gates"]["ledger_valid"])


if __name__ == "__main__":
    unittest.main()
