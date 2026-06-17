# PGFR-COMBO: Atom Extraction Template

기존 프로젝트를 재조합 가능한 단위(Atom)로 분해할 때 사용하는 템플릿.

## Atom Structure

```yaml
project:
  name: ""
  folder: ""
  readme_summary: ""      # 1문장 요약
  problem_statement: ""   # 풀고자 하는 핵심 문제

atoms:
  - name: "mechanism-name"
    type: mechanism       # mechanism | asset | infra | constraint
    description: ""
    inputs: []
    outputs: []
    depends_on: []
    reusable_score: 1-10  # 다른 프로젝트에서 재사용하기 쉬운 정도
    maturity: prototype | mvp | stable

assets:
  code: []                # 핵심 파일/모듈
  schemas: []             # YAML/JSON 스키마
  specs: []               # 문서화된 스펙
  cli_tools: []           # 명령줄 도구
  tests: []               # 테스트/검증 도구

infra:
  assumptions: []         # 의존하는 외부 시스템/라이브러리
  crypto: []              # 사용하는 암호/증명 메커니즘
  storage: []             # 데이터 저장 방식
  network: []             # 네트워크/통신 방식

domain:
  primary: ""             # 예: energy, finance, robotics, bio, ai-governance
  secondary: []           # 교차 도메인
  jurisdiction: []        # 지역/규제 범위

strategic:
  uniqueness: ""          # 이 프로젝트만의 차별점
  openness: 1-10          # 외부 프로젝트와 연결하기 쉬운 정도
  risk: 1-10              # 기술/시장/규제 리스크
```

## Extraction Prompt

각 프로젝트 README/DESIGN을 읽고 다음 질문에 답한다:

1. 이 프로젝트가 푸는 **가장 작은 핵심 문제**는 무엇인가?
2. 그 문제를 푸는 **메커니즘**은 무엇인가? (3개 이내)
3. 이 메커니즘의 **입력과 출력**은 무엇인가?
4. 다른 프로젝트에서 **재사용할 수 있는 부분**은 무엇인가?
5. 이 프로젝트가 **의존하는 인프라**는 무엇인가?
6. 이 프로젝트의 **도메인 경계**는 어디까지인가?

## Example: ADPR Atom

```yaml
project:
  name: "ADPR"
  folder: "ADPR"
  readme_summary: "AI-bio design provenance registry"
  problem_statement: "AI-designed biological constructs의 설계-to-배포 이력을 검증할 수 없다"

atoms:
  - name: "attestation-envelope"
    type: mechanism
    description: "{model, dataset, parameters, instructions, construct id}를 포함하는 해시 봉투"
    inputs: ["construct metadata"]
    outputs: ["content hash"]
    depends_on: []
    reusable_score: 8
    maturity: mvp
  - name: "transparency-log"
    type: mechanism
    description: "Sigstore-Rekor-class inclusion proof를 제공하는 추가 전용 로그"
    inputs: ["content hash"]
    outputs: ["attestation token"]
    depends_on: ["attestation-envelope"]
    reusable_score: 9
    maturity: prototype

assets:
  code: ["tools/attest_envelope.py", "tools/rekor_stub.py"]
  schemas: ["spec/data_schema.yaml"]
  specs: ["spec/attestation_envelope_spec.md"]
  cli_tools: ["attest_envelope", "rekor_stub"]
  tests: []

infra:
  assumptions: ["Python 3.10+", "std-lib only"]
  crypto: ["content hash", "digital signature", "inclusion proof"]
  storage: ["append-only log"]
  network: []

domain:
  primary: "bio-regulatory-tech"
  secondary: ["ai-governance", "provenance"]
  jurisdiction: ["cross-jurisdictional"]

strategic:
  uniqueness: "bio construct 전체 라이프사이클의 원본 증명"
  openness: 8
  risk: 6
```

## Reuse Scoring Rubric

| Score | Meaning |
|-------|---------|
| 9-10  | 거의 모든 프로젝트가 사용할 수 있는 범용 인프라 (예: 원본 로그) |
| 7-8   | 여러 도메인에서 재사용 가능한 메커니즘 (예: 이중 경매) |
| 5-6   | 특정 도메인군 내에서 재사용 가능 |
| 3-4   | 한 프로젝트에 강하게 결합됨 |
| 1-2   | 거의 재사용 불가능 |
