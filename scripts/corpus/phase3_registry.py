#!/usr/bin/env python3
"""Validate and freeze the HELIX Phase 3 six-full-cycle registry."""

import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import digest, read_ledger, verify_ledger  # noqa: E402
from core.helix_schema import schema_path, validate_against_schema  # noqa: E402


SCHEMA = "helix-corpus-phase3-registry/1.0"
FREEZE_SCHEMA = "helix-corpus-phase3-freeze-receipt/1.0"
EXPECTED_IDS = [f"HC-P3-FC-{index:03d}" for index in range(1, 7)]
PIPELINE = ["explore", "full_cycle", "implement", "handback", "close_loop", "feedback"]
REQUIRED_OUTPUTS = ["implementation_report", "handback_packet", "close_loop_receipt", "experiment_result"]


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _tokens(values):
    tokens = set()
    for value in values:
        tokens.update(part for part in str(value).lower().replace("-", "_").split("_") if part)
    return tokens


def domain_distance(left, right):
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    union = left_tokens | right_tokens
    return 1.0 if not union else 1.0 - (len(left_tokens & right_tokens) / len(union))


def _ledger_admissions(corpus_root):
    ledger_path = os.path.join(corpus_root, "evidence", "admission-ledger.jsonl")
    admissions = set()
    if os.path.exists(ledger_path):
        for event in read_ledger(ledger_path):
            if event.get("decision") == "ADMITTED":
                admissions.add((event.get("corpus_id"), event.get("tier"), event.get("manifest_sha256")))
    return ledger_path, admissions


def _manifest(corpus_root, corpus_id):
    path = os.path.join(corpus_root, "items", corpus_id, "manifest.json")
    return _load(path) if os.path.exists(path) else None


def validate_registry(repo_root, corpus_root, registry):
    problems = validate_against_schema(registry, schema_path(repo_root, "corpus-phase3-registry"))
    if problems:
        return sorted(set(problems))
    if registry.get("frozen") is not True:
        problems.append("registry must be frozen before Phase 3 execution")

    policy = registry.get("policy", {})
    for flag in ("unique_lead_verbs", "require_handback", "require_close_loop", "require_feedback", "record_failures"):
        if policy.get(flag) is not True:
            problems.append(f"policy.{flag} must be true")

    slots = registry.get("slots", [])
    ids = [slot.get("experiment_id") for slot in slots]
    if ids != EXPECTED_IDS:
        problems.append(f"experiment IDs/order must be {EXPECTED_IDS}, got {ids}")
    if len(slots) != policy.get("experiment_count"):
        problems.append("slot count must equal policy.experiment_count")

    verbs = [slot.get("lead_verb") for slot in slots]
    slugs = [slot.get("project_slug") for slot in slots]
    if len(verbs) != len(set(verbs)):
        problems.append("lead verbs must be unique")
    if len(slugs) != len(set(slugs)):
        problems.append("project slugs must be unique")

    ledger_path, admissions = _ledger_admissions(corpus_root)
    problems.extend(f"ledger: {problem}" for problem in verify_ledger(repo_root, ledger_path))
    minimum_external = policy.get("minimum_external_genes_per_experiment", 1)
    minimum_distance = policy.get("minimum_domain_distance", 0)
    recent_domains = registry.get("recent_project_domains", [])

    for slot in slots:
        experiment_id = slot.get("experiment_id")
        if slot.get("pipeline") != PIPELINE:
            problems.append(f"{experiment_id}: pipeline order must be {PIPELINE}")
        if slot.get("required_outputs") != REQUIRED_OUTPUTS:
            problems.append(f"{experiment_id}: required outputs must be {REQUIRED_OUTPUTS}")
        if slot.get("failure_route") != "failure_corpus":
            problems.append(f"{experiment_id}: failure route must be failure_corpus")

        baseline = slot.get("evidence_baseline", {})
        baseline_key = (baseline.get("corpus_id"), "evidence", baseline.get("manifest_sha256"))
        if baseline_key not in admissions:
            problems.append(f"{experiment_id}: evidence baseline is not Evidence-admitted")

        external_count = 0
        for binding in slot.get("gene_bindings", []):
            corpus_id = binding.get("corpus_id")
            manifest = _manifest(corpus_root, corpus_id)
            if manifest is None:
                problems.append(f"{experiment_id}: missing manifest {corpus_id}")
                continue
            manifest_sha = digest(manifest)
            if binding.get("manifest_sha256") != manifest_sha:
                problems.append(f"{experiment_id}: stale manifest binding for {corpus_id}")
            if binding.get("gene") not in manifest.get("genes", []):
                problems.append(f"{experiment_id}: unknown gene {binding.get('gene')} in {corpus_id}")
            if not any((corpus_id, tier, manifest_sha) in admissions for tier in ("generative", "evidence")):
                problems.append(f"{experiment_id}: gene source {corpus_id} is not admitted")
            if manifest.get("origin", {}).get("kind") == "external_repo":
                external_count += 1
        if external_count < minimum_external:
            problems.append(f"{experiment_id}: external gene count {external_count} < {minimum_external}")

        for recent in recent_domains:
            distance = domain_distance(slot.get("domain_signature", []), [recent])
            if distance < minimum_distance:
                problems.append(f"{experiment_id}: recent-domain distance {distance:.4f} < {minimum_distance:.4f} ({recent})")

    for index, left in enumerate(slots):
        for right in slots[index + 1:]:
            distance = domain_distance(left.get("domain_signature", []), right.get("domain_signature", []))
            if distance < minimum_distance:
                problems.append(f"{left.get('experiment_id')}/{right.get('experiment_id')}: pairwise domain distance {distance:.4f} < {minimum_distance:.4f}")
    return sorted(set(problems))


def freeze_registry(registry_path, corpus_root, pilot_report_path, out, now):
    registry = _load(registry_path)
    problems = validate_registry(ROOT, corpus_root, registry)
    if problems:
        return None, problems
    report_sha = _sha256_file(pilot_report_path)
    source = registry["source_pilot"]
    if source.get("report_sha256") != report_sha:
        return None, ["source pilot report hash mismatch"]
    report = _load(pilot_report_path)
    if report.get("verdict") != "READY_FOR_PHASE_3":
        return None, ["source pilot is not READY_FOR_PHASE_3"]
    receipt = {
        "schema": FREEZE_SCHEMA,
        "phase_id": registry["phase_id"],
        "registry": os.path.relpath(registry_path, ROOT).replace(os.sep, "/"),
        "registry_sha256": digest(registry),
        "source_pilot_report_sha256": report_sha,
        "frozen_at": now,
        "experiment_count": len(registry["slots"]),
        "verdict": "FROZEN_READY_TO_EXECUTE",
    }
    if os.path.exists(out):
        return None, [f"refusing to overwrite freeze receipt: {out}"]
    _write(out, receipt)
    return receipt, []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--registry", required=True)
    validate.add_argument("--corpus-root", default="seed/corpus")
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--registry", required=True)
    freeze.add_argument("--corpus-root", default="seed/corpus")
    freeze.add_argument("--pilot-report", required=True)
    freeze.add_argument("--out", required=True)
    freeze.add_argument("--now", required=True)
    args = parser.parse_args(argv)
    registry = _load(args.registry)
    if args.command == "validate":
        problems = validate_registry(ROOT, args.corpus_root, registry)
        print(json.dumps({"valid": not problems, "problems": problems}, ensure_ascii=False, indent=2))
        return 0 if not problems else 4
    receipt, problems = freeze_registry(args.registry, args.corpus_root, args.pilot_report, args.out, args.now)
    print(json.dumps(receipt or {"valid": False, "problems": problems}, ensure_ascii=False, indent=2))
    return 0 if receipt else 4


if __name__ == "__main__":
    sys.exit(main())
