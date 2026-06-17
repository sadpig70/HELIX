---
name: sdx
description: "SDX (Source Discovery eXplorer) — 정보 채널 발굴·평가·카탈로그화 메타 스킬. IdeaFirst/IdeaFirst-MC와 같은 합성 엔진의 입력 편향(영미권/최신뉴스 편중)을 깨기 위해 직교 정보 채널 80개를 발굴·유지한다. 5가지 발굴 전략(Reference Backtrack, Cross-Lingual Mirror, Failure Archive, Adjacent Borrow, Weak Signal)과 8축 메트릭 평가, 4-Axis 다양성 매트릭스를 사용. 동질화 감지 시 트리거 기반 자동 갱신. Triggers: SDX, 채널발굴, 정보소스발굴, source discovery, 편향제거, IdeaFirst채널, 직교채널, channel catalog, heterogeneous source"
user-invocable: true
argument-hint: "bootstrap|refresh|expand|audit [--cells=cell_id] [--out=dir] [--force]"
version: "1.5"
author: "양정욱 (sadpig70@gmail.com)"
---

# SDX (Source Discovery eXplorer) v1.5

> IdeaFirst는 합성 엔진, SDX는 그 위의 입력 채널 발굴 엔진.
> 합성의 다양성은 입력의 다양성을 초과할 수 없다.

## 존재 이유 (Why)

IdeaFirst 8-AI 실증 결과 24개 시스템 제안이 **3개 클러스터로 붕괴** (PQC×바이오, LEO×전력망, 휴머노이드×규제). 원인은 합성 엔진이 아닌 **입력 채널의 동질성** (모두 영미권 tech 미디어, 최신 24h, 같은 화제). SDX는 이 입력 단계에서 **직교 채널 80개**를 발굴·유지하여 IdeaFirst-MC의 합성 다양성을 구조적으로 보장한다.

## 핵심 파라미터

```yaml
TARGET_CHANNELS: 80              # 직교 기저만 유지
VALIDATION_DEPTH: url_alive_only # HTTP 200만 확인 (가벼움)
TRIGGER_MODE: homogenization_detected  # 동질화 감지 시 자동 발동
EXPLORATION_STRATEGIES: 5
EVALUATION_AXES: 8
DIVERSITY_MATRIX: 4-Axis
```

## DESIGN_DECISIONS (사용자 명시 결정 기록)

> 이 섹션은 v1.1에서 추가됨. 외부 리뷰가 컨텍스트 누락으로 잘못된 비판을 하지 않도록 결정 근거를 명시.

```yaml
validation_depth:
  selected: "url_alive_only"
  alternatives_considered:
    - "(a) URL alive only — SELECTED"
    - "(b) Sample content extraction + signal density 측정"
    - "(c) Insight generation test (실제 인사이트 1개 도출 검증)"
  rationale: |
    정밀(80개) + 트리거 기반 갱신과 결합 시 무거운 검증은 비용 대비 효익 낮음.
    카탈로그 사용 단계(IdeaFirst-MC)에서 채널 품질이 자연 측정되므로 사후 갱신 가능.
  user_decision_date: "2026-05-11"

catalog_size:
  selected: 80
  alternatives: ["(b) 300 mid", "(c) 1000+ large"]
  rationale: "직교 기저만 유지, 정밀도 우선"

update_trigger:
  selected: "homogenization_detected"
  alternatives: ["(a) quarterly", "(b) semi-annual"]
  rationale: "출력 동질화가 곧 입력 갱신 필요 신호"

channel_maintenance:                 # v1.3 — 외부 리뷰(채널 노화/pruning/동적 80) 공식 대응
  catalog_size_dynamic:
    decision: "80 고정 유지. 상향은 expand로만 허용, '비용절감용 하향 축소'는 non-goal."
    rationale: |
      80은 설계된 *직교 기저 차원*이지 비용 변수가 아니다. 지배 원칙 cost≪가치상
      '비싸니 줄이자'는 non-goal. 유지보수 투자 대상은 80개의 *신선도·직교 품질*.
  channel_decay_rate:
    decision: "명시화 — SDX_POLICY.channel_decay.half_life_rounds (기본 8라운드 반감)"
    rationale: "기존엔 homogenization(지연·시스템 신호)만으로 간접 포착 → per-channel 정량 *선행* 모델 추가."
  correlation_pruning:
    decision: "이미 존재(independence×2.0 / max_overlap_cut / ModeAudit 중복제거) + v1.3 DriftGuard 선행 가드 추가"
  user_decision_date: "2026-05-18"
```

## ACCESS_POLICY

채널 카탈로그에서 유료·제한 소스 처리 정책:

```yaml
access_tiers:
  tier_1_free:
    desc: "완전 무료, API 제한 적음"
    priority: "highest"
    examples: ["arXiv", "IETF datatracker", "Wikipedia"]

  tier_2_signup:
    desc: "무료 가입 필요"
    priority: "high"
    examples: ["HuggingFace", "Crunchbase free tier"]

  tier_3_paid:
    desc: "유료 구독"
    priority: "medium"
    handling: "URL alive check + 가입 안내만, 콘텐츠 직접 수집 X"
    examples: ["WSJ", "FT", "Crunchbase Pro"]

  tier_4_institutional:
    desc: "기관 계약 필요 (학술)"
    priority: "low (but high signal)"
    handling: "메타데이터만 수집 (제목·초록), 본문은 사용자가 기관 접근으로 처리"
    examples: ["CNKI", "Web of Science", "Scopus"]

catalog_balance_rule:
  tier_1_2_minimum: "≥ 50% of catalog (무료 접근 보장)"
  tier_3_4_maximum: "≤ 50% (고가치 신호이나 운영 부담)"
```

## SDX_POLICY (v1.2 신규 — 운영 임계값 단일 출처)

> 모든 동작 임계값을 한 곳에 모아 운영자가 코드 수정 없이 조정 가능하게 한다. PPR은 이 값들을 참조한다.

```yaml
homogenization_thresholds:
  keyword_coverage_max: 0.80        # M1: top-10 키워드가 출력의 80% 이상 점유 시 트리거
  domain_pair_repeat_max: 3         # M2: 같은 도메인 쌍이 5라운드 중 3회 이상 반복 시 트리거
  embedding_similarity_max: 0.65    # M3: 평균 임베딩 cosine 유사도 0.65 이상 시 트리거
  trigger_metric_count_min: 2       # 3개 메트릭 중 2개 이상 임계 초과 시 발동
  recent_rounds_window: 5           # 평가 윈도우 (라운드 수)

selection:
  max_overlap_cut: 0.5              # 그리디 직교 선택 시 기존 선택과 overlap 컷오프
  cell_coverage_floor: 0.6          # 4-Axis 셀 60% 미만 시 빈 셀 강제 보충
  diversity_improvement_target: 0.15 # refresh 모드 종료 조건 (개선폭 ≥ 15%)
  refresh_max_iterations: 3         # refresh Convergence Loop 최대 반복

bootstrap:
  candidate_target: 200             # 후보 풀 목표 크기
  validated_target: 120             # URL alive 통과 후 기대 크기
  basis_target: 80                  # 최종 직교 기저

http:
  url_check_timeout_sec: 10
  acceptable_status: [200, 301, 302]

audit:
  redundancy_similarity_threshold: 0.7  # ModeAudit에서 중복 채널로 간주

channel_decay:                       # v1.3 신규 — per-channel 노화/신선도 모델
  half_life_rounds: 8                # 미산출(no realized yield) 지속 시 freshness 반감 라운드 수
  stale_validated_days: 120         # validated_at 경과일 임계 초과 시 freshness ×0.7 (재검증 권고)
  freshness_floor: 4.0              # freshness < floor → weak 후보 (0-10 스케일)
  yield_window_rounds: 10           # realized-yield 집계 윈도우

weak_channel:                        # v1.3 신규 — AI_identify_weak_channels 정본 판정 기준
  total_score_floor: 6.0            # 가중 점수 하한
  protect_required_coverage: true   # required_coverage(geo/format/temporal/scale) 깨는 채널은 weak여도 제거 금지
  # composite: freshness<channel_decay.freshness_floor OR total_score<floor
  #            OR drift>selection.max_overlap_cut OR url_alive=false

drift_guard:                         # v1.3 신규 — 라운드별 경량 직교성 *선행* 신호
  check_every_round: true           # AOX Stage 6 wrap-up이 매 라운드 호출 (저비용)
  sample_pairs: 200                 # 전수 N×N(audit) 대신 표본 쌍 — cost≪가치: 선행 신호용 경량
  pair_overlap_warn: 0.5            # 표본 쌍 overlap 경고선 (= selection.max_overlap_cut와 정합)
  warn_pair_ratio_refresh: 0.10     # 경고 초과 쌍 비율 ≥10% → refresh 권고
  warn_pair_ratio_audit: 0.20       #                        ≥20% → full audit 권고

yield_attribution:                   # v1.3 신규 — realized-yield 귀속·기록 (decay 모델 입력 채움)
  yield_log_path: ".sdx/catalog/yield_log.jsonl"  # SDX 소유 append-only, 라운드당 1 레코드
  credit_scope: "evx_topk"          # winner | evx_topk | cix_topk — 기여 채널 인정 범위
                                    #   evx_topk = winner + 페르소나 top-3 finalists (sparse/diffuse 절충)
  count_per_round_max_once: true    # 한 라운드에 같은 채널은 yield_count +1 (아이디어 수 무관)
  fallback: "round_level_domain_channels"  # 정밀 trace 결손 시 winning idea 도메인의 TCX matched_channels
  # 정밀 경로: EVX winner → CIX idea.source_insight_id → IDX insight.source_tcx_items
  #            → TCX item.source_channel_id → SDX CH-NNNN  (전부 기존 필드, 상류 변경 불요)
```

## 4-Axis Diversity Matrix (요약 — 정본: `schemas/channel_entry.yaml#axis_system`)

모든 채널은 `(Temporal, Geographic, Format, Scale)` 4-tuple 셀 좌표를 가진다. 카탈로그는 가능한 한 셀을 고르게 커버한다.

| Axis | Cells | 정본 |
|---|---|---|
| **Temporal** | T-0, T-1Y, T-5Y, T-50Y, T-100Y+ | `schemas/channel_entry.yaml` |
| **Geographic** | US_EU, CN, RU_EE, IN_SEA, JP_KR, LATAM, AF, MENA | 동일 |
| **Format** | news, paper, patent, oss, std, vc, gov, conf, niche, nature | 동일 |
| **Scale** | macro, meso, micro | 동일 |

가능 셀 총수: 5 × 8 × 10 × 3 = 1,200. 카탈로그 80개로 최소 6.7% 커버.

## 5가지 발굴 전략

| ID | 이름 | 핵심 메커니즘 | 정본 프롬프트 |
|----|------|--------------|-------------|
| S1 | **Reference Backtrack** | 좋은 논문/기사의 출처 → 그 출처의 출처 → 도달지가 후보 | `strategies/01_reference_backtrack.md` |
| S2 | **Cross-Lingual Mirror** | 동일 주제를 7개 비영어권 언어로 검색 → 1차 자료 발굴 | `strategies/02_cross_lingual_mirror.md` |
| S3 | **Failure & Death Archive** | "killed by", "deprecated", "abandoned", "withdrawn" | `strategies/03_failure_archive.md` |
| S4 | **Adjacent Domain Borrow** | "X 분야 사람들은 어디서 정보 얻나?" 인접 분야의 정보 인프라 차용 | `strategies/04_adjacent_borrow.md` |
| S5 | **Weak Signal Hunt** | niche newsletter, mailing list, long-open issues, 비공개 그룹 | `strategies/05_weak_signal_hunt.md` |

> v1.2: 각 전략의 자연어 프롬프트가 **정본(canonical)**. SKILL.md PPR 함수는 thin wrapper로 그것을 참조한다.

## 8축 평가 메트릭 (요약 — 정본: `schemas/channel_entry.yaml#metric_guide`)

| Axis | 의미 | 가중치 |
|---|---|---|
| `independence` | 기존 카탈로그 채널과의 직교성 | **2.0** (핵심) |
| `signal_density` | 잡음 대비 정보율 | 1.0 |
| `persistence` | 지속 갱신 vs 일회성 | 1.0 |
| `accessibility` | 공개API/무료/유료/기관계약 | 1.0 |
| `geo_diversity` | 영미권 외 정도 | 1.0 |
| `temporal_depth` | 과거 도달 깊이 | 1.0 |
| `format_unique` | 다른 채널과 포맷 차이 | 1.0 |
| `trust_level` | 1차 자료성 | 1.0 |

각 0-10 점수. 측정 기준 상세는 `schemas/channel_entry.yaml#metric_guide` 참조.

```
total_score = (independence × 2.0 + Σ(other_7_axes)) / 9.0
분모 9.0 = 1×2.0 + 7×1.0 / 최댓값 10.0 / 최솟값 0.0
```

## 운영 모드 (4개)

| Mode | Trigger | Action |
|------|---------|--------|
| `bootstrap` | 카탈로그 부재 시 최초 1회 | 5전략 병렬 → 200 후보 → 80 직교 기저 선정 |
| `refresh` | 동질화 감지 자동 발동 | 약한 채널 N개 교체, 카탈로그 부분 갱신 |
| `expand` | 사용자가 특정 셀 지정 | 4-Axis 매트릭스의 빈 셀 집중 발굴 |
| `audit` | 분기/임의 시점 | 80×80 직교성 재계산, 중복 채널 제거 |

> v1.3: 위 4개는 CLI 모드. 추가로 **내부 훅 `DriftGuard`** (라운드별 경량 직교성
> 선행 신호 — AOX Stage 6 wrap-up이 호출, refresh/audit로 에스컬레이트)가 있다.
> CLI 모드가 아니며 `argument-hint`에 노출되지 않는다. homogenization(지연·시스템
> 신호)과 상보적인 per-pair *선행* 신호로, audit(분기)·refresh(동질화)만으로
> 라운드 사이 잔존하던 상관 누적을 조기 차단한다.

---

## 출력 경로 (`--out`) — v1.4

모든 모드는 `--out=<dir>` 인자로 출력 루트를 지정할 수 있다. 미지정 시 기본은 `.sdx/catalog/`.

```bash
/sdx bootstrap                          # 기본 → .sdx/catalog/
/sdx bootstrap --out=grok               # bare token → .sdx/grok/
/sdx bootstrap --out=.sdx/shards/agent-1/   # 경로 → 그대로 사용
```

**`--out` 값 정규화 규칙 (정본, 결정론적):**

`--out` 값을 다음 순서로 해석해 `{OUT}`을 확정한다. (미지정 시 `{OUT}` = `.sdx/catalog/`)

| 입력 형태 | 판정 기준 | 결과 `{OUT}` | 예 |
|---|---|---|---|
| **bare token** | `/`·`\` 구분자 없음 | `.sdx/<token>/` | `grok` → `.sdx/grok/` |
| **상대 경로** | 구분자 포함, 절대경로 아님 | 값 그대로 (프로젝트 루트 기준) | `.sdx/shards/agent-1/` → `.sdx/shards/agent-1/` |
| **절대 경로** | `/`로 시작 또는 `X:\` 드라이브 | 값 그대로 | `D:/cat/` → `D:/cat/` |

- `{OUT}`은 **항상 카탈로그 *루트***다 — `index.yaml`은 `{OUT}/index.yaml`. **`catalog/` 하위폴더를 자동 추가하지 않는다.** (∴ `--out=grok` → `.sdx/grok/index.yaml`. `.sdx/grok/catalog/`가 **아님**)
- bare token은 `.sdx/` **네임스페이스 하위**로 귀속된다 — `.sdx_grok/`(형제 디렉토리)도 `./grok/`(CWD 직속)도 **아니다**. 동시 실행 격리가 `.sdx/` 한곳에 모이도록 하기 위함.
- DESIGN Gantree / PPR / 출력 스키마의 **모든 `.sdx/catalog/` 경로는 확정된 `{OUT}` 기준으로 해석**한다 (`index.yaml`, `channels/`, `basis/`, `reports/`, `yield_log.jsonl`, `SDX_POLICY.yield_attribution.yield_log_path` 포함).
- **중간 산출물(Phase1~4)** — `seed_channels.yaml`, `all_candidates.yaml`, `validated.yaml`, `catalog_v1_basis.yaml` — 은 `{OUT}/.work/` 아래에 둔다. (고정 공유 경로 `.sdx/work/` 사용 금지)

**동시 실행 안전성 (concurrency):**

- `--out`은 **최종 카탈로그 + 중간 work + yield_log 전체**를 한 루트로 격리한다. 따라서 여러 에이전트가 서로 다른 `--out`을 주면 공유 mutable 경로가 없어 race condition이 발생하지 않는다.
- ⚠️ 같은 `--out`을 두 에이전트가 동시 지정하면 충돌한다 — **에이전트당 고유 `--out` 필수**.
- 교차/통합(merge)은 본 버전 범위 밖이다. 각 에이전트가 독립 `--out`으로 카탈로그를 "최대한" 산출한 뒤, 별도 통합 단계에서 전역 직교 재선택(Phase4 재실행)으로 합친다. ← 추후 설계.

---

## DESIGN: Gantree

> 모든 흐름 제어(if/while/for/Convergence Loop)는 **PPR `def` 블록**에 위치. Gantree는 노드 구조만 표현.

```
SDX_Main // SDX 메인 진입점 (in-progress) @v:1.5
    ModeBootstrap // 최초 카탈로그 80개 구축 (designing)
        Phase1_SeedAudit // 기존 알려진 채널 등재 (designing)
            AI_load_known_channels // 영미권 주요 소스 ~80개 베이스
            AI_identify_blind_spots // 명시적 결손 영역 식별
            # output: seed_channels.yaml

        Phase2_Exploration // 5전략 병렬 발굴 (designing) @dep:Phase1_SeedAudit
            [parallel]
            AI_explore_reference_backtrack
            AI_explore_cross_lingual
            AI_explore_failure_archive
            AI_explore_adjacent_borrow
            AI_explore_weak_signal
            [/parallel]
            AI_merge_candidates // 중복 제거
            # output: all_candidates.yaml  (~200개)

        Phase3_LightValidation // URL 살아있음만 확인 (designing) @dep:Phase2_Exploration
            AI_check_url_alive // HTTP 200/301/302만 통과
            AI_filter_dead
            # output: validated.yaml  (~120개)

        Phase4_OrthogonalityCompute // 직교성 계산 (designing) @dep:Phase3_LightValidation
            AI_score_8axis_metrics // 각 채널 8축 점수
            AI_compute_pairwise_overlap // 채널쌍 신호 중복도
            AI_select_orthogonal_basis_80 // 그리디 직교 선택
            # output: catalog_v1_basis.yaml  (80개)

        Phase5_CatalogEmit // 최종 출력 — sharded catalog (designing) @dep:Phase4_OrthogonalityCompute
            AI_format_yaml_entries           // schemas/channel_entry.yaml 준수
            AI_shard_by_format               // 채널을 format별 yaml로 분할
            AI_emit_index                    // index.yaml: Catalog Index Contract v1 (acceptance/shards.path/basis/reports/policy_version 필수)
            AI_emit_4axis_coverage_report    // 셀 커버리지 시각화
            AI_emit_orthogonality_matrix     // 80×80 (or N×N) pairwise overlap
            AI_emit_selection_log            // 채택/거절 로그
            # output_root: .sdx/catalog/
            # output: index.yaml                                    (entry point)
            # output: channels/{format}.yaml × 10                   (sharded by format)
            # output: basis/orthogonality_matrix_v{N}.json
            # output: basis/overlap_policy.yaml
            # output: basis/selection_log_v{N}.yaml
            # output: basis/rejected_candidates.yaml                (consolidated all versions)
            # output: reports/coverage_v{N}.md
            # output: reports/expand_v{N}.md                        (per expand cycle)

    ModeRefresh // 동질화 감지 시 부분 갱신 (designing)
        # entry: AI_detect_homogenization triggered  (or DriftGuard escalation)
        # process: AI_identify_weak_channels (v1.3: 노화·yield·드리프트 종합, required_coverage 보호)
        #          → AI_explore_5_strategies_focused
        #          → AI_validate_url_alive → AI_swap_into_catalog
        # convergence: diversity_improvement >= SDX_POLICY.selection.diversity_improvement_target
        # output_root: .sdx/catalog/                                (mutate shards in place)
        # output: channels/{format}.yaml                            (affected shards)
        # output: index.yaml                                        (version bump + counts)
        # output: reports/refresh_v{N}.md                           (per-refresh log)
        # output: reports/homogenization_log.md                     (trigger event record)

    ModeExpand // 특정 셀 강화 (designing)
        # input: target_cells (--cells 인자)
        # process: AI_explore_targeted_cells → AI_validate_url_alive → AI_inject_into_catalog
        # note: 카탈로그 크기 80 초과 허용 (사용자 명시 강화)
        # output_root: .sdx/catalog/                                (additive — preserve existing)
        # output: channels/{format}.yaml                            (target shards updated)
        # output: index.yaml                                        (version bump + counts)
        # output: basis/rejected_candidates.yaml                    (append new v{N} section)
        # output: reports/expand_v{N}.md                            (this expand cycle log)

    ModeAudit // 직교성 재평가 (designing)
        # process: AI_recompute_orthogonality_matrix → AI_identify_redundant_pairs
        #          → AI_propose_replacements → AI_request_user_approval
        # note: 자동 적용 금지 (사용자 승인 필수)
        # output_root: .sdx/catalog/
        # output: basis/orthogonality_matrix_v{N}.json              (full N×N)
        # output: basis/compute_NxN.py                              (reproducible script)
        # output: reports/audit_v{N}.md                             (violations + recommendations)
        # output: basis/selection_log_v{N}.yaml                     (only if policy changes)

    DriftGuard // 라운드별 경량 직교성 선행 신호 (designing) — ★ 내부 훅, CLI 모드 아님 @v:1.3
        # entry: AOX Stage 6 wrap-up이 매 라운드 호출 (SDX_POLICY.drift_guard.check_every_round)
        # process: AI_orthogonality_drift_guard (표본 sample_pairs쌍 overlap) → recommendation
        # escalate: warn_pair_ratio ≥ warn_pair_ratio_refresh → ModeRefresh
        #           warn_pair_ratio ≥ warn_pair_ratio_audit   → ModeAudit
        # rationale: audit(분기)·refresh(동질화)만으로 라운드 사이 상관 누적이 잔존 → 선행 가드
        # note: homogenization(지연·시스템 신호)과 상보 — drift는 per-pair *선행* 신호. cost≪가치: 전수 N×N 회피
        # output_root: .sdx/catalog/
        # output: reports/drift_guard_log.md                         (per-round append)

    YieldLedger // realized-yield 귀속 기록 (designing) — ★ 내부 훅, CLI 모드 아님 @v:1.3
        # entry: AOX Stage 6 wrap-up이 라운드 종료 시 호출 (sdx_yield_attribution_contract)
        # process: AOX가 provenance walk(EVX→CIX→IDX→TCX→CH) → channel_ids → AI_record_channel_yield
        # effect: yield_log append + 기여 채널 last_yield_round/yield_count 갱신 (decay 모델 입력 채움)
        # boundary: .sdx/catalog 변경은 SDX 전유 — AOX는 channel_ids만 전달(읽기는 AOX, 쓰기는 SDX)
        # note: last_yield_round/yield_count는 *provenance-walk 산출*이지 수기 입력 아님
        # output_root: .sdx/catalog/
        # output: yield_log.jsonl                                    (per-round append, SDX 소유)
```

---

## PPR: 핵심 함수 정의

### 발굴 전략 (5개) — strategies/*.md가 정본 프롬프트

각 함수는 thin wrapper. 실제 발굴 동작은 `strategies/0X_*.md`의 자연어 프롬프트를 따른다.

```python
def AI_explore_reference_backtrack(seed_papers: list[Paper]) -> list[ChannelCandidate]:
    """역추적 발굴 — seed_papers의 reference를 depth 3까지 추적.
    prompt: strategies/01_reference_backtrack.md
    """
    # acceptance_criteria:
    #   - len(result) >= 30
    #   - ratio_non_us_eu(result) >= 0.30
    #   - 모든 후보에 trace_path 부착 (seed → depth_1 → depth_2 → depth_3)
    candidates = []
    for paper in seed_papers:
        refs = AI_extract_references(paper, depth=3)
        for ref in refs:
            channel = AI_identify_publishing_venue(ref)
            if channel not in candidates:
                candidates.append(channel)
    return candidates


def AI_explore_cross_lingual(
    topic: str,
    target_langs: list[str] = ["zh-CN", "ja", "ru", "hi", "es", "pt-BR", "ar"],
) -> list[ChannelCandidate]:
    """언어 횡단 발굴 — 동일 주제를 7개 비영어권 언어로 native search.
    prompt: strategies/02_cross_lingual_mirror.md
    """
    # acceptance_criteria:
    #   - 7개 언어 모두 커버 (각 ≥ 5개)
    #   - len(result) >= 35
    #   - 영문 mirror 존재 채널은 우선순위 낮춤
    candidates = []
    for lang in target_langs:
        translated = AI_translate_topic(topic, lang)
        results = AI_search_native_lang(translated, lang)
        candidates += AI_extract_channels(results)
    return candidates


def AI_explore_failure_archive(domain: str) -> list[ChannelCandidate]:
    """실패·사장 아카이브 발굴.
    prompt: strategies/03_failure_archive.md
    """
    # acceptance_criteria:
    #   - len(result) >= 20
    #   - 각 후보에 death_metadata 부착 (year, cause, unanswered_question)
    #   - 분석적 아카이브 우선 (단순 obituary 제외)
    queries = [
        f"abandoned {domain} technology archive",
        f"deprecated {domain} standard",
        f"failed {domain} startup graveyard",
        f"killed by {domain}",
        f"withdrawn {domain} patent",
    ]
    candidates = AI_search_multi(queries)
    return AI_extract_channels(candidates)


def AI_explore_adjacent_borrow(target_domain: str) -> list[ChannelCandidate]:
    """인접 분야 정보 인프라 차용.
    prompt: strategies/04_adjacent_borrow.md
    """
    # acceptance_criteria:
    #   - 5개 인접 분야 모두 분야간 거리가 멀 것 (예: 모두 IT 아님)
    #   - 분야당 ≥ 4개 채널 (총 ≥ 20)
    #   - 각 채널에 transfer_difficulty 점수 부착
    adjacent_domains = AI_identify_adjacent_domains(target_domain, min_count=5)
    candidates = []
    for adj in adjacent_domains:
        infra = AI_query_info_infrastructure(adj)
        candidates += infra
    return candidates


def AI_explore_weak_signal() -> list[ChannelCandidate]:
    """약신호 사냥 — niche newsletter, long-open issues, 비공개 그룹.
    prompt: strategies/05_weak_signal_hunt.md
    """
    # acceptance_criteria:
    #   - len(result) >= 25
    #   - 각 후보에 활성도 점수 + 검색 가시성 점수 부착
    #   - "구글 검색 1페이지에 안 나오는" 것 우선
    sources = [
        "substack:top_niche",
        "github:issues_open>1y",
        "stackoverflow:unanswered>100votes",
        "discord:public_servers",
        "mailing_list:active",
    ]
    return AI_crawl_weak_signal_sources(sources)
```

### 검증 및 평가

```python
def AI_check_url_alive(channel: ChannelCandidate) -> bool:
    """경량 검증 — HTTP HEAD/GET → SDX_POLICY.http.acceptable_status만 통과."""
    # acceptance_criteria:
    #   - 내용 분석 수행 금지 (사용자 결정)
    #   - timeout = SDX_POLICY.http.url_check_timeout_sec
    try:
        response = http_head(channel.url, timeout=SDX_POLICY["http"]["url_check_timeout_sec"])
        return response.status in SDX_POLICY["http"]["acceptable_status"]
    except:
        return False


def AI_score_8axis_metrics(
    channel: ChannelCandidate,
    existing_catalog: list[ChannelEntry],
) -> ChannelMetrics:
    """8축 0-10 점수 산정. independence는 기존 카탈로그와의 비교 필요."""
    # acceptance_criteria:
    #   - 8개 축 모두 0-10 정수 또는 실수
    #   - independence는 max(overlap with existing) → 10 - (10 × max_ov)
    return {
        "independence":   AI_compute_independence(channel, existing_catalog),
        "signal_density": AI_estimate_signal_density(channel),
        "persistence":    AI_check_update_frequency(channel),
        "accessibility":  AI_check_api_or_free(channel),
        "geo_diversity":  AI_score_non_us_eu(channel),
        "temporal_depth": AI_check_archive_depth(channel),
        "format_unique":  AI_score_format_uniqueness(channel),
        "trust_level":    AI_estimate_trust(channel),
    }


def AI_compute_pairwise_overlap(ch_a: ChannelEntry, ch_b: ChannelEntry) -> float:
    """두 채널 간 신호 중복도 (0-1)."""
    # acceptance_criteria:
    #   - 0.0 <= result <= 1.0
    #   - 같은 4-Axis 셀이면 +0.4, 같은 도메인 +0.3,
    #     같은 publisher_group +0.2, 같은 언어 +0.1
    #   - overlap >= SDX_POLICY.audit.redundancy_similarity_threshold → 중복으로 간주
    score = 0.0
    if ch_a.axis_cell == ch_b.axis_cell:
        score += 0.4
    if ch_a.primary_domain == ch_b.primary_domain:
        score += 0.3
    if ch_a.publisher_group == ch_b.publisher_group:
        score += 0.2
    if ch_a.language == ch_b.language:
        score += 0.1
    return min(score, 1.0)


def AI_select_orthogonal_basis_80(
    candidates: list[ChannelCandidate],
) -> list[ChannelEntry]:
    """그리디 직교 선택 — total_score 내림차순으로 SDX_POLICY 임계 만족 후보만 채택."""
    # acceptance_criteria:
    #   - len(result) == SDX_POLICY.bootstrap.basis_target  (80)
    #   - 모든 쌍의 overlap < SDX_POLICY.selection.max_overlap_cut  (0.5)
    #   - 4-Axis 셀 커버리지 >= SDX_POLICY.selection.cell_coverage_floor  (0.6)
    selected = []
    sorted_cands = sorted(candidates, key=lambda c: c.total_score, reverse=True)
    target = SDX_POLICY["bootstrap"]["basis_target"]
    cut = SDX_POLICY["selection"]["max_overlap_cut"]
    for cand in sorted_cands:
        if len(selected) >= target:
            break
        max_ov = max(
            (AI_compute_pairwise_overlap(cand, s) for s in selected),
            default=0,
        )
        if max_ov < cut:
            selected.append(cand)
    if AI_cell_coverage(selected) < SDX_POLICY["selection"]["cell_coverage_floor"]:
        selected = AI_force_fill_empty_cells(selected, candidates)
    return selected
```

### 동질화 트리거

```python
def AI_detect_homogenization(recent_outputs: list[IdeaFirstOutput]) -> TriggerDecision:
    """IdeaFirst-MC 최근 N라운드 출력의 동질화 측정.
    SDX_POLICY.homogenization_thresholds.trigger_metric_count_min 이상 메트릭이
    임계를 초과하면 트리거 발동.
    """
    # acceptance_criteria:
    #   - 3개 메트릭(M1/M2/M3) 모두 산정
    #   - triggered: bool
    #   - metrics dict + recommendation 포함
    P = SDX_POLICY["homogenization_thresholds"]
    recent_outputs = recent_outputs[-P["recent_rounds_window"]:]

    # M1: 키워드 집중도
    top_keywords = AI_extract_top_keywords(recent_outputs, k=10)
    coverage = AI_compute_keyword_coverage(top_keywords, recent_outputs)
    m1 = coverage >= P["keyword_coverage_max"]

    # M2: 도메인 페어 반복
    pairs = AI_extract_domain_pairs(recent_outputs)
    max_pair_count = max(Counter(pairs).values())
    m2 = max_pair_count >= P["domain_pair_repeat_max"]

    # M3: 임베딩 유사도
    embeddings = [AI_embed(o.title + o.problem_statement) for o in recent_outputs]
    avg_sim = AI_avg_pairwise_cosine(embeddings)
    m3 = avg_sim >= P["embedding_similarity_max"]

    triggered_count = sum([m1, m2, m3])
    return {
        "triggered": triggered_count >= P["trigger_metric_count_min"],
        "metrics": {
            "keyword_coverage": coverage,
            "max_pair_count": max_pair_count,
            "avg_embedding_sim": avg_sim,
        },
        "recommendation": "refresh" if triggered_count >= P["trigger_metric_count_min"] else "no_action",
    }
```

### 채널 노화·드리프트 (v1.3 신규 — 외부 리뷰 대응)

```python
def AI_score_channel_freshness(ch: ChannelEntry, current_round: int) -> float:
    """채널 신선도 (0-10). 미산출 지속 + validated_at 노화에 따라 지수 감쇠.
    homogenization(시스템·지연 신호)과 달리 per-channel *선행* 신호."""
    # acceptance_criteria:
    #   - 0.0 <= freshness <= 10.0
    #   - rounds_since_yield 단조 증가 시 단조 감소 (반감 = channel_decay.half_life_rounds)
    D = SDX_POLICY["channel_decay"]
    anchor = ch.get("last_yield_round") or ch.get("first_seen_round") or current_round
    rounds_since_yield = max(0, current_round - anchor)
    base = 10.0 * (0.5 ** (rounds_since_yield / D["half_life_rounds"]))
    stale = AI_days_since(ch["validated_at"]) > D["stale_validated_days"]
    return round(min(10.0, max(0.0, base * (0.7 if stale else 1.0))), 2)


def AI_identify_weak_channels(
    catalog: Catalog, n: int, current_round: int, yield_log: YieldLog,
) -> list[ChannelEntry]:
    """교체 후보(weak) N개. 정본 기준 = SDX_POLICY.weak_channel.
    노화(freshness) + 실현 yield + 카탈로그 직교성 드리프트 + url 사망 종합.
    ★ required_coverage(geo/format/temporal/scale)를 깨는 채널은 weak여도 제거 금지."""
    # acceptance_criteria:
    #   - len(result) <= n
    #   - protect_required_coverage 시 커버리지 보존 (제거해도 required_coverage 유지)
    #   - 약함 점수 내림차순 (가장 약한 N개)
    W = SDX_POLICY["weak_channel"]
    D = SDX_POLICY["channel_decay"]
    drift_warn = SDX_POLICY["selection"]["max_overlap_cut"]

    scored = []
    for ch in catalog:
        fresh    = AI_score_channel_freshness(ch, current_round)
        realized = AI_realized_yield(ch, yield_log, window=D["yield_window_rounds"])
        drift    = AI_max_overlap_vs_catalog(ch, catalog)
        is_weak = (
            fresh < D["freshness_floor"]
            or ch["total_score"] < W["total_score_floor"]
            or drift > drift_warn
            or ch["url_alive"] is False
        )
        if is_weak:
            weakness = ((D["freshness_floor"] - fresh)
                        + max(0.0, drift - drift_warn) * 10.0
                        + (3.0 if realized == 0 else 0.0))
            scored.append((weakness, ch))

    ranked = [ch for _, ch in sorted(scored, key=lambda t: t[0], reverse=True)]
    if W["protect_required_coverage"]:
        ranked = AI_filter_coverage_safe(ranked, catalog)   # 제거 시 required_coverage 깨면 제외
    return ranked[:n]


def AI_orthogonality_drift_guard(catalog: Catalog) -> DriftDecision:
    """라운드별 경량 직교성 *선행* 신호 — AOX Stage 6 wrap-up이 매 라운드 호출.
    전수 N×N(ModeAudit) 대신 표본 쌍만 → 무거운 audit를 기다리지 않고
    상관 누적을 조기 포착해 refresh/audit로 에스컬레이트 (cost≪가치)."""
    # acceptance_criteria:
    #   - 표본 쌍 수 == min(SDX_POLICY.drift_guard.sample_pairs, C(len(catalog), 2))
    #   - recommendation ∈ {no_action, refresh, audit}
    G = SDX_POLICY["drift_guard"]
    pairs = AI_sample_channel_pairs(catalog, k=G["sample_pairs"])
    warn = [p for p in pairs if AI_compute_pairwise_overlap(*p) > G["pair_overlap_warn"]]
    ratio = len(warn) / max(1, len(pairs))
    if ratio >= G["warn_pair_ratio_audit"]:
        rec = "audit"
    elif ratio >= G["warn_pair_ratio_refresh"]:
        rec = "refresh"
    else:
        rec = "no_action"
    return {"warn_pair_ratio": round(ratio, 3), "sampled": len(pairs), "recommendation": rec}


def AI_load_yield_log() -> YieldLog:
    """SDX 소유 yield_log 적재 (append-only, 라운드당 1 레코드).
    레코드 = {round_id, ordinal, channel_ids:[CH-...], scope}."""
    # acceptance_criteria:
    #   - 파일 부재 시 빈 로그 반환 (최초 라운드)
    #   - ordinal 단조 증가 (freshness의 정수 라운드 거리 기준)
    path = SDX_POLICY["yield_attribution"]["yield_log_path"]
    return AI_read_jsonl(path) if AI_path_exists(path) else []


def AI_realized_yield(ch: ChannelEntry, yield_log: YieldLog, window: int) -> int:
    """최근 window 라운드 중 이 채널이 기여(채택 아이디어 산출)한 라운드 수."""
    # acceptance_criteria:
    #   - 0 <= result <= window
    recent = yield_log[-window:] if window else yield_log
    return sum(1 for rec in recent if ch["id"] in rec["channel_ids"])


def AI_record_channel_yield(round_id: str, channel_ids: list[str]) -> YieldRecord:
    """라운드 종료 시 기여 채널을 yield_log에 append + 각 엔트리 노화 필드 갱신.
    ★ .sdx/catalog 변경의 *유일한* 경로는 SDX (AOX는 channel_ids만 전달 — sdx_yield_attribution_contract).
    AOX Stage 6가 provenance를 walk해 channel_ids를 산출하면 SDX가 적용한다."""
    # acceptance_criteria:
    #   - yield_log에 정확히 1 레코드 append (ordinal = 직전+1)
    #   - 각 기여 채널: last_yield_round=ordinal, yield_count += 1
    #     (count_per_round_max_once → 라운드당 채널별 최대 1회)
    #   - 비기여 채널 / 그 외 스키마 필드 불변, required_coverage 무관(읽기 아님·교체 아님)
    Y = SDX_POLICY["yield_attribution"]
    log = AI_load_yield_log()
    ordinal = (log[-1]["ordinal"] + 1) if log else 0
    rec = {"round_id": round_id, "ordinal": ordinal,
           "channel_ids": sorted(set(channel_ids)), "scope": Y["credit_scope"]}
    AI_append_jsonl(Y["yield_log_path"], rec)
    for cid in rec["channel_ids"]:
        ch = AI_catalog_entry(cid)            # 카탈로그에 없으면 skip (교체로 사라진 채널)
        if ch is None:
            continue
        ch["last_yield_round"] = ordinal      # freshness anchor 갱신
        ch["yield_count"] = ch.get("yield_count", 0) + 1
        AI_write_catalog_entry(ch)            # shard in-place, v1.3 필드만 갱신
    return rec
```

### 모드 실행 함수 (v1.2 신규 — H2)

```python
def mode_bootstrap() -> Catalog:
    """ModeBootstrap의 5-Phase 순차 실행."""
    # acceptance_criteria:
    #   - len(catalog) == SDX_POLICY.bootstrap.basis_target
    #   - 4-Axis required_coverage 충족 (schemas/channel_entry.yaml#required_coverage)
    seeds      = phase1_seed_audit()
    candidates = phase2_exploration(seeds)              # [parallel] 5 strategies
    validated  = phase3_light_validation(candidates)
    basis      = phase4_orthogonality_compute(validated)
    return phase5_catalog_emit(basis)


def mode_refresh(catalog: Catalog, recent_outputs: list[IdeaFirstOutput]) -> Catalog:
    """동질화 감지 시 약한 채널 N개 교체. Convergence Loop."""
    # acceptance_criteria:
    #   - len(new_catalog) == len(catalog)  (크기 보존)
    #   - diversity_improvement >= SDX_POLICY.selection.diversity_improvement_target
    #     OR iterations == SDX_POLICY.selection.refresh_max_iterations
    decision = AI_detect_homogenization(recent_outputs)
    if not decision["triggered"]:
        return catalog

    weak = AI_identify_weak_channels(
        catalog, n=10,
        current_round=AI_current_round(),
        yield_log=AI_load_yield_log(),     # v1.3: 노화·실현 yield 반영
    )
    target_cells = AI_extract_cells(weak)

    for _ in range(SDX_POLICY["selection"]["refresh_max_iterations"]):
        candidates = AI_explore_5_strategies_focused(target_cells)
        validated = [c for c in candidates if AI_check_url_alive(c)]
        new_catalog = AI_swap_into_catalog(catalog, weak, validated)
        improvement = AI_evaluate_diversity_improvement(catalog, new_catalog)
        if improvement >= SDX_POLICY["selection"]["diversity_improvement_target"]:
            return new_catalog
        catalog = new_catalog
    return catalog


def mode_expand(catalog: Catalog, target_cells: list[AxisCell]) -> Catalog:
    """사용자가 지정한 4-Axis 셀에 5전략을 집중 적용. 카탈로그 크기 80 초과 허용."""
    # acceptance_criteria:
    #   - target_cells 모두에서 ≥ 1개 신규 채널 발굴
    #   - 기존 카탈로그 채널 보존 (제거 금지)
    candidates = AI_explore_targeted_cells(target_cells)
    validated = [c for c in candidates if AI_check_url_alive(c)]
    return AI_inject_into_catalog(catalog, validated)


def mode_audit(catalog: Catalog) -> AuditReport:
    """80x80 직교성 행렬 재계산 + 중복 후보 보고. 자동 적용 금지."""
    # acceptance_criteria:
    #   - matrix 크기 == len(catalog) × len(catalog)
    #   - 자동 카탈로그 수정 금지 — AI_request_user_approval 필수
    matrix = AI_recompute_orthogonality_matrix(catalog)
    threshold = SDX_POLICY["audit"]["redundancy_similarity_threshold"]
    redundant_pairs = AI_identify_redundant_pairs(matrix, threshold=threshold)
    replacements = AI_propose_replacements(redundant_pairs)
    return {
        "matrix": matrix,
        "redundant_pairs": redundant_pairs,
        "proposed_replacements": replacements,
        # 사용자 승인 후에만 catalog 갱신
    }
```

---

## 출력 스키마

### index.yaml — SDX Catalog Index Contract v1 (정본 — 다운스트림 계약) — v1.5

`index.yaml`은 SDX 카탈로그의 **진입점이자 소비자 계약(contract)**이다. TCX·IDX·sdx_ci 등 모든 소비자가 이 키 집합에 의존하므로, bootstrap/expand/refresh 및 sdx_ci(integrate/union)의 emit은 **반드시 아래 필수 키를 산출**한다.

```yaml
catalog:
  version: str                  # 예: "v1.3"
  policy_version: str           # 예: "sdx-1.5" — 소비자가 publisher_group taxonomy 추론용
  total_channels: int
  shard_key: "format"
  acceptance:                   # ★ 소비자 계약 핵심 (TCX catalog_validation)
    catalog_size: int           # 불변식: == sum(shards[].count) == total_channels
    lock_eligible: bool         # required_coverage 전항 PASS 시 true (사용 준비 완료 신호)
    required_coverage_passed: bool
shards:                         # list — 각 항목:
  - format: str
    file: str                   # 채널 shard 경로 (루트 상대)
    path: str                   # ★ == file (TCX shard_completeness 계약 별칭; 둘 다 유지)
    count: int
    id_range: str
basis:                          # ★ 최상위 키 (TCX required_keys)
  orthogonality_matrix: path
  overlap_policy: path
  selection_log: path
reports:                        # ★ 최상위 키
  coverage: path
```

**계약 불변식 (소비자가 검증):**

| 불변식 | 검증 주체 |
|---|---|
| `sum(shards[].count) == acceptance.catalog_size == total_channels` | TCX `consistency_check` (위반 시 abort) |
| 각 `shards[].path` 파일 실재 | TCX `shard_completeness` |
| `acceptance.lock_eligible == true` (또는 경고) | TCX `lock_check` |
| `catalog`/`shards`/`basis`/`reports`/`acceptance` 키 존재 | TCX `required_keys` |
| `lock_eligible` ⇔ required_coverage(geo 8/8, format ≥8, temporal 5/5, scale 3/3) 전항 PASS | SDX emit이 보장 |

> **호환성**: 기존 `references`/`axis_coverage`/`required_coverage_check`/`orthogonality_summary` 등 부가 키는 **그대로 유지**된다 — contract는 *필수 최소 집합*을 정의할 뿐 부가 정보를 금지하지 않는다. `file`과 `path`는 병기(생산자는 둘 다, 소비자는 `path` 우선).

### channel_catalog_v{N}.yaml (메인 산출물)

엔트리 스키마 정본: `schemas/channel_entry.yaml`. 핵심 필드:

```yaml
catalog:
  version: "v1.0"
  built_at: "2026-MM-DD"
  total_channels: 80
  axis_coverage:
    temporal_cells_filled: 5/5
    geographic_cells_filled: 7/8
    format_cells_filled: 9/10
    scale_cells_filled: 3/3
  channels:
    - id: "CH-0001"
      name: "..."
      url_pattern: "..."
      axis: {temporal, geographic, format, scale}
      metrics: {independence, signal_density, ...}  # 8 axes
      total_score: 7.5
      discovery_strategy: "S1_reference_backtrack"
      ...
```

### orthogonality_matrix.json

```json
{
  "size": 80,
  "channels": ["CH-0001", "CH-0002", "..."],
  "matrix": [[0.0, 0.2, "..."], "..."],
  "max_off_diagonal": 0.48,
  "avg_off_diagonal": 0.21
}
```

### homogenization_log.md

```markdown
## 2026-05-11 동질화 감지 로그

- IdeaFirst-MC 최근 5라운드 분석
- M1 키워드 집중도: 0.84 (TRIGGER) ✗
- M2 도메인 페어 반복: 4회 (TRIGGER) ✗
- M3 평균 임베딩 유사도: 0.61 (PASS) ✓
- 결정: refresh 모드 발동
- 교체 채널: CH-0023, CH-0045, CH-0067 → 신규 3개 등재
```

---

## 사용법

```bash
# 최초 카탈로그 구축 (1회)
/sdx bootstrap

# 동질화 감지 시 자동 갱신 (IdeaFirst-MC가 호출)
/sdx refresh

# 특정 4-Axis 셀 강화
/sdx expand --cells="T-100Y+,AF,nature"

# 직교성 재평가 (분기 권장)
/sdx audit
```

## IdeaFirst-MC와의 통합

```
[IdeaFirst-MC 실행]
    ↓
[STEP 0] channel_catalog_v1.yaml 로드
    ↓
[STEP 0.5] 4-Axis Matrix에서 셀 16개 무작위 샘플링
    ↓
[STEP 1-7] IdeaFirst 원형 진행 (각 셀의 채널을 8 AI에 분배)
    ↓
[POST] AI_detect_homogenization 자동 실행
    ↓
[IF triggered] /sdx refresh 자동 호출
```

---

## 신규성 검증

기존 정보 수집 도구는 RSS aggregator, 검색 alerter, 트렌드 모니터에 머문다. SDX는 **카탈로그 자체를 직교 기저로 설계하고, 출력 동질화를 트리거로 입력 채널을 자동 진화시키는** 메타 레이어다. 이는 단일 발굴 도구가 아닌, IdeaFirst 같은 합성 엔진의 **편향 면역 시스템**으로 기능한다.

## 향후 확장

- **자기 적용**: SDX 발굴 전략 자체를 5전략으로 발굴 (재귀)
- **다중 카탈로그**: 도메인별 특화 카탈로그 (의료-80, 우주-80 등)
- **IdeaFirst 출력 학습**: 실제로 좋은 인사이트를 낳은 채널에 가중치
- **공유 카탈로그**: AR Gducation 차원의 공용 채널 DB

## 버전 변경 이력

- **v1.5** (2026-06-02): SDX Catalog Index Contract v1 정식화 (다운스트림 계약)
  - `index.yaml`을 소비자 계약으로 격상 — `catalog.acceptance{catalog_size, lock_eligible, required_coverage_passed}`, `shards[].path`(=file 별칭), 최상위 `basis`/`reports`, `catalog.policy_version` 필수화
  - 계약 불변식 명시: `sum(shards.count)==acceptance.catalog_size==total_channels`, `lock_eligible ⇔ required_coverage 전항 PASS`
  - TCX `catalog_validation`(consistency_check/shard_completeness/lock_check/required_keys)와 정합 — SDX↔TCX 계약 드리프트 해소. sdx_ci(integrate/union) emit도 동일 계약 준수
  - 기존 부가 키(references/axis_coverage/orthogonality_summary 등) 전부 보존 — contract는 필수 최소 집합만 규정

- **v1.4** (2026-06-01): 출력 경로 파라미터화 (멀티 에이전트 동시 실행 대비)
  - 전 모드에 `--out=<dir>` 인자 추가 — 출력 루트 지정 (기본 `.sdx/catalog/`)
  - **`--out` 값 정규화 규칙(결정론적)**: bare token → `.sdx/<token>/`, 경로 → 그대로, 절대경로 → 그대로. `{OUT}`은 항상 카탈로그 루트(`catalog/` 자동 미추가)
  - `{OUT}` 해석 규칙 신설 — DESIGN/PPR의 모든 `.sdx/catalog/` 경로 및 `yield_log.jsonl`을 `{OUT}` 기준 해석
  - 중간 산출물(seed/all_candidates/validated 등)을 `{OUT}/.work/`로 정식 규정 — 기존 임시 공유 경로 `.sdx/work/` 폐지
  - 동시 실행 안전성: `--out` 단위 완전 격리(카탈로그+work+yield_log) → 에이전트당 고유 `--out` 시 race 없음
  - 교차/통합(merge) 모드는 본 버전 범위 밖 (추후 설계 — 전역 직교 재선택 기반)

- **v1.3** (2026-05-18): 외부 리뷰(채널 노화/pruning/동적 80) 공식 대응
  - `channel_maintenance` DESIGN_DECISIONS 추가 — 80 고정 유지(상향은 expand만), decay rate 명시화, correlation pruning 정리
  - `SDX_POLICY`에 `channel_decay`/`weak_channel`/`drift_guard`/`yield_attribution` 4개 블록 신설
  - 채널 노화·드리프트 PPR 추가 — `AI_score_channel_freshness`, `AI_identify_weak_channels`(정본 판정), `AI_orthogonality_drift_guard`, `AI_realized_yield`, `AI_record_channel_yield` 등
  - Gantree에 내부 훅 노드 2개 추가 — `DriftGuard`(라운드별 경량 직교성 선행 신호), `YieldLedger`(realized-yield 귀속)
  - `ModeRefresh` 약한 채널 판정에 노화·yield·required_coverage 보호 반영
  - frontmatter `version`/제목/`@v` 태그를 1.3으로 정합화 (본문 v1.3 기능과 헤더 불일치 해소)

- **v1.2** (2026-05-12): PGF 정합성 개선
  - Gantree status code 한국어 → PG 6개 영문 코드로 정규화 (`(designing)`, `(in-progress)`)
  - Gantree 안의 흐름 제어(if/while/Convergence Loop) → 별도 PPR `def` 블록으로 분리
  - `SDX_POLICY` 블록 신설 — 운영 임계값 8개를 단일 출처로 통합
  - `ModeRefresh`/`ModeExpand`/`ModeAudit`에 `mode_*()` PPR `def` 추가 (H2)
  - 4-Axis Matrix + 8축 메트릭의 진실 이중화 해소 — `schemas/channel_entry.yaml`을 정본으로 격상, SKILL.md는 요약+참조
  - 5전략 PPR을 thin wrapper로 단순화 — `strategies/0X_*.md`의 자연어 프롬프트가 정본
  - `acceptance_criteria` 형식을 PG 표준(`# acceptance_criteria:` 블록)으로 통일
  - 출력 파일 표기 `→ filename` → `# output: filename` (PG `→`는 데이터 파이프라인 전용)
  - 루트 노드에 `@v:1.2` 버전 태그 추가

- **v1.1** (2026-05-11): 외부 리뷰 반영
  - 점수 공식 명세 정확화 (분모 9.0 명시)
  - DESIGN_DECISIONS 섹션 추가 (결정 컨텍스트 기록)
  - ACCESS_POLICY 신규 (유료/기관 소스 처리)
  - strategies/ 5파일 분리

- **v1.0** (2026-05-11): 최초 릴리스

## 의존 스킬

- `pg` — PPR/Gantree notation (정본)
- `pgf` — design/plan/execute framework
- 통합 대상: `ideafirst-mc` (개발 예정)
