# WORKPLAN-HELIX-MONOREPO — 영속 실행 계획 (PGF plan, Large)

> 큰 작업을 배치로 분해·저장. 각 배치는 독립 검증 게이트를 가지며, status JSON으로 재개 가능.
> 한 턴에 전부 못 해도 status를 보고 다음 턴이 정확히 이어받는다 (resume).

## POLICY

```yaml
POLICY:
  vendor_not_reference: true     # 전부 포함 (자기완결)
  single_source_substrate: true  # 내부 로직은 HELIX-Core 단일 출처
  preserve_determinism: true
  verify_each_batch: true        # 배치마다 게이트 통과 후 다음
  dedup_shared_notation: true    # pg/pgf/pgxf 1벌
  gitignore_runtime_outputs: true
  max_verify_cycles: 2
```

## 배치 (의존 순서)

```text
B0 Skeleton          (pending)  skills/ scripts/{explore,exploit}/ seed/ 디렉토리 + MIGRATION.md manifest
B1 SharedNotation    (pending) @dep:B0  pg·pgf·pgxf canonical 1벌 vendor + personas.json 확인 + IdeaFirst pgf content-diff 보고
B2 ExploreSkills     (pending) @dep:B0  14 IdeaFirst 스킬 + schemas vendor → skills/
B3 ExploreScripts+Seed (pending) @dep:B0  .agents/scripts 12+tests → scripts/explore/ ; sdx-catalog·consumed_ledger → seed/
B4 ExploitSkills     (pending) @dep:B0  recreate·pgfr-combo → skills/ ; aggregate·ProjectGenome det.scripts → scripts/exploit/ ; corpus → seed/corpus
B5 PathNormalize     (pending) @dep:B1,B2,B3,B4  '.agents/skills'→'skills/' (36f) + '.agents/scripts'→'scripts/explore/' + 어댑터 배선 점검
B6 UnifiedRunbook    (pending) @dep:B5  RUNBOOK.md (두 시스템 전 기능 호출 매핑) + README 갱신 + validate 확장(스킬 인벤토리 강제)
B7 Verify            (pending) @dep:B6  64 tests + structure validate + dangling-ref=0 + personas reachable + dry pipeline trace
```

## 배치별 검증 게이트

```text
B0: 디렉토리 6개 생성 확인
B1: skills/{pg,pgf,pgxf} 존재 + pgf/discovery/personas.json 존재 + content-diff 기록
B2: skills/ 에 14 explore 스킬 SKILL.md 존재 (파일수 = 소스 합)
B3: scripts/explore/ 12+ py + seed/sdx-catalog, seed/idea-ledger 존재
B4: skills/{recreate,pgfr-combo} 존재 + scripts/exploit/ + seed/corpus 존재
B5: grep '.agents/skills' = 0 hits (skills 내) ; 어댑터가 skills/ 경로 참조
B6: RUNBOOK 에 sdx/tcx/idx/cix/evx/aox/recreate 등 모든 모드 호출 1줄씩
B7: unittest OK(≥64) + helix_validate PASS + dangling=0 + personas OK
```

## 재개 규약 (resume)

- 매 배치 완료 시 `status-HELIX-MONOREPO.json` 의 해당 노드 → "done", 검증 결과 기록.
- 중단 후 재개: status 읽어 첫 non-done 배치부터. 파일 복사는 idempotent(덮어쓰기 안전).
- B5 경로정규화는 **복사 완료 후 1회** — B1~B4 모두 done 이어야 진입.
