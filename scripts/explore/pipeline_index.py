#!/usr/bin/env python3
"""PipelineIndex — lightweight index for IdeaFirst pipeline artifacts.

Extends the pgxf indexing pattern beyond .pgf/ to the large pipeline outputs
(.cix idea pool, .idx insights, .evx winners) so an agent can lookup an idea or
insight by id, jump to its source line, and check consumed status WITHOUT loading
the full multi-thousand-line YAML into context.

The index is a derived artifact under .pgxf/ — rebuild anytime. Source artifacts
(.cix/.idx/.evx/.idea-ledger) are never modified.

Modes:
  build   — scan latest artifacts → .pgxf/INDEX-pipeline.json
  lookup  — id (IDEA-NNN / INS-...) → entry + source location, no full YAML load
  status  — print aggregates (mechanism dist, white-space share, consumed count)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PGXF_VERSION = "pipeline-index-0.1"
ID_LINE = re.compile(r"^\s*-\s*id:\s*([A-Za-z0-9_.-]+)\s*$")


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def line_index(path: Path) -> dict[str, int]:
    """1-based line scan for '- id: X' entries. First occurrence wins."""
    result: dict[str, int] = {}
    if not path.exists():
        return result
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = ID_LINE.match(line)
        if m and m.group(1) not in result:
            result[m.group(1)] = n
    return result


def index_idea_pool(cix_dir: Path) -> dict[str, Any]:
    pool_path = cix_dir / "idea_pool.yaml"
    data = read_yaml(pool_path)
    inn = data.get("innovation", {}) if isinstance(data, dict) else {}
    ideas = inn.get("ideas", []) or []
    lines = line_index(pool_path)
    cix_round = inn.get("round_id")

    entries: dict[str, Any] = {}
    for idea in ideas:
        if not isinstance(idea, dict):
            continue
        iid = idea.get("id")
        cat = idea.get("cixx_category", {}) or {}
        entries[iid] = {
            "id": iid,
            "rank": idea.get("rank"),
            "title": idea.get("title"),
            "mechanism": cat.get("mechanism"),
            "domain": cat.get("domain"),
            "is_white_space": bool(cat.get("is_white_space", False)),
            "category_saturation": idea.get("category_saturation"),
            "total_score": idea.get("total_score", idea.get("total_score_raw")),
            "source_insight_id": idea.get("source_insight_id"),
            "line": lines.get(iid),
            "consumed": None,  # filled by crossref_consumed
        }
    return {
        "file": str(pool_path).replace("\\", "/"),
        "round_id": cix_round,
        "count": len(entries),
        "ideas": entries,
    }


def index_insights(idx_dir: Path) -> dict[str, Any]:
    ins_path = idx_dir / "insight_layered_traced.yaml"
    data = read_yaml(ins_path)
    dist = data.get("distillation", {}) if isinstance(data, dict) else {}
    insights = dist.get("insights", []) or []
    lines = line_index(ins_path)

    entries: dict[str, Any] = {}
    for ins in insights:
        if not isinstance(ins, dict):
            continue
        iid = ins.get("id")
        statement = str(ins.get("statement", ""))
        entries[iid] = {
            "id": iid,
            "layer": ins.get("layer"),
            "total_score": ins.get("total_score"),
            "is_strong": bool(ins.get("is_strong", False)),
            "statement_preview": statement[:120],
            "line": lines.get(iid),
        }
    return {
        "file": str(ins_path).replace("\\", "/"),
        "round_id": dist.get("round_id"),
        "count": len(entries),
        "insights": entries,
    }


def index_evx_winners(evx_dir: Path) -> dict[str, Any]:
    stage6 = read_yaml(evx_dir / "stage6_final.yaml")
    if not stage6:
        return {}

    def wid(block: Any) -> Any:
        return block.get("id") if isinstance(block, dict) else None

    return {
        "file": str(evx_dir / "stage6_final.yaml").replace("\\", "/"),
        "round_id": stage6.get("round_id"),
        "consensus_winner": wid(stage6.get("consensus_winner")),
        "innovation_winner": wid(stage6.get("innovation_winner")),
        "final_1": wid(stage6.get("final_1")),
        "winners_identical": stage6.get("winners_identical"),
        "excluded_consumed": stage6.get("excluded_consumed"),
    }


def crossref_consumed(pool: dict[str, Any], ledger_path: Path) -> int:
    """Mark pool ideas consumed by same-round id match against the ledger."""
    ledger = read_yaml(ledger_path)
    entries = ledger.get("consumed_ideas", []) or []
    cix_round = pool.get("round_id")
    consumed_count = 0
    for iid, entry in pool.get("ideas", {}).items():
        for item in entries:
            item_cix = (item.get("source_chain") or {}).get("cix")
            if item.get("idea_id") == iid and item_cix and item_cix == cix_round:
                impls = item.get("implementations") or []
                repo = impls[0].get("repo_url") if impls and isinstance(impls[0], dict) else None
                entry["consumed"] = repo or True
                consumed_count += 1
                break
    return consumed_count


def aggregate(pool: dict[str, Any], insights: dict[str, Any], consumed_count: int) -> dict[str, Any]:
    mech: dict[str, int] = {}
    white = 0
    for e in pool.get("ideas", {}).values():
        m = e.get("mechanism") or "unknown"
        mech[m] = mech.get(m, 0) + 1
        if e.get("is_white_space"):
            white += 1
    layers: dict[str, int] = {}
    for e in insights.get("insights", {}).values():
        layer = e.get("layer") or "unknown"
        layers[layer] = layers.get(layer, 0) + 1
    total = pool.get("count", 0)
    return {
        "pool_total": total,
        "pool_consumed": consumed_count,
        "pool_eligible": total - consumed_count,
        "white_space_count": white,
        "white_space_share": round(white / total, 4) if total else 0.0,
        "mechanism_distribution": dict(sorted(mech.items(), key=lambda kv: (-kv[1], kv[0]))),
        "insight_layer_distribution": dict(sorted(layers.items())),
    }


def build_index(root: Path) -> dict[str, Any]:
    pool = index_idea_pool(root / ".cix" / "latest")
    insights = index_insights(root / ".idx" / "latest")
    evx = index_evx_winners(root / ".evx" / "latest")
    consumed_count = crossref_consumed(pool, root / ".idea-ledger" / "consumed_ideas.yaml")
    summary = aggregate(pool, insights, consumed_count)
    return {
        "pgxf_version": PGXF_VERSION,
        "idea_pool": pool,
        "insights": insights,
        "evx_winners": evx,
        "summary": summary,
    }


def cmd_build(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    index = build_index(root)
    out = root / ".pgxf" / "INDEX-pipeline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s = index["summary"]
    print(f"[pipeline-index] wrote {out}")
    print(f"  ideas: {s['pool_total']} ({s['pool_consumed']} consumed, {s['pool_eligible']} eligible) | "
          f"white-space: {s['white_space_count']} ({s['white_space_share']:.0%})")
    print(f"  insights: {index['insights']['count']} | winners(final_1): {index['evx_winners'].get('final_1')}")
    return 0


def _load_index(root: Path) -> dict[str, Any]:
    path = root / ".pgxf" / "INDEX-pipeline.json"
    if not path.exists():
        raise SystemExit("index missing — run: pipeline_index.py build")
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_lookup(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    index = _load_index(root)
    target = args.id
    pool = index["idea_pool"]
    ins = index["insights"]
    if target in pool["ideas"]:
        e = pool["ideas"][target]
        print(f"[pipeline-index] {target}")
        print(f"  title: {e['title']}")
        print(f"  rank: {e['rank']} | total_score: {e['total_score']}")
        print(f"  mechanism: {e['mechanism']} | domain: {e['domain']} | white_space: {e['is_white_space']} | saturation: {e['category_saturation']}")
        print(f"  source_insight: {e['source_insight_id']}")
        consumed = e.get("consumed")
        print(f"  consumed: {consumed if consumed else 'NO (eligible)'}")
        print(f"  location: {pool['file']}:{e['line']}")
        return 0
    if target in ins["insights"]:
        e = ins["insights"][target]
        print(f"[pipeline-index] {target}")
        print(f"  layer: {e['layer']} | total_score: {e['total_score']} | strong: {e['is_strong']}")
        print(f"  statement: {e['statement_preview']}")
        print(f"  location: {ins['file']}:{e['line']}")
        return 0
    print(f"[pipeline-index] not found: {target}", file=sys.stderr)
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    index = _load_index(root)
    print(json.dumps(index["summary"], ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline_index", description="Index IdeaFirst pipeline artifacts.")
    sub = ap.add_subparsers(dest="mode", required=True)
    pb = sub.add_parser("build", help="scan latest artifacts → .pgxf/INDEX-pipeline.json")
    pb.add_argument("--project-root", default=".")
    pb.set_defaults(func=cmd_build)
    pl = sub.add_parser("lookup", help="id → entry + source location")
    pl.add_argument("id")
    pl.add_argument("--project-root", default=".")
    pl.set_defaults(func=cmd_lookup)
    ps = sub.add_parser("status", help="print pipeline aggregates")
    ps.add_argument("--project-root", default=".")
    ps.set_defaults(func=cmd_status)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
