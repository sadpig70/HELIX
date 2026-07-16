#!/usr/bin/env python3
"""Inventory all platform packs for parity/provenance expansion."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.condense.machine_probe_dataset import build_dataset  # noqa: E402


REPRESENTATIVE_SLUGS = {
    ("Attestra", "proof-escrow"): "ProofEscrow",
    ("Attestra", "authority-arbiter"): "AuthorityArbiter",
    ("Attestra", "graph-quarantine"): "GraphQuarantine",
    ("Routestra", "contract-relay"): "ContractRelay",
    ("Attestra", "hook-circuit"): "HookCircuit",
}


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _representative_index(registry):
    return {entry["pack"]: entry for entry in registry.get("entries", [])}


def build_inventory(root, evidence_root, now):
    if not now:
        raise ValueError("--now is required for deterministic inventory")
    representative_registry = _load(os.path.join(evidence_root, "evidence-registry.json"))
    representative = _representative_index(representative_registry)
    dataset = build_dataset()
    rows_by_pack = {}
    for row in dataset["agreement"]["rows"]:
        platform = row.get("platform")
        pack = row.get("pack")
        if platform == "HELIX" or pack == "core":
            continue
        key = (platform, pack)
        entry = rows_by_pack.setdefault(key, {
            "platform": platform,
            "pack": pack,
            "stages": [],
            "machines": [],
            "probe_cases": [],
        })
        entry["stages"].append(row.get("stage"))
        for machine in row.get("matched", []):
            entry["machines"].append(machine)
        entry["probe_cases"].append(row.get("id"))

    entries = []
    for (platform, pack), entry in sorted(rows_by_pack.items()):
        rep_name = REPRESENTATIVE_SLUGS.get((platform, pack))
        if rep_name and rep_name in representative:
            rep_entry = representative[rep_name]
            status = rep_entry["status"]
            evidence = {
                "representative_pack": rep_name,
                "parity_receipts": rep_entry.get("parity_receipts", []),
                "provenance_statements": rep_entry.get("provenance_statements", []),
            }
            reason = "representative_evidence_registered"
        else:
            status = "PENDING"
            evidence = {}
            reason = "parity_provenance_bundle_not_started"
        entries.append({
            "platform": platform,
            "pack": pack,
            "status": status,
            "machines": sorted(set(entry["machines"])),
            "stages": sorted(set(entry["stages"])),
            "probe_cases": sorted(set(entry["probe_cases"])),
            "evidence": evidence,
            "reason": reason,
        })

    counts_by_status = {}
    counts_by_platform = {}
    for entry in entries:
        counts_by_status[entry["status"]] = counts_by_status.get(entry["status"], 0) + 1
        platform_counts = counts_by_platform.setdefault(entry["platform"], {})
        platform_counts[entry["status"]] = platform_counts.get(entry["status"], 0) + 1

    inventory = {
        "schema": "helix-parity-expansion-inventory/1.0",
        "generated_at": now,
        "source": {
            "machine_probe_dataset": "scripts/condense/machine_probe_dataset.py",
            "representative_registry": "seed/parity-provenance/evidence-registry.json",
        },
        "counts": {
            "packs": len(entries),
            "by_status": dict(sorted(counts_by_status.items())),
            "by_platform": {k: dict(sorted(v.items())) for k, v in sorted(counts_by_platform.items())},
            "probe_cases": sum(len(entry["probe_cases"]) for entry in entries),
        },
        "entries": entries,
        "problems": [] if len(entries) == 62 else [f"expected 62 platform packs, got {len(entries)}"],
    }
    return inventory


def validate_inventory(inventory):
    problems = []
    if inventory.get("schema") != "helix-parity-expansion-inventory/1.0":
        problems.append("schema mismatch")
    entries = inventory.get("entries", [])
    if inventory.get("counts", {}).get("packs") != len(entries):
        problems.append("counts.packs mismatch")
    if len(entries) != 62:
        problems.append(f"expected 62 platform packs, got {len(entries)}")
    statuses = {entry.get("status") for entry in entries}
    if not statuses <= {"VALID", "BLOCKED", "PENDING"}:
        problems.append(f"unknown statuses: {sorted(statuses - {'VALID', 'BLOCKED', 'PENDING'})}")
    keys = [(entry.get("platform"), entry.get("pack")) for entry in entries]
    if len(keys) != len(set(keys)):
        problems.append("duplicate platform/pack entries")
    by_status = {}
    for entry in entries:
        by_status[entry["status"]] = by_status.get(entry["status"], 0) + 1
        if not entry.get("machines"):
            problems.append(f"{entry.get('platform')}/{entry.get('pack')}: missing machines")
        if not entry.get("probe_cases"):
            problems.append(f"{entry.get('platform')}/{entry.get('pack')}: missing probe cases")
        if entry["status"] in ("VALID", "BLOCKED") and not entry.get("evidence"):
            problems.append(f"{entry.get('platform')}/{entry.get('pack')}: registered status lacks evidence")
        if entry["status"] == "PENDING" and entry.get("evidence"):
            problems.append(f"{entry.get('platform')}/{entry.get('pack')}: pending entry must not claim evidence")
    if inventory.get("counts", {}).get("by_status") != dict(sorted(by_status.items())):
        problems.append("counts.by_status mismatch")
    return sorted(set(problems + inventory.get("problems", [])))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", default=os.path.join(ROOT, "seed", "parity-provenance"))
    parser.add_argument("--out", default=os.path.join(ROOT, "seed", "parity-provenance", "expansion-inventory.json"))
    parser.add_argument("--now", required=True)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    if args.validate:
        inventory = _load(args.out)
    else:
        inventory = build_inventory(ROOT, os.path.abspath(args.evidence_root), args.now)
        _write(args.out, inventory)
    problems = validate_inventory(inventory)
    result = {"valid": not problems, "problems": problems, "counts": inventory.get("counts", {})}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not problems else 4


if __name__ == "__main__":
    sys.exit(main())
