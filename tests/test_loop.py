import unittest

import tests._path  # noqa: F401
from core.helix_loop import next_action, VALID_ACTIONS


class TestLoop(unittest.TestCase):
    def test_record_consumed_is_highest_priority(self):
        # even with diversity triggered, an unrecorded implemented winner wins
        a = next_action({
            "pending_implemented_winner": True, "winner_in_ledger": False,
            "diversity": {"triggered": True}, "corpus_size": 0,
        })
        self.assertEqual(a["action"], "RECORD_CONSUMED")

    def test_refresh_inputs_on_diversity(self):
        a = next_action({"last_engine": "exploit", "corpus_size": 5,
                         "diversity": {"triggered": True}})
        self.assertEqual(a["action"], "REFRESH_INPUTS")
        self.assertEqual(a["target"], "explore")

    def test_refresh_target_both_after_explore(self):
        a = next_action({"last_engine": "explore", "corpus_size": 5,
                         "diversity": {"triggered": True}})
        self.assertEqual(a["target"], "both")

    def test_explore_when_corpus_immature(self):
        a = next_action({"corpus_size": 0, "diversity": {"triggered": False}})
        self.assertEqual(a["action"], "RUN_EXPLORE")

    def test_exploit_after_explore_when_mature(self):
        a = next_action({"last_engine": "explore", "corpus_size": 5,
                         "diversity": {"triggered": False}})
        self.assertEqual(a["action"], "RUN_EXPLOIT")

    def test_explore_after_exploit_when_mature(self):
        a = next_action({"last_engine": "exploit", "corpus_size": 5,
                         "diversity": {"triggered": False}})
        self.assertEqual(a["action"], "RUN_EXPLORE")

    def test_already_recorded_winner_does_not_block(self):
        a = next_action({"pending_implemented_winner": True, "winner_in_ledger": True,
                         "corpus_size": 5, "last_engine": "explore",
                         "diversity": {"triggered": False}})
        self.assertEqual(a["action"], "RUN_EXPLOIT")

    def test_actions_are_valid_and_explained(self):
        for state in [{}, {"corpus_size": 9, "last_engine": "explore"},
                      {"diversity": {"triggered": True}}]:
            a = next_action(state)
            self.assertIn(a["action"], VALID_ACTIONS)
            self.assertTrue(a["why"])

    def test_deterministic(self):
        s = {"last_engine": "explore", "corpus_size": 3, "diversity": {"triggered": False}}
        self.assertEqual(next_action(s), next_action(s))

    def test_custom_min_corpus_policy(self):
        a = next_action({"last_engine": "explore", "corpus_size": 3,
                         "diversity": {"triggered": False}},
                        policy={"min_corpus_for_exploit": 10})
        self.assertEqual(a["action"], "RUN_EXPLORE")  # 3 < 10 -> immature


if __name__ == "__main__":
    unittest.main()
