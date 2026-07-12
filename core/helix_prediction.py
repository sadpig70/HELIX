#!/usr/bin/env python3
"""Sealed blind-prediction and oracle-reveal receipts for the HELIX Truth Plane.

Policy source of truth: docs/HOLDOUT-POLICY.md (Fixed Order, Reveal and Audit)
and schemas/helix-trial-receipt.schema.json. This module enforces the order

    cohort commitment lock -> prediction receipt seal -> reveal approval

with an append-only hash chain: a prediction receipt's parent is the cohort
commitment, a reveal receipt's parent is the sealed prediction receipt. Order
is proven by parent hashes, never by wall clock. ``ABSTAIN`` and
``MISSING_ARTIFACT`` are explicit sealed outcomes (success credit 0), not
silent gaps. A reveal is impossible without a sealed prediction hash, the
required approver receipts, and an oracle whose bytes still match the locked
commitment.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import json
import os
import sys

try:  # package import (python -m core.helix_prediction) or library use
    from .helix_holdout import (POLICY_VERSION, canonical_json_bytes,
                                cohort_commitment, locked_eligible_candidates)
    from .helix_schema import validate_against_schema, schema_path
    from .helix_state_receipt import sha256_file
except ImportError:  # direct script run: python core/helix_prediction.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import (POLICY_VERSION, canonical_json_bytes,
                                    cohort_commitment, locked_eligible_candidates)
    from core.helix_schema import validate_against_schema, schema_path
    from core.helix_state_receipt import sha256_file

SCHEMA_NAME = "helix-trial-receipt"
SCHEMA_ID = "helix-trial-receipt/1.0"
PREDICTION_OUTCOMES = ("PREDICT", "ABSTAIN", "MISSING_ARTIFACT")
NO_LABEL_OUTCOMES = ("ABSTAIN", "MISSING_ARTIFACT")


def seal_trial_receipt(receipt: dict) -> dict:
    """Return a copy sealed by SHA256 over canonical JSON minus the seal itself."""
    sealed = dict(receipt)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_trial_receipt_seal(receipt: dict) -> bool:
    expected = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _find_candidate(registry: dict, candidate_id: str) -> dict:
    for candidate in registry["candidates"]:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise ValueError(f"unknown candidate: {candidate_id}")


def _require_locked_commitment(registry: dict) -> str:
    cohort = registry["cohort"]
    if cohort["status"] not in ("locked", "scored"):
        raise ValueError("cohort is not locked; predictions require a sealed selection")
    expected = cohort["commitment_sha256"]
    if cohort_commitment(registry) != expected:
        raise ValueError("cohort commitment mismatch: registry was modified after lock")
    return expected


def _validate_prediction_body(prediction: dict) -> dict:
    outcome = prediction.get("outcome")
    if outcome not in PREDICTION_OUTCOMES:
        raise ValueError(f"invalid prediction outcome: {outcome!r}")
    action = prediction.get("action")
    machines = prediction.get("machines")
    if outcome in NO_LABEL_OUTCOMES:
        if action is not None or machines is not None:
            raise ValueError(f"{outcome} must not carry action or machines")
    else:
        if not isinstance(action, str) or not action:
            raise ValueError("PREDICT requires a non-empty action")
        if not isinstance(machines, list) or not all(
                isinstance(m, str) and m for m in machines):
            raise ValueError("PREDICT requires machines as a list of names")
    return {"outcome": outcome, "action": action, "machines": machines}


def build_prediction_receipt(root: str, registry: dict, candidate_id: str,
                             prediction: dict) -> dict:
    """Seal a prediction for one locked candidate before any oracle reveal.

    Refuses: unlocked/tampered cohort, excluded candidate, already-sealed
    prediction, revealed oracle (blindness is gone), label-carrying ABSTAIN,
    and a candidate view whose bytes drifted from the locked hash.
    """
    commitment = _require_locked_commitment(registry)
    candidate = _find_candidate(registry, candidate_id)
    if candidate["status"] == "excluded":
        raise ValueError(f"{candidate_id}: excluded candidates cannot be predicted")
    if candidate["prediction_receipt"]["status"] != "absent":
        raise ValueError(f"{candidate_id}: prediction is already sealed")
    if (candidate["oracle_commitment"]["access"] != "sealed"
            or candidate["reveal"]["status"] == "revealed"):
        raise ValueError(f"{candidate_id}: oracle already revealed; "
                         "a prediction now would not be blind")
    body = _validate_prediction_body(prediction)

    view = candidate["candidate_view"]
    if body["outcome"] != "MISSING_ARTIFACT":
        view_path = view["path"]
        full = view_path if os.path.isabs(view_path) else os.path.join(root, view_path)
        if not os.path.isfile(full):
            raise ValueError(f"{candidate_id}: candidate view missing; "
                             "seal MISSING_ARTIFACT instead")
        if sha256_file(full) != view["sha256"]:
            raise ValueError(f"{candidate_id}: candidate view drifted from the lock")

    return seal_trial_receipt({
        "schema": SCHEMA_ID,
        "receipt_kind": "prediction",
        "policy_version": POLICY_VERSION,
        "cohort_id": registry["cohort"]["cohort_id"],
        "cohort_commitment_sha256": commitment,
        "candidate_id": candidate_id,
        "parent_receipt_sha256": commitment,
        "prediction": {
            "candidate_view_sha256": view["sha256"],
            "predictor_role": "predictor",
            "outcome": body["outcome"],
            "action": body["action"],
            "machines": body["machines"],
        },
        "reveal": None,
    })


def apply_prediction_receipt(registry: dict, receipt: dict,
                             receipt_path: str) -> dict:
    """Record a sealed prediction receipt in the registry (lifecycle update)."""
    if receipt.get("receipt_kind") != "prediction" or not verify_trial_receipt_seal(receipt):
        raise ValueError("not a sealed prediction receipt")
    commitment = _require_locked_commitment(registry)
    if receipt["cohort_commitment_sha256"] != commitment:
        raise ValueError("receipt is chained to a different cohort commitment")
    updated = json.loads(json.dumps(registry))
    candidate = _find_candidate(updated, receipt["candidate_id"])
    if candidate["prediction_receipt"]["status"] != "absent":
        raise ValueError(f"{receipt['candidate_id']}: prediction is already sealed")
    candidate["prediction_receipt"] = {
        "status": "sealed",
        "path": receipt_path,
        "sha256": receipt["receipt_sha256"],
        "predictor_role": "predictor",
    }
    return updated


def build_reveal_receipt(root: str, registry: dict, candidate_id: str,
                         approvals: list) -> dict:
    """Approve an oracle reveal for a candidate whose prediction is sealed.

    Refuses: absent prediction seal (reveal-before-prediction), missing or
    duplicate approvers, roles outside reveal_authority, and an oracle file
    whose bytes no longer match the locked commitment.
    """
    commitment = _require_locked_commitment(registry)
    candidate = _find_candidate(registry, candidate_id)
    prediction = candidate["prediction_receipt"]
    if prediction["status"] != "sealed" or not prediction["sha256"]:
        raise ValueError(f"{candidate_id}: reveal before sealed prediction is forbidden")

    authority = registry["reveal_authority"]
    allowed_roles = set(authority["allowed_roles"])
    seen_ids = set()
    for approval in approvals:
        approver_id = approval.get("approver_id")
        if not isinstance(approver_id, str) or not approver_id:
            raise ValueError("approval without approver_id")
        if approver_id in seen_ids:
            raise ValueError(f"duplicate approver: {approver_id}")
        seen_ids.add(approver_id)
        if approval.get("role") not in allowed_roles:
            raise ValueError(f"{approver_id}: role {approval.get('role')!r} "
                             "cannot approve a reveal")
    if len(seen_ids) < authority["required_approvals"]:
        raise ValueError(f"{candidate_id}: insufficient reveal approvals "
                         f"({len(seen_ids)} < {authority['required_approvals']})")

    oracle = candidate["oracle_commitment"]
    oracle_path = oracle["path"]
    full = oracle_path if os.path.isabs(oracle_path) else os.path.join(root, oracle_path)
    if not os.path.isfile(full):
        raise ValueError(f"{candidate_id}: oracle artifact missing; reveal denied")
    if sha256_file(full) != oracle["sha256"]:
        raise ValueError(f"{candidate_id}: oracle does not match the sealed "
                         "commitment; reveal denied")

    return seal_trial_receipt({
        "schema": SCHEMA_ID,
        "receipt_kind": "reveal",
        "policy_version": POLICY_VERSION,
        "cohort_id": registry["cohort"]["cohort_id"],
        "cohort_commitment_sha256": commitment,
        "candidate_id": candidate_id,
        "parent_receipt_sha256": prediction["sha256"],
        "prediction": None,
        "reveal": {
            "prediction_receipt_sha256": prediction["sha256"],
            "oracle_commitment_sha256": oracle["sha256"],
            "approvals": [{"approver_id": a["approver_id"], "role": a["role"]}
                          for a in approvals],
        },
    })


def apply_reveal_receipt(registry: dict, receipt: dict) -> dict:
    """Record an approved reveal in the registry and open the oracle."""
    if receipt.get("receipt_kind") != "reveal" or not verify_trial_receipt_seal(receipt):
        raise ValueError("not a sealed reveal receipt")
    commitment = _require_locked_commitment(registry)
    if receipt["cohort_commitment_sha256"] != commitment:
        raise ValueError("receipt is chained to a different cohort commitment")
    updated = json.loads(json.dumps(registry))
    candidate = _find_candidate(updated, receipt["candidate_id"])
    prediction = candidate["prediction_receipt"]
    if (prediction["status"] != "sealed"
            or prediction["sha256"] != receipt["reveal"]["prediction_receipt_sha256"]):
        raise ValueError("reveal receipt is not chained to the sealed prediction")
    candidate["reveal"] = {
        "status": "revealed",
        "authorized_by": sorted(a["approver_id"]
                                for a in receipt["reveal"]["approvals"]),
        "receipt_sha256": receipt["receipt_sha256"],
    }
    candidate["oracle_commitment"]["access"] = "revealed"
    return updated


def verify_receipt_chain(root: str, registry: dict, prediction_receipt: dict,
                         reveal_receipt: dict = None) -> list:
    """Independently re-verify one candidate's receipt chain against the registry."""
    problems = [f"prediction schema: {p}" for p in validate_against_schema(
        prediction_receipt, schema_path(root, SCHEMA_NAME))]
    if reveal_receipt is not None:
        problems += [f"reveal schema: {p}" for p in validate_against_schema(
            reveal_receipt, schema_path(root, SCHEMA_NAME))]
    if problems:
        return sorted(problems)

    cohort = registry["cohort"]
    commitment = cohort["commitment_sha256"]
    if cohort_commitment(registry) != commitment:
        problems.append("registry: cohort commitment mismatch")

    cid = prediction_receipt["candidate_id"]
    try:
        candidate = _find_candidate(registry, cid)
    except ValueError:
        return sorted(problems + [f"{cid}: not in the locked registry"])

    if not verify_trial_receipt_seal(prediction_receipt):
        problems.append(f"{cid}: prediction receipt seal is broken")
    if prediction_receipt["receipt_kind"] != "prediction" or prediction_receipt["prediction"] is None:
        problems.append(f"{cid}: prediction receipt has no prediction body")
    else:
        body = prediction_receipt["prediction"]
        if prediction_receipt["cohort_commitment_sha256"] != commitment:
            problems.append(f"{cid}: prediction chained to a different commitment")
        if prediction_receipt["parent_receipt_sha256"] != commitment:
            problems.append(f"{cid}: prediction parent is not the cohort commitment")
        if body["candidate_view_sha256"] != candidate["candidate_view"]["sha256"]:
            problems.append(f"{cid}: prediction was made on a different candidate view")
        if body["outcome"] in NO_LABEL_OUTCOMES and (
                body["action"] is not None or body["machines"] is not None):
            problems.append(f"{cid}: {body['outcome']} carries labels")
        recorded = candidate["prediction_receipt"]
        if recorded["status"] == "sealed" and (
                recorded["sha256"] != prediction_receipt.get("receipt_sha256")):
            problems.append(f"{cid}: registry records a different sealed prediction")

    if reveal_receipt is None:
        if candidate["reveal"]["status"] == "revealed":
            problems.append(f"{cid}: registry is revealed but no reveal receipt given")
        return sorted(problems)

    if not verify_trial_receipt_seal(reveal_receipt):
        problems.append(f"{cid}: reveal receipt seal is broken")
    if reveal_receipt["receipt_kind"] != "reveal" or reveal_receipt["reveal"] is None:
        problems.append(f"{cid}: reveal receipt has no reveal body")
        return sorted(problems)
    reveal = reveal_receipt["reveal"]
    prediction_seal = prediction_receipt.get("receipt_sha256")
    if reveal_receipt["candidate_id"] != cid:
        problems.append(f"{cid}: reveal receipt names a different candidate")
    if reveal_receipt["cohort_commitment_sha256"] != commitment:
        problems.append(f"{cid}: reveal chained to a different commitment")
    if (reveal_receipt["parent_receipt_sha256"] != prediction_seal
            or reveal["prediction_receipt_sha256"] != prediction_seal):
        problems.append(f"{cid}: reveal is not chained to the sealed prediction")
    if reveal["oracle_commitment_sha256"] != candidate["oracle_commitment"]["sha256"]:
        problems.append(f"{cid}: reveal names a different oracle commitment")
    approvers = {a["approver_id"] for a in reveal["approvals"]}
    if len(approvers) < registry["reveal_authority"]["required_approvals"]:
        problems.append(f"{cid}: insufficient reveal approvals in receipt")
    recorded_reveal = candidate["reveal"]
    if recorded_reveal["status"] == "revealed" and (
            recorded_reveal["receipt_sha256"] != reveal_receipt.get("receipt_sha256")):
        problems.append(f"{cid}: registry records a different reveal receipt")
    return sorted(problems)


def _oracle_expected(root: str, candidate: dict):
    """Load a revealed oracle and re-verify its bytes against the commitment.

    Oracle contract: {"expected": {"action": str, "machines": [str, ...]}}.
    Returns (expected, None) or (None, reason).
    """
    path = candidate["oracle_commitment"]["path"]
    full = path if os.path.isabs(path) else os.path.join(root, path)
    if not os.path.isfile(full):
        return None, "oracle_missing"
    if sha256_file(full) != candidate["oracle_commitment"]["sha256"]:
        return None, "oracle_drifted_after_lock"
    with open(full, "r", encoding="utf-8") as f:
        expected = json.load(f).get("expected") or {}
    return {"action": expected.get("action"),
            "machines": sorted(expected.get("machines") or [])}, None


def score_cohort(root: str, registry: dict, chains: dict) -> dict:
    """Deterministically score sealed predictions against revealed oracles.

    ``chains`` maps candidate_id -> {"prediction": receipt, "reveal": receipt}.
    Credits follow docs/HOLDOUT-POLICY.md: only an exact action+machines match
    is success; wrong counts coverage only; ABSTAIN, MISSING_ARTIFACT, missing
    or unrevealed predictions, and protocol violations stay in the locked
    eligible denominator with zero credit. Candidates are never removed.
    macro-F1 is multi-label over machine ids across candidates whose oracle is
    verifiably revealed; non-predicting outcomes contribute false negatives.
    """
    eligible = locked_eligible_candidates(registry)
    counts = {"exact": 0, "wrong": 0, "abstain": 0, "missing_artifact": 0,
              "protocol_violation": 0, "missing_prediction": 0, "unrevealed": 0}
    rows = []
    oracle_labels = {}
    predicted_labels = {}
    for candidate in eligible:
        cid = candidate["candidate_id"]
        chain = chains.get(cid) or {}
        prediction_receipt = chain.get("prediction")
        reveal_receipt = chain.get("reveal")
        detail = None
        if not prediction_receipt:
            outcome = "missing_prediction"
        else:
            problems = verify_receipt_chain(root, registry,
                                            prediction_receipt, reveal_receipt)
            if problems:
                outcome, detail = "protocol_violation", problems
            else:
                body = prediction_receipt["prediction"]
                if body["outcome"] in NO_LABEL_OUTCOMES:
                    outcome = body["outcome"].lower()
                elif candidate["reveal"]["status"] != "revealed" or reveal_receipt is None:
                    outcome = "unrevealed"
                else:
                    expected, reason = _oracle_expected(root, candidate)
                    if expected is None:
                        outcome, detail = "protocol_violation", [f"{cid}: {reason}"]
                    else:
                        predicted = {"action": body["action"],
                                     "machines": sorted(body["machines"])}
                        outcome = "exact" if predicted == expected else "wrong"
                        detail = {"predicted": predicted, "expected": expected}
                        predicted_labels[cid] = set(predicted["machines"])
                if outcome != "protocol_violation" and candidate["reveal"]["status"] == "revealed":
                    expected, reason = _oracle_expected(root, candidate)
                    if expected is not None:
                        oracle_labels[cid] = set(expected["machines"])
        counts[outcome] += 1
        row = {"candidate_id": cid, "outcome": outcome}
        if detail is not None:
            row["detail"] = detail
        rows.append(row)

    classes = sorted(set().union(*oracle_labels.values(), *predicted_labels.values())
                     if oracle_labels or predicted_labels else set())
    f1_per_class = {}
    for cls in classes:
        tp = sum(1 for cid in oracle_labels
                 if cls in oracle_labels[cid] and cls in predicted_labels.get(cid, ()))
        fp = sum(1 for cid in oracle_labels
                 if cls not in oracle_labels[cid] and cls in predicted_labels.get(cid, ()))
        fn = sum(1 for cid in oracle_labels
                 if cls in oracle_labels[cid] and cls not in predicted_labels.get(cid, ()))
        f1_per_class[cls] = (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else 0.0

    denominator = len(eligible)
    scored = counts["exact"] + counts["wrong"]
    coverage = scored / denominator if denominator else 0.0
    macro_f1 = (sum(f1_per_class.values()) / len(f1_per_class)) if f1_per_class else 0.0
    scoring = registry["scoring"]
    return {
        "denominator": denominator,
        "counts": counts,
        "coverage": coverage,
        "success_rate": counts["exact"] / denominator if denominator else 0.0,
        "macro_f1": macro_f1,
        "f1_per_class": f1_per_class,
        "gates": {
            "minimum_coverage": scoring["minimum_coverage"],
            "coverage_pass": coverage >= scoring["minimum_coverage"],
            "minimum_macro_f1": scoring["minimum_macro_f1"],
            "macro_f1_pass": macro_f1 >= scoring["minimum_macro_f1"],
        },
        "rows": rows,
    }


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _main(argv) -> int:
    if len(argv) < 3:
        print("usage: python core/helix_prediction.py <registry.json> "
              "<prediction-receipt.json> [reveal-receipt.json] [root]")
        return 2
    registry = _load_json(argv[1])
    prediction_receipt = _load_json(argv[2])
    reveal_receipt = _load_json(argv[3]) if len(argv) > 3 else None
    root = os.path.abspath(argv[4] if len(argv) > 4 else ".")
    problems = verify_receipt_chain(root, registry, prediction_receipt, reveal_receipt)
    cid = prediction_receipt.get("candidate_id")
    print(f"=== HELIX trial receipt chain ({cid}) ===")
    print(f"  cohort commitment: {registry['cohort'].get('commitment_sha256')}")
    print(f"  prediction seal:   {prediction_receipt.get('receipt_sha256')}")
    if reveal_receipt is not None:
        print(f"  reveal seal:       {reveal_receipt.get('receipt_sha256')}")
    if problems:
        print("\nFAIL — problems:")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("\nPASS — receipt chain is sealed and consistent with the locked registry.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
