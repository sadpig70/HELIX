# COMPLETENESS-HELIX — 경계 해소 (pgf analyze → resolve)

> 목표: README "정직한 경계"의 *고백*을 *해소*로 바꿔 프로젝트 완전성을 올린다.
> 방법: pgf `design --analyze`로 각 경계의 실제 근거를 조사 → 해소 작업 설계·실행·검증.

## 분석 → 해소 매핑

| # | 경계(고백) | 분석 결과(사실) | 해소(실행) | 상태 |
|---|---|---|---|---|
| C1 | pgf 양 트리 분기 — 한쪽 채택, "저위험" | explore 스킬 pgf 기계의존 = `personas.json` **1개뿐, 동일**. persona `.md` 기계로드 0 → 차이는 prose-only | 의존성 폐쇄 검증 + `MIGRATION.md §1`에 재현명령 기록 → "검증된 무영향" | ✅ |
| C2 | 임베딩 임계 "차용값, 재보정 대상" | `measure_diversity`가 이미 `thresholds` override 지원. 빠진 건 provenance·절차 | `docs/CALIBRATION.md`(출처표 + `calibrate_thresholds` 절차) + README override 명시 | ✅ |
| C3 | `sim=None` → partial(부분 신호) | partial은 임베딩 미주입 시 sim 신호 누락 | `lexical_sim`(Jaccard, 결정론 stdlib) 기본 탑재 → 항상 완전 report. `sim_kind∈{lexical,semantic}` | ✅ |
| C4 | 이중나선 은유 2가닥 한정 | 불변항은 가닥 수가 아니라 백본 | `ARCHITECTURE §6` 백본중심 = N가닥 확장 가능(어댑터 추가) | ✅ |
| C5 | "패키징은 융합/로직 단일출처" 캐비엇 | 사실상 설계 진술 | README "설계 불변식"으로 사실화 | ✅ |

## 변경 산물

- `core/helix_diversity.py`: `lexical_sim` 추가, `measure_diversity` 기본 sim=lexical, `partial`→`sim_kind`
- `core/__init__.py`·`schemas/diversity-report.schema.json`·`helix.py`·`docs/SUBSTRATE-CONTRACT.md`: sim_kind 일관화
- `docs/CALIBRATION.md`(신규), `docs/ARCHITECTURE.md §6`(신규), `MIGRATION.md §1`(검증 기록)
- `README.md`: "정직한 경계" → "설계 불변식 & 확장점"(사실) + non-goals
- `tests/test_diversity.py`: lexical 기본·sim_kind·lexical_sim 테스트 추가

## 검증 게이트

- unittest: 66 pass · 결정론 2회 동일
- `helix_validate`: PASS (19 스킬 인벤토리 + personas)
- driver: `sim=lexical` 완전 신호
- 잔재 `partial` 참조 0

## 남은 non-goals (결함 아님 — 의도된 경계)

- 임베딩 모델 자체 미동봉 → 주입 인터페이스(`sim`)로 제공(결정론 경계 보존).
- 시장 수요·상업성 판정은 엔진 평가층 소관(백본 범위 밖).
