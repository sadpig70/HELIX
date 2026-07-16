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
from scripts.corpus.parity_pending_promotion import build_promotion, select_next_pending  # noqa: E402


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def run_batch(evidence_root, limit, now):
    if limit < 1:
        raise ValueError("--limit must be >= 1")
    if not now:
        raise ValueError("--now is required for deterministic batch promotion")
    promotions = []
    problems = []
    inventory_path = os.path.join(evidence_root, "expansion-inventory.json")
    for index in range(limit):
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
        "completed": len(promotions),
        "promotions": promotions,
        "problems": problems,
    }
    _write(os.path.join(evidence_root, "promotion-batch-report.json"), batch_report)
    return batch_report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", default=os.path.join(ROOT, "seed", "parity-provenance"))
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--now", required=True)
    args = parser.parse_args(argv)
    report, problems = run_batch(os.path.abspath(args.evidence_root), args.limit, args.now)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not problems else 4


if __name__ == "__main__":
    sys.exit(main())
