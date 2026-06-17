#!/usr/bin/env python3
"""EVX preflight checker for IdeaFirst."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def record(results: list[dict[str, Any]], check: str, status: str, message: str, **extra: Any) -> None:
    results.append({"check": check, "status": status, "message": message, **extra})


def verdict(results: list[dict[str, Any]]) -> str:
    if any(r["status"] == "FAIL" for r in results):
        return "blocked"
    if any(r["status"] == "WARN" for r in results):
        return "ready_with_warnings"
    return "ready"


def main() -> int:
    project = Path.cwd()
    results: list[dict[str, Any]] = []
    idea_pool = project / ".cix" / "latest" / "idea_pool.yaml"
    cix_manifest = project / ".cix" / "latest" / "manifest.yaml"
    personas = project / "skills" / "pgf" / "discovery" / "personas.json"
    stage5 = project / "skills" / "evx" / "scripts" / "stage5_eval.py"

    for label, path in {
        "idea_pool": idea_pool,
        "cix_manifest": cix_manifest,
        "personas": personas,
        "stage5_eval": stage5,
    }.items():
        record(results, label, "PASS" if path.is_file() else "FAIL", f"{path} {'exists' if path.is_file() else 'missing'}")

    if idea_pool.is_file():
        try:
            pool = load_yaml(idea_pool)
            ideas = pool["innovation"]["ideas"]
            ready = sum(1 for idea in ideas if idea.get("ready_for_ideafirst_mc_step_5"))
            required_scores = {"novelty", "generativity", "defensibility", "compounding", "surprise", "coherence"}
            missing_scores = [
                idea.get("id")
                for idea in ideas
                if set((idea.get("scores") or {}).keys()) & required_scores != required_scores
            ]
            layer_dist = pool["innovation"].get("layer_distribution_in_top_K", {})
            if len(ideas) == 24:
                record(results, "g1_top_k", "PASS", "CIX idea pool has 24 ideas.")
            else:
                record(results, "g1_top_k", "FAIL", f"CIX idea pool has {len(ideas)} ideas, expected 24.")
            if ready == len(ideas):
                record(results, "ready_flags", "PASS", "All ideas are ready for EVX STEP 5.")
            else:
                record(results, "ready_flags", "FAIL", f"Only {ready}/{len(ideas)} ideas are ready.")
            if not missing_scores:
                record(results, "score_axes", "PASS", "All ideas contain required CIX score axes.")
            else:
                record(results, "score_axes", "FAIL", "Some ideas miss score axes.", ideas=missing_scores)
            if all(layer_dist.get(layer, 0) >= 4 for layer in ("L6_Gap", "L7_Tension", "L9_Counterfactual", "L10_Generative")):
                record(results, "layer_floor", "PASS", "CIX top-K preserves EVX layer floor.")
            else:
                record(results, "layer_floor", "WARN", "CIX top-K layer floor is uneven.", layer_distribution=layer_dist)
        except Exception as exc:
            record(results, "idea_pool_parse", "FAIL", f"Failed to parse idea_pool.yaml: {exc}")

    if cix_manifest.is_file():
        try:
            manifest = load_yaml(cix_manifest)
            status = manifest.get("round", {}).get("status")
            capability = manifest.get("environment", {}).get("cross_model_capability")
            if status == "completed":
                record(results, "cix_status", "PASS", "CIX round status is completed.")
            else:
                record(results, "cix_status", "FAIL", f"CIX round status is {status}.")
            if capability in {"available", "available_manual"}:
                record(results, "cross_model_capability", "PASS", f"CIX cross-model capability is {capability}.")
            else:
                record(results, "cross_model_capability", "WARN", f"CIX cross-model capability is {capability}.")
        except Exception as exc:
            record(results, "cix_manifest_parse", "FAIL", f"Failed to parse CIX manifest: {exc}")

    evx_root = project / ".evx"
    lock = evx_root / ".lock"
    if lock.exists():
        record(results, "evx_lock", "FAIL", f"EVX lock exists: {lock}")
    else:
        record(results, "evx_lock", "PASS", "No EVX lock exists.")
    try:
        evx_root.mkdir(exist_ok=True)
        probe = evx_root / "_preflight_write_probe.tmp"
        probe.write_text("ok", encoding="utf-8")
        ok = probe.read_text(encoding="utf-8").strip() == "ok"
        probe.unlink()
        record(results, "write_probe", "PASS" if ok else "FAIL", ".evx write probe passed." if ok else ".evx write probe mismatch.")
    except Exception as exc:
        record(results, "write_probe", "FAIL", f".evx write probe failed: {exc}")

    if stage5.is_file() and idea_pool.is_file() and personas.is_file():
        proc = subprocess.run(
            [
                sys.executable,
                str(stage5),
                "--ideas",
                str(idea_pool),
                "--personas",
                str(personas),
                "--evx-root",
                str(project / ".evx_preflight_probe"),
                "--round-id",
                "EVX-PREFLIGHT-PROBE",
            ],
            cwd=project,
            text=True,
            capture_output=True,
            timeout=60,
        )
        probe_root = project / ".evx_preflight_probe"
        if probe_root.exists():
            import shutil

            shutil.rmtree(probe_root)
        record(
            results,
            "stage5_probe",
            "PASS" if proc.returncode == 0 else "FAIL",
            "stage5_eval.py probe passed." if proc.returncode == 0 else "stage5_eval.py probe failed.",
            stdout=proc.stdout[-1200:],
            stderr=proc.stderr[-1200:],
        )

    out_dir = project / ".evx" / "preflight"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict(results),
        "results": results,
    }
    (out_dir / "latest_preflight.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# EVX Preflight", "", f"- Verdict: `{payload['verdict']}`", "", "## Checks", ""]
    lines += [f"- `{r['status']}` `{r['check']}` — {r['message']}" for r in results]
    lines.append("")
    (out_dir / "latest_preflight.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[evx_preflight] verdict={payload['verdict']}")
    for r in results:
        print(f"[{r['status']}] {r['check']}: {r['message']}")
    return 1 if payload["verdict"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
