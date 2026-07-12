#!/usr/bin/env python3
"""Execution plans for the HELIX Actuation Plane (T3).

Policy source of truth: _workspace/HELIXDirection_process_plan.md §P4_1
("dry-run diff, side effects, rollback plan"). Before any authorized intent
may touch the filesystem, its exact planned effects are sealed:

- effects: per-path operation (create/modify/delete) with planned bytes —
  every path must fall inside the intent's approved write scope and the
  whole plan must fit the intent's budget (violations fail fast at build);
- dry-run preconditions: create targets must not exist yet, modify/delete
  targets must exist — verified against the real filesystem at build time
  and re-checkable immediately before actuation;
- rollback: the pre-execution bytes of every modify/delete target are stored
  at an IMMUTABLE content-addressed snapshot path ({sha256}.bin), so rollback
  evidence can never drift with living documents (T2 verification lesson);
  a created file's rollback is its deletion.

A plan can only exist chained to an authorizing GateResult whose decision is
ALLOW or SANDBOX and whose intent digest matches — no gate, no plan.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_execution_plan) or library use
    from .helix_authorization import verify_gate_result_seal
    from .helix_constitution import intent_digest
    from .helix_holdout import canonical_json_bytes
    from .helix_state_receipt import sha256_file
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_authorization import verify_gate_result_seal
    from core.helix_constitution import intent_digest
    from core.helix_holdout import canonical_json_bytes
    from core.helix_state_receipt import sha256_file

SCHEMA_ID = "helix-execution-plan/1.0"
OPS = ("create", "modify", "delete")
ACTUATABLE_DECISIONS = ("ALLOW", "SANDBOX")


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("plan_sha256", None)
    sealed["plan_sha256"] = hashlib.sha256(canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_plan_seal(plan: dict) -> bool:
    expected = plan.get("plan_sha256")
    body = {k: v for k, v in plan.items() if k != "plan_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _portable(path: str) -> str:
    return path.replace("\\", "/")


def _in_scope(path: str, write_paths: list) -> bool:
    """A path is in scope if it equals an entry or falls under a '/'-suffixed
    prefix entry."""
    path = _portable(path)
    for entry in write_paths:
        entry = _portable(entry)
        if path == entry or (entry.endswith("/") and path.startswith(entry)):
            return True
    return False


def _full(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _snapshot(root: str, snapshot_dir: str, target_full: str) -> tuple:
    """Store pre-execution bytes at an immutable content-addressed path.

    An existing file at the address is re-hashed, never trusted by name: a
    pre-planted poison file at the expected address would otherwise corrupt
    the rollback evidence (failure-injection finding, P4_6).
    """
    digest = sha256_file(target_full)
    rel = _portable(f"{snapshot_dir.rstrip('/')}/{digest}.bin")
    full = _full(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if not os.path.exists(full) or sha256_file(full) != digest:
        with open(target_full, "rb") as src, open(full, "wb") as dst:
            dst.write(src.read())
    return digest, rel


def build_execution_plan(root: str, plan_id: str, intent: dict,
                         gate_result: dict, effects: list,
                         snapshot_dir: str) -> dict:
    """Seal what an authorized execution will change, with rollback evidence.

    Fails fast on: an absent/tampered/non-actuating gate, a gate for another
    intent, out-of-scope paths, budget overruns, and dry-run precondition
    violations (create over an existing file, modify/delete of a missing one).
    """
    if not isinstance(gate_result, dict) or not verify_gate_result_seal(gate_result):
        raise ValueError("no plan without a sealed gate result")
    if gate_result["decision"] not in ACTUATABLE_DECISIONS:
        raise ValueError(f"gate decision {gate_result['decision']!r} does not "
                         "authorize actuation")
    digest = intent_digest(intent)
    if gate_result["intent_digest"] != digest:
        raise ValueError("gate result authorizes a different intent")
    if not effects:
        raise ValueError("an execution plan requires at least one effect")

    write_paths = intent["scope"]["write_paths"]
    budget = intent["budget"]
    planned_effects = []
    rollback = []
    total_bytes = 0
    seen_paths = set()
    for effect in effects:
        path = _portable(effect["path"])
        op = effect["op"]
        if op not in OPS:
            raise ValueError(f"{path}: unknown op {op!r}")
        if path in seen_paths:
            raise ValueError(f"{path}: duplicate effect path")
        seen_paths.add(path)
        if not _in_scope(path, write_paths):
            raise ValueError(f"{path}: outside the intent's approved write scope")
        planned_bytes = effect.get("planned_bytes", 0)
        if not isinstance(planned_bytes, int) or planned_bytes < 0:
            raise ValueError(f"{path}: planned_bytes must be a non-negative int")
        total_bytes += planned_bytes

        target_full = _full(root, path)
        exists = os.path.isfile(target_full)
        if op == "create" and exists:
            raise ValueError(f"{path}: plan claims create but the path exists")
        if op in ("modify", "delete") and not exists:
            raise ValueError(f"{path}: plan claims {op} but the path is missing")

        if op in ("modify", "delete"):
            pre_sha256, snapshot_rel = _snapshot(root, snapshot_dir, target_full)
            rollback.append({"path": path, "op": op, "pre_sha256": pre_sha256,
                             "snapshot_path": snapshot_rel})
        else:
            rollback.append({"path": path, "op": op, "pre_sha256": None,
                             "snapshot_path": None})
        planned_effects.append({"path": path, "op": op,
                                "planned_bytes": planned_bytes})

    if len(planned_effects) > budget["max_files"]:
        raise ValueError(f"budget overrun: {len(planned_effects)} effects > "
                         f"max_files {budget['max_files']}")
    if total_bytes > budget["max_bytes"]:
        raise ValueError(f"budget overrun: {total_bytes} planned bytes > "
                         f"max_bytes {budget['max_bytes']}")

    return _seal({
        "schema": SCHEMA_ID,
        "plan_id": plan_id,
        "intent_digest": digest,
        "gate_result_sha256": gate_result["result_sha256"],
        "gate_decision": gate_result["decision"],
        "state_receipt_hash": gate_result["state_receipt_hash"],
        "effects": planned_effects,
        "rollback": rollback,
        "budget_check": {"files": len(planned_effects),
                         "max_files": budget["max_files"],
                         "bytes": total_bytes,
                         "max_bytes": budget["max_bytes"]},
    })


def verify_execution_plan(root: str, plan: dict, intent: dict = None,
                          gate_result: dict = None,
                          check_preconditions: bool = False) -> list:
    """Re-verify a sealed plan: chain, scope, budget, rollback snapshots.

    ``check_preconditions=True`` additionally requires the CURRENT filesystem
    to still match the plan's dry-run assumptions (create targets absent,
    modify/delete targets present with the snapshotted bytes) — the check an
    actuator must run immediately before executing.
    """
    problems = []
    if not verify_plan_seal(plan):
        problems.append("plan seal is broken")
    if intent is not None:
        if intent_digest(intent) != plan.get("intent_digest"):
            problems.append("plan is bound to a different intent")
        else:
            for effect in plan.get("effects", []):
                if not _in_scope(effect["path"], intent["scope"]["write_paths"]):
                    problems.append(f"{effect['path']}: outside the intent's "
                                    "approved write scope")
            budget = intent["budget"]
            if len(plan.get("effects", [])) > budget["max_files"]:
                problems.append("budget overrun: effects exceed max_files")
            if sum(e["planned_bytes"] for e in plan.get("effects", [])) > budget["max_bytes"]:
                problems.append("budget overrun: planned bytes exceed max_bytes")
    if gate_result is not None:
        if not verify_gate_result_seal(gate_result):
            problems.append("gate result seal is broken")
        elif plan.get("gate_result_sha256") != gate_result["result_sha256"]:
            problems.append("plan is not chained to this gate result")
        elif gate_result["decision"] not in ACTUATABLE_DECISIONS:
            problems.append("chained gate decision does not authorize actuation")

    for entry in plan.get("rollback", []):
        if entry["op"] == "create":
            continue
        label = f"rollback {entry['path']}"
        snapshot_full = _full(root, entry["snapshot_path"])
        if not os.path.isfile(snapshot_full):
            problems.append(f"{label}: snapshot missing on disk")
        elif sha256_file(snapshot_full) != entry["pre_sha256"]:
            problems.append(f"{label}: snapshot bytes do not match pre_sha256")

    if check_preconditions:
        for entry in plan.get("rollback", []):
            path_full = _full(root, entry["path"])
            exists = os.path.isfile(path_full)
            if entry["op"] == "create" and exists:
                problems.append(f"{entry['path']}: precondition drifted — "
                                "create target already exists")
            elif entry["op"] in ("modify", "delete"):
                if not exists:
                    problems.append(f"{entry['path']}: precondition drifted — "
                                    f"{entry['op']} target is missing")
                elif sha256_file(path_full) != entry["pre_sha256"]:
                    problems.append(f"{entry['path']}: precondition drifted — "
                                    "target bytes changed since the plan was "
                                    "sealed")
    return sorted(problems)


if __name__ == "__main__":
    print("library module — build_execution_plan / verify_execution_plan")
    sys.exit(2)
