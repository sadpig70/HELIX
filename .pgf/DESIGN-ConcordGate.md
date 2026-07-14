# ConcordGate Design @v:1.0

## Provenance (recreate winner)

HELIX exploit strand (`RUN_EXPLOIT`) recombination over the 69-project corpus.
White-space: the corpus verifies **single** actions/handbacks/settlements, but no
project **reconciles multiple independent attestations about one subject** to
detect split-brain evidence. Recombined genes:

- ReproDossier — output-hash agreement across independent build provenances.
- ADPR / CertMesh — sealed hash-chain attestation ledger.
- WithheldActionWitness — a k-way justification verdict.

Novel axis (negative space): cross-attestation contradiction detection with an
independence unit. Conventions inherited: deterministic engine, k_way_verdict,
cli_triplet, append-only hash-chained ledger, stdlib-only.

## Intent

A local CLI that answers one question about N independent sealed attestations
about a single subject: **do they concord, or does the evidence split?** It
requires a quorum of independent sources (org = the independence unit), detects
the exact contradicting attestation pairs (cross-source and same-source), and
emits a sealed hash-chain concordance ledger. Verdict is 3-way:
`CONCORDANT` / `SPLIT` / `INSUFFICIENT`.

Fail-closed and honest: missing/duplicate/invalid attestations never inflate
concordance; a single source (or many attestations from one org) can never reach
quorum; every conflict is named, never hidden.

## Gantree

```text
ConcordGate // 독립 attestation 협화 판정 (designing) @v:1.0
    Attestation // sealed 주장 단위 (designing)
        Seal // canonical JSON SHA-256 무결성 (designing)
        Validate // attester{id,org}·subject_id·claims 필수 (designing)
    Independence // 독립 당사자 단위 (designing) @dep:Attestation
        SourceUnit // org = 독립 단위; 같은 org는 한 소스 (designing)
        Quorum // 독립 소스 수 >= quorum(기본 2) (designing)
    Reconcile // 필드별 협화/모순 판정 (designing) @dep:Independence
        FieldConcord // 공유 필드에서 소스간 값 일치 (designing)
        Conflict // 모순쌍 정확 지목(cross-source·same-source) (designing)
        Verdict // CONCORDANT|SPLIT|INSUFFICIENT (designing)
    Ledger // sealed hash-chain 조정 기록 (designing) @dep:Reconcile
        Append // append-only, parent chain (designing)
        Verify // seq·parent·seal 재검증 (designing)
    Cli // sample|run|report (designing) @dep:Ledger
```

## PPR

```python
def seal_attestation(att) -> Attestation:
    """attester{id,org}·subject_id·claims(비어있지 않은 dict)를 검증하고 봉인.
    acceptance_criteria:
      - 동일 입력 -> 동일 attestation_sha256 (결정론)
      - 필수 필드 결여 -> ValueError
    """

def reconcile(attestations, quorum=2) -> Reconciliation:
    """N개 attestation을 한 subject에 대해 조정.
    acceptance_criteria:
      - seal 깨진/외부 subject attestation은 제외하고 problem 기록
      - 독립 소스 = 서로 다른 org 수; 같은 org는 한 소스로 병합
      - 독립 소스 < quorum -> INSUFFICIENT
      - 어느 공유 필드든 소스간 값 불일치 -> SPLIT + 모순쌍 지목
      - 같은 org 내부 값 불일치 -> SPLIT(same-source) 지목
      - 그 외 -> CONCORDANT
      - 결정론적으로 봉인된 reconciliation 반환
    """

def append_ledger(root, ledger_rel, reconciliation) -> Entry:
    """append-only hash-chain 기록. parent=이전 entry_sha256.
    acceptance_criteria: seq 단조·parent 체인·entry seal 재검증 가능.
    """
```

## Invariants

- org가 독립 단위다. 한 org의 attestation이 여러 개여도 독립 소스는 1로 센다 —
  자기증언 중복이 quorum을 부풀리지 못한다.
- 모든 모순은 명시적으로 지목한다(어느 소스가 어느 필드에서 어떤 값으로 충돌하는지).
- fail-closed: 판정 불가/증거 부족은 CONCORDANT가 아니라 INSUFFICIENT.
- Deterministic, stdlib only: no clock, network, subprocess, randomness, AI.
- append-only ledger: 개별 라인 변조는 verify에서 탐지(unkeyed = 무결성).

## Verification plan

- 결정론: 동일 attestations -> 동일 verdict·seal.
- 독립 3소스 전부 일치 -> CONCORDANT.
- 두 소스가 한 필드에서 불일치 -> SPLIT + 정확한 모순쌍.
- 같은 org 2개만 -> INSUFFICIENT(독립 1).
- 같은 org 내부 불일치 -> SPLIT(same-source).
- 깨진 seal / 다른 subject -> 제외 + problem.
- ledger append/verify 왕복 + 변조 탐지.
- CLI sample/run/report 왕복.
- ≥10 tests + 결정론.
```
