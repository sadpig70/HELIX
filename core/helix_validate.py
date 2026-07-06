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
    from .helix_diversity import DEFAULT_THRESHOLDS, measure_diversity
    from .helix_loop import VALID_ACTIONS, next_action
    from .helix_project_paths import ensure_project_src
    from .helix_schema import validate_against_schema, schema_features, schema_path
except ImportError:  # direct script run: python core/helix_validate.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_ledger import is_consumed, MATCH_KEYS
    from core.helix_diversity import DEFAULT_THRESHOLDS, measure_diversity
    from core.helix_loop import VALID_ACTIONS, next_action
    from core.helix_project_paths import ensure_project_src
    from core.helix_schema import validate_against_schema, schema_features, schema_path

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


def validate_corpus_entry(entry: dict) -> list:
    """A corpus source must be a named project with a known origin (non-empty)."""
    problems = []
    if not entry.get("project"):
        problems.append("corpus entry: empty/missing project")
    if entry.get("origin") not in ("explore", "exploit"):
        problems.append(f"corpus entry: bad origin {entry.get('origin')!r}")
    return problems


def validate_loop_state(state: dict) -> list:
    problems = []
    if state.get("last_engine") not in (None, "explore", "exploit"):
        problems.append(f"loop state: bad last_engine {state.get('last_engine')!r}")
    cs = state.get("corpus_size", 0)
    if not isinstance(cs, int) or cs < 0:
        problems.append(f"loop state: corpus_size must be a non-negative int, got {cs!r}")
    return problems


def validate_thresholds(P: dict) -> list:
    """Sanity-check a thresholds dict: ratios in [0,1], counts >= 1."""
    problems = []
    for k in ("keyword_coverage", "avg_embedding_sim", "winner_embedding_similarity",
              "dup_cos", "unique_ratio_floor"):
        v = P.get(k)
        try:
            if v is None or not (0.0 <= float(v) <= 1.0):
                problems.append(f"threshold {k} out of [0,1]: {v!r}")
        except (TypeError, ValueError):
            problems.append(f"threshold {k} not a number: {v!r}")
    if int(P.get("min_breaches", 0)) < 1:
        problems.append(f"min_breaches must be >= 1: {P.get('min_breaches')!r}")
    if int(P.get("max_pair_count", 0)) < 1:
        problems.append(f"max_pair_count must be >= 1: {P.get('max_pair_count')!r}")
    return problems


def _schema_required(root: str, name: str) -> set:
    """Top-level `required` keys declared by a shipped schema."""
    try:
        with open(schema_path(root, name), "r", encoding="utf-8") as f:
            return set(json.load(f).get("required", []))
    except (FileNotFoundError, ValueError):
        return set()


def cross_check_schema_vs_validator(root: str) -> list:
    """Detect drift between schemas/ and the hand-written validators (F1).

    The schema's declared `required` keys must match what the code enforces; if a
    schema gains/loses a required key without the validator following, this fires.
    Also flags any schema that uses keywords outside the stdlib walker's subset
    while jsonschema is absent (would be silently under-validated).
    """
    problems = []
    ledger_req = _schema_required(root, "ledger")
    if ledger_req and ledger_req != set(REQUIRED_LEDGER_KEYS):
        problems.append(f"schema/validator drift: ledger.schema required {sorted(ledger_req)} "
                        f"!= REQUIRED_LEDGER_KEYS {sorted(REQUIRED_LEDGER_KEYS)}")
    try:
        import jsonschema  # noqa: F401
        have_jsonschema = True
    except ImportError:
        have_jsonschema = False
    if not have_jsonschema:
        for name in ("ledger", "diversity-report", "loop-state", "corpus-entry"):
            sp = schema_path(root, name)
            if not os.path.exists(sp):
                continue
            with open(sp, "r", encoding="utf-8") as f:
                feats = schema_features(json.load(f))
            if not feats["in_subset"]:
                problems.append(f"{name}.schema uses unsupported keywords {feats['unsupported']} "
                                f"and jsonschema is not installed (would be under-validated)")
    return problems


def validate_schemas(root: str) -> list:
    """Validate live/example artifacts against their shipped JSON Schemas (F1)."""
    problems = []
    # example ledger ↔ ledger.schema
    ex = os.path.join(root, "examples", "consumed_ledger.json")
    if os.path.exists(ex):
        with open(ex, "r", encoding="utf-8") as f:
            problems += [f"examples/consumed_ledger.json !~ ledger.schema: {p}"
                         for p in validate_against_schema(json.load(f), schema_path(root, "ledger"))]
    # a generated diversity report ↔ diversity-report.schema
    rep = measure_diversity([{"title": "a b"}, {"title": "a c"}])
    problems += [f"diversity report !~ diversity-report.schema: {p}"
                 for p in validate_against_schema(rep, schema_path(root, "diversity-report"))]
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


def validate_handback_integration(root: str) -> list:
    """Validate ActionHandbackVerifier integration artifacts (handback gate).

    Checks: (1) close_loop_demo/winner.json parses with required keys,
    (2) ActionHandbackVerifier core files exist, (3) the shipped handback
    packet fixture evaluates to ``valid`` via the verifier.
    """
    problems = []

    # 1. close_loop_demo winner fixture
    winner_path = os.path.join(root, "examples", "close_loop_demo", "winner.json")
    if os.path.exists(winner_path):
        with open(winner_path, "r", encoding="utf-8") as f:
            try:
                winner = json.load(f)
            except ValueError as e:
                problems.append(f"close_loop_demo/winner.json: invalid JSON: {e}")
            else:
                for key in ("winner", "implementation"):
                    if key not in winner:
                        problems.append(f"close_loop_demo/winner.json: missing key '{key}'")
    else:
        problems.append("missing file: examples/close_loop_demo/winner.json")

    # 2. ActionHandbackVerifier core files
    for rel in ("ActionHandbackVerifier/src/ActionHandbackVerifier/__init__.py",
                "ActionHandbackVerifier/src/ActionHandbackVerifier/verifier.py",
                "ActionHandbackVerifier/src/ActionHandbackVerifier/ledger.py",
                "ActionHandbackVerifier/src/ActionHandbackVerifier/cli.py"):
        if not os.path.exists(os.path.join(root, rel)):
            problems.append(f"missing file: {rel}")

    # 3. handback packet fixture verifies as valid
    packet_path = os.path.join(root, "examples", "exploit_state", "handback_packet.json")
    if os.path.exists(packet_path):
        try:
            sys.path.insert(0, root)
            ensure_project_src(root, "ActionHandbackVerifier")
            from ActionHandbackVerifier.verifier import evaluate_handback
            with open(packet_path, "r", encoding="utf-8") as f:
                packet = json.load(f)
            result = evaluate_handback(packet)
            if result["verdict"] != "valid":
                problems.append(
                    f"handback_packet.json: expected valid, got {result['verdict']}")
        except ImportError:
            pass  # ActionHandbackVerifier absent (standalone extracted) — skip
        except Exception as e:
            problems.append(f"handback_packet.json: evaluation failed: {e}")
    else:
        problems.append("missing file: examples/exploit_state/handback_packet.json")

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

    # default thresholds must be sane
    problems += [f"default thresholds: {p}" for p in validate_thresholds(DEFAULT_THRESHOLDS)]

    # enforce the shipped JSON Schemas + detect schema/validator drift (F1)
    problems += validate_schemas(root)
    problems += cross_check_schema_vs_validator(root)

    # handback gate integration (ActionHandbackVerifier artifacts)
    problems += validate_handback_integration(root)

    return problems


def _main(argv) -> int:
    root = argv[1] if len(argv) > 1 else "."
    print(f"=== HELIX validation (root: {os.path.abspath(root)}) ===")
    print(f"  - match keys: {', '.join(MATCH_KEYS)}")
    print(f"  - diversity thresholds: {DEFAULT_THRESHOLDS}")
    print(f"  - handback gate: ActionHandbackVerifier")
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
