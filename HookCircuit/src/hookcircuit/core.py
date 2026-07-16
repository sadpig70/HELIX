"""Deterministic reflex circuit breaker for plugin hooks."""

import copy
import hashlib
import json


CASE_SCHEMA = "hook-circuit-case/1.0"
RECEIPT_SCHEMA = "hook-circuit-receipt/1.0"
OUTCOMES = {"ok", "fail", "timeout"}


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def baseline_digest(hooks, observations):
    return digest({
        "hooks": sorted(copy.deepcopy(hooks), key=lambda row: row["hook_id"]),
        "observations": sorted(copy.deepcopy(observations), key=lambda row: (row["hook_id"], row.get("event_id", ""), row.get("sequence", 0))),
    })


def _validate(case):
    reasons = []
    if case.get("schema") != CASE_SCHEMA:
        reasons.append("INVALID_SCHEMA")
    hooks = case.get("hooks")
    observations = case.get("observations")
    if not isinstance(hooks, list) or not isinstance(observations, list):
        return reasons + ["INVALID_CASE_STRUCTURE"]
    hook_ids = []
    for hook in hooks:
        if not isinstance(hook, dict) or not isinstance(hook.get("hook_id"), str) or not hook["hook_id"]:
            reasons.append("INVALID_HOOK")
            continue
        hook_ids.append(hook["hook_id"])
        if not isinstance(hook.get("plugin"), str) or not hook["plugin"]:
            reasons.append("INVALID_HOOK_PLUGIN")
        if not isinstance(hook.get("event"), str) or not hook["event"]:
            reasons.append("INVALID_HOOK_EVENT")
        if isinstance(hook.get("max_failures"), bool) or not isinstance(hook.get("max_failures"), int) or hook["max_failures"] < 1:
            reasons.append("INVALID_MAX_FAILURES")
        if isinstance(hook.get("timeout_ms"), bool) or not isinstance(hook.get("timeout_ms"), int) or hook["timeout_ms"] < 1:
            reasons.append("INVALID_TIMEOUT")
    if len(set(hook_ids)) != len(hook_ids):
        reasons.append("DUPLICATE_HOOK")
    hook_set = set(hook_ids)
    for obs in observations:
        if not isinstance(obs, dict) or obs.get("hook_id") not in hook_set:
            reasons.append("OBSERVATION_HOOK_MISSING")
            continue
        if obs.get("outcome") not in OUTCOMES:
            reasons.append("INVALID_OUTCOME")
        elapsed = obs.get("elapsed_ms", 0)
        if isinstance(elapsed, bool) or not isinstance(elapsed, int) or elapsed < 0:
            reasons.append("INVALID_ELAPSED")
    if not reasons and case.get("baseline_sha256") != baseline_digest(hooks, observations):
        reasons.append("BASELINE_HASH_MISMATCH")
    return sorted(set(reasons))


def _hook_index(hooks):
    return {hook["hook_id"]: copy.deepcopy(hook) for hook in hooks}


def _dispatch_rows(hooks, observations):
    index = _hook_index(hooks)
    rows = []
    for obs in sorted(observations, key=lambda row: (row["hook_id"], row.get("event_id", ""), row.get("sequence", 0))):
        hook = index[obs["hook_id"]]
        timed_out = obs.get("outcome") == "timeout" or obs.get("elapsed_ms", 0) > hook["timeout_ms"]
        failed = obs.get("outcome") == "fail" or timed_out
        rows.append({
            "hook_id": obs["hook_id"],
            "plugin": hook["plugin"],
            "event": hook["event"],
            "event_id": str(obs.get("event_id", "")),
            "sequence": obs.get("sequence", 0),
            "outcome": obs["outcome"],
            "elapsed_ms": obs.get("elapsed_ms", 0),
            "failed": failed,
            "timed_out": timed_out,
        })
    return rows


def evaluate(case):
    case = copy.deepcopy(case)
    reasons = _validate(case)
    hooks = case.get("hooks") if isinstance(case.get("hooks"), list) else []
    observations = case.get("observations") if isinstance(case.get("observations"), list) else []
    dispatch, tripped, allowed, isolated_plugins = [], [], [], []
    if not reasons:
        dispatch = _dispatch_rows(hooks, observations)
        failures = {}
        for row in dispatch:
            if row["failed"]:
                failures[row["hook_id"]] = failures.get(row["hook_id"], 0) + 1
        index = _hook_index(hooks)
        for hook_id in sorted(index):
            count = failures.get(hook_id, 0)
            hook = index[hook_id]
            if count >= hook["max_failures"]:
                tripped.append({
                    "hook_id": hook_id,
                    "plugin": hook["plugin"],
                    "failure_count": count,
                    "threshold": hook["max_failures"],
                    "reason": "failure_threshold_reached",
                })
            else:
                allowed.append(hook_id)
        isolated_plugins = sorted({row["plugin"] for row in tripped})
    decision = "INVALID" if reasons else ("TRIPPED" if tripped else "ALLOWED")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "case_id": str(case.get("case_id", "")),
        "case_sha256": digest(case),
        "decision": decision,
        "reasons": reasons,
        "dispatch_evidence": dispatch,
        "tripped_hooks": tripped,
        "allowed_hooks": allowed,
        "isolated_plugins": isolated_plugins,
        "interrupted": decision == "TRIPPED",
        "gene_provenance": {"hook_contract": "HC-PILOT-EXT-006", "reflex_interruption": "HC-PILOT-HELIX-003"},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(case, receipt):
    return evaluate(case) == receipt

