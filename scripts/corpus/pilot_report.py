#!/usr/bin/env python3
"""Aggregate a fixed-slot corpus pilot into deterministic JSON/Markdown."""

import argparse
import collections
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import (  # noqa: E402
    hard_gate,
    manifest_digest,
    materialize_state,
    read_json,
    validate_manifest,
)
from scripts.corpus.pilot_registry import validate_registry  # noqa: E402


DIVERSITY_FIELDS = (
    "source_class", "domain", "primary_verb", "input_shape", "output_shape",
    "machine", "genes", "dependencies",
)


def _distribution(values):
    counts = collections.Counter(values)
    total = sum(counts.values())
    probabilities = [count / total for count in counts.values()] if total else []
    entropy = -sum(value * math.log2(value) for value in probabilities)
    normalized = entropy / math.log2(len(counts)) if len(counts) > 1 else 0.0
    return {
        "total": total,
        "unique": len(counts),
        "top_share": round(max(counts.values()) / total, 4) if total else None,
        "normalized_entropy": round(normalized, 4),
        "counts": dict(sorted(counts.items())),
    }


def _manifest_path(corpus_root, corpus_id):
    return os.path.join(corpus_root, "items", corpus_id, "manifest.json")


def _resolve(repo_root, path):
    if not path:
        return None
    return path if os.path.isabs(path) else os.path.join(repo_root, path)


def build_report(repo_root, registry, corpus_root):
    registry_problems = validate_registry(repo_root, registry)
    materialized = materialize_state(repo_root, corpus_root)
    entries = []
    diversity = {field: [] for field in DIVERSITY_FIELDS}
    provenance_bound = 0
    structured = 0
    reason_counts = collections.Counter()
    reasons_recorded = True
    for event in materialized["events"]:
        if event.get("decision") == "QUARANTINED":
            reasons = event.get("reasons", [])
            reasons_recorded = reasons_recorded and bool(reasons)
            reason_counts.update(reasons)

    for slot in registry.get("slots", []):
        corpus_id = slot.get("corpus_id")
        manifest = read_json(_manifest_path(corpus_root, corpus_id))
        events = materialized["state"].get(corpus_id, {})
        structure_problems = [] if manifest is None else validate_manifest(repo_root, manifest)
        evidence_problems = ["manifest_missing"]
        if manifest is not None:
            structured += not structure_problems
            candidate = slot.get("candidate") or {}
            evidence_root = _resolve(repo_root, candidate.get("evidence_root"))
            evidence_problems = hard_gate(manifest, evidence_root)
            provenance_bound += not evidence_problems
            character = manifest.get("character", {})
            diversity["source_class"].append(slot.get("source_class", "unknown"))
            diversity["domain"].append(character.get("domain", "unknown"))
            diversity["primary_verb"].append(character.get("primary_verb", "unknown"))
            diversity["input_shape"].append(character.get("input_shape", "unknown"))
            diversity["output_shape"].append(character.get("output_shape", "unknown"))
            diversity["machine"].append(manifest.get("machine", {}).get("label", "unknown"))
            diversity["genes"].extend(manifest.get("genes", []))
            diversity["dependencies"].extend(manifest.get("dependencies", []))
        decisions = {}
        for tier in ("generative", "evidence"):
            event = events.get(tier)
            decisions[tier] = event.get("decision", "NOT_REVIEWED") if event else "NOT_REVIEWED"
        entries.append({
            "corpus_id": corpus_id,
            "source_class": slot.get("source_class"),
            "registry_status": slot.get("status"),
            "manifest_sha256": manifest_digest(manifest) if manifest else None,
            "structure_problems": structure_problems,
            "evidence_problems": evidence_problems,
            **decisions,
        })

    generative_count = sum(item["generative"] == "ADMITTED" for item in entries)
    evidence_count = sum(item["evidence"] == "ADMITTED" for item in entries)
    quarantined = sum(
        item["generative"] == "QUARANTINED" or item["evidence"] == "QUARANTINED"
        for item in entries)
    targets = registry.get("targets", {})
    gates = {
        "registry_frozen_valid": not registry_problems,
        "candidate_count_24": len(entries) == targets.get("candidate_count", 24),
        "structured_manifests_24": structured == 24,
        "provenance_bound_24": provenance_bound == 24,
        "generative_min": generative_count >= targets.get("generative_min", 12),
        "evidence_min": evidence_count >= targets.get("evidence_min", 5),
        "decision_reasons_recorded": reasons_recorded,
        "ledger_valid": not materialized["ledger_problems"],
        "diversity_baseline_24": len(diversity["source_class"]) == 24,
    }
    if not gates["ledger_valid"]:
        verdict = "PILOT_FAILED"
    elif all(gates.values()):
        verdict = "READY_FOR_PHASE_3"
    elif structured == 24 and generative_count >= targets.get("generative_min", 12):
        verdict = "READY_WITH_REMEDIATION"
    else:
        verdict = "IN_PROGRESS"
    return {
        "schema": "helix-corpus-pilot-report/1.0",
        "pilot_id": registry.get("pilot_id"),
        "verdict": verdict,
        "counts": {
            "slots": len(entries),
            "structured_manifests": structured,
            "provenance_bound": provenance_bound,
            "generative_admitted": generative_count,
            "evidence_admitted": evidence_count,
            "quarantined": quarantined,
            "decision_events": len(materialized["events"]),
            "duplicate_reasons": sum(
                count for reason, count in reason_counts.items()
                if reason.startswith("duplicate_source:")),
        },
        "gates": gates,
        "registry_problems": registry_problems,
        "ledger_problems": materialized["ledger_problems"],
        "decision_reason_counts": dict(sorted(reason_counts.items())),
        "diversity": {field: _distribution(values)
                      for field, values in diversity.items()},
        "items": entries,
    }


def markdown(report):
    counts = report["counts"]
    lines = [
        f"# {report['pilot_id']} Report",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Structured manifests: {counts['structured_manifests']}/24",
        f"- Provenance bound: {counts['provenance_bound']}/24",
        f"- Generative admitted: {counts['generative_admitted']}/12 minimum",
        f"- Evidence admitted: {counts['evidence_admitted']}/5 minimum",
        f"- Quarantined: {counts['quarantined']}",
        f"- Duplicate reasons: {counts['duplicate_reasons']}",
        "",
        "## Gates",
        "",
    ]
    for name, passed in report["gates"].items():
        lines.append(f"- [{'x' if passed else ' '}] `{name}`")
    lines += ["", "## Decision reasons", ""]
    if report["decision_reason_counts"]:
        for reason, count in report["decision_reason_counts"].items():
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- None")
    lines += ["", "## Diversity baseline", ""]
    for field, values in report["diversity"].items():
        lines.append(
            f"- `{field}`: unique={values['unique']}, "
            f"top_share={values['top_share']}, entropy={values['normalized_entropy']}")
    lines += ["", "## Items", "",
              "| ID | Class | Generative | Evidence | Evidence problems |",
              "|---|---|---|---|---|"]
    for item in report["items"]:
        problems = ", ".join(item["evidence_problems"]) or "-"
        lines.append(
            f"| {item['corpus_id']} | {item['source_class']} | "
            f"{item['generative']} | {item['evidence']} | {problems} |")
    return "\n".join(lines) + "\n"


def _write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--corpus-root", default=os.path.join(ROOT, "seed", "corpus"))
    parser.add_argument("--out")
    parser.add_argument("--markdown")
    args = parser.parse_args(argv)
    with open(args.registry, "r", encoding="utf-8") as handle:
        registry = json.load(handle)
    report = build_report(ROOT, registry, os.path.abspath(args.corpus_root))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        _write(args.out, text)
    if args.markdown:
        _write(args.markdown, markdown(report))
    if not args.out:
        print(text, end="")
    return 4 if report["verdict"] == "PILOT_FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
