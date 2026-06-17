---
name: cix
description: "CIX (Creative Innovation eXplorer) — IDX 산출물(.idx/latest/)을 입력으로, 깊은 인사이트에 20가지 혁신 변형 렌즈를 강제 적용해 독창적 아이디어 시드를 생성하는 스킬. 자명한 결합(인접 분야 단순 더하기)을 자동 거부하고 6축 혁신 평가(Novelty/Generativity/Defensibility/Compounding/Surprise/Coherence)로 선별. IDX 다음, IdeaFirst-MC STEP 5 이전 단계. Triggers: CIX, 혁신아이디어, 창의변형, creative innovation, idea variation, lens application, 20렌즈, 혁신렌즈, 아이디어첨가"
user-invocable: true
argument-hint: "innovate|focus|filter [--insights=path] [--lens=L1,L9,L11]"
version: "1.5.1"
author: "양정욱 (sadpig70@gmail.com)"
---

# CIX (Creative Innovation eXplorer) v1.5.1

> 같은 인사이트에서 같은 아이디어가 나오는 이유는 같은 변형을 가하기 때문이다.
> 혁신은 *변형의 강제 다양화*다.

## 존재 이유 (Why)

IdeaFirst STEP 4의 평범성 진단: 8 AI가 동일한 인사이트로부터 모두 "인접 분야 단순 결합" 패턴을 산출했다 (PQC×바이오, LEO×전력망, 휴머노이드×규제). 이는 LLM이 학습 분포 내의 자명한 변형만 자연 선택하기 때문.

CIX는 **20가지 혁신 변형 렌즈**를 강제로 적용해 자명한 변형을 차단하고, **6축 혁신 평가**로 진짜 혁신만 통과시킨다. IDX가 보내준 깊은 인사이트(Gap·Tension·Counterfactual·Generative)에 변형을 가하면 출발점부터 다르므로 결과 아이디어가 평범할 수 없다.

## Inputs

```yaml
input:
  source_root: ".idx/latest"                          # ★ IDX 고정 진입점
  source_files:
    insight_layered_traced: ".idx/latest/insight_layered_traced.yaml"  # primary (evidence-trace)
    insight_layered:        ".idx/latest/insight_layered.yaml"          # fallback
    manifest:               ".idx/latest/manifest.yaml"                  # IDX round 추적용
    audit_report:           ".idx/latest/audit_report.md"                # 선택적 (품질 게이트 체크)
  cli_override: "--insights=<other_path>"             # 옵션, 일반적으로 미사용

  rule: |
    기본은 .idx/latest/. 사용자가 --insights로 다른 파일을 주면 그 경로 사용.
    어느 경우든 manifest.yaml을 함께 로드해 source_idx_round_id 추적.
```

IDX의 evidence-trace된 `insight_layered_traced.yaml`을 primary로 사용. CIX는 어떤 IDX round, 어떤 TCX round, 어떤 SDX catalog version에서 만들어졌는지 모두 manifest chain으로 추적.

## CIX_POLICY (all magic numbers externalized)

```yaml
CIX_POLICY:
  generation:
    lenses_per_insight: 7                  # v1.6 — 5 group-mandatory (A-E) + 2 multi-lens stacks
    multi_stack_depths: [2, 3]
    insights_input_count: 20               # from IDX
    total_raw_variations: 120              # 20 × 6
    agents:
      total: 8
      assignment_strategy: "primary+cross_check"  # PGF P1+P2, P3+P4, P5+P6, P7+P8 (v1.3)
      insights_per_pair: 5                 # 20 insights / 4 pairs
    random_seed_per_round: true            # 재현성

  rejection:
    decision_threshold_reasons: 1          # ★ v1.4: 1로 강화 (CIX R001에서 0% rejection 발생 — I1 fix)
    expected_rejection_rate: 0.50          # ~120 → ~60
    thresholds:
      existing_product_similarity: 0.7     # R3
      baseline_LLM_similarity: 0.7         # R4
      inter_agent_overlap: 0.7             # R5
      adjacent_market_companies_min: 10    # R1
    v1_4_note: |
      v1.3에서 self-flag만 이용 + decision_threshold_reasons=2였던 결과 0% rejection.
      v1.4: threshold=1 (단일 flag도 reject) + main thread heuristic 강화.
      향후 LLM scoring sub-agent 추가 시 다시 threshold=2로 환원 가능.

  scoring:
    axes: [novelty, generativity, defensibility, compounding, surprise, coherence]
    weights:                               # ★ v1.5 IdeaFirst 재조정 (surprise를 1순위로)
      novelty: 1.5                         # ⭐  v1.4: 1.0 → 1.5 (새로움 강화)
      generativity: 2.0                    # ⭐  유지
      defensibility: 0.5                   #     v1.4: 1.0 → 0.5 (구현 비용 0 → 방어 덜 중요)
      compounding: 2.0                     # ⭐  유지
      surprise: 2.5                        # ⭐⭐ v1.4: 1.5 → 2.5 (가장 강한 가중치)
      coherence: 1.0                       #     유지
    denominator: 9.5                       # v1.4: 8.5 → 9.5 (= sum of weights)
    pass_threshold: 6.0                    # of 10.0
    top_k_to_ideafirst_mc: 24

    rationale_v1_5: |                      # ★ NEW v1.5 — IdeaFirst redesign
      v1.4 weights에서 surprise가 1.5/8.5 = 17.6%만 차지 → 새로움 강조 약함.
      IdeaFirst Engine v1.3 §1.3 추가 원칙 "비용 ≪ 가치"에 따라 새로움을 1순위로 재배치.
      defensibility는 AI 시대 구현 비용 0 수렴 → 방어 자체보다 *새로움이 더 강한 해자*가 되므로 강등.
      reference: .pgf/ANALYSIS-IdeaFirst.md D1.
      expected_effect:
        - 같은 24 ideas에서 top-K가 surprise-우선으로 재랭킹됨
        - L10 Generative + 높은 surprise idea의 winner 확률 ↑
        - 동일 generativity·compounding 페어 중 더 새로운 것이 우선

    layer_normalization:                   # ★ NEW v1.4 — IDX layer 별 z-score (I2 fix)
      enabled: true
      method: "z_score_within_layer"
      rationale: |
        v1.3 R001에서 L6_Gap이 top-24 = 0개였음. 원인: heuristic이 L10-source ideas에
        +3 generativity +3 compounding +1 defensibility bonus를 줘서 cross-layer
        비교가 불공정. v1.4는 각 IDX layer 내부에서 먼저 z-score 정규화 후 global
        ranking → 모든 layer가 공평 경쟁.
      formula: |
        score_normalized = (score_raw - layer_mean) / layer_stddev
        global_rank_basis = score_normalized   # 가중합은 z-score 위에서 동일 weights 적용
      layer_min_top_k:                     # ★ NEW v1.4 — IDX architecture 보호
        L6_Gap: 4                          # 최소 4개 (총 24 중 ~17%)
        L7_Tension: 4
        L9_Counterfactual: 4
        L10_Generative: 4
        rationale: "16/24 hard floor (each ≥4), 나머지 8 slots는 점수 순"

    persona_bias_application:              # ★ NEW v1.4 — I3 fix (double-count 제거)
      mode: "filter_direction_only"        # v1.3은 final score에 embed; v1.4는 filter 방향만
      rationale: |
        v1.3에서 persona.novelty bias가 surprise 계산에 직접 들어가서 P8(novelty 2.5)이
        P7(0.3)을 7.5점 추월. P8가 top-5 점유. v1.4는 persona bias가 lens 선택과
        rejection direction에만 영향, final 6-axis score에는 미영향.

    surprise_validation:                   # ★ v1.5 IdeaFirst — D2 fix (fallback 폐기)
      requires_external_call: true         # production CIX에서 LLM sub-agent 필수
      validation_required: 2               # ≥2 methods
      fallback_acceptable: false           # ★ v1.4 true → v1.5 false (자기참조 평가 차단)
      required_methods: ["cross_model"]    # ★ NEW v1.5 — cross_model 의무, 다른 모드는 추가만
      rejection_on_validation_fail: true   # ★ NEW v1.5 — validation 실패 시 idea 자체 reject
      baseline_LLM_must_differ:            # ★ NEW v1.5 — 모델 클래스별 명시
        if_main_Claude:   "baseline ∈ {GPT-5, Gemini-3, Grok-5, Mistral-Large-3}"
        if_main_GPT:      "baseline ∈ {Claude, Gemini-3, Grok-5, Mistral-Large-3}"
        if_main_Gemini:   "baseline ∈ {Claude, GPT-5, Grok-5, Mistral-Large-3}"
        general_rule:     "main model class와 다른 family. 같은 family 내 다른 모델 사이즈는 허용 X."
      manifest_record_required:            # ★ NEW v1.5
        - baseline_model_id                # 사용한 baseline 모델 명
        - baseline_call_session_hash       # 호출 세션 격리 증명
        - prediction_similarity_per_persona  # 14 페르소나 각각의 예측 유사도
      v1_5_note: |
        v1.4 fallback_acceptable=true는 deprecated. heuristic-only 라운드는 manifest에
        execution.scoring_mode='deprecated_v1_5_heuristic'으로 표시되며 quality gate에서 fail.
        근거: IdeaFirst Engine v1.3 §1.3 "비용 ≪ 가치" + .pgf/ANALYSIS-IdeaFirst.md D2.
        같은 모델 자기참조 평가로는 새로움(novelty/surprise) 측정 불가 — 자명한 것을 자명하다고 모르는 함정.

  environment_requirements:                # ★ NEW v1.5.1 — capability handling (Codex 지적 반영)
    cross_model_baseline_required: true    # surprise_validation 의무를 충족하려면 필수
    capability_probe_required_before_run: true   # 라운드 시작 전 환경 capability 확인 의무

    capability_probe:                      # 환경이 다른 모델 호출 가능한지 사전 검사
      tests:
        - "main model class와 다른 family LLM의 API key 존재 여부"
        - "다른 모델로 trivial prompt 호출 가능한지 (네트워크/권한/quota 확인)"
        - "session 격리 (lens_info_hidden, context_minimal) 적용 가능한지"
      output_field: "manifest.environment.cross_model_capability"
      values: ["available", "unavailable", "degraded"]

    on_unavailable:                        # ★ 단독 환경 (e.g., Codex standalone) 처리
      action: "block_round"
      blocker_reason: "cross_model_baseline_unavailable"
      do_not:                              # 다음 행동은 금지
        - "fallback heuristic으로 우회 (v1.5에서 폐기됨)"
        - "scoring_mode='deprecated_v1_5_heuristic'으로 라운드 강행"
        - "surprise 점수 self-flag만으로 채워 출력"
      do:                                  # 대신 다음을 수행
        - "manifest.round.status = '(blocked)'"
        - "manifest.round.blocker_reason = 'cross_model_baseline_unavailable'"
        - "manifest.round.handoff_required = true"
        - "manifest.round.handoff_to = 'human_or_orchestrator_with_external_api'"
        - ".cix/rounds/{round_id}/HANDOFF.md 작성 — 필요한 baseline 모델 + 호출 양식"
        - "raw_seed_ideas.yaml은 출력 OK (surprise 계산 전 단계 산출물)"
        - "scored_ideas.yaml / idea_pool.yaml은 출력 X (surprise 의존 단계)"

    on_degraded:                           # quota 부족, 일부 페르소나만 baseline 가능 등
      action: "partial_round + flag"
      blocker_reason: "cross_model_partial_capability"
      manifest_record:
        - "baseline_calls_attempted / baseline_calls_succeeded"
        - "personas_validated / personas_skipped"
      idea_acceptance: "validated personas만 (skipped personas는 surprise 0으로 보수 처리)"

    handoff_md_schema:                     # .cix/rounds/{round_id}/HANDOFF.md 의무 필드
      required_sections:
        - blocker_context: "어느 stage에서 어떤 capability 부족"
        - resume_instruction: "외부 baseline API 갖춘 환경에서 어떤 명령으로 재개"
        - required_models: "필요한 baseline 모델 class 리스트 (e.g., GPT-5 또는 Gemini-3)"
        - input_seeds_path: ".cix/rounds/{round_id}/raw_seed_ideas.yaml (수행 가능 부분)"
        - resume_command: "/cix innovate --resume-round={round_id} --skip-already-validated"

    rationale: |
      v1.5는 cross-model baseline을 의무화했지만, 모든 런타임이 다른 family LLM 호출 능력을
      가지지는 않는다 (예: Codex 단독 환경, 로컬 모델 환경, sandboxed agent).
      그런 환경에서 fallback heuristic으로 우회하면 v1.5 정책 자체가 무의미해진다.
      따라서 environment capability를 *명시적 precondition*으로 다루고, 부족 시
      라운드를 깔끔하게 (blocked) + handoff_required로 표시하여 다른 환경으로 인계한다.
      "blocked"는 실패가 아니라 *환경 매칭 대기 상태*임을 manifest에 기록.

  surprise_validation:
    min_methods_required: 2                # 자기참조 편향 방지 (v1.1)
    available_methods:
      - cross_model                        # 14 페르소나를 7개 다른 LLM에 2개씩 분산 (7×2=14)
      - cross_prompt                       # 페르소나마다 다른 prompting framework
      - blind_baseline                     # 페르소나에게 lens 정보 숨김
      - temporal_separation                # 다른 세션에서 격리 호출
    expert_persona_count: 14               # ★ v1.6 — 7-model × 2 baseline (8→14)
    persona_similarity_cutoff: 0.5         # < 0.5면 not_predicted

  personas:                                # NEW v1.3 — PGF discovery 페르소나 정식 통합
    source: "{PGF_SKILL_DIR}/discovery/personas.json"
    version_pin: "1.0"
    enabled_set: [P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P14]   # ★ v1.6 — 14 페르소나 (7-model baseline)
    use_for_surprise_validation: true      # ★ v1.6 — P1-P14로 확장 (구 P1-P8 8-persona)
    use_for_lens_assignment: true          # 페르소나의 cognitive_style ↔ lens 그룹 affinity
    
    lens_group_affinity:                   # 페르소나 ↔ 25렌즈 5그룹 매핑 (v1.6: P9-P14 + Group_E 추가)
      Group_A_Inversion:                   # L1-L8 (방향 뒤집기)
        primary: [P1, P7, P11]             # creative + critical + adversary — 자명한 것·가정 뒤집기
        rationale: "Disruptive Engineer + Contrarian Critic + Adversarial Robustness 인지가 inversion 핵심"
      Group_B_Shift:                       # L9-L14 (차원 이동)
        primary: [P4, P8, P12, P13]        # cross-domain + 생태 biomimicry + 역사 temporal shift
        rationale: "cross-domain transfer가 본질 — 생태(P12)·시간축(P13) 이동 포함"
      Group_C_Constraint:                  # L15-L17 (제약 조작)
        primary: [P3, P5, P9]              # critical/policy + analytical/tech + ethics — 제약 인식
        rationale: "Regulatory Architect + Field Operator + Agency Ethicist가 제약(집행·운영·주체성)을 알아봄"
      Group_D_Composition:                 # L18-L19 (합성·분해)
        primary: [P2, P6, P10, P14]        # unit economics + adoption + UX 단위 + 인센티브 메커니즘
        rationale: "Cold-eyed Investor + Future Sociologist + UX Anthropologist + Mechanism Designer가 단위·메커니즘 합성 이해"
      Group_E_Restructuring:               # L21-L25 (자기참조·순서·반대편·경계·상태형태 재배치) — v1.6 신설
        primary: [P14, P8, P11]            # 메커니즘 디자이너 + 융합(재귀/메타) + 적대적(경계 재배치)
        rationale: "Mechanism Designer(반대편/stock-flow) + Convergence Architect(recursion/meta) + Adversarial Robustness(boundary/sequence)가 구조 재배치 핵심"
      L20_MultiStack:                      # 모든 페르소나 가능, 그룹 직교 강제 (그룹 A-E 간 조합)
        primary: [P1, P4, P8]              # creative 페르소나가 stack 깊이 활용
    
    surprise_validation_persona_pool:      # ★ v1.6 — P1-P14 (7-model × 2 baseline)
      - {pgf_id: P1, role: "VC 투자자 → 대체: Disruptive Engineer (paradigm shift 예측 잘함)", baseline_model: grok}
      - {pgf_id: P2, role: "Cold-eyed Investor (직접 매핑 — 시장 예측)", baseline_model: kimi}
      - {pgf_id: P3, role: "정책 입안자 → Regulatory Architect (직접 매핑)", baseline_model: claude}
      - {pgf_id: P4, role: "학계 연구자 → Connecting Scientist (직접 매핑)", baseline_model: gemini}
      - {pgf_id: P5, role: "산업 엔지니어 → Field Operator (직접 매핑)", baseline_model: kimi}
      - {pgf_id: P6, role: "비판적 저널리스트 → Future Sociologist (사회 영향 관점)", baseline_model: grok}
      - {pgf_id: P7, role: "컨설턴트 → Contrarian Critic (failure modes 인지)", baseline_model: claude}
      - {pgf_id: P8, role: "인접 분야 침입자 → Convergence Architect (cross-field)", baseline_model: gemini}
      - {pgf_id: P9, role: "Practical Agency Ethicist (인간 주체성·존엄 관점)", baseline_model: chatgpt}
      - {pgf_id: P10, role: "Embodied UX Anthropologist (실사용 마찰·접근성)", baseline_model: chatgpt}
      - {pgf_id: P11, role: "Adversarial Robustness Analyst (공격·악용 시나리오)", baseline_model: deepseek}
      - {pgf_id: P12, role: "Regenerative Systems Ecologist (생태·자원 한계)", baseline_model: deepseek}
      - {pgf_id: P13, role: "Historical Cycle Analyst (전례·채택곡선)", baseline_model: qwen}
      - {pgf_id: P14, role: "Mechanism Designer (인센티브·시장 메커니즘)", baseline_model: qwen}
    
    use_idx_persona_chain: true            # IDX manifest의 persona_chain 추적

  baseline_control:
    model_must_differ_from_main: true      # Claude면 GPT/Gemini 등 (v1.5에서 강화)
    prompt_style: "GENERIC"
    lens_info_hidden: true
    session_isolated: true
    context_minimal: true
    enforcement: "strict"                  # ★ v1.5 — soft → strict 승격
    on_violation: "reject_idea"            # ★ v1.5 — 위반 시 idea reject (v1.4: warning only)
    audit_trail:                           # ★ v1.5 — manifest 기록 의무
      - main_model_class
      - baseline_model_class
      - baseline_model_id
      - baseline_session_hash
      - prediction_similarity_per_persona

  lens_distribution:
    same_lens_per_agent_warning: 5         # 한 AI가 같은 렌즈 5+회 경고
    stack_grouping_rule: "different_groups_only"  # 그룹 내 2개 stack 금지

  storage:
    root: ".cix"                           # project-root relative
    layout:
      index:   "index.yaml"
      latest:  "latest/"                   # ★ 후속 IdeaFirst-MC STEP 5+ 고정 진입점
      rounds:  "rounds/"
      archive: "archive/"
    round_id_format: "CIX-{YYYYMMDD}-{NNN}"
    files_per_round:
      - idea_pool.yaml                     # 메인 (24 ideas)
      - idea_pool_annotated.yaml           # 변형 경로 추적 포함
      - raw_seed_ideas.yaml                # 거부 전 120건 (디버깅)
      - filtered_ideas.yaml                # 거부 후 ~60건
      - scored_ideas.yaml                  # 6축 평가 결과
      - lens_assignment.yaml               # 인사이트당 6 렌즈 할당 (재현성)
      - manifest.yaml                      # source IDX round + policy snapshot
      - generation_log.yaml                # AI별 렌즈 사용·거부·점수 로그
    latest_strategy: "copy"                # Windows 안전, symlink 아님
    retain_in_rounds_days: 90
    archive_target_pattern: "archive/{YYYY-Q[1-4]}/"
    archive_script: "{CIX_SKILL_DIR}/scripts/archive_rounds.py"
    concurrency_lock: ".cix/.lock"
```

## Modes

```yaml
innovate:
  steps: [load_idx_inputs, validate_manifest, assign_lenses, generate_variations, reject_obvious, score_6_axes, select_top_k, trace_annotate, emit]
focus:
  steps: [load_idx_inputs, validate_manifest, apply_specified_lenses_only, score_6_axes, emit]
  note: "--lens=L1,L9,L11 등으로 특정 렌즈만. 모든 인사이트에 적용"
filter:
  steps: [load_external_ideas, score_6_axes, emit_evaluation]
  note: "외부 아이디어를 6축 평가만 수행. 변형 생성 X"
```

## 20 혁신 렌즈 (4 그룹)

> 각 렌즈 상세 프롬프트는 `{CIX_SKILL_DIR}/prompts/lens_catalog.md` 참조.

### 그룹 A: Inversion Lenses (8개) — 방향 뒤집기

```yaml
L1_DirectionReversal:
  desc: "주체-객체, 검색자-피검색자, 능동-수동 반전"
  example: "검색엔진이 사용자를 검색 → 사용자가 검색엔진에 검색당하는 시스템"

L2_StakeholderInversion:
  desc: "갑↔을, 규제자↔규제대상, 소비자↔생산자"
  example: "환자가 의사를 평가 → 환자가 임상시험 protocol을 설계"

L3_CostInversion:
  desc: "무료↔유료, 비용↔수익, 적자↔흑자 구조 반전"
  example: "광고가 콘텐츠를 따라감 → 콘텐츠가 광고를 따라가서 광고가 본질"

L4_PrivacyInversion:
  desc: "공개↔비공개, 투명↔불투명 정보 흐름 반전"
  example: "기업 재무가 공개 → 모든 거래가 공개되고 신원만 비공개"

L5_OwnershipInversion:
  desc: "소유↔공유, 사유↔공공, 단독↔분산 소유"
  example: "데이터 소유권을 플랫폼이 가짐 → 사용자가 갖고 플랫폼이 임대"

L6_TrustModelInversion:
  desc: "중앙↔분산, 신뢰↔무신뢰, 인증↔자가증명"
  example: "은행이 신원 인증 → 사용자가 은행에게 신원 검증 능력을 인증"

L7_FailureAsFeature:
  desc: "버그→기능, 실패→자원, 단점→차별점"
  example: "AI hallucination = 버그 → AI hallucination = 창의성 발생기"

L8_SideEffectMining:
  desc: "부산물·외부효과·노이즈가 본질이 되는 시스템"
  example: "이산화탄소가 폐기물 → 이산화탄소가 합성 원료의 본질"
```

### 그룹 B: Shift Lenses (6개) — 차원 이동

```yaml
L9_ScaleShift:
  desc: "micro↔macro 규모 이동"
  example: "도시 단위 에너지 거래 → 가전 단위 / 국가 단위 에너지 거래"

L10_TimeShift:
  desc: "시간 스케일 이동 — 50년 전/100년 후"
  example: "현재 클라우드 → 100년 후 클라우드 / 50년 전이라면 무엇으로 구현"

L11_DomainTransplant:
  desc: "한 분야 패턴을 다른 분야로 *이식*"
  example: "면역계 분산 방어 → 사이버보안 / 게임 매치메이킹 → 노동시장"

L12_GranularityShift:
  desc: "처리 단위 변경 — 묶음↔개별"
  example: "월별 청구 → 초당 청구 / 개별 결제 → 묶음 정기 자동결제"

L13_FrequencyShift:
  desc: "주기 변경 — 실시간↔일회↔영구"
  example: "주식 거래 (실시간) → 1년 1회 / 평생회원권 → 분 단위 회원권"

L14_MediumSwap:
  desc: "매체·물질 교체 — 디지털↔물리↔생물↔화학"
  example: "디지털 컴퓨팅 → DNA 컴퓨팅 / 메일 통신 → 페로몬 통신"
```

### 그룹 C: Constraint Lenses (3개) — 제약 조작

```yaml
L15_ConstraintRemoval:
  desc: "당연시되는 제약을 제거하면?"
  example: "운전면허 폐지 / 국경 폐지 / 저작권 폐지"

L16_ConstraintAddition:
  desc: "극단적 제약 추가가 단순화·집중을 낳음"
  example: "휴대폰에 키패드 제거 → iPhone / 메뉴 1개 식당"

L17_ConstraintSubstitute:
  desc: "한 제약을 완전히 다른 제약으로 교체"
  example: "비용 제약 → 시간 제약 / 공간 제약 → 신뢰 제약"
```

### 그룹 D: Composition Lenses (3개) — 합성·분해

```yaml
L18_Atomization:
  desc: "더 작게 쪼개기 — micro-services, micro-payments, micro-tasks"
  example: "기사 단위 신문 → 문단 단위 / 일 단위 고용 → 작업 단위 고용"

L19_Aggregation:
  desc: "더 크게 묶기 — aggregator, bundler, hub"
  example: "개별 카드 → 통합 멤버십 / 분산 클라우드 → 통합 카탈로그"

L20_MultiLensStack:
  desc: "여러 렌즈의 순차 적용 — 가장 강한 변형 (CIX_POLICY.lens_distribution.stack_grouping_rule 적용)"
  example: "L1(Inversion) → L11(Transplant) → L17(Constraint Sub)"
```

---

## 6축 혁신 평가 (의미·예시만 — 임계값은 CIX_POLICY)

```yaml
Novelty:        "기존 시장에 없는가"
Generativity:   "이 아이디어가 또 다른 아이디어를 낳는가"   # ⭐ weight 2.0
Defensibility:  "후발주자가 따라잡기 어려운 해자가 있는가"
Compounding:    "시간 지날수록 가치가 증가하는가"           # ⭐ weight 2.0
Surprise:       "해당 분야 전문가도 예측 못했을 정도인가"   # ⭐ weight 1.5, persona 검증
Coherence:      "내부 논리 일관성"
```

가중치·denominator·pass_threshold는 `CIX_POLICY.scoring` 단일 출처. ⭐ 표시 3개 (Generativity, Compounding, Surprise) 가 진짜 대박 시스템을 가르는 축.

---

## DESIGN: Gantree

> 모든 흐름 제어(if/while/for/Convergence Loop)는 PPR `def` 블록에 위치. Gantree는 노드 구조만.

```
CIX_Main // CIX 메인 진입점 (in-progress) @v:1.2
    ModeInnovate // 기본 혁신 변형 모드 (designing)
        Phase1_LoadInsights // IDX latest 입력 로딩 (designing)
            AI_load_idx_insight_layered_traced  // .idx/latest/insight_layered_traced.yaml
            AI_load_idx_manifest                // .idx/latest/manifest.yaml → source_idx_round_id
            AI_validate_idx_audit_passed        // IDX audit_report.md 품질 통과 여부
            AI_validate_layer_distribution      // L6/L7/L9/L10 균형 확인
            # output: loaded_insights.yaml      (in-memory; not persisted unless --keep-intermediate)

        Phase2_LensAssignment // 인사이트당 6 렌즈 할당 (designing) @dep:Phase1_LoadInsights
            AI_assign_mandatory_4_group_lenses  // 그룹별 1개씩 (random per CIX_POLICY)
            AI_assign_2_multi_lens_stacks       // depth 2, 3 (CIX_POLICY.generation.multi_stack_depths)
            AI_validate_stack_grouping_rule     // 같은 그룹 내 stack 금지
            AI_verify_lens_distribution_evenness  // 8 AI 전체에서 균등
            # output: lens_assignment.yaml      (round dir; 재현성 핵심)

        Phase3_VariationGeneration // 8 AI 병렬 변형 생성 (designing) @dep:Phase2_LensAssignment
            [parallel]
            P1_apply_lenses_to_insights_1_to_5     // Disruptive Engineer (Group A bias)
            P7_apply_lenses_to_insights_1_to_5     // Contrarian Critic — cross-check (Group A bias)
            P4_apply_lenses_to_insights_6_to_10    // Connecting Scientist (Group B bias)
            P8_apply_lenses_to_insights_6_to_10    // Convergence Architect — cross-check (Group B bias)
            P3_apply_lenses_to_insights_11_to_15   // Regulatory Architect (Group C bias)
            P5_apply_lenses_to_insights_11_to_15   // Field Operator — cross-check (Group C bias)
            P2_apply_lenses_to_insights_16_to_20   // Cold-eyed Investor (Group D bias)
            P6_apply_lenses_to_insights_16_to_20   // Future Sociologist — cross-check (Group D bias)
            [/parallel]
            AI_merge_dedup_same_insight_lens_pair  // 같은 (insight, lens) 페어에서 더 나은 것 선택
            # output: raw_seed_ideas.yaml       (~120, round dir)

        Phase4_ObviousRejection // 자명 거부 필터 (designing) @dep:Phase3_VariationGeneration
            [parallel]
            AI_check_market_adjacency           // R1 (CIX_POLICY.rejection.thresholds)
            AI_check_lens_traceability          // R2
            AI_search_existing_products         // R3
            AI_baseline_LLM_prediction_test     // R4 (다른 model)
            AI_check_inter_agent_overlap        // R5
            AI_check_incumbent_benefit          // R6
            [/parallel]
            AI_aggregate_rejection_decisions    // ≥CIX_POLICY.rejection.decision_threshold_reasons → REJECT
            # output: filtered_ideas.yaml       (~60)

        Phase5_InnovationScoring // 6축 평가 (designing) @dep:Phase4_ObviousRejection
            AI_score_novelty
            AI_score_generativity
            AI_score_defensibility
            AI_score_compounding
            AI_score_surprise_via_expert_personas  // ≥CIX_POLICY.surprise_validation.min_methods_required
            AI_score_coherence
            AI_weighted_total                   // CIX_POLICY.scoring (weights + denominator)
            # output: scored_ideas.yaml

        Phase6_TopKSelection // 상위 K 선정 (designing) @dep:Phase5_InnovationScoring
            AI_sort_by_total_score
            AI_ensure_lens_diversity_in_top_k   // CIX_POLICY.scoring.top_k_to_ideafirst_mc
            AI_ensure_layer_diversity_in_top_k  // L6/L7/L9/L10 균형 유지
            # output: idea_pool.yaml

        Phase7_TraceAndAnnotate // 변형 경로 추적 첨부 (designing) @dep:Phase6_TopKSelection
            AI_attach_insight_to_idea_trace     // source_insight_id + IDX evidence chain
            AI_attach_lens_application_steps    // transformation steps
            AI_attach_baseline_comparison       // baseline LLM 예측 similarity
            AI_attach_surprise_validation_meta  // applied methods (재현성)
            # output: idea_pool_annotated.yaml

        Phase8_CatalogEmit // 최종 출력 (designing) @dep:Phase7_TraceAndAnnotate
            AI_build_manifest                   // source_idx_round, policy snapshot, hashes, cli_args
            AI_build_generation_log             // AI별 lens 사용·거부·점수 로그
            AI_emit_round_dir                   // .cix/rounds/{round_id}/ — 8 files
            AI_sync_latest                      // .cix/latest/ overwrite (copy)
            AI_update_cix_index                 // .cix/index.yaml — prepend round
            AI_maybe_run_archive                // 90일+ 자동 이동
            # output_root: .cix/

    ModeFocus // 특정 렌즈만 집중 적용 (designing)
        # input: --lens=L1,L9,L11
        # process: AI_parse_lens_args → AI_apply_only_specified_lenses_to_all_insights
        # note: 6축 평가 동일 적용, top_k는 적용 렌즈 수에 비례 축소
        # output: focused_ideas.yaml (round dir 내)

    ModeFilter // 외부 아이디어 6축 평가만 (designing)
        # input: --external-ideas=path
        # process: AI_load_external_ideas → AI_score_6_axes → AI_emit_evaluation_report
        # note: 변형 생성 X, 평가만. baseline_comparison 의무 적용
        # output: evaluation.md (round dir 내)
```

---

## PPR: 핵심 함수 정의

### Phase 8: 출력 emit (TCX/IDX와 동일 패턴)

```python
def AI_emit_round_dir(round_dir, artifacts, manifest, generation_log):
    """원자적 round dir 작성. artifacts = 6 main files."""
    # acceptance_criteria:
    #   - 8 files present in round dir (6 artifacts + manifest + generation_log)
    #   - latest/ byte-identical to new round dir
    #   - index.yaml.latest_round_id == new round id
    AI_acquire_lock(CIX_POLICY.storage.concurrency_lock)
    try:
        AI_write_files(round_dir, artifacts | {"manifest": manifest, "generation_log": generation_log})
        AI_clear_dir(CIX_POLICY.storage.latest)
        AI_copy_tree(round_dir, CIX_POLICY.storage.latest)
        AI_update_cix_index(...)
        AI_maybe_run_archive(CIX_POLICY.storage)
    finally:
        AI_release_lock(CIX_POLICY.storage.concurrency_lock)
```

### 렌즈 적용 (단일 + Stack)

```python
def AI_apply_single_lens(insight: Insight, lens: Lens) -> SeedIdea:
    """한 인사이트에 한 렌즈를 적용해 시드 아이디어 생성.
    프로세스:
      1. 인사이트의 핵심 구조 파싱 (주체, 객체, 방향, 자원, 제약)
      2. 렌즈에 정의된 변형 규칙 적용
      3. 변형 후 일관된 시스템 묘사로 재구성
      4. lens_application_trace 명시
    """
    # acceptance_criteria:
    #   - 변형 흔적이 명시적으로 추적 가능 (lens_traceable: true)
    #   - 결과가 일관된 시스템 묘사
    #   - 원 인사이트와 명확한 연결 유지 (source_insight_id)
    structure = AI_parse_insight_structure(insight)
    transformed = lens.transform(structure)
    idea = AI_synthesize_system_description(transformed)
    idea.lens_application = {
        "primary_lens": lens.id,
        "lens_stack": None,
        "transformation": {
            "original_problem": structure.summary,
            "lens_logic": lens.describe_logic(structure),
            "result": idea.system_description_head,
        },
    }
    return idea


def AI_apply_multi_lens_stack(insight: Insight, lenses: list[Lens]) -> SeedIdea:
    """여러 렌즈를 순차 적용. 그룹 간 조합만 허용."""
    # acceptance_criteria:
    #   - CIX_POLICY.lens_distribution.stack_grouping_rule 준수 (different_groups_only)
    #   - stack depth in CIX_POLICY.generation.multi_stack_depths
    assert AI_validate_stack_grouping(lenses), "Same-group lenses cannot stack"
    current = AI_parse_insight_structure(insight)
    trace = []
    for lens in lenses:
        current = lens.transform(current)
        trace.append({"lens": lens.id, "intermediate": current})
    idea = AI_synthesize_system_description(current)
    idea.lens_application = {
        "primary_lens": lenses[0].id,
        "lens_stack": [l.id for l in lenses],
        "transformation": {f"step_{i+1}": t for i, t in enumerate(trace)},
    }
    return idea
```

### 자명 거부 검사

```python
def AI_reject_obvious(idea: SeedIdea) -> RejectDecision:
    """자명한 결합은 자동 거부. CIX_POLICY.rejection 적용."""
    P = CIX_POLICY.rejection
    reasons = []
    if AI_domains_already_combined_in_market(idea.domains, min_companies=P.thresholds.adjacent_market_companies_min):
        reasons.append("ADJACENT_DOMAINS_MARKET_SATURATED")
    if not idea.lens_application_traceable:
        reasons.append("NO_LENS_TRANSFORMATION")
    existing = AI_search_existing_products(idea)
    if existing.similarity > P.thresholds.existing_product_similarity:
        reasons.append(f"EXISTING_PRODUCT_MATCH:{existing.product_name}")
    if AI_compute_similarity(AI_baseline_LLM_prediction_test(idea.source_insight), idea) > P.thresholds.baseline_LLM_similarity:
        reasons.append("PREDICTABLE_BY_BASELINE")
    if AI_inter_agent_overlap(idea) > P.thresholds.inter_agent_overlap:
        reasons.append("INTER_AGENT_DUPLICATE")
    if AI_benefits_only_incumbents(idea):
        reasons.append("INCUMBENT_FAVORING")
    return {
        "rejected": len(reasons) >= P.decision_threshold_reasons,
        "reasons": reasons,
        "review_needed": len(reasons) == P.decision_threshold_reasons - 1,
    }
```

### Baseline LLM Control (v1.1 자기참조 방지)

```python
def AI_baseline_LLM_prediction_test(insight: Insight) -> SeedIdea:
    """렌즈 없이 baseline LLM에 단순 요청. CIX_POLICY.baseline_control 준수."""
    # acceptance_criteria:
    #   - model_must_differ_from_main: 메인이 Claude면 baseline은 GPT/Gemini
    #   - session_isolated + lens_info_hidden + context_minimal
    BC = CIX_POLICY.baseline_control
    return AI_call_external_LLM(
        model_class="DIFFERENT_FROM_MAIN" if BC.model_must_differ_from_main else "ANY",
        prompt_style=BC.prompt_style,
        lens_info_hidden=BC.lens_info_hidden,
        session_isolated=BC.session_isolated,
        context_minimal=BC.context_minimal,
        input=insight.statement,
    )
```

### Surprise 평가 (전문가 페르소나) — v1.1 자기참조 방지

```python
def AI_score_surprise_via_expert_personas(idea: SeedIdea) -> int:
    """14 전문가 페르소나가 아이디어를 예측 가능한지 평가.
    CIX_POLICY.surprise_validation.min_methods_required 이상의 cross-validation 의무."""
    # acceptance_criteria:
    #   - applied validation methods >= CIX_POLICY.surprise_validation.min_methods_required
    #   - surprise_validation_methods 기록 (재현성)
    P = CIX_POLICY.surprise_validation
    applied = AI_select_validation_methods(idea, min_count=P.min_methods_required, pool=P.available_methods)
    assert len(applied) >= P.min_methods_required, "Self-reference bias risk"
    # v1.6 — PGF discovery P1-P14 사용 (CIX_POLICY.personas.surprise_validation_persona_pool)
    # 기존 ad-hoc 8 expert를 cross-skill 일관성 위해 PGF 페르소나로 통일(v1.3) → 14로 확장(v1.6).
    EXPERT_PERSONAS = AI_load_pgf_personas(
        source=CIX_POLICY.personas.source,
        version_pin=CIX_POLICY.personas.version_pin,
        ids=CIX_POLICY.personas.enabled_set,   # [P1..P8]
    )
    not_predicted_count = 0
    for persona in EXPERT_PERSONAS:
        prediction = AI_call_persona_with_validation(
            persona=persona, insight=idea.source_insight,
            validation_methods=applied,
            prompt="이 인사이트를 보고 새 시스템을 예측해보라",
        )
        if AI_compute_similarity(prediction, idea) < P.persona_similarity_cutoff:
            not_predicted_count += 1
    surprise_score = min(10, not_predicted_count * (10 / P.expert_persona_count))  # 8명 시 1.25
    idea.surprise_validation_methods = applied
    return surprise_score
```

### 가중 총점 계산 (CIX_POLICY 단일 출처)

```python
def AI_weighted_total(idea: SeedIdea) -> float:
    """CIX_POLICY.scoring.weights / denominator. 본 공식이 정본 — schemas는 참조만."""
    # acceptance_criteria:
    #   - 모든 axes (CIX_POLICY.scoring.axes) 점수 존재
    #   - 0.0 <= total <= 10.0
    W = CIX_POLICY.scoring.weights
    raw = sum(getattr(idea.scores, ax) * getattr(W, ax) for ax in CIX_POLICY.scoring.axes)
    return raw / CIX_POLICY.scoring.denominator
```

---

## Output Storage Layout

Runtime artifacts live at project-root `.cix/`:

```
<project-root>/
└── .cix/
    ├── index.yaml                     # rounds catalog + latest_round_path
    ├── latest/                        # ★ IdeaFirst-MC STEP 5+ 등이 사용하는 고정 진입점
    │   ├── idea_pool.yaml
    │   ├── idea_pool_annotated.yaml
    │   ├── raw_seed_ideas.yaml
    │   ├── filtered_ideas.yaml
    │   ├── scored_ideas.yaml
    │   ├── lens_assignment.yaml
    │   ├── manifest.yaml              # IDX source_round + CIX policy snapshot
    │   └── generation_log.yaml        # AI별 lens 사용·거부·점수
    ├── rounds/
    │   ├── CIX-20260513-001/          # 8 files per round
    │   ├── CIX-20260513-002/
    │   └── ...
    └── archive/
        └── 2026-Q2/
            ├── .READONLY
            └── CIX-*/...
```

**Downstream contract** — IdeaFirst-MC STEP 5는 `.cix/latest/idea_pool_annotated.yaml` 고정 경로로 소비.
**Upstream contract** — CIX는 `.idx/latest/*` 고정 경로로 소비. manifest로 IDX round_id 추적.

---

## Outputs

### idea_pool.yaml (메인)

상세 스키마: `{CIX_SKILL_DIR}/schemas/idea_output.yaml`. 핵심:

```yaml
innovation:
  version: "v1.2"
  round_id: "CIX-{YYYYMMDD}-{NNN}"
  built_at: "ISO-8601"
  source_idx_round: "IDX-{YYYYMMDD}-{NNN}"               # ★ IDX round 추적
  source_tcx_round: "TCX-{YYYYMMDD}-{NNN}"               # via IDX manifest chain
  source_catalog_version: "{catalog.version}"            # SDX version traceable
  generation_stats:
    raw_variations: "{CIX_POLICY.generation.total_raw_variations}"
    rejected_obvious: 58
    passed_filter: 62
    top_k_selected: "{CIX_POLICY.scoring.top_k_to_ideafirst_mc}"
  layer_distribution_in_top_K: {L6_Gap: 6, L7_Tension: 6, L9_Counterfactual: 6, L10_Generative: 6}
  ideas: [...]                                           # K entries
```

상세 entry 스키마 + Layer별 필수 필드는 `schemas/idea_output.yaml` 참조 (v1.2 — evidence v1.1 형식 통일).

---

## Usage

```bash
# 기본 — IDX latest 입력 사용
/cix innovate

# 특정 IDX round 또는 archive
/cix innovate --insights=.idx/rounds/IDX-20260512-001/insight_layered_traced.yaml

# 특정 렌즈만 집중 (실험·연구용)
/cix focus --lens=L7,L11,L15

# 외부 아이디어 6축 평가만
/cix filter --external-ideas=external_ideas.yaml
```

## Manual Baseline Guide

CIX v1.5.1 production surprise validation requires cross-model baseline.
When the runtime cannot call other model families directly, use the local
manual baseline guide:

```text
skills/cix/references/manual_baseline_guide.md
```

The guide standardizes external CLI agent assignments, prompts, required YAML
shape, output paths under `.cix/manual_baseline/`, and the resume sequence for
CIX → EVX → AOX.

## IdeaFirst-MC 파이프라인 내 위치

```
[SDX] .sdx/catalog/                                 # 80 채널 카탈로그 (lockable)
   ↓
[TCX] .tcx/latest/{news,industry_trend,quality_report}.md + manifest
   ↓
[IDX] .idx/latest/insight_layered_traced.yaml + manifest
   ↓
[CIX innovate] .cix/latest/idea_pool_annotated.yaml ⭐ (여기)
   ↓
[IdeaFirst-MC STEP 5] 투자자 관점 선별 (top 3 per agent)
   ↓
[IdeaFirst-MC STEP 6] Cross-AI 평가
   ↓
[IdeaFirst-MC STEP 7] 최종 1개
```

각 스킬 산출물은 `latest/` 고정 진입점 패턴으로 통일. 라운드별 이력은 `rounds/`에서 round_id로 조회.

## 신규성 검증

기존 LLM 아이디어 생성은 자유 발산 또는 단순 결합에 의존. CIX는 **변형 강제 + 자명 거부 + 6축 평가 + 자기참조 편향 방지**를 하나의 워크플로우로 묶어 평범한 결합을 구조적으로 차단한다. 특히 **Surprise를 다른 모델 페르소나로 외부 검증**하는 메커니즘과 **Compounding/Generativity 가중**으로 진짜 대박 시스템(시간 지날수록 가치 증가, 다른 아이디어를 낳는)을 우선 선별한다는 점이 차별적.

## File Layout

```
skills/cix/                              # skill (definition)
├── SKILL.md                            # this file
├── schemas/
│   └── idea_output.yaml                # output contracts (v1.2 — evidence v1.1 통일, 4 contracts)
├── prompts/
│   └── lens_catalog.md                 # 25 lens detailed prompts (groups A-E)
├── references/
│   └── manual_baseline_guide.md         # external CLI baseline operation guide
└── scripts/
    └── archive_rounds.py               # 90일+ round를 archive/{YYYY-Q[1-4]}/로 이동

<project-root>/.cix/                    # runtime (per-project)
├── index.yaml                           # rounds catalog + latest pointer
├── latest/                              # IdeaFirst-MC 등 downstream 고정 진입점
├── rounds/                              # round 완전 보존
└── archive/                             # 90일+ archived rounds
```

## Dependencies

```yaml
required:
  - pg                                  # PPR/Gantree notation
  - pgf                                  # design/plan/execute framework + ★ discovery/personas.json (v1.3)
  - idx                                  # ★ direct input source (.idx/latest/)

upstream_chain:
  - pgf/discovery: "{PGF_SKILL_DIR}/discovery/personas.json (v1.0 — 동일 P1-P14 페르소나, TCX/IDX와 공유)"
  - sdx                                  # via tcx → idx (catalog → trend → insight)
  - tcx                                  # via idx (industry_trend → insight)
  - idx                                  # 직접 입력 + persona chain inheritance

downstream:
  - ideafirst-mc                              # consumes .cix/latest/idea_pool_annotated.yaml (STEP 5-7)

skill_directory_refs:
  CIX_SKILL_DIR: "this skill's root (placeholder, runtime-neutral)"
  PGF_SKILL_DIR: "sibling skill — persona definitions (v1.3)"
  IDX runtime:   ".idx/" (project-root relative)
  CIX runtime:   ".cix/" (project-root relative)
```

## 향후 확장 (v1.3+)

- **렌즈 진화**: 사용 결과로 효과적인 렌즈 가중치 학습
- **신규 렌즈 발굴**: SDX식 직교 발굴 메커니즘 — **✅ v1.6: 그룹 E Restructuring(L21-L25) 등재** (아래 Lens Evolution Roadmap). 다음 후보는 직교 공백 점검으로.
- **도메인별 렌즈 풀**: 의료, 우주, 금융 등 분야별 특화 렌즈
- **렌즈 조합 최적화**: 어떤 Stack 조합이 어떤 Layer 인사이트에 효과적인지 매핑

## Lens Evolution Roadmap

> SDX가 직교 채널을 주기적으로 확장하듯, **렌즈도 직교 변환축의 집합**으로 보고 주기적으로
> 공백을 메워 확장한다. 렌즈는 CIX 생성 엔진의 핵심이므로, 추가 전 반드시 **과거 라운드 backtest**로
> 검증한다(신규 라운드 불필요).

### 절차 (6단계)

```
LensEvolution // 직교 공백 점검 → 후보 설계 → backtest → 등재
    1. MapAxes        // 기존 렌즈의 변환축 매핑 (A 속성반전 / B 좌표이동 / C 제약 / D 합성분해 / E 구조재배치)
    2. FindGaps       // 어떤 변환축이 비어있는가 — 기존 렌즈로 도달 불가한 변형
    3. DesignCandidate// 공백을 메우는 후보 렌즈 설계 (변형 절차 + 예시 + 조건, lens_catalog 양식)
    4. Backtest       // 과거 라운드(insight+baseline+idea_pool) 고정셋으로 채점 (신규 라운드 X)
                      //   surprise   = baseline 예측과 jaccard (< 0.7 통과, < 0.5 강함)
                      //   orthogonality = 기존 렌즈 아이디어와 jaccard (< 0.5 통과 = 새 변환축)
                      //   harness: _workspace/lens_backtest/lens_backtest.py
    5. Register       // 양 지표 통과분만 lens_catalog + CIX_POLICY.lens_group_affinity 정식 등재
    6. LiveProof      // 다음 실제 라운드에서 7모델 baseline 대비 surprise로 최종 실증·튜닝
```

### Backtest 합격 기준 (production 일관)
- **Surprise** < 0.7 (PREDICTABLE_BY_BASELINE 미만, `reject_and_score`와 동일선) — baseline이 못 떠올림
- **Orthogonality** < 0.5 (기존 렌즈 아이디어와 비중복) — 진짜 새 변환축
- 둘 다 통과해야 등재. Surprise만 = 중복 렌즈, Orthogonality만 = 자명 렌즈.

### 제약
- baseline은 production 페르소나 풀(현 P1-P14)만 존재 → 그 범위 페르소나로 backtest.
- 렌즈 아이디어 생성은 AI 런타임(비결정론) → 1회 생성 후 고정하여 결정론적 채점.
- backtest는 렌즈 *변별력* 단위 테스트이고, 전체 효과는 LiveProof(6단계)에서 확정.

### 이력
- **v1.6 (2026-06-08)**: 그룹 E Restructuring(L21 Recursion · L22 SequenceReorder · L23 CounterpartyCreation · L24 BoundaryRedraw · L25 StockToFlow) 등재. CIX-20260607-001 backtest 20/20 통과(전부 강한 surprise, ortho 0.04–0.10). 산출물 `_workspace/lens_backtest/`.
