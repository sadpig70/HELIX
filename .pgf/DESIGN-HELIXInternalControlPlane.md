# DESIGN - HELIXInternalControlPlane

## Intent

`_workspace/HELIX-FUTURE-DIRECTION.md`를 실행 가능한 내부 Control Plane으로 구현한다.
외부 pilot, T1 재상향, FederationPlane, 6번째 플랫폼은 범위 밖이다.

## Design Invariants

- deterministic core: clock/network/AI 금지, 시간과 서명 키는 주입
- fail-closed: 증거 부재, 상태 drift, lock 충돌은 실행 금지
- reuse existing Constitution/authorization/actuator receipts
- atomic durable state and idempotent transaction resume
- AI는 Condense proposal만 작성하고 deterministic gate가 accept/reject
- Phase gate를 건너뛰지 않는다

## Gantree

HELIXInternalControlPlane // self-governing internal change control (in-progress) @v:1.0
    TrustClosure // close known fail-open and provisioning gaps (designing)
        FailClosedRegistry // absent handback is quarantined from consumed ledger (designing)
        SignedStopAuthority // stop/resume receipts optionally require HMAC (designing)
        SerializedLedger // process-safe append adapter and verified append (designing)
        ProvisioningGate // AHV dependency preflight (designing)
        Utf8Validation // Windows validation output is encoding-safe (designing)
    TransactionKernel // pure transaction state machine (designing) @dep:TrustClosure
        TransactionStates // legal states and transitions (designing)
        TransactionSeal // canonical hash and optional HMAC verification (designing)
        IdempotentEvents // duplicate event is a no-op, illegal event fails (designing)
        RecoveryAudit // history replay reconstructs current state (designing)
    TransactionRuntime // atomic persistence and actuation bridge (designing) @dep:TransactionKernel
        AtomicStore // atomic checkpoint with exclusive lock (designing)
        AdmissionBridge // map run_admission result to transaction states (designing)
        ResumeBridge // resume terminal/incomplete transactions safely (designing)
        TransactionCLI // init/run/status/verify commands (designing)
    CondenseAcceptance // deterministic acceptance of AI meta proposals (designing) @dep:TransactionRuntime
        ProposalContract // machine/pack/probe/parity proposal schema (designing)
        EvidenceGate // require probe and parity evidence hashes (designing)
        ZeroKernelGate // BUILD_ON_PLATFORM forbids kernel changes (designing)
        ProposalReceipt // sealed accept/reject receipt (designing)
    PlatformComposition // typed five-stage internal pipeline (designing) @dep:CondenseAcceptance
        StageContract // route/clear/certify/attest/score typed envelopes (designing)
        ProvenanceChain // transaction and parent receipt propagation (designing)
        FailureIsolation // stop pipeline after first failed stage (designing)
        CompositionReplay // deterministic replay verification (designing)
    InternalMetrics // non-T4 internal optimization signals (designing) @dep:PlatformComposition
        MetricsContract // block/rollback/replay/stale/cost counters (designing)
        LedgerAggregation // derive metrics only from verified transaction history (designing)
        ClaimBoundary // explicitly non-product/non-T4 (designing)
    Verification // cross-perspective closure (designing) @dep:InternalMetrics
        AcceptanceTests // node criteria tests (designing)
        QualityReview // security and maintainability review (designing)
        ArchitectureReview // design-to-module consistency (designing)
        FullRegression // validate and complete test suite (designing)

## PPR

```python
def fail_closed_registry(registry: dict, migration: Optional[dict], state_hash: str) -> dict:
    admissions = registry_admissions(registry, migration, state_hash)
    return ledger(entries=[p for p in registry if admissions[p] == "ADMIT"])
    # acceptance_criteria:
    # - absent/thin/breach never enter consumed
    # - only a live anchored migration may admit absent legacy data

def transition_transaction(tx: Transaction, event: Event) -> Transaction:
    require(verify_transaction(tx))
    if event.id in tx.applied_event_ids:
        return tx
    require(event.type in LEGAL_TRANSITIONS[tx.state])
    return seal(apply(tx, event))
    # acceptance_criteria:
    # - identical tx/event yields identical output
    # - illegal transitions and tampered history fail closed

def accept_condense_proposal(proposal: dict, evidence: dict) -> Receipt:
    require(probe_hashes_match(evidence))
    require(parity_passed(evidence))
    if proposal.action == "BUILD_ON_PLATFORM":
        require(proposal.kernel_changes == [])
    return seal(deterministic_verdict(proposal, evidence))
    # acceptance_criteria:
    # - AI text alone can never authorize corpus mutation

def compose_platform_stages(stages: list[StageEnvelope]) -> CompositionReceipt:
    for stage in REQUIRED_ORDER:
        require(stage.input_parent == previous.receipt_sha256)
        if stage.status != "passed":
            return sealed_failure(stage, no_later_stages=True)
    return sealed_success(stages)
    # acceptance_criteria:
    # - order/provenance violations reject; failure stops later stages
```

## Scale Decision

실행 leaf는 28개로 PGF Large 기준(>30) 미만이다. `(decomposed)` 분리가 없으므로 PGXF를
구축하지 않는다. 노드 증가로 30개를 초과할 때 `pgxf build`를 적용한다.

## Acceptance

- 모든 신규 core 함수가 stdlib-only이고 determinism scan을 통과한다.
- fail-open registry 경로가 제거된다.
- transaction state를 atomic 저장하고 history로 재검증할 수 있다.
- Condense proposal과 5-stage composition이 deterministic receipt로 검증된다.
- 내부 metrics가 T4/product claim과 명시적으로 분리된다.
- 전체 테스트와 `helix_validate`가 통과한다.
