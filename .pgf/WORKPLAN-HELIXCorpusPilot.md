# HELIXCorpusPilot Work Plan

## POLICY

```python
POLICY = {
    "_version": "2.5",
    "max_retry": 3,
    "on_blocked": "halt",
    "completion": "all_done",
    "max_verify_cycles": 2,
    "verify_perspectives": ["integrity", "determinism", "authority"],
}
```

## Execution Tree

```text
HELIXCorpusPilot // Phase 2 pilot (done) @v:1.0
    B0Contract // frozen denominator (done)
        RegistrySchema // 24-slot schema (done)
        RegistrySemantics // exact 8/6/4/3/3 validation (done)
    B1Tooling // pilot meta-layer (done) @dep:B0Contract
        SnapshotBuilder // deterministic compact evidence (done)
        PilotReporter // ledger and diversity aggregation (done)
    B2Integration // documentation and repo validation (done) @dep:B1Tooling
        SupplyRunbook // commands and authority points (done)
        RepoValidator // schema subset guard (done)
        PilotState // durable checkpoint and report (done)
    B3Verification // implementation gates (done) @dep:B2Integration
        TargetedTests // registry, snapshot, report and tamper cases (done)
        FullRegression // complete unittest suite (done)
        RepoValidation // helix_validate (done)
        DiffHygiene // git diff --check (done)
    B4RealPilot // actual candidate cohort (done) @dep:B3Verification
        CandidateFreeze // requires human selection (done)
        CandidateAdmissions // 24 provenance and >=12 Generative (done)
        EvidencePromotions // >=5 human-approved Evidence (done)
        Phase3Decision // final diversity and integrity report (done)
```

## Batch gates

| Batch | Gate |
|---|---|
| B0 | exact slot IDs and `8/6/4/3/3` mix |
| B1 | deterministic snapshot and ledger-derived report |
| B2 | local docs, schema guard and durable status agree |
| B3 | targeted/full tests, validator and diff hygiene pass |
| B4 | 24 provenance, 12 Generative, 5 Evidence and human authority |
