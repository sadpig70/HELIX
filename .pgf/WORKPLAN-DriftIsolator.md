# DriftIsolator Work Plan

## POLICY

```python
POLICY = {"_version":"2.5","max_retry":3,"on_blocked":"halt","completion":"all_done","max_verify_cycles":2,"verify_perspectives":["acceptance","quality","architecture","security"]}
```

## Execution Tree

```text
DriftIsolator // minimal counterexample isolation (done) @v:1.0
    Contract (done)
        Canonicalization (done)
        BaselineBinding (done)
        EventGrammar (done)
    ReplayEngine (done) @dep:Contract
        PathResolution (done)
        EventApplication (done)
        DriftPredicate (done)
    Shrinker (done) @dep:ReplayEngine
        ChunkReduction (done)
        OneMinimalProof (done)
        IsolationReceipt (done)
    AuditLedger (done) @dep:Shrinker
    Interface (done) @dep:AuditLedger
    Verification (done) @dep:Interface
    HandbackCloseLoop (done) @dep:Verification
```
