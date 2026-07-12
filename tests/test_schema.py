"""Tests for v0.4 F1 SchemaEnforce: schemas/*.json are now a checked contract."""
import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_schema import (
    validate_against_schema, schema_features, schema_path,
)
from core.helix_validate import cross_check_schema_vs_validator
from core.helix_diversity import measure_diversity
from core.helix_provenance import winner_to_corpus_entry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestStdlibWalker(unittest.TestCase):
    def test_required_key_missing(self):
        schema = {"type": "object", "required": ["a", "b"], "properties": {}}
        probs = validate_against_schema({"a": 1}, schema)
        self.assertTrue(any("missing required key 'b'" in p for p in probs))

    def test_type_mismatch(self):
        schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
        self.assertTrue(validate_against_schema({"n": "not-int"}, schema))
        self.assertEqual(validate_against_schema({"n": 7}, schema), [])

    def test_integer_excludes_bool(self):
        schema = {"type": "integer"}
        self.assertTrue(validate_against_schema(True, schema))  # bool is not integer here

    def test_type_union_with_null(self):
        schema = {"type": "object", "properties": {"x": {"type": ["string", "null"]}}}
        self.assertEqual(validate_against_schema({"x": None}, schema), [])
        self.assertEqual(validate_against_schema({"x": "s"}, schema), [])
        self.assertTrue(validate_against_schema({"x": 3}, schema))

    def test_enum(self):
        schema = {"type": "object", "properties": {"o": {"enum": ["explore", "exploit"]}}}
        self.assertEqual(validate_against_schema({"o": "explore"}, schema), [])
        self.assertTrue(validate_against_schema({"o": "bogus"}, schema))

    def test_min_max(self):
        schema = {"type": "integer", "minimum": 0, "maximum": 4}
        self.assertEqual(validate_against_schema(3, schema), [])
        self.assertTrue(validate_against_schema(-1, schema))
        self.assertTrue(validate_against_schema(5, schema))

    def test_array_items(self):
        schema = {"type": "array", "items": {"type": "string"}}
        self.assertEqual(validate_against_schema(["a", "b"], schema), [])
        self.assertTrue(validate_against_schema(["a", 2], schema))

    def test_deterministic(self):
        schema = {"type": "object", "required": ["a", "b", "c"], "properties": {}}
        self.assertEqual(validate_against_schema({}, schema), validate_against_schema({}, schema))


class TestShippedSchemas(unittest.TestCase):
    def test_all_schemas_in_walker_subset(self):
        for name in ("ledger", "diversity-report", "loop-state", "corpus-entry",
                     "helix-state-receipt", "helix-holdout-registry"):
            with open(schema_path(ROOT, name), encoding="utf-8") as f:
                feats = schema_features(json.load(f))
            self.assertTrue(feats["in_subset"],
                            f"{name}.schema uses unsupported keywords {feats['unsupported']}")

    def test_example_ledger_matches_schema(self):
        with open(os.path.join(ROOT, "examples", "consumed_ledger.json"), encoding="utf-8") as f:
            doc = json.load(f)
        self.assertEqual(validate_against_schema(doc, schema_path(ROOT, "ledger")), [])

    def test_generated_diversity_report_matches_schema(self):
        rep = measure_diversity([{"title": "a b"}, {"title": "a c"}])
        self.assertEqual(validate_against_schema(rep, schema_path(ROOT, "diversity-report")), [])

    def test_corpus_entry_with_lineage_matches_schema(self):
        entry = winner_to_corpus_entry({
            "idea_id": "IDEA-9", "title": "T", "source_chain": {"cix": "CIX-1"},
            "implementations": [{"project_name": "P", "project_path": "p"}]})
        self.assertEqual(validate_against_schema(entry, schema_path(ROOT, "corpus-entry")), [])

    def test_no_schema_validator_drift(self):
        self.assertEqual(cross_check_schema_vs_validator(ROOT), [])


if __name__ == "__main__":
    unittest.main()
