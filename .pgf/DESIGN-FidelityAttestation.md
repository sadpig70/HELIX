# FidelityAttestation Design @v:1.0

## Intent

페르소나 conditional-adoption trial(`core/helix_adoption_trial.py`)의 provenance를
`simulated_unverified`에서 `fidelity_attested`로 격상하는 메커니즘. 방법론 대화의 결론:

> AI 페르소나의 판단은 진짜이지만, utility 신호가 되려면 인과적 독립성(provenance)이
> 필요하다. 남는 축은 "재현 충실도가 외부에서 보증되는가"이며, 그 마지막 칸은 코드가
> 아니라 **실존 인물의 보증**이 채운다.

이 설계는 실존 인물이 AI 재현을 검토·보증하는 sealed attestation을 도입하고, 그것이
유효할 때만 provenance를 격상한다. `real_owned_stakes`(실제 손익 소유)는 이 층 밖이며,
따라서 `fidelity_attested`도 여전히 **is_t4_utility=false**다 — 재현 충실도 보증은
"판단 진정성"을 강화하나 "실제 시장 효용"을 만들지 않는다.

## Gantree

```text
FidelityAttestation // 실존 인물 provenance 부여 (designing) @v:1.0
    PersonaSource // 페르소나의 실존 근거 바인딩 (designing)
        SourceRefs // 실존 인물 자료의 content hash 목록 (designing)
        SourceBinding // 페르소나가 그 자료에 근거함을 sealed로 명시 (designing) @dep:SourceRefs
    ReproductionSample // 실존 인물이 검토할 AI 재현 샘플 (designing)
        SampleCapture // 페르소나의 adoption 판단을 content hash로 봉인 (designing)
    Attestation // 실존 인물의 충실도 보증 (designing) @dep:ReproductionSample,SourceBinding
        AttestVerdict // faithful | partial | unfaithful (designing)
        ConflictDisclosure // 이해상충 명시 (예: attester=wedge 저자) (designing)
        Independence // attester != 재현 주체(AI) 강제 (designing)
        AttestSeal // canonical seal (designing) @dep:AttestVerdict,Independence
    ProvenanceUpgrade // attestation 유효 시 격상 (designing) @dep:Attestation
        UpgradeRule // faithful + 바인딩 일치일 때만 fidelity_attested (designing)
        UtilityGuard // fidelity_attested도 is_t4_utility=false 유지 (designing)
```

## PPR

```python
def build_persona_source(persona_id: str, source_refs: list) -> PersonaSource:
    """페르소나가 근거로 삼는 실존 인물 자료를 content hash로 바인딩.

    acceptance_criteria:
      - source_refs는 (ref, sha256) 쌍의 비어있지 않은 목록
      - 동일 (persona_id, source_refs) -> 동일 sealed source (결정론)
      - source 없는 페르소나는 fidelity 대상이 될 수 없다
    """
    # source_refs = [{ref, sha256}, ...] — 실존 인물의 발언/결정/우선순위 자료
    return seal({persona_id, source_refs})


def capture_reproduction(adoption_receipt: dict) -> ReproductionSample:
    """실존 인물이 검토할, AI 재현의 판단 샘플을 봉인.

    acceptance_criteria:
      - adoption receipt seal이 유효해야 한다
      - sample은 decision/reasons/interest_function을 그대로 담아 검토 가능
      - sample_sha256이 receipt에 결정론적으로 대응
    """
    return seal({persona_id, decision, reasons, interest_function, receipt_sha256})


def attest_fidelity(source, sample, attester, verdict, reservations,
                    conflict_of_interest) -> FidelityAttestation:
    """실존 인물이 AI 재현의 충실도를 보증한다.

    acceptance_criteria:
      - attester_id != 재현 주체(reproduction agent) — 독립 보증
      - verdict in {faithful, partial, unfaithful}
      - reviewed sample_sha256이 실제 sample과 일치
      - source_sha256이 실제 persona source와 일치
      - conflict_of_interest는 명시 기록 (은폐 금지; attester가 wedge 저자면 flag)
      - faithful이 아니면 격상 근거가 되지 못한다
    """
    require(attester["id"] != sample["reproduction_agent"])
    return seal({attester, source_sha256, sample_sha256, verdict,
                 reservations, conflict_of_interest})


def upgrade_provenance(adoption_receipt: dict, attestation: FidelityAttestation) -> str:
    """attestation이 유효·faithful·바인딩 일치이면 provenance를 격상.

    acceptance_criteria:
      - attestation seal 유효 + sample_sha256이 이 receipt의 재현과 일치
      - verdict == faithful -> "fidelity_attested"; 아니면 "simulated_unverified" 유지
      - fidelity_attested도 is_t4_utility=false (real_owned_stakes만 utility)
      - 격상은 attestation을 receipt에 바인딩해 감사 가능하게 기록
    """
    if not (verify(attestation) and attestation["sample_sha256"] == sample_of(receipt)
            and attestation["verdict"] == "faithful"):
        return "simulated_unverified"
    return "fidelity_attested"
```

## Invariants

- fidelity_attested는 utility 아님. `is_t4_utility`는 `real_owned_stakes`에서만 true —
  이 설계는 그 규칙을 건드리지 않는다.
- attester는 재현 주체(AI)와 분리되어야 한다 (독립 보증). 자기 재현을 자기가 보증하면 무효.
- conflict_of_interest(예: attester가 wedge 저자 = dogfooding)는 은폐 없이 기록한다.
  격상은 허용하되 conflict 플래그가 신호의 약함을 표시한다.
- trial은 자기 등급을 스스로 올리지 못한다 — 격상은 외부 attestation의 함수다.
- 실제 attestation이 없으면 simulated_unverified 유지 (위조 금지).

## Verification plan

- 결정론: 동일 입력 → 동일 seal.
- faithful attestation → fidelity_attested; partial/unfaithful → simulated 유지.
- attester == 재현 주체 → 거부 (독립성).
- 바인딩 불일치(다른 sample/source) → 격상 거부.
- conflict_of_interest 기록 확인.
- fidelity_attested receipt도 aggregate에서 is_t4_utility=false.
- 전체 회귀 + helix_validate.
```
