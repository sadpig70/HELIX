import unittest

import tests._path  # noqa: F401
from core.helix_diversity import (
    measure_diversity, lexical_sim, keyword_coverage, max_domain_pair_repeat,
    unique_ratio, DEFAULT_THRESHOLDS,
)


def make_pool(titles, domains=None):
    pool = []
    for i, t in enumerate(titles):
        item = {"title": t}
        if domains:
            item["domains"] = domains[i]
        pool.append(item)
    return pool


class TestDiversity(unittest.TestCase):
    def test_keyword_coverage_homogeneous_high(self):
        pool = make_pool(["mesh ledger gate", "mesh ledger stage", "mesh ledger index"])
        self.assertGreaterEqual(keyword_coverage(pool, k=3), 0.99)

    def test_keyword_coverage_diverse_lower(self):
        pool = make_pool(["alpha", "beta", "gamma", "delta", "epsilon"])
        self.assertLessEqual(keyword_coverage(pool, k=1), 0.4)

    def test_keyword_coverage_empty(self):
        self.assertEqual(keyword_coverage([]), 0.0)

    def test_max_domain_pair_repeat(self):
        pool = make_pool(["a", "b", "c"],
                         domains=[["bio", "energy"], ["bio", "energy"], ["bio", "robotics"]])
        self.assertEqual(max_domain_pair_repeat(pool), 2)

    def test_unique_ratio_with_injected_sim(self):
        pool = make_pool(["x1", "x2", "y1"])
        # x1,x2 near-duplicate; y1 distinct
        def sim(a, b):
            return 0.9 if a["title"][0] == b["title"][0] else 0.1
        self.assertAlmostEqual(unique_ratio(pool, sim, dup_cos=0.8), 2 / 3)

    def test_unique_ratio_none_without_sim(self):
        self.assertIsNone(unique_ratio(make_pool(["a", "b"]), None, 0.8))

    def test_lexical_default_when_no_sim(self):
        pool = make_pool(["mesh ledger", "mesh gate"], domains=[["d1", "d2"], ["d1", "d2"]])
        rep = measure_diversity(pool, sim=None)
        self.assertEqual(rep["sim_kind"], "lexical")
        # with the lexical default, sim-based metrics are produced (never None for >=2 items)
        self.assertIsNotNone(rep["metrics"]["avg_embedding_sim"])
        self.assertIsNotNone(rep["signals"]["unique_ratio"])

    def test_sim_kind_semantic_when_injected(self):
        pool = make_pool(["a", "b"])
        rep = measure_diversity(pool, sim=lambda x, y: 0.5)
        self.assertEqual(rep["sim_kind"], "semantic")

    def test_lexical_sim_basic(self):
        a = {"title": "policy drift dossier"}
        b = {"title": "policy drift calendar"}
        c = {"title": "quantum lichen oracle"}
        self.assertGreater(lexical_sim(a, b), lexical_sim(a, c))
        self.assertEqual(lexical_sim(a, a), 1.0)

    def test_triggered_when_two_breaches(self):
        # homogeneous pool: high keyword coverage + repeated domain pair + high sim
        pool = make_pool(["mesh ledger gate", "mesh ledger gate", "mesh ledger gate"],
                         domains=[["bio", "energy"]] * 3)
        def sim(a, b):
            return 0.95
        rep = measure_diversity(pool, recent_winners=pool, sim=sim)
        self.assertTrue(rep["triggered"])
        self.assertGreaterEqual(rep["breaches"], 2)

    def test_not_triggered_when_diverse(self):
        pool = make_pool(["alpha one", "beta two", "gamma three", "delta four"],
                         domains=[["a", "b"], ["c", "d"], ["e", "f"], ["g", "h"]])
        def sim(a, b):
            return 0.05
        rep = measure_diversity(pool, recent_winners=[], sim=sim)
        self.assertFalse(rep["triggered"])

    def test_deterministic(self):
        pool = make_pool(["mesh a", "mesh b"], domains=[["x", "y"], ["x", "y"]])
        def sim(a, b):
            return 0.5
        self.assertEqual(measure_diversity(pool, sim=sim), measure_diversity(pool, sim=sim))

    def test_default_thresholds_present(self):
        for k in ("keyword_coverage", "max_pair_count", "avg_embedding_sim",
                  "winner_embedding_similarity", "dup_cos", "min_breaches"):
            self.assertIn(k, DEFAULT_THRESHOLDS)


if __name__ == "__main__":
    unittest.main()
