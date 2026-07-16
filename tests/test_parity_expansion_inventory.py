import os
import unittest

import tests._path  # noqa: F401
from scripts.corpus.parity_expansion_inventory import build_inventory, validate_inventory
from scripts.condense.machine_probe_dataset import required_platforms_available


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_ROOT = os.path.join(ROOT, "seed", "parity-provenance")
NOW = "2026-07-16T00:00:00Z"


class TestParityExpansionInventory(unittest.TestCase):
    def test_tracked_inventory_is_valid_without_platform_checkouts(self):
        import json
        with open(os.path.join(EVIDENCE_ROOT, "expansion-inventory.json"), encoding="utf-8") as handle:
            inventory = json.load(handle)
        self.assertEqual(validate_inventory(inventory), [])
        self.assertEqual(inventory["counts"]["packs"], 62)

    @unittest.skipUnless(required_platforms_available(ROOT), "live platform repos are not checked out")
    def test_builds_62_pack_inventory(self):
        inventory = build_inventory(ROOT, EVIDENCE_ROOT, NOW)
        self.assertEqual(validate_inventory(inventory), [])
        self.assertEqual(inventory["counts"]["packs"], 62)
        self.assertEqual(inventory["counts"]["by_status"], {
            "BLOCKED": 4,
            "PENDING": 46,
            "VALID": 12,
        })
        self.assertEqual(inventory["counts"]["by_platform"]["Attestra"]["VALID"], 11)
        self.assertEqual(inventory["counts"]["by_platform"]["Clearstra"]["VALID"], 1)
        self.assertEqual(inventory["counts"]["by_platform"]["Routestra"]["BLOCKED"], 1)

    @unittest.skipUnless(required_platforms_available(ROOT), "live platform repos are not checked out")
    def test_pending_entries_do_not_claim_evidence(self):
        inventory = build_inventory(ROOT, EVIDENCE_ROOT, NOW)
        pending = [entry for entry in inventory["entries"] if entry["status"] == "PENDING"]
        self.assertEqual(len(pending), 46)
        self.assertTrue(all(entry["evidence"] == {} for entry in pending))


if __name__ == "__main__":
    unittest.main()
