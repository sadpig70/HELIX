#!/usr/bin/env python3
"""HELIX driver — wire both engines to the backbone and report the next loop turn.

Reads the two engines' latest artifacts (via adapters), builds the ONE unified
ledger, measures diversity over the combined idea pool, and computes the next
explore<->exploit action. With no roots given, runs over the shipped fixtures
under examples/ so it works out of the box (and in CI, stdlib only).

CLI:
    python helix.py status
    python helix.py status --explore-root D:/IdeaFirst --exploit-root D:/recreate_prj/ProjectGenome
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from core.helix_diversity import measure_diversity            # noqa: E402
from core.helix_ledger import is_consumed                     # noqa: E402
from core.helix_loop import next_action                       # noqa: E402
from core.helix_provenance import trace_winner, winner_to_corpus_entry  # noqa: E402
from engines.loaders import load_explore_state, load_exploit_state      # noqa: E402
from engines.unify import build_unified_ledger                # noqa: E402
from engines.explore import adapter as explore_adp            # noqa: E402
from engines.exploit import adapter as exploit_adp            # noqa: E402

FIXTURE_EXPLORE = os.path.join(ROOT, "examples", "explore_state")
FIXTURE_EXPLOIT = os.path.join(ROOT, "examples", "exploit_state")


def build_report(explore_root=None, exploit_root=None) -> dict:
    """Run one HELIX turn over the two engines' state. Deterministic given inputs."""
    explore_root = explore_root or FIXTURE_EXPLORE
    exploit_root = exploit_root or FIXTURE_EXPLOIT

    ex = load_explore_state(explore_root)
    xp = load_exploit_state(exploit_root)

    # 1) project each engine's native store onto the unified ledger, then merge
    explore_ledger = explore_adp.consumed_yaml_to_ledger(ex["consumed"]) if ex["consumed"] else None
    exploit_ledger = exploit_adp.registry_to_ledger(xp["registry"]) if xp["registry"] else None
    ledger = build_unified_ledger(explore_ledger, exploit_ledger)

    # 2) combined diversity pool (explore ideas + exploit candidates)
    pool = []
    if ex["idea_pool"]:
        pool += explore_adp.idea_pool_to_pool(ex["idea_pool"])
    if xp["candidates"]:
        pool += exploit_adp.candidates_to_pool(xp["candidates"])
    diversity = measure_diversity(pool, sim=None)  # sim injected by engines in production

    # 3) latest explore winner -> candidate, check against the shared ledger
    winner_report = None
    if ex["stage6_final"]:
        chain = explore_adp.evx_manifest_to_source_chain(ex["manifest"] or {})
        win = (ex["stage6_final"].get("consensus_winner")
               or ex["stage6_final"].get("innovation_winner"))
        if win:
            cand = explore_adp.evx_winner_to_candidate(win, chain)
            consumed = is_consumed(cand, ledger)
            winner_report = {
                "winner_id": cand["idea_id"],
                "title": cand["title"],
                "already_consumed": consumed["consumed"],
                "match": consumed["match"],
                "lineage": trace_winner(cand),
            }

    # 4) corpus feedback edge (base-pairing): an implemented explore winner -> corpus source
    corpus_feedback = []
    for e in ledger["consumed"]:
        if e.get("origin") == "explore" and e.get("implementations"):
            corpus_feedback.append(winner_to_corpus_entry(e))

    # 5) next loop action
    #    corpus = exploit-origin entries + explore winners fed back as corpus sources.
    corpus_size = sum(1 for e in ledger["consumed"] if e.get("origin") == "exploit") + len(corpus_feedback)
    last_engine = "explore" if ex["stage6_final"] else ("exploit" if xp["registry"] else None)
    # A freshly selected EVX winner is NOT yet built; recording into the ledger
    # happens on a later turn after pgf implements it. So the read-only status view
    # never marks a winner pending-implemented (RECORD_CONSUMED is driven by a build event).
    state = {
        "last_engine": last_engine,
        "diversity": diversity,
        "corpus_size": corpus_size,
        "pending_implemented_winner": False,
        "winner_in_ledger": bool(winner_report and winner_report["already_consumed"]),
    }
    action = next_action(state)

    return {
        "ledger_size": len(ledger["consumed"]),
        "ledger_origins": {
            "explore": sum(1 for e in ledger["consumed"] if e.get("origin") == "explore"),
            "exploit": sum(1 for e in ledger["consumed"] if e.get("origin") == "exploit"),
        },
        "pool_size": len(pool),
        "diversity": diversity,
        "winner": winner_report,
        "corpus_feedback": corpus_feedback,
        "next_action": action,
    }


def _print_report(r: dict) -> None:
    print("=== HELIX turn ===")
    print(f"  unified ledger: {r['ledger_size']} entries "
          f"(explore={r['ledger_origins']['explore']}, exploit={r['ledger_origins']['exploit']})")
    print(f"  diversity pool: {r['pool_size']} items | "
          f"triggered={r['diversity']['triggered']} (partial={r['diversity']['partial']}, "
          f"breaches={r['diversity']['breaches']})")
    if r["winner"]:
        w = r["winner"]
        print(f"  latest explore winner: {w['winner_id']} \"{w['title']}\" "
              f"-> already_consumed={w['already_consumed']}")
        print(f"      lineage: {' -> '.join(s['id'] for s in w['lineage'])}")
    if r["corpus_feedback"]:
        names = ", ".join(c["project"] for c in r["corpus_feedback"])
        print(f"  base-pairing (explore->corpus): {names}")
    a = r["next_action"]
    print(f"  NEXT ACTION: {a['action']}  ({a['why']})")


def _main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd != "status":
        sys.stderr.write("usage: python helix.py status "
                         "[--explore-root R] [--exploit-root R] [--json]\n")
        return 2
    explore_root = exploit_root = None
    as_json = "--json" in argv
    for i, a in enumerate(argv):
        if a == "--explore-root" and i + 1 < len(argv):
            explore_root = argv[i + 1]
        if a == "--exploit-root" and i + 1 < len(argv):
            exploit_root = argv[i + 1]
    report = build_report(explore_root, exploit_root)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
