#!/usr/bin/env python3
"""Deterministic two-layer router for HELIX Condense v0.8.

Layer 1 reads machine evidence from probe results. Layer 2 maps covered machines to
existing platform kernels, then to proven platform pack evidence. Human
`kernel_machines` labels remain the kernel coverage registry, but incoming claims are
routed from probe-positive machines, not cluster names.

Pure stdlib, no clock/network/AI.
"""

try:
    from .helix_machine_probes import normalize_machine_id
except ImportError:  # direct script import from repo root
    from core.helix_machine_probes import normalize_machine_id

DEFAULT_ROUTER_POLICY = {
    "min_cluster_for_condense": 5,
}


def _clean_machine(value):
    machine = normalize_machine_id(value)
    return machine if machine else ""


def platform_machine_sets(layered_corpus):
    """Return {platform_name: set(machine ids)} from layer1 platform coverage."""
    out = {}
    for platform in layered_corpus.get("layer1_platforms", []):
        name = platform.get("name") or platform.get("cluster")
        if not name:
            continue
        machines = {_clean_machine(m) for m in platform.get("kernel_machines", [])}
        out[str(name)] = {m for m in machines if m}
    return out


def platform_machine_index(layered_corpus):
    """Return {machine: [platform names]} for deterministic coverage lookup."""
    index = {}
    for platform, machines in platform_machine_sets(layered_corpus).items():
        for machine in machines:
            index.setdefault(machine, []).append(platform)
    return {machine: sorted(platforms) for machine, platforms in sorted(index.items())}


def pack_machine_index(layered_corpus, rows):
    """Return {machine: [platform names]} for probe-positive pack evidence.

    This does not promote pack behavior into `kernel_machines`. It only says that a
    machine has already been observed inside a platform's pack ecosystem, so similar
    future claims can be routed as pack growth instead of a new platform kernel.
    """
    known_platforms = set(platform_machine_sets(layered_corpus))
    index = {}
    for row in rows:
        platform = row.get("platform")
        if platform not in known_platforms:
            continue
        for machine in machines_from_probe_row(row):
            index.setdefault(machine, set()).add(platform)
    return {machine: sorted(platforms) for machine, platforms in sorted(index.items())}


def machines_from_probe_row(row):
    """Extract probe-positive machine ids from an agreement row or claim row.

    Preferred source is `matched` because that is the probe-confirmed evidence. If a
    row only has raw `results`, machines with `holds == True` are used. The explicit
    `machines` fallback is for tests and hand-authored normalized claims.
    """
    if row.get("matched") is not None:
        values = row.get("matched") or []
    elif isinstance(row.get("results"), dict):
        values = [m for m, result in row["results"].items()
                  if isinstance(result, dict) and result.get("holds")]
    else:
        values = row.get("machines") or []
    return sorted({_clean_machine(m) for m in values if _clean_machine(m)})


def _platforms_covering_all(platform_sets, machines):
    wanted = set(machines)
    return sorted(platform for platform, covered in platform_sets.items() if wanted <= covered)


def _per_machine_routes(index, machines):
    return {machine: index.get(machine, []) for machine in machines}


def route_machine_claim(layered_corpus, claim, policy=None, pack_index=None):
    """Route one probe-confirmed machine claim.

    Returns a deterministic decision:
    - BUILD_ON_PLATFORM: one existing platform covers all positive machines
    - SPLIT_BUILD_ON_PLATFORM: machines are covered, but not by one platform
    - CONDENSE: uncovered machine evidence reaches the cluster threshold
    - DEFER: not enough evidence or no probe-positive machine
    """
    P = {**DEFAULT_ROUTER_POLICY, **(policy or {})}
    machines = machines_from_probe_row(claim)
    platform_sets = platform_machine_sets(layered_corpus)
    index = platform_machine_index(layered_corpus)
    per_machine = _per_machine_routes(index, machines)
    covered = sorted(m for m, platforms in per_machine.items() if platforms)
    uncovered = sorted(set(machines) - set(covered))
    substantiated_count = int(claim.get("substantiated_count", 1) or 0)

    out = {
        "id": claim.get("id", ""),
        "machines": machines,
        "covered_machines": covered,
        "uncovered_machines": uncovered,
        "per_machine_platforms": per_machine,
    }
    if not machines:
        return {**out, "action": "DEFER", "why": "no probe-positive machine"}

    covering_all = _platforms_covering_all(platform_sets, machines)
    if covering_all:
        return {**out, "action": "BUILD_ON_PLATFORM", "platform": covering_all[0],
                "candidate_platforms": covering_all,
                "why": "probe-positive machines covered by existing platform kernel"}

    if not uncovered and covered:
        return {**out, "action": "SPLIT_BUILD_ON_PLATFORM",
                "routes": {m: per_machine[m][0] for m in machines},
                "why": "probe-positive machines covered across multiple platform kernels"}

    pack_index = pack_index or {}
    pack_routes = _per_machine_routes(pack_index, uncovered)
    pack_covered = sorted(m for m, platforms in pack_routes.items() if platforms)
    pack_uncovered = sorted(set(uncovered) - set(pack_covered))
    if pack_covered and not pack_uncovered:
        platforms = sorted({pack_routes[m][0] for m in pack_covered})
        if len(platforms) == 1:
            return {**out, "action": "BUILD_ON_PLATFORM", "platform": platforms[0],
                    "coverage_scope": "pack_evidence",
                    "per_machine_pack_platforms": pack_routes,
                    "why": "probe-positive machine covered by existing platform pack evidence"}
        return {**out, "action": "SPLIT_BUILD_ON_PLATFORM",
                "coverage_scope": "pack_evidence",
                "routes": {m: pack_routes[m][0] for m in pack_covered},
                "per_machine_pack_platforms": pack_routes,
                "why": "probe-positive machines covered across multiple platform pack ecosystems"}

    if substantiated_count >= int(P["min_cluster_for_condense"]):
        return {**out, "action": "CONDENSE",
                "why": "probe-positive machine not covered by existing platform kernels"}

    return {**out, "action": "DEFER",
            "why": "uncovered machine evidence below condense threshold"}


def route_probe_rows(layered_corpus, rows, policy=None):
    """Route agreement rows from `core.helix_machine_probes.agreement_report`."""
    pack_index = pack_machine_index(layered_corpus, rows)
    decisions = [route_machine_claim(layered_corpus, row, policy, pack_index) for row in rows]
    summary = {}
    for decision in decisions:
        action = decision["action"]
        summary[action] = summary.get(action, 0) + 1
    return {"decisions": decisions, "summary": dict(sorted(summary.items()))}
