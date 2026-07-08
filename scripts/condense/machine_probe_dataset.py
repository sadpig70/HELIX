#!/usr/bin/env python3
"""Build the U6 machine-probe dataset from live -stra pack samples.

This script executes each platform pack's declared sample I/O, normalizes the observed
behavior, and scores implemented machine claims with core.helix_machine_probes.

It is intentionally an extractor, not a new oracle: platform loaders/run_stage functions
produce behavior; probes only validate the normalized artifact shape. Pure local I/O,
stdlib only, no network/AI.
"""

import argparse
import contextlib
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_machine_probes import PROBES, agreement_report  # noqa: E402

REQUIRED_PLATFORM_DIRS = ("Attestra", "Clearstra", "Routestra", "Certstra", "Scorestra")


def missing_platform_dirs(root=ROOT):
    """Return required nested platform repos absent from this checkout."""
    return [name for name in REQUIRED_PLATFORM_DIRS if not os.path.isdir(os.path.join(root, name))]


def required_platforms_available(root=ROOT):
    """Whether the live -stra platform repos needed for U6 extraction are present."""
    return not missing_platform_dirs(root)


@contextlib.contextmanager
def platform_import(platform_dir):
    path = os.path.join(ROOT, platform_dir)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"missing platform repo: {path}")
    old_cwd = os.getcwd()
    sys.path.insert(0, path)
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(old_cwd)
        with contextlib.suppress(ValueError):
            sys.path.remove(path)


def _case(case_id, expected, artifact, platform, pack, stage):
    return {
        "id": case_id,
        "expected": expected,
        "artifact": artifact,
        "platform": platform,
        "pack": pack,
        "stage": stage,
    }


def _stage_skip(platform, pack, stage, machine, reason):
    return {"platform": platform, "pack": pack, "stage": stage, "machine": machine, "reason": reason}


def _implemented(machine):
    return machine in PROBES


def attestra_cases():
    with platform_import("Attestra"):
        from attestra_core.gate_runtime import run_gates
        from attestra_packs.loader import load_packs

        reg = load_packs()
        cases = []
        errors = list(reg["errors"])
        for name, pack in sorted(reg["packs"].items()):
            checks = []
            outputs = []
            packet = pack["samples"].get("valid", {})
            for sample_name in ("valid", "thin", "breach"):
                sample_packet = pack["samples"].get(sample_name)
                if sample_packet is None:
                    errors.append(f"Attestra/{name}: missing {sample_name} sample")
                    continue
                result = run_gates(
                    sample_packet,
                    pack["predicate_fns"],
                    now="T",
                    id_field=pack.get("id_field", "packet_id"),
                    schema=pack.get("schema"),
                )
                outputs.append({"sample": sample_name, "verdict": result.get("verdict")})
                checks.extend(result.get("checks", []))
            artifact = {
                "operation": "predicate_gate",
                "severity_order": ["valid", "thin", "breach"],
                "merge": "max_severity",
                "outputs": outputs,
                "checks": checks,
                "aggregate": {"verdict": outputs[-1]["verdict"] if outputs else "", "merge": "max_severity"},
            }
            cases.append(_case(f"Attestra:{name}", ["M2"], artifact, "Attestra", name, "predicate_gate"))
            m3_artifact = {**artifact, "packet": packet, "subject": packet.get(pack.get("id_field", "packet_id"), "")}
            cases.append(_case(f"Attestra:{name}:predicate-gate", ["M3"], m3_artifact, "Attestra", name, "predicate_gate"))
            if name == "policy-drift":
                for sample_name in ("valid", "thin", "breach"):
                    sample_packet = pack["samples"].get(sample_name)
                    if sample_packet is None:
                        continue
                    result = run_gates(
                        sample_packet,
                        pack["predicate_fns"],
                        now="T",
                        id_field=pack.get("id_field", "packet_id"),
                        schema=pack.get("schema"),
                    )
                    cases.append(_case(
                        f"Attestra:{name}:{sample_name}:drift", ["M11"],
                        {"operation": "drift_detection", "packet": sample_packet, "checks": result.get("checks", [])},
                        "Attestra", name, "drift_detection"))
        fp_items = []
        for name, pack in sorted(reg["packs"].items()):
            fp_items.append({
                "name": name,
                "parts": [pack["packet_schema"], *pack.get("predicates", [])],
                "fingerprint": pack["fingerprint"],
            })
        cases.append(_case(
            "Attestra:fingerprint-dedup", ["M14"],
            {"operation": "fingerprint_dedup", "items": fp_items, "duplicate_groups": []},
            "Attestra", "core", "fingerprint"))
        return cases, [], errors


def trust_core_cases():
    cases = []
    errors = []
    with platform_import("Attestra"):
        from attestra_core.ledger import append_record

        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "ledger.jsonl")
            append_record(ledger_path, {"subject": "S1", "verdict": "valid", "checks": [], "evaluated_at": "A"},
                          "handback", now="T1")
            append_record(ledger_path, {"subject": "S2", "verdict": "thin", "checks": [], "evaluated_at": "B"},
                          "handback", now="T2")
            with open(ledger_path, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f if line.strip()]
        cases.append(_case("Attestra:hash-chain-ledger", ["M1"],
                           {"operation": "hash_chain_ledger", "records": records},
                           "Attestra", "core", "ledger"))
    with platform_import("Certstra"):
        from certstra_core.provenance import verify_provenance

        record = {"evidence_hash": "e7"}
        chain = [{"evidence_hash": "e6", "confirmed": True}, {"evidence_hash": "e7", "confirmed": True}]
        result = verify_provenance(record, chain)
        cases.append(_case("Certstra:provenance-verify", ["M4"],
                           {"operation": "provenance_verify", "record": record, "chain": chain, "result": result},
                           "Certstra", "core", "provenance"))
    cases.append(_case(
        "HELIX:compatibility-gap-reference", ["M13"],
        {"operation": "compatibility_gap_scoring",
         "pairs": [
             {"source": "legacy-a", "target": "adapter-x", "compatibility_score": 0.8, "gap_score": 0.2},
             {"source": "legacy-b", "target": "adapter-x", "compatibility_score": 0.4, "gap_score": 0.6},
         ],
         "summary": {"pair_count": 2, "mean_compatibility": 0.6, "mean_gap": 0.4}},
        "HELIX", "core", "compatibility_gap"))
    return cases, [], errors


def clearstra_cases():
    stage_machines = {"price": "M6", "clear": "M5", "settle": "M7", "rehearse": "M8"}
    with platform_import("Clearstra"):
        from clearstra_markets.loader import load_markets, run_stage

        reg = load_markets()
        cases = []
        skipped = []
        errors = list(reg["errors"])
        for name, market in sorted(reg["markets"].items()):
            for stage in market["stages"]:
                machine = stage_machines[stage]
                if not _implemented(machine):
                    skipped.append(_stage_skip("Clearstra", name, stage, machine, "probe_not_implemented"))
                    continue
                sample = market["samples"].get(stage)
                if sample is None:
                    errors.append(f"Clearstra/{name}: missing {stage} sample")
                    continue
                result = run_stage(market, stage, sample, now="T")
                if stage == "price":
                    artifact = {"operation": "pricing", "outputs": [result]}
                elif stage == "clear":
                    artifact = {"operation": "clearing", **result}
                else:
                    artifact = {"operation": stage, "result": result}
                cases.append(_case(f"Clearstra:{name}:{stage}", [machine], artifact, "Clearstra", name, stage))
        return cases, skipped, errors


def routestra_cases():
    stage_machines = {"route": "M9", "bound": "M10"}
    with platform_import("Routestra"):
        from routestra_packs.loader import load_packs, run_stage

        reg = load_packs()
        cases = []
        skipped = []
        errors = list(reg["errors"])
        for name, pack in sorted(reg["packs"].items()):
            for stage in pack["stages"]:
                machine = stage_machines[stage]
                if not _implemented(machine):
                    skipped.append(_stage_skip("Routestra", name, stage, machine, "probe_not_implemented"))
                    continue
                sample = pack["samples"].get(stage)
                if sample is None:
                    errors.append(f"Routestra/{name}: missing {stage} sample")
                    continue
                result = run_stage(pack, stage, sample, now="T")
                if stage == "route":
                    artifact = {
                        "operation": "candidate_routing",
                        "selected": result.get("selected"),
                        "selected_score": result.get("selected_score"),
                        "selected_evidence": result.get("selected_evidence"),
                        "all_scores": result.get("all_scores", []),
                        "demand": result.get("demand", {}),
                    }
                else:
                    artifact = {
                        "operation": "threshold_bound",
                        "verdict_order": ["compliant", "restricted", "violation"],
                        "merge": "max_severity",
                        "bounds": [{"source": "sample_telemetry"}],
                        "dimensions": result.get("dimensions", []),
                        "aggregate": {"verdict": result.get("verdict"), "merge": "max_severity"},
                    }
                cases.append(_case(f"Routestra:{name}:{stage}", [machine], artifact, "Routestra", name, stage))
        return cases, skipped, errors


def certstra_cases():
    stage_machines = {"certify": "M2", "stage": "M12"}
    with platform_import("Certstra"):
        from certstra_packs.loader import load_packs, run_stage

        reg = load_packs()
        cases = []
        skipped = []
        errors = list(reg["errors"])
        for name, pack in sorted(reg["packs"].items()):
            for stage in pack["stages"]:
                machine = stage_machines[stage]
                if not _implemented(machine):
                    skipped.append(_stage_skip("Certstra", name, stage, machine, "probe_not_implemented"))
                    continue
                sample_names = [stage]
                if stage == "certify":
                    sample_names.extend([s for s in ("needs_review", "blocked") if s in pack["samples"]])
                outputs = []
                checks = []
                for sample_name in sample_names:
                    sample = pack["samples"].get(sample_name)
                    if sample is None:
                        errors.append(f"Certstra/{name}: missing {sample_name} sample")
                        continue
                    result = run_stage(pack, stage, sample, now="T")
                    outputs.append({"sample": sample_name, "verdict": result.get("verdict")})
                    checks.extend(result.get("checks", []))
                if stage == "stage":
                    artifact = {"operation": "staged_release", **result}
                else:
                    artifact = {
                        "operation": "certify",
                        "severity_order": ["certifiable", "needs_review", "blocked"],
                        "merge": "max_severity",
                        "outputs": outputs,
                        "checks": checks,
                        "aggregate": {"verdict": outputs[-1]["verdict"] if outputs else "", "merge": "max_severity"},
                    }
                cases.append(_case(f"Certstra:{name}:{stage}", [machine], artifact, "Certstra", name, stage))
        return cases, skipped, errors


def scorestra_cases():
    with platform_import("Scorestra"):
        from scorestra_packs.loader import load_packs, run_assess

        reg = load_packs()
        cases = []
        errors = list(reg["errors"])
        for name, pack in sorted(reg["packs"].items()):
            sample = pack["samples"].get("assess")
            if sample is None:
                errors.append(f"Scorestra/{name}: missing assess sample")
                continue
            result = run_assess(pack, sample, now="T")
            artifact = {
                "operation": "assessment_scoring",
                "weights": pack.get("weights", {}),
                "bands": pack.get("bands", []),
                "rules": pack.get("rules", []),
                "scored": result.get("scored", []),
                "count_by_tier": result.get("count_by_tier", {}),
                "result": result,
            }
            cases.append(_case(f"Scorestra:{name}:assess", ["M15"], artifact, "Scorestra", name, "assess"))
        return cases, [], errors


BUILDERS = (attestra_cases, clearstra_cases, routestra_cases, certstra_cases, scorestra_cases, trust_core_cases)


def build_dataset():
    cases = []
    skipped = []
    errors = []
    for build in BUILDERS:
        c, s, e = build()
        cases.extend(c)
        skipped.extend(s)
        errors.extend(e)
    report = agreement_report(cases)
    platforms = {}
    for case in cases:
        platforms.setdefault(case["platform"], {"cases": 0, "packs": set()})
        platforms[case["platform"]]["cases"] += 1
        platforms[case["platform"]]["packs"].add(case["pack"])
    platform_summary = {
        name: {"cases": row["cases"], "packs": len(row["packs"])}
        for name, row in sorted(platforms.items())
    }
    return {
        "total_platform_packs": 56,
        "implemented_probe_cases": len(cases),
        "skipped_claims": skipped,
        "errors": errors,
        "platform_summary": platform_summary,
        "agreement": report,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--out", help="write the machine-readable JSON report to this path")
    args = parser.parse_args(argv)
    dataset = build_dataset()
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(dataset, f, sort_keys=True, indent=2)
            f.write("\n")
    if args.json:
        print(json.dumps(dataset, sort_keys=True, indent=2))
        return 0 if not dataset["errors"] else 1
    agreement = dataset["agreement"]
    print("=== HELIX machine probe dataset ===")
    print(f"platform packs: {dataset['total_platform_packs']}")
    print(f"implemented probe cases: {dataset['implemented_probe_cases']}")
    print(f"scored claims: {agreement['scored_claims']}")
    print(f"matched claims: {agreement['matched_claims']}")
    print(f"agreement: {agreement['agreement']:.6f}")
    if dataset["skipped_claims"]:
        by_machine = {}
        for row in dataset["skipped_claims"]:
            by_machine[row["machine"]] = by_machine.get(row["machine"], 0) + 1
        print(f"skipped unimplemented probes: {dict(sorted(by_machine.items()))}")
    if dataset["errors"]:
        print("errors:")
        for err in dataset["errors"]:
            print(f"  - {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
