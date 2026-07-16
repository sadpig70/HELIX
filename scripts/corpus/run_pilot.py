#!/usr/bin/env python3
"""Serially intake and Generative-admit an approved corpus pilot cohort."""

import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import admit_item, intake_manifest  # noqa: E402
from scripts.corpus.pilot_registry import validate_registry  # noqa: E402


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path, value):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _parse_time(value):
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("--start must include a timezone")
    return parsed


def run(registry_path, manifest_dir, corpus_root, start):
    registry = _read(registry_path)
    problems = validate_registry(ROOT, registry)
    if problems:
        raise ValueError("registry: " + "; ".join(problems))
    results = []
    for index, slot in enumerate(registry["slots"]):
        corpus_id = slot["corpus_id"]
        manifest_path = os.path.join(manifest_dir, corpus_id + "-r1.json")
        manifest = _read(manifest_path)
        intake = intake_manifest(ROOT, corpus_root, manifest)
        evidence_root = slot["candidate"]["evidence_root"]
        if not os.path.isabs(evidence_root):
            evidence_root = os.path.join(ROOT, evidence_root)
        recorded_at = (start + datetime.timedelta(seconds=index)).isoformat()
        admission = admit_item(ROOT, corpus_root, corpus_id, "generative",
                               recorded_at, evidence_root=evidence_root)
        decision = admission["decision"]["decision"]
        slot["status"] = "generative_admitted" if decision == "ADMITTED" else "quarantined"
        results.append({
            "corpus_id": corpus_id,
            "intake": intake["status"],
            "decision": decision,
            "reasons": admission["decision"]["reasons"],
            "event_id": admission["event"]["event_id"],
            "added": admission["added"],
        })
    _write(registry_path, registry)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=os.path.join(
        ROOT, "_workspace", "corpus-pilot", "registry.json"))
    parser.add_argument("--manifest-dir", default=os.path.join(
        ROOT, "_workspace", "corpus-pilot", "manifests"))
    parser.add_argument("--corpus-root", default=os.path.join(ROOT, "seed", "corpus"))
    parser.add_argument("--start", required=True)
    args = parser.parse_args(argv)
    try:
        results = run(args.registry, args.manifest_dir, args.corpus_root,
                      _parse_time(args.start))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 4
    print(json.dumps({"processed": len(results), "items": results},
                     ensure_ascii=False, indent=2))
    return 0 if all(row["decision"] == "ADMITTED" for row in results) else 4


if __name__ == "__main__":
    sys.exit(main())
