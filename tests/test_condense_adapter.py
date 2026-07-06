import unittest

import tests._path  # noqa: F401
from core.helix_condense import condense_candidate, build_on_platform_candidate, condense_state
from core.helix_loop import next_action

LC = {
    "layer1_platforms": [{"cluster": "Governance/Trust"}, {"cluster": "Clearing/Market"},
                         {"cluster": "Routing/Siting"}, {"cluster": "Robotics/Release"}],
    "candidate_clusters": [
        {"cluster": "Compatibility Mesh", "substantiated_count": 5},
        {"cluster": "Bio staged-release", "substantiated_count": 3},
    ],
    "base_pairing_feedback": {"build_on_platform_candidates": {
        "Attestra": ["MethodBond", "ADPR"], "Routestra": ["WattMesh"]}},
}


class TestCondenseAdapter(unittest.TestCase):
    def test_picks_ripest_unplatformed_cluster(self):
        cc = condense_candidate(LC)
        self.assertEqual(cc["cluster"], "Compatibility Mesh")   # 5 >= 5; Bio (3) below threshold
        self.assertEqual(cc["substantiated_count"], 5)
        self.assertFalse(cc["platformized"])

    def test_platformed_cluster_excluded(self):
        lc = {**LC, "candidate_clusters": [{"cluster": "Governance/Trust", "substantiated_count": 28}]}
        self.assertIsNone(condense_candidate(lc))   # already a platform

    def test_below_threshold_none(self):
        lc = {**LC, "candidate_clusters": [{"cluster": "Bio staged-release", "substantiated_count": 3}]}
        self.assertIsNone(condense_candidate(lc))

    def test_custom_threshold(self):
        self.assertIsNone(condense_candidate(LC, policy={"min_cluster_for_condense": 6}))  # 5 < 6

    def test_build_on_platform_deterministic(self):
        bp = build_on_platform_candidate(LC)
        self.assertEqual(bp, {"project": "ADPR", "platform": "Attestra"})  # sorted platform, sorted project

    def test_condense_state_shape(self):
        s = condense_state(LC)
        self.assertIn("condense_candidate", s)
        self.assertIn("build_on_platform_candidate", s)

    def test_deterministic(self):
        self.assertEqual(condense_state(LC), condense_state(LC))

    def test_feeds_next_action(self):
        # adapter output drives next_action to CONDENSE (ripe cluster wins over pack-growth)
        state = {"corpus_size": 40, "last_engine": "explore", "diversity": {"triggered": False}}
        state.update(condense_state(LC))
        self.assertEqual(next_action(state)["action"], "CONDENSE")

    def test_empty_layered_corpus(self):
        self.assertEqual(condense_state({}), {})   # no candidates -> empty (backward compatible)

    def test_machine_covered_cluster_is_not_condense(self):
        # a cluster whose machine an existing platform already provides -> BUILD_ON_PLATFORM,
        # not a new platform (the SovMesh/Compatibility-Mesh finding).
        lc = {"layer1_platforms": [{"cluster": "Governance/Trust", "kernel_machines": ["M1", "M2", "M3", "M4"]}],
              "candidate_clusters": [{"cluster": "Compatibility Mesh", "substantiated_count": 9,
                                      "shared_machines": ["M2", "M3"]}]}
        self.assertIsNone(condense_candidate(lc))

    def test_novel_machine_cluster_can_condense(self):
        lc = {"layer1_platforms": [{"cluster": "Governance", "kernel_machines": ["M1", "M2", "M3", "M4"]}],
              "candidate_clusters": [{"cluster": "Bio", "substantiated_count": 6,
                                      "shared_machines": ["M11", "M12"]}]}
        self.assertEqual(condense_candidate(lc)["cluster"], "Bio")   # M11 novel -> condensable


if __name__ == "__main__":
    unittest.main()
