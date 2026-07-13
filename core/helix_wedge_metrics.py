#!/usr/bin/env python3
"""Operational metrics for the wedge, recomputed from the ledger (T4, P5_3).

Policy source of truth: process plan §P5 North Star and metrics —
``weekly_real_admission_decisions``, ``prevented_invalid_handbacks``,
``replay_success``, ``operator_intervention_rate``. Every number is
DERIVED from sealed evidence, never kept as a separate mutable counter:

- all decisions and their admission/verdict distributions come from the
  ledger's ``wedge_decision`` entries, while North-Star/T4 counts include only
  receipts sealed with ``provenance_class=real``;
- prevented_invalid_handbacks = EXCLUDED + QUARANTINE decisions (invalid
  handbacks blocked without manual review — the wedge's core value);
- replay_success re-runs ``verify_wedge_decision`` on every decision, so a
  receipt laundered WITHOUT also rebuilding its stored packet drags the rate
  below 100% instead of hiding; a write-capable adversary who rebuilds the
  packet too is NOT caught here (unkeyed seals — see helix_wedge security
  boundary);
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

SCHEMA_ID = "helix-wedge-metrics/1.1"
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
    real_decisions = [
        d for d in decisions
        if d.get("provenance_class") == "real"
        and d.get("metric", {}).get("counts_toward")
        == "weekly_real_admission_decisions"
    ]
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

    real_by_admission = {name: 0 for name in ADMISSIONS}
    real_operators = set()
    for decision in real_decisions:
        real_by_admission[decision["admission"]] = (
            real_by_admission.get(decision["admission"], 0) + 1)
        real_operators.add(decision.get("operator", {}).get("id"))

    provenance_counts = {name: 0 for name in
                         ("real", "synthetic", "unclassified")}
    for decision in decisions:
        provenance = decision.get("provenance_class", "unclassified")
        key = provenance if provenance in provenance_counts else "unclassified"
        provenance_counts[key] += 1

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
    real_total = len(real_decisions)
    prevented = sum(by_admission[name] for name in PREVENTED)
    real_prevented = sum(real_by_admission[name] for name in PREVENTED)
    weeks = (period or {}).get("weeks")
    report = {
        "schema": SCHEMA_ID,
        "ledger": ledger_rel,
        "ledger_head_sha256": ledger_head,
        "metrics_valid": not verify_actuation_ledger(root, ledger_rel),
        "decisions_total": total,
        "real_decisions_total": real_total,
        "provenance_counts": provenance_counts,
        "by_admission": by_admission,
        "real_by_admission": real_by_admission,
        "by_verdict": dict(sorted(by_verdict.items())),
        "distinct_operators": sorted(o for o in operators if o),
        "real_distinct_operators": sorted(o for o in real_operators if o),
        "gate_refusals": gate_refusals,
        "prevented_invalid_handbacks": prevented,
        "real_prevented_invalid_handbacks": real_prevented,
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
            "decisions": real_total,
            "excluded_by_provenance": total - real_total,
            "period": period or {"weeks": None,
                                 "note": "period metadata not injected"},
            "weekly_rate": (real_total / weeks) if weeks else None,
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


PILOT_SCHEMA_ID = "helix-pilot-report/1.1"


def aggregate_pilot(root: str, participant_ledgers: dict, period: dict = None,
                    sidecar: dict = None) -> dict:
    """Combine per-participant wedge ledgers into one T4 pilot report.

    ``participant_ledgers``: {participant_id: ledger_rel}. Each participant's
    numbers are recomputed from their own sealed ledger (wedge_metrics), then
    summed. ``sidecar`` carries the metrics that need real-world signals
    outside sealed receipts — kept explicit and separate:
      {"false_admits": {pid: count}, "retained": [pid, ...],
       "manual_review_baseline_minutes": {...}, "wedge_review_minutes": {...}}
    False-admits and adoption cannot be derived from the ledger (a ledger only
    knows the decision at admission time), so they are honestly marked
    unmeasured when the sidecar omits them.

    T4 gate (process plan §P5): weekly >=20 explicit-real decisions OR review time 50%
    reduction; false-admit <=1%; replay 100%; >=2 of >=3 external participants
    retained. Each criterion reports pass/None(unmeasured); the overall verdict
    is "passed" only when every measured criterion passes AND none required is
    unmeasured.
    """
    sidecar = sidecar or {}
    per_participant = {}
    combined_decisions = 0
    combined_real_decisions = 0
    combined_admit = 0
    combined_prevented = 0
    replay_ok = True
    problems = []
    real_participant_ids = []
    for pid in sorted(participant_ledgers):
        m = wedge_metrics(root, participant_ledgers[pid])
        per_participant[pid] = m
        combined_decisions += m["decisions_total"]
        combined_real_decisions += m["real_decisions_total"]
        combined_admit += m["real_by_admission"]["ADMIT"]
        combined_prevented += m["real_prevented_invalid_handbacks"]
        if m["real_decisions_total"] > 0:
            real_participant_ids.append(pid)
        if not m["metrics_valid"]:
            problems.append(f"{pid}: ledger chain invalid")
        if m["replay"]["total"] and m["replay"]["rate"] != 1.0:
            replay_ok = False
            problems.append(f"{pid}: replay rate {m['replay']['rate']} < 1.0")

    participants = len(participant_ledgers)
    real_participants = len(real_participant_ids)
    weeks = (period or {}).get("weeks")
    weekly_rate = (combined_real_decisions / weeks) if weeks else None

    false_admits = sidecar.get("false_admits")
    false_admit_rate = None
    if false_admits is not None and combined_admit:
        false_admit_rate = sum(false_admits.get(pid, 0)
                               for pid in real_participant_ids) / combined_admit
    elif false_admits is not None and combined_real_decisions:
        false_admit_rate = 0.0

    retained = sidecar.get("retained")
    retained_count = (len(set(retained) & set(real_participant_ids))
                      if retained is not None else None)

    baseline = sidecar.get("manual_review_baseline_minutes")
    wedge_min = sidecar.get("wedge_review_minutes")
    review_reduction = None
    if baseline and wedge_min and real_participant_ids:
        b = sum(baseline.get(pid, 0) for pid in real_participant_ids)
        w = sum(wedge_min.get(pid, 0) for pid in real_participant_ids)
        review_reduction = (b - w) / b if b else None

    def gate(measured, ok):
        return None if not measured else bool(ok)

    throughput_pass = gate(
        weekly_rate is not None or review_reduction is not None,
        (weekly_rate is not None and weekly_rate >= 20)
        or (review_reduction is not None and review_reduction >= 0.5))
    false_admit_pass = gate(false_admit_rate is not None,
                            false_admit_rate is not None and false_admit_rate <= 0.01)
    replay_pass = replay_ok
    adoption_pass = gate(retained_count is not None,
                         real_participants >= 3 and (retained_count or 0) >= 2)

    required = [throughput_pass, false_admit_pass, replay_pass, adoption_pass]
    verdict = ("passed" if all(x is True for x in required)
               else ("failed" if any(x is False for x in required)
                     else "incomplete"))

    return _seal({
        "schema": PILOT_SCHEMA_ID,
        "participants": participants,
        "participant_ids": sorted(participant_ledgers),
        "real_participants": real_participants,
        "real_participant_ids": sorted(real_participant_ids),
        "combined": {
            "decisions_total": combined_decisions,
            "real_decisions_total": combined_real_decisions,
            "excluded_by_provenance": combined_decisions - combined_real_decisions,
            "admitted": combined_admit,
            "prevented_invalid_handbacks": combined_prevented,
            "weekly_rate": weekly_rate,
            "period": period or {"weeks": None},
        },
        "north_star": {"metric": "weekly_real_admission_decisions",
                       "value": weekly_rate},
        "t4_gate": {
            "throughput": {"pass": throughput_pass, "weekly_rate": weekly_rate,
                           "review_time_reduction": review_reduction,
                           "target": ">=20/week or >=50% review-time cut"},
            "false_admit": {"pass": false_admit_pass, "rate": false_admit_rate,
                            "target": "<=0.01"},
            "replay": {"pass": replay_pass, "target": "100%"},
            "adoption": {"pass": adoption_pass, "participants": participants,
                         "real_participants": real_participants,
                         "retained": retained_count,
                         "target": ">=3 external, >=2 retained"},
            "verdict": verdict,
        },
        "per_participant": per_participant,
        "problems": sorted(problems),
    })


if __name__ == "__main__":
    print("library module — wedge_metrics(...) / aggregate_pilot(...)")
    sys.exit(2)
