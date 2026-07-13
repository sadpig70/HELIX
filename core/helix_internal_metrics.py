#!/usr/bin/env python3
"""Internal-only operational metrics; never a T4 or product claim."""

from .helix_transaction import verify_transaction

SCHEMA_ID = "helix-internal-control-metrics/1.0"


def aggregate_internal_metrics(transactions: list) -> dict:
    counts = {"verified_transactions": 0, "blocked": 0, "rolled_back": 0,
              "replayable": 0, "quarantined": 0, "invalid": 0}
    for tx in transactions:
        if verify_transaction(tx):
            counts["invalid"] += 1
            continue
        counts["verified_transactions"] += 1
        state = tx["state"]
        key = {"BLOCKED": "blocked", "ROLLED_BACK": "rolled_back",
               "REPLAYABLE": "replayable",
               "QUARANTINED": "quarantined"}.get(state)
        if key:
            counts[key] += 1
    denominator = counts["verified_transactions"] or 1
    return {"schema": SCHEMA_ID, "scope": "internal_optimization_only",
            "is_t4_utility": False, "is_product_claim": False,
            "counts": counts,
            "replay_rate": counts["replayable"] / denominator,
            "rollback_rate": counts["rolled_back"] / denominator}
