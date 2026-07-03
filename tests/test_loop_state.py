"""Tests for v0.4 F3 LoopCorePromote: deterministic autonomous-loop control state."""
import os
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_loop_state import (
    should_stop, update_coverage, least_covered, rate_limit_ok,
    load_loop_state, checkpoint_loop_state, loop_status_report,
)


class TestShouldStop(unittest.TestCase):
    def test_running_by_default(self):
        self.assertFalse(should_stop({"turn": 1})["stop"])

    def test_human_stop_first(self):
        r = should_stop({"stop_file_present": True, "consecutive_dry": 9})
        self.assertEqual(r["reason"], "human_stop")

    def test_max_turns(self):
        self.assertEqual(should_stop({"turn": 5}, {"max_turns": 5})["reason"], "max_turns")
        self.assertFalse(should_stop({"turn": 4}, {"max_turns": 5})["stop"])

    def test_dry(self):
        self.assertEqual(should_stop({"consecutive_dry": 2})["reason"], "dry")

    def test_failures(self):
        self.assertEqual(should_stop({"consecutive_failures": 3})["reason"], "consecutive_failures")

    def test_handback_breach_stops(self):
        self.assertEqual(should_stop({"handback_breach": True})["reason"], "handback_breach")

    def test_handback_breach_absent_continues(self):
        self.assertFalse(should_stop({"turn": 1})["stop"])

    def test_deterministic(self):
        s = {"turn": 2, "consecutive_dry": 1}
        self.assertEqual(should_stop(s), should_stop(s))


class TestCoverage(unittest.TestCase):
    def _ledger(self):
        return {"consumed": [
            {"origin": "explore", "archetype": "Gate", "semantic_family": "fam-a"},
            {"origin": "explore", "archetype": "Sensing", "semantic_family": "fam-a"},
            {"origin": "exploit", "archetype": "Gate", "semantic_family": "fam-b"},
        ]}

    def test_histogram(self):
        cov = update_coverage(self._ledger())
        self.assertEqual(cov["origin"], {"explore": 2, "exploit": 1})
        self.assertEqual(cov["archetype"], {"Gate": 2, "Sensing": 1})
        self.assertEqual(cov["semantic_family"], {"fam-a": 2, "fam-b": 1})

    def test_least_covered(self):
        self.assertEqual(least_covered({"explore": 2, "exploit": 1}), "exploit")
        self.assertEqual(least_covered({}), "")

    def test_least_covered_tie_break_by_key(self):
        self.assertEqual(least_covered({"b": 1, "a": 1}), "a")


class TestRateLimit(unittest.TestCase):
    def test_new_window_resets(self):
        state = {"publish_window_id": "2026-06-16", "published_this_window": 9}
        self.assertTrue(rate_limit_ok(state, "2026-06-17", {"publish_rate_limit": 6}))

    def test_within_window_respects_limit(self):
        state = {"publish_window_id": "2026-06-17", "published_this_window": 6}
        self.assertFalse(rate_limit_ok(state, "2026-06-17", {"publish_rate_limit": 6}))
        state["published_this_window"] = 5
        self.assertTrue(rate_limit_ok(state, "2026-06-17", {"publish_rate_limit": 6}))


class TestStateIo(unittest.TestCase):
    def test_load_default_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            state = load_loop_state(os.path.join(d, "loop-state.json"))
            self.assertEqual(state["turn"], 0)
            self.assertEqual(state["status"], "active")

    def test_checkpoint_roundtrip_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "loop", "loop-state.json")  # nested dir auto-created
            checkpoint_loop_state(p, {"turn": 3, "status": "active"})
            self.assertEqual(load_loop_state(p)["turn"], 3)

    def test_status_report(self):
        rep = loop_status_report({"turn": 2, "status": "active"},
                                 ledger={"consumed": [{"origin": "explore"}]})
        self.assertFalse(rep["stop"]["stop"])
        self.assertEqual(rep["coverage"]["origin"], {"explore": 1})
        self.assertEqual(rep["least_covered_origin"], "explore")

    def test_status_report_handback_breach_stops(self):
        rep = loop_status_report(
            {"turn": 1, "status": "active"},
            handback_gate={"checked": 2, "passed": 1, "excluded": 1},
        )
        self.assertTrue(rep["stop"]["stop"])
        self.assertEqual(rep["stop"]["reason"], "handback_breach")

    def test_status_report_no_handback_breach(self):
        rep = loop_status_report(
            {"turn": 1, "status": "active"},
            handback_gate={"checked": 1, "passed": 1, "excluded": 0},
        )
        self.assertFalse(rep["stop"]["stop"])


if __name__ == "__main__":
    unittest.main()
