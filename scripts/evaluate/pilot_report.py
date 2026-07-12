#!/usr/bin/env python3
"""Aggregate multi-participant wedge pilot ledgers into one T4 report.

Reads a pilot config JSON and prints (or writes) the sealed pilot report from
core/helix_wedge_metrics.aggregate_pilot. Config shape:

    {
      "participants": {"team-a": ".helix/wedge/team-a.jsonl", ...},
      "period": {"weeks": 8, "label": "pilot 2026-Qx"},
      "sidecar": {                       # real-world signals (outside ledger)
        "false_admits": {"team-a": 0},   # admitted handbacks later found bad
        "retained": ["team-a", "team-b"],
        "manual_review_baseline_minutes": {"team-a": 600},
        "wedge_review_minutes": {"team-a": 120}
      }
    }

CLI:
    python scripts/evaluate/pilot_report.py --config pilot.json [--out report.json]
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_wedge_metrics import aggregate_pilot  # noqa: E402


def _main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--out")
    args = parser.parse_args(argv[1:])

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    report = aggregate_pilot(os.path.abspath(args.root),
                             config["participants"],
                             period=config.get("period"),
                             sidecar=config.get("sidecar"))
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")

    gate = report["t4_gate"]
    print(f"=== HELIX wedge pilot report ===")
    print(f"  participants: {report['participants']} "
          f"{report['participant_ids']}")
    print(f"  decisions:    {report['combined']['decisions_total']}"
          f" (admitted {report['combined']['admitted']},"
          f" prevented {report['combined']['prevented_invalid_handbacks']})")
    ns = report["north_star"]["value"]
    print(f"  north star:   weekly_real_admission_decisions ="
          f" {ns if ns is not None else 'n/a (no period)'}")
    for key in ("throughput", "false_admit", "replay", "adoption"):
        c = gate[key]
        verdict = {True: "PASS", False: "FAIL", None: "unmeasured"}[c["pass"]]
        print(f"  T4 {key}: {verdict} (target {c['target']})")
    print(f"\n  T4 VERDICT: {gate['verdict'].upper()}")
    if report["problems"]:
        print("  problems:")
        for p in report["problems"]:
            print(f"    * {p}")
    return 0 if gate["verdict"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
