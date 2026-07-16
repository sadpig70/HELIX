# HELIX Holdout Policy v1.0

## Purpose

HELIX의 `platform generator` 주장을 기존 corpus agreement가 아닌 **처음 보는 source에 대한 blind
prediction**으로 반증 가능하게 검증한다. 이 정책은 후보를 잘 맞히기 위한 절차가 아니라 label leakage,
사후 표본 교체, missing/abstain의 성공 위장, 무권한 oracle 공개를 차단하는 규율이다.

## Roles

| Role | Authority | Forbidden |
|---|---|---|
| `selector` | selection rule에 따라 source를 선택하고 source hash를 봉인 | oracle label 작성, prediction 수행 |
| `candidate_builder` | source에서 label-free candidate view 생성 | machine/action/platform 정답 열람 |
| `predictor` | candidate view만 읽고 prediction receipt 봉인 | oracle store, canonical corpus label 열람 |
| `oracle_author` | 독립 검토로 oracle 작성 후 commitment만 공개 | prediction receipt 수정 |
| `reveal_approver` | prediction seal 확인 후 reveal 승인 | prediction 전 reveal |
| `scorer` | sealed prediction과 revealed oracle 비교 | 표본 삭제, denominator 변경 |

한 주체가 `predictor`와 `oracle_author`를 동시에 맡을 수 없다. reveal은 `reveal_approver` 2명 중
최소 1명의 명시적 승인 receipt가 필요하다.

## Selection

1. live cohort는 최소 20개 source로 구성한다.
2. selection rule, cutoff, license allowlist, exclusion corpus hashes를 후보 열람 전에 문서화한다.
3. cohort manifest를 canonical JSON SHA256으로 봉인한 뒤 후보를 교체하거나 삭제하지 않는다.
4. source는 immutable revision과 artifact SHA256을 가져야 한다. branch tip, latest URL만으로 잠그지 않는다.
5. source license는 SPDX identifier와 local evidence path/hash를 모두 요구한다. 불명확하면 excluded다.
6. 기존 HELIX corpus, 62 packs, M1~M17 fixtures, U6/U9 artifacts와 source/artifact hash가 겹치면 excluded다.
7. 동일 upstream의 fork 또는 generated mirror는 하나의 source family로 계산한다.

## Candidate / Oracle Isolation

Candidate view에 허용되는 것은 관찰 가능한 operation, inputs, outputs, invariants, sample behavior와 source
provenance뿐이다. 다음 label은 금지한다.

- `expected`, `machines`, `machine_id`
- `action`, `expected_action`, `platform`, `platform_hint`
- 기존 HELIX routing note, pack name, oracle rationale

Oracle은 별도 path와 ACL에 둔다. registry에는 prediction 전 oracle content가 아니라 commitment SHA256만
기록한다. candidate artifact와 oracle artifact는 path와 hash가 모두 달라야 한다.

## Fixed Order

```text
selection policy seal
    -> source/candidate hash lock
    -> oracle commitment lock
    -> predictor receives candidate view only
    -> prediction receipt seal
    -> reveal approval
    -> oracle reveal receipt
    -> deterministic scoring
```

순서 위반 후보는 점수에서 제거하지 않고 protocol violation으로 남기며 denominator에 포함한다.

## Prediction Outcomes

| Outcome | Coverage | Success credit |
|---|---:|---:|
| exact existing-machine/action match | 1 | 1 |
| wrong machine/action/platform | 1 | 0 |
| `ABSTAIN` | 0 | 0 |
| `MISSING_ARTIFACT` | 0 | 0 |
| protocol violation / leaked | 0 | 0 |

`expectation=none` 또는 oracle 미공개 상태의 `ok=True`는 blind success가 아니다. Coverage denominator는
locked eligible candidates 전체이며, scoring denominator는 reveal된 후보만이 아니라 locked eligible
candidates 전체다.

## Metrics and Gates

- artifact coverage >= 0.80.
- existing-machine macro-F1 >= 0.80.
- selection/oracle leakage = 0.
- abstain, missing, protocol violation을 별도 count로 공개.
- false-CONDENSE count와 estimated implementation cost 공개.
- novelty 후보는 구현 후 기존 machine으로 환원됐는지 기록.

Baseline과 HELIX를 동일 cohort에서 평가한다. HELIX가 사전 선언 baseline을 넘지 못하면 generator 주장을
`internal corpus router`로 강등한다.

## Reveal and Audit

- reveal 승인에는 approver id, prediction receipt hash, oracle commitment hash, policy version이 필요하다.
- prediction hash가 없거나 commitment와 oracle hash가 다르면 reveal은 거부한다.
- reveal 이후 oracle 수정은 새 cohort로만 허용한다.
- 모든 selection/prediction/reveal/scoring receipt는 append-only hash chain으로 연결한다.
- wall clock은 외부 audit metadata일 뿐 판정 hash의 입력이 아니다. 순서는 parent receipt hash로 증명한다.

## Failure Strategy

- license 불명확: `excluded`, 다른 후보로 사후 교체 금지.
- source unavailable: `MISSING_ARTIFACT`, 성공 0, denominator 유지.
- predictor가 oracle path 접근: cohort `leakage_breach`, 전체 결과 격리.
- reveal-before-prediction: candidate `protocol_violation`, 성공 0.
- cohort commitment 이후 selection rule 변경: 새 cohort id로 다시 시작.

## P2_1 Acceptance

- Draft-07 registry schema가 stdlib schema subset 안에 있다.
- synthetic fixture가 schema와 semantic policy 검사를 통과한다.
- candidate/oracle path 분리, immutable source/license evidence, role separation이 강제된다.
- `ABSTAIN`, `MISSING_ARTIFACT`, protocol violation의 success credit가 모두 0이다.
- 실제 holdout 수집은 P2_2 이전에 시작하지 않는다.
