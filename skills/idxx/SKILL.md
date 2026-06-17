---
name: idxx
description: "IDXX (Insight Distillation eXclusionary eXpansion) — 이미 *구현된* 인사이트 테마(소모 아이디어 → source_insight provenance walk로 역추적)를 입력으로 받아, 그 테마의 재증류를 회피하고 under-distilled·약신호·교차트렌드 인사이트로 IDX 증류를 조향하는 스킬. SDXX(채널)·CIXX(아이디어 카테고리)와 함께 동질화를 입력→인사이트→출력 3점에서 차단. IDX 정본(10층 계위·evidence-trace·layer reject)을 재사용하고, insight 포화 맵 + 증류 steering overlay + ★evidence-floor 가드를 추가. Triggers: IDXX, 인사이트편향제거, 미증류인사이트, 재증류회피, 약신호인사이트, exclusionary distillation, insight steering, under-distilled, 동질화탈출 인사이트, built-upon insight"
user-invocable: true
argument-hint: "steer [--trends=path] [--map=path] [--out=dir] | map [--ledger=path]"
version: "1.0"
author: "양정욱 (sadpig70@gmail.com)"
---

# IDXX (Insight Distillation eXclusionary eXpansion) v1.0

> IDX가 트렌드에서 인사이트를 *증류*한다면, IDXX는 이미 *구현된* 인사이트 테마를 입력으로 받아
> 그 **여집합**(미증류·약신호 인사이트)으로 증류를 조향한다.
> SDXX가 입력(채널)을, CIXX가 출력(아이디어 카테고리)을 다양화하듯, IDXX는 그 사이(인사이트)를 다양화한다.

## 존재 이유 (Why) — IDX의 독립적 동질화

IDX는 "가장 강한 메타패턴"을 인사이트로 선별하는데, 그게 항상 **같은 시끄러운 거대트렌드**
(agentic AI·PQC·robotics·inference-grid)다 → 채널을 바꿔도(SDXX) IDX가 **같은 인사이트를 재증류**하는
독립적 동질화 경향이 있다. 실측: 한 라운드 L6 인사이트 5개 중 3개가 **이미 발행된 프로젝트의 명제**
(INS-L6-003=robotrace, 004=settlemesh, 005=infermesh). IDX는 "이 인사이트로 이미 무언가 만들어졌다"는
기억이 없어 같은 테마를 반복 증류한다.

**IDXX = 배제를 증류 단계로 끌어올린다 (pre-distillation steering).** 소모 아이디어를 source_insight로
역추적(provenance walk)해 "이미 *구현된* 인사이트 테마" 포화 맵을 만들고, IDX 증류가 그 테마를
강등·미증류 영역을 승격하도록 조향. EVX 정형 필터와 상보가 아니라 상승작용.

| | IDX | IDXX |
|---|---|---|
| 구현된 테마 인지 | 없음 | **provenance walk로 built-upon 테마 인지** |
| 증류 선별 | 가장 강한 메타패턴(=반복 거대트렌드) | 포화 회피 + **under-distilled 승격** |
| 출력 | insight_layered_traced | 동일 스키마 + 포화 메타 |

> SDXX → IDXX → CIXX = 입력→인사이트→출력 3대 생성단에서 동질화 차단. TCX는 SDXX가 견인, EVX/AOX는
> 선택이라 별도 XX 불요 — **3점에서 멈춘다.**

## ★ evidence-floor 가드 (IDXX 고유 — 가장 중요)

인사이트는 **증거-추적(evidence-traced) 원재료**다. 셋(SDXX/CIXX/IDXX) 중 IDXX가 가장 섬세하다 —
반복 회피를 위해 **증거 약한 패턴을 신규로 승격하면 인사이트 품질이 붕괴**(forced novelty into noise).

규칙:
- 조향은 **IDX 증거-추적 후보 인사이트 *안에서만*** 작동. 증거 미달 패턴을 절대 승격하지 않는다.
- 포화 맵은 built-upon 테마를 **강등(demote)** 할 뿐, 증거 없는 신규를 강요하지 않는다.
- IDX의 evidence trace(hash/span/confidence) 의무는 그대로 — IDXX는 *순서/가중*만 조향.

## 정본 재사용 (IDX/AOX 자산 — 중복 정의 금지)

| 자산 | 정본 위치 |
|---|---|
| 10층 인사이트 계위 (L6 Gap·L7 Tension·L9 Counterfactual·L10 Generative + 조건부 L8) | `idx` SKILL.md §계위 |
| layer 도출 로직 / layer reject / dedup | `idx` SKILL.md |
| Evidence Trace (hash/span/confidence) | `idx` SKILL.md §Evidence Trace |
| insight_output 스키마 | `skills/idx/schemas/insight_output.yaml` |
| Persona ↔ Layer 분배 (P1-P14) | `idx` SKILL.md §Persona↔Layer |
| 소모 ledger + provenance(cix/idx round) | `.idea-ledger/consumed_ideas.yaml`, `.cix/rounds/*`, `.idx/rounds/*` |

IDXX가 추가하는 것은 **insight 포화 맵**(`scripts/build_insight_saturation_map.py`),
**증류 steering overlay**(`strategies/steering_overlay.md`), **evidence-floor 가드**, **prompts/**뿐.

## 포화 모델 (built-upon 테마 = demote, covered ≠ forbidden)

```
saturation(insight) = (built_upon_topic_overlap, layer_recurrence)
  built_upon_insights = provenance walk(소모 idea → cix round idea_pool → source_insight_id
                                        → idx round insight.statement)
  demote: 후보 인사이트가 built_upon 테마와 의미적으로 같으면 강등
  promote: under-distilled 토픽/약신호/교차트렌드 + 미사용 layer
```

핵심 규칙 (over-exclusion 회피):
- **테마 단위로 강등** — 거대트렌드 전체를 막지 않는다.
- `covered ≠ forbidden`: built-upon 토픽이라도 **다른 layer/tension/각도**면 허용·장려.
  - "agentic AI × accountable-ops gap" = 구현됨(agentmesh) → 강등
  - "agentic AI × *다른 L7 tension*" = 미증류 → 허용

## 핵심 파라미터

```yaml
BUILT_UPON_DEMOTE: true            # built_upon 테마 인사이트 강등
DEMOTE_PENALTY: 0.30               # 포화 테마 일치 시 total_score 가중 감점(증거 점수는 불변)
EVIDENCE_FLOOR_REQUIRED: true      # ★ 증거-추적 미달 후보는 조향 대상조차 아님(거부)
UNDER_DISTILLED_FLOOR: 0.4         # 출력 인사이트 중 under-distilled 비율 하한(목표)
LAYER_BALANCE: keep_idx_floors     # IDX layer floor(L6/L7/L9/L10) 그대로 유지
EMIT_FORMAT: idx_insight_traced    # 출력은 IDX insight_layered_traced 스키마 그대로(CIX 무변경 소비)
```

---

## DESIGN: Gantree

```
IDXX_Main // 인사이트 조향 증류 진입점 (in-progress) @v:1.0
    ModeMap // insight 포화 맵 빌드 (designing)
        # script: scripts/build_insight_saturation_map.py (결정론 — provenance walk)
        AI_walk_consumed_to_insight // 소모 idea → cix round → source_insight_id → idx round → statement
        AI_collect_built_upon // built-upon 인사이트 테마(statement/layer/project/topics)
        AI_round_topic_history // .idx/rounds/* 토픽 빈도 → recurring_topics + layer history
        # output: {OUT}/insight_saturation_map.yaml
    ModeSteer // IDX 증류를 under-distilled로 조향 (designing)
        Phase0_LoadMap // 포화 맵 적재 (designing)
        Phase1_EvidenceCandidates // IDX 정본 증류로 evidence-traced 후보 인사이트 생성 (designing) @dep:Phase0_LoadMap
            # IDX 정본 layer 도출 + evidence trace 그대로 — 후보 풀 생성
            AI_distill_layer_candidates // L6/L7/L9/L10 (+L8 조건부)
        Phase2_SaturationReweight // 포화 테마 강등 (designing) @dep:Phase1_EvidenceCandidates
            AI_demote_built_upon // built_upon 일치 → DEMOTE_PENALTY (★ evidence 점수는 불변)
            # criteria: evidence-floor 미달 후보는 애초에 제외(거부) — 강등이 아니라 부적격
        Phase3_SelectBalanced // layer floor + under-distilled floor 보장 (designing) @dep:Phase2_SaturationReweight
            AI_select_layer_floor // IDX layer floor 유지(L6/L7/L9/L10)
            AI_ensure_under_distilled_floor // under-distilled 비율 ≥ UNDER_DISTILLED_FLOOR
        Phase4_Emit // insight emit (IDX 스키마) + 포화 리포트 (designing) @dep:Phase3_SelectBalanced
            # output_root: {OUT}  (기본 .idxx/ ; --out=.idx/<round> 가능)
            # output: insight_layered_traced.yaml (IDX 스키마 — CIX/CIXX 직접 소비)
            # output: reports/insight_coverage_v{N}.md
            # output: insight_saturation_map.yaml (사용된 맵 snapshot)
```

---

## PPR: 핵심 함수

```python
def AI_walk_consumed_to_insight(entry: LedgerEntry) -> Optional[BuiltUpon]:
    """소모 idea → source_insight 역추적. cix/idx round가 디스크에 있으면 정밀 statement."""
    # acceptance_criteria:
    #   - cix round idea_pool에서 idea_id로 source_insight_id 조회
    #   - idx round insight에서 statement/layer 조회
    #   - 실패 시 consumed title/semantic_family fallback (layer='fallback')

def AI_build_insight_saturation_map(ledger, idx_rounds) -> InsightSaturationMap:
    """built-upon 테마 + recurring 토픽 + layer history."""
    # acceptance_criteria:
    #   - built_upon_insights = [{statement, layer, project, topics}]
    #   - recurring_topics = 2+ IDX 라운드에 등장한 토픽
    #   - layer_distribution_history per round

def saturation(insight: Insight, smap: InsightSaturationMap) -> float:
    """후보 인사이트가 built-upon 테마와 얼마나 겹치는지 (0-1, 의미 기반)."""
    # acceptance_criteria:
    #   - 같은 (토픽군 × layer) built-upon → 높음
    #   - 같은 토픽 + 다른 layer/tension → 낮음 (covered≠forbidden)

def AI_reweight_with_evidence_floor(insight: Insight, smap) -> Insight:
    """★ evidence-floor + 포화 강등. 증거 미달이면 부적격(거부), 통과하면 포화 테마만 감점."""
    # acceptance_criteria:
    #   - insight.evidence trace 미달(IDX evidence 기준) → 'EVIDENCE_FLOOR_FAIL' 거부
    #   - saturation(insight, smap) 높음 → total_score -= DEMOTE_PENALTY (evidence/trace 필드 불변)
    if not AI_idx_evidence_ok(insight):                 # IDX 정본 evidence 기준 재사용
        insight.rejected = "EVIDENCE_FLOOR_FAIL"; return insight
    if saturation(insight, smap) >= 0.65:
        insight.total_score = max(0.0, insight.total_score - DEMOTE_PENALTY)
        insight.steering = "BUILT_UPON_DEMOTED"
    return insight

def mode_steer(trends_path, smap, out) -> InsightSet:
    """built-upon 회피 + under-distilled 승격으로 IDX 증류 조향 → insight set(IDX 스키마)."""
    # acceptance_criteria:
    #   - 산출 insight set은 IDX insight_layered_traced 스키마 준수(CIX/CIXX 무변경 소비)
    #   - 모든 출력 인사이트 evidence-traced (evidence-floor 통과)
    #   - layer floor(IDX) 유지 + under-distilled 비율 ≥ UNDER_DISTILLED_FLOOR
    #   - ledger/.idx/.cix 불변(read-only), {OUT}에만 기록(비파괴)
    cand = AI_distill_layer_candidates(trends_path)      # IDX 정본 + evidence trace
    cand = [AI_reweight_with_evidence_floor(i, smap) for i in cand if not i.rejected]
    return AI_select_layer_floor_and_under_distilled(cand, smap)
```

---

## 출력 스키마

IDXX `insight_layered_traced.yaml`은 **IDX insight_output 스키마를 그대로** 따른다(CIX/CIXX 무변경 소비).
각 인사이트에 IDXX 메타만 부착:

```yaml
# ... IDX insight 전 필드 (id, layer, statement, evidence, metrics, total_score, source_tcx_items, ...) ...
  idxx_steering: {built_upon_overlap: 0.NN, is_under_distilled: true, demoted: false}
```

### reports/insight_coverage_v{N}.md

```markdown
## IDXX insight coverage — <UTC>
- built-upon 테마(provenance walk): 24 (resolved 24/24)
- 강등된 후보(built-upon 재증류 시도): N
- evidence-floor 탈락: M  ← 증거 미달 신규 승격 차단(품질 보호)
- 출력 인사이트: 20 | under-distilled 비율: 0.45 (floor 0.40 통과) | layer floor 유지
- 새 토픽 유입(미증류): <weak-signal/cross-trend 토픽 목록>
```

---

## 사용법

```bash
# insight 포화 맵 빌드 (결정론 provenance walk)
python skills/idxx/scripts/build_insight_saturation_map.py --ledger .idea-ledger/consumed_ideas.yaml --out .idxx

# under-distilled 조향 증류 (TCX latest 입력)
/idxx steer --trends=.tcx/latest --map=.idxx/insight_saturation_map.yaml --out=.idxx/round0609

# 결과를 IDX latest로 승격해 CIX/CIXX 연계 (운영 단계, 승인 후)
#   .idxx/round0609/insight_layered_traced.yaml → .idx/latest/
```

`--out` 정규화·`{OUT}/.work/`·동시실행 격리는 SDX/SDXX v1.4 규칙 동일 (기본 `{OUT}` = `.idxx/`).

## 멀티 에이전트 + prompts (SDXX/CIXX와 동형)

`prompts/` 7-model × 2-persona 자가완결 조향-증류 프롬프트 (P1-P14, IDX Persona↔Layer 정합).
각 모델이 같은 포화 맵 공유 → 서로 다른 layer/약신호 분담 → insight 후보 병합(테마 dedup) → layer/evidence floor 재선택.

## 파이프라인 통합 (AOX 내 위치)

```
... TCX → [IDX 증류] → CIX ...   (현재)
... TCX → [IDXX steer = IDX 증류 + built-upon 회피 + evidence-floor] → insights → CIX(/CIXX) → EVX → AOX ...
```
- IDXX는 IDX를 **대체가 아니라 조향**. layer 계위/evidence trace 그대로, 증류 *순서·가중*만 포화 맵으로 조정.
- 출력이 IDX 스키마라 **CIX/CIXX/EVX/AOX 무변경**. 비파괴(`.idxx/`에만 기록).

## 경계 / 신규성

- IDXX = **조향기**. layer 계위·evidence trace의 소유자는 IDX, ledger 소유자는 AOX. IDXX는 읽어서 조향만.
- 기존 IDX/CIX/EVX/AOX 일절 수정 없음(보존). 포화 맵 + steering overlay + evidence-floor 가드가 추가 레이어.
- ★ 셋 중 가장 섬세 — evidence-floor 가드가 forced-novelty(노이즈 승격)를 막는 안전장치.

## 의존 스킬

- `idx` — 10층 계위·evidence trace·layer reject·insight_output 스키마 정본 (읽기 전용 재사용)
- `pg` — PPR/Gantree notation (정본)
- `pgf` — design/execute framework, 멀티 에이전트 delegate
- 연계: `sdxx`(채널)·`cixx`(아이디어 카테고리) — IDXX는 그 사이(인사이트) 대칭 스킬, `aox`(ledger 소유·provenance)
