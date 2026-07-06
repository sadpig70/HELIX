#!/usr/bin/env python3
"""HELIX I/O glue — read engine artifacts (JSON always, YAML if PyYAML present).

The transform logic lives in the adapters (pure, stdlib, tested). This module is
the thin boundary that turns files into dicts. JSON (recreate registry, HELIX
fixtures) needs only stdlib; YAML (IdeaFirst runtime) uses PyYAML when available
and raises a clear, actionable error otherwise — tests never depend on YAML.
"""

import glob
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


_EXTS = (".json", ".yaml", ".yml")


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def _with_ext(stem):
    return [stem + e for e in _EXTS]


def resolve_latest(root: str, subdir: str, stem: str) -> str:
    """Deterministically locate an artifact under `root`, with no reliance on a
    `latest` pointer being present:

      0) {root}/{subdir}/{stem}.{ext}                  (flat store, e.g. .idea-ledger)
      1) {root}/{subdir}/latest/{stem}.{ext}           (latest copy/symlink)
      2) {root}/{subdir}/rounds/*/{stem}.{ext}  or  {root}/{subdir}/*/{stem}.{ext}
         -> pick the lexicographically max round dir (IDs like EVX-20260610-001
            sort by date+seq, so max == latest). Fully deterministic.

    Returns a path or None.
    """
    for stems in (_with_ext(stem),):
        for s in stems:
            p = os.path.join(root, subdir, s)
            if os.path.exists(p):
                return p
            p = os.path.join(root, subdir, "latest", s)
            if os.path.exists(p):
                return p
    cands = []
    for pat in (os.path.join(root, subdir, "rounds", "*"),
                os.path.join(root, subdir, "*")):
        for d in glob.glob(pat):
            if not os.path.isdir(d):
                continue
            for s in _with_ext(stem):
                p = os.path.join(d, s)
                if os.path.exists(p):
                    cands.append((os.path.basename(d), p))
    if cands:
        cands.sort(key=lambda t: t[0], reverse=True)  # latest round id first
        return cands[0][1]
    return None


def _load_any(root: str, stem: str, subdir: str):
    """Fixture file at root first (examples), else live resolver under subdir."""
    fixture = _first_existing(*[os.path.join(root, s) for s in _with_ext(stem)])
    return read_doc(fixture or resolve_latest(root, subdir, stem))


def _latest_run_path(root: str, subdir: str) -> str:
    """Resolve a recreate-style latest run directory, if latest.json exists."""
    latest = os.path.join(root, subdir, "latest.json")
    doc = read_doc(latest)
    if not isinstance(doc, dict):
        return None
    run_path = doc.get("latest_run_path")
    if not run_path:
        return None
    if not os.path.isabs(run_path):
        run_path = os.path.join(root, run_path)
    return run_path if os.path.isdir(run_path) else None


def _load_latest_run_any(root: str, subdir: str, stem: str):
    """Load {stem} from the latest run directory before falling back."""
    run_path = _latest_run_path(root, subdir)
    if run_path:
        for s in _with_ext(stem):
            p = os.path.join(run_path, s)
            if os.path.exists(p):
                return read_doc(p)
    return _load_any(root, stem, subdir)


def load_explore_state(root: str) -> dict:
    """Resolve IdeaFirst artifacts under `root` (json fixtures or live yaml rounds)."""
    return {
        "stage6_final": _load_any(root, "stage6_final", ".evx"),
        "manifest":     _load_any(root, "manifest", ".evx"),
        "idea_pool":    _load_any(root, "idea_pool", ".cix"),
        "consumed":     _load_any(root, "consumed_ideas", ".idea-ledger"),
    }


def load_exploit_state(root: str) -> dict:
    """Resolve recreate artifacts under `root`."""
    return {
        "registry":   _load_any(root, "registry", ".recreate"),
        "candidates": _load_latest_run_any(root, ".recreate", "candidates"),
        "run_status": _load_latest_run_any(root, ".recreate", "status"),
    }
