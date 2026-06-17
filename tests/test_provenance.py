import unittest

import tests._path  # noqa: F401
from core.helix_provenance import trace_winner, winner_to_corpus_entry


class TestProvenance(unittest.TestCase):
    def test_trace_explore_winner(self):
        winner = {
            "idea_id": "IDEA-018", "origin": "explore",
            "source_insight_id": "INS-L10-003",
            "source_chain": {"evx": "EVX-1", "cix": "CIX-1", "idx": "IDX-1",
                             "tcx": "TCX-1", "sdx_catalog": "v2"},
            "source_channels": ["CH-0001"],
        }
        lineage = trace_winner(winner)
        layers = [step["layer"] for step in lineage]
        self.assertEqual(layers[0], "winner")
        self.assertIn("insight", layers)
        self.assertIn("cix", layers)
        self.assertIn("channel", layers)
        # ordering: evx before cix before idx before tcx
        idx_evx = layers.index("evx")
        idx_cix = layers.index("cix")
        idx_tcx = layers.index("tcx")
        self.assertLess(idx_evx, idx_cix)
        self.assertLess(idx_cix, idx_tcx)

    def test_trace_exploit_winner(self):
        winner = {
            "id": "GEN-WAW", "origin": "exploit", "seed_name": "WithheldActionWitness",
            "idea_trace": {"kernel_id": "IK-001"},
            "sources": ["PnR", "ADPR"], "parents": [],
        }
        lineage = trace_winner(winner)
        layers = [s["layer"] for s in lineage]
        self.assertIn("seed", layers)
        self.assertIn("kernel", layers)
        self.assertIn("corpus_source", layers)

    def test_winner_to_corpus_entry(self):
        consumed = {
            "idea_id": "IDEA-001", "title": "Agent PACT Mesh",
            "semantic_family": "agentops-mesh",
            "source_chain": {"cix": "CIX-1"},
            "implementations": [{"project_name": "AgentPACT", "project_path": "pact",
                                 "repo_url": "https://example.invalid/pact"}],
        }
        entry = winner_to_corpus_entry(consumed)
        self.assertEqual(entry["project"], "AgentPACT")
        self.assertEqual(entry["origin"], "explore")
        self.assertEqual(entry["from_idea_id"], "IDEA-001")
        self.assertEqual(entry["readme_hint"], "Agent PACT Mesh")

    def test_winner_to_corpus_entry_requires_impl(self):
        with self.assertRaises(ValueError):
            winner_to_corpus_entry({"idea_id": "X", "title": "vapor", "implementations": []})

    def test_deterministic(self):
        w = {"id": "A", "origin": "exploit", "sources": ["b", "a"]}
        self.assertEqual(trace_winner(w), trace_winner(w))


if __name__ == "__main__":
    unittest.main()
