import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import confluence as c


class TestEngine(unittest.TestCase):
    def test_dominance(self):
        self.assertTrue(c.dominates({"a": 2, "b": 2}, {"a": 1, "b": 2}))
        self.assertFalse(c.dominates({"a": 2, "b": 1}, {"a": 1, "b": 2}))
        self.assertFalse(c.dominates({"a": 1, "b": 1}, {"a": 1, "b": 1}))

    def test_pareto_front_is_non_dominated(self):
        ev = [{"genome": [0], "objectives": {"a": 1, "b": 3}},
              {"genome": [1], "objectives": {"a": 3, "b": 1}},
              {"genome": [2], "objectives": {"a": 1, "b": 1}}]  # dominated
        front = c.pareto_front(ev)
        genomes = {tuple(e["genome"]) for e in front}
        self.assertEqual(genomes, {(0,), (1,)})

    def test_run_is_deterministic_and_sealed(self):
        d = c.DOMAINS["molecule"]
        r1 = c.evolve(d, seed="fixed", population=16, generations=5)
        r2 = c.evolve(d, seed="fixed", population=16, generations=5)
        self.assertEqual(r1["run_sha256"], r2["run_sha256"])
        self.assertTrue(c.verify_run_seal(r1))

    def test_different_seed_differs(self):
        d = c.DOMAINS["energy"]
        a = c.evolve(d, seed="s1", population=16, generations=5)
        b = c.evolve(d, seed="s2", population=16, generations=5)
        self.assertNotEqual(a["run_sha256"], b["run_sha256"])

    def test_front_members_are_valid_and_mutually_nondominated(self):
        d = c.DOMAINS["alloy"]
        run = c.evolve(d, seed="s", population=20, generations=6)
        objs = [f["objectives"] for f in run["pareto_front"]]
        for i, a in enumerate(objs):
            for j, b in enumerate(objs):
                if i != j:
                    self.assertFalse(c.dominates(b, a),
                                     "front member is dominated")


class TestConstraints(unittest.TestCase):
    def test_invalid_genomes_excluded(self):
        d = c.DOMAINS["schema"]
        # a genome of all "--" (index 5) has no key field -> invalid
        allblank = tuple(5 for _ in d["positions"])
        self.assertTrue(d["constraints"](allblank))
        self.assertFalse(c.is_valid(d, allblank))

    def test_all_front_candidates_satisfy_constraints(self):
        for name, d in c.DOMAINS.items():
            run = c.evolve(d, seed="s", population=16, generations=5)
            for f in run["pareto_front"]:
                self.assertEqual(d["constraints"](tuple(f["genome"])), [],
                                 f"{name} front has an invalid candidate")


class TestDomains(unittest.TestCase):
    def test_all_eight_domains_present(self):
        self.assertEqual(set(c.DOMAINS), {
            "molecule", "alloy", "floorplan", "energy", "schema",
            "mandala", "melody", "story"})

    def test_each_domain_produces_a_front_and_render(self):
        for name, d in c.DOMAINS.items():
            run = c.evolve(d, seed="s", population=16, generations=5)
            self.assertTrue(run["pareto_front"], f"{name} empty front")
            art = c.render_best(d, run)
            self.assertIn(art["format"], ("svg", "wav", "text"))

    def test_mandala_renders_well_formed_svg(self):
        import xml.dom.minidom as m
        run = c.evolve(c.DOMAINS["mandala"], seed="s", population=12, generations=4)
        svg = c.render_best(c.DOMAINS["mandala"], run)["content"]
        m.parseString(svg)  # raises if malformed
        self.assertTrue(svg.startswith("<svg"))

    def test_melody_renders_riff_wave_header(self):
        run = c.evolve(c.DOMAINS["melody"], seed="s", population=12, generations=4)
        wav = c.render_best(c.DOMAINS["melody"], run)["content"]
        self.assertEqual(wav[:4], b"RIFF")
        self.assertEqual(wav[8:12], b"WAVE")

    def test_objectives_are_floats(self):
        for name, d in c.DOMAINS.items():
            g = c.init_genome(d["positions"], "s", 0)
            for k, v in d["objectives"](g).items():
                self.assertIsInstance(v, float, f"{name}.{k} not float")


class TestCli(unittest.TestCase):
    def setUp(self):
        import tempfile, shutil
        self.dir = tempfile.mkdtemp(prefix="confluence-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_domains_command(self):
        self.assertEqual(c.main(["domains"]), 0)

    def test_run_render_report_roundtrip(self):
        svg = os.path.join(self.dir, "art.svg")
        ledger = os.path.join(self.dir, "runs.jsonl")
        rc = c.main(["run", "--domain", "mandala", "--seed", "s",
                     "--population", "12", "--generations", "4",
                     "--render", svg, "--ledger", ledger])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(svg))
        self.assertEqual(c.main(["report", "--ledger", ledger]), 0)

    def test_unknown_domain_fails(self):
        self.assertEqual(c.main(["run", "--domain", "nope"]), 2)


if __name__ == "__main__":
    unittest.main()
