import json
import os
import unittest

import tests._path  # noqa: F401
from engines.explore import adapter as A
from core.helix_ledger import is_consumed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "examples", "explore_state")


def load(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return json.load(f)


class TestExploreAdapter(unittest.TestCase):
    def test_winner_to_candidate(self):
        s6 = load("stage6_final.json")
        chain = A.evx_manifest_to_source_chain(load("manifest.json"))
        cand = A.evx_winner_to_candidate(s6["consensus_winner"], chain)
        self.assertEqual(cand["idea_id"], "IDEA-018")
        self.assertEqual(cand["origin"], "explore")
        self.assertEqual(cand["source_chain"]["cix"], "CIX-20260609-001")

    def test_manifest_to_chain(self):
        chain = A.evx_manifest_to_source_chain(load("manifest.json"))
        self.assertEqual(chain["evx"], "EVX-20260610-001")
        self.assertEqual(chain["sdx_catalog"], "v2")
        self.assertNotIn(None, chain.values())

    def test_idea_pool_to_pool(self):
        pool = A.idea_pool_to_pool(load("idea_pool.json"))
        self.assertEqual(len(pool), 4)
        self.assertTrue(all("title" in it and "domains" in it for it in pool))

    def test_idea_pool_to_pool_accepts_live_innovation_shape(self):
        pool = A.idea_pool_to_pool({
            "innovation": {
                "round_id": "CIX-20260702-001",
                "ideas": [
                    {
                        "id": "IDEA-001",
                        "title": "AI Operations Autonomous Compatibility Mesh (L6)",
                        "domains": ["aiops", "governance"],
                        "system_description": "Compatibility verifier for autonomous operations.",
                        "source_insight_id": "INSIGHT-001",
                    }
                ],
            }
        })
        self.assertEqual(len(pool), 1)
        self.assertEqual(pool[0]["id"], "IDEA-001")
        self.assertEqual(pool[0]["title"], "AI Operations Autonomous Compatibility Mesh (L6)")
        self.assertEqual(pool[0]["domains"], ["aiops", "governance"])

    def test_consumed_yaml_to_ledger_indexes(self):
        ledger = A.consumed_yaml_to_ledger(load("consumed_ideas.json"))
        self.assertEqual(len(ledger["consumed"]), 1)
        # aliases promoted into blocked_names by reindex
        self.assertIn("agentpact", ledger["blocked_names"])
        self.assertIn("pact", ledger["blocked_names"])
        # the recorded idea is self-detected as consumed
        r = is_consumed({"title": "AgentPACT"}, ledger)
        self.assertTrue(r["consumed"])

    def test_fresh_winner_not_consumed(self):
        ledger = A.consumed_yaml_to_ledger(load("consumed_ideas.json"))
        cand = A.evx_winner_to_candidate(load("stage6_final.json")["consensus_winner"])
        self.assertFalse(is_consumed(cand, ledger)["consumed"])

    def test_winner_to_consumed_entry(self):
        entry = A.evx_winner_to_consumed_entry(
            load("stage6_final.json")["consensus_winner"],
            source_chain={"cix": "CIX-1"},
            implementations=[{"project_name": "TimeBox", "project_path": "timebox"}],
            semantic_family="timebox-family")
        self.assertEqual(entry["origin"], "explore")
        self.assertTrue(entry["implementations"])


if __name__ == "__main__":
    unittest.main()
