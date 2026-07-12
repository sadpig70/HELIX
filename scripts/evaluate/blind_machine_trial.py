#!/usr/bin/env python3
"""Blind machine trial harness for the HELIX Truth Plane (P2_4).

Runs one full blind round over a locked holdout registry, per candidate:

    candidate view -> injected predictor -> prediction receipt seal
        -> reveal approval -> oracle reveal -> deterministic scoring

The predictor is an injected callable ``predictor(view: dict) -> prediction``
(the AI proposal lives outside the determinism boundary); the harness itself is
stdlib-deterministic and structurally blind: a predictor receives only the
parsed candidate view, never an oracle path or content. Every system named in
``systems`` runs against the same locked cohort with its own receipt chain, so
HELIX and pre-declared baselines are compared on identical denominators.
ABSTAIN, MISSING_ARTIFACT, and protocol violations stay in the locked eligible
denominator with zero credit (docs/HOLDOUT-POLICY.md).

CLI (receipts and report land under gitignored _workspace/):
    python scripts/evaluate/blind_machine_trial.py
    python scripts/evaluate/blind_machine_trial.py --system helix=pkg.mod:predict_fn
"""

import argparse
import copy
import importlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.helix_novelty import (  # noqa: E402
    NOT_IMPLEMENTED,
    aggregate_novelty,
    build_reduction_receipt,
    is_novelty_claim,
)
from core.helix_prediction import (  # noqa: E402
    apply_prediction_receipt,
    apply_reveal_receipt,
    build_prediction_receipt,
    build_reveal_receipt,
    score_cohort,
)

DEFAULT_REGISTRY = "seed/evaluation/holdout-registry.json"
DEFAULT_OUT = "_workspace/helix-direction/trials/synthetic-blind-trial"
DEFAULT_APPROVALS = [{"approver_id": "approver-synthetic-1", "role": "reveal_approver"}]


def abstain_baseline(view: dict) -> dict:
    """Pre-declared floor baseline: never predicts (coverage 0, credit 0)."""
    return {"outcome": "ABSTAIN", "action": None, "machines": None}


def constant_baseline(view: dict) -> dict:
    """Pre-declared naive baseline: one constant action and machine for all."""
    return {"outcome": "PREDICT", "action": "BUILD_ON_PLATFORM", "machines": ["M1"]}


DEFAULT_SYSTEMS = {
    "baseline-abstain": abstain_baseline,
    "baseline-constant": constant_baseline,
}


def _write_json(root: str, rel: str, doc: dict) -> str:
    full = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return rel


def run_trial(root: str, registry: dict, predictor, approvals: list,
              receipts_rel: str):
    """One blind round for one system: seal, reveal, and collect receipt chains.

    Returns (revealed_registry, chains). The predictor sees only the parsed
    candidate view; a missing view file is sealed as MISSING_ARTIFACT without
    calling the predictor.
    """
    registry = copy.deepcopy(registry)
    chains = {}
    for candidate in registry["candidates"]:
        if candidate["status"] == "excluded":
            continue
        cid = candidate["candidate_id"]
        view_rel = candidate["candidate_view"]["path"]
        view_full = view_rel if os.path.isabs(view_rel) else os.path.join(root, view_rel)
        if not os.path.isfile(view_full):
            prediction = {"outcome": "MISSING_ARTIFACT", "action": None, "machines": None}
        else:
            with open(view_full, "r", encoding="utf-8") as f:
                prediction = predictor(json.load(f))
        prediction_receipt = build_prediction_receipt(root, registry, cid, prediction)
        rel = _write_json(root, f"{receipts_rel}/{cid}.prediction.json",
                          prediction_receipt)
        registry = apply_prediction_receipt(registry, prediction_receipt, rel)
        reveal_receipt = build_reveal_receipt(root, registry, cid, approvals)
        _write_json(root, f"{receipts_rel}/{cid}.reveal.json", reveal_receipt)
        registry = apply_reveal_receipt(registry, reveal_receipt)
        chains[cid] = {"prediction": prediction_receipt, "reveal": reveal_receipt}
    return registry, chains


def run_novelty_phase(root: str, registry: dict, chains: dict,
                      evidence_map: dict, receipts_rel: str) -> dict:
    """Seal one reduction receipt per novelty claim (CONDENSE/DEFER prediction).

    ``evidence_map`` maps candidate_id -> externally injected implementation
    evidence; claims without evidence are sealed honestly as not_implemented,
    so every novelty claim leaves an auditable receipt.
    """
    receipts = {}
    for cid in sorted(chains):
        chain = chains[cid]
        body = (chain.get("prediction") or {}).get("prediction") or {}
        if not is_novelty_claim(body):
            continue
        implementation = evidence_map.get(cid, dict(NOT_IMPLEMENTED))
        receipt = build_reduction_receipt(root, registry, chain["prediction"],
                                          chain["reveal"], implementation)
        _write_json(root, f"{receipts_rel}/{cid}.reduction.json", receipt)
        receipts[cid] = receipt
    return receipts


def run_blind_trial(root: str, registry: dict, systems: dict,
                    approvals: list, out_rel: str,
                    reduction_evidence: dict = None) -> dict:
    """Run every system over the same locked cohort and score them identically.

    ``reduction_evidence`` maps system name -> candidate_id -> implementation
    evidence for the novelty phase (external experiments, injected by receipt).
    """
    report = {
        "schema": "helix-blind-trial-report/1.0",
        "policy_version": registry["policy_version"],
        "cohort_id": registry["cohort"]["cohort_id"],
        "cohort_commitment_sha256": registry["cohort"]["commitment_sha256"],
        "systems": {},
    }
    for name in sorted(systems):
        revealed, chains = run_trial(root, registry, systems[name], approvals,
                                     f"{out_rel}/{name}/receipts")
        reductions = run_novelty_phase(
            root, revealed, chains, (reduction_evidence or {}).get(name, {}),
            f"{out_rel}/{name}/receipts")
        metrics = score_cohort(root, revealed, chains)
        metrics["novelty"] = aggregate_novelty(root, revealed, chains, reductions)
        report["systems"][name] = metrics
    _write_json(root, f"{out_rel}/blind-trial-report.json", report)
    return report


def _load_callable(spec: str):
    module_name, _, attr = spec.partition(":")
    return getattr(importlib.import_module(module_name), attr)


def _main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="root-relative output dir for receipts + report")
    parser.add_argument("--system", action="append", default=[],
                        metavar="NAME=MODULE:FN",
                        help="additional predictor to evaluate on the same cohort")
    parser.add_argument("--approver", action="append", default=[],
                        help="reveal approver id (role reveal_approver)")
    parser.add_argument("--reduction-evidence", default=None, metavar="PATH",
                        help="JSON {system: {candidate_id: implementation}} of "
                             "external implementation evidence for novelty claims")
    args = parser.parse_args(argv[1:])

    root = os.path.abspath(args.root)
    registry_full = args.registry if os.path.isabs(args.registry) else os.path.join(root, args.registry)
    with open(registry_full, "r", encoding="utf-8") as f:
        registry = json.load(f)

    systems = dict(DEFAULT_SYSTEMS)
    for spec in args.system:
        name, _, target = spec.partition("=")
        systems[name] = _load_callable(target)
    approvals = ([{"approver_id": a, "role": "reveal_approver"} for a in args.approver]
                 or DEFAULT_APPROVALS)
    reduction_evidence = None
    if args.reduction_evidence:
        with open(args.reduction_evidence, "r", encoding="utf-8") as f:
            reduction_evidence = json.load(f)

    report = run_blind_trial(root, registry, systems, approvals, args.out,
                             reduction_evidence)
    print(f"=== HELIX blind machine trial ({report['cohort_id']}) ===")
    print(f"  commitment: {report['cohort_commitment_sha256']}")
    for name, metrics in report["systems"].items():
        gates = metrics["gates"]
        novelty = metrics["novelty"]["counts"]
        print(f"  {name}: exact={metrics['counts']['exact']}"
              f"/{metrics['denominator']}"
              f" coverage={metrics['coverage']:.2f}"
              f" macro_f1={metrics['macro_f1']:.2f}"
              f" gates={'PASS' if gates['coverage_pass'] and gates['macro_f1_pass'] else 'FAIL'}"
              f" | novelty claims={novelty['claims']}"
              f" false_condense={novelty['false_condense']}"
              f" confirmed={novelty['novel_confirmed']}")
    print(f"  report: {args.out}/blind-trial-report.json")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
