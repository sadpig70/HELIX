#!/usr/bin/env python3
"""Deterministic machine probes for HELIX Condense v0.6.

The probes validate normalized behavioral evidence, not source text. A meta layer or a
pack runner may produce the evidence, but this module only checks deterministic shape
and algebraic properties:

    {"machine": "M15", "holds": True, "evidence": {...}}

Pure stdlib, no clock/network/AI.
"""

import hashlib
import json

SEVERITY_FAMILIES = (
    ("valid", "thin", "breach"),
    ("compliant", "restricted", "violation"),
    ("certifiable", "needs_review", "blocked"),
    ("balanced", "constrained", "critical_bottleneck"),
)

MAX_MERGE_NAMES = {"max", "max_severity", "worst", "highest_severity", "severity_max"}
PRICE_FIELDS = ("price", "cost", "premium", "option_premium", "scarcity_premium", "fee")
PRICE_SUFFIXES = ("_price", "_cost", "_premium", "_value", "_fee")
SCORE_FIELDS = ("score", "weighted_score", "risk_score", "posture_score", "exposure_score")
DISTRIBUTION_FIELDS = ("count_by_tier", "tier_distribution", "distribution", "counts")


def _result(machine, holds, evidence):
    return {"machine": machine, "holds": bool(holds), "evidence": evidence}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _dicts(value):
    return [x for x in _as_list(value) if isinstance(x, dict)]


def _canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_text(text):
    chars = []
    last_space = False
    for ch in str(text or "").lower():
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            chars.append(ch)
            last_space = False
        elif not last_space:
            chars.append(" ")
            last_space = True
    return " ".join("".join(chars).split())


def _fingerprint_parts(parts):
    tokens = sorted({_normalize_text(p) for p in parts if str(p).strip()})
    return _sha256_text("|".join(tokens))


def _labels_from_artifact(artifact):
    labels = []
    if not isinstance(artifact, dict):
        return labels
    for key in ("severity_order", "verdict_order", "tiers", "bands"):
        for item in _as_list(artifact.get(key)):
            if isinstance(item, dict):
                label = item.get("verdict") or item.get("tier") or item.get("label")
            else:
                label = item
            if label is not None:
                labels.append(str(label))
    for key in ("outputs", "checks", "dimensions", "scored"):
        for item in _dicts(artifact.get(key)):
            label = item.get("verdict") or item.get("tier") or item.get("class") or item.get("band")
            if label is not None:
                labels.append(str(label))
    aggregate = artifact.get("aggregate") or artifact.get("result") or {}
    if isinstance(aggregate, dict):
        label = aggregate.get("verdict") or aggregate.get("tier")
        if label is not None:
            labels.append(str(label))
    return labels


def _severity_family(labels):
    got = set(str(x) for x in labels)
    for family in SEVERITY_FAMILIES:
        if set(family) <= got:
            return family
    return None


def _merge_name(artifact):
    return str(artifact.get("merge") or artifact.get("aggregation") or artifact.get("verdict_merge") or "").lower()


def _has_max_severity_merge(artifact):
    merge = _merge_name(artifact)
    if merge in MAX_MERGE_NAMES:
        return True
    aggregate = artifact.get("aggregate") or artifact.get("result") or {}
    if isinstance(aggregate, dict):
        return str(aggregate.get("merge") or "").lower() in MAX_MERGE_NAMES
    return False


def _numeric_fields(mapping, names):
    if not isinstance(mapping, dict):
        return {}
    out = {}
    for name in names:
        value = mapping.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[name] = value
    return out


def _pricing_numeric_fields(mapping):
    out = _numeric_fields(mapping, PRICE_FIELDS)
    if not isinstance(mapping, dict):
        return out
    for name, value in mapping.items():
        if name in out:
            continue
        if not any(str(name).endswith(suffix) for suffix in PRICE_SUFFIXES):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[name] = value
    return out


def _has_verdict_algebra(artifact):
    return _severity_family(_labels_from_artifact(artifact)) is not None and _has_max_severity_merge(artifact)


def _ledger_core(record):
    return {k: v for k, v in record.items() if k not in ("record_hash", "recorded_at")}


def probe_M1(artifact):
    """M1: append-only hash-chain ledger with canonical record hashes."""
    records = _dicts(artifact.get("records"))
    if not records and isinstance(artifact.get("result"), dict):
        records = _dicts(artifact["result"].get("records"))
    prev = ""
    valid_chain = bool(records)
    time_metadata_excluded = True
    for index, record in enumerate(records):
        if record.get("index") != index:
            valid_chain = False
        if record.get("prev_hash", "") != prev:
            valid_chain = False
        core = _ledger_core(record)
        expected = _sha256_text(_canonical_json(core))
        if record.get("record_hash") != expected:
            valid_chain = False
        alternate = dict(record)
        if "recorded_at" in alternate:
            alternate["recorded_at"] = "__changed__"
            if _sha256_text(_canonical_json(_ledger_core(alternate))) != expected:
                time_metadata_excluded = False
        prev = record.get("record_hash", "")
    holds = valid_chain and time_metadata_excluded
    return _result("M1", holds, {
        "record_count": len(records),
        "valid_chain": valid_chain,
        "time_metadata_excluded": time_metadata_excluded,
    })


def probe_M2(artifact):
    """M2: discrete 3-stage verdict severity with max-severity aggregation."""
    labels = _labels_from_artifact(artifact)
    family = _severity_family(labels)
    holds = family is not None and _has_max_severity_merge(artifact)
    return _result("M2", holds, {
        "severity_family": list(family) if family else [],
        "labels_seen": sorted(set(labels)),
        "max_severity_merge": _has_max_severity_merge(artifact),
    })


def probe_M3(artifact):
    """M3: predicate gate over evidence packet with aggregate verdict."""
    checks = _dicts(artifact.get("checks"))
    aggregate = artifact.get("aggregate") or artifact.get("result") or {}
    if isinstance(aggregate, dict) and not checks:
        checks = _dicts(aggregate.get("checks"))
    packet = artifact.get("packet") if isinstance(artifact.get("packet"), dict) else {}
    has_packet_evidence = bool(packet.get("packet_id") or packet.get("subject") or artifact.get("subject"))
    predicate_shape = bool(checks) and all(
        (row.get("gate") or row.get("check"))
        and row.get("verdict") is not None
        and "reason" in row
        for row in checks
    )
    family = _severity_family([row.get("verdict") for row in checks] + _labels_from_artifact(artifact))
    severity = {name: i for i, name in enumerate(family or [])}
    if predicate_shape and family:
        worst = max(checks, key=lambda row: severity.get(row.get("verdict"), -1))
        expected_verdict = worst.get("verdict")
        expected_worst = worst.get("gate") or worst.get("check")
    else:
        expected_verdict = None
        expected_worst = None
    aggregate_matches = (
        isinstance(aggregate, dict)
        and aggregate.get("verdict") == expected_verdict
        and (aggregate.get("worst") in (expected_worst, None) or expected_worst is None)
    )
    no_private_payload = not any(
        str(k).lower() in {"payload", "private_payload", "raw_payload", "secret", "secrets", "credential", "credentials"}
        for k in packet
    )
    holds = predicate_shape and family is not None and aggregate_matches and has_packet_evidence and no_private_payload
    return _result("M3", holds, {
        "predicate_count": len(checks),
        "severity_family": list(family) if family else [],
        "aggregate_matches": aggregate_matches,
        "has_packet_evidence": has_packet_evidence,
        "no_private_payload": no_private_payload,
    })


def probe_M4(artifact):
    """M4: provenance verification against a confirmed evidence chain."""
    record = artifact.get("record") if isinstance(artifact.get("record"), dict) else {}
    chain = _dicts(artifact.get("chain"))
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    evidence = record.get("evidence_hash") or result.get("evidence_hash")
    confirmed = next((row for row in chain if row.get("evidence_hash") == evidence and row.get("confirmed") is True), None)
    expected_valid = evidence is not None and confirmed is not None
    reported = result.get("provenance_valid")
    chain_length = result.get("chain_length")
    holds = (
        evidence is not None
        and isinstance(chain, list)
        and reported is expected_valid
        and (chain_length in (None, len(chain)))
        and not _has_verdict_algebra(artifact)
    )
    return _result("M4", holds, {
        "evidence_hash": evidence,
        "chain_length": len(chain),
        "confirmed_match": confirmed is not None,
        "reported_matches_expected": reported is expected_valid,
    })


def _numbers_close(a, b, eps=1e-9):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= eps


def _expected_clear_allocations(requests, supply):
    ranked = sorted(requests, key=lambda row: (-float(row.get("priority", 0)), str(row.get("party_id", ""))))
    remaining = float(supply)
    expected = []
    for request in ranked:
        amount = float(request.get("amount", 0))
        take = min(amount, remaining)
        if take > 0:
            expected.append({
                "party_id": request.get("party_id"),
                "amount": take,
                "priority": float(request.get("priority", 0)),
            })
            remaining -= take
    return expected, remaining


def probe_M5(artifact):
    """M5: conflict-free priority clearing over limited supply."""
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    requests = _dicts(result.get("requests"))
    allocations = _dicts(result.get("allocations"))
    supply = result.get("supply")
    allocated = result.get("allocated")
    remaining = result.get("remaining")
    request_shape = bool(requests) and all(
        "party_id" in row
        and isinstance(row.get("amount"), (int, float))
        and not isinstance(row.get("amount"), bool)
        and isinstance(row.get("priority"), (int, float))
        and not isinstance(row.get("priority"), bool)
        for row in requests
    )
    allocation_shape = all(
        "party_id" in row
        and isinstance(row.get("amount"), (int, float))
        and not isinstance(row.get("amount"), bool)
        and row.get("amount") >= 0
        for row in allocations
    )
    supply_shape = isinstance(supply, (int, float)) and not isinstance(supply, bool) and supply >= 0
    parties = [row.get("party_id") for row in allocations]
    no_conflict = len(parties) == len(set(parties))
    requested = {row.get("party_id"): float(row.get("amount", 0)) for row in requests}
    no_overfill_party = all(float(row.get("amount", 0)) <= requested.get(row.get("party_id"), -1) + 1e-9 for row in allocations)
    total_allocated = sum(float(row.get("amount", 0)) for row in allocations)
    conservation = (
        supply_shape
        and _numbers_close(total_allocated, allocated)
        and _numbers_close(float(supply) - total_allocated, remaining)
        and total_allocated <= float(supply) + 1e-9
    )
    expected, expected_remaining = _expected_clear_allocations(requests, supply) if request_shape and supply_shape else ([], None)
    expected_matches = (
        len(expected) == len(allocations)
        and all(
            got.get("party_id") == exp.get("party_id")
            and _numbers_close(float(got.get("amount", 0)), exp.get("amount", 0))
            and _numbers_close(float(got.get("priority", 0)), exp.get("priority", 0))
            for got, exp in zip(allocations, expected)
        )
        and (expected_remaining is not None and _numbers_close(float(remaining), expected_remaining))
    )
    holds = (
        request_shape
        and allocation_shape
        and conservation
        and no_conflict
        and no_overfill_party
        and expected_matches
        and not _has_verdict_algebra(artifact)
    )
    return _result("M5", holds, {
        "request_count": len(requests),
        "allocation_count": len(allocations),
        "conservation": conservation,
        "no_conflict": no_conflict,
        "no_overfill_party": no_overfill_party,
        "priority_allocation_matches": expected_matches,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M6(artifact):
    """M6: deterministic pricing/cost/premium output without verdict algebra."""
    outputs = _dicts(artifact.get("outputs")) or _dicts(artifact.get("priced")) or _dicts(artifact.get("orders"))
    if not outputs and isinstance(artifact.get("result"), dict):
        outputs = [artifact["result"]]
    numeric = []
    for item in outputs:
        fields = _pricing_numeric_fields(item)
        if fields:
            numeric.append(fields)
    operation = str(artifact.get("operation") or artifact.get("stage") or "").lower()
    pricing_named = operation in {"price", "pricing", "costing"} or "pricing" in _as_list(artifact.get("operations"))
    holds = bool(numeric) and (pricing_named or bool(_pricing_numeric_fields(artifact))) and not _has_verdict_algebra(artifact)
    return _result("M6", holds, {
        "numeric_price_fields": numeric,
        "pricing_named": pricing_named,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M7(artifact):
    """M7: settlement/netting result with zero-sum buyer/seller legs."""
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    buyer_net = result.get("buyer_net")
    seller_net = result.get("seller_net")
    settlement_amount = result.get("settlement_amount")
    has_legs = (
        isinstance(buyer_net, (int, float))
        and not isinstance(buyer_net, bool)
        and isinstance(seller_net, (int, float))
        and not isinstance(seller_net, bool)
    )
    zero_sum = has_legs and _numbers_close(float(buyer_net) + float(seller_net), 0.0)
    has_settlement_amount = isinstance(settlement_amount, (int, float)) and not isinstance(settlement_amount, bool)
    has_outcome_or_mode = any(k in result for k in ("actual_failure", "outcome", "settlement_mode", "settled_at"))
    holds = has_legs and zero_sum and has_settlement_amount and has_outcome_or_mode and not _has_verdict_algebra(artifact)
    return _result("M7", holds, {
        "has_legs": has_legs,
        "zero_sum": zero_sum,
        "settlement_amount": settlement_amount,
        "has_outcome_or_mode": has_outcome_or_mode,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M8(artifact):
    """M8: shock rehearsal aggregating survival days and shortfall over items."""
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    per_item = _dicts(result.get("per_item"))
    survival_days = result.get("survival_days")
    total_shortfall = result.get("total_shortfall")
    affected = result.get("affected")
    item_shape = bool(per_item) and all(
        isinstance(row.get("coverage_days"), (int, float))
        and not isinstance(row.get("coverage_days"), bool)
        and isinstance(row.get("shortfall"), (int, float))
        and not isinstance(row.get("shortfall"), bool)
        and row.get("shortfall") >= 0
        for row in per_item
    )
    expected_survival = min((float(row["coverage_days"]) for row in per_item), default=float("inf"))
    expected_shortfall = sum(float(row["shortfall"]) for row in per_item if row.get("shortfall", 0) > 0)
    expected_affected = [
        row.get("id", row.get("party_id", ""))
        for row in per_item
        if row.get("shortfall", 0) > 0
    ]
    affected_shape = isinstance(affected, list) and all(isinstance(x, str) for x in affected)
    survival_matches = item_shape and _numbers_close(float(survival_days), expected_survival)
    shortfall_matches = item_shape and _numbers_close(float(total_shortfall), expected_shortfall)
    affected_matches = affected_shape and list(affected) == expected_affected
    has_scenario = bool(result.get("scenario"))
    holds = (
        item_shape
        and survival_matches
        and shortfall_matches
        and affected_matches
        and has_scenario
        and not _has_verdict_algebra(artifact)
    )
    return _result("M8", holds, {
        "item_count": len(per_item),
        "survival_matches_min_coverage": survival_matches,
        "shortfall_matches_sum": shortfall_matches,
        "affected_matches_positive_shortfall": affected_matches,
        "has_scenario": has_scenario,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M9(artifact):
    """M9: score every candidate, preserve eligibility reasons, select best eligible."""
    all_scores = _dicts(artifact.get("all_scores"))
    if not all_scores and isinstance(artifact.get("result"), dict):
        all_scores = _dicts(artifact["result"].get("all_scores"))
    selected = artifact.get("selected")
    selected_score = artifact.get("selected_score")
    if isinstance(artifact.get("result"), dict):
        selected = artifact["result"].get("selected", selected)
        selected_score = artifact["result"].get("selected_score", selected_score)
    scored_shape = bool(all_scores) and all(
        "name" in row and isinstance(row.get("score"), (int, float)) and not isinstance(row.get("score"), bool)
        and isinstance(row.get("eligible"), bool)
        for row in all_scores
    )
    eligible = [row for row in all_scores if row.get("eligible") is True]
    best = min(eligible, key=lambda row: (-row["score"], str(row["name"]))) if eligible else None
    selected_matches = (
        (best is None and selected in (None, ""))
        or (best is not None and selected == best.get("name") and selected_score == best.get("score"))
    )
    ineligible = [row for row in all_scores if row.get("eligible") is False]
    rejection_reasons_preserved = all(str(row.get("reason", "")) for row in ineligible)
    holds = scored_shape and selected_matches and rejection_reasons_preserved and not _has_verdict_algebra(artifact)
    return _result("M9", holds, {
        "candidate_count": len(all_scores),
        "eligible_count": len(eligible),
        "selected": selected,
        "best_eligible": best.get("name") if best else None,
        "selected_matches_best": selected_matches,
        "rejection_reasons_preserved": rejection_reasons_preserved,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M10(artifact):
    """M10: threshold-bound dimensions merged by highest severity."""
    dimensions = _dicts(artifact.get("dimensions"))
    thresholds = _dicts(artifact.get("thresholds")) or _dicts(artifact.get("bounds"))
    labels = []
    for dim in dimensions:
        if "dimension" in dim and "verdict" in dim:
            labels.append(str(dim["verdict"]))
    family = _severity_family(labels + _labels_from_artifact(artifact))
    has_dimension_verdicts = bool(dimensions) and all("dimension" in d and "verdict" in d for d in dimensions)
    has_threshold_evidence = bool(thresholds) or any(
        any(k in d for k in ("threshold", "limit", "min", "max", "utilization")) for d in dimensions
    )
    holds = has_dimension_verdicts and has_threshold_evidence and family is not None and _has_max_severity_merge(artifact)
    return _result("M10", holds, {
        "dimension_count": len(dimensions),
        "threshold_evidence": has_threshold_evidence,
        "severity_family": list(family) if family else [],
        "max_severity_merge": _has_max_severity_merge(artifact),
    })


def probe_M11(artifact):
    """M11: baseline/current drift magnitude classified against a threshold."""
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    policy = artifact.get("policy") if isinstance(artifact.get("policy"), dict) else {}
    if not policy and isinstance(artifact.get("packet"), dict):
        policy = artifact["packet"].get("policy", {})
    baseline = policy.get("baseline_id") or result.get("baseline_id")
    current = policy.get("current_id") or result.get("current_id")
    drift = policy.get("drift", result.get("drift"))
    threshold = policy.get("drift_threshold", result.get("drift_threshold"))
    checks = _dicts(artifact.get("checks")) or _dicts(result.get("checks"))
    drift_check = next((row for row in checks if row.get("gate") == "drift_magnitude" or row.get("check") == "drift_magnitude"), None)
    numeric = (
        isinstance(drift, (int, float))
        and not isinstance(drift, bool)
        and isinstance(threshold, (int, float))
        and not isinstance(threshold, bool)
        and threshold >= 0
    )
    if numeric:
        if drift <= threshold:
            expected = "valid"
        elif drift <= threshold * 1.2:
            expected = "thin"
        else:
            expected = "breach"
    else:
        expected = None
    check_matches = drift_check is not None and drift_check.get("verdict") == expected
    holds = bool(baseline) and bool(current) and numeric and check_matches
    return _result("M11", holds, {
        "baseline_present": bool(baseline),
        "current_present": bool(current),
        "drift": drift,
        "drift_threshold": threshold,
        "expected_verdict": expected,
        "check_matches_expected": check_matches,
    })


def _expected_stage_plan(source_stages):
    plan = []
    cumulative = 0.0
    halted = False
    for i, stage in enumerate(source_stages):
        cohort = stage.get("cohort_pct", 0)
        cumulative += float(cohort)
        observed = stage.get("observed_incidents", 0)
        threshold = stage.get("incident_threshold", 0)
        gate = "go" if observed <= threshold else "halt"
        plan.append({
            "stage": stage.get("name", f"stage-{i}"),
            "cohort_pct": cohort,
            "cumulative_pct": cumulative,
            "observation_window": stage.get("observation_window"),
            "observed_incidents": observed,
            "incident_threshold": threshold,
            "gate": gate,
        })
        if gate == "halt":
            halted = True
            break
    complete = (not halted) and bool(plan) and abs(cumulative - 100.0) < 1e-6
    return plan, halted, complete


def probe_M12(artifact):
    """M12: staged rollout/quarantine schedule with go/halt observation gates."""
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    planned = _dicts(result.get("stages"))
    release = result.get("release") if isinstance(result.get("release"), dict) else {}
    source_stages = _dicts(release.get("stages")) or _dicts(result.get("source_stages"))
    halted = result.get("halted")
    rollout_complete = result.get("rollout_complete")
    source_shape = bool(source_stages) and all(
        "cohort_pct" in row
        and isinstance(row.get("cohort_pct"), (int, float))
        and not isinstance(row.get("cohort_pct"), bool)
        and isinstance(row.get("observed_incidents", 0), (int, float))
        and not isinstance(row.get("observed_incidents", 0), bool)
        and isinstance(row.get("incident_threshold", 0), (int, float))
        and not isinstance(row.get("incident_threshold", 0), bool)
        for row in source_stages
    )
    planned_shape = bool(planned) and all(
        "stage" in row
        and isinstance(row.get("cohort_pct"), (int, float))
        and not isinstance(row.get("cohort_pct"), bool)
        and isinstance(row.get("cumulative_pct"), (int, float))
        and not isinstance(row.get("cumulative_pct"), bool)
        and row.get("gate") in ("go", "halt")
        for row in planned
    )
    expected, expected_halted, expected_complete = _expected_stage_plan(source_stages) if source_shape else ([], None, None)
    plan_matches = (
        planned_shape
        and len(planned) == len(expected)
        and all(
            got.get("stage") == exp.get("stage")
            and _numbers_close(float(got.get("cohort_pct", 0)), float(exp.get("cohort_pct", 0)))
            and _numbers_close(float(got.get("cumulative_pct", 0)), float(exp.get("cumulative_pct", 0)))
            and got.get("observation_window") == exp.get("observation_window")
            and got.get("observed_incidents") == exp.get("observed_incidents")
            and got.get("incident_threshold") == exp.get("incident_threshold")
            and got.get("gate") == exp.get("gate")
            for got, exp in zip(planned, expected)
        )
    )
    halt_state_matches = halted is expected_halted
    complete_state_matches = rollout_complete is expected_complete
    holds = (
        source_shape
        and planned_shape
        and plan_matches
        and halt_state_matches
        and complete_state_matches
        and not _has_verdict_algebra(artifact)
    )
    return _result("M12", holds, {
        "source_stage_count": len(source_stages),
        "planned_stage_count": len(planned),
        "plan_matches_source": plan_matches,
        "halt_state_matches": halt_state_matches,
        "complete_state_matches": complete_state_matches,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M13(artifact):
    """M13: compatibility/gap scoring across source-target pairs.

    Distinct from M9 (select one), M10 (threshold-bound verdict), and M15 (tier
    distribution): M13 scores pairwise compatibility/gap surfaces and summarizes them.
    """
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    pairs = _dicts(result.get("pairs")) or _dicts(result.get("scored_pairs"))
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    pair_shape = bool(pairs) and all(
        (row.get("source") or row.get("source_id"))
        and (row.get("target") or row.get("target_id"))
        and isinstance(row.get("compatibility_score"), (int, float))
        and not isinstance(row.get("compatibility_score"), bool)
        and isinstance(row.get("gap_score"), (int, float))
        and not isinstance(row.get("gap_score"), bool)
        for row in pairs
    )
    scores_in_range = pair_shape and all(
        0 <= float(row.get("compatibility_score")) <= 1
        and 0 <= float(row.get("gap_score")) <= 1
        for row in pairs
    )
    count = len(pairs)
    mean_compat = round(sum(float(row["compatibility_score"]) for row in pairs) / count, 6) if count else 0.0
    mean_gap = round(sum(float(row["gap_score"]) for row in pairs) / count, 6) if count else 0.0
    summary_matches = (
        summary.get("pair_count") in (None, count)
        and (summary.get("mean_compatibility") is None or _numbers_close(float(summary["mean_compatibility"]), mean_compat))
        and (summary.get("mean_gap") is None or _numbers_close(float(summary["mean_gap"]), mean_gap))
    )
    has_route_selection = "selected" in result or "all_scores" in result
    has_tier_distribution = any(isinstance(result.get(key), dict) for key in DISTRIBUTION_FIELDS)
    has_price_fields = bool(_pricing_numeric_fields(result)) or any(bool(_pricing_numeric_fields(row)) for row in pairs)
    holds = (
        pair_shape
        and scores_in_range
        and summary_matches
        and not has_route_selection
        and not has_tier_distribution
        and not has_price_fields
        and not _has_verdict_algebra(artifact)
    )
    return _result("M13", holds, {
        "pair_count": count,
        "scores_in_range": scores_in_range,
        "summary_matches": summary_matches,
        "route_selection_absent": not has_route_selection,
        "tier_distribution_absent": not has_tier_distribution,
        "pricing_absent": not has_price_fields,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M14(artifact):
    """M14: deterministic identity fingerprint and duplicate-surface detection."""
    items = _dicts(artifact.get("items"))
    if not items and isinstance(artifact.get("result"), dict):
        items = _dicts(artifact["result"].get("items"))
    checked = []
    groups = {}
    for item in items:
        parts = item.get("parts")
        if parts is None:
            parts = [item.get("packet_schema", ""), *item.get("predicates", [])]
        expected = _fingerprint_parts(parts)
        got = item.get("fingerprint")
        checked.append(got == expected)
        groups.setdefault(got, []).append(item.get("name", ""))
    duplicate_groups = [names for names in groups.values() if len([n for n in names if n]) > 1]
    reported_duplicates = artifact.get("duplicate_groups")
    if reported_duplicates is None and isinstance(artifact.get("result"), dict):
        reported_duplicates = artifact["result"].get("duplicate_groups")
    if reported_duplicates is None:
        duplicates_match = True
    else:
        normalized_expected = sorted(sorted(g) for g in duplicate_groups)
        normalized_reported = sorted(sorted(g) for g in reported_duplicates)
        duplicates_match = normalized_expected == normalized_reported
    holds = bool(items) and all(checked) and duplicates_match
    return _result("M14", holds, {
        "item_count": len(items),
        "fingerprints_match": all(checked) if checked else False,
        "duplicate_group_count": len(duplicate_groups),
        "duplicates_match_report": duplicates_match,
    })


def _tiers_from_bands(bands):
    tiers = []
    for band in _dicts(bands):
        tier = band.get("tier") or band.get("label") or band.get("class")
        if tier is not None:
            tiers.append(str(tier))
    return tiers


def probe_M15(artifact):
    """M15: weighted assessment score -> tier/rule class -> aggregate distribution."""
    scored = _dicts(artifact.get("scored"))
    if not scored and isinstance(artifact.get("result"), dict):
        scored = _dicts(artifact["result"].get("scored"))
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    distribution = {}
    for key in DISTRIBUTION_FIELDS:
        if isinstance(result.get(key), dict):
            distribution = result[key]
            break
    bands = _dicts(artifact.get("bands"))
    rules = _dicts(artifact.get("rules"))
    weights = artifact.get("weights") if isinstance(artifact.get("weights"), dict) else {}
    tiers = set(_tiers_from_bands(bands))
    tiers.update(str(r.get("tier")) for r in rules if r.get("tier") is not None)
    tiers.update(str(x.get("tier")) for x in scored if x.get("tier") is not None)
    score_fields = []
    for item in scored:
        fields = _numeric_fields(item, SCORE_FIELDS)
        if fields:
            score_fields.append(fields)
    weighted_score_evidence = bool(weights) or bool(score_fields)
    rule_ladder_evidence = bool(rules) and bool(scored)
    tiered_items = bool(scored) and all("tier" in item for item in scored)
    distribution_matches_tiers = bool(distribution) and set(str(k) for k in distribution).issubset(tiers or set(distribution))
    holds = (
        bool(tiers)
        and tiered_items
        and distribution_matches_tiers
        and (weighted_score_evidence or rule_ladder_evidence)
        and not _has_verdict_algebra(artifact)
    )
    return _result("M15", holds, {
        "weighted_score_evidence": weighted_score_evidence,
        "rule_ladder_evidence": rule_ladder_evidence,
        "tier_count": len(tiers),
        "distribution_keys": sorted(str(k) for k in distribution),
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M16(artifact):
    """M16: route deviation simulation with rollback restoration evidence.

    This is intentionally narrower than generic simulation. It targets RouteSentinel's
    documented surface: planned route, actual route, deviation policy, rollback state,
    and a deterministic control decision.
    """
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    planned = _as_list(result.get("planned_route"))
    actual = _as_list(result.get("actual_route"))
    policy = result.get("deviation_policy") if isinstance(result.get("deviation_policy"), dict) else {}
    rollback = result.get("rollback") if isinstance(result.get("rollback"), dict) else {}
    reported = result.get("simulation") if isinstance(result.get("simulation"), dict) else result

    route_shape = (
        bool(planned)
        and bool(actual)
        and all(isinstance(step, str) and step for step in planned)
        and all(isinstance(step, str) and step for step in actual)
    )
    planned_set = set(planned)
    deviations = [step for step in actual if step not in planned_set]
    blocked = set(str(x) for x in _as_list(policy.get("blocked_zones")))
    blocked_hits = [step for step in actual if step in blocked]
    max_deviation_count = policy.get("max_deviation_count", 0)
    max_shape = isinstance(max_deviation_count, int) and not isinstance(max_deviation_count, bool) and max_deviation_count >= 0
    rollback_required = bool(deviations or blocked_hits or (max_shape and len(deviations) > max_deviation_count))
    rollback_completed = rollback.get("completed") is True
    expected_decision = "rollback" if rollback_required and rollback_completed else (
        "reroute" if rollback_required else "clear"
    )
    restored_route = rollback.get("restored_route")
    if restored_route is None:
        restored_route = reported.get("restored_route")
    restored_matches = (not rollback_required) or (list(restored_route or []) == list(planned))

    simulation_matches = (
        reported.get("deviation_count") in (None, len(deviations))
        and reported.get("blocked_zone_hits") in (None, len(blocked_hits))
        and reported.get("rollback_required") in (None, rollback_required)
        and reported.get("decision") == expected_decision
    )
    holds = (
        route_shape
        and max_shape
        and simulation_matches
        and restored_matches
        and not _has_verdict_algebra(artifact)
    )
    return _result("M16", holds, {
        "planned_steps": len(planned),
        "actual_steps": len(actual),
        "deviation_count": len(deviations),
        "blocked_zone_hits": len(blocked_hits),
        "rollback_required": rollback_required,
        "rollback_completed": rollback_completed,
        "expected_decision": expected_decision,
        "simulation_matches": simulation_matches,
        "restored_matches": restored_matches,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


def probe_M17(artifact):
    """M17: endowment funding projection with sustainability/access verdict.

    Narrow EndowFront surface: aggregate one-time pledges, project corpus/payout/cost
    over a declared horizon, then decide endowed/underfunded/depleted and open access.
    """
    result = artifact.get("result") if isinstance(artifact.get("result"), dict) else artifact
    policy = result.get("policy") if isinstance(result.get("policy"), dict) else {}
    pledges = _dicts(result.get("pledges"))
    schedule = _dicts(result.get("schedule"))
    posture = result.get("posture") if isinstance(result.get("posture"), dict) else {}
    evidence = _dicts(result.get("evidence"))

    amounts = [p.get("amount") for p in pledges]
    pledge_shape = bool(pledges) and all(
        p.get("pledge_id")
        and isinstance(p.get("amount"), (int, float))
        and not isinstance(p.get("amount"), bool)
        and p.get("amount") > 0
        for p in pledges
    )
    policy_numbers = all(
        isinstance(policy.get(k), (int, float)) and not isinstance(policy.get(k), bool)
        for k in ("real_return_rate", "frontier_cost_year0", "cost_growth_rate", "min_coverage_ratio")
    )
    horizon = policy.get("horizon_years")
    policy_shape = (
        policy_numbers
        and isinstance(horizon, int)
        and not isinstance(horizon, bool)
        and horizon > 0
        and policy.get("frontier_cost_year0") > 0
        and policy.get("real_return_rate") >= 0
        and policy.get("cost_growth_rate") >= 0
    )
    corpus0 = sum(float(x) for x in amounts) if pledge_shape else 0.0
    expected_cost = float(policy.get("frontier_cost_year0", 0.0))
    expected_opening = corpus0
    schedule_matches = bool(schedule) and policy_shape and len(schedule) <= int(horizon)
    for i, row in enumerate(schedule, start=1):
        opening = row.get("opening_corpus")
        payout = row.get("payout")
        cost = row.get("cost")
        closing = row.get("closing_corpus")
        row_ok = (
            row.get("year") == i
            and _numbers_close(float(opening), expected_opening)
            and _numbers_close(float(payout), expected_opening * float(policy["real_return_rate"]))
            and _numbers_close(float(cost), expected_cost)
            and _numbers_close(float(closing), expected_opening + float(payout) - float(cost))
        ) if all(isinstance(v, (int, float)) and not isinstance(v, bool)
                 for v in (opening, payout, cost, closing)) else False
        if not row_ok:
            schedule_matches = False
            break
        expected_opening = float(closing)
        if expected_opening < 0:
            break
        expected_cost = expected_cost * (1.0 + float(policy["cost_growth_rate"]))

    closings = [float(row.get("closing_corpus", 0.0)) for row in schedule]
    years_funded = 0
    for closing in closings:
        if closing < 0:
            break
        years_funded += 1
    funded_all_horizon = years_funded >= int(horizon) if policy_shape else False
    final_corpus = closings[years_funded - 1] if years_funded > 0 else corpus0
    min_corpus = min(closings) if closings else corpus0
    preserved = final_corpus >= corpus0 - 1e-9
    payout_year0 = corpus0 * float(policy.get("real_return_rate", 0.0))
    coverage_year0 = payout_year0 / float(policy.get("frontier_cost_year0", 1.0)) if policy_shape else 0.0
    if not funded_all_horizon:
        expected_verdict = "depleted"
    elif preserved and coverage_year0 >= float(policy.get("min_coverage_ratio", 0.0)):
        expected_verdict = "endowed"
    else:
        expected_verdict = "underfunded"
    expected_open_access = expected_verdict == "endowed" and bool(policy.get("require_open_access"))

    posture_matches = (
        posture.get("verdict") == expected_verdict
        and _numbers_close(float(posture.get("corpus", -1)), corpus0)
        and _numbers_close(float(posture.get("payout_year0", -1)), payout_year0)
        and _numbers_close(float(posture.get("coverage_year0", -1)), coverage_year0)
        and posture.get("years_funded") == years_funded
        and posture.get("horizon_years") == horizon
        and _numbers_close(float(posture.get("min_corpus", -1)), min_corpus)
        and _numbers_close(float(posture.get("final_corpus", -1)), final_corpus)
        and posture.get("preserved") is preserved
        and posture.get("open_access_granted") is expected_open_access
    ) if posture else False
    evidence_shape = len(evidence) in (0, len(pledges)) and all(row.get("ref_id") for row in evidence)
    holds = (
        pledge_shape
        and policy_shape
        and schedule_matches
        and posture_matches
        and evidence_shape
        and not _has_verdict_algebra(artifact)
    )
    return _result("M17", holds, {
        "pledge_count": len(pledges),
        "schedule_years": len(schedule),
        "corpus": corpus0,
        "expected_verdict": expected_verdict,
        "coverage_year0": round(coverage_year0, 6),
        "years_funded": years_funded,
        "schedule_matches": schedule_matches,
        "posture_matches": posture_matches,
        "evidence_shape": evidence_shape,
        "verdict_algebra_absent": not _has_verdict_algebra(artifact),
    })


PROBES = {
    "M1": probe_M1,
    "M2": probe_M2,
    "M3": probe_M3,
    "M4": probe_M4,
    "M5": probe_M5,
    "M6": probe_M6,
    "M7": probe_M7,
    "M8": probe_M8,
    "M9": probe_M9,
    "M10": probe_M10,
    "M11": probe_M11,
    "M12": probe_M12,
    "M13": probe_M13,
    "M14": probe_M14,
    "M15": probe_M15,
    "M16": probe_M16,
    "M17": probe_M17,
}


def normalize_machine_id(value):
    text = str(value).strip()
    if "(" in text:
        text = text.split("(", 1)[0]
    if "+" in text:
        text = text.split("+", 1)[0]
    return text.strip()


def probe(machine, artifact):
    machine_id = normalize_machine_id(machine)
    if machine_id not in PROBES:
        return _result(machine_id, False, {"error": "probe_not_implemented"})
    return PROBES[machine_id](artifact)


def probe_all(artifact, machines=None):
    ids = [normalize_machine_id(m) for m in (machines or sorted(PROBES))]
    return {m: probe(m, artifact) for m in ids}


def agreement_report(cases):
    """Measure probe agreement for supplied normalized cases.

    cases: [{"id": str, "expected": ["M2", ...], "artifact": {...}}, ...]
    Only machines with implemented probes are scored. Unknown expected machines are
    reported but excluded from the denominator.
    """
    rows = []
    total = 0
    matched = 0
    for case in cases:
        expected = sorted({normalize_machine_id(m) for m in case.get("expected", [])})
        implemented = [m for m in expected if m in PROBES]
        results = probe_all(case.get("artifact", {}), implemented)
        row_matches = sorted(m for m, r in results.items() if r["holds"])
        total += len(implemented)
        matched += len([m for m in implemented if results[m]["holds"]])
        row = {
            "id": case.get("id", ""),
            "expected": expected,
            "scored": implemented,
            "matched": row_matches,
            "results": results,
        }
        for key in ("platform", "pack", "stage"):
            if key in case:
                row[key] = case[key]
        rows.append(row)
    return {
        "cases": len(rows),
        "scored_claims": total,
        "matched_claims": matched,
        "agreement": round(matched / total, 6) if total else 0.0,
        "rows": rows,
    }
