import copy
import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_constitution import (
    classify_risk,
    intent_digest,
    validate_action_intent,
)
from core.helix_schema import schema_features


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "action-intent.schema.json")
EXAMPLES = os.path.join(ROOT, "examples", "constitution")


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as f:
        return json.load(f)


class TestExamplesAndSchema(unittest.TestCase):
    def test_schema_stays_in_stdlib_subset(self):
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema_features(schema), {"in_subset": True, "unsupported": []})

    def _intent_names(self):
        return [name for name in sorted(os.listdir(EXAMPLES))
                if name.startswith("intent-") and name.endswith(".json")]

    def test_all_example_intents_validate(self):
        for name in self._intent_names():
            with self.subTest(example=name):
                self.assertEqual(validate_action_intent(ROOT, _load(name)), [])

    def test_examples_cover_every_risk_class(self):
        declared = {_load(name)["risk_class"] for name in self._intent_names()}
        self.assertEqual(declared, {"R0", "R1", "R2", "R3"})


class TestRiskDerivation(unittest.TestCase):
    def setUp(self):
        self.base = _load("intent-r0-inspect.json")

    def variant(self, **changes):
        intent = copy.deepcopy(self.base)
        for dotted, value in changes.items():
            target = intent
            keys = dotted.split(".")
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
        return intent

    def test_read_only_derives_r0(self):
        self.assertEqual(classify_risk(self.base), "R0")

    def test_reversible_local_write_derives_r1(self):
        intent = self.variant(**{"scope.write_paths": ["out/report.json"]})
        self.assertEqual(classify_risk(intent), "R1")

    def test_irreversible_local_write_derives_r2(self):
        intent = self.variant(**{"scope.write_paths": ["out/report.json"],
                                 "reversibility.reversible": False,
                                 "reversibility.rollback_plan": None})
        self.assertEqual(classify_risk(intent), "R2")

    def test_publish_and_remote_mutation_derive_r2(self):
        self.assertEqual(classify_risk(self.variant(**{"scope.publish": True})), "R2")
        self.assertEqual(
            classify_risk(self.variant(**{"scope.remote_mutation": True})), "R2")

    def test_any_impact_flag_derives_r3(self):
        for flag in ("authority", "economic", "physical", "broad_public"):
            with self.subTest(flag=flag):
                intent = self.variant(**{f"impact.{flag}": True})
                self.assertEqual(classify_risk(intent), "R3")

    def test_impact_dominates_scope(self):
        intent = self.variant(**{"impact.economic": True, "scope.publish": True})
        self.assertEqual(classify_risk(intent), "R3")


class TestFailClosedValidation(unittest.TestCase):
    def setUp(self):
        self.base = _load("intent-r1-local-artifact.json")

    def test_under_classification_is_rejected(self):
        cases = (
            ("intent-r1-local-artifact.json", "R0"),
            ("intent-r2-publish.json", "R1"),
            ("intent-r3-authority.json", "R2"),
        )
        for name, lower in cases:
            with self.subTest(name=name, declared=lower):
                intent = _load(name)
                intent["risk_class"] = lower
                problems = validate_action_intent(ROOT, intent)
                self.assertTrue(any("under-classification" in p for p in problems),
                                problems)

    def test_over_declaration_is_allowed(self):
        intent = _load("intent-r0-inspect.json")
        intent["risk_class"] = "R2"
        self.assertEqual(validate_action_intent(ROOT, intent), [])

    def test_reversible_requires_rollback_plan(self):
        intent = copy.deepcopy(self.base)
        intent["reversibility"]["rollback_plan"] = "  "
        problems = validate_action_intent(ROOT, intent)
        self.assertTrue(any("rollback_plan" in p for p in problems), problems)

    def test_write_intent_requires_positive_budget(self):
        intent = copy.deepcopy(self.base)
        intent["budget"]["max_files"] = 0
        problems = validate_action_intent(ROOT, intent)
        self.assertTrue(any("positive budget" in p for p in problems), problems)

    def test_empty_or_duplicate_write_paths_are_rejected(self):
        intent = copy.deepcopy(self.base)
        intent["scope"]["write_paths"] = ["a.txt", "a.txt", " "]
        problems = validate_action_intent(ROOT, intent)
        self.assertTrue(any("duplicate" in p for p in problems), problems)
        self.assertTrue(any("empty path" in p for p in problems), problems)

    def test_blank_identity_fields_are_rejected(self):
        intent = copy.deepcopy(self.base)
        intent["justification"] = "   "
        intent["proposer"]["id"] = ""
        problems = validate_action_intent(ROOT, intent)
        self.assertTrue(any("justification" in p for p in problems), problems)
        self.assertTrue(any("proposer.id" in p for p in problems), problems)

    def test_schema_shape_failures_are_reported(self):
        intent = copy.deepcopy(self.base)
        del intent["impact"]
        problems = validate_action_intent(ROOT, intent)
        self.assertTrue(any("schema:" in p and "impact" in p for p in problems),
                        problems)


class TestDigest(unittest.TestCase):
    def test_digest_is_deterministic_and_key_order_independent(self):
        intent = _load("intent-r2-publish.json")
        reordered = json.loads(json.dumps(intent, sort_keys=True))
        self.assertEqual(intent_digest(intent), intent_digest(reordered))

    def test_digest_changes_when_content_changes(self):
        intent = _load("intent-r2-publish.json")
        changed = copy.deepcopy(intent)
        changed["scope"]["publish"] = False
        self.assertNotEqual(intent_digest(intent), intent_digest(changed))


if __name__ == "__main__":
    unittest.main()
