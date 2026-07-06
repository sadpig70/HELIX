# DESIGN — LoopShield

> Does each invisible automation loop carry a reflex-interrupt pathway with
> delegation underwriting and anomaly attestation?

## Origin

- **Path:** EXPLOIT (recreate)
- **Source fingerprint:** LoopKit + DelegationUnderwriter + AfferentCore
- **Recombination method:** DistantHybridization + LayerFusion

## Gantree

```text
LoopShield // reflex-interrupt attestation for automation loops (done)
    Phase1_Engine // deterministic 5-predicate scoring engine (done)
        ScorePredicate // authority|interrupt|observability|attestation|repair (done)
        ComputeReflexScore // fraction of predicates passed (done)
        ComputeCoverage // high|medium|low classification (done)
        DeriveVerdict // 4-way: cleared|flagged|attenuated|blocked (done)
        HashChainLedger // SHA-256 append-only audit trail (done)
        EvaluateLoops // orchestrate batch evaluation (done)
    Phase2_CLI // sample / evaluate / report subcommands (done)
        CmdSample // write template loop definitions (done)
        CmdEvaluate // evaluate JSON → result + optional MD report (done)
        CmdReport // render Markdown from JSON result (done)
    Phase3_Report // Markdown report renderer (done)
        VerdictDistribution // summary table (done)
        CriticalGapCounts // missing predicate stats (done)
        PerLoopDetail // per-loop predicate breakdown (done)
        LedgerAuditTrail // hash-chain display + seal (done)
    Phase4_Tests // 44 unit tests (done)
        TestScorePredicate // 11 tests for predicate scoring (done)
        TestReflexScore // 3 tests for reflex computation (done)
        TestCoverage // 3 tests for coverage classification (done)
        TestDeriveVerdict // 6 tests for verdict rules (done)
        TestScoreLoop // 5 tests for full loop scoring (done)
        TestLedger // 5 tests for hash-chain integrity (done)
        TestEvaluateLoops // 6 tests for orchestration (done)
        TestReport // 2 tests for report rendering (done)
        TestCLI // 4 tests for CLI subcommands (done)
```

## Reuse plan

| Source (corpus) | Reuse mode | What |
|---|---|---|
| LoopKit | parametrize | observability + repair predicate structure |
| DelegationUnderwriter | copy | authority + liability pre-screening pattern |
| AfferentCore | parametrize | reflex-interrupt pathway + attestation evidence model |

## Verdict scheme

```text
reflex_score < 0.6 or coverage == low          → blocked
≥ 2 critical predicates failed                  → blocked
coverage == medium and any critical gap         → attenuated
coverage == medium and no critical gaps         → flagged
otherwise                                        → cleared
```

Critical predicates: authority, interrupt, attestation.

## Boundary clause

LoopShield does not execute, schedule, or repair automation loops.
It only evaluates whether reflex-interrupt pathways exist.
