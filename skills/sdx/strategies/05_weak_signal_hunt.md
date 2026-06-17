# S5: Weak Signal Hunt (약신호 사냥)

## 원리
주류 미디어에 도달하기 전의 정보. **트래픽 낮음, 인덱싱 안 됨, 비공개 그룹**일수록 LLM 훈련 데이터에 적게 포함되어 신호 차별성 높음.

## 프롬프트

```
다음 약신호 소스를 탐색하라:

1. Niche newsletters (Substack, Patreon, Ghost):
   - 구독자 < 10,000 이지만 분야 전문가가 운영
   - 각 분야당 ≥ 3개

2. Long-open GitHub Issues:
   - opened > 1 year, comments > 20, unresolved
   - 실제 사용자 pain point 노출

3. Stack Overflow unanswered:
   - votes > 100, answers = 0
   - 미해결 기술 갭

4. Discord/Slack public servers:
   - 분야 전문 커뮤니티 (Drone Racing, Synthbio, Retro Computing 등)
   - 공개 채널 + invite link 가능한 것

5. Mailing lists:
   - LWN, RIPE NCC, ICANN, IETF working group
   - 활성 (최근 30일 < 20 posts 이상)

6. 비공개에 가까운 아카이브:
   - Internet Archive special collections
   - 대학 연구실 internal report 공개분
   - 정부 FOIA 공개 문서

각 채널에 대해:
- URL / invite link
- 활성도 점수 (게시 빈도)
- 분야
- 검색 엔진 가시성 (낮을수록 좋음)

조건:
- ≥ 25개 후보
- "구글 검색 1페이지에 안 나오는" 것 우선

준수사항: 사용자의 연구/경력/역량은 완전히 배제.
영문으로 출력.
```

## 기대 발견 예시

- **LWN.net** (Linux kernel weekly)
- **Bunnie Huang's blog**
- **Drew DeVault's blog**
- **Long-form Substacks** (Construction Physics, Slime Mold Time Mold)
- **Amateur radio digests**
- **Hacker News "Ask HN" archives**

## 출력 스키마 (per candidate)

```yaml
candidate:
  source_strategy: "S5_weak_signal"
  name: "Construction Physics"
  url: "https://www.construction-physics.com/"
  signal_type: "niche_substack"
  metrics:
    subscriber_count_approx: 30000
    posting_frequency: "weekly"
    search_visibility: "low"  # 구글 1페이지 미노출
    expert_run: true
  field: "construction industry analysis"
```
