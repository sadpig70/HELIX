# IDXX Steering Overlay (인사이트 조향 오버레이)

> IDX 증류 프롬프트(layer 도출·evidence trace, **정본·수정 금지**)에 **append**되는 조향절.
> 증류를 *시작하기 전부터* 이미 *구현된* 인사이트 테마를 회피하고 under-distilled로 유도.
> `mode_steer`가 [IDX 증류 프롬프트] + [이 오버레이] 를 합쳐 실행한다.

## 프롬프트 (IDX 증류 프롬프트 끝에 추가)

```
=== 인사이트 조향 (IDXX) ===

아래는 *이미 구현된*(소모 아이디어 → source_insight provenance walk로 역추적) 인사이트 테마의
포화 맵이다 (입력 insight_saturation_map):

BUILT-UPON 인사이트 테마 (이미 프로젝트로 구현됨 — 재증류 강등):
{built_upon_insights}

BUILT-UPON 토픽:
{built_upon_topics}

여러 IDX 라운드에 반복된 토픽 (over-distilled 경향):
{recurring_topics}

layer 분포 history:
{layer_distribution_history}

증류 시 다음을 지켜라:

1. BUILT-UPON 테마와 *같은 (토픽 × layer)* 인사이트를 다시 증류하지 마라.
   이미 무언가 만들어진 인사이트를 또 뽑는 것은 낭비다 (예: "agentic AI × accountable-ops gap"은
   agentmesh로 구현됨 → 재증류 금지).

2. ★ covered ≠ forbidden: BUILT-UPON *토픽*이라도 **다른 layer/tension/각도**면 허용·장려.
   거대트렌드 전체를 막지 말고 (토픽 × layer) 단위로만 강등하라.
   예) agentic AI를 L7 Tension·L9 Counterfactual의 *다른 각도*로 보는 것은 환영.

3. under-distilled를 적극 겨냥하라 (증류의 첫 질문 = "포화 맵에 없는 인사이트는 무엇인가?"):
   - 시끄러운 거대트렌드에 묻힌 **약신호(weak-signal)** 인사이트.
   - 둘 이상 트렌드를 잇는 **교차트렌드(cross-trend)** 인사이트.
   - history에서 under-used인 layer를 의도적으로 채워라(단, IDX layer floor는 유지).

4. ★★ EVIDENCE-FLOOR (절대 규칙 — IDXX 고유):
   반복을 피하려고 **증거가 약한 패턴을 인사이트로 승격하지 마라.**
   모든 출력 인사이트는 IDX 정본 evidence trace(source_tcx_items + quote + hash/span/confidence)를
   *그대로* 충족해야 한다. 조향은 **증거-추적된 후보 안에서 순서·가중을 바꾸는 것**일 뿐,
   증거 없는 신규를 만들어내는 것이 아니다. 증거 미달이면 under-distilled라도 버려라.

5. 각 인사이트에 부착하라:
   - idxx_steering: {built_upon_overlap, is_under_distilled, demoted}
   - 단, evidence/source_tcx_items/trace_summary 등 IDX 증거 필드는 *변경 없이* 그대로 둔다.

조건 충돌 시 우선순위: [EVIDENCE-FLOOR] > [under-distilled 조향] > [증류 수량].
증거를 희생해 신규성을 얻지 마라.
```

## 적용 메모

- `{built_upon_insights}/{built_upon_topics}/{recurring_topics}/{layer_distribution_history}` 는
  `scripts/build_insight_saturation_map.py` 산출(`insight_saturation_map.yaml`)로 치환된다.
- 이 오버레이는 증류 *steering*일 뿐, 최종 보증은 `AI_reweight_with_evidence_floor`
  (evidence-floor 거부 + built-upon 강등)와 `AI_select_layer_floor_and_under_distilled`가 한다.
- EVX 정형 consumed 필터는 그대로 사후 안전망 (삼중 방어: IDXX 증류조향 + CIXX 생성조향 + EVX 정형).
- ★ 셋 중 IDXX가 가장 섬세 — evidence-floor가 forced-novelty(노이즈 승격)를 막는 마지막 가드다.
