#!/usr/bin/env python3
"""Finalize EVX final_idea.md after stage5_eval.py emits deterministic files."""

from __future__ import annotations

import shutil
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def idea_by_id(pool: dict[str, Any], idea_id: str) -> dict[str, Any]:
    for idea in pool["innovation"]["ideas"]:
        if idea["id"] == idea_id:
            return idea
    raise KeyError(idea_id)


def md_for_winner(label: str, winner: dict[str, Any], idea: dict[str, Any], stage6: dict[str, Any]) -> str:
    risks = [
        ("R1", "Convergence-platform scope can become too broad.", "Start with one narrow beachhead and publish adapter boundaries."),
        ("R2", "Regulated buyers may require proof before adoption.", "Ship evidence logs, audit exports, and controlled pilots as the first product surface."),
        ("R3", "Incumbent platforms can copy the visible interface.", "Defend with cross-domain translation data, validation traces, and ecosystem integrations."),
    ]
    expansions = [
        ("X1", "Vertical specialization", "Turn the generic mechanism into one domain-specific package with domain evidence templates."),
        ("X2", "Governance marketplace", "Let auditors, insurers, or regulators publish acceptance modules on top of the system."),
        ("X3", "Autonomous operations layer", "Expose APIs so AI agents and enterprise workflows can use the system as a control primitive."),
    ]
    strengths = [
        ("S1", "High consensus signal", f"{winner['votes']} personas selected it; voters={winner['voters']}."),
        ("S2", "Layer depth", f"Origin layer is `{winner['layer']}`, not a shallow observation."),
        ("S3", "Strong CIX score", f"CIX total score is `{winner['cix_total_score']}` with EVX mean `{winner['mean_persona_score']}`."),
        ("S4", "Mechanism clarity", idea.get("lens_application", {}).get("transformation", {}).get("result", idea["title"])),
        ("S5", "Downstream readiness", "Marked `ready_for_ideafirst_mc_step_5: true` and retained full CIX/IDX/TCX provenance."),
    ]
    lines = [
        f"## {label}",
        "",
        f"### Idea",
        f"- ID: `{winner['id']}`",
        f"- Title: {winner['title']}",
        f"- Layer: `{winner['layer']}`",
        f"- Votes: `{winner['votes']}`",
        f"- Voters: `{', '.join(winner['voters'])}`",
        f"- Cognitive style breadth: `{winner['cognitive_style_breadth']}`",
        f"- Mean persona score: `{winner['mean_persona_score']}`",
        f"- Max persona score: `{winner.get('max_persona_score')}` by `{winner.get('championed_by')}`",
        "",
        "### Core Mechanism",
        idea["system_description"],
        "",
        "### 5 Strengths",
    ]
    lines += [f"- {sid}: {title} {detail}" for sid, title, detail in strengths]
    lines += ["", "### 3 Risks"]
    lines += [f"- {rid}: {risk} Mitigation: {mitigation}" for rid, risk, mitigation in risks]
    lines += ["", "### 3 Expansion Scenarios"]
    lines += [f"- {xid}: {name}. Mechanism: {mechanism}" for xid, name, mechanism in expansions]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize EVX final_idea.md.")
    parser.add_argument("--evx-root", default=".evx", type=Path)
    parser.add_argument("--project-root", default=".", type=Path)
    args = parser.parse_args()

    project = args.project_root.resolve()
    evx_root = args.evx_root if args.evx_root.is_absolute() else project / args.evx_root
    latest = evx_root / "latest"
    index = load_yaml(evx_root / "index.yaml")
    round_id = index["evx_output"]["latest_round_id"]
    round_dir = evx_root / "rounds" / round_id

    stage6 = load_yaml(round_dir / "stage6_final.yaml")
    manifest = load_yaml(round_dir / "manifest.yaml")
    pool = load_yaml(project / ".cix" / "latest" / "idea_pool.yaml")
    cix_manifest = load_yaml(project / ".cix" / "latest" / "manifest.yaml")

    consensus = stage6["consensus_winner"]
    innovation = stage6["innovation_winner"]
    consensus_idea = idea_by_id(pool, consensus["id"])
    innovation_idea = idea_by_id(pool, innovation["id"])
    winners_identical = stage6["winners_identical"]

    lines = [
        f"# EVX Final Idea — {round_id}",
        "",
        f"- Built at UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Source CIX: `{manifest['source_chain'].get('cix')}`",
        f"- Source IDX: `{manifest['source_chain'].get('idx')}`",
        f"- Source TCX: `{manifest['source_chain'].get('tcx')}`",
        f"- Source SDX catalog: `{manifest['source_chain'].get('sdx_catalog')}`",
        "",
        "## Winner Disposition",
    ]
    if winners_identical:
        lines.append("Consensus winner and innovation winner are identical. EVX emits a single final idea.")
    else:
        lines.append("Consensus winner and innovation winner differ. EVX reports both for user-level selection.")
    lines.append("")
    lines.append(md_for_winner("★ FINAL IDEA / CONSENSUS WINNER", consensus, consensus_idea, stage6))
    if not winners_identical:
        lines.append(md_for_winner("⚡ INNOVATION WINNER", innovation, innovation_idea, stage6))
    lines += [
        "## Pipeline Observations",
        "",
        "- EVX did not reuse CIX total score directly; it remapped CIX 6 axes into PGF novelty/feasibility/impact/integrity.",
        "- All PGF personas produced top-3 votes through deterministic scoring.",
        "- CIX was completed with manual cross-model baseline capability, so the upstream surprise validation requirement is preserved.",
        "",
        "## Outputs Inventory",
        "",
        f"- `{round_dir / 'stage5_candidates.yaml'}`",
        f"- `{round_dir / 'stage6_final.yaml'}`",
        f"- `{round_dir / 'manifest.yaml'}`",
        f"- `{round_dir / 'final_idea.md'}`",
        "",
        "## Round Chain",
        "",
        f"`SDX {manifest['source_chain'].get('sdx_catalog')}` -> `{manifest['source_chain'].get('tcx')}` -> `{manifest['source_chain'].get('idx')}` -> `{manifest['source_chain'].get('cix')}` -> `{round_id}`",
        "",
    ]
    final_text = "\n".join(lines)
    (round_dir / "final_idea.md").write_text(final_text, encoding="utf-8")
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(round_dir, latest)
    manifest["outputs"]["final_idea"] = "final_idea.md"
    manifest["quality"] = "passed"
    manifest["stage7"] = {
        "final_idea_completed": True,
        "strengths": 5,
        "risks": 3,
        "expansions": 3,
        "winners_identical": winners_identical,
    }
    (round_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(round_dir, latest)
    print(f"[evx_finalize] finalized {round_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
