# SDX-CI Cross-Agent Report — union (전체 5소스 통합)

- **실행**: 2026-06-02 · `sdx_ci union` · 출력 `.sdx/catalog/` (TCX 기본 입력 경로)
- **입력**: 5소스 — `.sdx_org/{catalog, chatgpt, gemini, grok, kimi}` (원본은 `.sdx_org/`에 보존)
- **모드**: union (URL canonical dedup, 직교 재선택 없음 — 최대 풍부)

## 요약
| 항목 | 값 |
|---|---|
| 제출 합계 | **317** (catalog 100 + chatgpt 80 + gemini 80 + grok 7 + kimi 50) |
| dedup union | **175** |
| 중복 제거 | 142 |
| global_redundancy | **0.448** (warn ≥ 0.40 초과) |
| lock_eligible | **true** (required_coverage 8/8·10/10·5/5·3/3 전항 PASS) |
| **verdict** | ⚠️ **diversify_recommended** |

## 소스별 기여
| source | submitted | unique_to_source |
|---|---|---|
| catalog (운영 100ch) | 100 | **39** |
| chatgpt | 80 | 12 |
| gemini | 80 | **3** |
| grok | 7 | 4 |
| kimi | 50 | **34** |

- **catalog(39)·kimi(34)**가 고유 기여 최다 — 통합 다양성의 실질 축. catalog의 비영미권 expand 채널들이 대거 고유.
- **gemini(3)**: chatgpt(0.72)+catalog(0.452) 양쪽과 중복 심해 고유 기여 최소.

## Pairwise Jaccard (url 겹침)
|         | catalog | chatgpt | gemini | grok | kimi |
|---------|---------|---------|--------|------|------|
| catalog |   —     | 0.343   | 0.452  | 0.03 | 0.10 |
| chatgpt | 0.343   |   —     | **0.72** | 0.00 | 0.10 |
| gemini  | 0.452   | **0.72** |   —    | 0.00 | 0.10 |
| grok    | 0.03    | 0.00    | 0.00   |  —   | 0.02 |
| kimi    | 0.10    | 0.10    | 0.10   | 0.02 |  —   |

- **chatgpt↔gemini = 0.72** 여전히 최고 — 두 산출물이 거의 동일(분산 발굴 실패 지점).
- catalog는 chatgpt/gemini와 0.34~0.45 중복(공통 베이스 소스), grok/kimi와는 거의 직교.

## format 분포 (175)
niche 36 · paper 27 · nature 23 · gov 20 · news 17 · std 15 · oss 12 · patent 12 · vc 7 · conf 6 (10/10)

## ⚠️ 데이터 품질 이슈 (정직 보고)
1. **grok 73채널 누락**: index는 80 주장, 실제 파일 7채널만 → 통합엔 7개만. grok 정상 재산출 시 재통합 권장.
2. **비표준 geo 셀 `global`**: 일부 외부 AI 산출물이 `geographic: "global"`(SDX axis enum 8셀에 없음) 사용. coverage 8/8 판정엔 무영향(표준 8셀 별도 충족)이나, TCX axis 참조 시 미정의 셀로 처리될 수 있음 → 정규화 권장.

## TCX 계약 적합성 (.sdx/catalog)
| 체크 | 결과 |
|---|---|
| consistency_check (abort) | ✅ PASS (175==175) |
| shard_completeness (abort) | ✅ PASS (10 shard 실재) |
| lock_check | ✅ PASS (lock_eligible true) |
| policy_compatibility | ✅ PASS (sdx-1.5) |
| required_keys | ⚠️ `basis` 생략 (union 직교 미계산 — non-fatal WARN) |

## 권고
- 본 union(175)은 TCX 입력으로 사용 가능(abort 조건·lock 모두 PASS).
- 다음 라운드: chatgpt/gemini 중복(0.72) 해소를 위한 분담 + grok 정상 재산출 + `global` 셀 정규화.
- 직교 기저가 필요하면 추후 `integrate` 모드(전역 8축 재계산)로 175→직교 재선택.

---
*union 산출물: `.sdx/catalog/{index.yaml, channels/{format}.yaml, pool/union_pool.yaml}` · 원본 보존: `.sdx_org/`*
