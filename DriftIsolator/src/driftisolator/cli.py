import argparse
import json
import sys
from .core import isolate
from .ledger import append_receipt, ledger_report
from .samples import sample_case


def main(argv=None):
    parser=argparse.ArgumentParser(description="Minimal runtime-drift counterexample isolation"); sub=parser.add_subparsers(dest="command",required=True)
    sample=sub.add_parser("sample"); sample.add_argument("--kind",choices=("drift","no-drift","invalid-baseline"),default="drift")
    run=sub.add_parser("run"); run.add_argument("case"); run.add_argument("--ledger"); run.add_argument("--now")
    report=sub.add_parser("report"); report.add_argument("--ledger",required=True); args=parser.parse_args(argv)
    if args.command=="sample": print(json.dumps(sample_case(args.kind),indent=2,sort_keys=True)); return 0
    if args.command=="report":
        result=ledger_report(args.ledger); print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["valid"] else 4
    if bool(args.ledger)!=bool(args.now): parser.error("--ledger and --now must be supplied together")
    with open(args.case,"r",encoding="utf-8") as handle: case=json.load(handle)
    receipt=isolate(case)
    if args.ledger: append_receipt(args.ledger,receipt,args.now)
    print(json.dumps(receipt,indent=2,sort_keys=True)); return 2 if receipt["decision"]=="INVALID" else 0


if __name__=="__main__": sys.exit(main())
