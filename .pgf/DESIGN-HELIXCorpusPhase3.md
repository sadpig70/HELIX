# HELIXCorpusPhase3 Design

## Gantree

```text
HELIXCorpusPhase3 // six-full-cycle production experiment (frozen) @v:1.0
    EntryGate // Phase 2 evidence boundary (done)
        PilotVerdict // READY_FOR_PHASE_3 report hash (done)
        CorpusLedger // 24 Generative / 5 Evidence / 29 events (done)
    ExperimentRegistry // immutable six-slot execution contract (done) @dep:EntryGate
        Identity // HC-P3-FC-001..006 and project slugs (done)
        Diversity // unique verbs and >=0.75 domain distance (done)
        GeneBinding // >=1 external gene plus admitted manifest hash (done)
        EvidenceBaseline // each slot bound to Evidence admission (done)
    CycleProtocol // same ordered closure for every experiment (done) @dep:ExperimentRegistry
        Explore → FullCycle → Implement → Handback → CloseLoop → Feedback
        FailureRoute // every failed cycle → Failure Corpus (done)
    Freeze // registry hash plus Phase 2 report hash receipt (done) @dep:CycleProtocol
    Execution // six sequential full-cycles (pending) @dep:Freeze
        FC001 → FC002 → FC003 → FC004 → FC005 → FC006
    Phase3Closure // >=3 independent projects plus measured outcomes (pending) @dep:Execution
```

## PPR

```python
def execute_phase3(registry: FrozenRegistry) -> Phase3Report:
    assert validate_registry(registry) == []
    assert verify_freeze_receipt(registry, phase2_report=True)
    results = []
    for slot in registry.slots:  # frozen order, one full-cycle at a time
        candidate = AI_explore(slot.domain_signature, slot.gene_bindings)
        project = AI_pgf_full_cycle(candidate, lead_verb=slot.lead_verb)
        result = implement(project) → verify_handback → close_loop → measure_feedback
        if result.failed:
            record_failure_corpus(result)
        results.append(result)
    return measure(results, independent_projects=3,
                   external_gene_transfer=True,
                   machine_candidates=True,
                   platform_absorption=True)

# invariants:
#   - registry identity, order and manifest hashes do not change after freeze
#   - no repeated lead verb and every pair/recent domain distance is >= 0.75
#   - every experiment consumes at least one admitted external gene
#   - handback precedes close-loop; feedback follows close-loop
#   - negative outcomes remain negative and enter Failure Corpus
```

## Frozen slots

| ID | Project | Verb | External gene | Evidence baseline |
|---|---|---|---|---|
| HC-P3-FC-001 | ProofEscrow | escrow | signed_step_metadata | EXT-001 |
| HC-P3-FC-002 | AuthorityArbiter | arbitrate | policy_data_separation | HELIX-001 |
| HC-P3-FC-003 | DriftIsolator | isolate | counterexample_shrinking | HELIX-003 |
| HC-P3-FC-004 | GraphQuarantine | quarantine | path_analysis | HELIX-004 |
| HC-P3-FC-005 | ContractRelay | relay | normalized_errors | HELIX-002 |
| HC-P3-FC-006 | HookCircuit | trip | hook_contract | EXT-001 |
