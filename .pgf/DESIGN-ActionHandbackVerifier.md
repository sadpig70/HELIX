# ActionHandbackVerifier Design @v:1.1

Source seed: `.recreate/runs/001-action-handback-verifier/DESIGN-SEED-ActionHandbackVerifier.md`

## Gantree

```text
ActionHandbackVerifier // delegated action handback verification MVP (done) @v:1.1
    InputContract // handback packet JSON schema and deterministic sample fixtures (done)
        SampleFixtures // valid/thin/breach examples emitted by sample command (done)
        PacketSections // delegation/custody/route/rollback/trace sections (done)
    PredicateEngine // five predicate checks over one handback packet (done) @dep:InputContract
        AuthorityCheck // delegation authority and action scope check (done)
        CustodyCheck // handoff custody continuity check (done)
        RouteCheck // route deviation and rollback trigger check (done)
        RollbackCheck // rollback completion and restoration proof check (done)
        TraceCheck // digest/evidence-path proof surface with private payload rejection (done)
    VerdictAggregate // worst severity aggregate valid/thin/breach (done) @dep:PredicateEngine
    CliTriplet // sample/run/report stdlib CLI (done) @dep:VerdictAggregate
        SampleCommand // emit deterministic fixtures (done)
        RunCommand // evaluate one packet and emit JSON verdict; --ledger appends record (done)
        ReportCommand // emit Markdown report with evidence paths (done)
    ClosedAuditLedger // append-only hash-chain ledger + verify subcommand (done) @dep:VerdictAggregate
        LedgerAppend // deterministic record with result_hash/record_hash/prev_hash (done)
        LedgerVerify // tamper detection via chain + record re-validation (done)
        VerifyCommand // verify --ledger CLI (done)
    TestSuite // deterministic acceptance tests incl. ledger (done) @dep:CliTriplet,ClosedAuditLedger
    Verify // 3-perspective PGF verification (done) @dep:TestSuite
```

## PPR

```python
def evaluate_handback(packet: dict) -> dict:
    """Evaluate one delegated field-action handback packet."""
    checks = [
        check_authority(packet),
        check_custody(packet),
        check_route(packet),
        check_rollback(packet),
        check_trace(packet),
    ]
    verdict = worst_severity(checks, order=["valid", "thin", "breach"])
    return {
        "handback_id": packet.get("handback_id", ""),
        "verdict": verdict,
        "checks": checks,
        "aggregate_digest": digest_public_surface(packet),
    }
    # acceptance_criteria:
    #   - same packet returns same verdict and digest across repeated runs
    #   - route pass cannot override authority/custody breach
    #   - private payload fields are rejected or excluded from digest output
    #   - every non-valid check cites an evidence_path or missing field

def check_authority(packet: dict) -> dict:
    """Delegation authority predicate."""
    delegation = packet.get("delegation", {})
    required = ["authority_id", "delegated_to", "action", "allowed_actions", "evidence_path"]
    if missing(required, delegation):
        return thin_or_breach("authority", missing(required, delegation))
    if delegation["action"] not in delegation["allowed_actions"]:
        return breach("authority", "action outside delegated authority", delegation.get("evidence_path"))
    if expired(delegation.get("expires_at"), packet.get("handback_time")):
        return breach("authority", "delegation expired before handback", delegation.get("evidence_path"))
    return valid("authority", delegation["evidence_path"])

def check_custody(packet: dict) -> dict:
    """Custody continuity predicate."""
    custody = packet.get("custody", {})
    required = ["artifact_id", "from_actor", "to_actor", "handback_confirmed", "evidence_path"]
    if missing(required, custody):
        return thin_or_breach("custody", missing(required, custody))
    if custody["to_actor"] != packet.get("delegation", {}).get("delegated_to"):
        return breach("custody", "custody receiver does not match delegated actor", custody["evidence_path"])
    if not custody["handback_confirmed"]:
        return breach("custody", "handback not confirmed", custody["evidence_path"])
    return valid("custody", custody["evidence_path"])

def check_route(packet: dict) -> dict:
    """Route deviation and rollback trigger predicate."""
    route = packet.get("route", {})
    required = ["planned_route_id", "actual_route_id", "status", "evidence_path"]
    if missing(required, route):
        return thin_or_breach("route", missing(required, route))
    if route["status"] == "failed":
        return breach("route", "route check failed", route["evidence_path"])
    if route["status"] == "deviated" and not route.get("rollback_required"):
        return thin("route", "route deviated but rollback requirement is not declared", route["evidence_path"])
    return valid("route", route["evidence_path"])

def check_rollback(packet: dict) -> dict:
    """Rollback duty predicate."""
    rollback = packet.get("rollback", {})
    required = ["required", "completed", "evidence_path"]
    if missing(required, rollback):
        return thin_or_breach("rollback", missing(required, rollback))
    if rollback["required"] and not rollback["completed"]:
        return breach("rollback", "required rollback not completed", rollback["evidence_path"])
    if rollback["required"] and not rollback.get("restoration_hash"):
        return thin("rollback", "rollback completed without restoration_hash", rollback["evidence_path"])
    return valid("rollback", rollback["evidence_path"])

def check_trace(packet: dict) -> dict:
    """Evidence trace predicate; reject private payload storage."""
    trace = packet.get("trace", {})
    if has_private_payload(packet):
        return breach("trace", "packet contains private payload field", trace.get("evidence_path", ""))
    if not trace.get("digest") or not trace.get("evidence_path"):
        return thin("trace", "trace digest or evidence_path missing", trace.get("evidence_path", ""))
    if not is_sha256_hex(trace["digest"]):
        return breach("trace", "trace digest is not sha256 hex", trace["evidence_path"])
    return valid("trace", trace["evidence_path"])
```

## PPR — ClosedAuditLedger

```python
def append_record(path: str, result: dict) -> dict:
    """Append a deterministic hash-chain record for one verdict result.

    The record excludes wall-clock timestamps so the chain is reproducible.
    """
    prev_hash = last_record_hash(path)            # "" for genesis
    record = {
        "index": len(read_ledger(path)),
        "handback_id": result.get("handback_id", ""),
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

- Acceptance: run CLI sample, run valid/thin/breach fixtures, assert deterministic verdicts.
- Quality: stdlib-only, small pure predicate functions, no hidden global clock.
- Architecture: Gantree maps to `ActionHandbackVerifier/verifier.py`, `ledger.py`, `cli.py`, `samples.py`, tests.
- Ledger: append three verdicts, verify passes; tamper any field, verify fails with non-zero exit.
