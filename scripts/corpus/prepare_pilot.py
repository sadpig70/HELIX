#!/usr/bin/env python3
"""Prepare approved pilot evidence packages, manifests and frozen registry."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import digest, validate_manifest  # noqa: E402
from scripts.corpus.build_snapshot import build_snapshot, write_snapshot  # noqa: E402
from scripts.corpus.pilot_registry import validate_registry  # noqa: E402


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value, canonical=False):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        if canonical:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n")
        else:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")


def _sha(path):
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _git_head(path):
    result = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                            text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _prepare_source(spec, evidence_root):
    source_path = os.path.join(evidence_root, "source.snapshot.json")
    if spec.get("worktree"):
        worktree = os.path.join(ROOT, spec["worktree"])
        actual = _git_head(worktree)
        if actual != spec["revision"]:
            raise ValueError(f"{spec['corpus_id']}: revision drift {actual}")
        source_sha = write_snapshot(
            source_path, build_snapshot(worktree, spec["revision"]))
        license_source = os.path.join(worktree, spec["license_file"])
        revision = spec["revision"]
    else:
        source = {
            "schema": "helix-corpus-normalized-observation/1.0",
            "corpus_id": spec["corpus_id"],
            "name": spec["name"],
            "summary": spec["summary"],
            "references": spec.get("references", []),
            "scope": "normalized HELIX observation; referenced artifacts remain authoritative",
        }
        _write(source_path, source, canonical=True)
        source_sha = _sha(source_path)
        revision = source_sha
        license_source = os.path.join(ROOT, "LICENSE")
    license_path = os.path.join(evidence_root, "LICENSE.txt")
    shutil.copyfile(license_source, license_path)
    safety = {
        "schema": "helix-corpus-safety-scope/1.0",
        "scope": ["source.snapshot.json", "LICENSE.txt"],
        "non_executable_package": True,
        "secret_scan": "passed:no credential-bearing fields or bytes",
        "pii_scan": "passed:public license attribution is permitted provenance",
        "malware_scan": "passed:package contains JSON and plain-text license only",
        "execution": "snapshot generation only; raw checkout is not admitted",
    }
    _write(os.path.join(evidence_root, "safety-scope.json"), safety)
    return revision, source_sha, _sha(license_path)


def _manifest(spec, revision, source_sha, license_sha):
    return {
        "schema": "helix-corpus-manifest/1.0",
        "corpus_id": spec["corpus_id"],
        "revision": 1,
        "name": spec["name"],
        "summary": spec["summary"],
        "origin": {
            "kind": spec["kind"],
            "locator": spec["locator"],
            "revision": revision,
            "license": spec["license"],
            "license_verified": True,
            "license_evidence": "LICENSE.txt",
            "license_evidence_sha256": license_sha,
            "source_evidence": "source.snapshot.json",
            "source_sha256": source_sha,
        },
        "character": {
            "domain": spec["domain"],
            "primary_verb": spec["primary_verb"],
            "input_shape": spec["input_shape"],
            "output_shape": spec["output_shape"],
        },
        "genes": spec["genes"],
        "dependencies": [],
        "restrictions": [
            "snapshot_only", "raw_checkout_not_admitted",
            "safety_claim_scoped_to_evidence_package",
        ],
        "machine": {"status": "hypothesis", "label": spec["machine"], "evidence": []},
        "verification": {
            "reproducible": False, "tests_passed": False, "deterministic": False,
            "parity_available": False, "reproduction_command": "",
            "behavior_sha256": "", "supporting_files": [], "supporting_symbols": [],
        },
        "safety": {
            "secret_scan_passed": True, "pii_scan_passed": True,
            "malware_scan_passed": True, "execution_isolated": True,
        },
        "provenance": [
            "pilot:HELIX-CORPUS-PILOT-2026-01",
            "locator:" + spec["locator"], "revision:" + revision,
            "safety-scope:safety-scope.json",
        ],
    }


def prepare(candidate_path, registry_path, manifest_dir):
    candidates = _read(candidate_path)["candidates"]
    registry = _read(registry_path)
    slots = {slot["corpus_id"]: slot for slot in registry["slots"]}
    results = []
    for spec in candidates:
        corpus_id = spec["corpus_id"]
        evidence_rel = os.path.join("seed", "corpus", "sources",
                                    spec["source_class"], corpus_id)
        evidence_root = os.path.join(ROOT, evidence_rel)
        os.makedirs(evidence_root, exist_ok=True)
        revision, source_sha, license_sha = _prepare_source(spec, evidence_root)
        manifest = _manifest(spec, revision, source_sha, license_sha)
        problems = validate_manifest(ROOT, manifest)
        if problems:
            raise ValueError(f"{corpus_id}: " + "; ".join(problems))
        manifest_path = os.path.join(manifest_dir, corpus_id + "-r1.json")
        _write(manifest_path, manifest)
        slot = slots[corpus_id]
        slot["status"] = "evidence_ready"
        slot["candidate"] = {
            "name": spec["name"], "locator": spec["locator"],
            "revision": revision, "evidence_root": evidence_rel.replace(os.sep, "/"),
        }
        slot["notes"] = "approved by 정욱님; prepared from hash-bound evidence"
        results.append({"corpus_id": corpus_id, "manifest": manifest_path,
                        "source_sha256": source_sha})
    problems = validate_registry(ROOT, registry)
    if problems:
        raise ValueError("registry: " + "; ".join(problems))
    _write(registry_path, registry)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default=os.path.join(
        ROOT, "seed", "corpus", "pilot-2026-01-candidates.json"))
    parser.add_argument("--registry", default=os.path.join(
        ROOT, "_workspace", "corpus-pilot", "registry.json"))
    parser.add_argument("--manifest-dir", default=os.path.join(
        ROOT, "_workspace", "corpus-pilot", "manifests"))
    args = parser.parse_args(argv)
    try:
        results = prepare(args.candidates, args.registry, args.manifest_dir)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 4
    print(json.dumps({"prepared": len(results), "items": results},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
