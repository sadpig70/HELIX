# WORKPLAN-HELIX — 실행 계획 (PGF plan)

> DESIGN-HELIX.md → 실행 가능한 작업 계획. POLICY + 노드 순서 + 검증.

## POLICY

```yaml
POLICY:
  max_verify_cycles: 2
  stdlib_only: true            # ProjectGenome CI 철학 계승 — 외부 의존 금지
  determinism: strict          # core helper 시계/네트워크/AI 금지 (주입)
  federate_not_fuse: true      # 엔진 복사 금지 — 어댑터/계약만
  single_source_of_truth: true # ledger/diversity/provenance 중복 정의 금지
```

## 노드 순서 (의존 위상정렬)

```text
1. HelixCore.Fingerprint     (done)   — ProjectGenome fingerprint 재사용 승격
2. HelixCore.Ledger          @dep:1   — 통합 재사용 차단 게이트
3. HelixCore.Diversity       @dep:1   — 통합 동질화 측정
4. HelixCore.Provenance      @dep:2   — 계보 + winner→corpus 환류
5. HelixCore.Loop            @dep:3,4 — 폐루프 드라이버
6. HelixCore.Validate        @dep:2,3 — 구조·스키마 검증기
7. HelixSchemas              @dep:2,3,5 — JSON Schema 4종
8. HelixEngines (어댑터)      @dep:1-6 — explore/exploit 계약 문서
9. HelixDocs                 — README + ARCHITECTURE + SUBSTRATE-CONTRACT
10. HelixExamples            @dep:2,5 — 샘플 ledger + 1라운드 산출
11. HelixTests               @dep:1-6 — unittest 6종
12. VERIFY                   @dep:11  — 테스트 + validate + 3관점
```

## 검증 게이트

```text
- core helper 전부 stdlib import만 (외부 패키지 0)
- core helper 전부 now/sim 주입식 (Date.now·random·embedding 호출 0)
- unittest 6종 green
- helix_validate PASS (구조 + 스키마 일치)
- 3관점: acceptance(완료기준) · quality(중복/재사용) · architecture(federate 유지)
```
