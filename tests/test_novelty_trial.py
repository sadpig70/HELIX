import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_novelty import (
    aggregate_novelty,
    build_reduction_receipt,
    is_novelty_claim,
)
from core.helix_prediction import seal_trial_receipt
from core.helix_schema import schema_features, validate_against_schema
from scripts.evaluate.blind_machine_trial import run_blind_trial, run_trial
from scripts.evaluate.build_synthetic_holdout import generate
from tests.test_blind_runner import perfect_predictor


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "helix-reduction-receipt.schema.json")
APPROVALS = [{"approver_id": "approver-test-1", "role": "reveal_approver"}]


def condense_predictor(view):
    """Claims a novel machine (CONDENSE) for every candidate."""
    index = int(view["candidate_id"].split("-")[1])
    return {"outcome": "PREDICT", "action": "CONDENSE",
            "machines": [f"M{(index % 15) + 1}"]}


class NoveltyFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-novelty-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        for name in ("helix-holdout-registry", "helix-trial-receipt",
                     "helix-reduction-receipt"):
            shutil.copy(os.path.join(ROOT, "schemas", f"{name}.schema.json"),
                        os.path.join(self.root, "schemas"))
        self.registry = generate(self.root)

    def run_condense_trial(self):
        return run_trial(self.root, self.registry, condense_predictor,
                         APPROVALS, "_trial/receipts")

    def evidence_file(self, name="impl-evidence.json"):
        rel = f"_trial/evidence/{name}"
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"experiment": "synthetic implementation record"}, f)
        return rel

    def implemented(self, reduced, reduced_to=None, cost=5):
        return {"implemented": True, "evidence_path": self.evidence_file(),
                "estimated_cost_units": cost, "reduced_to_existing": reduced,
                "reduced_to": reduced_to}


class TestReductionReceipt(NoveltyFixtureCase):
    def test_confirmed_novelty_and_false_condense_verdicts(self):
        revealed, chains = self.run_condense_trial()
        cid = sorted(chains)[0]
        confirmed = build_reduction_receipt(
            self.root, revealed, chains[cid]["prediction"], chains[cid]["reveal"],
            self.implemented(reduced=False))
        self.assertEqual(confirmed["verdict"], "novel_confirmed")
        self.assertEqual(confirmed["parent_receipt_sha256"],
                         chains[cid]["reveal"]["receipt_sha256"])
        reduced = build_reduction_receipt(
            self.root, revealed, chains[cid]["prediction"], chains[cid]["reveal"],
            self.implemented(reduced=True, reduced_to=["M3"]))
        self.assertEqual(reduced["verdict"], "reduced_to_existing")
        self.assertEqual(validate_against_schema(confirmed, SCHEMA), [])
        self.assertEqual(validate_against_schema(reduced, SCHEMA), [])

    def test_not_implemented_claim_is_sealed_but_never_confirmed(self):
        revealed, chains = self.run_condense_trial()
        cid = sorted(chains)[0]
        receipt = build_reduction_receipt(
            self.root, revealed, chains[cid]["prediction"], chains[cid]["reveal"],
            {"implemented": False, "estimated_cost_units": 0})
        self.assertEqual(receipt["verdict"], "not_implemented")
        self.assertIsNone(receipt["implementation"]["evidence_path"])

    def test_reduction_before_reveal_is_forbidden(self):
        revealed, chains = self.run_condense_trial()
        cid = sorted(chains)[0]
        with self.assertRaisesRegex(ValueError, "before oracle reveal"):
            build_reduction_receipt(self.root, revealed,
                                    chains[cid]["prediction"], None,
                                    self.implemented(reduced=False))

    def test_non_novelty_prediction_cannot_get_a_reduction_receipt(self):
        revealed, chains = run_trial(self.root, self.registry, perfect_predictor,
                                     APPROVALS, "_trial/receipts")
        build_on = next(cid for cid in sorted(chains)
                        if chains[cid]["prediction"]["prediction"]["action"]
                        == "BUILD_ON_PLATFORM")
        with self.assertRaisesRegex(ValueError, "not a novelty claim"):
            build_reduction_receipt(self.root, revealed,
                                    chains[build_on]["prediction"],
                                    chains[build_on]["reveal"],
                                    self.implemented(reduced=False))

    def test_malformed_implementation_evidence_is_refused(self):
        revealed, chains = self.run_condense_trial()
        cid = sorted(chains)[0]
        cases = (
            ({"implemented": True, "evidence_path": None,
              "estimated_cost_units": 1, "reduced_to_existing": False,
              "reduced_to": None}, "requires evidence_path"),
            ({"implemented": True, "evidence_path": "_trial/evidence/absent.json",
              "estimated_cost_units": 1, "reduced_to_existing": False,
              "reduced_to": None}, "evidence missing"),
            (self.implemented(reduced=True, reduced_to=[]), "reduced to"),
            (self.implemented(reduced=False, reduced_to=["M1"]), "must not name"),
            ({"implemented": False, "estimated_cost_units": -1}, "non-negative"),
        )
        for implementation, message in cases:
            with self.subTest(message=message), \
                    self.assertRaisesRegex(ValueError, message):
                build_reduction_receipt(self.root, revealed,
                                        chains[cid]["prediction"],
                                        chains[cid]["reveal"], implementation)

    def test_schema_stays_in_stdlib_subset(self):
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema_features(schema), {"in_subset": True, "unsupported": []})


class TestNoveltyAggregation(NoveltyFixtureCase):
    def make_receipts(self, chains, revealed):
        cids = sorted(chains)
        receipts = {}
        receipts[cids[0]] = build_reduction_receipt(
            self.root, revealed, chains[cids[0]]["prediction"],
            chains[cids[0]]["reveal"], self.implemented(reduced=False, cost=7))
        receipts[cids[1]] = build_reduction_receipt(
            self.root, revealed, chains[cids[1]]["prediction"],
            chains[cids[1]]["reveal"],
            self.implemented(reduced=True, reduced_to=["M9"], cost=11))
        receipts[cids[2]] = build_reduction_receipt(
            self.root, revealed, chains[cids[2]]["prediction"],
            chains[cids[2]]["reveal"], {"implemented": False,
                                        "estimated_cost_units": 0})
        return receipts

    def test_false_condense_count_cost_and_precision(self):
        revealed, chains = self.run_condense_trial()
        novelty = aggregate_novelty(self.root, revealed, chains,
                                    self.make_receipts(chains, revealed))
        counts = novelty["counts"]
        self.assertEqual(counts["claims"], 20)
        self.assertEqual(counts["novel_confirmed"], 1)
        self.assertEqual(counts["false_condense"], 1)
        self.assertEqual(counts["not_implemented"], 1)
        self.assertEqual(counts["untracked"], 17)
        self.assertEqual(novelty["costs"]["total_estimated_cost_units"], 18)
        self.assertEqual(novelty["costs"]["false_condense_cost_units"], 11)
        self.assertEqual(novelty["novelty_precision_implemented"], 0.5)
        self.assertEqual(novelty["novelty_yield"], 1 / 20)

    def test_unimplemented_claims_never_inflate_the_metrics(self):
        revealed, chains = self.run_condense_trial()
        novelty = aggregate_novelty(self.root, revealed, chains, {})
        self.assertEqual(novelty["counts"]["untracked"], 20)
        self.assertIsNone(novelty["novelty_precision_implemented"])
        self.assertEqual(novelty["novelty_yield"], 0.0)

    def test_claim_mismatch_with_sealed_prediction_is_a_violation(self):
        revealed, chains = self.run_condense_trial()
        receipts = self.make_receipts(chains, revealed)
        victim = sorted(receipts)[0]
        tampered = copy.deepcopy(receipts[victim])
        tampered["novelty_claim"]["machines"] = ["M99"]
        receipts[victim] = seal_trial_receipt(tampered)
        novelty = aggregate_novelty(self.root, revealed, chains, receipts)
        self.assertEqual(novelty["counts"]["protocol_violation"], 1)
        self.assertEqual(novelty["counts"]["novel_confirmed"], 0)

    def test_tampered_evidence_file_is_a_violation(self):
        revealed, chains = self.run_condense_trial()
        receipts = self.make_receipts(chains, revealed)
        with open(os.path.join(self.root, "_trial", "evidence",
                               "impl-evidence.json"), "a", encoding="utf-8") as f:
            f.write("tampered\n")
        novelty = aggregate_novelty(self.root, revealed, chains, receipts)
        self.assertEqual(novelty["counts"]["protocol_violation"], 2)

    def test_aggregation_refuses_a_tampered_registry(self):
        revealed, chains = self.run_condense_trial()
        doc = copy.deepcopy(revealed)
        doc["cohort"]["selection_rule"] = "changed after lock"
        with self.assertRaisesRegex(ValueError, "commitment mismatch"):
            aggregate_novelty(self.root, doc, chains, {})


class TestRunnerNoveltySection(NoveltyFixtureCase):
    def test_report_carries_a_novelty_section_per_system(self):
        evidence = {"condense": {
            "SYN-001": self.implemented(reduced=True, reduced_to=["M2"], cost=3)}}
        report = run_blind_trial(self.root, self.registry,
                                 {"condense": condense_predictor,
                                  "perfect": perfect_predictor},
                                 APPROVALS, "_trial/out", evidence)
        condense = report["systems"]["condense"]["novelty"]
        self.assertEqual(condense["counts"]["claims"], 20)
        self.assertEqual(condense["counts"]["false_condense"], 1)
        self.assertEqual(condense["counts"]["not_implemented"], 19)
        self.assertEqual(condense["counts"]["untracked"], 0)
        # perfect predictor claims DEFER on even-indexed candidates
        perfect = report["systems"]["perfect"]["novelty"]
        self.assertEqual(perfect["counts"]["claims"], 10)
        self.assertEqual(perfect["counts"]["not_implemented"], 10)
        receipt_path = os.path.join(self.root, "_trial", "out", "condense",
                                    "receipts", "SYN-001.reduction.json")
        with open(receipt_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["verdict"], "reduced_to_existing")

    def test_novelty_phase_is_deterministic(self):
        report_a = run_blind_trial(self.root, self.registry,
                                   {"condense": condense_predictor},
                                   APPROVALS, "_trial/run-a")
        report_b = run_blind_trial(self.root, self.registry,
                                   {"condense": condense_predictor},
                                   APPROVALS, "_trial/run-b")
        self.assertEqual(json.dumps(report_a, sort_keys=True),
                         json.dumps(report_b, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
