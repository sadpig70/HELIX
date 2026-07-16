"""Deterministic path-aware evidence quarantine."""

import copy
import hashlib
import json
from collections import deque


CASE_SCHEMA = "graph-quarantine-case/1.0"
RECEIPT_SCHEMA = "graph-quarantine-receipt/1.0"
PROPAGATION = {"block", "monitor", "ignore"}


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def baseline_digest(nodes, edges, contamination_sources):
    return digest({
        "nodes": sorted(copy.deepcopy(nodes), key=lambda row: row["id"]),
        "edges": sorted(copy.deepcopy(edges), key=lambda row: (row["from"], row["to"], row.get("relation", ""), row.get("propagation", "block"))),
        "contamination_sources": sorted(contamination_sources),
    })


def _validate(case):
    reasons = []
    if case.get("schema") != CASE_SCHEMA:
        reasons.append("INVALID_SCHEMA")
    nodes = case.get("nodes")
    edges = case.get("edges")
    sources = case.get("contamination_sources")
    if not isinstance(nodes, list) or not isinstance(edges, list) or not isinstance(sources, list):
        return reasons + ["INVALID_CASE_STRUCTURE"]
    node_ids = []
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"]:
            reasons.append("INVALID_NODE")
        else:
            node_ids.append(node["id"])
    if len(set(node_ids)) != len(node_ids):
        reasons.append("DUPLICATE_NODE")
    node_set = set(node_ids)
    for edge in edges:
        if not isinstance(edge, dict):
            reasons.append("INVALID_EDGE")
            continue
        if edge.get("from") not in node_set or edge.get("to") not in node_set:
            reasons.append("EDGE_ENDPOINT_MISSING")
        if edge.get("propagation", "block") not in PROPAGATION:
            reasons.append("INVALID_PROPAGATION")
    if any(source not in node_set for source in sources):
        reasons.append("SOURCE_MISSING")
    if not reasons and case.get("baseline_sha256") != baseline_digest(nodes, edges, sources):
        reasons.append("BASELINE_HASH_MISMATCH")
    return sorted(set(reasons))


def _adjacency(edges):
    out = {}
    for edge in edges:
        mode = edge.get("propagation", "block")
        if mode == "ignore":
            continue
        out.setdefault(edge["from"], []).append({
            "to": edge["to"],
            "relation": edge.get("relation", ""),
            "propagation": mode,
        })
    for rows in out.values():
        rows.sort(key=lambda row: (row["to"], row["relation"], row["propagation"]))
    return out


def _walk(sources, adjacency):
    queue = deque((source, [source], "block") for source in sorted(sources))
    best = {}
    while queue:
        node, path, strength = queue.popleft()
        for edge in adjacency.get(node, []):
            target = edge["to"]
            next_strength = "monitor" if strength == "monitor" or edge["propagation"] == "monitor" else "block"
            prior = best.get(target)
            next_path = path + [target]
            if prior and (prior["strength"], len(prior["path"]), prior["path"]) <= (next_strength, len(next_path), next_path):
                continue
            best[target] = {"node_id": target, "strength": next_strength, "path": next_path}
            queue.append((target, next_path, next_strength))
    return best


def quarantine(case):
    case = copy.deepcopy(case)
    reasons = _validate(case)
    nodes = case.get("nodes") if isinstance(case.get("nodes"), list) else []
    edges = case.get("edges") if isinstance(case.get("edges"), list) else []
    sources = case.get("contamination_sources") if isinstance(case.get("contamination_sources"), list) else []
    node_ids = sorted(node["id"] for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str))

    paths, quarantine_set, monitor_set = [], [], []
    if not reasons:
        reached = _walk(sources, _adjacency(edges))
        for row in sorted(reached.values(), key=lambda item: (item["node_id"], item["strength"], item["path"])):
            paths.append(row)
            if row["strength"] == "block":
                quarantine_set.append(row["node_id"])
            else:
                monitor_set.append(row["node_id"])
    contaminated = set(sources) | set(quarantine_set)
    clean = [node_id for node_id in node_ids if node_id not in contaminated and node_id not in set(monitor_set)]
    decision = "INVALID" if reasons else ("QUARANTINED" if quarantine_set or sources else "CLEAR")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "case_id": str(case.get("case_id", "")),
        "case_sha256": digest(case),
        "decision": decision,
        "reasons": reasons,
        "sources": sorted(source for source in sources if source in node_ids),
        "quarantine_set": sorted(set(quarantine_set)),
        "monitor_set": sorted(set(monitor_set) - set(quarantine_set)),
        "clean_branches": clean,
        "paths": paths,
        "blast_radius": len(set(quarantine_set)) + len(set(sources)),
        "gene_provenance": {"path_analysis": "HC-PILOT-EXT-004", "staged_quarantine": "HC-PILOT-HELIX-004"},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(case, receipt):
    return quarantine(case) == receipt

