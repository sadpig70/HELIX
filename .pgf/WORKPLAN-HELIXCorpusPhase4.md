# HELIXCorpusPhase4 Work Plan

## POLICY

```python
POLICY = {
    "_version": "2.5",
    "max_retry": 3,
    "on_blocked": "halt",
    "design_modify_scope": ["registry", "docs", "pgf_status"],
    "completion": "all_done",
    "max_iterations": 20,
    "max_verify_cycles": 2,
}
```

## Execution Tree

```text
HELIXCorpusPhase4 // platform-pack absorption planning for Phase 3 machines (in-progress) @v:1.0
    B0EntryGate // consume Phase 3 closure and Condense gate doctrine (done)
    B1PackRegistry // freeze platform-pack absorption registry (done) @dep:B0EntryGate
    B2PackContracts // define per-platform absorption contracts (done) @dep:B1PackRegistry
        AttestraPackLane // five trust/gate packs for Attestra (done)
        RoutestraPackLane // one route/handoff pack for Routestra (done)
    B3Validation // verify registry consistency and repository health (done) @dep:B2PackContracts
    B4Handoff // choose the next executable platform absorption batch (done) @dep:B3Validation
```

## Batch gates

| Batch | Gate |
|---|---|
| B0 | Phase 3 outcome says `PHASE3_COMPLETE_READY_FOR_PHASE4` and `DO_NOT_EMIT_NEW_PLATFORM_KERNEL` |
| B1 | Registry has six packs, all mapped to existing platforms |
| B2 | Each pack has parity, determinism, zero-kernel, structure and tests gates |
| B3 | JSON consistency check, Phase 3 registry validation, HELIX validator and regression pass |
| B4 | Exactly one next task selected |
