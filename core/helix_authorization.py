#!/usr/bin/env python3
"""Deterministic authorization gate for the HELIX Constitution (T2).

Implements the DESIGN PPR ``admit()``: combine the three sealed contracts —
ActionIntent (P3_1), EvidenceManifest (P3_2), risk policy matrix (P3_3) —
into one GateResult decision:

    DENY     intent invalid, evidence missing/mismatched/unbound, or the
             approval set contains a violation (self-approval, duplicate,
             malformed). Missing or mismatched evidence NEVER returns ALLOW.
    RETIRE   the evidence manifest was issued under a different policy
             version; the contracts must be re-issued, not re-judged.
    HUMAN    contracts verify but authority is not yet granted: approvals
             insufficient, dry-run evidence absent, or approvals expired by
             state drift (renewal, not violation).
    SANDBOX  contracts and authority hold but every artifact's provenance is
             ``external`` — thin evidence with no receipt-backed lineage may
             run in a sandbox only.
    ALLOW    all contracts verify, authority satisfied, lineage present.

Precedence is fixed: DENY > RETIRE > HUMAN > SANDBOX > ALLOW — checked in the
order intent -> evidence presence -> policy generation -> evidence bytes ->
approval violations -> approval sufficiency -> provenance thinness. Identical
inputs and policy version produce an identical sealed result, and every
result carries non-empty reasons plus the input digests needed to replay it.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_authorization) or library use
    from .helix_constitution import intent_digest, validate_action_intent
    from .helix_evidence import verify_evidence_manifest
    from .helix_holdout import canonical_json_bytes
    from .helix_risk_policy import (POLICY_VERSION, effective_risk_class,
                                    evaluate_risk_policy)
    from .helix_stop_token import blocking_stops
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_constitution import intent_digest, validate_action_intent
    from core.helix_evidence import verify_evidence_manifest
    from core.helix_holdout import canonical_json_bytes
    from core.helix_risk_policy import (POLICY_VERSION, effective_risk_class,
                                        evaluate_risk_policy)
    from core.helix_stop_token import blocking_stops

SCHEMA_ID = "helix-gate-result/1.0"
DECISIONS = ("ALLOW", "SANDBOX", "HUMAN", "DENY", "RETIRE")

# Risk-policy problems that mean "authority not granted yet" (-> HUMAN) rather
# than "the submission itself is a violation" (-> DENY). Approval expiry by
# state drift is renewal, not violation.
_RENEWAL_MARKERS = ("insufficient human approvals", "dry-run evidence",
                    "expired")


def _seal(result: dict) -> dict:
    sealed = dict(result)
    sealed.pop("result_sha256", None)
    sealed["result_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_gate_result_seal(result: dict) -> bool:
    expected = result.get("result_sha256")
    body = {k: v for k, v in result.items() if k != "result_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _is_renewal(problem: str) -> bool:
    return any(marker in problem for marker in _RENEWAL_MARKERS)


def _thin_evidence(manifest: dict) -> bool:
    """Thin = no artifact has a receipt-backed lineage (external-only)."""
    artifacts = manifest.get("artifacts", [])
    return bool(artifacts) and all(
        artifact["provenance"]["origin"] == "external" for artifact in artifacts)


def authorize(root: str, intent: dict, evidence_manifest,
              approvals: list, current_state_receipt_hash: str,
              stop_tokens: list = None, resume_receipts: list = None) -> dict:
    """Judge one proposed action; return a sealed GateResult.

    Active stop tokens (core/helix_stop_token) are checked right after the
    intent shape: a stop covering this intent's side effects returns DENY no
    matter what evidence or approvals say (T3: stop 이후 write/publish=0).
    Read-only intents pass stops by definition.
    """
    risk = effective_risk_class(intent)
    base = {
        "schema": SCHEMA_ID,
        "policy_version": POLICY_VERSION,
        "risk_class": risk,
        "intent_digest": intent_digest(intent),
        "evidence_manifest_sha256": (evidence_manifest or {}).get("manifest_sha256"),
        "state_receipt_hash": current_state_receipt_hash,
        "valid_approvers": [],
    }

    def decide(decision, reasons, valid_approvers=()):
        return _seal({**base, "decision": decision,
                      "reasons": sorted(reasons),
                      "valid_approvers": sorted(valid_approvers)})

    intent_problems = validate_action_intent(root, intent)
    if intent_problems:
        return decide("DENY", [f"intent: {p}" for p in intent_problems])

    blocking = blocking_stops(intent, stop_tokens or [], resume_receipts or [])
    if blocking:
        return decide("DENY", [
            f"stopped: token {item['token_id']} ({item['reason']}) blocks "
            "this scope; no side effect may run until a separate authority "
            "resumes it" for item in blocking])

    if not isinstance(evidence_manifest, dict):
        return decide("DENY", ["missing evidence manifest: no evidence can "
                               "never authorize"])

    manifest_policy = evidence_manifest.get("policy_version")
    if manifest_policy != POLICY_VERSION:
        return decide("RETIRE", [f"evidence issued under policy "
                                 f"{manifest_policy!r} != gate policy "
                                 f"{POLICY_VERSION!r}; re-issue the contracts"])

    evidence_problems = verify_evidence_manifest(root, evidence_manifest, intent)
    if evidence_problems:
        return decide("DENY", [f"evidence: {p}" for p in evidence_problems])

    policy = evaluate_risk_policy(intent, approvals,
                                  current_state_receipt_hash, evidence_manifest)
    violations = [p for p in policy["problems"] if not _is_renewal(p)]
    if violations:
        return decide("DENY", [f"approval: {p}" for p in violations],
                      policy["valid_approvers"])
    if not policy["satisfied"]:
        renewals = [f"approval: {p}" for p in policy["problems"]]
        return decide("HUMAN", renewals or ["human authority required"],
                      policy["valid_approvers"])

    if _thin_evidence(evidence_manifest):
        return decide("SANDBOX", ["thin evidence: every artifact is "
                                  "external-only with no receipt-backed "
                                  "lineage; sandbox execution only"],
                      policy["valid_approvers"])

    return decide("ALLOW", [f"all contracts verified; risk {risk} authority "
                            "satisfied with receipt-backed evidence"],
                  policy["valid_approvers"])


if __name__ == "__main__":
    print("library module — use authorize(root, intent, evidence_manifest, "
          "approvals, state_receipt_hash)")
    sys.exit(2)
