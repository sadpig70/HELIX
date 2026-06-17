---
name: evx
description: "EVX (Evaluation eXplorer) — CIX 산출물(.cix/latest/idea_pool.yaml)을 입력으로 받아 14 PGF 페르소나 평가 합의 + 강점·리스크·확장 시나리오로 최종 1 아이디어를 선정하는 스킬. IdeaFirst-MC STEP 5(14 AI × top 3) + STEP 6(Cross-AI → 1) + STEP 7(5S/3R/3X)을 AOX inline에서 분리. CIX 다음, AOX 마무리 직전 단계. Triggers: EVX, 평가, 최종선정, evaluation, top-3, cross-AI, consensus, final idea, 5strengths, risk assessment, expansion scenarios"
user-invocable: true
argument-hint: "evaluate|rerank|compare [--ideas=path] [--method=consensus|weighted]"
version: "1.1"
author: "양정욱 (sadpig70@gmail.com)"
---

# EVX (Evaluation eXplorer) v1.1

> 좋은 아이디어를 *고르는 일*은 만드는 일과 같은 무게의 별도 책임이다.
> 자기 자신이 만든 점수로 자기 자신을 뽑게 두면 점수의 의미가 사라진다.

## 존재 이유 (Why)

IdeaFirst Engine v1.2의 Stage 5(Evaluation)는 AOX inline으로 남아 있어, "14 AI × top 3 → cross-AI → 최종 1 → 5S/3R/3X"가 매번 ad-hoc 프롬프트로 재구성됐다. 이 결과 다음 문제가 발생했다:

1. **선정 기준 비표준** — 어느 평가축으로 top 3를 뽑는지 라운드마다 다름.
2. **CIX 자기참조** — CIX의 6축 total_score를 그대로 따르면 평가가 사실상 CIX의 재발표.
3. **재현 불가** — final_idea.md만 남고 14 페르소나가 어떻게 골랐는지 기록 없음.
4. **STEP 5-6-7 합쳐버림** — 세 단계의 역할 경계가 흐려져 디버깅 불가.

EVX는 Stage 5를 정식 스킬로 분리한다. CIX의 6축 점수를 **PGF 4축(novelty/feasibility/impact/integrity)으로 재매핑**한 뒤 각 페르소나의 evaluation_bias로 가중하여, **선정자가 생성자(CIX)와 다른 점수 체계로 평가**하도록 강제한다.

## Inputs

```yaml
input:
  source_root: ".cix/latest"                              # ★ CIX 고정 진입점
  source_files:
    idea_pool:          ".cix/latest/idea_pool.yaml"      # primary (top-K ideas with 6-axis scores)
    cix_manifest:       ".cix/latest/manifest.yaml"       # CIX round 추적용
    lens_assignment:    ".cix/latest/lens_assignment.yaml" # 선택적 (lens-aware tie-break)
  cli_override: "--ideas=<other_path>"                    # 옵션, 일반적으로 미사용
  rule: |
    기본은 .cix/latest/. 사용자가 --ideas로 다른 파일을 주면 그 경로 사용.
    어느 경우든 manifest.yaml을 함께 로드해 source_cix_round_id 추적.
```

EVX는 CIX manifest를 통해 source_idx_round_id, source_tcx_round_id, sdx_catalog_version까지 chain 추적. final_idea.md에 4-skill provenance 명시.

## EVX_POLICY (all magic numbers externalized)

```yaml
EVX_POLICY:
  stage5_top3:                                     # STEP 5 — 각 페르소나 상위 3
    personas_total: 14
    top_per_persona: 3
    expected_pool_size_max: 42                     # 14 × 3 = 42 후보 (중복 가능)

  axis_mapping:                                    # ★ 핵심 — CIX 6축 → PGF 4축
    novelty:     "(cix.novelty + cix.surprise) / 2"
    feasibility: "cix.defensibility"
    impact:      "(cix.generativity + cix.compounding) / 2"
    integrity:   "cix.coherence"
    rationale: |
      CIX 6축이 PGF 4축으로 손실 없이 mapping. novelty+surprise는 모두 "새로움" 차원,
      defensibility는 "구현 후 지킬 수 있나" = feasibility, generativity+compounding은
      "downstream 영향력" = impact, coherence는 "내부 일관성" = integrity로 의미 대응.
      CIX 점수를 그대로 쓰지 않고 재매핑함으로써 EVX 평가가 CIX 재발표가 되지 않게 한다.

  scoring:
    persona_score_formula: "Σ(bias_w[axis] × pgf_axis[axis]) / Σ(bias_w)"
    bias_source: "{PGF_SKILL_DIR}/discovery/personas.json#personas[*].evaluation_bias"
    bias_axes: [novelty, feasibility, impact, integrity]

  stage6_consensus:                                # STEP 6 — Cross-AI 글로벌 평가
    method: "dual_winner_v1_1"                     # ★ v1.1 IdeaFirst — single → dual
    dual_winner:                                   # ★ NEW v1.1
      enabled: true
      consensus_winner:                            # 안전한 합의 (기존 chain)
        method: "vote_count_with_breadth_tiebreak"
        tiebreak_order:
          - votes
          - cognitive_style_breadth
          - mean_persona_score
      innovation_winner:                           # 강한 champion (새로움 우선)
        method: "max_persona_score_among_voted"
        rule: "voted at least once + max(persona_score across all 14 personas)"
        tiebreak_order:
          - max_persona_score
          - votes                                  # 동점 시 합의 보조
          - mean_persona_score
      collapse_rule:                               # 둘이 같으면 single 출력
        if_identical: "report as single winner with note 'consensus == innovation'"
        if_different: "report both with comparison note (사용자가 선택)"
    rationale_v1_1: |
      v1.0의 single consensus winner는 한 cognitive_style 진영 4명의 합의 idea(IDEA-W2-030,
      4 votes, breadth 2)를 선택했지만, 강한 champion(P8 × L10 5-way tie score 9.06)을 가렸다.
      IdeaFirst Engine v1.3 §1.3 "비용 ≪ 가치" 원칙에 따라, 합의의 안전함과 혁신의 강함은
      *다른 차원*이므로 시스템이 사용자 대신 결정하지 않고 둘 다 출력한다.
      reference: .pgf/ANALYSIS-IdeaFirst.md D3+D4.

  stage7_assessment:                               # STEP 7 — 강점·리스크·확장
    strengths_required: 5                          # S1-S5
    risks_required: 3                              # R1-R3
    expansions_required: 3                         # X1-X3
    require_mitigation_per_risk: true              # R{n}에 대응되는 완화책 명시
    require_mechanism_per_expansion: true          # X{n}에 적용 메커니즘 명시

  quality_gates:
    g1_input_top_k_present: 24                     # CIX의 ideas top_k 일치
    g2_all_personas_voted: true                    # 모든 P1-P14 top-3 존재
    g3_final_1_votes_min: 2                        # winner ≥2 votes (단독 표는 약함)
    g4_assessment_counts: {strengths: 5, risks: 3, expansions: 3}
    g5_axis_mapping_traceable: true                # final_idea.md가 cix → pgf 매핑을 인용

  personas:                                        # ★ TCX v1.5/IDX v1.3/CIX v1.3와 동일 페르소나
    source: "{PGF_SKILL_DIR}/discovery/personas.json"
    version_pin: "1.0"
    enabled_set: [P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P14]   # v1.6 — 14 페르소나 (stage5_eval가 personas.json 동적 로드)
    use_evaluation_bias: true                      # ★ EVX 핵심 차별점

  storage:
    root: ".evx"                                   # project-root relative
    layout:
      index:   "index.yaml"
      latest:  "latest/"                           # ★ AOX summary가 사용
      rounds:  "rounds/"
      archive: "archive/"
    round_id_format: "EVX-{YYYYMMDD}-{NNN}"
    files_per_round:
      - stage5_candidates.yaml                     # 14 페르소나 top-3
      - stage6_final.yaml                          # consensus ranking + final 1
      - final_idea.md                              # 최종 1 + 5S/3R/3X (사람용 보고서)
      - manifest.yaml                              # source_cix_round + chain + policy snapshot
    latest_strategy: "copy"                        # Windows 안전
    retain_in_rounds_days: 90
    archive_target_pattern: "archive/{YYYY-Q[1-4]}/"
    archive_script: "{EVX_SKILL_DIR}/scripts/archive_rounds.py"
    concurrency_lock: ".evx/.lock"
```

## Modes

```yaml
evaluate:
  steps: [load_cix_inputs, validate_manifest, map_axes, persona_score_all, stage5_top3, stage6_consensus, stage7_assessment, emit]
  note: "기본 — CIX latest를 받아 최종 1 + 5S/3R/3X 산출"

rerank:
  steps: [load_existing_candidates, recompute_consensus, emit_diff]
  note: "--candidates=path로 기존 stage5_candidates.yaml을 재집계 (정책 변경 검증용)"

compare:
  steps: [load_multiple_cix_rounds, evaluate_each, emit_comparison]
  note: "여러 CIX round를 동일 정책으로 평가하여 round 간 winner 비교"
```

## DESIGN: Gantree

```
EVX_Main // EVX 메인 진입점 (designing) @v:1.0
    ModeEvaluate // 기본 평가 모드 (designing)
        Phase1_LoadCixInputs // CIX latest 입력 로딩 (designing)
            AI_load_cix_idea_pool                    // .cix/latest/idea_pool.yaml
            AI_load_cix_manifest                     // .cix/latest/manifest.yaml → source_cix_round_id
            AI_load_pgf_personas                     // {PGF_SKILL_DIR}/discovery/personas.json
            AI_validate_top_k_match                  // EVX_POLICY.quality_gates.g1
            # output: loaded_ideas + persona_biases (in-memory)

        Phase2_AxisMapping // CIX 6축 → PGF 4축 (designing) @dep:Phase1_LoadCixInputs
            AI_compute_pgf_novelty                   // (cix.novelty + cix.surprise) / 2
            AI_compute_pgf_feasibility               // cix.defensibility
            AI_compute_pgf_impact                    // (cix.generativity + cix.compounding) / 2
            AI_compute_pgf_integrity                 // cix.coherence
            # output: ideas with pgf_axes attached

        Phase3_PersonaScoring // 각 페르소나로 24 ideas 점수화 (designing) @dep:Phase2_AxisMapping
            [parallel-deterministic]                  # 14 × 24 = 336 점수 계산, 함수형 결정
            P1_score_all_24
            P2_score_all_24
            P3_score_all_24
            P4_score_all_24
            P5_score_all_24
            P6_score_all_24
            P7_score_all_24
            P8_score_all_24
            P9_score_all_24
            P10_score_all_24
            P11_score_all_24
            P12_score_all_24
            P13_score_all_24
            P14_score_all_24
            [/parallel-deterministic]
            # output: persona_score_matrix (pid → [(idea_id, score)])

        Phase4_Stage5Top3 // 각 페르소나 상위 3 (designing) @dep:Phase3_PersonaScoring
            AI_select_top_3_per_persona              // EVX_POLICY.stage5_top3.top_per_persona
            AI_validate_all_personas_voted           // EVX_POLICY.quality_gates.g2
            # output: stage5_candidates.yaml

        Phase5_Stage6Consensus // Cross-AI 합의 → 최종 1 (designing) @dep:Phase4_Stage5Top3
            AI_count_votes_per_idea
            AI_compute_cognitive_style_breadth       // voter cognitive_style 유니크 수
            AI_compute_mean_persona_score            // 14 페르소나 평균
            AI_rank_with_tiebreak                    // EVX_POLICY.stage6_consensus.tiebreak_order
            AI_validate_winner_votes_min             // EVX_POLICY.quality_gates.g3
            # output: stage6_final.yaml (ranking_top_8 + final_1)

        Phase6_Stage7Assessment // 5S/3R/3X 작성 (designing) @dep:Phase5_Stage6Consensus
            AI_draft_5_strengths                      // evidence from idea record + voter rationale
            AI_draft_3_risks_with_mitigations         // EVX_POLICY.stage7_assessment.require_mitigation_per_risk
            AI_draft_3_expansions_with_mechanisms     // require_mechanism_per_expansion
            AI_validate_assessment_counts             // g4
            # output: final_idea.md

        Phase7_CatalogEmit // 최종 출력 (designing) @dep:Phase6_Stage7Assessment
            AI_build_manifest                         // chain: SDX → TCX → IDX → CIX → EVX
            AI_emit_round_dir                         // .evx/rounds/{round_id}/ — 4 files
            AI_sync_latest                            // .evx/latest/ overwrite (copy)
            AI_update_evx_index                       // .evx/index.yaml — prepend round
            AI_maybe_run_archive                      // 90일+ 자동 이동
            # output_root: .evx/

    ModeRerank // 기존 stage5_candidates 재집계 (designing)
        # input: --candidates=path or default .evx/latest/stage5_candidates.yaml
        # process: AI_load_candidates → AI_recompute_stage6_consensus → AI_emit_diff_report
        # note: 정책 변경 (tiebreak order, axis mapping 등) 영향 검증용

    ModeCompare // 여러 CIX round 평가 비교 (designing)
        # input: --cix-rounds=CIX-A,CIX-B,...
        # process: AI_evaluate_each → AI_collect_winners → AI_emit_comparison_report
        # output: comparison.md (round 간 winner 변화 + 합의 강도 차이)
```

## PPR: 핵심 함수 정의

### Axis mapping (단일 출처)

```python
def AI_map_cix_to_pgf(cix_scores: dict) -> dict:
    """CIX 6축 점수를 PGF 4축으로 결정론적 매핑. EVX_POLICY.axis_mapping 단일 출처.
    EVX 평가는 이 매핑 위에서만 수행 — CIX의 total_score를 직접 사용하지 않는다.
    """
    return {
        "novelty":     (cix_scores["novelty"] + cix_scores["surprise"]) / 2,
        "feasibility":  cix_scores["defensibility"],
        "impact":      (cix_scores["generativity"] + cix_scores["compounding"]) / 2,
        "integrity":    cix_scores["coherence"],
    }
```

### Persona scoring (CIX 자기참조 차단)

```python
def AI_persona_score(idea, persona) -> float:
    """한 페르소나의 evaluation_bias로 한 idea의 PGF 4축을 가중평균.
    페르소나의 bias가 합산 가중치 분모가 되어 페르소나 간 비교 가능.
    """
    pgf = AI_map_cix_to_pgf(idea["scores"])
    bias = persona["evaluation_bias"]
    w_sum = sum(bias.values())
    return sum(bias[ax] * pgf[ax] for ax in bias) / w_sum
```

### Stage 6 consensus (tiebreak chain)

```python
def AI_rank_consensus(votes_by_idea, persona_score_matrix, personas):
    """tiebreak_order 적용. votes > cognitive_style_breadth > mean_persona_score.
    합의는 "다양한 cognitive_style이 동시에 동의" 라는 의미를 가중.
    """
    rows = []
    for iid, voters in votes_by_idea.items():
        styles = {personas[p]["cognitive_style"] for p in voters}
        mean_s = sum(s for s in persona_score_matrix.get(iid, [])) / max(1, len(persona_score_matrix.get(iid, [])))
        rows.append({
            "id": iid, "votes": len(voters), "voters": sorted(voters),
            "cognitive_style_breadth": len(styles),
            "mean_persona_score": round(mean_s, 3),
        })
    rows.sort(key=lambda r: (-r["votes"], -r["cognitive_style_breadth"], -r["mean_persona_score"]))
    return rows
```

### Phase 7: emit (TCX/IDX/CIX와 동일 패턴)

```python
def AI_emit_round_dir(round_dir, artifacts, manifest):
    """원자적 round dir 작성. artifacts = stage5/stage6/final_idea.
    acceptance: 4 files present, latest/ byte-identical, index.latest_round_id 갱신.
    """
    AI_acquire_lock(EVX_POLICY.storage.concurrency_lock)
    try:
        AI_write_files(round_dir, artifacts | {"manifest": manifest})
        AI_clear_dir(EVX_POLICY.storage.latest)
        AI_copy_tree(round_dir, EVX_POLICY.storage.latest)
        AI_update_evx_index(...)
        AI_maybe_run_archive(EVX_POLICY.storage)
    finally:
        AI_release_lock(EVX_POLICY.storage.concurrency_lock)
```

---

## Output Storage Layout

```
<project-root>/
└── .evx/
    ├── index.yaml                       # rounds catalog + latest_round_path
    ├── latest/                          # ★ AOX summary가 사용하는 고정 진입점
    │   ├── stage5_candidates.yaml
    │   ├── stage6_final.yaml
    │   ├── final_idea.md
    │   └── manifest.yaml
    ├── rounds/
    │   ├── EVX-20260513-001/
    │   ├── EVX-20260513-002/
    │   └── ...
    └── archive/
        └── 2026-Q2/
            ├── .READONLY
            └── EVX-*/...
```

**Upstream contract** — `.cix/latest/idea_pool.yaml` (+ manifest) 고정 경로.
**Downstream contract** — AOX Stage 6 wrap-up이 `.evx/latest/final_idea.md` 소비.

---

## Outputs

### stage5_candidates.yaml

```yaml
stage: STEP_5_8AI_TOP3
personas:
  P1:
    persona_name_en: "Disruptive Engineer"
    evaluation_bias: {novelty: 2.0, feasibility: 0.5, impact: 1.0, integrity: 1.0}
    top_3:
      - {rank: 1, score: 9.00, id: IDEA-W3-018, title: "...", layer: L9_Counterfactual,
         generated_by_persona: P1, cix_total_score: 8.71}
      - ...
  P2: ...
  ...
  P14: ...
```

### stage6_final.yaml

```yaml
stage: STEP_6_CROSS_AI_FINAL_1
method: "vote_count → cognitive_style_breadth → mean_persona_score"
ranking_top_8:
  - {id, title, layer, votes, voters, cognitive_style_breadth, mean_persona_score, ...}
  ...
final_1:
  id, title, votes, voters, layer, generated_by_persona, cix_total_score, mean_persona_score
```

### final_idea.md

사람용 보고서. 다음 섹션 필수:
- ★ FINAL IDEA (id + title + core mechanism)
- Why N personas converged (consensus rationale + cognitive_style 분석)
- 5 Strengths (S1–S5, 각 evidence)
- 3 Risks (R1–R3, 각 mitigation)
- 3 Expansion Scenarios (X1–X3, 각 mechanism)
- Pipeline-level observations
- Outputs inventory
- Round chain (provenance)

### manifest.yaml

```yaml
round_id: "EVX-{YYYYMMDD}-{NNN}"
built_at: ISO-8601
inputs:
  idea_pool: ".cix/latest/idea_pool.yaml"
  idea_pool_sha16: <hash>
  personas: "skills/pgf/discovery/personas.json"
  personas_sha16: <hash>
source_chain:
  cix: "CIX-{YYYYMMDD}-{NNN}"
  idx: "IDX-{YYYYMMDD}-{NNN}"
  tcx: "TCX-{YYYYMMDD}-{NNN}"
  sdx_catalog: "v{x.y}"
policy:
  axis_mapping: {...}                       # EVX_POLICY.axis_mapping
  scoring: "weighted_average(bias × pgf_axis)"
  consensus_tiebreak: [votes, cognitive_style_breadth, mean_persona_score]
outputs:
  stage5: "stage5_candidates.yaml"
  stage6: "stage6_final.yaml"
  final:  "final_idea.md"
```

---

## Usage

```bash
# 기본 — CIX latest 입력 사용
/evx evaluate

# 특정 CIX round 평가
/evx evaluate --ideas=.cix/rounds/CIX-20260513-002/idea_pool.yaml

# 기존 stage5_candidates를 재집계 (정책 변경 영향 보기)
/evx rerank --candidates=.evx/latest/stage5_candidates.yaml

# 여러 CIX round 평가 비교
/evx compare --cix-rounds=CIX-20260513-001,CIX-20260513-002
```

## IdeaFirst-MC 파이프라인 내 위치

```
[SDX] .sdx/catalog/
   ↓
[TCX] .tcx/latest/
   ↓
[IDX] .idx/latest/insight_layered_traced.yaml
   ↓
[CIX] .cix/latest/idea_pool.yaml
   ↓
[EVX evaluate] .evx/latest/final_idea.md ⭐ (여기)
   ↓
[AOX] summary.md + 동질화 감지 + 다음 라운드 트리거
```

EVX가 AOX Stage 5(14 AI × top 3) + STEP 6(Cross-AI) + STEP 7(5S/3R/3X)를 합쳐 받아 들이고, AOX는 wrap-up만 책임짐.

## 신규성 검증

기존 IdeaFirst AOX inline Stage 5는 (1) 매번 ad-hoc 프롬프트, (2) CIX 점수 재발표, (3) 페르소나 선택 기록 없음의 3가지 문제가 있었다. EVX는 다음을 구조적으로 해결:

| 기존 문제 | EVX 메커니즘 |
|---|---|
| ad-hoc 평가 기준 | `EVX_POLICY.axis_mapping` 단일 출처 (CIX 6 → PGF 4) |
| CIX 자기참조 | 평가축이 PGF 4축으로 재매핑 — CIX total_score 미사용 |
| 페르소나 선택 기록 없음 | `stage5_candidates.yaml`에 8 × top-3 + bias + score 영구 기록 |
| vote 동률 처리 | cognitive_style_breadth → mean_persona_score 명시적 chain |
| 5S/3R/3X 임의 작성 | EVX_POLICY.stage7_assessment + quality_gates.g4 강제 |

## File Layout

```
skills/evx/                              # skill (definition)
├── SKILL.md                            # this file
├── schemas/
│   └── eval_output.yaml                # 4 contracts (stage5/stage6/final_idea/manifest)
└── scripts/
    ├── stage5_eval.py                  # 결정론적 8-persona scoring + consensus + emit
    └── archive_rounds.py               # 90일+ round를 archive/{YYYY-Q[1-4]}/로 이동

<project-root>/.evx/                    # runtime (per-project)
├── index.yaml
├── latest/
├── rounds/
└── archive/
```

## Dependencies

```yaml
required:
  - pg                                  # PPR/Gantree notation
  - pgf                                  # ★ discovery/personas.json (evaluation_bias)
  - cix                                  # ★ direct input source (.cix/latest/)

upstream_chain:
  - pgf/discovery: "{PGF_SKILL_DIR}/discovery/personas.json (v1.0)"
  - sdx                                  # via tcx → idx → cix
  - tcx                                  # via idx → cix
  - idx                                  # via cix
  - cix                                  # 직접 입력 + manifest chain

downstream:
  - aox                                  # consumes .evx/latest/final_idea.md (Stage 6 wrap-up)

skill_directory_refs:
  EVX_SKILL_DIR: "this skill's root"
  PGF_SKILL_DIR: "sibling skill — persona definitions"
  CIX runtime:   ".cix/" (project-root relative)
  EVX runtime:   ".evx/" (project-root relative)
```

## 향후 확장 (v1.x+)

- **v1.1 LLM-augmented assessment** — 5S/3R/3X을 LLM sub-agent가 작성 (현재 v1.0은 main thread). evidence quoting + contradiction detection 추가.
- **v1.2 multi-axis evaluation** (IdeaFirst doc v2.0 EVX 정의 반영) — 기술 6축 + 상업 5축 + 리스크 3축 (현재는 PGF 4축만). RIX(Risk Inspection eXplorer) 분리 전 단계 흡수.
- **v1.3 voter calibration** — 페르소나 historical accuracy 추적 후 voter weight 동적 조정 (P1이 결과적으로 옳았던 비율).
- **v1.4 ensemble** — 다른 LLM(Claude/GPT/Gemini)을 페르소나별로 분산 호출 (CIX의 baseline_control와 동일 원칙).
