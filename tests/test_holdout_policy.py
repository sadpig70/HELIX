import copy
import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_schema import schema_features, validate_against_schema


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "helix-holdout-registry.schema.json")
EXAMPLE = os.path.join(ROOT, "examples", "holdout", "registry-policy-example.json")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def policy_problems(registry):
    problems = []
    cohort = registry["cohort"]
    if cohort["kind"] == "live" and cohort["minimum_candidates"] < 20:
        problems.append("live cohort minimum_candidates must be >= 20")
    forbidden = set(registry["leakage_control"]["forbidden_candidate_fields"])
    required_forbidden = {
        "expected", "machines", "machine_id", "action", "expected_action",
        "platform", "platform_hint", "oracle_rationale",
    }
    if not required_forbidden <= forbidden:
        problems.append("forbidden candidate label set is incomplete")
    credits = registry["scoring"]["credits"]
    for outcome in ("wrong", "abstain", "missing_artifact", "protocol_violation"):
        if credits[outcome] != 0:
            problems.append(f"{outcome} success credit must be 0")
    if registry["scoring"]["coverage_denominator"] != "locked_eligible_candidates":
        problems.append("coverage denominator can exclude locked candidates")
    if registry["scoring"]["score_denominator"] != "locked_eligible_candidates":
        problems.append("score denominator can exclude locked candidates")

    excluded_hashes = set(registry["leakage_control"]["excluded_source_hashes"])
    for candidate in registry["candidates"]:
        cid = candidate["candidate_id"]
        source = candidate["source"]
        eligibility = candidate["eligibility"]
        view = candidate["candidate_view"]
        oracle = candidate["oracle_commitment"]
        prediction = candidate["prediction_receipt"]
        reveal = candidate["reveal"]
        if view["path"] == oracle["path"] or view["sha256"] == oracle["sha256"]:
            problems.append(f"{cid}: candidate and oracle are not isolated")
        if source["artifact_sha256"] in excluded_hashes and candidate["status"] != "excluded":
            problems.append(f"{cid}: known source hash must be excluded")
        eligible = (eligibility["source_hash_unseen"] and eligibility["family_unseen"]
                    and not eligibility["registry_overlap"] and eligibility["license_allowed"])
        if candidate["status"] == "eligible" and not eligible:
            problems.append(f"{cid}: eligibility claims do not support eligible status")
        if oracle["access"] == "sealed" and reveal["status"] == "revealed":
            problems.append(f"{cid}: reveal contradicts sealed oracle")
        if reveal["status"] == "revealed":
            if prediction["status"] != "sealed" or not prediction["sha256"]:
                problems.append(f"{cid}: reveal before sealed prediction")
            if len(reveal["authorized_by"]) < registry["reveal_authority"]["required_approvals"]:
                problems.append(f"{cid}: insufficient reveal approvals")
        if not source["immutable_revision"] or not source["license_evidence_sha256"]:
            problems.append(f"{cid}: source or license evidence is not immutable")
    return problems


class TestHoldoutPolicy(unittest.TestCase):
    def setUp(self):
        self.schema = _load(SCHEMA)
        self.example = _load(EXAMPLE)

    def test_schema_is_in_stdlib_subset(self):
        self.assertEqual(schema_features(self.schema), {"in_subset": True, "unsupported": []})

    def test_synthetic_fixture_matches_shape_and_semantics(self):
        self.assertEqual(validate_against_schema(self.example, self.schema), [])
        self.assertEqual(policy_problems(self.example), [])

    def test_live_cohort_requires_twenty_candidates(self):
        doc = copy.deepcopy(self.example)
        doc["cohort"]["kind"] = "live"
        doc["cohort"]["minimum_candidates"] = 19
        self.assertIn("live cohort minimum_candidates must be >= 20", policy_problems(doc))

    def test_abstain_and_missing_cannot_receive_success_credit(self):
        for outcome in ("abstain", "missing_artifact", "protocol_violation"):
            with self.subTest(outcome=outcome):
                doc = copy.deepcopy(self.example)
                doc["scoring"]["credits"][outcome] = 1
                self.assertTrue(any(outcome in p for p in policy_problems(doc)))

    def test_candidate_and_oracle_must_be_isolated(self):
        doc = copy.deepcopy(self.example)
        candidate = doc["candidates"][0]
        candidate["oracle_commitment"]["path"] = candidate["candidate_view"]["path"]
        self.assertTrue(any("not isolated" in p for p in policy_problems(doc)))

    def test_known_source_cannot_be_eligible(self):
        doc = copy.deepcopy(self.example)
        candidate = doc["candidates"][1]
        candidate["status"] = "eligible"
        self.assertTrue(any("known source hash" in p for p in policy_problems(doc)))

    def test_reveal_requires_prediction_and_approval(self):
        doc = copy.deepcopy(self.example)
        candidate = doc["candidates"][0]
        candidate["oracle_commitment"]["access"] = "revealed"
        candidate["reveal"]["status"] = "revealed"
        problems = policy_problems(doc)
        self.assertTrue(any("sealed prediction" in p for p in problems))
        self.assertTrue(any("reveal approvals" in p for p in problems))

    def test_required_label_fields_stay_forbidden(self):
        doc = copy.deepcopy(self.example)
        doc["leakage_control"]["forbidden_candidate_fields"].remove("platform")
        self.assertIn("forbidden candidate label set is incomplete", policy_problems(doc))


if __name__ == "__main__":
    unittest.main()
