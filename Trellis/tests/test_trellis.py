import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import trellis as t


class TestValidate(unittest.TestCase):
    def test_sample_is_valid(self):
        self.assertEqual(t.validate(t.SAMPLE), [])

    def test_missing_prerequisite_detected(self):
        g = {"b": ["a"]}  # 'a' undefined
        self.assertTrue(any("not a defined skill" in p for p in t.validate(g)))

    def test_cycle_detected(self):
        g = {"a": ["b"], "b": ["c"], "c": ["a"]}
        probs = t.validate(g)
        self.assertTrue(any(p.startswith("cycle:") for p in probs))

    def test_self_dependency_detected(self):
        self.assertTrue(any("itself" in p for p in t.validate({"a": ["a"]})))


class TestOrdering(unittest.TestCase):
    def test_topo_order_respects_prereqs(self):
        order = t.topo_order(t.SAMPLE)
        for s in t.SAMPLE:
            for p in t.SAMPLE[s]:
                self.assertLess(order.index(p), order.index(s))

    def test_topo_order_is_deterministic_alpha_tiebreak(self):
        self.assertEqual(t.topo_order(t.SAMPLE), t.topo_order(dict(t.SAMPLE)))
        # roots come out alphabetically among ties
        g = {"z": [], "a": [], "m": ["a", "z"]}
        self.assertEqual(t.topo_order(g)[:2], ["a", "z"])

    def test_topo_raises_on_cycle(self):
        with self.assertRaises(ValueError):
            t.topo_order({"a": ["b"], "b": ["a"]})


class TestPlan(unittest.TestCase):
    def test_plan_orders_prereqs_first(self):
        pl = t.plan(t.SAMPLE, "calculus")
        for s in pl:
            for p in t.SAMPLE[s]:
                if p in pl:
                    self.assertLess(pl.index(p), pl.index(s))

    def test_plan_is_minimal_closure(self):
        pl = set(t.plan(t.SAMPLE, "calculus"))
        # calculus needs functions/trig/geometry/algebra/arithmetic — NOT stats/ML
        self.assertIn("calculus", pl)
        self.assertNotIn("statistics", pl)
        self.assertNotIn("machine_learning", pl)
        self.assertNotIn("linear_algebra", pl)

    def test_plan_ends_at_goal(self):
        self.assertEqual(t.plan(t.SAMPLE, "machine_learning")[-1],
                         "machine_learning")

    def test_plan_is_deterministic(self):
        self.assertEqual(t.plan(t.SAMPLE, "probability"),
                         t.plan(t.SAMPLE, "probability"))

    def test_plan_rejects_invalid_graph(self):
        with self.assertRaises(ValueError):
            t.plan({"a": ["b"], "b": ["a"]}, "a")

    def test_unknown_goal_raises(self):
        with self.assertRaises(KeyError):
            t.plan(t.SAMPLE, "nonexistent")


class TestDepthAndRender(unittest.TestCase):
    def test_depth_is_longest_chain(self):
        self.assertEqual(t.depth(t.SAMPLE, "arithmetic"), 0)
        self.assertEqual(t.depth(t.SAMPLE, "algebra"), 1)
        # ml: arithmetic->algebra->{geometry?}->trig->calculus->probability->ml
        self.assertEqual(t.depth(t.SAMPLE, "machine_learning"), 5)

    def test_render_svg_is_well_formed(self):
        import xml.dom.minidom as x
        svg = t.render_svg(t.SAMPLE, "machine_learning")
        x.parseString(svg)
        self.assertTrue(svg.startswith("<svg"))

    def test_render_plan_lists_every_step(self):
        text = t.render_plan(t.SAMPLE, "machine_learning")
        self.assertIn("machine_learning", text)
        self.assertEqual(text.count("\n"), 10)  # header + 10 steps -> 10 newlines


class TestCli(unittest.TestCase):
    def test_sample(self):
        self.assertEqual(t.main(["sample"]), 0)

    def test_plan_and_check(self):
        self.assertEqual(t.main(["plan", "--goal", "calculus"]), 0)
        self.assertEqual(t.main(["check"]), 0)


if __name__ == "__main__":
    unittest.main()
