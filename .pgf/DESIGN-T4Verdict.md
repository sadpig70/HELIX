# T4Verdict Design @v:1.0

## Intent

P5_5 external pilot 개시의 자율 구축 슬라이스. 실제 외부 참가자 모집·공개는 정욱님의
실세계 행위이며 자율 불가. 자율로 만들 수 있는 것은 pilot이 열렸을 때 그 데이터를
**위조·과대주장 불가**로 판정하는 T4 verdict 기계다.

기존 `aggregate_pilot`(core/helix_wedge_metrics.py)은 T4 metrics 게이트(throughput ·
false-admit · replay · retention)만 판정한다. 그러나 그 게이트는 참가자가 **진짜 독립
operator**이며 **검증된 real_owned_stakes**를 가졌는지 요구하지 않는다. self-dealing 내부자가
만든 ledger 여러 개로도 metrics 게이트는 통과할 수 있다 — pilot 수준의 T4 위조.

이 설계는 metrics 게이트 위에 **provenance 게이트**를 합성한다: 각 참가자는 자신의 실
ledger head에 바인딩된 검증된 real_owned_stakes attestation을 가져야 하며, operator는 wedge
저자·서로와 독립이어야 한다. T4는 **두 게이트를 모두 통과할 때만** passed다.

honest 기본값: T4는 기본 **not_passed**이며, 모든 요건이 검증될 때만 passed. 각 미충족은
구체적 gap으로 보고한다. 데이터가 없으면(빈 pilot) not_passed. 이 기계는 실 데이터를
생성하지 않는다 — 그것은 외부 pilot이라는 실세계 사건이다.

## Gantree

```text
T4Verdict // metrics + provenance 합성 T4 판정 (designing) @v:1.0
    MetricsGate // 기존 aggregate_pilot 재사용 (designing)
        Reuse // 중복 구현 금지, 단일 출처 (designing)
    ProvenanceGate // 참가자별 검증된 real_owned_stakes (designing) @dep:MetricsGate
        LedgerBinding // attestation.real_work.ledger_head == 그 참가자 실 ledger head (designing)
        GradeVerified // owned_stakes_grade == real_owned_stakes (designing)
        MutualIndependence // operator id·org가 wedge 저자·서로와 구별 (designing)
        CountThreshold // >=2 검증 독립 참가자(>=3 중) (designing)
    Compose // passed = metrics.passed AND provenance.passed (designing) @dep:MetricsGate,ProvenanceGate
        FailClosed // 기본 not_passed, gap 명시 (designing)
        NoForgery // 단일/미검증/self-dealing 경로로 절대 pass 불가 (designing)
        Sealed // metrics seal + attestation hash 바인딩, 재현 가능 (designing)
```

## PPR

```python
def t4_verdict(root, participant_ledgers, owned_stakes_attestations,
               wedge_author_id, period=None, sidecar=None) -> T4Verdict:
    """Compose the metrics gate and the provenance gate into a T4 verdict.

    participant_ledgers        = {pid: ledger_rel}   (real sealed wedge ledgers)
    owned_stakes_attestations  = {pid: attestation}  (one per participant)

    acceptance_criteria:
      - metrics gate = aggregate_pilot(...) reused verbatim (single source)
      - for each pid: attestation seal-valid, owned_stakes_grade ==
        real_owned_stakes, and real_work.ledger_head_sha256 == that participant's
        sealed ledger head (binds the claim to the exact real decisions)
      - operators mutually independent: distinct ids AND distinct orgs, none ==
        wedge_author_id
      - verified_independent >= 2 of >= 3 participants
      - verdict == "passed" ONLY when metrics verdict == "passed" AND provenance
        gate passes; otherwise "not_passed" with explicit gaps
      - a bare label / single operator / self-dealing set can never pass
      - sealed and reproducible from the same ledgers + attestations
    """
    metrics = aggregate_pilot(root, participant_ledgers, period, sidecar)
    prov = _provenance_gate(metrics, owned_stakes_attestations, wedge_author_id)
    passed = metrics["t4_gate"]["verdict"] == "passed" and prov["pass"]
    return seal({metrics, prov, verdict: "passed" if passed else "not_passed",
                 gaps: [...]})
```

## Invariants

- metrics 게이트는 재구현하지 않고 aggregate_pilot을 그대로 호출한다(단일 출처).
- provenance 게이트는 metrics와 **논리곱(AND)** 이다 — 어느 하나라도 미충족이면 not_passed.
- 각 attestation은 그 참가자의 실 ledger head에 바인딩되어야 한다(claim이 실제 sealed
  decisions에 고정). 바인딩 불일치면 그 참가자는 검증 실패.
- operator 상호 독립: 동일인이 여러 참가자로 위장하거나 wedge 저자가 참가자로 들어오면
  검증 실패(자기거래 차단). id와 org 모두 구별.
- 단일 operator·미검증·self-dealing 경로로는 절대 passed 불가. T4 위조가 코드로 차단.
- honest 상한: 이 기계는 판정만 한다. 실 데이터(독립 외부 operator의 real work)는 P5_5
  pilot이라는 실세계 사건이 생성한다. 데이터 없으면 not_passed.
- Deterministic, stdlib only: no clock/network/subprocess/randomness/AI.

## Verification plan

- 빈 pilot / 참가자 0 → not_passed (gap: no participants).
- metrics passed + provenance passed(≥2 독립 검증) → passed.
- metrics passed + attestation 없음/미검증 → not_passed (provenance gap).
- self-dealing: operator == wedge 저자 또는 동일 operator 중복 → not_passed.
- ledger_head 바인딩 불일치 attestation → 그 참가자 검증 실패.
- metrics failed(예: replay<100%) + provenance passed → not_passed (metrics gap).
- 결정론: 동일 입력 → 동일 seal.
- 기존 aggregate_pilot/wedge_metrics 회귀 clean.
- full regression + helix_validate.
```
