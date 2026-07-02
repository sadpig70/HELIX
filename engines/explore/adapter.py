#!/usr/bin/env python3
"""HELIX-A — Explore strand adapter (IdeaFirst -> backbone). Pure transforms, stdlib only.

Maps the canonical IdeaFirst runtime artifacts onto HELIX-Core structures so the
explore engine stops keeping its own ledger/diversity/provenance logic:

    .evx/latest/stage6_final.yaml   -> winner candidate (ledger.is_consumed)
    .cix/latest/idea_pool.yaml      -> diversity pool (diversity.measure_diversity)
    .evx/latest/manifest.yaml       -> provenance source_chain
    .idea-ledger/consumed_ideas.yaml-> unified HELIX ledger

These functions take ALREADY-PARSED dicts (the YAML/JSON loading lives in
engines/loaders.py) and return plain dicts — fully deterministic and testable
without any YAML dependency.
"""

import os
import sys

# allow `python engines/explore/adapter.py` and library import alike
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.helix_ledger import reindex_ledger, SCHEMA_VERSION  # noqa: E402


def evx_winner_to_candidate(winner: dict, source_chain: dict = None) -> dict:
    """EVX stage6 winner -> HELIX candidate (for is_consumed before promotion)."""
    return {
        "idea_id": winner.get("id"),
        "title": winner.get("title", ""),
        "aliases": winner.get("aliases", []),
        "semantic_family": winner.get("semantic_family"),
        "origin": "explore",
        "source_insight_id": winner.get("source_insight_id"),
        "source_chain": source_chain or {},
    }


def evx_manifest_to_source_chain(manifest: dict) -> dict:
    """EVX manifest -> normalized source_chain {evx, cix, idx, tcx, sdx_catalog}."""
    inputs = (manifest or {}).get("inputs", {}) or {}
    rnd = (manifest or {}).get("round", {}) or {}

    def _id(v):
        return v.get("id") if isinstance(v, dict) else v

    chain = {
        "evx": _id(rnd) or rnd.get("id"),
        "cix": _id(inputs.get("cix_round")),
        "idx": _id(inputs.get("idx_round")),
        "tcx": _id(inputs.get("tcx_round")),
        "sdx_catalog": inputs.get("sdx_catalog"),
    }
    return {k: v for k, v in chain.items() if v}


def idea_pool_to_pool(idea_pool: dict) -> list:
    """CIX idea_pool.yaml -> diversity pool items {title, domains, system_description}."""
    ideas = (idea_pool or {}).get("ideas")
    innovation = (idea_pool or {}).get("innovation")
    if ideas is None and isinstance(innovation, dict):
        ideas = innovation.get("ideas")

    pool = []
    for idea in ideas or []:
        pool.append({
            "id": idea.get("id"),
            "title": idea.get("title", ""),
            "domains": idea.get("domains", []) or [],
            "system_description": idea.get("system_description", ""),
            "source_insight_id": idea.get("source_insight_id"),
        })
    return pool


def consumed_yaml_to_ledger(consumed_doc: dict) -> dict:
    """IdeaFirst consumed_ideas.yaml (top key `consumed_ideas`) -> unified HELIX ledger."""
    entries = []
    for e in (consumed_doc or {}).get("consumed_ideas", []) or []:
        entries.append({
            "idea_id": e.get("idea_id"),
            "title": e.get("title", ""),
            "normalized_title": e.get("normalized_title"),
            "aliases": e.get("aliases", []) or [],
            "semantic_family": e.get("semantic_family"),
            "origin": "explore",
            "source_chain": e.get("source_chain", {}) or {},
            "implementations": e.get("implementations", []) or [],
            "reuse_policy": e.get("reuse_policy"),
            "consumed_at_utc": e.get("consumed_at_utc"),
        })
    ledger = {"schema_version": SCHEMA_VERSION, "consumed": entries,
              "blocked_names": [], "source_fingerprints": {}, "generated_fingerprints": {}}
    return reindex_ledger(ledger)


def evx_winner_to_consumed_entry(winner: dict, source_chain: dict, implementations: list,
                                 semantic_family: str = None, aliases: list = None) -> dict:
    """Build a HELIX consumed entry for an implemented explore winner (-> append_consumed)."""
    return {
        "idea_id": winner.get("id"),
        "title": winner.get("title", ""),
        "aliases": aliases or winner.get("aliases", []) or [],
        "semantic_family": semantic_family or winner.get("semantic_family"),
        "origin": "explore",
        "source_chain": source_chain or {},
        "implementations": implementations or [],
        "reuse_policy": "exclude_same_or_derivative",
    }
