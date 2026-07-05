#!/usr/bin/env python3
"""Condense state adapter (stdlib only, pure/deterministic).

Turns a layered-corpus registry into the `condense_candidate` /
`build_on_platform_candidate` state that core.helix_loop.next_action consumes. This is
what lets `helix.py status` propose CONDENSE (ripe cluster -> platform) and
BUILD_ON_PLATFORM (fitting project -> pack) from real corpus data.

Determinism: pure function of the layered-corpus dict; identical input -> identical
output. No clock/network/AI. File loading is the driver's (meta/IO) responsibility.
"""

DEFAULT_CONDENSE_POLICY = {
    "min_cluster_for_condense": 5,   # must match core.helix_loop
}


def _platformed_clusters(layered_corpus):
    return {p.get("cluster") for p in layered_corpus.get("layer1_platforms", [])}


def condense_candidate(layered_corpus, policy=None):
    """Ripest unplatformed candidate cluster (>= threshold substantiated projects).

    Deterministic tie-break: highest substantiated_count, then cluster name ascending.
    Returns {cluster, substantiated_count, platformized:False} or None.
    """
    P = {**DEFAULT_CONDENSE_POLICY, **(policy or {})}
    platformed = _platformed_clusters(layered_corpus)
    ripe = [c for c in layered_corpus.get("candidate_clusters", [])
            if c.get("cluster") not in platformed
            and int(c.get("substantiated_count", 0)) >= P["min_cluster_for_condense"]]
    if not ripe:
        return None
    best = sorted(ripe, key=lambda c: (-int(c["substantiated_count"]), str(c["cluster"])))[0]
    return {"cluster": best["cluster"],
            "substantiated_count": int(best["substantiated_count"]),
            "platformized": False}


def build_on_platform_candidate(layered_corpus):
    """First (deterministic) project fitting an existing platform's contract.

    Reads base_pairing_feedback.build_on_platform_candidates ({platform: [projects]});
    picks platform then project in sorted order. Returns {project, platform} or None.
    """
    bp = (layered_corpus.get("base_pairing_feedback", {})
          .get("build_on_platform_candidates", {}))
    for platform in sorted(bp):
        projects = bp.get(platform) or []
        if projects:
            return {"project": sorted(projects)[0], "platform": platform}
    return None


def condense_state(layered_corpus, policy=None):
    """Merge-ready state fragment for next_action: {condense_candidate?, build_on_platform_candidate?}."""
    out = {}
    cc = condense_candidate(layered_corpus, policy)
    if cc:
        out["condense_candidate"] = cc
    bp = build_on_platform_candidate(layered_corpus)
    if bp:
        out["build_on_platform_candidate"] = bp
    return out
