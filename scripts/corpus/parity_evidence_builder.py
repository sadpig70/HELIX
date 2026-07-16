#!/usr/bin/env python3
"""Build source-lock and machine-evidence artifacts for parity/provenance pilots."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import digest  # noqa: E402
from core.helix_schema import schema_path, validate_against_schema  # noqa: E402
from scripts.corpus.phase3_outcome import PROJECT_ROUTES  # noqa: E402
from scripts.corpus.phase3_registry import validate_registry  # noqa: E402


DEFAULT_PACKS = (
    "ProofEscrow",
    "AuthorityArbiter",
    "GraphQuarantine",
    "ContractRelay",
    "HookCircuit",
)


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _manifest_path(corpus_root, corpus_id):
    return os.path.join(corpus_root, "items", corpus_id, "manifest.json")


def _source_lock(manifest, now):
    origin = manifest.get("origin", {})
    return {
        "schema": "helix-parity-source-lock/1.0",
        "source_id": f"source:{manifest['corpus_id']}",
        "corpus_id": manifest["corpus_id"],
        "origin_kind": origin.get("kind", ""),
        "locator": origin.get("locator", ""),
        "revision": origin.get("revision", ""),
        "source_sha256": origin.get("source_sha256", ""),
        "license": origin.get("license", ""),
        "license_evidence_sha256": origin.get("license_evidence_sha256", ""),
        "captured_at": now,
        "restrictions": manifest.get("restrictions", []),
    }


def _machine_evidence(manifest):
    verification = manifest.get("verification", {})
    machine = manifest.get("machine", {})
    problems = []
    if machine.get("status") != "substantiated":
        problems.append("machine_status_not_substantiated")
    if not verification.get("reproducible"):
        problems.append("not_reproducible")
    if not verification.get("tests_passed"):
        problems.append("tests_not_passed")
    if not verification.get("deterministic"):
        problems.append("not_deterministic")
    if not verification.get("behavior_sha256"):
        problems.append("missing_behavior_sha256")
    return {
        "schema": "helix-parity-machine-evidence/1.0",
        "evidence_id": f"machine:{manifest['corpus_id']}",
        "source_lock_id": f"source:{manifest['corpus_id']}",
        "machine_label": machine.get("label", ""),
        "machine_status": machine.get("status", "hypothesis"),
        "reproduction_command": verification.get("reproduction_command", ""),
        "tests_passed": bool(verification.get("tests_passed")),
        "deterministic": bool(verification.get("deterministic")),
        "behavior_sha256": verification.get("behavior_sha256", ""),
        "supporting_files": verification.get("supporting_files", []),
        "problems": problems,
    }


def _selected_slots(registry, packs):
    wanted = set(packs)
    slots = [slot for slot in registry.get("slots", []) if slot.get("project_slug") in wanted]
    found = {slot.get("project_slug") for slot in slots}
    missing = sorted(wanted - found)
    if missing:
        raise ValueError(f"missing packs in registry: {missing}")
    return sorted(slots, key=lambda slot: slot.get("ordinal", 0))


def _validate_doc(repo_root, name, doc):
    return validate_against_schema(doc, schema_path(repo_root, name))


def build_bundle(repo_root, registry_path, corpus_root, out_dir, packs=DEFAULT_PACKS, now=None):
    if not now:
        raise ValueError("--now is required for deterministic evidence artifacts")
    registry = _load(registry_path)
    problems = validate_registry(repo_root, corpus_root, registry)
    if problems:
        return None, problems

    report = {
        "schema": "helix-parity-evidence-build-report/1.0",
        "policy_version": "HELIX-PARITY-PROVENANCE/1.0",
        "registry": os.path.relpath(registry_path, repo_root).replace(os.sep, "/"),
        "registry_sha256": digest(registry),
        "generated_at": now,
        "packs": [],
        "problems": [],
    }

    for slot in _selected_slots(registry, packs):
        pack = slot["project_slug"]
        target_platform = PROJECT_ROUTES.get(pack, "")
        pack_dir = os.path.join(out_dir, "representative", pack)
        pack_entry = {
            "pack": pack,
            "experiment_id": slot["experiment_id"],
            "target_platform": target_platform,
            "source_locks": [],
            "machine_evidence": [],
            "problems": [],
        }
        seen = set()
        for binding in slot.get("gene_bindings", []):
            corpus_id = binding["corpus_id"]
            if corpus_id in seen:
                continue
            seen.add(corpus_id)
            manifest_path = _manifest_path(corpus_root, corpus_id)
            if not os.path.exists(manifest_path):
                pack_entry["problems"].append(f"{corpus_id}: missing manifest")
                continue
            manifest = _load(manifest_path)
            manifest_sha = digest(manifest)
            if binding.get("manifest_sha256") != manifest_sha:
                pack_entry["problems"].append(f"{corpus_id}: stale manifest binding")
            if binding.get("gene") not in manifest.get("genes", []):
                pack_entry["problems"].append(f"{corpus_id}: missing gene {binding.get('gene')}")

            source_lock = _source_lock(manifest, now)
            machine_evidence = _machine_evidence(manifest)
            source_problems = _validate_doc(repo_root, "source-lock", source_lock)
            machine_problems = _validate_doc(repo_root, "machine-evidence", machine_evidence)
            for problem in source_problems:
                pack_entry["problems"].append(f"{corpus_id}: source-lock: {problem}")
            for problem in machine_problems:
                pack_entry["problems"].append(f"{corpus_id}: machine-evidence: {problem}")

            source_rel = os.path.join(
                "representative", pack, "source-locks", f"{corpus_id}.json")
            machine_rel = os.path.join(
                "representative", pack, "machine-evidence", f"{corpus_id}.json")
            _write(os.path.join(out_dir, source_rel), source_lock)
            _write(os.path.join(out_dir, machine_rel), machine_evidence)
            pack_entry["source_locks"].append(source_rel.replace(os.sep, "/"))
            pack_entry["machine_evidence"].append(machine_rel.replace(os.sep, "/"))
            pack_entry["problems"].extend(
                f"{corpus_id}: {problem}" for problem in machine_evidence["problems"])

        report["packs"].append(pack_entry)
        report["problems"].extend(
            f"{pack}: {problem}" for problem in pack_entry["problems"])

    _write(os.path.join(out_dir, "build-report.json"), report)
    return report, report["problems"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=os.path.join(
        ROOT, "seed", "corpus", "phase3-2026-01-experiments.json"))
    parser.add_argument("--corpus-root", default=os.path.join(ROOT, "seed", "corpus"))
    parser.add_argument("--out", default=os.path.join(ROOT, "seed", "parity-provenance"))
    parser.add_argument("--packs", default=",".join(DEFAULT_PACKS))
    parser.add_argument("--now", required=True)
    parser.add_argument("--strict", action="store_true",
                        help="Return non-zero when generated machine evidence has problems.")
    args = parser.parse_args(argv)
    packs = tuple(part.strip() for part in args.packs.split(",") if part.strip())
    report, problems = build_bundle(
        ROOT,
        os.path.abspath(args.registry),
        os.path.abspath(args.corpus_root),
        os.path.abspath(args.out),
        packs=packs,
        now=args.now,
    )
    print(json.dumps(report or {"valid": False, "problems": problems}, ensure_ascii=False, indent=2, sort_keys=True))
    if report is None:
        return 4
    return 4 if args.strict and problems else 0


if __name__ == "__main__":
    sys.exit(main())
