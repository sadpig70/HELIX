#!/usr/bin/env python3
"""Promote one pending platform pack into a parity/provenance evidence bundle."""

import argparse
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import digest  # noqa: E402
from core.helix_schema import schema_path, validate_against_schema  # noqa: E402
from scripts.condense.machine_probe_dataset import build_dataset  # noqa: E402


DEFAULT_PLATFORM = "Attestra"
DEFAULT_PACK = "policy-drift"


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def _head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def _pack_source_files(platform, pack):
    if platform == "Attestra" and pack == "policy-drift":
        return [
            os.path.join(ROOT, "Attestra", "attestra_packs", "policy_drift.py"),
            os.path.join(ROOT, "Attestra", "schemas", "packet-policy.schema.json"),
        ]
    raise ValueError(f"unsupported promotion target: {platform}/{pack}")


def _combined_file_digest(paths):
    return digest({os.path.relpath(path, ROOT).replace(os.sep, "/"): _sha256_file(path) for path in paths})


def _probe_rows(platform, pack):
    dataset = build_dataset()
    rows = [
        row for row in dataset["agreement"]["rows"]
        if row.get("platform") == platform and row.get("pack") == pack
    ]
    if not rows:
        raise ValueError(f"no machine probe rows for {platform}/{pack}")
    failed = [row.get("id") for row in rows if sorted(row.get("matched", [])) != sorted(row.get("expected", []))]
    if failed:
        raise ValueError(f"machine probe mismatch for {platform}/{pack}: {failed}")
    return sorted(rows, key=lambda row: row.get("id", ""))


def build_promotion(platform, pack, evidence_root, now):
    if not now:
        raise ValueError("--now is required for deterministic promotion")
    rows = _probe_rows(platform, pack)
    source_files = _pack_source_files(platform, pack)
    out_dir = os.path.join(evidence_root, "expansion", platform, pack)
    source_rel = os.path.join("expansion", platform, pack, "source-locks", "local-pack.json")
    machine_rel = os.path.join("expansion", platform, pack, "machine-evidence", "live-probe.json")
    contract_rel = os.path.join("expansion", platform, pack, "parity-contracts", "live-probe.json")
    receipt_rel = os.path.join("expansion", platform, pack, "parity-receipts", "live-probe.json")
    statement_rel = os.path.join("expansion", platform, pack, "provenance-statements", "live-probe.json")

    source_id = f"source:{platform}:{pack}"
    machine_id = f"machine:{platform}:{pack}:live-probe"
    source_lock = {
        "schema": "helix-parity-source-lock/1.0",
        "source_id": source_id,
        "corpus_id": f"PLATFORM-PACK-{platform}-{pack}",
        "origin_kind": "helix_generated",
        "locator": f"{platform}/{pack}",
        "revision": _head(),
        "source_sha256": _combined_file_digest(source_files),
        "license": "MIT",
        "license_evidence_sha256": _sha256_file(os.path.join(ROOT, platform, "LICENSE")),
        "captured_at": now,
        "restrictions": ["local_platform_pack_snapshot"],
    }
    machine_evidence = {
        "schema": "helix-parity-machine-evidence/1.0",
        "evidence_id": machine_id,
        "source_lock_id": source_id,
        "machine_label": "live-machine-probe",
        "machine_status": "substantiated",
        "reproduction_command": "python scripts/condense/machine_probe_dataset.py --json",
        "tests_passed": True,
        "deterministic": True,
        "behavior_sha256": digest(rows),
        "supporting_files": [_rel(path) for path in source_files],
        "problems": [],
    }
    contract = {
        "schema": "helix-parity-contract/1.0",
        "contract_id": f"contract:{platform}:{pack}:live-probe",
        "pack": pack,
        "target_platform": platform,
        "source_locks": [f"seed/parity-provenance/{source_rel.replace(os.sep, '/')}"],
        "machine_evidence": [f"seed/parity-provenance/{machine_rel.replace(os.sep, '/')}"],
        "inputs": {
            "probe_cases": [row["id"] for row in rows],
        },
        "expected": {
            "case_count": len(rows),
            "machines": sorted({machine for row in rows for machine in row.get("matched", [])}),
        },
        "comparators": ["probe_matched_expected", "machine_evidence_substantiated"],
        "invariants": ["do_not_mark_pass_without_live_probe_match"],
    }
    observations = {
        "probe_cases": [row["id"] for row in rows],
        "matched_machines": contract["expected"]["machines"],
        "case_count": len(rows),
        "contract_sha256": digest(contract),
    }
    receipt = {
        "schema": "helix-parity-receipt/1.0",
        "receipt_id": f"receipt:{platform}:{pack}:live-probe",
        "contract_id": contract["contract_id"],
        "runner": "helix-parity-pending-promotion/1.0",
        "executed_at": now,
        "decision": "PASS",
        "source_lock_sha256s": [digest(source_lock)],
        "machine_evidence_sha256s": [digest(machine_evidence)],
        "observations": observations,
        "problems": [],
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = digest({**receipt, "receipt_sha256": ""})
    statement = {
        "schema": "helix-parity-provenance-statement/1.0",
        "statement_id": f"provenance:{platform}:{pack}:live-probe",
        "artifact": f"{platform}/{pack}",
        "pack": pack,
        "target_platform": platform,
        "source_locks": contract["source_locks"],
        "parity_receipts": [f"seed/parity-provenance/{receipt_rel.replace(os.sep, '/')}"],
        "claims": ["source_locked", "machine_probe_substantiated", "parity_decision:PASS", "parity_passed"],
        "statement_sha256": "",
    }
    statement["statement_sha256"] = digest({**statement, "statement_sha256": ""})

    docs = [
        ("source-lock", source_lock, os.path.join(evidence_root, source_rel)),
        ("machine-evidence", machine_evidence, os.path.join(evidence_root, machine_rel)),
        ("parity-contract", contract, os.path.join(evidence_root, contract_rel)),
        ("parity-receipt", receipt, os.path.join(evidence_root, receipt_rel)),
        ("provenance-statement", statement, os.path.join(evidence_root, statement_rel)),
    ]
    problems = []
    for schema_name, doc, _ in docs:
        problems.extend(f"{schema_name}: {p}" for p in validate_against_schema(doc, schema_path(ROOT, schema_name)))
    if problems:
        return None, problems
    for _, doc, path in docs:
        _write(path, doc)
    report = {
        "schema": "helix-parity-pending-promotion-report/1.0",
        "generated_at": now,
        "platform": platform,
        "pack": pack,
        "status": "VALID",
        "source_lock": f"seed/parity-provenance/{source_rel.replace(os.sep, '/')}",
        "machine_evidence": f"seed/parity-provenance/{machine_rel.replace(os.sep, '/')}",
        "parity_contract": f"seed/parity-provenance/{contract_rel.replace(os.sep, '/')}",
        "parity_receipt": f"seed/parity-provenance/{receipt_rel.replace(os.sep, '/')}",
        "provenance_statement": f"seed/parity-provenance/{statement_rel.replace(os.sep, '/')}",
        "probe_case_count": len(rows),
        "machines": contract["expected"]["machines"],
        "problems": [],
    }
    _write(os.path.join(out_dir, "promotion-report.json"), report)
    return report, []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    parser.add_argument("--pack", default=DEFAULT_PACK)
    parser.add_argument("--evidence-root", default=os.path.join(ROOT, "seed", "parity-provenance"))
    parser.add_argument("--now", required=True)
    args = parser.parse_args(argv)
    report, problems = build_promotion(
        args.platform, args.pack, os.path.abspath(args.evidence_root), args.now)
    print(json.dumps(report or {"valid": False, "problems": problems}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report else 4


if __name__ == "__main__":
    sys.exit(main())
