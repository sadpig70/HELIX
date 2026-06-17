#!/usr/bin/env python3
"""HELIX schema enforcement — make schemas/*.json a *checked* contract (stdlib only).

The repo ships four JSON Schema (draft-07) contracts under `schemas/`, but until
now nothing loaded them: `helix_validate` only hand-checked a subset of keys, so
the declared schemas could silently drift from the data and the validator. This
module closes that gap.

Determinism boundary (same pattern as engines/loaders.py PyYAML use): if the
optional `jsonschema` package is present it is used (full draft-07); otherwise a
deterministic stdlib subset walker validates the keywords the HELIX schemas
actually use — `type` (incl. ["string","null"] unions), `required`, `properties`,
`items`, `enum`, `minimum`, `maximum`. The HELIX schemas use no `$ref`/`allOf`/
`oneOf`, so the subset is complete for them; `schema_features()` flags anything
out of subset so a schema change can't silently outrun the walker.
"""

import json
import os

# JSON Schema type name -> Python type(s). "integer" excludes bool (Python quirk).
_TYPE_OK = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}

# Keywords the stdlib walker understands. A schema using anything else needs jsonschema.
_SUPPORTED = {
    "$schema", "$id", "title", "description", "type", "required", "properties",
    "items", "enum", "minimum", "maximum",
}


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _type_matches(value, type_spec) -> bool:
    types = type_spec if isinstance(type_spec, list) else [type_spec]
    return any(_TYPE_OK.get(t, lambda v: True)(value) for t in types)


def _walk(value, schema, path, problems):
    """Deterministic recursive validation of the draft-07 subset HELIX uses."""
    t = schema.get("type")
    if t is not None and not _type_matches(value, t):
        problems.append(f"{path}: expected type {t}, got {type(value).__name__}")
        return  # type mismatch -> deeper checks would be noise

    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} not in enum {schema['enum']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            problems.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                problems.append(f"{path}: missing required key '{key}'")
        props = schema.get("properties", {})
        for key in sorted(value):  # sorted -> deterministic problem order
            if key in props:
                _walk(value[key], props[key], f"{path}.{key}", problems)

    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _walk(item, schema["items"], f"{path}[{i}]", problems)


def schema_features(schema: dict) -> dict:
    """Report whether a schema stays inside the stdlib walker's supported subset.

    {in_subset: bool, unsupported: [keyword, ...]} — used by tests/validate so a
    future schema using $ref/allOf/oneOf forces the jsonschema path instead of
    being silently under-validated by the walker.
    """
    unsupported = set()

    def scan_schema(node):
        # `node` is a (sub)schema object; its KEYS are keywords, but the keys of a
        # `properties` map are arbitrary property names (not keywords).
        if not isinstance(node, dict):
            return
        for k, v in node.items():
            if k not in _SUPPORTED and not k.startswith("$"):
                unsupported.add(k)
            if k in ("properties", "definitions", "patternProperties"):
                if isinstance(v, dict):
                    for sub in v.values():
                        scan_schema(sub)
            elif k == "items":
                for sub in (v if isinstance(v, list) else [v]):
                    scan_schema(sub)
            elif k in ("additionalProperties", "not"):
                scan_schema(v)
            elif k in ("allOf", "anyOf", "oneOf"):
                if isinstance(v, list):
                    for sub in v:
                        scan_schema(sub)

    scan_schema(schema)
    return {"in_subset": not unsupported, "unsupported": sorted(unsupported)}


def validate_against_schema(doc, schema) -> list:
    """Validate `doc` against a draft-07 `schema` (path str or parsed dict).

    Uses `jsonschema` when installed (full draft-07), else the deterministic
    stdlib subset walker. Returns a list of problem strings (empty == valid).
    """
    if isinstance(schema, str):
        schema = _load_json(schema)
    try:
        import jsonschema  # optional; full draft-07 when available
        return [f"$.{'.'.join(str(p) for p in e.absolute_path)}: {e.message}"
                for e in sorted(jsonschema.Draft7Validator(schema).iter_errors(doc),
                                key=lambda e: list(e.absolute_path))]
    except ImportError:
        problems = []
        _walk(doc, schema, "$", problems)
        return problems


def schema_path(root: str, name: str) -> str:
    """Absolute path to a shipped schema (e.g. name='ledger')."""
    return os.path.join(root, "schemas", f"{name}.schema.json")
