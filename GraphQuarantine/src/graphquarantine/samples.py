"""Sample GraphQuarantine cases."""

import copy

from .core import CASE_SCHEMA, baseline_digest


def sample_case(kind="quarantined"):
    nodes = [
        {"id": "root"},
        {"id": "bad-evidence"},
        {"id": "derived-a"},
        {"id": "derived-b"},
        {"id": "clean-sibling"},
        {"id": "watch-only"},
    ]
    edges = [
        {"from": "bad-evidence", "to": "derived-a", "relation": "derived_from", "propagation": "block"},
        {"from": "derived-a", "to": "derived-b", "relation": "feeds", "propagation": "block"},
        {"from": "bad-evidence", "to": "watch-only", "relation": "mentioned_with", "propagation": "monitor"},
        {"from": "root", "to": "clean-sibling", "relation": "sibling", "propagation": "ignore"},
    ]
    sources = ["bad-evidence"]
    if kind == "clear":
        sources = []
    case = {
        "schema": CASE_SCHEMA,
        "case_id": f"sample-{kind}",
        "nodes": copy.deepcopy(nodes),
        "edges": copy.deepcopy(edges),
        "contamination_sources": sources,
    }
    case["baseline_sha256"] = baseline_digest(case["nodes"], case["edges"], case["contamination_sources"])
    if kind == "invalid-baseline":
        case["baseline_sha256"] = "0" * 64
    return case

