"""Sample HookCircuit cases."""

import copy

from .core import CASE_SCHEMA, baseline_digest


def sample_case(kind="tripped"):
    hooks = [
        {"hook_id": "h-auth", "plugin": "authz", "event": "before_dispatch", "max_failures": 1, "timeout_ms": 50},
        {"hook_id": "h-log", "plugin": "audit", "event": "after_dispatch", "max_failures": 2, "timeout_ms": 100},
        {"hook_id": "h-cache", "plugin": "cache", "event": "before_dispatch", "max_failures": 1, "timeout_ms": 25},
    ]
    observations = [
        {"hook_id": "h-auth", "event_id": "evt-1", "sequence": 1, "outcome": "ok", "elapsed_ms": 12},
        {"hook_id": "h-log", "event_id": "evt-1", "sequence": 2, "outcome": "ok", "elapsed_ms": 10},
        {"hook_id": "h-cache", "event_id": "evt-1", "sequence": 3, "outcome": "timeout", "elapsed_ms": 40},
    ]
    if kind == "clean":
        observations[-1] = {"hook_id": "h-cache", "event_id": "evt-1", "sequence": 3, "outcome": "ok", "elapsed_ms": 8}
    case = {"schema": CASE_SCHEMA, "case_id": f"sample-{kind}", "hooks": copy.deepcopy(hooks), "observations": copy.deepcopy(observations)}
    case["baseline_sha256"] = baseline_digest(case["hooks"], case["observations"])
    if kind == "invalid-baseline":
        case["baseline_sha256"] = "0" * 64
    return case

