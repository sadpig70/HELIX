#!/usr/bin/env python3
"""Contestability for HELIX Constitution gate decisions (T2 governance).

Policy source of truth: .pgf/DESIGN-HELIXDirection.md (Contestability:
"replay, appeal, override reason") and the T2 gate rules "30 actions replay"
and "reason 없는 override=0".

Three receipts, one invariant — the original GateResult is immutable:

- replay:   re-evaluate a stored GateResult from its own recorded inputs and
            require the fresh sealed result to match bit-for-bit. Any
            divergence is classified, never averaged away.
- appeal:   a sealed objection chained to the result's seal. An appeal never
            changes the decision — re-judging is a new gate run.
- override: the ONLY way a human reverses a decision. It is a separate sealed
            receipt chained to the original result, requires a non-empty
            reason, a human overrider, a state-receipt anchor, and a decision
            that actually differs. A reason-less override cannot exist.

``effective_decision`` folds valid overrides over the original result:
invalid overrides (broken seal, wrong chain, non-human) are reported and
ignored; CONFLICTING valid overrides fail closed to DENY.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_contestability) or library use
    from .helix_authorization import (DECISIONS, authorize,
                                      verify_gate_result_seal)
    from .helix_constitution import intent_digest
    from .helix_holdout import canonical_json_bytes
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_authorization import (DECISIONS, authorize,
                                          verify_gate_result_seal)
    from core.helix_constitution import intent_digest
    from core.helix_holdout import canonical_json_bytes

APPEAL_SCHEMA_ID = "helix-appeal-receipt/1.0"
OVERRIDE_SCHEMA_ID = "helix-override-receipt/1.0"


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


def verify_appeal_seal(receipt: dict) -> bool:
    return _seal_ok(receipt, "receipt_sha256")


def verify_override_seal(receipt: dict) -> bool:
    return _seal_ok(receipt, "receipt_sha256")


def replay_gate_result(root: str, stored_result: dict, intent: dict,
                       evidence_manifest, approvals: list,
                       state_receipt_hash: str, stop_tokens: list = None,
                       resume_receipts: list = None) -> dict:
    """Re-run the gate on the recorded inputs and compare seal-for-seal.

    Returns {replayed, stored_result_sha256, fresh_result_sha256, problems}.
    Problems are classified: broken stored seal, inputs that are not the
    recorded ones, and any field divergence between stored and fresh.
    """
    problems = []
    if not verify_gate_result_seal(stored_result):
        problems.append("stored gate result seal is broken")
    if stored_result.get("intent_digest") != intent_digest(intent):
        problems.append("replay inputs differ: intent is not the recorded one")
    manifest_seal = (evidence_manifest or {}).get("manifest_sha256")
    if stored_result.get("evidence_manifest_sha256") != manifest_seal:
        problems.append("replay inputs differ: evidence manifest is not the "
                        "recorded one")
    if stored_result.get("state_receipt_hash") != state_receipt_hash:
        problems.append("replay inputs differ: state receipt anchor is not "
                        "the recorded one")

    fresh = authorize(root, intent, evidence_manifest, approvals,
                      state_receipt_hash, stop_tokens=stop_tokens,
                      resume_receipts=resume_receipts)
    if fresh["result_sha256"] != stored_result.get("result_sha256"):
        for key in ("decision", "risk_class", "reasons", "valid_approvers",
                    "policy_version"):
            if fresh.get(key) != stored_result.get(key):
                problems.append(
                    f"replay divergence: {key} stored="
                    f"{stored_result.get(key)!r} fresh={fresh.get(key)!r}")
        problems.append("replay divergence: sealed results differ")
    return {
        "replayed": not problems,
        "stored_result_sha256": stored_result.get("result_sha256"),
        "fresh_result_sha256": fresh["result_sha256"],
        "problems": sorted(set(problems)),
    }


def file_appeal(result: dict, appellant: dict, reason: str) -> dict:
    """Record a sealed objection chained to a gate result. Changes nothing."""
    if not verify_gate_result_seal(result):
        raise ValueError("cannot appeal a tampered gate result; restore the "
                         "sealed original first")
    if not (appellant.get("id") or "").strip():
        raise ValueError("appellant.id must be non-empty")
    if not (reason or "").strip():
        raise ValueError("an appeal without a reason is not contestable")
    return _seal({
        "schema": APPEAL_SCHEMA_ID,
        "gate_result_sha256": result["result_sha256"],
        "contested_decision": result["decision"],
        "appellant": {"kind": appellant.get("kind", "ai"),
                      "id": appellant["id"]},
        "reason": reason,
    }, "receipt_sha256")


def file_override(result: dict, overrider: dict, reason: str,
                  new_decision: str, state_receipt_hash: str) -> dict:
    """Seal a human reversal of one gate decision. The original stays intact."""
    if not verify_gate_result_seal(result):
        raise ValueError("cannot override a tampered gate result; restore "
                         "the sealed original first")
    if overrider.get("kind") != "human":
        raise ValueError("only a human can override a gate decision")
    if not (overrider.get("id") or "").strip():
        raise ValueError("overrider.id must be non-empty")
    if not (reason or "").strip():
        raise ValueError("a reason-less override cannot exist")
    if new_decision not in DECISIONS:
        raise ValueError(f"new_decision must be one of {DECISIONS}")
    if new_decision == result["decision"]:
        raise ValueError("override must change the decision; re-affirming is "
                         "not an override")
    if not (state_receipt_hash or "").strip():
        raise ValueError("override requires a state-receipt anchor")
    return _seal({
        "schema": OVERRIDE_SCHEMA_ID,
        "gate_result_sha256": result["result_sha256"],
        "original_decision": result["decision"],
        "new_decision": new_decision,
        "overrider": {"kind": "human", "id": overrider["id"]},
        "reason": reason,
        "anchor": {"state_receipt_hash": state_receipt_hash},
    }, "receipt_sha256")


def _override_valid(result: dict, receipt: dict) -> bool:
    return (verify_override_seal(receipt)
            and receipt.get("gate_result_sha256") == result.get("result_sha256")
            and receipt.get("overrider", {}).get("kind") == "human"
            and bool((receipt.get("overrider", {}).get("id") or "").strip())
            and bool((receipt.get("reason") or "").strip())
            and receipt.get("new_decision") in DECISIONS
            and receipt.get("new_decision") != result.get("decision"))


def effective_decision(result: dict, overrides: list) -> dict:
    """Fold overrides over one immutable gate result, fail-closed.

    - no valid override: the gate decision stands;
    - exactly one valid override: its decision applies;
    - conflicting valid overrides: DENY (never guess between humans);
    - invalid overrides are reported as problems and apply nothing.
    """
    problems = []
    if not verify_gate_result_seal(result):
        return {"decision": "DENY", "source": "invalid_result",
                "problems": ["gate result seal is broken; fail closed"]}
    valid = []
    for index, receipt in enumerate(overrides or []):
        if _override_valid(result, receipt):
            valid.append(receipt)
        else:
            problems.append(f"override[{index}] is invalid and applies nothing")
    decisions = sorted({receipt["new_decision"] for receipt in valid})
    if not valid:
        return {"decision": result["decision"], "source": "gate",
                "problems": sorted(problems)}
    if len(decisions) > 1:
        problems.append(f"conflicting overrides {decisions}; failing closed")
        return {"decision": "DENY", "source": "conflict",
                "problems": sorted(problems)}
    return {"decision": decisions[0], "source": "override",
            "problems": sorted(problems)}


if __name__ == "__main__":
    print("library module — replay_gate_result / file_appeal / file_override "
          "/ effective_decision")
    sys.exit(2)
