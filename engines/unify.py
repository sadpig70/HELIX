#!/usr/bin/env python3
"""HELIX engine federation — merge per-engine ledgers into one shared ledger. stdlib only.

This is the concrete "single source of truth" join: the explore strand
(consumed_ideas) and the exploit strand (registry) are projected onto the unified
HELIX ledger (via the adapters), then merged here. Both engines then read/write
ONE ledger -> no desync between systems.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.helix_ledger import (  # noqa: E402
    reindex_ledger, empty_ledger, is_consumed, SCHEMA_VERSION,
)


def _merge_duplicate_entry(merged: dict, new_entry: dict, match_id) -> None:
    """Fold a cross-engine duplicate into the existing entry (deterministic).

    The first-seen entry keeps its identity; aliases, implementations and
    source_chain links from the duplicate are unioned in (audit-preserving).
    """
    for e in merged["consumed"]:
        if e.get("idea_id") == match_id:
            al = e.setdefault("aliases", [])
            for a in new_entry.get("aliases", []) or []:
                if a not in al:
                    al.append(a)
            # record the other engine's title as an alias so it stays blocked
            if new_entry.get("title") and new_entry["title"] not in al and new_entry["title"] != e.get("title"):
                al.append(new_entry["title"])
            impls = e.setdefault("implementations", [])
            have = {i.get("project_name") for i in impls}
            for i in new_entry.get("implementations", []) or []:
                if i.get("project_name") not in have:
                    impls.append(i)
            sc = e.setdefault("source_chain", {})
            for k, v in (new_entry.get("source_chain") or {}).items():
                sc.setdefault(k, v)
            e.setdefault("merged_from", []).append(new_entry.get("idea_id") or new_entry.get("title"))
            return


def merge_ledgers(*ledgers) -> dict:
    """Union consumed entries across ledgers using the FULL HELIX match contract.

    Dedup is not by idea_id alone — a new entry is matched against the merged
    ledger via `is_consumed` (idea_id / normalized_title / aliases / semantic_family
    / source_fingerprint / generated_fingerprint). A collision is folded into the
    existing entry rather than left as a second row, protecting the single-source
    ledger promise. Deterministic: first-seen order; reindex after each insert.
    """
    merged = empty_ledger()
    for led in ledgers:
        if not led:
            continue
        for entry in led.get("consumed", []):
            hit = is_consumed(entry, merged)
            if hit["consumed"]:
                _merge_duplicate_entry(merged, entry, hit["match"]["idea_id"])
                reindex_ledger(merged)
            else:
                merged["consumed"].append(dict(entry))
                reindex_ledger(merged)
    merged["schema_version"] = SCHEMA_VERSION
    return merged


def build_unified_ledger(explore_ledger: dict = None, exploit_ledger: dict = None) -> dict:
    """Merge the two engines' projected ledgers into the shared HELIX ledger."""
    return merge_ledgers(explore_ledger, exploit_ledger)
