"""Tests for the codex-review (v0.3) improvements: actuator, repair semantics,
contract merge, live resolver, sim injection, deeper validators, calibration."""
import importlib
import json
import os
import sys
import tempfile
import unittest

import tests._path  # noqa: F401
import helix
from core.helix_diversity import measure_diversity, keyword_coverage
from core.helix_loop import next_action
from core.helix_provenance import winner_to_corpus_entry
from core.helix_validate import (
    validate_corpus_entry, validate_loop_state, validate_thresholds,
)
from core.helix_diversity import DEFAULT_THRESHOLDS
from engines.unify import merge_ledgers
from engines.loaders import resolve_latest
from engines.explore import adapter as EX

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---- P0-1 CloseLoopActuator ----
class TestCloseLoop(unittest.TestCase):
    def _winner(self):
        return {"id": "IDEA-777", "title": "Quantum Lichen Oracle"}

    def _impl(self):
        return {"project_name": "QuantumLichenOracle", "project_path": "qlo",
                "repo_url": "https://example.invalid/qlo"}

    def test_close_then_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "ledger.json")
            cor = os.path.join(d, "corpus.json")
            r1 = helix.close_loop(self._winner(), {"cix": "CIX-1"}, self._impl(),
                                  led, cor, now="2026-06-17T00:00:00+00:00")
            self.assertEqual(r1["status"], "closed")
            self.assertTrue(r1["corpus_added"])
            # ledger + corpus actually written
            self.assertTrue(os.path.exists(led) and os.path.exists(cor))
            with open(cor, encoding="utf-8") as f:
                self.assertEqual(json.load(f)[0]["project"], "QuantumLichenOracle")
            # rerun is a no-op
            r2 = helix.close_loop(self._winner(), {"cix": "CIX-1"}, self._impl(),
                                  led, cor, now="2026-06-17T01:00:00+00:00")
            self.assertEqual(r2["status"], "already_recorded")

    def test_corpus_append_idempotent_by_project(self):
        with tempfile.TemporaryDirectory() as d:
            cor = os.path.join(d, "corpus.json")
            e = {"project": "P", "origin": "explore"}
            self.assertTrue(helix.append_corpus_entry(cor, e))
            self.assertFalse(helix.append_corpus_entry(cor, e))


# ---- P0-2 DiversityRepairSemantics ----
class TestRepairSemantics(unittest.TestCase):
    def test_unique_ratio_collapse_sets_repair_below_min_breaches(self):
        # 2 items sharing 3/4 tokens -> Jaccard 0.6; thresholds isolate the
        # unique_ratio path so only the (single) keyword breach occurs, yet
        # repair_required must still fire from unique_ratio_below_floor.
        pool = [{"title": "policy drift dossier alpha"},
                {"title": "policy drift dossier beta"}]
        thr = {"dup_cos": 0.5, "unique_ratio_floor": 0.6, "avg_embedding_sim": 0.9}
        rep = measure_diversity(pool, thresholds=thr)
        self.assertLess(rep["signals"]["unique_ratio"], 0.6)
        self.assertTrue(rep["signals"]["unique_ratio_below_floor"])
        self.assertLess(rep["breaches"], rep["thresholds"]["min_breaches"])  # not "triggered"
        self.assertFalse(rep["triggered"])
        self.assertTrue(rep["repair_required"])                              # but repair fires

    def test_loop_acts_on_repair_required(self):
        a = next_action({"last_engine": "exploit", "corpus_size": 5,
                         "diversity": {"triggered": False, "repair_required": True}})
        self.assertEqual(a["action"], "REFRESH_INPUTS")

    def test_adaptive_k_reduces_oversensitivity(self):
        # distinct single-token items: k=10 covers the whole vocab (coverage 1.0),
        # while adaptive k (~sqrt(vocab)) does not -> the small-pool over-sensitivity fix.
        pool = [{"title": w} for w in
                ("alpha", "beta", "gamma", "delta", "epsilon", "zeta")]
        self.assertEqual(keyword_coverage(pool, k=10), 1.0)
        self.assertLess(keyword_coverage(pool), 1.0)


# ---- P1-1 LedgerMergeCollision ----
class TestMergeByContract(unittest.TestCase):
    def test_cross_engine_collision_merged(self):
        a = EX.consumed_yaml_to_ledger({"consumed_ideas": [
            {"idea_id": "E-1", "title": "Agent PACT", "aliases": ["PACT"],
             "semantic_family": "fam-x", "implementations": [{"project_name": "AgentPACT"}]}]})
        # different idea_id but same semantic_family -> contract collision
        b = EX.consumed_yaml_to_ledger({"consumed_ideas": [
            {"idea_id": "X-9", "title": "Different Name", "semantic_family": "fam-x",
             "implementations": [{"project_name": "OtherImpl"}]}]})
        merged = merge_ledgers(a, b)
        self.assertEqual(len(merged["consumed"]), 1)  # folded, not duplicated
        self.assertIn("X-9", merged["consumed"][0].get("merged_from", []))

    def test_distinct_entries_not_merged(self):
        a = EX.consumed_yaml_to_ledger({"consumed_ideas": [
            {"idea_id": "E-1", "title": "Alpha", "implementations": [{"project_name": "Alpha"}]}]})
        b = EX.consumed_yaml_to_ledger({"consumed_ideas": [
            {"idea_id": "E-2", "title": "Beta", "implementations": [{"project_name": "Beta"}]}]})
        self.assertEqual(len(merge_ledgers(a, b)["consumed"]), 2)


# ---- P1-2 LiveArtifactResolver ----
class TestResolveLatest(unittest.TestCase):
    def test_picks_lexicographic_max_round(self):
        with tempfile.TemporaryDirectory() as d:
            for rid in ("EVX-20260610-001", "EVX-20260610-002", "EVX-20260609-009"):
                rd = os.path.join(d, ".evx", "rounds", rid)
                os.makedirs(rd)
                with open(os.path.join(rd, "manifest.json"), "w") as f:
                    json.dump({"round": {"id": rid}}, f)
            p = resolve_latest(d, ".evx", "manifest")
            self.assertIn("EVX-20260610-002", p)

    def test_flat_store(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".idea-ledger"))
            fp = os.path.join(d, ".idea-ledger", "consumed_ideas.json")
            with open(fp, "w") as f:
                json.dump({"consumed_ideas": []}, f)
            self.assertEqual(resolve_latest(d, ".idea-ledger", "consumed_ideas"), fp)


# ---- P1-3 SemanticSimInjection ----
class TestSimInjection(unittest.TestCase):
    def test_lexical_returns_none(self):
        self.assertIsNone(helix.resolve_sim("lexical"))
        self.assertIsNone(helix.resolve_sim(None))

    def test_module_function(self):
        fn = helix.resolve_sim("core.helix_diversity:lexical_sim")
        self.assertTrue(callable(fn))
        self.assertEqual(fn({"title": "a b"}, {"title": "a b"}), 1.0)

    def test_report_uses_injected_sim(self):
        r = helix.build_report(sim=lambda x, y: 0.9)
        self.assertEqual(r["diversity"]["sim_kind"], "semantic")


# ---- P2-1 SchemaValidator depth ----
class TestValidators(unittest.TestCase):
    def test_corpus_entry(self):
        self.assertEqual(validate_corpus_entry({"project": "P", "origin": "explore"}), [])
        self.assertTrue(validate_corpus_entry({"project": "", "origin": "explore"}))
        self.assertTrue(validate_corpus_entry({"project": "P", "origin": "bogus"}))

    def test_loop_state(self):
        self.assertEqual(validate_loop_state({"last_engine": "explore", "corpus_size": 3}), [])
        self.assertTrue(validate_loop_state({"last_engine": "nope"}))
        self.assertTrue(validate_loop_state({"corpus_size": -1}))

    def test_thresholds(self):
        self.assertEqual(validate_thresholds(DEFAULT_THRESHOLDS), [])
        self.assertTrue(validate_thresholds({**DEFAULT_THRESHOLDS, "dup_cos": 1.5}))

    def test_winner_to_corpus_entry_guards_empty_project(self):
        with self.assertRaises(ValueError):
            winner_to_corpus_entry({"idea_id": "X", "title": "t",
                                    "implementations": [{"project_path": "p"}]})  # no project_name


# ---- P2-2 CalibrationHarness ----
class TestCalibrate(unittest.TestCase):
    def test_calibrate_quantiles(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        cal = importlib.import_module("calibrate_diversity")
        rounds = [{"pool_sims": [0.1, 0.2, 0.3, 0.9], "winner_sims": [0.4, 0.5]}]
        out = cal.calibrate(rounds, target_trigger_rate=0.2)
        self.assertIn("avg_embedding_sim", out["thresholds"])
        self.assertIn("dup_cos", out["thresholds"])
        # deterministic
        self.assertEqual(out, cal.calibrate(rounds, target_trigger_rate=0.2))


if __name__ == "__main__":
    unittest.main()
