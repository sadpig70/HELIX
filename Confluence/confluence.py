#!/usr/bin/env python3
"""Confluence — a domain-agnostic generative design-space explorer.

Drug design, materials, semiconductor floorplanning, energy mixes, data schemas,
and the arts look unrelated, but they share one abstraction: **compose primitives
under constraints toward multiple objectives.** Confluence is one deterministic
engine over that abstraction. A domain is defined by four functions —
``positions`` (choices per locus), ``constraints``, ``objectives`` (all
maximized), ``render`` — and the engine generates candidate designs, keeps the
Pareto-optimal (non-dominated) set, and evolves it over generations.

The same engine runs eight domains, spanning hard science and the arts:
    molecule (pharma) · alloy (materials) · floorplan (semiconductor) ·
    energy (energy mix) · schema (data) · mandala (SVG art) ·
    melody (WAV music) · story (narrative text).

Honest boundary: the domain packs are **illustrative models**, not production R&D
tools — Confluence does not discover real drugs or design real chips. Its point is
the unifying abstraction and the demonstration that one generative engine crosses
science and art.

Deterministic and standard-library only: candidate generation and variation come
from SHA-256 of a seed, never ``random`` or a clock. The same (domain, seed,
params) always reproduce the same sealed run.
"""

import argparse
import hashlib
import io
import json
import math
import struct
import sys
import wave

RUN_SCHEMA = "confluence-run/1.0"


# --- deterministic helpers ---------------------------------------------------

def _h(*parts) -> int:
    """A deterministic non-negative integer from hashing the given parts."""
    key = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int(hashlib.sha256(key).hexdigest(), 16)


def canonical_json_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(doc: dict, field: str) -> dict:
    sealed = dict(doc)
    sealed.pop(field, None)
    sealed[field] = _sha256(canonical_json_bytes(sealed))
    return sealed


def verify_run_seal(run: dict) -> bool:
    body = {k: v for k, v in run.items() if k != "run_sha256"}
    return isinstance(run.get("run_sha256"), str) and \
        run["run_sha256"] == _sha256(canonical_json_bytes(body))


# --- engine ------------------------------------------------------------------

def init_genome(positions: list, seed: str, idx: int) -> tuple:
    return tuple(_h(seed, "init", idx, i) % len(positions[i])
                 for i in range(len(positions)))


def is_valid(domain: dict, genome: tuple) -> bool:
    return not domain["constraints"](genome)


def dominates(a: dict, b: dict) -> bool:
    """a Pareto-dominates b: >= on every objective and > on at least one."""
    ge = all(a[k] >= b[k] for k in a)
    gt = any(a[k] > b[k] for k in a)
    return ge and gt


def pareto_front(evaluated: list) -> list:
    """Non-dominated members, de-duplicated by genome, deterministically ordered."""
    front = []
    for e in evaluated:
        if not any(dominates(o["objectives"], e["objectives"])
                   for o in evaluated if o["genome"] != e["genome"]):
            front.append(e)
    seen, unique = set(), []
    for e in sorted(front, key=lambda x: tuple(x["genome"])):
        g = tuple(e["genome"])
        if g not in seen:
            seen.add(g)
            unique.append(e)
    return unique


def _crossover(seed, gen, k, a, b):
    return tuple(a[i] if _h(seed, "x", gen, k, i) % 2 == 0 else b[i]
                 for i in range(len(a)))


def _mutate(domain, seed, gen, k, g):
    positions = domain["positions"]
    locus = _h(seed, "ml", gen, k) % len(g)
    val = _h(seed, "mv", gen, k, locus) % len(positions[locus])
    return tuple(val if i == locus else g[i] for i in range(len(g)))


def _seed_population(domain, seed, size):
    positions = domain["positions"]
    pop, idx, cap = [], 0, size * 40
    seen = set()
    while len(pop) < size and idx < cap:
        g = init_genome(positions, seed, idx)
        if g not in seen and is_valid(domain, g):
            seen.add(g)
            pop.append(g)
        idx += 1
    return pop


def evolve(domain: dict, seed: str = "confluence",
           population: int = 24, generations: int = 8) -> dict:
    """Deterministic multi-objective evolutionary search over a domain."""
    pop = _seed_population(domain, seed, population)
    problems = []
    if not pop:
        problems.append("no valid candidates found under the domain constraints")

    for gen in range(generations):
        if not pop:
            break
        evaluated = [{"genome": list(g), "objectives": domain["objectives"](g)}
                     for g in pop]
        front = pareto_front(evaluated)
        parents = [tuple(e["genome"]) for e in front] or pop
        offspring, seen, k = [], set(tuple(p) for p in parents), 0
        while len(offspring) < population and k < population * 6:
            a = parents[_h(seed, "pa", gen, k) % len(parents)]
            b = parents[_h(seed, "pb", gen, k) % len(parents)]
            child = _mutate(domain, seed, gen, k, _crossover(seed, gen, k, a, b))
            if child not in seen and is_valid(domain, child):
                seen.add(child)
                offspring.append(child)
            k += 1
        # elitism: keep the front, add fresh offspring, dedupe, cap
        merged, seen2 = [], set()
        for g in [tuple(e["genome"]) for e in front] + offspring:
            if g not in seen2:
                seen2.add(g)
                merged.append(g)
        pop = merged[:population]

    evaluated = [{"genome": list(g), "objectives": domain["objectives"](g)}
                 for g in pop]
    front = pareto_front(evaluated)

    front_out = []
    for e in front:
        g = tuple(e["genome"])
        front_out.append({
            "genome": list(g),
            "summary": domain["summary"](g),
            "objectives": {k: round(float(v), 6)
                           for k, v in e["objectives"].items()},
            "render_format": domain["render"](g)["format"],
        })
    obj_keys = sorted(front[0]["objectives"]) if front else []
    best_by_objective = {}
    for key in obj_keys:
        best = max(front, key=lambda e: (e["objectives"][key],
                                         tuple(-x for x in e["genome"])))
        best_by_objective[key] = {"genome": list(best["genome"]),
                                  "value": round(float(best["objectives"][key]), 6)}

    return _seal({
        "schema": RUN_SCHEMA,
        "domain": domain["name"],
        "seed": seed,
        "population": population,
        "generations": generations,
        "evaluated_final": len(pop),
        "pareto_front": front_out,
        "objectives": obj_keys,
        "best_by_objective": best_by_objective,
        "problems": problems,
    }, "run_sha256")


def best_genome(domain: dict, run: dict, objective: str = None) -> tuple:
    front = run["pareto_front"]
    if not front:
        raise ValueError("run has an empty Pareto front; nothing to render")
    if objective and objective in run.get("objectives", []):
        pick = max(front, key=lambda e: (e["objectives"][objective],
                                         tuple(-x for x in e["genome"])))
    else:
        pick = front[0]
    return tuple(pick["genome"])


def render_best(domain: dict, run: dict, objective: str = None) -> dict:
    return domain["render"](best_genome(domain, run, objective))


# --- domain packs ------------------------------------------------------------

def _totals(items, key):
    return sum(it.get(key, 0) for it in items)


# molecule (pharma)
_FRAGS = [
    ("Ar", {"pot": 2, "tox": 1, "syn": 2, "ring": 1}),
    ("NH2", {"pot": 1, "tox": 1, "syn": 3}),
    ("C=O", {"pot": 1, "tox": 1, "syn": 3}),
    ("X", {"pot": 2, "tox": 3, "syn": 2}),
    ("OH", {"pot": 1, "tox": 0, "syn": 3}),
    ("R", {"pot": 0, "tox": 0, "syn": 3}),
    ("NO2", {"pot": 2, "tox": 4, "syn": 1}),
    ("--", {}),
]


def _mol_items(g):
    return [_FRAGS[i][1] for i in g]


def _molecule():
    n = 5
    return {
        "name": "molecule",
        "positions": [_FRAGS] * n,
        "constraints": lambda g: (
            (["needs at least one aromatic ring"]
             if not any(_FRAGS[i][1].get("ring") for i in g) else [])
            + (["all fragments empty"]
               if all(_FRAGS[i][0] == "--" for i in g) else [])),
        "objectives": lambda g: {
            "potency": float(_totals(_mol_items(g), "pot")),
            "safety": float(n * 4 - _totals(_mol_items(g), "tox")),
            "synthesizability": float(_totals(_mol_items(g), "syn")),
        },
        "summary": lambda g: "-".join(_FRAGS[i][0] for i in g
                                      if _FRAGS[i][0] != "--") or "(empty)",
        "render": lambda g: {"format": "text",
                             "content": "molecule: " + "-".join(
                                 _FRAGS[i][0] for i in g if _FRAGS[i][0] != "--")},
    }


# alloy (materials)
_ELEMENTS = [
    ("Fe", {"str": 3, "cond": 2, "stab": 3}),
    ("Ni", {"str": 2, "cond": 2, "stab": 4}),
    ("Cr", {"str": 3, "cond": 1, "stab": 4}),
    ("Cu", {"str": 1, "cond": 5, "stab": 2}),
    ("Al", {"str": 1, "cond": 4, "stab": 2}),
    ("Ti", {"str": 4, "cond": 1, "stab": 3}),
    ("Mg", {"str": 1, "cond": 3, "stab": 1}),
    ("--", {}),
]


def _alloy():
    n = 4
    return {
        "name": "alloy",
        "positions": [_ELEMENTS] * n,
        "constraints": lambda g: (
            ["needs at least two distinct real elements"]
            if len({_ELEMENTS[i][0] for i in g if _ELEMENTS[i][0] != "--"}) < 2
            else []),
        "objectives": lambda g: {
            "strength": float(_totals([_ELEMENTS[i][1] for i in g], "str")),
            "conductivity": float(_totals([_ELEMENTS[i][1] for i in g], "cond")),
            "stability": float(_totals([_ELEMENTS[i][1] for i in g], "stab")),
        },
        "summary": lambda g: " · ".join(
            f"{name}x{[_ELEMENTS[j][0] for j in g].count(name)}"
            for name in sorted({_ELEMENTS[i][0] for i in g if _ELEMENTS[i][0] != "--"})),
        "render": lambda g: {"format": "text", "content": "alloy: " + " ".join(
            _ELEMENTS[i][0] for i in g if _ELEMENTS[i][0] != "--")},
    }


# floorplan (semiconductor)
_BLOCKS = [
    ("CPU", {"pwr": 4, "perf": 5, "area": 4}),
    ("GPU", {"pwr": 5, "perf": 5, "area": 5}),
    ("L2", {"pwr": 2, "perf": 3, "area": 2}),
    ("IO", {"pwr": 2, "perf": 1, "area": 2}),
    ("MEM", {"pwr": 3, "perf": 2, "area": 3}),
    ("NPU", {"pwr": 3, "perf": 4, "area": 3}),
    ("--", {}),
]


def _floorplan():
    n = 6
    names = lambda g: [_BLOCKS[i][0] for i in g]
    return {
        "name": "floorplan",
        "positions": [_BLOCKS] * n,
        "constraints": lambda g: [
            m for m in (("missing CPU" if "CPU" not in names(g) else None),
                        ("missing MEM" if "MEM" not in names(g) else None))
            if m],
        "objectives": lambda g: {
            "low_power": float(n * 5 - _totals([_BLOCKS[i][1] for i in g], "pwr")),
            "performance": float(_totals([_BLOCKS[i][1] for i in g], "perf")),
            "low_area": float(n * 5 - _totals([_BLOCKS[i][1] for i in g], "area")),
        },
        "summary": lambda g: "".join(f"[{_BLOCKS[i][0]}]" for i in g
                                     if _BLOCKS[i][0] != "--"),
        "render": lambda g: {"format": "text", "content": "floorplan: " + "".join(
            f"[{_BLOCKS[i][0]}]" for i in g if _BLOCKS[i][0] != "--")},
    }


# energy (energy mix)
_SOURCES = [
    ("solar", {"cost": 2, "carbon": 0, "firm": 1}),
    ("wind", {"cost": 2, "carbon": 0, "firm": 1}),
    ("gas", {"cost": 3, "carbon": 4, "firm": 5}),
    ("nuclear", {"cost": 4, "carbon": 0, "firm": 5}),
    ("hydro", {"cost": 3, "carbon": 1, "firm": 4}),
    ("coal", {"cost": 2, "carbon": 5, "firm": 5}),
]


def _energy():
    n = 5
    items = lambda g: [_SOURCES[i][1] for i in g]
    return {
        "name": "energy",
        "positions": [_SOURCES] * n,
        "constraints": lambda g: (
            ["firm capacity below baseload (needs >= 12)"]
            if _totals(items(g), "firm") < 12 else []),
        "objectives": lambda g: {
            "low_cost": float(n * 4 - _totals(items(g), "cost")),
            "low_carbon": float(n * 5 - _totals(items(g), "carbon")),
            "reliability": float(_totals(items(g), "firm")),
        },
        "summary": lambda g: " · ".join(
            f"{name} {[_SOURCES[j][0] for j in g].count(name) * 100 // n}%"
            for name in sorted({_SOURCES[i][0] for i in g})),
        "render": lambda g: {"format": "text", "content": "energy mix: " + ", ".join(
            f"{_SOURCES[i][0]}" for i in g)},
    }


# schema (data)
_FIELDS = [
    ("id:key", {"info": 1, "cost": 1, "red": 0, "key": 1}),
    ("name", {"info": 2, "cost": 1, "red": 0}),
    ("email", {"info": 3, "cost": 1, "red": 0}),
    ("created_at", {"info": 1, "cost": 1, "red": 0}),
    ("full_name", {"info": 2, "cost": 1, "red": 2}),
    ("--", {}),
]


def _schema():
    n = 6
    return {
        "name": "schema",
        "positions": [_FIELDS] * n,
        "constraints": lambda g: (
            ["needs a key field (id:key)"]
            if not any(_FIELDS[i][1].get("key") for i in g) else []),
        "objectives": lambda g: {
            "information": float(_totals([_FIELDS[i][1] for i in g], "info")),
            "low_cost": float(n * 1 - _totals([_FIELDS[i][1] for i in g], "cost")),
            "low_redundancy": float(
                n * 2 - _totals([_FIELDS[i][1] for i in g], "red")),
        },
        "summary": lambda g: ", ".join(sorted(
            {_FIELDS[i][0] for i in g if _FIELDS[i][0] != "--"})),
        "render": lambda g: {"format": "text", "content": "schema: {" + ", ".join(
            sorted({_FIELDS[i][0] for i in g if _FIELDS[i][0] != "--"})) + "}"},
    }


# mandala (SVG art)
_SYM = [3, 4, 5, 6, 8, 12]
_PALETTE = [
    ("sunset", ["#f97316", "#ef4444", "#fbbf24"]),
    ("ocean", ["#0ea5e9", "#22d3ee", "#2563eb"]),
    ("forest", ["#22c55e", "#84cc16", "#065f46"]),
    ("violet", ["#8b5cf6", "#d946ef", "#6366f1"]),
]
_SHAPE = ["petal", "circle", "star"]
_LAYERS = [2, 3, 4, 5]


def _mandala_svg(g):
    sym = _SYM[g[0]]
    palette = _PALETTE[g[1]][1]
    shape = _SHAPE[g[2]]
    layers = _LAYERS[g[3]]
    cx = cy = 160
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320" '
             f'width="320" height="320"><rect width="320" height="320" '
             f'fill="#0f172a" rx="14"/>']
    for layer in range(layers):
        r = 30 + layer * (110 // layers)
        color = palette[layer % len(palette)]
        for k in range(sym):
            ang = 2 * math.pi * k / sym + layer * 0.2
            x = cx + r * math.cos(ang)
            y = cy + r * math.sin(ang)
            if shape == "circle":
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{8 + layer * 2}" '
                             f'fill="{color}" opacity="0.75"/>')
            elif shape == "star":
                parts.append(f'<polygon points="{x:.1f},{y - 9:.1f} '
                             f'{x + 3:.1f},{y:.1f} {x:.1f},{y + 9:.1f} {x - 3:.1f},{y:.1f}" '
                             f'fill="{color}" opacity="0.8"/>')
            else:
                parts.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{6 + layer}" '
                             f'ry="{14 + layer * 2}" fill="{color}" opacity="0.7" '
                             f'transform="rotate({math.degrees(ang):.1f} {x:.1f} {y:.1f})"/>')
    parts.append('</svg>')
    return "".join(parts)


def _mandala():
    return {
        "name": "mandala",
        "positions": [_SYM, _PALETTE, _SHAPE, _LAYERS],
        "constraints": lambda g: [],
        "objectives": lambda g: {
            "symmetry": float(_SYM[g[0]]),
            "harmony": float(3 - abs(_SYM[g[0]] - _LAYERS[g[3]] * 2) / 4.0),
            "richness": float(_LAYERS[g[3]] * (g[2] + 1)),
        },
        "summary": lambda g: (f"{_SYM[g[0]]}-fold {_PALETTE[g[1]][0]} "
                              f"{_SHAPE[g[2]]} x{_LAYERS[g[3]]}"),
        "render": lambda g: {"format": "svg", "content": _mandala_svg(g)},
    }


# melody (WAV music)
_SCALE = [0, 2, 4, 5, 7, 9, 11, 12]  # major scale semitone offsets
_CONSONANT = {0, 3, 4, 5, 7, 8, 9, 12}


def _melody_wav(g):
    rate = 8000
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    frames = bytearray()
    dur = int(rate * 0.2)
    for idx in g:
        freq = 261.63 * (2 ** (_SCALE[idx] / 12.0))
        for t in range(dur):
            val = int(9000 * math.sin(2 * math.pi * freq * t / rate)
                      * (1 - t / dur))  # decay envelope
            frames += struct.pack("<h", val)
    w.writeframes(bytes(frames))
    w.close()
    return buf.getvalue()


def _melody():
    n = 8
    idxs = lambda g: [_SCALE[i] for i in g]

    def consonance(g):
        s = idxs(g)
        return sum(1 for a, b in zip(s, s[1:]) if abs(a - b) in _CONSONANT)

    return {
        "name": "melody",
        "positions": [list(range(len(_SCALE)))] * n,
        "constraints": lambda g: (["too monotone (needs >= 3 distinct notes)"]
                                  if len(set(g)) < 3 else []),
        "objectives": lambda g: {
            "consonance": float(consonance(g)),
            "variety": float(len(set(g))),
            "resolution": float(2 if g[-1] in (0, 7) else 0),
        },
        "summary": lambda g: "notes " + "-".join(
            "CDEFGABc"[i] for i in g),
        "render": lambda g: {"format": "wav", "content": _melody_wav(g)},
    }


# story (narrative text)
_BEATS = ["ordinary_world", "call", "refusal", "threshold", "trials",
          "ordeal", "reward", "road_back", "return"]


def _story():
    n = 6
    return {
        "name": "story",
        "positions": [list(range(len(_BEATS)))] * n,
        "constraints": lambda g: (["needs an ordeal (climax)"]
                                  if _BEATS.index("ordeal") not in g else []),
        "objectives": lambda g: {
            "arc": float(len({_BEATS[i] for i in g})),
            "momentum": float(sum(1 for a, b in zip(g, g[1:]) if b > a)),
            "coherence": float(sum(1 for a, b in zip(g, g[1:]) if 0 < b - a <= 3)),
        },
        "summary": lambda g: " -> ".join(_BEATS[i] for i in g),
        "render": lambda g: {"format": "text",
                             "content": "story beats:\n  " + "\n  ".join(
                                 f"{k + 1}. {_BEATS[i]}" for k, i in enumerate(g))},
    }


DOMAINS = {d["name"]: d for d in (
    _molecule(), _alloy(), _floorplan(), _energy(), _schema(),
    _mandala(), _melody(), _story())}


# --- CLI (domains / run / report) -------------------------------------------

def _cmd_domains(args) -> int:
    print(json.dumps({
        "domains": {name: {"loci": len(d["positions"]),
                           "objectives": sorted(d["objectives"](
                               init_genome(d["positions"], "x", 0)))}
                    for name, d in sorted(DOMAINS.items())}},
        ensure_ascii=False, indent=2))
    return 0


def _cmd_run(args) -> int:
    if args.domain not in DOMAINS:
        print(f"unknown domain: {args.domain}; try one of "
              f"{sorted(DOMAINS)}", file=sys.stderr)
        return 2
    domain = DOMAINS[args.domain]
    run = evolve(domain, seed=args.seed, population=args.population,
                 generations=args.generations)
    # The sealed run is the ledger record; render metadata is CLI-side only so
    # it never invalidates the seal.
    if args.ledger:
        _append_ledger(args.ledger, run)
    printable = dict(run)
    if args.render:
        artifact = render_best(domain, run, args.objective)
        content = artifact["content"]
        mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
        kw = {} if "b" in mode else {"encoding": "utf-8", "newline": "\n"}
        with open(args.render, mode, **kw) as f:
            f.write(content)
        printable["rendered_to"] = args.render
        printable["rendered_format"] = artifact["format"]
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0 if run["pareto_front"] else 2


def _append_ledger(path, run):
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n")


def _cmd_report(args) -> int:
    runs = []
    with open(args.ledger, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                runs.append(json.loads(line))
    ok = sum(1 for r in runs if verify_run_seal(r))
    report = {
        "ledger": args.ledger,
        "runs": len(runs),
        "seal_verified": ok,
        "by_domain": {},
    }
    for r in runs:
        report["by_domain"][r["domain"]] = report["by_domain"].get(
            r["domain"], 0) + 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok == len(runs) else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="confluence",
        description="Generative design-space explorer across many domains.")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("domains", help="list available domains and objectives")
    run = sub.add_parser("run", help="evolve a Pareto set for one domain")
    run.add_argument("--domain", required=True)
    run.add_argument("--seed", default="confluence")
    run.add_argument("--population", type=int, default=24)
    run.add_argument("--generations", type=int, default=8)
    run.add_argument("--render", default=None,
                     help="write the best candidate's artifact to this path")
    run.add_argument("--objective", default=None,
                     help="render the candidate best on this objective")
    run.add_argument("--ledger", default=None)
    rep = sub.add_parser("report", help="summarize a run ledger")
    rep.add_argument("--ledger", required=True)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"domains": _cmd_domains, "run": _cmd_run,
            "report": _cmd_report}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
