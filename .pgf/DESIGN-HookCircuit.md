# DESIGN-HookCircuit

HookCircuit // reflex circuit breaker for plugin hooks (done) @v:0.1
    CaseContract // deterministic hook dispatch case schema (done)
        # input: hooks, events, observations, baseline_sha256
        # criteria: no clock, network, randomness, eval, or external dependency
    CircuitEngine // hook contract and reflex interruption (done) @dep:CaseContract
        # process: validate hook contracts, count failures/timeouts, trip only failing hooks
        # output: dispatch evidence, tripped hooks, isolated plugins, allowed hooks
        # criteria: failing hook trips in isolation while deterministic dispatch evidence is preserved
    ReceiptLedger // append-only hash-chain evidence ledger (done) @dep:CircuitEngine
        # criteria: tampering with chain or receipt is detected
    CliSurface // sample/run/report commands (done) @dep:ReceiptLedger
        # criteria: invalid case exits 2, tripped case exits 1, clean case exits 0
    HelixClosure // handback, close-loop, feedback (done) @dep:CliSurface
        # criteria: ActionHandbackVerifier 5/5 valid and close-loop idempotent

```python
def evaluate(case: dict) -> dict:
    """Evaluate plugin hook dispatch and trip isolated circuit breakers."""
    # acceptance_criteria:
    #   - baseline hash binds hooks/events/observations
    #   - invalid hook contracts fail closed
    #   - failing or timed-out hook trips only its own circuit
    #   - clean hooks remain dispatchable
    #   - receipt hash is deterministic and replayable
```

