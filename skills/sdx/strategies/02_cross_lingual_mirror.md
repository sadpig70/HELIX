# S2: Cross-Lingual Mirror (언어 횡단)

## 원리
영어 검색은 영미권 채널을 우선 노출. 비영어권 1차 자료는 모국어로만 검색해야 도달 가능.

## 대상 언어 (7개)

| 언어 코드 | 지역 | 우선 분야 |
|---------|-----|---------|
| zh-CN | 중국 본토 | AI, 양자, 신소재, 학술 전반 |
| ja | 일본 | 소부장, 로봇, 정밀공학 |
| ru | 러시아 | 군사, 우주, 재료공학 |
| hi | 인도 | 적정기술, ICT4D, 농업 |
| es | 스페인/라틴아메리카 | 농업, 자원, 신흥시장 |
| pt-BR | 브라질 | 자원, 농업, 핀테크 |
| ar | 중동·북아프리카 | 에너지, 사막 기술 |

## 프롬프트

```
입력 주제 X에 대해 다음을 수행하라:

1. X를 7개 언어로 정확히 번역 (영어 음차 금지, 현지 용어 사용)
2. 각 언어로 native search 실행:
   - 학술: 중국=CNKI/万方, 일본=CiNii, 러시아=eLibrary, 인도=Shodhganga
   - 정부: 각국 정부 도메인 (.gov.cn, .gov.ru, .gov.in 등)
   - 산업: 각국 주요 산업 협회 사이트
   - 미디어: 각 언어권 1차 미디어 (영문판 아닌 본문)
3. 각 언어에서 ≥ 5개 채널 발굴 (총 ≥ 35개)
4. 각 채널에 대해:
   - 원어 명칭 + 영문 번역
   - URL
   - 영어로 접근 가능한지 여부
   - 영미권 미디어 인용도 (낮을수록 좋음)

조건:
- 7개 언어 모두 커버
- 영문판 mirror가 있는 채널은 우선순위 낮춤 (이미 영미권으로 흘러간 정보)

준수사항: 사용자의 연구/경력/역량은 완전히 배제.
출력은 영어 + 원어 병기.
```

## 기대 발견 예시

- **中国知网 (CNKI)** — 중국 학위논문 1차
- **J-STAGE** — 일본 학회지 통합
- **eLibrary.ru** — 러시아 학술
- **Redalyc** — 라틴아메리카 학술
- **Shodhganga** — 인도 학위논문
- **각 국가 특허청** 데이터베이스 (CNIPA, JPlatPat, FIPS)

## 출력 스키마 (per candidate)

```yaml
candidate:
  source_strategy: "S2_cross_lingual"
  name_original: "中国知网"
  name_english: "China National Knowledge Infrastructure"
  url: "https://kns.cnki.net/"
  language: ["zh-CN"]
  english_mirror: false
  us_eu_citation_rate: "low"  # 영미권 미디어 인용도
  access_tier: "tier_4_institutional"
```
