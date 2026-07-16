# HELIXCorpusSupply Design @v:1.0

## Intent

`Generative Corpus`와 `Evidence Corpus`를 서로 다른 admission authority로 운영한다.
AI는 `gene`/`machine` 가설을 제안할 수 있지만, corpus 상태 전이와 receipt seal은 동일 입력에
동일 출력을 내는 결정론 코어만 수행한다. 기존 `close-loop` corpus entry는 유지하고 이 plane이
상위의 versioned 공급 계약을 제공한다.

## Invariants

- 기존 `schemas/corpus-entry.schema.json`과 `close-loop` 경로는 변경하지 않는다.
- `Generative admission != Evidence promotion`이며 서로 다른 receipt로 기록한다.
- ledger는 append-only hash chain이고 item manifest는 revision별 immutable snapshot이다.
  `manifest.json`은 최신 revision의 materialized pointer이며 receipt는 정확한 snapshot hash에 바인딩된다.
- 시간·네트워크·AI는 core에 없다. `now`와 human review receipt는 CLI에서 주입한다.
- evidence promotion은 generative admission, 실행 증거, human approval binding을 모두 요구한다.
- machine novelty는 가설이며 이 시스템만으로 `CONDENSE`를 승인하지 않는다.
- `corpus_id`는 path component로 안전한 `HC-[A-Z0-9-]+`만 허용한다.
- v1 ledger writer는 single-writer이며 append 후 `flush+fsync`; 기존 chain 이상 시 쓰기를 거부한다.
- Condense 최소 근거 수는 기존 router policy(현재 5)의 권위이며 corpus supply가 복제하지 않는다.

## Gantree

```text
HELIXCorpusSupply // versioned dual-corpus supply plane (done) @v:1.0
    ContractPlane // schemas and immutable identities; see DESIGN-HELIXCorpusSupply-Contracts.md (decomposed)
    AdmissionPlane // deterministic gates and sealed receipts; see DESIGN-HELIXCorpusSupply-Admission.md (decomposed) @dep:ContractPlane
    OperationsPlane // store, CLI, migration and health; see DESIGN-HELIXCorpusSupply-Operations.md (decomposed) @dep:AdmissionPlane
    IntegrationPlane // additive HELIX integration (done) @dep:OperationsPlane
        PreserveLegacyCorpusEntry // keep close-loop contract unchanged (done)
        RegisterSchemas // ship manifest and receipt schemas (done)
        DispatchCorpusCli // route helix.py corpus subcommands (done)
        ExtendRepoValidation // validate new schema subset and seed policy (done)
    VerificationPlane // evidence-backed completion gates (done) @dep:IntegrationPlane
        UnitGate // corpus supply unit tests (done)
        CliGate // subprocess CLI integration tests (done)
        DeterminismGate // replay and hash-chain verification (done)
        RegressionGate // full HELIX tests and validator (done)
        ArchitectureGate // Gantree-to-module consistency review (done)
```

## PPR

```python
def corpus_supply_cycle(manifest_path: str, tier: str, now: str,
                        review_receipt_path: Optional[str] = None) -> dict:
    """Intake one immutable manifest and issue a deterministic tier receipt."""
    # acceptance_criteria:
    #   - existing close-loop corpus format remains backward compatible
    #   - hard-gate failure never appends an ADMITTED event
    #   - evidence tier cannot bypass prior generative admission
    #   - identical input produces identical manifest/fingerprint/decision hashes
    manifest = load_manifest(manifest_path)
    validation = validate_manifest(manifest)
    if validation.problems:
        return quarantine(validation.problems)
    snapshot = intake_manifest(manifest)
    if tier == "generative":
        return admit_generative(snapshot, now=now)
    return promote_evidence(snapshot, review_receipt_path, now=now)
```

## Authority Boundaries

| Surface | Authority | May not do |
|---|---|---|
| Characterization | AI/meta layer | mutate admission state |
| Hard/generative/evidence gate | deterministic core | infer missing evidence |
| Human review receipt | injected evidence | override hard gate |
| Admission ledger | append-only writer | edit/delete prior events |
| Condense router | existing HELIX plane | treat hypothesis as verified machine |

## Completion Criteria

1. All decomposed leaves have typed contracts and acceptance criteria.
2. No circular `@dep` exists.
3. New CLI works from a temporary corpus root without network access.
4. Full regression suite and `core/helix_validate.py` pass.
5. Review has `Critical=0` and `High<=2` before PLAN.
