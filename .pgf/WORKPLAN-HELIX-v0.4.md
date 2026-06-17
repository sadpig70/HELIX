# WORKPLAN-HELIX-v0.4 — hardening & operationalization

> 설계: `_workspace/PGF-HELIX-v0.4-hardening-design-2026-06-17.md` (PGF design --analyze, F1~F8).
> 목표: v0.3 operational closed-loop controller → **계약 강제 · 크래시 안전 · 테스트 가능한 루프**.
> 불변: core 결정론 경계(now/sim 주입, stdlib, 옵션 import는 함수 내부) · vendored skills/ 미수정.
> 변경 범위: core 신규파일 + 기존 core 일부 + helix.py + schemas + docs + ci + tests.

## POLICY
```yaml
preserve_determinism: true     # core+engines stdlib; clock은 helix.py CLI 엣지만
backward_compatible: true       # 기존 83 테스트 무회귀 (override 우선순위·키 추가만)
verify_each: true
atomic_writes: true             # ledger/corpus/loop-state 원자적 교체
```

## 배치 (의존 순서 — 설계 §5)
```text
1_SchemaEnforce      (designing) #F1 #P0   core/helix_schema.py + helix_validate wire + drift 검사 + test_schema
2_AtomicActuator     (designing) #F2 #F5 #P0  core/helix_io.py + save_ledger/append_corpus_entry atomic + corpus 가드 + test_atomic_io
3_LoopCorePromote    (designing) #F3 #P1 @dep:2  core/helix_loop_state.py + helix.py loop-status + schema wire + test_loop_state
4_SimKindThresholds  (designing) #F4 #P1   helix_diversity sim_kind별 임계 + CALIBRATION 갱신
5_ProvenanceLineage  (designing) #F7 #P2   winner_to_corpus_entry lineage + corpus schema
6_CiHarden           (designing) #F6 #P2   ci.yml scripts compile + 결정론 2회 게이트
7_ReadmeStatusSync   (designing) #F8 #P3   README close-loop 표면 + status 정본
8_VerifyV04          (needs-verify) @dep:1,2,3,4,5,6,7
```

## 검증 게이트
```text
- python -m unittest discover -s tests  -> OK (신규 test_schema/test_atomic_io/test_loop_state 포함, 무회귀)
- python core/helix_validate.py .       -> PASS (schema 강제 + drift 검사 포함)
- python helix.py status --json (2회)   -> byte-identical
- python -m compileall core engines helix.py scripts tests -> OK
- core+engines: 시계·난수·외부의존 0 (helix.py CLI 엣지 제외)
- 원본 불변: skills/·vendor 미수정
```
