# DriftIsolator Design @v:1.0

## Gantree

```text
DriftIsolator // minimal counterexample isolation for runtime drift (designing) @v:1.0
    Contract // baseline, events and result receipt (designing)
        Canonicalization // stable JSON and SHA-256 (designing)
        BaselineBinding // initial/expected state hash validation (designing)
        EventGrammar // set, increment and append only (designing)
    ReplayEngine // deterministic state transition replay (designing) @dep:Contract
        PathResolution (designing)
        EventApplication (designing)
        DriftPredicate (designing)
    Shrinker // deterministic ddmin counterexample reduction (designing) @dep:ReplayEngine
        ChunkReduction (designing)
        OneMinimalProof (designing)
        IsolationReceipt (designing)
    AuditLedger // append-only result chain (designing) @dep:Shrinker
    Interface // CLI, examples and documentation (designing) @dep:AuditLedger
    Verification // tests, replay and HELIX handback (designing) @dep:Interface
```

## PPR

```python
def isolate(case: DriftCase) -> IsolationReceipt:
    assert digest(case.initial_state, case.expected_state) == case.baseline_sha256
    final = replay(case.initial_state, case.events)
    if final == case.expected_state:
        return NO_DRIFT
    minimal = ddmin(case.events, predicate=lambda e: replay(case.initial_state, e) != case.expected_state)
    assert all(not predicate(remove_one(minimal, i)) for i in range(len(minimal)))
    return seal(ISOLATED, minimal, final_state=replay(case.initial_state, minimal))

# acceptance_criteria:
#   - baseline hash mismatch and invalid event grammar fail closed
#   - drift trace is deterministic and 1-minimal
#   - no eval, network, randomness or hidden wall clock
#   - receipt/ledger replay, >=3 examples and >=10 tests
```

## Gene provenance

- `counterexample_shrinking`: `HC-PILOT-EXT-003` manifest `9923a7b1758fd950bde28b72fd3548f137de3db9e979942b515a3b85a110ca3b`.
- `baseline_drift`: `HC-PILOT-HELIX-003` manifest `eebe81f3a7f188f355f0cb6c47e92cb7da4ccee75beee560cb595be22c48350f`.
