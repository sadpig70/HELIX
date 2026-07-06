# ActionHandbackVerifier Work Plan

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
ActionHandbackVerifier // delegated action handback verification MVP (done) @v:1.1
    InputContract // handback packet JSON schema and deterministic sample fixtures (done)
        SampleFixtures // valid/thin/breach examples emitted by sample command (done)
        PacketSections // delegation/custody/route/rollback/trace sections (done)
    PredicateEngine // five predicate checks over one handback packet (done) @dep:InputContract
        AuthorityCheck // delegation authority and action scope check (done)
        CustodyCheck // handoff custody continuity check (done)
        RouteCheck // route deviation and rollback trigger check (done)
        RollbackCheck // rollback completion and restoration proof check (done)
        TraceCheck // digest/evidence-path proof surface with private payload rejection (done)
    VerdictAggregate // worst severity aggregate valid/thin/breach (done) @dep:PredicateEngine
    CliTriplet // sample/run/report stdlib CLI (done) @dep:VerdictAggregate
        SampleCommand // emit deterministic fixtures (done)
        RunCommand // evaluate one packet, emit JSON verdict, optional --ledger append (done)
        ReportCommand // emit Markdown report with evidence paths (done)
    ClosedAuditLedger // append-only hash-chain ledger + verify subcommand (done) @dep:VerdictAggregate
        LedgerAppend // deterministic record with result_hash/record_hash/prev_hash (done)
        LedgerVerify // tamper detection via chain + record re-validation (done)
        VerifyCommand // verify --ledger CLI with JSON result + exit code (done)
    TestSuite // deterministic acceptance tests incl. ledger tamper cases (done) @dep:CliTriplet,ClosedAuditLedger
    Verify // 3-perspective PGF verification (done) @dep:TestSuite
```
