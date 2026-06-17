#!/usr/bin/env python3
"""AOX local runner for IdeaFirst.

This runner turns the AOX PG/PGF contract into concrete local artifacts:

- .aox/{run_id}/status.json
- .aox/{run_id}/summary.md
- .aox/{run_id}/stage refs
- .aox/latest/
- .aox/index.yaml
- .idea-ledger/consumed_ideas.yaml

It composes existing skill outputs and local emit scripts instead of absorbing
sub-skill internals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


AOX_VERSION = "1.3.1-local-runner"
STAGES = ["0_init", "1_sdx", "2_tcx", "3_idx", "4_cix", "5_evx", "6_wrapup"]
START_FROM_ALIASES = {
    None: "0_init",
    "init": "0_init",
    "0_init": "0_init",
    "sdx": "1_sdx",
    "1_sdx": "1_sdx",
    "tcx": "2_tcx",
    "2_tcx": "2_tcx",
    "idx": "3_idx",
    "3_idx": "3_idx",
    "cix": "4_cix",
    "4_cix": "4_cix",
    "evx": "5_evx",
    "5_evx": "5_evx",
    "wrapup": "6_wrapup",
    "6_wrapup": "6_wrapup",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha16(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def semantic_family_from_title(title: str) -> str:
    normalized = normalize_title(title)
    normalized = re.sub(r"-l\d+$", "", normalized)
    parts = [p for p in normalized.split("-") if p not in {"autonomous"}]
    return "-".join(parts)


def normalize_start_from(value: str | None) -> str:
    key = value.lower() if isinstance(value, str) else value
    if key not in START_FROM_ALIASES:
        valid = ", ".join(k for k in START_FROM_ALIASES if k)
        raise ValueError(f"invalid --start-from={value!r}; valid values: {valid}")
    return START_FROM_ALIASES[key]


def stage_should_run(start_from: str, stage: str) -> bool:
    return STAGES.index(stage) >= STAGES.index(start_from)


def next_round_id(aox_root: Path, today: str | None = None) -> str:
    date_part = today or datetime.now().strftime("%Y%m%d")
    existing = []
    for child in aox_root.glob(f"AOX-{date_part}-*"):
        match = re.fullmatch(rf"AOX-{date_part}-(\d{{3}})", child.name)
        if match:
            existing.append(int(match.group(1)))
    return f"AOX-{date_part}-{(max(existing) + 1 if existing else 1):03d}"


def run_py(project_root: Path, script: str, *args: str) -> None:
    cmd = [sys.executable, script, *args]
    result = subprocess.run(cmd, cwd=project_root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def ensure_latest_outputs(project_root: Path, run_full: bool, start_from: str) -> list[str]:
    """Ensure downstream latest outputs exist. Returns action log."""
    actions: list[str] = []
    scripts = project_root / "scripts" / "explore"
    evx_stage5 = project_root / "skills" / "evx" / "scripts" / "stage5_eval.py"

    force_tcx = stage_should_run(start_from, "2_tcx")
    if force_tcx or not (project_root / ".tcx" / "latest" / "manifest.yaml").exists():
        if not run_full:
            raise FileNotFoundError(".tcx/latest/manifest.yaml")
        run_py(project_root, str(scripts / "tcx_full_emit.py"), "--project-root", ".")
        actions.append("2_tcx: emitted" if force_tcx else "2_tcx: emitted_missing")
    else:
        actions.append("2_tcx: reused .tcx/latest")

    force_idx = stage_should_run(start_from, "3_idx")
    if force_idx or not (project_root / ".idx" / "latest" / "manifest.yaml").exists():
        if not run_full:
            raise FileNotFoundError(".idx/latest/manifest.yaml")
        run_py(project_root, str(scripts / "idx_distill_emit.py"), "--project-root", ".")
        actions.append("3_idx: emitted" if force_idx else "3_idx: emitted_missing")
    else:
        actions.append("3_idx: reused .idx/latest")

    force_cix = stage_should_run(start_from, "4_cix")
    if force_cix or not (project_root / ".cix" / "latest" / "manifest.yaml").exists():
        if not run_full:
            raise FileNotFoundError(".cix/latest/manifest.yaml")
        run_py(project_root, str(scripts / "cix_manual_emit.py"), "--project-root", ".")
        actions.append("4_cix: emitted" if force_cix else "4_cix: emitted_missing")
    else:
        actions.append("4_cix: reused .cix/latest")

    force_evx = stage_should_run(start_from, "5_evx")
    if force_evx or not (project_root / ".evx" / "latest" / "manifest.yaml").exists():
        if not run_full:
            raise FileNotFoundError(".evx/latest/manifest.yaml")
        run_py(
            project_root,
            str(evx_stage5),
            "--evx-root", ".evx",
            "--consumed-ledger", ".idea-ledger/consumed_ideas.yaml",
            "--verbose",
        )
        run_py(project_root, str(scripts / "evx_finalize.py"), "--evx-root", ".evx", "--project-root", ".")
        actions.append("5_evx: emitted ledger_filtered" if force_evx else "5_evx: emitted_missing ledger_filtered")
    else:
        actions.append("5_evx: reused .evx/latest")

    return actions


def load_chain(project_root: Path) -> dict[str, Any]:
    evx_manifest = read_yaml(project_root / ".evx" / "latest" / "manifest.yaml")
    cix_manifest = read_yaml(project_root / ".cix" / "latest" / "manifest.yaml")
    idx_manifest = read_yaml(project_root / ".idx" / "latest" / "manifest.yaml")
    tcx_manifest = read_yaml(project_root / ".tcx" / "latest" / "manifest.yaml")
    stage6 = read_yaml(project_root / ".evx" / "latest" / "stage6_final.yaml")
    final_1 = stage6.get("final_1") or stage6.get("consensus_winner") or {}
    consensus = stage6.get("consensus_winner") or final_1
    innovation = stage6.get("innovation_winner") or final_1
    source_chain = evx_manifest.get("source_chain", {})

    return {
        "tcx_round_id": source_chain.get("tcx") or tcx_manifest.get("round_id"),
        "idx_round_id": source_chain.get("idx") or idx_manifest.get("round_id"),
        "cix_round_id": source_chain.get("cix") or cix_manifest.get("round", {}).get("id"),
        "evx_round_id": evx_manifest.get("round_id"),
        "source_chain": source_chain,
        "final_idea": final_1,
        "consensus_winner": consensus,
        "innovation_winner": innovation,
        "winners_identical": consensus.get("id") == innovation.get("id"),
        "cix_environment": cix_manifest.get("environment", {}),
        "evx_quality": evx_manifest.get("quality"),
        "evx_stage7": evx_manifest.get("stage7", {}),
    }


def verify_required(project_root: Path) -> list[dict[str, Any]]:
    checks = [
        ("sdx_catalog", ".sdx/catalog/index.yaml"),
        ("tcx_manifest", ".tcx/latest/manifest.yaml"),
        ("idx_manifest", ".idx/latest/manifest.yaml"),
        ("idx_traced", ".idx/latest/insight_layered_traced.yaml"),
        ("cix_manifest", ".cix/latest/manifest.yaml"),
        ("cix_idea_pool", ".cix/latest/idea_pool.yaml"),
        ("evx_manifest", ".evx/latest/manifest.yaml"),
        ("evx_final_idea", ".evx/latest/final_idea.md"),
        ("pgf_personas", "skills/pgf/discovery/personas.json"),
    ]
    results = []
    for name, rel in checks:
        path = project_root / rel
        results.append(
            {
                "name": name,
                "path": rel,
                "status": "PASS" if path.exists() else "FAIL",
                "sha16": sha16(path),
            }
        )
    return results


def resolve_idea_override(
    project_root: Path,
    idea_id: str,
    idea_title: str | None = None,
) -> dict[str, Any]:
    """Resolve an explicit --idea-id against the current CIX idea pool.

    The EVX stage6 final_1 is round-fixed, so recording any idea other than the
    consensus winner needs an explicit override. The id must exist in
    .cix/latest/idea_pool.yaml unless --idea-title is supplied as an escape hatch.
    """
    pool = read_yaml(project_root / ".cix" / "latest" / "idea_pool.yaml")
    pool_ideas = (pool.get("innovation") or {}).get("ideas") or pool.get("ideas") or []
    match = next((i for i in pool_ideas if i.get("id") == idea_id), None)
    if match is None and not idea_title:
        raise SystemExit(
            f"--idea-id {idea_id} not found in .cix/latest/idea_pool.yaml; "
            "pass --idea-title to record it anyway"
        )
    title = idea_title or (match or {}).get("title", "")
    return {"id": idea_id, "title": title}


def append_consumed_idea(
    project_root: Path,
    chain: dict[str, Any],
    project_name: str,
    project_path: str,
    repo_url: str,
    aliases: list[str] | None = None,
    semantic_family: str | None = None,
    final_idea_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ledger_path = project_root / ".idea-ledger" / "consumed_ideas.yaml"
    ledger = read_yaml(ledger_path) if ledger_path.exists() else {}
    ideas = ledger.setdefault("consumed_ideas", [])
    final_idea = final_idea_override or chain["final_idea"]
    idea_id = final_idea.get("id")
    title = final_idea.get("title", "")
    normalized = normalize_title(title)
    aliases = aliases or [project_name]
    semantic_family = semantic_family or semantic_family_from_title(title)

    idea_cix = (chain.get("source_chain") or {}).get("cix")
    for item in ideas:
        # idea_id (IDEA-NNN) is round-local — each CIX round re-numbers from IDEA-001.
        # Only treat an idea_id match as the same idea when both come from the SAME CIX
        # round; otherwise rely on normalized_title (prevents cross-round id collisions).
        item_cix = (item.get("source_chain") or {}).get("cix")
        id_match = bool(idea_id and item.get("idea_id") == idea_id and idea_cix and item_cix == idea_cix)
        if id_match or item.get("normalized_title") == normalized:
            item.setdefault("implementations", [])
            if not any(i.get("repo_url") == repo_url for i in item["implementations"]):
                item["implementations"].append(
                    {"project_name": project_name, "project_path": project_path, "repo_url": repo_url}
                )
            write_yaml(ledger_path, ledger)
            return {"action": "already_present", "path": str(ledger_path), "idea_id": idea_id}

    ideas.append(
        {
            "idea_id": idea_id,
            "title": title,
            "normalized_title": normalized,
            "aliases": aliases,
            "semantic_family": semantic_family,
            "source_chain": chain["source_chain"],
            "consumed_at_utc": utc_now(),
            "implementations": [
                {"project_name": project_name, "project_path": project_path, "repo_url": repo_url}
            ],
            "reuse_policy": "exclude_same_or_derivative",
        }
    )
    write_yaml(ledger_path, ledger)
    return {"action": "appended", "path": str(ledger_path), "idea_id": idea_id}


def check_consumed_idea(project_root: Path, chain: dict[str, Any]) -> dict[str, Any]:
    ledger_path = project_root / ".idea-ledger" / "consumed_ideas.yaml"
    ledger = read_yaml(ledger_path) if ledger_path.exists() else {}
    ideas = ledger.get("consumed_ideas", []) or []
    final_idea = chain["final_idea"]
    idea_id = final_idea.get("id")
    idea_cix = (chain.get("source_chain") or {}).get("cix")
    title = final_idea.get("title", "")
    normalized = normalize_title(title)
    family = semantic_family_from_title(title)

    for item in ideas:
        item_cix = (item.get("source_chain") or {}).get("cix")
        aliases = {normalize_title(str(alias)) for alias in item.get("aliases", [])}
        # idea_id (IDEA-NNN) is round-local; only a same-CIX-round id match counts as consumed
        # (otherwise rely on the semantic matches below). Mirrors stage5_eval / append_consumed_idea.
        if idea_id and idea_id == item.get("idea_id") and idea_cix and item_cix and idea_cix == item_cix:
            return {"action": "checked_final_already_consumed", "path": str(ledger_path), "idea_id": idea_id}
        if normalized and normalized == item.get("normalized_title"):
            return {"action": "checked_final_already_consumed", "path": str(ledger_path), "idea_id": idea_id}
        if normalized in aliases:
            return {"action": "checked_final_already_consumed", "path": str(ledger_path), "idea_id": idea_id}
        if family and family == item.get("semantic_family"):
            return {"action": "checked_final_already_consumed", "path": str(ledger_path), "idea_id": idea_id}

    return {"action": "checked_not_recorded", "path": str(ledger_path), "idea_id": idea_id}


def build_status(
    run_id: str,
    mode: str,
    start_from: str,
    started_at: str,
    completed_at: str,
    actions: list[str],
    checks: list[dict[str, Any]],
    chain: dict[str, Any],
    ledger_result: dict[str, Any],
) -> dict[str, Any]:
    cross_model = chain["cix_environment"].get("cross_model_capability", "unknown")
    capability = "available" if cross_model.startswith("available") else cross_model
    stages = {}
    for stage in STAGES:
        if stage == "1_sdx":
            stages[stage] = "skipped_reused"
        elif stage_should_run(start_from, stage) or stage in {"0_init", "6_wrapup"}:
            stages[stage] = "completed"
        else:
            stages[stage] = "skipped_reused"
    stages["1_sdx"] = "skipped_reused"
    return {
        "run_id": run_id,
        "aox_version": AOX_VERSION,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": None,
        "mode": mode,
        "args": {"start_from": start_from, "run_id_to_resume": None, "config_path": None, "dry_run": False},
        "environment_capability": {
            "cross_model_baseline_for_cix": capability,
            "file_io": "available",
            "pgf_personas_json_access": "available"
            if any(c["name"] == "pgf_personas" and c["status"] == "PASS" for c in checks)
            else "unavailable",
            "main_model_class": "Codex",
            "probe_timestamp": started_at,
            "basis": chain["cix_environment"].get("capability_basis"),
        },
        "handoff_mode": False,
        "last_stage_completable": None,
        "blocked_reasons": [],
        "current_stage": "6_wrapup",
        "stages": stages,
        "stage_timestamps": {
            "0_init": {"started": started_at, "completed": started_at},
            "1_sdx": {"started": started_at, "completed": started_at, "action": "skip_reuse"},
            "2_tcx": {"started": started_at, "completed": started_at, "action": actions[0]},
            "3_idx": {"started": started_at, "completed": started_at, "action": actions[1]},
            "4_cix": {"started": started_at, "completed": started_at, "action": actions[2]},
            "5_evx": {"started": started_at, "completed": started_at, "action": actions[3]},
            "6_wrapup": {"started": started_at, "completed": completed_at},
        },
        "sub_round_ids": {
            "tcx_round_id": chain["tcx_round_id"],
            "idx_round_id": chain["idx_round_id"],
            "cix_round_id": chain["cix_round_id"],
            "evx_round_id": chain["evx_round_id"],
        },
        "errors": [],
        "homogenization": {
            "triggered_at_start": False,
            "measured_at_end": completed_at,
            "metrics": {"status": "not_implemented_in_local_runner"},
            "recommendation": "no_action",
        },
        "kpis": {
            "novelty": None,
            "diversity": None,
            "sustained_innovation": None,
            "surprise_pass_rate": None,
            "post_hoc_yield": None,
            "duration_seconds_byproduct": None,
            "autonomous_execution_rate_byproduct": None,
            "basis": "KPI embedding/baseline metrics require a future AOX measurement module.",
        },
        "outputs": {
            "sdx_catalog_index": ".sdx/catalog/index.yaml",
            "sdx_catalog_root": ".sdx/catalog",
            "tcx_latest": ".tcx/latest/",
            "idx_latest": ".idx/latest/insight_layered_traced.yaml",
            "cix_latest": ".cix/latest/idea_pool.yaml",
            "evx_latest": ".evx/latest/",
            "final_idea": ".evx/latest/final_idea.md",
            "round_chain": chain["source_chain"],
            "consensus_winner_id": chain["consensus_winner"].get("id"),
            "innovation_winner_id": chain["innovation_winner"].get("id"),
            "winners_identical": chain["winners_identical"],
        },
        "quality": {
            "required_checks": checks,
            "evx_quality": chain["evx_quality"],
            "evx_stage7": chain["evx_stage7"],
            "consumed_ledger": ledger_result,
            "verdict": "passed" if all(c["status"] == "PASS" for c in checks) else "failed",
        },
    }


def build_summary(run_id: str, status: dict[str, Any], chain: dict[str, Any]) -> str:
    final = chain["final_idea"]
    source_chain = chain["source_chain"]
    topics = status["sub_round_ids"]
    return f"""# AOX Run Summary

**Run ID**: `{run_id}`
**AOX Version**: `{AOX_VERSION}`
**Mode**: `{status["mode"]}`
**Start From**: `{status["args"]["start_from"]}`
**Status**: `completed`

## Sub-skill Round IDs

- TCX round: `{topics["tcx_round_id"]}`
- IDX round: `{topics["idx_round_id"]}`
- CIX round: `{topics["cix_round_id"]}`
- EVX round: `{topics["evx_round_id"]}`

## Environment Capability

- cross_model_baseline_for_cix: `{status["environment_capability"]["cross_model_baseline_for_cix"]}`
- main_model_class: `Codex`
- basis: `{status["environment_capability"].get("basis")}`

## Stage Status

| Stage | Status | Action |
|---|---|---|
| 0_init | {status["stages"]["0_init"]} | capability + path checks |
| 1_sdx | {status["stages"]["1_sdx"]} | `.sdx/catalog/index.yaml` |
| 2_tcx | {status["stages"]["2_tcx"]} | `{status["stage_timestamps"]["2_tcx"]["action"]}` |
| 3_idx | {status["stages"]["3_idx"]} | `{status["stage_timestamps"]["3_idx"]["action"]}` |
| 4_cix | {status["stages"]["4_cix"]} | `{status["stage_timestamps"]["4_cix"]["action"]}` |
| 5_evx | {status["stages"]["5_evx"]} | `{status["stage_timestamps"]["5_evx"]["action"]}` |
| 6_wrapup | {status["stages"]["6_wrapup"]} | status, summary, consumed ledger |

## Final Idea

- ID: `{final.get("id")}`
- Title: `{final.get("title")}`
- Votes: `{final.get("votes")}`
- Mean persona score: `{final.get("mean_persona_score")}`
- Winners identical: `{status["outputs"]["winners_identical"]}`

## Round Chain

```yaml
{yaml.safe_dump(source_chain, allow_unicode=True, sort_keys=False).strip()}
```

## Outputs

- Status: `.aox/{run_id}/status.json`
- EVX ref: `.aox/{run_id}/5_evx/evx_ref.json`
- Summary: `.aox/{run_id}/summary.md`
- Final idea: `.evx/latest/final_idea.md`
- Consumed ledger: `.idea-ledger/consumed_ideas.yaml`

## Notes

- Homogenization embedding metrics are not implemented in this local runner.
- This runner composes official latest outputs and records an honest AOX state.
"""


def sync_latest(aox_root: Path, run_dir: Path) -> None:
    latest = aox_root / "latest"
    if latest.exists():
        shutil.rmtree(latest)
    latest.mkdir(parents=True)
    for name in ["status.json", "summary.md"]:
        shutil.copy2(run_dir / name, latest / name)
    if (run_dir / "5_evx" / "evx_ref.json").exists():
        (latest / "5_evx").mkdir()
        shutil.copy2(run_dir / "5_evx" / "evx_ref.json", latest / "5_evx" / "evx_ref.json")


def update_index(aox_root: Path, run_id: str, status: dict[str, Any]) -> None:
    index_path = aox_root / "index.yaml"
    index = read_yaml(index_path) if index_path.exists() else {"aox_output": {"version": AOX_VERSION, "runs": []}}
    out = index.setdefault("aox_output", {})
    runs = out.setdefault("runs", [])
    runs = [r for r in runs if r.get("id") != run_id]
    runs.insert(
        0,
        {
            "id": run_id,
            "path": run_id,
            "at": status["completed_at"],
            "mode": status["mode"],
            "quality": status["quality"]["verdict"],
            "final_idea_id": status["outputs"]["consensus_winner_id"],
            "evx_round_id": status["sub_round_ids"]["evx_round_id"],
        },
    )
    out["version"] = AOX_VERSION
    out["generated_at"] = utc_now()
    out["latest_run_id"] = run_id
    out["latest_run_path"] = run_id
    out["runs"] = runs
    write_yaml(index_path, index)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run AOX full/wrapup locally.")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--mode", choices=["full", "wrapup", "dry-run"], default="full")
    ap.add_argument("--start-from", default=None,
                    help="Stage alias to rerun from: sdx, tcx, idx, cix, evx, wrapup")
    ap.add_argument("--project-name", default="AgentPACT")
    ap.add_argument("--project-path", default="pact")
    ap.add_argument("--repo-url", default="https://github.com/sadpig70/pact")
    ap.add_argument("--aliases", default=None,
                    help="Comma-separated aliases when --record-consumed is used")
    ap.add_argument("--semantic-family", default=None,
                    help="Semantic family override when --record-consumed is used")
    ap.add_argument("--record-consumed", action="store_true",
                    help="Append final idea to consumed ledger after concrete project creation")
    ap.add_argument("--idea-id", default=None,
                    help="Override the recorded idea id (e.g. IDEA-020) when --record-consumed is used; "
                         "must exist in .cix/latest/idea_pool.yaml unless --idea-title is given")
    ap.add_argument("--idea-title", default=None,
                    help="Idea title override; required only when --idea-id is absent from the current pool")
    ns = ap.parse_args()

    project_root = Path(ns.project_root).resolve()
    aox_root = project_root / ".aox"
    aox_root.mkdir(parents=True, exist_ok=True)
    start_from = normalize_start_from(ns.start_from)
    if ns.mode == "wrapup" and ns.start_from is None:
        start_from = "6_wrapup"

    if ns.mode == "dry-run":
        plan = {
            "mode": "dry-run",
            "start_from": start_from,
            "will_check": [".sdx/catalog/index.yaml", ".tcx/latest/", ".idx/latest/", ".cix/latest/", ".evx/latest/"],
            "will_emit": [".aox/{run_id}/status.json", ".aox/{run_id}/summary.md"],
            "ledger_policy": "read before EVX selection; append only with --record-consumed",
        }
        write_yaml(aox_root / "execution_plan.yaml", plan)
        print("[aox] dry-run plan written: .aox/execution_plan.yaml")
        return 0

    started = utc_now()
    actions = ensure_latest_outputs(project_root, run_full=(ns.mode == "full"), start_from=start_from)
    checks = verify_required(project_root)
    if any(c["status"] != "PASS" for c in checks):
        missing = [c["path"] for c in checks if c["status"] != "PASS"]
        raise SystemExit(f"AOX required checks failed: {missing}")

    chain = load_chain(project_root)
    if ns.record_consumed:
        aliases = [a.strip() for a in ns.aliases.split(",") if a.strip()] if ns.aliases else [ns.project_name]
        final_idea_override = resolve_idea_override(project_root, ns.idea_id, ns.idea_title) if ns.idea_id else None
        ledger_result = append_consumed_idea(
            project_root,
            chain,
            ns.project_name,
            ns.project_path,
            ns.repo_url,
            aliases=aliases,
            semantic_family=ns.semantic_family,
            final_idea_override=final_idea_override,
        )
    else:
        ledger_result = check_consumed_idea(project_root, chain)
    run_id = next_round_id(aox_root)
    run_dir = aox_root / run_id
    for sub in ["0_init", "1_sdx", "2_tcx", "3_idx", "4_cix", "5_evx", "6_wrapup", "logs"]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    completed = utc_now()
    status = build_status(run_id, ns.mode, start_from, started, completed, actions, checks, chain, ledger_result)

    write_json(run_dir / "status.json", status)
    write_json(
        run_dir / "1_sdx" / "catalog_ref.json",
        {"catalog_index": ".sdx/catalog/index.yaml", "catalog_root": ".sdx/catalog", "action": "skip_reuse"},
    )
    write_json(run_dir / "5_evx" / "evx_ref.json", {"evx_latest": ".evx/latest/", **status["sub_round_ids"]})
    (run_dir / "summary.md").write_text(build_summary(run_id, status, chain), encoding="utf-8")
    sync_latest(aox_root, run_dir)
    update_index(aox_root, run_id, status)

    print(f"[aox] completed {run_id}")
    print(f"[aox] summary: {run_dir / 'summary.md'}")
    print(f"[aox] consumed ledger: {ledger_result['path']} ({ledger_result['action']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
