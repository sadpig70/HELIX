# S4: Adjacent Domain Borrow (인접 분야 차용)

## 원리
같은 도메인 내에서만 정보를 수집하면 시야가 좁아짐. **인접 분야가 사용하는 정보 인프라를 차용**하면 cross-domain 합성이 자연스러워짐.

## 매핑 예시

| 타겟 도메인 | 차용 인접 분야 |
|------------|---------------|
| 의료 | 농업(센서·기상), 군사(트리아지), 공중보건(역학) |
| 군사 | 게임(시뮬레이션), 영화(VFX), 스포츠(전술분석) |
| 금융 | 스포츠 베팅(확률), 기상예보(불확실성), 카지노(리스크) |
| 도시 | 개미·벌(군집), 면역계(분산방어), 신경망(라우팅) |
| 우주 | 심해(고압환경), 극지(생존), 등산(고소순응) |

## 프롬프트

```
타겟 도메인 D에 대해 다음을 수행하라:

1. D와 구조적으로 유사하지만 **분야가 다른** 5개 인접 분야 식별
   (단순 인접 X, 문제 구조의 동형성 기준)

2. 각 인접 분야 전문가들이 사용하는 정보 인프라 조사:
   - 어떤 저널을 읽는가
   - 어떤 컨퍼런스에 가는가
   - 어떤 데이터베이스를 쓰는가
   - 어떤 표준/규제를 따르는가
   - 어떤 비공식 채널(커뮤니티, 메일링리스트)이 있는가

3. 각 인접 분야당 ≥ 4개 채널 발굴 (총 ≥ 20개)

4. 각 채널에 대해:
   - 원래 분야
   - D에 적용 가능한 구조적 유사성
   - 직접 차용 가능 / 변환 필요 / 영감만 제공

조건:
- 5개 인접 분야 모두 분야간 거리가 멀 것 (예: 모두 IT 아님)
- 각 채널에 D로의 transfer 가능성 점수 포함

준수사항: 사용자의 연구/경력/역량은 완전히 배제.
영문으로 출력.
```

## 기대 발견 예시

- **AsktheBuilder/eHow** (건축 → 도시 인프라)
- **BoardGameGeek** (게임 디자인 → 인센티브 설계)
- **Climbing.com** (등산 → 우주 생존)
- **Stack Exchange Cooking** (요리 → 화학공정)
- **AmericanKennelClub** (사육 → 합성생물학 행동 패턴)

## 출력 스키마 (per candidate)

```yaml
candidate:
  source_strategy: "S4_adjacent_borrow"
  name: "BoardGameGeek Designer Diaries"
  url: "https://boardgamegeek.com/blogs"
  origin_domain: "game design"
  target_domain: "incentive mechanism design"
  structural_homology: "worker placement ≈ resource allocation"
  transfer_difficulty: "direct"  # direct / requires_translation / inspirational_only
```
