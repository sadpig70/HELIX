# HELIXCorpusPilot Design

## Gantree

```text
HELIXCorpusPilot // fixed-denominator Phase 2 execution plane (done) @v:1.0
    PilotContract // immutable 24-slot denominator (done)
        RegistrySchema // class, slot, candidate and target contract (done)
        RegistryValidator // exact IDs, mix and substitution guard (done)
    EvidencePreparation // compact deterministic provenance (done) @dep:PilotContract
        SourceSnapshot // sorted path/hash evidence without checkout bulk (done)
        EvidenceBoundary // network and AI remain outside deterministic core (done)
    PilotObservation // ledger-derived readiness measurement (done) @dep:PilotContract
        AdmissionAggregation // Generative and Evidence counts from receipts (done)
        DiversityBaseline // domain, verb, shape, machine, gene distributions (done)
        Phase3Gate // 24/12/5 plus integrity verdict (done)
    CandidateExecution // real 24 candidate selection and processing (done) @dep:PilotObservation
        CandidateFreeze // human scope and rights decision (done)
        GenerativeRun // deterministic single-writer admission queue (done)
        EvidenceRun // reproduction plus human-bound review receipts (done)
    PilotClosure // final report and Phase 3 decision (done) @dep:CandidateExecution
```

## PPR

```python
def run_corpus_pilot(registry: Registry, candidates: list[Candidate]) -> PilotReport:
    assert validate_fixed_mix(registry) == []
    selected = AI_assess_candidate_fit(candidates, constraints=registry.slots)
    human_freeze(selected)  # authority boundary
    prepared = parallel(snapshot_source, characterize_manifest, reproduce_candidate)
    for item in stable_slot_order(prepared):  # single writer
        validate(item.manifest) → intake → admit
        if item.has_substantiated_evidence:
            human_review(item.evidence) → promote
        verify_ledger()
    return ledger_truth → aggregate_diversity → evaluate_phase3_gate

# acceptance_criteria:
#   - denominator and source mix cannot drift after freeze
#   - snapshot bytes are deterministic and revision-bound
#   - no promotion without human review bound to manifest SHA-256
#   - READY_FOR_PHASE_3 only when all 24/12/5/integrity gates pass
```

## Authority boundary

- Codex may implement tools, collect public metadata, prepare snapshots, propose characterization,
  run reproduction and record deterministic receipts.
- 정욱님 retains the final candidate freeze and Evidence approval authority.
- External publication, push and license exceptions are outside this pilot contract.
