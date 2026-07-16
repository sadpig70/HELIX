"""GraphQuarantine command line interface."""

import argparse
import json
import sys

from .core import quarantine
from .ledger import append_receipt, ledger_report
from .samples import sample_case


def _read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _emit(value):
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="graphquarantine")
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("sample")
    sample.add_argument("kind", nargs="?", default="quarantined", choices=["quarantined", "clear", "invalid-baseline"])
    run = sub.add_parser("run")
    run.add_argument("case")
    run.add_argument("--ledger")
    run.add_argument("--recorded-at", default="1970-01-01T00:00:00Z")
    report = sub.add_parser("report")
    report.add_argument("ledger")
    args = parser.parse_args(argv)

    if args.command == "sample":
        _emit(sample_case(args.kind))
        return 0
    if args.command == "run":
        receipt = quarantine(_read_json(args.case))
        if args.ledger:
            append_receipt(args.ledger, receipt, args.recorded_at)
        _emit(receipt)
        return 2 if receipt["decision"] == "INVALID" else 0
    _emit(ledger_report(args.ledger))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

