"""Append-only hash-chain ledger."""

import copy
import json
import os

from .canonical import digest


EVENT_SCHEMA = "authority-arbiter-ledger-event/1.0"


def read_ledger(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_ledger(path):
    problems, previous = [], ""
    for sequence, event in enumerate(read_ledger(path), start=1):
        label = f"event[{sequence}]"
        if event.get("schema") != EVENT_SCHEMA or event.get("sequence") != sequence:
            problems.append(f"{label}: invalid contract")
        if event.get("previous_event_sha256", "") != previous:
            problems.append(f"{label}: broken previous hash")
        receipt = copy.deepcopy(event.get("receipt", {}))
        claimed_receipt = receipt.pop("receipt_sha256", None)
        if claimed_receipt != digest(receipt):
            problems.append(f"{label}: invalid receipt hash")
        body = copy.deepcopy(event)
        claimed = body.pop("event_sha256", None)
        if claimed != digest(body):
            problems.append(f"{label}: invalid event hash")
        previous = str(claimed or "")
    return problems


def append_receipt(path, receipt, recorded_at):
    if verify_ledger(path):
        raise ValueError("refusing to append to an invalid ledger")
    events = read_ledger(path)
    event = {"schema": EVENT_SCHEMA, "sequence": len(events) + 1,
             "previous_event_sha256": events[-1]["event_sha256"] if events else "",
             "recorded_at": recorded_at, "receipt": copy.deepcopy(receipt)}
    event["event_sha256"] = digest(event)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def ledger_report(path):
    events, problems = read_ledger(path), verify_ledger(path)
    counts = {key: 0 for key in ("ARBITRATED_ALLOW", "ARBITRATED_DENY", "ESCALATE")}
    for event in events:
        decision = event.get("receipt", {}).get("decision")
        if decision in counts:
            counts[decision] += 1
    return {"valid": not problems, "problems": problems, "events": len(events),
            "decisions": counts, "head_sha256": events[-1]["event_sha256"] if events else ""}
