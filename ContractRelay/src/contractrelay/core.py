"""Deterministic fail-closed federated contract relay."""

import copy
import hashlib
import json


CASE_SCHEMA = "contract-relay-case/1.0"
RECEIPT_SCHEMA = "contract-relay-receipt/1.0"
TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def baseline_digest(source, target, contract, payload, custody):
    return digest({
        "source": source,
        "target": target,
        "contract": contract,
        "payload": payload,
        "custody": custody,
    })


def normalized_error(code, path, message, severity="error"):
    return {"code": code, "path": path, "message": message, "severity": severity}


def _value_at(payload, path):
    node = payload
    for part in str(path).split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _validate_case(case):
    reasons = []
    if case.get("schema") != CASE_SCHEMA:
        reasons.append("INVALID_SCHEMA")
    if not isinstance(case.get("source"), str) or not isinstance(case.get("target"), str):
        reasons.append("INVALID_ENDPOINTS")
    if not isinstance(case.get("contract"), dict) or not isinstance(case.get("payload"), dict) or not isinstance(case.get("custody"), dict):
        reasons.append("INVALID_CASE_STRUCTURE")
    if not reasons and case.get("baseline_sha256") != baseline_digest(case["source"], case["target"], case["contract"], case["payload"], case["custody"]):
        reasons.append("BASELINE_HASH_MISMATCH")
    return sorted(set(reasons))


def _contract_errors(case):
    contract, payload = case["contract"], case["payload"]
    errors = []
    allowed_sources = contract.get("allowed_sources", [])
    allowed_targets = contract.get("allowed_targets", [])
    if allowed_sources and case["source"] not in allowed_sources:
        errors.append(normalized_error("SOURCE_NOT_ALLOWED", "$.source", "source is outside contract authority"))
    if allowed_targets and case["target"] not in allowed_targets:
        errors.append(normalized_error("TARGET_NOT_ALLOWED", "$.target", "target is outside contract authority"))
    for field in sorted(contract.get("required_fields", [])):
        exists, _ = _value_at(payload, field)
        if not exists:
            errors.append(normalized_error("MISSING_FIELD", f"$.payload.{field}", "required field is missing"))
    field_types = contract.get("field_types", {})
    for field in sorted(field_types):
        exists, value = _value_at(payload, field)
        if not exists:
            continue
        expected_name = field_types[field]
        expected = TYPES.get(expected_name)
        if expected is None:
            errors.append(normalized_error("UNKNOWN_TYPE", f"$.contract.field_types.{field}", "contract uses an unknown type"))
        elif expected_name == "integer" and isinstance(value, bool):
            errors.append(normalized_error("TYPE_MISMATCH", f"$.payload.{field}", "expected integer"))
        elif expected_name == "number" and isinstance(value, bool):
            errors.append(normalized_error("TYPE_MISMATCH", f"$.payload.{field}", "expected number"))
        elif not isinstance(value, expected):
            errors.append(normalized_error("TYPE_MISMATCH", f"$.payload.{field}", f"expected {expected_name}"))
    return errors


def _custody_errors(case):
    custody = case["custody"]
    errors = []
    if custody.get("from_actor") != case["source"]:
        errors.append(normalized_error("CUSTODY_SOURCE_MISMATCH", "$.custody.from_actor", "custody sender must match source"))
    if custody.get("to_actor") != case["target"]:
        errors.append(normalized_error("CUSTODY_TARGET_MISMATCH", "$.custody.to_actor", "custody receiver must match target"))
    if custody.get("handoff_confirmed") is not True:
        errors.append(normalized_error("HANDOFF_UNCONFIRMED", "$.custody.handoff_confirmed", "handoff must be explicitly confirmed"))
    if not custody.get("route_id"):
        errors.append(normalized_error("ROUTE_MISSING", "$.custody.route_id", "route_id is required"))
    return errors


def _relay_token(case):
    return digest({
        "source": case["source"],
        "target": case["target"],
        "contract_id": case["contract"].get("contract_id", ""),
        "payload_sha256": digest(case["payload"]),
        "route_id": case["custody"].get("route_id", ""),
    })


def relay(case):
    case = copy.deepcopy(case)
    reasons = _validate_case(case)
    errors = []
    relay_token = ""
    if not reasons:
        errors = _contract_errors(case) + _custody_errors(case)
        errors.sort(key=lambda row: (row["code"], row["path"], row["message"]))
        if not errors:
            relay_token = _relay_token(case)
    decision = "INVALID" if reasons else ("BLOCKED" if errors else "RELAYED")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "case_id": str(case.get("case_id", "")),
        "case_sha256": digest(case),
        "decision": decision,
        "reasons": reasons,
        "errors": errors,
        "source": str(case.get("source", "")),
        "target": str(case.get("target", "")),
        "relay_token": relay_token,
        "fail_closed": decision != "RELAYED",
        "gene_provenance": {"normalized_errors": "HC-PILOT-EXT-005", "fail_closed_handback": "HC-PILOT-HELIX-001"},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(case, receipt):
    return relay(case) == receipt

