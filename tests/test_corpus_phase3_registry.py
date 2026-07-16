import copy
import hashlib
import json
import os
import tempfile
import unittest

from core.helix_corpus_supply import digest
from scripts.corpus.phase3_registry import freeze_registry, validate_registry


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_ROOT = os.path.join(ROOT, "seed", "corpus")
REGISTRY_PATH = os.path.join(CORPUS_ROOT, "phase3-2026-01-experiments.json")


def registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


class CorpusPhase3RegistryTests(unittest.TestCase):
    def test_frozen_registry_is_valid_and_exactly_six_slots(self):
        value = registry()
        self.assertEqual([], validate_registry(ROOT, CORPUS_ROOT, value))
        self.assertEqual(6, len(value["slots"]))
        self.assertEqual(6, len({slot["lead_verb"] for slot in value["slots"]}))

    def test_duplicate_verb_and_wrong_pipeline_fail_closed(self):
        value = registry()
        value["slots"][1]["lead_verb"] = value["slots"][0]["lead_verb"]
        value["slots"][0]["pipeline"] = list(reversed(value["slots"][0]["pipeline"]))
        problems = validate_registry(ROOT, CORPUS_ROOT, value)
        self.assertTrue(any("lead verbs must be unique" in problem for problem in problems))
        self.assertTrue(any("pipeline order" in problem for problem in problems))

    def test_stale_gene_binding_and_domain_collapse_fail_closed(self):
        value = registry()
        value["slots"][0]["gene_bindings"][0]["manifest_sha256"] = "0" * 64
        value["slots"][1]["domain_signature"] = copy.deepcopy(value["slots"][0]["domain_signature"])
        problems = validate_registry(ROOT, CORPUS_ROOT, value)
        self.assertTrue(any("stale manifest binding" in problem for problem in problems))
        self.assertTrue(any("pairwise domain distance" in problem for problem in problems))

    def test_freeze_receipt_binds_registry_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="helix-phase3-freeze-", dir=ROOT) as tmp:
            pilot_report = os.path.join(tmp, "pilot-report.json")
            with open(pilot_report, "w", encoding="utf-8", newline="\n") as handle:
                json.dump({"verdict": "READY_FOR_PHASE_3"}, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
            with open(pilot_report, "rb") as handle:
                pilot_report_sha = hashlib.sha256(handle.read()).hexdigest()

            registry_copy = registry()
            registry_copy["source_pilot"]["report"] = pilot_report
            registry_copy["source_pilot"]["report_sha256"] = pilot_report_sha
            registry_path = os.path.join(tmp, "phase3-registry.json")
            with open(registry_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(registry_copy, handle, ensure_ascii=False, indent=2)
                handle.write("\n")

            out = os.path.join(tmp, "freeze.json")
            receipt, problems = freeze_registry(
                registry_path, CORPUS_ROOT, pilot_report, out,
                "2026-07-15T22:00:00+09:00")
            self.assertEqual([], problems)
            self.assertEqual("FROZEN_READY_TO_EXECUTE", receipt["verdict"])
            self.assertEqual(digest(registry_copy), receipt["registry_sha256"])
            second, problems = freeze_registry(
                registry_path, CORPUS_ROOT, pilot_report, out,
                "2026-07-15T22:00:01+09:00")
            self.assertIsNone(second)
            self.assertTrue(any("refusing to overwrite" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
