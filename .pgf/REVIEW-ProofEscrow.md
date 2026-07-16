# REVIEW-ProofEscrow

## Scope

- Target: `.pgf/DESIGN-ProofEscrow.md`
- Mode: design-review, iteration 1
- Perspectives: feasibility, risk, architecture

## Summary

`Critical=0`, `High=0`. 설계는 구현 가능하며 PLAN 전환 기준을 통과한다.

## Findings

### [medium][security] Trust secret separation

- Risk: 요청 문서가 trust key를 포함하면 receipt/ledger로 비밀이 전파될 수 있다.
- Resolution: `trust_store`를 API/CLI 경계의 별도 입력으로 두고 receipt에는 signer ID만 기록했다.

### [medium][integrity] Signed steps alone do not prove behavior

- Risk: artifact metadata 서명만으로 실행 behavior를 과대 주장할 수 있다.
- Resolution: `tests_passed`, `deterministic`, approved/baseline/observed hash 일치를 독립 gate로 강제했다.

### [low][architecture] Ledger must not alter verdict semantics

- Resolution: engine을 순수 함수로 유지하고 ledger는 검증된 receipt를 기록하는 후단 모듈로 분리했다.

## Verdict

`APPROVED` — 3/3 perspectives pass after the two design constraints were incorporated.
