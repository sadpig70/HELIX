#!/usr/bin/env python3
"""Consumed-ideas ledger lint for IdeaFirst.

Validates .idea-ledger/consumed_ideas.yaml beyond YAML well-formedness:

- schema: required keys, types, parseable consumed_at_utc, implementation shape
- uniqueness: (idea_id, source_chain.cix) pairs, normalized_title, repo_url
- drift: semantic_family near-duplicates (token Jaccard + sequence ratio),
  alias collisions against other entries' normalized_title

Exit code: 0 = clean or warnings only, 1 = errors (or warnings with --strict).
Derivative-exclusion entries (marked by `excluded_reason`) are expected to sit
near their consumed siblings, so their family near-matches are reported as info.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

REQUIRED_KEYS = ["idea_id", "title", "normalized_title", "aliases", "semantic_family",
                 "source_chain", "consumed_at_utc", "reuse_policy"]
FAMILY_JACCARD_THRESHOLD = 0.6
FAMILY_RATIO_THRESHOLD = 0.8


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def tokens(family: str) -> set[str]:
    return {t for t in normalize(family).split("-") if t}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def lint_schema(entries: list[Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        ref = f"entry[{index}]"
        if not isinstance(entry, dict):
            findings.append({"level": "error", "code": "ENTRY_TYPE", "ref": ref,
                             "message": "entry must be a mapping"})
            continue
        ref = entry.get("idea_id") or ref
        for key in REQUIRED_KEYS:
            if key not in entry:
                findings.append({"level": "error", "code": "MISSING_KEY", "ref": ref,
                                 "message": f"missing required key: {key}"})
        if not isinstance(entry.get("aliases"), list):
            findings.append({"level": "error", "code": "ALIASES_TYPE", "ref": ref,
                             "message": "aliases must be a list"})
        chain = entry.get("source_chain")
        if not isinstance(chain, dict) or not chain.get("cix"):
            findings.append({"level": "error", "code": "SOURCE_CHAIN", "ref": ref,
                             "message": "source_chain.cix is required"})
        try:
            datetime.fromisoformat(str(entry.get("consumed_at_utc", "")))
        except ValueError:
            findings.append({"level": "error", "code": "TIMESTAMP", "ref": ref,
                             "message": "consumed_at_utc is not ISO-8601"})
        implementations = entry.get("implementations")
        is_exclusion = bool(entry.get("excluded_reason"))
        if implementations is None and not is_exclusion:
            findings.append({"level": "warning", "code": "NO_IMPLEMENTATIONS", "ref": ref,
                             "message": "consumed entry has neither implementations nor excluded_reason"})
        if isinstance(implementations, list):
            for impl in implementations:
                if not isinstance(impl, dict) or not impl.get("repo_url"):
                    findings.append({"level": "error", "code": "IMPL_SHAPE", "ref": ref,
                                     "message": "implementation needs a repo_url"})
        if entry.get("normalized_title") and normalize(entry.get("title", "")) != entry["normalized_title"]:
            findings.append({"level": "warning", "code": "TITLE_MISMATCH", "ref": ref,
                             "message": "normalized_title does not match normalize(title)"})
    return findings


def lint_uniqueness(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_ids: dict[tuple[str, str], str] = {}
    seen_titles: dict[str, str] = {}
    seen_repos: dict[str, tuple[str, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ref = str(entry.get("idea_id", "?"))
        cix = str((entry.get("source_chain") or {}).get("cix", ""))
        id_key = (ref, cix)
        if id_key in seen_ids:
            findings.append({"level": "error", "code": "DUP_IDEA_ID", "ref": ref,
                             "message": f"duplicate (idea_id, cix) pair also at {seen_ids[id_key]}"})
        seen_ids[id_key] = ref
        ntitle = str(entry.get("normalized_title", ""))
        if ntitle:
            if ntitle in seen_titles:
                findings.append({"level": "error", "code": "DUP_TITLE", "ref": ref,
                                 "message": f"normalized_title also used by {seen_titles[ntitle]}"})
            seen_titles[ntitle] = ref
        for impl in entry.get("implementations") or []:
            repo = str(impl.get("repo_url", "")) if isinstance(impl, dict) else ""
            if repo:
                if repo in seen_repos and seen_repos[repo][0] != ref:
                    # Two ideas from the SAME round merged into one repo is a documented
                    # pattern (e.g. wastestack = IDEA-002+IDEA-019); cross-round reuse is not.
                    same_round = seen_repos[repo][1] == cix
                    findings.append({
                        "level": "info" if same_round else "warning",
                        "code": "MERGED_IMPL" if same_round else "DUP_REPO",
                        "ref": ref,
                        "message": f"repo_url also recorded under {seen_repos[repo][0]}",
                    })
                seen_repos[repo] = (ref, cix)
    return findings


def lint_drift(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    records = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("semantic_family"):
            records.append({
                "ref": str(entry.get("idea_id", "?")),
                "family": str(entry["semantic_family"]),
                "tokens": tokens(str(entry["semantic_family"])),
                "exclusion": bool(entry.get("excluded_reason")),
                "normalized_title": str(entry.get("normalized_title", "")),
                "aliases": {normalize(str(a)) for a in entry.get("aliases") or []},
            })
    for a, b in combinations(records, 2):
        if a["family"] == b["family"]:
            # An exclusion entry reusing its consumed sibling's family is the marker
            # that records WHY it was excluded; identical families are only an error
            # when both entries are independently implemented ideas.
            both_implemented = not (a["exclusion"] or b["exclusion"])
            findings.append({
                "level": "error" if both_implemented else "info",
                "code": "DUP_FAMILY" if both_implemented else "EXPECTED_DERIVATIVE_PAIR",
                "ref": f"{a['ref']}~{b['ref']}",
                "message": f"identical semantic_family: {a['family']}",
            })
            continue
        score_jaccard = jaccard(a["tokens"], b["tokens"])
        score_ratio = difflib.SequenceMatcher(None, a["family"], b["family"]).ratio()
        if score_jaccard >= FAMILY_JACCARD_THRESHOLD or score_ratio >= FAMILY_RATIO_THRESHOLD:
            level = "info" if (a["exclusion"] or b["exclusion"]) else "warning"
            findings.append({
                "level": level,
                "code": "NEAR_FAMILY" if level == "warning" else "EXPECTED_DERIVATIVE_PAIR",
                "ref": f"{a['ref']}~{b['ref']}",
                "message": (f"family similarity jaccard={score_jaccard:.2f} ratio={score_ratio:.2f}: "
                            f"'{a['family']}' vs '{b['family']}'"),
            })
    for a, b in combinations(records, 2):
        if a["normalized_title"] and a["normalized_title"] in b["aliases"]:
            findings.append({"level": "warning", "code": "ALIAS_COLLISION", "ref": f"{b['ref']}~{a['ref']}",
                             "message": f"alias of {b['ref']} equals normalized_title of {a['ref']}"})
        if b["normalized_title"] and b["normalized_title"] in a["aliases"]:
            findings.append({"level": "warning", "code": "ALIAS_COLLISION", "ref": f"{a['ref']}~{b['ref']}",
                             "message": f"alias of {a['ref']} equals normalized_title of {b['ref']}"})
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint the consumed-ideas ledger.")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--json", action="store_true", help="emit the full findings report as JSON")
    ns = ap.parse_args()

    ledger_path = Path(ns.project_root).resolve() / ".idea-ledger" / "consumed_ideas.yaml"
    if not ledger_path.exists():
        print(f"[ledger-lint] missing ledger: {ledger_path}", file=sys.stderr)
        return 1
    try:
        ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"[ledger-lint] YAML parse failed: {exc}", file=sys.stderr)
        return 1
    entries = ledger.get("consumed_ideas") or []

    findings = lint_schema(entries) + lint_uniqueness(entries) + lint_drift(entries)
    counts = {"error": 0, "warning": 0, "info": 0}
    for finding in findings:
        counts[finding["level"]] = counts.get(finding["level"], 0) + 1

    if ns.json:
        print(json.dumps({"entries": len(entries), "counts": counts, "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        for finding in findings:
            print(f"[{finding['level']}] {finding['code']} {finding['ref']}: {finding['message']}")
        print(f"[ledger-lint] entries={len(entries)} errors={counts['error']} "
              f"warnings={counts['warning']} info={counts['info']}")

    if counts["error"] or (ns.strict and counts["warning"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
