#!/usr/bin/env python3
"""Verify EVX latest output against the latest round directory."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import yaml


REQUIRED_FILES = [
    "stage5_candidates.yaml",
    "stage6_final.yaml",
    "final_idea.md",
    "manifest.yaml",
]

REQUIRED_SECTIONS = [
    "FINAL IDEA",
    "5 Strengths",
    "3 Risks",
    "3 Expansion Scenarios",
    "Round Chain",
]

EXPECTED_PERSONA_COUNT = 14


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ns = ap.parse_args()

    root = Path(ns.project_root).resolve()
    evx_root = root / ".evx"
    index_path = evx_root / "index.yaml"
    if not index_path.exists():
        raise SystemExit(f"missing index: {index_path}")

    index_doc = load_yaml(index_path)
    index = index_doc.get("evx_output", index_doc)
    round_id = index.get("latest_round_id")
    if not round_id:
        raise SystemExit("missing latest_round_id in .evx/index.yaml")

    round_dir = evx_root / "rounds" / round_id
    latest_dir = evx_root / "latest"
    missing = [
        name
        for name in REQUIRED_FILES
        if not (round_dir / name).exists() or not (latest_dir / name).exists()
    ]

    identical = {}
    for name in REQUIRED_FILES:
        round_file = round_dir / name
        latest_file = latest_dir / name
        if round_file.exists() and latest_file.exists():
            identical[name] = sha256(round_file) == sha256(latest_file)

    stage5 = load_yaml(latest_dir / "stage5_candidates.yaml")
    stage6 = load_yaml(latest_dir / "stage6_final.yaml")
    manifest = load_yaml(latest_dir / "manifest.yaml")
    final_text = (latest_dir / "final_idea.md").read_text(encoding="utf-8")

    personas = stage5.get("personas", {})
    final_1 = stage6.get("final_1", {})
    consensus = stage6.get("consensus_winner", {})
    innovation = stage6.get("innovation_winner", {})
    sections_present = {section: section in final_text for section in REQUIRED_SECTIONS}

    report = {
        "verdict": "passed"
        if not missing
        and all(identical.values())
        and len(personas) == EXPECTED_PERSONA_COUNT
        and all(len(data.get("top_3", [])) == 3 for data in personas.values())
        and manifest.get("quality") == "passed"
        and all(sections_present.values())
        else "failed",
        "round_id": round_id,
        "missing": missing,
        "latest_identical": identical,
        "persona_count": len(personas),
        "top3_counts": {pid: len(data.get("top_3", [])) for pid, data in personas.items()},
        "final_1": {
            "id": final_1.get("id"),
            "title": final_1.get("title"),
            "votes": final_1.get("votes"),
            "voters": final_1.get("voters"),
            "mean_persona_score": final_1.get("mean_persona_score"),
        },
        "dual_winner": {
            "consensus_id": consensus.get("id"),
            "innovation_id": innovation.get("id"),
            "identical": consensus.get("id") == innovation.get("id"),
        },
        "manifest_quality": manifest.get("quality"),
        "stage7": manifest.get("stage7"),
        "source_chain": manifest.get("source_chain"),
        "sections_present": sections_present,
    }
    print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False))
    return 0 if report["verdict"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
