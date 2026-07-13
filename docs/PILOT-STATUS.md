# HELIX External Pilot Status

> 갱신: 2026-07-13
> 상태: **PAUSED_BY_USER**

## 결정

정욱님의 현재 작업 상황에 따라 P5_5 외부 pilot track은 여기서 중지한다. 이는 실패나
T4 판정이 아니라 **실세계 모집·8주 운영을 시작하지 않기로 한 명시적 범위 결정**이다.

- 외부 operator 모집: 시작하지 않음
- 외부 8주 운영: 시작하지 않음
- 실제 `real_owned_stakes` attestation: 0건
- T4 utility: `NOT JUDGED`
- product claim: 보류
- thesis: `GOVERNED INTERNAL SYSTEM` 유지

## 중지 전 완료된 작업

- `PILOT-SIM`: 3개 합성 persona, 21 handback, ledger/replay `21/21`
- 합성 결과의 정직 경계: T4 `not_passed`, 외부 증거 주장 없음
- `provenance_class=real|synthetic` receipt 봉인
- CLI 생략 시 `unclassified` fail-closed
- `synthetic`·legacy/unclassified decision의 North Star/T4 metrics 제외
- 명시적 real decision이 있는 ledger만 real participant로 집계
- 관련 CLI·metrics·T4·문서 회귀 테스트 완료
- 최종 검증: `python core/helix_validate.py .` PASS, `695 tests OK`

PGF 기록:

- `.pgf/DESIGN-PilotSim.md`
- `.pgf/WORKPLAN-PilotSim.md`
- `.pgf/status-PilotSim.json`
- `.pgf/DESIGN-PilotProvenanceBoundary.md`
- `.pgf/WORKPLAN-PilotProvenanceBoundary.md`
- `.pgf/status-PilotProvenanceBoundary.json`

## 재개 조건

외부 pilot은 자동 재개하지 않는다. 정욱님이 새로 명시적으로 재개를 지시할 때만 다음
순서로 시작한다.

1. kit 공개 범위 재결정
2. 독립 외부 operator 3곳 이상 모집
3. participant preflight에서 `--provenance-class real` 및 별도 single-writer ledger 확인
4. 8주 운영과 sealed ledger/sidecar/owned-stakes 수집
5. `core.helix_t4.t4_verdict`로 최종 판정

재개 전까지 외부 pilot의 정확한 다음 작업은 **없음**이다.
