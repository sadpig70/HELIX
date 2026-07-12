#!/usr/bin/env python3
"""Locked blind-holdout registry builder/validator for the HELIX Truth Plane.

Policy source of truth: docs/HOLDOUT-POLICY.md and
schemas/helix-holdout-registry.schema.json (P2_1). This module makes the policy
executable: it builds a policy-compliant cohort manifest, seals it with a
canonical-JSON SHA256 commitment, and validates any registry against schema,
policy semantics, the commitment lock, and the actual artifact bytes on disk.

Commitment semantics: the cohort commitment covers everything selection locks —
cohort identity/rule/cutoff, leakage control, scoring, reveal authority, and
each candidate's identity, source, eligibility, candidate-view hash, and oracle
commitment hash. Post-lock lifecycle fields (prediction receipt, reveal record,
oracle access, eligible->scored/protocol_violation status) are excluded so
sealing a prediction cannot break the lock, while deleting or replacing a
candidate, flipping an excluded candidate to eligible, or changing the
selection rule always changes the commitment.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import json
import os
import sys

try:  # package import (python -m core.helix_holdout) or library use
    from .helix_schema import validate_against_schema, schema_path
    from .helix_state_receipt import sha256_file
except ImportError:  # direct script run: python core/helix_holdout.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_schema import validate_against_schema, schema_path
    from core.helix_state_receipt import sha256_file

SCHEMA_NAME = "helix-holdout-registry"
SCHEMA_ID = "helix-holdout-registry/1.0"
POLICY_VERSION = "HELIX-HOLDOUT/1.0"
LIVE_MINIMUM_CANDIDATES = 20
FORBIDDEN_CANDIDATE_FIELDS = (
    "expected", "machines", "machine_id", "action", "expected_action",
    "platform", "platform_hint", "oracle_rationale",
)
ZERO_CREDIT_OUTCOMES = ("wrong", "abstain", "missing_artifact", "protocol_violation")
LOCKED_DENOMINATOR = "locked_eligible_candidates"
DEFAULT_LICENSE_ALLOWLIST = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause")


def canonical_json_bytes(value) -> bytes:
    """Canonical JSON bytes: sorted keys, no whitespace, UTF-8."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _candidate_lock_view(candidate: dict) -> dict:
    """Per-candidate projection covered by the cohort commitment.

    ``locked_status`` collapses the lifecycle: excluded stays excluded forever;
    eligible may later become scored/protocol_violation without breaking the lock.
    """
    return {
        "candidate_id": candidate["candidate_id"],
        "locked_status": "excluded" if candidate["status"] == "excluded" else "eligible",
        "source": candidate["source"],
        "eligibility": candidate["eligibility"],
        "candidate_view": {
            "path": candidate["candidate_view"]["path"],
            "sha256": candidate["candidate_view"]["sha256"],
        },
        "oracle_commitment": {
            "path": candidate["oracle_commitment"]["path"],
            "sha256": candidate["oracle_commitment"]["sha256"],
        },
    }


def commitment_view(registry: dict) -> dict:
    """Deterministic projection of everything the selection lock covers."""
    cohort = registry["cohort"]
    return {
        "schema": registry["schema"],
        "policy_version": registry["policy_version"],
        "cohort": {
            "cohort_id": cohort["cohort_id"],
            "kind": cohort["kind"],
            "selection_rule": cohort["selection_rule"],
            "selection_cutoff": cohort["selection_cutoff"],
            "minimum_candidates": cohort["minimum_candidates"],
        },
        "leakage_control": registry["leakage_control"],
        "scoring": registry["scoring"],
        "reveal_authority": registry["reveal_authority"],
        "candidates": sorted(
            (_candidate_lock_view(c) for c in registry["candidates"]),
            key=lambda view: view["candidate_id"]),
    }


def cohort_commitment(registry: dict) -> str:
    """SHA256 over the canonical commitment view. Same input -> same commitment."""
    return hashlib.sha256(canonical_json_bytes(commitment_view(registry))).hexdigest()


def lock_registry(registry: dict) -> dict:
    """Return a copy with cohort status=locked and the recomputed commitment."""
    locked = json.loads(json.dumps(registry))
    locked["cohort"]["status"] = "locked"
    locked["cohort"]["commitment_sha256"] = cohort_commitment(locked)
    return locked


def _forbidden_labels(value, forbidden) -> set:
    """Recursively collect forbidden label keys present in a candidate view."""
    found = set()
    if isinstance(value, dict):
        for key, sub in value.items():
            if key in forbidden:
                found.add(key)
            found |= _forbidden_labels(sub, forbidden)
    elif isinstance(value, list):
        for sub in value:
            found |= _forbidden_labels(sub, forbidden)
    return found


def _require_file(root: str, rel_path: str, role: str) -> str:
    full = rel_path if os.path.isabs(rel_path) else os.path.join(root, rel_path)
    if not os.path.isfile(full):
        raise ValueError(f"{role} file missing: {rel_path}")
    return full


def build_candidate(root: str, spec: dict, leakage_control: dict,
                    license_allowlist, seen_hashes: set, seen_families: set) -> dict:
    """Hash real artifacts and derive eligibility for one candidate spec.

    spec = {candidate_id, source: {kind, locator, immutable_revision, family_id,
    license_id, license_evidence_path[, artifact_path]}, candidate_view_path,
    oracle_path}. For kind=local_snapshot the locator is the artifact path.
    """
    source_spec = spec["source"]
    artifact_rel = source_spec.get("artifact_path", source_spec["locator"])
    artifact_sha = sha256_file(_require_file(root, artifact_rel, "source artifact"))
    license_sha = sha256_file(_require_file(
        root, source_spec["license_evidence_path"], "license evidence"))
    view_full = _require_file(root, spec["candidate_view_path"], "candidate view")
    view_sha = sha256_file(view_full)
    oracle_sha = sha256_file(_require_file(root, spec["oracle_path"], "oracle"))

    with open(view_full, "r", encoding="utf-8") as f:
        leaked = _forbidden_labels(
            json.load(f), set(leakage_control["forbidden_candidate_fields"]))
    if leaked:
        raise ValueError(
            f"{spec['candidate_id']}: candidate view leaks labels {sorted(leaked)}")
    if spec["candidate_view_path"] == spec["oracle_path"] or view_sha == oracle_sha:
        raise ValueError(
            f"{spec['candidate_id']}: candidate view and oracle are not isolated")

    excluded_hashes = set(leakage_control["excluded_source_hashes"])
    excluded_families = set(leakage_control.get("excluded_family_ids", []))
    family_id = source_spec["family_id"]
    # Selection-rule exclusions (e.g. archived/fork/README-size filters) that the
    # four eligibility booleans cannot express; they force excluded status.
    reasons = list(spec.get("excluded_reasons") or [])
    source_hash_unseen = artifact_sha not in excluded_hashes and artifact_sha not in seen_hashes
    if not source_hash_unseen:
        reasons.append("known or duplicate source artifact hash")
    family_unseen = family_id not in excluded_families and family_id not in seen_families
    if not family_unseen:
        reasons.append("known or duplicate source family")
    registry_overlap = artifact_sha in excluded_hashes or family_id in excluded_families
    if registry_overlap:
        reasons.append("overlap with excluded registries")
    license_allowed = source_spec["license_id"] in set(license_allowlist)
    if not license_allowed:
        reasons.append(f"license {source_spec['license_id']} not in allowlist")

    eligible = (source_hash_unseen and family_unseen and not registry_overlap
                and license_allowed and not spec.get("excluded_reasons"))
    if eligible:
        seen_hashes.add(artifact_sha)
        seen_families.add(family_id)

    return {
        "candidate_id": spec["candidate_id"],
        "status": "eligible" if eligible else "excluded",
        "source": {
            "kind": source_spec["kind"],
            "locator": source_spec["locator"],
            "immutable_revision": source_spec["immutable_revision"],
            "artifact_sha256": artifact_sha,
            "family_id": family_id,
            "license_id": source_spec["license_id"],
            "license_evidence_path": source_spec["license_evidence_path"],
            "license_evidence_sha256": license_sha,
        },
        "eligibility": {
            "source_hash_unseen": source_hash_unseen,
            "family_unseen": family_unseen,
            "registry_overlap": registry_overlap,
            "license_allowed": license_allowed,
            "reasons": reasons,
        },
        "candidate_view": {
            "path": spec["candidate_view_path"],
            "sha256": view_sha,
            "builder_role": "candidate_builder",
            "label_free": True,
        },
        "oracle_commitment": {
            "path": spec["oracle_path"],
            "sha256": oracle_sha,
            "author_role": "oracle_author",
            "access": "sealed",
        },
        "prediction_receipt": {
            "status": "absent", "path": None, "sha256": None,
            "predictor_role": "predictor",
        },
        "reveal": {"status": "sealed", "authorized_by": [], "receipt_sha256": None},
    }


def build_registry(root: str, cohort: dict, leakage_control: dict, scoring: dict,
                   reveal_authority: dict, candidate_specs: list,
                   license_allowlist=DEFAULT_LICENSE_ALLOWLIST) -> dict:
    """Build and lock a policy-compliant registry from real artifact files."""
    seen_hashes, seen_families = set(), set()
    candidates = [
        build_candidate(root, spec, leakage_control, license_allowlist,
                        seen_hashes, seen_families)
        for spec in candidate_specs
    ]
    registry = {
        "schema": SCHEMA_ID,
        "policy_version": POLICY_VERSION,
        "cohort": {
            "cohort_id": cohort["cohort_id"],
            "kind": cohort["kind"],
            "selection_rule": cohort["selection_rule"],
            "selection_cutoff": cohort["selection_cutoff"],
            "commitment_sha256": "",
            "minimum_candidates": cohort["minimum_candidates"],
            "status": "draft",
        },
        "leakage_control": leakage_control,
        "scoring": scoring,
        "reveal_authority": reveal_authority,
        "candidates": candidates,
    }
    return lock_registry(registry)


def locked_eligible_candidates(registry: dict) -> list:
    """Candidates that were eligible at lock (the immutable denominator)."""
    return [c for c in registry["candidates"] if c["status"] != "excluded"]


def _policy_problems(registry: dict) -> list:
    problems = []
    cohort = registry["cohort"]
    eligible = locked_eligible_candidates(registry)
    if cohort["kind"] == "live":
        if cohort["status"] not in ("locked", "scored"):
            problems.append("live cohort must be locked before use")
        if cohort["minimum_candidates"] < LIVE_MINIMUM_CANDIDATES:
            problems.append("live cohort minimum_candidates must be >= 20")
        if len(eligible) < max(LIVE_MINIMUM_CANDIDATES, cohort["minimum_candidates"]):
            problems.append(
                f"live cohort has {len(eligible)} locked eligible candidates, "
                f"requires >= {max(LIVE_MINIMUM_CANDIDATES, cohort['minimum_candidates'])}")

    forbidden = set(registry["leakage_control"]["forbidden_candidate_fields"])
    if not set(FORBIDDEN_CANDIDATE_FIELDS) <= forbidden:
        problems.append("forbidden candidate label set is incomplete")
    credits = registry["scoring"]["credits"]
    for outcome in ZERO_CREDIT_OUTCOMES:
        if credits[outcome] != 0:
            problems.append(f"{outcome} success credit must be 0")
    if registry["scoring"]["coverage_denominator"] != LOCKED_DENOMINATOR:
        problems.append("coverage denominator can exclude locked candidates")
    if registry["scoring"]["score_denominator"] != LOCKED_DENOMINATOR:
        problems.append("score denominator can exclude locked candidates")

    excluded_hashes = set(registry["leakage_control"]["excluded_source_hashes"])
    excluded_families = set(registry["leakage_control"].get("excluded_family_ids", []))
    seen_ids, eligible_hashes, eligible_families = set(), {}, {}
    for candidate in registry["candidates"]:
        cid = candidate["candidate_id"]
        if cid in seen_ids:
            problems.append(f"{cid}: duplicate candidate_id")
        seen_ids.add(cid)
        source = candidate["source"]
        eligibility = candidate["eligibility"]
        view = candidate["candidate_view"]
        oracle = candidate["oracle_commitment"]
        prediction = candidate["prediction_receipt"]
        reveal = candidate["reveal"]

        if view["path"] == oracle["path"] or view["sha256"] == oracle["sha256"]:
            problems.append(f"{cid}: candidate and oracle are not isolated")
        if not source["immutable_revision"] or not source["license_evidence_sha256"]:
            problems.append(f"{cid}: source or license evidence is not immutable")

        if candidate["status"] != "excluded":
            if source["artifact_sha256"] in excluded_hashes:
                problems.append(f"{cid}: known source hash must be excluded")
            if source["family_id"] in excluded_families:
                problems.append(f"{cid}: known source family must be excluded")
            supported = (eligibility["source_hash_unseen"] and eligibility["family_unseen"]
                         and not eligibility["registry_overlap"]
                         and eligibility["license_allowed"])
            if not supported:
                problems.append(f"{cid}: eligibility claims do not support eligible status")
            other = eligible_hashes.get(source["artifact_sha256"])
            if other:
                problems.append(f"{cid}: duplicate eligible source hash with {other}")
            eligible_hashes[source["artifact_sha256"]] = cid
            other = eligible_families.get(source["family_id"])
            if other:
                problems.append(f"{cid}: duplicate eligible source family with {other}")
            eligible_families[source["family_id"]] = cid

        if oracle["access"] == "sealed" and reveal["status"] == "revealed":
            problems.append(f"{cid}: reveal contradicts sealed oracle")
        if oracle["access"] == "revealed" and reveal["status"] != "revealed":
            problems.append(f"{cid}: oracle revealed without a reveal receipt")
        if reveal["status"] == "revealed":
            if prediction["status"] != "sealed" or not prediction["sha256"]:
                problems.append(f"{cid}: reveal before sealed prediction")
            if len(reveal["authorized_by"]) < registry["reveal_authority"]["required_approvals"]:
                problems.append(f"{cid}: insufficient reveal approvals")
            if not reveal["receipt_sha256"]:
                problems.append(f"{cid}: reveal without receipt hash")
    return problems


def _commitment_problems(registry: dict) -> list:
    cohort = registry["cohort"]
    if cohort["status"] not in ("locked", "scored"):
        return []
    expected = cohort.get("commitment_sha256")
    actual = cohort_commitment(registry)
    if expected != actual:
        return ["cohort commitment mismatch: locked selection was modified "
                f"(expected {expected}, recomputed {actual})"]
    return []


def _hash_problem(root: str, cid: str, role: str, rel_path: str, expected: str) -> list:
    full = rel_path if os.path.isabs(rel_path) else os.path.join(root, rel_path)
    if not os.path.isfile(full):
        return [f"{cid}: {role} missing: {rel_path}"]
    actual = sha256_file(full)
    if actual != expected:
        return [f"{cid}: {role} hash mismatch: {rel_path}"]
    return []


def _artifact_problems(root: str, registry: dict) -> list:
    """Verify recorded hashes against the actual bytes on disk."""
    problems = []
    forbidden = set(registry["leakage_control"]["forbidden_candidate_fields"])
    for candidate in registry["candidates"]:
        cid = candidate["candidate_id"]
        source = candidate["source"]
        if source["kind"] == "local_snapshot":
            problems += _hash_problem(root, cid, "source artifact",
                                      source["locator"], source["artifact_sha256"])
        problems += _hash_problem(root, cid, "license evidence",
                                  source["license_evidence_path"],
                                  source["license_evidence_sha256"])
        view = candidate["candidate_view"]
        view_problems = _hash_problem(root, cid, "candidate view",
                                      view["path"], view["sha256"])
        problems += view_problems
        if not view_problems:
            full = view["path"] if os.path.isabs(view["path"]) else os.path.join(root, view["path"])
            try:
                with open(full, "r", encoding="utf-8") as f:
                    leaked = _forbidden_labels(json.load(f), forbidden)
            except ValueError:
                leaked = set()
                problems.append(f"{cid}: candidate view is not valid JSON")
            if leaked:
                problems.append(f"{cid}: candidate view leaks labels {sorted(leaked)}")
        oracle = candidate["oracle_commitment"]
        problems += _hash_problem(root, cid, "oracle commitment",
                                  oracle["path"], oracle["sha256"])
    return problems


def validate_registry(root: str, registry: dict, check_artifacts: bool = True) -> list:
    """Full registry validation: schema + policy + commitment lock + artifacts."""
    problems = [f"schema: {p}" for p in validate_against_schema(
        registry, schema_path(root, SCHEMA_NAME))]
    if problems:
        return problems  # shape is broken; deeper checks would be noise
    problems += _policy_problems(registry)
    problems += _commitment_problems(registry)
    if check_artifacts:
        problems += _artifact_problems(root, registry)
    return sorted(problems)


def _main(argv) -> int:
    if len(argv) < 2:
        print("usage: python core/helix_holdout.py <registry.json> [root]")
        return 2
    root = os.path.abspath(argv[2] if len(argv) > 2 else ".")
    with open(argv[1], "r", encoding="utf-8") as f:
        registry = json.load(f)
    problems = validate_registry(root, registry)
    eligible = locked_eligible_candidates(registry)
    print(f"=== HELIX holdout registry ({argv[1]}) ===")
    print(f"  cohort: {registry['cohort']['cohort_id']} "
          f"kind={registry['cohort']['kind']} status={registry['cohort']['status']}")
    print(f"  locked eligible candidates: {len(eligible)} / {len(registry['candidates'])}")
    print(f"  commitment: {registry['cohort'].get('commitment_sha256')}")
    if problems:
        print("\nFAIL — problems:")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("\nPASS — registry is schema-valid, policy-compliant, and lock-consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
