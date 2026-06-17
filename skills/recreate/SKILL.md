---
name: recreate
description: "Recreate — 기존 프로젝트 코퍼스(README/DESIGN)를 재조합·변형·이식해 새 프로젝트 DesignSeed를 생성하는 메타 스킬. 코퍼스를 3축(형태·속성·기능)으로 분해 → 3경로(RECOMBINE/MUTATE/TRANSPLANT) × 8 발산도구로 후보 생성 → 정량 차별화 게이트 → 실증 → DesignSeed 출력 → pgf full-cycle 핸드오프. Triggers: recreate, 재조합, 재창조, 프로젝트 재생성, 기존 프로젝트 조합, new project from corpus, project genome, recombine, mutate, transplant, 코퍼스 기반 창조, 새 프로젝트 생성, distant hybrid, negative space, conflict compiler"
user-invocable: true
argument-hint: "run [corpus-dir?] | map | generate [--count N] | seed [candidate?] | status"
depends-on:
  - pg
  - pgf
---

# Recreate — Corpus-to-Project Genome Compiler

> 이미 만들어진 프로젝트들을 **유전자(부품)로 분해**한 뒤, 새 프로젝트 씨앗으로 **재조립**하는 메타 스킬.
> "새 아이디어 1개를 더 고르는 것"이 아니라, 코퍼스의 **생성 문법**을 추출해 재사용 가능한 생성 장치를 돌린다.
>
> 출력 `DesignSeed`는 `pgf full-cycle`의 DESIGN 입력으로 직결된다. (WHAT은 말하고 HOW는 pgf에 맡긴다.)

---

## 실행 런타임 (모든 에이전트 공통)

이 스킬은 **런타임 중립**이다. Claude Code뿐 아니라 codex, kimi cli, antigravity, grok build 등
어떤 AI 에이전트도 수행할 수 있다. 위 frontmatter(`user-invocable`/`argument-hint`/`triggers`/
`depends-on`)와 `/recreate` 슬래시는 **Claude Code 전용 메타데이터**다 — 슬래시·스킬 자동발견이 없는
런타임은 아래 규약으로 실행한다.

1. **진입**: 이 `SKILL.md`를 처음부터 끝까지 읽는다. `{SKILL_DIR}` = 이 파일이 있는 디렉토리
   (`skills/recreate/`). reference 문서는 `{SKILL_DIR}/reference/<name>.md` 를 **파일 열기 도구
   (Read/open/cat 등 런타임이 가진 것)**로 로드한다 — 경로는 항상 이 파일 기준 상대경로다.
2. **호출**: 슬래시가 없으면 모드를 **자연어로 지시**한다 (아래 "호출 방법" 표의 우측 열).
   예: "recreate를 run 모드로 수행해" = `/recreate run`.
3. **산출**: Phase별 산출물을 `<corpus-root>/.recreate/` 에 파일로 남긴다 (아래 "산출물 레이아웃").

## PG/PGF 의존성 & fallback

이 스킬은 PG(PPR/Gantree) 표기와 PGF full-cycle을 사용한다.

- **pg·pgf 스킬 파일에 접근 가능하면** 먼저 로드한다 (정본). Claude Code는 `depends-on`으로 자동 로드.
- **접근 불가하면**(타 런타임에 미설치) — PG는 **parser-free**라 별도 툴체인 없이 이 문서의 표기를
  그대로 해석하면 된다. 최소 표기 요약:

```text
AI_xxx(...)      # AI 인지 연산 (판단/추론/인식/창조). 결정론 계산은 일반 코드로.
AI_make_xxx(...) # 사역: 대상을 ~하게 만든다 (evolve/adapt/converge 등)
a → b → c        # 파이프라인: 좌측 출력이 우측 입력
[parallel] ... [/parallel]   # 병렬 실행 구간 (내부 노드는 독립)
들여쓰기(4칸)     # Gantree 계층 (트리 깊이)
(status)         # 노드 상태: done | in-progress | designing | blocked | needs-verify
# acceptance_criteria:       # 노드 완료 조건 (인라인)
```

- **PGF full-cycle 미가용 시**: Phase 6의 `DesignSeed`까지만 산출하고, 핸드오프는 "이 seed를
  design→plan→execute→verify 순으로 구현하라"는 자연어 지시로 대체한다 (`reference/design-seed.md` §4~5의
  아키타입별 Gantree 골격을 그대로 사용).

---

## 핵심 명제

> **새 프로젝트 = 코퍼스를 3축(형태·속성·기능)으로 분해해 얻은 부품을, 3경로(재조합·변형·이식)와
> 그 안의 발산 도구로 조합하고, 정량 차별화 게이트를 통과시킨 뒤, 실제 후보로 산출해 자기검증한
> DesignSeed다.**

생성은 창작이 아니라 **구조화된 탐색 + 검증**이다. 코퍼스가 이미 생성 문법을 들고 있으므로,
`parts`(재사용 부품)가 비면 후보를 기각해 "코퍼스 기반성"을 강제한다.

---

## 코퍼스가 들고 있는 생성 문법 (스킬의 전제)

거의 모든 코퍼스 프로젝트가 공유하는 **공통 골격(skeleton)** — 생성물도 이를 따라야 한다:

```text
single_question        # "이 X에 대해 Y인가?" — 한 줄 질문
  → deterministic_engine    # 정밀 계산은 코드, 판단만 규칙
  → k_way_verdict      # 3/4분 판정 (cleared/thin/blocked, approve/review/deny …)
  → dual_output        # 기계용 JSON + 사람용 Markdown
  → cli_triplet        # sample / run / report
  → boundary_clause    # "이것은 ~가 아니다"
  → provenance         # lens stack (L1~L25)
```

부가 규율: append-only hash-chained ledger(다수), stdlib-only/무의존.

### 코퍼스 재료의 2계층

- **1차 재료**: 코퍼스 루트 각 폴더의 `README.md` (코드 없음, README only) + `_workspace/project_list.md`.
- **2차 정밀 재료**: 각 프로젝트 전체 소스는 `github.com/sadpig70/{repo}` 에 공개. `{repo}`=폴더명
  (대소문자 혼재: `ADPR`, `afferentcore`, `MCO`, `pact`, `RRE` …). README만으로 엔진 로직·
  `verdict_scheme`·`adapter_contract` 분해가 모호하면 해당 repo의 코드/`.pgf/DESIGN-*.md`를 fetch해 보강.

---

## 호출 방법

슬래시(Claude Code)와 자연어(모든 런타임)는 등가다.

| 슬래시 (Claude Code) | 자연어 지시 (codex/kimi/antigravity/grok 등) | 동작 |
|---|---|---|
| `/recreate run [corpus-dir]` | "recreate를 run 모드로 수행" | 풀 파이프라인: map → generate → differentiate → select → prove → seed |
| `/recreate map` | "recreate map 수행 (코퍼스를 ProjectGene 인벤토리로)" | Phase 0~1만 |
| `/recreate generate [--count N]` | "recreate generate 수행, 후보 N개 (기본 12)" | Phase 2~5: 생성 + 차별화 + 선정 + 실증 |
| `/recreate seed [candidate]` | "recreate seed 수행, 후보 {이름}을 DesignSeed로" | Phase 6: DesignSeed + pgf 핸드오프 안내 |
| `/recreate status` | "recreate 진행 상태 보고" | 현재 진행 상태 |

- `corpus-dir`/대상 생략 시 현재 작업 디렉토리를 코퍼스 루트로 본다 (`project_list.md` + 각 폴더 `README.md`).
- 모드 없이 호출하면 `run`으로 간주.

### 산출물 레이아웃

```text
<corpus-root>/
    .recreate/
        latest.json             # 최신 run 포인터 (symlink 미사용)
        registry.json           # run을 넘어 누적: 생성 프로젝트 · 소비 source · blocked names
        runs/
            {run_id}/           # 불변 — 덮어쓰기 금지 (run_id = {NNN}-{winner-slug})
                input_manifest.json   # 코퍼스 included / 생성물 excluded 고정
                genes.json            # Phase 0~1: 3축 ProjectGene 인벤토리
                inventory.md          # 형태/속성/기능 선반 + lens palette + vocab registry
                candidates.md         # Phase 2~5: 후보 brief + 차별화 verdict + 평가 점수
                avoidance_report.md   # Phase 2b: 재실행 회피 판정 (근거+점수)
                DESIGN-SEED-{Name}.md # Phase 6: pgf DESIGN 입력 (최종 산출)
                status.json           # run 상태
```

> **재실행 안전**: 매 run은 `runs/{run_id}/`에 격리되어 기존 산출을 덮어쓰지 않는다. `registry.json`이
> 생성 프로젝트·소비 source를 누적해 다음 run의 중복(같은 이름·같은 source 조합·같은 문제)을 회피한다.
> 생성 프로젝트 폴더는 코퍼스 스캔에서 제외된다. 상세 → `reference/rerun-avoidance.md`.

---

## 파이프라인 (Gantree)

```text
RecreateMethod // 코퍼스 → 새 프로젝트 DesignSeed (in-progress) @v:2.2
    Phase0_Corpus // 재료 적재·정규화 + run 격리 (in-progress)
        LoadRegistry // .recreate/registry.json 로드 (없으면 빈 registry)
        CreateRunScope // .recreate/runs/{NNN}-pending/ 생성
        BuildInputManifest // 코퍼스 included / 생성 프로젝트 excluded 고정
        LoadList // project_list.md 로드
        ReadReadmes // 각 README 읽기 (생성 프로젝트 제외)
        BuildGenes // 3축 ProjectGene 추출
    Phase1_Inventory // 3축 인벤토리 + 어휘 레지스트리 (designing) @dep:Phase0_Corpus
        [parallel]
        ArchetypeShelf // 형태별 엔진 선반
        PrimitiveShelf // 속성별 mechanism/contract 선반
        LayerShelf // 기능 계층별 슬롯 선반
        LensPalette // 변형 렌즈 팔레트 (L1~L25)
        VocabRegistry // 과밀 어휘 동적 충돌검사 테이블
        GeneGraph // ABCLink 기질 — gene 경량 KG (idea-layer) #idea
        [/parallel]
    Phase1_5_IdeaKernel // 상류 의도 벡터 (idea-layer, 경량) (designing) @dep:Phase1_Inventory #idea
        # input: registry(과거 gap) + inventory(negative-space) + triangulated primitives
        # process: AI_make_idea_kernel → 6 primitive의 측정가능 목표 선언 (NoNameFirst)
        # output: input_manifest.json 의 idea_kernel 블록
    Phase2_Generate // 3경로 × 8 발산도구 → 후보 K개 (designing) @dep:Phase1_5_IdeaKernel
        [parallel]
        GenRecombine // DistantHybridization + LayerFusion + ConflictCompiler + ABCLink #idea
        GenMutate // LensApply + GrammarMutation + NegativeSpaceInversion
        GenTransplant // DomainTransplant + SystemIntegration
        [/parallel]
        GenerateDebateEvolve // 발산 뒤 비판→진화 직렬 루프 (idea-layer P3) (designing) #idea
    Phase2b_Avoidance // 재실행 회피 (과거 run/생성물/소비 source) (designing) @dep:Phase2_Generate
        RejectGeneratedNameCollision // 결정론 hard-reject
        RejectSourceFingerprintCollision // 결정론 hard-reject
        RejectCorpusNameCollision // 결정론 hard-reject
        AssessConsumedSourcePenalty // AI_ 판정 우선 + 점수 로깅
        DiversityGuard // 동질화 연속신호 soft 병치 (idea-layer P1) #idea
        EmitAvoidanceReport // 모든 판단 근거+점수 기록
    Phase3_Differentiate // 코퍼스 대비 의미 차별화 게이트 (designing) @dep:Phase2b_Avoidance
        # overlap 이산임계 + unique_ratio 보조신호 (idea-layer P1) #idea
    Phase4_SelectOrIntegrate // 상보 통합 → 6축 선정 (designing) @dep:Phase3_Differentiate
        DetectComplementary // 같은 문제·다른 강점 군집 탐지 (overlap과 다른 신호)
        Integrate // 상보 군집을 제3 후보로 통합 (능가 시만 채택)
        TournamentSelect // pairwise Elo + idea_fit, 절대점수와 병행 (idea-layer P2) #idea
        Select // 원본+통합 풀에서 6축 top K
    Phase5_Prove // 실증: 후보 brief 산출 + 자기검증 (designing) @dep:Phase4_SelectOrIntegrate
        EvaluatorGate // 결정론 답변가능을 게이트로 승격 (idea-layer P4) #idea
    Phase6_SeedDesign // DesignSeed 출력 + run rename {NNN}-{winner} (designing) @dep:Phase5_Prove
        CrossModelVerify // 합의·증거라벨 + idea_trace 첨부 (idea-layer P5) #idea
    Phase7_UpdateRegistry // winner·소비 source 누적 + latest.json 갱신 (designing) @dep:Phase6_SeedDesign
        MeasureKernelGap // 의도 대비 달성 gap → 다음 kernel 조향 (idea-layer 폐루프) #idea
```

> **Idea Layer (가산)**: `#idea` 노드는 메타 파이프라인층(아이디어 발견·평가)의 가산 앵커다. 기존
> Phase0~7을 대체하지 않고 강화한다. IdeaKernel(상류 의도) → 6 게이트(하류 측정) → kernel_gap(환류)의
> 폐쇄 제어 루프. **결정론 경계**: `#idea` 게이트는 `AI_` 비결정론(메타층)이며, 생성물 verdict 경로와
> Phase2b 이산 hard-reject는 결정론 불변. 정본 → `reference/idea-layer.md`.

> **2게이트 분리**: `Phase2b_Avoidance`(과거 run·생성물 회피)와 `Phase3_Differentiate`(코퍼스 대비 차별화)는
> 보는 대상·신호가 다르다 — 생성 프로젝트는 코퍼스 스캔에서 제외되므로 Phase3가 못 보고, 이름/fingerprint
> 충돌은 Phase3가 안 본다. 상세 → `reference/rerun-avoidance.md §5`.

한 줄 흐름:

```python
load_registry + create_run_scope + input_manifest   # 격리 + 생성물 제외
  → build_genes            # 코퍼스(생성물 제외) → 3축 ProjectGene
  → build_inventory        # [parallel] 형태/속성/기능 선반 + lens + vocab + gene_graph(idea)
  → make_idea_kernel       # idea: 상류 의도 — 6 primitive 목표 선언 (NoNameFirst)
  → generate_candidates    # [parallel] 3경로 × 8 발산도구(+ABCLink) → K=12 후보 → debate_evolve(idea)
  → avoidance_gate (each)  # 과거 run/생성물 회피: hard-reject + AI penalty (+DiversityGuard idea) → avoidance_report
  → differentiate (each)   # 코퍼스 대비 overlap + tag_clash + vocab_clash (+unique_ratio idea) 게이트
  → select_or_integrate    # 상보 군집 통합 → 6축 top 5 (+tournament/idea_fit idea, margin 낮으면 cross-model)
  → prove                  # 실제 brief 산출 + 자기검증 (0개면 실패) + evaluator_gate(idea)
  → emit_design_seed       # runs/{run_id}/DESIGN-SEED-{Name}.md (+idea_trace) (run rename)
  → update_registry        # winner·소비 source 누적 + latest.json + idea_outcome/kernel_gap(idea 폐루프)
  → /pgf full-cycle {Name} # 설계→계획→실행→검증 (핸드오프, run-scoped seed 참조)
```

> **Phase 4가 select-or-integrate인 이유 (자기참조):** recreate 자신이 `method_claude` 하나를 *고른* 게
> 아니라 `method_claude`+`chatgpf`를 *통합*해 만들어졌다. 여러 런타임/페르소나가 낸 후보가 상보적이면
> argmax로 버리지 말고 제3으로 합친다 (`overlap` 낮음 + `complementarity` 높음 → integrate).

---

## 3축 부품 분해 (요약)

코퍼스의 각 프로젝트를 **세 축으로 동시에** 태깅한다. 한 축만으로는 조합 어휘가 빈약하다.

| 축 | 내용 | 역할 |
|---|---|---|
| **형태 (archetype)** | Gate / Mesh / Clearing / Index / Ledger / Stage / Appraisal | 어떤 *엔진 골격*을 재사용 |
| **속성 (primitive)** | mechanism / evidence_model / control_primitive / artifact_type / grammar | 부품의 *인터페이스·어휘* |
| **기능 (layer)** | Sensing / Evidence / Control / Allocation / Release | stack의 *어느 계층 슬롯* |

상세 스키마·분류 기준·7 아키타입 정의·lens palette → `reference/gene-extraction.md`.

---

## 3경로 × 8 발산도구 (요약)

분류는 직교(3경로), 발상은 풍부(8도구).

```text
RECOMBINE  (≥2 부품 합성)
    DistantHybridization   // 먼 domain + 중간 이상 evidence 유사도
    LayerFusion            // Sensing→Evidence→Control→Allocation→Release 각 1개 stack
    ConflictCompiler       // 충돌하는 두 프로젝트를 붙여 새 tension

MUTATE     (1 부품 × 렌즈로 축 교체)
    LensApply              // 코퍼스 lens(L1~L25) 적용, axis 교체
    GrammarMutation        // 과밀 문법 → 신문법 치환
    NegativeSpaceInversion // "하지 않은 행위"를 제품화

TRANSPLANT (메커니즘을 새 도메인/OS로)
    DomainTransplant       // mechanism만 추출 → 도메인 명사 제거 → 재명명
    SystemIntegration      // 다도메인 → 단일 OS 통합
```

각 도구의 코퍼스 정박 실례·생성 알고리즘 → `reference/generation-paths.md`.

---

## 차별화 게이트 (요약)

거의 모든 코퍼스 README가 수작업하던 "It differs from X"를 정량 자동화한다.

```python
overlap >= 0.7  or tag_clash >= 3              -> duplicate   (기각 or pivot)
overlap >= 0.4  or tag_clash >= 2 or vocab_clash -> needs_pivot (변형 후 재투입)
else                                            -> distinct    (통과)
```

- 과밀 어휘 `OVERUSED = [mesh, clearing-market, generic ledger, simple gate, escrow, marketplace]`.
- `vocab_clash`면 distinct여도 **재명명 강제** (ContextCreep 교훈).
- 평가 6축: reuse_leverage · novelty · domain_demand · buildability · boundary_clarity · system_potential.

상세 임계·평가 루브릭·pivot 규칙 → `reference/differentiation.md`.

---

## Select-or-Integrate (Phase 4 — 요약)

`overlap`(결과물 중복도)과 `complementarity`(같은 문제·다른 강점축)는 **다른 신호**다.

```python
overlap 높음                         -> duplicate  (하나 버림 — Phase 3)
overlap 낮음 + complementarity 높음  -> integrate  (제3 후보로 통합 — Phase 4)
overlap 낮음 + complementarity 낮음  -> 독립 후보   (각자 select)
```

- **통합 절차** (method_integrated 생성의 일반화): consensus 추출 → 상보 강점 매핑 → 골격(spine) 선택
  → `AI_make_absorb`(흡수, 병합 아님) → 충돌 해소.
- **통합 게이트**: 통합 후보가 원본 최고 6축점을 **능가할 때만 채택**. 아니면 폐기(원본 유지) — 무분별한
  합치기 방지 (divergence ↔ convergence 짝).
- **적용 조건**(실증): 통합은 **강한 same_problem + 구조적으로 정렬된 상보축**(시간축 lifecycle 등) + 부모가
  못 보는 고유가치가 있을 때만 능가한다. 렌즈 ensemble·임의 layer-stack은 contract만 넓혀 대개 기각.
  margin 근소(±0.1)면 cross-model 합의로 검증. 정본 `reference/differentiation.md §3.2a`. 실증 run 006(양성)/007(음성).
- **multi-runtime**: 여러 모델이 낸 후보의 *모델 간 상보*까지 통합 — recreate 자신이 만들어진 방식의 자동 재현.
  단 점수·통합도 가능하면 cross-model 합의로 (단일 평가자 편향이 다양성을 좁힘).

상세 PPR → `reference/differentiation.md §3`.

---

## 실증 규율 (Phase 5 — 필수)

**통합 방법론은 반드시 실제 후보를 산출해 자기검증한다. 후보 0개면 방법론 실패로 본다.**
각 후보 brief는 다음 5개 check를 통과해야 한다:

- source projects ≥ 2개 사용
- 이름/mechanism에 과밀 어휘 없음
- 최근접 sibling 대비 명시적 차별점 보유
- cli_triplet + stdlib-only skeleton 적합
- single_question이 결정론적 엔진으로 답변 가능

---

## DesignSeed 핸드오프 (Phase 6)

최종 산출 `DESIGN-SEED-{Name}.md`는 `pgf full-cycle`의 DESIGN 입력 계약이다. 필드:

```text
name · single_question · archetype · layers_used · reuse_plan(copy/parametrize/redesign)
· lens_stack · domain · verdict_scheme · cli_triplet · boundary · acceptance_seeds
· differentiation_note
```

핸드오프: `/pgf full-cycle {Name}` 실행 시 이 seed를 DESIGN 단계 입력으로 전달.
DESIGN은 archetype·reuse_plan·verdict_scheme을 Gantree+PPR로 전개한다.

상세 계약·필드 매핑·pgf 연결 → `reference/design-seed.md`.

---

## Reference 문서 가이드

| 문서 | 내용 | 로드 시점 |
|---|---|---|
| `reference/gene-extraction.md` | 3축 ProjectGene 스키마, 7 아키타입·5 layer 정의, lens palette(L1~L25), 추출 PPR | Phase 0~1 (map) |
| `reference/generation-paths.md` | 3경로 × 8 발산도구 상세 알고리즘 + 코퍼스 anchor 실례 | Phase 2 (generate) |
| `reference/rerun-avoidance.md` | run 격리·registry·input_manifest 계약, 2게이트 분리, 회피 알고리즘 | Phase 0/2b/7 (재실행) |
| `reference/differentiation.md` | 정량 게이트 임계, vocab registry, 6축 평가 루브릭, select-or-integrate | Phase 3~5 |
| `reference/design-seed.md` | DesignSeed 계약, 필드 매핑, pgf full-cycle 핸드오프 | Phase 6 (seed) |
| `reference/idea-layer.md` | IdeaKernel·6 게이트·폐쇄 제어 루프 (메타 파이프라인 가산 레이어) | Phase 1.5~7 (`#idea` 노드) |

> PG 표기법(Gantree/PPR/AI_/→/[parallel])과 PGF 실행 모드는 `pg`·`pgf` 스킬이 정본이다. 중복 정의하지 않는다.

---

## 공진화 (배포 형태)

이 스킬은 1회용 절차가 아니라 **재사용 도구**다. 코퍼스가 50→100개로 커져도 동일 파이프라인을 재사용하며,
커질수록 차별화 게이트가 강해지고(과밀 어휘 누적) 부품 선반이 풍부해진다 — `vocab_registry`·`lens_palette`가
자동 확장되는 공진화 속성을 갖는다.

---

## 정직한 경계

- lens 역추출은 Provenance 미기재 시 추론 — `(inferred)` 플래그로 구분.
- overlap/임계(0.4/0.7), tag_clash(2/3)는 코퍼스 초기값 — 성장 시 재보정.
- domain_demand·system_potential은 외부 신호 없이 AI 판단 — 시장 검증은 범위 밖.
- RECOMBINE이 이종 아키타입 엔진을 stack 시 verdict_scheme 충돌 가능 — DESIGN에서 해소.
- GrammarMutation 신문법도 재포화 가능 — vocab_registry 동적 충돌검사로 완화하되 완전 차단 아님.
- idea-layer 게이트(DiversityGuard/Tournament/CrossModel 등)는 `AI_` 비결정론 — 메타층 한정. 생성물
  verdict 경로와 Phase2b 이산 hard-reject는 결정론 불변. 임베딩 임계(cos 0.8)는 차용값으로 재보정 대상.
