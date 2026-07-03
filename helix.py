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

import importlib                                              # noqa: E402
from core.helix_diversity import measure_diversity            # noqa: E402
from core.helix_io import atomic_write_json, read_json        # noqa: E402
from core.helix_ledger import (                               # noqa: E402
    is_consumed, append_consumed, load_ledger, save_ledger,
)
from core.helix_loop import next_action                       # noqa: E402
from core.helix_provenance import trace_winner, winner_to_corpus_entry  # noqa: E402
from core.helix_validate import validate_corpus_entry         # noqa: E402
from engines.loaders import load_explore_state, load_exploit_state      # noqa: E402
from engines.unify import build_unified_ledger                # noqa: E402
from engines.explore import adapter as explore_adp            # noqa: E402
from engines.exploit import adapter as exploit_adp            # noqa: E402

FIXTURE_EXPLORE = os.path.join(ROOT, "examples", "explore_state")
FIXTURE_EXPLOIT = os.path.join(ROOT, "examples", "exploit_state")


def resolve_sim(spec):
    """Resolve a --sim spec to a callable. 'lexical'/None -> None (lexical default);
    'module.path:function' -> imported callable. Import happens here (outside core),
    so the determinism boundary holds: core only ever receives a callable."""
    if not spec or spec == "lexical":
        return None
    if ":" not in spec:
        raise ValueError("--sim must be 'lexical' or 'module.path:function'")
    mod, fn = spec.split(":", 1)
    return getattr(importlib.import_module(mod), fn)


def append_corpus_entry(corpus_path: str, entry: dict) -> bool:
    """Append a corpus entry to a JSON-list file, idempotent by project name.

    Returns True if newly added, False if the project was already present.
    The entry is validated against the corpus contract before writing (F5: refuse
    invalid sources at the write boundary, not just in tests), and the file is
    written atomically (F2) so a crash mid-write cannot corrupt the corpus.
    """
    problems = validate_corpus_entry(entry)
    if problems:
        raise ValueError(f"append_corpus_entry: rejected invalid corpus entry: {problems}")
    corpus = read_json(corpus_path, default=[])
    if any(c.get("project") == entry.get("project") for c in corpus):
        return False
    corpus.append(entry)
    atomic_write_json(corpus_path, corpus)
    return True


def close_loop(explore_winner: dict, source_chain: dict, implementation: dict,
               ledger_path: str, corpus_path: str, now: str,
               packet_path: str = None) -> dict:
    """Actuator: record an implemented explore winner and feed it to the corpus.

    Idempotent — re-running on an already-recorded winner is a no-op. `now` is
    injected (the CLI stamps it). This is what turns next_action's RECORD_CONSUMED
    intent into an actual ledger/corpus mutation (closes the loop).

    If ``packet_path`` is supplied, the handback packet is verified with
    ActionHandbackVerifier *before* writing. A ``breach`` verdict aborts the
    write (nothing is persisted); ``valid``/``thin`` annotate the entry.
    """
    handback = None
    if packet_path:
        with open(packet_path, "r", encoding="utf-8") as f:
            packet = json.load(f)
        from ActionHandbackVerifier.verifier import evaluate_handback
        verdict_doc = evaluate_handback(packet)
        handback = {"verdict": verdict_doc["verdict"],
                    "handback_id": verdict_doc.get("handback_id", "")}
        if handback["verdict"] == "breach":
            return {"status": "handback_breach",
                    "idea_id": explore_winner.get("idea_id", ""),
                    "handback": handback}

    entry = explore_adp.evx_winner_to_consumed_entry(
        winner=explore_winner, source_chain=source_chain,
        implementations=[implementation])
    if handback:
        entry["handback_verdict"] = handback["verdict"]
    ledger = load_ledger(ledger_path)
    if is_consumed(entry, ledger)["consumed"]:
        result = {"status": "already_recorded", "idea_id": entry["idea_id"]}
        if handback:
            result["handback"] = handback
        return result
    append_consumed(ledger, entry, now=now)
    corpus_entry = winner_to_corpus_entry(entry)
    added = append_corpus_entry(corpus_path, corpus_entry)
    save_ledger(ledger_path, ledger)
    result = {"status": "closed", "idea_id": entry["idea_id"],
              "corpus_entry": corpus_entry, "corpus_added": added}
    if handback:
        result["handback"] = handback
    return result


def verify_handback(registry_path: str, project_name: str, packet_path: str) -> dict:
    """Actuator: verify a project's handback packet and persist the verdict.

    Loads the handback packet, evaluates it with ActionHandbackVerifier, and
    writes the verdict into the registry entry's ``handback_verdict`` field
    (atomic write). The next ``registry_to_ledger`` read trusts the persisted
    verdict without re-evaluation, closing the write/read loop.
    """
    registry = read_json(registry_path, default=None)
    if registry is None:
        raise FileNotFoundError(f"registry not found: {registry_path}")
    projects = registry.get("generated_projects", {})
    gp = projects.get(project_name)
    if gp is None:
        raise KeyError(f"project not found in registry: {project_name}")
    with open(packet_path, "r", encoding="utf-8") as f:
        packet = json.load(f)
    from ActionHandbackVerifier.verifier import evaluate_handback
    result = evaluate_handback(packet)
    gp["handback_verdict"] = result["verdict"]
    atomic_write_json(registry_path, registry)
    return {
        "status": "verified",
        "project": project_name,
        "verdict": result["verdict"],
        "handback_id": result.get("handback_id", ""),
        "persisted": True,
    }


def build_report(explore_root=None, exploit_root=None, sim=None) -> dict:
    """Run one HELIX turn over the two engines' state. Deterministic given inputs.

    `sim` is an optional semantic similarity callable; when None the diversity
    measure uses its deterministic lexical default.
    """
    explore_root = explore_root or FIXTURE_EXPLORE
    exploit_root = exploit_root or FIXTURE_EXPLOIT

    ex = load_explore_state(explore_root)
    xp = load_exploit_state(exploit_root)

    # 1) project each engine's native store onto the unified ledger, then merge
    explore_ledger = explore_adp.consumed_yaml_to_ledger(ex["consumed"]) if ex["consumed"] else None
    exploit_ledger = exploit_adp.registry_to_ledger(xp["registry"]) if xp["registry"] else None
    handback_gate = exploit_ledger.pop("_handback_gate", None) if exploit_ledger else None
    ledger = build_unified_ledger(explore_ledger, exploit_ledger)

    # 2) combined diversity pool (explore ideas + exploit candidates)
    pool = []
    if ex["idea_pool"]:
        pool += explore_adp.idea_pool_to_pool(ex["idea_pool"])
    if xp["candidates"]:
        pool += exploit_adp.candidates_to_pool(xp["candidates"])
    # lexical default by design; inject a semantic sim (--sim) for grade-up
    diversity = measure_diversity(pool, sim=sim)

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
    exploit_run_status = xp.get("run_status") or {}
    exploit_phase = exploit_run_status.get("phase")
    # A run-scoped recreate status is stronger evidence than the fixture explore
    # winner: it means the exploit strand actually completed a live turn.
    last_engine = "exploit" if exploit_phase else (
        "explore" if ex["stage6_final"] else ("exploit" if xp["registry"] else None)
    )
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
        "latest_exploit_run": {
            "run_id": exploit_run_status.get("run_id"),
            "phase": exploit_phase,
            "winner": exploit_run_status.get("winner"),
            "implementation_path": exploit_run_status.get("implementation_path"),
        } if exploit_run_status else None,
        "corpus_feedback": corpus_feedback,
        "handback_gate": handback_gate,
        "next_action": action,
    }


def _print_report(r: dict) -> None:
    print("=== HELIX turn ===")
    print(f"  unified ledger: {r['ledger_size']} entries "
          f"(explore={r['ledger_origins']['explore']}, exploit={r['ledger_origins']['exploit']})")
    print(f"  diversity pool: {r['pool_size']} items | "
          f"triggered={r['diversity']['triggered']} (sim={r['diversity']['sim_kind']}, "
          f"breaches={r['diversity']['breaches']})")
    d = r["diversity"]
    if d["triggered"]:
        pairs = d.get("signals", {}).get("breached_pairs", [])
        if pairs:
            top = pairs[0]
            print(f"  diversity breach: top pair '{top['pair'][0]} + {top['pair'][1]}' "
                  f"= {top['count']}x (threshold {top['threshold']})")
        kws = d.get("signals", {}).get("breached_keywords", [])
        if kws:
            print(f"  keyword concentration: {', '.join(kws[:5])}")
    if r["winner"]:
        w = r["winner"]
        print(f"  latest explore winner: {w['winner_id']} \"{w['title']}\" "
              f"-> already_consumed={w['already_consumed']}")
        print(f"      lineage: {' -> '.join(s['id'] for s in w['lineage'])}")
    if r["corpus_feedback"]:
        names = ", ".join(c["project"] for c in r["corpus_feedback"])
        print(f"  base-pairing (explore->corpus): {names}")
    g = r.get("handback_gate")
    if g and g.get("checked"):
        print(f"  handback gate: {g['checked']} checked, {g['passed']} passed, {g['excluded']} excluded")
    a = r["next_action"]
    print(f"  NEXT ACTION: {a['action']}  ({a['why']})")


def _opt(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
    return default


def _now(argv):
    """Timestamp for actuator writes. Injected via --now, else read at the CLI edge
    (allowed: the CLI is outside the deterministic core)."""
    n = _opt(argv, "--now")
    if n:
        return n
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


USAGE = ("usage:\n"
         "  python helix.py status [--explore-root R] [--exploit-root R] [--sim lexical|mod:fn] [--json]\n"
         "  python helix.py close-loop --winner <winner.json> --ledger <ledger.json> "
         "--corpus <corpus.json> [--now <iso>] [--packet <handback.json>]\n"
         "  python helix.py verify-handback --registry <registry.json> --project <name> "
         "--packet <handback.json>\n"
         "  python helix.py loop-status [--loop-state <loop-state.json>] [--ledger <ledger.json>]\n")


def _main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"

    if cmd == "status":
        report = build_report(_opt(argv, "--explore-root"), _opt(argv, "--exploit-root"),
                              sim=resolve_sim(_opt(argv, "--sim")))
        if "--json" in argv:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_report(report)
        return 0

    if cmd == "close-loop":
        wf = _opt(argv, "--winner")
        ledger_path = _opt(argv, "--ledger")
        corpus_path = _opt(argv, "--corpus")
        packet_path = _opt(argv, "--packet")
        if not (wf and ledger_path and corpus_path):
            sys.stderr.write(USAGE)
            return 2
        with open(wf, "r", encoding="utf-8") as f:
            spec = json.load(f)
        result = close_loop(
            explore_winner=spec["winner"],
            source_chain=spec.get("source_chain", {}),
            implementation=spec["implementation"],
            ledger_path=ledger_path, corpus_path=corpus_path, now=_now(argv),
            packet_path=packet_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in ("closed", "already_recorded") else 1

    if cmd == "verify-handback":
        registry_path = _opt(argv, "--registry")
        project_name = _opt(argv, "--project")
        packet_path = _opt(argv, "--packet")
        if not (registry_path and project_name and packet_path):
            sys.stderr.write(USAGE)
            return 2
        result = verify_handback(registry_path, project_name, packet_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["verdict"] != "breach" else 1

    if cmd == "loop-status":
        # read-only: report the autonomous loop's deterministic control state
        # (stop decision + coverage). Turn execution stays in the INSTRUCTIONS meta-layer.
        from core.helix_loop_state import load_loop_state, loop_status_report
        state = load_loop_state(_opt(argv, "--loop-state", ".helix/loop/loop-state.json"))
        ledger_path = _opt(argv, "--ledger")
        ledger = load_ledger(ledger_path) if ledger_path else None
        report = loop_status_report(state, ledger)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    sys.stderr.write(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
