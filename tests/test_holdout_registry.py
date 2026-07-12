import copy
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_holdout import (
    cohort_commitment,
    lock_registry,
    locked_eligible_candidates,
    validate_registry,
)
from scripts.evaluate.build_synthetic_holdout import REGISTRY_REL, generate


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_REGISTRY = os.path.join(ROOT, *REGISTRY_REL.split("/"))


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class HoldoutFixtureCase(unittest.TestCase):
    """Shared temp fixture: a generated live-size tree that tests may mutate."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-holdout-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "schemas"))
        shutil.copy(os.path.join(ROOT, "schemas", "helix-holdout-registry.schema.json"),
                    os.path.join(self.root, "schemas"))
        self.registry = generate(self.root)

    def full_path(self, rel):
        return os.path.join(self.root, *rel.split("/"))


class TestCommitmentDeterminism(HoldoutFixtureCase):
    def test_regenerating_the_fixture_reproduces_the_same_commitment(self):
        other = tempfile.mkdtemp(prefix="helix-holdout-")
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        regenerated = generate(other)
        self.assertEqual(regenerated["cohort"]["commitment_sha256"],
                         self.registry["cohort"]["commitment_sha256"])
        self.assertEqual(regenerated, self.registry)

    def test_commitment_is_pure_function_of_locked_content(self):
        self.assertEqual(cohort_commitment(self.registry),
                         self.registry["cohort"]["commitment_sha256"])
        self.assertEqual(cohort_commitment(copy.deepcopy(self.registry)),
                         cohort_commitment(self.registry))

    def test_candidate_order_does_not_change_the_commitment(self):
        doc = copy.deepcopy(self.registry)
        doc["candidates"].reverse()
        self.assertEqual(cohort_commitment(doc), cohort_commitment(self.registry))


class TestLockTamperDetection(HoldoutFixtureCase):
    def assert_commitment_breach(self, doc):
        problems = validate_registry(self.root, doc, check_artifacts=False)
        self.assertTrue(any("cohort commitment mismatch" in p for p in problems),
                        problems)

    def test_candidate_deletion_is_detected(self):
        doc = copy.deepcopy(self.registry)
        del doc["candidates"][3]
        self.assert_commitment_breach(doc)

    def test_candidate_replacement_is_detected(self):
        doc = copy.deepcopy(self.registry)
        doc["candidates"][0]["source"]["artifact_sha256"] = "0" * 64
        self.assert_commitment_breach(doc)

    def test_selection_rule_change_is_detected(self):
        doc = copy.deepcopy(self.registry)
        doc["cohort"]["selection_rule"] = "relaxed rule after the fact"
        self.assert_commitment_breach(doc)

    def test_excluded_candidate_cannot_be_flipped_to_eligible(self):
        doc = copy.deepcopy(self.registry)
        excluded = next(c for c in doc["candidates"] if c["status"] == "excluded")
        excluded["status"] = "eligible"
        problems = validate_registry(self.root, doc, check_artifacts=False)
        self.assertTrue(any("cohort commitment mismatch" in p for p in problems),
                        problems)
        self.assertTrue(any("eligibility claims" in p for p in problems), problems)

    def test_post_lock_lifecycle_does_not_break_the_lock(self):
        doc = copy.deepcopy(self.registry)
        candidate = doc["candidates"][0]
        candidate["status"] = "scored"
        candidate["prediction_receipt"] = {
            "status": "sealed", "path": "_holdout/predictions/SYN-001.json",
            "sha256": "1" * 64, "predictor_role": "predictor",
        }
        candidate["oracle_commitment"]["access"] = "revealed"
        candidate["reveal"] = {"status": "revealed", "authorized_by": ["approver-1"],
                               "receipt_sha256": "2" * 64}
        doc["cohort"]["status"] = "scored"
        problems = validate_registry(self.root, doc, check_artifacts=False)
        self.assertEqual(problems, [])


class TestArtifactVerification(HoldoutFixtureCase):
    def test_source_artifact_tamper_is_detected(self):
        locator = self.registry["candidates"][0]["source"]["locator"]
        with open(self.full_path(locator), "a", encoding="utf-8") as f:
            f.write("tampered\n")
        problems = validate_registry(self.root, self.registry)
        self.assertTrue(any("source artifact hash mismatch" in p for p in problems),
                        problems)

    def test_license_evidence_tamper_is_detected(self):
        license_rel = self.registry["candidates"][0]["source"]["license_evidence_path"]
        with open(self.full_path(license_rel), "a", encoding="utf-8") as f:
            f.write("tampered\n")
        problems = validate_registry(self.root, self.registry)
        self.assertTrue(any("license evidence hash mismatch" in p for p in problems),
                        problems)

    def test_missing_source_artifact_is_detected(self):
        locator = self.registry["candidates"][1]["source"]["locator"]
        os.remove(self.full_path(locator))
        problems = validate_registry(self.root, self.registry)
        self.assertTrue(any("source artifact missing" in p for p in problems), problems)

    def test_label_leak_in_candidate_view_is_detected(self):
        doc = copy.deepcopy(self.registry)
        candidate = doc["candidates"][0]
        view_full = self.full_path(candidate["candidate_view"]["path"])
        view = _load(view_full)
        view["platform"] = "Attestra"
        with open(view_full, "w", encoding="utf-8", newline="\n") as f:
            json.dump(view, f, ensure_ascii=False, indent=2)
        # A dishonest builder re-seals the leaky view; content check still fires.
        from core.helix_holdout import sha256_file
        candidate["candidate_view"]["sha256"] = sha256_file(view_full)
        doc = lock_registry(doc)
        problems = validate_registry(self.root, doc)
        self.assertTrue(any("leaks labels" in p and "platform" in p for p in problems),
                        problems)


class TestPolicySemantics(HoldoutFixtureCase):
    def test_candidate_and_oracle_must_be_isolated(self):
        doc = copy.deepcopy(self.registry)
        candidate = doc["candidates"][0]
        candidate["oracle_commitment"]["path"] = candidate["candidate_view"]["path"]
        problems = validate_registry(self.root, doc, check_artifacts=False)
        self.assertTrue(any("not isolated" in p for p in problems), problems)

    def test_known_source_hash_cannot_be_eligible(self):
        known = next(c for c in self.registry["candidates"]
                     if c["candidate_id"] == "SYN-KNOWN-HASH")
        self.assertEqual(known["status"], "excluded")
        self.assertFalse(known["eligibility"]["source_hash_unseen"])
        self.assertTrue(known["eligibility"]["registry_overlap"])

    def test_known_family_cannot_be_eligible(self):
        known = next(c for c in self.registry["candidates"]
                     if c["candidate_id"] == "SYN-KNOWN-FAMILY")
        self.assertEqual(known["status"], "excluded")
        self.assertFalse(known["eligibility"]["family_unseen"])

    def test_live_cohort_requires_twenty_locked_eligible_candidates(self):
        small_root = tempfile.mkdtemp(prefix="helix-holdout-")
        self.addCleanup(shutil.rmtree, small_root, ignore_errors=True)
        os.makedirs(os.path.join(small_root, "schemas"))
        shutil.copy(os.path.join(ROOT, "schemas", "helix-holdout-registry.schema.json"),
                    os.path.join(small_root, "schemas"))
        registry = generate(small_root, eligible_count=19)
        problems = validate_registry(small_root, registry)
        self.assertTrue(any("locked eligible candidates" in p and ">= 20" in p
                            for p in problems), problems)

    def test_selection_rule_exclusions_force_excluded_status(self):
        from core.helix_holdout import build_candidate
        eligible = next(c for c in self.registry["candidates"]
                        if c["status"] != "excluded")
        spec = {
            "candidate_id": "FORCED-001",
            "source": {
                "kind": "local_snapshot",
                "locator": eligible["source"]["locator"],
                "immutable_revision": "forced-rev",
                "family_id": "forced-family",
                "license_id": "MIT",
                "license_evidence_path": eligible["source"]["license_evidence_path"],
            },
            "candidate_view_path": eligible["candidate_view"]["path"],
            "oracle_path": eligible["oracle_commitment"]["path"],
            "excluded_reasons": ["filter2: archived repository"],
        }
        built = build_candidate(self.root, spec,
                                self.registry["leakage_control"],
                                ("MIT",), set(), set())
        self.assertEqual(built["status"], "excluded")
        self.assertIn("filter2: archived repository",
                      built["eligibility"]["reasons"])

    def test_reveal_before_sealed_prediction_is_rejected(self):
        doc = copy.deepcopy(self.registry)
        candidate = doc["candidates"][0]
        candidate["oracle_commitment"]["access"] = "revealed"
        candidate["reveal"]["status"] = "revealed"
        problems = validate_registry(self.root, doc, check_artifacts=False)
        self.assertTrue(any("reveal before sealed prediction" in p for p in problems),
                        problems)
        self.assertTrue(any("insufficient reveal approvals" in p for p in problems),
                        problems)

    def test_oracle_reveal_without_reveal_receipt_is_rejected(self):
        doc = copy.deepcopy(self.registry)
        doc["candidates"][0]["oracle_commitment"]["access"] = "revealed"
        problems = validate_registry(self.root, doc, check_artifacts=False)
        self.assertTrue(any("oracle revealed without a reveal receipt" in p
                            for p in problems), problems)


class TestSeedRegistry(unittest.TestCase):
    """The committed live-size registry must verify against the real repo files."""

    def setUp(self):
        self.registry = _load(SEED_REGISTRY)

    def test_seed_registry_is_locked_live_and_fully_valid(self):
        self.assertEqual(self.registry["cohort"]["kind"], "live")
        self.assertEqual(self.registry["cohort"]["status"], "locked")
        self.assertEqual(validate_registry(ROOT, self.registry), [])

    def test_seed_registry_has_twenty_locked_eligible_candidates(self):
        self.assertGreaterEqual(len(locked_eligible_candidates(self.registry)), 20)

    def test_seed_registry_matches_the_generator(self):
        other = tempfile.mkdtemp(prefix="helix-holdout-")
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        self.assertEqual(generate(other), self.registry)


if __name__ == "__main__":
    unittest.main()
