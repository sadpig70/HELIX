# HELIXCorpusPhase4 Design @v:1.0

## Gantree

```text
HELIXCorpusPhase4 // platform-pack absorption planning for Phase 3 machines (designing) @v:1.0
    B0EntryGate // consume Phase 3 closure and Condense gate doctrine (designing)
    B1PackRegistry // freeze platform-pack absorption registry (designing) @dep:B0EntryGate
    B2PackContracts // define per-platform absorption contracts (designing) @dep:B1PackRegistry
        AttestraPackLane // five trust/gate packs for Attestra (designing)
        RoutestraPackLane // one route/handoff pack for Routestra (designing)
    B3Validation // verify registry consistency and repository health (designing) @dep:B2PackContracts
    B4Handoff // choose the next executable platform absorption batch (designing) @dep:B3Validation
```

## PPR

```python
def B0EntryGate(phase3_outcome: dict, condense_doc: str) -> dict:
    """Accept Phase 4 only when Phase 3 closed as pack absorption, not new kernel emission."""
    assert phase3_outcome["status"] == "PHASE3_COMPLETE_READY_FOR_PHASE4"
    assert phase3_outcome["decision"]["phase4"] == "PROCEED_TO_PLATFORM_ABSORPTION_PACKAGING"
    assert phase3_outcome["decision"]["condense"] == "DO_NOT_EMIT_NEW_PLATFORM_KERNEL"
    return {"phase4_allowed": True, "source_of_truth": "Phase 3 outcome + docs/CONDENSE.md"}

def B1PackRegistry(results: list[dict]) -> dict:
    """Create a deterministic registry of platform pack candidates from Phase 3 results."""
    packs = AI_transform_results_to_pack_registry(results)
    # criteria: 6 packs, every pack has source project, machine label, target platform, parity source, gates
    return {"packs": packs, "status": "registry_frozen"}

def B2PackContracts(registry: dict) -> dict:
    """Map each pack to platform-level acceptance gates without mutating external repositories."""
    contracts = AI_design_platform_absorption_contracts(registry)
    # criteria: zero-kernel-change + reference-parity + determinism-clean + tests-green + structure-conform
    return contracts

def B3Validation(registry_path: str) -> dict:
    """Verify registry JSON and cross-check it against the Phase 3 outcome."""
    report = deterministic_validate_registry(registry_path)
    # criteria: JSON parses, count is 6, routes are Attestra=5 Routestra=1, all gates present
    return report

def B4Handoff(status: dict) -> str:
    """Select exactly one next executable batch."""
    return "execute Phase4 B2-AttestraPackLane absorption contract for five Attestra packs"
```

## Acceptance criteria

- Phase 4 registry contains exactly six Phase 3 pack candidates.
- Each pack preserves source project, source result, machine label, handback trace, platform route and gate list.
- Existing platform kernels remain locked; no new Condense kernel is authorized.
- Verification is based on executable checks, not self-report.
- Handoff reports exactly one next task.

