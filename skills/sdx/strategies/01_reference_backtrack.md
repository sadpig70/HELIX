# S1: Reference Backtrack (역추적)

## 원리
좋은 자료의 출처를 재귀적으로 따라가면 결국 1차 소스에 도달. 그 1차 소스가 어디서 출판되었는지가 새 채널 후보.

## 프롬프트

```
다음 작업을 수행하라:

1. 입력으로 받은 seed 자료 N개의 reference/citation/footnote를 모두 추출
2. 추출된 출처를 다시 검색해서 그 출처의 출처를 추적 (depth 3까지)
3. depth 3에서 도달한 출판처/저널/아카이브/플랫폼을 채널 후보로 등재
4. 각 채널 후보에 대해:
   - 출판처 명칭
   - URL 패턴
   - 1차 자료 여부 (1차/2차/3차)
   - 영미권 외 여부
   - 추적 경로 (어떤 seed에서 출발했는지)

조건:
- 최소 30개 후보
- 영미권 외 ≥ 30%
- Wikipedia, 일반 뉴스, blog는 제외 (1차 자료 우선)

준수사항: 사용자의 연구/경력/역량은 완전히 배제.
영문으로 출력.
```

## 기대 발견 예시

- 박물관 디지털 아카이브 (Smithsonian, Cooper Hewitt)
- 학회 워크숍 proceedings (메이저 학회 부설)
- 대학 technical report series
- 정부 백서 (각국 산업부 발간)
- Foundation reports (Pew, McKinsey Global Institute)

## 출력 스키마 (per candidate)

```yaml
candidate:
  source_strategy: "S1_reference_backtrack"
  name: "..."
  url: "..."
  classification:
    primary_secondary_tertiary: "primary"
    region: "non_US_EU"
  trace_path:
    seed: "Bloomberg article on PQC"
    depth_1: "MIT Tech Review citation"
    depth_2: "NIST whitepaper reference"
    depth_3: "ISO standard document (DESTINATION)"
```
