# idea-layer — IdeaKernel · 6 게이트 · 폐쇄 제어 루프

> Recreate의 **메타 파이프라인층(아이디어 발견·평가)** 정본. Phase0~7을 *대체하지 않고* 가산 앵커한다.
> 3 AI-idea 보고서(`ai_idea_방법론_{chatgpt,claude,kimi}.md`)에서 도메인을 제거한 메타 메커니즘을
> recreate에 이식한 통합 설계의 실행 사양. 설계 출처: `_workspace/ai_idea_방법론/통합_claude_idea_방법론.md`.

---

## 0. 핵심 명제

> **IdeaKernel(상류 의도)과 6 게이트(하류 검증)는 같은 6개 primitive를 lifecycle의 두 지점에서
> 표현한 것이다. kernel이 목표를 *선언*하고, 게이트가 달성을 *측정*하고, registry가 그 gap을 다음
> run의 kernel로 *환류* — recreate는 `closed_loop` primitive를 자기 자신에 적용한 폐쇄 제어 루프가 된다.**

이 레이어는 새 Phase를 만들지 않는다. 기존 Phase0~7 노드를 강화하는 가산 패치다 (파이프라인 재작성 금지).

---

## 1. 결정론 경계 (지배 제약 — 혼동 시 설계 붕괴)

```text
메타 파이프라인층 (아이디어 발견·평가)            →  AI_ 비결정론 허용
  - IdeaKernel 생성, DiversityGuard·Tournament·DebateEvolve·CrossModelVerify·ABCLink, idea_fit
  - 이유: "어떤 아이디어를 만들/고를까"는 본질적으로 판단

생성물 verdict 경로 (DesignSeed가 약속하는 deterministic engine)  →  결정론 불변
  - single_question → deterministic_engine → k_way_verdict
  - EvaluatorGate가 이 경계의 문지기 (생성물 verdict가 결정론인지 *검사*)
  - 이유: 생성된 프로젝트는 stdlib-only·재현가능·machine-checkable 해야 함

Phase2b 이산 hard-reject (name/fingerprint 충돌)  →  결정론 불변
  - DiversityGuard(AI_)는 soft-penalty 계층에 병치, 이산 게이트를 흐리지 않는다
```

---

## 2. Triangulation 규율 (인식론적 토대)

3보고서 중 **2자 이상 합의(triangulation)가 잡히는 메커니즘만** 정식 채택한다. 단일 보고서 주장은
보수적으로 강등(참고용). 도메인 수치(picomolar, 3.4×, 91% 등)는 **전이 대상 아님** — 구조만 전이한다.

```python
def AI_extract_transferable(reports: dict[str,str]) -> list[Primitive]:
    """3보고서에서 도메인(신약/단백질/재료) 제거 후 전이가능 메커니즘만 추출."""
    signals   = {r: AI_extract_mechanisms(reports[r]) for r in ["chatgpt","claude","kimi"]}
    consensus = AI_triangulate(signals, min_agreement=2)    # ≥2자 합의만 채택
    return AI_map_to_recreate_primitives(consensus, schema=SIX_PRIMITIVES)
    # acceptance_criteria:
    #   - 채택 primitive는 ≥2 보고서 근거 보유 (provenance에 출처 기록)
    #   - 도메인 수치는 전이하지 않는다 (구조만)
```

---

## 3. 통합 척추 — 6 Primitive를 두 지점에서

각 primitive는 **상류 kernel 필드(의도)로 태어나** **하류 게이트(측정)로 검증되고** recreate Phase에 앵커된다.

| # | Primitive | ① 상류 kernel 필드 (의도) | ② 하류 게이트 (측정) | 앵커 Phase | 결정론 클래스 |
|---|---|---|---|---|---|
| P1 | `diversity_guard` | `target_nonoverlap`, `anti_examples` | **DiversityGuard** — unique_ratio·island refill | Phase2b + Phase3 | 메타 `AI_` |
| P2 | `surrogate_before_selection` | `surrogate_score_hint` | **TournamentSelect** + `idea_fit` | Phase4 | 메타 `AI_` |
| P3 | `closed_loop` | (kernel→registry 전체 사이클) | **GenerateDebateEvolve** | Phase2 loop | 메타 `AI_` |
| P4 | `program_search` | `deterministic_engine_hint` | **EvaluatorGate** — evaluate-함수 규율 | Phase5 | **결정론**(verdict 경로) |
| P5 | `evaluator_skepticism` | `kill_conditions` | **CrossModelVerify** — 합의·증거라벨 | Phase6 + Phase7 | 메타 `AI_` |
| P6 | `provenance_memory` | `kernel_id`, `idea_trace` | **ABCLink** + `idea_outcome` registry | Phase1 + Phase7 | 메타 `AI_` |

> P4만 결정론 경계 위에 앉는다. EvaluatorGate 자체는 메타 판단이지만, 그것이 강제하는 대상(생성물 verdict)은 결정론 불변.

---

## 4. 상류 — IdeaKernel (run 전 의도 벡터)

`IdeaKernel`은 project name이 아니다. 구현 전의 **탐색 의도·검증 방식·회피 조건**을 담는 중간 산출물이며,
각 필드는 6 primitive의 측정가능 목표를 선언한다. 전(前) run의 gap(`next_run_emphasis`)을 입력받아 조향된다.

```python
IdeaKernel = dict = {
    "kernel_id": str,                   # P6 provenance ("IK-{NNN}")
    "problem_frame": str,               # 어떤 결핍/마찰/비대칭을 다루는가
    "method_archetype": list[str],      # §6 매핑 (program_search, source_grounded_linking 등)
    "target_nonoverlap": list[str],     # P1 목표 — 겹치면 안 되는 축 (≥3)
    "target_nonoverlap_score": float,   # P1 수치목표 (unique_ratio 하한)
    "lens_stack": list[str],            # 우선 사용 lens (L1~L25)
    "source_search_queries": list[str], # 소스 탐색 질의 (≥5)
    "surrogate_score_hint": str,        # P2 — 후보를 어떻게 먼저 점수화하나
    "deterministic_engine_hint": str,   # P4 — MVP 결정론 엔진이 답할 단일 질문
    "anti_examples": list[str],         # P1 보조 — 만들면 안 되는 유사 프로젝트
    "kill_conditions": list[str],       # P5 — 발견 즉시 폐기 조건 (≥3)
}

def AI_make_idea_kernel(registry: dict, inventory: dict, primitives: list) -> IdeaKernel:
    """run 전 탐색 의도. 이름이 아니라 문제/검증/회피를 먼저(NoNameFirst).
       전 run의 gap을 saturation 입력으로 받아 조향(폐루프)."""
    saturation   = AI_profile_registry_saturation(registry)     # 과거 gap 누적 반영
    empty_spaces = AI_find_negative_space(inventory, registry)
    method_mix   = AI_select_method_archetypes(primitives, empty_spaces)
    return {
        "kernel_id": AI_make_stable_id("IK"),
        "problem_frame": AI_formulate_problem_frame(empty_spaces, method_mix),
        "method_archetype": method_mix,
        "target_nonoverlap": AI_list_nonoverlap_axes(registry, saturation),
        "target_nonoverlap_score": AI_set_diversity_target(saturation),
        "lens_stack": AI_choose_lenses(inventory["lens"], method_mix, saturation),
        "source_search_queries": AI_generate_source_queries(empty_spaces, method_mix, min_count=5),
        "surrogate_score_hint": AI_define_surrogate_score(method_mix),
        "deterministic_engine_hint": AI_define_engine_question(method_mix),
        "anti_examples": AI_find_near_generated_projects(registry, k=5),
        "kill_conditions": AI_define_kill_conditions(registry),
    }
    # acceptance_criteria (IdeaKernelAcceptance):
    #   - source_search_queries ≥ 5, target_nonoverlap ≥ 3, kill_conditions ≥ 3
    #   - deterministic_engine_hint 존재 (P4 목표 필수)
    #   - NoNameFirst: project name을 이 단계에서 확정하지 않음
```

산출: run-scoped `input_manifest.json`의 `idea_kernel` 블록 (`rerun-avoidance.md §3.3`).

---

## 5. 하류 — 6 게이트 (실행 사양)

> 각 게이트는 기존 Phase 노드 *옆에* 가산 앵커된다. 본 절은 시그니처·acceptance·앵커를 고정한다.
> kernel bias 주입과 토너먼트의 흐름 위치는 각 정본(`generation-paths.md`·`differentiation.md`) 참조.

### 5.1 DiversityGuard (P1) — `rerun-avoidance.md` Phase2b soft 계층

동질화를 연속신호로 측정해 이산 충돌검사를 보완. 임계 미달 시 K를 늘리지 않고 island 재발산.

```python
def measure_homogenization(candidates: list[Candidate], corpus_genes: list[Gene]) -> DiversityReport:
    embs = [AI_embed(c.brief + c.mechanism + c.single_question) for c in candidates]
    dup_pairs = [(i, j) for i < j if cosine(embs[i], embs[j]) > 0.8]   # Si et al. 차용 임계
    unique_ratio = (len(candidates) - len({j for _, j in dup_pairs})) / len(candidates)
    corpus_embs  = [AI_embed(g.summary) for g in corpus_genes]
    nearest = [max(cosine(e, ce) for ce in corpus_embs) for e in embs]
    return DiversityReport(unique_ratio=unique_ratio, dup_pairs=dup_pairs,
                           corpus_regression=[s for s in nearest if s > 0.8])
    # acceptance_criteria: 모든 유사도가 avoidance_report.md에 점수로 병합. 임계 0.8은 코퍼스 초기값(재보정).

def enforce_diversity(report: DiversityReport, candidates: list[Candidate]) -> list[Candidate]:
    if report.unique_ratio < 0.5:                       # 풀 절반 이상 의미중복 → K 늘리기 금지
        clusters  = AI_cluster(candidates)              # Co-Scientist Proximity
        survivors = [AI_pick_representative(cl) for cl in clusters]
        gaps      = AI_find_untouched(corpus_axes, survivors)
        refills   = generate_candidates(focus=gaps, paths=DIVERGENT_ONLY)   # FunSearch island 재발산
        return survivors + refills
    return candidates
    # acceptance_criteria: 결과 풀 unique_ratio ≥ 0.5(재측정). 재발산 후보는 미사용 의미축 명시(감사).
```

> 앵커: Phase2b `AssessConsumedSourcePenalty`와 같은 AI-판정 계층에 병치. 이산 hard-reject 불변, DiversityReport는 `avoidance_report.md`에 병합.

### 5.2 TournamentSelect (P2) — `differentiation.md §3.3` Select 보강

6축 절대점수의 캘리브레이션 약점을 pairwise 비교로 보완. 절대점수와 **둘 다** 내고 불일치 시 CrossModelVerify로.

```python
def tournament_select(candidates: list[Candidate], k_top: int = 5) -> list[Candidate]:
    elo = {c.id: 1500 for c in candidates}
    for a, b in scheduled_pairs(candidates):            # 전체쌍 또는 스위스
        winner, loser = AI_debate_compare(a, b, axes=SIX_AXES)   # 모의 토론 우열
        elo = update_elo(elo, winner, loser)
    return sorted(candidates, key=lambda c: elo[c.id], reverse=True)[:k_top]
    # acceptance_criteria:
    #   - 6축 절대점수 top과 토너먼트 top의 불일치를 보고(갈리면 cross-model 합의로 판정)
    #   - 가능하면 AI_debate_compare를 multi-runtime로 (P5와 결합)
```

### 5.3 GenerateDebateEvolve (P3) — `generation-paths.md §4` 발산 뒤 루프

발산 1회로 끝내지 않고 비판→진화를 반복(claude Generate-Debate-Evolve). pgf Convergence Loop와 동형.

```python
def reflection_critic(candidate: Candidate) -> Critique:
    return Critique(
        feasibility   = AI_assess_buildability(candidate),       # cli_triplet+stdlib로 되는가
        novelty       = AI_assess_novelty(candidate, corpus),
        verifiability = AI_can_decide_by_engine(candidate.single_question),   # P4와 연결
        weakness      = AI_find_weakness(candidate))
    # acceptance_criteria: 약점이 구체적 재명명/재초점 액션으로 환원 가능

def generate_debate_evolve(seeds: list[Candidate], max_rounds: int = 2) -> list[Candidate]:
    pool = seeds
    for round in range(max_rounds):
        critiques = [reflection_critic(c) for c in pool]
        weak = [c for c, cr in zip(pool, critiques) if cr.novelty < THRESH or not cr.verifiability]
        if not weak:
            break                                                # 안정화 — 조기 종료
        evolved = [AI_make_recombine(top, lens=cr.weakness) for top, cr in survivors_of(pool)]
        pool = [c for c in pool if c not in weak] + evolved      # 흡수 재조합(병합 아님)
    return pool
    # acceptance_criteria:
    #   - 라운드마다 약점 후보 수 단조감소(수렴) — 아니면 dry로 보고
    #   - max_rounds 안에 수렴 못하면 산출 보존 + 보고(무한루프 금지)
```

### 5.4 EvaluatorGate (P4) — `design-seed.md`/`differentiation.md §4` prove 승격 (결정론 문지기)

FunSearch/AlphaEvolve 교훈: 기계검증 가능한 evaluate 함수가 있을 때만 자율생성이 유효.
recreate의 결정론 verdict engine = 그 evaluate 함수임을 게이트로 명시. prove 5-check 중 1개를 게이트로 승격.

```python
def evaluator_gate(seed: DesignSeed) -> Verdict:
    checks = {
        "engine_decidable":         AI_can_decide_by_engine(seed.single_question),   # 네트워크/시계/AI 호출 없이
        "verdict_machine_checkable": is_kway_deterministic(seed.verdict_scheme),     # 입력→고정출력
        "evaluate_definable":        has_cli_triplet_skeleton(seed),                 # sample/run/report로 호출 가능
    }
    if not all(checks.values()):
        return Verdict("REJECT", reason="evaluate 함수 미정의 — 자율생성 적용 불가(주관/모호 목표)")
    return Verdict("PASS")
    # acceptance_criteria:
    #   - REJECT 시 Phase2 롤백(비싼 구현 전 차단)
    #   - PASS = "이 아이디어는 FunSearch류 자율탐색에 올릴 수 있다"의 증명
```

### 5.5 CrossModelVerify (P5) — `rerun-avoidance.md` Phase7 + IdeaQualityGate

단일 LLM 평가자는 명백한 오류를 놓친다(A-Lab novelty 사후정정). 점수·novelty를 multi-runtime 합의로,
실증과 주장을 분리 라벨. `registry.cross_model`이 이미 존재 → 자연 결합.

```python
def cross_model_verify(seed: DesignSeed, runtimes: list[str]) -> VerifyReport:
    votes     = [AI_score_on_runtime(seed, rt) for rt in runtimes]
    consensus = aggregate_consensus(votes)                       # 단일 평가자 편향 완화
    evidence  = read_gate_evidence(seed.run_id)                  # GATE-EVIDENCE (exit_code 근거)
    label     = "verified" if evidence.all_passed else "claimed" # 실증/주장 분리
    return VerifyReport(consensus_score=consensus, strength_label=label,
                        dissent=[v for v in votes if diverges(v, consensus)])
    # acceptance_criteria:
    #   - novelty/6축 점수가 단일 runtime이 아니라 합의로 기록
    #   - strength_label='claimed'면 registry status를 'seeded'에 멈추고 publish 보류(A-Lab 교훈)
    #   - margin 근소(±0.1)면 cross-model 재투표 (differentiation.md §3.2a 관례 재사용)
```

### 5.6 ABCLink (P6) — `generation-paths.md §1` RECOMBINE 합류

A-B(부품1)+B-C(부품2)→미검증 신규 A-C. DistantHybridization을 Swanson ABC로 명시 구조화.

```python
def abc_link(genes: list[Gene]) -> list[Candidate]:
    kg = build_gene_graph(genes)                                # gene-extraction.md §7 경량 KG
    for A, C in distant_pairs(kg):                              # 직접 엣지 없는(미연결) 쌍
        B = AI_find_bridge(A, C, kg)                            # 중간항(공유 control_primitive 등)
        if B and AI_is_nonobvious(A, C, B):
            yield make_candidate(parents=[A, B, C], path="ABCLink")
    # acceptance_criteria:
    #   - parts ≥ 2 (ABC는 자연히 ≥3) — 코퍼스 기반성
    #   - A-C가 기존 fingerprint/코퍼스명과 충돌하면 Phase2b hard-reject로 회수
```

---

## 6. Method Archetype 매핑 (과학 AI → recreate)

도메인 복붙 금지(`NoGenericScienceCopy`). 과학 AI 패러다임을 recreate 도메인으로 변환한다.

| 과학 AI 패러다임 | recreate MethodArchetype | primitive | 생성 효과 |
|---|---|---|---|
| LLM 가설 생성 | `hypothesis_generation` | P3 | problem_frame·single_question 강화 |
| 멀티에이전트 토론 | `tournament_reflection` | P2,P3 | Phase4 비판/순위/통합 강화 |
| RAG/지식그래프 | `source_grounded_linking` | P6 | source query·ABC 연결 강화 |
| 생성형 diffusion | `conditional_recombination` | P1 | 조건부 조합, 무작위 재조합 억제 |
| 능동학습/BO | `active_selection` | P2 | 불확실성/정보가치로 다음 후보 선택 |
| FunSearch/AlphaEvolve | `program_search` | **P4** | "판정 프로그램"을 생성하도록 유도 |
| 심볼릭 회귀 | `rule_extraction` | P4 | 현상 → 간단한 규칙/지표 환원 |
| self-driving lab | `closed_loop_project` | **P3,P6** | CLI 결과가 다음 입력으로 환류 |

**권장 기본 조합** (recreate가 코퍼스 기반 + 결정론 MVP여야 하므로):

```text
default_method_archetype =
    source_grounded_linking + conditional_recombination + tournament_reflection + program_search
```

---

## 7. 폐쇄 제어 루프 (통합 고유부) — Phase7 환류

두 부모(상류 kernel / 하류 게이트)를 잇는 환류선. kernel이 *선언한* 목표와 게이트가 *측정한* 달성을
primitive별로 대조해 gap을 산출하고, 그 gap이 다음 run kernel을 조향한다. **환류 없이 run 종료 금지(NoOpenLoop).**

```python
def AI_measure_kernel_gap(kernel: IdeaKernel, div: DiversityReport,
                          report: VerifyReport, winner: Candidate) -> dict:
    gap = {
        "diversity":   kernel["target_nonoverlap_score"] - div.unique_ratio,        # P1 목표−실측
        "surrogate":   kernel.get("surrogate_target", 0.0) - winner.elo_normalized, # P2
        "determinism": 1.0 if evaluator_gate(winner.seed).ok else 0.0,              # P4 통과여부
        "skepticism":  report.consensus_margin,                                     # P5 합의 견고도
        "provenance":  len(winner.idea_trace["parents"]),                           # P6 계보 깊이
    }
    gap["next_run_emphasis"] = AI_rank_primitives_by_gap(gap)   # gap 큰 primitive → 다음 kernel 강화
    return gap
    # acceptance_criteria:
    #   - 모든 primitive에 target↔measured 쌍 기록 (계기판 완성)
    #   - next_run_emphasis가 AI_make_idea_kernel의 saturation 입력으로 환류 (방향타 연결)

def update_registry_with_idea_outcome(registry, winner, kernel, gap) -> dict:
    registry.setdefault("idea_kernels", {})[kernel["kernel_id"]] = {
        "problem_frame": kernel["problem_frame"],
        "method_archetype": kernel["method_archetype"],
        "lens_stack": kernel["lens_stack"],
        "winner": winner["name"],
        "kernel_gap": gap,
        "next_run_emphasis": gap["next_run_emphasis"],
        "strength_label": winner.get("strength_label", "claimed"),
        "outcome": "seeded",
    }
    return registry
```

산출: `registry.json`의 `idea_kernels` 맵 (`rerun-avoidance.md §3.2`).

---

## 8. Phase 앵커맵 (가산 — 새 Phase 없음)

```text
recreate Phase            ← idea-layer 모듈                     앵커 방식
──────────────────────────────────────────────────────────────────────────────
Phase1.5 (경량)           ← IdeaKernel (상류 의도)             inventory 후 kernel 생성, input_manifest에 첨부
Phase1_Inventory          ← ABCLink 기질 (gene 그래프)         genes.json → build_gene_graph
Phase2_Generate           ← kernel bias + GenerateDebateEvolve  [parallel] 발산 뒤 비판·진화 직렬 루프
Phase2b_Avoidance         ← DiversityGuard                     AssessConsumedSourcePenalty 옆 soft 병치
Phase3_Differentiate      ← DiversityGuard 연속신호            overlap 이산임계에 unique_ratio 보조신호
Phase4_SelectOrIntegrate  ← TournamentSelect + idea_fit        6축 절대점수 ∥ pairwise, 불일치 시 P5
Phase5_Prove              ← EvaluatorGate                      5-check 중 "결정론 답변가능"을 게이트로 승격
Phase6_SeedDesign         ← CrossModelVerify                   idea_trace 섹션 + 합의·증거라벨
Phase7_UpdateRegistry     ← AI_measure_kernel_gap + idea_outcome ★폐루프 환류: gap 누적 → 다음 kernel 조향
```

---

## 9. Acceptance Criteria (3단)

```text
IdeaKernelAcceptance // run 전 (P 목표 선언)
    QueryRichness // source_search_queries ≥ 5
    AntiOverlap // target_nonoverlap ≥ 3 + target_nonoverlap_score 존재 (P1)
    Determinism // deterministic_engine_hint 존재 (P4)
    KillConditions // kill_conditions ≥ 3 (P5)
    NoNameFirst // kernel 단계에서 project name 미확정

CandidateIdeaAcceptance // 후보 통과 (P 게이트 측정)
    CorpusGrounded // parts ≥ 2 source projects
    IdeaTracePresent // candidate.idea_trace.kernel_id 존재 (P6)
    NonHomogeneous // unique_ratio ≥ 0.5 + 이산충돌 없음 (P1)
    DeterministicQuestion // evaluator_gate 통과 (P4)
    TournamentRanked // pairwise Elo 순위 존재 (P2)
    EvaluatorSkepticism // margin < 0.10 → needs_cross_review (P5)

DesignSeedIdeaAcceptance // seed 핸드오프
    IdeaTraceSection // Idea Trace 섹션 포함 (P6)
    MethodArchetypeMapped // §6 방법론 명시
    StrengthLabeled // strength_label ∈ {verified, claimed} (P5)
    ClosedLoopRecorded // kernel_gap이 registry에 기록 (P3 루프 폐쇄)
    BoundaryExplicit // "이 프로젝트가 아닌 것" 명시
```

---

## 10. Guardrails

```text
NoNameBeforeKernel // 문제 frame 이전 프로젝트명 확정 금지
NoVibeOnly // 멋진 이름/분위기만으로 후보 생성 금지
NoLLMOnlyEvaluator // LLM 평가점수만으로 winner 확정 금지 → CrossModelVerify 합의
NoRegistryBypass // 회피를 idea novelty로 우회 금지
NoGenericScienceCopy // 도메인 변환 없이 과학방법론 복붙 금지
NoUnboundedAgent // 멀티에이전트 토론은 Phase4 평가구조로만 축소
NoDeterminismBlur // 메타 AI_ 게이트가 이산 게이트·생성물 verdict 결정론을 흐리지 않음
NoScaleForDiversity // 동질화 시 K 늘리기 금지 → island 재발산
NoSelfReportEvidence // GATE-EVIDENCE 없이 verified 라벨 금지
NoOpenLoop // kernel_gap 환류 없이 run 종료 금지 (루프 폐쇄 강제)
NoUntriangulated // 단일 보고서 주장을 합의로 승격 금지
```

---

## 11. 도입 우선순위 (전이가치 × 적용비용)

| 순위 | 모듈 | 패치 대상 | 비용 | 근거 |
|---|---|---|---|---|
| 1 | DiversityGuard + CrossModelVerify | `rerun-avoidance.md`·`differentiation.md` | 저 | ★★★ 동질화는 recreate 존재이유, 기존 게이트에 지표·합의만 추가 |
| 2 | EvaluatorGate | `design-seed.md`·`differentiation.md` | 무 | ★★★ 문서 명문화만, 결정론 제약에 이론 근거 |
| 3 | IdeaKernel + idea_trace 필드 | input_manifest/candidates/SEED | 저 | 산출물에 trace만 남겨 기존 동작 불변, 데이터 축적 |
| 4 | GenerateDebateEvolve + TournamentSelect | `generation-paths.md`·`differentiation.md` | 중 | ★★ AI_ 호출 증가, discovery 모드와 결합 시 자연 |
| 5 | AI_measure_kernel_gap + idea_outcome | `rerun-avoidance.md` Phase7 | 중 | 통합 고유부 — 3·4 데이터 축적 후 루프 폐쇄 |
| 6 | ABCLink (gene 그래프) | `generation-paths.md`·`gene-extraction.md` | 중 | ★ 코퍼스 50→100 성장 시 가치 상승 |

> 권장 시작점: 1·2 (가산, 즉시 가치). 폐루프(5)는 3·4가 idea_trace·gap 데이터를 쌓은 뒤 닫는다 — 빈 환류는 무의미.

---

## 정직한 경계

- 3보고서는 bio/chem/materials 산출물 — 추출한 것은 **메타 메커니즘**이며 도메인 수치는 전이 대상 아님.
- 자체보고 성능(Nova 3.4× 등)은 독립검증 안 됨 → 다페르소나 완화책은 *방향*으로만 채택, 배수 불신.
- 임베딩 임계(cos 0.8)는 Si et al. 차용값 — recreate 코퍼스에 맞춰 재보정(현 overlap 0.4/0.7과 별개 축).
- DiversityGuard/Reflection/Tournament/CrossModel은 `AI_` 비결정론 — 메타층 한정. 생성물 verdict는 결정론 불변.
- 이 레이어는 recreate를 **대체하지 않는다** — 전부 기존 Phase에 앵커되는 가산 패치(파이프라인 재작성 금지).
