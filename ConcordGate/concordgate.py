#!/usr/bin/env python3
"""ConcordGate — reconcile independent attestations about one subject.

Many tools verify a single action or handback. ConcordGate answers a different
question: given N independent, sealed attestations about ONE subject, do they
**concord**, or does the evidence **split**? It requires a quorum of independent
sources (an organization is the independence unit — many attestations from one
org count as one source), names the exact contradicting pairs, and appends a
sealed hash-chain reconciliation ledger.

Verdict is 3-way and fail-closed:
    CONCORDANT   — a quorum of independent sources agree on every shared claim.
    SPLIT        — independent sources (or one source with itself) contradict on
                   at least one claimed field; every conflict is named.
    INSUFFICIENT — fewer than `quorum` independent sources; concordance unproven.

Design notes:
- The independence unit is the attester organization. A single org asserting the
  same claim ten times is still one source — self-testimony cannot inflate a
  quorum. This is the causal-independence principle applied to evidence.
- Contradictions are never hidden: cross-source and same-source conflicts are
  reported with the exact field and the two conflicting (source, value) pairs.
- Uncertainty fails closed: missing quorum yields INSUFFICIENT, not CONCORDANT.

Deterministic, standard library only: no clock, network, subprocess, randomness,
or AI. Seals are unkeyed SHA-256 over canonical JSON — integrity (tamper-evident
against accidental edits), not authenticity against a key-holding adversary.
"""

import argparse
import hashlib
import json
import os
import sys

SCHEMA_ATTESTATION = "concordgate-attestation/1.0"
SCHEMA_RECONCILIATION = "concordgate-reconciliation/1.0"
VERDICTS = ("CONCORDANT", "SPLIT", "INSUFFICIENT")
DEFAULT_QUORUM = 2


# --- canonical sealing -------------------------------------------------------

def canonical_json_bytes(obj) -> bytes:
    """Deterministic JSON encoding: sorted keys, compact, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(doc: dict, field: str) -> dict:
    sealed = dict(doc)
    sealed.pop(field, None)
    sealed[field] = _sha256(canonical_json_bytes(sealed))
    return sealed


def _verify(doc: dict, field: str) -> bool:
    expected = doc.get(field)
    body = {k: v for k, v in doc.items() if k != field}
    return isinstance(expected, str) and expected == _sha256(
        canonical_json_bytes(body))


# --- attestations ------------------------------------------------------------

def validate_attestation(att: dict) -> list:
    """Structural problems with an attestation (empty list = well-formed)."""
    problems = []
    if not isinstance(att, dict):
        return ["attestation must be an object"]
    attester = att.get("attester")
    if not isinstance(attester, dict):
        problems.append("attester must be an object {id, org}")
    else:
        if not (attester.get("id") or "").strip():
            problems.append("attester.id must be non-empty")
        if not (attester.get("org") or "").strip():
            problems.append("attester.org must be non-empty (independence unit)")
    if not (att.get("subject_id") or "").strip():
        problems.append("subject_id must be non-empty")
    claims = att.get("claims")
    if not isinstance(claims, dict) or not claims:
        problems.append("claims must be a non-empty object of field -> value")
    return sorted(problems)


def seal_attestation(att: dict) -> dict:
    """Validate and seal one attestation. Deterministic in its content."""
    problems = validate_attestation(att)
    if problems:
        raise ValueError(f"invalid attestation: {problems[0]}")
    attester = att["attester"]
    return _seal({
        "schema": SCHEMA_ATTESTATION,
        "attester": {"id": attester["id"].strip(),
                     "org": attester["org"].strip()},
        "subject_id": att["subject_id"].strip(),
        "claims": dict(att["claims"]),
    }, "attestation_sha256")


def verify_attestation_seal(att: dict) -> bool:
    return _verify(att, "attestation_sha256")


# --- reconciliation ----------------------------------------------------------

def reconcile(attestations: list, subject_id: str = None,
              quorum: int = DEFAULT_QUORUM) -> dict:
    """Reconcile attestations about one subject into a sealed verdict.

    The independence unit is ``attester.org``. Cross-org disagreement on any
    shared field is a SPLIT; same-org disagreement is a SPLIT (self-contradiction).
    Fewer than ``quorum`` independent orgs yields INSUFFICIENT.
    """
    if quorum < 1:
        raise ValueError("quorum must be >= 1")
    problems = []
    valid = []
    subjects = set()
    for i, att in enumerate(attestations or []):
        if not verify_attestation_seal(att):
            problems.append(f"attestation[{i}] seal is broken; excluded")
            continue
        if subject_id is not None and att.get("subject_id") != subject_id:
            problems.append(
                f"attestation[{i}] is about subject "
                f"'{att.get('subject_id')}', not '{subject_id}'; excluded")
            continue
        valid.append(att)
        subjects.add(att.get("subject_id"))

    if subject_id is None and len(subjects) > 1:
        problems.append(
            f"attestations span multiple subjects {sorted(subjects)}; "
            "pass subject_id to scope the reconciliation")
        valid = []

    resolved_subject = (subject_id if subject_id is not None
                        else (next(iter(subjects)) if subjects else None))

    # field -> org -> set of values (as canonical strings) with a sample raw value
    field_org_values = {}
    for att in valid:
        org = att["attester"]["org"]
        for field, value in att["claims"].items():
            key = _sha256(canonical_json_bytes(value))
            field_org_values.setdefault(field, {}).setdefault(org, {})[key] = value

    conflicts = []
    for field in sorted(field_org_values):
        org_values = field_org_values[field]
        # same-source: one org holding two different values for a field
        for org in sorted(org_values):
            vals = org_values[org]
            if len(vals) > 1:
                ordered = [vals[k] for k in sorted(vals)]
                conflicts.append({
                    "field": field, "kind": "same-source",
                    "source_a": org, "value_a": ordered[0],
                    "source_b": org, "value_b": ordered[1],
                })
        # cross-source: two orgs holding different values for a field
        orgs = sorted(org_values)
        for a in range(len(orgs)):
            for b in range(a + 1, len(orgs)):
                keys_a = set(org_values[orgs[a]])
                keys_b = set(org_values[orgs[b]])
                if keys_a and keys_b and keys_a != keys_b:
                    ka = sorted(keys_a)[0]
                    kb = sorted(keys_b)[0]
                    conflicts.append({
                        "field": field, "kind": "cross-source",
                        "source_a": orgs[a], "value_a": org_values[orgs[a]][ka],
                        "source_b": orgs[b], "value_b": org_values[orgs[b]][kb],
                    })

    independent_sources = sorted({att["attester"]["org"] for att in valid})
    n_independent = len(independent_sources)

    if n_independent < quorum:
        verdict = "INSUFFICIENT"
    elif conflicts:
        verdict = "SPLIT"
    else:
        verdict = "CONCORDANT"

    return _seal({
        "schema": SCHEMA_RECONCILIATION,
        "subject_id": resolved_subject,
        "quorum": quorum,
        "verdict": verdict,
        "independent_sources": independent_sources,
        "independent_source_count": n_independent,
        "attestations_considered": len(valid),
        "reconciled_fields": sorted(field_org_values),
        "conflicts": conflicts,
        "problems": sorted(problems),
    }, "reconciliation_sha256")


def verify_reconciliation_seal(rec: dict) -> bool:
    return _verify(rec, "reconciliation_sha256")


# --- hash-chain ledger -------------------------------------------------------

def _ledger_path(root: str, ledger_rel: str) -> str:
    return os.path.join(root, *ledger_rel.split("/"))


def read_ledger(root: str, ledger_rel: str) -> list:
    path = _ledger_path(root, ledger_rel)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_ledger(root: str, ledger_rel: str, reconciliation: dict) -> dict:
    """Append a reconciliation as a sealed, parent-chained ledger entry."""
    if not verify_reconciliation_seal(reconciliation):
        raise ValueError("refusing to append a reconciliation with a broken seal")
    entries = read_ledger(root, ledger_rel)
    parent = entries[-1]["entry_sha256"] if entries else None
    body = {
        "seq": len(entries),
        "parent_sha256": parent,
        "reconciliation": reconciliation,
    }
    entry = dict(body)
    entry["entry_sha256"] = _sha256(canonical_json_bytes(body))
    path = _ledger_path(root, ledger_rel)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return entry


def verify_ledger(root: str, ledger_rel: str) -> list:
    """Re-verify seq monotonicity, parent chain, and per-entry seals."""
    problems = []
    parent = None
    for i, entry in enumerate(read_ledger(root, ledger_rel)):
        if entry.get("seq") != i:
            problems.append(f"entry[{i}] seq broken (got {entry.get('seq')})")
        if entry.get("parent_sha256") != parent:
            problems.append(f"entry[{i}] parent chain broken")
        body = {k: v for k, v in entry.items() if k != "entry_sha256"}
        if entry.get("entry_sha256") != _sha256(canonical_json_bytes(body)):
            problems.append(f"entry[{i}] entry seal broken")
        if not verify_reconciliation_seal(entry.get("reconciliation", {})):
            problems.append(f"entry[{i}] reconciliation seal broken")
        parent = entry.get("entry_sha256")
    return problems


# --- CLI (sample / run / report) --------------------------------------------

def _sample() -> dict:
    """A three-source example: two orgs concord, a third splits one field."""
    subject = "release-2026.4.0"
    raw = [
        {"attester": {"id": "alice", "org": "AuditCo"},
         "subject_id": subject,
         "claims": {"sha256": "abc123", "signed": True, "sbom": "present"}},
        {"attester": {"id": "bob", "org": "ReproLab"},
         "subject_id": subject,
         "claims": {"sha256": "abc123", "signed": True, "sbom": "present"}},
        {"attester": {"id": "carol", "org": "ThirdEye"},
         "subject_id": subject,
         "claims": {"sha256": "def999", "signed": True}},
    ]
    return {"subject_id": subject,
            "attestations": [seal_attestation(a) for a in raw]}


def _cmd_sample(args) -> int:
    print(json.dumps(_sample(), ensure_ascii=False, indent=2))
    return 0


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cmd_run(args) -> int:
    doc = _load(args.attestations)
    attestations = doc.get("attestations", doc) if isinstance(doc, dict) else doc
    subject = args.subject or (doc.get("subject_id")
                               if isinstance(doc, dict) else None)
    rec = reconcile(attestations, subject_id=subject, quorum=args.quorum)
    if args.ledger:
        entry = append_ledger(args.root, args.ledger, rec)
        rec = entry["reconciliation"]
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return {"CONCORDANT": 0, "SPLIT": 3, "INSUFFICIENT": 2}[rec["verdict"]]


def _cmd_report(args) -> int:
    problems = verify_ledger(args.root, args.ledger)
    entries = read_ledger(args.root, args.ledger)
    by_verdict = {}
    for e in entries:
        v = e["reconciliation"]["verdict"]
        by_verdict[v] = by_verdict.get(v, 0) + 1
    report = {
        "ledger": args.ledger,
        "entries": len(entries),
        "by_verdict": by_verdict,
        "ledger_valid": not problems,
        "problems": problems,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="concordgate",
        description="Reconcile independent attestations about one subject.")
    parser.add_argument("--root", default=".", help="ledger root directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sample", help="emit a runnable example attestation set")

    run = sub.add_parser("run", help="reconcile an attestation set -> verdict")
    run.add_argument("--attestations", required=True,
                     help="JSON file: {subject_id, attestations:[...]} or [...]")
    run.add_argument("--subject", default=None, help="scope to this subject_id")
    run.add_argument("--quorum", type=int, default=DEFAULT_QUORUM)
    run.add_argument("--ledger", default=None,
                     help="append the sealed reconciliation to this ledger")

    rep = sub.add_parser("report", help="recompute verdicts from a ledger")
    rep.add_argument("--ledger", required=True)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"sample": _cmd_sample, "run": _cmd_run,
            "report": _cmd_report}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
