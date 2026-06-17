#!/usr/bin/env python3
"""HELIX unified consumed/registry ledger — the reuse-prevention gate (stdlib only).

This is the concrete *merge point* of the two systems. Both engines independently
built a "don't repeat what we already produced" store:

  * IdeaFirst  -> `.idea-ledger/consumed_ideas.yaml`
        (exclude_match_on: idea_id, normalized_title, aliases, semantic_family)
  * recreate   -> `.recreate/registry.json`
        (blocked_names, source_fingerprints, generated_fingerprints)

HELIX-Core defines ONE ledger that both engines read before selection and write
after a winner becomes a concrete project. JSON is canonical (stdlib, CI-friendly);
adapters in `engines/` map the per-engine YAML/JSON views onto this shape.

Determinism: pure functions; `now` (timestamp) is injected, never read from a clock.
The ledger is a reuse gate, NOT a quality certificate.
"""

import json

from .helix_fingerprint import (
    normalize_name,
    source_fingerprint,
    generated_fingerprint,
)

SCHEMA_VERSION = "0.1"

# exclude_match_on (unified): IdeaFirst keys + ProjectGenome fingerprints.
MATCH_KEYS = (
    "idea_id",
    "normalized_title",
    "aliases",
    "semantic_family",
    "source_fingerprint",
    "generated_fingerprint",
)


def empty_ledger() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "consumed": [],
        "blocked_names": [],          # normalized titles/names
        "source_fingerprints": {},    # fp -> idea_id
        "generated_fingerprints": {}, # fp -> idea_id
    }


def candidate_keys(candidate: dict) -> dict:
    """Derive the deterministic match keys for a candidate (engine-neutral)."""
    aliases = candidate.get("aliases", []) or []
    return {
        "idea_id": candidate.get("idea_id"),
        "normalized_title": normalize_name(candidate.get("title", "")),
        "aliases": sorted({normalize_name(a) for a in aliases if a}),
        "semantic_family": candidate.get("semantic_family"),
        "source_fingerprint": source_fingerprint(candidate.get("sources", [])),
        "generated_fingerprint": generated_fingerprint(candidate.get("parents", [])),
    }


def _entry_match(keys: dict, entry: dict, blocked: set) -> str:
    """Return the name of the first matching key, or '' if no match (deterministic)."""
    if keys["idea_id"] and keys["idea_id"] == entry.get("idea_id"):
        return "idea_id"
    nt = keys["normalized_title"]
    entry_aliases = set(entry.get("_norm_aliases", []))
    entry_title = entry.get("_norm_title", normalize_name(entry.get("title", "")))
    if nt and (nt == entry_title or nt in entry_aliases or nt in blocked):
        return "normalized_title"
    # candidate alias hitting the entry's title/aliases
    for a in keys["aliases"]:
        if a and (a == entry_title or a in entry_aliases or a in blocked):
            return "aliases"
    if keys["semantic_family"] and keys["semantic_family"] == entry.get("semantic_family"):
        return "semantic_family"
    if keys["source_fingerprint"] and keys["source_fingerprint"] == entry.get("source_fingerprint"):
        return "source_fingerprint"
    if keys["generated_fingerprint"] and keys["generated_fingerprint"] == entry.get("generated_fingerprint"):
        return "generated_fingerprint"
    return ""


def is_consumed(candidate: dict, ledger: dict) -> dict:
    """Deterministically decide whether a candidate collides with the ledger.

    Returns {consumed: bool, match: {idea_id, on} | None, keys: {...}}.
    `on` names which key triggered the match (audit trail).
    """
    keys = candidate_keys(candidate)
    blocked = {normalize_name(n) for n in ledger.get("blocked_names", [])}
    for entry in ledger.get("consumed", []):
        on = _entry_match(keys, entry, blocked)
        if on:
            return {"consumed": True,
                    "match": {"idea_id": entry.get("idea_id"), "on": on},
                    "keys": keys}
    return {"consumed": False, "match": None, "keys": keys}


def append_consumed(ledger: dict, entry: dict, now: str) -> dict:
    """Append a consumed entry. `now` is injected (no clock read).

    Records only when the winner became concrete (has implementations) — this
    mirrors both engines' `record_only_when: winner becomes a project/MVP/repo`.
    Mutates and returns the ledger; raises ValueError on policy violation.
    """
    if not entry.get("implementations"):
        raise ValueError("append_consumed: refused — no implementations "
                         "(record only when a winner becomes a concrete project)")
    title = entry.get("title", "")
    norm_title = normalize_name(title)
    norm_aliases = sorted({normalize_name(a) for a in entry.get("aliases", []) if a})
    record = dict(entry)
    record["normalized_title"] = entry.get("normalized_title") or norm_title
    record["_norm_title"] = norm_title
    record["_norm_aliases"] = norm_aliases
    record["consumed_at_utc"] = now
    record.setdefault("origin", entry.get("origin", "unknown"))
    record.setdefault("source_fingerprint",
                      source_fingerprint(entry.get("sources", [])))
    record.setdefault("generated_fingerprint",
                      generated_fingerprint(entry.get("parents", [])))

    ledger.setdefault("consumed", []).append(record)

    blocked = ledger.setdefault("blocked_names", [])
    if norm_title and norm_title not in blocked:
        blocked.append(norm_title)
    for a in norm_aliases:
        if a not in blocked:
            blocked.append(a)

    if record["source_fingerprint"]:
        ledger.setdefault("source_fingerprints", {})[record["source_fingerprint"]] = record.get("idea_id")
    if record["generated_fingerprint"]:
        ledger.setdefault("generated_fingerprints", {})[record["generated_fingerprint"]] = record.get("idea_id")
    return ledger


def reindex_ledger(ledger: dict) -> dict:
    """Rebuild blocked_names / source_fingerprints / generated_fingerprints and the
    internal _norm caches from `consumed[]`. Single source of truth for indexing,
    used when building a ledger from a native engine store or merging ledgers.
    """
    blocked = []
    seen = set()
    sfp = {}
    gfp = {}
    for e in ledger.get("consumed", []):
        nt = normalize_name(e.get("normalized_title") or e.get("title", ""))
        e["_norm_title"] = nt
        e["_norm_aliases"] = sorted({normalize_name(a) for a in e.get("aliases", []) if a})
        for b in [nt] + e["_norm_aliases"]:
            if b and b not in seen:
                seen.add(b)
                blocked.append(b)
        sf = e.get("source_fingerprint") or source_fingerprint(e.get("sources", []))
        if sf:
            e["source_fingerprint"] = sf
            sfp[sf] = e.get("idea_id")
        gf = e.get("generated_fingerprint") or generated_fingerprint(e.get("parents", []))
        if gf:
            e["generated_fingerprint"] = gf
            gfp[gf] = e.get("idea_id")
    ledger["blocked_names"] = blocked
    ledger["source_fingerprints"] = sfp
    ledger["generated_fingerprints"] = gfp
    ledger.setdefault("schema_version", SCHEMA_VERSION)
    ledger.setdefault("consumed", [])
    return ledger


def load_ledger(path) -> dict:
    """Load the JSON ledger; return an empty ledger if absent."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return empty_ledger()
    # backfill normalized caches for older files
    for entry in data.get("consumed", []):
        entry.setdefault("_norm_title", normalize_name(entry.get("title", "")))
        entry.setdefault("_norm_aliases",
                         sorted({normalize_name(a) for a in entry.get("aliases", []) if a}))
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def save_ledger(path, ledger: dict) -> None:
    """Persist the ledger as pretty JSON (drops internal _norm caches)."""
    out = json.loads(json.dumps(ledger))  # deep copy
    for entry in out.get("consumed", []):
        entry.pop("_norm_title", None)
        entry.pop("_norm_aliases", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
