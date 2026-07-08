# HELIXForwardClosure Design @v:1.0

## Gantree

```text
HELIXForwardClosure // close live forward-prediction missing artifacts (in-progress) @v:1.0
    CanonicalStateAudit // read HANDOFF, machine graph, live manifest, source registry (done)
    CandidateNormalization // convert every remaining missing artifact into probe evidence (in-progress) @dep:CanonicalStateAudit
        AgentPACT // hash-chain accountability layer -> M1 (designing)
        GPOA // two-axis governance incident classification -> M15 (designing)
        MLX // method license metadata predicate gate -> M3 (designing)
        PnR // non-response proof score index -> M15 (designing)
        QVeil // PQC API upgrade predicate gate -> M3 (designing)
        Qvidence // bio evidence commitment chain -> M4 (designing)
        WattMesh // home energy negotiation route selection -> M9 (designing)
    LivePredictionClosure // regenerate manifest/report and require MISSING_ARTIFACT=0 (designing) @dep:CandidateNormalization
    VerificationGate // run HELIX hard gates and targeted regressions (designing) @dep:LivePredictionClosure
    HandoffAndPublish // update HANDOFF and push only after all gates pass (designing) @dep:VerificationGate
```

## PPR

```python
def normalize_candidate(name: str, source_note: str) -> dict:
    """Create normalized behavioral evidence from local source text only.

    acceptance_criteria:
      - candidate JSON has id, expected, substantiated_count, artifact
      - core.helix_machine_probes.agreement_report matches all expected machines
      - forward_predict routes to an existing platform or a deliberate defer/condense
      - no new probe is added unless existing probes would be a lossy force-fit
    """
    evidence = AI_extract_mechanism_from_local_source(name, source_note)
    machine = AI_choose_narrow_existing_machine(evidence)
    if machine.is_force_fit:
        return AI_design_new_narrow_probe(name, evidence)
    return build_candidate_json(name, machine, evidence)


def verify_closure() -> dict:
    """Verify full HELIX forward closure.

    acceptance_criteria:
      - collect_forward_candidates artifact_counts == {"available": 10, "missing": 0}
      - live forward report summary == {"BUILD_ON_PLATFORM": 8, "DEFER": 2}
      - python core/helix_validate.py . exits 0
      - python -m unittest discover -s tests -q exits 0
      - U6 machine_probe_dataset agreement remains 1.0 over 95 claims
      - git commit/push happens only after verification passes
    """
    return run_gate_commands()
```
