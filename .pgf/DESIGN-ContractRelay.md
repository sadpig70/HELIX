# DESIGN-ContractRelay

ContractRelay // fail-closed federated contract relay (done) @v:0.1
    CaseContract // deterministic relay case schema (done)
        # input: source, target, contract, payload, custody, baseline_sha256
        # criteria: no clock, network, randomness, eval, or external dependency
    ValidationEngine // contract and custody validation (done) @dep:CaseContract
        # process: validate required fields, primitive types, allowed source/target, custody continuity
        # output: normalized errors with code/path/severity/message
        # criteria: ambiguity blocks relay
    RelayReceipt // deterministic relay decision receipt (done) @dep:ValidationEngine
        # output: RELAYED, BLOCKED, INVALID
        # criteria: clean cases relay, invalid contracts block with normalized errors
    ReceiptLedger // append-only hash-chain evidence ledger (done) @dep:RelayReceipt
        # criteria: tampering with chain or receipt is detected
    HelixClosure // handback, close-loop, feedback (done) @dep:ReceiptLedger
        # criteria: ActionHandbackVerifier 5/5 valid and close-loop idempotent

```python
def relay(case: dict) -> dict:
    """Validate a federated data contract before custody transfer."""
    # acceptance_criteria:
    #   - baseline hash binds source/target/contract/payload/custody
    #   - all failures are normalized as deterministic errors
    #   - ambiguous custody or contract mismatch returns BLOCKED
    #   - clean request returns RELAYED with relay token
    #   - receipt hash is deterministic and replayable
```

