#!/usr/bin/env python3
"""CLI for BioClock."""

import argparse
import json
import sys

from .core import certify_bio_clock, render_report, track_drift
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


def cmd_track(args):
    protocol = _load_json(args.protocol)
    evidence = _load_json(args.evidence)
    result = track_drift(protocol, evidence)
    _dump_json(result, args.out)
    return 0


def cmd_certify(args):
    drift_report = _load_json(args.drift)
    quarantine_schedule = _load_json(args.quarantine)
    result = certify_bio_clock(drift_report, quarantine_schedule)
    _dump_json(result, args.out)
    return 0


def cmd_report(args):
    result = _load_json(args.input)
    text = render_report(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="bio-clock")
    sub = p.add_subparsers(dest="cmd", required=True)

    sample = sub.add_parser("sample", help="emit deterministic protocol/evidence/quarantine fixtures")
    sample.add_argument("--out", default="BioClock_samples")
    sample.set_defaults(func=cmd_sample)

    track = sub.add_parser("track", help="measure evidence drift for one protocol")
    track.add_argument("--protocol", required=True)
    track.add_argument("--evidence", required=True)
    track.add_argument("--out")
    track.set_defaults(func=cmd_track)

    certify = sub.add_parser("certify", help="certify a bio clock from a drift report and quarantine schedule")
    certify.add_argument("--drift", required=True)
    certify.add_argument("--quarantine", required=True)
    certify.add_argument("--out")
    certify.set_defaults(func=cmd_certify)

    report = sub.add_parser("report", help="render a Markdown report from a drift or certification result")
    report.add_argument("--input", required=True)
    report.add_argument("--out")
    report.set_defaults(func=cmd_report)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
