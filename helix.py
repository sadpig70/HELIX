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
from core.helix_condense import condense_state                # noqa: E402
from core.helix_router import route_probe_rows                # noqa: E402
from core.helix_state_receipt import (                        # noqa: E402
    apply_drift_gate, build_state_receipt, compare_receipts,
)
from core.helix_project_paths import ensure_project_src       # noqa: E402
from core.helix_provenance import trace_winner, winner_to_corpus_entry  # noqa: E402
from core.helix_validate import validate_corpus_entry         # noqa: E402
from engines.loaders import (                                 # noqa: E402
    load_explore_state, load_exploit_state, resolve_explore_paths,
    resolve_exploit_paths,
)
from engines.unify import build_unified_ledger                # noqa: E402
from engines.explore import adapter as explore_adp            # noqa: E402
from engines.exploit import adapter as exploit_adp            # noqa: E402

FIXTURE_EXPLORE = os.path.join(ROOT, "examples", "explore_state")
FIXTURE_EXPLOIT = os.path.join(ROOT, "examples", "exploit_state")


def probe_router_summary(layered_corpus: dict) -> dict:
    """Route live machine-probe agreement rows against layered platform coverage.

    This is CLI/meta-layer glue: it executes the U6 dataset builder when the local
    platform repos are available, then feeds only probe-confirmed machines to the
    deterministic router. Missing platform repos or extraction failures are reported
    as unavailable instead of changing the core next_action policy.
    """
    try:
        from scripts.condense.machine_probe_dataset import build_dataset
        dataset = build_dataset()
    except Exception as e:
        return {"available": False, "reason": str(e)}
    routed = route_probe_rows(layered_corpus, dataset["agreement"]["rows"])
    deferred = {}
    for decision in routed["decisions"]:
        if decision["action"] == "DEFER":
            for machine in decision.get("uncovered_machines", []):
                deferred[machine] = deferred.get(machine, 0) + 1
    return {
        "available": True,
        "summary": routed["summary"],
        "deferred_machines": dict(sorted(deferred.items())),
        "probe_cases": dataset["agreement"]["cases"],
        "scored_claims": dataset["agreement"]["scored_claims"],
        "matched_claims": dataset["agreement"]["matched_claims"],
        "agreement": dataset["agreement"]["agreement"],
    }


def load_forward_predict_summary(path: str) -> dict:
    """Load a U9 forward-prediction report summary for status output."""
    if not path:
        return None
    if not os.path.exists(path):
        return {"available": False, "reason": f"missing report: {path}"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except Exception as e:
        return {"available": False, "reason": str(e)}
    rows = []
    for row in report.get("rows", []):
        rows.append({
            "id": row.get("id", ""),
            "action": row.get("actual_action", ""),
            "platform": row.get("actual_platform"),
            "ok": bool(row.get("ok")),
        })
    return {
        "available": True,
        "all_ok": bool(report.get("all_ok")),
        "count": int(report.get("count", len(rows)) or 0),
        "summary": report.get("summary", {}),
        "rows": rows,
    }


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
        ensure_project_src(ROOT, "ActionHandbackVerifier")
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
    ensure_project_src(ROOT, "ActionHandbackVerifier")
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


def build_report(explore_root=None, exploit_root=None, sim=None, layered_corpus_path=None,
                 forward_predict_report_path=None) -> dict:
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
    # Condense strand (opt-in): when a layered-corpus is given (--layered-corpus), derive
    # CONDENSE / BUILD_ON_PLATFORM candidates from it. Pure transform; file loading is the
    # driver's job. No path -> no candidates -> status behaves exactly as before.
    condense = {}
    router = None
    if layered_corpus_path and os.path.exists(layered_corpus_path):
        with open(layered_corpus_path, "r", encoding="utf-8") as f:
            layered_corpus = json.load(f)
            condense = condense_state(layered_corpus)
            router = probe_router_summary(layered_corpus)
        state.update(condense)
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
        "condense": condense or None,
        "router": router,
        "forward_predict": load_forward_predict_summary(forward_predict_report_path),
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
    c = r.get("condense")
    if c:
        cc = c.get("condense_candidate")
        if cc:
            print(f"  condense candidate: '{cc['cluster']}' "
                  f"({cc['substantiated_count']} substantiated, unplatformed)")
        bp = c.get("build_on_platform_candidate")
        if bp:
            print(f"  build-on-platform: {bp['project']} -> {bp['platform']} (grow as pack)")
    router = r.get("router")
    if router:
        if router.get("available"):
            print(f"  probe router: {router['summary']} "
                  f"(matched={router['matched_claims']}/{router['scored_claims']}, "
                  f"agreement={router['agreement']:.6f})")
            if router.get("deferred_machines"):
                print(f"      deferred machines: {router['deferred_machines']}")
        else:
            print(f"  probe router: unavailable ({router.get('reason', 'unknown')})")
    fp = r.get("forward_predict")
    if fp:
        if fp.get("available"):
            print(f"  forward predict: {fp['summary']} (count={fp['count']}, all_ok={fp['all_ok']})")
            for row in fp.get("rows", []):
                platform = f" -> {row['platform']}" if row.get("platform") else ""
                print(f"      {row['id']}: {row['action']}{platform}")
        else:
            print(f"  forward predict: unavailable ({fp.get('reason', 'unknown')})")
    a = r["next_action"]
    print(f"  NEXT ACTION: {a['action']}  ({a['why']})")


def _opt(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
    return default


def _git_head(root: str):
    """Read the current commit without invoking Git; return None when unavailable."""
    git_dir = os.path.join(root, ".git")
    if os.path.isfile(git_dir):
        with open(git_dir, "r", encoding="utf-8") as f:
            marker = f.read().strip()
        if marker.startswith("gitdir:"):
            target = marker.split(":", 1)[1].strip()
            git_dir = target if os.path.isabs(target) else os.path.join(root, target)
    head_path = os.path.join(git_dir, "HEAD")
    if not os.path.isfile(head_path):
        return None
    with open(head_path, "r", encoding="utf-8") as f:
        head = f.read().strip()
    if not head.startswith("ref:"):
        return head or None
    ref = head.split(":", 1)[1].strip()
    ref_path = os.path.join(git_dir, *ref.split("/"))
    if os.path.isfile(ref_path):
        with open(ref_path, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    packed = os.path.join(git_dir, "packed-refs")
    if os.path.isfile(packed):
        with open(packed, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith(("#", "^")):
                    value, _, name = line.strip().partition(" ")
                    if name == ref:
                        return value
    return None


def _load_report_bindings(path: str) -> list:
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    reports = doc.get("reports") if isinstance(doc, dict) else None
    if not isinstance(reports, list):
        raise ValueError("--report-seals must contain a reports array")
    return reports


def _unsealed_report(report: str, path: str) -> dict:
    return {"report": report, "path": path, "expected_sha256": None, "sources": []}


def _receipt_replay_argv(argv) -> list:
    """Reproduce the receipt on stdout; output location is intentionally excluded."""
    result = ["python", "helix.py"]
    i = 1
    while i < len(argv):
        if argv[i] == "--out":
            i += 2
            continue
        result.append(argv[i])
        i += 1
    return result


def _now(argv):
    """Timestamp for actuator writes. Injected via --now, else read at the CLI edge
    (allowed: the CLI is outside the deterministic core)."""
    n = _opt(argv, "--now")
    if n:
        return n
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _live_receipt_hash() -> str:
    """Current live state-receipt hash with default paths (wedge anchor)."""
    default_reports = {
        "machine_probe": os.path.join(
            ROOT, "_workspace", "condense", "U6-machine-probe-report.json"),
        "forward_candidate_manifest": os.path.join(
            ROOT, "_workspace", "condense", "U9-live-candidate-manifest.json"),
        "forward_prediction": os.path.join(
            ROOT, "_workspace", "condense", "U9-live-forward-predict-report.json"),
    }
    report_bindings = [_unsealed_report(name, path)
                       for name, path in default_reports.items()]
    layered_corpus = os.path.join(ROOT, "seed", "condense", "layered-corpus.json")
    runtime_report = build_report(
        ROOT, ROOT, sim=resolve_sim(None), layered_corpus_path=layered_corpus,
        forward_predict_report_path=default_reports["forward_prediction"])
    input_paths = {}
    input_paths.update(resolve_explore_paths(ROOT))
    input_paths.update(resolve_exploit_paths(ROOT))
    input_paths["layered_corpus"] = layered_corpus
    gate_paths = {
        "platform_kernel": os.path.join(ROOT, "seed", "condense",
                                        "platform-kernel-lock.json"),
        "machine_probe": os.path.join(ROOT, "seed", "condense",
                                      "machine-probe-gate.json"),
        "router": os.path.join(ROOT, "seed", "condense", "router-gate.json"),
        "forward_predict": os.path.join(ROOT, "seed", "condense",
                                        "forward-predict-gate.json"),
        "loop_policy": os.path.join(ROOT, "core", "helix_loop.py"),
    }
    receipt = build_state_receipt(ROOT, runtime_report, input_paths, gate_paths,
                                  report_bindings, git_head=_git_head(ROOT))
    return receipt["receipt_hash"]


USAGE = ("usage:\n"
         "  python helix.py status [--explore-root R] [--exploit-root R] "
         "[--layered-corpus P] [--forward-predict-report P] [--sim lexical|mod:fn] [--json]\n"
         "  python helix.py state-receipt [--explore-root R] [--exploit-root R] "
         "[--layered-corpus P] [--report-seals P] [--compare P] [--out P]\n"
         "  python helix.py close-loop --winner <winner.json> --ledger <ledger.json> "
         "--corpus <corpus.json> [--now <iso>] [--packet <handback.json>]\n"
         "  python helix.py verify-handback --registry <registry.json> --project <name> "
         "--packet <handback.json>\n"
         "  python helix.py audit-handback --packet <handback.json> [--operator ID] "
         "[--provenance-class real|synthetic] [--ledger P] [--packets-dir P] "
         "[--state-receipt-hash H] [--json]\n"
         "  python helix.py corpus validate|intake|admit|promote|fingerprint|verify-ledger|status|health|quarantine-report|migrate "
         "[--root <corpus-root>] [options]\n"
         "  python helix.py loop-status [--loop-state <loop-state.json>] [--ledger <ledger.json>]\n")


def _main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"

    if cmd == "corpus":
        from core.helix_corpus_supply import corpus_cli
        code, payload = corpus_cli(argv[2:], ROOT)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code

    if cmd == "status":
        report = build_report(_opt(argv, "--explore-root"), _opt(argv, "--exploit-root"),
                              sim=resolve_sim(_opt(argv, "--sim")),
                              layered_corpus_path=_opt(argv, "--layered-corpus"),
                              forward_predict_report_path=_opt(argv, "--forward-predict-report"))
        if "--json" in argv:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_report(report)
        return 0

    if cmd == "state-receipt":
        explore_root = _opt(argv, "--explore-root", ROOT)
        exploit_root = _opt(argv, "--exploit-root", ROOT)
        layered_corpus = _opt(
            argv, "--layered-corpus", os.path.join(ROOT, "seed", "condense", "layered-corpus.json"))
        default_reports = {
            "machine_probe": os.path.join(
                ROOT, "_workspace", "condense", "U6-machine-probe-report.json"),
            "forward_candidate_manifest": os.path.join(
                ROOT, "_workspace", "condense", "U9-live-candidate-manifest.json"),
            "forward_prediction": _opt(
                argv, "--forward-predict-report",
                os.path.join(ROOT, "_workspace", "condense", "U9-live-forward-predict-report.json")),
        }
        report_bindings = _load_report_bindings(_opt(argv, "--report-seals"))
        sealed_names = {binding.get("report") for binding in report_bindings}
        for report_name, report_path in default_reports.items():
            if report_name not in sealed_names:
                report_bindings.append(_unsealed_report(report_name, report_path))

        runtime_report = build_report(
            explore_root, exploit_root,
            sim=resolve_sim(_opt(argv, "--sim")),
            layered_corpus_path=layered_corpus,
            forward_predict_report_path=default_reports["forward_prediction"],
        )
        input_paths = {}
        input_paths.update(resolve_explore_paths(explore_root))
        input_paths.update(resolve_exploit_paths(exploit_root))
        if layered_corpus:
            input_paths["layered_corpus"] = layered_corpus
        gate_paths = {
            "platform_kernel": os.path.join(
                ROOT, "seed", "condense", "platform-kernel-lock.json"),
            "machine_probe": os.path.join(
                ROOT, "seed", "condense", "machine-probe-gate.json"),
            "router": os.path.join(ROOT, "seed", "condense", "router-gate.json"),
            "forward_predict": os.path.join(
                ROOT, "seed", "condense", "forward-predict-gate.json"),
            "loop_policy": os.path.join(ROOT, "core", "helix_loop.py"),
        }
        receipt = build_state_receipt(
            ROOT, runtime_report, input_paths, gate_paths, report_bindings,
            git_head=_git_head(ROOT), replay_argv=_receipt_replay_argv(argv),
        )
        compare_path = _opt(argv, "--compare")
        if compare_path:
            with open(compare_path, "r", encoding="utf-8") as f:
                stored_receipt = json.load(f)
            receipt = apply_drift_gate(
                receipt, compare_receipts(stored_receipt, receipt))
        out = _opt(argv, "--out")
        if out:
            atomic_write_json(out, receipt)
        else:
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
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

    if cmd == "audit-handback":
        # First utility wedge (P5): one submitted packet -> one sealed,
        # replayable admission decision. Exit codes: 0 ADMIT, 3 SANDBOX_ONLY,
        # 4 QUARANTINE/EXCLUDED, 1 gate refusal, 2 usage.
        from core.helix_wedge import audit_handback, verify_wedge_decision
        packet_path = _opt(argv, "--packet")
        if not packet_path:
            sys.stderr.write(USAGE)
            return 2
        with open(packet_path, "r", encoding="utf-8") as f:
            packet = json.load(f)
        provenance_class = _opt(argv, "--provenance-class")
        if provenance_class not in (None, "real", "synthetic"):
            sys.stderr.write("--provenance-class must be real or synthetic\n")
            return 2
        operator = {
            "kind": "human",
            "id": _opt(argv, "--operator", "operator-local"),
        }
        ledger_rel = _opt(argv, "--ledger",
                          os.path.join(".helix", "wedge", "ledger.jsonl"))
        packets_dir = _opt(argv, "--packets-dir",
                           os.path.join(".helix", "wedge", "packets"))
        anchor = _opt(argv, "--state-receipt-hash") or _live_receipt_hash()
        result = audit_handback(ROOT, packet, operator, anchor,
                                ledger_rel.replace(os.sep, "/"),
                                packets_dir.replace(os.sep, "/"),
                                provenance_class=provenance_class)
        if result["decision"] is None:
            print(json.dumps({"stage": "gate", "why": result["why"],
                              "gate_decision": result["gate"]["decision"]},
                             ensure_ascii=False, indent=2))
            return 1
        decision = result["decision"]
        replay_problems = verify_wedge_decision(ROOT, decision)
        if "--json" in argv:
            print(json.dumps({"decision": decision,
                              "replay_problems": replay_problems},
                             ensure_ascii=False, indent=2))
        else:
            print("=== HELIX wedge decision ===")
            print(f"  handback_id: {decision['handback_id']}")
            print(f"  verdict:     {decision['handback_verdict']}")
            print(f"  admission:   {decision['admission']}  ({decision['admission_basis']})")
            print(f"  provenance:  {decision['provenance_class']}")
            print(f"  decision:    {decision['decision_id']}  seal {decision['receipt_sha256'][:16]}…")
            print(f"  packet:      {decision['packet_path']}")
            print(f"  ledger:      {ledger_rel}")
            print(f"  replay:      python helix.py audit-handback --packet "
                  f"{decision['packet_path']} --state-receipt-hash {anchor}"
                  f" --operator {decision['operator']['id']}"
                  + (f" --provenance-class {decision['provenance_class']}"
                     if decision["provenance_class"] != "unclassified" else "")
                  + f" --ledger {ledger_rel} --packets-dir {packets_dir}")
            print(f"  replay check: {'REPRODUCED' if not replay_problems else replay_problems}")
        if replay_problems:
            return 1
        return {"ADMIT": 0, "SANDBOX_ONLY": 3}.get(decision["admission"], 4)

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
