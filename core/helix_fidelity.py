#!/usr/bin/env python3
"""Fidelity attestation — earning the ``fidelity_attested`` provenance grade.

The persona conditional-adoption trial (``core/helix_adoption_trial.py``) grades
every adoption receipt by provenance. Its middle grade, ``fidelity_attested``,
is meant to mean: *a named real person reviewed the AI's reproduction of their
perspective and attests it is faithful.* But ``build_adoption_receipt`` only
requires that grade to carry a named ``attested_by`` string — so the grade can
be **asserted** without any verifiable backing. That is the same shape of gap
the wedge had with unverified evidence.

This module makes ``fidelity_attested`` **earnable, not merely assertable**:

    persona source  -> the real person's material the persona is grounded in
    reproduction    -> the AI persona's sealed judgment (what gets reviewed)
    attestation     -> the real person's sealed verdict on that reproduction

An attestation only earns the upgrade when it is (a) seal-valid, (b) bound to
the exact reproduction sample by hash, (c) independent — the attester is not the
reproduction agent (you cannot attest your own reproduction), and (d) its
verdict is ``faithful``. Anything else stays ``simulated_unverified``.

Honest ceiling (unchanged): ``fidelity_attested`` strengthens the *authenticity*
of the judgment — a real perspective was faithfully reproduced — but the stakes
are still simulated. It is NOT ``real_owned_stakes`` and NOT a T4 utility
verdict. Only an independent party running the wedge on real work with owned
outcomes reaches that. This module never claims otherwise.

Deterministic, stdlib only: no clock, network, subprocess, randomness, or AI.
The persona reasoning and the human review both happen outside this module; here
we only validate, seal, bind, and grade.
"""

import hashlib
import os
import sys

try:
    from .helix_holdout import canonical_json_bytes
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_holdout import canonical_json_bytes

SCHEMA_SOURCE = "helix-persona-source/1.0"
SCHEMA_SAMPLE = "helix-reproduction-sample/1.0"
SCHEMA_ATTEST = "helix-fidelity-attestation/1.0"

FIDELITY_VERDICTS = ("faithful", "partial", "unfaithful")


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


# --- persona source: the real person's material the persona is grounded in ---

def build_persona_source(persona_id: str, source_refs: list) -> dict:
    """Bind a persona to the real-person material it is grounded in.

    source_refs is a non-empty list of {"ref": <label>, "sha256": <hex>} — each
    a content-addressed pointer to real material (a decision log, a stated
    priority, a prior review). A persona with no source cannot be a subject of
    fidelity attestation: there is nothing to be faithful to.
    """
    if not (persona_id or "").strip():
        raise ValueError("persona_id must be non-empty")
    if not isinstance(source_refs, list) or not source_refs:
        raise ValueError("source_refs must be a non-empty list of {ref, sha256}")
    norm = []
    for i, ref in enumerate(source_refs):
        if not isinstance(ref, dict):
            raise ValueError(f"source_refs[{i}] must be a dict {{ref, sha256}}")
        label = (ref.get("ref") or "").strip()
        digest = (ref.get("sha256") or "").strip()
        if not label or not digest:
            raise ValueError(f"source_refs[{i}] needs non-empty ref and sha256")
        norm.append({"ref": label, "sha256": digest})
    return _seal({
        "schema": SCHEMA_SOURCE,
        "persona_id": persona_id,
        "source_refs": norm,
    }, "source_sha256")


def verify_source(source: dict) -> bool:
    return _verify(source, "source_sha256")


# --- reproduction sample: the AI persona's judgment, what gets reviewed -------

def capture_reproduction(persona: dict, judgment: dict,
                         reproduction_agent: str) -> dict:
    """Seal the AI persona's judgment so a real person can review that exact text.

    reproduction_agent identifies what produced the reproduction (the AI runtime
    /subagent). It is recorded so the attestation can enforce independence: the
    reviewer must not be the producer.
    """
    if not (reproduction_agent or "").strip():
        raise ValueError("reproduction_agent must be non-empty (who reproduced?)")
    if not (persona.get("persona_id") or "").strip():
        raise ValueError("persona_id must be non-empty")
    if not (judgment.get("reasons") or []):
        raise ValueError("a reproduction without reasons is not reviewable")
    return _seal({
        "schema": SCHEMA_SAMPLE,
        "persona_id": persona["persona_id"],
        "interest_function": persona.get("interest_function", ""),
        "reproduction_agent": reproduction_agent,
        "decision": judgment.get("decision"),
        "reasons": list(judgment.get("reasons", [])),
        "defects_found": list(judgment.get("defects_found", [])),
        "conditions": list(judgment.get("conditions", [])),
    }, "sample_sha256")


def verify_sample(sample: dict) -> bool:
    return _verify(sample, "sample_sha256")


# --- attestation: the real person's verdict on the reproduction ---------------

def attest_fidelity(source: dict, sample: dict, attester: dict, verdict: str,
                    reservations=None, conflict_of_interest=None) -> dict:
    """A named real person attests whether the reproduction is faithful.

    attester = {"id": <name>, "role": <what they are>}. Independence is
    enforced: the attester's id must differ from the sample's reproduction_agent
    — you cannot attest your own reproduction. conflict_of_interest is recorded
    verbatim and never hidden (e.g. "attester is the wedge author" = dogfooding,
    a weak-but-real signal, not a laundered one).
    """
    if not verify_source(source):
        raise ValueError("persona source seal is broken")
    if not verify_sample(sample):
        raise ValueError("reproduction sample seal is broken")
    if source.get("persona_id") != sample.get("persona_id"):
        raise ValueError("source and sample are for different personas")
    attester_id = (attester.get("id") if isinstance(attester, dict) else "") or ""
    if not attester_id.strip():
        raise ValueError("attester.id must be non-empty (a named real person)")
    if attester_id.strip() == (sample.get("reproduction_agent") or "").strip():
        raise ValueError("attester must not be the reproduction agent "
                         "(cannot attest one's own reproduction)")
    if verdict not in FIDELITY_VERDICTS:
        raise ValueError(f"verdict must be one of {FIDELITY_VERDICTS}")
    return _seal({
        "schema": SCHEMA_ATTEST,
        "persona_id": sample["persona_id"],
        "attester": {"id": attester_id.strip(),
                     "role": (attester.get("role") or "").strip()},
        "source_sha256": source["source_sha256"],
        "sample_sha256": sample["sample_sha256"],
        "verdict": verdict,
        "reservations": list(reservations or []),
        "conflict_of_interest": (conflict_of_interest or "").strip() or None,
    }, "attestation_sha256")


def verify_attestation(attestation: dict) -> bool:
    return _verify(attestation, "attestation_sha256")


# --- grading: turn an attestation into an earned provenance grade -------------

def attestation_grade(sample: dict, attestation: dict) -> str:
    """The grade a reproduction *earns* from an attestation.

    Returns "fidelity_attested" only when the attestation is seal-valid, bound
    to this exact sample, and its verdict is faithful. Otherwise the honest
    grade is "simulated_unverified" — an unbacked or non-faithful claim earns
    nothing.
    """
    if not verify_sample(sample):
        return "simulated_unverified"
    if not verify_attestation(attestation):
        return "simulated_unverified"
    if attestation.get("sample_sha256") != sample.get("sample_sha256"):
        return "simulated_unverified"
    if attestation.get("verdict") != "faithful":
        return "simulated_unverified"
    return "fidelity_attested"


def earn_provenance(sample: dict, attestation: dict) -> dict:
    """Build a provenance dict with a DERIVED grade, ready for the adoption trial.

    The grade is computed from the attestation, never asserted. Stakes stay
    "simulated": fidelity attestation upgrades authenticity of the judgment, not
    the reality of the stakes — that is real_owned_stakes, out of this scope.
    """
    grade = attestation_grade(sample, attestation)
    prov = {
        "grade": grade,
        "attested_by": attestation.get("attester", {}).get("id")
                       if grade == "fidelity_attested" else None,
        "stakes": "simulated",
        "sample_sha256": sample.get("sample_sha256"),
        "attestation_sha256": attestation.get("attestation_sha256"),
        "conflict_of_interest": attestation.get("conflict_of_interest"),
    }
    return prov


if __name__ == "__main__":
    print("library module — build_persona_source / capture_reproduction / "
          "attest_fidelity / earn_provenance")
    sys.exit(2)
