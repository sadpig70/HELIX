"""Append-only hash-chain ledger for ProofEscrow receipts."""

import copy
import json
import os

from .canonical import digest


EVENT_SCHEMA = "proofescrow-ledger-event/1.0"


def read_ledger(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_ledger(path):
    problems = []
    previous = ""
    for index, event in enumerate(read_ledger(path), start=1):
        label = f"event[{index}]"
        if event.get("schema") != EVENT_SCHEMA:
            problems.append(f"{label}: invalid schema")
        if event.get("sequence") != index:
            problems.append(f"{label}: invalid sequence")
        if event.get("previous_event_sha256", "") != previous:
            problems.append(f"{label}: broken previous hash")
        receipt = event.get("receipt", {})
        receipt_body = copy.deepcopy(receipt)
        claimed_receipt = receipt_body.pop("receipt_sha256", None)
        if claimed_receipt != digest(receipt_body):
            problems.append(f"{label}: invalid receipt hash")
        event_body = copy.deepcopy(event)
        claimed_event = event_body.pop("event_sha256", None)
        if claimed_event != digest(event_body):
            problems.append(f"{label}: invalid event hash")
        previous = str(claimed_event or "")
    return problems


def append_receipt(path, receipt, recorded_at):
    if verify_ledger(path):
        raise ValueError("refusing to append to an invalid ledger")
    events = read_ledger(path)
    event = {
        "schema": EVENT_SCHEMA,
        "sequence": len(events) + 1,
        "previous_event_sha256": events[-1]["event_sha256"] if events else "",
        "recorded_at": recorded_at,
        "receipt": copy.deepcopy(receipt),
    }
    event["event_sha256"] = digest(event)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def ledger_report(path):
    events = read_ledger(path)
    problems = verify_ledger(path)
    return {
        "valid": not problems,
        "problems": problems,
        "events": len(events),
        "released": sum(event.get("receipt", {}).get("decision") == "RELEASED" for event in events),
        "held": sum(event.get("receipt", {}).get("decision") == "HELD" for event in events),
        "head_sha256": events[-1]["event_sha256"] if events else "",
    }
