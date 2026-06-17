---
name: sa-icx
description: "SA-ICX (Stand-Alone Idea Creative eXplorer) — cross-model 평가가 미가용인 단일 모델 런타임에서 IDX 인사이트를 입력으로 14 PGF 페르소나를 병렬 subagent로 파견해 120개 raw idea seeds와 standalone candidate pool을 생성하는 스킬. CIXX category_map 조향(white-space 우선, overused mechanism 회피)을 생성 단계에 적용한다. CIX v1.5.1의 cross-model certified production round를 대체하지 않으며, .cix/latest를 쓰지 않고 .sa-icx/에만 산출한다. Triggers: sa-icx, standalone icx, stand-alone icx, 단독 ICX, 독립 ICX, 14페르소나 아이디어 생성, multi persona idea forge"
user-invocable: true
argument-hint: "forge|resume|audit [--input=.idx/latest/insight_layered_traced.yaml] [--from-cix-raw=.cix/rounds/{CIX-ID}/raw_seed_ideas.yaml] [--round-id=...]"
version: "0.2"
author: "양정욱 (sadpig70@gmail.com)"
---

# SA-ICX (Stand-Alone Idea Creative eXplorer) v0.2

SA-ICX는 cross-model 평가가 미가용인 단일 모델 런타임(Claude Code, Codex 등)에서 실행 가능한 ICX 후보 생성기다.

목적은 CIX v1.5.1이 요구하는 cross-model baseline이 없을 때도, IDX의 깊은 인사이트를 14 PGF 페르소나 관점으로 강하게 변형해 후보 pool을 만드는 것이다. 생성 전에 CIXX category_map을 적재해 포화 카테고리(overused mechanism)를 회피하고 white-space 카테고리를 우선한다.

## Boundary

SA-ICX는 CIX production 결과가 아니다.

```yaml
validation_level: "single_model_multi_persona"
cross_model_certified: false
may_write_cix_latest: false
may_feed_evx_production: false
promotion_required: "cix_v1_5_1_phase_5_cross_model"
```

금지:
- `.cix/latest/` 쓰기
- CIX `idea_pool.yaml`로 위장
- `cross_model_certified: true` 표기
- surprise 점수를 cross-model 검증값처럼 기록
- EVX production 입력으로 직접 전달

허용:
- `.sa-icx/rounds/{round_id}/`에 standalone 후보 저장
- 14 PGF 페르소나를 14 subagent 역할로 분배
- raw / filtered / candidate pool 생성
- CIX v1.5.1 승격용 handoff 작성

## Inputs

```yaml
input:
  primary: ".idx/latest/insight_layered_traced.yaml"
  fallback: ".idx/latest/insight_layered.yaml"
  cix_raw_resume: ".cix/rounds/{CIX-ID}/raw_seed_ideas.yaml"
  manifest: ".idx/latest/manifest.yaml"
  personas: "skills/pgf/discovery/personas.json"   # 14 personas (P1-P14) — 정본
  consumed_ideas_ledger: ".idea-ledger/consumed_ideas.yaml"
  category_map_builder: "skills/cixx/scripts/build_category_map.py"   # ledger -> 포화 맵 (결정론)
  steering_overlay: "skills/cixx/strategies/steering_overlay.md"
```

입력 인사이트는 L6/L7/L9/L10 각 5개, 총 20개를 기대한다. 부족하면 `manifest.round.status = "blocked"`로 기록하고 중단한다.

`--from-cix-raw`가 제공되면 SA-ICX는 이미 보존된 CIX phase 1-4 raw seeds를 standalone 후보 생성 입력으로 사용한다. 이 경우 새 raw generation을 반복하지 않고, raw seed의 `lens_application`, `source_round_chain`, `scores: null` 상태를 보존한 채 standalone filtering/scoring만 수행한다.

## Outputs

```yaml
output_root: ".sa-icx"
round_id_format: "SA-ICX-{YYYYMMDD}-{NNN}"
files:
  - raw_seed_ideas.yaml          # 20 insights x 6 lenses = 120
  - filtered_candidates.yaml     # single-runtime rejection 후 후보
  - candidate_pool.yaml          # standalone top candidates
  - persona_reports/             # P1-P14 subagent reports
  - manifest.yaml
  - PROMOTE_TO_CIX.md            # CIX v1.5.1 승격 안내
```

`latest/` mirror는 선택 사항이지만 `.sa-icx/latest/`만 사용한다. `.cix/latest/`는 절대 사용하지 않는다.

## Execution

```text
SA_ICX_Forge
    LoadInputs
        read .idx/latest/insight_layered_traced.yaml
        read .idx/latest/manifest.yaml
        read skills/pgf/discovery/personas.json   # 14 personas

    BuildCategoryMap
        run: python skills/cixx/scripts/build_category_map.py (ledger -> category_map.yaml)
        load overused_mechanisms (예: compatibility-mesh, clearing-market) and white_space cells
        if ledger absent: empty map, steering skipped (manifest에 기록)

    OrResumeRawSeeds
        if --from-cix-raw is present:
            read existing raw_seed_ideas.yaml
            verify count == 120
            verify all lens_application.transformation exists
            skip GenerateRawSeeds

    AssignWork
        P1_DisruptiveEngineer      -> radical inversion / paradigm break
        P2_ColdEyedInvestor        -> market mechanism / moat
        P3_RegulatoryArchitect     -> governance and compliance inversion
        P4_ConnectingScientist     -> cross-domain analogy
        P5_FieldOperator           -> deployable mechanism
        P6_FutureSociologist       -> social behavior shift
        P7_ContrarianCritic        -> failure-as-feature / rejection pressure
        P8_ConvergenceArchitect    -> multi-stack fusion
        P9_PracticalAgencyEthicist     -> agency, refusal, consent mechanism
        P10_EmbodiedUxAnthropologist   -> embodied/physical-cue UX, field ritual
        P11_AdversarialRobustnessAnalyst -> attack surface, failure-mode inversion
        P12_RegenerativeSystemsEcologist -> regenerative loop, biological transplant
        P13_HistoricalCycleAnalyst     -> historical analogy, cycle reframing
        P14_MechanismDesigner          -> incentive/mechanism design
        (정본은 personas.json — 위 라벨은 기본 역할 분배)

    GenerateRawSeeds
        each insight receives 6 lens applications
        inject steering overlay: white-space 카테고리 우선, overused mechanism 회피
        preserve lens_application.transformation for every seed
        output raw_seed_ideas.yaml

    FilterCandidates
        read .idea-ledger/consumed_ideas.yaml if present
        remove adjacent-market obviousness
        remove weak lens trace
        remove duplicate mechanism
        remove candidates matching consumed ideas on the canonical keys:
            idea_id (same-round only), normalized_title, aliases, semantic_family
        reject overused-mechanism reapplication: CONSUMED_CATEGORY_SATURATED
        write .idea-ledger/exclusion_report_latest.md when any consumed candidate is found
        output filtered_candidates.yaml

    ScoreStandalone
        score axes: novelty, generativity, defensibility, compounding, coherence
        tag each candidate: cixx_category {domain, mechanism, is_white_space}, category_saturation
        surprise_proxy allowed only as internal_hint, not certification
        output candidate_pool.yaml (white-space 비율을 manifest에 기록)

    EmitRound
        write .sa-icx/rounds/{round_id}/
        write manifest.yaml
        write PROMOTE_TO_CIX.md
```

## Subagent Pattern

런타임이 subagent를 지원하면 **14 페르소나 병렬 파견이 기본**이다 (PGF discover 패턴).
파견 시 `pgf/agent-protocol.md`의 PG TaskSpec으로 입력·출력 타입과 acceptance_criteria를 구조화해 전달한다. 각 subagent는 자기 페르소나 slice만 소유하고 `persona_reports/P{n}.yaml`을 쓰거나 main agent가 쓸 구조화 결과를 반환한다. subagent 미지원 런타임에서는 main agent가 페르소나를 순차 시뮬레이션한다 (결과 등급 동일: single-model).

Default partition:

```yaml
P1: [L9_Counterfactual, L10_Generative]
P2: [L7_Tension]
P3: [L6_Gap, L7_Tension]
P4: [L9_Counterfactual]
P5: [L6_Gap]
P6: [L10_Generative]
P7: [L6_Gap, L7_Tension]
P8: [L9_Counterfactual, L10_Generative]
P9: [L7_Tension, L10_Generative]
P10: [L6_Gap, L10_Generative]
P11: [L7_Tension, L9_Counterfactual]
P12: [L10_Generative]
P13: [L9_Counterfactual]
P14: [L6_Gap, L9_Counterfactual]
```

Main agent responsibilities:
- no duplicate mechanisms across personas
- layer balance in candidate pool
- steering compliance: overused mechanism 회피, white-space 비율 보고
- manifest honesty
- promotion boundary enforcement

## Manifest Contract

```yaml
round:
  id: "SA-ICX-{YYYYMMDD}-{NNN}"
  version: "0.2"
  mode: "forge"
  status: "completed | blocked"

validation:
  level: "single_model_multi_persona"
  cross_model_certified: false
  surprise_proxy_is_certification: false
  cix_promotion_required: true

inputs:
  source_idx_round: "IDX-{YYYYMMDD}-{NNN}"
  source_tcx_round: "TCX-{YYYYMMDD}-{NNN}"
  sdx_catalog: "현재 .sdx/catalog/index.yaml의 version 값을 기록"
  source_cix_blocked_round: "CIX-{YYYYMMDD}-{NNN} | null"

steering:
  category_map_used: boolean
  overused_mechanisms_avoided: ["기록: category_map의 overused 목록"]
  white_space_share: "candidate_pool 중 is_white_space 비율"

outputs:
  raw_seed_count: 120
  filtered_count: integer
  candidate_count: integer
  consumed_excluded_count: integer
  saturated_rejected_count: integer   # CONSUMED_CATEGORY_SATURATED

policy:
  may_write_cix_latest: false
  may_feed_evx_production: false
  promotion_target: "CIX v1.5.1 phase 5 surprise_validation"
  consumed_idea_reuse_policy: "exclude_same_or_derivative"
```

## Promotion

`PROMOTE_TO_CIX.md` must include:

```bash
/cix innovate --from-sa-icx=.sa-icx/rounds/{round_id} --from-phase=5_surprise_validation
```

If that command is not implemented in the current repo, state the manual promotion contract instead:

```text
Use SA-ICX raw/candidate pool as candidate-generation evidence.
Run CIX v1.5.1 cross_model surprise_validation before emitting .cix/latest.
```

## SA Chain Integration

SA-ICX is the first stage of the standalone chain:

```text
SA-AOX -> SA-ICX -> SA-EVX -> SA-AOX wrap-up
```

Downstream contract:

```yaml
sa_evx_input:
  candidate_pool: ".sa-icx/latest/candidate_pool.yaml"
  manifest: ".sa-icx/latest/manifest.yaml"
  fallback_round_path: ".sa-icx/rounds/{round_id}/candidate_pool.yaml"
```

If `.sa-icx/latest/` is not enabled, SA-EVX must consume the explicit round path. SA-ICX output remains standalone and uncertified until promoted through CIX v1.5.1 cross-model validation.
