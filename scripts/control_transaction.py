#!/usr/bin/env python3
"""CLI for durable HELIX transaction state."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.helix_transaction import (new_transaction, record_admission_result,
                                    transition, verify_transaction)
from engines.transaction_store import load_transaction, save_transaction


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--path", required=True)
    init.add_argument("--id", required=True)
    init.add_argument("--intent-digest", required=True)
    event = sub.add_parser("event")
    event.add_argument("--path", required=True)
    event.add_argument("--event-id", required=True)
    event.add_argument("--event", required=True)
    event.add_argument("--receipt-sha256")
    record = sub.add_parser("record-result")
    record.add_argument("--path", required=True)
    record.add_argument("--result", required=True)
    for name in ("status", "verify"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--path", required=True)
    args = parser.parse_args(argv)
    if args.command == "init":
        if load_transaction(args.path) is not None:
            raise SystemExit("transaction already exists")
        tx = new_transaction(args.id, args.intent_digest)
        save_transaction(args.path, tx)
    else:
        tx = load_transaction(args.path)
        if tx is None:
            raise SystemExit("transaction not found")
        if args.command == "event":
            tx = transition(tx, args.event_id, args.event,
                            args.receipt_sha256)
            save_transaction(args.path, tx)
        elif args.command == "record-result":
            with open(args.result, "r", encoding="utf-8") as f:
                tx = record_admission_result(tx, json.load(f))
            save_transaction(args.path, tx)
        elif args.command == "verify":
            problems = verify_transaction(tx)
            print(json.dumps({"valid": not problems, "problems": problems},
                             ensure_ascii=False, sort_keys=True))
            return 0 if not problems else 1
    print(json.dumps(tx, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
