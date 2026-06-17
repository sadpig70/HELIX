# design-seed — DesignSeed 계약 · pgf 핸드오프

> Recreate Phase 6 (`seed` 모드 / `/recreate seed`)의 정본.
> 선정·실증된 후보를 `pgf full-cycle`의 DESIGN 입력으로 변환한다. 이 스킬의 종착점.

---

## 1. DesignSeed 스키마 (pgf DESIGN 입력 계약)

```python
DesignSeed = dict = {
    "name": str,                    # CamelCase 프로젝트명 (과밀 어휘 금지)
    "single_question": str,         # "이 X에 대해 Y인가?" — blockquote 한 줄
    "archetype": str,               # Gate/Mesh/Clearing/Index/Ledger/Stage/Appraisal
    "layers_used": list[str],       # 기능 계층 stack (LayerFusion 산출일 때)
    "reuse_plan": list[dict],       # 부품별 {source, kind, reuse_cost: copy|parametrize|redesign}
    "lens_stack": list[str],        # 적용 lens (L1~L25)
    "domain": str,                  # target 도메인
    "verdict_scheme": list[str],    # k-way 판정 (예: ["cleared","thin","blocked"])
    "cli_triplet": list[str],       # ["sample","run","report"] (코퍼스 표준 계승)
    "boundary": str,                # "이것은 ~가 아니다"
    "acceptance_seeds": list[str],  # DESIGN의 acceptance_criteria 씨앗
    "differentiation_note": str,    # 최근접 siblings 대비 명시 차별점
    "idea_trace": Optional[dict],   # idea-layer: 아래 §6 (kernel→gene→candidate→seed 계보)
}
```

> `idea_trace`는 idea-layer가 켜진 run에서만 채워지는 **선택 필드**다. 없으면 기존 7요소 seed 그대로(동작 불변).

---

## 2. 출력 PPR

```python
def emit_design_seed(winner: Candidate) -> DesignSeed:
    return {
        "name": winner["name"],
        "single_question": winner["single_question"],
        "archetype": AI_pick_archetype(winner),
        "layers_used": winner.get("layers", []),
        "reuse_plan": AI_plan_reuse(winner["parts"]),       # copy/parametrize/redesign 표기
        "lens_stack": winner["applied_lenses"],
        "domain": winner["target_domain"],
        "verdict_scheme": AI_design_verdicts(winner),       # k-way 판정 설계
        "cli_triplet": ["sample", "run", "report"],
        "boundary": AI_draft_boundary(winner),
        "acceptance_seeds": AI_seed_acceptance(winner),
        "differentiation_note": winner["brief"]["differentiation"],
        "idea_trace": build_idea_trace(winner, kernel, verify_report),   # idea-layer (kernel 있을 때만)
    }
    # acceptance_criteria:
    #   - skeleton 7요소 모두 채워짐 (single_question..provenance)
    #   - reuse_plan 각 부품에 reuse_cost 명시
    #   - verdict_scheme은 3 또는 4-way
    #   - EvaluatorGate(idea-layer P4) PASS — single_question이 결정론 엔진으로 답 가능 (REJECT면 seed 차단)
    #   - idea_trace 있으면 strength_label ∈ {verified, claimed} (CrossModelVerify, idea-layer P5)
```

---

## 3. 산출 파일 형식 — `DESIGN-SEED-{Name}.md`

```markdown
# DESIGN-SEED-{Name}

> Recreate 산출. `/pgf full-cycle {Name}` 의 DESIGN 입력.

## 한 질문
> {single_question}

## 분류
- archetype: {archetype}
- layers_used: {layers}
- domain: {domain}
- lens_stack: {L...}

## 재사용 계획 (reuse_plan)
| 부품 | source project | kind | reuse_cost |
|---|---|---|---|
| ... | ... | engine/contract/verdict/ledger | copy/parametrize/redesign |

## 판정 (verdict_scheme)
{k-way: 예 cleared / thin / blocked}

## 인터페이스 (skeleton)
- cli_triplet: sample / run / report
- output: JSON (기계) + Markdown (사람)
- 무의존 stdlib-only

## acceptance_criteria 씨앗
- {seed 1}
- {seed 2}

## 경계 (boundary)
> 이것은 {~}가 아니다.

## 차별점
{differentiation_note}

## Idea Trace (idea-layer, 선택)
- kernel_id: {IK-NNN}
- problem_frame: {어떤 결핍/마찰/비대칭}
- method_archetype: {source_grounded_linking / program_search / ...}
- deterministic_engine_hint: {MVP 결정론 엔진이 답할 단일 질문}
- proof_surface: {CLI/report/test/fixture}
- strength_label: {verified | claimed}   # CrossModelVerify
- why_not_existing_projects: {anti_examples 대비 차별}
```

> `Idea Trace`는 PGF full-cycle이 WHAT을 더 정확히 이해하게 하는 보조 계약이다 — 특히
> `method_archetype`(어떤 검증 패러다임을 쓸지)과 `deterministic_engine_hint`(EvaluatorGate 통과 근거).
> 기존 필드는 모두 유지. 정본 → `idea-layer.md §4·§7`.

---

## 4. pgf full-cycle 핸드오프

DesignSeed → pgf 전환 매핑:

| DesignSeed 필드 | pgf DESIGN 전개 |
|---|---|
| `archetype` | 해당 아키타입의 표준 Gantree 골격으로 노드 분해 |
| `reuse_plan` | `copy`=기존 코드 이식 노드, `parametrize`=인자화 노드, `redesign`=신규 PPR def |
| `verdict_scheme` | 판정 엔진 노드 + 각 verdict 분기 PPR |
| `layers_used` | 계층별 모듈(Sensing/Evidence/Control/Allocation/Release)을 Gantree 서브트리로 |
| `acceptance_seeds` | 각 노드의 `# acceptance_criteria:` 인라인으로 전개 |
| `cli_triplet` | `sample`/`run`/`report` 진입점 노드 |
| `boundary` | DESIGN의 MVP Scope 섹션 |
| `idea_trace.method_archetype` | DESIGN의 검증 패러다임 선택 (program_search → evaluate 함수 노드 강조) |
| `idea_trace.deterministic_engine_hint` | 결정론 엔진 노드의 single_question 시드 (EvaluatorGate 통과분) |

핸드오프 실행 (슬래시 ↔ 자연어 등가):

```
/pgf full-cycle {Name}                 # DESIGN-SEED-{Name}.md 를 DESIGN 입력으로 전달
/pgf full-cycle {Name} --with-review   # 설계 후 다관점 review 게이트 삽입 (권장)
```

- **pgf 스킬이 있는 런타임**: 위 슬래시(또는 "pgf full-cycle {Name}을 with-review로 수행" 자연어).
- **pgf 미가용 런타임**: 이 seed를 "design → plan → execute → verify 순으로 구현하라"는 자연어로
  지시한다. 아래 §5의 아키타입별 Gantree 골격을 DESIGN 출발점으로 그대로 사용.

pgf는 DESIGN → plan → execute → verify를 자율 실행한다. Recreate는 **씨앗까지만** 책임지고,
구현은 검증된 pgf 라이프사이클(또는 동등한 자연어 절차)에 위임한다.

---

## 5. 아키타입별 pgf Gantree 골격 힌트

DESIGN 전개 시 archetype에 따라 기본 노드 구조를 제안한다 (pgf design이 상세화):

```text
Gate       → InputSpec → RuleEngine(N rules) → SeverityAggregate(verdict) → Report
Mesh       → Adapters(normalize) → Assess → Price → LedgerFold → Report
Clearing   → SupplyBook + DemandBook → PriorityClear → Posture → Report
Index      → Observations → Score → Tier → Report
Ledger     → Envelope → Canonicalize → HashChain → Attest → Verify
Stage      → Profile → RiskBand → StagedSchedule(rollback triggers) → Report
Appraisal  → Asset → Simulate(cycle) → Settle → Bankability → Report
```

각 골격은 코퍼스의 동일 아키타입 프로젝트(예: Gate=SettleMesh, Appraisal=WasteStack)를
참조 구현으로 삼아 reuse_plan을 채운다.
