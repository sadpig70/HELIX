# DESIGN — HELIX 통합 폐루프 파이프라인 (aox ⊕ recreate, pg/pgf)

> aox(IdeaFirst, EXPLORE)와 recreate(EXPLOIT)의 **모든 기능을 하나의 폐루프로 파이프라인**한 pg/pgf 설계.
> 백본(HELIX-Core)이 두 strand를 단일 출처로 묶고, `next_action`이 매 라운드 strand를 분기하며,
> 구현된 explore winner가 exploit 코퍼스로 환류(염기쌍)해 **수렴 없이 복리로 도는 나선**을 이룬다.
> 표기: `skills/pg`(Gantree/PPR). 운영 지시문은 `INSTRUCTIONS-helix-{fullcycle,loop-autonomous}.md`(이 설계의 실행 사양).

---

## 0. 핵심 명제

> **하나의 백본 · 두 가닥 · 분기 구동.** 모든 EXPLORE 함수(sdx~aox, exclusionary, sa-*)와 모든 EXPLOIT
> 함수(recreate Phase0~7 + idea-layer)는 각 가닥의 *내부 파이프라인*이고, 백본의 `next_action`이 라운드마다
> 어느 가닥을 돌릴지 정하며(RECORD/REFRESH/EXPLORE/EXPLOIT), 통합 ledger가 양쪽 재사용을 단일 게이트로 막고,
> diversity.repair가 exclusionary 가드(sdxx/idxx/cixx) 또는 recreate avoidance로 라우팅되며, 구현 winner는
> base-pairing으로 코퍼스에 환류된다.

## 1. 결정론 경계 (지배 제약)

```text
백본 (core/, helix.py CLI 제외)   → 순수 결정론 (stdlib, now/sim 주입). ledger·diversity·provenance·loop·fingerprint
엔진 LLM 단계 (AI_*)              → 메타층. sdx~evx 수집/증류/창조/평가, recreate AI_ 판정 — 비결정론 허용
exploit 생성물 verdict 경로        → 결정론 불변 (stdlib MVP)
wall-clock                       → helix.py CLI 엣지에서만(--now 주입)
```

## 2. 통합 Gantree (main)

```text
HelixUnifiedLoop // aox⊕recreate 통합 폐루프 (designing) @v:1.0
    Backbone // HELIX-Core 단일 출처 결정론 substrate (done)
        Ledger // 통합 소모/등록 게이트 (is_consumed, 6키 계약)
        Diversity // 동질화/복구 측정 (lexical 기본 + sim 주입, repair_required)
        Provenance // 계보 + winner→corpus (염기쌍)
        Loop // next_action 결정론 정책 (RECORD/REFRESH/EXPLORE/EXPLOIT)
        Fingerprint // 정체성 primitive
        Validate // 구조·계약 검증
    OuterLoop // next_action 구동 라운드 (designing) @dep:Backbone
        LoadState // helix.py status --json → next_action·diversity·ledger·corpus_feedback
        Steer // coverage 히스토그램(strand/archetype/layer/domain) → 편중축 보정
        Dispatch // next_action 분기 → ExploreStrand | ExploitStrand | CloseLoop | Refresh
        Implement // winner → pgf full-cycle --with-review → 새 프로젝트 (transcription)
        CloseLoop // helix.py close-loop → ledger append + corpus 환류 (actuator)
        Feedback // kernel_gap(recreate) + homogenization(aox) → Diversity 갱신 → 다음 라운드 조향
        Checkpoint // loop-state + GATE-EVIDENCE + heartbeat
    ExploreStrand // IdeaFirst 전 기능 — see ExploreStrand tree (decomposed) @dep:Backbone #explore
    ExploitStrand // recreate 전 기능 — see ExploitStrand tree (decomposed) @dep:Backbone #exploit
    BasePairing // 구현된 explore winner → exploit 코퍼스 source (designing) @dep:ExploreStrand,ExploitStrand
        # winner_to_corpus_entry: origin=explore, semantic_family, source_chain → corpus.json
    Notation // pg·pgf·pgxf — 이 설계의 표기/실행 언어 + pgf full-cycle 핸드오프 (done)
```

> 2게이트/분기 위치: `Dispatch`(strand 선택, 백본 결정), `Ledger`(재사용 차단, 양 가닥 공통),
> `route_repair`(diversity→exclusionary 라우팅), `Capability`(explore full↔standalone).

## 3. ExploreStrand (decomposed) — 세계 → final_idea (IdeaFirst 전 기능)

```text
ExploreStrand // 세계 스캔 → 혁신 winner (decomposed) @v:1.3
    Capability // aox environment_capability_check → full | standalone 분기 (designing)
        # cross_model_baseline 가용? → full(cix/evx) : standalone(sa-icx/sa-evx)
    Channels // 정보 채널 확보 (designing) @dep:Capability
        SdxEnsure // sdx bootstrap|expand|refresh|audit — 80채널 카탈로그 (.sdx/catalog)
        SdxxExpand // sdxx discover — 미보유 직교채널만 (repair:channels 시)
        SdxCiIntegrate // sdx_ci integrate|union — 멀티에이전트 카탈로그 교차통합
        GitTrend // collect_git_trand daily|weekly|monthly — GitHub trending 소스 보강
    Collect // tcx full — 채널 소비 → news.md + industry_trend.md (14 domains) (designing) @dep:Channels
    Distill // 깊은 인사이트 (designing) @dep:Collect
        IdxDistill // idx distill — 10층(L6/L7/L9/L10) insight_layered_traced.yaml
        IdxxSteer // idxx steer — 미증류·약신호로 조향 (repair:insight 시)
    Innovate // 혁신 시드 (designing) @dep:Distill
        CixInnovate // cix innovate — 20렌즈 → 24시드(6축: novelty/generativity/.../surprise/coherence)
        CixxSteer // cixx steer — white-space 카테고리 조향 (repair:category 시)
    Evaluate // evx evaluate — 14 PGF 페르소나 합의 → dual winner(consensus+innovation) + 5S/3R/3X (designing) @dep:Innovate
    Orchestrate // aox full|partial|resume — stage0~6 상태/round_id/drift_guard/yield_attribution/homogenization (designing) @dep:Evaluate
    Standalone // cross-model 미가용 fallback (designing) @dep:Capability
        SaIcxForge // sa-icx forge — 14페르소나 120 raw seeds (CixxSteer 적용)
        SaEvxEvaluate // sa-evx evaluate — dual winner (consumed-ledger 배제)
        SaAoxOrchestrate // sa-aox full — standalone 오케스트레이션 (.sa-*/ 산출, production 위장 금지)
```

## 4. ExploitStrand (decomposed) — 코퍼스 → DesignSeed (recreate 전 기능 + idea-layer)

```text
ExploitStrand // 코퍼스 재조합 → DesignSeed (decomposed) @v:2.2
    Kernel // idea-layer IdeaKernel (상류 의도, Phase1.5) (designing)
        # AI_make_idea_kernel: 6 primitive 목표 선언(NoNameFirst), 과거 kernel_gap 입력
    Extract // gene-extraction (Phase0~1) (designing) @dep:Kernel
        BuildGenes // 3축 ProjectGene (형태/속성/기능) — 코퍼스(+환류 winner) → genes.json
        BuildInventory // ArchetypeShelf/PrimitiveShelf/LayerShelf/LensPalette/VocabRegistry
        GeneGraph // ABCLink 기질 (경량 KG)
    Generate // generation-paths (Phase2) (designing) @dep:Extract
        # [parallel] RECOMBINE(DistantHybridization·LayerFusion·ConflictCompiler·ABCLink)
        #            MUTATE(LensApply·GrammarMutation·NegativeSpaceInversion)
        #            TRANSPLANT(DomainTransplant·SystemIntegration)
        # → kernel bias → GenerateDebateEvolve(생성-비판-진화)
    Avoid // rerun-avoidance (Phase2b) (designing) @dep:Generate
        # hard-reject(name/fingerprint/corpus명) + AssessConsumedSourcePenalty + DiversityGuard(repair:exploit)
    Differentiate // differentiation (Phase3) (designing) @dep:Avoid
        # overlap/tag_clash/vocab_clash 이산 + unique_ratio 연속(백본 Diversity)
    Select // Phase4 select-or-integrate (designing) @dep:Differentiate
        # 6축 top-K + Integrate(상보, 능가 시만) + TournamentSelect(pairwise Elo) + idea_fit
    Prove // Phase5 (designing) @dep:Select
        # prove 5-check + EvaluatorGate(결정론 엔진 답변가능 — idea-layer P4)
    Seed // design-seed (Phase6) — DESIGN-SEED-{Name}.md + idea_trace (designing) @dep:Prove
    Registry // Phase7 (designing) @dep:Seed
        # registry update(version+1, fingerprint 네임스페이스) + MeasureKernelGap(idea-layer 폐루프)
```

## 5. PPR — 통합 오케스트레이션 글루 (핵심 함수)

```python
# ── 한 라운드 = 백본이 strand를 분기 ──────────────────────────────
def helix_round(state: dict, policy: dict) -> Outcome:
    st = AI_load_status()                      # helix.py status --json (백본: next_action·diversity·ledger)
    focus = steer_focus(st, state["coverage"]) # §6 다양성 보정 (결정론 히스토그램)
    act = st["next_action"]["action"]

    if act == "RECORD_CONSUMED":               # 구현 winner 미기록 → 루프 폐쇄만
        return close_loop_actuator(state.pending_winner)        # helix.py close-loop
    if act == "REFRESH_INPUTS":                # 동질화/island collapse → 입력 갱신 후 생성
        route_repair(st["diversity"], st["next_action"]["target"])  # → sdxx|idxx|cixx | recreate avoidance

    winner = (explore_pipeline(st, focus, policy) if act in ("RUN_EXPLORE", "REFRESH_INPUTS")
              else exploit_pipeline(st, focus, policy))         # strand 분기

    if is_consumed(to_candidate(winner), unified_ledger())["consumed"]:  # 단일 출처 게이트
        return rollback_and_resteer(state)     # 폐기 → REFRESH → 재생성 (dry면 DryError)

    project = AI_pgf_full_cycle(winner, with_review=True)       # 구현 (transcription)
    if not run_all_gates(project):             # GATE-EVIDENCE (실측, 자기보고 금지)
        return seed_only(winner, project)      # 공개 보류, 루프 계속
    close_loop_actuator(winner, project)       # ledger append + corpus 환류 (염기쌍)
    return implemented(winner, project)
    # acceptance_criteria:
    #   - winner는 통합 ledger 신선 · parts≥2(exploit) · evaluator_gate 통과(결정론 답변가능)
    #   - close_loop으로 ledger/corpus 실제 갱신 (NoOpenLoop)

# ── EXPLORE: aox 전 기능 파이프라인 (capability 분기 + exclusionary refresh) ──
def explore_pipeline(st, focus, policy) -> Winner:
    cap = AI_aox_probe_capability()                            # aox environment_capability_check
    if cap.cross_model == "unavailable":
        return standalone_pipeline(st, focus)                  # sa-icx → sa-evx → sa-aox
    catalog = AI_sdx_ensure(focus)                             # sdx bootstrap|refresh
    if focus.repair == "channels":
        catalog = AI_sdxx_expand(catalog, focus)               # sdxx 직교확장
    catalog = AI_sdx_ci_integrate(catalog)                     # sdx_ci (멀티에이전트, 옵션) + collect_git_trand 보강
    trends   = AI_tcx_collect(catalog)                         # tcx full
    insights = AI_idx_distill(trends, steer=focus.idxx)        # idx (+ idxx 미증류 조향)
    ideas    = AI_cix_innovate(insights, steer=focus.cixx, k=policy["candidates_K"])  # cix (+ cixx white-space)
    winner   = AI_evx_evaluate(ideas, depth=policy["verify_depth"])   # evx dual winner + 5S/3R/3X
    return AI_aox_orchestrate(winner)         # aox wrapup: round_id·drift_guard·yield_attribution·homogenization
    # → 백본 Diversity가 homogenization을 흡수(단일 측정), aox 자기 임계 복제 금지(desync 방지)

# ── EXPLOIT: recreate 전 기능 + idea-layer ──
def exploit_pipeline(st, focus, policy) -> Winner:
    kernel  = AI_make_idea_kernel(unified_ledger(), inventory(), primitives())   # idea-layer 상류 의도
    genes   = AI_build_genes(corpus_with_pairing())           # gene-extraction (환류 winner 포함)
    inv     = AI_build_inventory(genes); kg = build_gene_graph(genes)
    cands   = generate_candidates(inv, kernel, k=policy["candidates_K"])  # 3경로×8도구+ABCLink+DebateEvolve
    cands   = avoidance_gate(cands)                           # Phase2b hard-reject + DiversityGuard
    cands   = differentiate(cands, genes)                     # Phase3 overlap/tag/vocab + unique_ratio
    winner  = select_with_tournament(cands, kernel)          # Phase4 6축+Integrate+Tournament+idea_fit
    assert evaluator_gate(winner).ok                         # Phase5 prove + EvaluatorGate
    seed    = emit_design_seed_with_idea_trace(winner, kernel)   # Phase6
    return seed   # Phase7 registry + kernel_gap 은 close_loop/Feedback에서

# ── diversity 복구 라우팅 (5점 게이트로) ──
def route_repair(diversity: dict, target: str) -> str:
    b = diversity["signals"]["breached"]
    if target in ("explore", "both"):
        if "keyword_coverage" in b:                 return "sdxx"   # 입력(채널)
        if diversity_meta(diversity)["insight_repeat"]: return "idxx"   # 인사이트
        return "cixx"                                                  # 출력(카테고리)
    return "recreate_avoidance"                     # exploit: unique_ratio_below_floor → island 재발산

# ── 폐루프 환류 (kernel_gap + homogenization → 백본 Diversity) ──
def Feedback(state, winner, gap_inputs):
    gap = AI_measure_kernel_gap(state.kernel, *gap_inputs)   # recreate idea-layer 폐루프
    update_registry_with_idea_outcome(unified_ledger(), winner, state.kernel, gap)
    state.coverage = recompute_coverage(unified_ledger())    # strand/archetype/layer/domain
    # gap·homogenization → 다음 라운드 measure_diversity/next_action 조향
```

```python
# ── 외부 폐루프 (factory) — 정지조건까지 무중단 ──
def helix_factory_loop(policy):
    state = load_or_init_loop_state()
    while not should_stop(state, policy):           # max_turns/budget/dry/fail/STOP/무결성
        outcome = helix_round(state, policy)        # 위 — 한 라운드(strand 분기)
        Feedback(state, outcome.winner, outcome.gap_inputs)
        if state.turn % policy["evolve_every"] == 0:
            calibrate_thresholds(history())         # scripts/calibrate_diversity.py → policy.thresholds
        checkpoint(state); heartbeat(state); reenter()
    finalize_loop_report(state)
```

## 6. 데이터 자재 흐름 (typed I/O — 가닥을 흐르는 자재)

```text
EXPLORE:  ChannelCatalog → TrendReport → InsightSet → IdeaPool → EvaluatedWinner(=final_idea)
EXPLOIT:  IdeaKernel → ProjectGenes → CandidatePool → Differentiated → DesignSeed
공통/백본: → pgf full-cycle → NewProject → (구현시) LedgerEntry + CorpusEntry(염기쌍)
           ↑ UnifiedLedger(is_consumed 게이트) · DiversityReport(repair_required) · KernelGap(환류)
```

## 7. 제어 흐름 요약 (condition · branch · loop)

| 종류 | 위치 | 내용 |
|---|---|---|
| 분기 | `Dispatch`(next_action) | RECORD / REFRESH / EXPLORE / EXPLOIT |
| 분기 | `Capability` | explore full(cix/evx) ↔ standalone(sa-icx/sa-evx) |
| 분기 | `route_repair` | sdxx(채널) / idxx(인사이트) / cixx(카테고리) / recreate avoidance |
| 게이트 | `is_consumed`(통합 ledger) | 6키 충돌 시 폐기·재조향 (cross-engine 중복 포함) |
| 게이트 | `EvaluatorGate` | single_question 결정론 답변가능 아니면 reject |
| 반복 | `helix_factory_loop` | 정지조건까지 라운드 |
| 반복 | `GenerateDebateEvolve` | 생성-비판-진화 수렴 |
| 반복 | island 재발산 | unique_ratio < floor 동안 |
| 반복 | retry/backoff | 구현/검증/publish 실패 시 |

## 8. 함수 커버리지 매트릭스 (★ 빠짐없음 증명)

| 기능(스킬/모드) | 가닥 | Gantree 노드 | PPR |
|---|---|---|---|
| sdx bootstrap/expand/refresh/audit | EXPLORE | Channels.SdxEnsure | `AI_sdx_ensure` |
| sdxx discover | EXPLORE | Channels.SdxxExpand | `AI_sdxx_expand` (route_repair:channels) |
| sdx_ci integrate/union/compare | EXPLORE | Channels.SdxCiIntegrate | `AI_sdx_ci_integrate` |
| collect_git_trand daily/weekly/monthly | EXPLORE | Channels.GitTrend | sdx_ci 보강 |
| tcx full/collect/analyze | EXPLORE | Collect | `AI_tcx_collect` |
| idx distill/focus/audit | EXPLORE | Distill.IdxDistill | `AI_idx_distill` |
| idxx steer/map | EXPLORE | Distill.IdxxSteer | route_repair:insight |
| cix innovate/focus/filter | EXPLORE | Innovate.CixInnovate | `AI_cix_innovate` |
| cixx steer/map | EXPLORE | Innovate.CixxSteer | route_repair:category |
| evx evaluate/rerank/compare | EXPLORE | Evaluate | `AI_evx_evaluate` |
| aox full/partial/resume/dry-run | EXPLORE | Orchestrate | `AI_aox_orchestrate` + `helix_round`/loop |
| sa-aox / sa-icx / sa-evx | EXPLORE | Standalone | `standalone_pipeline` (Capability 분기) |
| recreate map (Phase0~1) | EXPLOIT | Extract | `AI_build_genes`/`AI_build_inventory` |
| recreate generate (Phase2) | EXPLOIT | Generate | `generate_candidates` |
| rerun-avoidance (Phase2b/7) | EXPLOIT | Avoid / Registry | `avoidance_gate`/`update_registry_*` |
| differentiation (Phase3~5) | EXPLOIT | Differentiate/Select/Prove | `differentiate`/`select_with_tournament` |
| design-seed (Phase6) | EXPLOIT | Seed | `emit_design_seed_with_idea_trace` |
| idea-layer (kernel+6게이트+폐루프) | EXPLOIT | Kernel + Avoid/Diff/Select/Prove + Registry | `AI_make_idea_kernel`/`AI_measure_kernel_gap` |
| recreate run/status | EXPLOIT | ExploitStrand 전체 / OuterLoop | `exploit_pipeline` |
| pgfr-combo | EXPLOIT | Notation(핸드오프) | `AI_pgf_full_cycle` |
| pg/pgf/pgxf | 공통 | Notation | 표기·full-cycle·대규모 인덱스 |
| ledger/diversity/provenance/loop/fingerprint/validate | 백본 | Backbone | `is_consumed`/`measure_diversity`/`next_action`/`close_loop` |
| calibrate_diversity | 백본 | OuterLoop.evolve | `calibrate_thresholds` |

→ EXPLORE 14 + EXPLOIT(recreate 6모듈 + pgfr-combo) + 공통 pg/pgf/pgxf + 백본 6모듈·도구 = **전 기능이 단일 트리에 매핑**.

## 9. Acceptance & 불변식

```text
UnifiedPipelineAcceptance
    AllFunctionsMapped   // §8 매트릭스 — aox·recreate 전 기능이 노드/PPR로 파이프라인됨
    SingleBackboneGate   // 양 가닥 winner가 통합 ledger is_consumed 단일 게이트 통과
    DispatchDriven       // strand는 백본 next_action이 결정(임의 순차 아님)
    BasePairingClosed    // 구현 explore winner → exploit 코퍼스 환류 (close_loop, NoOpenLoop)
    RepairRouted         // diversity.repair → sdxx/idxx/cixx 또는 recreate avoidance로 라우팅
    DeterminismBoundary  // 백본 결정론 / 엔진 AI_ 메타층 / exploit verdict 결정론 / 시계 CLI 엣지
    NoDesync             // homogenization(aox)·kernel_gap(recreate)을 백본 Diversity 단일 측정으로 흡수
    OriginalImmutable    // skills/·core/·정본 불변 — 새 run/.helix 상태만 추가
```

> 본 설계의 실행 사양은 `INSTRUCTIONS-helix-fullcycle.md`(1턴)·`INSTRUCTIONS-helix-loop-autonomous.md`(무중단 루프).
> 즉 이 문서는 *무엇을 어떻게 파이프라인하는가*(설계)이고, 두 INSTRUCTIONS는 *런타임이 어떻게 수행하는가*(운영)다.
```
