#!/usr/bin/env python3
"""Deterministic acceptance gate for AI-authored Condense proposals."""

import hashlib
import os

from .helix_holdout import canonical_json_bytes
from .helix_state_receipt import sha256_file

SCHEMA_ID = "helix-condense-proposal-receipt/1.0"
ACTIONS = ("CONDENSE", "BUILD_ON_PLATFORM")


def _seal(doc: dict) -> dict:
    body = {k: v for k, v in doc.items() if k != "receipt_sha256"}
    body["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()
    return body


def evaluate_condense_proposal(root: str, proposal: dict) -> dict:
    problems = []
    action = proposal.get("action")
    if action not in ACTIONS:
        problems.append("unknown proposal action")
    if not (proposal.get("machine") or "").strip():
        problems.append("machine claim is required")
    if not (proposal.get("target") or "").strip():
        problems.append("proposal target is required")
    kernel_changes = proposal.get("kernel_changes") or []
    if action == "BUILD_ON_PLATFORM" and kernel_changes:
        problems.append("BUILD_ON_PLATFORM violates zero-kernel-change")
    evidence_results = []
    for role in ("probe", "parity"):
        evidence = (proposal.get("evidence") or {}).get(role)
        row = {"role": role, "valid": False}
        if not isinstance(evidence, dict) or evidence.get("passed") is not True:
            problems.append(f"{role} evidence must explicitly pass")
        else:
            path = evidence.get("path")
            full = path if os.path.isabs(path or "") else os.path.join(root, path or "")
            if not path or not os.path.isfile(full):
                problems.append(f"{role} evidence file is missing")
            elif sha256_file(full) != evidence.get("sha256"):
                problems.append(f"{role} evidence hash mismatch")
            else:
                row["valid"] = True
                row["sha256"] = evidence["sha256"]
        evidence_results.append(row)
    return _seal({
        "schema": SCHEMA_ID,
        "proposal_id": proposal.get("proposal_id"),
        "action": action,
        "machine": proposal.get("machine"),
        "target": proposal.get("target"),
        "decision": "ACCEPT" if not problems else "REJECT",
        "problems": sorted(problems),
        "evidence": evidence_results,
    })


def verify_condense_receipt(receipt: dict) -> bool:
    expected = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return expected == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
