# HELIXCorpusSupply Work Plan

## POLICY

```python
POLICY = {
    "_version": "2.5",
    "max_retry": 3,
    "on_blocked": "halt",
    "design_modify_scope": ["impl", "internal_interface"],
    "completion": "all_done",
    "max_verify_cycles": 2,
    "verify_perspectives": ["security", "maintainability", "determinism"],
    "max_iterations": 50,
}
```

## Execution Tree

```text
HELIXCorpusSupply // dual-corpus supply foundation (done) @v:1.0
    B0Contracts // versioned contracts (done)
        ManifestContract // corpus manifest schema (done)
        ReceiptContract // admission and review receipt schemas (done)
        PolicyContract // seed corpus supply policy (done)
    B1Core // deterministic corpus supply core (done) @dep:B0Contracts
        ManifestValidation // schema and semantic hard gates (done)
        FingerprintSet // stable source/interface/behavior/machine/gene hashes (done)
        ItemStore // immutable snapshot store (done)
        LedgerAuthority // append-only hash chain and verifier (done)
        GenerativeGate // broad honest admission (done)
        EvidenceGate // strict promotion with review binding (done)
        HealthReport // materialized state and health metrics (done)
        LegacyMigration // project-list candidate conversion (done)
    B2Integration // additive HELIX wiring (done) @dep:B1Core
        CorpusCli // corpus command dispatcher (done)
        PreserveLegacyCorpusEntry // close-loop regression compatibility (done)
        ExtendRepoValidation // schema/policy validation hook (done)
    B3Tests // direct verification coverage (done) @dep:B2Integration
        UnitGate // pure core tests (done)
        CliGate // subprocess integration tests (done)
        MigrationGate // legacy conversion honesty tests (done)
        SecurityGate // path, conflict and chain tamper tests (done)
    B4Verify // evidence-backed completion (done) @dep:B3Tests
        TargetedTests // new test module pass (done)
        FullRegression // 695+ suite pass (done)
        HelixValidate // structure validator pass (done)
        DeterminismReplay // identical replay and chain verify (done)
        ArchitectureReview // design versus files review (done)
    B5Report // durable Korean report and final state (done) @dep:B4Verify
        ImplementationReport // implementation and operation report (done)
        PGXFIndex // sync large-work index (done)
        StatusClosure // WORKPLAN/status terminal sync (done)
```

## Batch Gates

- B0: every schema is valid JSON and remains inside `helix_schema` stdlib subset.
- B1: `python -m unittest tests.test_corpus_supply -q`.
- B2: CLI help/validate/intake/admit/promote/status/health/migrate behavior verified.
- B3: refusal paths prove no unauthorized ledger write.
- B4: targeted tests, full suite, validator, `git diff --check` all exit 0.
- B5: report contains exact commands, evidence and honest deferred scope.
