#!/usr/bin/env python3
"""Build and validate the parity/provenance coverage dashboard."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.corpus.parity_expansion_inventory import validate_inventory  # noqa: E402


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _status_count(counts, status):
    return counts.get("by_status", {}).get(status, 0)


def _platform_rows(inventory):
    entries = inventory.get("entries", [])
    rows = []
    for platform, counts in sorted(inventory.get("counts", {}).get("by_platform", {}).items()):
        total = sum(counts.values())
        valid = counts.get("VALID", 0)
        blocked = counts.get("BLOCKED", 0)
        pending = counts.get("PENDING", 0)
        platform_entries = [entry for entry in entries if entry.get("platform") == platform]
        rows.append({
            "platform": platform,
            "total": total,
            "valid": valid,
            "blocked": blocked,
            "pending": pending,
            "coverage_percent": _pct(valid, total),
            "blocked_packs": sorted(
                entry["pack"] for entry in platform_entries if entry.get("status") == "BLOCKED"),
            "next_pending": _next_pending(platform_entries),
        })
    return rows


def _next_pending(entries):
    pending = [entry for entry in entries if entry.get("status") == "PENDING"]
    if not pending:
        return None
    pending.sort(key=lambda entry: (
        -len(entry.get("probe_cases", [])),
        entry.get("platform", ""),
        entry.get("pack", ""),
    ))
    winner = pending[0]
    return {
        "pack": winner["pack"],
        "probe_case_count": len(winner.get("probe_cases", [])),
        "machines": winner.get("machines", []),
    }


def _next_candidates(inventory, limit):
    pending = [entry for entry in inventory.get("entries", []) if entry.get("status") == "PENDING"]
    pending.sort(key=lambda entry: (
        -len(entry.get("probe_cases", [])),
        entry.get("platform", ""),
        entry.get("pack", ""),
    ))
    return [{
        "platform": entry["platform"],
        "pack": entry["pack"],
        "probe_case_count": len(entry.get("probe_cases", [])),
        "machines": entry.get("machines", []),
    } for entry in pending[:limit]]


def build_dashboard(evidence_root, now, candidate_limit=10):
    if not now:
        raise ValueError("--now is required for deterministic dashboard")
    inventory_path = os.path.join(evidence_root, "expansion-inventory.json")
    pilot_path = os.path.join(evidence_root, "representative-pilot-report.json")
    batch_path = os.path.join(evidence_root, "promotion-batch-report.json")
    inventory = _load(inventory_path)
    pilot = _load(pilot_path)
    batch = _load(batch_path) if os.path.exists(batch_path) else None

    counts = inventory.get("counts", {})
    total = counts.get("packs", 0)
    valid = _status_count(counts, "VALID")
    blocked = _status_count(counts, "BLOCKED")
    pending = _status_count(counts, "PENDING")

    dashboard = {
        "schema": "helix-parity-coverage-dashboard/1.0",
        "generated_at": now,
        "source": {
            "expansion_inventory": "seed/parity-provenance/expansion-inventory.json",
            "representative_pilot_report": "seed/parity-provenance/representative-pilot-report.json",
            "promotion_batch_report": (
                "seed/parity-provenance/promotion-batch-report.json" if batch else None),
        },
        "summary": {
            "packs": total,
            "valid": valid,
            "blocked": blocked,
            "pending": pending,
            "coverage_percent": _pct(valid, total),
            "blocked_percent": _pct(blocked, total),
            "pending_percent": _pct(pending, total),
        },
        "representative": {
            "counts": pilot.get("counts", {}),
            "problems": pilot.get("problems", []),
        },
        "latest_batch": {
            "completed": batch.get("completed", 0) if batch else 0,
            "requested_limit": batch.get("requested_limit") if batch else None,
            "problems": batch.get("problems", []) if batch else [],
            "promotions": [{
                "ordinal": item.get("ordinal"),
                "platform": item.get("platform"),
                "pack": item.get("pack"),
                "probe_case_count": item.get("probe_case_count"),
            } for item in batch.get("promotions", [])] if batch else [],
        },
        "platforms": _platform_rows(inventory),
        "blocked": [{
            "platform": entry["platform"],
            "pack": entry["pack"],
            "reason": entry.get("reason"),
            "evidence": entry.get("evidence", {}),
        } for entry in inventory.get("entries", []) if entry.get("status") == "BLOCKED"],
        "next_candidates": _next_candidates(inventory, candidate_limit),
        "problems": [],
    }
    dashboard["problems"] = validate_dashboard(dashboard, inventory)
    return dashboard


def validate_dashboard(dashboard, inventory=None):
    problems = []
    if dashboard.get("schema") != "helix-parity-coverage-dashboard/1.0":
        problems.append("schema mismatch")
    summary = dashboard.get("summary", {})
    total = summary.get("packs")
    if total != summary.get("valid", 0) + summary.get("blocked", 0) + summary.get("pending", 0):
        problems.append("summary status counts do not add up")
    if inventory is not None:
        inventory_problems = validate_inventory(inventory)
        problems.extend(f"inventory: {problem}" for problem in inventory_problems)
        counts = inventory.get("counts", {})
        expected = {
            "packs": counts.get("packs"),
            "valid": _status_count(counts, "VALID"),
            "blocked": _status_count(counts, "BLOCKED"),
            "pending": _status_count(counts, "PENDING"),
        }
        actual = {key: summary.get(key) for key in expected}
        if actual != expected:
            problems.append(f"summary mismatch expected {expected}, got {actual}")
    platform_total = sum(row.get("total", 0) for row in dashboard.get("platforms", []))
    if platform_total != total:
        problems.append(f"platform total mismatch expected {total}, got {platform_total}")
    candidate_keys = [
        (entry.get("platform"), entry.get("pack")) for entry in dashboard.get("next_candidates", [])]
    if len(candidate_keys) != len(set(candidate_keys)):
        problems.append("duplicate next candidates")
    if dashboard.get("latest_batch", {}).get("problems"):
        problems.append("latest batch has unresolved problems")
    return sorted(set(problems + dashboard.get("problems", [])))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", default=os.path.join(ROOT, "seed", "parity-provenance"))
    parser.add_argument("--out", default=os.path.join(ROOT, "seed", "parity-provenance", "coverage-dashboard.json"))
    parser.add_argument("--now", required=True)
    parser.add_argument("--candidate-limit", type=int, default=10)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    evidence_root = os.path.abspath(args.evidence_root)
    inventory = _load(os.path.join(evidence_root, "expansion-inventory.json"))
    if args.validate:
        dashboard = _load(args.out)
    else:
        dashboard = build_dashboard(evidence_root, args.now, args.candidate_limit)
        _write(args.out, dashboard)
    problems = validate_dashboard(dashboard, inventory)
    result = {
        "valid": not problems,
        "problems": problems,
        "summary": dashboard.get("summary", {}),
        "next_candidates": dashboard.get("next_candidates", [])[:3],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not problems else 4


if __name__ == "__main__":
    sys.exit(main())
