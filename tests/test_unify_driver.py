import json
import os
import unittest

import tests._path  # noqa: F401
from engines.unify import merge_ledgers, build_unified_ledger
from engines.explore import adapter as EX
from engines.exploit import adapter as XP
from core.helix_ledger import is_consumed
import helix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


class TestUnify(unittest.TestCase):
    def setUp(self):
        self.explore = EX.consumed_yaml_to_ledger(
            _load("examples", "explore_state", "consumed_ideas.json"))
        self.exploit = XP.registry_to_ledger(
            _load("examples", "exploit_state", "registry.json"))

    def test_merge_unions_both_origins(self):
        merged = build_unified_ledger(self.explore, self.exploit)
        origins = {e["origin"] for e in merged["consumed"]}
        self.assertEqual(origins, {"explore", "exploit"})
        self.assertEqual(len(merged["consumed"]), 2)

    def test_merge_dedups_by_idea_id(self):
        merged = merge_ledgers(self.explore, self.explore)  # same ledger twice
        self.assertEqual(len(merged["consumed"]), 1)

    def test_merged_indexes_detect_both(self):
        merged = build_unified_ledger(self.explore, self.exploit)
        self.assertTrue(is_consumed({"title": "AgentPACT"}, merged)["consumed"])
        self.assertTrue(is_consumed({"title": "WithheldActionWitness"}, merged)["consumed"])

    def test_merge_deterministic(self):
        a = build_unified_ledger(self.explore, self.exploit)
        b = build_unified_ledger(self.explore, self.exploit)
        self.assertEqual(a, b)


class TestDriver(unittest.TestCase):
    def test_build_report_over_fixtures(self):
        r = helix.build_report()  # defaults to examples/
        self.assertEqual(r["ledger_origins"], {"explore": 1, "exploit": 1})
        self.assertEqual(r["pool_size"], 4 + 3)  # 4 explore ideas + 3 exploit candidates
        # the explore winner (IDEA-018) is fresh -> not yet consumed
        self.assertFalse(r["winner"]["already_consumed"])
        # AgentPACT is an implemented explore winner -> base-pairing feedback to corpus
        self.assertTrue(any(c["project"] == "AgentPACT" for c in r["corpus_feedback"]))
        # corpus has matured (exploit entry + AgentPACT fed back) and last engine was
        # explore -> the loop recombines via exploit (compound), not re-explore.
        self.assertEqual(r["next_action"]["action"], "RUN_EXPLOIT")

    def test_report_deterministic(self):
        self.assertEqual(helix.build_report(), helix.build_report())


if __name__ == "__main__":
    unittest.main()
