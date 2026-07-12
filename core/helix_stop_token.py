#!/usr/bin/env python3
"""Stop/resume protocol for the HELIX Constitution (T2/T3 governance).

Policy source of truth: .pgf/DESIGN-HELIXDirection.md (StopResumeProtocol:
"signed stop token and separate resume authority") and the T3 gate rule
"stop token 이후 write/publish=0".

A stop token is an IMMUTABLE sealed document: issuer, reason, scope (global
or write-path prefixes), and the state-receipt anchor at issue time. Resuming
never edits the token — it appends a separate sealed resume receipt chained
to the token's hash (same append-only pattern as prediction -> reveal).

Separation of authority, fail-closed:
- the token issuer can never approve the resume of their own stop; an
  approval set containing the issuer (or any duplicate/non-human/malformed
  approval) refuses the resume outright;
- a tampered token cannot be resumed (the chain no longer matches) and it
  KEEPS blocking — a broken seal must never quietly disable a stop;
- an invalid or tampered resume receipt lifts nothing.

Blocking semantics: stops constrain SIDE EFFECTS. A read-only intent (no
write paths, no remote mutation, no publish) passes even under a global stop.
A global stop blocks every side-effecting intent; a path_prefix stop blocks
intents whose write paths fall under any listed prefix (remote/publish
effects are only blocked by global stops).

No wall clock: order and expiry are proven by state-receipt anchors and the
hash chain alone.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_stop_token) or library use
    from .helix_holdout import canonical_json_bytes
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import canonical_json_bytes

STOP_SCHEMA_ID = "helix-stop-token/1.0"
RESUME_SCHEMA_ID = "helix-resume-receipt/1.0"
SCOPE_KINDS = ("global", "path_prefix")


def _seal(doc: dict, seal_key: str) -> dict:
    sealed = dict(doc)
    sealed.pop(seal_key, None)
    sealed[seal_key] = hashlib.sha256(canonical_json_bytes(sealed)).hexdigest()
    return sealed


def _seal_ok(doc: dict, seal_key: str) -> bool:
    expected = doc.get(seal_key)
    body = {k: v for k, v in doc.items() if k != seal_key}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def verify_stop_token_seal(token: dict) -> bool:
    return _seal_ok(token, "token_sha256")


def verify_resume_receipt_seal(receipt: dict) -> bool:
    return _seal_ok(receipt, "receipt_sha256")


def issue_stop_token(token_id: str, issuer: dict, reason: str, scope: dict,
                     state_receipt_hash: str) -> dict:
    """Issue one immutable sealed stop token."""
    if not (token_id or "").strip():
        raise ValueError("token_id must be non-empty")
    if not (issuer.get("id") or "").strip():
        raise ValueError("issuer.id must be non-empty")
    if not (reason or "").strip():
        raise ValueError("a stop without a reason is not contestable")
    if not (state_receipt_hash or "").strip():
        raise ValueError("stop token requires a state-receipt anchor")
    kind = scope.get("kind")
    if kind not in SCOPE_KINDS:
        raise ValueError(f"scope.kind must be one of {SCOPE_KINDS}")
    prefixes = scope.get("prefixes")
    if kind == "path_prefix":
        if (not isinstance(prefixes, list) or not prefixes
                or not all(isinstance(p, str) and p.strip() for p in prefixes)):
            raise ValueError("path_prefix scope requires non-empty prefixes")
    elif prefixes is not None:
        raise ValueError("global scope must not carry prefixes")
    return _seal({
        "schema": STOP_SCHEMA_ID,
        "token_id": token_id,
        "issuer": {"kind": issuer.get("kind", "human"), "id": issuer["id"]},
        "reason": reason,
        "scope": {"kind": kind, "prefixes": sorted(prefixes) if prefixes else None},
        "anchor": {"state_receipt_hash": state_receipt_hash},
    }, "token_sha256")


def issue_resume_receipt(token: dict, approvals: list, reason: str,
                         state_receipt_hash: str,
                         required_approvals: int = 1) -> dict:
    """Approve lifting one stop; chained to the token's seal, fail-closed.

    Refuses: a token whose seal is broken (restore the original first), a
    reason-less resume, and any approval set containing the token issuer,
    a duplicate, a non-human, a blank id, or a stale/missing anchor.
    """
    if not verify_stop_token_seal(token):
        raise ValueError("stop token seal is broken; a tampered stop cannot "
                         "be resumed")
    if not (reason or "").strip():
        raise ValueError("a resume without a reason is not contestable")
    issuer_id = token["issuer"]["id"]
    seen = set()
    for index, approval in enumerate(approvals or []):
        label = f"approval[{index}]"
        approver_id = approval.get("approver_id")
        if not isinstance(approver_id, str) or not approver_id.strip():
            raise ValueError(f"{label}: approver_id must be non-empty")
        if approval.get("kind") != "human":
            raise ValueError(f"{label}: only humans grant resume authority")
        if approver_id == issuer_id:
            raise ValueError(f"{label}: separated authority — issuer "
                             f"{issuer_id} cannot resume their own stop")
        if approver_id in seen:
            raise ValueError(f"{label}: duplicate approver {approver_id}")
        seen.add(approver_id)
        anchor = (approval.get("anchor") or {}).get("state_receipt_hash")
        if anchor != state_receipt_hash:
            raise ValueError(f"{label}: approval must be anchored to the "
                             "current state receipt")
    if len(seen) < max(1, required_approvals):
        raise ValueError(f"insufficient resume approvals: {len(seen)} < "
                         f"{max(1, required_approvals)}")
    return _seal({
        "schema": RESUME_SCHEMA_ID,
        "stop_token_sha256": token["token_sha256"],
        "reason": reason,
        "state_receipt_hash": state_receipt_hash,
        "approvals": [{"approver_id": a["approver_id"], "kind": "human",
                       "anchor": {"state_receipt_hash": state_receipt_hash}}
                      for a in approvals],
    }, "receipt_sha256")


def _resume_lifts(token: dict, receipt: dict) -> bool:
    """A resume lifts a stop only if its own chain and rules re-verify."""
    if not verify_resume_receipt_seal(receipt):
        return False
    if receipt.get("stop_token_sha256") != token.get("token_sha256"):
        return False
    issuer_id = token["issuer"]["id"]
    seen = set()
    for approval in receipt.get("approvals", []):
        approver_id = approval.get("approver_id")
        if (not approver_id or approver_id == issuer_id or approver_id in seen
                or approval.get("kind") != "human"
                or (approval.get("anchor") or {}).get("state_receipt_hash")
                != receipt.get("state_receipt_hash")):
            return False
        seen.add(approver_id)
    return bool(seen)


def active_stops(tokens: list, resume_receipts: list) -> list:
    """Tokens still in force: every token without a verifiable resume.

    A token with a broken seal stays active — tampering must never lift a
    stop — and can only be resumed after the original token is restored.
    """
    return [token for token in tokens or []
            if not any(_resume_lifts(token, receipt)
                       for receipt in resume_receipts or [])]


def _has_side_effects(intent: dict) -> bool:
    scope = intent["scope"]
    return bool(scope["write_paths"]) or scope["remote_mutation"] or scope["publish"]


def blocking_stops(intent: dict, tokens: list, resume_receipts: list) -> list:
    """Active stop tokens whose scope blocks this intent's side effects.

    Read-only intents are never blocked. Returns [{token_id, token_sha256,
    reason}] sorted by token_id — non-empty means: no side effect may run,
    regardless of any authorization gate outcome.
    """
    if not _has_side_effects(intent):
        return []
    write_paths = [p.replace("\\", "/") for p in intent["scope"]["write_paths"]]
    blocking = []
    for token in active_stops(tokens, resume_receipts):
        scope = token["scope"]
        if scope["kind"] == "global":
            hit = True
        else:
            hit = any(path.startswith(prefix)
                      for path in write_paths
                      for prefix in scope["prefixes"])
        if hit:
            blocking.append({"token_id": token["token_id"],
                             "token_sha256": token.get("token_sha256"),
                             "reason": token["reason"]})
    return sorted(blocking, key=lambda item: item["token_id"])


if __name__ == "__main__":
    print("library module — issue_stop_token / issue_resume_receipt / "
          "active_stops / blocking_stops")
    sys.exit(2)
