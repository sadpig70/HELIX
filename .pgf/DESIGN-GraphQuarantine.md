# DESIGN-GraphQuarantine

GraphQuarantine // path-aware evidence quarantine (done) @v:0.1
    CaseContract // deterministic graph case schema (done)
        # input: nodes, directed edges, contamination_sources, baseline_sha256
        # criteria: no clock, network, randomness, eval, or external dependency
    QuarantineEngine // path-aware propagation (done) @dep:CaseContract
        # process: contaminated source -> directed BFS over block/monitor edges
        # output: quarantine_set, monitor_set, clean_branches, shortest paths
        # criteria: contaminated paths blocked without blocking clean sibling branches
    ReceiptLedger // append-only hash-chain evidence ledger (done) @dep:QuarantineEngine
        # output: replayable receipt event chain
        # criteria: tampering with chain or receipt is detected
    CliSurface // sample/run/report commands (done) @dep:ReceiptLedger
        # criteria: invalid case exits 2, valid cases exit 0
    HelixClosure // handback, close-loop, feedback (done) @dep:CliSurface
        # criteria: ActionHandbackVerifier 5/5 valid and close-loop idempotent

```python
def quarantine(case: dict) -> dict:
    """Compute path-aware evidence quarantine."""
    # acceptance_criteria:
    #   - baseline hash binds nodes/edges/contamination_sources
    #   - only reachable block-path nodes are quarantined
    #   - monitor-only paths do not escalate to quarantine
    #   - clean branches remain explicitly listed
    #   - receipt hash is deterministic and replayable
```

