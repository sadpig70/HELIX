#!/usr/bin/env python3
"""HELIX I/O glue — read engine artifacts (JSON always, YAML if PyYAML present).

The transform logic lives in the adapters (pure, stdlib, tested). This module is
the thin boundary that turns files into dicts. JSON (recreate registry, HELIX
fixtures) needs only stdlib; YAML (IdeaFirst runtime) uses PyYAML when available
and raises a clear, actionable error otherwise — tests never depend on YAML.
"""

import json
import os


def read_doc(path: str):
    """Parse a .json/.yaml/.yml file into a dict. Returns None if the file is absent."""
    if not path or not os.path.exists(path):
        return None
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        if ext == ".json":
            return json.load(f)
        if ext in (".yaml", ".yml"):
            try:
                import yaml  # optional; only needed for live IdeaFirst artifacts
            except ImportError as e:
                raise RuntimeError(
                    f"reading {path} needs PyYAML (live IdeaFirst artifacts are YAML). "
                    f"Install pyyaml, or pre-convert to JSON. Original: {e}")
            return yaml.safe_load(f)
    raise ValueError(f"unsupported extension for {path}")


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def load_explore_state(root: str) -> dict:
    """Resolve IdeaFirst artifacts under `root` (json fixtures or live yaml)."""
    def pick(*rel):
        cands = []
        for r in rel:
            cands += [os.path.join(root, r + ".json"),
                      os.path.join(root, r + ".yaml"),
                      os.path.join(root, r + ".yml")]
        return _first_existing(*cands)
    return {
        "stage6_final": read_doc(pick(".evx/latest/stage6_final", "stage6_final")),
        "manifest":     read_doc(pick(".evx/latest/manifest", "manifest")),
        "idea_pool":    read_doc(pick(".cix/latest/idea_pool", "idea_pool")),
        "consumed":     read_doc(pick(".idea-ledger/consumed_ideas", "consumed_ideas")),
    }


def load_exploit_state(root: str) -> dict:
    """Resolve recreate artifacts under `root`."""
    def pick(*rel):
        cands = []
        for r in rel:
            cands += [os.path.join(root, r + ".json")]
        return _first_existing(*cands)
    return {
        "registry":   read_doc(pick(".recreate/registry", "registry")),
        "candidates": read_doc(pick(".recreate/candidates", "candidates")),
    }
