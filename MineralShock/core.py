#!/usr/bin/env python3
"""MineralShock core logic (stdlib only).

ReserveFlow (strategic-mineral reserve right pricing) +
RefusalOption (refusal option premium) +
ShockRehearsal (supply shock simulation).
"""

from __future__ import annotations


def price_reserve_right(mineral, stockpile_tonnes, criticality, daily_demand):
    """Price the right to draw on a strategic-mineral reserve stockpile."""
    coverage_days = (
        stockpile_tonnes / daily_demand if daily_demand > 0 else float("inf")
    )
    scarcity_premium = criticality / max(coverage_days, 1)
    right_price = stockpile_tonnes * criticality * (1 + scarcity_premium)
    return {
        "mineral": mineral,
        "stockpile_tonnes": stockpile_tonnes,
        "criticality": criticality,
        "daily_demand": daily_demand,
        "coverage_days": coverage_days,
        "scarcity_premium": scarcity_premium,
        "right_price": right_price,
    }


def price_refusal_option(refusal_capacity_tonnes, threat_level, mineral_value):
    """Price the option premium for refusing to ship a mineral."""
    option_premium = refusal_capacity_tonnes * mineral_value * threat_level * 0.1
    return {
        "refusal_capacity_tonnes": refusal_capacity_tonnes,
        "threat_level": threat_level,
        "mineral_value": mineral_value,
        "option_premium": option_premium,
    }


def simulate_shock(scenario, reserves):
    """Rehearse a supply shock against a set of mineral reserves.

    scenario: {"name", "demand_spiup_pct", "supply_disruption_pct"}
    reserves: list of {"mineral", "stockpile_tonnes", "daily_demand", ...}
    """
    name = scenario.get("name", "")
    demand_spiup_pct = scenario.get("demand_spiup_pct", 0)
    supply_disruption_pct = scenario.get("supply_disruption_pct", 0)

    per_mineral = []
    affected_minerals = []
    total_shortfall_tonnes = 0.0
    coverage_values = []

    for r in reserves:
        mineral = r.get("mineral", "")
        stockpile = r.get("stockpile_tonnes", 0)
        daily_demand = r.get("daily_demand", 0)

        effective_stockpile = stockpile * (1 - supply_disruption_pct)
        shocked_demand = daily_demand * (1 + demand_spiup_pct)
        if shocked_demand > 0:
            shocked_coverage = effective_stockpile / shocked_demand
        else:
            shocked_coverage = float("inf")
        shortfall = stockpile * supply_disruption_pct

        per_mineral.append(
            {
                "mineral": mineral,
                "effective_stockpile_tonnes": effective_stockpile,
                "shocked_daily_demand": shocked_demand,
                "coverage_days": shocked_coverage,
                "shortfall_tonnes": shortfall,
            }
        )
        coverage_values.append(shocked_coverage)
        if shortfall > 0:
            total_shortfall_tonnes += shortfall
            affected_minerals.append(mineral)

    survival_days = min(coverage_values) if coverage_values else float("inf")

    return {
        "scenario_name": name,
        "demand_spiup_pct": demand_spiup_pct,
        "supply_disruption_pct": supply_disruption_pct,
        "total_shortfall_tonnes": total_shortfall_tonnes,
        "affected_minerals": affected_minerals,
        "survival_days": survival_days,
        "per_mineral": per_mineral,
    }


def _fmt(value):
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value == float("inf"):
            return "inf"
        return f"{value:.4f}"
    return str(value)


def render_report(result):
    """Render a Markdown report for a MineralShock result."""
    if "scenario_name" in result:
        return _render_shock(result)
    if "right_price" in result:
        return _render_reserve(result)
    if "option_premium" in result:
        return _render_refusal(result)
    return _render_generic(result)


def _render_shock(result):
    lines = [
        f"# MineralShock Report \u2014 {result.get('scenario_name', '')}",
        "",
        f"- demand_spiup_pct: {_fmt(result.get('demand_spiup_pct', 0))}",
        f"- supply_disruption_pct: {_fmt(result.get('supply_disruption_pct', 0))}",
        f"- total_shortfall_tonnes: {_fmt(result.get('total_shortfall_tonnes', 0))}",
        f"- survival_days: {_fmt(result.get('survival_days', 0))}",
        "",
        "## Per-mineral impact",
        "",
        "| mineral | effective_stockpile_tonnes | shocked_daily_demand | coverage_days | shortfall_tonnes |",
        "|---|---|---|---|---|",
    ]
    for m in result.get("per_mineral", []):
        lines.append(
            f"| {m.get('mineral', '')} "
            f"| {_fmt(m.get('effective_stockpile_tonnes', 0))} "
            f"| {_fmt(m.get('shocked_daily_demand', 0))} "
            f"| {_fmt(m.get('coverage_days', 0))} "
            f"| {_fmt(m.get('shortfall_tonnes', 0))} |"
        )
    lines.append("")
    lines.append("## Affected minerals")
    lines.append("")
    affected = result.get("affected_minerals", [])
    if affected:
        for mineral in affected:
            lines.append(f"- {mineral}")
    else:
        lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)


def _render_reserve(result):
    lines = [
        f"# MineralShock Reserve Right \u2014 {result.get('mineral', '')}",
        "",
        f"- stockpile_tonnes: {_fmt(result.get('stockpile_tonnes', 0))}",
        f"- criticality: {_fmt(result.get('criticality', 0))}",
        f"- daily_demand: {_fmt(result.get('daily_demand', 0))}",
        f"- coverage_days: {_fmt(result.get('coverage_days', 0))}",
        f"- scarcity_premium: {_fmt(result.get('scarcity_premium', 0))}",
        f"- right_price: {_fmt(result.get('right_price', 0))}",
        "",
    ]
    return "\n".join(lines)


def _render_refusal(result):
    lines = [
        "# MineralShock Refusal Option",
        "",
        f"- refusal_capacity_tonnes: {_fmt(result.get('refusal_capacity_tonnes', 0))}",
        f"- threat_level: {_fmt(result.get('threat_level', 0))}",
        f"- mineral_value: {_fmt(result.get('mineral_value', 0))}",
        f"- option_premium: {_fmt(result.get('option_premium', 0))}",
        "",
    ]
    return "\n".join(lines)


def _render_generic(result):
    lines = ["# MineralShock Report", ""]
    for key in sorted(result.keys()):
        lines.append(f"- {key}: {_fmt(result[key])}")
    lines.append("")
    return "\n".join(lines)
