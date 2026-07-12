#!/usr/bin/env python3
"""View-grounded oracle gate for the T1 blind trial retry.

Post-mortem (`_workspace/helix-direction/T1-retry/postmortem.md`) found that
T1's M10/M15 collapse was not the predictor's failure but the evaluation's:
the oracle labeled machines (rate-limiter -> M10, leaderboard -> M15) whose
DECISIVE features were never exposed in the candidate view the predictor
sees. Since a blind trial treats the oracle as ground truth, an over-reaching
oracle scores a correct predictor as "wrong" — oracle quality is the score
ceiling.

This gate closes that hole deterministically. Machine identification stays an
AI judgment (the oracle author), but every claimed machine must be GROUNDED:
for each decisive feature of the machine, the oracle must quote the exact view
text that exhibits it. The gate verifies — with pure substring matching, no
AI, no clock — that (1) every claimed machine is known, (2) every decisive
feature is grounded, and (3) each grounding quote actually appears in the
view. A machine whose feature cannot be quoted from the view cannot be
labeled. This structurally blocks over-reach (the label needs evidence the
view doesn't contain) and the oracle/view asymmetry (grounding is checked
against the view, not the hidden source).

The MACHINE_FEATURES catalog operationalizes each probe's semantics
(core/helix_machine_probes.py) into observable decisive features — this is
also T1-retry requirement (3), the machine adjudication rubric.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import json
import os
import sys

# Each machine -> the decisive observable features an oracle must ground in
# the candidate view before labeling it. Derived from the probe docstrings in
# core/helix_machine_probes.py; a machine is NOT its topic, it is its mechanism.
MACHINE_FEATURES = {
    "M1": ["append-only records", "hash chain over records"],
    "M2": ["discrete severity stages", "max-severity aggregation"],
    "M3": ["predicate check over evidence", "aggregate verdict"],
    "M4": ["provenance verification against an evidence chain"],
    "M5": ["priority ordering", "conflict-free allocation over limited supply"],
    "M6": ["deterministic price or cost output"],
    "M7": ["settlement or netting", "zero-sum buyer/seller legs"],
    "M8": ["survival-days or shortfall aggregation over items"],
    "M9": ["per-candidate scoring", "eligibility preservation",
           "best-eligible selection"],
    "M10": ["multiple threshold-bound dimensions", "merge by highest severity"],
    "M11": ["baseline-versus-current drift magnitude",
            "classification against a threshold"],
    "M12": ["staged rollout or quarantine schedule", "go/halt observation gates"],
    "M13": ["source-target pair scoring", "compatibility or gap measurement"],
    "M14": ["deterministic identity fingerprint", "duplicate-surface detection"],
    "M15": ["weighted assessment score", "tier or rule-class classification",
            "aggregate distribution over classes"],
    "M16": ["route-deviation simulation", "rollback restoration evidence"],
    "M17": ["endowment or funding projection", "sustainability or access verdict"],
}

VIEW_FIELDS = ("observed_operations", "observed_inputs", "observed_outputs",
               "invariants", "sample_behavior")


def view_text(view: dict) -> str:
    """Flatten a candidate view's observable fields into one lowercased blob."""
    parts = []
    for field in VIEW_FIELDS:
        value = view.get(field)
        if isinstance(value, list):
            parts.extend(str(v) for v in value)
        elif value is not None:
            parts.append(str(value))
    return " \n ".join(parts).lower()


def verify_oracle_grounding(view: dict, oracle: dict) -> list:
    """Deterministically verify that an oracle's machine labels are view-grounded.

    oracle = {"expected": {"action", "machines": [...]},
              "grounding": {machine_id: {feature: "exact view quote", ...}}}
    Empty machines (DEFER / no machine) need no grounding. Returns a sorted
    list of problems; empty == every label is grounded in the view.
    """
    problems = []
    text = view_text(view)
    expected = oracle.get("expected") or {}
    machines = expected.get("machines") or []
    grounding = oracle.get("grounding") or {}

    for machine in machines:
        if machine not in MACHINE_FEATURES:
            problems.append(f"{machine}: unknown machine (not in rubric)")
            continue
        machine_grounding = grounding.get(machine) or {}
        for feature in MACHINE_FEATURES[machine]:
            quote = machine_grounding.get(feature)
            if not isinstance(quote, str) or not quote.strip():
                problems.append(
                    f"{machine}: decisive feature '{feature}' is not grounded "
                    "(no view quote) — cannot label without evidence")
            elif quote.lower() not in text:
                problems.append(
                    f"{machine}: grounding quote for '{feature}' does not "
                    f"appear in the view: {quote!r}")

    # Grounding for machines not claimed is dead weight — flag it so an oracle
    # cannot smuggle unlabeled evidence past review.
    for machine in grounding:
        if machine not in machines:
            problems.append(f"{machine}: grounding provided but machine is not "
                            "claimed in expected.machines")
    return sorted(problems)


def _main(argv) -> int:
    if len(argv) < 3:
        print("usage: python core/helix_oracle_grounding.py "
              "<view.json> <oracle.json>")
        return 2
    with open(argv[1], "r", encoding="utf-8") as f:
        view = json.load(f)
    with open(argv[2], "r", encoding="utf-8") as f:
        oracle = json.load(f)
    problems = verify_oracle_grounding(view, oracle)
    cid = view.get("candidate_id", "?")
    print(f"=== oracle grounding gate ({cid}) ===")
    print(f"  claimed machines: {(oracle.get('expected') or {}).get('machines')}")
    if problems:
        print("\nFAIL — ungrounded labels (would be rejected):")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("\nPASS — every machine label is grounded in the view.")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
