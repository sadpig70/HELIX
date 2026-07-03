#!/usr/bin/env python3
"""CLI for MineralShock."""

import argparse
import json
import sys

from .core import (
    price_refusal_option,
    price_reserve_right,
    render_report,
    simulate_shock,
)
from .samples import write_samples


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(doc, path=None):
    text = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def cmd_sample(args):
    written = write_samples(args.out)
    _dump_json({"written": written})
    return 0


def cmd_price(args):
    data = _load_json(args.input)
    if args.refusal:
        result = price_refusal_option(**data)
    else:
        result = price_reserve_right(**data)
    _dump_json(result, args.out)
    return 0


def cmd_shock(args):
    data = _load_json(args.input)
    result = simulate_shock(data["scenario"], data["reserves"])
    _dump_json(result, args.out)
    return 0


def cmd_report(args):
    data = _load_json(args.input)
    if "scenario_name" in data:
        result = data
    else:
        result = simulate_shock(data["scenario"], data["reserves"])
    text = render_report(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="MineralShock")
    sub = p.add_subparsers(dest="cmd", required=True)

    sample = sub.add_parser("sample", help="emit deterministic mineral and shock fixtures")
    sample.add_argument("--out", default="MineralShock_samples")
    sample.set_defaults(func=cmd_sample)

    price = sub.add_parser("price", help="price a reserve right (or --refusal option)")
    price.add_argument("--input", required=True)
    price.add_argument("--out")
    price.add_argument(
        "--refusal",
        action="store_true",
        help="price a refusal option instead of a reserve right",
    )
    price.set_defaults(func=cmd_price)

    shock = sub.add_parser("shock", help="rehearse a shock scenario against reserves")
    shock.add_argument("--input", required=True)
    shock.add_argument("--out")
    shock.set_defaults(func=cmd_shock)

    report = sub.add_parser("report", help="render a Markdown report")
    report.add_argument("--input", required=True)
    report.add_argument("--out")
    report.set_defaults(func=cmd_report)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
