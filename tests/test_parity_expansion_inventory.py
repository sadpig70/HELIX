import os
import unittest

import tests._path  # noqa: F401
from scripts.corpus.parity_expansion_inventory import build_inventory, validate_inventory


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_ROOT = os.path.join(ROOT, "seed", "parity-provenance")
NOW = "2026-07-16T00:00:00Z"


class TestParityExpansionInventory(unittest.TestCase):
    def test_builds_62_pack_inventory(self):
        inventory = build_inventory(ROOT, EVIDENCE_ROOT, NOW)
        self.assertEqual(validate_inventory(inventory), [])
        self.assertEqual(inventory["counts"]["packs"], 62)
        self.assertEqual(inventory["counts"]["by_status"], {
            "BLOCKED": 4,
            "PENDING": 57,
            "VALID": 1,
        })
        self.assertEqual(inventory["counts"]["by_platform"]["Attestra"]["VALID"], 1)
        self.assertEqual(inventory["counts"]["by_platform"]["Routestra"]["BLOCKED"], 1)

    def test_pending_entries_do_not_claim_evidence(self):
        inventory = build_inventory(ROOT, EVIDENCE_ROOT, NOW)
        pending = [entry for entry in inventory["entries"] if entry["status"] == "PENDING"]
        self.assertEqual(len(pending), 57)
        self.assertTrue(all(entry["evidence"] == {} for entry in pending))


if __name__ == "__main__":
    unittest.main()
