#!/usr/bin/env python3
"""Collect live layered-corpus forward-prediction candidates into a manifest.

The collector is intentionally conservative: it does not invent probe artifacts from
human notes. Entries without normalized behavioral artifacts are marked
`missing_artifact=true` so `forward_predict.py --manifest` can report them without
forcing a probe.
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LAYERED_CORPUS = os.path.join(ROOT, "seed", "condense", "layered-corpus.json")
DEFAULT_OUT = os.path.join(ROOT, "_workspace", "condense", "U9-live-candidate-manifest.json")
DEFAULT_ARTIFACT_CATALOG = os.path.join(ROOT, "seed", "condense", "forward-candidate-artifacts.json")

MARKER_RE = re.compile(r"^(?P<name>.*?)(?:\((?P<marker>[^()]*)\))?$")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_artifact_catalog(path):
    if not path or not os.path.exists(path):
        return {}
    data = _load_json(path)
    artifacts = data.get("artifacts", {})
    return artifacts if isinstance(artifacts, dict) else {}


def _display_path(path):
    if os.path.isabs(path):
        try:
            return os.path.relpath(path, ROOT).replace(os.sep, "/")
        except ValueError:
            return path.replace(os.sep, "/")
    return path.replace(os.sep, "/")


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _parse_marked_name(value):
    match = MARKER_RE.match(str(value).strip())
    if not match:
        return str(value).strip(), "", ""
    name = match.group("name").strip()
    marker = (match.group("marker") or "").strip()
    if marker.startswith("deferred:"):
        return name, "deferred", marker.split(":", 1)[1]
    if marker == "design-only":
        return name, "future", "design-only"
    if marker.startswith("done"):
        return name, "done", marker
    return name, marker, marker


def _implemented_names(layered_corpus):
    names = set()
    for platform in layered_corpus.get("layer1_platforms", []):
        for name in platform.get("consolidated", []):
            parsed, _, _ = _parse_marked_name(name)
            names.add(_norm(parsed))
    for cluster in layered_corpus.get("candidate_clusters", []):
        for name in cluster.get("members_implemented", []):
            names.add(_norm(name))
    return names


def _entry_id(status, name):
    return f"layered-{status}-{_norm(name) or 'candidate'}"


def _base_candidate_entries(layered_corpus, implemented):
    feedback = layered_corpus.get("base_pairing_feedback", {})
    candidates = feedback.get("build_on_platform_candidates", {})
    for platform, values in sorted(candidates.items()):
        for value in values:
            name, status, reason = _parse_marked_name(value)
            if status not in ("deferred", "future"):
                continue
            resolved = _norm(name) in implemented
            yield {
                "id": _entry_id(status, name),
                "name": name,
                "status": status,
                "reason": reason,
                "source": f"base_pairing_feedback.build_on_platform_candidates.{platform}",
                "platform_hint": platform,
                "resolved": resolved,
                "missing_artifact": True,
                "missing_artifact_reason": "layered-corpus marker has no normalized probe artifact",
                "substantiated_count": 1,
            }


def _cluster_candidate_entries(layered_corpus, implemented):
    for cluster in layered_corpus.get("candidate_clusters", []):
        cluster_name = cluster.get("cluster", "")
        substantiated_count = int(cluster.get("substantiated_count", 1) or 0)
        shared_machines = cluster.get("shared_machines", [])
        for route in cluster.get("routing", []):
            if not route.get("deferred"):
                continue
            name = route.get("member", "")
            resolved = bool(route.get("done")) or _norm(name) in implemented
            yield {
                "id": _entry_id("deferred", name),
                "name": name,
                "status": "deferred",
                "reason": route.get("machine", "") or route.get("note", ""),
                "note": route.get("note", ""),
                "source": f"candidate_clusters.{cluster_name}.routing",
                "cluster": cluster_name,
                "substantiated_count": substantiated_count,
                "shared_machines": shared_machines,
                "resolved": resolved,
                "missing_artifact": True,
                "missing_artifact_reason": "cluster routing note has no normalized probe artifact",
            }


def _merge_entries(entries):
    merged = {}
    for entry in entries:
        key = _norm(entry.get("name") or entry.get("id"))
        if key not in merged:
            merged[key] = dict(entry)
            merged[key]["sources"] = [entry.get("source", "")]
            continue
        current = merged[key]
        current["sources"].append(entry.get("source", ""))
        current["source"] = current["sources"][0]
        current["resolved"] = bool(current.get("resolved") or entry.get("resolved"))
        if current.get("substantiated_count", 0) < entry.get("substantiated_count", 0):
            current["substantiated_count"] = entry["substantiated_count"]
        for key_name in ("cluster", "shared_machines", "note"):
            if entry.get(key_name) and not current.get(key_name):
                current[key_name] = entry[key_name]
    return [merged[key] for key in sorted(merged)]


def _apply_artifact_catalog(entries, artifact_catalog):
    out = []
    for entry in entries:
        updated = dict(entry)
        spec = artifact_catalog.get(entry.get("name", ""))
        if isinstance(spec, dict) and spec.get("candidate"):
            updated.pop("missing_artifact", None)
            updated.pop("missing_artifact_reason", None)
            updated["candidate"] = spec["candidate"]
            updated["artifact_source"] = spec.get("source", "")
            updated["artifact_source_note"] = spec.get("source_note", "")
        out.append(updated)
    return out


def collect_manifest(layered_corpus, layered_corpus_path=DEFAULT_LAYERED_CORPUS,
                     include_resolved=False, artifact_catalog=None):
    implemented = _implemented_names(layered_corpus)
    entries = _merge_entries(
        list(_base_candidate_entries(layered_corpus, implemented))
        + list(_cluster_candidate_entries(layered_corpus, implemented))
    )
    if not include_resolved:
        entries = [entry for entry in entries if not entry.get("resolved")]
    entries = _apply_artifact_catalog(entries, artifact_catalog or {})
    status_counts = {}
    artifact_counts = {"available": 0, "missing": 0}
    for entry in entries:
        status = entry.get("status", "")
        status_counts[status] = status_counts.get(status, 0) + 1
        if entry.get("missing_artifact"):
            artifact_counts["missing"] += 1
        else:
            artifact_counts["available"] += 1
    return {
        "schema": "helix-forward-predict-manifest/1.0",
        "version": 1,
        "purpose": "Live deferred/future candidates collected from layered-corpus markers",
        "layered_corpus": _display_path(layered_corpus_path),
        "collector": "scripts/condense/collect_forward_candidates.py",
        "count": len(entries),
        "status_counts": dict(sorted(status_counts.items())),
        "artifact_counts": artifact_counts,
        "include_resolved": include_resolved,
        "candidates": entries,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--layered-corpus", default=DEFAULT_LAYERED_CORPUS)
    parser.add_argument("--artifact-catalog", default=DEFAULT_ARTIFACT_CATALOG)
    parser.add_argument("--include-resolved", action="store_true")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    manifest = collect_manifest(
        _load_json(args.layered_corpus),
        layered_corpus_path=args.layered_corpus,
        include_resolved=args.include_resolved,
        artifact_catalog=_load_artifact_catalog(args.artifact_catalog),
    )
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, indent=2)
            f.write("\n")
    if args.json:
        print(json.dumps(manifest, sort_keys=True, indent=2))
    else:
        print("=== HELIX forward candidate manifest ===")
        print(f"candidates: {manifest['count']} | status_counts={manifest['status_counts']}")
        print(f"artifacts: {manifest['artifact_counts']}")
        print(f"out: {_display_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
