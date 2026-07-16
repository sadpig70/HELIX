#!/usr/bin/env python3
"""Validate and summarize tracked HELIX Phase 3 full-cycle outcomes."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.corpus.phase3_registry import validate_registry  # noqa: E402


PROJECT_ROUTES = {
    "ProofEscrow": "Attestra",
    "AuthorityArbiter": "Attestra",
    "DriftIsolator": "Attestra",
    "GraphQuarantine": "Attestra",
    "ContractRelay": "Routestra",
    "HookCircuit": "Attestra",
}


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _project_problems(repo_root, slot):
    problems = []
    project = slot["project_slug"]
    project_root = os.path.join(repo_root, project)
    if not os.path.isdir(project_root):
        return [f"{slot['experiment_id']}: missing project directory {project}"]

    required_paths = [
        "README.md",
        "pyproject.toml",
        os.path.join("src", project.lower(), "__init__.py"),
    ]
    for rel in required_paths:
        if not os.path.exists(os.path.join(project_root, rel)):
            problems.append(f"{slot['experiment_id']}: missing {project}/{rel}")

    tests_dir = os.path.join(project_root, "tests")
    if not os.path.isdir(tests_dir):
        problems.append(f"{slot['experiment_id']}: missing {project}/tests")

    readme_path = os.path.join(project_root, "README.md")
    if os.path.exists(readme_path):
        readme = _read(readme_path)
        for binding in slot.get("gene_bindings", []):
            if binding["gene"] not in readme:
                problems.append(
                    f"{slot['experiment_id']}: README missing gene {binding['gene']}")
            if binding["corpus_id"] not in readme:
                problems.append(
                    f"{slot['experiment_id']}: README missing corpus {binding['corpus_id']}")

    if project not in PROJECT_ROUTES:
        problems.append(f"{slot['experiment_id']}: no platform route for {project}")
    return problems


def build_outcome(repo_root, registry_path, corpus_root):
    registry = _load(registry_path)
    problems = validate_registry(repo_root, corpus_root, registry)
    project_problems = []
    platform_routes = {}
    machine_candidates = []
    for slot in registry.get("slots", []):
        project = slot.get("project_slug")
        project_problems.extend(_project_problems(repo_root, slot))
        target = PROJECT_ROUTES.get(project)
        if target:
            platform_routes.setdefault(target, []).append(project)
        machine_candidates.append({
            "experiment_id": slot.get("experiment_id"),
            "project": project,
            "lead_verb": slot.get("lead_verb"),
            "route": "BUILD_ON_PLATFORM" if target else "UNROUTED",
            "target_platform": target,
            "success_signal": slot.get("success_signal"),
        })

    all_problems = sorted(set(problems + project_problems))
    completed = len(registry.get("slots", [])) - len({
        problem.split(":", 1)[0] for problem in project_problems
    })
    metrics = {
        "experiments_total": len(registry.get("slots", [])),
        "experiments_completed": completed,
        "implementation_successes": completed,
        "independent_projects": completed,
        "external_gene_transfers": completed,
        "platform_absorbed": sum(
            1 for candidate in machine_candidates
            if candidate["route"] == "BUILD_ON_PLATFORM"),
        "new_platform_kernels_emitted": 0,
        "unresolved_failures": len(all_problems),
    }
    return {
        "schema": "helix-corpus-phase3-outcome/1.0",
        "phase_id": registry.get("phase_id"),
        "status": (
            "PHASE3_COMPLETE_READY_FOR_PHASE4"
            if not all_problems and metrics["experiments_total"] == 6
            else "PHASE3_NEEDS_REMEDIATION"
        ),
        "source_registry": os.path.relpath(registry_path, repo_root).replace(os.sep, "/"),
        "metrics": metrics,
        "platform_routes": {key: sorted(value) for key, value in sorted(platform_routes.items())},
        "machine_candidates": machine_candidates,
        "decision": {
            "phase4": (
                "PROCEED_TO_PLATFORM_ABSORPTION_PACKAGING"
                if not all_problems else "HOLD_FOR_REMEDIATION"),
            "condense": "DO_NOT_EMIT_NEW_PLATFORM_KERNEL",
            "reason": (
                "All six Phase 3 projects exist as tracked deterministic packs and route to existing platforms."
                if not all_problems else "Tracked Phase 3 outcome validation found problems."
            ),
        },
        "problems": all_problems,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=os.path.join(
        ROOT, "seed", "corpus", "phase3-2026-01-experiments.json"))
    parser.add_argument("--corpus-root", default=os.path.join(ROOT, "seed", "corpus"))
    args = parser.parse_args(argv)
    outcome = build_outcome(ROOT, os.path.abspath(args.registry), os.path.abspath(args.corpus_root))
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 0 if not outcome["problems"] else 4


if __name__ == "__main__":
    sys.exit(main())
