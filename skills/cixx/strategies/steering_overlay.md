# CIXX Steering Overlay (카테고리 조향 오버레이)

> CIX 생성 프롬프트(렌즈 적용·seed 생성, **정본·수정 금지**)에 **append**되는 조향절.
> 생성을 *시작하기 전부터* 소모된 카테고리(도메인×메커니즘)를 회피하고 white-space로 유도.
> `mode_steer`가 [CIX 생성 프롬프트] + [이 오버레이] 를 합쳐 실행한다.

## 프롬프트 (CIX 생성 프롬프트 끝에 추가)

```
=== 카테고리 조향 (CIXX) ===

아래는 *이미 소모된*(구현 또는 derivative-제외) 아이디어 카테고리의 포화 맵이다 (입력 category_map):

OVERUSED 메커니즘 (소모 전체의 ≥30% 점유 — 강하게 회피):
{overused_mechanisms}

SATURATED 셀 (도메인×메커니즘 ≥3회 소모 — 재생성 금지):
{saturated_cells}

메커니즘 점유율:
{mechanism_share}

이미 발행된 프로젝트 (참고):
{published_projects}

생성 시 다음을 지켜라:

1. SATURATED 셀의 (도메인×메커니즘) 조합으로 아이디어를 만들지 마라.
   특히 OVERUSED 메커니즘(예: compatibility-mesh)을 *기존 도메인*에 다시 적용하는 것은 금지.
   ── "또 Compatibility Mesh를 X도메인에" 패턴이 바로 동질화의 원인이다.

2. ★ covered ≠ forbidden: 포화 *도메인*이라도 **메커니즘이 진짜 다르면 허용·장려**.
   예) Robotics×compatibility-mesh = 금지(robotrace), 그러나 Robotics×<다른 메커니즘> = 환영.
   도메인 전체를 막지 말고 (도메인×메커니즘) 셀 단위로만 회피하라.

3. white-space를 적극 겨냥하라 (생성의 첫 질문 = "소모 맵에 없는 칸은 어디인가?"):
   - underused/신규 메커니즘을 우선 적용 — OVERUSED가 아닌 렌즈 그룹(CIX 4그룹)을 의도적으로 다양화.
   - 미커버 (도메인 × underused-메커니즘) 셀을 채우는 아이디어에 가중.
   - ledger에 전혀 없는 *새 메커니즘 형태*(신규 렌즈 조합)를 탐색하라.

4. 각 아이디어에 다음을 부착하라:
   - cixx_category: {domain, mechanism, is_white_space}
   - category_saturation: 소모 맵 대비 (도메인×메커니즘) 의미 overlap 추정 (0-1, 낮을수록 신규)
   - novelty_vs_consumed: 소모된 것과 무엇이 다른가 (1줄: 다른 메커니즘/도메인/셀 명시)

조건 충돌 시 우선순위: [카테고리 조향] > [생성 수량].
수량을 채우려고 포화 셀을 재생성하지 마라 — 모자라면 모자란 대로 두고 사유를 남겨라.
단, CIX의 렌즈 추적성(lens_application_traceable)·6축 품질 기준은 그대로 충족해야 한다.
```

## 적용 메모

- `{overused_mechanisms}/{saturated_cells}/{mechanism_share}/{published_projects}` 는
  `scripts/build_category_map.py` 산출(`category_map.yaml`)로 치환된다.
- 이 오버레이는 생성 *steering*일 뿐, 최종 배제는 `AI_reject_obvious_plus`(CONSUMED_CATEGORY_SATURATED)와
  `AI_select_topK_white_space_floor`(white-space 비율 하한)가 이중 보증한다.
- EVX 정형 consumed 필터는 그대로 사후 안전망으로 둔다(삼중 방어: 사전조향 + 의미rejection + 정형EVX).
