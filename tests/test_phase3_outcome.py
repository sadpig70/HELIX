import os
import unittest

from scripts.corpus.phase3_outcome import build_outcome


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Phase3OutcomeTests(unittest.TestCase):
    def test_tracked_phase3_outcome_is_complete_and_routed(self):
        outcome = build_outcome(
            ROOT,
            os.path.join(ROOT, "seed", "corpus", "phase3-2026-01-experiments.json"),
            os.path.join(ROOT, "seed", "corpus"),
        )
        self.assertEqual([], outcome["problems"])
        self.assertEqual("PHASE3_COMPLETE_READY_FOR_PHASE4", outcome["status"])
        self.assertEqual(6, outcome["metrics"]["experiments_completed"])
        self.assertEqual(6, outcome["metrics"]["platform_absorbed"])
        self.assertEqual(0, outcome["metrics"]["new_platform_kernels_emitted"])
        self.assertEqual(
            ["AuthorityArbiter", "DriftIsolator", "GraphQuarantine",
             "HookCircuit", "ProofEscrow"],
            outcome["platform_routes"]["Attestra"],
        )
        self.assertEqual(["ContractRelay"], outcome["platform_routes"]["Routestra"])


if __name__ == "__main__":
    unittest.main()
