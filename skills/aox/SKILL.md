---
name: aox
description: "AOX (IdeaFirst Orchestrator eXplorer) — SDX → TCX → IDX → CIX → EVX 전체 파이프라인을 자율 실행하는 마스터 오케스트레이터. 하부 스킬을 표준 인터페이스로 호출, run_id 관리, 산출물 버전 관리, 단계간 상태 추적, 실패 복구, 동질화 자동 감지·재실행 지원. IdeaFirst의 평면 워크플로우를 자율 시스템으로 승격. Triggers: AOX, IdeaFirst 풀사이클, IdeaFirst 자율실행, 전체 파이프라인, master orchestrator, full cycle, end-to-end idea generation, 아이디어발굴 자동화"
user-invocable: true
argument-hint: "full|partial|resume|dry-run [--start-from=stage] [--run-id=...] [--config=...]"
version: "1.3.1"
author: "양정욱 (sadpig70@gmail.com)"
---

# AOX (IdeaFirst Orchestrator eXplorer) v1.3.1

> SDX는 채널을, TCX는 정보를, IDX는 인사이트를, CIX는 아이디어를 만든다.
> AOX는 이 모두가 *자율적으로* 흐르게 한다.

## 존재 이유 (Why)

외부 리뷰 핵심 지적: SDX/IDX/CIX는 잘 설계된 스킬이지만 **수동 호출만 가능**. 마스터 오케스트레이터 부재로 자율 실행 불가.

AOX는 이 갭을 메운다:
1. **하부 스킬 표준 인터페이스 호출** — SDX/TCX/IDX/CIX/평가를 contract 기반 연결
2. **상태 관리** — run_id, status.json, 단계별 산출물 버전
3. **실패 복구** — 중단된 실행 재개, 부분 산출물 활용
4. **자동 트리거** — 동질화 감지 시 SDX refresh 자동 호출
5. **로그·재현성** — 모든 단계·AI 호출 기록

## 핵심 파라미터

```yaml
PIPELINE_STAGES: 7  # 0_init, 1_sdx, 2_tcx, 3_idx, 4_cix, 5_evx, 6_wrapup
SUBSKILLS_REQUIRED: [pg, pgf, sdx, tcx, idx, cix, evx]
MAX_RETRY_PER_STAGE: 2
HOMOGENIZATION_CHECK: per_run
ARTIFACT_VERSIONING: run_id based
LOG_LEVEL: structured_json
SDX_CATALOG_INPUT: ".sdx/catalog/index.yaml"
EVX_OUTPUT_FIXED:  ".evx/latest/final_idea.md"
```

## Completion Definition

AOX is complete when the full production pipeline can run by composing official
skills only. AOX must not absorb SDX/TCX/IDX/CIX/EVX internals; it completes the
system by loading their contracts, invoking them in order, verifying outputs,
tracking state, and recording failures or handoffs.

```yaml
aox_completion_criteria:
  source_of_truth:
    - "skills/aox/SKILL.md"
    - "skills/{sdx,tcx,idx,cix,evx}/SKILL.md"
    - "skills/pg/SKILL.md"
    - "skills/pgf/SKILL.md"
    - ".idea-ledger/consumed_ideas.yaml"
  excluded_from_pipeline_contract:
    - "aox_agents.md"
  complete_when:
    - "AOX can execute stage order through skill contracts only"
    - "each required subskill is discoverable and has readable inputs/outputs"
    - "status.json records stage state and subskill round ids"
    - "consumed idea ledger is checked before winner reuse"
    - "blocked production stages produce honest handoff instead of fake completion"
  incomplete_when:
    - "AOX requires non-canonical handoff notes to know the pipeline"
    - "AOX must manually recreate subskill internals instead of invoking skills"
    - "winner selection can repeat consumed ideas"
```

## AOX_POLICY (★ v1.3 IdeaFirst — 다중 라운드 회귀 정책)

```yaml
AOX_POLICY:
  environment_capability_check:            # ★ NEW v1.3.1 — Codex 지적 반영
    run_at: "stage_0_init"                 # 0_init 단계에서 먼저 확인 후 pipeline 진입
    required_capabilities:
      cross_model_baseline_for_cix:        # CIX v1.5.1 환경 요구사항
        required_by: ["4_cix"]
        probe: "다른 family LLM API 호출 trivial test"
        on_unavailable: "block_stage_4_with_handoff"
      file_io:
        required_by: ["all_stages"]
        on_unavailable: "abort_run"
      pgf_personas_json_access:
        required_by: ["2_tcx", "3_idx", "4_cix", "5_evx"]
        on_unavailable: "abort_run"

    blocked_handling:                      # 단독 환경 (Codex standalone) 처리
      strategy: "graceful_handoff"         # abort보다 인계 우선
      stages_completable_in_standalone:    # 외부 모델 호출 없이도 완료 가능
        - "0_init"
        - "1_sdx (skip+reuse mode)"
        - "2_tcx (collect+analyze without persona-cross-model)"
        - "3_idx"
        - "4_cix (until phase 4, raw_seed_ideas.yaml까지)"
      stages_requiring_external:           # 외부 모델 의무
        - "4_cix phase 5+ (surprise_validation cross-model)"
        - "5_evx (deterministic은 가능하나, EVX v1.2 LLM-aug 시 외부 필요)"
      handoff_artifact: ".aox/{run_id}/HANDOFF.md"

  validation:                              # ★ NEW v1.3 — 지속혁신성 측정
    min_consecutive_rounds: 5              # 5회 연속 라운드까지 추적
    winner_similarity_max: 0.5             # 라운드 N과 N-1 winner cosine 상한
    measurement_window: 5                  # rolling window
    sdx_refresh_trigger_on_breach: true    # 초과 시 다음 라운드 SDX refresh 자동 발동
    persona_rotation_on_breach: false      # v1.4 후보 (현재 비활성)
    novelty_baseline_threshold: 0.7        # baseline_LLM 예측 실패율 하한
    diversity_threshold: 0.6               # 24 ideas pairwise distance 평균 하한
    surprise_pass_rate_min: 0.75           # 14 페르소나 중 ≥11 예측 실패 (비율 ≥0.75)
    rationale: |
      IdeaFirst Engine v1.3 §1.3 신규 원칙 "비용 ≪ 가치"에 따라, 시스템의 가치는
      *반복적으로* 새 것을 낳는 능력에 있다. 1회 실증으로는 우연일 수 있으므로
      5회 연속 라운드 winner 임베딩 유사도 ≤0.5일 때만 시스템이 *지속혁신성*을 가진다고 판정.
      reference: .pgf/ANALYSIS-IdeaFirst.md G2.

  kpi_collection:                          # ★ NEW v1.3 — Tech Doc §10.2와 동기화
    mandatory_per_run:
      - novelty                            # baseline_LLM prediction failure rate
      - diversity                          # 24 ideas pairwise embedding distance mean
      - sustained_innovation               # 라운드 N vs N-1 winner cosine
      - surprise_pass_rate                 # 14 personas predict-fail count / 14
    optional:
      - post_hoc_yield                     # 12개월 후 후속 추적 (외부 측정)
    cost_kpis_demoted:                     # 부산물로만 기록 (목표치 없음)
      - duration_seconds
      - autonomous_execution_rate

  homogenization:                          # 기존 동질화 측정 + v1.3 확장
    check_window_runs: 5
    thresholds:
      keyword_coverage: 0.80
      max_pair_count: 3
      avg_embedding_sim: 0.65
      winner_embedding_similarity: 0.5     # ★ NEW v1.3 — 라운드별 winner 비교
    triggered_when: "≥2 of 4 thresholds breached"
    drift_guard:                           # ★ v1.3 — SDX 직교성 선행 가드 연동
      enabled: true                        # Stage 6에서 SDX AI_orthogonality_drift_guard 호출 (저비용)
      thresholds_owned_by: "SDX_POLICY.drift_guard"   # 단일 출처 — AOX 임계 복제 금지(desync 방지)
      on_refresh: "기존 homogenization_trigger.flag 재사용 → 다음 라운드 Stage 1 /sdx refresh"
      on_audit:   ".aox/global/sdx_audit_recommended.flag 기록 — ModeAudit는 사용자 승인 게이트, 자동 audit 금지"
    yield_attribution:                     # ★ v1.3 — realized-yield 귀속 (decay 모델 입력)
      enabled: true                        # Stage 6에서 provenance walk → SDX AI_record_channel_yield
      scope_owned_by: "SDX_POLICY.yield_attribution"  # 단일 출처 — credit_scope/fallback는 SDX 소유
```

## SDX/TCX Catalog Contract (v1.1)

현재 SDX 산출물은 단일 `channel_catalog.yaml`이 아니라 구조화된 catalog tree다.
AOX는 `.aox/global/channel_catalog.yaml`을 정본으로 복사하지 않는다. 정본은 프로젝트 루트의 `.sdx/catalog`이고, AOX run은 해당 index와 shard 경로를 기록하거나 run-local snapshot을 만든다.

```yaml
sdx_catalog_contract:
  canonical_index: ".sdx/catalog/index.yaml"
  canonical_root: ".sdx/catalog"
  shard_key: "format"
  expected_total_channels: 80
  required_shards:
    - channels/news.yaml
    - channels/paper.yaml
    - channels/patent.yaml
    - channels/oss.yaml
    - channels/std.yaml
    - channels/vc.yaml
    - channels/gov.yaml
    - channels/conf.yaml
    - channels/niche.yaml
    - channels/nature.yaml

sdx_drift_guard_contract:                 # ★ v1.3 — SDX 직교성 선행 가드 (read-only)
  provider: "SDX"
  function: "AI_orthogonality_drift_guard(catalog)"   # SDX 내부 훅, CLI 모드 아님
  caller: "AOX Stage 6 wrap-up (매 라운드, SDX_POLICY.drift_guard.check_every_round)"
  side_effect: "none — 카탈로그 비변경 (표본 쌍 overlap 읽기만)"
  thresholds_owned_by: "SDX_POLICY.drift_guard"        # AOX는 임계 복제 금지 (단일 출처)
  returns: "{warn_pair_ratio, sampled, recommendation∈{no_action,refresh,audit}}"

sdx_yield_attribution_contract:           # ★ v1.3 — realized-yield 귀속 (write는 SDX 전유)
  provider: "SDX (AI_record_channel_yield)"
  caller: "AOX Stage 6 wrap-up — 라운드 종료 시"
  aox_role: "provenance READ only — EVX manifest→CIX idea.source_insight_id"
            "→IDX insight.source_tcx_items→TCX item.source_channel_id→CH-NNNN"
  sdx_role: "WRITE only — yield_log append + 기여 채널 last_yield_round/yield_count 갱신"
  boundary: ".sdx/catalog 변경은 SDX 전유 (AOX는 channel_ids 리스트만 전달)"
  scope_owned_by: "SDX_POLICY.yield_attribution"       # credit_scope/fallback 단일 출처
  upstream: "TCX/IDX/CIX/EVX 스키마 변경 불요 — 추적 필드 이미 존재"

tcx_invocation:
  command: "/tcx full --catalog=.sdx/catalog/index.yaml --output={run_dir}/2_tcx/"
```

## 운영 모드

```yaml
modes:
  full:
    desc: "Stage 0 → 5 전체 실행 (기본)"
    use_when: "정기 라운드 또는 첫 실행"
  
  partial:
    desc: "특정 단계부터 실행 (--start-from=STAGE)"
    use_when: "이전 산출물 재사용"
    example: "/aox partial --start-from=idx (TCX까지 결과 그대로 사용)"
  
  resume:
    desc: "중단된 실행 재개 (--run-id=...)"
    use_when: "세션 중단, 오류 후 재개"
    behavior: "status.json 읽어서 마지막 완료 단계 다음부터"
  
  dry-run:
    desc: "실제 실행 없이 계획만 출력"
    use_when: "리소스 추정, 단계 검증"
    output: "execution_plan.md"
```

---

## 파이프라인 6단계

### Stage 0: Init

```python
def Stage_0_Init(args) -> RunContext:
    """
    실행 컨텍스트 초기화 + ★ v1.3.1 environment capability probe.
    """
    run_id = generate_uuid() + "-" + timestamp()  # "a3f4-2026-05-11T05:00:00"
    run_dir = f".aox/{run_id}/"

    os.makedirs(run_dir + "logs/", exist_ok=True)

    # ★ v1.3.1 — Environment capability probe (Codex 지적 반영)
    # CIX v1.5.1 cross-model 의무를 충족할 수 있는 환경인지 사전 확인.
    capability = AI_probe_environment_capabilities(
        required=AOX_POLICY.environment_capability_check.required_capabilities,
    )
    # capability = {
    #   "cross_model_baseline_for_cix": "available" | "unavailable" | "degraded",
    #   "file_io": "available",
    #   "pgf_personas_json_access": "available",
    # }

    blocked_stages = AI_determine_blocked_stages(capability)
    if "4_cix_phase_5_plus" in blocked_stages:
        # 단독 환경 (Codex 등) — stage 4 중반까지만 수행하고 인계
        AI_warn(f"Stage 4 CIX surprise_validation requires cross-model baseline. "
                f"Current environment: {capability.cross_model_baseline_for_cix}. "
                f"Round will run up to raw_seed_ideas.yaml, then handoff.")
        args.handoff_mode = True
        args.last_stage_completable = "4_cix_phase_4_raw_seeds"
    
    status = {
        "run_id": run_id,
        "started_at": datetime.utcnow().isoformat(),
        "mode": args.mode,
        "stages": {
            "0_init":   "completed",
            "1_sdx":    "pending",
            "2_tcx":    "pending",
            "3_idx":    "pending",
            "4_cix":    "pending",
            "5_evx":    "pending",
            "6_wrapup": "pending",
        },
        "current_stage": "0_init",
        "errors": [],
        "homogenization_triggered_count": 0,
        # ★ v1.3.1 capability tracking
        "environment_capability": capability,
        "handoff_mode": args.get("handoff_mode", False),
        "last_stage_completable": args.get("last_stage_completable", None),
        "blocked_reasons": [],
        # ★ v1.3.1 sub-skill round_id 매핑 (AOX run_id와 분리)
        "sub_round_ids": {
            "tcx_round_id": None,
            "idx_round_id": None,
            "cix_round_id": None,       # /cix --resume-round= 에 사용 (NOT ctx.run_id)
            "evx_round_id": None,
        },
    }
    
    write_json(run_dir + "status.json", status)
    return RunContext(run_id, run_dir, status, args)
```

### Stage 1: SDX (조건부)

```python
def Stage_1_SDX(ctx: RunContext) -> SDXResult:
    """
    구조화된 SDX catalog tree 확보. 조건부 실행.
    
    조건:
    - .sdx/catalog/index.yaml 부재 → /sdx bootstrap 또는 /sdx expand로 catalog tree 생성
    - catalog tree 존재 + audit_pending → 경고 후 skip 가능
    - 동질화 트리거 발동 상태 → refresh
    """
    catalog_root = ".sdx/catalog"
    catalog_index = ".sdx/catalog/index.yaml"
    
    if not exists(catalog_index):
        ctx.log("Stage 1: structured SDX catalog absent, running /sdx bootstrap")
        run_subskill("/sdx bootstrap")
        AI_verify_sdx_catalog_tree(catalog_index, expected_total=80)
        snapshot_tree(catalog_root, ctx.run_dir + "1_sdx/catalog_snapshot/")
        ctx.status["stages"]["1_sdx"] = "completed_bootstrap"
        return SDXResult(catalog_index=catalog_index, catalog_root=catalog_root)
    
    if ctx.homogenization_signaled:
        ctx.log("Stage 1: homogenization detected, running /sdx refresh")
        run_subskill("/sdx refresh")
        AI_verify_sdx_catalog_tree(catalog_index, expected_total=80)
        snapshot_tree(catalog_root, ctx.run_dir + "1_sdx/catalog_snapshot/")
        ctx.status["stages"]["1_sdx"] = "completed_refresh"
        return SDXResult(catalog_index=catalog_index, catalog_root=catalog_root)
    
    # 기본: skip + reuse. 정본은 .sdx/catalog이고 run에는 참조/스냅샷만 기록.
    ctx.log("Stage 1: structured SDX catalog exists, skipping SDX")
    AI_verify_sdx_catalog_tree(catalog_index, expected_total=80)
    write_json(ctx.run_dir + "1_sdx/catalog_ref.json", {
        "catalog_index": catalog_index,
        "catalog_root": catalog_root,
        "shard_key": "format",
        "total_channels": 80,
    })
    ctx.status["stages"]["1_sdx"] = "skipped_reused"
    return SDXResult(catalog_index=catalog_index, catalog_root=catalog_root)
```

### Stage 2: TCX

```python
def Stage_2_TCX(ctx: RunContext, sdx_result: SDXResult) -> TCXResult:
    """
    뉴스 수집 + 산업 동향 분석.
    """
    output_dir = ctx.run_dir + "2_tcx/"
    
    cmd = f"/tcx full --catalog={sdx_result.catalog_index} --output={output_dir}"
    
    for attempt in range(MAX_RETRY_PER_STAGE + 1):
        result = run_subskill(cmd, capture_log=output_dir + "tcx.log")
        
        # 품질 게이트 6개 통과 확인
        if AOX_verify_tcx_quality_gates(output_dir):
            ctx.status["stages"]["2_tcx"] = "completed"
            return TCXResult(
                news_md=output_dir + "news.md",
                industry_trend_md=output_dir + "industry_trend.md"
            )
        
        ctx.log(f"Stage 2 attempt {attempt+1} failed quality gates, retrying")
    
    ctx.status["stages"]["2_tcx"] = "failed"
    raise StageFailure("TCX failed all retries")
```

### Stage 3: IDX

```python
def Stage_3_IDX(ctx: RunContext, tcx_result: TCXResult) -> IDXResult:
    """
    industry_trend.md → 20 깊은 인사이트 (L6/L7/L9/L10).
    """
    output_dir = ctx.run_dir + "3_idx/"
    
    cmd = f"/idx distill --input={tcx_result.industry_trend_md} --output={output_dir}"
    
    for attempt in range(MAX_RETRY_PER_STAGE + 1):
        result = run_subskill(cmd, capture_log=output_dir + "idx.log")
        
        if AOX_verify_idx_quality_gates(output_dir):
            ctx.status["stages"]["3_idx"] = "completed"
            return IDXResult(insight_layered=output_dir + "insight_layered_traced.yaml")
        
        ctx.log(f"Stage 3 attempt {attempt+1} failed, retrying")
    
    ctx.status["stages"]["3_idx"] = "failed"
    raise StageFailure("IDX failed all retries")
```

### Stage 4: CIX

```python
def Stage_4_CIX(ctx: RunContext, idx_result: IDXResult) -> CIXResult:
    """
    20 인사이트 → 24 혁신 시드 아이디어.
    ★ v1.3.1: Phase 4 (raw_seeds)까지는 환경 무관 수행. Phase 5+ (surprise_validation)는
    cross-model baseline 의무이므로 capability check 후 결정.

    ★ 핵심: CIX는 자체 round_id를 가진다 (예: "CIX-20260514-001"). AOX run_id
    (예: "a3f4-2026-05-14T05:00:00")와 별개. resume command 작성 시 반드시
    CIX round_id 사용 — AOX run_id 넘기면 CIX가 인식 못함.
    """
    output_dir = ctx.run_dir + "4_cix/"

    # ★ v1.3.1 — phase 4 (raw_seeds)까지는 항상 수행 가능
    # CIX 첫 호출이 자체 round_id 할당 → 그 ID를 추적해서 이후 모든 resume에 사용
    cmd_phase_1_to_4 = (f"/cix innovate --insights={idx_result.insight_layered} "
                       f"--output={output_dir} --stop-after=phase_4_raw_seeds")
    raw_result = run_subskill(cmd_phase_1_to_4, capture_log=output_dir + "cix.log")

    # ★ v1.3.1 — CIX가 출력한 round_id를 ctx에 명시 추적 (AOX run_id와 매핑)
    # CIX는 자기 manifest.round.id 또는 .cix/index.yaml.latest_round_id에 자기 round_id 기록
    cix_round_id = AI_read_yaml(".cix/index.yaml")["cix_output"]["latest_round_id"]
    # 예: cix_round_id = "CIX-20260514-001"
    ctx.sub_round_ids["cix_round_id"] = cix_round_id
    ctx.status["stage_timestamps"]["4_cix"]["cix_round_id"] = cix_round_id
    # status.json에 양방향 매핑 보존 — handoff resume 시 정확한 ID 사용 가능

    # ★ v1.3.1 — phase 5+ 는 cross-model baseline 필요
    cap = ctx.status["environment_capability"]["cross_model_baseline_for_cix"]
    if cap == "unavailable":
        # 단독 환경 (Codex 등) — handoff 처리
        # ★ 주의: HANDOFF.md는 CIX round dir에 작성 (AOX run dir 아님)
        # ★ resume_command는 CIX round_id 사용 (NOT ctx.run_id)
        cix_round_dir = f".cix/rounds/{cix_round_id}"
        handoff_path = f"{cix_round_dir}/HANDOFF.md"
        ctx.log(f"Stage 4: cross-model baseline unavailable. Blocking phase 5+. "
                f"Writing handoff to {handoff_path} for CIX round {cix_round_id}.")
        AI_write_handoff_md(
            path=handoff_path,
            blocker_reason="cross_model_baseline_unavailable",
            # ★ FIX: CIX round_id 사용, AOX run_id 아님
            resume_command=f"/cix innovate --resume-round={cix_round_id} "
                          f"--from-phase=5_surprise_validation",
            required_capabilities={
                "cross_model_baseline_for_cix": "available",
                "main_model_class_differs_from": ctx.status["environment_capability"]["main_model_class"],
            },
            required_models=AI_describe_baseline_options(
                main_class=ctx.status["environment_capability"]["main_model_class"]
            ),
            input_artifacts_preserved={
                "raw_seed_ideas": f"{cix_round_dir}/raw_seed_ideas.yaml",
                "lens_assignment": f"{cix_round_dir}/lens_assignment.yaml",
                "manifest": f"{cix_round_dir}/manifest.yaml",
            },
            round_chain={
                "cix": cix_round_id,
                "idx": ctx.sub_round_ids.get("idx_round_id"),
                "tcx": ctx.sub_round_ids.get("tcx_round_id"),
                "sdx_catalog": AI_read_sdx_version(),
            },
        )
        # CIX manifest.round 상태도 갱신 (in-place patch)
        AI_patch_yaml(f"{cix_round_dir}/manifest.yaml", {
            "round.status": "(blocked)",
            "round.blocker_reason": "cross_model_baseline_unavailable",
            "round.handoff_required": True,
            "round.handoff_artifact": handoff_path,
            "round.phase_completed": "phase_4_raw_seeds",
            "execution.scoring_mode": "v1_5_blocked",
        })
        # AOX status도 갱신
        ctx.status["stages"]["4_cix"] = "blocked"
        ctx.status["blocked_reasons"].append({
            "stage": "4_cix",
            "reason": "cross_model_baseline_unavailable",
            "cix_round_id": cix_round_id,           # ★ CIX round_id 명시
            "aox_run_id": ctx.run_id,               # ★ AOX run_id 매핑
            "handoff_artifact": handoff_path,
            "timestamp": AI_now(),
        })
        # ★ pipeline halt — Stage 5/6는 진행 안 함
        raise StageBlocked("4_cix",
                           reason="cross_model_baseline_unavailable",
                           cix_round_id=cix_round_id,
                           handoff_path=handoff_path)

    elif cap == "degraded":
        # 일부 페르소나만 baseline 가능 — partial 수행 (CIX round_id 사용)
        ctx.log(f"Stage 4: cross-model baseline partial. Running phase 5+ with partial validation "
                f"for CIX round {cix_round_id}.")
        cmd_phase_5 = (f"/cix innovate --resume-round={cix_round_id} "
                      f"--from-phase=5 --partial-validation")
        result = run_subskill(cmd_phase_5, capture_log=output_dir + "cix.log")
    else:
        # available — 정상 수행 (CIX round_id 사용)
        cmd_phase_5 = f"/cix innovate --resume-round={cix_round_id} --from-phase=5"
        result = run_subskill(cmd_phase_5, capture_log=output_dir + "cix.log")

    for attempt in range(MAX_RETRY_PER_STAGE + 1):
        if AOX_verify_cix_quality_gates(output_dir):
            ctx.status["stages"]["4_cix"] = "completed"
            return CIXResult(
                idea_pool=output_dir + "idea_pool.yaml",
                cix_round_id=cix_round_id,           # ★ round_id 명시 반환
            )
        ctx.log(f"Stage 4 attempt {attempt+1} failed, retrying")
        run_subskill(cmd_phase_5, capture_log=output_dir + "cix.log")

    ctx.status["stages"]["4_cix"] = "failed"
    raise StageFailure("CIX failed all retries")
```

### Round ID Disambiguation (★ v1.3.1 — Codex 지적 반영)

AOX run_id와 sub-skill round_id는 *항상 별개*다:

| 식별자 | 형식 | 위치 |
|---|---|---|
| AOX run_id | `a3f4-2026-05-14T05:00:00` | `.aox/{run_id}/` |
| SDX catalog version | `v1.3` | `.sdx/catalog/index.yaml.sdx_catalog.version` |
| TCX round_id | `TCX-20260514-001` | `.tcx/rounds/{round_id}/` |
| IDX round_id | `IDX-20260514-001` | `.idx/rounds/{round_id}/` |
| CIX round_id | `CIX-20260514-001` | `.cix/rounds/{round_id}/` |
| EVX round_id | `EVX-20260514-001` | `.evx/rounds/{round_id}/` |

AOX는 모든 sub-skill round_id를 `ctx.sub_round_ids` dict에 추적하여 resume command 생성, HANDOFF.md 작성, summary.md round_chain 인용 등 모든 후속 작업에 *정확한 ID*를 사용.

```python
# ✅ 올바름 (v1.3.1)
resume_command = f"/cix innovate --resume-round={ctx.sub_round_ids['cix_round_id']}"
handoff_path = f".cix/rounds/{ctx.sub_round_ids['cix_round_id']}/HANDOFF.md"

# ❌ 잘못됨 (v1.3 이전 버그)
resume_command = f"/cix innovate --resume-round={ctx.run_id}"  # AOX run_id
# CIX는 .cix/rounds/a3f4-.../ 라는 디렉토리가 없어서 round를 인식 못함
```

### Sub-round_id 등록 의무 (각 Stage 후)

```python
# Stage 2 TCX 후
ctx.sub_round_ids["tcx_round_id"] = AI_read_yaml(".tcx/index.yaml")["tcx_output"]["latest_round_id"]

# Stage 3 IDX 후
ctx.sub_round_ids["idx_round_id"] = AI_read_yaml(".idx/index.yaml")["idx_output"]["latest_round_id"]

# Stage 4 CIX 후 (위 함수 참조)
ctx.sub_round_ids["cix_round_id"] = AI_read_yaml(".cix/index.yaml")["cix_output"]["latest_round_id"]

# Stage 5 EVX 후
ctx.sub_round_ids["evx_round_id"] = AI_read_yaml(".evx/index.yaml")["evx_output"]["latest_round_id"]
```

### Stage 5: EVX (★ v1.2 — inline 분리 완료)

```python
def Stage_5_EVX(ctx: RunContext, cix_result: CIXResult) -> EVXResult:
    """
    IdeaFirst STEP 5-7을 EVX 스킬에 위임 (v1.2부터 표준).
    
    EVX 책임:
      STEP 5: 14 PGF persona × top 3 (evaluation_bias 기반)
      STEP 6: Cross-AI consensus → 최종 1 (vote → cog_style_breadth → mean_score)
      STEP 7: 5 Strengths / 3 Risks / 3 Expansion scenarios
    
    AOX는 EVX 호출 + 산출물 record + quality gates만 책임.
    EVX는 .cix/latest/를 직접 소비하므로 cix_result.idea_pool은 검증용으로만 사용.
    """
    output_dir = ctx.run_dir + "5_evx/"
    
    # EVX는 .cix/latest/ 고정 입력 사용. AOX는 manifest hash로 cix_result 추적만.
    cmd = f"/evx evaluate --evx-root=.evx"
    
    for attempt in range(MAX_RETRY_PER_STAGE + 1):
        result = run_subskill(cmd, capture_log=output_dir + "evx.log")
        
        # EVX_POLICY.quality_gates 모두 통과 + final winner votes ≥ 2 확인
        if AOX_verify_evx_quality_gates(".evx/latest/"):
            ctx.status["stages"]["5_evx"] = "completed"
            # AOX run dir에는 EVX latest 경로 + manifest hash만 기록 (산출물 중복 방지)
            write_json(output_dir + "evx_ref.json", {
                "evx_round_id":   AI_read_yaml(".evx/index.yaml")["evx_output"]["latest_round_id"],
                "evx_round_path": ".evx/latest/",
                "stage5_candidates": ".evx/latest/stage5_candidates.yaml",
                "stage6_final":      ".evx/latest/stage6_final.yaml",
                "final_idea_md":     ".evx/latest/final_idea.md",
                "manifest":          ".evx/latest/manifest.yaml",
            })
            return EVXResult(
                evx_round_path=".evx/latest/",
                final_idea=".evx/latest/final_idea.md",
            )
        
        ctx.log(f"Stage 5 attempt {attempt+1} failed EVX quality gates, retrying")
    
    ctx.status["stages"]["5_evx"] = "failed"
    raise StageFailure("EVX failed all retries")
```

### Stage 6: Wrap-up

```python
def Stage_6_WrapUp(ctx: RunContext, evx_result: EVXResult) -> WrapUpResult:
    """
    실행 마무리 + 동질화 감지 (다음 라운드용). v1.2: 산출물 경로를 EVX 표준으로 갱신.
    """
    # 동질화 측정 — .evx/latest/final_idea.md 기반
    homogenization = AI_measure_homogenization(
        recent_runs=AI_load_recent_run_outputs(N=5),
        current_run=ctx
    )
    
    if homogenization.triggered:
        ctx.log(f"⚠ Homogenization detected after this run: {homogenization.metrics}")
        # 다음 라운드에 SDX refresh 트리거하도록 마킹
        write_flag(".aox/global/homogenization_trigger.flag", homogenization.metrics)

    # ★ v1.3 — SDX 직교성 *선행* 가드 (저비용, 매 라운드). homogenization과 상보:
    #   homogenization = 출력 동질화(지연·시스템 신호) / drift = 채널 상관 누적(선행 신호)
    #   계약: sdx_drift_guard_contract (read-only, 임계는 SDX_POLICY.drift_guard 단일 출처)
    drift = {"recommendation": "no_action"}
    if AOX_POLICY.homogenization.drift_guard.enabled:
        drift = AI_sdx_drift_guard(catalog_index=".sdx/catalog/index.yaml")  # → SDX AI_orthogonality_drift_guard
        if drift["recommendation"] == "refresh" and not homogenization.triggered:
            ctx.log(f"⚠ Orthogonality drift (refresh): {drift}")
            # 기존 메커니즘 재사용 — 다음 라운드 Stage 1이 동일 flag로 /sdx refresh
            write_flag(".aox/global/homogenization_trigger.flag", {"source": "drift_guard", **drift})
        elif drift["recommendation"] == "audit":
            # ModeAudit는 사용자 승인 필수 → 자동 실행 금지, 권고만 surface
            ctx.log(f"⚠ Orthogonality drift (audit recommended, user-gated): {drift}")
            write_flag(".aox/global/sdx_audit_recommended.flag", drift)

    # ★ v1.3 — realized-yield 귀속 (SDX decay 모델 입력 채움). 계약: sdx_yield_attribution_contract
    #   AOX = provenance READ만 / SDX = .sdx/catalog WRITE만 (경계 분리)
    yield_attr = {"recorded": 0}
    if AOX_POLICY.homogenization.yield_attribution.enabled:
        # 기존 추적 필드만 walk — 상류 스키마 변경 없음 (정밀 실패 시 SDX_POLICY.fallback)
        contributing = AI_trace_winner_channels(
            evx_manifest=".evx/latest/manifest.yaml",        # source_chain
            idea_pool=".cix/latest/idea_pool.yaml",          # idea.source_insight_id
            idx_traced=".idx/latest/insight_layered_traced.yaml",  # insight.source_tcx_items
            tcx_latest=".tcx/latest/",                        # item.source_channel_id
            scope=SDX_POLICY.yield_attribution.credit_scope,  # 단일 출처 — AOX는 읽기만(복제 금지)
        )
        # .sdx/catalog 변경은 SDX 전유 — AOX는 channel_ids만 위임
        yield_attr = AI_sdx_record_yield(round_id=ctx.run_id, channel_ids=contributing)
        ctx.log(f"realized-yield recorded: {yield_attr}")

    # 실행 요약 — 모든 산출물을 각 스킬의 latest 고정 경로로 가리킴
    summary = {
        "run_id": ctx.run_id,
        "completed_at": datetime.utcnow().isoformat(),
        "duration_seconds": ctx.elapsed(),
        "stages_status": ctx.status["stages"],
        "outputs": {
            "sdx_catalog_index": ".sdx/catalog/index.yaml",
            "sdx_catalog_root":  ".sdx/catalog",
            "tcx_latest":        ".tcx/latest/",
            "idx_latest":        ".idx/latest/insight_layered_traced.yaml",
            "cix_latest":        ".cix/latest/idea_pool.yaml",
            "evx_latest":        ".evx/latest/",
            "final_idea":        ".evx/latest/final_idea.md",   # ★ v1.2: AOX → EVX 결과 가리킴
        },
        "round_chain": AI_read_yaml(".evx/latest/manifest.yaml")["source_chain"],
        "homogenization": homogenization,
        "drift_guard": drift,                  # ★ v1.3 — SDX 직교성 선행 가드 결과 (감사 로그)
        "yield_attribution": yield_attr,       # ★ v1.3 — realized-yield 귀속 결과 (감사 로그)
    }
    write_md(ctx.run_dir + "summary.md", summary)
    ctx.status["stages"]["6_wrapup"] = "completed"
    
    return WrapUpResult(summary)
```

---

## DESIGN: Gantree + PPR

```
AOX_Main // 마스터 오케스트레이터 (status: 설계중)
    ModeFull // 전체 파이프라인 (status: 설계중)
        Stage0_Init // 실행 컨텍스트 초기화 (status: 설계중)
            AI_generate_run_id
            AI_create_run_directory
            AI_initialize_status_json
            → ctx

        Stage1_SDX // SDX catalog tree 확보 (조건부) (status: 설계중) [@dep:Stage0_Init]
            AI_check_catalog_tree_existence // .sdx/catalog/index.yaml
            AI_check_homogenization_flag
            AI_decide_sdx_action // bootstrap | refresh | skip
            AI_invoke_subskill_sdx
            AI_verify_sdx_catalog_tree // 10 shards, 80 channels
            → sdx_result

        Stage2_TCX // 정보 수집·분석 (status: 설계중) [@dep:Stage1_SDX]
            AI_invoke_subskill_tcx_full // --catalog=.sdx/catalog/index.yaml
            AI_verify_quality_gates_6
            AI_retry_on_failure // max 2회
            → tcx_result

        Stage3_IDX // 깊은 인사이트 도출 (status: 설계중) [@dep:Stage2_TCX]
            AI_invoke_subskill_idx_distill
            AI_verify_layer_distribution // 5/5/5/5
            AI_retry_on_failure
            → idx_result

        Stage4_CIX // 혁신 아이디어 생성 (status: 설계중) [@dep:Stage3_IDX]
            AI_invoke_subskill_cix_innovate
            AI_verify_rejection_rate // 40-60%
            AI_retry_on_failure
            → cix_result

        Stage5_EVX // 평가·최종선정 (EVX 위임) (status: 설계중) [@dep:Stage4_CIX]
            AI_invoke_subskill_evx_evaluate    // /evx evaluate (.cix/latest → .evx/latest)
            AI_verify_evx_quality_gates        // g1-g5 (14 personas voted, winner ≥2 votes, 5S/3R/3X)
            AI_record_evx_round_id             // status.json + evx_ref.json
            AI_retry_on_failure                // max 2회
            → evx_result (.evx/latest/final_idea.md)

        Stage6_WrapUp // 마무리 + 동질화 감지 + 직교성 선행 가드 (status: 설계중) [@dep:Stage5_EVX]
            AI_measure_homogenization          // 출력 동질화 (지연·시스템 신호)
            AI_sdx_drift_guard                 // ★ v1.3 SDX 직교성 선행 가드 (read-only, sdx_drift_guard_contract)
            AI_trace_winner_channels           // ★ v1.3 provenance walk EVX→CIX→IDX→TCX→CH (READ only)
            AI_sdx_record_yield                // ★ v1.3 → SDX AI_record_channel_yield (WRITE는 SDX 전유)
            AI_set_next_run_trigger_if_needed  // refresh→homogenization_trigger.flag 재사용 / audit→승인게이트 flag
            AI_generate_run_summary            // homogenization + drift_guard + yield_attribution 기록
            → wrap_up_result

    ModePartial // 특정 단계부터 시작 (status: 설계중)
        AI_parse_start_from_arg
        AI_load_previous_artifacts_for_stages_before
        AI_run_stages_from_start_to_end

    ModeResume // 중단된 실행 재개 (status: 설계중)
        AI_load_run_id_from_arg
        AI_read_status_json
        AI_identify_last_completed_stage
        AI_resume_from_next_stage

    ModeDryRun // 계획만 출력 (status: 설계중)
        AI_generate_execution_plan
        AI_estimate_resources
        AI_emit_plan_md_without_execution
```

---

## PPR: 추가 핵심 함수

### Subskill 호출 인터페이스 (Contract)

```python
class SubskillContract:
    """
    AOX는 하부 스킬을 *Contract* 기반으로 호출.
    각 스킬은 표준 입출력 인터페이스를 보장.
    """
    name: str          # "sdx" | "tcx" | "idx" | "cix"
    mode: str          # 해당 스킬의 모드
    input_paths: dict  # {"catalog": "..."} 등
    output_paths: dict # 예상 산출물 경로
    timeout_seconds: int
    quality_gates: list[Callable]

CONTRACTS = {
    "sdx_bootstrap": SubskillContract(
        name="sdx", mode="bootstrap",
        input_paths={},
        output_paths={"catalog_index": ".sdx/catalog/index.yaml", "catalog_root": ".sdx/catalog"},
        timeout_seconds=600,
        quality_gates=[
            lambda out: count_channels_from_shards(out) == 80,
            lambda out: count_format_shards(out) == 10,
        ]
    ),
    
    "tcx_full": SubskillContract(
        name="tcx", mode="full",
        input_paths={"catalog_index": ".sdx/catalog/index.yaml"},
        output_paths={
            "news": "{run_dir}/2_tcx/news.md",
            "industry_trend": "{run_dir}/2_tcx/industry_trend.md",
        },
        timeout_seconds=900,
        quality_gates=[
            lambda out: 21_domains_covered(out),
            lambda out: cross_domain_synthesis_present(out),
        ]
    ),
    
    # IDX, CIX 동일 패턴
    
    "evx_evaluate": SubskillContract(   # ★ v1.2 신규
        name="evx", mode="evaluate",
        input_paths={
            "idea_pool":     ".cix/latest/idea_pool.yaml",
            "cix_manifest":  ".cix/latest/manifest.yaml",
            "pgf_personas":  "skills/pgf/discovery/personas.json",
        },
        output_paths={
            "stage5_candidates": ".evx/latest/stage5_candidates.yaml",
            "stage6_final":      ".evx/latest/stage6_final.yaml",
            "final_idea":        ".evx/latest/final_idea.md",
            "manifest":          ".evx/latest/manifest.yaml",
        },
        timeout_seconds=120,             # 결정론적 점수 계산 — 빠름
        quality_gates=[
            lambda out: g2_all_personas_voted(out),                   # g2
            lambda out: final_winner_votes_min_2(out),                # g3
            lambda out: assessment_counts_5S_3R_3X(out),              # g4
            lambda out: axis_mapping_traceable_in_manifest(out),      # g5
        ]
    ),
}

def AI_invoke_subskill(contract: SubskillContract, ctx: RunContext) -> SubskillResult:
    """표준 인터페이스로 하부 스킬 호출"""
    cmd = AI_build_command(contract, ctx)
    output = AI_execute(cmd, timeout=contract.timeout_seconds)
    
    for gate in contract.quality_gates:
        if not gate(output):
            return SubskillResult(success=False, reason=f"Gate failed: {gate.__name__}")
    
    return SubskillResult(success=True, outputs=contract.output_paths)
```

### 동질화 감지 (Stage 6)

```python
def AI_measure_homogenization(recent_runs: list[RunContext], current_run: RunContext) -> Homogenization:
    """
    최근 N=5 라운드 출력의 동질화 측정. v1.3 — winner-level similarity 추가.
    """
    all_ideas = [r.final_idea for r in recent_runs + [current_run]]

    # M1: 핵심 키워드 집중도
    top_keywords = AI_extract_top_keywords(all_ideas, k=10)
    keyword_coverage = AI_compute_keyword_coverage(top_keywords, all_ideas)

    # M2: 도메인 페어 반복
    pairs = AI_extract_domain_pairs(all_ideas)
    max_pair_count = max(Counter(pairs).values())

    # M3: 임베딩 유사도
    embeddings = [AI_embed(i.title + i.problem) for i in all_ideas]
    avg_sim = AI_avg_pairwise_cosine(embeddings)

    # M4: ★ v1.3 — winner 간 임베딩 유사도 (지속혁신성 측정)
    consensus_winners = [r.evx_consensus_winner for r in recent_runs + [current_run]]
    innovation_winners = [r.evx_innovation_winner for r in recent_runs + [current_run]]
    winner_embeds = [AI_embed(w.title + w.system_description) for w in consensus_winners]
    winner_similarity = AI_avg_pairwise_cosine(winner_embeds)
    # innovation winner도 추적 — 둘이 다르면 더 풍부한 신호
    innovation_embeds = [AI_embed(w.title + w.system_description) for w in innovation_winners]
    innovation_similarity = AI_avg_pairwise_cosine(innovation_embeds)

    P = AOX_POLICY.homogenization.thresholds  # v1.3 정책 참조
    triggered = (
        (keyword_coverage >= P.keyword_coverage) +
        (max_pair_count >= P.max_pair_count) +
        (avg_sim >= P.avg_embedding_sim) +
        (winner_similarity >= P.winner_embedding_similarity)    # ★ v1.3
    ) >= 2

    return Homogenization(
        triggered=triggered,
        metrics={
            "keyword_coverage": keyword_coverage,
            "max_pair_count": max_pair_count,
            "avg_embedding_sim": avg_sim,
            "winner_embedding_similarity": winner_similarity,          # ★ v1.3
            "innovation_winner_similarity": innovation_similarity,     # ★ v1.3
            "sustained_innovation_kpi_met": winner_similarity <= 0.5,  # ★ v1.3
        },
        recommendation="refresh" if triggered else "no_action",
    )
```

---

## 디렉토리 구조

```
.aox/
├── global/
│   ├── homogenization_trigger.flag   # 다음 라운드 트리거 신호 (동질화 OR drift refresh 권고 공용)
│   ├── sdx_audit_recommended.flag    # ★ v1.3 drift_guard audit 권고 (사용자 승인 게이트, 자동실행 X)
│   └── recent_runs.json              # 최근 N개 run 목록 (동질화 측정용)
│
└── {run_id}/                          # 예: "a3f4-2026-05-11T05:00:00"
    ├── status.json
    ├── 0_init/
    │   └── args.json
    ├── 1_sdx/
    │   ├── catalog_ref.json           # .sdx/catalog/index.yaml 참조
    │   └── catalog_snapshot/          # refresh/bootstrap 시 선택적 스냅샷
    ├── 2_tcx/
    │   ├── news.md
    │   ├── industry_trend.md
    │   └── quality_report.md
    ├── 3_idx/
    │   ├── insight_layered_traced.yaml
    │   └── context_layers.yaml
    ├── 4_cix/
    │   ├── idea_pool.yaml
    │   ├── generation_log.yaml
    │   └── rejection_log.md
    ├── 5_evx/                          # ★ v1.2: inline 5_eval → standalone evx ref
    │   └── evx_ref.json                # .evx/latest/ 가리키는 메타 (산출물 중복 X)
    ├── logs/
    │   ├── aox.log
    │   ├── sdx.log (if invoked)
    │   ├── tcx.log
    │   ├── idx.log
    │   ├── cix.log
    │   └── evx.log                     # ★ v1.2: eval.log → evx.log
    └── summary.md
```

EVX 산출물 정본은 `.evx/latest/`. AOX run dir은 ref만 보관 — round chain은 `.evx/latest/manifest.yaml`의 `source_chain` 필드에서 SDX→CIX 전체 추적.

---

## Consumed Idea Ledger Contract

AOX/SA-AOX must prevent repeated use of already implemented winners.

```yaml
consumed_idea_ledger:
  path: ".idea-ledger/consumed_ideas.yaml"
  read_before_selection: true
  exclude_match_on:
    - idea_id
    - normalized_title
    - aliases
    - semantic_family
  write_after_project_creation: true
  record_only_when: "winner becomes a concrete project, MVP, repo, or durable PGF track"
  reuse_policy: "exclude_same_or_derivative"
```

Execution rule:

```text
CandidatePool
    CheckConsumedLedger
    ExcludeConsumedIdeas
    SelectWinner
    IfWinnerImplemented -> AppendConsumedIdea
```

The ledger is not a quality certificate. It is a reuse-prevention gate.

---

## status.json 스키마

```yaml
status_schema:
  run_id: "string"
  started_at: "ISO 8601"
  completed_at: "ISO 8601 | null"
  mode: "full | partial | resume | dry-run"
  args: {object}
  
  current_stage: "0_init | 1_sdx | ... | 6_wrapup"
  
  stages:
    "0_init":   "pending | in_progress | completed | failed | skipped"
    "1_sdx":    ...
    "2_tcx":    ...
    "3_idx":    ...
    "4_cix":    ...
    "5_evx":    ...    # ★ v1.2: 5_eval → 5_evx
    "6_wrapup": ...
  
  stage_timestamps:
    "1_sdx": {started: ..., completed: ...}
    ...
  
  errors:
    - stage: "..."
      attempt: 1
      reason: "..."
      timestamp: "..."
  
  homogenization_triggered_count: 0
  
  outputs:                            # ★ v1.2: 각 스킬의 latest/ 고정 경로 사용
    sdx_catalog_index: ".sdx/catalog/index.yaml"
    sdx_catalog_root:  ".sdx/catalog"
    tcx_latest:        ".tcx/latest/"
    idx_latest:        ".idx/latest/insight_layered_traced.yaml"
    cix_latest:        ".cix/latest/idea_pool.yaml"
    evx_latest:        ".evx/latest/"
    final_idea:        ".evx/latest/final_idea.md"
```

---

## 사용법

```bash
# 기본: 전체 파이프라인 실행
/aox full

# 특정 단계부터 (이전 산출물 재사용)
/aox partial --start-from=idx --previous-run=a3f4-2026-05-10T18:00:00

# 중단된 실행 재개
/aox resume --run-id=a3f4-2026-05-11T05:00:00

# 계획만 보기 (실제 실행 없음)
/aox dry-run

# 설정 파일 사용
/aox full --config=aox_config.yaml
```

## Local Codex Runner (2026-06-02)

현재 `D:/IdeaFirst` 로컬 실행기는 AOX 계약을 실제 파일 산출물로 남긴다. 하위 스킬 내부를 흡수하지 않고 기존 latest 산출물과 로컬 emit 스크립트를 조합한다.

```powershell
# dry-run 계획만 생성
python scripts/explore/aox_full.py --project-root . --mode dry-run

# 전체 AOX run 생성. missing latest가 있으면 하위 emit 스크립트를 호출하고,
# 이미 존재하면 .{skill}/latest를 재사용한다.
python scripts/explore/aox_full.py --project-root . --mode full

# 이전 TCX/IDX/CIX를 재사용하고 EVX만 consumed ledger 기준으로 재평가
python scripts/explore/aox_full.py --project-root . --mode full --start-from evx

# CIX부터 새 idea_pool을 만들고 EVX를 ledger-aware로 재평가
python scripts/explore/aox_full.py --project-root . --mode full --start-from cix

# 구체 프로젝트가 생성된 경우에만 consumed ledger에 기록
python scripts/explore/aox_full.py --project-root . --mode wrapup --record-consumed --project-name RoboTrace --project-path robotrace --repo-url https://github.com/sadpig70/robotrace --aliases RoboTrace,RobotRace --semantic-family robot-incident-evidence-compatibility-mesh

# 최신 AOX run 검증
python scripts/explore/aox_verify_latest.py --project-root .
```

Ledger policy:

- EVX reads `.idea-ledger/consumed_ideas.yaml` before winner selection and excludes matching candidates.
- Matching keys: `idea_id`, `normalized_title`, `aliases`, `semantic_family`.
- AOX local runner checks ledger every run, but appends only with `--record-consumed` after a winner becomes a concrete project, MVP, repo, or durable PGF track.
- Recommended rerun entry: `--start-from evx` when only consumed exclusion changed; `--start-from cix` when a fresh idea pool is needed.

Local runner outputs:

```text
.aox/
├── index.yaml
├── latest/
│   ├── status.json
│   ├── summary.md
│   └── 5_evx/evx_ref.json
└── AOX-{YYYYMMDD}-{NNN}/
    ├── status.json
    ├── summary.md
    ├── 1_sdx/catalog_ref.json
    └── 5_evx/evx_ref.json

.idea-ledger/
└── consumed_ideas.yaml
```

## aox_config.yaml (옵션)

```yaml
# AOX 실행 설정
ai_model_routing:
  AI_1: "claude-opus-4-7"
  AI_2: "gpt-5"
  AI_3: "gemini-3-ultra"
  AI_4: "grok-5"
  AI_5: "kimi-k3"
  AI_6: "deepseek-v4"
  AI_7: "qwen-3-max"
  AI_8: "mistral-large-3"

stages_to_run: ["1_sdx", "2_tcx", "3_idx", "4_cix", "5_evx", "6_wrapup"]   # ★ v1.2

quality_gate_strictness: "high"  # strict | high | medium | low

max_retry_per_stage: 2

homogenization:
  check_window_runs: 5
  thresholds:
    keyword_coverage: 0.80
    max_pair_count: 3
    avg_embedding_sim: 0.65

logging:
  level: "info"
  format: "structured_json"
```

---

## 통합 파이프라인 시각화

```
[AOX] /aox full
   │
   ├─ Stage 0: Init
   │    └─ run_id = a3f4-...
   │
   ├─ Stage 1: SDX (conditional)
   │    ├─ .sdx/catalog/index.yaml absent? → /sdx bootstrap
   │    ├─ homogenization? → /sdx refresh
   │    └─ otherwise: skip + reuse
   │       Output: .sdx/catalog/index.yaml + channels/*.yaml
   │
   ├─ Stage 2: TCX
   │    └─ /tcx full --catalog=.sdx/catalog/index.yaml
   │       Output: news.md + industry_trend.md
   │
   ├─ Stage 3: IDX
   │    └─ /idx distill --input=industry_trend.md
   │       Output: insight_layered_traced.yaml (20 깊은 인사이트)
   │
   ├─ Stage 4: CIX
   │    └─ /cix innovate --insights=...
   │       Output: idea_pool.yaml (24 혁신 시드)
   │
   ├─ Stage 5: EVX (v1.2 — standalone skill)         ⭐
   │    └─ /evx evaluate
   │       ├─ STEP 5: 14 PGF persona × top 3 (evaluation_bias)
   │       ├─ STEP 6: Cross-AI consensus → 최종 1 (vote→breadth→mean)
   │       └─ STEP 7: 5 Strengths / 3 Risks / 3 Expansion
   │          Output: .evx/latest/{stage5_candidates, stage6_final, final_idea, manifest}
   │
   └─ Stage 6: Wrap-up
        ├─ 동질화 측정 (다음 라운드 트리거)
        └─ summary.md  (각 스킬 latest/ 경로 참조 + .evx manifest source_chain)
```

---

## v2.0 분리 권장 — ★ EVX는 v1.2(2026-05-13)에 분리 완료

```yaml
EVX_v1_0:
  status:   "released 2026-05-13"
  source:   "skills/evx/SKILL.md v1.0"
  runtime:  ".evx/{index.yaml, latest/, rounds/, archive/}"
  first_round: "EVX-20260513-001 (winner: IDEA-W2-030, 4 votes)"
  axes:
    pgf_4: [novelty, feasibility, impact, integrity]   # ← cix 6축에서 결정론적 매핑
  ax_mapping: "EVX_POLICY.axis_mapping (single source of truth)"
  quality_gates: 5      # g1-g5
  next_steps:
    v1_1: "LLM-augmented 5S/3R/3X (현재는 main thread heuristic)"
    v1_2: "기술 6축 + 상업 5축 + 리스크 3축 (IdeaFirst doc v2.0 EVX 정의 흡수)"
    v1_3: "voter calibration (페르소나 historical accuracy 추적)"
```

AOX Stage 5는 이제 `/evx evaluate` 단일 호출. Stage 5 inline 코드는 모두 제거됨.

---

## 신규성 검증

기존 워크플로우 도구(LangChain agents, DSPy 등)는 LLM call 체이닝에 집중. AOX는 다음 차별점:

1. **하부 스킬의 자율성 보존** — 각 스킬은 독립 실행 가능. AOX는 contract로만 연결.
2. **품질 게이트 단계별 명시** — 단순 chain이 아닌 단계별 검증
3. **동질화 자기 감지** — 자기 출력을 모니터링해서 입력 자동 갱신
4. **PG/PGF native** — Gantree+PPR로 표현 가능한 첫 마스터 오케스트레이터

## 한계

- 모델 라우팅은 config 기반 (자동 최적 라우팅 X)
- 비용 추정 미구현 (dry-run의 한계)
- 시각적 대시보드 X (status.json 텍스트만)
- EVX v1.0은 결정론적 heuristic 평가 — LLM-augmented 5S/3R/3X는 EVX v1.1 이후

## 의존 스킬

```yaml
required_subskills:
  - pg          # PPR/Gantree notation
  - pgf         # ★ discovery/personas.json (14 P1-P14, evaluation_bias) — TCX/IDX/CIX/EVX 공통
  - sdx         # structured catalog tree
  - tcx         # collection & analysis
  - idx         # insight distillation
  - cix         # creative innovation
  - evx         # ★ v1.2 신규 (Stage 5 inline → standalone)

optional:
  - (없음)
```

## 버전

AOX v1.3.1 — 2026-05-14

### v1.3.1 변경 (environment capability handling + round_id disambiguation — Codex 지적 반영)

- `AOX_POLICY.environment_capability_check` 블록 신설 — pipeline 진입 전 cross-model 호출 가능성 사전 검사
- **Stage 0 Init**: `AI_probe_environment_capabilities()` 추가. unavailable 시 handoff_mode 활성화
- **Stage 4 CIX**: phase 1-4 (raw_seeds)는 환경 무관 수행, phase 5+ (surprise_validation)는 cross-model 의무이므로 capability gate. unavailable 시 `StageBlocked` raise + `HANDOFF.md` 작성
- **★ Round ID Disambiguation** (Codex 2차 지적 반영): AOX `run_id`와 sub-skill `round_id`는 항상 별개. resume command 작성 시 *반드시 CIX/IDX/TCX/EVX round_id 사용*. status.sub_round_ids 매핑 추적
  - 잘못된 예 (v1.3 이전 버그): `/cix innovate --resume-round={ctx.run_id}` ← AOX run_id 넘김
  - 올바른 예 (v1.3.1): `/cix innovate --resume-round={ctx.sub_round_ids['cix_round_id']}`
- **단독 환경(Codex 등)**: 라운드를 fail이 아닌 *blocked* 처리. raw_seed_ideas.yaml까지는 보존. 외부 baseline 갖춘 환경에서 `--resume-round={cix_round_id} --from-phase=5`로 재개 가능
- **status.json 신규 필드**: `environment_capability`, `handoff_mode`, `last_stage_completable`, `blocked_reasons`, `sub_round_ids`
- **HANDOFF.md 작성 위치**: `.cix/rounds/{cix_round_id}/HANDOFF.md` (AOX run_dir 아님). CIX manifest.round.handoff_artifact에도 동일 path 기록
- **CIX manifest in-place patch**: blocked 시 `round.status='(blocked)'` + `round.blocker_reason` + `round.handoff_required` + `round.phase_completed='phase_4_raw_seeds'`
- 호환: v1.3 정본 정책 불변. capability 처리 + round_id 명시 추적만 추가.

### v1.3 변경 (IdeaFirst — 다중 라운드 회귀 정책)

- **AOX_POLICY 블록 신설**: `validation` (min_consecutive_rounds=5, winner_similarity_max=0.5) + `kpi_collection` (4 mandatory KPIs + 1 optional) + `homogenization` (winner_embedding_similarity 추가)
- **AI_measure_homogenization 갱신**: M1-M3에 M4 winner-level similarity 추가. innovation_winner도 별도 추적 (consensus와 다를 수 있으므로).
- **KPI 재정의 반영**: Tech Doc §10.2와 동기화 — 비용 KPI(duration, autonomous_execution_rate)를 *제약*에서 *부산물*로 강등.
- **sdx_refresh_trigger_on_breach**: winner_similarity > 0.5 5회 연속이면 다음 라운드 SDX refresh 자동 발동 (지속혁신성 깨졌으므로 입력 갱신).
- **EVX v1.1 dual winner 수용**: ctx.evx_consensus_winner / ctx.evx_innovation_winner 양면 참조.
- 근거: IdeaFirst Engine v1.3 §1.3 "비용 ≪ 가치" + `.pgf/ANALYSIS-IdeaFirst.md` G2.

### v1.2 변경 (Stage 5 inline → EVX standalone)

- **EVX 스킬 정식 호출**: Stage 5 inline 60줄 → `/evx evaluate` 단일 호출 + quality gates 검증.
- **PIPELINE_STAGES 6 → 7**: stages dict에 `5_evx` + `6_wrapup` 명시 (기존 `6_wrapup`은 코드에는 있으나 status dict에 누락됨 — v1.2에서 명시).
- **SUBSKILLS_REQUIRED에 evx 추가**, optional 영역 비움.
- **CONTRACTS에 `evx_evaluate` SubskillContract 추가** (input/output paths, 5 quality gates).
- **AOX run dir `5_eval/` → `5_evx/`**, `evx_ref.json` 한 파일만 남김 (산출물 정본은 `.evx/latest/`).
- **Stage 6 summary outputs 키 갱신**: `news/industry_trend/insights/ideas/final_idea` (run-dir 경로) → `.{skill}/latest/` 고정 경로 + `round_chain` 필드 (.evx manifest source_chain 그대로 인용).
- **EVX_OUTPUT_FIXED 상수**: `.evx/latest/final_idea.md` AOX summary 고정 진입점.

### v1.1 변경

- SDX v1.3 구조화 catalog tree 반영: `.sdx/catalog/index.yaml` + `channels/*.yaml`
- `.aox/global/channel_catalog.yaml` 정본 전제 제거
- TCX 호출을 `/tcx full --catalog=.sdx/catalog/index.yaml`로 고정
- status/summary output key를 `channel_catalog`에서 `sdx_catalog_index`/`sdx_catalog_root`로 갱신
