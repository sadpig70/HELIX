#!/usr/bin/env python3
"""Generate the deterministic synthetic live-size holdout fixture (P2_2).

Writes seed/evaluation/holdout/** (sources, licenses, candidate views, oracles)
and the locked registry seed/evaluation/holdout-registry.json via
core.helix_holdout.build_registry. No clock, network, or randomness: rerunning
produces byte-identical files, so the cohort commitment is reproducible.

The fixture exists to verify locking semantics before any real external source
collection. Oracle files carry synthetic labels only; the label vocabulary
never appears in candidate views (the builder refuses leaky views).

CLI:
    python scripts/evaluate/build_synthetic_holdout.py [--root PATH]
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_holdout import build_registry, sha256_file  # noqa: E402

BASE_REL = "seed/evaluation/holdout"
REGISTRY_REL = "seed/evaluation/holdout-registry.json"
LICENSE_TEXT = (
    "MIT License (synthetic evidence)\n\n"
    "Copyright (c) synthetic holdout fixture\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    "of this software to deal in the software without restriction.\n"
)
OPERATION_POOL = (
    "append_entry", "verify_chain", "route_request", "clear_obligation",
    "score_candidate", "attest_claim", "bound_flow", "price_unit",
    "gate_predicate", "aggregate_tier", "emit_receipt", "replay_ledger",
)


def _write(root: str, rel: str, text: str) -> str:
    full = os.path.join(root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return rel


def _source_text(index: int, family: str) -> str:
    ops = [OPERATION_POOL[(index + k) % len(OPERATION_POOL)] for k in range(3)]
    return json.dumps({
        "name": f"synthetic-source-{index:03d}",
        "family": family,
        "readme": f"Synthetic project {index:03d}: {', '.join(ops)} over a local store.",
        "operations": ops,
        "entrypoints": [f"cli_{op}" for op in ops],
    }, ensure_ascii=False, indent=2) + "\n"


def _view_text(candidate_id: str, index: int, locator: str, revision: str) -> str:
    ops = [OPERATION_POOL[(index + k) % len(OPERATION_POOL)] for k in range(3)]
    return json.dumps({
        "candidate_id": candidate_id,
        "provenance": {"locator": locator, "immutable_revision": revision},
        "observed_operations": ops,
        "observed_inputs": [f"{op}_request" for op in ops],
        "observed_outputs": [f"{op}_receipt" for op in ops],
        "invariants": [f"{ops[0]} is append-only", f"{ops[1]} is deterministic"],
        "sample_behavior": f"processes {ops[0]} then emits {ops[2]} evidence",
    }, ensure_ascii=False, indent=2) + "\n"


def _oracle_text(candidate_id: str, index: int) -> str:
    return json.dumps({
        "candidate_id": candidate_id,
        "expected": {
            "action": "BUILD_ON_PLATFORM" if index % 2 else "DEFER",
            "machines": [f"M{(index % 15) + 1}"],
        },
        "oracle_rationale": f"synthetic oracle label for candidate {index:03d}",
    }, ensure_ascii=False, indent=2) + "\n"


def _candidate_files(root: str, candidate_id: str, index: int, family: str) -> dict:
    source_rel = _write(root, f"{BASE_REL}/sources/{candidate_id}.json",
                        _source_text(index, family))
    revision = f"synthetic-snapshot-{index:03d}"
    view_rel = _write(root, f"{BASE_REL}/candidates/{candidate_id}.view.json",
                      _view_text(candidate_id, index, source_rel, revision))
    oracle_rel = _write(root, f"{BASE_REL}/oracles/{candidate_id}.oracle.json",
                        _oracle_text(candidate_id, index))
    return {"source_rel": source_rel, "view_rel": view_rel,
            "oracle_rel": oracle_rel, "revision": revision}


def generate(root: str, eligible_count: int = 20) -> dict:
    """Write the synthetic fixture tree under ``root`` and return the locked registry."""
    license_rel = _write(root, f"{BASE_REL}/licenses/MIT-synthetic.txt", LICENSE_TEXT)

    specs = []
    for index in range(1, eligible_count + 1):
        candidate_id = f"SYN-{index:03d}"
        family = f"synthetic-family-{index:03d}"
        files = _candidate_files(root, candidate_id, index, family)
        specs.append({
            "candidate_id": candidate_id,
            "source": {
                "kind": "local_snapshot",
                "locator": files["source_rel"],
                "immutable_revision": files["revision"],
                "family_id": family,
                "license_id": "MIT",
                "license_evidence_path": license_rel,
            },
            "candidate_view_path": files["view_rel"],
            "oracle_path": files["oracle_rel"],
        })

    # Injected exclusions: one known-hash overlap, one known-family overlap.
    known_hash_files = _candidate_files(root, "SYN-KNOWN-HASH", 901, "synthetic-family-901")
    known_family_files = _candidate_files(root, "SYN-KNOWN-FAMILY", 902, "known-family-902")
    specs.append({
        "candidate_id": "SYN-KNOWN-HASH",
        "source": {
            "kind": "local_snapshot",
            "locator": known_hash_files["source_rel"],
            "immutable_revision": known_hash_files["revision"],
            "family_id": "synthetic-family-901",
            "license_id": "MIT",
            "license_evidence_path": license_rel,
        },
        "candidate_view_path": known_hash_files["view_rel"],
        "oracle_path": known_hash_files["oracle_rel"],
    })
    specs.append({
        "candidate_id": "SYN-KNOWN-FAMILY",
        "source": {
            "kind": "local_snapshot",
            "locator": known_family_files["source_rel"],
            "immutable_revision": known_family_files["revision"],
            "family_id": "known-family-902",
            "license_id": "MIT",
            "license_evidence_path": license_rel,
        },
        "candidate_view_path": known_family_files["view_rel"],
        "oracle_path": known_family_files["oracle_rel"],
    })

    known_hash = sha256_file(os.path.join(root, known_hash_files["source_rel"]))
    registry = build_registry(
        root,
        cohort={
            "cohort_id": "LIVE-SYNTH-P2-2-001",
            "kind": "live",
            "selection_rule": ("Synthetic live-size cohort generated by "
                               "scripts/evaluate/build_synthetic_holdout.py to verify "
                               "locking semantics before real source collection"),
            "selection_cutoff": "synthetic-sequence-p2-2",
            "minimum_candidates": 20,
        },
        leakage_control={
            "excluded_registries": [
                "seed/condense/layered-corpus.json",
                "seed/condense/forward-candidate-artifacts.json",
            ],
            "excluded_source_hashes": [known_hash],
            "excluded_family_ids": ["known-family-902"],
            "forbidden_candidate_fields": [
                "expected", "machines", "machine_id", "action", "expected_action",
                "platform", "platform_hint", "oracle_rationale",
            ],
            "predictor_forbidden_paths": [f"{BASE_REL}/oracles"],
            "overlap_policy": "exclude_locked_no_replacement",
        },
        scoring={
            "coverage_denominator": "locked_eligible_candidates",
            "score_denominator": "locked_eligible_candidates",
            "credits": {"exact": 1, "wrong": 0, "abstain": 0,
                        "missing_artifact": 0, "protocol_violation": 0},
            "minimum_coverage": 0.8,
            "minimum_macro_f1": 0.8,
        },
        reveal_authority={
            "required_approvals": 1,
            "allowed_roles": ["reveal_approver"],
            "prediction_seal_required": True,
            "commitment_match_required": True,
        },
        candidate_specs=specs,
    )
    _write(root, REGISTRY_REL,
           json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    return registry


def _main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--eligible", type=int, default=20)
    args = parser.parse_args(argv[1:])
    registry = generate(os.path.abspath(args.root), args.eligible)
    eligible = [c for c in registry["candidates"] if c["status"] != "excluded"]
    print(f"registry: {REGISTRY_REL}")
    print(f"locked eligible candidates: {len(eligible)} / {len(registry['candidates'])}")
    print(f"commitment: {registry['cohort']['commitment_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
