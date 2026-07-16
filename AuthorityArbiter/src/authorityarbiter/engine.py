"""Deterministic delegated-policy arbitration."""

import copy

from .canonical import digest


REQUEST_SCHEMA = "authority-arbiter-request/1.0"
RECEIPT_SCHEMA = "authority-arbiter-receipt/1.0"
EFFECTS = {"allow", "deny"}
OPERATORS = {"eq", "ne", "in", "exists", "gt", "gte", "lt", "lte"}


def resolve_fact(facts, path):
    value = facts
    for part in str(path).split("."):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def evaluate_condition(condition, facts):
    if not isinstance(condition, dict):
        return False
    operator = condition.get("operator")
    if operator not in OPERATORS:
        return False
    exists, actual = resolve_fact(facts, condition.get("field", ""))
    expected = condition.get("value")
    if operator == "exists":
        return exists is bool(expected)
    if not exists:
        return False
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "in":
        return isinstance(expected, list) and actual in expected
    if isinstance(actual, bool) or isinstance(expected, bool):
        return False
    try:
        return {"gt": actual > expected, "gte": actual >= expected,
                "lt": actual < expected, "lte": actual <= expected}[operator]
    except (TypeError, KeyError):
        return False


def _reason(reasons, code, path):
    reasons.append((code, path))


def arbitrate(request):
    """Return ARBITRATED_ALLOW, ARBITRATED_DENY or ESCALATE."""
    request = copy.deepcopy(request)
    reasons = []
    if request.get("schema") != REQUEST_SCHEMA:
        _reason(reasons, "INVALID_SCHEMA", "schema")
    for key in ("case_id", "action", "facts", "authorities", "policies", "delegation", "custody", "route"):
        if key not in request or request[key] in (None, ""):
            _reason(reasons, "MISSING_FIELD", key)

    action = request.get("action")
    facts = request.get("facts") if isinstance(request.get("facts"), dict) else {}
    delegation = request.get("delegation") if isinstance(request.get("delegation"), dict) else {}
    custody = request.get("custody") if isinstance(request.get("custody"), dict) else {}
    route = request.get("route") if isinstance(request.get("route"), dict) else {}
    if action not in (delegation.get("allowed_actions") or []):
        _reason(reasons, "ACTION_NOT_DELEGATED", "action")
    if custody.get("from_actor") != delegation.get("delegated_to"):
        _reason(reasons, "CUSTODY_SENDER_MISMATCH", "custody.from_actor")
    if custody.get("to_actor") != delegation.get("return_to"):
        _reason(reasons, "CUSTODY_RETURN_MISMATCH", "custody.to_actor")
    if custody.get("handback_confirmed") is not True:
        _reason(reasons, "HANDBACK_NOT_CONFIRMED", "custody.handback_confirmed")
    if route.get("status") != "passed":
        _reason(reasons, "ROUTE_NOT_PASSED", "route.status")
    if route.get("planned_route_id") != route.get("actual_route_id"):
        _reason(reasons, "ROUTE_MISMATCH", "route.actual_route_id")

    authority_rows = request.get("authorities") if isinstance(request.get("authorities"), list) else []
    authorities = {}
    for index, row in enumerate(authority_rows):
        if not isinstance(row, dict) or not row.get("authority_id") or not isinstance(row.get("rank"), int):
            _reason(reasons, "INVALID_AUTHORITY", f"authorities[{index}]")
            continue
        authorities[row["authority_id"]] = row["rank"]
    chain = delegation.get("authority_chain") if isinstance(delegation.get("authority_chain"), list) else []

    matched = []
    policy_rows = request.get("policies") if isinstance(request.get("policies"), list) else []
    seen_ids = set()
    for index, policy in enumerate(policy_rows):
        path = f"policies[{index}]"
        if not isinstance(policy, dict):
            _reason(reasons, "INVALID_POLICY", path)
            continue
        policy_id = policy.get("policy_id")
        authority_id = policy.get("authority_id")
        effect = policy.get("effect")
        priority = policy.get("priority")
        conditions = policy.get("conditions")
        if not policy_id or policy_id in seen_ids:
            _reason(reasons, "INVALID_POLICY_ID", f"{path}.policy_id")
            continue
        seen_ids.add(policy_id)
        if authority_id not in authorities or authority_id not in chain:
            _reason(reasons, "UNTRACED_AUTHORITY", f"{path}.authority_id")
            continue
        if effect not in EFFECTS or not isinstance(priority, int) or not isinstance(conditions, list):
            _reason(reasons, "INVALID_POLICY", path)
            continue
        if all(evaluate_condition(condition, facts) for condition in conditions):
            matched.append({"policy_id": policy_id, "authority_id": authority_id,
                            "authority_rank": authorities[authority_id],
                            "priority": priority, "effect": effect})

    matched.sort(key=lambda row: (-row["authority_rank"], -row["priority"], row["policy_id"]))
    decision = "ESCALATE"
    selected = []
    if not matched:
        _reason(reasons, "NO_MATCHING_POLICY", "policies")
    elif not reasons:
        precedence = (matched[0]["authority_rank"], matched[0]["priority"])
        selected = [row for row in matched if (row["authority_rank"], row["priority"]) == precedence]
        effects = {row["effect"] for row in selected}
        if len(effects) != 1:
            _reason(reasons, "TIED_CONFLICT", "policies")
        else:
            decision = "ARBITRATED_ALLOW" if effects == {"allow"} else "ARBITRATED_DENY"

    reason_rows = [{"code": code, "path": path} for code, path in sorted(set(reasons))]
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "case_id": str(request.get("case_id", "")),
        "request_sha256": digest(request),
        "decision": decision,
        "reasons": reason_rows,
        "selected_policies": [row["policy_id"] for row in selected],
        "selected_authority": selected[0]["authority_id"] if selected and decision != "ESCALATE" else "",
        "authority_trace": matched,
        "handback": {
            "artifact_id": str(custody.get("artifact_id", "")),
            "return_to": str(delegation.get("return_to", "")),
            "route_id": str(route.get("actual_route_id", "")),
            "confirmed": custody.get("handback_confirmed") is True,
        },
        "gene_provenance": {
            "policy_data_separation": "HC-PILOT-EXT-002",
            "authority_custody_route": "HC-PILOT-HELIX-001",
        },
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(request, receipt):
    return arbitrate(request) == receipt
