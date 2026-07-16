# HELIXCorpusSupply AdmissionPlane @v:1.0

## Gantree

```text
AdmissionPlane // deterministic dual-tier authority (done) @v:1.0
    HardGate // non-compensable source and safety checks (done)
        SchemaCheck // manifest contract validation (done)
        ProvenanceCheck // pinned origin and source hash (done)
        LicenseCheck // declared SPDX-like license evidence (done)
        EvidenceTruthCheck // source/license hashes match bytes under injected evidence root (done)
        IdentifierCheck // stable corpus ID and immutable revision (done)
    GenerativeGate // broad but honest generation admission (done) @dep:HardGate
        GeneRequirement // at least one reusable gene (done)
        HypothesisLabel // unverified machine remains hypothesis (done)
        DuplicateIdentityCheck // same ID with different bytes is conflict (done)
        DuplicateSourceCheck // same source hash under another ID is refused (done)
    EvidenceGate // strict promotion authority (done) @dep:GenerativeGate
        PriorAdmissionCheck // require admitted generative state (done)
        RevisionLineageCheck // supersedes hash binds prior generative receipt (done)
        ReproductionCheck // command plus passed result (done)
        BehaviorEvidenceCheck // behavior fingerprint and supporting symbols (done)
        DeterminismCheck // explicit deterministic verdict (done)
        HumanReceiptCheck // approve verdict bound to manifest hash (done)
    LedgerAuthority // append-only replayable decisions (done) @dep:EvidenceGate
        CanonicalEvent // stable event body (done)
        HashChainAppend // bind previous event hash (done)
        IdempotentReplay // identical decision returns existing event (done)
        ConflictRefusal // contradictory same-tier decision fails closed (done)
        LedgerVerify // recompute complete chain (done)
```

## PPR

```python
def decide_admission(manifest: dict, tier: Literal["generative", "evidence"],
                     state: dict, review: Optional[dict]) -> Decision:
    """Pure gate decision; no file writes."""
    # acceptance_criteria:
    #   - hard gate is never score-compensated
    #   - evidence requires prior generative ADMITTED
    #   - review.approved and review.manifest_sha256 must bind current manifest
    #   - reasons are stable sorted identifiers
    hard = hard_gate(manifest)
    if hard:
        return Decision("QUARANTINED", sorted(hard))
    if tier == "generative":
        return generative_gate(manifest)
    return evidence_gate(manifest, state, review)

def append_admission_event(path: str, decision: Decision, now: str) -> dict:
    """Append one hash-chained event atomically enough for a single-writer ledger."""
    # acceptance_criteria:
    #   - prior bytes are never rewritten; append is flush+fsync under single-writer policy
    #   - event hash verifies after append
    #   - exact replay is idempotent
    #   - malformed existing chain blocks append
    verify_ledger(path)
    return append_jsonl(build_event(decision, previous_hash(path), now))
```
