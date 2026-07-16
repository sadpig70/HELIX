# HELIXCorpusSupply OperationsPlane @v:1.0

## Gantree

```text
OperationsPlane // filesystem and operator surfaces (done) @v:1.0
    ItemStore // immutable manifest snapshots (done)
        ResolveCorpusRoot // injected root or seed/corpus (done)
        SafeItemPath // validated ID cannot escape corpus root (done)
        AtomicSnapshotWrite // manifest.json by corpus_id (done)
        RevisionSnapshotWrite // immutable revisions/N.json (done)
        ExistingSnapshotCheck // identical is no-op, same/lower revision mismatch is conflict (done)
    CorpusCli // helix.py corpus command family (done) @dep:ItemStore
        ValidateCommand // validate a manifest without writes (done)
        IntakeCommand // snapshot a valid manifest (done)
        AdmitCommand // generative admission (done)
        PromoteCommand // evidence promotion with review receipt (done)
        StatusCommand // materialized state from ledger (done)
        HealthCommand // counts, chain integrity and quarantine pressure (done)
        MigrateCommand // legacy project-list preview or emit (done)
    MigrationPlane // backward-compatible bootstrap (done) @dep:CorpusCli
        ParseLegacyList // extract project names and descriptions (done)
        EmitHypothesisManifest // generative-only incomplete manifests (done)
        NoAutoAdmission // migration never fabricates provenance (done)
    ReportingPlane // deterministic operational summaries (done) @dep:MigrationPlane
        TierCounts // discovered/generative/evidence counts (done)
        ChainStatus // event count and validity (done)
        ProblemCounts // quarantine and rejection reasons (done)
```

## PPR

```python
def corpus_cli(argv: list[str], root: str) -> int:
    """Dispatch a bounded offline corpus operation."""
    # acceptance_criteria:
    #   - usage error=2, gate refusal=4, success=0
    #   - JSON output is machine-readable
    #   - no command performs network access
    return dispatch(argv, root)

def migrate_legacy_project_list(path: str) -> list[dict]:
    """Create honest migration candidates without admission or fake evidence."""
    # acceptance_criteria:
    #   - every markdown project bullet is represented once
    #   - origin.kind=legacy_inventory and machine.status=hypothesis
    #   - verification flags are false and no ledger event is appended
    return [legacy_candidate(row) for row in parse_project_rows(path)]
```
