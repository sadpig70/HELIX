#!/usr/bin/env python3
"""Owned-stakes attestation — earning the ``real_owned_stakes`` provenance grade.

This is the top rung of the persona adoption trial's provenance ladder and the
ONLY grade that flips ``is_t4_utility`` true (see ``core/helix_adoption_trial``).
Because of that, an *asserted* (unbacked) ``real_owned_stakes`` claim would
fabricate a T4 utility signal — the highest-stakes forgery in the system. This
module makes the grade **earnable, not assertable**, the same way
``core/helix_fidelity.py`` did for ``fidelity_attested`` — but with a stricter
independence rule.

The independence rule is the crux, and it differs from fidelity on purpose:

  fidelity_attested : about the *authenticity of a reproduced judgment*. The
                      wedge author can validly attest whether an AI reproduced
                      HIS perspective, so dogfooding is allowed WITH a conflict
                      flag (weak-but-real).
  real_owned_stakes : about *utility under owned consequences*. If the party
                      judging utility is the party who owns the wedge, it is
                      self-dealing, not a market signal. So independence is HARD
                      here — an operator who is the wedge author is DISQUALIFIED,
                      not merely flagged.

Honest ceiling (unchanged): a single verified real_owned_stakes receipt is a
``utility_candidate``, NOT a T4 pass. The full T4 verdict still needs the
multi-participant pilot gate (``docs/PILOT-PROTOCOL.md``). This module verifies
one operator's owned-stakes evidence is real and independent; it does not, by
itself, declare T4 passed.

Deterministic, stdlib only: no clock, network, subprocess, randomness, or AI.
The module validates, seals, binds, and grades; it does not fetch external
ledgers (the ledger head hash is recorded and verified where the ledger is
present, like external anchoring).
"""

import hashlib
import os
import sys

try:
    from .helix_holdout import canonical_json_bytes
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import canonical_json_bytes

SCHEMA_OWNED = "helix-owned-stakes-attestation/1.0"

# Objective outcome keys that count as measurable (not self-reported sentiment).
OBJECTIVE_MEASURES = ("prevented_invalid", "admitted", "excluded",
                      "sandboxed", "quarantined")


def _seal(doc: dict, field: str) -> dict:
    sealed = dict(doc)
    sealed.pop(field, None)
    sealed[field] = hashlib.sha256(canonical_json_bytes(sealed)).hexdigest()
    return sealed


def _verify(doc: dict, field: str) -> bool:
    expected = doc.get(field)
    body = {k: v for k, v in doc.items() if k != field}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _is_hex64(s) -> bool:
    if not isinstance(s, str) or len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def attest_owned_stakes(operator: dict, wedge_author_id: str, real_work: dict,
                        outcomes: dict, stakes_owned: str) -> dict:
    """An independent operator attests running the wedge on real, owned work.

    operator    = {"id": <name>, "org": <org>} — independent of the wedge author.
    real_work   = {"ledger_ref": <label>, "ledger_head_sha256": <hex>,
                   "decision_count": <int>, "simulated": <bool, must be false>}
    outcomes    = objective measures (int counts) + {"replay_verified": True}.
    stakes_owned= a non-empty statement of the real consequence the operator bore.

    Independence is HARD: an operator equal to the wedge author is rejected
    (self-use is not a utility signal), in deliberate contrast to fidelity.
    """
    operator_id = (operator.get("id") if isinstance(operator, dict) else "") or ""
    if not operator_id.strip():
        raise ValueError("operator.id must be non-empty (a named party)")
    if not (wedge_author_id or "").strip():
        raise ValueError("wedge_author_id must be provided to enforce independence")
    if operator_id.strip() == wedge_author_id.strip():
        raise ValueError("operator must be independent of the wedge author "
                         "(dogfooding is not a utility signal for owned stakes)")
    if not isinstance(real_work, dict):
        raise ValueError("real_work must be a dict")
    if real_work.get("simulated"):
        raise ValueError("real_owned_stakes requires real work, not simulated")
    dc = real_work.get("decision_count")
    if not isinstance(dc, int) or dc <= 0:
        raise ValueError("real_work.decision_count must be a positive int "
                         "(real decisions were made)")
    if not _is_hex64(real_work.get("ledger_head_sha256")):
        raise ValueError("real_work.ledger_head_sha256 must bind to a real "
                         "ledger head (64-hex)")
    if not (real_work.get("ledger_ref") or "").strip():
        raise ValueError("real_work.ledger_ref must be non-empty")
    if not isinstance(outcomes, dict):
        raise ValueError("outcomes must be a dict of objective measures")
    if outcomes.get("replay_verified") is not True:
        raise ValueError("outcomes.replay_verified must be True — the real "
                         "decisions must be reproducible")
    measures = {k: v for k, v in outcomes.items() if k in OBJECTIVE_MEASURES}
    if not measures:
        raise ValueError("outcomes must contain at least one objective measure "
                         f"from {OBJECTIVE_MEASURES}, not only sentiment")
    for k, v in measures.items():
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"outcome {k} must be a non-negative int")
    if not (stakes_owned or "").strip():
        raise ValueError("stakes_owned must state the real consequence borne")
    return _seal({
        "schema": SCHEMA_OWNED,
        "operator": {"id": operator_id.strip(),
                     "org": (operator.get("org") or "").strip()},
        "wedge_author_id": wedge_author_id.strip(),
        "real_work": {
            "ledger_ref": real_work["ledger_ref"].strip(),
            "ledger_head_sha256": real_work["ledger_head_sha256"],
            "decision_count": dc,
            "simulated": False,
        },
        "outcomes": dict(outcomes),
        "stakes_owned": stakes_owned.strip(),
    }, "attestation_sha256")


def verify_owned_stakes_attestation(attestation: dict) -> bool:
    return _verify(attestation, "attestation_sha256")


def owned_stakes_grade(attestation: dict) -> str:
    """The grade earned. real_owned_stakes only when independent + real + objective.

    Returns "real_owned_stakes" when the attestation is seal-valid, the operator
    is independent of the wedge author, the work is real (not simulated) with a
    positive decision count bound to a ledger head, and the real decisions are
    replay-verified. Anything else earns "simulated_unverified".
    """
    if not verify_owned_stakes_attestation(attestation):
        return "simulated_unverified"
    op = attestation.get("operator", {}).get("id")
    author = attestation.get("wedge_author_id")
    if not op or not author or op == author:
        return "simulated_unverified"
    rw = attestation.get("real_work", {})
    if rw.get("simulated") or not isinstance(rw.get("decision_count"), int) \
            or rw.get("decision_count", 0) <= 0:
        return "simulated_unverified"
    if not _is_hex64(rw.get("ledger_head_sha256")):
        return "simulated_unverified"
    if attestation.get("outcomes", {}).get("replay_verified") is not True:
        return "simulated_unverified"
    return "real_owned_stakes"


def earn_owned_provenance(attestation: dict) -> dict:
    """Build a provenance dict with a DERIVED grade + real stakes.

    Grade is computed from the attestation, never asserted. Unlike fidelity,
    stakes are "real" here — this is the rung where consequences are genuinely
    owned. Carries attestation_sha256 so aggregate_adoption can verify the claim.
    """
    grade = owned_stakes_grade(attestation)
    return {
        "grade": grade,
        "attested_by": attestation.get("operator", {}).get("id")
                       if grade == "real_owned_stakes" else None,
        "stakes": "real" if grade == "real_owned_stakes" else "simulated",
        "attestation_sha256": attestation.get("attestation_sha256"),
        "operator_org": attestation.get("operator", {}).get("org"),
    }


if __name__ == "__main__":
    print("library module — attest_owned_stakes / owned_stakes_grade / "
          "earn_owned_provenance")
    sys.exit(2)
