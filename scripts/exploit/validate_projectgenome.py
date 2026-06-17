#!/usr/bin/env python3
"""Deterministic contract checks for a ProjectGenome run (stdlib only).

Validates the parts an AI runtime is supposed to produce, so that a public user
gets a clear pass/fail instead of silent drift. No third-party deps (no
jsonschema): pragmatic structural checks aligned with schemas/ and the skill.

Checks, when the relevant files are present:
  1. JSON parses (registry, genes, crossmodel scores).
  2. registry: schema_version + version present; every source_fingerprint /
     generated_fingerprint key is canonical ("+".join(sorted(set))); no key maps
     to two different projects; generated_projects.*.source_fingerprint matches
     its consumed_sources.
  3. ProjectGene: required fields present; archetype matches Primary(+Secondary);
     layer in the 5-set.
  4. DesignSeed (DESIGN-SEED-*.md): required sections present.
  5. crossmodel scores: aggregate == sum(6 axes) per candidate.

usage:
  python scripts/validate_projectgenome.py [root]   # default: current dir
exit code 0 = all present checks passed, 1 = problems found.
"""

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fingerprint import source_fingerprint, is_valid_archetype, LAYERS  # noqa: E402

AXES = ["reuse_leverage", "novelty", "domain_demand", "buildability",
        "boundary_clarity", "system_potential"]
GENE_REQUIRED = ["project", "repo", "domain", "archetype", "mechanism", "layer",
                 "verdict_scheme", "vocab"]
SEED_SECTIONS = ["한 질문", "분류", "재사용 계획", "판정", "경계"]


def _load_json(path, problems):
    try:
        with open(path, "r", encoding="utf-8") as h:
            return json.load(h)
    except (OSError, ValueError) as exc:
        problems.append("JSON parse failed: %s (%s)" % (path, exc))
        return None


def check_registry(path, problems, notes):
    reg = _load_json(path, problems)
    if reg is None:
        return
    if "schema_version" not in reg:
        problems.append("registry: missing schema_version")
    if not isinstance(reg.get("version"), int):
        problems.append("registry: version must be an integer")
    for ns in ("source_fingerprints", "generated_fingerprints"):
        seen = {}
        for key, val in (reg.get(ns) or {}).items():
            canon = "+".join(sorted(set(key.split("+"))))
            if key != canon:
                problems.append("registry.%s key not canonical: %r (want %r)" % (ns, key, canon))
            proj = (val or {}).get("project")
            if key in seen and seen[key] != proj:
                problems.append("registry.%s key %r maps to two projects" % (ns, key))
            seen[key] = proj
    for name, gp in (reg.get("generated_projects") or {}).items():
        fp = gp.get("source_fingerprint")
        cs = gp.get("consumed_sources")
        if fp and cs and fp != source_fingerprint(cs):
            problems.append("generated_projects.%s: source_fingerprint %r != fingerprint(consumed_sources) %r"
                            % (name, fp, source_fingerprint(cs)))
    notes.append("registry checked: %s" % path)


def check_genes(path, problems, notes):
    genes = _load_json(path, problems)
    if genes is None:
        return
    if not isinstance(genes, list):
        problems.append("genes.json: expected a JSON array")
        return
    for i, g in enumerate(genes):
        for f in GENE_REQUIRED:
            if f not in g or g[f] in (None, "", []):
                problems.append("genes[%d] (%s): missing/empty %s" % (i, g.get("project", "?"), f))
        if "archetype" in g and not is_valid_archetype(g["archetype"]):
            problems.append("genes[%d] (%s): invalid archetype %r" % (i, g.get("project", "?"), g["archetype"]))
        if "layer" in g and g["layer"] not in LAYERS:
            problems.append("genes[%d] (%s): invalid layer %r" % (i, g.get("project", "?"), g["layer"]))
    notes.append("genes checked: %d entries in %s" % (len(genes), path))


def _section(text, heading):
    """Body of a '## {heading}...' section up to the next '## ' (or EOF)."""
    m = re.search(r"^##\s+%s.*$" % re.escape(heading), text, re.MULTILINE)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^##\s+", rest, re.MULTILINE)
    return rest[:nxt.start()] if nxt else rest


def check_seed(path, problems, notes):
    try:
        with open(path, "r", encoding="utf-8") as h:
            text = h.read()
    except OSError as exc:
        problems.append("DesignSeed read failed: %s (%s)" % (path, exc))
        return
    name = os.path.basename(path)
    for sec in SEED_SECTIONS:
        if sec not in text:
            problems.append("%s: missing required section containing %r" % (name, sec))

    # Structural checks (beyond keyword presence) — only when the field is present.
    m = re.search(r"archetype:\s*([A-Za-z][A-Za-z+]*)", text)
    if m and not is_valid_archetype(m.group(1)):
        problems.append("%s: invalid archetype %r (expected 1-2 of the 7)" % (name, m.group(1)))
    m = re.search(r"layers_used:\s*([A-Za-z][A-Za-z,/ ]*)", text)
    if m:
        for tok in re.split(r"[,/]", m.group(1)):
            tok = tok.strip()
            if tok and tok not in LAYERS:
                problems.append("%s: invalid layer %r in layers_used" % (name, tok))

    reuse = _section(text, "재사용 계획")
    if reuse is not None:
        rows = [ln for ln in reuse.splitlines()
                if ln.lstrip().startswith("|") and "---" not in ln]
        data_rows = max(0, len(rows) - 1)  # drop the header row
        if data_rows < 2:
            problems.append("%s: reuse_plan needs >=2 parts (corpus-basedness), got %d"
                            % (name, data_rows))

    boundary = _section(text, "경계")
    if boundary is not None and not re.search(r"아니다|not\b|NOT\b", boundary):
        problems.append("%s: boundary must declare what this is NOT ('~가 아니다')" % name)

    notes.append("DesignSeed checked: %s" % name)


def check_scores(path, problems, notes):
    doc = _load_json(path, problems)
    if doc is None:
        return
    for cand, s in (doc.get("scores") or {}).items():
        recomputed = round(sum(s.get(a, 0) for a in AXES), 4)
        if abs(recomputed - s.get("aggregate", -1)) > 0.001:
            problems.append("%s/%s: aggregate %.4f != sum(axes) %.4f"
                            % (os.path.basename(path), cand, s.get("aggregate", -1), recomputed))
    notes.append("scores checked: %s" % os.path.basename(path))


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    problems, notes, found = [], [], 0

    for rel in ("registry.empty.json", "schemas/registry.empty.json",
                ".recreate/registry.json"):
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            found += 1
            check_registry(p, problems, notes)

    for p in glob.glob(os.path.join(root, "**", "genes.json"), recursive=True):
        found += 1
        check_genes(p, problems, notes)
    for p in glob.glob(os.path.join(root, "**", "DESIGN-SEED-*.md"), recursive=True):
        found += 1
        check_seed(p, problems, notes)
    for p in glob.glob(os.path.join(root, "**", "*.scores.json"), recursive=True):
        if os.path.basename(p).startswith(("_TEMPLATE", "_")):
            continue
        found += 1
        check_scores(p, problems, notes)

    print("=== ProjectGenome validation (root: %s) ===" % os.path.abspath(root))
    for n in notes:
        print("  -", n)
    if found == 0:
        print("  (no validatable artifacts found — run the pipeline first, or pass a run dir)")
    print()
    if problems:
        print("FAIL — %d problem(s):" % len(problems))
        for pr in problems:
            print("  !", pr)
        return 1
    print("PASS — %d artifact group(s) checked, no problems." % found)
    return 0


if __name__ == "__main__":
    sys.exit(main())
