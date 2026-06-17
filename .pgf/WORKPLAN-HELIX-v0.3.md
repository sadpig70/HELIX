# WORKPLAN-HELIX-v0.3 — codex 리뷰 적용 (read-only → operational closed loop)

> 출처: `_workspace/PGF-HELIX-system-analysis-2026-06-17.md` (codex PGF design --analyze 리뷰).
> 목표: actuator 층을 더해 "선언적 폐루프"를 "실제 폐루프"로. 권장 순서(리뷰 §5) 채택.

## POLICY
```yaml
preserve_determinism: true     # core+adapters stdlib; clock/sim은 CLI(엣지)에서만
verify_each: true
idempotent_writes: true        # ledger/corpus append 재실행 안전
```

## 배치 (의존 순서)
```text
P0-1 CloseLoopActuator      (designing)  helix.py close-loop: winner→ledger append + corpus write (idempotent)
P0-2 DiversityRepairSemantics (designing) unique_ratio collapse → repair_required(trigger 포함); 작은 pool keyword k 적응
P1-1 LedgerMergeCollision   (designing) @dep:none  merge를 full match contract(is_consumed)로 dedup/merge
P1-2 LiveArtifactResolver   (designing)  loaders: latest 없을 때 round dir 결정론 선택
P1-3 SemanticSimInjection   (designing)  helix.py status --sim lexical|module:function (core 밖에서만 호출)
P2-1 SchemaValidator        (designing)  validate_corpus_entry/loop_state/thresholds + winner_to_corpus_entry project 가드
P2-2 CalibrationHarness     (designing)  scripts/calibrate_diversity.py (rounds JSONL → thresholds JSON)
P3-1 StatusDocsSync         (designing)  status/docs 테스트수 드리프트 제거
```

## 검증 게이트
```text
- unittest discover OK (신규 테스트 포함) · 결정론 2회 동일
- helix_validate PASS
- close-loop 재실행 idempotent (already_recorded)
- core/adapters에 시계·난수·외부의존 0 (CLI 제외)
- driver/JSON 출력 정상
```
