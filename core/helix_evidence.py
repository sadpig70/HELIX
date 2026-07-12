#!/usr/bin/env python3
"""Evidence manifest contract for the HELIX Constitution (T2 governance).

Policy source of truth: .pgf/DESIGN-HELIXDirection.md (EvidenceManifest node)
and the T2 gate rule "missing/mismatched artifact hash는 항상 DENY". A manifest
binds the artifacts that justify ONE action intent (by canonical intent
digest) to their content hashes, issuer, provenance, and policy version, and
is sealed with a canonical-JSON SHA256.

Fail-closed verification: an empty artifact list, a missing file, or a hash or
size mismatch is a problem — evidence that cannot be re-verified against the
actual bytes on disk can never authorize anything. Receipt-backed provenance
(state/trial/reduction receipts, command outputs) must carry a non-null
reference (the receipt hash or replay command) so every artifact is traceable
to its producer.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import json
import os
import sys

try:  # package import (python -m core.helix_evidence) or library use
    from .helix_constitution import intent_digest
    from .helix_holdout import canonical_json_bytes
    from .helix_schema import validate_against_schema, schema_path
    from .helix_state_receipt import sha256_file
except ImportError:  # direct script run: python core/helix_evidence.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_constitution import intent_digest
    from core.helix_holdout import canonical_json_bytes
    from core.helix_schema import validate_against_schema, schema_path
    from core.helix_state_receipt import sha256_file

SCHEMA_NAME = "evidence-manifest"
SCHEMA_ID = "helix-evidence-manifest/1.0"
POLICY_VERSION = "HELIX-CONSTITUTION/1.0"
RECEIPT_ORIGINS = ("state_receipt", "trial_receipt", "reduction_receipt",
                   "command_output")


def seal_manifest(manifest: dict) -> dict:
    """Return a copy sealed by SHA256 over canonical JSON minus the seal itself."""
    sealed = dict(manifest)
    sealed.pop("manifest_sha256", None)
    sealed["manifest_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_manifest_seal(manifest: dict) -> bool:
    expected = manifest.get("manifest_sha256")
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _full_path(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def build_evidence_manifest(root: str, manifest_id: str, intent: dict,
                            issuer: dict, artifact_specs: list) -> dict:
    """Hash real artifact files and seal a manifest bound to one intent.

    artifact_specs: [{role, path, provenance: {origin, reference}}, ...].
    Fails fast on a missing file — evidence is built from bytes that exist.
    """
    if not artifact_specs:
        raise ValueError("evidence manifest requires at least one artifact")
    artifacts = []
    seen_paths = set()
    for spec in artifact_specs:
        path = spec["path"]
        if path in seen_paths:
            raise ValueError(f"duplicate evidence artifact path: {path}")
        seen_paths.add(path)
        full = _full_path(root, path)
        if not os.path.isfile(full):
            raise ValueError(f"evidence artifact missing: {path}")
        provenance = spec["provenance"]
        if provenance["origin"] in RECEIPT_ORIGINS and not provenance.get("reference"):
            raise ValueError(f"{path}: provenance origin {provenance['origin']} "
                             "requires a reference")
        artifacts.append({
            "role": spec["role"],
            "path": path,
            "sha256": sha256_file(full),
            "bytes": os.path.getsize(full),
            "provenance": {"origin": provenance["origin"],
                           "reference": provenance.get("reference")},
        })
    return seal_manifest({
        "schema": SCHEMA_ID,
        "manifest_id": manifest_id,
        "policy_version": POLICY_VERSION,
        "intent_digest": intent_digest(intent),
        "issuer": {"kind": issuer["kind"], "id": issuer["id"]},
        "artifacts": artifacts,
    })


def verify_evidence_manifest(root: str, manifest: dict, intent: dict = None) -> list:
    """Fail-closed re-verification against the actual bytes on disk.

    Empty list == every artifact re-verifies and the seal, binding, and
    provenance rules hold. Any problem means the evidence cannot authorize.
    """
    problems = [f"schema: {p}" for p in validate_against_schema(
        manifest, schema_path(root, SCHEMA_NAME))]
    if problems:
        return sorted(problems)

    if not verify_manifest_seal(manifest):
        problems.append("manifest seal is broken")
    if not manifest["manifest_id"].strip():
        problems.append("manifest_id must be non-empty")
    if not manifest["issuer"]["id"].strip():
        problems.append("issuer.id must be non-empty")
    if not manifest["artifacts"]:
        problems.append("empty evidence: no artifacts can never authorize")
    if intent is not None and intent_digest(intent) != manifest["intent_digest"]:
        problems.append("intent binding mismatch: manifest justifies a "
                        "different intent")

    seen_paths = set()
    for artifact in manifest["artifacts"]:
        path = artifact["path"]
        label = f"artifact {artifact['role']} ({path})"
        if not artifact["role"].strip() or not path.strip():
            problems.append(f"{label}: role and path must be non-empty")
            continue
        if path in seen_paths:
            problems.append(f"{label}: duplicate artifact path")
        seen_paths.add(path)
        provenance = artifact["provenance"]
        if provenance["origin"] in RECEIPT_ORIGINS and not provenance["reference"]:
            problems.append(f"{label}: provenance {provenance['origin']} "
                            "requires a reference")
        full = _full_path(root, path)
        if not os.path.isfile(full):
            problems.append(f"{label}: missing on disk (fail-closed: DENY)")
            continue
        if sha256_file(full) != artifact["sha256"]:
            problems.append(f"{label}: content hash mismatch (fail-closed: DENY)")
        if os.path.getsize(full) != artifact["bytes"]:
            problems.append(f"{label}: byte length mismatch")
    return sorted(problems)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _main(argv) -> int:
    if len(argv) < 2:
        print("usage: python core/helix_evidence.py <manifest.json> "
              "[intent.json] [root]")
        return 2
    manifest = _load_json(argv[1])
    intent = _load_json(argv[2]) if len(argv) > 2 else None
    root = os.path.abspath(argv[3] if len(argv) > 3 else ".")
    problems = verify_evidence_manifest(root, manifest, intent)
    print(f"=== HELIX evidence manifest ({manifest.get('manifest_id')}) ===")
    print(f"  intent_digest: {manifest.get('intent_digest')}")
    print(f"  artifacts:     {len(manifest.get('artifacts', []))}")
    print(f"  seal:          {manifest.get('manifest_sha256')}")
    if problems:
        print("\nFAIL — problems (evidence cannot authorize):")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("\nPASS — every artifact re-verifies; binding and seal hold.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
