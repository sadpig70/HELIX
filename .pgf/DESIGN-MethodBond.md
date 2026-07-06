# DESIGN — MethodBond

> Is a published method or model artifact properly licensed, independently reproducible, and certified against its declared behavior baseline?

## Gantree

```text
MethodBond // method-publishing trust-bundle gate (designing) @v:1.0
    SchemaLayer // license + reproducibility + certification schema contracts (designing)
        LoadArtifact // read artifact descriptor JSON (designing)
        ValidateLicense // MLX schema validation: required fields + allowed values (designing)
        ValidateReproSchema // independent provenance list + input/output hash presence (designing)
        ValidateCertSchema // baseline + candidate policy presence (designing)
    EngineLayer // deterministic verdict computation (designing)
        CheckLicense // verify license terms are complete and values in allow-list (designing)
        CheckReproducibility // compare output hashes across provenances (designing)
        CheckCertification // compute baseline-vs-candidate drift (designing)
        ComposeVerdict // certified / conditional / rejected (designing)
    LedgerLayer // hash-chained audit log (designing)
        AppendEntry // SHA-256 chain every evaluation (designing)
    CLILayer // sample / evaluate / report triplet (designing)
        SampleCommand // emit a valid sample artifact (designing)
        EvaluateCommand // run engine on input file (designing)
        ReportCommand // render Markdown report (designing)
    TestLayer // unittest coverage (designing)
        EngineTests // positive/negative/edge cases (designing)
        CLITests // integration tests (designing)
    Packaging // pyproject + README + LICENSE + .gitignore (designing)
```

## PPR

```python
def MethodBond.evaluate(descriptor_path, now=None):
    artifact = LoadArtifact(descriptor_path)
    license_ok, license_detail = CheckLicense(artifact.license)
    repro_ok, repro_detail = CheckReproducibility(artifact.provenances)
    cert_ok, cert_detail = CheckCertification(artifact.baseline, artifact.candidate)
    verdict = ComposeVerdict(license_ok, repro_ok, cert_ok, details)
    AppendEntry(artifact, verdict, now=now)
    return {"verdict": verdict, "license": license_detail, "repro": repro_detail, "cert": cert_detail}

def ComposeVerdict(license_ok, repro_ok, cert_ok, details):
    if license_ok and repro_ok and cert_ok:
        return "certified"
    if (not license_ok) or (not repro_ok):
        return "rejected"
    return "conditional"  # license+repro OK but cert drift or partial policy gap

def AppendEntry(artifact, verdict, now=None):
    prev = read_last_hash(LEDGER_PATH)
    entry = {"timestamp": now or utc_now(), "artifact_id": artifact.id,
             "verdict": verdict, "prev_hash": prev}
    entry["hash"] = sha256(json.dumps(entry, sort_keys=True))
    append_line(LEDGER_PATH, entry)
```

## Verdict Scheme

- `certified`: license valid, reproducibility proven, baseline conformance clean.
- `conditional`: license+repro OK, but baseline has a recoverable drift or waiver.
- `rejected`: missing/invalid license, unreproducible build, or unacceptable baseline drift.

## Acceptance Criteria

1. `python -m MethodBond sample` emits a valid sample artifact descriptor.
2. `python -m MethodBond evaluate sample.json` returns `certified` and appends a ledger entry.
3. `python -m MethodBond report sample.json` renders Markdown with verdict rationale.
4. `python -m unittest discover -s tests -q` passes ≥20 tests.
5. `py_compile` succeeds on all source files.
