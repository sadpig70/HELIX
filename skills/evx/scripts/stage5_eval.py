#!/usr/bin/env python3
"""EVX evaluate — IdeaFirst-MC STEP 5 + 6 (deterministic core).

Reads CIX latest (.cix/latest/idea_pool.yaml + manifest.yaml), maps CIX 6-axis to
PGF 4-axis per EVX_POLICY.axis_mapping, scores all (persona × idea) cells, derives
each persona's top-3 (stage5_candidates.yaml), then aggregates to a single winner
(stage6_final.yaml) via vote_count → cognitive_style_breadth → mean_persona_score.

final_idea.md (the human-readable STEP 7 report with 5S/3R/3X) is authored separately
by the main thread — this script writes only the deterministic stages.

Default invocation (from project root that contains `.cix/`):

    python skills/evx/scripts/stage5_eval.py
    python skills/evx/scripts/stage5_eval.py --ideas .cix/rounds/CIX-20260513-001/idea_pool.yaml
    python skills/evx/scripts/stage5_eval.py --evx-root .evx --round-id EVX-20260513-001

Behavior:
- Round id auto-assigned as EVX-{YYYYMMDD}-{NNN} if --round-id not given.
- Round dir is created at .evx/rounds/{round_id}/.
- .evx/latest/ is overwritten (Windows-safe copy).
- .evx/index.yaml is prepended with the new round entry.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("[evx] PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

DEFAULT_PROJECT_ROOT = Path.cwd()
DEFAULT_PGF_PERSONAS = "skills/pgf/discovery/personas.json"

# ── EVX_POLICY.axis_mapping (single source of truth, also in SKILL.md)
AXIS_MAPPING_FORMULAS = {
    "novelty":     "(cix.novelty + cix.surprise) / 2",
    "feasibility": "cix.defensibility",
    "impact":      "(cix.generativity + cix.compounding) / 2",
    "integrity":   "cix.coherence",
}


def map_cix_to_pgf(cix_scores: dict) -> dict:
    return {
        "novelty":     (cix_scores["novelty"] + cix_scores["surprise"]) / 2,
        "feasibility":  cix_scores["defensibility"],
        "impact":      (cix_scores["generativity"] + cix_scores["compounding"]) / 2,
        "integrity":    cix_scores["coherence"],
    }


def persona_score(idea: dict, persona: dict) -> float:
    pgf = map_cix_to_pgf(idea["scores"])
    bias = persona["evaluation_bias"]
    w_sum = sum(bias.values())
    return sum(bias[ax] * pgf[ax] for ax in bias) / w_sum


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def semantic_family_from_title(title: str) -> str:
    normalized = normalize_title(title)
    normalized = re.sub(r"-l\d+$", "", normalized)
    parts = [p for p in normalized.split("-") if p not in {"autonomous"}]
    return "-".join(parts)


def load_consumed_items(ledger_path: Path) -> list[dict]:
    if not ledger_path.exists():
        return []
    data = yaml.safe_load(ledger_path.read_text(encoding="utf-8")) or {}
    return data.get("consumed_ideas", []) or []


def consumed_match_reason(idea: dict, consumed_items: list[dict]) -> str | None:
    idea_id = idea.get("id")
    idea_cix = (idea.get("source_round_chain") or {}).get("cix")
    title = idea.get("title", "")
    normalized = normalize_title(title)
    family = idea.get("semantic_family") or semantic_family_from_title(title)

    for item in consumed_items:
        # idea_id (IDEA-NNN) is round-local — each CIX round re-numbers from IDEA-001.
        # Only treat an idea_id match as consumed when both come from the SAME CIX round;
        # otherwise rely on the semantic matches below (prevents cross-round id collisions).
        item_cix = (item.get("source_chain") or {}).get("cix")
        if idea_id and idea_id == item.get("idea_id") and idea_cix and item_cix and idea_cix == item_cix:
            return f"idea_id:{idea_id}@{idea_cix}"
        if normalized and normalized == item.get("normalized_title"):
            return f"normalized_title:{normalized}"
        aliases = item.get("aliases") or []
        if normalized in {normalize_title(str(alias)) for alias in aliases}:
            return f"alias:{normalized}"
        if family and family == item.get("semantic_family"):
            return f"semantic_family:{family}"
    return None


def next_round_id(rounds_dir: Path, today: dt.date) -> str:
    prefix = f"EVX-{today.strftime('%Y%m%d')}-"
    if not rounds_dir.exists():
        return f"{prefix}001"
    existing = [p.name for p in rounds_dir.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    n = max((int(x.split("-")[-1]) for x in existing), default=0) + 1
    return f"{prefix}{n:03d}"


def load_cix_chain(cix_manifest_path: Path):
    """Extract upstream round chain from CIX manifest, if present.
    CIX manifest layout (v1.4): round.id, inputs.{source_idx_round, source_tcx_round, source_catalog_version}.
    """
    chain = {"cix": None, "idx": None, "tcx": None, "sdx_catalog": None}
    if not cix_manifest_path.exists():
        return chain
    try:
        m = yaml.safe_load(cix_manifest_path.read_text(encoding="utf-8")) or {}
        chain["cix"] = (m.get("round") or {}).get("id") or m.get("round_id") or m.get("cix_round_id")
        inputs = m.get("inputs") or {}
        idx_round = inputs.get("idx_round") or {}
        chain["idx"] = inputs.get("source_idx_round") or idx_round.get("id") or m.get("source_idx_round")
        chain["tcx"] = inputs.get("source_tcx_round") or idx_round.get("source_tcx_round") or m.get("source_tcx_round")
        chain["sdx_catalog"] = (
            inputs.get("source_catalog_version")
            or m.get("source_catalog_version")
            or inputs.get("sdx_catalog")
        )
    except Exception:  # noqa: BLE001 — manifest read is best-effort provenance
        pass
    return chain


def evaluate(ideas_path: Path, personas_path: Path, evx_root: Path,
             round_id: str | None = None, consumed_ledger: Path | None = None,
             verbose: bool = False) -> dict:
    today = dt.date.today()
    rounds_dir = evx_root / "rounds"
    rounds_dir.mkdir(parents=True, exist_ok=True)
    if round_id is None:
        round_id = next_round_id(rounds_dir, today)
    round_dir = rounds_dir / round_id
    round_dir.mkdir(parents=True, exist_ok=True)

    # ── Load
    ideas_doc = yaml.safe_load(ideas_path.read_text(encoding="utf-8"))
    all_ideas = ideas_doc["innovation"]["ideas"]
    consumed_items = load_consumed_items(consumed_ledger) if consumed_ledger else []
    excluded_consumed = []
    ideas = []
    for idea in all_ideas:
        reason = consumed_match_reason(idea, consumed_items)
        if reason:
            excluded_consumed.append({
                "id": idea.get("id"),
                "title": idea.get("title"),
                "reason": reason,
            })
        else:
            ideas.append(idea)
    if verbose and excluded_consumed:
        print(f"[evx] excluded consumed ideas: {len(excluded_consumed)}")
    personas_doc = json.loads(personas_path.read_text(encoding="utf-8"))
    personas = {p["id"]: p for p in personas_doc["personas"]}

    # ── Phase 3: persona_score matrix
    matrix = {}  # pid → [(score, idea_id, title, layer, gen_persona, cix_total)]
    for pid, p in personas.items():
        rows = []
        for it in ideas:
            s = persona_score(it, p)
            rows.append((
                round(s, 3), it["id"], it["title"],
                it.get("source_insight_layer", ""),
                it.get("generated_by_persona", ""),
                it.get("total_score", 0),
            ))
        rows.sort(key=lambda r: -r[0])
        matrix[pid] = rows

    # ── Phase 4: stage5 top-3
    stage5 = {
        "stage": "STEP_5_8AI_TOP3",
        "input_idea_count": len(all_ideas),
        "eligible_idea_count": len(ideas),
        "excluded_consumed": excluded_consumed,
        "personas": {},
    }
    for pid in sorted(matrix):
        top3 = matrix[pid][:3]
        stage5["personas"][pid] = {
            "persona_name_en": personas[pid]["name_en"],
            "evaluation_bias": personas[pid]["evaluation_bias"],
            "top_3": [
                {"rank": i + 1, "score": r[0], "id": r[1], "title": r[2],
                 "layer": r[3], "generated_by_persona": r[4],
                 "cix_total_score": r[5]}
                for i, r in enumerate(top3)
            ],
        }

    # ── Phase 5: stage6 consensus
    votes: dict[str, set] = {}
    all_scores: dict[str, list[float]] = {}
    for pid, rows in matrix.items():
        for r in rows:
            all_scores.setdefault(r[1], []).append(r[0])
        for r in rows[:3]:
            votes.setdefault(r[1], set()).add(pid)

    idea_meta = {it["id"]: it for it in ideas}
    consensus = []
    for iid, pid_set in votes.items():
        mean_s = sum(all_scores[iid]) / len(all_scores[iid])
        max_s = max(all_scores[iid])
        # find which persona gave the max score for this idea (champion)
        champion_pid = None
        for pid, rows in matrix.items():
            for r in rows:
                if r[1] == iid and r[0] == max_s:
                    champion_pid = pid
                    break
            if champion_pid:
                break
        styles = {personas[p]["cognitive_style"] for p in pid_set}
        consensus.append({
            "id": iid,
            "title": idea_meta[iid]["title"],
            "layer": idea_meta[iid].get("source_insight_layer", ""),
            "generated_by_persona": idea_meta[iid].get("generated_by_persona", ""),
            "cix_total_score": idea_meta[iid].get("total_score", 0),
            "votes": len(pid_set),
            "voters": sorted(pid_set),
            "cognitive_style_breadth": len(styles),
            "mean_persona_score": round(mean_s, 3),
            "max_persona_score": round(max_s, 3),       # ★ v1.1
            "championed_by": champion_pid,              # ★ v1.1
        })

    # ── v1.1: dual ranking — consensus + innovation
    consensus_ranking = sorted(
        consensus,
        key=lambda c: (-c["votes"], -c["cognitive_style_breadth"], -c["mean_persona_score"]),
    )
    innovation_ranking = sorted(
        consensus,
        key=lambda c: (-c["max_persona_score"], -c["votes"], -c["mean_persona_score"]),
    )

    consensus_winner = consensus_ranking[0] if consensus_ranking else None
    innovation_winner = innovation_ranking[0] if innovation_ranking else None
    winners_identical = (
        consensus_winner is not None
        and innovation_winner is not None
        and consensus_winner["id"] == innovation_winner["id"]
    )

    stage6 = {
        "stage": "STEP_6_CROSS_AI_DUAL_WINNER",
        "method_v1_1": "consensus (votes→breadth→mean) + innovation (max_persona_score→votes→mean)",
        "input_idea_count": len(all_ideas),
        "eligible_idea_count": len(ideas),
        "excluded_consumed": excluded_consumed,
        "consensus_ranking_top_8": consensus_ranking[:8],
        "innovation_ranking_top_8": innovation_ranking[:8],
        "consensus_winner": consensus_winner,
        "innovation_winner": innovation_winner,
        "winners_identical": winners_identical,
        # backward compat — v1.0 single field
        "ranking_top_8": consensus_ranking[:8],
        "final_1": consensus_winner,
    }

    # ── Quality gates
    final_votes = stage6["final_1"]["votes"] if stage6["final_1"] else 0
    quality = "passed" if final_votes >= 2 else "failed_g3_winner_votes_min"

    # ── Manifest
    chain = load_cix_chain(ideas_path.parent / "manifest.yaml")
    chain["sdx_catalog"] = chain.get("sdx_catalog") or ideas_doc.get("innovation", {}).get("source_catalog_version")
    manifest = {
        "round_id": round_id,
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {
            "idea_pool": str(ideas_path).replace("\\", "/"),
            "idea_pool_sha16": sha16(ideas_path),
            "personas": str(personas_path).replace("\\", "/"),
            "personas_sha16": sha16(personas_path),
        },
        "source_chain": chain,
        "policy": {
            "axis_mapping": AXIS_MAPPING_FORMULAS,
            "scoring": "weighted_average(bias × pgf_axis)",
            "consensus_tiebreak": ["votes", "cognitive_style_breadth", "mean_persona_score"],
            "quality_gates_g3_winner_votes_min": 2,
            "consumed_ledger": {
                "path": str(consumed_ledger).replace("\\", "/") if consumed_ledger else None,
                "read_before_selection": True,
                "excluded_count": len(excluded_consumed),
                "eligible_idea_count": len(ideas),
            },
        },
        "outputs": {
            "stage5_candidates": "stage5_candidates.yaml",
            "stage6_final": "stage6_final.yaml",
            "final_idea": "final_idea.md",
        },
        "quality": quality,
    }

    # ── Write round dir
    (round_dir / "stage5_candidates.yaml").write_text(
        yaml.safe_dump(stage5, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (round_dir / "stage6_final.yaml").write_text(
        yaml.safe_dump(stage6, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (round_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
    # final_idea.md is left for the main thread to author; only create a placeholder
    fi_path = round_dir / "final_idea.md"
    if not fi_path.exists():
        fi_path.write_text(
            f"# {round_id} — final_idea.md (placeholder)\n\n"
            f"`stage5_candidates.yaml` and `stage6_final.yaml` are written. "
            f"5S/3R/3X assessment for `{stage6['final_1']['id'] if stage6['final_1'] else '?'}` pending.\n",
            encoding="utf-8")

    # ── Sync .evx/latest/ (Windows-safe copy)
    latest = evx_root / "latest"
    if latest.exists():
        for child in latest.iterdir():
            if child.is_file():
                child.unlink()
            else:
                shutil.rmtree(child)
    latest.mkdir(parents=True, exist_ok=True)
    for f in round_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, latest / f.name)

    # ── Update .evx/index.yaml (prepend)
    index_path = evx_root / "index.yaml"
    existing = {}
    if index_path.exists():
        existing = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    out = existing.get("evx_output", {})
    out["version"] = out.get("version", "v1.0")
    out["schema"] = "evx.output_index.v1"
    out["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    out["latest_round_id"] = round_id
    out["latest_round_path"] = f"rounds/{round_id}"
    entry = {
        "id": round_id,
        "path": f"rounds/{round_id}",
        "at": manifest["built_at"],
        "mode": "evaluate",
        "quality": quality,
        "source_cix_round": chain.get("cix"),
        "final_idea_id": stage6["final_1"]["id"] if stage6["final_1"] else None,
        "final_votes": final_votes,
        "cognitive_style_breadth": stage6["final_1"]["cognitive_style_breadth"] if stage6["final_1"] else 0,
        "mean_persona_score": stage6["final_1"]["mean_persona_score"] if stage6["final_1"] else 0,
        "excluded_consumed_count": len(excluded_consumed),
        "eligible_idea_count": len(ideas),
    }
    rounds_list = out.get("rounds", []) or []
    rounds_list = [r for r in rounds_list if r.get("id") != round_id]
    rounds_list.insert(0, entry)
    out["rounds"] = rounds_list
    out.setdefault("archive_policy", {
        "retain_in_rounds_days": 90,
        "archive_target_pattern": "archive/{YYYY-Q[1-4]}/",
        "archive_script": "{EVX_SKILL_DIR}/scripts/archive_rounds.py",
        "last_archive_run": "never",
    })
    index_path.write_text(
        yaml.safe_dump({"evx_output": out}, sort_keys=False, allow_unicode=True), encoding="utf-8")

    # ── Console summary (v1.1 dual winner)
    print(f"=== EVX {round_id} — {quality} ===")
    print(f"  consumed filter: excluded={len(excluded_consumed)} eligible={len(ideas)}/{len(all_ideas)}")
    print(f"  STAGE 5: {len(personas)} personas × top-3 written: {round_dir / 'stage5_candidates.yaml'}")
    print(f"  STAGE 6: dual winner consensus written: {round_dir / 'stage6_final.yaml'}")
    cw = stage6["consensus_winner"]
    iw = stage6["innovation_winner"]
    if cw:
        print(f"\n  ★ CONSENSUS WINNER (안전한 합의): {cw['id']}  {cw['title']}")
        print(f"     votes={cw['votes']}  voters={cw['voters']}  breadth={cw['cognitive_style_breadth']}"
              f"  mean={cw['mean_persona_score']:.3f}")
        print(f"     layer={cw['layer']}  generated_by={cw['generated_by_persona']}"
              f"  cix_total={cw['cix_total_score']}")
    if iw and not stage6["winners_identical"]:
        print(f"\n  ⚡ INNOVATION WINNER (강한 champion): {iw['id']}  {iw['title']}")
        print(f"     max_persona_score={iw['max_persona_score']:.3f}  championed_by={iw['championed_by']}")
        print(f"     votes={iw['votes']}  voters={iw['voters']}  breadth={iw['cognitive_style_breadth']}")
        print(f"     layer={iw['layer']}  generated_by={iw['generated_by_persona']}"
              f"  cix_total={iw['cix_total_score']}")
        print(f"\n  → 사용자 선택지: 합의 winner와 혁신 winner가 다릅니다. 둘 다 검토 필요.")
    elif stage6["winners_identical"]:
        print(f"\n  ✓ 합의 winner == 혁신 winner (single output)")
    print(f"\n  latest/: {latest}")
    print(f"  index:   {index_path}")
    return {"round_id": round_id, "quality": quality,
            "consensus_winner": cw, "innovation_winner": iw,
            "winners_identical": stage6["winners_identical"]}


def main():
    ap = argparse.ArgumentParser(description="EVX evaluate — IdeaFirst-MC STEP 5+6 deterministic core")
    ap.add_argument("--ideas", default=".cix/latest/idea_pool.yaml",
                    help="Path to CIX idea_pool.yaml (default: .cix/latest/idea_pool.yaml)")
    ap.add_argument("--personas", default=DEFAULT_PGF_PERSONAS,
                    help=f"Path to PGF personas.json (default: {DEFAULT_PGF_PERSONAS})")
    ap.add_argument("--evx-root", default=".evx",
                    help="Path to .evx/ output directory (default: ./.evx)")
    ap.add_argument("--round-id", default=None,
                    help="Override round id (default: auto EVX-YYYYMMDD-NNN)")
    ap.add_argument("--consumed-ledger", default=".idea-ledger/consumed_ideas.yaml",
                    help="Consumed idea ledger path (default: .idea-ledger/consumed_ideas.yaml)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    ideas = Path(args.ideas)
    personas = Path(args.personas)
    evx_root = Path(args.evx_root)
    if not ideas.exists():
        print(f"[evx] idea_pool not found: {ideas}", file=sys.stderr)
        return 1
    if not personas.exists():
        print(f"[evx] personas.json not found: {personas}", file=sys.stderr)
        return 1
    evx_root.mkdir(parents=True, exist_ok=True)
    consumed_ledger = Path(args.consumed_ledger) if args.consumed_ledger else None
    result = evaluate(ideas, personas, evx_root, args.round_id, consumed_ledger, args.verbose)
    return 0 if result["quality"] == "passed" else 2


if __name__ == "__main__":
    sys.exit(main())
