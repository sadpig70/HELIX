#!/usr/bin/env python3
"""Create and validate the fixed 24-slot HELIX corpus pilot registry."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_schema import validate_against_schema, schema_path  # noqa: E402


SCHEMA = "helix-corpus-pilot-registry/1.0"
CLASS_SPECS = (
    ("external_oss", "EXT", 8, "evidence"),
    ("helix_generated", "HELIX", 6, "evidence"),
    ("operational_problem", "PROB", 4, "generative"),
    ("failure_refutation", "FAIL", 3, "generative"),
    ("research_mechanism", "RES", 3, "generative"),
)
EXPECTED_COUNTS = {name: count for name, _, count, _ in CLASS_SPECS}


def registry_template(pilot_id="HELIX-CORPUS-PILOT-2026-01"):
    slots = []
    for source_class, prefix, count, target in CLASS_SPECS:
        for number in range(1, count + 1):
            slots.append({
                "corpus_id": f"HC-PILOT-{prefix}-{number:03d}",
                "source_class": source_class,
                "status": "unassigned",
                "admission_target": target,
                "candidate": None,
                "notes": "",
            })
    return {
        "schema": SCHEMA,
        "pilot_id": pilot_id,
        "frozen": True,
        "targets": {
            "candidate_count": 24,
            "generative_min": 12,
            "evidence_min": 5,
        },
        "slots": slots,
    }


def expected_ids():
    return {slot["corpus_id"] for slot in registry_template()["slots"]}


def validate_registry(repo_root, registry):
    problems = validate_against_schema(
        registry, schema_path(repo_root, "corpus-pilot-registry"))
    if problems:
        return sorted(set(problems))
    if registry.get("frozen") is not True:
        problems.append("registry must be frozen before pilot execution")
    slots = registry.get("slots", [])
    ids = [slot.get("corpus_id") for slot in slots]
    if len(slots) != 24:
        problems.append(f"slot count must be 24, got {len(slots)}")
    if len(ids) != len(set(ids)):
        problems.append("corpus_id values must be unique")
    missing = sorted(expected_ids() - set(ids))
    unexpected = sorted(set(ids) - expected_ids())
    if missing:
        problems.append("missing fixed slots: " + ",".join(missing))
    if unexpected:
        problems.append("unexpected fixed slots: " + ",".join(unexpected))

    counts = {}
    evidence_targets = 0
    identities = {}
    for slot in slots:
        source_class = slot.get("source_class")
        counts[source_class] = counts.get(source_class, 0) + 1
        evidence_targets += slot.get("admission_target") == "evidence"
        candidate = slot.get("candidate")
        if slot.get("status") == "unassigned" and candidate is not None:
            problems.append(f"{slot.get('corpus_id')}: unassigned slot has candidate")
        if slot.get("status") != "unassigned" and not candidate:
            problems.append(f"{slot.get('corpus_id')}: assigned status requires candidate")
        if candidate:
            for key in ("name", "locator", "revision", "evidence_root"):
                if not str(candidate.get(key, "")).strip():
                    problems.append(f"{slot.get('corpus_id')}: candidate.{key} required")
            identity = (candidate.get("locator"), candidate.get("revision"))
            identities.setdefault(identity, []).append(slot.get("corpus_id"))
    if counts != EXPECTED_COUNTS:
        problems.append(f"source class counts must be {EXPECTED_COUNTS}, got {counts}")
    if evidence_targets < registry.get("targets", {}).get("evidence_min", 5):
        problems.append("evidence target slots are below evidence_min")
    for identity, corpus_ids in sorted(identities.items()):
        if len(corpus_ids) > 1:
            problems.append(
                f"duplicate candidate locator/revision {identity}: {','.join(corpus_ids)}")
    return sorted(set(problems))


def write_json(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--out", required=True)
    init.add_argument("--pilot-id", default="HELIX-CORPUS-PILOT-2026-01")
    validate = sub.add_parser("validate")
    validate.add_argument("--registry", required=True)
    args = parser.parse_args(argv)
    if args.command == "init":
        if os.path.exists(args.out):
            parser.error(f"refusing to overwrite existing registry: {args.out}")
        write_json(args.out, registry_template(args.pilot_id))
        print(args.out)
        return 0
    with open(args.registry, "r", encoding="utf-8") as handle:
        registry = json.load(handle)
    problems = validate_registry(ROOT, registry)
    print(json.dumps({"valid": not problems, "problems": problems},
                     ensure_ascii=False, indent=2))
    return 0 if not problems else 4


if __name__ == "__main__":
    sys.exit(main())
