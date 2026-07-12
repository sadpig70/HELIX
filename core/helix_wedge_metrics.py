#!/usr/bin/env python3
"""Operational metrics for the wedge, recomputed from the ledger (T4, P5_3).

Policy source of truth: process plan §P5 North Star and metrics —
``weekly_real_admission_decisions``, ``prevented_invalid_handbacks``,
``replay_success``, ``operator_intervention_rate``. Every number is
DERIVED from sealed evidence, never kept as a separate mutable counter:

- decisions and their admission/verdict distributions come from the
  ledger's ``wedge_decision`` entries;
- prevented_invalid_handbacks = EXCLUDED + QUARANTINE decisions (invalid
  handbacks blocked without manual review — the wedge's core value);
- replay_success re-runs ``verify_wedge_decision`` on every decision, so a
  laundered receipt drags the rate below 100% instead of hiding;
- interventions are sealed appeal/override receipts chained to gate results
  that actually appear in this ledger — unverifiable receipts are reported,
  never counted;
- a corrupt ledger yields ``metrics_valid=false``: no metrics on top of a
  broken chain.

Determinism boundary: latency/cost need a wall clock, which never enters
sealed receipts. They are sidecar audit metadata by design — the report
carries an explicit ``measured=false`` marker with the sidecar convention
instead of fake numbers. Period math uses caller-injected period metadata.

The report is sealed and anchored to the ledger head hash: the same ledger
always reproduces the same report.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_wedge_metrics) or library use
    from .helix_actuator import read_actuation_ledger, verify_actuation_ledger
    from .helix_contestability import verify_appeal_seal, verify_override_seal
    from .helix_holdout import canonical_json_bytes
    from .helix_wedge import verify_wedge_decision
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_actuator import read_actuation_ledger, verify_actuation_ledger
    from core.helix_contestability import verify_appeal_seal, verify_override_seal
    from core.helix_holdout import canonical_json_bytes
    from core.helix_wedge import verify_wedge_decision

SCHEMA_ID = "helix-wedge-metrics/1.0"
ADMISSIONS = ("ADMIT", "SANDBOX_ONLY", "QUARANTINE", "EXCLUDED")
PREVENTED = ("QUARANTINE", "EXCLUDED")


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("report_sha256", None)
    sealed["report_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_metrics_seal(report: dict) -> bool:
    expected = report.get("report_sha256")
    body = {k: v for k, v in report.items() if k != "report_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def wedge_metrics(root: str, ledger_rel: str, appeals: list = None,
                  overrides: list = None, period: dict = None) -> dict:
    """Recompute the T4 metric set from one wedge ledger; sealed report."""
    problems = list(verify_actuation_ledger(root, ledger_rel))
    entries = read_actuation_ledger(root, ledger_rel)
    ledger_head = entries[-1]["entry_sha256"] if entries else None

    decisions = [e["receipt"] for e in entries if e["kind"] == "wedge_decision"]
    decided_requests = {e["request_id"] for e in entries
                        if e["kind"] == "wedge_decision"}
    gate_refusals = sum(1 for e in entries if e["kind"] == "gate"
                        and e["request_id"] not in decided_requests)

    by_admission = {name: 0 for name in ADMISSIONS}
    by_verdict = {}
    operators = set()
    replay_failures = []
    for decision in decisions:
        by_admission[decision["admission"]] = (
            by_admission.get(decision["admission"], 0) + 1)
        verdict = decision.get("handback_verdict")
        by_verdict[str(verdict)] = by_verdict.get(str(verdict), 0) + 1
        operators.add(decision.get("operator", {}).get("id"))
        replay_problems = verify_wedge_decision(root, decision)
        if replay_problems:
            replay_failures.append({"decision_id": decision.get("decision_id"),
                                    "problems": replay_problems})

    ledger_gate_seals = {e["receipt"].get("result_sha256")
                         for e in entries if e["kind"] == "gate"}
    interventions = 0
    for index, receipt in enumerate(appeals or []):
        if (verify_appeal_seal(receipt)
                and receipt.get("gate_result_sha256") in ledger_gate_seals):
            interventions += 1
        else:
            problems.append(f"appeal[{index}] is unverifiable or foreign; "
                            "not counted")
    for index, receipt in enumerate(overrides or []):
        if (verify_override_seal(receipt)
                and receipt.get("gate_result_sha256") in ledger_gate_seals):
            interventions += 1
        else:
            problems.append(f"override[{index}] is unverifiable or foreign; "
                            "not counted")

    total = len(decisions)
    prevented = sum(by_admission[name] for name in PREVENTED)
    weeks = (period or {}).get("weeks")
    report = {
        "schema": SCHEMA_ID,
        "ledger": ledger_rel,
        "ledger_head_sha256": ledger_head,
        "metrics_valid": not verify_actuation_ledger(root, ledger_rel),
        "decisions_total": total,
        "by_admission": by_admission,
        "by_verdict": dict(sorted(by_verdict.items())),
        "distinct_operators": sorted(o for o in operators if o),
        "gate_refusals": gate_refusals,
        "prevented_invalid_handbacks": prevented,
        "replay": {
            "verified": total - len(replay_failures),
            "total": total,
            "rate": ((total - len(replay_failures)) / total) if total else None,
            "failures": replay_failures,
        },
        "intervention": {
            "count": interventions,
            "rate": (interventions / total) if total else None,
        },
        "north_star": {
            "metric": "weekly_real_admission_decisions",
            "decisions": total,
            "period": period or {"weeks": None,
                                 "note": "period metadata not injected"},
            "weekly_rate": (total / weeks) if weeks else None,
        },
        "latency_cost": {
            "measured": False,
            "how": "wall clock never enters sealed receipts; record "
                   "time_to_decision/cost as sidecar audit metadata keyed by "
                   "decision_id, outside the deterministic boundary",
        },
        "problems": sorted(problems),
    }
    return _seal(report)


if __name__ == "__main__":
    print("library module — wedge_metrics(root, ledger_rel, appeals, "
          "overrides, period)")
    sys.exit(2)
