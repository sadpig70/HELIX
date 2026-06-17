#!/usr/bin/env python3
"""TCX v1.5 — deterministic domain ↔ persona assignment using PGF discovery personas.

Implements TCX_POLICY.persona_assignment from SKILL.md:
  - Loads PGF personas.json (v1.0) as single source of truth
  - Loads TCX default.yaml or --domains override
  - Applies domain_lens_affinity matching to assign primary + cross-check personas
  - Guarantees every domain has >= cross_check_min_per_domain personas
  - Caps each persona at max_domains_per_persona
  - Prefers cross-check pair with different cognitive_style

Default invocation (from project root):

    python skills/tcx/scripts/assign_personas.py
    python skills/tcx/scripts/assign_personas.py --output sampling_log_personas.yaml
    python skills/tcx/scripts/assign_personas.py --personas skills/pgf/discovery/personas.json --domains skills/tcx/domain_sets/default.yaml
    python skills/tcx/scripts/assign_personas.py --use-canonical  # default mapping (no algorithmic recompute)

Output: yaml summary of persona_assignment (mirror of TCX_POLICY.persona_assignment.canonical_mapping).
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[assign_personas] PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# Default canonical mapping (mirrors SKILL.md#TCX_POLICY.persona_assignment.canonical_mapping)
# Keyed by 14-domain ID with "DNN_Name" form. Aliases (DNN-only) auto-resolved below.
# v1.6 — P1-P8 pairs preserved (proven cross-check); P9-P14 added where their lens fits.
CANONICAL_MAPPING_FULL = {
    "D01_AI":             ["P5", "P8"],
    "D02_Quantum":        ["P1", "P4"],
    "D03_Robotics":       ["P1", "P5"],
    "D04_SynBio":         ["P4", "P8"],
    "D05_Space":          ["P1", "P7"],
    "D06_Energy":         ["P7", "P3", "P12"],      # +P12 ecology (energy ↔ planetary limits)
    "D07_Semiconductors": ["P2", "P5"],
    "D08_Climate":        ["P6", "P4", "P12"],      # +P12 ecology
    "D09_Healthcare":     ["P4", "P6", "P9", "P10"],  # +P9 ethics, +P10 embodied UX
    "D10_Cyber":          ["P3", "P7", "P11"],      # +P11 adversarial robustness
    "D11_Manufacturing":  ["P5", "P2"],
    "D12_AgriFood":       ["P6", "P8", "P12"],      # +P12 ecology
    "D13_Geopolitics":    ["P3", "P2", "P13"],      # +P13 historical cycle
    "D14_FinTech":        ["P2", "P3", "P14"],      # +P14 mechanism designer
}
# Build alias-aware mapping (DNN → personas) by extracting numeric prefix
CANONICAL_MAPPING = {}
for full_id, personas in CANONICAL_MAPPING_FULL.items():
    CANONICAL_MAPPING[full_id] = personas
    short_id = full_id.split("_")[0]   # "D01_AI" → "D01"
    CANONICAL_MAPPING[short_id] = personas

# domain_lens affinity (mirrors SKILL.md#TCX_POLICY.persona_assignment.domain_lens_affinity)
# v1.6 — new lenses (ecology/ethics/human_experience/security/history/economics) added
# to domains where they fit, so algorithmic mode also engages P9-P14.
DOMAIN_LENS_AFFINITY_FULL = {
    "D01_AI":             ["technology", "science_technology"],
    "D02_Quantum":        ["technology", "science"],
    "D03_Robotics":       ["technology"],
    "D04_SynBio":         ["science", "science_technology"],
    "D05_Space":          ["technology", "market"],
    "D06_Energy":         ["market", "policy", "ecology"],
    "D07_Semiconductors": ["market", "technology"],
    "D08_Climate":        ["society", "science", "ecology"],
    "D09_Healthcare":     ["science", "society", "ethics", "human_experience"],
    "D10_Cyber":          ["policy", "technology", "security"],
    "D11_Manufacturing":  ["technology", "market"],
    "D12_AgriFood":       ["society", "science", "ecology"],
    "D13_Geopolitics":    ["policy", "market", "history"],
    "D14_FinTech":        ["market", "policy", "economics"],
}
DOMAIN_LENS_AFFINITY = {}
for full_id, lenses in DOMAIN_LENS_AFFINITY_FULL.items():
    DOMAIN_LENS_AFFINITY[full_id] = lenses
    DOMAIN_LENS_AFFINITY[full_id.split("_")[0]] = lenses


def load_personas(path: Path):
    if not path.exists():
        print(f"[assign_personas] personas.json not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def load_domain_set(path: Path):
    if not path.exists():
        print(f"[assign_personas] domain set not found: {path}", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def algorithmic_assignment(personas_data, domain_set, policy):
    """Algorithmic domain_lens-based assignment when canonical mapping not applicable."""
    personas = personas_data["personas"]
    cross_min = policy.get("cross_check_min_per_domain", 2)
    max_per = policy.get("max_domains_per_persona", 4)

    result = {}
    load = {p["id"]: 0 for p in personas}

    domains = domain_set["domain_set"]["domains"]
    for d in domains:
        d_id = d.get("id", d.get("name", "UNKNOWN"))
        lens_pref = DOMAIN_LENS_AFFINITY.get(d_id, [])

        def affinity_score(p):
            base = 0
            if p["domain_lens"] in lens_pref:
                base = 2 if lens_pref and p["domain_lens"] == lens_pref[0] else 1
            return (-base, load[p["id"]])  # higher affinity first, then lighter load

        ranked = sorted(personas, key=affinity_score)
        # filter to those still under load cap
        ranked_available = [p for p in ranked if load[p["id"]] < max_per]
        if len(ranked_available) < cross_min:
            print(f"[assign_personas] WARNING: domain {d_id} cannot satisfy cross_check_min={cross_min} "
                  f"under max_domains_per_persona={max_per}", file=sys.stderr)
            ranked_available = ranked  # fallback — ignore cap

        primary = ranked_available[0]
        # Cross-check: prefer different cognitive_style
        cross_check = next(
            (p for p in ranked_available[1:] if p["cognitive_style"] != primary["cognitive_style"]),
            ranked_available[1] if len(ranked_available) > 1 else None
        )

        assigned = [primary["id"]]
        if cross_check:
            assigned.append(cross_check["id"])

        result[d_id] = assigned
        for pid in assigned:
            load[pid] += 1

    return result, load


def validate_assignment(assignment, policy, num_personas=14):
    """Returns list of validation issues; empty list = pass."""
    cross_min = policy.get("cross_check_min_per_domain", 2)
    max_per = policy.get("max_domains_per_persona", 4)
    issues = []
    load = {}
    for d, personas in assignment.items():
        if len(personas) < cross_min:
            issues.append(f"domain {d} has only {len(personas)} personas (min {cross_min})")
        for pid in personas:
            load[pid] = load.get(pid, 0) + 1
    for pid, count in load.items():
        if count > max_per:
            issues.append(f"persona {pid} assigned to {count} domains (max {max_per})")
    return issues, load


def emit_summary(assignment, personas_data, load, source_strategy):
    persona_map = {p["id"]: p for p in personas_data["personas"]}
    summary = {
        "persona_assignment": {
            "source": "skills/pgf/discovery/personas.json",
            "version_pin": personas_data.get("version", "unknown"),
            "strategy": source_strategy,
            "cross_check_min_per_domain": 2,
            "max_domains_per_persona": 4,
            "domains_count": len(assignment),
            "assignments_by_domain": {d: personas for d, personas in assignment.items()},
            "load_balance": dict(sorted(load.items())),
            "by_persona": {
                pid: {
                    "name": persona_map[pid]["name_en"],
                    "cognitive_style": persona_map[pid]["cognitive_style"],
                    "domain_lens": persona_map[pid]["domain_lens"],
                    "time_horizon": persona_map[pid]["time_horizon"],
                    "evaluation_bias": persona_map[pid]["evaluation_bias"],
                    "assigned_domains": [d for d, ps in assignment.items() if pid in ps],
                    "domain_count": load.get(pid, 0),
                }
                for pid in sorted(persona_map.keys())
            },
        }
    }
    return summary


def main():
    ap = argparse.ArgumentParser(description="TCX v1.5 — assign PGF personas to domains.")
    ap.add_argument("--personas", default="skills/pgf/discovery/personas.json",
                    help="path to PGF personas.json")
    ap.add_argument("--domains", default="skills/tcx/domain_sets/default.yaml",
                    help="path to TCX domain set yaml")
    ap.add_argument("--use-canonical", action="store_true",
                    help="Use canonical_mapping (fastest, deterministic) instead of algorithmic")
    ap.add_argument("--output", default=None, help="output yaml path (stdout if omitted)")
    ap.add_argument("--cross-min", type=int, default=2,
                    help="cross_check_min_per_domain (default 2)")
    ap.add_argument("--max-per", type=int, default=4,
                    help="max_domains_per_persona (default 4)")
    args = ap.parse_args()

    personas_data = load_personas(Path(args.personas))
    domain_data = load_domain_set(Path(args.domains))
    policy = {"cross_check_min_per_domain": args.cross_min, "max_domains_per_persona": args.max_per}

    # Determine strategy
    domain_set_name = domain_data.get("domain_set", {}).get("name", "")
    use_canonical = args.use_canonical or domain_set_name == "default_ideafirst_domains"

    if use_canonical:
        # Verify canonical mapping covers all domains in the input set
        domain_ids = [d.get("id", d.get("name")) for d in domain_data["domain_set"]["domains"]]
        missing = [d for d in domain_ids if d not in CANONICAL_MAPPING]
        if missing:
            print(f"[assign_personas] canonical mapping missing domains: {missing}; "
                  f"falling back to algorithmic", file=sys.stderr)
            assignment, load = algorithmic_assignment(personas_data, domain_data, policy)
            strategy = "algorithmic (canonical fallback)"
        else:
            assignment = {d: list(CANONICAL_MAPPING[d]) for d in domain_ids}
            load = {}
            for personas in assignment.values():
                for pid in personas:
                    load[pid] = load.get(pid, 0) + 1
            strategy = "canonical"
    else:
        assignment, load = algorithmic_assignment(personas_data, domain_data, policy)
        strategy = "algorithmic (domain_lens_aware)"

    # Validate
    issues, _ = validate_assignment(assignment, policy)
    if issues:
        print("[assign_personas] VALIDATION ISSUES:", file=sys.stderr)
        for iss in issues:
            print(f"  - {iss}", file=sys.stderr)

    summary = emit_summary(assignment, personas_data, load, strategy)
    out_yaml = yaml.safe_dump(summary, sort_keys=False, allow_unicode=True)

    if args.output:
        Path(args.output).write_text(out_yaml, encoding="utf-8")
        print(f"[assign_personas] wrote: {args.output}")
    else:
        print(out_yaml)

    print(f"[assign_personas] strategy={strategy}, domains={len(assignment)}, "
          f"load_balance={dict(sorted(load.items()))}, issues={len(issues)}",
          file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
