# PilotSim Work Plan

## POLICY

```python
POLICY = {
    "max_retry": 2,
    "on_blocked": "report_and_continue_independent_nodes",
    "completion": "all_done_or_blocked",
    "delegation_max_depth": 1,
    "honesty_boundary": "synthetic_only_never_t4_evidence",
}
```

## Execution Tree

```text
PilotSim // three-persona synthetic wedge pre-pilot (done) @v:1.0
    PrepareContracts // define honest simulation boundary and artifacts (done)
    [parallel]
    ReleaseLead // software release handback operator (done)
    SREOperator // CI/CD and infrastructure handback operator (done)
    AIGovernanceLead // AI approval and evidence-integrity operator (done)
    [/parallel]
    AggregateEvidence // recompute metrics and replay from three ledgers (done) @dep:ReleaseLead,SREOperator,AIGovernanceLead
    JudgeBoundary // run T4 with no real-owned-stakes attestations (done) @dep:AggregateEvidence
    RecordReport // persist evidence and conclusions (done) @dep:JudgeBoundary
```
