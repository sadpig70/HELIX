# HELIXCorpusSupply ContractPlane @v:1.0

## Gantree

```text
ContractPlane // immutable supply contracts (done) @v:1.0
    ManifestContract // corpus-manifest/1.0 (done)
        IdentityFields // corpus_id, name, schema, revision (done)
        OriginFields // source kind, pinned locator, license, source hash (done)
        CharacterFields // domain, verb, input/output shape (done)
        GeneFields // reusable genes and machine hypothesis (done)
        VerificationFields // reproducibility and evidence declarations (done)
    ReceiptContract // corpus-admission-receipt/1.0 (done)
        DecisionFields // tier, decision, reasons, manifest hash (done)
        ChainFields // previous event hash and event hash (done)
        ReviewBinding // evidence promotion review receipt hash (done)
        ReviewReceiptContract // reviewer, approve verdict, manifest hash (done)
    PolicyContract // versioned deterministic thresholds (done)
        GenerativePolicy // gene and provenance requirements (done)
        EvidencePolicy // execution and human review requirements (done)
        CondenseBoundary // promotion never implies CONDENSE (done)
    CompatibilityContract // coexist with base-pairing entries (done)
        LegacySchemaIsolation // old corpus-entry schema unchanged (done)
        MigrationEnvelope // legacy rows become hypothesis-only manifests (done)
    RevisionContract // generative-to-evidence evolution without history rewrite (done)
        MonotonicRevision // revision must increase for changed manifest bytes (done)
        ImmutableSnapshot // revisions/N.json never changes after creation (done)
        CurrentPointer // manifest.json materializes the latest snapshot (done)
        ReceiptBinding // each receipt binds its exact revision hash (done)
        SupersedesBinding // revision N binds prior admitted manifest hash (done)
```

## PPR

```python
def validate_manifest_contract(root: str, manifest: dict) -> list[str]:
    """Validate structural and semantic hard-gate requirements."""
    # acceptance_criteria:
    #   - draft-07 schema stays inside HELIX stdlib validator subset
    #   - source hash is a lowercase sha256 digest
    #   - corpus_id is safe as one filesystem path component
    #   - external/implemented sources carry pinned revision and license evidence
    #   - evidence locators resolve under an injected evidence root and hashes match real bytes
    #   - machine.status is hypothesis or substantiated, never implicit
    return validate_schema(manifest) + validate_semantics(manifest)

def manifest_digest(manifest: dict) -> str:
    """Stable content identity independent of whitespace and key order."""
    # acceptance_criteria:
    #   - canonical JSON uses sorted keys and compact separators
    #   - same object yields same sha256 across runs
    return sha256(canonical_json(manifest))
```
