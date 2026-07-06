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

    # --- U5: Condense / Build-on-platform (project generator -> platform generator) ---

    def test_condense_on_ripe_cluster(self):
        a = next_action({"last_engine": "explore", "corpus_size": 9, "diversity": {"triggered": False},
                         "condense_candidate": {"cluster": "Robotics/Release",
                                                "substantiated_count": 5, "platformized": False}})
        self.assertEqual(a["action"], "CONDENSE")
        self.assertEqual(a["target"], "Robotics/Release")

    def test_condense_skipped_when_platformized(self):
        a = next_action({"corpus_size": 9, "last_engine": "explore", "diversity": {"triggered": False},
                         "condense_candidate": {"cluster": "Governance",
                                                "substantiated_count": 28, "platformized": True}})
        self.assertNotEqual(a["action"], "CONDENSE")

    def test_condense_below_threshold(self):
        a = next_action({"corpus_size": 9, "last_engine": "explore", "diversity": {"triggered": False},
                         "condense_candidate": {"cluster": "Bio",
                                                "substantiated_count": 3, "platformized": False}})
        self.assertNotEqual(a["action"], "CONDENSE")   # 3 < 5

    def test_record_consumed_beats_condense(self):
        a = next_action({"pending_implemented_winner": True, "winner_in_ledger": False,
                         "condense_candidate": {"cluster": "X", "substantiated_count": 9,
                                                "platformized": False}})
        self.assertEqual(a["action"], "RECORD_CONSUMED")

    def test_refresh_beats_condense(self):
        a = next_action({"corpus_size": 9, "diversity": {"triggered": True},
                         "condense_candidate": {"cluster": "X", "substantiated_count": 9,
                                                "platformized": False}})
        self.assertEqual(a["action"], "REFRESH_INPUTS")

    def test_build_on_platform_preferred(self):
        a = next_action({"last_engine": "explore", "corpus_size": 9, "diversity": {"triggered": False},
                         "build_on_platform_candidate": {"project": "MethodBond", "platform": "Attestra"}})
        self.assertEqual(a["action"], "BUILD_ON_PLATFORM")
        self.assertEqual(a["target"], {"project": "MethodBond", "platform": "Attestra"})

    def test_condense_beats_build_on_platform(self):
        a = next_action({"corpus_size": 9, "last_engine": "explore", "diversity": {"triggered": False},
                         "condense_candidate": {"cluster": "X", "substantiated_count": 6, "platformized": False},
                         "build_on_platform_candidate": {"project": "P", "platform": "Attestra"}})
        self.assertEqual(a["action"], "CONDENSE")   # convergence before pack-growth

    def test_custom_condense_threshold(self):
        a = next_action({"corpus_size": 9, "last_engine": "explore", "diversity": {"triggered": False},
                         "condense_candidate": {"cluster": "X", "substantiated_count": 6, "platformized": False}},
                        policy={"min_cluster_for_condense": 10})
        self.assertNotEqual(a["action"], "CONDENSE")   # 6 < 10

    def test_backward_compat_without_new_fields(self):
        # states without condense/build fields behave exactly as before U5
        self.assertEqual(next_action({"last_engine": "explore", "corpus_size": 5,
                                      "diversity": {"triggered": False}})["action"], "RUN_EXPLOIT")
        self.assertEqual(next_action({"last_engine": "exploit", "corpus_size": 5,
                                      "diversity": {"triggered": False}})["action"], "RUN_EXPLORE")


if __name__ == "__main__":
    unittest.main()
