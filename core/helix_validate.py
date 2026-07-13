#!/usr/bin/env python3
"""HELIX structure & contract validator (stdlib only).

Light, dependency-free validation (same philosophy as ProjectGenome
scripts/validate_projectgenome.py): check that the shipped contracts and example
artifacts are internally consistent, without pulling in jsonschema.

CLI:
    python core/helix_validate.py            # validate repo at cwd
    python core/helix_validate.py <root>
"""

import ast
import hashlib
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

DETERMINISM_SCAN_DIRS = (
    "core",
    "engines",
    os.path.join("ActionHandbackVerifier", "src", "ActionHandbackVerifier"),
)

ZERO_KERNEL_LOCK = os.path.join("seed", "condense", "platform-kernel-lock.json")
MACHINE_PROBE_GATE = os.path.join("seed", "condense", "machine-probe-gate.json")
ROUTER_GATE = os.path.join("seed", "condense", "router-gate.json")
FORWARD_PREDICT_GATE = os.path.join("seed", "condense", "forward-predict-gate.json")

FORBIDDEN_IMPORT_ROOTS = {
    "http",
    "random",
    "requests",
    "secrets",
    "socket",
    "subprocess",
    "urllib",
}

FORBIDDEN_CALLS = {
    "datetime.date.today",
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "os.system",
    "time.monotonic",
    "time.perf_counter",
    "time.process_time",
    "time.time",
}

FORBIDDEN_CALL_PREFIXES = (
    "http.",
    "random.",
    "requests.",
    "secrets.",
    "socket.",
    "subprocess.",
    "urllib.",
)


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


def _iter_determinism_python_files(root: str):
    for rel_dir in DETERMINISM_SCAN_DIRS:
        base = os.path.join(root, rel_dir)
        if not os.path.isdir(base):
            continue
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith(".py"):
                    path = os.path.join(current, name)
                    yield path, os.path.relpath(path, root).replace(os.sep, "/")


def _call_name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _resolve_alias(name: str, aliases: dict) -> str:
    parts = name.split(".")
    if parts and parts[0] in aliases:
        return ".".join([aliases[parts[0]]] + parts[1:])
    return name


def _is_forbidden_call(name: str) -> bool:
    return name in FORBIDDEN_CALLS or any(name.startswith(prefix) for prefix in FORBIDDEN_CALL_PREFIXES)


def validate_determinism_boundary(root: str) -> list:
    """Static guard for runtime code that must remain deterministic/offline.

    This intentionally scans HELIX runtime boundaries only. Exploratory scripts,
    tests, and workspace artifacts may use clocks/processes/network for tooling,
    but core runtime code must not.
    """
    problems = []
    for path, rel in _iter_determinism_python_files(root):
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=rel)
        except SyntaxError as e:
            problems.append(f"{rel}: syntax error while determinism scanning: {e}")
            continue

        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".", 1)[0]
                    local = alias.asname or root_name
                    aliases[local] = alias.name
                    if root_name in FORBIDDEN_IMPORT_ROOTS:
                        problems.append(f"{rel}:{node.lineno}: forbidden import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root_name = module.split(".", 1)[0]
                if root_name in FORBIDDEN_IMPORT_ROOTS:
                    problems.append(f"{rel}:{node.lineno}: forbidden import from {module}")
                for alias in node.names:
                    local = alias.asname or alias.name
                    aliases[local] = f"{module}.{alias.name}" if module else alias.name

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                raw = _call_name(node.func)
                if not raw:
                    continue
                resolved = _resolve_alias(raw, aliases)
                if _is_forbidden_call(resolved):
                    problems.append(f"{rel}:{node.lineno}: forbidden call {resolved}")
    return problems


def _sha256_file(path: str) -> str:
    # Kernel locks describe source bytes, independent of Git checkout EOL mode.
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def _iter_kernel_files(base: str, kernel_dirs: list):
    for rel_dir in kernel_dirs:
        current_base = os.path.join(base, rel_dir)
        if not os.path.isdir(current_base):
            continue
        for current, dirs, files in os.walk(current_base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith(".py"):
                    path = os.path.join(current, name)
                    yield os.path.relpath(path, base).replace(os.sep, "/"), path


def validate_zero_kernel_change(root: str) -> list:
    """Ensure BUILD_ON_PLATFORM growth did not alter locked platform kernels.

    The lock is intentionally file-content based instead of git-status based so the
    validator stays stdlib-only and deterministic. Missing nested platform repos are
    skipped because HELIX itself does not vendor those repos.
    """
    problems = []
    lock_path = os.path.join(root, ZERO_KERNEL_LOCK)
    if not os.path.exists(lock_path):
        return [f"missing zero-kernel lock: {ZERO_KERNEL_LOCK}"]
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            lock = json.load(f)
    except ValueError as e:
        return [f"{ZERO_KERNEL_LOCK}: invalid JSON: {e}"]

    platforms = lock.get("platforms", {})
    if not isinstance(platforms, dict):
        return [f"{ZERO_KERNEL_LOCK}: platforms must be an object"]

    for platform, spec in sorted(platforms.items()):
        base = os.path.join(root, platform)
        if not os.path.isdir(base):
            continue
        kernel_dirs = spec.get("kernel_dirs", [])
        locked_files = spec.get("files", {})
        if not isinstance(kernel_dirs, list) or not isinstance(locked_files, dict):
            problems.append(f"{ZERO_KERNEL_LOCK}: {platform} has invalid lock shape")
            continue

        seen = set()
        for rel, path in _iter_kernel_files(base, kernel_dirs):
            seen.add(rel)
            expected = locked_files.get(rel)
            if expected is None:
                problems.append(f"{platform}: unlocked kernel file appeared: {rel}")
                continue
            actual = _sha256_file(path)
            if actual != expected:
                problems.append(f"{platform}: kernel drift: {rel}")
        for rel in sorted(set(locked_files) - seen):
            problems.append(f"{platform}: locked kernel file missing: {rel}")
    return problems


def _load_json_file(root: str, rel: str):
    path = os.path.join(root, rel)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_machine_probe_dataset(root: str, dataset=None) -> list:
    """Gate live platform-pack behavior against deterministic machine probes.

    HELIX does not vendor the nested `-stra` repos, so a plain HELIX checkout can
    lack the platform samples. When the repos are present, this becomes a hard gate:
    U6's probe agreement must stay at the locked threshold.
    """
    problems = []
    gate_path = os.path.join(root, MACHINE_PROBE_GATE)
    if not os.path.exists(gate_path):
        return [f"missing machine probe gate: {MACHINE_PROBE_GATE}"]
    try:
        gate = _load_json_file(root, MACHINE_PROBE_GATE)
    except ValueError as e:
        return [f"{MACHINE_PROBE_GATE}: invalid JSON: {e}"]

    required_platforms = gate.get("required_platforms", [])
    if not isinstance(required_platforms, list):
        return [f"{MACHINE_PROBE_GATE}: required_platforms must be a list"]
    missing_platforms = [p for p in required_platforms if not os.path.isdir(os.path.join(root, p))]
    if missing_platforms:
        return []

    if dataset is None:
        try:
            from scripts.condense.machine_probe_dataset import build_dataset
            dataset = build_dataset()
        except Exception as e:
            return [f"machine probe dataset failed: {e}"]

    criteria = gate.get("criteria", {})
    agreement = dataset.get("agreement", {})
    checks = [
        ("total_platform_packs", dataset.get("total_platform_packs")),
        ("implemented_probe_cases", dataset.get("implemented_probe_cases")),
        ("scored_claims", agreement.get("scored_claims")),
        ("matched_claims", agreement.get("matched_claims")),
    ]
    for key, actual in checks:
        expected = criteria.get(key)
        if expected is not None and actual != expected:
            problems.append(f"machine probe gate: {key} {actual!r} != {expected!r}")

    expected_agreement = criteria.get("agreement")
    actual_agreement = agreement.get("agreement")
    if expected_agreement is not None and actual_agreement != expected_agreement:
        problems.append(f"machine probe gate: agreement {actual_agreement!r} != {expected_agreement!r}")
    if criteria.get("allow_errors") is False and dataset.get("errors"):
        problems.append(f"machine probe gate: errors present: {dataset.get('errors')}")
    if criteria.get("allow_skipped_claims") is False and dataset.get("skipped_claims"):
        problems.append(f"machine probe gate: skipped claims present: {dataset.get('skipped_claims')}")
    return problems


def validate_probe_router(root: str, dataset=None, layered_corpus=None) -> list:
    """Gate the U8 probe router summary against the locked routed state."""
    gate_path = os.path.join(root, ROUTER_GATE)
    if not os.path.exists(gate_path):
        return [f"missing router gate: {ROUTER_GATE}"]
    try:
        gate = _load_json_file(root, ROUTER_GATE)
    except ValueError as e:
        return [f"{ROUTER_GATE}: invalid JSON: {e}"]

    required_platforms = gate.get("required_platforms", [])
    if not isinstance(required_platforms, list):
        return [f"{ROUTER_GATE}: required_platforms must be a list"]
    missing_platforms = [p for p in required_platforms if not os.path.isdir(os.path.join(root, p))]
    if missing_platforms:
        return []

    corpus_rel = gate.get("layered_corpus", os.path.join("seed", "condense", "layered-corpus.json"))
    if layered_corpus is None:
        try:
            layered_corpus = _load_json_file(root, corpus_rel)
        except (FileNotFoundError, ValueError) as e:
            return [f"router gate: cannot load {corpus_rel}: {e}"]

    if dataset is None:
        try:
            from scripts.condense.machine_probe_dataset import build_dataset
            dataset = build_dataset()
        except Exception as e:
            return [f"router gate dataset failed: {e}"]

    try:
        from core.helix_router import route_probe_rows
        routed = route_probe_rows(layered_corpus, dataset.get("agreement", {}).get("rows", []))
    except Exception as e:
        return [f"router gate failed: {e}"]

    problems = []
    criteria = gate.get("criteria", {})
    expected_summary = criteria.get("summary")
    if expected_summary is not None and routed.get("summary") != expected_summary:
        problems.append(f"router gate: summary {routed.get('summary')!r} != {expected_summary!r}")

    deferred = {}
    for decision in routed.get("decisions", []):
        if decision.get("action") == "DEFER":
            for machine in decision.get("uncovered_machines", []):
                deferred[machine] = deferred.get(machine, 0) + 1
    expected_deferred = criteria.get("deferred_machines")
    if expected_deferred is not None and deferred != expected_deferred:
        problems.append(f"router gate: deferred_machines {deferred!r} != {expected_deferred!r}")

    expected_decisions = criteria.get("decision_count")
    actual_decisions = len(routed.get("decisions", []))
    if expected_decisions is not None and actual_decisions != expected_decisions:
        problems.append(f"router gate: decision_count {actual_decisions!r} != {expected_decisions!r}")
    return problems


def validate_forward_predict_gate(root: str, dataset=None, layered_corpus=None) -> list:
    """Gate U9 forward-prediction fixtures against locked expected routes."""
    gate_path = os.path.join(root, FORWARD_PREDICT_GATE)
    if not os.path.exists(gate_path):
        return [f"missing forward-predict gate: {FORWARD_PREDICT_GATE}"]
    try:
        gate = _load_json_file(root, FORWARD_PREDICT_GATE)
    except ValueError as e:
        return [f"{FORWARD_PREDICT_GATE}: invalid JSON: {e}"]

    required_platforms = gate.get("required_platforms", [])
    if not isinstance(required_platforms, list):
        return [f"{FORWARD_PREDICT_GATE}: required_platforms must be a list"]
    missing_platforms = [p for p in required_platforms if not os.path.isdir(os.path.join(root, p))]
    if missing_platforms:
        return []

    corpus_rel = gate.get("layered_corpus", os.path.join("seed", "condense", "layered-corpus.json"))
    if layered_corpus is None:
        try:
            layered_corpus = _load_json_file(root, corpus_rel)
        except (FileNotFoundError, ValueError) as e:
            return [f"forward-predict gate: cannot load {corpus_rel}: {e}"]

    if dataset is None:
        try:
            from scripts.condense.machine_probe_dataset import build_dataset
            dataset = build_dataset()
        except Exception as e:
            return [f"forward-predict gate dataset failed: {e}"]
    pack_rows = dataset.get("agreement", {}).get("rows", [])

    try:
        from scripts.condense.forward_predict import predict_candidate
    except Exception as e:
        return [f"forward-predict gate import failed: {e}"]

    problems = []
    fixtures = gate.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        return [f"{FORWARD_PREDICT_GATE}: fixtures must be a non-empty list"]
    for fixture in fixtures:
        rel = fixture.get("candidate")
        if not rel:
            problems.append(f"{FORWARD_PREDICT_GATE}: fixture missing candidate")
            continue
        try:
            candidate = _load_json_file(root, rel)
            result = predict_candidate(candidate, layered_corpus, pack_rows=pack_rows)
        except Exception as e:
            problems.append(f"forward-predict gate: {rel} failed: {e}")
            continue
        prediction = result.get("prediction", {})
        expected_action = fixture.get("action")
        actual_action = prediction.get("action")
        if expected_action is not None and actual_action != expected_action:
            problems.append(f"forward-predict gate: {rel} action {actual_action!r} != {expected_action!r}")
        expected_platform = fixture.get("platform")
        actual_platform = prediction.get("platform")
        if expected_platform is not None and actual_platform != expected_platform:
            problems.append(f"forward-predict gate: {rel} platform {actual_platform!r} != {expected_platform!r}")
        if fixture.get("platform_absent") and actual_platform:
            problems.append(f"forward-predict gate: {rel} platform {actual_platform!r} should be absent")
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
        "core/helix_router.py",
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

    # U7 hard gate: deterministic/offline runtime boundary.
    problems += validate_determinism_boundary(root)

    # U7 hard gate: BUILD_ON_PLATFORM must not mutate existing platform kernels.
    problems += validate_zero_kernel_change(root)

    # U7 hard gate: live pack behavior must still satisfy machine probes.
    problems += validate_machine_probe_dataset(root)

    # U8 hard gate: probe-positive routing summary must stay stable.
    problems += validate_probe_router(root)

    # U9 hard gate: forward-prediction fixture routes must stay stable.
    problems += validate_forward_predict_gate(root)

    return problems


def _main(argv) -> int:
    root = argv[1] if len(argv) > 1 else "."
    print(f"=== HELIX validation (root: {os.path.abspath(root)}) ===")
    print(f"  - match keys: {', '.join(MATCH_KEYS)}")
    print(f"  - diversity thresholds: {DEFAULT_THRESHOLDS}")
    print(f"  - handback gate: ActionHandbackVerifier")
    print(f"  - determinism gate: {', '.join(DETERMINISM_SCAN_DIRS)}")
    print(f"  - zero-kernel gate: {ZERO_KERNEL_LOCK}")
    print(f"  - machine-probe gate: {MACHINE_PROBE_GATE}")
    print(f"  - router gate: {ROUTER_GATE}")
    print(f"  - forward-predict gate: {FORWARD_PREDICT_GATE}")
    problems = validate_project(root)
    if problems:
        print("\nFAIL - problems:")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("\nPASS - HELIX structure + example artifacts consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
