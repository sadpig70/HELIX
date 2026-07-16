"""Sample ContractRelay cases."""

import copy

from .core import CASE_SCHEMA, baseline_digest


def sample_case(kind="relayed"):
    source = "system-a"
    target = "system-b"
    contract = {
        "contract_id": "contract-v1",
        "allowed_sources": ["system-a"],
        "allowed_targets": ["system-b"],
        "required_fields": ["subject.id", "subject.score", "handoff.reason"],
        "field_types": {
            "subject.id": "string",
            "subject.score": "number",
            "handoff.reason": "string",
        },
    }
    payload = {
        "subject": {"id": "case-17", "score": 0.82},
        "handoff": {"reason": "verified"},
    }
    custody = {
        "from_actor": "system-a",
        "to_actor": "system-b",
        "handoff_confirmed": True,
        "route_id": "route-ab",
    }
    if kind == "blocked":
        payload = {"subject": {"id": "case-17", "score": "high"}, "handoff": {}}
        custody = {"from_actor": "system-a", "to_actor": "system-c", "handoff_confirmed": False, "route_id": ""}
    case = {
        "schema": CASE_SCHEMA,
        "case_id": f"sample-{kind}",
        "source": source,
        "target": target,
        "contract": copy.deepcopy(contract),
        "payload": copy.deepcopy(payload),
        "custody": copy.deepcopy(custody),
    }
    case["baseline_sha256"] = baseline_digest(case["source"], case["target"], case["contract"], case["payload"], case["custody"])
    if kind == "invalid-baseline":
        case["baseline_sha256"] = "0" * 64
    return case

