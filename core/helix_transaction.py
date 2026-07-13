#!/usr/bin/env python3
"""Pure deterministic state machine for governed HELIX transactions."""

import hashlib

from .helix_holdout import canonical_json_bytes
from .helix_signing import sign_bytes, verify_signature

SCHEMA_ID = "helix-transaction/1.0"
INITIAL = "PLANNED"
TERMINAL = {"REPLAYABLE", "ROLLED_BACK", "BLOCKED", "QUARANTINED"}
TRANSITIONS = {
    "PLANNED": {"authorize": "AUTHORIZED", "block": "BLOCKED"},
    "AUTHORIZED": {"apply": "APPLYING", "block": "BLOCKED"},
    "APPLYING": {"applied": "APPLIED", "rollback": "ROLLBACK_REQUIRED",
                 "quarantine": "QUARANTINED"},
    "APPLIED": {"verify": "VERIFYING", "rollback": "ROLLBACK_REQUIRED"},
    "VERIFYING": {"verified": "VERIFIED", "rollback": "ROLLBACK_REQUIRED",
                  "quarantine": "QUARANTINED"},
    "VERIFIED": {"handback": "HANDBACK_COMPLETE"},
    "HANDBACK_COMPLETE": {"replay": "REPLAYABLE",
                          "rollback": "ROLLBACK_REQUIRED"},
    "ROLLBACK_REQUIRED": {"rolled_back": "ROLLED_BACK",
                          "quarantine": "QUARANTINED"},
}


def _body(tx: dict) -> dict:
    return {k: v for k, v in tx.items() if k not in ("transaction_sha256",
                                                       "transaction_hmac")}


def _seal(tx: dict, signing_key=None) -> dict:
    sealed = dict(_body(tx))
    sealed["transaction_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    if signing_key is not None:
        sealed["transaction_hmac"] = sign_bytes(
            signing_key, canonical_json_bytes(_body(sealed)))
    return sealed


def new_transaction(transaction_id: str, intent_digest: str,
                    signing_key=None) -> dict:
    if not transaction_id or not intent_digest:
        raise ValueError("transaction_id and intent_digest are required")
    return _seal({"schema": SCHEMA_ID, "transaction_id": transaction_id,
                  "intent_digest": intent_digest, "state": INITIAL,
                  "history": [], "applied_event_ids": []}, signing_key)


def verify_transaction(tx: dict, signing_key=None) -> list:
    problems = []
    expected = tx.get("transaction_sha256")
    if expected != hashlib.sha256(canonical_json_bytes(_body(tx))).hexdigest():
        problems.append("transaction seal is broken")
    if tx.get("transaction_hmac") is not None:
        if signing_key is None or not verify_signature(
                signing_key, canonical_json_bytes(_body(tx)),
                tx.get("transaction_hmac")):
            problems.append("transaction HMAC is invalid, missing, or unverified")
    elif signing_key is not None:
        problems.append("transaction HMAC is invalid, missing, or unverified")
    replay = INITIAL
    seen = set()
    for item in tx.get("history", []):
        event_id, event = item.get("event_id"), item.get("event")
        if not event_id or event_id in seen:
            problems.append("history contains a missing or duplicate event_id")
            continue
        seen.add(event_id)
        target = TRANSITIONS.get(replay, {}).get(event)
        if target is None:
            problems.append(f"illegal replay transition: {replay}/{event}")
            continue
        if item.get("from") != replay or item.get("to") != target:
            problems.append(f"history transition mismatch for {event_id}")
        replay = target
    if replay != tx.get("state"):
        problems.append("history does not reconstruct current state")
    if sorted(seen) != sorted(tx.get("applied_event_ids", [])):
        problems.append("applied_event_ids do not match history")
    return sorted(set(problems))


def transition(tx: dict, event_id: str, event: str, receipt_sha256=None,
               signing_key=None) -> dict:
    if verify_transaction(tx, signing_key):
        raise ValueError("cannot transition a tampered transaction")
    if event_id in tx["applied_event_ids"]:
        return tx
    target = TRANSITIONS.get(tx["state"], {}).get(event)
    if target is None:
        raise ValueError(f"illegal transaction transition: {tx['state']}/{event}")
    updated = dict(_body(tx))
    updated["state"] = target
    updated["history"] = list(tx["history"]) + [{
        "event_id": event_id, "event": event, "from": tx["state"],
        "to": target, "receipt_sha256": receipt_sha256,
    }]
    updated["applied_event_ids"] = list(tx["applied_event_ids"]) + [event_id]
    return _seal(updated, signing_key)


def record_admission_result(tx: dict, result: dict, signing_key=None) -> dict:
    """Project one completed ``run_admission`` result into transaction state.

    Event IDs are derived from the request id and stage, so replaying the same
    result is idempotent. This is an audit bridge: authorization remains owned
    by ``run_admission`` and this function cannot turn a refusal into execution.
    """
    request_id = result.get("request_id")
    if not request_id:
        raise ValueError("admission result requires request_id")

    def advance(current, event, receipt=None):
        return transition(current, f"{request_id}:{event}", event, receipt,
                          signing_key)

    gate = result.get("gate") or {}
    if gate.get("decision") not in ("ALLOW", "SANDBOX"):
        return advance(tx, "block", gate.get("result_sha256"))
    tx = advance(tx, "authorize", gate.get("result_sha256"))
    if not result.get("executed"):
        return advance(tx, "block", (result.get("guard") or {}).get(
            "receipt_sha256"))
    tx = advance(tx, "apply", (result.get("plan") or {}).get("plan_sha256"))
    tx = advance(tx, "applied", (result.get("guard") or {}).get(
        "receipt_sha256"))
    tx = advance(tx, "verify", (result.get("handback") or {}).get(
        "handback_sha256"))
    handback = result.get("handback") or {}
    if handback.get("verdict") != "clean":
        tx = advance(tx, "rollback", handback.get("handback_sha256"))
        if result.get("rolled_back"):
            return advance(tx, "rolled_back")
        return advance(tx, "quarantine")
    tx = advance(tx, "verified", handback.get("handback_sha256"))
    tx = advance(tx, "handback", handback.get("handback_sha256"))
    return advance(tx, "replay", handback.get("handback_sha256"))
