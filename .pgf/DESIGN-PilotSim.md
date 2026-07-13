# PilotSim Design @v:1.0

## Gantree

```text
PilotSim // three-persona synthetic wedge pre-pilot (in-progress) @v:1.0
    PrepareContracts // define honest simulation boundary and artifacts (done)
    [parallel]
    ReleaseLead // software release handback operator (designing)
    SREOperator // CI/CD and infrastructure handback operator (designing)
    AIGovernanceLead // AI approval and evidence-integrity operator (designing)
    [/parallel]
    AggregateEvidence // recompute metrics and replay from three ledgers (designing) @dep:ReleaseLead,SREOperator,AIGovernanceLead
    JudgeBoundary // run T4 with no real-owned-stakes attestations (designing) @dep:AggregateEvidence
    RecordReport // persist evidence and conclusions (designing) @dep:JudgeBoundary
```

## PPR

```python
def run_persona(persona: PersonaSpec, output_root: Path) -> PersonaResult:
    """Generate and audit seven synthetic handbacks in an isolated directory."""
    packets = AI_generate_domain_handbacks(persona, counts={"valid": 4, "thin": 2, "breach": 1})
    decisions = audit_handback(packets, operator=persona.operator_id)
    # acceptance_criteria:
    #   - exactly 7 decisions
    #   - admission distribution ADMIT=4, SANDBOX_ONLY=2, EXCLUDED=1
    #   - ledger chain and every replay verify
    #   - all artifacts explicitly marked simulated
    return PersonaResult(packets, decisions)

def aggregate_simulation(results: list[PersonaResult]) -> SimulationReport:
    """Recompute metrics while preventing synthetic evidence from becoming T4 provenance."""
    metrics = aggregate_pilot(results, period={"weeks": 1}, synthetic_sidecar=True)
    t4 = t4_verdict(results, owned_stakes_attestations={})
    # acceptance_criteria:
    #   - combined decisions == 21
    #   - metrics gate exercises throughput, false-admit, replay, retention
    #   - final T4 verdict == not_passed
    #   - report states this is not external adoption evidence
    return SimulationReport(metrics, t4)
```

## Safety Boundary

- Persona names and organizations are fictional simulation labels, not external entities.
- No `real_owned_stakes` attestation may be created.
- A metrics pass is permitted as a plumbing test; T4 must remain `not_passed`.
- Outputs must stay under `_workspace/pilot-sim/` except PGF state files.
