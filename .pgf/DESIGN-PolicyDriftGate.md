# PolicyDriftGate Design @v:1.0

Source seed: `.recreate/runs/003-policydriftgate/DESIGN-SEED-PolicyDriftGate.md`

## Gantree

```text
PolicyDriftGate // AI agent behavior policy drift and loop interruption safety gate (in-progress) @v:1.0
    InputContract // audit packet JSON schema and deterministic sample fixtures (in-progress)
        SampleFixtures // cleared/warned/interrupted examples emitted by sample command (in-progress)
        PacketSections // behavior/dossier/runtime_signal sections (in-progress)
    PredicateEngine // predicate checks over behavioral, deployment log, and loop signals (in-progress) @dep:InputContract
        BehaviorCheck // behavior policy drift check comparing candidate vs baseline (in-progress)
        DossierCheck // deployment log drift compliance audit (in-progress)
        LoopSignalCheck // real-time loop detection and interrupt trigger (in-progress)
    VerdictAggregate // worst severity aggregate cleared/warned/interrupted with loop interruption bypass (in-progress) @dep:PredicateEngine
    CliTriplet // sample/run/report stdlib CLI (in-progress) @dep:VerdictAggregate
        SampleCommand // emit deterministic fixtures (in-progress)
        RunCommand // evaluate one packet, emit JSON verdict, optional --ledger append (in-progress)
        ReportCommand // emit Markdown report with drift analysis and attestation details (in-progress)
    ClosedAuditLedger // append-only hash-chain ledger + verify subcommand (in-progress) @dep:VerdictAggregate
        LedgerAppend // deterministic record with result_hash/record_hash/prev_hash (in-progress)
        LedgerVerify // tamper detection via chain + record re-validation (in-progress)
        VerifyCommand // verify --ledger CLI with JSON result + exit code (in-progress)
    TestSuite // deterministic acceptance tests (in-progress) @dep:CliTriplet,ClosedAuditLedger
    Verify // 3-perspective PGF verification (in-progress) @dep:TestSuite
```

## PPR

```python
def evaluate_policy_drift(packet: dict) -> dict:
    """Evaluate AI agent behavior policy, deployment dossier, and loop signals."""
    checks = [
        check_behavior(packet),
        check_dossier(packet),
        check_loop_signal(packet),
    ]
    # Loop signal interruption takes priority and overrides others
    loop_result = next((c for c in checks if c["predicate"] == "loop_signal"), None)
    if loop_result and loop_result["verdict"] == "interrupted":
        verdict = "interrupted"
    else:
        verdict = worst_severity(checks, order=["cleared", "warned", "interrupted"])
        
    return {
        "audit_id": packet.get("audit_id", ""),
        "verdict": verdict,
        "checks": checks,
        "aggregate_digest": digest_public_surface(packet),
    }
    # acceptance_criteria:
    #   - same packet returns same verdict and digest across repeated runs
    #   - loop_signal interrupt overrides cleared/warned policy checks
    #   - private payload fields are rejected or excluded from digest output
    #   - every non-cleared check cites an evidence_path or missing field

def check_behavior(packet: dict) -> dict:
    """Behavior policy drift predicate comparing candidate vs baseline."""
    behavior = packet.get("behavior", {})
    required = ["baseline_hash", "candidate_hash", "drift_metric", "threshold", "evidence_path"]
    if missing(required, behavior):
        return thin_or_breach("behavior", missing(required, behavior))
    if behavior["drift_metric"] > behavior["threshold"]:
        return breached("behavior", "behavior policy drift exceeds threshold", behavior["evidence_path"])
    if behavior["drift_metric"] > behavior["threshold"] * 0.8:
        return warned("behavior", "behavior policy drift approaching threshold", behavior["evidence_path"])
    return cleared("behavior", behavior["evidence_path"])

def check_dossier(packet: dict) -> dict:
    """Deployment log drift compliance audit predicate."""
    dossier = packet.get("dossier", {})
    required = ["approved_baseline_version", "logs_analyzed", "non_compliance_count", "evidence_path"]
    if missing(required, dossier):
        return thin_or_breach("dossier", missing(required, dossier))
    if dossier["non_compliance_count"] > 0:
        return breached("dossier", f"detected {dossier['non_compliance_count']} non-compliance events", dossier["evidence_path"])
    return cleared("dossier", dossier["evidence_path"])

def check_loop_signal(packet: dict) -> dict:
    """Real-time loop detection and safety interrupt predicate."""
    signal = packet.get("runtime_signal", {})
    required = ["loop_detected", "attestation_issued", "evidence_path"]
    if missing(required, signal):
        return thin_or_breach("loop_signal", missing(required, signal))
    if signal["loop_detected"]:
        if not signal["attestation_issued"]:
            return warned("loop_signal", "loop detected but no attestation issued yet", signal["evidence_path"])
        return breached("loop_signal", "abnormal loop detected and safety interrupted", signal["evidence_path"])
    return cleared("loop_signal", signal["evidence_path"])
```

## PPR — ClosedAuditLedger

```python
def append_record(path: str, result: dict) -> dict:
    """Append a deterministic hash-chain record for one audit result.

    The record excludes wall-clock timestamps so the chain is reproducible.
    """
    prev_hash = last_record_hash(path)            # "" for genesis
    record = {
        "index": len(read_ledger(path)),
        "audit_id": result.get("audit_id", ""),
        "verdict": result.get("verdict", ""),
        "aggregate_digest": result.get("aggregate_digest", ""),
        "result_hash": sha256_json(result),        # canonical JSON of full result
        "prev_hash": prev_hash,
    }
    record["record_hash"] = sha256_json(record)    # record excluding record_hash
    append_jsonl(path, record)
    return record
    # acceptance_criteria:
    #   - same result always produces the same record_hash
    #   - first record prev_hash == "" (genesis)
    #   - each subsequent record prev_hash == previous record_hash
    #   - record_hash recomputes from all fields except itself

def verify_ledger(path: str) -> dict:
    """Re-validate the append-only hash chain.

    Returns {"valid": bool, "records": int, "error": str}.
    Detects index gaps, broken prev_hash links, and field tampering
    (record_hash mismatch).
    """
    records = read_ledger(path)
    prev_hash = ""
    for i, rec in enumerate(records):
        if rec["index"] != i:           fail(f"record {i}: index mismatch")
        if rec["prev_hash"] != prev_hash: fail(f"record {i}: prev_hash mismatch (chain broken)")
        if rec["record_hash"] != sha256_json(without(rec, "record_hash")):
            fail(f"record {i}: record_hash mismatch (tampered)")
        prev_hash = rec["record_hash"]
    return {"valid": True, "records": len(records), "error": ""}
```

## Verify Strategy

- Acceptance: run CLI sample, run cleared/warned/interrupted fixtures, assert deterministic verdicts.
- Quality: stdlib-only, small pure predicate helpers, no hidden global clock.
- Architecture: Gantree maps to `PolicyDriftGate/verifier.py`, `ledger.py`, `cli.py`, `samples.py`, tests.
- Ledger: append three verdicts, verify passes; tamper any field, verify fails with non-zero exit.
