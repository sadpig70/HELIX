#!/usr/bin/env python3
"""Risk policy matrix for the HELIX Constitution (T2 governance).

Policy source of truth: _workspace/HELIXDirection_process_plan.md §P3 risk
table and the T2 gate rules ("stop/resume authority 분리", "reason 없는
override=0"). This module is the pure approval/separation/expiry matrix:

    R0  read-only inspection      0 approvals  deterministic auto-allow
    R1  local reversible artifact 0 approvals  allow within budget (budget
                                               shape is enforced by P3_1)
    R2  write/publish/remote      1 human approval, distinct from proposer
    R3  authority/economic/...    2 distinct human approvals, none by the
                                  proposer, plus dry-run evidence

Deterministic expiry: an approval carries no wall-clock timestamp. It is
anchored to the state-receipt hash it was granted against; if the current
state receipt differs, the approval is expired (state drift revokes authority
automatically — same semantics as the P1 drift gate). Separation of duties:
the proposer can never approve their own action, and a submitted approval set
containing ANY invalid approval (self, duplicate, stale, malformed) fails the
whole evaluation — fail-closed, never "count only the good ones".

This module judges the approval matrix only. Evidence byte verification is
core/helix_evidence.py; combining both into ALLOW|SANDBOX|HUMAN|DENY|RETIRE
is the authorization gate (P3_4).

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import os
import sys

try:  # package import (python -m core.helix_risk_policy) or library use
    from .helix_constitution import RISK_ORDER, classify_risk
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_constitution import RISK_ORDER, classify_risk

POLICY_VERSION = "HELIX-CONSTITUTION/1.0"
DRY_RUN_ROLE = "dry_run"

_MATRIX = {
    "R0": {"human_approvals": 0, "dry_run_required": False},
    "R1": {"human_approvals": 0, "dry_run_required": False},
    "R2": {"human_approvals": 1, "dry_run_required": False},
    "R3": {"human_approvals": 2, "dry_run_required": True},
}


def policy_matrix() -> dict:
    """The full approval matrix (copy) for documentation and audit output."""
    return {risk: dict(req) for risk, req in _MATRIX.items()}


def effective_risk_class(intent: dict) -> str:
    """Defensive risk: the higher of the declared and the derived class.

    P3_1 already rejects under-classification; the policy still never trusts
    the label below the derived effects.
    """
    declared = intent["risk_class"]
    derived = classify_risk(intent)
    return max(declared, derived, key=RISK_ORDER.index)


def _approval_problems(intent: dict, approvals: list,
                       current_state_receipt_hash: str) -> tuple:
    """Validate the submitted approval set; return (problems, valid_humans)."""
    problems = []
    proposer_id = intent["proposer"]["id"]
    seen = set()
    valid_humans = []
    for index, approval in enumerate(approvals):
        label = f"approval[{index}]"
        approver_id = approval.get("approver_id")
        if not isinstance(approver_id, str) or not approver_id.strip():
            problems.append(f"{label}: approver_id must be non-empty")
            continue
        if approval.get("kind") != "human":
            problems.append(f"{label}: kind {approval.get('kind')!r} cannot "
                            "approve (only humans grant authority)")
            continue
        if approver_id == proposer_id:
            problems.append(f"{label}: separation of duties — proposer "
                            f"{proposer_id} cannot approve their own action")
            continue
        if approver_id in seen:
            problems.append(f"{label}: duplicate approver {approver_id}")
            continue
        seen.add(approver_id)
        anchor = (approval.get("anchor") or {}).get("state_receipt_hash")
        if not isinstance(anchor, str) or not anchor:
            problems.append(f"{label}: missing state-receipt anchor")
            continue
        if anchor != current_state_receipt_hash:
            problems.append(f"{label}: expired — anchored to stale state "
                            f"receipt {anchor[:16]}… != current "
                            f"{current_state_receipt_hash[:16]}…")
            continue
        valid_humans.append(approver_id)
    return problems, valid_humans


def _has_dry_run(evidence_manifest) -> bool:
    if not isinstance(evidence_manifest, dict):
        return False
    return any(artifact.get("role") == DRY_RUN_ROLE
               for artifact in evidence_manifest.get("artifacts", []))


def evaluate_risk_policy(intent: dict, approvals: list,
                         current_state_receipt_hash: str,
                         evidence_manifest: dict = None) -> dict:
    """Judge whether the submitted approvals satisfy the matrix for one intent.

    Fail-closed: any invalid approval in the set (self-approval, duplicate,
    stale or missing anchor, malformed) is a problem and the evaluation is
    not satisfied, even if enough other approvals exist.
    """
    risk = effective_risk_class(intent)
    requirements = dict(_MATRIX[risk])
    problems, valid_humans = _approval_problems(
        intent, approvals or [], current_state_receipt_hash)

    if len(valid_humans) < requirements["human_approvals"]:
        problems.append(
            f"insufficient human approvals: {len(valid_humans)} < "
            f"{requirements['human_approvals']} required for {risk}")
    if requirements["dry_run_required"] and not _has_dry_run(evidence_manifest):
        problems.append(f"{risk} requires dry-run evidence "
                        f"(manifest artifact with role '{DRY_RUN_ROLE}')")

    return {
        "policy_version": POLICY_VERSION,
        "risk_class": risk,
        "requirements": requirements,
        "valid_approvers": sorted(valid_humans),
        "problems": sorted(problems),
        "satisfied": not problems,
    }


if __name__ == "__main__":
    print("library module — approval matrix:", policy_matrix())
    sys.exit(2)
