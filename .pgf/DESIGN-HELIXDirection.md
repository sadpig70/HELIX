# HELIXDirection Design @v:1.0

## Intent

HELIX의 다음 단계는 플랫폼 수 확대가 아니다. **검증되지 않은 AI 산출물을 증거 기반으로
분류·승인·실행·재현하는 Deterministic Admission Control Plane**으로 전환한다.

핵심 명제:

> AI는 proposal을 만들고, HELIX는 그 주장을 반증 가능한 evidence로 검증하며,
> Constitution이 권한을 제한하고, actuator가 승인된 action만 실행한다.

## Gantree

```text
HELIXDirection // evidence-carrying autonomous spiral (designed) @v:1.0
    TruthPlane // 자기 생태계 agreement를 외부 타당성으로 확장 (priority-0)
        CanonicalState // runtime state가 HANDOFF보다 우선인 단일 snapshot (designed)
        HoldoutRegistry // timestamp/hash-locked unseen corpus (designed) @dep:CanonicalState
        BlindPredictionLedger // prediction-before-oracle, abstain explicit (designed) @dep:HoldoutRegistry
        NoveltyTrial // false-CONDENSE cost와 machine 환원율 측정 (designed) @dep:BlindPredictionLedger
    Constitution // action의 정당성·위험·책임 경계 (priority-1) @dep:CanonicalState
        ActionIntent // risk R0~R3, scope, budget, reversibility (designed)
        EvidenceManifest // artifact hash, issuer, policy version (designed)
        AuthorizationGate // ALLOW|SANDBOX|HUMAN|DENY|RETIRE (designed) @dep:ActionIntent,EvidenceManifest
        StopResumeProtocol // signed stop token and separate resume authority (designed) @dep:AuthorizationGate
        Contestability // replay, appeal, override reason (designed) @dep:AuthorizationGate
    ActuationPlane // advisor에서 폐루프 runtime으로 전환 (priority-2) @dep:TruthPlane,Constitution
        UnifiedCommand // propose->gate->dry-run->execute->handback->ledger (designed)
        FailClosedAdmission // missing=quarantine, thin=sandbox, valid=admit (designed)
        SideEffectBoundary // every write/publish rechecks authorization and stop (designed)
        RecoveryProof // rollback and replay evidence required (designed)
    UtilityPlane // 공급량이 아닌 실제 효익 검증 (priority-3) @dep:ActuationPlane
        FirstWedge // agent handback/approval audit using AHV+Attestra (designed)
        OperationalMetrics // decisions, latency, intervention, false-admit, cost (designed)
        ExternalPilots // three independent workflows (designed) @dep:FirstWedge
    FederationPlane // 외부 생태계 확장은 증명 후에만 (conditional) @dep:UtilityPlane
        SignedMachineClaims // external claim+probe+provenance bundle (designed)
        CompositionIR // typed M-DAG with invariant and rollback contracts (designed)
        CarryingCapacity // owner, SLO, incident, budget, expiry (designed)
        Lifecycle // freeze|merge|retire before new CONDENSE (designed)
```

## PPR

```python
def admit(intent: ActionIntent, proposal: Proposal, evidence: EvidenceManifest) -> GateResult:
    """Deterministically decide whether an AI-proposed action may advance.

    acceptance_criteria:
      - identical inputs and policy version produce identical result
      - missing or mismatched evidence never returns ALLOW
      - R2 requires one human approval; R3 requires two-party approval and dry-run
      - no handback is QUARANTINE; thin is SANDBOX_ONLY
      - every result records replay command, policy version, and reason
    """
    verified = verify_content_hashes(evidence)
    if not verified:
        return DENY
    return evaluate_risk_policy(intent, proposal, evidence)


def blind_machine_trial(candidate: LockedCandidate) -> TrialReceipt:
    """Test the platform-generator claim without label leakage.

    acceptance_criteria:
      - candidate source hash and selection time precede prediction
      - oracle is hidden until prediction receipt is sealed
      - abstain and missing artifact are not counted as success
      - false-CONDENSE cost and post-implementation machine reduction are recorded
    """
    prediction = propose_and_probe(candidate.hidden_oracle_view)
    receipt = seal_prediction(prediction)
    return reveal_oracle_and_score(receipt, candidate.oracle)


def execute_authorized(receipt: GateResult, action: Action) -> ImpactHandback:
    """Close the proposal-to-effect loop without bypassing human control.

    acceptance_criteria:
      - authorization and stop token are checked immediately before each side effect
      - writes remain within approved paths/repos and risk-weighted budget
      - execution emits outcome delta, actual resource use, rollback, and trace evidence
      - failed or expired authority cannot be converted into consumed ledger state
    """
    require_current_authority(receipt)
    require_not_stopped(action.scope)
    result = run_with_blast_radius(action)
    return verify_impact_handback(result)
```

## Phase Gates

| Phase | Go | Kill / downgrade |
|---|---|---|
| T0 State authority | CLI snapshot, report, HANDOFF가 같은 action/hash를 가리킴 | drift 발생 시 actuator 작업 금지 |
| T1 Blind validity | unseen coverage >=80%, existing-machine macro-F1 >=0.80, leakage 0 | baseline 이하이면 `internal corpus router`로 강등 |
| T2 Governance shadow | 30 actions replay, high-risk false-ALLOW 0, risk disagreement <=10% | false-ALLOW 1건이면 자동화 중단 |
| T3 Closed actuator | stop 이후 side effect 0, replay 100%, ungated admission 0 | bypass 1건이면 fail-closed 복귀 |
| T4 Utility pilot | 2시간 내 연결, 주 20 decisions 또는 검토시간 50% 절감 | 8주 내 미달이면 제품 주장을 철회 |
| T5 Federation | 2 independent users, parity eligible execution 100%, owner/SLO/budget 존재 | 조건 미달이면 새 platform/registry 확장 금지 |

## Invariants

- `core` 결정론 경계와 `AI proposal / deterministic decision` 분리를 유지한다.
- test/pack/platform 수를 North Star로 사용하지 않는다.
- `expectation=none`, missing artifact, skipped parity를 성공으로 계산하지 않는다.
- `HANDOFF.md`는 runtime snapshot을 설명할 뿐 권위 있는 상태가 아니다.
- 새 `CONDENSE`는 novel machine 증거 외에 사용자·owner·유지예산·sunset 조건을 요구한다.
- 자동화 범위 확대는 기존 approval을 상속하지 않고 새 approval을 요구한다.

## First Executable Slice

`HELIX State Receipt`를 먼저 설계·구현한다. 동일한 명령이 canonical inputs, policy/gate hashes,
next action, blockers, report freshness를 하나의 hashable receipt로 출력하게 하여 현재 확인된
`HANDOFF=RUN_EXPLOIT` 대 `live=REFRESH_INPUTS` 드리프트를 구조적으로 제거한다.

