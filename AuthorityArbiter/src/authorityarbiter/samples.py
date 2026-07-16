"""Deterministic arbitration samples."""

import copy


def sample_request(kind="allow"):
    request = {
        "schema": "authority-arbiter-request/1.0",
        "case_id": "AA-DEMO-001",
        "action": "deploy_agent",
        "facts": {"risk": {"level": "low"}, "environment": "staging"},
        "authorities": [
            {"authority_id": "platform-owner", "rank": 100},
            {"authority_id": "service-owner", "rank": 50}
        ],
        "policies": [
            {"policy_id": "allow-low-risk", "authority_id": "platform-owner", "priority": 10,
             "effect": "allow", "conditions": [{"field": "risk.level", "operator": "eq", "value": "low"}]},
            {"policy_id": "deny-staging", "authority_id": "service-owner", "priority": 99,
             "effect": "deny", "conditions": [{"field": "environment", "operator": "eq", "value": "staging"}]}
        ],
        "delegation": {"authority_id": "platform-owner", "delegated_to": "deploy-agent-7",
                       "action": "deploy_agent", "allowed_actions": ["deploy_agent"],
                       "authority_chain": ["platform-owner", "service-owner"], "return_to": "platform-owner"},
        "custody": {"artifact_id": "agent-release-42", "from_actor": "deploy-agent-7",
                    "to_actor": "platform-owner", "handback_confirmed": True},
        "route": {"planned_route_id": "deploy-review", "actual_route_id": "deploy-review", "status": "passed"}
    }
    if kind == "deny":
        request["authorities"][0]["rank"] = 40
    elif kind == "tie":
        request["policies"][1]["authority_id"] = "platform-owner"
        request["policies"][1]["priority"] = 10
    elif kind != "allow":
        raise ValueError(f"unknown sample kind: {kind}")
    return copy.deepcopy(request)
