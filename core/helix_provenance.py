#!/usr/bin/env python3
"""HELIX provenance + corpus feedback (stdlib only).

Two responsibilities:

  1. trace_winner() — deterministic lineage walk. For an explore winner this is
     EVX -> CIX(source_insight_id) -> IDX -> TCX -> SDX channel; for an exploit
     winner it is seed -> idea_trace.kernel -> corpus sources/parents. Both
     normalize to an ordered [{layer, id}] lineage for audit and dedup.

  2. winner_to_corpus_entry() — the *base-pairing* bond of the double helix:
     an implemented explore winner becomes an exploit corpus source, so the next
     turn of recreate can recombine it. This is the edge that closes the
     explore<->exploit loop (replication template re-use).

Determinism: pure dict-walking; no clock/network/AI.
"""

# Ordered link layers for an explore winner (product -> root).
_EXPLORE_CHAIN_ORDER = ("evx", "cix", "idx", "tcx", "sdx_catalog")


def trace_winner(winner: dict) -> list:
    """Return an ordered lineage [{layer, id}] for an explore or exploit winner.

    Unknown/missing links are skipped. Deterministic and engine-neutral.
    """
    lineage = []
    origin = winner.get("origin")

    # explicit winner id first
    if winner.get("idea_id") or winner.get("id"):
        lineage.append({"layer": "winner", "id": winner.get("idea_id") or winner.get("id")})

    chain = winner.get("source_chain", {}) or {}

    if origin == "exploit" or "idea_trace" in winner or winner.get("seed_name"):
        # exploit (recreate) lineage: seed -> kernel -> corpus sources/parents
        if winner.get("seed_name"):
            lineage.append({"layer": "seed", "id": winner["seed_name"]})
        trace = winner.get("idea_trace", {}) or {}
        if trace.get("kernel_id"):
            lineage.append({"layer": "kernel", "id": trace["kernel_id"]})
        for src in sorted(set(winner.get("sources", []) or [])):
            lineage.append({"layer": "corpus_source", "id": src})
        for parent in sorted(set(winner.get("parents", []) or [])):
            lineage.append({"layer": "parent_project", "id": parent})
        return lineage

    # explore (IdeaFirst) lineage: EVX -> CIX -> IDX -> TCX -> SDX
    if winner.get("source_insight_id"):
        lineage.append({"layer": "insight", "id": winner["source_insight_id"]})
    for layer in _EXPLORE_CHAIN_ORDER:
        if chain.get(layer):
            lineage.append({"layer": layer, "id": chain[layer]})
    for ch in winner.get("source_channels", []) or []:
        lineage.append({"layer": "channel", "id": ch})
    return lineage


def winner_to_corpus_entry(consumed_entry: dict) -> dict:
    """Convert an implemented explore winner into an exploit corpus source stub.

    ** The base-pairing bond. ** Only implemented winners (with a concrete
    project) may enter the corpus, so the exploit engine recombines real assets,
    not vapor. Raises ValueError otherwise.
    """
    impls = consumed_entry.get("implementations") or []
    if not impls:
        raise ValueError("winner_to_corpus_entry: winner has no implementation "
                         "(only built projects may seed the corpus)")
    impl = impls[0]
    if not impl.get("project_name"):
        raise ValueError("winner_to_corpus_entry: implementation has no project_name "
                         "(a corpus source must be a named project)")
    return {
        "project": impl.get("project_name"),
        "repo": impl.get("repo_url"),
        "path": impl.get("project_path"),
        "origin": "explore",                 # exploit can see this came from a scan
        "source_chain": consumed_entry.get("source_chain", {}),
        "semantic_family": consumed_entry.get("semantic_family"),
        "readme_hint": consumed_entry.get("title"),
        "from_idea_id": consumed_entry.get("idea_id"),
    }
