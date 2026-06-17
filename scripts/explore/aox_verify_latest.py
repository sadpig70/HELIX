#!/usr/bin/env python3
"""Verify the latest AOX run artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import yaml


REQUIRED = [
    "status.json",
    "summary.md",
    "5_evx/evx_ref.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ns = ap.parse_args()

    root = Path(ns.project_root).resolve()
    aox = root / ".aox"
    index = load_yaml(aox / "index.yaml").get("aox_output", {})
    run_id = index.get("latest_run_id")
    if not run_id:
        raise SystemExit("missing .aox/index.yaml latest_run_id")

    run_dir = aox / run_id
    latest = aox / "latest"
    missing = [rel for rel in REQUIRED if not (run_dir / rel).exists() or not (latest / rel).exists()]
    identical = {
        rel: sha256(run_dir / rel) == sha256(latest / rel)
        for rel in REQUIRED
        if (run_dir / rel).exists() and (latest / rel).exists()
    }
    status = load_yaml(run_dir / "status.json")
    ledger = root / ".idea-ledger" / "consumed_ideas.yaml"
    final_idea = root / ".evx" / "latest" / "final_idea.md"
    verdict = (
        not missing
        and all(identical.values())
        and status.get("quality", {}).get("verdict") == "passed"
        and ledger.exists()
        and final_idea.exists()
    )
    report = {
        "verdict": "passed" if verdict else "failed",
        "latest_run_id": run_id,
        "missing": missing,
        "latest_identical": identical,
        "status_quality": status.get("quality", {}).get("verdict"),
        "final_idea": status.get("outputs", {}).get("consensus_winner_id"),
        "consumed_ledger_exists": ledger.exists(),
    }
    print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False))
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
