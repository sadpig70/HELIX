#!/usr/bin/env python3
"""T4 verdict — compose the metrics gate with an independent-provenance gate.

``aggregate_pilot`` (core/helix_wedge_metrics.py) judges the T4 *metrics* gate:
throughput, false-admit rate, replay, retention. But those numbers alone do not
prove the participants are genuinely INDEPENDENT operators running the wedge on
real, owned work — a self-dealing insider could produce several ledgers that pass
the metrics gate. That is T4 forgery at the pilot level.

This module adds a PROVENANCE gate on top and requires BOTH to pass. Each
participant must present a verified ``real_owned_stakes`` attestation
(core/helix_owned_stakes.py) bound to that participant's own sealed ledger head,
and the operators must be mutually independent and independent of the wedge
author. T4 is ``passed`` only when the metrics gate passes AND at least two of at
least three participants clear the independent-provenance gate.

Honest by construction:
- fail-closed default is ``not_passed``; every unmet requirement is reported as
  an explicit gap;
- no single-operator, unbacked, or self-dealing set can ever pass;
- this module JUDGES; it does not produce the data. Real ``real_owned_stakes``
  evidence comes from an external pilot (P5_5) — a real-world event, not code.
  With no real participants the verdict is ``not_passed``.

Deterministic, stdlib only: no clock, network, subprocess, randomness, or AI.
Reuses aggregate_pilot verbatim (single source for the metrics); the same
ledgers + attestations always reproduce the same sealed verdict.
"""

import hashlib
import os
import sys

try:
    from .helix_holdout import canonical_json_bytes
    from .helix_owned_stakes import owned_stakes_grade
    from .helix_wedge_metrics import aggregate_pilot
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import canonical_json_bytes
    from core.helix_owned_stakes import owned_stakes_grade
    from core.helix_wedge_metrics import aggregate_pilot

T4_SCHEMA_ID = "helix-t4-verdict/1.0"


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("verdict_sha256", None)
    sealed["verdict_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_t4_seal(verdict: dict) -> bool:
    expected = verdict.get("verdict_sha256")
    body = {k: v for k, v in verdict.items() if k != "verdict_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _provenance_gate(metrics: dict, attestations: dict,
                     wedge_author_id: str) -> dict:
    """Verify each participant's independent real_owned_stakes, bound to its ledger.

    An operator id or org shared across participants disqualifies ALL of its
    participants (a single party masquerading as several is not independent).
    """
    all_per = metrics.get("per_participant", {})
    per = {pid: report for pid, report in all_per.items()
           if report.get("real_decisions_total", 0) > 0}

    # pre-pass: which operator ids/orgs appear for more than one participant
    op_pids, org_pids = {}, {}
    for pid, att in attestations.items():
        if pid not in per or not isinstance(att, dict):
            continue
        op = att.get("operator", {})
        if op.get("id"):
            op_pids.setdefault(op["id"], set()).add(pid)
        if op.get("org"):
            org_pids.setdefault(op["org"], set()).add(pid)

    results = {}
    problems = []
    verified = 0
    for pid in sorted(per):
        head = per[pid].get("ledger_head_sha256")
        att = attestations.get(pid)
        reasons = []
        if not isinstance(att, dict):
            reasons.append("no owned-stakes attestation")
        else:
            if owned_stakes_grade(att) != "real_owned_stakes":
                reasons.append("attestation does not earn real_owned_stakes")
            rw = att.get("real_work", {})
            if not head or rw.get("ledger_head_sha256") != head:
                reasons.append("attestation not bound to this participant's "
                               "real ledger head")
            op = att.get("operator", {})
            oid, org = op.get("id"), op.get("org")
            if oid == wedge_author_id:
                reasons.append("operator is the wedge author (self-dealing)")
            if oid and len(op_pids.get(oid, ())) > 1:
                reasons.append("operator id shared across participants "
                               "(not independent)")
            if org and len(org_pids.get(org, ())) > 1:
                reasons.append("operator org shared across participants "
                               "(not independent)")
        ok = not reasons
        results[pid] = {"verified": ok, "reasons": sorted(reasons)}
        if ok:
            verified += 1
        else:
            problems.append(f"{pid}: " + "; ".join(sorted(reasons)))

    participants = metrics.get("real_participants", 0)
    gate_pass = participants >= 3 and verified >= 2
    return {
        "pass": gate_pass,
        "participants": participants,
        "verified_independent": verified,
        "target": ">=3 participants, >=2 with a verified independent "
                  "real_owned_stakes attestation bound to their real ledger",
        "per_participant": results,
        "problems": sorted(problems),
    }


def t4_verdict(root: str, participant_ledgers: dict,
               owned_stakes_attestations: dict, wedge_author_id: str,
               period: dict = None, sidecar: dict = None) -> dict:
    """Compose the metrics gate and the independent-provenance gate into T4.

    participant_ledgers       = {pid: ledger_rel}  (real sealed wedge ledgers)
    owned_stakes_attestations = {pid: attestation} (one independent operator each)

    verdict == "passed" ONLY when the metrics gate passes AND the provenance gate
    passes. Otherwise "not_passed" with explicit gaps. A bare label, single
    operator, or self-dealing set can never pass.
    """
    if not (wedge_author_id or "").strip():
        raise ValueError("wedge_author_id is required to enforce operator "
                         "independence in the provenance gate")
    metrics = aggregate_pilot(root, participant_ledgers, period, sidecar)
    prov = _provenance_gate(metrics, owned_stakes_attestations or {},
                            wedge_author_id.strip())
    metrics_passed = metrics["t4_gate"]["verdict"] == "passed"
    passed = metrics_passed and prov["pass"]

    gaps = []
    if not metrics_passed:
        gaps.append(f"metrics gate not passed (verdict: "
                    f"{metrics['t4_gate']['verdict']})")
    if not prov["pass"]:
        gaps.append("independent-provenance gate not passed: need >=2 verified "
                    f"independent real_owned_stakes of >=3 participants "
                    f"(have {prov['verified_independent']} verified, "
                    f"{prov['participants']} participants)")

    return _seal({
        "schema": T4_SCHEMA_ID,
        "verdict": "passed" if passed else "not_passed",
        "metrics_verdict": metrics["t4_gate"]["verdict"],
        "provenance_gate": prov,
        "metrics_report_sha256": metrics["report_sha256"],
        "gaps": gaps,
        "note": ("T4 utility CONFIRMED: metrics gate AND >=2 independent verified "
                 "real_owned_stakes participants — utility signal is real and "
                 "unforgeable" if passed else
                 "T4 NOT passed: metrics and/or independent-provenance "
                 "requirements unmet. No single-operator, unbacked, or "
                 "self-dealing path can pass this gate."),
        "problems": sorted(list(metrics.get("problems", []))
                           + list(prov.get("problems", []))),
    })


if __name__ == "__main__":
    print("library module — t4_verdict(root, participant_ledgers, "
          "owned_stakes_attestations, wedge_author_id, ...)")
    sys.exit(2)
