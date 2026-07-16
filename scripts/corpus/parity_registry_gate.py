#!/usr/bin/env python3
"""CI gate for HELIX parity/provenance representative evidence."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import digest  # noqa: E402
from core.helix_schema import schema_path, validate_against_schema  # noqa: E402


EXPECTED_PACKS = {
    "ProofEscrow",
    "AuthorityArbiter",
    "GraphQuarantine",
    "ContractRelay",
    "HookCircuit",
}


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _abs(root, rel_path):
    return os.path.join(root, rel_path.replace("/", os.sep))


def _validate(root, schema_name, rel_path):
    path = _abs(root, rel_path)
    if not os.path.exists(path):
        return None, [f"{rel_path}: missing"]
    doc = _load(path)
    return doc, [f"{rel_path}: {problem}" for problem in validate_against_schema(
        doc, schema_path(root, schema_name))]


def _check_receipt_seal(receipt, rel_path):
    expected = digest({**receipt, "receipt_sha256": ""})
    if receipt.get("receipt_sha256") != expected:
        return [f"{rel_path}: receipt_sha256 mismatch"]
    return []


def _check_statement_seal(statement, rel_path):
    expected = digest({**statement, "statement_sha256": ""})
    if statement.get("statement_sha256") != expected:
        return [f"{rel_path}: statement_sha256 mismatch"]
    return []


def validate_parity_registry(root, registry_path, report_path):
    problems = []
    registry_rel = os.path.relpath(registry_path, root).replace(os.sep, "/")
    report_rel = os.path.relpath(report_path, root).replace(os.sep, "/")
    registry, registry_problems = _validate(root, "evidence-registry", registry_rel)
    problems.extend(registry_problems)
    if registry is None:
        return problems
    if not os.path.exists(report_path):
        problems.append(f"{report_rel}: missing")
        report = None
    else:
        report = _load(report_path)
    entries = registry.get("entries", [])
    packs = {entry.get("pack") for entry in entries}
    if packs != EXPECTED_PACKS:
        problems.append(f"registry packs mismatch: expected {sorted(EXPECTED_PACKS)}, got {sorted(packs)}")
    if len(entries) != 5:
        problems.append(f"registry entry count must be 5, got {len(entries)}")

    valid_count = 0
    blocked_count = 0
    for entry in entries:
        pack = entry.get("pack", "<unknown>")
        entry_status = entry.get("status")
        for rel_path in entry.get("source_locks", []):
            _, doc_problems = _validate(root, "source-lock", rel_path)
            problems.extend(f"{pack}: {problem}" for problem in doc_problems)
        for rel_path in entry.get("machine_evidence", []):
            _, doc_problems = _validate(root, "machine-evidence", rel_path)
            problems.extend(f"{pack}: {problem}" for problem in doc_problems)
        for rel_path in entry.get("parity_contracts", []):
            contract, doc_problems = _validate(root, "parity-contract", rel_path)
            problems.extend(f"{pack}: {problem}" for problem in doc_problems)
            if contract and contract.get("pack") != pack:
                problems.append(f"{pack}: {rel_path}: contract pack mismatch")
        receipt_decisions = []
        for rel_path in entry.get("parity_receipts", []):
            receipt, doc_problems = _validate(root, "parity-receipt", rel_path)
            problems.extend(f"{pack}: {problem}" for problem in doc_problems)
            if receipt:
                problems.extend(f"{pack}: {problem}" for problem in _check_receipt_seal(receipt, rel_path))
                receipt_decisions.append(receipt.get("decision"))
        for rel_path in entry.get("provenance_statements", []):
            statement, doc_problems = _validate(root, "provenance-statement", rel_path)
            problems.extend(f"{pack}: {problem}" for problem in doc_problems)
            if statement:
                problems.extend(f"{pack}: {problem}" for problem in _check_statement_seal(statement, rel_path))
                if statement.get("pack") != pack:
                    problems.append(f"{pack}: {rel_path}: provenance statement pack mismatch")

        if entry_status == "VALID":
            valid_count += 1
            if receipt_decisions != ["PASS"]:
                problems.append(f"{pack}: VALID entry must have exactly one PASS receipt, got {receipt_decisions}")
        elif entry_status == "BLOCKED":
            blocked_count += 1
            if "PASS" in receipt_decisions:
                problems.append(f"{pack}: BLOCKED entry must not contain PASS receipt")
            if not receipt_decisions:
                problems.append(f"{pack}: BLOCKED entry must still carry a non-PASS receipt")
        else:
            problems.append(f"{pack}: unsupported registry status {entry_status!r}")

    if report:
        counts = report.get("counts", {})
        expected_counts = {"packs": len(entries), "valid": valid_count, "blocked": blocked_count}
        if counts != expected_counts:
            problems.append(f"{report_rel}: counts mismatch expected {expected_counts}, got {counts}")
        if report.get("evidence_registry") != registry_rel:
            problems.append(f"{report_rel}: evidence_registry mismatch")
        if blocked_count and not report.get("problems"):
            problems.append(f"{report_rel}: blocked packs require explicit problems")
    return sorted(set(problems))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=os.path.join(
        ROOT, "seed", "parity-provenance", "evidence-registry.json"))
    parser.add_argument("--report", default=os.path.join(
        ROOT, "seed", "parity-provenance", "representative-pilot-report.json"))
    args = parser.parse_args(argv)
    problems = validate_parity_registry(
        ROOT, os.path.abspath(args.registry), os.path.abspath(args.report))
    result = {
        "valid": not problems,
        "problems": problems,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not problems else 4


if __name__ == "__main__":
    sys.exit(main())
