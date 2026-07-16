#!/usr/bin/env python3
"""Run a bounded parity/provenance promotion batch with validation after each step."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.corpus.parity_expansion_inventory import build_inventory, validate_inventory  # noqa: E402
from scripts.corpus.parity_coverage_dashboard import build_dashboard  # noqa: E402
from scripts.corpus.parity_pending_promotion import build_promotion, select_next_pending  # noqa: E402


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _dashboard_candidates(path, limit):
    dashboard = _load(path)
    if dashboard.get("schema") != "helix-parity-coverage-dashboard/1.0":
        raise ValueError(f"{path}: schema mismatch")
    candidates = dashboard.get("next_candidates", [])[:limit]
    if len(candidates) < limit:
        raise ValueError(f"{path}: requested {limit} candidates, got {len(candidates)}")
    return [(item["platform"], item["pack"]) for item in candidates]


def _is_pending(inventory, platform, pack):
    return any(
        entry.get("platform") == platform and entry.get("pack") == pack and entry.get("status") == "PENDING"
        for entry in inventory.get("entries", [])
    )


def run_batch(evidence_root, limit, now, dashboard_path=None, refresh_dashboard=False):
    if limit < 1:
        raise ValueError("--limit must be >= 1")
    if not now:
        raise ValueError("--now is required for deterministic batch promotion")
    promotions = []
    problems = []
    inventory_path = os.path.join(evidence_root, "expansion-inventory.json")
    dashboard_candidates = _dashboard_candidates(dashboard_path, limit) if dashboard_path else []
    for index in range(limit):
        if dashboard_candidates:
            platform, pack = dashboard_candidates[index]
            inventory = build_inventory(ROOT, evidence_root, now)
            inventory_problems = validate_inventory(inventory)
            if inventory_problems:
                problems.extend(f"{platform}/{pack}: inventory: {problem}" for problem in inventory_problems)
                break
            if not _is_pending(inventory, platform, pack):
                problems.append(f"{platform}/{pack}: dashboard candidate is not currently PENDING")
                break
        else:
            try:
                platform, pack = select_next_pending(evidence_root)
            except ValueError as exc:
                problems.append(str(exc))
                break
        report, promotion_problems = build_promotion(platform, pack, evidence_root, now)
        if promotion_problems:
            problems.extend(f"{platform}/{pack}: {problem}" for problem in promotion_problems)
            break
        inventory = build_inventory(ROOT, evidence_root, now)
        inventory_problems = validate_inventory(inventory)
        if inventory_problems:
            problems.extend(f"{platform}/{pack}: inventory: {problem}" for problem in inventory_problems)
            break
        _write(inventory_path, inventory)
        promotions.append({
            "ordinal": index + 1,
            "platform": platform,
            "pack": pack,
            "promotion_report": report["parity_receipt"],
            "machines": report["machines"],
            "probe_case_count": report["probe_case_count"],
            "inventory_counts": inventory["counts"],
        })
    batch_report = {
        "schema": "helix-parity-promotion-batch-report/1.0",
        "generated_at": now,
        "requested_limit": limit,
        "selection_source": "coverage-dashboard" if dashboard_path else "expansion-inventory",
        "dashboard": os.path.relpath(dashboard_path, ROOT).replace(os.sep, "/") if dashboard_path else None,
        "completed": len(promotions),
        "promotions": promotions,
        "problems": problems,
    }
    _write(os.path.join(evidence_root, "promotion-batch-report.json"), batch_report)
    if refresh_dashboard:
        dashboard = build_dashboard(evidence_root, now)
        _write(os.path.join(evidence_root, "coverage-dashboard.json"), dashboard)
    return batch_report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", default=os.path.join(ROOT, "seed", "parity-provenance"))
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--now", required=True)
    parser.add_argument("--dashboard", help="Use next_candidates from a coverage dashboard as the batch source.")
    parser.add_argument("--refresh-dashboard", action="store_true",
                        help="Refresh coverage-dashboard.json after the batch completes.")
    args = parser.parse_args(argv)
    report, problems = run_batch(
        os.path.abspath(args.evidence_root),
        args.limit,
        args.now,
        dashboard_path=os.path.abspath(args.dashboard) if args.dashboard else None,
        refresh_dashboard=args.refresh_dashboard,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not problems else 4


if __name__ == "__main__":
    sys.exit(main())
