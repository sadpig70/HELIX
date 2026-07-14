#!/usr/bin/env python3
"""Trellis — a deterministic curriculum / skill-tree planner.

Give Trellis a set of skills with prerequisites (a directed acyclic graph) and a
goal. It produces a valid ordered learning path — a topological order with an
alphabetical tie-break, so the same graph always yields the same plan — the
minimal prerequisite closure for the goal, and depth/effort metrics. It **fails
closed** on cycles or missing prerequisites: you cannot learn a cyclic
prerequisite, so Trellis reports the problem instead of emitting a bogus plan.

This is the HELIX loop's fourth distinct-character output (verify -> design ->
play -> learn), transplanting Meander's graph-traversal gene into the learning
domain (a skill graph instead of a maze grid).

Honest note: Trellis orders the prerequisite graph you give it. It does not judge
pedagogy or invent prerequisites — the graph is the input, the ordered plan is
the output. Standard library only: no random, clock, network, subprocess, or AI.
"""

import argparse
import json
import sys

SAMPLE = {
    "arithmetic": [],
    "algebra": ["arithmetic"],
    "geometry": ["arithmetic"],
    "trigonometry": ["algebra", "geometry"],
    "functions": ["algebra"],
    "calculus": ["trigonometry", "functions"],
    "linear_algebra": ["functions"],
    "statistics": ["algebra"],
    "probability": ["statistics", "calculus"],
    "machine_learning": ["linear_algebra", "probability", "calculus"],
}


# --- validation --------------------------------------------------------------

def validate(graph: dict) -> list:
    """Problems with the graph (empty list = a well-formed DAG)."""
    problems = []
    for skill, prereqs in sorted(graph.items()):
        if not isinstance(prereqs, (list, tuple)):
            problems.append(f"{skill}: prerequisites must be a list")
            continue
        for p in prereqs:
            if p not in graph:
                problems.append(f"{skill}: prerequisite '{p}' is not a defined skill")
            if p == skill:
                problems.append(f"{skill}: depends on itself")
    cyc = _find_cycle(graph)
    if cyc:
        problems.append("cycle: " + " -> ".join(cyc))
    return sorted(set(problems))


def _find_cycle(graph: dict):
    """Return one cycle as a list of skills, or None. Deterministic."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {s: WHITE for s in graph}
    stack = []

    def dfs(u):
        color[u] = GRAY
        stack.append(u)
        for v in sorted(graph.get(u, [])):
            if v not in graph:
                continue
            if color[v] == GRAY:
                return stack[stack.index(v):] + [v]
            if color[v] == WHITE:
                got = dfs(v)
                if got:
                    return got
        color[u] = BLACK
        stack.pop()
        return None

    for s in sorted(graph):
        if color[s] == WHITE:
            got = dfs(s)
            if got:
                return got
    return None


# --- ordering ----------------------------------------------------------------

def topo_order(graph: dict) -> list:
    """Kahn's algorithm with an alphabetical tie-break (deterministic)."""
    indeg = {s: 0 for s in graph}
    for s in graph:
        for p in graph[s]:
            if p in graph:
                indeg[s] += 1
    ready = sorted(s for s in graph if indeg[s] == 0)
    order = []
    while ready:
        u = ready.pop(0)
        order.append(u)
        for s in sorted(graph):
            if u in graph[s]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    ready.append(s)
        ready.sort()
    if len(order) != len(graph):
        raise ValueError("graph has a cycle; no topological order exists")
    return order


def prerequisites(graph: dict, goal: str) -> set:
    """Transitive prerequisite closure of goal, including goal itself."""
    if goal not in graph:
        raise KeyError(f"unknown goal skill: {goal}")
    closure, stack = set(), [goal]
    while stack:
        cur = stack.pop()
        if cur in closure:
            continue
        closure.add(cur)
        for p in graph.get(cur, []):
            if p in graph:
                stack.append(p)
    return closure


def plan(graph: dict, goal: str) -> list:
    """The minimal learning path to a goal: topo order of its prereq closure."""
    problems = validate(graph)
    if problems:
        raise ValueError(f"cannot plan an invalid graph: {problems[0]}")
    needed = prerequisites(graph, goal)
    sub = {s: [p for p in graph[s] if p in needed] for s in needed}
    return topo_order(sub)


def depth(graph: dict, skill: str, _seen=None) -> int:
    """Longest prerequisite chain ending at skill (0 for a root)."""
    _seen = _seen or set()
    if skill in _seen:
        raise ValueError("cycle while computing depth")
    prereqs = [p for p in graph.get(skill, []) if p in graph]
    if not prereqs:
        return 0
    return 1 + max(depth(graph, p, _seen | {skill}) for p in prereqs)


def metrics(graph: dict) -> dict:
    roots = sorted(s for s in graph if not [p for p in graph[s] if p in graph])
    return {
        "skills": len(graph),
        "starting_points": roots,
        "max_depth": max((depth(graph, s) for s in graph), default=0),
        "valid": not validate(graph),
    }


# --- rendering ---------------------------------------------------------------

def render_plan(graph: dict, goal: str) -> str:
    steps = plan(graph, goal)
    lines = [f"Learning path to '{goal}' ({len(steps)} steps):"]
    for i, s in enumerate(steps, 1):
        prereqs = [p for p in graph[s] if p in graph]
        note = f"   (needs: {', '.join(sorted(prereqs))})" if prereqs else ""
        lines.append(f"  {i:>2}. {s}{note}")
    return "\n".join(lines)


def render_svg(graph: dict, goal: str = None) -> str:
    skills = plan(graph, goal) if goal else topo_order(graph)
    layer = {s: depth(graph, s) for s in skills}
    max_layer = max(layer.values(), default=0)
    by_layer = {}
    for s in skills:
        by_layer.setdefault(layer[s], []).append(s)
    colw, rowh, pad = 168, 60, 20
    W = pad * 2 + (max_layer + 1) * colw
    H = pad * 2 + max(len(v) for v in by_layer.values()) * rowh
    pos = {}
    for lz in range(max_layer + 1):
        col = sorted(by_layer.get(lz, []))
        for j, s in enumerate(col):
            pos[s] = (pad + lz * colw + 20, pad + j * rowh + 20)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="#0f172a" rx="10"/>']
    for s in skills:
        x2, y2 = pos[s]
        for p in graph[s]:
            if p in pos:
                x1, y1 = pos[p]
                out.append(f'<line x1="{x1 + 120}" y1="{y1 + 12}" x2="{x2}" '
                           f'y2="{y2 + 12}" stroke="#334155" stroke-width="1.5"/>')
    for s in skills:
        x, y = pos[s]
        fill = "#f59e0b" if s == goal else "#1e293b"
        out.append(f'<rect x="{x}" y="{y}" width="130" height="26" rx="6" '
                   f'fill="{fill}" stroke="#475569"/>'
                   f'<text x="{x + 65}" y="{y + 18}" font-family="sans-serif" '
                   f'font-size="12" fill="#e2e8f0" text-anchor="middle">{s}</text>')
    out.append("</svg>")
    return "".join(out)


# --- CLI (sample / plan / check) --------------------------------------------

def _load_graph(path):
    if not path:
        return dict(SAMPLE)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cmd_sample(args) -> int:
    print(render_plan(SAMPLE, "machine_learning"))
    print(json.dumps(metrics(SAMPLE), ensure_ascii=False))
    return 0


def _cmd_plan(args) -> int:
    graph = _load_graph(args.graph)
    problems = validate(graph)
    if problems:
        print(json.dumps({"valid": False, "problems": problems},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(render_plan(graph, args.goal))
    print(json.dumps({"steps": len(plan(graph, args.goal)), **metrics(graph)},
                     ensure_ascii=False))
    if args.svg:
        with open(args.svg, "w", encoding="utf-8", newline="\n") as f:
            f.write(render_svg(graph, args.goal))
        print(f"svg: {args.svg}")
    return 0


def _cmd_check(args) -> int:
    graph = _load_graph(args.graph)
    problems = validate(graph)
    print(json.dumps({"valid": not problems, "problems": problems,
                      **({} if problems else {"order": topo_order(graph)})},
                     ensure_ascii=False, indent=2))
    return 0 if not problems else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="trellis", description="Deterministic curriculum / skill-tree planner.")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("sample", help="plan the built-in sample curriculum")
    pl = sub.add_parser("plan", help="order the learning path to a goal")
    pl.add_argument("--goal", required=True)
    pl.add_argument("--graph", default=None, help="JSON {skill: [prereqs]}")
    pl.add_argument("--svg", default=None)
    ck = sub.add_parser("check", help="validate a skill graph (cycles / missing)")
    ck.add_argument("--graph", default=None)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"sample": _cmd_sample, "plan": _cmd_plan,
            "check": _cmd_check}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
