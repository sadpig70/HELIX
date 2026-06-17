# S3: Failure & Death Archive (실패·사장 탐색)

## 원리
성공한 기술/표준만 보면 미래 예측은 항상 현재의 확장. 사장된 기술·실패한 표준에는 **미해결 문제와 미답 질문**이 남아있어 새로운 합성 재료가 됨.

## 프롬프트

```
도메인 D에 대해 다음을 수행하라:

1. 다음 검색 패턴 적용:
   - "abandoned {D} technology"
   - "deprecated {D} standard"
   - "failed {D} startup"
   - "killed by {D}" / "{D} killed by"
   - "withdrawn {D} patent"
   - "obsolete {D} protocol"
   - "discontinued {D} project"

2. 발견된 실패 사례의 아카이브/추모 사이트/회고록을 채널로 등재:
   - Failory, Killed by Google, Killed by Microsoft
   - IETF datatracker (obsolete RFCs)
   - IEEE withdrawn standards
   - Wikipedia "abandoned X" categories
   - Pitch graveyard, VC "why we passed" posts

3. 각 채널에 대해:
   - 사망 시점·원인
   - 해결되지 않은 채 남은 질문
   - 재부활 가능 조건 (기술/시장/규제 변화)

조건:
- ≥ 20개 후보
- 각 후보에 "왜 사장되었는가" 명시
- 단순 obituary 아카이브 제외, 분석적 아카이브 우선

준수사항: 사용자의 연구/경력/역량은 완전히 배제.
영문으로 출력.
```

## 기대 발견 예시

- **IETF Deprecated RFCs** (e.g., RFC 793 → 9293)
- **Computer History Museum** (사장된 아키텍처)
- **Long Now Foundation Archive**
- **Mars Failed Missions Database** (NASA)
- **ClinicalTrials.gov terminated trials**
- **EUR-Lex withdrawn directives** (EU 법안)

## 출력 스키마 (per candidate)

```yaml
candidate:
  source_strategy: "S3_failure_archive"
  name: "IETF Deprecated RFCs"
  url: "https://datatracker.ietf.org/doc/search?status=obsolete"
  death_metadata:
    death_year: "varies"
    primary_cause: "technical obsolescence"
    unanswered_question: "왜 이 디자인 선택이 실패했나"
    revival_condition: "양자 컴퓨팅 도래 시 일부 부활 가능성"
```
