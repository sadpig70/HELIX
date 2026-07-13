#!/usr/bin/env python3
"""Typed receipt chain for the five existing HELIX platform stages."""

import hashlib

from .helix_holdout import canonical_json_bytes

SCHEMA_ID = "helix-platform-composition/1.0"
STAGES = ("route", "clear", "certify", "attest", "score")


def _digest(value) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def compose(transaction_id: str, initial_input: dict, stages: list) -> dict:
    problems = []
    accepted = []
    parent = _digest(initial_input)
    failed = False
    for index, expected_name in enumerate(STAGES):
        if index >= len(stages):
            problems.append(f"missing stage: {expected_name}")
            break
        stage = stages[index]
        if failed:
            problems.append(f"stage present after failure: {stage.get('stage')}")
            continue
        if stage.get("stage") != expected_name:
            problems.append(f"stage order mismatch: expected {expected_name}")
        if stage.get("transaction_id") != transaction_id:
            problems.append(f"{expected_name}: transaction_id mismatch")
        if stage.get("parent_sha256") != parent:
            problems.append(f"{expected_name}: provenance parent mismatch")
        body = {k: v for k, v in stage.items() if k != "receipt_sha256"}
        if stage.get("receipt_sha256") != _digest(body):
            problems.append(f"{expected_name}: receipt seal broken")
        accepted.append(stage)
        parent = stage.get("receipt_sha256")
        failed = stage.get("status") != "passed"
        if failed:
            break
    if len(stages) > len(accepted):
        problems.append("later stages must not execute after a failure")
    result = {"schema": SCHEMA_ID, "transaction_id": transaction_id,
              "initial_input_sha256": _digest(initial_input),
              "stage_receipts": [s.get("receipt_sha256") for s in accepted],
              "status": "passed" if not failed and not problems
              and len(accepted) == len(STAGES)
              else "failed", "problems": sorted(set(problems))}
    result["composition_sha256"] = _digest(result)
    return result


def build_stage(stage: str, transaction_id: str, parent_sha256: str,
                output: dict, status: str = "passed") -> dict:
    if stage not in STAGES or status not in ("passed", "failed"):
        raise ValueError("invalid platform stage or status")
    body = {"stage": stage, "transaction_id": transaction_id,
            "parent_sha256": parent_sha256, "output": output,
            "status": status}
    body["receipt_sha256"] = _digest(body)
    return body
