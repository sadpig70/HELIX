import unittest

import tests._path  # noqa: F401
from core.helix_ledger import (
    empty_ledger, is_consumed, append_consumed, candidate_keys,
)


def _impl(name):
    return [{"project_name": name, "project_path": name.lower(), "repo_url": "https://example.invalid/x"}]


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.ledger = empty_ledger()
        append_consumed(self.ledger, {
            "idea_id": "IDEA-001", "title": "Agent PACT Mesh",
            "aliases": ["AgentPACT", "PACT"], "semantic_family": "agentops-mesh",
            "origin": "explore", "implementations": _impl("AgentPACT"),
        }, now="2026-01-01T00:00:00+00:00")
        append_consumed(self.ledger, {
            "idea_id": "GEN-WAW", "title": "Withheld Action Witness",
            "origin": "exploit", "sources": ["ADPR", "PnR", "ReleaseMesh"],
            "implementations": _impl("WithheldActionWitness"),
        }, now="2026-01-02T00:00:00+00:00")

    def test_match_by_idea_id(self):
        r = is_consumed({"idea_id": "IDEA-001", "title": "totally different"}, self.ledger)
        self.assertTrue(r["consumed"])
        self.assertEqual(r["match"]["on"], "idea_id")

    def test_match_by_normalized_title(self):
        r = is_consumed({"title": "agent  pact   mesh"}, self.ledger)
        self.assertTrue(r["consumed"])
        self.assertEqual(r["match"]["on"], "normalized_title")

    def test_match_by_alias(self):
        # candidate's title equals a recorded alias
        r = is_consumed({"title": "AgentPACT"}, self.ledger)
        self.assertTrue(r["consumed"])
        self.assertIn(r["match"]["on"], ("normalized_title", "aliases"))

    def test_match_by_semantic_family(self):
        r = is_consumed({"title": "Brand New Name", "semantic_family": "agentops-mesh"}, self.ledger)
        self.assertTrue(r["consumed"])
        self.assertEqual(r["match"]["on"], "semantic_family")

    def test_match_by_source_fingerprint_order_independent(self):
        r = is_consumed({"title": "Different", "sources": ["ReleaseMesh", "PnR", "ADPR"]}, self.ledger)
        self.assertTrue(r["consumed"])
        self.assertEqual(r["match"]["on"], "source_fingerprint")

    def test_clean_candidate_not_consumed(self):
        r = is_consumed({"idea_id": "IDEA-999", "title": "Quantum Lichen Oracle",
                         "sources": ["Foo", "Bar"]}, self.ledger)
        self.assertFalse(r["consumed"])
        self.assertIsNone(r["match"])

    def test_append_requires_implementation(self):
        with self.assertRaises(ValueError):
            append_consumed(self.ledger, {"idea_id": "X", "title": "No Impl"},
                            now="2026-01-03T00:00:00+00:00")

    def test_now_is_injected(self):
        led = empty_ledger()
        append_consumed(led, {"idea_id": "T", "title": "Timed", "implementations": _impl("Timed")},
                        now="2026-12-31T23:59:59+00:00")
        self.assertEqual(led["consumed"][0]["consumed_at_utc"], "2026-12-31T23:59:59+00:00")

    def test_candidate_keys_deterministic(self):
        c = {"title": "Foo Bar", "sources": ["b", "a"], "aliases": ["Zed", "zed"]}
        self.assertEqual(candidate_keys(c), candidate_keys(c))
        self.assertEqual(candidate_keys(c)["source_fingerprint"], "a+b")
        self.assertEqual(candidate_keys(c)["aliases"], ["zed"])

    def test_blocked_names_updated(self):
        self.assertIn("agentpactmesh", self.ledger["blocked_names"])
        self.assertIn("pact", self.ledger["blocked_names"])


if __name__ == "__main__":
    unittest.main()
