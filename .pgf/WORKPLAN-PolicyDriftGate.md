# PolicyDriftGate Work Plan

## POLICY

```python
POLICY = {
    "_version": "2.5",
    "max_retry": 3,
    "on_blocked": "halt",
    "design_modify_scope": ["impl", "internal_interface"],
    "completion": "all_done",
    "max_iterations": 30,
    "max_verify_cycles": 2,
    "verify_perspectives": ["acceptance", "quality", "architecture"],
}
```

## Execution Tree

```text
PolicyDriftGate // AI agent behavior policy drift and loop interruption safety gate (in-progress) @v:1.0
    InputContract // audit packet JSON schema and deterministic sample fixtures (in-progress)
        SampleFixtures // cleared/warned/interrupted examples emitted by sample command (in-progress)
        PacketSections // behavior/dossier/runtime_signal sections (in-progress)
    PredicateEngine // predicate checks over behavioral, deployment log, and loop signals (in-progress) @dep:InputContract
        BehaviorCheck // behavior policy drift check comparing candidate vs baseline (in-progress)
        DossierCheck // deployment log drift compliance audit (in-progress)
        LoopSignalCheck // real-time loop detection and interrupt trigger (in-progress)
    VerdictAggregate // worst severity aggregate cleared/warned/interrupted with loop interruption bypass (in-progress) @dep:PredicateEngine
    CliTriplet // sample/run/report stdlib CLI (in-progress) @dep:VerdictAggregate
        SampleCommand // emit deterministic fixtures (in-progress)
        RunCommand // evaluate one packet, emit JSON verdict, optional --ledger append (in-progress)
        ReportCommand // emit Markdown report with drift analysis and attestation details (in-progress)
    ClosedAuditLedger // append-only hash-chain ledger + verify subcommand (in-progress) @dep:VerdictAggregate
        LedgerAppend // deterministic record with result_hash/record_hash/prev_hash (in-progress)
        LedgerVerify // tamper detection via chain + record re-validation (in-progress)
        VerifyCommand // verify --ledger CLI with JSON result + exit code (in-progress)
    TestSuite // deterministic acceptance tests (in-progress) @dep:CliTriplet,ClosedAuditLedger
    Verify // 3-perspective PGF verification (in-progress) @dep:TestSuite
```
