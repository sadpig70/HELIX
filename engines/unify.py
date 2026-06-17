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
from core.helix_ledger import reindex_ledger, empty_ledger, SCHEMA_VERSION  # noqa: E402


def merge_ledgers(*ledgers) -> dict:
    """Union consumed entries across ledgers (dedup by idea_id), then rebuild indexes.

    Deterministic: entries keep first-seen order; a later duplicate idea_id is dropped.
    """
    merged = empty_ledger()
    seen = set()
    for led in ledgers:
        if not led:
            continue
        for entry in led.get("consumed", []):
            key = entry.get("idea_id") or entry.get("title")
            if key in seen:
                continue
            seen.add(key)
            merged["consumed"].append(dict(entry))
    reindex_ledger(merged)
    merged["schema_version"] = SCHEMA_VERSION
    return merged


def build_unified_ledger(explore_ledger: dict = None, exploit_ledger: dict = None) -> dict:
    """Merge the two engines' projected ledgers into the shared HELIX ledger."""
    return merge_ledgers(explore_ledger, exploit_ledger)
