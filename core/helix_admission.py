#!/usr/bin/env python3
"""Fail-closed admission classes for the HELIX Actuation Plane (T3).

Policy source of truth: .pgf/DESIGN-HELIXDirection.md (FailClosedAdmission:
"missing=quarantine, thin=sandbox, valid=admit") and process plan §P4
migration policy ("기존 fail-open 경로는 migration flag와 만료일을 둔 뒤
제거한다").

Deterministic mapping from a handback verdict to an admission class:

    valid   -> ADMIT          (full handback evidence)
    thin    -> SANDBOX_ONLY   (evidence exists but is thin)
    breach  -> EXCLUDED       (handback boundary failed; never admitted)
    absent  -> QUARANTINE     (no evidence can never authorize — fail-closed)
    other   -> QUARANTINE     (unknown verdicts fail closed)

The ONLY exception is an explicit migration flag: a sealed, reasoned,
state-receipt-anchored grace that temporarily admits ``absent`` legacy
entries. It expires automatically when the state receipt moves (same drift
semantics as approvals) and it never upgrades thin/breach. Without a live
flag, absent is unconditionally QUARANTINE.

This module classifies and seals receipts. ``engines/exploit.registry_to_ledger``
uses these classes directly, so absent/thin/breach entries cannot enter the
consumed ledger. The migration flag is the only explicit legacy exception.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_admission) or library use
    from .helix_holdout import canonical_json_bytes
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import canonical_json_bytes

SCHEMA_ID = "helix-admission-receipt/1.0"
MIGRATION_SCHEMA_ID = "helix-admission-migration/1.0"
ADMISSION_CLASSES = ("ADMIT", "SANDBOX_ONLY", "QUARANTINE", "EXCLUDED")
KNOWN_VERDICTS = ("valid", "thin", "breach")


def _seal(doc: dict, seal_key: str = "receipt_sha256") -> dict:
    sealed = dict(doc)
    sealed.pop(seal_key, None)
    sealed[seal_key] = hashlib.sha256(canonical_json_bytes(sealed)).hexdigest()
    return sealed


def _seal_ok(doc: dict, seal_key: str = "receipt_sha256") -> bool:
    expected = doc.get(seal_key)
    body = {k: v for k, v in doc.items() if k != seal_key}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def verify_admission_receipt_seal(receipt: dict) -> bool:
    return _seal_ok(receipt)


def issue_migration_flag(reason: str, state_receipt_hash: str,
                         issuer_id: str) -> dict:
    """Issue the explicit, expiring grace that admits legacy absent entries."""
    if not (reason or "").strip():
        raise ValueError("a migration flag without a reason is not contestable")
    if not (state_receipt_hash or "").strip():
        raise ValueError("migration flag requires a state-receipt anchor")
    if not (issuer_id or "").strip():
        raise ValueError("migration flag requires an issuer id")
    return _seal({
        "schema": MIGRATION_SCHEMA_ID,
        "allow_absent": True,
        "reason": reason,
        "issuer_id": issuer_id,
        "anchor": {"state_receipt_hash": state_receipt_hash},
    }, "flag_sha256")


def _migration_live(migration, current_state_receipt_hash: str) -> bool:
    """A migration flag is live only if sealed, allowing, and anchored to the
    CURRENT state receipt — drift expires it automatically."""
    return (isinstance(migration, dict)
            and _seal_ok(migration, "flag_sha256")
            and migration.get("schema") == MIGRATION_SCHEMA_ID
            and migration.get("allow_absent") is True
            and bool((migration.get("reason") or "").strip())
            and (migration.get("anchor") or {}).get("state_receipt_hash")
            == current_state_receipt_hash)


def classify_admission(verdict, migration=None,
                       current_state_receipt_hash: str = None) -> dict:
    """Map one handback verdict (or its absence) to an admission class."""
    if verdict == "valid":
        return {"admission": "ADMIT", "basis": "handback_valid",
                "migration_applied": False}
    if verdict == "thin":
        return {"admission": "SANDBOX_ONLY", "basis": "handback_thin",
                "migration_applied": False}
    if verdict == "breach":
        return {"admission": "EXCLUDED", "basis": "handback_breach",
                "migration_applied": False}
    if verdict is None:
        if _migration_live(migration, current_state_receipt_hash):
            return {"admission": "ADMIT",
                    "basis": "migration_legacy_fail_open (expires on state "
                             "drift)",
                    "migration_applied": True}
        return {"admission": "QUARANTINE",
                "basis": "no_handback_evidence_fail_closed",
                "migration_applied": False}
    return {"admission": "QUARANTINE",
            "basis": f"unknown_verdict_fail_closed:{verdict!r}",
            "migration_applied": False}


def build_admission_receipt(project: str, verdict, migration=None,
                            current_state_receipt_hash: str = None) -> dict:
    """Seal one admission decision for one generated project."""
    if not (project or "").strip():
        raise ValueError("project name must be non-empty")
    decision = classify_admission(verdict, migration, current_state_receipt_hash)
    return _seal({
        "schema": SCHEMA_ID,
        "project": project,
        "handback_verdict": verdict,
        "admission": decision["admission"],
        "basis": decision["basis"],
        "migration_applied": decision["migration_applied"],
        "migration_flag_sha256": (migration or {}).get("flag_sha256")
        if decision["migration_applied"] else None,
        "state_receipt_hash": current_state_receipt_hash,
    })


def admit_projects(verdicts: dict, migration=None,
                   current_state_receipt_hash: str = None) -> dict:
    """Classify a {project: verdict|None} mapping; returns receipts + summary."""
    receipts = {}
    summary = {cls: 0 for cls in ADMISSION_CLASSES}
    for project in sorted(verdicts):
        receipt = build_admission_receipt(project, verdicts[project],
                                          migration,
                                          current_state_receipt_hash)
        receipts[project] = receipt
        summary[receipt["admission"]] += 1
    return {"receipts": receipts, "summary": summary}


if __name__ == "__main__":
    print("library module — classify_admission / build_admission_receipt / "
          "admit_projects / issue_migration_flag")
    sys.exit(2)
