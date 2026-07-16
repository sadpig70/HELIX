#!/usr/bin/env python3
"""Build and run HELIX parity contracts for representative platform packs."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import digest  # noqa: E402
from core.helix_schema import schema_path, validate_against_schema  # noqa: E402


PROOFESCROW_CONTRACT_ID = "contract:ProofEscrow:released"


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _sha256_file(path):
    with open(path, "rb") as handle:
        import hashlib
        hasher = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def _proofescrow_paths(root, evidence_root):
    pack_root = os.path.join(root, "ProofEscrow")
    evidence_pack = os.path.join(evidence_root, "representative", "ProofEscrow")
    return {
        "pack_root": pack_root,
        "request": os.path.join(pack_root, "examples", "released-request.json"),
        "trust_store": os.path.join(pack_root, "examples", "trust-store.json"),
        "source_locks": [
            os.path.join(evidence_pack, "source-locks", "HC-PILOT-EXT-001.json"),
            os.path.join(evidence_pack, "source-locks", "HC-PILOT-HELIX-002.json"),
        ],
        "machine_evidence": [
            os.path.join(evidence_pack, "machine-evidence", "HC-PILOT-EXT-001.json"),
            os.path.join(evidence_pack, "machine-evidence", "HC-PILOT-HELIX-002.json"),
        ],
    }


def build_proofescrow_contract(root, evidence_root, out):
    paths = _proofescrow_paths(root, evidence_root)
    request = _load(paths["request"])
    expected = {
        "pack_decision": "RELEASED",
        "helix_decision": "PASS",
        "required_gene_provenance": {
            "signed_step_metadata": "HC-PILOT-EXT-001",
            "behavior_baseline_binding": "HC-PILOT-HELIX-002",
        },
    }
    contract = {
        "schema": "helix-parity-contract/1.0",
        "contract_id": PROOFESCROW_CONTRACT_ID,
        "pack": "ProofEscrow",
        "target_platform": "Attestra",
        "source_locks": [_rel(path) for path in paths["source_locks"]],
        "machine_evidence": [_rel(path) for path in paths["machine_evidence"]],
        "inputs": {
            "request": _rel(paths["request"]),
            "trust_store": _rel(paths["trust_store"]),
        },
        "expected": expected,
        "comparators": [
            "pack_decision_equals_expected",
            "gene_provenance_equals_expected",
            "source_and_machine_evidence_present",
        ],
        "invariants": [
            "fail_closed_to_unavailable_on_missing_input",
            "receipt_hash_canonical",
        ],
    }
    problems = validate_against_schema(contract, schema_path(root, "parity-contract"))
    if problems:
        return None, problems
    _write(out, contract)
    return contract, []


def _load_proofescrow(root):
    src = os.path.join(root, "ProofEscrow", "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from proofescrow.engine import evaluate  # noqa: E402
    return evaluate


def run_contract(root, contract_path, out, now):
    if not now:
        raise ValueError("--now is required for deterministic parity receipts")
    contract = _load(contract_path)
    problems = validate_against_schema(contract, schema_path(root, "parity-contract"))
    observations = {
        "contract_sha256": digest(contract),
        "pack_receipt": None,
        "comparators": [],
    }
    if problems:
        return _receipt(contract, now, "UNAVAILABLE", observations, problems), problems

    missing = []
    paths = []
    for rel_path in contract["source_locks"] + contract["machine_evidence"]:
        path = os.path.join(root, rel_path)
        paths.append(path)
        if not os.path.exists(path):
            missing.append(rel_path)
    if missing:
        problems = [f"missing input: {path}" for path in sorted(missing)]
        receipt = _receipt(contract, now, "UNAVAILABLE", observations, problems)
        _write(out, receipt)
        return receipt, problems

    if contract.get("pack") != "ProofEscrow":
        problems = [f"unsupported pack: {contract.get('pack')}"]
        receipt = _receipt(contract, now, "UNAVAILABLE", observations, problems)
        _write(out, receipt)
        return receipt, problems

    for key in ("request", "trust_store"):
        rel_path = contract["inputs"].get(key, "")
        path = os.path.join(root, rel_path)
        paths.append(path)
        if not os.path.exists(path):
            missing.append(rel_path)
    if missing:
        problems = [f"missing input: {path}" for path in sorted(missing)]
        receipt = _receipt(contract, now, "UNAVAILABLE", observations, problems)
        _write(out, receipt)
        return receipt, problems

    evaluate = _load_proofescrow(root)
    request = _load(os.path.join(root, contract["inputs"]["request"]))
    trust_store = _load(os.path.join(root, contract["inputs"]["trust_store"]))
    pack_receipt = evaluate(request, trust_store)
    observations["pack_receipt"] = pack_receipt
    expected = contract.get("expected", {})
    comparator_results = [
        {
            "name": "pack_decision_equals_expected",
            "pass": pack_receipt.get("decision") == expected.get("pack_decision"),
        },
        {
            "name": "gene_provenance_equals_expected",
            "pass": pack_receipt.get("gene_provenance") == expected.get("required_gene_provenance"),
        },
        {
            "name": "source_and_machine_evidence_present",
            "pass": all(os.path.exists(path) for path in paths),
        },
    ]
    observations["comparators"] = comparator_results
    failed = [item["name"] for item in comparator_results if not item["pass"]]
    decision = "PASS" if not failed else "FAIL"
    problems = [f"comparator failed: {name}" for name in failed]
    receipt = _receipt(contract, now, decision, observations, problems)
    receipt_problems = validate_against_schema(receipt, schema_path(root, "parity-receipt"))
    problems.extend(f"parity-receipt: {problem}" for problem in receipt_problems)
    _write(out, receipt)
    return receipt, problems


def _receipt(contract, now, decision, observations, problems):
    source_hashes = []
    machine_hashes = []
    for rel_path in contract.get("source_locks", []):
        path = os.path.join(ROOT, rel_path)
        source_hashes.append(_sha256_file(path) if os.path.exists(path) else "")
    for rel_path in contract.get("machine_evidence", []):
        path = os.path.join(ROOT, rel_path)
        machine_hashes.append(_sha256_file(path) if os.path.exists(path) else "")
    receipt = {
        "schema": "helix-parity-receipt/1.0",
        "receipt_id": f"receipt:{contract.get('pack', 'unknown')}:released",
        "contract_id": contract.get("contract_id", ""),
        "runner": "helix-parity-contract-runner/1.0",
        "executed_at": now,
        "decision": decision,
        "source_lock_sha256s": source_hashes,
        "machine_evidence_sha256s": machine_hashes,
        "observations": observations,
        "problems": problems,
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = digest({**receipt, "receipt_sha256": ""})
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build-proofescrow")
    build.add_argument("--evidence-root", default=os.path.join(ROOT, "seed", "parity-provenance"))
    build.add_argument("--out", default=os.path.join(
        ROOT, "seed", "parity-provenance", "representative", "ProofEscrow",
        "parity-contracts", "released.json"))
    run = sub.add_parser("run")
    run.add_argument("--contract", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--now", required=True)
    args = parser.parse_args(argv)
    if args.command == "build-proofescrow":
        contract, problems = build_proofescrow_contract(
            ROOT, os.path.abspath(args.evidence_root), os.path.abspath(args.out))
        print(json.dumps(contract or {"valid": False, "problems": problems}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if contract else 4
    receipt, problems = run_contract(ROOT, os.path.abspath(args.contract), os.path.abspath(args.out), args.now)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["decision"] == "PASS" and not problems else 4


if __name__ == "__main__":
    sys.exit(main())
