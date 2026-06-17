---
name: idx
description: "IDX (Insight Distillation eXplorer) — TCX 산출물(.tcx/latest/)을 입력으로, 정보 데이터풀에서 깊은 인사이트를 10층 계위로 분리 도출하는 스킬. 기존 IdeaFirst의 평면적 인사이트 도출(Layer 1-3, 관찰·패턴 수준)이 평범한 결합 아이디어로 귀결되는 문제를 해결. Gap(공백), Tension(긴장), Counterfactual(반사실), Generative(생성적) 4개 깊은 층위에 집중. 8개 AI를 층위별로 페어 분배. TCX 다음, CIX 이전 단계. Triggers: IDX, 인사이트도출, 깊은인사이트, layered insight, insight distillation, Gap Tension Counterfactual, 인사이트추출"
user-invocable: true
argument-hint: "distill|focus|audit [--layers=6,7,9,10] [--input=.tcx/latest/] [--rounds=N]"
version: "1.4"
author: "양정욱 (sadpig70@gmail.com)"
---

# IDX (Insight Distillation eXplorer) v1.4

> 평범한 인사이트는 평범한 아이디어만 낳는다.
> 인사이트의 *층위*가 아이디어의 천장을 결정한다.

## 존재 이유 (Why)

IdeaFirst STEP 3 ("10개 인사이트 도출")의 평면성이 STEP 4 (아이디어 생성)의 평범성을 결정짓는다는 실증 진단. 8 AI 결과의 인사이트들이 모두 *관찰(Observation) ~ 메커니즘(Mechanism)* 수준에 머물러 (Layer 1-3), 인접 분야 단순 결합으로 귀결됐다.

IDX는 인사이트를 **10층 계위**로 재정의하고, Layer 6/7/9/10 (Gap·Tension·Counterfactual·Generative)에 집중하여 **CIX의 변형 입력 품질**을 구조적으로 끌어올린다.

## Inputs

```yaml
input:
  source_root: ".tcx/latest"                          # ★ TCX 고정 진입점
  source_files:
    industry_trend: ".tcx/latest/industry_trend.md"
    news:           ".tcx/latest/news.md"
    quality_report: ".tcx/latest/quality_report.md"   # 선택적 (품질 게이트 체크)
    manifest:       ".tcx/latest/manifest.yaml"        # TCX round 추적용
  cli_override: "--input=<other_dir>"                  # 옵션, 일반적으로 미사용

  rule: |
    기본은 .tcx/latest/. 사용자가 --input으로 다른 디렉토리를 주면 그 dir 사용.
    어느 경우든 manifest.yaml을 함께 로드해 source_round_id 추적.
```

`industry_trend.md`/`news.md`/`quality_report.md`는 TCX 정본 출력. IDX는 어떤 catalog version, 어떤 domain set, 어떤 sampling으로 만들어졌는지 모두 manifest로 추적.

## IDX_POLICY (all magic numbers externalized)

```yaml
IDX_POLICY:
  distillation:
    target_insights_total: 20                # final output count
    layers_output: [6, 7, 9, 10]             # surface vs deep 구분
    layers_context: [1, 2, 3, 4, 5]          # 보조 — 컨텍스트로만 생성, 출력 X
    insights_per_layer: 5                    # 20 / 4 layers
    agents_per_layer: 2                      # 8 AI / 4 layers
    agents_total: 8

  dedup:
    same_layer_similarity_threshold: 0.75    # 같은 Layer 내 strict
    cross_layer_similarity_threshold: 0.85   # 다른 Layer 간 relaxed

  layer_metric_thresholds:                   # reject rules
    L6_Gap:
      non_obviousness: 6
      importance_of_filling: 6
    L7_Tension:
      force_balance: 7
      resolution_difficulty: 7
    L9_Counterfactual:
      plausibility: 5
      divergence_from_actual: 7
    L10_Generative:
      seeds_yielded: 3
      depth_of_implication: 7

  layer_8_activation:
    enabled_by_default: false
    activation_conditions:
      temporal_span_years_min: 3
      measurement_points_min: 5
      quantitative_indicators_min: 10

  audit_mode:                              # NEW v1.4 — IDX-20260513-001 audit 학습 반영
    non_destructive_default: true          # 기본 원본 미수정
    apply_flag_required: true              # --apply 시에만 라벨 변경
    cross_reference_cix: true              # .cix/latest/{idea_pool, raw_seed_ideas} 자동 cross-ref
    metrics_computed:
      - threshold_compliance              # 기존
      - layer_style_match                 # NEW — statement keyword 검증
      - persona_purity                    # NEW — persona system_prompt 키워드 매칭
      - cix_downstream_utilization        # NEW — CIX raw + top-24 진입수
      - misclassification_candidates      # NEW — style/required_fields 불일치
    misclassification_verification: false  # 옵션 — true면 CIX rescoring sub-agent 호출

  layer_pure_assertion:                    # NEW v1.4 — IDX architecture 보호
    enabled: true
    rule: "각 layer (L6/L7/L9/L10)가 다음 라운드에 최소 1 STRONG insight 보장"
    strong_definition: "total_score ≥ 8.0 AND cix_downstream_top24 ≥ 1"
    on_fail: "warn in audit_report; do not block round emit"

  hybrid_layer_support:                    # NEW v1.4 — INS-L6-004 사례 학습
    enabled: true
    optional_field: "secondary_layer"      # L6/L7/L9/L10 중 부가 분류
    rationale: |
      INS-L6-004 같이 L6 (gap) + L7 (tension) 양면 보유한 insight를 위해.
      primary는 단일 layer, secondary는 옵션. downstream CIX는 양면 활용 가능.

  personas:                              # NEW v1.3 — PGF discovery 페르소나 정식 통합
    source: "{PGF_SKILL_DIR}/discovery/personas.json"
    version_pin: "1.0"                   # personas.json#version
    enabled_set: [P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P14]   # v1.6 — 14 페르소나 풀
    wave_count: 2                        # primary 8(2/layer) / parallelism; P9-P14는 cross-check 검증
    parallelism: 4                       # Anthropic 권장
    layer_affinity:                      # Layer ↔ 페르소나 (v1.6: primary P1-P8 유지 + P9-P14 cross-check 보강)
      L6_Gap:
        primary: [P3, P7]                # critical/policy + critical/market — gaps 탐지에 최적
        cross_check: [P1, P5, P9, P11]   # creative/analytical + 주체성공백(P9) + 공격면공백(P11)
        rationale: "비판적 시각 + 분석적 보완 — 누락된 영역 발견"
      L7_Tension:
        primary: [P2, P3]                # market/analytical + policy/critical — 권력·이해 충돌
        cross_check: [P7, P6, P12, P14]  # critical + sociologist + 자원한계(P12) + 인센티브(P14)
        rationale: "구조적 트레이드오프 + 행위자 갈등 surfacing"
      L9_Counterfactual:
        primary: [P1, P8]                # creative/tech + creative/sci_tech — 가정 전복
        cross_check: [P4, P6, P13]       # intuitive 페어 + 역사 반사실(P13)
        rationale: "급진적 분기 + 직관적 ramifications"
      L10_Generative:
        primary: [P8, P4]                # creative/sci_tech + intuitive/science — 메타 패턴
        cross_check: [P1, P6, P10]       # creative tech + intuitive society + 실사용 생성(P10)
        rationale: "cross-domain 추상화 + 도메인간 연결"
    
    use_tcx_persona_chain: true          # TCX manifest의 persona assignment 추적
                                          # IDX manifest에 source_tcx_round + persona_chain 기록

  storage:
    root: ".idx"                              # project-root relative
    layout:
      index:   "index.yaml"
      latest:  "latest/"                       # ★ CIX 등 downstream 고정 진입점
      rounds:  "rounds/"
      archive: "archive/"
    round_id_format: "IDX-{YYYYMMDD}-{NNN}"
    files_per_round:
      - insight_layered.yaml                   # 메인 (20 insights)
      - insight_layered_traced.yaml            # evidence trace 첨부 버전
      - context_layers.yaml                    # Layer 1-5 보조 (디버깅용)
      - audit_report.md                        # 품질 평가 결과
      - manifest.yaml                          # source TCX round + policy snapshot
      - distillation_log.yaml                  # 어떤 AI가 어떤 Layer를 도출했나
    latest_strategy: "copy"                    # Windows 안전, symlink 아님
    retain_in_rounds_days: 90
    archive_target_pattern: "archive/{YYYY-Q[1-4]}/"
    archive_script: "{IDX_SKILL_DIR}/scripts/archive_rounds.py"
    concurrency_lock: ".idx/.lock"
```

## Modes

```yaml
distill:
  steps: [load_tcx_inputs, validate_manifest, gen_context_layers, distill_deep, score_and_select, traceback, emit]
focus:
  steps: [load_tcx_inputs, validate_manifest, gen_context_layers, distill_focused, emit]
  note: "--layers=N,M으로 특정 층위만 집중. 8 AI 전원 그 층위에 분배"
audit:
  steps: [load_existing_insights, rescore, identify_misclassified, emit_audit_report]
  note: "기존 .idx/rounds/{id}/insight_layered.yaml 재평가"
```

## 10층 인사이트 계위 (Insight Hierarchy)

```yaml
# 표층 (Surface — Context로만 사용)
Layer_1_Observation:
  desc: "데이터에 명시된 사실"
  example: "PQC 마이그레이션 마감 2026"

Layer_2_Pattern:
  desc: "반복되는 구조"
  example: "양자컴퓨팅 진전 + PQC 의무화 + 바이오 데이터 폭증 동시 발생"

Layer_3_Mechanism:
  desc: "패턴의 원인"
  example: "PQC 의무화는 'harvest now decrypt later' 위협이 가시화됐기 때문"

Layer_4_Constraint:
  desc: "이 영역에서 변하지 않는 것"
  example: "임상데이터는 30년+ 보존 필수 (법적 제약)"

Layer_5_Anomaly:
  desc: "예외·아웃라이어"
  example: "GR00T/N1 등 휴머노이드 OS가 표준화 전에 상용화"

# 심층 (Deep — IDX 출력 대상) ⭐
Layer_6_Gap:
  desc: "데이터에 명시되지 않은, 그러나 명백한 공백"
  questions:
    - "X는 다 언급되는데 왜 Y는 언급되지 않는가?"
    - "어떤 조합이 명백히 가능한데 아무도 안 만들었나?"
    - "어떤 행위자가 빠져있나?"
  example: "PQC 마이그레이션 논의에 IoT·임베디드 영역이 통째로 빠짐"
  quality_metrics:
    - non_obviousness
    - importance_of_filling

Layer_7_Tension:
  desc: "모순·상충·트레이드오프"
  questions:
    - "어떤 힘과 어떤 힘이 부딪히는가?"
    - "양립 불가능해 보이는 두 요구가 동시에 강해지는가?"
    - "단기 최적과 장기 최적이 어디서 갈라지는가?"
  example: "AI 데이터 주권 강화 ↔ AI 모델 공유 필요성 동시 증가"
  quality_metrics:
    - force_balance
    - resolution_difficulty

Layer_9_Counterfactual:
  desc: "반사실 — '만약 X가 없다면/달랐다면?'"
  questions:
    - "이 시장의 가장 큰 가정을 뒤집으면 무엇이 가능한가?"
    - "현재 당연시되는 제약이 사라지면 무엇이 폭발하는가?"
    - "역사의 어느 시점에 다른 선택이 있었다면?"
  example: "만약 HTTPS가 처음부터 quantum-safe였다면 PQC 마이그레이션 시장 자체가 없었을 것 → 다른 시장은 어디?"
  quality_metrics:
    - plausibility
    - divergence_from_actual

Layer_10_Generative:
  desc: "다른 인사이트를 *낳는* 메타 인사이트 ⭐⭐"
  questions:
    - "이 인사이트가 사실이라면 또 어떤 인사이트가 도출되는가?"
    - "이 패턴이 다른 도메인에도 작동하는가?"
    - "이 갭/긴장은 다른 형태로 어디에 또 존재하는가?"
  example: "'표준화 전 상용화' 패턴 (휴머노이드 OS)이 양자 SDK, 바이오 데이터 포맷에도 동일하게 작동 중"
  quality_metrics:
    - seeds_yielded
    - depth_of_implication

# 시계열 (Temporal — 조건부 활성화, IDX_POLICY.layer_8_activation 참조)
Layer_8_Trajectory:
  desc: "시간축 변화 방향"
  status: "활성화 조건 충족 시에만 — IDX_POLICY.layer_8_activation"
```

각 임계값은 `IDX_POLICY.layer_metric_thresholds`에서 단일 출처로 관리. 본 섹션은 의미·예시만 기술.

## Persona ↔ Layer 분배 전략 (PGF P1-P14, v1.6)

> v1.3에서 추상적 "AI_1~AI_8"이 PGF discovery cognitive personas로 정식 대체됨.
> v1.6에서 풀이 14로 확장 — 기존 P1-P8은 primary 유지(검증된 layer-purity), 신규 P9-P14는 cross-check로 보강.
> Layer ↔ persona 매핑은 `IDX_POLICY.personas.layer_affinity` 단일 출처.

```yaml
persona_layer_assignment:
  # IDX_POLICY.personas.layer_affinity 정본 참조. 아래는 default canonical mapping.
  
  L6_Gap:
    primary:     [P3 Regulatory Architect, P7 Contrarian Critic]
    cross_check: [P1 Disruptive Engineer, P5 Field Operator, P9 Practical Agency Ethicist, P11 Adversarial Robustness Analyst]
    # P3·P7의 critical 인지 → 누락 영역 발견. P1·P5 + P9(주체성 공백)·P11(공격면 공백) cross-check.
  
  L7_Tension:
    primary:     [P2 Cold-eyed Investor, P3 Regulatory Architect]
    cross_check: [P7 Contrarian Critic, P6 Future Sociologist, P12 Regenerative Systems Ecologist, P14 Mechanism Designer]
    # 시장↔정책 충돌(P2·P3) + 비판·사회(P7·P6) + 자원한계(P12)·인센티브(P14) 긴장
  
  L9_Counterfactual:
    primary:     [P1 Disruptive Engineer, P8 Convergence Architect]
    cross_check: [P4 Connecting Scientist, P6 Future Sociologist, P13 Historical Cycle Analyst]
    # creative 가정 전복(P1·P8) + intuitive(P4·P6) + 역사 반사실(P13 "과거 사이클이라면")
  
  L10_Generative:
    primary:     [P8 Convergence Architect, P4 Connecting Scientist]
    cross_check: [P1 Disruptive Engineer, P6 Future Sociologist, P10 Embodied UX Anthropologist]
    # cross-domain 추상화(P8·P4) — Layer 10의 본질 + 실사용 생성(P10)

per_persona_output:
  context_layers_1_to_5: "각 persona당 5-10개 (보조용)"
  primary_layer: "IDX_POLICY.distillation.insights_per_layer 만큼 (default 5)"
  inheritance: |
    TCX manifest에서 source persona ID 추적.
    각 페르소나는 .tcx/latest/news_items.yaml에서 자기가 생성한 item을 우선 참조.

total:
  context: "14 × 5~10 = 70-140 → 필터링 후 ~10 유지 (P1-P8 primary + P9-P14 cross-check)"
  output: "primary 2 personas × 5 × 4 layers = 40 → dedup → 20 (target_insights_total)"
```

**핵심**: 각 페르소나는 자기 layer **만** 출력. evaluation_bias가 자연스럽게 layer 적합도와 정합 (예: P3 critical → L6 Gap; P8 creative/sci_tech → L10 Generative). 1차 IDX 실행에서 "AI_1~AI_8" 추상 분배는 페르소나 일관성 보증 불가였으나, v1.3은 PGF의 검증된 직교성으로 layer-purity를 구조적으로 보장.

---

## DESIGN: Gantree

> 모든 흐름 제어(if/while/for/Convergence Loop)는 PPR `def` 블록에 위치. Gantree는 노드 구조만.

```
IDX_Main // IDX 메인 진입점 (in-progress) @v:1.2
    ModeDistill // 기본 도출 모드 (designing)
        Phase1_DataIngest // TCX latest 입력 로딩 (designing)
            AI_load_tcx_inputs               // .tcx/latest/{industry_trend,news,quality_report}.md
            AI_load_tcx_manifest             // .tcx/latest/manifest.yaml → source_round_id
            AI_validate_tcx_quality_gates    // TCX의 quality_report 통과 여부 확인
            AI_segment_by_domain             // domain_set 기준 분할
            # output: data_pool.yaml         (in-memory; not persisted unless --keep-intermediate)

        Phase2_ContextLayerGen // Layer 1-5 자동 생성 (designing) @dep:Phase1_DataIngest
            [parallel]
            AI_extract_observations          // L1
            AI_extract_patterns              // L2
            AI_infer_mechanisms              // L3
            AI_identify_constraints          // L4
            AI_detect_anomalies              // L5
            [/parallel]
            # output: context_layers.yaml    (round dir; 보조용)

        Phase3_DeepDistillation // Layer 6/7/9/10 병렬 도출 (designing) @dep:Phase2_ContextLayerGen
            [parallel]
            P3_distill_gaps                  // Layer 6 primary (Regulatory Architect)
            P7_distill_gaps                  // Layer 6 cross (Contrarian Critic)
            P2_distill_tensions              // Layer 7 primary (Cold-eyed Investor)
            P3_distill_tensions              // Layer 7 secondary (Regulatory Architect) — same persona, different layer
            P1_distill_counterfactuals       // Layer 9 primary (Disruptive Engineer)
            P8_distill_counterfactuals       // Layer 9 secondary (Convergence Architect)
            P8_distill_generatives           // Layer 10 primary (Convergence Architect)
            P4_distill_generatives           // Layer 10 secondary (Connecting Scientist)
            [/parallel]
            # output: raw_deep_insights.yaml (~40 candidates)

        Phase4_QualityScoring // 층위별 메트릭 평가 (designing) @dep:Phase3_DeepDistillation
            AI_score_per_layer_metrics       // IDX_POLICY.layer_metric_thresholds 적용
            AI_score_cross_layer_independence
            # output: scored_insights.yaml

        Phase5_DedupAndSelect // 중복 제거 + 상위 N 선정 (designing) @dep:Phase4_QualityScoring
            AI_validate_layer_specific_rules // Layer별 필수 필드 검증 (v1.1 도입)
            AI_dedup_semantic                // IDX_POLICY.dedup 적용
            AI_select_top_N                  // IDX_POLICY.distillation.target_insights_total
            AI_validate_layer_purity         // 잘못 분류된 인사이트 재배치
            # output: insight_layered.yaml

        Phase6_TraceBack // 출처 데이터 인용 첨부 (designing) @dep:Phase5_DedupAndSelect
            AI_link_to_source_data           // 각 인사이트가 어떤 TCX 채널·item에서 왔는지
            AI_emit_quote_evidence_with_hash // v1.1 — span/hash/confidence
            # output: insight_layered_traced.yaml

        Phase7_CatalogEmit // 최종 출력 (designing) @dep:Phase6_TraceBack
            AI_build_manifest                // source_round, policy snapshot, hashes
            AI_build_distillation_log        // AI별 layer 도출 결과 기록
            AI_emit_round_dir                // .idx/rounds/{round_id}/ — 6 files
            AI_sync_latest                   // .idx/latest/ overwrite (copy)
            AI_update_idx_index              // .idx/index.yaml — prepend round
            AI_maybe_run_archive             // 90일+ 자동 이동
            # output_root: .idx/

    ModeFocus // 특정 층위만 집중 도출 (designing)
        # input: --layers=N[,M] (e.g., --layers=7,9)
        # process: AI_parse_layer_args → AI_distribute_all_8_AI_to_target_layers
        # note: target_insights_total은 IDX_POLICY 그대로 유지
        # output: insight_focused.yaml (single layer or pair)

    ModeAudit // 기존 인사이트 품질 재평가 (designing)
        # process: AI_reload_existing_insights → AI_rescore_with_current_metrics
        #          → AI_identify_misclassified → AI_propose_layer_reassignment
        # input: .idx/rounds/{round_id}/insight_layered.yaml (or path via --input)
        # output: audit_report.md (no catalog mutation unless --apply)
```

---

## PPR: 핵심 함수 정의

### Phase 7: 출력 emit (TCX와 동일 패턴)

```python
def AI_emit_round_dir(round_dir, artifacts, manifest, distillation_log):
    """원자적 round dir 작성 — TCX와 동일 패턴.
    artifacts: {insight_layered, insight_layered_traced, context_layers, audit_report}
    """
    # acceptance_criteria:
    #   - 6 files present in round dir (4 artifacts + manifest + distillation_log)
    #   - latest/ byte-identical to new round dir
    #   - index.yaml.latest_round_id == new round id
    AI_acquire_lock(IDX_POLICY.storage.concurrency_lock)
    try:
        AI_write_files(round_dir, artifacts | {"manifest": manifest, "distillation_log": distillation_log})
        AI_clear_dir(IDX_POLICY.storage.latest)
        AI_copy_tree(round_dir, IDX_POLICY.storage.latest)
        AI_update_idx_index(...)
        AI_maybe_run_archive(IDX_POLICY.storage)
    finally:
        AI_release_lock(IDX_POLICY.storage.concurrency_lock)
```

### Layer 6: Gap 도출

```python
def AI_distill_gaps(data_pool: DataPool, context: ContextLayers) -> list[GapInsight]:
    """데이터에 명시되지 않은, 그러나 명백한 공백 발견."""
    # acceptance_criteria:
    #   - non_obviousness >= IDX_POLICY.layer_metric_thresholds.L6_Gap.non_obviousness
    #   - importance_of_filling >= IDX_POLICY.layer_metric_thresholds.L6_Gap.importance_of_filling
    #   - len(result) == IDX_POLICY.distillation.insights_per_layer
    #   - required fields: what_is_missing, why_it_matters (per insight_output.yaml#L6_Gap)
    candidates = []
    candidates += AI_find_missing_in_natural_pairs(data_pool)
    candidates += AI_find_missing_stakeholders(data_pool)
    candidates += AI_find_missing_dimensions(data_pool)       # 시간/지리/스케일
    candidates += AI_find_unbuilt_combinations(data_pool)
    scored = [AI_score_gap_quality(c) for c in candidates]
    return AI_select_top_N(scored, layer="L6_Gap", n=IDX_POLICY.distillation.insights_per_layer)

# Example output:
# "PQC 마이그레이션 논의는 데이터센터·금융·정부에 집중. IoT·임베디드 디바이스
# (수십억 대, 교체 어려움, 30년+ 수명)는 통째로 빠짐."
```

### Layer 7: Tension 도출

```python
def AI_distill_tensions(data_pool: DataPool, context: ContextLayers) -> list[TensionInsight]:
    """상충하는 두 힘이 동시에 강해지는 지점."""
    # acceptance_criteria:
    #   - force_balance >= IDX_POLICY.layer_metric_thresholds.L7_Tension.force_balance
    #   - resolution_difficulty >= IDX_POLICY.layer_metric_thresholds.L7_Tension.resolution_difficulty
    #   - len(result) == IDX_POLICY.distillation.insights_per_layer
    #   - required fields: force_A, force_B, convergence_zone, false_resolutions
    candidates = []
    candidates += AI_find_simultaneous_strengthening_opposites(data_pool)
    candidates += AI_find_short_long_term_conflicts(data_pool)
    candidates += AI_find_stakeholder_interest_conflicts(data_pool)
    candidates += AI_find_technical_regulatory_conflicts(data_pool)
    scored = [AI_score_tension_quality(c) for c in candidates]
    return AI_select_top_N(scored, layer="L7_Tension", n=IDX_POLICY.distillation.insights_per_layer)

# Example output:
# "AI 모델 학습 규모 요구 ↔ 데이터 주권 규제. 둘 다 동시에 강해짐.
# 연합학습은 부분 해법이지만 본질적 손실 동반."
```

### Layer 9: Counterfactual 도출

```python
def AI_distill_counterfactuals(data_pool: DataPool, context: ContextLayers) -> list[CFInsight]:
    """'만약 X가 다르다면?' 가정 변경."""
    # acceptance_criteria:
    #   - plausibility >= IDX_POLICY.layer_metric_thresholds.L9_Counterfactual.plausibility
    #   - divergence_from_actual >= ... .L9_Counterfactual.divergence_from_actual
    #   - len(result) == IDX_POLICY.distillation.insights_per_layer
    #   - required fields: counterfactual_premise, branched_world, divergence_axes, implausibility_check
    candidates = []
    candidates += AI_identify_unspoken_assumptions_and_invert(data_pool)
    candidates += AI_remove_taken_for_granted_constraints(data_pool)
    candidates += AI_alt_history_branches(data_pool)
    candidates += AI_remove_dominant_actor(data_pool)
    scored = [AI_score_cf_quality(c) for c in candidates]
    return AI_select_top_N(scored, layer="L9_Counterfactual", n=IDX_POLICY.distillation.insights_per_layer)
```

### Layer 10: Generative 도출

```python
def AI_distill_generatives(data_pool: DataPool, context: ContextLayers) -> list[GenInsight]:
    """다른 인사이트를 *낳는* 메타 인사이트. 가장 가치 있는 층위."""
    # acceptance_criteria:
    #   - seeds_yielded >= IDX_POLICY.layer_metric_thresholds.L10_Generative.seeds_yielded
    #   - depth_of_implication >= ... .L10_Generative.depth_of_implication
    #   - len(result) == IDX_POLICY.distillation.insights_per_layer
    #   - required fields: meta_pattern, yielded_seeds (≥3), cross_domain_evidence (≥2), abstraction_level
    all_lower = context.l6_gaps + context.l7_tensions + context.l9_cf
    candidates = []
    candidates += AI_find_cross_domain_recurring_patterns(all_lower)
    candidates += AI_abstract_to_higher_level(all_lower)
    candidates += AI_identify_seed_insights(all_lower)
    scored = [AI_score_generative_quality(c) for c in candidates]
    return AI_select_top_N(scored, layer="L10_Generative", n=IDX_POLICY.distillation.insights_per_layer)
```

### Dedup (IDX_POLICY.dedup 적용)

```python
def AI_dedup_semantic(insights: list[Insight]) -> list[Insight]:
    """layer 내부는 strict, layer 간은 relaxed (IDX_POLICY.dedup)."""
    P = IDX_POLICY.dedup
    embeddings = [AI_embed(ins.statement) for ins in insights]
    keep = []
    for i, ins in enumerate(sorted(insights, key=lambda x: -x.score)):
        threshold = (P.same_layer_similarity_threshold
                     if any(k.layer == ins.layer for k in keep)
                     else P.cross_layer_similarity_threshold)
        max_sim = max((cosine(embeddings[i], AI_embed(k.statement)) for k in keep), default=0)
        if max_sim < threshold:
            keep.append(ins)
    return keep
```

### Layer-Specific Reject Rules

```python
def AI_validate_layer_specific_rules(insight: Insight) -> ValidationResult:
    """schemas/insight_output.yaml#layer_specific_fields + IDX_POLICY 적용. Reject 시 사유 명시."""
    # acceptance_criteria:
    #   - required_fields (per schemas) 모두 존재
    #   - semantic_checks (per schemas) 통과
    #   - metric thresholds (per IDX_POLICY.layer_metric_thresholds) 통과
    rules = AI_load_layer_rules_from_schema()                  # schemas/insight_output.yaml
    thresholds = IDX_POLICY.layer_metric_thresholds[insight.layer]
    for field in rules[insight.layer]["required_fields"]:
        if not hasattr(insight, field) or getattr(insight, field) is None:
            return REJECT(reason=f"Missing required field: {field}")
    for check in rules[insight.layer]["semantic_checks"]:
        if not AI_semantic_check(insight, check):
            return REJECT(reason=f"Semantic check failed: {check}")
    for metric, threshold in thresholds.items():
        if getattr(insight.metrics, metric) < threshold:
            return REJECT(reason=f"Metric {metric} below threshold: {threshold}")
    return ACCEPT
```

### Evidence Trace (v1.1 — hash/span/confidence 강화)

```python
def AI_emit_quote_evidence_with_hash(insight: Insight, source_data: DataPool) -> Insight:
    """v1.1 — quote 위변조 방지 + 검증성 확보."""
    for ev in insight.evidence:
        ev.source_file = AI_locate_source_file(ev.quote, source_data)
        ev.source_section = AI_locate_section(ev.quote, ev.source_file)
        ev.source_span = AI_locate_char_offset(ev.quote, ev.source_file)
        ev.quote_hash = sha256(ev.quote.encode()).hexdigest()
        ev.confidence = AI_score_quote_accuracy(ev.quote, ev.source_file, ev.source_span)
        ev.contradictions = AI_find_contradicting_sources(ev.quote, source_data)
    return insight
```

### L8 Trajectory 조건부 활성화

```python
def AI_check_L8_activation_eligibility(data_pool: DataPool) -> bool:
    """IDX_POLICY.layer_8_activation 참조. 조건 미충족 시 L8 자동 SKIP."""
    P = IDX_POLICY.layer_8_activation
    if not P.enabled_by_default:
        # default disabled — check conditions
        return (
            data_pool.temporal_span_years >= P.activation_conditions.temporal_span_years_min
            and data_pool.measurement_points >= P.activation_conditions.measurement_points_min
            and len(data_pool.quantitative_indicators) >= P.activation_conditions.quantitative_indicators_min
        )
    return True
```

---

## Output Storage Layout

Runtime artifacts live at project-root `.idx/`:

```
<project-root>/
└── .idx/
    ├── index.yaml                     # rounds catalog + latest_round_path
    ├── latest/                        # ★ CIX 등이 사용하는 고정 진입점
    │   ├── insight_layered.yaml
    │   ├── insight_layered_traced.yaml
    │   ├── context_layers.yaml
    │   ├── audit_report.md
    │   ├── manifest.yaml              # TCX source_round + IDX policy snapshot
    │   └── distillation_log.yaml      # AI별 layer 도출 로그
    ├── rounds/
    │   ├── IDX-20260513-001/          # 6 files per round
    │   ├── IDX-20260513-002/
    │   └── ...
    └── archive/
        └── 2026-Q2/
            ├── .READONLY
            └── IDX-*/...
```

**Downstream contract** — CIX는 `.idx/latest/insight_layered_traced.yaml` 고정 경로로 소비.
**Upstream contract** — IDX는 `.tcx/latest/*` 고정 경로로 소비. manifest로 TCX round_id 추적.

---

## Outputs

### insight_layered.yaml (메인)

상세 스키마: `schemas/insight_output.yaml`. 핵심:

```yaml
distillation:
  version: "v1.2"
  round_id: "IDX-{YYYYMMDD}-{NNN}"
  built_at: "ISO-8601"
  source_tcx_round: "TCX-{YYYYMMDD}-{NNN}"          # ★ TCX round 추적
  source_catalog_version: "{catalog.version}"        # SDX version도 traceable
  total_insights: "{IDX_POLICY.distillation.target_insights_total}"
  layer_distribution:
    L6_Gap: 5
    L7_Tension: 5
    L9_Counterfactual: 5
    L10_Generative: 5
  insights: [...]                                    # 20 entries
```

상세 entry 스키마 + Layer별 필수 필드는 `schemas/insight_output.yaml` 참조 (v1.2 — evidence v1.1 형식 통일).

---

## Usage

```bash
# 기본 — TCX latest 입력 사용
/idx distill

# 특정 디렉토리에서 (다른 TCX round 또는 archive)
/idx distill --input=.tcx/rounds/TCX-20260510-003/

# 특정 층위만 (8 AI 전원 집중)
/idx focus --layers=7,9                              # Tension + Counterfactual만

# 기존 인사이트 재평가
/idx audit                                            # default: .idx/latest/insight_layered.yaml
/idx audit --input=.idx/rounds/IDX-20260512-001/insight_layered.yaml
```

## IdeaFirst-MC 파이프라인 내 위치

```
[SDX] .sdx/catalog/                                 # 80 채널 카탈로그
   ↓
[TCX] .tcx/latest/{news,industry_trend,quality_report}.md + manifest
   ↓
[IDX distill] .idx/latest/{insight_layered_traced,...}.yaml ⭐ (여기)
   ↓
[CIX innovate] → idea_pool_v1.yaml                  # 향후 .cix/latest/
   ↓
[IdeaFirst STEP 5-7] 상위 선별 → 최종 1개
```

각 스킬 산출물은 `latest/` 고정 진입점 패턴으로 통일. 라운드별 이력은 `rounds/`에서 round_id로 조회.

## 신규성 검증

기존 LLM 인사이트 도출은 "N개 인사이트 추출"이라는 양적 지시에 의존. 결과 분포가 자연스럽게 Layer 1-3에 편중. IDX는 **층위 분리 강제 + AI별 단일 층위 전담 + IDX_POLICY 임계치 강제 + TCX manifest 추적**으로 깊은 층위 산출을 구조적으로 보장. 특히 Layer 10 (Generative) 강제는 메타 인사이트 산출을 명시적 목표로 가지는 첫 워크플로우.

## File Layout

```
skills/idx/                              # skill (definition)
├── SKILL.md                            # this file
├── schemas/
│   └── insight_output.yaml             # output contracts (v1.2 — evidence v1.1 통일)
└── scripts/
    └── archive_rounds.py               # 90일+ round를 archive/{YYYY-Q[1-4]}/로 이동

<project-root>/.idx/                    # runtime (per-project)
├── index.yaml                           # rounds catalog + latest pointer
├── latest/                              # CIX 등 downstream 고정 진입점
├── rounds/                              # round 완전 보존
└── archive/                             # 90일+ archived rounds
```

## Dependencies

```yaml
required:
  - pg                                  # PPR/Gantree notation
  - pgf                                  # design/plan/execute framework + ★ discovery/personas.json (v1.3)
  - tcx                                  # ★ direct input source (.tcx/latest/)

upstream_chain:
  - pgf/discovery: "{PGF_SKILL_DIR}/discovery/personas.json (v1.0 — 동일 P1-P14 페르소나)"
  - sdx                                  # via tcx (catalog → news/trend)
  - tcx                                  # 직접 입력

downstream:
  - cix                                  # consumes .idx/latest/insight_layered_traced.yaml + 동일 페르소나

skill_directory_refs:
  IDX_SKILL_DIR: "this skill's root (placeholder, runtime-neutral)"
  PGF_SKILL_DIR: "sibling skill — persona definitions (v1.3)"
  TCX runtime: ".tcx/" (project-root relative)
  IDX runtime: ".idx/" (project-root relative)
```
