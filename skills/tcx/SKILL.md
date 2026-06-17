---
name: tcx
description: "TCX (Trend Collection & Analysis eXplorer) — SDX structured catalog tree를 소비해 대상 domain_set의 신호를 수집하고 4개 기준으로 산업 동향을 분석한다. Catalog/axis/policy 모두 SDX index.yaml과 schemas/channel_entry.yaml을 정본으로 동적 로드. Output: news.md, industry_trend.md, quality_report.md. Triggers: TCX, 뉴스수집, 트렌드분석, trend collection, industry trend, 산업동향분석, IdeaFirst STEP 1, IdeaFirst STEP 2, news to trend"
user-invocable: true
argument-hint: "full|collect|analyze [--catalog=.sdx/catalog/index.yaml] [--domains=...] [--rounds=N]"
version: "1.5"
author: "양정욱 (sadpig70@gmail.com)"
---

# TCX (Trend Collection & Analysis eXplorer) v1.5

TCX는 SDX가 만든 구조화 catalog를 PGF discovery의 14 cognitive personas로 병렬 수집·분석해, IDX가 소비할 `industry_trend.md`를 만든다.

> **v1.5 변경**: PGF discovery 페르소나 정식 통합(v1.5 P1-P8 → v1.6 P1-P14). TCX 자체가 "8 AI"를 추상 정의하던 것을 폐기하고 PGF `discovery/personas.json`을 단일 출처로 참조. `TCX_POLICY.personas + persona_assignment + scoring` 블록 신설. `domain_lens_affinity` 기반 deterministic 매핑으로 **모든 도메인 ≥2 페르소나 cross-check** 자동 보장. evaluation_bias 가중치를 quantitative scoring에 활용.
>
> **v1.4 변경**: 카탈로그 상수, 4-Axis enum, magic numbers를 모두 외부 정본(SDX index.yaml + schemas) 참조 또는 TCX_POLICY 블록으로 외부화. `.tcx/{index.yaml, latest/, rounds/, archive/}` 4-level storage 외부화.

## Inputs

```yaml
input:
  catalog_index: ".sdx/catalog/index.yaml"           # path만 받음; 내용은 동적 로드
  catalog_root_derived_from: "catalog_index.parent"
  domain_set_default: "{TCX_SKILL_DIR}/domain_sets/default.yaml"
  domain_set_override: "--domains=name1,name2,..."

  rule: |
    사용자 지정 --domains가 있으면 그 실행의 정본으로 사용.
    그 외에는 default.yaml 로드.
```

`index.yaml`은 manifest다. 채널 본문은 항상 `{catalog_root}/channels/*.yaml` shard에서 로드한다.
**카탈로그 카운트·shard 분포·셀 enum은 SDX가 정본**: TCX는 재정의하지 않는다.

## Catalog Validation (S1 — manifest reference, NO hardcoded counts)

```yaml
catalog_validation:
  source_of_truth: "index.yaml"
  required_keys:
    - shards                   # 존재 + 각 shard의 path/count 필드
    - basis                    # overlap_policy, orthogonality_matrix 등
    - reports                  # coverage report
    - acceptance               # catalog_size, lock_eligible

  lock_check:
    rule: "catalog.acceptance.lock_eligible == true"
    on_fail: "warn — TCX will still proceed but flag in quality_report.md"

  consistency_check:
    rule: "sum(shards[*].count) == catalog.acceptance.catalog_size"
    on_fail: "FAIL — catalog is malformed, abort"

  shard_completeness:
    rule: "all shards listed in index.shards must have an existing yaml file at index.shards[k].path"
    on_fail: "FAIL — missing shard file"

  policy_compatibility:
    rule: "catalog.policy_version is read; TCX adapts to whatever publisher_group taxonomy it implies"
    note: "TCX does not assume a fixed taxonomy"
```

→ SDX가 80→100 채널이 되거나 shard 분포가 8/11/10/.. 에서 다른 분포가 되어도 TCX는 무수정.

## Axis Reference (S2 — single source of truth)

```yaml
axis_definitions:
  source_of_truth: "{sdx_skill_root}/schemas/channel_entry.yaml#axis_system"
  resolution: "load at runtime; do NOT inline enum values in TCX"

  used_axes:
    temporal:   "loaded from axis_system.temporal"
    geographic: "loaded from axis_system.geographic"
    format:     "loaded from axis_system.format"
    scale:      "loaded from axis_system.scale"

  enforcement: |
    axis_tags in news.md items reference these enums by name.
    If SDX adds a cell (e.g., format=thesis), TCX automatically accepts it without code change.
```

## TCX_POLICY (S3 — all magic numbers externalized)

```yaml
TCX_POLICY:
  sampling:
    items_per_domain: 10               # G2 gate threshold
    min_format_shards: "all"           # G5 — every format shard must contribute at least 1 channel
    min_geographic_cells: 6            # G5 — geographic diversity floor
    target_channels_per_round: [32, 48]  # range
    rebalance_axes:
      temporal: "cover_all_available"
      geographic: "cover_at_least_{TCX_POLICY.sampling.min_geographic_cells}"
      scale: "cover_macro_meso_micro"

  collection:
    rounds_default: 1
    timeout_per_channel_sec: 30
    max_retries_per_channel: 2

  quality_gates_thresholds:
    G2_domain_coverage_floor:        "POLICY.sampling.items_per_domain"
    G5_geographic_diversity_floor:   "POLICY.sampling.min_geographic_cells"
    G5_format_shards_required:       "POLICY.sampling.min_format_shards"

  diversity:
    avoid_single_region_dominance: true
    max_single_region_share: 0.40    # 한 region이 sampling의 40% 초과 시 rebalance
    max_single_format_share: 0.30
    no_user_personalization: true    # G6 — 메모리·프로필·선호도 반영 금지

  storage:                            # v1.4 — output storage policy
    root: ".tcx"                       # project-root relative; SDX의 .sdx와 형제
    layout:
      index:   "index.yaml"            # rounds catalog + latest pointer
      latest:  "latest/"               # fixed-path entry for downstream (IDX 등)
      rounds:  "rounds/"               # 매 round 완전 보존
      archive: "archive/"              # 90일+ round를 quarter-grouped로 이동
    round_id_format: "TCX-{YYYYMMDD}-{NNN}"   # NNN = 그 날짜의 순번 001~
    files_per_round:
      - news.md
      - industry_trend.md
      - quality_report.md
      - manifest.yaml                  # catalog/domain_set/policy + persona snapshot
      - sampling_log.yaml              # 어떤 채널이 어떤 도메인·페르소나에 매칭됐나
    latest_strategy: "copy"            # symlink 대신 copy (Windows 호환)
    retain_in_rounds_days: 90          # rounds/에 보존 기간
    archive_target_pattern: "archive/{YYYY-Q[1-4]}/"
    archive_script: "{TCX_SKILL_DIR}/scripts/archive_rounds.py"
    concurrency_lock: ".tcx/.lock"     # 동시 실행 방지

  personas:                           # NEW v1.5 — PGF discovery 페르소나 정식 통합
    source: "{PGF_SKILL_DIR}/discovery/personas.json"
    version_pin: "1.0"                 # personas.json#version 고정 (변경 시 manifest mismatch)
    enabled_set: [P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P14]   # v1.6 — 전체 14 cognitive personas
    wave_count: 4                      # 14 / parallelism (4 wave × 4 ≈ 14)
    parallelism: 4                     # Anthropic 권장 4-5 parallel sub-agents
    diversity_axes:                    # PGF 페르소나 직교성 축
      - cognitive_style                # analytical | intuitive | critical | creative
      - domain_lens                    # technology | market | policy | science | society | science_technology | ethics | human_experience | security | ecology | history | economics
      - time_horizon                   # short | long

  persona_assignment:                 # NEW v1.5 — W1 (single-persona-domain) 해결 핵심
    strategy: "domain_lens_aware"     # PGF domain_lens 자동 affinity 매핑
    cross_check_min_per_domain: 2     # 모든 도메인 ≥2 persona (cross-check 강제)
    max_domains_per_persona: 4        # overload 방지
    cross_check_pairing_rule: "different_cognitive_style_preferred"
    deterministic: true               # rng_seed 기반 재현 가능
    
    domain_lens_affinity:             # 14 도메인 → PGF domain_lens 매핑 (v1.6: 신규 lens 추가)
      D01_AI:             [technology, science_technology]
      D02_Quantum:        [technology, science]
      D03_Robotics:       [technology]
      D04_SynBio:         [science, science_technology]
      D05_Space:          [technology, market]
      D06_Energy:         [market, policy, ecology]
      D07_Semiconductors: [market, technology]
      D08_Climate:        [society, science, ecology]
      D09_Healthcare:     [science, society, ethics, human_experience]
      D10_Cyber:          [policy, technology, security]
      D11_Manufacturing:  [technology, market]
      D12_AgriFood:       [society, science, ecology]
      D13_Geopolitics:    [policy, market, history]
      D14_FinTech:        [market, policy, economics]
    
    canonical_mapping:                # v1.6 — 14-domain × 14-persona 결정 매핑 (P1-P8 쌍 유지 + P9-P14 lens-fit 추가)
      D01_AI:             [P5, P8]    # tech/analytical + sci_tech/creative
      D02_Quantum:        [P1, P4]    # tech/creative + science/intuitive
      D03_Robotics:       [P1, P5]    # tech/creative + tech/analytical
      D04_SynBio:         [P4, P8]    # science/intuitive + sci_tech/creative
      D05_Space:          [P1, P7]    # tech/creative + market/critical
      D06_Energy:         [P7, P3, P12]      # +P12 ecology (planetary limits)
      D07_Semiconductors: [P2, P5]    # market/analytical + tech/analytical
      D08_Climate:        [P6, P4, P12]      # +P12 ecology
      D09_Healthcare:     [P4, P6, P9, P10]  # +P9 ethics, +P10 embodied UX
      D10_Cyber:          [P3, P7, P11]      # +P11 adversarial robustness
      D11_Manufacturing:  [P5, P2]    # tech/analytical + market/analytical
      D12_AgriFood:       [P6, P8, P12]      # +P12 ecology
      D13_Geopolitics:    [P3, P2, P13]      # +P13 historical cycle
      D14_FinTech:        [P2, P3, P14]      # +P14 mechanism designer
    
    persona_load_balance:             # 매핑 결과 — 페르소나당 도메인 수 (≤4 제약 충족)
      P1: 3   # D02, D03, D05
      P2: 4   # D07, D11, D13, D14
      P3: 4   # D06, D10, D13, D14
      P4: 4   # D02, D04, D08, D09 (D12 → P8로 이동: load balance)
      P5: 4   # D01, D03, D07, D11
      P6: 3   # D08, D09, D12
      P7: 3   # D05, D06, D10
      P8: 3   # D01, D04, D12

  scoring:                            # NEW v1.5 — persona evaluation_bias 정량 사용
    use_persona_evaluation_bias: true
    bias_axes: [novelty, feasibility, impact, integrity]
    item_score_formula: |
      per-persona: score(item) = sum(persona.evaluation_bias[k] * intrinsic[k] for k in bias_axes)
      per-item:    final_score = mean(per-persona scores for personas that produced/cross-checked it)
    rank_within_domain_by: "weighted_persona_consensus"
    surface_disagreement: true        # high variance between cross-check pair → flag as tension signal
    tension_variance_threshold: 0.3   # |score_A - score_B|/max > 0.3 → flag for IDX L7 input
```

## Modes

```yaml
full:
  steps: [load_catalog, load_domain_set, load_personas, assign_personas, sample_channels, collect_news_per_persona_wave1, collect_news_per_persona_wave2, merge_news, analyze_trends_per_wave, merge_trends, cross_domain_synthesis, quality_check, emit]
collect:
  steps: [load_catalog, load_domain_set, load_personas, assign_personas, sample_channels, collect_news_per_persona_wave1, collect_news_per_persona_wave2, merge_news]
analyze:
  steps: [load_existing_news, analyze_trends_per_wave, merge_trends, cross_domain_synthesis, quality_check]
```

**wave structure**: 14 persona news collection은 `TCX_POLICY.personas.parallelism` 만큼 병렬 → `wave_count` 차수로 직렬. 기본 4 parallel × 4 wave (v1.6 — 14 페르소나). Trend analysis는 4 wave (각 wave가 3-4 domain 담당).

## Process

```python
def TCX_full(catalog_arg=".sdx/catalog/index.yaml", domains=None, policy=None):
    """SDX catalog tree → news.md + industry_trend.md + quality_report.md (v1.5 — persona-driven)"""
    # acceptance_criteria:
    #   - catalog_validation passes (consistency_check, shard_completeness)
    #   - persona_assignment satisfies cross_check_min_per_domain ≥ 2
    #   - all 7 quality gates pass OR quality_report.md documents fail
    #   - no user-personalization side-effects (G6)

    catalog = AI_load_sdx_catalog_tree(catalog_arg)              # 동적 — index + all shards
    AI_validate_catalog(catalog)                                  # S1 manifest reference
    axis = AI_load_axis_system_from_sdx(catalog)                  # S2 SDX schema reference

    policy = policy or AI_load_policy("TCX_POLICY")
    domain_set = AI_resolve_domain_set(
        cli_override=domains,
        default_path=AI_resolve_path("{TCX_SKILL_DIR}/domain_sets/default.yaml"),
    )

    # v1.5 — load PGF personas + assign to domains deterministically
    personas = AI_load_pgf_personas(policy.personas.source, version_pin=policy.personas.version_pin)
    assignment = AI_assign_personas(
        personas=personas,
        domain_set=domain_set,
        policy=policy.persona_assignment,
    )
    AI_validate_persona_assignment(assignment, min_cross_check=policy.persona_assignment.cross_check_min_per_domain)

    sampled = AI_sample_channels(
        catalog=catalog,
        axis=axis,
        policy=policy.sampling,
    )
    # v1.5 — pre-attach channels to personas based on persona.search_keywords + channel.shard affinity
    channel_assignment = AI_assign_channels_to_personas(sampled, personas, assignment)

    # v1.5 — collect news per persona, parallelism limited by policy.personas.parallelism, waves serialized
    news = AI_collect_news_persona_waves(
        domain_set=domain_set,
        assignment=assignment,
        channel_assignment=channel_assignment,
        wave_count=policy.personas.wave_count,
        parallelism=policy.personas.parallelism,
        items_per_persona_per_domain=policy.sampling.items_per_domain // policy.persona_assignment.cross_check_min_per_domain,
    )

    # v1.5 — score each item using all assigned personas' evaluation_bias; flag disagreements as L7 tension
    scored_news = AI_score_items_via_persona_bias(news, personas, policy.scoring)

    trend = AI_analyze_trends_per_wave(scored_news, dimensions=ANALYSIS_DIMENSIONS, parallelism=policy.personas.parallelism)
    cross_domain = AI_cross_domain_synthesis(trend, scored_news, assignment)
    quality = AI_check_quality(scored_news, trend, cross_domain, domain_set, sampled, assignment,
                                policy=policy.quality_gates_thresholds)

    # v1.4 storage — round dir + latest copy + index update + archive trigger
    AI_emit_outputs(
        artifacts={"news": scored_news, "industry_trend": trend, "cross_domain": cross_domain, "quality_report": quality},
        manifest=AI_build_manifest(catalog, domain_set, policy, sampled, personas, assignment),
        sampling_log=AI_build_sampling_log(sampled, domain_set, assignment, channel_assignment),
        storage=policy.storage,
    )


def AI_assign_personas(personas, domain_set, policy):
    """v1.5 — deterministic domain ↔ persona mapping per TCX_POLICY.persona_assignment.
    
    Uses canonical_mapping if domain_set matches default 14-domain set;
    otherwise computes via domain_lens_affinity.
    
    Returns: {domain_id: [primary_persona_id, cross_check_persona_id]}
    """
    # acceptance_criteria:
    #   - every domain in domain_set has ≥ policy.cross_check_min_per_domain personas
    #   - no persona has > policy.max_domains_per_persona domains
    #   - cross-check pair has different cognitive_style when possible
    if AI_domain_set_matches(domain_set, "default_ideafirst_domains"):
        return policy.canonical_mapping
    
    result = {}
    persona_load = {p.id: 0 for p in personas}
    for d in domain_set.domains:
        lens_pref = policy.domain_lens_affinity.get(d.id, [])
        # score each persona by domain_lens match + load balance
        scored = sorted(personas, key=lambda p: (
            -(1 if p.domain_lens in lens_pref else 0),
            -(2 if p.domain_lens == lens_pref[0] else 0) if lens_pref else 0,
            persona_load[p.id],
        ))
        primary = scored[0]
        # pick cross-check with different cognitive_style
        cross_check = next(
            (p for p in scored[1:] if p.cognitive_style != primary.cognitive_style),
            scored[1]
        )
        result[d.id] = [primary.id, cross_check.id]
        persona_load[primary.id] += 1
        persona_load[cross_check.id] += 1
    return result


def AI_score_items_via_persona_bias(news, personas, scoring_policy):
    """v1.5 — apply each persona's evaluation_bias to score items quantitatively.
    Surface high-variance pairs as L7 tension candidates (for IDX downstream).
    """
    # acceptance_criteria:
    #   - every item has scores: {persona_id: {bias_axes...: float}}
    #   - tension_flags ≥ 0; surface_disagreement set per scoring_policy
    for item in news.items:
        producing_personas = [item.persona_id] + item.cross_check_personas
        item.persona_scores = {}
        for pid in producing_personas:
            p = AI_lookup_persona(personas, pid)
            intrinsic = AI_estimate_item_intrinsic(item, axes=scoring_policy.bias_axes)
            item.persona_scores[pid] = sum(
                p.evaluation_bias[k] * intrinsic[k] for k in scoring_policy.bias_axes
            )
        scores = list(item.persona_scores.values())
        item.final_score = sum(scores) / len(scores)
        if scoring_policy.surface_disagreement and len(scores) >= 2:
            variance = (max(scores) - min(scores)) / max(scores) if max(scores) else 0
            item.tension_flag = variance > scoring_policy.tension_variance_threshold
    return news


def AI_emit_outputs(artifacts, manifest, sampling_log, storage):
    """v1.4 output storage — atomic round emit + latest sync + maintenance."""
    # acceptance_criteria:
    #   - rounds/{round_id}/ contains all 5 files (3 .md + manifest + sampling_log)
    #   - latest/ contents are byte-identical to the new round dir
    #   - index.yaml.latest_round_id == new round id
    #   - lock file released after commit
    round_id = AI_next_round_id(storage.root, format=storage.round_id_format)
    round_dir = f"{storage.root}/{storage.layout.rounds}{round_id}/"
    lock_path = storage.concurrency_lock

    AI_acquire_lock(lock_path)
    try:
        # 1) Write round directory atomically (temp dir → rename)
        AI_write_files(round_dir, artifacts | {"manifest": manifest, "sampling_log": sampling_log})

        # 2) Sync latest/ by copy (Windows-safe; not symlink)
        AI_clear_dir(f"{storage.root}/{storage.layout.latest}")
        AI_copy_tree(round_dir, f"{storage.root}/{storage.layout.latest}")

        # 3) Update index.yaml — prepend new round, set latest pointer
        AI_update_tcx_index(
            index_path=f"{storage.root}/{storage.layout.index}",
            new_round={"id": round_id, "path": f"{storage.layout.rounds}{round_id}",
                       "quality": artifacts["quality_report"].verdict,
                       "catalog_v": manifest["inputs"]["catalog"]["version"]},
        )

        # 4) Maintenance — trigger archive if any round older than retain window
        AI_maybe_run_archive(storage)
    finally:
        AI_release_lock(lock_path)

    return round_id
```

## Sampling Policy (driven by TCX_POLICY.sampling)

```yaml
format_shard_first:
  rule: |
    1. Iterate every shard in catalog.shards (whatever the current set is).
    2. Pick at least 1 channel from each shard with non-zero count.
    3. Continue picking until target_channels_per_round range met,
       balancing across temporal/geographic/scale cells per POLICY.rebalance_axes.
  references: TCX_POLICY.sampling
  no_static_shard_list: true   # ← do NOT hardcode [news, paper, patent, ...]
```

## Analysis Dimensions

```yaml
analysis_dimensions:
  D1_Technology_Trend: "기술 등장, 성숙도 변화, 표준화 진행"
  D2_Market_Structure: "경쟁구도, M&A, 신규진입, 시장집중도"
  D3_Policy_Regulation: "법안, 규제기관, 국가간 규제 분절"
  D4_Risk_Opportunity: "단기/중기 리스크, 기회, 변곡점"
```

## Quality Gates (S3 — thresholds reference POLICY, not hardcoded)

```yaml
quality_gates:
  G1_catalog_contract:
    rule: |
      catalog_validation.consistency_check passes
      AND catalog_validation.shard_completeness passes
      AND catalog.acceptance.lock_eligible OR warning_flagged

  G2_domain_coverage:
    rule: "every domain in domain_set has >= TCX_POLICY.quality_gates_thresholds.G2_domain_coverage_floor news items"

  G3_dimension_coverage:
    rule: "every domain has all 4 analysis dimensions in industry_trend.md"

  G4_channel_attribution:
    rule: "every item has source_channel_id and source_channel_name resolvable in catalog"

  G5_sampling_diversity:
    rule: |
      format_shards_used.count == catalog.shards.keys().count
      AND geographic_cells_used.count >= TCX_POLICY.quality_gates_thresholds.G5_geographic_diversity_floor

  G6_no_user_personalization:
    rule: "no user-specific memory, profile, preference, or capability bias detected in domain_set or sampling"

  G7_cross_domain_synthesis:
    rule: "industry_trend.md includes non-empty recurring_patterns, cascading_effects, boundary_phenomena"
```

## Output Storage Layout

Runtime artifacts live at project-root `.tcx/`:

```
<project-root>/
└── .tcx/
    ├── index.yaml                     # rounds catalog + latest_round_path
    ├── latest/                        # ★ downstream(IDX 등)의 고정 진입점
    │   ├── news.md
    │   ├── industry_trend.md
    │   ├── quality_report.md
    │   ├── manifest.yaml              # catalog/domain_set/policy snapshot
    │   └── sampling_log.yaml          # round 재현용
    ├── rounds/
    │   ├── TCX-20260513-001/          # 매 round 완전 보존 (5 files)
    │   ├── TCX-20260513-002/
    │   └── ...
    └── archive/                       # 90일+ round 자동 이동
        └── 2026-Q2/
            └── TCX-20260213-001/ ...
```

**Downstream contract** — IDX/AOX 등은 `.tcx/latest/{news,industry_trend,quality_report}.md` 고정 경로 사용.
실행 라운드 단위 이력은 `rounds/` 또는 `archive/`에서 round_id로 조회.

## Outputs

`news.md`:

```markdown
# News Collection — Round {round_id}
> TCX v1.3
> Catalog: {input.catalog_index}
> Catalog version/policy: {catalog.version} / {catalog.policy_version}
> Catalog size: {catalog.acceptance.catalog_size}
> Domain set: {domain_set.name}
> Channels sampled: {N} / {catalog.acceptance.catalog_size}

## {domain}
1. **{title}** [Source: {source_channel_id} / {source_channel_name}]
   - Date: {YYYY-MM-DD}
   - Summary: ...
   - Why important: ...
```

`industry_trend.md`:

```markdown
# Industry Trend Analysis — Round {round_id}

## {domain}
### D1 Technology Trend
### D2 Market Structure
### D3 Policy Regulation
### D4 Risk & Opportunity

## Cross-Domain Synthesis
### Recurring Patterns
### Cascading Effects
### Boundary Phenomena
```

## Usage

```bash
/tcx full --catalog=.sdx/catalog/index.yaml
/tcx collect --catalog=.sdx/catalog/
/tcx analyze --input=news.md
/tcx full --domains="AI,양자기술,로보틱스"
```

## Dependencies

```yaml
required:
  - pg                                  # PPR/Gantree notation
  - pgf                                  # design/plan/execute framework + ★ discovery/personas.json (v1.5)
  - sdx                                  # ★ direct input source (catalog tree)

upstream_chain:
  - pgf/discovery: "{PGF_SKILL_DIR}/discovery/personas.json (v1.0 — 14 cognitive personas)"

downstream:
  - idx                                  # consumes .tcx/latest/

skill_directory_refs:
  TCX_SKILL_DIR: "this skill's root (placeholder, runtime-neutral)"
  PGF_SKILL_DIR: "sibling skill — used for persona definitions (v1.5)"
  sdx_skill_root: "sibling skill — used for axis_system reference"
```

## File Layout

```
skills/tcx/                          # skill (definition)
├── SKILL.md                        # this file
├── schemas/
│   └── output_schemas.yaml         # output metadata contracts (v1.5 — persona_id field)
├── domain_sets/
│   └── default.yaml                # default_ideafirst_domains (14 domains)
└── scripts/
    ├── archive_rounds.py           # 90일+ round를 archive/{YYYY-Q[1-4]}/로 이동
    └── assign_personas.py          # v1.5 — deterministic domain ↔ persona 매핑

<project-root>/.tcx/                 # runtime (per-project)
├── index.yaml                       # rounds catalog + latest pointer
├── latest/                          # IDX 등이 사용하는 고정 진입점
├── rounds/                          # round 완전 보존
└── archive/                         # 90일+ archived rounds
```
