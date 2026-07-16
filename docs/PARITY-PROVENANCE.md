# HELIX Parity·Provenance Evidence Baseline

이 문서는 `docs/PARITY-PROVENANCE-WORKPLAN.md`의 `Stage0BaselineAudit` 실행 결과다.
목표는 대표 5개 플랫폼 팩의 현재 parity/provenance 근거 수준을 과대주장 없이 고정하고,
다음 단계인 `Stage1ContractSchemas`의 구현 입력을 명확히 하는 것이다.

## Current phase basis

- Phase 3 outcome validator: `PHASE3_COMPLETE_READY_FOR_PHASE4`
- Registry: `seed/corpus/phase3-2026-01-experiments.json`
- Representative target platform packs:
  - `ProofEscrow`
  - `AuthorityArbiter`
  - `GraphQuarantine`
  - `ContractRelay`
  - `HookCircuit`

```pg
ParityProvenanceEvidencePlan
    Stage0BaselineAudit // representative evidence baseline
        SelectFivePacks -> done
        ReadBindings -> done
        ClassifyPV -> done
        SaveReport -> done
    Stage1ContractSchemas // next
        DefineEvidenceSchemas
        AddSchemaFixtures
        AddSchemaValidationTests
```

## Evidence level definitions

### Parity level

- `P0`: static source/gene trace only. No executable parity contract exists.
- `P1-ready`: source behavior or project tests exist and can seed parity contracts, but no explicit parity receipt exists yet.
- `P2-target`: differential parity runner exists and produces receipts.
- `P3-target`: parity invariant is reused as a regression gate.

### Provenance level

- `V1`: source locator, revision, license evidence, or source hash is locked in corpus manifest.
- `V2-ready`: corpus manifest and generated pack README form a traceable static provenance edge, but no explicit provenance statement exists yet.
- `V3-target`: signed or hash-addressed evidence receipt binds source lock, machine evidence, parity result, and generated artifact.

## Stage 0 representative baseline

| Pack | Target platform | Registry bindings | Source state | Current P/V classification | Blocker | Next lift |
| --- | --- | --- | --- | --- | --- | --- |
| `ProofEscrow` | `Attestra` | `HC-PILOT-EXT-001:signed_step_metadata`, `HC-PILOT-HELIX-002:behavior_baseline_binding` | Both source manifests are `substantiated`; reproduction/tests/determinism are present; `parity_available=false`. | `P1-ready / V2-ready` | No explicit parity contract, receipt, or provenance statement. | Convert behavior fixtures into `parity-contract` and bind receipt to source locks. |
| `AuthorityArbiter` | `Attestra` | `HC-PILOT-EXT-002:policy_data_separation`, `HC-PILOT-HELIX-001:authority_custody_route` | HELIX source is `substantiated`; external OPA source has license/source lock but `machine.status=hypothesis` and verification is false. | `P0+P1-ready / V1+V2-ready` | External behavior evidence is not substantiated; no parity contract/receipt. | Add external machine evidence or scoped behavior fixture, then create authority parity contract. |
| `GraphQuarantine` | `Attestra` | `HC-PILOT-EXT-004:path_analysis`, `HC-PILOT-HELIX-004:staged_quarantine` | HELIX source is `substantiated`; external NetworkX source is `hypothesis` and verification is false. | `P0+P1-ready / V1+V2-ready` | External path-analysis evidence is not substantiated; no parity contract/receipt. | Substantiate graph behavior fixture before promoting to `P2-target`. |
| `ContractRelay` | `Routestra` | `HC-PILOT-EXT-005:normalized_errors`, `HC-PILOT-HELIX-001:fail_closed_handback` | HELIX source is `substantiated`; external jsonschema source is `hypothesis` and verification is false. | `P0+P1-ready / V1+V2-ready` | External normalized-error behavior evidence is not substantiated; no parity contract/receipt. | Add schema-error fixture and relay parity contract. |
| `HookCircuit` | `Attestra` | `HC-PILOT-EXT-006:hook_contract`, `HC-PILOT-HELIX-003:reflex_interruption` | HELIX source is `substantiated`; external pluggy source is `hypothesis` and verification is false. | `P0+P1-ready / V1+V2-ready` | External hook behavior evidence is not substantiated; no parity contract/receipt. | Add hook-call fixture and circuit parity contract. |

## Findings

1. All five representative packs exist as generated platform projects with `README.md`, `pyproject.toml`, `src/`, and `tests/`.
2. All five packs expose static gene provenance in their README files.
3. Corpus manifests lock source locator, revision, license evidence, and source hash for all referenced corpus IDs.
4. None of the representative packs currently has an explicit parity contract, parity receipt, provenance statement, or evidence registry entry.
5. `ProofEscrow` has the strongest immediate promotion path because both referenced source manifests are substantiated.
6. `AuthorityArbiter`, `GraphQuarantine`, `ContractRelay`, and `HookCircuit` must not be promoted to full `P2/V3` until their external hypothesis sources receive scoped machine evidence.

## Implementation decision for Stage 1

`Stage1ContractSchemas` should be implemented before any runner logic. The first durable artifact should be schema and fixture coverage for:

- `source-lock`
- `machine-evidence`
- `parity-contract`
- `parity-receipt`
- `provenance-statement`
- `evidence-registry`

This keeps the next implementation step narrow: define what counts as admissible evidence before generating or validating new receipts.

## Next PGF node

```pg
Stage1ContractSchemas
    DefineEvidenceSchemas
        source-lock.schema.json
        machine-evidence.schema.json
        parity-contract.schema.json
        parity-receipt.schema.json
        provenance-statement.schema.json
        evidence-registry.schema.json
    AddSchemaFixtures
        valid_minimal
        invalid_missing_required
    AddSchemaValidationTests
        python -m unittest discover -s tests -q
```

## Stage 2 source-lock and machine-evidence build

`scripts/corpus/parity_evidence_builder.py` generates deterministic V1/V2 evidence artifacts from the Phase 3 registry and corpus manifests.

```pg
Stage2EvidenceBuilder
    ReadPhase3Registry -> done
    BuildSourceLocks -> done
    BuildMachineEvidence -> done
    ValidateAgainstSchemas -> done
    SaveRepresentativeArtifacts -> done
```

Tracked output:

- `seed/parity-provenance/build-report.json`
- `seed/parity-provenance/representative/<Pack>/source-locks/*.json`
- `seed/parity-provenance/representative/<Pack>/machine-evidence/*.json`

Result:

- `ProofEscrow`: all generated `source-lock` and `machine-evidence` artifacts are schema-valid with no builder problems.
- `AuthorityArbiter`, `GraphQuarantine`, `ContractRelay`, `HookCircuit`: generated artifacts are schema-valid, but each has one external source with explicit machine-evidence problems:
  - `machine_status_not_substantiated`
  - `not_reproducible`
  - `tests_not_passed`
  - `not_deterministic`
  - `missing_behavior_sha256`

This preserves the Stage 0 conclusion: these packs have V1/V2 source traceability, but must not be promoted to `P2/V3` until external machine evidence is substantiated.

## Stage 3 ProofEscrow parity contract runner

`scripts/corpus/parity_contract_runner.py` builds and runs the first executable parity contract.

```pg
Stage3ParityContractRunner
    BuildProofEscrowContract -> done
    RunProofEscrowParity -> done
    SaveParityReceipt -> done
    TestUnavailableFailClosed -> done
```

Tracked output:

- `seed/parity-provenance/representative/ProofEscrow/parity-contracts/released.json`
- `seed/parity-provenance/representative/ProofEscrow/parity-receipts/released.json`

Result:

- Contract: `contract:ProofEscrow:released`
- Runner: `helix-parity-contract-runner/1.0`
- HELIX parity decision: `PASS`
- Pack-local decision: `RELEASED`
- Pack-local receipt schema: `proofescrow-receipt/1.0`
- HELIX parity receipt schema: `helix-parity-receipt/1.0`

The runner deliberately separates two receipts:

1. `ProofEscrow` pack-local receipt: proves the pack engine released the sample according to its own deterministic rules.
2. HELIX `parity-receipt`: proves the pack-local result matched the HELIX parity contract and that source/machine evidence artifacts were present.

Missing input is tested as `UNAVAILABLE`, not as success.

## Stage 4 representative 5-pack pilot

`scripts/corpus/parity_representative_pilot.py` generates the representative bundle for all five selected packs and writes the evidence registry.

```pg
Stage4RepresentativePilot
    BuildFivePackContracts -> done
    RunFivePackReceipts -> done
    BuildProvenanceStatements -> done
    BuildEvidenceRegistry -> done
    PreserveBlockedState -> done
```

Tracked output:

- `seed/parity-provenance/evidence-registry.json`
- `seed/parity-provenance/representative-pilot-report.json`
- `seed/parity-provenance/representative/<Pack>/parity-contracts/released.json`
- `seed/parity-provenance/representative/<Pack>/parity-receipts/released.json`
- `seed/parity-provenance/representative/<Pack>/provenance-statements/representative.json`

Representative pilot status:

| Pack | Registry status | Receipt decision | Reason |
| --- | --- | --- | --- |
| `ProofEscrow` | `VALID` | `PASS` | Executable parity runner exists and source/machine evidence is substantiated. |
| `AuthorityArbiter` | `BLOCKED` | `UNAVAILABLE` | External OPA machine evidence is still unsubstantiated and no pack runner exists. |
| `GraphQuarantine` | `BLOCKED` | `UNAVAILABLE` | External NetworkX machine evidence is still unsubstantiated and no pack runner exists. |
| `ContractRelay` | `BLOCKED` | `UNAVAILABLE` | External jsonschema machine evidence is still unsubstantiated and no pack runner exists. |
| `HookCircuit` | `BLOCKED` | `UNAVAILABLE` | External pluggy machine evidence is still unsubstantiated and no pack runner exists. |

Pilot count:

- `packs`: 5
- `VALID`: 1
- `BLOCKED`: 4

No blocked pack is promoted to success. The registry is intentionally admissible as a status registry, not as a claim that all five packs reached `P2/V3`.

## Stage 5 CI gates

`scripts/corpus/parity_registry_gate.py` validates the representative parity/provenance evidence in CI.

```pg
Stage5CIGates
    ValidateEvidenceRegistrySchema -> done
    ValidateReferencedArtifacts -> done
    ValidateReceiptSeals -> done
    ValidateProvenanceStatementSeals -> done
    ValidateStatusHonesty -> done
    WireGitHubActions -> done
```

CI now runs:

```bash
python scripts/corpus/parity_representative_pilot.py \
  --evidence-root seed/parity-provenance \
  --now 2026-07-16T00:00:00Z

python scripts/corpus/parity_registry_gate.py \
  --registry seed/parity-provenance/evidence-registry.json \
  --report seed/parity-provenance/representative-pilot-report.json
```

Gate checks:

- `evidence-registry.json` matches `schemas/evidence-registry.schema.json`.
- Every referenced `source-lock`, `machine-evidence`, `parity-contract`, `parity-receipt`, and `provenance-statement` exists and is schema-valid.
- `receipt_sha256` and `statement_sha256` seals match canonical HELIX digest rules.
- `VALID` entries must have exactly one `PASS` receipt.
- `BLOCKED` entries must not contain a `PASS` receipt and must still carry a non-success receipt.
- pilot report counts must match registry status counts.

This makes the representative evidence chain CI-enforced while preserving honest blocked states.

## Stage 6 expansion inventory

`scripts/corpus/parity_expansion_inventory.py` builds the expansion inventory for all 62 live platform packs.

```pg
Stage6ExpansionInventory
    ReadLivePlatformLoaders -> done
    ExcludeCoreProbeRows -> done
    MergeRepresentativeRegistry -> done
    ClassifyAllPacks -> done
    SaveExpansionInventory -> done
    AddCIGateValidation -> done
```

Tracked output:

- `seed/parity-provenance/expansion-inventory.json`

Classification rule:

- `VALID`: representative registry entry has a `PASS` parity receipt.
- `BLOCKED`: representative registry entry exists but is non-success and must not be promoted.
- `PENDING`: live platform pack exists and has machine-probe coverage, but no parity/provenance bundle has been started.

Inventory result:

| Status | Count |
| --- | ---: |
| `VALID` | 1 |
| `BLOCKED` | 4 |
| `PENDING` | 57 |
| Total | 62 |

Platform split:

| Platform | VALID | BLOCKED | PENDING |
| --- | ---: | ---: | ---: |
| `Attestra` | 1 | 3 | 24 |
| `Clearstra` | 0 | 0 | 12 |
| `Routestra` | 0 | 1 | 11 |
| `Certstra` | 0 | 0 | 5 |
| `Scorestra` | 0 | 0 | 5 |

The inventory uses live platform probe rows from `scripts/condense/machine_probe_dataset.py`, excludes `core` and `HELIX` probe rows, and therefore tracks exactly the 62 platform packs.

## Stage 7 first pending promotion

`scripts/corpus/parity_pending_promotion.py` promotes the strongest pending pack into a full parity/provenance bundle.

```pg
Stage7FirstPendingPromotion
    SelectStrongestPending -> done
    BuildSourceLock -> done
    BuildMachineEvidence -> done
    BuildParityContract -> done
    BuildParityReceipt -> done
    BuildProvenanceStatement -> done
    RefreshExpansionInventory -> done
```

Selected pack:

- Platform: `Attestra`
- Pack: `policy-drift`
- Reason: strongest pending candidate by live probe density: 5 probe cases across `M2`, `M3`, and `M11`.

Tracked output:

- `seed/parity-provenance/expansion/Attestra/policy-drift/source-locks/local-pack.json`
- `seed/parity-provenance/expansion/Attestra/policy-drift/machine-evidence/live-probe.json`
- `seed/parity-provenance/expansion/Attestra/policy-drift/parity-contracts/live-probe.json`
- `seed/parity-provenance/expansion/Attestra/policy-drift/parity-receipts/live-probe.json`
- `seed/parity-provenance/expansion/Attestra/policy-drift/provenance-statements/live-probe.json`
- `seed/parity-provenance/expansion/Attestra/policy-drift/promotion-report.json`

Promotion result:

- `policy-drift`: `PENDING` → `VALID`
- parity receipt decision: `PASS`
- machines: `M2`, `M3`, `M11`

Updated inventory:

| Status | Before | After |
| --- | ---: | ---: |
| `VALID` | 1 | 2 |
| `BLOCKED` | 4 | 4 |
| `PENDING` | 57 | 56 |
| Total | 62 | 62 |

## Stage 8 promotion factory

`scripts/corpus/parity_pending_promotion.py` is now a reusable promotion factory.

```pg
Stage8PromotionFactory
    GeneralizeSourceResolution -> done
    AddAutoNextSelection -> done
    PromoteNextPending -> done
    RefreshExpansionInventory -> done
```

Factory behavior:

- resolves platform pack source files from live platform loader metadata;
- supports `Attestra`, `Clearstra`, `Routestra`, `Certstra`, and `Scorestra`;
- selects the strongest pending pack with `--auto-next` by descending live probe case count;
- writes the same five-artifact bundle: `source-lock`, `machine-evidence`, `parity-contract`, `parity-receipt`, `provenance-statement`.

Second promoted pack:

- Platform: `Clearstra`
- Pack: `reserve-flow`
- Selection path: `--auto-next`
- Machines: `M5`, `M6`, `M8`
- Probe cases: 3
- Result: `PENDING` → `VALID`

Updated inventory:

| Status | Before Stage 8 | After Stage 8 |
| --- | ---: | ---: |
| `VALID` | 2 | 3 |
| `BLOCKED` | 4 | 4 |
| `PENDING` | 56 | 55 |
| Total | 62 | 62 |

## Stage 9 batch promotion gate

`scripts/corpus/parity_promotion_batch.py` runs bounded promotion batches.

```pg
Stage9BatchPromotionGate
    RunAutoNextLoop(limit=N) -> done
    ValidateAfterEachPromotion -> done
    StopOnFirstProblem -> done
    WriteBatchReport -> done
    RefreshExpansionInventory -> done
```

Batch safety rule:

- each promotion uses the factory from Stage 8;
- after each promotion, `expansion-inventory.json` is rebuilt and validated;
- if any promotion or inventory validation fails, the batch stops and reports the problem;
- the batch does not mutate `BLOCKED` representative evidence.

Executed batch:

- limit: 3
- promoted:
  - `Attestra/action-governance` (`M2`, `M3`)
  - `Attestra/afferent-core` (`M2`, `M3`)
  - `Attestra/afferent-interrupt` (`M2`, `M3`)

Tracked output:

- `seed/parity-provenance/promotion-batch-report.json`
- `seed/parity-provenance/expansion/Attestra/action-governance/*`
- `seed/parity-provenance/expansion/Attestra/afferent-core/*`
- `seed/parity-provenance/expansion/Attestra/afferent-interrupt/*`

Updated inventory:

| Status | Before Stage 9 | After Stage 9 |
| --- | ---: | ---: |
| `VALID` | 3 | 6 |
| `BLOCKED` | 4 | 4 |
| `PENDING` | 55 | 52 |
| Total | 62 | 62 |

## Stage 10 coverage dashboard

`scripts/corpus/parity_coverage_dashboard.py` builds the operator-facing coverage view from tracked parity/provenance evidence.

```pg
Stage10CoverageDashboard
    LoadExpansionInventory -> done
    LoadRepresentativePilotReport -> done
    LoadLatestBatchReport -> done
    SummarizeCoverageByStatusAndPlatform -> done
    SelectNextPendingCandidates -> done
    ValidateDashboardInCI -> done
```

Dashboard scope:

- reads `seed/parity-provenance/expansion-inventory.json`;
- reads `seed/parity-provenance/representative-pilot-report.json`;
- reads `seed/parity-provenance/promotion-batch-report.json`;
- writes `seed/parity-provenance/coverage-dashboard.json`;
- does not create or mutate evidence bundles.

Current coverage:

| Metric | Value |
| --- | ---: |
| Total packs | 62 |
| `VALID` | 6 |
| `BLOCKED` | 4 |
| `PENDING` | 52 |
| Coverage | 9.68% |
| Blocked | 6.45% |
| Pending | 83.87% |

Top next candidates from the dashboard:

| Platform | Pack | Probe cases |
| --- | --- | ---: |
| `Attestra` | `context-boundary` | 2 |
| `Attestra` | `cover-gate` | 2 |
| `Attestra` | `custody-relay` | 2 |

CI gate:

```bash
python scripts/corpus/parity_coverage_dashboard.py \
  --out seed/parity-provenance/coverage-dashboard.json \
  --now 2026-07-16T00:00:00Z \
  --validate
```

## Stage 11 dashboard-driven promotion batch

`scripts/corpus/parity_promotion_batch.py` now supports dashboard-driven selection.

```pg
Stage11DashboardDrivenPromotionBatch
    ReadCoverageDashboard.next_candidates -> done
    PromoteBoundedCandidateBatch(limit=3) -> done
    ValidateInventoryAfterEachPromotion -> done
    RefreshCoverageDashboard -> done
    PreserveRepresentativeBlockedEvidence -> done
```

Execution command:

```bash
python scripts/corpus/parity_promotion_batch.py \
  --evidence-root seed/parity-provenance \
  --limit 3 \
  --now 2026-07-16T00:00:00Z \
  --dashboard seed/parity-provenance/coverage-dashboard.json \
  --refresh-dashboard
```

Promoted from dashboard candidates:

| Platform | Pack | Machines | Probe cases |
| --- | --- | --- | ---: |
| `Attestra` | `context-boundary` | `M2`, `M3` | 2 |
| `Attestra` | `cover-gate` | `M2`, `M3` | 2 |
| `Attestra` | `custody-relay` | `M2`, `M3` | 2 |

Updated inventory:

| Status | Before Stage 11 | After Stage 11 |
| --- | ---: | ---: |
| `VALID` | 6 | 9 |
| `BLOCKED` | 4 | 4 |
| `PENDING` | 52 | 49 |
| Total | 62 | 62 |

Updated dashboard:

| Metric | Before Stage 11 | After Stage 11 |
| --- | ---: | ---: |
| Coverage | 9.68% | 14.52% |
| Pending | 83.87% | 79.03% |

Next dashboard candidates after Stage 11:

| Platform | Pack | Probe cases |
| --- | --- | ---: |
| `Attestra` | `delegation` | 2 |
| `Attestra` | `drift-isolator` | 2 |
| `Attestra` | `gen-cert` | 2 |

## Stage 12 dashboard-driven promotion batch 2

Stage 12 repeats the Stage 11 dashboard-driven loop against the refreshed candidate queue.

```pg
Stage12DashboardDrivenPromotionBatch2
    ReadCoverageDashboard.next_candidates -> done
    PromoteBoundedCandidateBatch(limit=3) -> done
    ValidateInventoryAfterEachPromotion -> done
    RefreshCoverageDashboard -> done
    AdvanceAttestraCoverageFrontier -> done
```

Promoted from dashboard candidates:

| Platform | Pack | Machines | Probe cases |
| --- | --- | --- | ---: |
| `Attestra` | `delegation` | `M2`, `M3` | 2 |
| `Attestra` | `drift-isolator` | `M2`, `M3` | 2 |
| `Attestra` | `gen-cert` | `M2`, `M3` | 2 |

Updated inventory:

| Status | Before Stage 12 | After Stage 12 |
| --- | ---: | ---: |
| `VALID` | 9 | 12 |
| `BLOCKED` | 4 | 4 |
| `PENDING` | 49 | 46 |
| Total | 62 | 62 |

Updated dashboard:

| Metric | Before Stage 12 | After Stage 12 |
| --- | ---: | ---: |
| Coverage | 14.52% | 19.35% |
| Pending | 79.03% | 74.19% |

Next dashboard candidates after Stage 12:

| Platform | Pack | Probe cases |
| --- | --- | ---: |
| `Attestra` | `handback` | 2 |
| `Attestra` | `method-bond` | 2 |
| `Attestra` | `pqc-mesh` | 2 |
