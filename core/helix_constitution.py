#!/usr/bin/env python3
"""Action intent contract for the HELIX Constitution (T2 governance).

Policy source of truth: .pgf/DESIGN-HELIXDirection.md (ActionIntent node) and
_workspace/HELIXDirection_process_plan.md §P3 risk table:

    R0  read-only inspection                          deterministic auto-allow
    R1  local reversible artifact                     allow within budget
    R2  write / publish / remote mutation             one human approval
    R3  authority, economic, physical, broad public   two-party approval + dry-run

This module fixes the intent SHAPE and the deterministic risk derivation. The
declared risk class may never be LOWER than the class derived from the
intent's own declared effects — under-classification fails closed. Approval
matrices, expiry, and gate evaluation belong to later Constitution nodes
(P3_3/P3_4); this module deliberately stops at the contract.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import json
import os
import sys

try:  # package import (python -m core.helix_constitution) or library use
    from .helix_holdout import canonical_json_bytes
    from .helix_schema import validate_against_schema, schema_path
except ImportError:  # direct script run: python core/helix_constitution.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import canonical_json_bytes
    from core.helix_schema import validate_against_schema, schema_path

SCHEMA_NAME = "action-intent"
SCHEMA_ID = "helix-action-intent/1.0"
RISK_ORDER = ("R0", "R1", "R2", "R3")


def intent_digest(intent: dict) -> str:
    """Canonical SHA256 identity of an intent (key-order independent)."""
    return hashlib.sha256(canonical_json_bytes(intent)).hexdigest()


def classify_risk(intent: dict) -> str:
    """Derive the minimum honest risk class from the declared effects.

    Pure function of scope/impact/reversibility — proposers cannot lower it
    by choosing a friendlier label.
    """
    impact = intent["impact"]
    if any(impact[key] for key in ("authority", "economic", "physical", "broad_public")):
        return "R3"
    scope = intent["scope"]
    writes = bool(scope["write_paths"])
    if scope["remote_mutation"] or scope["publish"]:
        return "R2"
    if writes and not intent["reversibility"]["reversible"]:
        return "R2"
    if writes:
        return "R1"
    return "R0"


def validate_action_intent(root: str, intent: dict) -> list:
    """Schema + semantic validation. Empty list == admissible intent shape."""
    problems = [f"schema: {p}" for p in validate_against_schema(
        intent, schema_path(root, SCHEMA_NAME))]
    if problems:
        return problems  # shape is broken; semantic checks would be noise

    for key in ("intent_id", "title", "justification"):
        if not intent[key].strip():
            problems.append(f"{key} must be non-empty")
    if not intent["proposer"]["id"].strip():
        problems.append("proposer.id must be non-empty")

    scope = intent["scope"]
    seen_paths = set()
    for path in scope["write_paths"]:
        if not path.strip():
            problems.append("scope.write_paths contains an empty path")
        elif path in seen_paths:
            problems.append(f"scope.write_paths duplicate: {path}")
        seen_paths.add(path)

    reversibility = intent["reversibility"]
    if reversibility["reversible"] and not (reversibility["rollback_plan"] or "").strip():
        problems.append("reversible intent requires a rollback_plan")

    derived = classify_risk(intent)
    declared = intent["risk_class"]
    if RISK_ORDER.index(declared) < RISK_ORDER.index(derived):
        problems.append(
            f"risk under-classification: declared {declared} < derived {derived} "
            "(fail-closed; declare the derived class or higher)")

    budget = intent["budget"]
    if scope["write_paths"] and (budget["max_files"] < 1 or budget["max_bytes"] < 1):
        problems.append("write intent requires a positive budget "
                        "(max_files >= 1 and max_bytes >= 1)")

    return sorted(problems)


def _main(argv) -> int:
    if len(argv) < 2:
        print("usage: python core/helix_constitution.py <intent.json> [root]")
        return 2
    root = os.path.abspath(argv[2] if len(argv) > 2 else ".")
    with open(argv[1], "r", encoding="utf-8") as f:
        intent = json.load(f)
    problems = validate_action_intent(root, intent)
    print(f"=== HELIX action intent ({intent.get('intent_id')}) ===")
    print(f"  title:    {intent.get('title')}")
    print(f"  declared: {intent.get('risk_class')}  derived: {classify_risk(intent)}")
    print(f"  digest:   {intent_digest(intent)}")
    if problems:
        print("\nFAIL — problems:")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("\nPASS — intent is schema-valid and honestly classified.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
