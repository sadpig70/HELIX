"""Deterministic runtime-drift replay and counterexample shrinking."""

import copy
import hashlib
import json


CASE_SCHEMA = "drift-isolator-case/1.0"
RECEIPT_SCHEMA = "drift-isolator-receipt/1.0"
OPS = {"set", "increment", "append"}


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def baseline_digest(initial_state, expected_state):
    return digest({"initial_state": initial_state, "expected_state": expected_state})


def _parent(state, path, create=False):
    parts = str(path).split(".")
    if not path or any(not part for part in parts):
        raise ValueError("invalid path")
    node = state
    for part in parts[:-1]:
        if part not in node:
            if not create:
                raise ValueError("missing path")
            node[part] = {}
        if not isinstance(node[part], dict):
            raise ValueError("non-object path")
        node = node[part]
    return node, parts[-1]


def apply_event(state, event):
    if not isinstance(event, dict) or event.get("op") not in OPS or not event.get("event_id"):
        raise ValueError("invalid event")
    state = copy.deepcopy(state)
    parent, key = _parent(state, event.get("path"), create=event["op"] == "set")
    if event["op"] == "set":
        parent[key] = copy.deepcopy(event.get("value"))
    elif event["op"] == "increment":
        if key not in parent or isinstance(parent[key], bool) or not isinstance(parent[key], (int, float)):
            raise ValueError("increment target must be numeric")
        amount = event.get("value")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("increment value must be numeric")
        parent[key] += amount
    else:
        if key not in parent or not isinstance(parent[key], list):
            raise ValueError("append target must be a list")
        parent[key].append(copy.deepcopy(event.get("value")))
    return state


def replay(initial_state, events):
    state = copy.deepcopy(initial_state)
    for event in events:
        state = apply_event(state, event)
    return state


def shrink(events, predicate):
    """Deterministic ddmin followed by a stable one-by-one minimality pass."""
    current = list(copy.deepcopy(events))
    granularity = 2
    while len(current) >= 2:
        chunk_size = max(1, (len(current) + granularity - 1) // granularity)
        reduced = False
        for start in range(0, len(current), chunk_size):
            candidate = current[:start] + current[start + chunk_size:]
            if predicate(candidate):
                current = candidate
                granularity = max(2, granularity - 1)
                reduced = True
                break
        if not reduced:
            if granularity >= len(current):
                break
            granularity = min(len(current), granularity * 2)
    changed = True
    while changed:
        changed = False
        for index in range(len(current)):
            candidate = current[:index] + current[index + 1:]
            if predicate(candidate):
                current = candidate
                changed = True
                break
    return current


def isolate(case):
    case = copy.deepcopy(case)
    reasons = []
    if case.get("schema") != CASE_SCHEMA:
        reasons.append("INVALID_SCHEMA")
    initial = case.get("initial_state")
    expected = case.get("expected_state")
    events = case.get("events")
    if not isinstance(initial, dict) or not isinstance(expected, dict) or not isinstance(events, list):
        reasons.append("INVALID_CASE_STRUCTURE")
    elif case.get("baseline_sha256") != baseline_digest(initial, expected):
        reasons.append("BASELINE_HASH_MISMATCH")
    try:
        final = replay(initial or {}, events or [])
    except ValueError as error:
        reasons.append("INVALID_EVENT:" + str(error))
        final = copy.deepcopy(initial or {})

    decision, minimal = "INVALID", []
    if not reasons:
        if final == expected:
            decision = "NO_DRIFT"
        else:
            predicate = lambda rows: replay(initial, rows) != expected
            minimal = shrink(events, predicate)
            decision = "ISOLATED"
    one_minimal = bool(minimal) and all(
        replay(initial, minimal[:index] + minimal[index + 1:]) == expected
        for index in range(len(minimal)))
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "case_id": str(case.get("case_id", "")),
        "case_sha256": digest(case),
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "original_event_count": len(events) if isinstance(events, list) else 0,
        "minimal_event_count": len(minimal),
        "minimal_events": minimal,
        "minimal_final_state": replay(initial, minimal) if minimal else copy.deepcopy(final),
        "expected_state": copy.deepcopy(expected) if isinstance(expected, dict) else {},
        "one_minimal": one_minimal,
        "gene_provenance": {"counterexample_shrinking":"HC-PILOT-EXT-003","baseline_drift":"HC-PILOT-HELIX-003"}
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(case, receipt):
    return isolate(case) == receipt
