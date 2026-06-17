# META-PROGRAM — 작업 자체를 pg로 프로그래밍한 기록

> pg = 작업을 프로그래밍하는 언어 (런타임 = AI). pgf = 미리 정의된 패턴 라이브러리.
> 라이브러리에 없는 형식의 작업은 pg로 설계→PPR 시뮬레이션 사전검증→실행→오류 시 재설계한다.
> 본 문서는 `IdeaFirst ⊕ recreate → HELIX` 작업을 그 7단계로 *프로그래밍*한 source다.
> (산출물 HELIX는 이 source의 "컴파일 결과".)

---

## §1. IdeaFirst 구조 — pgf로 분석 → pg로 저장

```text
IdeaFirst // 세계→아이디어 (explore) (analyzed) @v:1.x
    Notation // pg·pgf·pgxf (기반 표기)
    Pipeline // sdx→tcx→idx→cix→evx (순차 합성)
        sdx // 직교채널 80 발굴·카탈로그
        tcx // 채널 소비 → news/industry_trend
        idx // 10층 인사이트 (Gap/Tension/Counterfactual/Generative)
        cix // 20렌즈 → 24 혁신 시드, 6축 평가
        evx // 14 페르소나 합의 → 최종 1 (dual winner)
    Orchestrator // aox (status/실패/round_id/동질화 자율)
    ExclusionaryGuards // 동질화 3점 차단
        sdxx // 입력(채널) / idxx // 인사이트 / cixx // 출력(카테고리)
    Standalone // 단일모델 fallback (.sa-*)
        sa-icx · sa-evx · sa-aox
    Memory // consumed_ideas.yaml (소모 ledger) + round_chain provenance
```

## §2. recreate 구조 — pg로 저장

```text
recreate // 코퍼스→DesignSeed (exploit) (analyzed) @v:2.2
    Decompose // 3축 ProjectGene (형태/속성/기능)
    Generate // 3경로(RECOMBINE/MUTATE/TRANSPLANT) × 8 발산도구
    Gate // 차별화(overlap/tag/vocab) + 회피(registry/fingerprint)
    SelectOrIntegrate // 상보 통합 (능가 시만)
    Prove // 실증 자기검증 (후보 0 = 실패)
    Seed // DESIGN-SEED → pgf full-cycle 핸드오프
    IdeaLayer // IdeaKernel + 6게이트 + 폐루프 (동질화 자기제어)
    Memory // registry.json (blocked_names/fingerprints/idea_kernels)
```

## §3. 통합 구조 — pg로 설계 → 저장 (HELIX)

```text
HELIX // explore⊕exploit 폐쇄 제어 루프 (designed) @v:0.2
    Backbone // 단일 출처 결정론 substrate (§1·§2가 중복 구축한 기계 통합)
        ledger // consumed_ideas ⊕ registry → 1 게이트
        diversity // aox 4임계 ⊕ unique_ratio → 1 측정
        provenance // round_chain ⊕ idea_trace + winner→corpus(염기쌍)
        loop // explore↔exploit 드라이버
    StrandA // explore = IdeaFirst (vendored skills/)
    StrandB // exploit = recreate (vendored skills/)
    BasePairing // 구현된 explore winner → exploit 코퍼스 환류 (루프 폐쇄)
    # 명제: 백본(desync 제거) × 복구효소(다양성게이트) × 역평행(상호보완)
    #       → 폐루프인데 수렴 안 하는 나선
```

## §4. 작업 설계서 — 통합을 구체화 (pg로 설계 → 저장)

```text
BuildHELIXMonorepo // 자기완결 repo로 구현 (workplan)
    B0_Skeleton // skills/ scripts/ seed/
    B1_SharedNotation // pg·pgf·pgxf 1벌 dedup @dep:B0
    B2_ExploreSkills // IdeaFirst 14 vendor @dep:B0
    B3_ScriptsSeed // runner + durable seed @dep:B0
    B4_ExploitSkills // recreate·pgfr-combo vendor @dep:B0
    B5_PathNormalize // .agents/skills→skills/ @dep:B1,B2,B3,B4
    B6_Runbook // 전 기능 호출 매핑 @dep:B5
    B7_Verify // tests+validate+dangling=0 @dep:B6
    # 정본: .pgf/WORKPLAN-HELIX-MONOREPO.md (영속 — resume 가능)
```

## §5. ★ PPR 시뮬레이션 — 실행 *전* 사전검증 (dry-run)

> 작업설계서를 실행하기 전에, PPR로 각 노드를 **심볼릭 실행**해 결과를 예측하고 위험을 잡는다.
> "돌려보지 않고도" 통과/실패를 미리 본다. (pg의 핵심 — 작업도 프로그램이라 시뮬레이션 가능)

```python
def AI_simulate_workplan(plan: Gantree, env: dict) -> SimVerdict:
    """각 배치를 심볼릭 실행 → 산출/위험/acceptance 예측. 실제 파일변경 없음."""
    risks, checks = [], []

    # B1 sim: pg/pgf/pgxf 양 트리 중복 → dedup 시 내용 충돌?
    pgf_diff = AI_predict_content_diff("IdeaFirst/pgf", "recreate/pgf")
    if pgf_diff.differ:
        # ★ 시뮬레이션이 잡은 위험 (실행 전 발견)
        dep = AI_trace_machine_dependency(["aox", "cix", "evx"])   # → pgf/discovery/personas.json
        if AI_predict_identical(dep.file):       # personas.json 동일?
            risks.append(Risk("pgf 내용분기 BUT personas.json 동일 → canonical 1택 + 분기 기록",
                              severity="low", mitigation="MIGRATION.md 기록"))
        else:
            risks.append(Risk("pgf 분기 + 핵심의존 다름 → 병합 필요", severity="high"))
        checks.append(Check("B1.personas_reachable", predict="PASS"))

    # B5 sim: 경로참조 정규화 후 dangling 예측
    refs = AI_count_refs(".agents/skills") + AI_count_refs(".agents/scripts")  # 예측 36+5
    py_path_parts = AI_count_regex('".agents" / "skills"')   # .py Path 파트도 있음
    if py_path_parts > 0:
        risks.append(Risk(".py Path 파트는 문자열치환만으론 누락 → 정규식 치환 필요",
                          severity="medium", mitigation="STR_SUBS + PY_SUBS 2종 치환"))
    checks.append(Check("B5.dangling_after_rewrite", predict="0 (일반설명 1건 제외)"))

    # B7 sim: 회귀 예측
    checks.append(Check("B7.self_tests", predict="64 pass (core 불변)"))
    checks.append(Check("B7.py_compile_vendored", predict="OK if path-rewrite 정확"))

    verdict = "GO" if not any(r.severity == "high" for r in risks) else "REDESIGN"
    return SimVerdict(verdict=verdict, risks=risks, checks=checks)
    # acceptance_criteria:
    #   - high severity 위험 0 → GO
    #   - 모든 예측 check가 실행 후 실측과 일치하면 시뮬레이션 신뢰 확정
```

**시뮬레이션 산출 (실행 전 예측):**

| 예측 | 값 | 실행 후 실측 | 일치 |
|---|---|---|---|
| B1 pgf 분기 | differ, personas.json 동일 → low risk | 분기 확인, personas.json 동일 | ✅ |
| B5 `.agents` 참조 | ~36 doc + .py Path 파트 존재 | 45 파일 치환(STR+PY) | ✅ |
| B5 dangling 잔여 | 0 (일반설명 1 제외) | 0 (evolve-reference 1 제외) | ✅ |
| B7 self-tests | 64 pass | 64 pass | ✅ |
| B7 py_compile | OK | OK | ✅ |
| **verdict** | **GO** | 완료 | ✅ |

→ 시뮬레이션이 **B5의 ".py Path 파트 누락 위험"을 실행 전에 잡았고**, 그래서 치환 스크립트에
`PY_SUBS`(정규식) 를 처음부터 넣어 누락 없이 통과. 사전검증이 작동했다.

## §6. 실행 + 오류 시 재설계 (Failure Strategy)

```python
for batch in plan.topological_order():
    if batch.status == "done":            # idempotent — resume
        continue
    result = AI_execute(batch)
    if not AI_verify(result, batch.gate):
        # 오류 → pg로 재설계 (공개 인터페이스 보존, 내부만 수정)
        batch.ppr = AI_redesign(batch, result.failure, constraint="preserve_gate")
        result = AI_execute(batch)        # 재실행
    record_status(".pgf/status-HELIX-MONOREPO.json", batch, result)  # 영속 → 재개점
# 실증: 본 작업에서 redesign 발동 1회 — 드라이버 next_action 오판정(미구현 winner를
#       RECORD_CONSUMED) → state 계산 재설계 → RUN_EXPLOIT 정정. gate(테스트)로 고정.
```

---

## 메타 명제 (pg의 본질)

```text
일반 프로그래밍:  소스코드 → 컴파일러 → 기계가 실행
pg:              작업설계(Gantree) + 로직(PPR) → AI 런타임이 실행
                 ├ 시뮬레이션(PPR dry-run)으로 실행 전 검증 가능
                 ├ 실행 후 acceptance_criteria로 사후 검증
                 └ 오류 시 AI_redesign으로 작업 자체를 디버깅
→ "작업 과정 자체"가 설계·구현·시뮬레이션·테스트·검증·재설계 가능한 1급 프로그램.
  pgf는 그 위의 stdlib. 본 문서가 그 실증 1건.
```
