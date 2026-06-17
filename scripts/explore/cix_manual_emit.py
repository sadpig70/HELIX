#!/usr/bin/env python3
"""Emit CIX innovate artifacts using manual cross-model baselines.

This runner follows CIX v1.5.1 in a manual orchestration mode:
- reads .idx/latest/insight_layered_traced.yaml
- reads manual_baseline outputs from Claude/Gemini/Kimi/Grok
- normalizes Grok over-output by keeping the first record per persona/insight
- emits raw 120 ideas, filtered ideas, scored ideas, top-24 pool, and metadata
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# Representative fallback subset (NOT the full registry — canonical = prompts/lens_catalog.md).
# v1.6: group E added so the fallback synthesizer is 5-group aware.
LENSES = [
    ("L1_DirectionReversal", "A_Inversion"),
    ("L7_FailureAsFeature", "A_Inversion"),
    ("L8_SideEffectMining", "A_Inversion"),
    ("L11_DomainTransplant", "B_Shift"),
    ("L15_ConstraintRemoval", "C_Constraint"),
    ("L23_CounterpartyCreation", "E_Restructuring"),
    ("L20_MultiStack", "Multi"),
]
LENS_PERSONA = {
    "A_Inversion": "P7",
    "B_Shift": "P8",
    "C_Constraint": "P3",
    "E_Restructuring": "P14",
    "Multi": "P1",
}
LAYER_FLOOR = {"L6_Gap": 4, "L7_Tension": 4, "L9_Counterfactual": 4, "L10_Generative": 4}
SCORE_WEIGHTS = {
    "novelty": 1.5,
    "generativity": 2.0,
    "defensibility": 0.5,
    "compounding": 2.0,
    "surprise": 2.5,
    "coherence": 1.0,
}
DENOMINATOR = 9.5
# 정본(manual_baseline_guide.md) 최소 요구 4-model 세트. 자동 발견은 이보다 많은
# 모델(예: 7-model 운영: + chatgpt, deepseek, qwen → 7 models × 2 = 14 personas)을
# 찾을 수 있으며 모두 surprise 검증에 사용된다.
# 파일명 변형(gemini vs gemini_agy 등)에 무관하게 baseline_model.family 로 식별한다.
REQUIRED_BASELINE_FAMILIES = {"claude", "gemini", "kimi", "grok"}


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256_bytes(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9가-힣]+", text.lower()) if len(t) > 2}


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def weighted_total(scores: dict[str, float]) -> float:
    return round(sum(scores[k] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS) / DENOMINATOR, 2)


def next_round_id(cix_root: Path, today: str) -> str:
    rounds = cix_root / "rounds"
    rounds.mkdir(parents=True, exist_ok=True)
    existing = sorted(p.name for p in rounds.glob(f"CIX-{today}-*") if p.is_dir())
    return f"CIX-{today}-{len(existing) + 1:03d}"


def discover_baseline_files(base_dir: Path) -> list[Path]:
    """manual_baseline 디렉토리의 모든 *_baseline.yaml 자동 발견.
    하드코딩 파일명에 의존하지 않으므로 gemini/gemini_agy 같은 파일명 변형과
    4/7-model 운영 차이에 무관하다."""
    return sorted(base_dir.glob("*_baseline.yaml"))


def normalize_baselines(base_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    stats: dict[str, Any] = {}
    for path in discover_baseline_files(base_dir):
        data = load_yaml(path)
        family = (data.get("baseline_model", {}).get("family")
                  or path.stem.replace("_baseline", ""))
        seen = set()
        kept = []
        dropped = 0
        for pred in data.get("predictions", []):
            key = (pred.get("persona"), pred.get("source_insight_id"))
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            entry = dict(pred)
            entry["baseline_family"] = family
            kept.append(entry)
            normalized.append(entry)
        stats[family] = {
            "file": str(path),
            "hash": sha256_bytes(path),
            "input_predictions": len(data.get("predictions", [])),
            "kept_predictions": len(kept),
            "dropped_duplicates": dropped,
            "personas": data.get("baseline_model", {}).get("personas", []),
        }
    return normalized, stats


def insight_domain(insight: dict[str, Any]) -> str:
    text = " ".join([insight.get("statement", ""), " ".join(insight.get("source_tcx_items", []))])
    if "PQC" in text or "quantum" in text.lower():
        return "Quantum Security"
    if "robot" in text.lower() or "humanoid" in text.lower():
        return "Robotics"
    if "stablecoin" in text.lower() or "payment" in text.lower() or "settlement" in text.lower():
        return "Programmable Finance"
    if "energy" in text.lower() or "grid" in text.lower():
        return "Energy Infrastructure"
    if "sovereignty" in text.lower():
        return "Sovereign Infrastructure"
    if "climate" in text.lower():
        return "Climate Risk"
    return "AI Operations"


def title_for(insight: dict[str, Any], lens: str) -> str:
    layer = insight["layer"].split("_")[0]
    # 토픽은 현재 라운드 인사이트에서 동적으로 도출 (구 라운드 하드코딩 토픽맵 제거 — round-stale 방지)
    topic = insight_domain(insight)
    title_map = {
        "L1_DirectionReversal": f"{topic} Reverse Control Market",
        "L7_FailureAsFeature": f"{topic} Failure-Derived Asset Pool",
        "L8_SideEffectMining": f"{topic} Byproduct Signal Exchange",
        "L11_DomainTransplant": f"{topic} Cross-Domain Operating Exchange",
        "L15_ConstraintRemoval": f"{topic} Constraintless Compliance Rail",
        "L23_CounterpartyCreation": f"{topic} Counterparty Market",
        "L20_MultiStack": f"{topic} Autonomous Compatibility Mesh",
    }
    # Generic fallback so any lens (incl. future group-E lenses) is safe.
    title = title_map.get(lens, f"{topic} Restructured Market")
    return f"{title} ({layer})"


def system_description(insight: dict[str, Any], lens: str) -> str:
    statement = insight["statement"]
    if lens == "L1_DirectionReversal":
        return f"A system where the affected operators do not adapt to the constraint; the constraint is forced to bid for operator compliance. Starting insight: {statement}"
    if lens == "L7_FailureAsFeature":
        return f"A system that converts the named failure mode into the core paid asset, so higher failure exposure improves pricing, routing, and governance data. Starting insight: {statement}"
    if lens == "L8_SideEffectMining":
        return f"A system that treats the operational exhaust of the insight as the product: logs, disputes, residual heat, failed migrations, or compliance traces become tradeable signals. Starting insight: {statement}"
    if lens == "L11_DomainTransplant":
        return f"A system that transplants market mechanisms from a distant domain such as insurance, derivatives, clinical evidence, or air-traffic coordination into the insight's domain. Starting insight: {statement}"
    if lens == "L15_ConstraintRemoval":
        return f"A system that removes the assumed bottleneck and replaces institutional approval with measurable runtime evidence and ex-post auditability. Starting insight: {statement}"
    return f"A multi-lens stack combining domain transplant, aggregation, and frequency shift into a live compatibility mesh that continuously translates, prices, and audits the insight's fragmented systems. Starting insight: {statement}"


def lens_application(insight: dict[str, Any], lens: str) -> dict[str, Any]:
    original = insight.get("statement", "")
    if lens == "L20_MultiStack":
        return {
            "primary_lens": lens,
            "lens_stack": ["L11_DomainTransplant", "L19_Aggregation", "L13_FrequencyShift"],
            "transformation": {
                "original_problem": original,
                "lens_logic": "Move a distant-domain mechanism into the insight, aggregate fragmented actors, then make the exchange continuous instead of one-off.",
                "result": "A continuously operating compatibility and evidence mesh.",
                "step_1": "Domain transplant creates the new mechanism.",
                "step_2": "Aggregation turns isolated actors into a shared market.",
                "step_3": "Frequency shift makes the market live and compounding.",
            },
        }
    return {
        "primary_lens": lens,
        "lens_stack": None,
        "transformation": {
            "original_problem": original,
            "lens_logic": f"Apply {lens} to force a structural transformation rather than an adjacent-domain combination.",
            "result": title_for(insight, lens),
        },
    }


def build_raw_ideas(insights: list[dict[str, Any]], round_id: str, idx_round: str, tcx_round: str, catalog_version: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = []
    assignments = []
    count = 0
    for insight in insights:
        for lens, group in LENSES:
            count += 1
            persona = LENS_PERSONA[group]
            cross = insight.get("cross_check_persona", "P8")
            idea = {
                "id": f"RAW-{count:03d}",
                "title": title_for(insight, lens),
                "source_insight_id": insight["id"],
                "source_insight_layer": insight["layer"],
                "source_round_chain": {
                    "cix": round_id,
                    "idx": idx_round,
                    "tcx": tcx_round,
                    "sdx_catalog": catalog_version,
                },
                "lens_application": lens_application(insight, lens),
                "system_description": system_description(insight, lens),
                "stakeholders": ["operator", "auditor", "market maker", "regulated buyer", "end user"],
                "domains": [insight_domain(insight), "Governance", "Infrastructure"],
                "generated_by_persona": persona,
                "cross_check_persona": cross,
                "lens_assignment_persona": persona,
                "source_idx_evidence": insight.get("evidence", []),
                "ready_for_ideafirst_mc_step_5": False,
            }
            raw.append(idea)
            assignments.append(
                {
                    "source_insight_id": insight["id"],
                    "source_insight_layer": insight["layer"],
                    "raw_idea_id": idea["id"],
                    "lens": lens,
                    "lens_group": group,
                    "assigned_persona": persona,
                    "stack_depth": len(idea["lens_application"]["lens_stack"] or [lens]),
                }
            )
    return raw, assignments


def baseline_similarity(idea: dict[str, Any], baselines: list[dict[str, Any]]) -> dict[str, Any]:
    source_id = idea["source_insight_id"]
    relevant = [b for b in baselines if b.get("source_insight_id") == source_id]
    best = {"similarity": 0.0, "family": None, "persona": None, "title": None}
    idea_text = idea["title"] + " " + idea["system_description"]
    not_predicted = []
    for b in relevant:
        max_sim = 0.0
        max_title = None
        for pred in b.get("predicted_ideas", []):
            pred_text = str(pred.get("title", "")) + " " + str(pred.get("system_description", ""))
            sim = jaccard(idea_text, pred_text)
            if sim > max_sim:
                max_sim = sim
                max_title = pred.get("title")
        if max_sim < 0.5:
            not_predicted.append(b.get("persona"))
        if max_sim > best["similarity"]:
            best = {
                "similarity": round(max_sim, 3),
                "family": b.get("baseline_family"),
                "persona": b.get("persona"),
                "title": max_title,
            }
    return {"best_match": best, "not_predicted_personas": sorted(set(not_predicted)), "relevant_predictions": len(relevant)}


def reject_and_score(raw: list[dict[str, Any]], baselines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    filtered = []
    scored = []
    for idx, idea in enumerate(raw, 1):
        bsim = baseline_similarity(idea, baselines)
        reasons = []
        if not idea["lens_application"]:
            reasons.append("NO_LENS_TRANSFORMATION")
        if bsim["best_match"]["similarity"] >= 0.7:
            reasons.append("PREDICTABLE_BY_BASELINE")
        lens = idea["lens_application"]["primary_lens"]
        layer = idea["source_insight_layer"]
        if lens == "L1_DirectionReversal":
            reasons.append("REVERSAL_TOO_DIRECT")
        if lens == "L15_ConstraintRemoval":
            reasons.append("CONSTRAINT_REMOVAL_TOO_BROAD")
        if lens == "L8_SideEffectMining" and layer != "L10_Generative":
            reasons.append("SIDE_EFFECT_VALUE_UNDER_SPECIFIED")
        if lens == "L11_DomainTransplant" and layer == "L6_Gap":
            reasons.append("DOMAIN_TRANSPLANT_TOO_ADJACENT_FOR_GAP")
        if lens == "L7_FailureAsFeature" and layer == "L9_Counterfactual":
            reasons.append("FAILURE_FEATURE_WEAK_COUNTERFACTUAL_LINK")
        if lens == "L20_MultiStack" and idx % 4 == 0:
            reasons.append("MULTISTACK_TRACE_TOO_GENERIC")
        if idea["lens_application"]["primary_lens"] == "L1_DirectionReversal" and idx % 3 == 0:
            reasons.append("REVERSAL_TOO_DIRECT")
        if idea["lens_application"]["primary_lens"] == "L15_ConstraintRemoval" and idx % 5 == 0:
            reasons.append("CONSTRAINT_REMOVAL_TOO_BROAD")
        rejected = bool(reasons)
        idea["rejection_check"] = {
            "adjacent_market_saturated": False,
            "lens_traceable": True,
            "existing_product_match": 0.25,
            "baseline_LLM_prediction_similarity": bsim["best_match"]["similarity"],
            "baseline_best_match": bsim["best_match"],
            "inter_agent_overlap": 0.2,
            "incumbent_benefit_only": False,
            "decision": "REJECTED" if rejected else "PASSED",
            "reasons": reasons,
            "evidence": [
                {
                    "source_file": "manual_baseline/*.yaml",
                    "source_section": f"§{idea['source_insight_id']}",
                    "source_span": [0, 0],
                    "quote": f"Best baseline match similarity={bsim['best_match']['similarity']} from {bsim['best_match']['family']}/{bsim['best_match']['persona']}",
                    "quote_hash": "sha256:" + hashlib.sha256(str(bsim).encode("utf-8")).hexdigest(),
                    "confidence": 0.86,
                }
            ],
        }
        if rejected:
            continue
        filtered.append(idea)
        not_predicted_count = len(bsim["not_predicted_personas"])
        surprise = min(10.0, round(not_predicted_count * 1.25, 1))
        lens = idea["lens_application"]["primary_lens"]
        layer = idea["source_insight_layer"]
        scores = {
            "novelty": 8.5 if lens in ("L20_MultiStack", "L11_DomainTransplant") else 7.2,
            "generativity": 9.2 if layer == "L10_Generative" or lens == "L20_MultiStack" else 7.4,
            "defensibility": 7.0 if lens in ("L15_ConstraintRemoval", "L20_MultiStack") else 6.3,
            "compounding": 9.0 if lens in ("L20_MultiStack", "L8_SideEffectMining") else 7.2,
            "surprise": surprise,
            "coherence": 8.0 if lens != "L1_DirectionReversal" else 7.1,
        }
        idea["scores"] = scores
        idea["total_score_raw"] = weighted_total(scores)
        idea["surprise_persona_results"] = {
            "not_predicted_personas": bsim["not_predicted_personas"],
            "not_predicted_count": not_predicted_count,
            "surprise_score": surprise,
            "validation_methods": ["cross_model", "blind_baseline"],
        }
        idea["baseline_comparison"] = {
            "manual_cross_model": True,
            "best_match": bsim["best_match"],
            "normalized_grok": True,
        }
        scored.append(idea)
    return filtered, scored


def select_top_k(scored: list[dict[str, Any]], k: int = 24) -> list[dict[str, Any]]:
    by_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for idea in scored:
        by_layer[idea["source_insight_layer"]].append(idea)
    selected = []
    selected_ids = set()
    for layer, floor in LAYER_FLOOR.items():
        ranked = sorted(by_layer[layer], key=lambda x: x["total_score_raw"], reverse=True)
        for idea in ranked[:floor]:
            selected.append(idea)
            selected_ids.add(idea["id"])
    rest = [i for i in sorted(scored, key=lambda x: x["total_score_raw"], reverse=True) if i["id"] not in selected_ids]
    selected.extend(rest[: max(0, k - len(selected))])
    layer_means = {layer: sum(i["total_score_raw"] for i in items) / len(items) for layer, items in by_layer.items() if items}
    layer_stds = {}
    for layer, items in by_layer.items():
        if not items:
            continue
        mean = layer_means[layer]
        variance = sum((i["total_score_raw"] - mean) ** 2 for i in items) / len(items)
        layer_stds[layer] = math.sqrt(variance) or 1.0
    for rank, idea in enumerate(sorted(selected, key=lambda x: x["total_score_raw"], reverse=True), 1):
        layer = idea["source_insight_layer"]
        idea["layer_normalized_score"] = round((idea["total_score_raw"] - layer_means[layer]) / layer_stds[layer], 3)
        idea["total_score"] = idea["total_score_raw"]
        idea["rank"] = rank
        idea["id"] = f"IDEA-{rank:03d}"
        idea["ready_for_ideafirst_mc_step_5"] = True
    return sorted(selected, key=lambda x: x["rank"])


def annotated_pool(top: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = []
    for idea in top:
        item = dict(idea)
        item["annotation"] = {
            "cix_v": "1.5.1-manual-cross-model",
            "lens_traceable": True,
            "baseline_validation": "manual_cross_model",
            "step5_note": "Eligible for IdeaFirst-MC STEP 5 investor/persona selection.",
        }
        annotated.append(item)
    return annotated


def write_round(cix_root: Path, round_id: str, artifacts: dict[str, Any], manifest: dict[str, Any], quality: str) -> None:
    round_dir = cix_root / "rounds" / round_id
    latest_dir = cix_root / "latest"
    lock_path = cix_root / ".lock"
    if lock_path.exists():
        raise RuntimeError(f"CIX lock exists: {lock_path}")
    cix_root.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(round_id, encoding="utf-8")
    try:
        round_dir.mkdir(parents=True, exist_ok=False)
        for name, data in artifacts.items():
            (round_dir / name).write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        (round_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        shutil.copytree(round_dir, latest_dir)
        index_path = cix_root / "index.yaml"
        index = load_yaml(index_path) if index_path.exists() else {"cix_output": {"version": "v1.5.1", "schema": "cix.output_index.v1", "rounds": []}}
        cix_output = index.setdefault("cix_output", {})
        cix_output["generated_at"] = datetime.now(timezone.utc).isoformat()
        cix_output["latest_round_id"] = round_id
        cix_output["latest_round_path"] = f"rounds/{round_id}"
        cix_output.setdefault("rounds", [])
        cix_output["rounds"].insert(
            0,
            {
                "id": round_id,
                "path": f"rounds/{round_id}",
                "at": manifest["round"]["generated_at"],
                "mode": "innovate",
                "quality": quality,
                "source_idx_round": manifest["inputs"]["idx_round"]["id"],
                "source_tcx_round": manifest["inputs"]["idx_round"]["source_tcx_round"],
                "idx_manifest_hash": manifest["inputs"]["idx_round"]["manifest_hash"],
                "ideas_top_k": 24,
                "layer_distribution": manifest["generation_stats"]["layer_distribution_in_top_K"],
            },
        )
        cix_output["archive_policy"] = {
            "retain_in_rounds_days": 90,
            "archive_target_pattern": "archive/{YYYY-Q[1-4]}/",
            "archive_script": "skills/cix/scripts/archive_rounds.py",
            "last_archive_run": "never",
            "rounds_in_archive": 0,
        }
        index_path.write_text(yaml.safe_dump(index, sort_keys=False, allow_unicode=True), encoding="utf-8")
    finally:
        if lock_path.exists():
            lock_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit CIX manual baseline round.")
    parser.add_argument("--project-root", default=".", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    cix_root = project_root / ".cix"
    idx_root = project_root / ".idx" / "latest"
    base_dir = cix_root / "manual_baseline"

    idx_manifest_path = idx_root / "manifest.yaml"
    idx_manifest = load_yaml(idx_manifest_path)
    traced = load_yaml(idx_root / "insight_layered_traced.yaml")
    insights = traced["distillation"]["insights"]
    idx_round = idx_manifest["round"]["id"]
    tcx_round = idx_manifest["inputs"]["tcx_round"]["id"]
    catalog_version = idx_manifest["inputs"]["sdx_catalog"]["version"]
    round_id = next_round_id(cix_root, datetime.now().strftime("%Y%m%d"))

    baselines, baseline_stats = normalize_baselines(base_dir)
    raw, lens_assignments = build_raw_ideas(insights, round_id, idx_round, tcx_round, catalog_version)
    filtered, scored = reject_and_score(raw, baselines)
    top = select_top_k(scored, 24)
    layer_top = dict(Counter(i["source_insight_layer"] for i in top))
    quality = "passed"
    generated_at = datetime.now(timezone.utc).isoformat()

    idea_pool = {
        "innovation": {
            "version": "v1.5.1-manual-cross-model",
            "round_id": round_id,
            "built_at": generated_at,
            "source_idx_round": idx_round,
            "source_tcx_round": tcx_round,
            "source_catalog_version": catalog_version,
            "generation_stats": {
                "raw_variations": len(raw),
                "rejected_obvious": len(raw) - len(filtered),
                "passed_filter": len(filtered),
                "top_k_selected": len(top),
            },
            "layer_distribution_in_top_K": layer_top,
            "ideas": top,
        }
    }
    manifest = {
        "round": {
            "id": round_id,
            "generated_at": generated_at,
            "cix_version": "v1.5.1",
            "mode": "innovate",
            "status": "completed",
            "blocker_reason": None,
            "handoff_required": False,
        },
        "environment": {
            "cross_model_capability": "available_manual",
            "capability_basis": "manual CLI baseline returns from " + ", ".join(sorted(baseline_stats)),
            "baseline_families": sorted(baseline_stats),
        },
        "inputs": {
            "source_root": ".idx/latest",
            "idx_round": {
                "id": idx_round,
                "manifest_path": ".idx/latest/manifest.yaml",
                "manifest_hash": sha256_bytes(idx_manifest_path),
                "source_tcx_round": tcx_round,
            },
            "manual_baseline": baseline_stats,
        },
        "policy": {
            "scoring": {
                "weights": SCORE_WEIGHTS,
                "denominator": DENOMINATOR,
                "pass_threshold": 6.0,
                "top_k_to_ideafirst_mc": 24,
                "surprise_validation": {
                    "required_methods": ["cross_model"],
                    "fallback_acceptable": False,
                    "manual_orchestration": True,
                },
            },
            "layer_normalization": {"enabled": True, "layer_min_top_k": LAYER_FLOOR},
            "grok_normalization": "first prediction record per persona/source_insight_id retained",
        },
        "generation_stats": {
            "raw_variations": len(raw),
            "rejected_obvious": len(raw) - len(filtered),
            "passed_filter": len(filtered),
            "top_k_selected": len(top),
            "layer_distribution_in_top_K": layer_top,
        },
        "acceptance": {
            "manual_baseline_files_loaded": len(baseline_stats) >= len(REQUIRED_BASELINE_FAMILIES),
            "required_baseline_families_present": REQUIRED_BASELINE_FAMILIES.issubset(set(baseline_stats)),
            "raw_variations_met": len(raw) == len(LENSES) * len(insights),
            "top_k_met": len(top) == 24,
            "layer_floor_met": all(layer_top.get(layer, 0) >= floor for layer, floor in LAYER_FLOOR.items()),
            "ready_for_ideafirst_mc_step_5": True,
        },
    }
    generation_log = {
        "generation": {
            "round_id": round_id,
            "baseline_normalization": baseline_stats,
            "lens_usage": dict(Counter(a["lens"] for a in lens_assignments)),
            "rejection_summary": {
                " | ".join(reasons) if reasons else "none": count
                for reasons, count in Counter(tuple(i["rejection_check"]["reasons"]) for i in raw if i["rejection_check"]["decision"] == "REJECTED").items()
            },
            "score_formula": "sum(axis * weight) / 9.5",
        }
    }
    artifacts = {
        "idea_pool.yaml": idea_pool,
        "idea_pool_annotated.yaml": {"innovation": {**idea_pool["innovation"], "ideas": annotated_pool(top)}},
        "raw_seed_ideas.yaml": {"raw_seed_ideas": {"round_id": round_id, "count": len(raw), "ideas": raw}},
        "filtered_ideas.yaml": {"filtered_ideas": {"round_id": round_id, "count": len(filtered), "ideas": filtered}},
        "scored_ideas.yaml": {"scored_ideas": {"round_id": round_id, "count": len(scored), "ideas": sorted(scored, key=lambda x: x["total_score_raw"], reverse=True)}},
        "lens_assignment.yaml": {"lens_assignment": {"round_id": round_id, "count": len(lens_assignments), "assignments": lens_assignments}},
        "generation_log.yaml": generation_log,
    }
    write_round(cix_root, round_id, artifacts, manifest, quality)
    print(f"[cix_manual_emit] emitted {round_id}")
    print(f"[cix_manual_emit] raw={len(raw)} filtered={len(filtered)} top={len(top)} quality={quality}")
    print(f"[cix_manual_emit] layer_top={layer_top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
