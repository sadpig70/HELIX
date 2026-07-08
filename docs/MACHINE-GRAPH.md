# HELIX Machine Graph

> Version: v0.6-U6 draft. Source promoted from `_workspace/condense/U1-mechanism-graph.md`
> plus the later Scorestra M15 finding in `seed/condense/layered-corpus.json`.

This document fixes the Condense machine ontology so routing labels stop drifting. A
machine claim is not accepted merely because a human label says so; it must eventually
map to a deterministic probe in `core/helix_machine_probes.py`.

## Machine Catalog

| ID | Machine | Definition | Current Probe |
|---|---|---|---|
| M1 | hash-chain ledger | Append-only canonical JSON record chain; record hash excludes time metadata; tamper detection by recomputing links. | `probe_M1` |
| M2 | verdict severity | Discrete three-step verdict algebra such as `valid/thin/breach`, with max-severity merge. | `probe_M2` |
| M3 | predicate gate | Evidence packet -> independent predicate checks -> aggregate verdict; rejects missing/private payload evidence. | `probe_M3` |
| M4 | provenance verify | Selection or commitment verified against confirmed evidence chain; hash-only commitment; lineage walk. | `probe_M4` |
| M5 | clearing / priority allocation | Bid/right pool -> conflict-free priority allocation with conservation, non-overlap, and priority ordering. | `probe_M5` |
| M6 | pricing | Deterministic continuous price/cost/premium formula; no verdict algebra. | `probe_M6` |
| M7 | settlement | Realized outcome vs contract -> zero-sum payoff or netting result. | `probe_M7` |
| M8 | shock rehearsal | Demand/supply disruption scenario -> shortfall/survival stress result. | `probe_M8` |
| M9 | candidate scoring + routing | Candidate pool scored against constraints/evidence; best eligible route selected; rejection reasons preserved. | `probe_M9` |
| M10 | threshold-bound | Telemetry/resource dimensions compared to thresholds, producing dimension verdicts merged by highest severity. | `probe_M10` |
| M11 | drift detection | Baseline vs current state -> drift magnitude and verdict. | `probe_M11` |
| M12 | staged quarantine/release | Risk-scaled or cohort-scaled quarantine/release schedule with observation gates. | `probe_M12` |
| M13 | compatibility/gap scoring | Beachhead adapter pattern; cross-domain compatibility or gap scoring. | `probe_M13` |
| M14 | fingerprint/identity + dedup | Normalize artifact identity, fingerprint it, and block duplicate/reused work. | `probe_M14` |
| M15 | assessment-scoring | Normalize batch -> per-item weighted score or rule-ladder class -> graded tier/band -> aggregate distribution. Distinct from M2, M6, M9, and M10. | `probe_M15` |
| M16 | route simulation rollback | Planned route + actual route + deviation policy -> rollback/reroute/clear control decision with restoration evidence. | `probe_M16` |
| M17 | endowment funding projection | One-time pledge corpus + policy -> year-by-year corpus projection -> sustainability/open-access verdict. | `probe_M17` |

## U6 Probe Contract

`core/helix_machine_probes.py` accepts normalized behavioral artifacts, not source text.
The meta layer may read code or run pack samples, but the deterministic probe only sees
evidence such as verdict outputs, threshold dimensions, price outputs, scored items,
tiers, and distributions.

```python
{
    "operation": "assessment_scoring",
    "weights": {"a": 0.5, "b": 0.3},
    "bands": [{"min": 0.7, "tier": "high"}, {"min": 0.0, "tier": "low"}],
    "scored": [{"id": "x", "score": 0.9, "tier": "high"}],
    "count_by_tier": {"high": 1, "low": 0},
}
```

Each probe returns:

```python
{"machine": "M15", "holds": True, "evidence": {...}}
```

## Current Probe Coverage

U6 started with the four routing-critical machines named in `HANDOFF.md`, then extended
coverage across the trust substrate exposed by the live `-stra` repos:

- `M1`: detects canonical hash-chain ledger records and time-metadata exclusion.
- `M2`: detects predicate/certification verdict severity and max-severity merge.
- `M3`: detects evidence-packet predicate gates and aggregate verdict consistency.
- `M4`: detects provenance verification against a confirmed evidence chain.
- `M5`: detects conservation, no-conflict allocation, no party overfill, and strict priority clearing.
- `M6`: detects numeric pricing/cost/premium outputs and rejects verdict algebra.
- `M7`: detects settlement/netting results with zero-sum buyer/seller legs.
- `M8`: detects shock rehearsal aggregation: survival is min coverage, total shortfall is summed positive shortfall, affected tracks positive shortfall items.
- `M9`: detects candidate scoring, eligibility filtering, rejection reasons, and best-eligible route selection.
- `M10`: detects threshold-bound dimension verdicts and max-severity merge.
- `M11`: detects baseline/current drift magnitude against a threshold and verifies the emitted drift verdict.
- `M12`: detects staged rollout/quarantine schedules with cumulative cohort planning, go/halt gates, and completion state.
- `M13`: detects pairwise compatibility/gap scoring summaries and rejects route-selection, tier-distribution, pricing, bound, and verdict machines.
- `M14`: detects deterministic identity fingerprints and duplicate behavior surfaces.
- `M15`: detects both Scorestra modes:
  - weighted `score -> band -> count_by_tier`
  - rule-ladder `factors -> tier -> count_by_tier` for DetourDesk/FieldRoot style 2-D classification
- `M16`: detects RouteSentinel-style route deviation simulation and rollback restoration evidence. This is a narrow
  novel-machine probe, not a generic simulator.
- `M17`: detects EndowFront-style permanent endowment projection: pledge aggregation, yearly payout/cost/closing
  schedule, sustainability verdict, and open-access grant. This is a narrow funding-projection probe, not generic pricing.

The initial unit dataset reproduces the key U6 target split:

| Corpus Finding | Expected Probe Result |
|---|---|
| SovMesh / PqcMesh / SignalMesh | M2 |
| AgentMesh | M6 |
| FlowMesh | M10 |
| ForgeQuarantine / LoopKit / LazarettoStage | M15 score-band |
| DetourDesk / FieldRoot | M15 rule-ladder |

This is the first deterministic acceptance surface.

## Live 56-Pack Measurement

`scripts/condense/machine_probe_dataset.py` runs the live sample I/O for all five `-stra`
platform repos, adds deterministic trust-substrate core artifacts, and feeds normalized
artifacts into `agreement_report()`.

```bash
python scripts/condense/machine_probe_dataset.py
```

Current U6 result:

```text
platform packs: 56
implemented probe cases: 95
scored claims: 95
matched claims: 95
agreement: 1.000000
skipped unimplemented probes: {}
```

Interpretation: U6 now proves the implemented probe set
(`M1/M2/M3/M4/M5/M6/M7/M8/M9/M10/M11/M12/M13/M14/M15`) against live pack behavior plus
deterministic trust-substrate artifacts. This automatically reproduces hash-chain ledger,
predicate-gate, provenance, fingerprint/dedup, the compatibility mesh split, Clearstra
priority clearing, settlement, and shock rehearsal, Routestra route selection, Certstra
staged release, policy drift detection, a reference compatibility/gap machine, and the M15
Scorestra cluster.

`M13` has no current live `-stra` pack claim. Its probe is included as a reference machine
and unit-tested against the Compatibility Mesh split so SovMesh/PqcMesh/SignalMesh,
AgentMesh, and FlowMesh remain classified as `M2/M6/M10`, not as a false shared `M13`.

`ADPR` is a source-backed forward candidate normalized as existing `M4`. Its source describes
it as a hash-only provenance log and commitment store, so
`examples/condense/candidate-adpr-m4.json` routes to `BUILD_ON_PLATFORM` on Attestra without
creating a new machine.

All remaining design-only candidates now have normalized source artifacts:

- `AgentPACT` -> `M1` hash-chain accountability ledger -> `BUILD_ON_PLATFORM` / Attestra.
- `GPOA` -> `M15` two-axis governance quadrant scoring -> `BUILD_ON_PLATFORM` / Scorestra.
- `MLX` -> `M3` method-license metadata predicate gate -> `BUILD_ON_PLATFORM` / Attestra.
- `PnR` -> `M15` non-response proof scoring -> `BUILD_ON_PLATFORM` / Scorestra.
- `QVeil` -> `M3` PQC API upgrade predicate gate -> `BUILD_ON_PLATFORM` / Attestra.
- `Qvidence` -> `M4` bio evidence commitment verification -> `BUILD_ON_PLATFORM` / Attestra.
- `WattMesh` -> `M9` home-energy negotiation routing -> `BUILD_ON_PLATFORM` / Routestra.

`M16` is currently forward-prediction only. RouteSentinel has no live vendored repo, but
the `.recreate` source gene documents its narrow surface (`planned route`, `actual route`,
`deviation policy`, `rollback state`), and `examples/condense/candidate-routesentinel-m16.json`
turns that source artifact into a deterministic normalized candidate.

`M17` is currently forward-prediction only. EndowFront is read from the public
`github.com/sadpig70/endowfront` source and normalized into
`examples/condense/candidate-endowfront-m17.json`; it remains uncovered by existing
platform kernels.

## U8 Router Policy

`core/helix_router.py` routes probe-positive machines in two deterministic layers:

1. `kernel_machines` coverage from `seed/condense/layered-corpus.json`.
2. Live pack evidence from U6 agreement rows (`platform`, `pack`, `stage`, `matched`).

Pack evidence does not promote a machine into the platform kernel. It only proves that a
future matching claim can grow as a pack under an existing platform contract.

Current consequence:

- `M11` is routed to Attestra as `coverage_scope=pack_evidence` because it is proven by
  the `policy-drift` pack, but it is not added to Attestra `kernel_machines`.
- `M13` remains `DEFER`: it is a reference compatibility/gap machine with no live `-stra`
  pack coverage yet.

`seed/condense/router-gate.json` locks this U8 routed state as a `helix_validate` hard
gate: `BUILD_ON_PLATFORM=94`, `DEFER=1`, `deferred_machines={"M13": 1}` over 95 probe
decisions.

## U9 Forward Prediction

`scripts/condense/forward_predict.py` is the first deterministic experiment scaffold for
new candidates. It accepts one normalized candidate artifact, probes the claimed
machine, and routes the probe-positive result through the U8 router:

```bash
python scripts/condense/forward_predict.py --candidate candidate.json \
  --layered-corpus seed/condense/layered-corpus.json --json
```

This predicts whether the candidate should become `BUILD_ON_PLATFORM`, `DEFER`, or
`CONDENSE` before any pack or platform code is written.

Candidate batches use a manifest. Each entry can point to a candidate JSON file or
carry the normalized candidate inline:

```json
{
  "schema": "helix-forward-predict-manifest/1.0",
  "layered_corpus": "seed/condense/layered-corpus.json",
  "candidates": [
    {"candidate": "candidate.json"},
    {"id": "inline", "expected": ["M13"], "artifact": {"operation": "..."}}
  ]
}
```

Oracle fields (`action`, `platform`, `platform_absent`) are optional. When omitted,
the report still records the prediction but marks the row as `expectation="none"`.

```bash
python scripts/condense/forward_predict.py \
  --manifest examples/condense/forward-predict-manifest.json \
  --out _workspace/condense/U9-forward-predict-report.json
```

Live `layered-corpus` deferred/future markers can be converted into a manifest:

```bash
python scripts/condense/collect_forward_candidates.py \
  --out _workspace/condense/U9-live-candidate-manifest.json
python scripts/condense/forward_predict.py \
  --manifest _workspace/condense/U9-live-candidate-manifest.json \
  --out _workspace/condense/U9-live-forward-predict-report.json
```

The collector does not infer behavioral artifacts from prose. It only attaches artifacts
listed in `seed/condense/forward-candidate-artifacts.json`. Current live output is `10`
candidates (`deferred=2`, `future=8`) with `artifact_counts={"available": 10, "missing": 0}`.
Eight candidates predict `BUILD_ON_PLATFORM`; RouteSentinel `M16` and EndowFront `M17`
remain deliberate `DEFER` rows because no current platform covers those narrow machines.

Regression fixtures live in `examples/condense/`:

- `candidate-scorestra-m15.json` -> `BUILD_ON_PLATFORM` / `Scorestra`
- `candidate-adpr-m4.json` -> `BUILD_ON_PLATFORM` / `Attestra`
- `candidate-agentpact-m1.json` -> `BUILD_ON_PLATFORM` / `Attestra`
- `candidate-gpoa-m15.json` -> `BUILD_ON_PLATFORM` / `Scorestra`
- `candidate-mlx-m3.json` -> `BUILD_ON_PLATFORM` / `Attestra`
- `candidate-pnr-m15.json` -> `BUILD_ON_PLATFORM` / `Scorestra`
- `candidate-qveil-m3.json` -> `BUILD_ON_PLATFORM` / `Attestra`
- `candidate-qvidence-m4.json` -> `BUILD_ON_PLATFORM` / `Attestra`
- `candidate-wattmesh-m9.json` -> `BUILD_ON_PLATFORM` / `Routestra`
- `candidate-m13-defer.json` -> `DEFER`
- `candidate-m13-condense.json` -> `CONDENSE`
- `candidate-routesentinel-m16.json` -> `DEFER` / uncovered `M16`
- `candidate-endowfront-m17.json` -> `DEFER` / uncovered `M17`

`seed/condense/forward-predict-gate.json` locks these three predictions as a
`helix_validate` hard gate.

The standard U9 report artifact is:

```bash
python scripts/condense/forward_predict.py --gate seed/condense/forward-predict-gate.json \
  --layered-corpus seed/condense/layered-corpus.json \
  --out _workspace/condense/U9-forward-predict-report.json
```

Current report summary: `all_ok=True`,
`{"BUILD_ON_PLATFORM": 1, "CONDENSE": 1, "DEFER": 1}`.

`helix.py status` can surface that report when requested:

```bash
python helix.py status --layered-corpus seed/condense/layered-corpus.json \
  --forward-predict-report _workspace/condense/U9-forward-predict-report.json
```
