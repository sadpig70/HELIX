#!/usr/bin/env python3
"""Unified actuation command for the HELIX Actuation Plane (T3).

Policy source of truth: process plan §P4_5 and DESIGN UnifiedCommand — one
deterministic pipeline closes the loop:

    intent + evidence  -> authorize (gate, stop-aware)
                       -> execution plan (scope/budget/precondition fail-fast)
                       -> side-effect guard (authority/stop/drift recheck)
                       -> execute effects (only if cleared)
                       -> impact handback (honest outcome delta)
                       -> deviated? perform rollback with proof
                       -> append every receipt to a hash-chained ledger

Guarantees, enforced stage by stage:
- any refusal (gate not ALLOW/SANDBOX, plan build failure, guard not cleared)
  ends the pipeline with ZERO side effects, and the refusal itself is
  ledgered;
- a deviated handback triggers a real rollback whose proof is recorded; a
  rollback with problems is reported as failed recovery, never as success;
- ``consumable`` is true only for ALLOW + clean — the P4_2 admission
  semantics' consumption switch-over point: SANDBOX runs are never consumed
  into the unified ledger, deviated runs are rolled back and not consumed.

The actuation ledger is an append-only JSONL hash chain (parent seal ->
entry seal), so the full decision-to-effect history replays and tampering
with any line breaks the chain.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import json
import os
import sys

try:  # package import (python -m core.helix_actuator) or library use
    from .helix_authorization import authorize
    from .helix_execution_plan import build_execution_plan
    from .helix_holdout import canonical_json_bytes
    from .helix_impact_handback import (build_impact_handback,
                                        perform_rollback, snapshot_scope)
    from .helix_side_effect_guard import guard_side_effects
except ImportError:  # direct script run
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_authorization import authorize
    from core.helix_execution_plan import build_execution_plan
    from core.helix_holdout import canonical_json_bytes
    from core.helix_impact_handback import (build_impact_handback,
                                            perform_rollback, snapshot_scope)
    from core.helix_side_effect_guard import guard_side_effects

LEDGER_SCHEMA_ID = "helix-actuation-ledger-entry/1.0"


def _full(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _entry_seal(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "entry_sha256"}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def read_actuation_ledger(root: str, ledger_rel: str) -> list:
    full = _full(root, ledger_rel)
    if not os.path.isfile(full):
        return []
    entries = []
    with open(full, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def append_actuation_ledger(root: str, ledger_rel: str, kind: str,
                            request_id: str, receipt: dict) -> dict:
    """Append one sealed entry chained to the previous entry's seal."""
    entries = read_actuation_ledger(root, ledger_rel)
    parent = entries[-1]["entry_sha256"] if entries else None
    entry = {
        "schema": LEDGER_SCHEMA_ID,
        "seq": len(entries),
        "kind": kind,
        "request_id": request_id,
        "parent_sha256": parent,
        "receipt": receipt,
    }
    entry["entry_sha256"] = _entry_seal(entry)
    full = _full(root, ledger_rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return entry


def verify_actuation_ledger(root: str, ledger_rel: str) -> list:
    """Re-verify the append-only chain: seq, parent links, entry seals."""
    problems = []
    parent = None
    for index, entry in enumerate(read_actuation_ledger(root, ledger_rel)):
        if entry.get("seq") != index:
            problems.append(f"entry {index}: seq {entry.get('seq')!r} broken")
        if entry.get("parent_sha256") != parent:
            problems.append(f"entry {index}: parent chain broken")
        if _entry_seal(entry) != entry.get("entry_sha256"):
            problems.append(f"entry {index}: entry seal broken")
        parent = entry.get("entry_sha256")
    return problems


def verify_actuation_chain(root: str, ledger_rel: str) -> list:
    """Cross-receipt audit of the ledger — the bypass detector.

    A canonical seal proves integrity, not authorship, so a forged-but-sealed
    receipt can only be caught by requiring every receipt to sit in ONE
    gapless authorization chain inside the ledger: per request,
    gate -> plan -> guard -> handback (-> rollback), each referencing the
    previous receipt's hash, with no execution receipts after a non-actuating
    gate or a plan refusal, and no handback whose guard/plan never appeared.
    """
    problems = verify_actuation_ledger(root, ledger_rel)
    state = {}
    for entry in read_actuation_ledger(root, ledger_rel):
        rid = entry.get("request_id")
        kind = entry.get("kind")
        receipt = entry.get("receipt") or {}
        st = state.setdefault(rid, {"gate": None, "plan": None, "guard": None,
                                    "handback": None, "refused": False})
        label = f"{rid}/{kind}"
        if kind == "gate":
            st["gate"] = receipt
        elif kind == "plan_refusal":
            st["refused"] = True
        elif kind in ("plan", "guard", "handback", "rollback"):
            gate = st["gate"]
            if gate is None:
                problems.append(f"{label}: execution receipt without any gate "
                                "(ungated admission)")
                continue
            if gate.get("decision") not in ("ALLOW", "SANDBOX"):
                problems.append(f"{label}: execution receipt after "
                                f"non-actuating gate {gate.get('decision')!r} "
                                "(ungated admission)")
                continue
            if st["refused"]:
                problems.append(f"{label}: execution receipt after a plan "
                                "refusal")
                continue
            if kind == "plan":
                if receipt.get("gate_result_sha256") != gate.get("result_sha256"):
                    problems.append(f"{label}: plan not chained to the "
                                    "ledgered gate")
                st["plan"] = receipt
            elif kind == "guard":
                if (st["plan"] is None or receipt.get("plan_sha256")
                        != st["plan"].get("plan_sha256")):
                    problems.append(f"{label}: guard not chained to the "
                                    "ledgered plan")
                st["guard"] = receipt
            elif kind == "handback":
                guard = st["guard"]
                if (guard is None or receipt.get("guard_receipt_sha256")
                        != guard.get("receipt_sha256")):
                    problems.append(f"{label}: handback not chained to a "
                                    "ledgered guard (guard bypass)")
                elif not guard.get("cleared"):
                    problems.append(f"{label}: handback after an uncleared "
                                    "guard (guard bypass)")
                st["handback"] = receipt
            elif kind == "rollback":
                handback = st["handback"]
                if handback is None or handback.get("verdict") != "deviated":
                    problems.append(f"{label}: rollback without a deviated "
                                    "handback")
    return sorted(problems)


def _execute_effects(root: str, effects: list) -> None:
    for effect in effects:
        full = _full(root, effect["path"])
        if effect["op"] == "delete":
            os.remove(full)
        else:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as f:
                f.write(effect["content"])


def run_admission(root: str, request: dict, current_state_receipt_hash: str,
                  ledger_rel: str, snapshot_dir: str,
                  stop_tokens: list = None,
                  resume_receipts: list = None) -> dict:
    """One full propose->gate->execute->handback->ledger round, fail-closed.

    request = {request_id, intent, evidence_manifest, approvals,
    effects: [{path, op, content?}]} — content (utf-8 str) is required for
    create/modify and sizes the plan's byte budget honestly.
    """
    request_id = request["request_id"]
    intent = request["intent"]

    def ledger(kind, receipt):
        return append_actuation_ledger(root, ledger_rel, kind, request_id,
                                       receipt)

    gate = authorize(root, intent, request.get("evidence_manifest"),
                     request.get("approvals") or [],
                     current_state_receipt_hash, stop_tokens=stop_tokens,
                     resume_receipts=resume_receipts)
    ledger("gate", gate)
    if gate["decision"] not in ("ALLOW", "SANDBOX"):
        return {"request_id": request_id, "executed": False, "stage": "gate",
                "gate": gate, "consumable": False,
                "why": f"gate decision {gate['decision']} does not authorize "
                       "actuation; zero side effects"}

    effect_specs = []
    for effect in request.get("effects") or []:
        planned_bytes = 0
        if effect["op"] in ("create", "modify"):
            planned_bytes = len(effect["content"].encode("utf-8"))
        effect_specs.append({"path": effect["path"], "op": effect["op"],
                             "planned_bytes": planned_bytes})
    try:
        plan = build_execution_plan(root, f"PLAN-{request_id}", intent, gate,
                                    effect_specs, snapshot_dir)
    except ValueError as e:
        refusal = {"schema": "helix-plan-refusal/1.0",
                   "request_id": request_id, "error": str(e)}
        ledger("plan_refusal", refusal)
        return {"request_id": request_id, "executed": False, "stage": "plan",
                "gate": gate, "consumable": False, "why": str(e)}
    ledger("plan", plan)

    guard = guard_side_effects(root, intent, gate, plan,
                               current_state_receipt_hash,
                               stop_tokens=stop_tokens,
                               resume_receipts=resume_receipts)
    ledger("guard", guard)
    if not guard["cleared"]:
        return {"request_id": request_id, "executed": False, "stage": "guard",
                "gate": gate, "plan": plan, "guard": guard,
                "consumable": False,
                "why": "guard did not clear; zero side effects"}

    pre_scope = snapshot_scope(root, intent)
    _execute_effects(root, request.get("effects") or [])
    post_scope = snapshot_scope(root, intent)

    handback = build_impact_handback(root, f"HB-{request_id}", plan, guard,
                                     pre_scope=pre_scope,
                                     post_scope=post_scope)
    ledger("handback", handback)

    rolled_back = False
    rollback_report = None
    if handback["verdict"] == "deviated":
        rollback_report = perform_rollback(root, plan)
        rolled_back = not rollback_report["problems"]
        ledger("rollback", {"schema": "helix-rollback-report/1.0",
                            "request_id": request_id,
                            "plan_sha256": plan["plan_sha256"],
                            "recovered": rolled_back,
                            **rollback_report})

    consumable = (gate["decision"] == "ALLOW"
                  and handback["verdict"] == "clean")
    return {
        "request_id": request_id,
        "executed": True,
        "stage": "complete",
        "gate": gate,
        "plan": plan,
        "guard": guard,
        "handback": handback,
        "rolled_back": rolled_back,
        "rollback_report": rollback_report,
        "consumable": consumable,
        "why": ("clean ALLOW run; eligible for ledger consumption" if consumable
                else "SANDBOX or deviated run; never consumed"),
    }


if __name__ == "__main__":
    print("library module — run_admission / append_actuation_ledger / "
          "verify_actuation_ledger")
    sys.exit(2)
