"""Tests for v0.4 F4 SimKindThresholds + F7 ProvenanceLineage + loop-status CLI."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import tests._path  # noqa: F401
import helix
from core.helix_diversity import (
    measure_diversity, base_thresholds, DEFAULT_THRESHOLDS, LEXICAL_THRESHOLD_OVERRIDES,
)
from core.helix_provenance import winner_to_corpus_entry, trace_winner


# ---- F4 SimKindThresholds ----
class TestSimKindThresholds(unittest.TestCase):
    def test_lexical_baseline_lower_than_semantic(self):
        lex = base_thresholds("lexical")
        sem = base_thresholds("semantic")
        self.assertLess(lex["avg_embedding_sim"], sem["avg_embedding_sim"])
        self.assertLess(lex["winner_embedding_similarity"], sem["winner_embedding_similarity"])
        # scale-free signals identical across sim_kind
        self.assertEqual(lex["keyword_coverage"], sem["keyword_coverage"])
        self.assertEqual(lex["dup_cos"], sem["dup_cos"])

    def test_semantic_baseline_is_default(self):
        self.assertEqual(base_thresholds("semantic"), DEFAULT_THRESHOLDS)

    def test_report_uses_lexical_baseline_when_no_sim(self):
        rep = measure_diversity([{"title": "a b"}, {"title": "a c"}])
        self.assertEqual(rep["sim_kind"], "lexical")
        self.assertEqual(rep["thresholds"]["avg_embedding_sim"],
                         LEXICAL_THRESHOLD_OVERRIDES["avg_embedding_sim"])

    def test_report_uses_semantic_baseline_when_sim_injected(self):
        rep = measure_diversity([{"title": "a"}, {"title": "b"}], sim=lambda x, y: 0.5)
        self.assertEqual(rep["sim_kind"], "semantic")
        self.assertEqual(rep["thresholds"]["avg_embedding_sim"],
                         DEFAULT_THRESHOLDS["avg_embedding_sim"])

    def test_explicit_thresholds_still_override(self):
        rep = measure_diversity([{"title": "a"}, {"title": "b"}],
                                thresholds={"avg_embedding_sim": 0.99})
        self.assertEqual(rep["thresholds"]["avg_embedding_sim"], 0.99)


# ---- F7 ProvenanceLineage ----
class TestProvenanceLineage(unittest.TestCase):
    def test_corpus_entry_carries_full_lineage(self):
        consumed = {
            "idea_id": "IDEA-1", "title": "T",
            "source_chain": {"evx": "EVX-1", "cix": "CIX-1", "idx": "IDX-1",
                             "tcx": "TCX-1", "sdx_catalog": "v2"},
            "implementations": [{"project_name": "P", "project_path": "p"}],
        }
        entry = winner_to_corpus_entry(consumed)
        self.assertIn("lineage", entry)
        self.assertEqual(entry["lineage"], trace_winner(consumed))
        layers = [s["layer"] for s in entry["lineage"]]
        self.assertEqual(layers[0], "winner")
        self.assertIn("cix", layers)

    def test_lineage_ids_are_strings(self):
        entry = winner_to_corpus_entry({
            "idea_id": "IDEA-1", "title": "T", "source_chain": {"cix": "CIX-1"},
            "implementations": [{"project_name": "P"}]})
        for step in entry["lineage"]:
            self.assertIsInstance(step["id"], str)


# ---- F3 loop-status CLI smoke ----
class TestLoopStatusCli(unittest.TestCase):
    def test_loop_status_command(self):
        with tempfile.TemporaryDirectory() as d:
            ls = os.path.join(d, "loop-state.json")
            with open(ls, "w", encoding="utf-8") as f:
                json.dump({"turn": 1, "status": "active"}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = helix._main(["helix.py", "loop-status", "--loop-state", ls])
            self.assertEqual(rc, 0)
            out = json.loads(buf.getvalue())
            self.assertEqual(out["turn"], 1)
            self.assertFalse(out["stop"]["stop"])


if __name__ == "__main__":
    unittest.main()
