# HELIX Architecture — 이중나선 → 시스템 (정정판)

> 이름 HELIX는 장식이 아니라 **설계 사양**이다. DNA 이중나선의 각 구성요소가 시스템 요소에
> 대응하며, "왜 폐루프인데 안 좁아지나"가 기하학에서 바로 읽힌다.

## 1. 매핑 표

| 나선 구성 | 시스템 요소 | 비고 |
|---|---|---|
| 가닥 A (sense strand) | **explore** = IdeaFirst (sdx→tcx→idx→cix→evx, aox) | 세계→아이디어 (outside-in) |
| 가닥 B (antisense strand) | **exploit** = recreate/ProjectGenome (corpus→seed) | 자산→seed (inside-out) |
| **역평행 (antiparallel)** | A=outside-in, B=inside-out | 두 가닥이 반대 방향 — 은유 강화 포인트 |
| 백본 (backbone) | **HELIX-Core**: ledger·diversity·provenance·fingerprint·loop | 두 가닥을 묶는 단일 기반층 (불변항) |
| **염기쌍 결합 (base-pairing)** | **winner→corpus 환류 + 공유 ledger** | ★가닥을 *잇는* 결합 (정정: pgf 아님) |
| 전사/번역 (transcription) | final_idea / DesignSeed → pgf full-cycle | 가닥에서 *나오는* 산물 |
| 복제 (replication) | 새 프로젝트 산출 (자가증식) | pgf 위임 |
| **복구효소 (repair enzyme)** | 5점 다양성 게이트 | ★세대 퇴화(동질화) 방지 (정정: pitch보다 정확) |
| 나선 상승 (pitch/rise) | 회전마다 폭 유지 → 수렴 없이 전진 | 폐루프 ≠ 원 |

## 2. 두 가지 정정 (초기 제안 대비)

설계 검토에서 잡은 두 가지를 반영했다:

1. **base-pairing 재배치.** DNA에서 염기쌍 결합(A-T)은 *두 가닥을 묶는 가닥-간 결합*이다.
   따라서 이를 `pgf 핸드오프`(하류 산물)가 아니라 **엔진 간 결합 = winner→corpus 환류 +
   공유 ledger**에 매핑한다. pgf 핸드오프는 가닥에서 *나오는* 것이므로 **transcription**에 둔다.
2. **복구효소 추가.** 나선이 세대를 거듭해도 퇴화하지 않는 건 DNA repair/proofreading 덕이다.
   5점 다양성 게이트가 정확히 그 역할이므로 "pitch" 비유보다 **복구효소**가 정확하다.

## 3. 역평행 (antiparallel) — 보너스 정합

- 가닥 A(explore)는 **outside-in**: 무한한 외부 세계 → 한 점(final_idea)으로 수축.
- 가닥 B(exploit)는 **inside-out**: 유한한 내부 자산 → 새 조합으로 팽창.
- 두 흐름이 반대 방향(antiparallel)이라는 점이 이중나선과 정확히 맞는다. 이 반대 방향성이
  서로의 약점을 메운다: A는 신선하나 1회적, B는 누적되나 근친교배 위험 → 합치면 상쇄.

## 4. 5점 다양성 게이트 (복구효소의 실제 위치)

```text
입력          인사이트        출력카테고리      재조합          평가
 │              │              │              │              │
sdxx ──────► idxx ──────► cixx ──────► recreate ──────► cross-model
(채널)        (인사이트)     (아이디어)     avoidance       consensus
 └──── explore 측 입력 게이트 ────┘   └ exploit 측 ┘   └ 공통 ┘
        ▲ 모두 HELIX-Core.measure_diversity 의 신호로 트리거됨 (단일 측정)
```

게이트 *판단/실행*은 각 엔진에 있지만, *측정*은 백본이 단일 함수로 제공한다 → desync 없음.

## 5. 왜 원이 아니라 나선인가 (가치 명제의 기하학)

```text
원(circle)   = 환류하지만 같은 자리로 회귀 → 동질화·근친교배로 수렴
나선(helix)  = 환류 + 전진 = 백본(desync 제거) × 복구효소(폭 유지) × antiparallel(상호보완)
             → 폐루프인데 출력이 수렴하지 않는 유일한 구조
```

이 세 요소(백본·복구효소·역평행)가 함께 있을 때에만 "닫혔으나 좁아지지 않음"이 성립한다.
HELIX-Core는 그 세 요소를 코드로 구현한 백본이다.

## 6. 설계 불변식 — 백본 중심 (가닥 수 무관)

이중나선은 가닥 *2개*의 이미지이지만, HELIX의 **불변항은 가닥 수가 아니라 백본**이다.
"공유 백본이 상보 가닥들을 묶어 수렴 없이 전진한다"는 명제는 가닥이 몇 개든 유지된다 —
삼중나선(collagen)도 생물에 실재하고, explore 소스가 3+로 늘어도 `core/helix_loop`의 드라이버는
가닥 목록을 받아 라운드를 배분할 뿐이다. 즉 은유는 2가닥에서 가장 선명하나, 아키텍처는
**N가닥으로 확장 가능**하며 백본(`core/`)만 단일 출처로 유지하면 된다. (가닥 추가 = 어댑터 추가.)
