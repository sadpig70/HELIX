#!/usr/bin/env python3
"""Deterministic sample reserves and shock scenarios for MineralShock."""

import copy

LITHIUM = {
    "mineral": "lithium",
    "stockpile_tonnes": 12000,
    "criticality": 0.92,
    "daily_demand": 40,
}

COBALT = {
    "mineral": "cobalt",
    "stockpile_tonnes": 8000,
    "criticality": 0.85,
    "daily_demand": 25,
}

RARE_EARTH = {
    "mineral": "rare_earth",
    "stockpile_tonnes": 5000,
    "criticality": 0.95,
    "daily_demand": 15,
}

SCENARIO_TRADE_WAR = {
    "name": "trade-war-2026",
    "demand_spiup_pct": 0.35,
    "supply_disruption_pct": 0.40,
}

SCENARIO_BLOCKADE = {
    "name": "strait-blockade-2026",
    "demand_spiup_pct": 0.60,
    "supply_disruption_pct": 0.70,
}


def mineral_reserves():
    return [copy.deepcopy(LITHIUM), copy.deepcopy(COBALT), copy.deepcopy(RARE_EARTH)]


def shock_scenarios():
    return [copy.deepcopy(SCENARIO_TRADE_WAR), copy.deepcopy(SCENARIO_BLOCKADE)]


def samples():
    return {
        "lithium": copy.deepcopy(LITHIUM),
        "cobalt": copy.deepcopy(COBALT),
        "rare_earth": copy.deepcopy(RARE_EARTH),
        "trade_war": {
            "scenario": copy.deepcopy(SCENARIO_TRADE_WAR),
            "reserves": mineral_reserves(),
        },
        "blockade": {
            "scenario": copy.deepcopy(SCENARIO_BLOCKADE),
            "reserves": mineral_reserves(),
        },
    }


def write_samples(out_dir):
    import json
    import os

    os.makedirs(out_dir, exist_ok=True)
    written = {}
    for name, doc in samples().items():
        path = os.path.join(out_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        written[name] = path
    return written
