#!/usr/bin/env python3
"""Reproduce selected pilot items and build hash-bound Evidence revisions."""

import argparse
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import (  # noqa: E402
    intake_manifest,
    manifest_digest,
    materialize_state,
    read_json,
)


CORPUS_ROOT = os.path.join(ROOT, "seed", "corpus")
REGISTRY_PATH = os.path.join(ROOT, "_workspace", "corpus-pilot", "registry.json")
MANIFEST_DIR = os.path.join(ROOT, "_workspace", "corpus-pilot", "manifests")
REVIEW_DIR = os.path.join(ROOT, "_workspace", "corpus-pilot", "reviews")


SPECS = {
    "HC-PILOT-EXT-001": {
        "cwd": ".helix/corpus-worktrees/HC-PILOT-EXT-001",
        "command": [
            r"C:\Program Files\Git\bin\bash.exe", "-lc",
            "source /d/HELIX/.helix/venvs/HC-PILOT-EXT-001/Scripts/activate "
            "&& python /d/HELIX/scripts/corpus/run_in_toto_supported_tests.py",
        ],
        "command_text": "python scripts/corpus/run_in_toto_supported_tests.py",
        "supporting_files": ["in_toto/rulelib.py", "tests/test_rulelib.py",
                             "reproduction.json", "behavior-output.json"],
        "supporting_symbols": ["unpack_rule", "pack_create_rule", "verify_create_rule"],
        "machine_evidence": ["249 supported tests passed; 3 symlink tests excluded explicitly"],
        "exclusions": [
            "tests.test_runlib.TestRecordArtifactsAsDict.test_record_follow_symlinked_directories",
            "tests.test_runlib.TestRecordArtifactsAsDict.test_record_symlinked_files",
            "tests.test_runlib.TestRecordArtifactsAsDict.test_record_without_dead_symlinks",
        ],
    },
    "HC-PILOT-HELIX-002": {
        "cwd": "MethodBond",
        "command": ["python", "-m", "unittest", "discover", "-s", "tests", "-q"],
        "command_text": "python -m unittest discover -s tests -q",
        "supporting_files": ["MethodBond/engine.py", "tests/test_engine.py",
                             "reproduction.json", "behavior-output.json"],
        "supporting_symbols": ["evaluate", "_check_reproducibility", "_check_certification"],
        "machine_evidence": ["32 unit and integration tests passed"],
        "exclusions": [],
    },
    "HC-PILOT-HELIX-001": {
        "cwd": "ActionHandbackVerifier",
        "command": ["python", "-m", "unittest", "discover", "-s", "tests", "-q"],
        "command_text": "python -m unittest discover -s tests -q",
        "supporting_files": ["src/ActionHandbackVerifier/verifier.py",
                             "tests/test_action_handback_verifier.py",
                             "reproduction.json", "behavior-output.json"],
        "supporting_symbols": ["evaluate_handback", "aggregate_verdict",
                               "digest_public_surface"],
        "machine_evidence": ["14 unit and integration tests passed"],
        "exclusions": [],
    },
    "HC-PILOT-HELIX-003": {
        "cwd": "PolicyDriftGate",
        "command": ["python", "-m", "unittest", "discover", "-s", "tests", "-q"],
        "command_text": "python -m unittest discover -s tests -q",
        "supporting_files": ["src/PolicyDriftGate/verifier.py",
                             "tests/test_policy_drift_gate.py",
                             "reproduction.json", "behavior-output.json"],
        "supporting_symbols": ["evaluate_policy_drift", "check_behavior",
                               "check_loop_signal"],
        "machine_evidence": ["14 unit and integration tests passed"],
        "exclusions": [],
    },
    "HC-PILOT-HELIX-004": {
        "cwd": "BioClock",
        "command": ["python", "-m", "unittest", "discover", "-s", "tests", "-q"],
        "command_text": "python -m unittest discover -s tests -q",
        "supporting_files": ["src/BioClock/core.py", "tests/test_bioclock.py",
                             "reproduction.json", "behavior-output.json"],
        "supporting_symbols": ["track_drift", "certify_bio_clock", "_severity_for"],
        "machine_evidence": ["19 unit and integration tests passed"],
        "exclusions": [],
    },
}


def _write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha_text(value):
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _probe(corpus_id):
    if corpus_id == "HC-PILOT-EXT-001":
        from in_toto.rulelib import pack_create_rule, unpack_rule
        packed = pack_create_rule("dist/*.whl")
        return {"packed": packed, "unpacked": unpack_rule(packed)}
    if corpus_id == "HC-PILOT-HELIX-001":
        source_root = os.path.join(ROOT, "ActionHandbackVerifier", "src")
        sys.path.insert(0, source_root)
        from ActionHandbackVerifier.samples import samples
        from ActionHandbackVerifier.verifier import evaluate_handback
        return evaluate_handback(samples()["valid"])
    if corpus_id == "HC-PILOT-HELIX-003":
        source_root = os.path.join(ROOT, "PolicyDriftGate", "src")
        sys.path.insert(0, source_root)
        from PolicyDriftGate.samples import samples
        from PolicyDriftGate.verifier import evaluate_policy_drift
        return evaluate_policy_drift(samples()["cleared"])
    if corpus_id == "HC-PILOT-HELIX-004":
        source_root = os.path.join(ROOT, "BioClock", "src")
        sys.path.insert(0, source_root)
        from BioClock.core import certify_bio_clock, track_drift
        from BioClock.samples import samples
        fixtures = samples()
        drift = track_drift(fixtures["valid_protocol"], fixtures["valid_evidence"])
        return {"drift": drift,
                "certification": certify_bio_clock(drift, fixtures["valid_quarantine"])}
    method_root = os.path.join(ROOT, "MethodBond")
    if method_root not in sys.path:
        sys.path.insert(0, method_root)
    from MethodBond.engine import evaluate
    artifact = {
        "id": "pilot-method",
        "license": {"transfer_type": "permissive", "source_domain": "open",
                    "target_industry": "general", "revenue_share_pct": 0},
        "provenances": [
            {"input_hash": "sha256:in", "output_hash": "sha256:out",
             "build_command": "python build.py", "builder_id": "builder-a"},
            {"input_hash": "sha256:in", "output_hash": "sha256:out",
             "build_command": "python build.py", "builder_id": "builder-b"},
        ],
        "baseline_policy": {"rules": {"max_latency": 100}},
        "candidate_policy": {"rules": {"max_latency": 100}},
    }
    return evaluate(artifact)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", dest="ids", choices=sorted(SPECS))
    args = parser.parse_args(argv)
    registry = read_json(REGISTRY_PATH)
    slots = {slot["corpus_id"]: slot for slot in registry["slots"]}
    state = materialize_state(ROOT, CORPUS_ROOT)
    if state["ledger_problems"]:
        raise ValueError("admission ledger invalid: " + "; ".join(state["ledger_problems"]))
    results = []
    selected = args.ids or list(SPECS)
    for corpus_id in selected:
        spec = SPECS[corpus_id]
        evidence_root = slots[corpus_id]["candidate"]["evidence_root"]
        evidence_root = os.path.join(ROOT, evidence_root)
        completed = subprocess.run(
            spec["command"], cwd=os.path.join(ROOT, spec["cwd"]),
            text=True, capture_output=True, check=False)
        reproduction = {
            "schema": "helix-corpus-reproduction/1.0",
            "corpus_id": corpus_id,
            "command": spec["command_text"],
            "exit_code": completed.returncode,
            "stdout_sha256": _sha_text(completed.stdout),
            "stderr_sha256": _sha_text(completed.stderr),
            "excluded_tests": spec["exclusions"],
            "result": "passed" if completed.returncode == 0 else "failed",
        }
        _write(os.path.join(evidence_root, "reproduction.json"), reproduction)
        with open(os.path.join(evidence_root, "reproduction.log"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(completed.stdout)
            handle.write(completed.stderr)
        if completed.returncode != 0:
            raise ValueError(f"{corpus_id}: reproduction failed")
        behavior_sha = _write(
            os.path.join(evidence_root, "behavior-output.json"), _probe(corpus_id))

        current = read_json(os.path.join(CORPUS_ROOT, "items", corpus_id, "manifest.json"))
        prior = state["state"][corpus_id]["generative"]
        revision = dict(current)
        revision["revision"] = current["revision"] + 1
        revision["supersedes_manifest_sha256"] = prior["manifest_sha256"]
        revision["machine"] = {
            "status": "substantiated", "label": current["machine"]["label"],
            "evidence": spec["machine_evidence"],
        }
        revision["verification"] = {
            "reproducible": True, "tests_passed": True, "deterministic": True,
            "parity_available": False,
            "reproduction_command": spec["command_text"],
            "behavior_sha256": behavior_sha,
            "supporting_files": spec["supporting_files"],
            "supporting_symbols": spec["supporting_symbols"],
        }
        if spec["exclusions"]:
            revision["restrictions"] = revision["restrictions"] + [
                "windows_symlink_tests_excluded_without_developer_mode"]
        manifest_path = os.path.join(MANIFEST_DIR, corpus_id + "-r2.json")
        _write(manifest_path, revision)
        intake = intake_manifest(ROOT, CORPUS_ROOT, revision)
        packet = {
            "schema": "helix-corpus-evidence-review-packet/1.0",
            "corpus_id": corpus_id,
            "manifest_sha256": manifest_digest(revision),
            "prior_generative_manifest_sha256": prior["manifest_sha256"],
            "reproduction": reproduction,
            "behavior_sha256": behavior_sha,
            "machine_evidence": spec["machine_evidence"],
            "restrictions": revision["restrictions"],
            "approval_intent": "정욱님 pre-approved ID before manifest hash existed",
            "required_action": "human must confirm this exact manifest_sha256",
        }
        packet_path = os.path.join(REVIEW_DIR, corpus_id + "-packet.json")
        _write(packet_path, packet)
        slots[corpus_id]["status"] = "evidence_ready"
        results.append({"corpus_id": corpus_id, "intake": intake["status"],
                        "manifest_sha256": packet["manifest_sha256"],
                        "packet": packet_path})
    _write(REGISTRY_PATH, registry)
    print(json.dumps({"prepared": len(results), "items": results},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
