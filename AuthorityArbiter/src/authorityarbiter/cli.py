"""AuthorityArbiter CLI."""

import argparse
import json
import sys

from .engine import arbitrate
from .ledger import append_receipt, ledger_report
from .samples import sample_request


def _load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Delegated policy conflict arbitration")
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("sample")
    sample.add_argument("--kind", choices=("allow", "deny", "tie"), default="allow")
    run = sub.add_parser("run")
    run.add_argument("request")
    run.add_argument("--ledger")
    run.add_argument("--now")
    report = sub.add_parser("report")
    report.add_argument("--ledger", required=True)
    args = parser.parse_args(argv)
    if args.command == "sample":
        print(json.dumps(sample_request(args.kind), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "report":
        result = ledger_report(args.ledger)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["valid"] else 4
    if bool(args.ledger) != bool(args.now):
        parser.error("--ledger and --now must be supplied together")
    receipt = arbitrate(_load(args.request))
    if args.ledger:
        append_receipt(args.ledger, receipt, args.now)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 3 if receipt["decision"] == "ESCALATE" else 0


if __name__ == "__main__":
    sys.exit(main())
