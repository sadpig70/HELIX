# HELIX Parity·Provenance Evidence Workplan

이 문서는 `_workspace/HELIX Parity·Provenance 증거 강화 설계안.md`를 HELIX repo에서 단계별로 실행하기 위한
PG/PGF 작업계획서다. 목표는 HELIX의 `project → pack → platform` 주장을 문서 설명이 아니라 재실행 가능한
evidence chain으로 승격하는 것이다.

```text
ParityProvenanceEvidencePlan // HELIX evidence chain 구축 (designing) @v:1.0
    ContractLayer // schema and canonical receipt contracts (planned)
    RepresentativePilot // five representative pack evidence chains (planned) @dep:ContractLayer
    RunnerLayer // source-lock/parity/provenance deterministic runners (planned) @dep:ContractLayer
    RegistryLayer // multi-platform evidence registry and coverage dashboard (planned) @dep:RepresentativePilot,RunnerLayer
    CIGates // fail-closed validation in HELIX CI (planned) @dep:RegistryLayer
    ExpansionPlan // 62-pack staged rollout and independent reproduction path (planned) @dep:CIGates
```

## 1. 타당성 검토

### Verdict

타당하다. 현재 HELIX는 다음 상태까지 도달했다.

- Corpus supply plane: `24 items / 24 Generative / 5 Evidence / quarantine 0`.
- Phase 3: tracked validator 기준 `PHASE3_COMPLETE_READY_FOR_PHASE4`.
- Phase 4 방향: 6개 Phase 3 프로젝트가 기존 platform pack으로 흡수될 준비 완료.
- 현 약점: pack이 어느 source commit·machine evidence·parity receipt·review를 거쳐 release 가능한지
  다중 repo 전체에서 봉인하는 증거층은 아직 별도 체계로 닫혀 있지 않다.

따라서 parity·provenance 강화는 선택적 문서 보강이 아니라 HELIX의 핵심 thesis를 제3자가 재검증 가능한
형태로 만드는 필수 후속 작업이다.

### Scope judgment

전체 62팩을 곧바로 V3/P4 이상으로 올리는 것은 과대 범위다. 먼저 5개 대표 pack MVP를 구축한 뒤,
schema와 runner가 안정되면 62팩으로 확장한다.

### 제약

- 외부 독립 검증자, 비대칭 서명, 외부 anchor는 외부 권위와 키 운영이 필요하므로 MVP에서는 `declared/internal`
  등급으로만 표현한다.
- Source checkout이 필요한 live parity는 네트워크/권한 실패를 `UNAVAILABLE`로 분리한다. 성공으로 간주하지 않는다.
- 기존 플랫폼 repo의 CI 변경은 각 repo 권한과 상태 확인 후 별도 단계로 진행한다.

## 2. 증거 등급 기준

```text
ParityLevels // behavioral equivalence levels
    P0_StaticTrace // source/pack mapping only
    P1_GoldenVector // stored source output vs current pack
    P2_LiveDifferential // fixed source commit vs current pack in same run
    P3_Invariant // shared machine invariants
    P4_Adversarial // boundary/conflict/malicious cases
    P5_IndependentReproduction // clean-env independent rerun

ProvenanceLevels // lineage and trust levels
    V0_Declared // project name/url only
    V1_SourceLocked // repo+commit+file/license hashes
    V2_TransformationTraced // source→machine→pack edges
    V3_ReproductionVerified // parity receipt + CI run
    V4_IndependentlyAttested // independent reviewer/reproducer
    V5_ExternallyAnchored // external ledger-head anchor
```

MVP 목표는 대표 5팩에 대해 `P2+P3 / V3`다. 외부 thesis 대표 증거는 이후 `P2+P3+P4+P5 / V4`로 올린다.

## 3. 대표 pack 선정

MVP는 플랫폼별 대표성과 현재 repo 접근성을 우선한다.

| Priority | Platform | Pack / Project | 이유 | MVP target |
|---:|---|---|---|---|
| 1 | Attestra | `ProofEscrow` | Phase 3 FC-001, source+behavior evidence 결합 | P2+P3/V3 |
| 2 | Attestra | `AuthorityArbiter` | delegated authority/custody handback 대표 | P2+P3/V3 |
| 3 | Attestra | `GraphQuarantine` | quarantine path machine, 실패 경계 대표 | P2+P3/V3 |
| 4 | Routestra | `ContractRelay` | Routestra 흡수 pack, normalized errors/custody 대표 | P2+P3/V3 |
| 5 | Attestra | `HookCircuit` | hook dispatch/circuit breaker, adversarial 확장 후보 | P2+P3/V3 |

`DriftIsolator`는 2차 대표 후보로 둔다. 1차에서 Attestra 편중이 크지만 Phase 3 outcome상 실제 흡수 비율이
Attestra 5 / Routestra 1이므로 MVP에서는 현재 evidence density를 우선한다.

## 4. PGF 작업 분해

### 4.1 ContractLayer

```text
ContractLayer // evidence artifact schemas (planned)
    SourceLockSchema // fixed source identity schema (planned)
    MachineEvidenceSchema // machine claim and source symbol support schema (planned)
    ParityContractSchema // source/pack entrypoints, cases, comparator policy (planned)
    ParityReceiptSchema // parity run result and seal schema (planned)
    ProvenanceSchema // source→machine→pack→receipt statement schema (planned)
    EvidenceRegistrySchema // multi-platform coverage registry schema (planned)
```

PPR:

```python
def build_contract_layer() -> ContractResult:
    """
    acceptance_criteria:
      - schemas are JSON-schema draft-07 compatible
      - each schema has schema/version field
      - no schema implies author identity from SHA-256 alone
      - tests validate minimal valid and invalid examples
    """
    schemas = AI_design_schema_set(source_design, current_corpus_contracts)
    tests = create_schema_validation_tests(schemas)
    return verify(schemas, tests)
```

Deliverables:

- `schemas/source-lock.schema.json`
- `schemas/machine-evidence.schema.json`
- `schemas/parity-contract.schema.json`
- `schemas/parity-receipt.schema.json`
- `schemas/provenance-statement.schema.json`
- `schemas/evidence-registry.schema.json`
- `tests/test_evidence_schemas.py`

### 4.2 RunnerLayer

```text
RunnerLayer // deterministic evidence commands (planned)
    CanonicalJson // stable digest/comparison helper (planned)
    SourceLockRunner // create/verify source locks from corpus manifests (planned)
    MachineEvidenceRunner // validate machine evidence file support (planned)
    ParityRunner // run P1/P2/P3 parity levels (planned)
    ReceiptVerifier // verify receipt seal and comparator hash (planned)
    ZeroKernelChangeRunner // validate pack-only changes (planned)
```

PPR:

```python
def run_parity(pack: PackSpec, level: list[str]) -> ParityReceipt:
    """
    acceptance_criteria:
      - source commit missing -> UNAVAILABLE, not VALID
      - branch-only source -> UNVERIFIABLE
      - comparator hash mismatch -> UNVERIFIABLE
      - output mismatch -> BREACH
      - no wall-clock in receipt hash; now is injected
    """
    source = verify_source_lock(pack.source_lock)
    contract = verify_parity_contract(pack.contract)
    source_result = execute_source_if_available(source, contract)
    pack_result = execute_pack(contract)
    receipt = compare_and_seal(source_result, pack_result, contract)
    return receipt
```

Deliverables:

- `scripts/evidence/source_lock.py`
- `scripts/evidence/parity_runner.py`
- `scripts/evidence/provenance_registry.py`
- `scripts/evidence/zero_kernel_change.py`
- `tests/test_evidence_runners.py`

### 4.3 RepresentativePilot

```text
RepresentativePilot // five representative chains (planned)
    ProofEscrowChain // source-lock→machine→parity→provenance (planned)
    AuthorityArbiterChain // delegated authority representative (planned)
    GraphQuarantineChain // quarantine path representative (planned)
    ContractRelayChain // Routestra representative (planned)
    HookCircuitChain // hook/circuit representative (planned)
```

각 대표 pack의 최소 evidence bundle:

```text
evidence/packs/{platform}/{pack}/
    source-lock.json
    machine-evidence.json
    parity-contract.json
    parity-cases/
    provenance.json
    receipts/
        parity-receipt.json
```

MVP에서 source checkout이 불가능한 pack은 `P1/V2`로 낮추고, `reason`을 receipt에 남긴다. 단, 대표 목표는
최소 3개 pack `P2+P3/V3`, 나머지 2개 `P1+P3/V2` 이상이다.

### 4.4 RegistryLayer

```text
RegistryLayer // coverage and consistency (planned)
    EvidenceRegistry // one tracked registry for HELIX + platforms (planned)
    CoverageReport // P/V coverage dashboard (planned)
    StaleDetector // pack/kernel/comparator changes mark stale (planned)
    OrphanDetector // registry pack missing in platform/project tree (planned)
```

Deliverables:

- `evidence/registry.json`
- `docs/PARITY-PROVENANCE.md`
- `scripts/evidence/coverage.py`
- `tests/test_evidence_registry.py`

### 4.5 CIGates

```text
CIGates // fail-closed checks (planned)
    SchemaGate // schemas and registry valid (planned)
    ReceiptGate // receipt seal valid (planned)
    CoverageGate // representative MVP thresholds met (planned)
    StaleGate // no stale representative pack (planned)
    CleanTreeGate // no generated drift after tests (planned)
```

CI MVP gate:

```bash
python scripts/evidence/provenance_registry.py validate --registry evidence/registry.json
python scripts/evidence/coverage.py --registry evidence/registry.json --min-representatives 5
```

### 4.6 ExpansionPlan

```text
ExpansionPlan // beyond MVP (planned)
    Inventory62 // classify all packs A-F (planned)
    SourceLockAll // V1 for all source-backed packs (planned)
    GoldenParityAll // P1 for all feasible packs (planned)
    LiveParityPriority // P2 by priority queue (planned)
    InvariantAdversarial // P3/P4 machine-level suites (planned)
    IndependentReproduction // V4 representative set (planned)
    ExternalAnchor // V5 ledger head anchor (planned)
```

## 5. PGXF 인덱스 전략

이 작업은 30노드를 넘고 장기화될 가능성이 높다. 따라서 MVP 이후에는 PGXF로 durable index를 둔다.

```text
.pgf/parity-provenance/
    INDEX.md                 // node id, file, status, dependencies
    DESIGN-ParityProvenance.md
    WORKPLAN-ParityProvenance.md
    status-ParityProvenance.json
    nodes/
        ContractLayer.md
        RunnerLayer.md
        RepresentativePilot.md
        RegistryLayer.md
        CIGates.md
        ExpansionPlan.md
```

초기 MVP는 이 문서 하나로 충분하다. 노드가 실제로 30개를 넘거나 2회 이상 compaction/handoff가 발생하면
위 PGXF 구조로 분해한다.

## 6. 단계별 실행 계획

### Stage 0 — Baseline audit

Goal: 현재 증거 상태와 source availability를 정직하게 분류한다.

Tasks:

1. 5개 대표 pack의 README, tests, source corpus manifest, Phase 3 registry binding 확인.
2. 각 대표 pack을 `P0/V0~V2`로 초기 등급화.
3. source checkout 가능 여부와 license evidence 상태 확인.

Acceptance:

- `docs/PARITY-PROVENANCE.md` 초안에 baseline table 존재.
- 대표 5팩 모두 initial classification 보유.

### Stage 1 — Contract schemas

Goal: evidence artifact의 최소 계약을 고정한다.

Tasks:

1. 6개 schema 작성.
2. valid/invalid fixtures 작성.
3. schema tests 추가.

Acceptance:

- `python -m unittest tests.test_evidence_schemas -q` 통과.
- 전체 tests/validator 통과.

### Stage 2 — Source lock and machine evidence MVP

Goal: 대표 5팩에 대해 V1/V2 기반을 만든다.

Tasks:

1. corpus manifest에서 source-lock 초안 생성.
2. 각 pack README/source에서 machine evidence 생성.
3. source hash/license hash와 manifest binding 검증.

Acceptance:

- 대표 5팩 source-lock valid.
- machine evidence가 registry gene binding과 불일치하지 않음.

### Stage 3 — Parity contract and runner

Goal: P1/P2/P3를 실행할 runner를 만든다.

Tasks:

1. canonical comparator 구현.
2. parity-contract schema/runner 구현.
3. representative pack 1개(`ProofEscrow`)로 end-to-end receipt 생성.
4. 실패 verdict `BREACH/UNAVAILABLE/UNVERIFIABLE/STALE` 테스트.

Acceptance:

- `ProofEscrow` receipt가 `VALID` 또는 source 불가 시 명시적 `UNAVAILABLE`.
- 실패 verdict가 success로 세탁되지 않음.

### Stage 4 — Representative 5-pack pilot

Goal: 5개 representative evidence chain 생성.

Tasks:

1. 5개 pack에 source-lock/machine/parity/provenance bundle 생성.
2. receipt seal 검증.
3. registry에 등록.
4. coverage report 생성.

Acceptance:

- 5 representative chains tracked.
- 최소 3개가 `P2+P3/V3`, 나머지 2개가 `P1+P3/V2` 이상.
- coverage dashboard에 stale/breach/source unavailable count 표시.

### Stage 5 — CI closure

Goal: evidence chain drift를 CI에서 차단한다.

Tasks:

1. registry validator 추가.
2. representative coverage gate 추가.
3. clean-tree gate와 통합.

Acceptance:

- CI에서 evidence registry와 receipt seal 검증.
- source unavailable은 명확한 non-VALID 상태로 보고.

### Stage 6 — Expansion and independent reproduction

Goal: 62팩 확장과 외부 thesis 증거 강화.

Tasks:

1. 62팩 inventory A-F.
2. 우선순위별 V1/P1 확대.
3. 대표 pack을 P4/P5/V4로 승격.
4. 외부 anchor 설계는 ledger 안정 후 별도 승인으로 진행.

Acceptance:

- `evidence/migration/pack-inventory.json` 존재.
- 대표 set의 independent reproduction plan 존재.

## 7. 리스크와 대응

| Risk | Impact | Mitigation |
|---|---|---|
| source repo unavailable | live parity blocked | verdict `UNAVAILABLE`, golden P1 fallback |
| source lock incomplete | provenance overclaim | V-level 자동 강등 |
| comparator too permissive | false parity | comparator hash+policy review, invariants |
| producer verifies own pack | self-proof risk | actor roles/conflict disclosure |
| CI network flake | false failure | `UNAVAILABLE` distinct from `BREACH`, but not success |
| 62팩 scope explosion | delivery delay | representative MVP first, PGXF split later |
| SHA/signature confusion | trust overclaim | docs and schema limitations fields |

## 8. 다음 실행 노드

다음 턴의 최우선 작업은 Stage 0이다.

```text
Stage0BaselineAudit // representative evidence baseline (ready)
    SelectFivePacks // confirm representative list (ready)
    ReadBindings // registry + manifest + README cross-check (ready)
    ClassifyPV // assign initial P/V levels (ready)
    SaveReport // docs/PARITY-PROVENANCE.md baseline section (ready)
```

Stage 0은 코드 변경보다 증거 상태 감사가 핵심이다. 이 결과가 있어야 schema와 runner가 과도하거나 부족하지 않게 설계된다.
