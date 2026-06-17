---
name: cixx
description: "CIXX (Creative Innovation eXclusionary eXpansion) — 소모(구현/derivative-제외) 아이디어 ledger를 입력으로 받아, 이미 포화된 카테고리(도메인×메커니즘)를 회피하고 미탐색 white-space 카테고리로 CIX 생성을 조향(pre-generation steering)하는 스킬. SDXX가 채널(입력)을 다양화하듯 CIXX는 아이디어 카테고리(출력)를 다양화한다. CIX의 정본(20 렌즈·6축 평가·idea_output 스키마·rejection_check)을 재사용하고, 소모-카테고리 포화 맵 + 생성 steering overlay + rejection_check 의미 확장(CONSUMED_CATEGORY_SATURATED)을 추가. 동질화(같은 메커니즘 반복) 탈출에 사용. Triggers: CIXX, 카테고리편향제거, 미탐색카테고리, 소모아이디어참조, white-space 발굴, exclusionary innovation, category steering, 메커니즘다양화, out-of-category, 동질화탈출 아이디어"
user-invocable: true
argument-hint: "steer [--ledger=path] [--insights=path] [--lens=...] [--out=dir] | map [--ledger=path]"
version: "1.0"
author: "양정욱 (sadpig70@gmail.com)"
---

# CIXX (Creative Innovation eXclusionary eXpansion) v1.0

> CIX가 인사이트 × 렌즈로 아이디어를 *생성*한다면, CIXX는 이미 *소모된* 아이디어 카테고리를
> 입력으로 받아 그 **여집합**(미탐색 도메인×메커니즘)으로 생성을 조향한다.
> SDXX가 입력(채널)을 다양화하듯, CIXX는 출력(아이디어 카테고리)을 다양화한다.

## 존재 이유 (Why) — CIX/EVX의 현재 결함

소모 아이디어 회피 장치는 있으나 **전부 생성 *이후* 정형 매칭**이다:
- EVX `consumed_match_reason`: ledger 대비 `idea_id / normalized_title / alias / semantic_family` **문자열 매칭** → 의미적 카테고리 중복은 통과(IDEA-003=robotrace, IDEA-004=infermesh가 통과한 실증).
- CIX `AI_reject_obvious`: `existing_product_match / baseline_LLM / inter_agent_overlap`은 있으나 **"소모 카테고리 포화"** 축이 없음.

무엇보다 **CIX는 ledger를 모르고 생성**한다 → 이미 포화된 "Compatibility Mesh × 기존도메인"을
반복 양산(실측: 소모 39 중 14가 compatibility-mesh, 한 pool에서 22/24가 derivative).

**CIXX = 배제를 생성 단계로 끌어올린다 (pre-generation steering).** 소모-카테고리 포화 맵을
CIX 생성에 주입해 포화 셀을 회피하고 white-space를 적극 겨냥. EVX 정형 필터와 **상보가 아니라
상승작용**: 사전 조향(안 만듦) + 사후 의미 필터(만들어도 카테고리 중복이면 거부) 이중 방어.

| | CIX | CIXX |
|---|---|---|
| 소모 ledger 인지 | EVX 사후 정형 매칭만 | **생성 사전 조향 + 사후 의미 필터** |
| 카테고리 모델 | 없음(렌즈×인사이트만) | **도메인 × 메커니즘 포화 맵** |
| 목적 | 인사이트→아이디어 생성 | 포화 회피·**미탐색 카테고리** 생성 |
| 출력 | idea_pool | idea_pool(동일 스키마) + category coverage |

> SDXX↔CIXX 대칭: SDXX는 입력단(채널) 동질화를, CIXX는 출력단(아이디어 카테고리) 동질화를 차단.
> 둘을 함께 쓰면 동질화를 **양끝에서** 끊는다.

## 정본 재사용 (CIX/EVX/AOX 자산 — 중복 정의 금지)

| 자산 | 정본 위치 |
|---|---|
| 20 혁신 렌즈 (4 그룹) | `skills/cix/prompts/lens_catalog.md`, `cix` SKILL.md §렌즈 |
| 6축 혁신 평가 / `CIX_POLICY` | `cix` SKILL.md |
| idea_output 스키마 (lens_application·domains·rejection_check·semantic_family) | `skills/cix/schemas/idea_output.yaml` |
| `AI_reject_obvious` 자명 거부 | `cix` SKILL.md (CIXX가 1축 *추가*) |
| 소모 ledger + `consumed_match_reason` (정형 매칭) | `skills/evx/scripts/stage5_eval.py` |
| ledger 파일 | `.idea-ledger/consumed_ideas.yaml` (AOX 소유) |

CIXX가 추가하는 것은 **소모-카테고리 포화 맵**(`scripts/build_category_map.py`),
**생성 steering overlay**(`strategies/steering_overlay.md`), **rejection_check 1축 확장**뿐.

## 카테고리 모델 (★ 입도 = 도메인 × 메커니즘, covered ≠ forbidden)

```
category(idea) = (domain, mechanism)
  domain    = idea.domains[0] 정규화 (AI Operations, Robotics, Quantum Security, ...)
  mechanism = lens_application 또는 title에서 도출한 메커니즘 클러스터
              (compatibility-mesh, signal-exchange, operating-exchange, failure-market,
               clearing-market, roaming, battery, endowment, ... )
```

핵심 규칙 (over-exclusion 회피):
- **포화 판정은 (도메인 × 메커니즘) 셀 단위.** 도메인 단독으로 막지 않는다.
- `covered ≠ forbidden`:
  - "Robotics × compatibility-mesh" = 포화(robotrace) → **회피**
  - "Robotics × *다른 메커니즘*" = 미탐색 → **허용·장려**
- 즉 **포화 도메인이라도 메커니즘이 진짜 다르면 통과**. 강제 novelty(novelty-for-novelty) 방지.

## 핵심 파라미터

```yaml
SATURATION_THRESHOLD: 0.65        # 아이디어 vs 소모-카테고리 의미 overlap ≥ → CONSUMED_CATEGORY_SATURATED
CELL_SATURATED_COUNT: 3           # 같은 (도메인×메커니즘) 셀이 ledger에 ≥3회 → 셀 SATURATED
MECHANISM_OVERUSE_RATIO: 0.30     # 한 메커니즘이 소모 전체의 ≥30% 점유 → OVERUSED (white-space 강제)
WHITE_SPACE_FLOOR: 0.4            # top-K 아이디어 중 white-space 비율 하한 (생성 목표)
EMIT_FORMAT: cix_idea_pool        # 출력은 CIX idea_pool 스키마 그대로 (다운스트림 EVX 무변경)
```

---

## DESIGN: Gantree

```
CIXX_Main // 카테고리 조향 생성 진입점 (in-progress) @v:1.0
    ModeMap // 소모-카테고리 포화 맵 빌드 (designing)
        # script: scripts/build_category_map.py (결정론 — ledger 파싱)
        AI_load_consumed_ledger // .idea-ledger/consumed_ideas.yaml 적재
        AI_extract_category // 각 entry → (domain, mechanism, semantic_family)
        AI_build_saturation_map // 셀 카운트 + 메커니즘 점유율 + white-space 식별
        # output: {OUT}/category_map.yaml
    ModeSteer // CIX 생성을 white-space로 조향 (designing)
        Phase0_LoadMap // category_map 적재 (designing)
            # ModeMap 산출 or 즉석 빌드
        Phase1_SteeredGenerate // CIX 생성 + steering overlay (designing) @dep:Phase0_LoadMap
            # overlay: strategies/steering_overlay.md (CIX 생성 프롬프트에 포화맵·white-space 주입)
            # CIX 정본 렌즈/6축 그대로, lens×domain 선택만 white-space 편향
            AI_steer_lens_domain // 포화 셀 회피, 미탐색 셀 우선
            AI_generate_seed_ideas // CIX AI_apply_lens (정본 재사용)
        Phase2_CategoryReject // rejection_check 의미 확장 (designing) @dep:Phase1_SteeredGenerate
            AI_reject_obvious_plus // CIX 자명거부 + CONSUMED_CATEGORY_SATURATED 1축 추가
            # criteria: category_saturation(idea, map) ≥ SATURATION_THRESHOLD → reject 사유 추가
        Phase3_ScoreSelect // CIX 6축 scoring + white-space floor (designing) @dep:Phase2_CategoryReject
            AI_score_6axis // CIX 정본
            AI_select_topK_white_space_floor // top-K, white-space 비율 ≥ WHITE_SPACE_FLOOR 보장
        Phase4_Emit // idea_pool emit (CIX 스키마) + category coverage (designing) @dep:Phase3_ScoreSelect
            # output_root: {OUT}  (기본 .cixx/ ; --out=.cix/<round> 가능)
            # output: idea_pool.yaml (CIX 스키마 — EVX 직접 소비)
            # output: reports/category_coverage_v{N}.md
            # output: category_map.yaml (사용된 맵 snapshot)
```

---

## PPR: 핵심 함수

```python
def AI_extract_category(entry: LedgerEntry) -> Category:
    """소모 ledger 1건 → (domain, mechanism, semantic_family)."""
    # acceptance_criteria:
    #   - domain = title 앞부분 정규화 (mechanism 키워드 이전)
    #   - mechanism = title/semantic_family에서 메커니즘 클러스터 매칭
    #   - 미매칭 시 mechanism='other'

def AI_build_saturation_map(ledger: list[LedgerEntry]) -> CategoryMap:
    """소모-카테고리 포화 맵. 셀 카운트·메커니즘 점유율·white-space."""
    # acceptance_criteria:
    #   - cells[(domain,mechanism)] = count
    #   - mechanism_share[m] = count(m)/total  → ≥ MECHANISM_OVERUSE_RATIO 면 'OVERUSED'
    #   - saturated_cells = {cell : count ≥ CELL_SATURATED_COUNT}
    #   - white_space = 도메인축 × 메커니즘축 격자에서 미커버/희소 셀 목록
    cells = Counter(AI_extract_category(e)[:2] for e in ledger)
    total = sum(cells.values())
    mech = Counter(); [mech.update({c[1]: n}) for c, n in cells.items()]
    return {
        "cells": dict(cells),
        "mechanism_share": {m: round(c/total, 3) for m, c in mech.items()},
        "overused_mechanisms": [m for m, c in mech.items() if c/total >= MECHANISM_OVERUSE_RATIO],
        "saturated_cells": [c for c, n in cells.items() if n >= CELL_SATURATED_COUNT],
        "white_space": AI_identify_white_space(cells, mech),
    }

def AI_identify_white_space(cells, mech) -> WhiteSpace:
    """미탐색·희소 (도메인×메커니즘) 셀 + 저빈도 메커니즘 추천."""
    # acceptance_criteria:
    #   - underused_mechanisms: 점유율 낮은 메커니즘(또는 신규 메커니즘 후보)
    #   - target_cells: 알려진 도메인 × underused_mechanism 중 미커버 셀
    #   - novel_mechanism_prompts: ledger에 없는 메커니즘 탐색 유도(렌즈 그룹 다양화)

def category_saturation(idea: SeedIdea, cmap: CategoryMap) -> float:
    """아이디어의 (도메인×메커니즘)이 소모 카테고리와 얼마나 겹치는지 (0-1, 의미 기반).
    EVX 정형 매칭이 놓치는 카테고리-derivative를 잡는다."""
    # acceptance_criteria:
    #   - 같은 (도메인,메커니즘) saturated_cell → 1.0
    #   - 같은 메커니즘 OVERUSED + 유사 도메인 → 높음
    #   - 다른 메커니즘 → 낮음 (covered 도메인이라도 통과 가능)
    dom, mech = AI_category_of(idea)
    if (dom, mech) in cmap["saturated_cells"]: return 1.0
    base = 0.7 if mech in cmap["overused_mechanisms"] else 0.0
    return round(min(1.0, base + AI_semantic_domain_overlap(dom, cmap)), 3)

# --- rejection_check 의미 확장 (CIX AI_reject_obvious + 1축) ---
def AI_reject_obvious_plus(idea: SeedIdea, cmap: CategoryMap) -> RejectDecision:
    """CIX 정본 자명거부 + CONSUMED_CATEGORY_SATURATED. 다른 축/임계는 CIX_POLICY 그대로."""
    # acceptance_criteria:
    #   - CIX AI_reject_obvious 전 로직 보존(재사용)
    #   - category_saturation(idea, cmap) ≥ SATURATION_THRESHOLD → reasons += 'CONSUMED_CATEGORY_SATURATED'
    #   - decision_threshold_reasons는 CIX_POLICY 그대로 (추가 축이 1표로 합산)
    base = AI_reject_obvious(idea)                       # CIX 정본 재사용
    if category_saturation(idea, cmap) >= SATURATION_THRESHOLD:
        base["reasons"].append("CONSUMED_CATEGORY_SATURATED")
        base["rejected"] = len(base["reasons"]) >= CIX_POLICY.rejection.decision_threshold_reasons
    return base

# --- 생성 조향 (오케스트레이터) ---
def mode_steer(ledger_path, insights_path, out) -> IdeaPool:
    """소모-카테고리 회피 + white-space 조향으로 CIX 생성 → idea_pool(CIX 스키마)."""
    # acceptance_criteria:
    #   - 산출 idea_pool은 CIX idea_output 스키마 준수 (EVX 무변경 소비)
    #   - top-K 중 white-space 비율 ≥ WHITE_SPACE_FLOOR
    #   - ledger 불변(read-only), .cix/.idea-ledger 미변경(비파괴 — {OUT}에만 기록)
    cmap = AI_build_saturation_map(AI_load_consumed_ledger(ledger_path))
    raw  = AI_generate_with_overlay(insights_path, cmap)   # CIX 생성 + steering_overlay
    kept = [i for i in raw if not AI_reject_obvious_plus(i, cmap)["rejected"]]
    scored = [AI_score_6axis(i) for i in kept]             # CIX 정본
    return AI_select_topK_white_space_floor(scored, cmap, floor=WHITE_SPACE_FLOOR)
```

---

## 출력 스키마

CIXX `idea_pool.yaml`은 **CIX idea_output 스키마를 그대로** 따른다(다운스트림 EVX 무변경 소비).
각 아이디어에 CIXX 메타 2필드만 부착:

```yaml
# ... CIX idea 전 필드 (id, title, lens_application, domains, rejection_check, semantic_family, ...) ...
  cixx_category: {domain: "...", mechanism: "...", is_white_space: true}
  category_saturation: 0.NN     # 소모-카테고리 의미 overlap (낮을수록 신규 카테고리)
```

### reports/category_coverage_v{N}.md

```markdown
## CIXX category coverage — <UTC>
- 소모 ledger: 39 (구현 24 + derivative 15)
- OVERUSED 메커니즘: compatibility-mesh (0.36) ← white-space 강제 발동
- saturated 셀: [(Robotics, compatibility-mesh), (AI Operations, compatibility-mesh), ...]
- 생성 top-K: 24 | white-space 비율: 0.58 (floor 0.40 통과)
- 신규 메커니즘 유입: signal-exchange ×3, operating-exchange ×2, <novel> ×4
```

---

## 사용법

```bash
# 소모-카테고리 포화 맵만 빌드 (결정론)
/cixx map --ledger=.idea-ledger/consumed_ideas.yaml
#   → .cixx/category_map.yaml (또는 --out)

# white-space 조향 생성 (IDX latest 입력, CIX 정본 렌즈)
/cixx steer --insights=.idx/latest/insight_layered_traced.yaml --out=.cixx/round0609

# 결과를 CIX latest로 승격해 EVX 연계 (운영 단계, 승인 후)
#   .cixx/round0609/idea_pool.yaml → .cix/latest/ (또는 새 .cix round로 emit)
```

`--out` 정규화·`{OUT}/.work/`·동시실행 격리는 SDX/SDXX v1.4 규칙 동일 (기본 `{OUT}` = `.cixx/`).

## 멀티 에이전트 + 통합 (SDXX와 동형)

여러 에이전트가 같은 `category_map`을 공유하되 서로 다른 white-space 셀/렌즈 그룹을 분담 →
각자 `--out=.cixx/shards/agent-N/` 생성 → idea_pool 병합(중복 카테고리 dedup) → top-K 재선택.
포화 맵 공유로 모든 에이전트가 동일 포화 셀을 회피하므로 산출은 모두 out-of-category.

## 파이프라인 통합 (AOX 내 위치)

```
... TCX → IDX → [CIX 생성] ...   (현재)
... TCX → IDX → [CIXX steer = CIX 생성 + 소모-카테고리 회피] → idea_pool → EVX → AOX ...   (적용)
```
- CIXX는 CIX를 **대체가 아니라 조향**한다. CIX 렌즈/6축/스키마 그대로, 생성 입력에 포화 맵만 추가.
- 출력이 CIX idea_pool 스키마라 **EVX/AOX 무변경**. EVX 정형 consumed 필터는 사후 안전망으로 유지.
- 비파괴: `.cixx/`에만 기록. `.cix/latest` 승격·`.idea-ledger` 기록은 기존 AOX 경로(승인 단계).

## 경계 / 신규성

- CIXX = **조향기**. 렌즈·평가·스키마의 소유자는 CIX, 소모 ledger의 소유자는 AOX. CIXX는 읽어서 조향만.
- 기존 CIX/EVX/AOX는 일절 수정하지 않는다(보존). 카테고리 포화 맵 + steering overlay + rejection 1축이 추가 레이어.

## 의존 스킬

- `cix` — 20 렌즈·6축·idea_output 스키마·rejection_check 정본 (읽기 전용 재사용)
- `pg` — PPR/Gantree notation (정본)
- `pgf` — design/execute framework, 멀티 에이전트 delegate
- 연계: `evx`(사후 consumed 필터), `aox`(ledger 소유·기록), `sdxx`(입력단 대칭 스킬)
