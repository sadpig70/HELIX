#!/usr/bin/env python3
"""Pre-effect guard for the HELIX Actuation Plane (T3).

Policy source of truth: .pgf/DESIGN-HELIXDirection.md (SideEffectBoundary:
"every write/publish rechecks authorization and stop") and the invariant
"failed or expired authority cannot be converted into consumed ledger state".

``guard_side_effects`` is the single judgment an actuator must obtain
IMMEDIATELY before executing a sealed plan. It re-checks, in one pass:

1. the plan itself — seal, intent binding, gate chain, scope, budget, and
   rollback snapshots (core/helix_execution_plan.verify_execution_plan);
2. authority currency — the gate result must be anchored to the CURRENT
   state receipt; state drift expires plan authority exactly like it expires
   approvals (P3_3) and migration flags (P4_2);
3. stops — an active stop covering the intent's side effects blocks
   execution no matter what the gate said (T3: stop 이후 write/publish=0);
4. filesystem preconditions — the plan's dry-run assumptions must still hold
   (no target drift, no pre-empted creates).

The guard only judges; it never executes. Its sealed receipt is chained to
the plan seal, so an actuator (P4_5) can prove that every effect it ran was
cleared by a guard bound to exactly that plan at exactly that state.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_side_effect_guard) or library use
    from .helix_authorization import verify_gate_result_seal
    from .helix_constitution import intent_digest
    from .helix_execution_plan import verify_execution_plan
    from .helix_holdout import canonical_json_bytes
    from .helix_stop_token import blocking_stops
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_authorization import verify_gate_result_seal
    from core.helix_constitution import intent_digest
    from core.helix_execution_plan import verify_execution_plan
    from core.helix_holdout import canonical_json_bytes
    from core.helix_stop_token import blocking_stops

SCHEMA_ID = "helix-side-effect-guard/1.0"


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_guard_receipt_seal(receipt: dict) -> bool:
    expected = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def guard_side_effects(root: str, intent: dict, gate_result: dict, plan: dict,
                       current_state_receipt_hash: str,
                       stop_tokens: list = None,
                       resume_receipts: list = None,
                       stop_token_signing_key=None,
                       resume_signing_key=None) -> dict:
    """Judge whether a sealed plan may execute RIGHT NOW; return a sealed
    guard receipt with ``cleared`` and classified problems. Never executes."""
    problems = list(verify_execution_plan(root, plan, intent, gate_result,
                                          check_preconditions=True))

    digest = intent_digest(intent)
    if (isinstance(gate_result, dict) and verify_gate_result_seal(gate_result)
            and gate_result.get("intent_digest") != digest):
        problems.append("gate result authorizes a different intent")

    gate_anchor = (gate_result or {}).get("state_receipt_hash")
    if gate_anchor != current_state_receipt_hash:
        problems.append(
            "authority expired: gate anchored to state receipt "
            f"{str(gate_anchor)[:16]}… != current "
            f"{str(current_state_receipt_hash)[:16]}… (state drift revokes "
            "plan authority)")

    blocking = blocking_stops(intent, stop_tokens or [], resume_receipts or [],
                              stop_token_signing_key, resume_signing_key)
    for item in blocking:
        problems.append(f"stopped: token {item['token_id']} ({item['reason']}) "
                        "blocks this scope at execution time")

    problems = sorted(set(problems))
    return _seal({
        "schema": SCHEMA_ID,
        "plan_sha256": plan.get("plan_sha256"),
        "gate_result_sha256": (gate_result or {}).get("result_sha256"),
        "intent_digest": digest,
        "state_receipt_hash": current_state_receipt_hash,
        "blocking_stops": blocking,
        "problems": problems,
        "cleared": not problems,
    })


if __name__ == "__main__":
    print("library module — guard_side_effects(root, intent, gate_result, "
          "plan, state_receipt_hash, stop_tokens, resume_receipts)")
    sys.exit(2)
