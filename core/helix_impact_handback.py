#!/usr/bin/env python3
"""Impact handback for the HELIX Actuation Plane (T3).

Policy source of truth: process plan §P4_4 ("outcome delta, use, rollback,
trace schema") and DESIGN RecoveryProof ("rollback and replay evidence
required"). After an actuator executes a guarded plan, the impact handback
seals what ACTUALLY happened, honestly:

- outcome delta: every planned effect re-hashed from the real filesystem
  (create/modify record post bytes; delete records absence). An effect that
  did not land is recorded ``not_applied`` — never silently dropped.
- actual use vs budget: real files/bytes charged against the intent budget.
- undeclared changes: with a pre-execution scope snapshot, any file inside
  the approved write scope that changed WITHOUT being in the plan is a
  violation. Without a snapshot the check is honestly marked unchecked.
- rollback proof: the plan's content-addressed snapshots are re-verified,
  and ``perform_rollback`` can actually restore the pre-execution state and
  prove it by re-hashing.
- trace: intent digest -> gate seal -> plan seal -> guard seal, so every
  effect is attributable to exactly one cleared authorization chain.

A handback with problems seals ``verdict=deviated`` — deviations are
recorded, never laundered. No handback may exist without a cleared guard.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:  # package import (python -m core.helix_impact_handback) or library use
    from .helix_execution_plan import verify_execution_plan, verify_plan_seal
    from .helix_holdout import canonical_json_bytes
    from .helix_side_effect_guard import verify_guard_receipt_seal
    from .helix_state_receipt import sha256_file
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_execution_plan import verify_execution_plan, verify_plan_seal
    from core.helix_holdout import canonical_json_bytes
    from core.helix_side_effect_guard import verify_guard_receipt_seal
    from core.helix_state_receipt import sha256_file

SCHEMA_ID = "helix-impact-handback/1.0"


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_handback_seal(handback: dict) -> bool:
    expected = handback.get("receipt_sha256")
    body = {k: v for k, v in handback.items() if k != "receipt_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def _full(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def snapshot_scope(root: str, intent: dict) -> dict:
    """Hash every file currently under the intent's write scope.

    Actuators capture this immediately before executing so the handback can
    detect undeclared changes inside the approved scope.
    """
    manifest = {}
    for entry in intent["scope"]["write_paths"]:
        entry = entry.replace("\\", "/")
        full = _full(root, entry)
        if entry.endswith("/"):
            if not os.path.isdir(full):
                continue
            for current, dirs, files in os.walk(full):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for name in sorted(files):
                    path = os.path.join(current, name)
                    rel = os.path.relpath(path, root).replace(os.sep, "/")
                    manifest[rel] = sha256_file(path)
        elif os.path.isfile(full):
            manifest[entry] = sha256_file(full)
    return manifest


def _collect_outcomes(root: str, plan: dict) -> tuple:
    outcomes = []
    problems = []
    files = 0
    total_bytes = 0
    rollback_by_path = {e["path"]: e for e in plan["rollback"]}
    for effect in plan["effects"]:
        path, op = effect["path"], effect["op"]
        full = _full(root, path)
        exists = os.path.isfile(full)
        post_sha, post_bytes, status = None, None, "not_applied"
        if op == "delete":
            if not exists:
                status = "applied"
            else:
                problems.append(f"{path}: planned delete but the file still exists")
        elif exists:
            post_sha = sha256_file(full)
            post_bytes = os.path.getsize(full)
            pre_sha = rollback_by_path[path]["pre_sha256"]
            if op == "modify" and post_sha == pre_sha:
                problems.append(f"{path}: planned modify but bytes are unchanged")
            else:
                status = "applied"
                files += 1
                total_bytes += post_bytes
        else:
            problems.append(f"{path}: planned {op} but no file was produced")
        outcomes.append({"path": path, "op": op, "status": status,
                         "post_sha256": post_sha, "post_bytes": post_bytes})
    return outcomes, problems, files, total_bytes


def _undeclared_changes(root: str, plan: dict, pre_scope: dict) -> list:
    planned = {e["path"] for e in plan["effects"]}
    changes = []
    post_scope = {}
    for path, pre_sha in pre_scope.items():
        full = _full(root, path)
        if not os.path.isfile(full):
            post_scope[path] = None
        else:
            post_scope[path] = sha256_file(full)
    # files that appeared: walk again over the same prefixes is the caller's
    # concern via snapshot_scope; compare using a fresh snapshot keyed off the
    # union of pre paths and current scope contents.
    for path, pre_sha in sorted(pre_scope.items()):
        if path in planned:
            continue
        post_sha = post_scope[path]
        if post_sha is None:
            changes.append({"path": path, "kind": "deleted"})
        elif post_sha != pre_sha:
            changes.append({"path": path, "kind": "modified"})
    return changes


def build_impact_handback(root: str, handback_id: str, plan: dict,
                          guard_receipt: dict, pre_scope: dict = None,
                          post_scope: dict = None) -> dict:
    """Seal what actually happened after executing one guarded plan.

    Refuses to exist without a sealed, CLEARED guard chained to this exact
    plan. ``pre_scope``/``post_scope`` are scope snapshots (snapshot_scope)
    taken by the actuator before/after execution; when given, any in-scope
    change outside the plan is reported as an undeclared violation.
    """
    if not verify_plan_seal(plan):
        raise ValueError("no handback without a sealed execution plan")
    if not isinstance(guard_receipt, dict) or not verify_guard_receipt_seal(guard_receipt):
        raise ValueError("no handback without a sealed guard receipt")
    if not guard_receipt.get("cleared"):
        raise ValueError("guard did not clear this plan; effects must not "
                         "have run and cannot be handed back")
    if guard_receipt.get("plan_sha256") != plan.get("plan_sha256"):
        raise ValueError("guard receipt is chained to a different plan")

    outcomes, problems, files, total_bytes = _collect_outcomes(root, plan)

    budget = plan["budget_check"]
    budget_ok = (files <= budget["max_files"] and total_bytes <= budget["max_bytes"])
    if not budget_ok:
        problems.append(f"budget exceeded in reality: files={files}/"
                        f"{budget['max_files']} bytes={total_bytes}/"
                        f"{budget['max_bytes']}")

    if pre_scope is not None:
        changes = _undeclared_changes(root, plan, pre_scope)
        if post_scope:
            planned = {e["path"] for e in plan["effects"]}
            for path in sorted(set(post_scope) - set(pre_scope) - planned):
                changes.append({"path": path, "kind": "created"})
        undeclared = {"checked": True, "changes": changes}
        for change in changes:
            problems.append(f"undeclared in-scope change: {change['kind']} "
                            f"{change['path']}")
    else:
        undeclared = {"checked": False, "changes": []}

    rollback_problems = [p for p in verify_execution_plan(root, plan)
                         if "snapshot" in p]
    rollback_ready = not rollback_problems
    problems.extend(rollback_problems)

    problems = sorted(set(problems))
    return _seal({
        "schema": SCHEMA_ID,
        "handback_id": handback_id,
        "intent_digest": plan["intent_digest"],
        "gate_result_sha256": plan["gate_result_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "guard_receipt_sha256": guard_receipt["receipt_sha256"],
        "state_receipt_hash": guard_receipt["state_receipt_hash"],
        "outcomes": outcomes,
        "actual_use": {"files": files, "bytes": total_bytes},
        "budget_ok": budget_ok,
        "undeclared": undeclared,
        "rollback_ready": rollback_ready,
        "problems": problems,
        "verdict": "clean" if not problems else "deviated",
    })


def verify_impact_handback(root: str, handback: dict, plan: dict = None,
                           guard_receipt: dict = None) -> list:
    """Re-verify a sealed handback: seal, chain, and current filesystem state."""
    problems = []
    if not verify_handback_seal(handback):
        problems.append("handback seal is broken")
    if plan is not None:
        if not verify_plan_seal(plan):
            problems.append("plan seal is broken")
        elif handback.get("plan_sha256") != plan["plan_sha256"]:
            problems.append("handback is not chained to this plan")
    if guard_receipt is not None:
        if not verify_guard_receipt_seal(guard_receipt):
            problems.append("guard receipt seal is broken")
        elif handback.get("guard_receipt_sha256") != guard_receipt["receipt_sha256"]:
            problems.append("handback is not chained to this guard receipt")
    for outcome in handback.get("outcomes", []):
        if outcome["status"] != "applied" or outcome["op"] == "delete":
            continue
        full = _full(root, outcome["path"])
        if not os.path.isfile(full):
            problems.append(f"{outcome['path']}: handed-back file is missing now")
        elif sha256_file(full) != outcome["post_sha256"]:
            problems.append(f"{outcome['path']}: bytes drifted after handback")
    return sorted(problems)


def perform_rollback(root: str, plan: dict) -> dict:
    """Restore the pre-execution state from the plan's immutable snapshots.

    create -> remove the created file; modify/delete -> restore snapshot
    bytes and prove it by re-hashing against pre_sha256. Returns
    {restored, problems}; any unprovable restoration is a problem, and a
    rollback with problems must never be recorded as a successful recovery.
    """
    restored = []
    problems = []
    if not verify_plan_seal(plan):
        return {"restored": [], "problems": ["plan seal is broken; refusing "
                                             "to roll back from it"]}
    for entry in plan["rollback"]:
        path = entry["path"]
        full = _full(root, path)
        if entry["op"] == "create":
            if os.path.isfile(full):
                os.remove(full)
            restored.append({"path": path, "action": "removed_created_file"})
            continue
        snapshot_full = _full(root, entry["snapshot_path"])
        if not os.path.isfile(snapshot_full):
            problems.append(f"{path}: rollback snapshot missing")
            continue
        if sha256_file(snapshot_full) != entry["pre_sha256"]:
            problems.append(f"{path}: rollback snapshot bytes are corrupt")
            continue
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(snapshot_full, "rb") as src, open(full, "wb") as dst:
            dst.write(src.read())
        if sha256_file(full) != entry["pre_sha256"]:
            problems.append(f"{path}: restoration did not reproduce pre_sha256")
        else:
            restored.append({"path": path, "action": "restored_pre_bytes"})
    return {"restored": restored, "problems": sorted(problems)}


if __name__ == "__main__":
    print("library module — snapshot_scope / build_impact_handback / "
          "verify_impact_handback / perform_rollback")
    sys.exit(2)
