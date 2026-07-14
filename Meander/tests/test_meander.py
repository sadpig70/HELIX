import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import meander as m


class TestGenerate(unittest.TestCase):
    def test_deterministic(self):
        a = m.generate(12, 8, "seed-x")
        b = m.generate(12, 8, "seed-x")
        self.assertEqual(m.render_ascii(a), m.render_ascii(b))

    def test_different_seed_differs(self):
        a = m.render_ascii(m.generate(12, 8, "s1"))
        b = m.render_ascii(m.generate(12, 8, "s2"))
        self.assertNotEqual(a, b)

    def test_perfect_maze_is_spanning_tree(self):
        for seed in ("a", "b", "c"):
            maze = m.generate(10, 7, seed)
            self.assertEqual(m.passage_count(maze), 10 * 7 - 1,
                             "a perfect maze has cells-1 passages")

    def test_passages_are_symmetric(self):
        maze = m.generate(9, 6, "sym")
        for a, nbrs in maze["passages"].items():
            for b in nbrs:
                self.assertIn(a, maze["passages"][b])

    def test_rejects_nonpositive_dims(self):
        with self.assertRaises(ValueError):
            m.generate(0, 5, "x")


class TestSolve(unittest.TestCase):
    def test_always_solvable(self):
        for seed in ("q", "r", "s", "t"):
            maze = m.generate(14, 9, seed)
            path = m.solve(maze)
            self.assertTrue(path, "perfect maze must be solvable")
            self.assertEqual(path[0], (0, 0))
            self.assertEqual(path[-1], (8, 13))

    def test_path_is_connected(self):
        maze = m.generate(10, 10, "conn")
        path = m.solve(maze)
        for a, b in zip(path, path[1:]):
            self.assertIn(b, maze["passages"][a], "path step crosses a wall")

    def test_solution_at_least_manhattan(self):
        maze = m.generate(12, 8, "man")
        path = m.solve(maze)
        self.assertGreaterEqual(len(path) - 1, (7) + (11))  # manhattan to goal

    def test_single_cell_is_trivial(self):
        maze = m.generate(1, 1, "one")
        self.assertEqual(m.solve(maze), [(0, 0)])


class TestMetricsAndRender(unittest.TestCase):
    def test_metrics_shape(self):
        maze = m.generate(10, 10, "mm")
        met = m.metrics(maze)
        for k in ("cells", "solution_length", "dead_ends", "junctions",
                  "difficulty"):
            self.assertIn(k, met)
        self.assertEqual(met["cells"], 100)

    def test_ascii_grid_dimensions(self):
        maze = m.generate(6, 4, "grid")
        lines = m.render_ascii(maze).splitlines()
        self.assertEqual(len(lines), 4 * 2 + 1)          # 2 rows per cell + top
        self.assertEqual(len(lines[0]), 6 * 4 + 1)       # 4 chars per cell + 1

    def test_svg_is_well_formed(self):
        import xml.dom.minidom as x
        maze = m.generate(8, 8, "svg")
        svg = m.render_svg(maze, m.solve(maze))
        x.parseString(svg)
        self.assertTrue(svg.startswith("<svg"))


class TestCli(unittest.TestCase):
    def setUp(self):
        import tempfile, shutil
        self.dir = tempfile.mkdtemp(prefix="meander-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_sample(self):
        self.assertEqual(m.main(["sample"]), 0)

    def test_generate_and_solve_with_svg(self):
        svg = os.path.join(self.dir, "maze.svg")
        self.assertEqual(m.main(["solve", "--width", "10", "--height", "6",
                                 "--seed", "cli", "--svg", svg]), 0)
        self.assertTrue(os.path.exists(svg))


if __name__ == "__main__":
    unittest.main()
