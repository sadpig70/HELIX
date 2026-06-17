#!/usr/bin/env python3
"""HELIX autonomous-loop state — the *deterministic* parts of the factory loop (stdlib only).

`docs/INSTRUCTIONS-helix-loop-autonomous.md` specifies a rich continuous loop
(should_stop, coverage steering, publish rate-limit, checkpoint). Most of it is an
LLM meta-layer (running an engine turn, implementing via pgf, publishing) and stays
in the instructions. But the loop's *control* decisions — when to stop, what the
coverage histogram is, whether a publish is within the rate limit — are pure
functions of state, exactly like `core/helix_loop.next_action`. Leaving them as
prose means every runtime re-derives them, risking inconsistency and giving them no
test. This module promotes those deterministic pieces to tested code; the engine
turn itself remains the meta-layer.

Determinism: pure functions of (state, policy). `now`/window ids are injected, never
read from a clock. State is persisted via core.helix_io (atomic).
"""

import os

from .helix_io import atomic_write_json, read_json

DEFAULT_LOOP_STATE_POLICY = {
    "max_turns": None,               # None -> unbounded
    "max_consecutive_dry": 2,        # two dry turns in a row -> stop
    "max_consecutive_failures": 3,   # three unrecovered failures -> stop
    "publish_rate_limit": 6,         # max publishes per rolling window
}


def should_stop(state: dict, policy: dict = None) -> dict:
    """Decide whether the loop must finalize (deterministic).

    Mirrors INSTRUCTIONS-loop §5. Returns {stop: bool, reason: str}; the first
    matching condition wins (stable priority: human > integrity > budget > dry > fail).
    """
    P = dict(DEFAULT_LOOP_STATE_POLICY)
    if policy:
        P.update(policy)

    if state.get("stop_file_present"):
        return {"stop": True, "reason": "human_stop"}
    if state.get("integrity_alarm"):
        return {"stop": True, "reason": "integrity_alarm"}
    if state.get("budget_exhausted"):
        return {"stop": True, "reason": "budget_exhausted"}
    max_turns = P.get("max_turns")
    if max_turns is not None and int(state.get("turn", 0)) >= int(max_turns):
        return {"stop": True, "reason": "max_turns"}
    if int(state.get("consecutive_dry", 0)) >= P["max_consecutive_dry"]:
        return {"stop": True, "reason": "dry"}
    if int(state.get("consecutive_failures", 0)) >= P["max_consecutive_failures"]:
        return {"stop": True, "reason": "consecutive_failures"}
    return {"stop": False, "reason": ""}


def update_coverage(ledger: dict) -> dict:
    """Histogram the unified ledger for steering (origin / archetype / semantic_family).

    Pure count over consumed[]; the loop uses the least-covered axis as the next
    turn's exploration focus (anti mode-collapse). Deterministic.
    """
    cov = {"origin": {}, "archetype": {}, "semantic_family": {}}
    for e in ledger.get("consumed", []):
        for axis, key in (("origin", "origin"),
                          ("archetype", "archetype"),
                          ("semantic_family", "semantic_family")):
            val = e.get(key)
            if val:
                cov[axis][val] = cov[axis].get(val, 0) + 1
    return cov


def least_covered(coverage_axis: dict) -> str:
    """Return the lowest-count key of a coverage axis (deterministic tie-break by key)."""
    if not coverage_axis:
        return ""
    return sorted(coverage_axis.items(), key=lambda kv: (kv[1], kv[0]))[0][0]


def rate_limit_ok(state: dict, current_window_id: str, policy: dict = None) -> bool:
    """Is a publish allowed now? Resets the count when the window id changes.

    `current_window_id` is injected (e.g. a date stamp from the CLI edge), so this
    stays clock-free and deterministic.
    """
    P = dict(DEFAULT_LOOP_STATE_POLICY)
    if policy:
        P.update(policy)
    limit = int(P["publish_rate_limit"])
    if state.get("publish_window_id") != current_window_id:
        return True  # new window -> counter resets, room available
    return int(state.get("published_this_window", 0)) < limit


def load_loop_state(path: str) -> dict:
    """Load loop-state.json, or a fresh state if absent."""
    return read_json(path, default={
        "status": "active", "turn": 0, "consecutive_dry": 0,
        "consecutive_failures": 0, "strand_counts": {"explore": 0, "exploit": 0},
    })


def checkpoint_loop_state(path: str, state: dict) -> None:
    """Persist loop-state atomically (crash-safe checkpoint, INSTRUCTIONS-loop §7)."""
    atomic_write_json(path, state)


def loop_status_report(state: dict, ledger: dict = None, policy: dict = None) -> dict:
    """Read-only summary for the `helix.py loop-status` helper (no turn execution)."""
    rep = {
        "status": state.get("status", "active"),
        "turn": state.get("turn", 0),
        "stop": should_stop(state, policy),
        "strand_counts": state.get("strand_counts", {}),
    }
    if ledger is not None:
        cov = update_coverage(ledger)
        rep["coverage"] = cov
        rep["least_covered_origin"] = least_covered(cov["origin"])
    return rep
