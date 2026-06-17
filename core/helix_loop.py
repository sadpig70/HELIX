#!/usr/bin/env python3
"""HELIX explore<->exploit loop driver (stdlib only).

The deterministic policy that makes the system a *spiral, not a circle*: it
decides what the next turn does, prioritising loop closure (record consumed) and
diversity refresh (anti-homogenization) over raw generation. This is the single
place where the two engines are sequenced; the engines themselves stay independent.

Action vocabulary:
    RECORD_CONSUMED  - an implemented winner must be written to the ledger
                       (closes provenance; base-pairing). Highest priority.
    REFRESH_INPUTS   - diversity triggered -> refresh inputs before generating
                       (explore: sdx/sdxx refresh; exploit: bump avoidance).
    RUN_EXPLORE      - scan the world for fresh signal (IdeaFirst).
    RUN_EXPLOIT      - recombine accumulated assets (recreate).

Determinism: pure function of `state`; identical state -> identical action.
"""

DEFAULT_LOOP_POLICY = {
    "min_corpus_for_exploit": 2,   # below this, prefer fresh external signal
}

VALID_ACTIONS = ("RECORD_CONSUMED", "REFRESH_INPUTS", "RUN_EXPLORE", "RUN_EXPLOIT")


def next_action(state: dict, policy: dict = None) -> dict:
    """Decide the next loop action from the current state (deterministic).

    Expected `state` keys (all optional, with safe defaults):
        last_engine: "explore" | "exploit" | None
        diversity: {"triggered": bool, ...}     (from measure_diversity)
        corpus_size: int                         (exploit corpus source count)
        pending_implemented_winner: bool         (a built winner awaiting record)
        winner_in_ledger: bool                   (already recorded?)

    Returns {action, why, [target]}.
    """
    P = dict(DEFAULT_LOOP_POLICY)
    if policy:
        P.update(policy)

    last_engine = state.get("last_engine")
    diversity = state.get("diversity") or {}
    corpus_size = int(state.get("corpus_size", 0))

    # 1) Close the loop first — an implemented winner must enter the ledger.
    if state.get("pending_implemented_winner") and not state.get("winner_in_ledger"):
        return {"action": "RECORD_CONSUMED",
                "why": "implemented winner -> ledger (close provenance; base-pairing)"}

    # 2) Repair before reproducing — homogenization OR exploit-side island collapse.
    #    repair_required subsumes `triggered` and adds the unique_ratio-floor signal,
    #    so a recreate-side collapse cannot be visible-but-non-actionable.
    if diversity.get("repair_required", diversity.get("triggered")):
        target = "explore" if last_engine == "exploit" else "both"
        return {"action": "REFRESH_INPUTS",
                "why": "diversity repair_required -> refresh inputs before generating",
                "target": target}

    # 3) Immature corpus -> bring in fresh external novelty.
    if corpus_size < P["min_corpus_for_exploit"]:
        return {"action": "RUN_EXPLORE",
                "why": "corpus immature -> scan world for fresh signal"}

    # 4) Balance the two strands: after explore, compound via exploit; else explore.
    if last_engine == "explore":
        return {"action": "RUN_EXPLOIT",
                "why": "fresh assets accumulated -> recombine (compound)"}
    return {"action": "RUN_EXPLORE",
            "why": "balance the strands -> scan for fresh signal"}
