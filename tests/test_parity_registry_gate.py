import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from scripts.corpus.parity_registry_gate import validate_parity_registry


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "seed", "parity-provenance")


class TestParityRegistryGate(unittest.TestCase):
    def test_seed_registry_is_valid(self):
        problems = validate_parity_registry(
            ROOT,
            os.path.join(SEED, "evidence-registry.json"),
            os.path.join(SEED, "representative-pilot-report.json"),
        )
        self.assertEqual(problems, [])

    def test_tampered_valid_status_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            copied = os.path.join(tmp, "seed", "parity-provenance")
            shutil.copytree(SEED, copied)
            registry_path = os.path.join(copied, "evidence-registry.json")
            report_path = os.path.join(copied, "representative-pilot-report.json")
            with open(registry_path, encoding="utf-8") as handle:
                registry = json.load(handle)
            for entry in registry["entries"]:
                if entry["pack"] == "AuthorityArbiter":
                    entry["status"] = "VALID"
                    break
            with open(registry_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(registry, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            problems = validate_parity_registry(ROOT, registry_path, report_path)
            self.assertTrue(any("VALID entry" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
