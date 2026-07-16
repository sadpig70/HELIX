import json
import os
import unittest

import tests._path  # noqa: F401
from core.helix_schema import schema_features, schema_path, validate_against_schema


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEMA_NAMES = (
    "source-lock",
    "machine-evidence",
    "parity-contract",
    "parity-receipt",
    "provenance-statement",
    "evidence-registry",
)


def load_json(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


class TestParityProvenanceSchemas(unittest.TestCase):
    def test_schemas_stay_in_stdlib_subset(self):
        for name in SCHEMA_NAMES:
            schema = load_json("schemas", f"{name}.schema.json")
            self.assertEqual(
                schema_features(schema),
                {"in_subset": True, "unsupported": []},
                f"{name}.schema.json must stay in HELIX stdlib validator subset",
            )

    def test_valid_minimal_fixtures_match_schemas(self):
        fixture = load_json("examples", "parity-provenance", "valid_minimal.json")
        for name in SCHEMA_NAMES:
            self.assertEqual(
                validate_against_schema(fixture[name], schema_path(ROOT, name)),
                [],
                name,
            )

    def test_missing_required_fixtures_are_rejected(self):
        fixture = load_json("examples", "parity-provenance", "invalid_missing_required.json")
        for name in SCHEMA_NAMES:
            problems = validate_against_schema(fixture[name], schema_path(ROOT, name))
            self.assertTrue(problems, name)
            self.assertTrue(any("missing required key" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
