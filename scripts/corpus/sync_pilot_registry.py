#!/usr/bin/env python3
"""Synchronize editable pilot status labels from authoritative ledger receipts."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_corpus_supply import materialize_state  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=os.path.join(
        ROOT, "_workspace", "corpus-pilot", "registry.json"))
    parser.add_argument("--corpus-root", default=os.path.join(ROOT, "seed", "corpus"))
    args = parser.parse_args(argv)
    with open(args.registry, "r", encoding="utf-8") as handle:
        registry = json.load(handle)
    state = materialize_state(ROOT, args.corpus_root)
    if state["ledger_problems"]:
        print("; ".join(state["ledger_problems"]), file=sys.stderr)
        return 4
    for slot in registry["slots"]:
        tiers = state["state"].get(slot["corpus_id"], {})
        if tiers.get("evidence", {}).get("decision") == "ADMITTED":
            slot["status"] = "evidence_admitted"
        elif slot.get("status") != "evidence_ready" and (
                tiers.get("generative", {}).get("decision") == "ADMITTED"):
            slot["status"] = "generative_admitted"
    with open(args.registry, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(registry, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"synced": len(registry["slots"])}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
