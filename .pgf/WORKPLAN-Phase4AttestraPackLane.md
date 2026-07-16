# Phase4AttestraPackLane Work Plan

## POLICY

```python
POLICY = {
    "_version": "2.5",
    "max_retry": 3,
    "on_blocked": "halt",
    "design_modify_scope": ["contracts", "parity_fixture_specs", "pgf_status"],
    "completion": "all_done",
    "max_iterations": 20,
    "max_verify_cycles": 2,
}
```

## Execution Tree

```text
Phase4AttestraPackLane // contract and parity fixture design for five Attestra packs (in-progress) @v:1.0
    A0EntryGate // read Phase 4 registry and isolate Attestra packs (done)
    A1ContractMap // define one absorption contract per Attestra pack (done) @dep:A0EntryGate
        ProofEscrowContract // release escrow attestation gate pack (done)
        AuthorityArbiterContract // delegated authority verdict pack (done)
        DriftIsolatorContract // runtime drift evidence pack (done)
        GraphQuarantineContract // path-aware evidence quarantine pack (done)
        HookCircuitContract // plugin runtime safety gate pack (done)
    A2ParityFixtureSpec // define source-derived parity fixtures for every pack (done) @dep:A1ContractMap
    A3AbsorptionGuardrails // lock zero-kernel and source read-only constraints (done) @dep:A2ParityFixtureSpec
    A4Verify // validate JSON contracts and source project tests (done) @dep:A3AbsorptionGuardrails
```

## Batch gates

| Batch | Gate |
|---|---|
| A0 | Source Phase 4 registry has five Attestra packs |
| A1 | Every pack has a concrete Attestra pack surface and forbidden-change contract |
| A2 | Every pack has source example fixtures and expected outcomes |
| A3 | `zero-kernel-change`, `source-project-read-only`, `provenance-retained` locked |
| A4 | JSON assertions, source tests, HELIX validator, regression and diff check pass |
