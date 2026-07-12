#!/usr/bin/env python3
"""First utility wedge: agent handback/approval audit (T4, P5_1).

Policy source of truth: process plan §P5 first user journey —

    agent handback packet
        -> ActionHandbackVerifier evidence check   (existing 5-predicate)
        -> admission class                          (P4_2: valid=ADMIT /
                                                     thin=SANDBOX_ONLY /
                                                     breach=EXCLUDED)
        -> Constitution authorization               (the audit itself, R0)
        -> replayable audit receipt                 (actuation ledger entry)

``audit_handback`` is the single entry an operator calls with one handback
packet; it reuses the existing backbone end to end and invents no new
judgment logic. The packet is stored at an immutable content-addressed path
and becomes the evidence artifact of an R0 (read-only judgment) intent; the
gate result, admission receipt, and the sealed wedge decision are chained
and appended to the actuation ledger. The decision receipt carries the T4
North-Star metric marker (``weekly_real_admission_decisions``) so real usage
is countable without any extra bookkeeping.

Replayability: ``verify_wedge_decision`` re-hashes the stored packet,
re-runs the AHV verdict and the admission classification, and re-checks
every seal — a decision that cannot be reproduced is reported, never trusted.

Security boundary (honest): seals are unkeyed SHA-256 (integrity, not
authenticity). Replay catches an honest mistake or accidental corruption
that leaves the stored packet intact, but a write-capable adversary who
rebuilds the packet too can make replay reproduce a laundered verdict — this
is NOT tamper-evidence against such an adversary; keyed signing and external
anchoring would be required (backlog). Also, ``valid`` attests packet
structure only: AHV does not read the files at ``evidence_path``, so evidence
existence/authenticity is unverified here.

Absent-packet admission (QUARANTINE) for registry entries is already covered
by engines/exploit registry_admissions; this wedge audits SUBMITTED packets.

Deterministic given its inputs; stdlib + vendored AHV only.
"""

import hashlib
import json
import os
import sys

try:  # package import (python -m core.helix_wedge) or library use
    from .helix_admission import build_admission_receipt, classify_admission
    from .helix_actuator import append_actuation_ledger
    from .helix_authorization import authorize, verify_gate_result_seal
    from .helix_evidence import build_evidence_manifest
    from .helix_holdout import canonical_json_bytes
    from .helix_project_paths import ensure_project_src
    from .helix_state_receipt import sha256_file
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_admission import build_admission_receipt, classify_admission
    from core.helix_actuator import append_actuation_ledger
    from core.helix_authorization import authorize, verify_gate_result_seal
    from core.helix_evidence import build_evidence_manifest
    from core.helix_holdout import canonical_json_bytes
    from core.helix_project_paths import ensure_project_src
    from core.helix_state_receipt import sha256_file

SCHEMA_ID = "helix-wedge-decision/1.0"
AUDITABLE_GATES = ("ALLOW", "SANDBOX")  # the audit is a judgment, not a write


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_wedge_seal(decision: dict) -> bool:
    expected = decision.get("receipt_sha256")
    body = {k: v for k, v in decision.items() if k != "receipt_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _full(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _ahv_verdict(root: str, packet: dict) -> str:
    ensure_project_src(root, "ActionHandbackVerifier")
    try:
        from ActionHandbackVerifier.verifier import evaluate_handback
    except ImportError:
        raise ValueError("ActionHandbackVerifier is required for handback "
                         "audits and is not available")
    return evaluate_handback(packet)["verdict"]


def _store_packet(root: str, packets_dir: str, packet: dict) -> tuple:
    """Store the submitted packet at an immutable content-addressed path."""
    raw = canonical_json_bytes(packet)
    digest = hashlib.sha256(raw).hexdigest()
    rel = f"{packets_dir.rstrip('/')}/{digest}.json"
    full = _full(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:  # unconditional write also heals a poisoned path
        f.write(raw)
    return digest, rel


EVIDENCE_PREDICATES = ("delegation", "custody", "route", "rollback", "trace")


def _verify_evidence(root: str, packet: dict, evidence_root) -> dict:
    """Check that the packet's cited evidence artifacts actually exist.

    Addresses the persona-trial finding that a ``valid`` verdict attests
    packet STRUCTURE only — AHV never reads the files at ``evidence_path``.
    When the participant submits an ``evidence_root`` (the directory holding
    their evidence files), this verifies each cited path exists and, if the
    packet carries an ``evidence_hashes`` map {path: sha256}, that the bytes
    match. Returns {status, checks}:

    - not_provided : no evidence_root, or the packet cites no evidence paths —
      the wedge cannot see the participant's files and says so honestly rather
      than pretending the evidence is verified.
    - verified     : every cited artifact is present (and declared hashes match).
    - unverified   : a cited artifact is missing or hash-mismatched.
    """
    if not evidence_root:
        return {"status": "not_provided", "checks": []}
    hashes = packet.get("evidence_hashes") or {}
    checks = []
    ok = True
    for pred in EVIDENCE_PREDICATES:
        path = (packet.get(pred) or {}).get("evidence_path")
        if not path:
            continue
        full = path if os.path.isabs(path) else os.path.join(
            _full(root, evidence_root), path)
        exists = os.path.isfile(full)
        check = {"predicate": pred, "evidence_path": path, "exists": exists,
                 "hash_match": None}
        if not exists:
            ok = False
        elif path in hashes:
            check["hash_match"] = sha256_file(full) == hashes[path]
            if not check["hash_match"]:
                ok = False
        checks.append(check)
    if not checks:
        return {"status": "not_provided", "checks": []}
    return {"status": "verified" if ok else "unverified", "checks": checks}


def _audit_intent(operator: dict, packet_sha256: str) -> dict:
    return {
        "schema": "helix-action-intent/1.0",
        "intent_id": f"INT-WEDGE-{packet_sha256[:12]}",
        "title": "Audit one agent handback packet",
        "proposer": {"kind": operator.get("kind", "human"),
                     "id": operator["id"]},
        "risk_class": "R0",
        "scope": {"write_paths": [], "remote_mutation": False,
                  "publish": False},
        "impact": {"authority": False, "economic": False, "physical": False,
                   "broad_public": False},
        "reversibility": {"reversible": True,
                          "rollback_plan": "read-only judgment; the audit "
                                           "trail is append-only"},
        "budget": {"max_files": 0, "max_bytes": 0},
        "justification": "Judge whether this agent handback packet may be "
                         "admitted (wedge: handback/approval audit).",
    }


def audit_handback(root: str, packet: dict, operator: dict,
                   current_state_receipt_hash: str, ledger_rel: str,
                   packets_dir: str, migration=None, evidence_root=None,
                   evidence_required=False, signing_key=None) -> dict:
    """One admission decision for one submitted handback packet.

    Returns {decision, gate, admission_receipt} on success; a non-auditable
    gate (DENY/HUMAN/RETIRE) refuses with zero records beyond the gate entry.

    Evidence truth (persona-trial fix): with ``evidence_root``, cited evidence
    artifacts are verified for existence/hash. With ``evidence_required=True``,
    a ``valid`` packet whose evidence is ``unverified`` is downgraded to
    ``thin`` (ADMIT -> SANDBOX_ONLY) so structure-only claims cannot earn
    ADMIT. Without evidence_root the wedge honestly records
    ``evidence_check.status = not_provided`` and does not pretend to verify.
    """
    if not isinstance(packet, dict) or not packet:
        raise ValueError("audit requires a submitted handback packet; "
                         "absent-packet admission for registry entries is "
                         "registry_admissions' job")
    if not (operator.get("id") or "").strip():
        raise ValueError("operator.id must be non-empty")

    packet_sha256, packet_rel = _store_packet(root, packets_dir, packet)
    intent = _audit_intent(operator, packet_sha256)
    manifest = build_evidence_manifest(
        root, f"EVM-WEDGE-{packet_sha256[:12]}", intent,
        {"kind": operator.get("kind", "human"), "id": operator["id"]},
        [{"role": "handback_packet", "path": packet_rel,
          "provenance": {"origin": "external", "reference": None}}])
    gate = authorize(root, intent, manifest, [], current_state_receipt_hash)
    decision_id = f"WD-{packet_sha256[:16]}"
    append_actuation_ledger(root, ledger_rel, "gate", decision_id, gate,
                            signing_key=signing_key)
    if gate["decision"] not in AUDITABLE_GATES:
        return {"decision": None, "stage": "gate", "gate": gate,
                "why": f"gate decision {gate['decision']} refuses the audit"}

    raw_verdict = _ahv_verdict(root, packet)
    evidence_check = _verify_evidence(root, packet, evidence_root)
    verdict = raw_verdict
    evidence_downgrade = False
    if (evidence_required and evidence_check["status"] == "unverified"
            and raw_verdict == "valid"):
        verdict = "thin"  # structure valid but evidence unverified -> sandbox
        evidence_downgrade = True
    admission_receipt = build_admission_receipt(
        packet.get("handback_id") or decision_id, verdict, migration,
        current_state_receipt_hash)

    decision = _seal({
        "schema": SCHEMA_ID,
        "decision_id": decision_id,
        "operator": {"kind": operator.get("kind", "human"),
                     "id": operator["id"]},
        "handback_id": packet.get("handback_id"),
        "packet_sha256": packet_sha256,
        "packet_path": packet_rel,
        "handback_verdict": raw_verdict,
        "effective_verdict": verdict,
        "evidence_check": {"status": evidence_check["status"],
                           "checks": evidence_check["checks"],
                           "downgraded": evidence_downgrade},
        "admission": admission_receipt["admission"],
        "admission_basis": admission_receipt["basis"],
        "admission_receipt_sha256": admission_receipt["receipt_sha256"],
        "gate_result_sha256": gate["result_sha256"],
        "gate_decision": gate["decision"],
        "state_receipt_hash": current_state_receipt_hash,
        "metric": {"kind": "admission_decision",
                   "counts_toward": "weekly_real_admission_decisions"},
    })
    append_actuation_ledger(root, ledger_rel, "wedge_decision", decision_id,
                            decision, signing_key=signing_key)
    return {"decision": decision, "gate": gate,
            "admission_receipt": admission_receipt}


def verify_wedge_decision(root: str, decision: dict) -> list:
    """Replay one wedge decision from its stored packet; empty == reproduced."""
    problems = []
    if not verify_wedge_seal(decision):
        problems.append("wedge decision seal is broken")
    packet_full = _full(root, decision.get("packet_path", ""))
    if not os.path.isfile(packet_full):
        problems.append("stored packet is missing; decision is not replayable")
        return sorted(problems)
    if sha256_file(packet_full) != decision.get("packet_sha256"):
        problems.append("stored packet bytes do not match the decision")
        return sorted(problems)
    with open(packet_full, "r", encoding="utf-8") as f:
        packet = json.load(f)
    verdict = _ahv_verdict(root, packet)
    if verdict != decision.get("handback_verdict"):
        problems.append(f"verdict does not replay: recorded "
                        f"{decision.get('handback_verdict')!r}, fresh {verdict!r}")
    # Admission is derived from the EFFECTIVE verdict (raw, or thin after an
    # evidence downgrade). evidence_check itself is a decision-time record and
    # is not re-verified here (participant evidence may be unavailable at
    # replay); the seal covers it.
    effective = decision.get("effective_verdict", decision.get("handback_verdict"))
    reclass = classify_admission(effective, None,
                                 decision.get("state_receipt_hash"))
    if (not decision.get("admission_basis", "").startswith("migration")
            and reclass["admission"] != decision.get("admission")):
        problems.append(f"admission does not replay: recorded "
                        f"{decision.get('admission')!r}, fresh "
                        f"{reclass['admission']!r}")
    return sorted(problems)


if __name__ == "__main__":
    print("library module — audit_handback / verify_wedge_decision")
    sys.exit(2)
