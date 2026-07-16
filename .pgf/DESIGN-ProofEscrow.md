# ProofEscrow Design @v:1.0

## Gantree

```text
ProofEscrow // evidence-bound AI artifact release escrow (designing) @v:1.0
    Contract // deterministic request and receipt contract (designing)
        Canonicalization // stable JSON and SHA-256 (designing)
        StepSignature // HMAC-SHA256 over artifact step metadata (designing)
        BehaviorBinding // approved baseline equals observed behavior (designing)
    EscrowEngine // fail-closed release decision (designing) @dep:Contract
        RequestValidation // schema and evidence completeness (designing)
        ArtifactVerification // signer, signature and final-product checks (designing)
        BehaviorVerification // tests, determinism and baseline checks (designing)
        ReceiptEmission // RELEASED or HELD with stable reasons (designing)
    AuditLedger // append-only receipt chain (designing) @dep:EscrowEngine
        AppendEvent // injected-time event with previous hash (designing)
        ReplayVerification // receipt and event hash verification (designing)
    Interface // standalone stdlib package (designing) @dep:EscrowEngine,AuditLedger
        CLI // sample, run and report commands (designing)
        Examples // released and held inputs (designing)
        Documentation // usage, security boundary and gene provenance (designing)
    Verification // executable evidence (designing) @dep:Interface
        UnitIntegrationTests // >=10 behavior and tamper tests (designing)
        DeterminismCheck // identical input gives identical receipt (designing)
        HandbackEvidence // HELIX delegated-action packet (designing)
```

## PPR

```python
def evaluate_release(request: EscrowRequest, trust_store: dict[str, bytes]) -> EscrowReceipt:
    request → validate_contract
    step_checks = verify_hmac_steps(request.artifact.steps, trust_store)
    behavior_check = bind_behavior(
        approved=request.policy.approved_behavior_sha256,
        baseline=request.behavior.baseline_sha256,
        observed=request.behavior.observed_sha256,
    )
    reasons = stable_sort(step_checks.failures + behavior_check.failures)
    decision = "RELEASED" if not reasons else "HELD"
    return seal_receipt(request, decision, reasons)

def append_receipt(ledger: Path, receipt: EscrowReceipt, now: str) -> LedgerEvent:
    assert verify_receipt(receipt)
    previous = last_event_hash(ledger)
    return canonical_event(receipt, previous, now) → append_jsonl

# acceptance_criteria:
#   - stdlib only; no wall clock, network or randomness in verdict path
#   - trust secrets are never copied to request, receipt or ledger
#   - missing/tampered signature, baseline drift or nondeterminism always yields HELD
#   - receipt and ledger are replay-verifiable and deterministic
#   - package has README, MIT LICENSE, >=3 examples and >=10 tests
```

## Gene provenance

- `signed_step_metadata` from `HC-PILOT-EXT-001` manifest
  `f36477866369548bb21412f3f13f7f0de48a1720943fdaa1732cf8365db6435c`.
- `behavior_baseline_binding` from `HC-PILOT-HELIX-002` manifest
  `7af0e996fe99d123b5285cb39c28cdfd01895db7895cbf056d675ac6cc8a13bc`.
