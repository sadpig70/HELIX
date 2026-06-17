#!/usr/bin/env python3
"""HELIX structure & contract validator (stdlib only).

Light, dependency-free validation (same philosophy as ProjectGenome
scripts/validate_projectgenome.py): check that the shipped contracts and example
artifacts are internally consistent, without pulling in jsonschema.

CLI:
    python core/helix_validate.py            # validate repo at cwd
    python core/helix_validate.py <root>
"""

import json
import os
import sys

try:  # package import (python -m core.helix_validate) or library use
    from .helix_ledger import is_consumed, MATCH_KEYS
    from .helix_diversity import DEFAULT_THRESHOLDS
    from .helix_loop import VALID_ACTIONS, next_action
except ImportError:  # direct script run: python core/helix_validate.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_ledger import is_consumed, MATCH_KEYS
    from core.helix_diversity import DEFAULT_THRESHOLDS
    from core.helix_loop import VALID_ACTIONS, next_action

REQUIRED_LEDGER_KEYS = ("schema_version", "consumed", "blocked_names",
                        "source_fingerprints", "generated_fingerprints")
REQUIRED_ENTRY_KEYS = ("idea_id", "title")


def validate_ledger(ledger: dict) -> list:
    """Return a list of problems (empty = valid)."""
    problems = []
    if not isinstance(ledger, dict):
        return ["ledger is not an object"]
    for key in REQUIRED_LEDGER_KEYS:
        if key not in ledger:
            problems.append(f"ledger missing key: {key}")
    for i, entry in enumerate(ledger.get("consumed", [])):
        for key in REQUIRED_ENTRY_KEYS:
            if not entry.get(key):
                problems.append(f"consumed[{i}] missing/empty: {key}")
    # cross-check: is_consumed on a recorded entry must report consumed
    for i, entry in enumerate(ledger.get("consumed", [])):
        probe = {"idea_id": entry.get("idea_id"), "title": entry.get("title")}
        res = is_consumed(probe, ledger)
        if not res["consumed"]:
            problems.append(f"consumed[{i}] ({entry.get('idea_id')}) "
                            f"not self-detected by is_consumed")
    return problems


def validate_diversity_report(rep: dict) -> list:
    problems = []
    for key in ("triggered", "breaches", "metrics", "signals"):
        if key not in rep:
            problems.append(f"diversity report missing key: {key}")
    if "metrics" in rep:
        for m in ("keyword_coverage", "max_pair_count"):
            if m not in rep["metrics"]:
                problems.append(f"diversity metrics missing: {m}")
    return problems


def validate_loop_action(action: dict) -> list:
    problems = []
    if action.get("action") not in VALID_ACTIONS:
        problems.append(f"invalid loop action: {action.get('action')}")
    if not action.get("why"):
        problems.append("loop action missing 'why'")
    return problems


EXPECTED_SKILLS = [
    # shared notation
    "pg", "pgf", "pgxf",
    # explore (IdeaFirst)
    "sdx", "sdxx", "sdx_ci", "tcx", "idx", "idxx", "cix", "cixx", "evx", "aox",
    "sa-aox", "sa-evx", "sa-icx", "collect_git_trand",
    # exploit (recreate)
    "recreate", "pgfr-combo",
]


def validate_skill_inventory(root: str) -> list:
    """Ensure the self-contained skill inventory + key dependencies are vendored."""
    problems = []
    for name in EXPECTED_SKILLS:
        if not os.path.exists(os.path.join(root, "skills", name, "SKILL.md")):
            problems.append(f"missing vendored skill: skills/{name}/SKILL.md")
    # aox/cix/evx depend on this exact file
    if not os.path.exists(os.path.join(root, "skills", "pgf", "discovery", "personas.json")):
        problems.append("missing skills/pgf/discovery/personas.json (aox/cix/evx dependency)")
    return problems


def validate_project(root: str) -> list:
    """Validate the HELIX project layout + example artifacts under `root`."""
    problems = []
    problems += validate_skill_inventory(root)
    expected = [
        "core/helix_fingerprint.py",
        "core/helix_ledger.py",
        "core/helix_diversity.py",
        "core/helix_provenance.py",
        "core/helix_loop.py",
        "core/helix_validate.py",
        "engines/explore/adapter.py",
        "engines/exploit/adapter.py",
        "engines/unify.py",
        "engines/loaders.py",
        "helix.py",
        "schemas/ledger.schema.json",
        "schemas/diversity-report.schema.json",
        "schemas/loop-state.schema.json",
        "schemas/corpus-entry.schema.json",
        "docs/ARCHITECTURE.md",
        "docs/SUBSTRATE-CONTRACT.md",
        "README.md",
    ]
    for rel in expected:
        if not os.path.exists(os.path.join(root, rel)):
            problems.append(f"missing file: {rel}")

    # validate example ledger if present
    ex = os.path.join(root, "examples", "consumed_ledger.json")
    if os.path.exists(ex):
        with open(ex, "r", encoding="utf-8") as f:
            problems += [f"examples/consumed_ledger.json: {p}"
                         for p in validate_ledger(json.load(f))]

    # smoke-check the loop policy is wired (deterministic)
    a = next_action({"corpus_size": 0})
    problems += [f"loop smoke: {p}" for p in validate_loop_action(a)]

    return problems


def _main(argv) -> int:
    root = argv[1] if len(argv) > 1 else "."
    print(f"=== HELIX validation (root: {os.path.abspath(root)}) ===")
    print(f"  - match keys: {', '.join(MATCH_KEYS)}")
    print(f"  - diversity thresholds: {DEFAULT_THRESHOLDS}")
    problems = validate_project(root)
    if problems:
        print("\nFAIL — problems:")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("\nPASS — HELIX structure + example artifacts consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
