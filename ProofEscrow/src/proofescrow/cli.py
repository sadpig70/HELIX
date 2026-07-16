"""ProofEscrow command-line interface."""

import argparse
import json
import sys

from .engine import evaluate
from .ledger import append_receipt, ledger_report
from .samples import sample_bundle


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evidence-bound artifact release escrow")
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("sample")
    sample.add_argument("--kind", choices=("released", "held-signature", "held-behavior"), default="released")
    run = sub.add_parser("run")
    run.add_argument("request")
    run.add_argument("--trust-store", required=True)
    run.add_argument("--ledger")
    run.add_argument("--now")
    report = sub.add_parser("report")
    report.add_argument("--ledger", required=True)
    args = parser.parse_args(argv)
    if args.command == "sample":
        print(json.dumps(sample_bundle(args.kind), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "report":
        result = ledger_report(args.ledger)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["valid"] else 4
    if bool(args.ledger) != bool(args.now):
        parser.error("--ledger and --now must be supplied together")
    receipt = evaluate(_load(args.request), _load(args.trust_store))
    if args.ledger:
        append_receipt(args.ledger, receipt, args.now)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["decision"] == "RELEASED" else 2


if __name__ == "__main__":
    sys.exit(main())
