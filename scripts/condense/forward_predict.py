#!/usr/bin/env python3
"""Forward-predict HELIX Condense routing for normalized candidates.

Input is normalized behavioral evidence, not source text:

{
  "id": "NewCandidate",
  "expected": ["M15"],
  "substantiated_count": 1,
  "artifact": {...}
}

The script probes the artifact, then routes the probe-positive machines through the
U8 router using current layered-corpus coverage plus live pack evidence.

A manifest can group candidate files or inline candidate objects:

{
  "schema": "helix-forward-predict-manifest/1.0",
  "layered_corpus": "seed/condense/layered-corpus.json",
  "candidates": [{"candidate": "candidate.json"}, {"id": "...", "expected": [...], "artifact": {...}}]
}
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_machine_probes import agreement_report  # noqa: E402
from core.helix_router import pack_machine_index, route_machine_claim  # noqa: E402
from scripts.condense.machine_probe_dataset import build_dataset  # noqa: E402

DEFAULT_LAYERED_CORPUS = os.path.join(ROOT, "seed", "condense", "layered-corpus.json")
DEFAULT_GATE = os.path.join(ROOT, "seed", "condense", "forward-predict-gate.json")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _display_path(path):
    if os.path.isabs(path):
        try:
            return os.path.relpath(path, ROOT).replace(os.sep, "/")
        except ValueError:
            return path.replace(os.sep, "/")
    return path.replace(os.sep, "/")


def _resolve_ref(ref, base_dir=None):
    if os.path.isabs(ref):
        return ref
    candidates = []
    if base_dir:
        candidates.append(os.path.join(base_dir, ref))
    candidates.append(os.path.join(ROOT, ref))
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def _candidate_case(candidate):
    expected = candidate.get("expected")
    if expected is None:
        expected = candidate.get("machines")
    if not expected:
        raise ValueError("candidate must include non-empty 'expected' or 'machines'")
    return {
        "id": candidate.get("id", "candidate"),
        "expected": expected,
        "artifact": candidate.get("artifact", {}),
    }


def _candidate_from_manifest_entry(entry, manifest_dir):
    if isinstance(entry, str):
        path = _resolve_ref(entry, manifest_dir)
        return _load_json(path), entry
    if not isinstance(entry, dict):
        raise ValueError("manifest candidates must be paths or objects")

    source = entry.get("candidate")
    if isinstance(source, str):
        candidate = _load_json(_resolve_ref(source, manifest_dir))
        ref = source
    elif isinstance(source, dict):
        candidate = dict(source)
        ref = entry.get("id") or source.get("id") or "inline-candidate"
    elif "artifact" in entry:
        candidate = {k: entry[k] for k in ("id", "expected", "machines",
                                           "substantiated_count", "artifact") if k in entry}
        ref = entry.get("id", "inline-candidate")
    else:
        raise ValueError("manifest candidate object needs 'candidate' or inline 'artifact'")

    for key in ("id", "expected", "machines", "substantiated_count", "artifact"):
        if key in entry and key != "candidate":
            candidate[key] = entry[key]
    return candidate, ref


def predict_candidate(candidate, layered_corpus, pack_rows=None, policy=None):
    """Return probe + router prediction for one normalized candidate dict."""
    report = agreement_report([_candidate_case(candidate)])
    row = dict(report["rows"][0])
    row["substantiated_count"] = int(candidate.get("substantiated_count", 1) or 0)
    if pack_rows is None:
        pack_rows = build_dataset()["agreement"]["rows"]
    pack_index = pack_machine_index(layered_corpus, pack_rows)
    decision = route_machine_claim(layered_corpus, row, policy=policy, pack_index=pack_index)
    return {
        "id": row["id"],
        "probe": {
            "expected": row["expected"],
            "scored": row["scored"],
            "matched": row["matched"],
            "agreement": report["agreement"],
            "results": row["results"],
        },
        "prediction": decision,
    }


def _report_row(spec, result, candidate_ref):
    prediction = result["prediction"]
    action = prediction.get("action", "")
    expected_action = spec.get("action") if isinstance(spec, dict) else None
    expected_platform = spec.get("platform") if isinstance(spec, dict) else None
    platform_absent = bool(spec.get("platform_absent")) if isinstance(spec, dict) else False
    has_expectation = (
        expected_action is not None
        or expected_platform is not None
        or platform_absent
    )
    ok = True
    if expected_action is not None:
        ok = ok and expected_action == action
    if expected_platform is not None:
        ok = ok and expected_platform == prediction.get("platform")
    if platform_absent:
        ok = ok and not prediction.get("platform")
    return {
        "candidate": candidate_ref,
        "id": result["id"],
        "matched": result["probe"]["matched"],
        "expected_action": expected_action,
        "actual_action": action,
        "expected_platform": expected_platform,
        "actual_platform": prediction.get("platform"),
        "ok": ok,
        "expectation": "locked" if has_expectation else "none",
        "prediction": prediction,
    }


def _missing_artifact_row(entry):
    candidate_ref = entry.get("candidate") or entry.get("id") or entry.get("name") or "missing-artifact"
    return {
        "candidate": candidate_ref,
        "id": entry.get("id") or entry.get("name") or candidate_ref,
        "matched": [],
        "expected_action": entry.get("action"),
        "actual_action": "MISSING_ARTIFACT",
        "expected_platform": entry.get("platform"),
        "actual_platform": None,
        "ok": True,
        "expectation": "missing_artifact",
        "missing_artifact": True,
        "reason": entry.get("reason") or entry.get("missing_artifact_reason", "normalized artifact absent"),
        "prediction": {
            "action": "MISSING_ARTIFACT",
            "why": entry.get("missing_artifact_reason", "normalized artifact absent"),
        },
    }


def _summarize_rows(rows):
    summary = {}
    for row in rows:
        action = row.get("actual_action", "")
        summary[action] = summary.get(action, 0) + 1
    return dict(sorted(summary.items()))


def build_report(gate_path=DEFAULT_GATE, layered_corpus_path=None, policy=None):
    """Build the U9 fixture report from a forward-predict gate file."""
    gate = _load_json(gate_path)
    corpus_path = layered_corpus_path or _resolve_ref(gate.get("layered_corpus", DEFAULT_LAYERED_CORPUS))
    layered_corpus = _load_json(corpus_path)
    pack_rows = build_dataset()["agreement"]["rows"]
    rows = []
    for fixture in gate.get("fixtures", []):
        candidate_rel = fixture["candidate"]
        candidate_path = _resolve_ref(candidate_rel)
        result = predict_candidate(_load_json(candidate_path), layered_corpus, pack_rows=pack_rows, policy=policy)
        rows.append(_report_row(fixture, result, candidate_rel))
    return {
        "gate": _display_path(gate_path),
        "layered_corpus": _display_path(corpus_path),
        "count": len(rows),
        "summary": _summarize_rows(rows),
        "all_ok": all(row["ok"] for row in rows),
        "rows": rows,
    }


def build_manifest_report(manifest_path, layered_corpus_path=None, policy=None):
    """Build a forward-prediction report from a candidate manifest."""
    manifest = _load_json(manifest_path)
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    corpus_ref = layered_corpus_path or manifest.get("layered_corpus", DEFAULT_LAYERED_CORPUS)
    corpus_path = _resolve_ref(corpus_ref, manifest_dir)
    layered_corpus = _load_json(corpus_path)
    pack_rows = build_dataset()["agreement"]["rows"]
    rows = []
    entries = manifest.get("candidates", [])
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest must include non-empty 'candidates' list")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("missing_artifact"):
            rows.append(_missing_artifact_row(entry))
            continue
        candidate, candidate_ref = _candidate_from_manifest_entry(entry, manifest_dir)
        result = predict_candidate(candidate, layered_corpus, pack_rows=pack_rows, policy=policy)
        rows.append(_report_row(entry if isinstance(entry, dict) else {}, result, candidate_ref))
    return {
        "manifest": _display_path(manifest_path),
        "schema": manifest.get("schema", "helix-forward-predict-manifest/1.0"),
        "layered_corpus": _display_path(corpus_path),
        "count": len(rows),
        "summary": _summarize_rows(rows),
        "all_ok": all(row["ok"] for row in rows),
        "rows": rows,
    }


def _print_text(result):
    p = result["prediction"]
    probe = result["probe"]
    print("=== HELIX forward prediction ===")
    print(f"candidate: {result['id']}")
    print(f"probe: matched={probe['matched']} scored={probe['scored']} agreement={probe['agreement']:.6f}")
    print(f"prediction: {p['action']} ({p['why']})")
    if p.get("platform"):
        print(f"platform: {p['platform']}")
    if p.get("routes"):
        print(f"routes: {p['routes']}")
    if p.get("uncovered_machines"):
        print(f"uncovered_machines: {p['uncovered_machines']}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", help="candidate JSON with id/expected/artifact")
    parser.add_argument("--gate", help="forward-predict gate JSON; builds a multi-candidate report")
    parser.add_argument("--manifest", help="candidate manifest JSON; builds a multi-candidate report")
    parser.add_argument("--layered-corpus")
    parser.add_argument("--min-cluster-for-condense", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="write JSON prediction to path")
    args = parser.parse_args(argv)
    selected = [bool(args.candidate), bool(args.gate), bool(args.manifest)]
    if sum(selected) != 1:
        parser.error("exactly one of --candidate, --gate, or --manifest is required")

    policy = {"min_cluster_for_condense": args.min_cluster_for_condense}
    if args.gate:
        result = build_report(args.gate, layered_corpus_path=args.layered_corpus, policy=policy)
    elif args.manifest:
        result = build_manifest_report(args.manifest, layered_corpus_path=args.layered_corpus, policy=policy)
    else:
        candidate = _load_json(args.candidate)
        layered_corpus = _load_json(args.layered_corpus or DEFAULT_LAYERED_CORPUS)
        result = predict_candidate(candidate, layered_corpus, policy=policy)
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, sort_keys=True, indent=2)
            f.write("\n")
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2))
    elif args.gate or args.manifest:
        print("=== HELIX forward prediction report ===")
        label = "fixtures" if args.gate else "candidates"
        print(f"{label}: {result['count']} | all_ok={result['all_ok']} | summary={result['summary']}")
        for row in result["rows"]:
            platform = f" -> {row['actual_platform']}" if row.get("actual_platform") else ""
            print(f"  {row['id']}: {row['actual_action']}{platform} | matched={row['matched']}")
    else:
        _print_text(result)
    return 0 if result.get("all_ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
