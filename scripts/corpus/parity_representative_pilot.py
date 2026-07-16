#!/usr/bin/env python3
"""Build representative parity/provenance bundles for the five-pilot set."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import digest  # noqa: E402
from core.helix_schema import schema_path, validate_against_schema  # noqa: E402
from scripts.corpus.parity_contract_runner import (  # noqa: E402
    build_proofescrow_contract,
    run_contract,
)


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def _generic_contract(pack_entry):
    pack = pack_entry["pack"]
    return {
        "schema": "helix-parity-contract/1.0",
        "contract_id": f"contract:{pack}:representative",
        "pack": pack,
        "target_platform": pack_entry["target_platform"],
        "source_locks": [f"seed/parity-provenance/{path}" for path in pack_entry["source_locks"]],
        "machine_evidence": [f"seed/parity-provenance/{path}" for path in pack_entry["machine_evidence"]],
        "inputs": {
            "status": "runner_not_implemented",
        },
        "expected": {
            "helix_decision": "UNAVAILABLE",
            "reason": "representative_runner_not_implemented_or_machine_evidence_blocked",
        },
        "comparators": [
            "source_and_machine_evidence_present",
            "unsupported_runner_reports_unavailable",
        ],
        "invariants": [
            "fail_closed_to_unavailable_on_missing_runner",
            "do_not_promote_hypothesis_source_to_pass",
        ],
    }


def _statement(pack_entry, receipt_rel):
    pack = pack_entry["pack"]
    receipt = _load(os.path.join(ROOT, receipt_rel))
    claims = ["source_locked", f"parity_decision:{receipt['decision']}"]
    if receipt["decision"] == "PASS":
        claims.append("parity_passed")
    else:
        claims.append("parity_not_valid")
    if pack_entry["problems"]:
        claims.append("machine_evidence_blocked")
    statement = {
        "schema": "helix-parity-provenance-statement/1.0",
        "statement_id": f"provenance:{pack}:representative",
        "artifact": pack,
        "pack": pack,
        "target_platform": pack_entry["target_platform"],
        "source_locks": [f"seed/parity-provenance/{path}" for path in pack_entry["source_locks"]],
        "parity_receipts": [receipt_rel],
        "claims": claims,
        "statement_sha256": "",
    }
    statement["statement_sha256"] = digest({**statement, "statement_sha256": ""})
    return statement


def build_pilot(root, evidence_root, now):
    if not now:
        raise ValueError("--now is required for deterministic representative pilot artifacts")
    build_report = _load(os.path.join(evidence_root, "build-report.json"))
    registry_entries = []
    problems = []
    for pack_entry in build_report["packs"]:
        pack = pack_entry["pack"]
        pack_dir = os.path.join(evidence_root, "representative", pack)
        contract_path = os.path.join(pack_dir, "parity-contracts", "released.json")
        receipt_path = os.path.join(pack_dir, "parity-receipts", "released.json")
        statement_path = os.path.join(pack_dir, "provenance-statements", "representative.json")

        if pack == "ProofEscrow":
            contract, contract_problems = build_proofescrow_contract(root, evidence_root, contract_path)
        else:
            contract = _generic_contract(pack_entry)
            contract_problems = validate_against_schema(contract, schema_path(root, "parity-contract"))
            if not contract_problems:
                _write(contract_path, contract)
        problems.extend(f"{pack}: contract: {problem}" for problem in contract_problems)
        if contract_problems:
            continue

        receipt, receipt_problems = run_contract(root, contract_path, receipt_path, now)
        if receipt["decision"] != "PASS":
            receipt_problems = sorted(set(receipt_problems + pack_entry["problems"]))
        problems.extend(f"{pack}: receipt: {problem}" for problem in receipt_problems)

        statement = _statement(pack_entry, _rel(receipt_path))
        statement_problems = validate_against_schema(
            statement, schema_path(root, "provenance-statement"))
        problems.extend(f"{pack}: provenance-statement: {problem}" for problem in statement_problems)
        if not statement_problems:
            _write(statement_path, statement)

        status = "VALID" if receipt["decision"] == "PASS" and not receipt_problems else "BLOCKED"
        registry_entries.append({
            "pack": pack,
            "target_platform": pack_entry["target_platform"],
            "source_locks": [f"seed/parity-provenance/{path}" for path in pack_entry["source_locks"]],
            "machine_evidence": [f"seed/parity-provenance/{path}" for path in pack_entry["machine_evidence"]],
            "parity_contracts": [_rel(contract_path)],
            "parity_receipts": [_rel(receipt_path)],
            "provenance_statements": [_rel(statement_path)],
            "status": status,
        })

    registry = {
        "schema": "helix-parity-evidence-registry/1.0",
        "registry_id": "registry:parity-provenance:representative-5",
        "policy_version": "HELIX-PARITY-PROVENANCE/1.0",
        "updated_at": now,
        "entries": registry_entries,
    }
    registry_problems = validate_against_schema(registry, schema_path(root, "evidence-registry"))
    problems.extend(f"evidence-registry: {problem}" for problem in registry_problems)
    registry_path = os.path.join(evidence_root, "evidence-registry.json")
    if not registry_problems:
        _write(registry_path, registry)

    report = {
        "schema": "helix-parity-representative-pilot-report/1.0",
        "generated_at": now,
        "evidence_registry": _rel(registry_path),
        "counts": {
            "packs": len(registry_entries),
            "valid": sum(1 for entry in registry_entries if entry["status"] == "VALID"),
            "blocked": sum(1 for entry in registry_entries if entry["status"] == "BLOCKED"),
        },
        "problems": problems,
    }
    _write(os.path.join(evidence_root, "representative-pilot-report.json"), report)
    return report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", default=os.path.join(ROOT, "seed", "parity-provenance"))
    parser.add_argument("--now", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    report, problems = build_pilot(ROOT, os.path.abspath(args.evidence_root), args.now)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 4 if args.strict and problems else 0


if __name__ == "__main__":
    sys.exit(main())
