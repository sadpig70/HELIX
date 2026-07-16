"""Append-only hook-circuit receipt ledger."""

import copy
import json
import os

from .core import digest


def read_ledger(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_ledger(path):
    problems, previous = [], ""
    for seq, event in enumerate(read_ledger(path), 1):
        if event.get("sequence") != seq or event.get("previous_event_sha256", "") != previous:
            problems.append(f"event[{seq}]: broken chain")
        receipt = copy.deepcopy(event.get("receipt", {}))
        claimed_receipt = receipt.pop("receipt_sha256", None)
        if claimed_receipt != digest(receipt):
            problems.append(f"event[{seq}]: invalid receipt hash")
        body = copy.deepcopy(event)
        claimed = body.pop("event_sha256", None)
        if claimed != digest(body):
            problems.append(f"event[{seq}]: invalid event hash")
        previous = str(claimed or "")
    return problems


def append_receipt(path, receipt, recorded_at):
    if verify_ledger(path):
        raise ValueError("invalid ledger")
    events = read_ledger(path)
    event = {
        "sequence": len(events) + 1,
        "previous_event_sha256": events[-1]["event_sha256"] if events else "",
        "recorded_at": recorded_at,
        "receipt": copy.deepcopy(receipt),
    }
    event["event_sha256"] = digest(event)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def ledger_report(path):
    events, problems = read_ledger(path), verify_ledger(path)
    return {
        "valid": not problems,
        "problems": problems,
        "events": len(events),
        "tripped": sum(event.get("receipt", {}).get("decision") == "TRIPPED" for event in events),
        "allowed": sum(event.get("receipt", {}).get("decision") == "ALLOWED" for event in events),
        "head_sha256": events[-1]["event_sha256"] if events else "",
    }

