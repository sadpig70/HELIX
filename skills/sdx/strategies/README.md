# SDX 발굴 전략 카탈로그

> v1.1: 5개 전략별 파일로 분리. 이 파일은 인덱스.

## 전략 5개

| ID | 파일 | 핵심 메커니즘 | 기대 발굴 수 |
|----|------|--------------|------------|
| S1 | [01_reference_backtrack.md](./01_reference_backtrack.md) | 출처의 출처를 3단계까지 추적 | ≥30 |
| S2 | [02_cross_lingual_mirror.md](./02_cross_lingual_mirror.md) | 7개 비영어권 언어로 native search | ≥35 |
| S3 | [03_failure_archive.md](./03_failure_archive.md) | 사장된 기술·실패 표준 아카이브 | ≥20 |
| S4 | [04_adjacent_borrow.md](./04_adjacent_borrow.md) | 인접 분야의 정보 인프라 차용 | ≥20 |
| S5 | [05_weak_signal_hunt.md](./05_weak_signal_hunt.md) | niche newsletter, long-open issues | ≥25 |

총 후보 ~130개 → 중복 제거 + URL alive 검증 → ~120개 → 직교성 선택 → **80개 직교 기저**

## 공통 규칙

1. 사용자의 연구/경력/역량은 발굴 과정에서 완전 배제
2. 영문 출력 (IdeaFirst-MC와 일관성)
3. 각 후보에 4-Axis 셀 좌표 부착 (Temporal, Geographic, Format, Scale)
4. 출처 추적 가능 (어떤 검색에서 발견되었는지)

## 8개 AI 분배

각 전략이 독립 AI에 분배. 한 AI가 다 하면 같은 검색 패턴 회귀 편향.

- AI 1: S1 (Reference Backtrack)
- AI 2: S1 (cross-check, 다른 seed 사용)
- AI 3-4: S2 (Cross-Lingual Mirror, 언어 분담)
- AI 5: S3 (Failure Archive)
- AI 6: S4 (Adjacent Borrow)
- AI 7: S5 (Weak Signal)
- AI 8: 통합 + dedup
