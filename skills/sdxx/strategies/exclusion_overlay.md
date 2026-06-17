# SDXX Exclusion Overlay (배제 오버레이)

> SDX 5전략 프롬프트(`sdx/strategies/01~05_*.md`, **정본·수정 금지**)에 **append**되는 배제절.
> 발굴을 *시작하기 전부터* 보유 채널 영역을 피하게 만드는 pre-discovery steering.
> 각 `AI_explore_*_excl` 함수가 [SDX 전략 프롬프트] + [이 오버레이] 를 합쳐 실행한다.

## 프롬프트 (각 전략 프롬프트 끝에 추가)

```
=== 배제 조건 (SDXX) ===

아래는 우리가 *이미 보유한* 채널들의 식별 다이제스트다 (입력 exclude_known):

{exclude_known_digest}
  # 채널당: name · url_host · publisher_group · primary_domain · axis_cell · language

발굴 시 다음을 엄격히 지켜라:

1. 위 목록의 채널(또는 그와 사실상 같은 소스)을 후보로 등재하지 마라.
   - "사실상 같은 소스" 판정 = 다음 중 하나라도 충족:
     · url_host 동일 (도메인이 같으면 경로가 달라도 같은 소스)
     · publisher_group 동일 + primary_domain 동일
     · 같은 4-Axis 셀(axis_cell) + 같은 도메인
   즉 *이름이 달라도* 같은 발행 주체/도메인/축이면 제외한다.

2. 단순히 목록을 피하는 데 그치지 말고, **목록에 없는 publisher_group · 도메인 · 4-Axis 셀**을
   적극적으로 겨냥하라. "이미 가진 것과 다른 곳은 어디인가?"를 발굴의 첫 질문으로 삼아라.

3. exclude_known이 점유한 영역의 *인접·미점유* 영역을 우선한다:
   - 같은 주제라도 보유 채널과 다른 언어권/지역(geographic)·다른 포맷(format)·
     다른 시간축(temporal)·다른 규모(scale)의 1차 소스를 찾아라.
   - 보유가 비어 있는 4-Axis 셀(입력 known_coverage의 빈 셀)을 메우는 후보에 가중.

4. 각 후보에 다음 필드를 추가로 부착하라:
   - novelty_vs_known: 보유 집합 대비 무엇이 다른가 (1줄: 다른 지역/포맷/주체/축 명시)
   - nearest_known: 가장 가까운 보유 채널과 그 차이 (없으면 "none")

조건 충돌 시 우선순위: [배제 조건] > [원 전략의 발굴 목표 수량].
즉 수량을 채우려고 보유 채널을 재등재하지 마라 — 모자라면 모자란 대로 두고 사유를 남겨라.
```

## 적용 메모

- `{exclude_known_digest}` 는 `AI_build_known_digest(known)` 산출(경량 식별키)로 치환된다.
  8축 메트릭 전체를 넣지 않는다(프롬프트 비대화 방지).
- 카탈로그가 크면(예: 175개) digest를 publisher_group·domain·axis_cell 기준으로 **그룹 요약**해
  토큰을 줄일 수 있다 (개별 채널 나열 대신 "보유 점유 영역" 요약). 단 url_host 목록은 유지(정확 배제).
- 이 오버레이는 발굴 *steering*일 뿐, 최종 배제는 `AI_is_known`(overlap 피처)과
  `AI_select_orthogonal_vs_known`(사후 직교 선택)이 이중으로 보증한다.
