#!/usr/bin/env python3
"""Persona conditional-adoption trial for the wedge (methodology from dialogue).

This module operationalizes a conclusion reached in a methodology dialogue,
recorded honestly in code so it cannot drift into over-claiming:

A non-deterministic AI persona can genuinely evaluate the wedge — it can
ACCEPT or REJECT it — provided (a) its interest function is specified
independently of the wedge (never "adopt X"), and (b) the persona reasons
non-deterministically about whether the wedge serves that interest. That
recovers the counterfactual ("a bad wedge gets rejected") which a
deterministic persona destroys.

But what such a trial measures is bounded by ONE axis that neither substrate
(human/AI) nor metaphysics settles: causal independence / provenance. The
single remaining question is whether the adoption signal's evidence comes
from inside the system being judged or from outside it. So every adoption
receipt here carries an explicit PROVENANCE grade:

    simulated_unverified  : synthetic persona, no real-person backing, stakes
                            are simulated. -> conditional-adoption signal ONLY;
                            NOT a T4 utility verdict.
    fidelity_attested     : a named real person attests the persona faithfully
                            reproduces their perspective. -> stronger, but
                            stakes still simulated unless owned externally.
    real_owned_stakes     : an independent party runs it on real work with
                            objective outcomes. -> genuine utility signal.

The trial never upgrades its own grade. It records what is true and leaves
the ceiling explicit. A rejection is a real defect signal (the point of the
counterfactual); an acceptance under simulated_unverified provenance is NOT
evidence of market utility.

Deterministic given its inputs; the persona reasoning happens in isolated
subagents outside this module. Here we only validate, seal, and aggregate.
Stdlib only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:
    from .helix_holdout import canonical_json_bytes
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import canonical_json_bytes

SCHEMA_ID = "helix-adoption-receipt/1.0"
DECISIONS = ("adopt", "reject", "conditional")
PROVENANCE_GRADES = ("simulated_unverified", "fidelity_attested",
                     "real_owned_stakes")
# Which grades may count as a utility (not just robustness) signal.
UTILITY_GRADES = ("real_owned_stakes",)

# Words that, if they appear in a persona's interest function, mean the
# interest was defined in terms of the wedge itself — destroying independence.
WEDGE_COUPLED_TERMS = ("wedge", "audit-handback", "admission gate", "helix")


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_adoption_seal(receipt: dict) -> bool:
    expected = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def validate_persona(persona: dict) -> list:
    """A persona must state a wedge-INDEPENDENT interest function.

    The whole point is that the interest is defined without reference to the
    wedge, so the adoption judgment is not circular. A persona whose interest
    mentions the wedge is rejected.
    """
    problems = []
    if not (persona.get("persona_id") or "").strip():
        problems.append("persona_id must be non-empty")
    interest = persona.get("interest_function")
    if not isinstance(interest, str) or not interest.strip():
        problems.append("interest_function must be a non-empty statement")
    else:
        low = interest.lower()
        for term in WEDGE_COUPLED_TERMS:
            if term in low:
                problems.append(
                    f"interest_function mentions '{term}' — it must be defined "
                    "independently of the wedge, or the adoption judgment is "
                    "circular (deterministic-persona trap)")
    if not isinstance(persona.get("constraints"), list):
        problems.append("constraints must be a list (may be empty)")
    return sorted(problems)


def build_adoption_receipt(persona: dict, judgment: dict,
                           provenance: dict) -> dict:
    """Seal one persona's non-deterministic adoption judgment of the wedge.

    judgment = {decision: adopt|reject|conditional, reasons: [...],
                defects_found: [...], conditions: [...]}
    provenance = {grade, attested_by, stakes} — graded honestly; the trial
    cannot invent a real person or real stakes it does not have.
    """
    persona_problems = validate_persona(persona)
    if persona_problems:
        raise ValueError(f"invalid persona: {persona_problems[0]}")
    decision = judgment.get("decision")
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    if not (judgment.get("reasons") or []):
        raise ValueError("an adoption judgment without reasons is not auditable")
    grade = provenance.get("grade")
    if grade not in PROVENANCE_GRADES:
        raise ValueError(f"provenance.grade must be one of {PROVENANCE_GRADES}")
    if grade != "simulated_unverified" and not (provenance.get("attested_by") or "").strip():
        raise ValueError(f"grade {grade} requires a named attester "
                         "(a real person or independent owner)")
    return _seal({
        "schema": SCHEMA_ID,
        "persona_id": persona["persona_id"],
        "interest_function": persona["interest_function"],
        "constraints": persona.get("constraints", []),
        "decision": decision,
        "reasons": list(judgment["reasons"]),
        "defects_found": list(judgment.get("defects_found", [])),
        "conditions": list(judgment.get("conditions", [])),
        "provenance": {
            "grade": grade,
            "attested_by": provenance.get("attested_by"),
            "stakes": provenance.get("stakes", "simulated"),
            # Binding fields (present when the grade was earned via
            # core.helix_fidelity.earn_provenance, absent for a bare assertion).
            # They let aggregate_adoption verify a fidelity_attested claim
            # against the actual attestation instead of trusting the label.
            "sample_sha256": provenance.get("sample_sha256"),
            "attestation_sha256": provenance.get("attestation_sha256"),
            "conflict_of_interest": provenance.get("conflict_of_interest"),
        },
    })


def _effective_grade(receipt: dict, attest_ctx: dict, problems: list,
                     index: int) -> str:
    """The grade a receipt actually earns once attestations are checked.

    Mirrors the wedge's evidence_required idiom: a non-simulated claim is only
    honored when a valid attestation bound to this receipt is present. An
    unbacked claim is downgraded to simulated_unverified and the downgrade is
    recorded, never hidden. Two claims are verifiable:

    - fidelity_attested : bound by reproduction-sample hash; verdict must be
      faithful (core.helix_fidelity).
    - real_owned_stakes : bound by attestation hash; the attestation must earn
      the grade — independent operator, real work, objective outcomes
      (core.helix_owned_stakes). This is the grade that flips is_t4_utility, so
      an unbacked one must never pass.
    """
    prov = receipt.get("provenance", {})
    grade = prov.get("grade")
    if attest_ctx is None or grade not in ("fidelity_attested",
                                           "real_owned_stakes"):
        return grade
    if grade == "fidelity_attested":
        from core.helix_fidelity import verify_attestation
        sample_hash = prov.get("sample_sha256")
        att = attest_ctx["by_sample"].get(sample_hash) if sample_hash else None
        if (att is not None and verify_attestation(att)
                and att.get("verdict") == "faithful"
                and att.get("sample_sha256") == sample_hash):
            return "fidelity_attested"
        problems.append(
            f"receipt[{index}] claims fidelity_attested but no valid faithful "
            "attestation is bound to its reproduction sample; downgraded to "
            "simulated_unverified")
        return "simulated_unverified"
    # grade == "real_owned_stakes"
    from core.helix_owned_stakes import owned_stakes_grade
    att_hash = prov.get("attestation_sha256")
    att = attest_ctx["by_hash"].get(att_hash) if att_hash else None
    if att is not None and owned_stakes_grade(att) == "real_owned_stakes":
        return "real_owned_stakes"
    problems.append(
        f"receipt[{index}] claims real_owned_stakes but no valid independent "
        "owned-stakes attestation is bound to it; downgraded to "
        "simulated_unverified (a bare label cannot fabricate a T4 utility signal)")
    return "simulated_unverified"


def aggregate_adoption(receipts: list, attestations: list = None) -> dict:
    """Summarize adoption receipts, keeping the provenance ceiling explicit.

    When ``attestations`` is provided, every non-simulated claim is verified
    against it — fidelity_attested by reproduction-sample hash (must be
    faithful), real_owned_stakes by attestation hash (must be an independent,
    real, objective owned-stakes attestation) — and downgraded if unbacked. When
    it is None, grades are taken as recorded (backward compatible).
    """
    valid = []
    problems = []
    for index, r in enumerate(receipts or []):
        if not verify_adoption_seal(r):
            problems.append(f"receipt[{index}] seal is broken; excluded")
            continue
        valid.append(r)

    attest_ctx = None
    if attestations is not None:
        attest_ctx = {"by_sample": {}, "by_hash": {}}
        for a in attestations:
            sample_h = a.get("sample_sha256")
            if sample_h:
                attest_ctx["by_sample"][sample_h] = a
            att_h = a.get("attestation_sha256")
            if att_h:
                attest_ctx["by_hash"][att_h] = a

    by_decision = {d: 0 for d in DECISIONS}
    by_grade = {g: 0 for g in PROVENANCE_GRADES}
    defects = []
    for index, r in enumerate(valid):
        by_decision[r["decision"]] += 1
        grade = _effective_grade(r, attest_ctx, problems, index)
        by_grade[grade] = by_grade.get(grade, 0) + 1
        for d in r["defects_found"]:
            defects.append({"persona": r["persona_id"], "defect": d})

    total = len(valid)
    adopt = by_decision["adopt"]
    # A utility-eligible signal needs real_owned_stakes provenance. Anything
    # less is conditional-adoption / robustness only — stated, never hidden.
    utility_eligible = sum(by_grade[g] for g in UTILITY_GRADES)
    return {
        "total_personas": total,
        "by_decision": by_decision,
        "by_provenance_grade": by_grade,
        "adoption_rate": (adopt / total) if total else None,
        "rejections": by_decision["reject"],
        "defects_found": defects,
        "utility_eligible_receipts": utility_eligible,
        "verdict": {
            "kind": ("conditional_adoption_simulated"
                     if utility_eligible == 0 else "utility_candidate"),
            "is_t4_utility": utility_eligible > 0,
            "note": ("conditional adoption under simulated, unverified-provenance "
                     "personas — a robustness/adoption-propensity signal, NOT a "
                     "T4 utility verdict; rejections are genuine defect signals"
                     if utility_eligible == 0 else
                     "contains real-owned-stakes receipts; may inform T4"),
        },
        "problems": sorted(problems),
    }


if __name__ == "__main__":
    print("library module — validate_persona / build_adoption_receipt / "
          "aggregate_adoption")
    sys.exit(2)
