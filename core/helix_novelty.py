#!/usr/bin/env python3
"""Novelty reduction receipts and aggregation for the HELIX Truth Plane.

Policy source of truth: docs/HOLDOUT-POLICY.md ("novelty 후보는 구현 후 기존
machine으로 환원됐는지 기록", "false-CONDENSE count와 estimated implementation
cost 공개") and schemas/helix-reduction-receipt.schema.json. A novelty claim is
a sealed ``PREDICT`` whose action is ``CONDENSE`` or ``DEFER`` — an assertion
that no existing machine covers the candidate. This module makes that
assertion falsifiable: after the oracle reveal, an implementation experiment
either confirms the novel machine or reduces it to existing machines
(false-CONDENSE, wasted cost).

The reduction receipt extends the append-only chain

    cohort commitment -> prediction seal -> reveal -> reduction

so a reduction verdict cannot exist without a completed blind trial behind it.
The implementation experiment itself is external evidence injected by path and
hash; this module only verifies, seals, and aggregates deterministically.
``not_implemented`` claims are never counted as confirmed novelty.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import json
import os
import sys

try:  # package import (python -m core.helix_novelty) or library use
    from .helix_holdout import POLICY_VERSION, cohort_commitment
    from .helix_prediction import (seal_trial_receipt, verify_receipt_chain,
                                   verify_trial_receipt_seal)
    from .helix_schema import validate_against_schema, schema_path
    from .helix_state_receipt import sha256_file
except ImportError:  # direct script run: python core/helix_novelty.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import POLICY_VERSION, cohort_commitment
    from core.helix_prediction import (seal_trial_receipt, verify_receipt_chain,
                                       verify_trial_receipt_seal)
    from core.helix_schema import validate_against_schema, schema_path
    from core.helix_state_receipt import sha256_file

SCHEMA_NAME = "helix-reduction-receipt"
SCHEMA_ID = "helix-reduction-receipt/1.0"
NOVELTY_ACTIONS = ("CONDENSE", "DEFER")
REDUCTION_VERDICTS = ("novel_confirmed", "reduced_to_existing", "not_implemented")
NOT_IMPLEMENTED = {"implemented": False, "estimated_cost_units": 0}


def is_novelty_claim(prediction_body: dict) -> bool:
    return (prediction_body.get("outcome") == "PREDICT"
            and prediction_body.get("action") in NOVELTY_ACTIONS)


def _validate_implementation(root: str, implementation: dict) -> dict:
    """Normalize injected implementation evidence, hashing real files."""
    implemented = implementation.get("implemented")
    if not isinstance(implemented, bool):
        raise ValueError("implementation.implemented must be a boolean")
    cost = implementation.get("estimated_cost_units")
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
        raise ValueError("estimated_cost_units must be a non-negative number")
    if not implemented:
        for key in ("evidence_path", "reduced_to_existing", "reduced_to"):
            if implementation.get(key) is not None:
                raise ValueError(f"not-implemented claim must not carry {key}")
        return {"implemented": False, "evidence_path": None, "evidence_sha256": None,
                "estimated_cost_units": cost, "reduced_to_existing": None,
                "reduced_to": None}

    evidence_path = implementation.get("evidence_path")
    if not isinstance(evidence_path, str) or not evidence_path:
        raise ValueError("implemented claim requires evidence_path")
    full = evidence_path if os.path.isabs(evidence_path) else os.path.join(root, evidence_path)
    if not os.path.isfile(full):
        raise ValueError(f"implementation evidence missing: {evidence_path}")
    reduced = implementation.get("reduced_to_existing")
    if not isinstance(reduced, bool):
        raise ValueError("implemented claim requires reduced_to_existing boolean")
    reduced_to = implementation.get("reduced_to")
    if reduced:
        if (not isinstance(reduced_to, list) or not reduced_to
                or not all(isinstance(m, str) and m for m in reduced_to)):
            raise ValueError("reduction requires the existing machines it reduced to")
    elif reduced_to is not None:
        raise ValueError("confirmed novelty must not name reduced_to machines")
    return {"implemented": True, "evidence_path": evidence_path,
            "evidence_sha256": sha256_file(full), "estimated_cost_units": cost,
            "reduced_to_existing": reduced, "reduced_to": reduced_to}


def build_reduction_receipt(root: str, registry: dict, prediction_receipt: dict,
                            reveal_receipt: dict, implementation: dict) -> dict:
    """Seal one post-implementation reduction verdict for a novelty claim.

    Refuses: an incomplete or broken blind-trial chain (reduction requires a
    revealed oracle), a non-novelty prediction, and malformed or unhashable
    implementation evidence.
    """
    if reveal_receipt is None:
        raise ValueError("reduction before oracle reveal is forbidden")
    problems = verify_receipt_chain(root, registry, prediction_receipt, reveal_receipt)
    if problems:
        raise ValueError(f"blind-trial chain is not intact: {problems[0]}")
    body = prediction_receipt["prediction"]
    cid = prediction_receipt["candidate_id"]
    if not is_novelty_claim(body):
        raise ValueError(f"{cid}: prediction {body.get('action')!r} is not a "
                         "novelty claim (CONDENSE/DEFER)")
    normalized = _validate_implementation(root, implementation)
    if not normalized["implemented"]:
        verdict = "not_implemented"
    elif normalized["reduced_to_existing"]:
        verdict = "reduced_to_existing"
    else:
        verdict = "novel_confirmed"
    return seal_trial_receipt({
        "schema": SCHEMA_ID,
        "policy_version": POLICY_VERSION,
        "cohort_id": registry["cohort"]["cohort_id"],
        "cohort_commitment_sha256": registry["cohort"]["commitment_sha256"],
        "candidate_id": cid,
        "parent_receipt_sha256": reveal_receipt["receipt_sha256"],
        "novelty_claim": {"action": body["action"],
                          "machines": sorted(body["machines"])},
        "implementation": normalized,
        "verdict": verdict,
    })


def _reduction_problems(root: str, registry: dict, chain: dict,
                        receipt: dict) -> list:
    """Re-verify one reduction receipt against the sealed chain and evidence."""
    cid = receipt.get("candidate_id")
    problems = [f"{cid}: schema: {p}" for p in validate_against_schema(
        receipt, schema_path(root, SCHEMA_NAME))]
    if problems:
        return problems
    if not verify_trial_receipt_seal(receipt):
        return [f"{cid}: reduction receipt seal is broken"]
    if receipt["cohort_commitment_sha256"] != registry["cohort"]["commitment_sha256"]:
        problems.append(f"{cid}: reduction chained to a different commitment")
    reveal = chain.get("reveal") or {}
    if receipt["parent_receipt_sha256"] != reveal.get("receipt_sha256"):
        problems.append(f"{cid}: reduction is not chained to the reveal receipt")
    body = (chain.get("prediction") or {}).get("prediction") or {}
    claim = receipt["novelty_claim"]
    if (claim["action"] != body.get("action")
            or claim["machines"] != sorted(body.get("machines") or [])):
        problems.append(f"{cid}: reduction claim differs from the sealed prediction")
    implementation = receipt["implementation"]
    if implementation["implemented"]:
        evidence_path = implementation["evidence_path"]
        full = evidence_path if os.path.isabs(evidence_path) else os.path.join(root, evidence_path)
        if not os.path.isfile(full):
            problems.append(f"{cid}: implementation evidence missing: {evidence_path}")
        elif sha256_file(full) != implementation["evidence_sha256"]:
            problems.append(f"{cid}: implementation evidence hash mismatch")
    return problems


def aggregate_novelty(root: str, registry: dict, chains: dict,
                      reduction_receipts: dict) -> dict:
    """Deterministic novelty section: false-CONDENSE count, cost, and precision.

    Claims come from intact blind-trial chains whose sealed prediction asserts
    CONDENSE/DEFER. ``novelty_precision_implemented`` divides only resolved
    claims; unresolved claims (not_implemented/untracked) are published, and
    ``novelty_yield`` charges them against the claim total so an unimplemented
    claim can never inflate the metric.
    """
    if cohort_commitment(registry) != registry["cohort"]["commitment_sha256"]:
        raise ValueError("cohort commitment mismatch: registry was modified after lock")
    counts = {"claims": 0, "novel_confirmed": 0, "false_condense": 0,
              "not_implemented": 0, "untracked": 0, "protocol_violation": 0}
    total_cost = 0
    false_condense_cost = 0
    rows = []
    for cid in sorted(chains):
        chain = chains[cid]
        prediction_receipt = chain.get("prediction")
        if not prediction_receipt:
            continue
        if verify_receipt_chain(root, registry, prediction_receipt,
                                chain.get("reveal")):
            continue  # broken chains are already protocol violations in scoring
        body = prediction_receipt["prediction"]
        if not is_novelty_claim(body):
            continue
        counts["claims"] += 1
        receipt = reduction_receipts.get(cid)
        if receipt is None:
            counts["untracked"] += 1
            rows.append({"candidate_id": cid, "claim": body["action"],
                         "verdict": "untracked"})
            continue
        problems = _reduction_problems(root, registry, chain, receipt)
        if problems:
            counts["protocol_violation"] += 1
            rows.append({"candidate_id": cid, "claim": body["action"],
                         "verdict": "protocol_violation", "detail": problems})
            continue
        verdict = receipt["verdict"]
        cost = receipt["implementation"]["estimated_cost_units"]
        total_cost += cost
        if verdict == "novel_confirmed":
            counts["novel_confirmed"] += 1
        elif verdict == "reduced_to_existing":
            counts["false_condense"] += 1
            false_condense_cost += cost
        else:
            counts["not_implemented"] += 1
        rows.append({"candidate_id": cid, "claim": body["action"],
                     "verdict": verdict, "estimated_cost_units": cost})

    resolved = counts["novel_confirmed"] + counts["false_condense"]
    return {
        "counts": counts,
        "costs": {"total_estimated_cost_units": total_cost,
                  "false_condense_cost_units": false_condense_cost},
        "novelty_precision_implemented": (
            counts["novel_confirmed"] / resolved if resolved else None),
        "novelty_yield": (
            counts["novel_confirmed"] / counts["claims"] if counts["claims"] else None),
        "rows": rows,
    }


if __name__ == "__main__":
    print("library module — use scripts/evaluate/blind_machine_trial.py "
          "or core/helix_prediction.py for CLI entry points")
    sys.exit(2)
