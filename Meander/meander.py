#!/usr/bin/env python3
"""Meander — a deterministic maze generator and solver.

Given a width, height, and seed, Meander carves a **perfect maze**: a spanning
tree over the grid, so there is exactly one path between any two cells and the
maze is always solvable. It finds the shortest solution, scores the maze's
playability, and renders it as ASCII or SVG. The same seed always produces the
same maze — no randomness, no clock.

This is the HELIX loop's third distinct-character output (verify -> design ->
play), reusing the seeded-deterministic-generation gene from Confluence in a new
domain: games. It is a recreational tool, not a research artifact.

Standard library only: no random, clock, network, subprocess, or AI.
"""

import argparse
import hashlib
import json
import sys
from collections import deque

DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


def _h(*parts) -> int:
    key = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int(hashlib.sha256(key).hexdigest(), 16)


# --- generation --------------------------------------------------------------

def generate(w: int, h: int, seed: str = "meander") -> dict:
    """Carve a perfect maze with a deterministic depth-first search."""
    if w < 1 or h < 1:
        raise ValueError("width and height must be >= 1")
    passages = {(r, c): set() for r in range(h) for c in range(w)}
    visited = {(0, 0)}
    stack = [(0, 0)]
    step = 0
    while stack:
        r, c = stack[-1]
        nbrs = sorted(
            (r + dr, c + dc) for dr, dc in DIRS.values()
            if 0 <= r + dr < h and 0 <= c + dc < w
            and (r + dr, c + dc) not in visited)
        if not nbrs:
            stack.pop()
            continue
        nxt = nbrs[_h(seed, "carve", r, c, step) % len(nbrs)]
        passages[(r, c)].add(nxt)
        passages[nxt].add((r, c))
        visited.add(nxt)
        stack.append(nxt)
        step += 1
    return {"w": w, "h": h, "seed": seed, "passages": passages}


def passage_count(maze: dict) -> int:
    return sum(len(v) for v in maze["passages"].values()) // 2


# --- solving -----------------------------------------------------------------

def solve(maze: dict, start=None, goal=None) -> list:
    """Shortest path (BFS) from start to goal through open passages."""
    start = start or (0, 0)
    goal = goal or (maze["h"] - 1, maze["w"] - 1)
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for n in sorted(maze["passages"][cur]):
            if n not in prev:
                prev[n] = cur
                q.append(n)
    if goal not in prev:
        return []
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def metrics(maze: dict, path: list = None) -> dict:
    path = path if path is not None else solve(maze)
    P = maze["passages"]
    cells = maze["w"] * maze["h"]
    dead_ends = sum(1 for v in P.values() if len(v) == 1)
    junctions = sum(1 for v in P.values() if len(v) >= 3)
    return {
        "cells": cells,
        "solution_length": len(path),
        "dead_ends": dead_ends,
        "junctions": junctions,
        "difficulty": round(len(path) / cells + junctions / cells, 4)
        if cells else 0.0,
    }


# --- rendering ---------------------------------------------------------------

def render_ascii(maze: dict, path: list = None) -> str:
    w, h, P = maze["w"], maze["h"], maze["passages"]
    on_path = set(path or [])
    lines = ["+" + "".join("---+" for _ in range(w))]
    for r in range(h):
        row = "|"
        for c in range(w):
            cell = " . " if (r, c) in on_path else "   "
            row += cell + (" " if (r, c + 1) in P[(r, c)] else "|")
        lines.append(row)
        bottom = "+"
        for c in range(w):
            bottom += ("   " if (r + 1, c) in P[(r, c)] else "---") + "+"
        lines.append(bottom)
    return "\n".join(lines)


def render_svg(maze: dict, path: list = None) -> str:
    w, h, P = maze["w"], maze["h"], maze["passages"]
    s, pad = 24, 10
    W, H = w * s + 2 * pad, h * s + 2 * pad
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="#0f172a" rx="10"/>']
    if path:
        pts = " ".join(f"{pad + c * s + s // 2},{pad + r * s + s // 2}"
                       for r, c in path)
        out.append(f'<polyline points="{pts}" fill="none" stroke="#38bdf8" '
                   f'stroke-width="3" stroke-linejoin="round" opacity="0.9"/>')
    walls = []
    for r in range(h):
        for c in range(w):
            x, y = pad + c * s, pad + r * s
            if (r - 1, c) not in P[(r, c)]:
                walls.append(f"M{x} {y}h{s}")
            if (r, c - 1) not in P[(r, c)]:
                walls.append(f"M{x} {y}v{s}")
    walls.append(f"M{pad} {pad + h * s}h{w * s}")   # bottom border
    walls.append(f"M{pad + w * s} {pad}v{h * s}")   # right border
    out.append(f'<path d="{"".join(walls)}" stroke="#e2e8f0" stroke-width="2" '
               f'fill="none" stroke-linecap="square"/>')
    # start (green) and exit (amber)
    out.append(f'<circle cx="{pad + s // 2}" cy="{pad + s // 2}" r="5" '
               f'fill="#22c55e"/>')
    out.append(f'<circle cx="{pad + (w - 1) * s + s // 2}" '
               f'cy="{pad + (h - 1) * s + s // 2}" r="5" fill="#f59e0b"/>')
    out.append("</svg>")
    return "".join(out)


# --- CLI (sample / generate / solve) ----------------------------------------

def _cmd_sample(args) -> int:
    maze = generate(8, 5, "sample")
    path = solve(maze)
    print(render_ascii(maze, path))
    print(json.dumps(metrics(maze, path), ensure_ascii=False))
    return 0


def _cmd_generate(args) -> int:
    maze = generate(args.width, args.height, args.seed)
    path = solve(maze) if args.solution else None
    print(render_ascii(maze, path))
    print(json.dumps(metrics(maze), ensure_ascii=False))
    if args.svg:
        with open(args.svg, "w", encoding="utf-8", newline="\n") as f:
            f.write(render_svg(maze, solve(maze) if args.solution else None))
        print(f"svg: {args.svg}")
    return 0


def _cmd_solve(args) -> int:
    maze = generate(args.width, args.height, args.seed)
    path = solve(maze)
    print(render_ascii(maze, path))
    print(json.dumps({"path": [list(p) for p in path],
                      **metrics(maze, path)}, ensure_ascii=False))
    if args.svg:
        with open(args.svg, "w", encoding="utf-8", newline="\n") as f:
            f.write(render_svg(maze, path))
        print(f"svg: {args.svg}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="meander", description="Deterministic maze generator and solver.")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("sample", help="print a small solved example maze")
    for name, helptext in (("generate", "carve a maze"),
                           ("solve", "carve a maze and show the shortest path")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--width", type=int, default=16)
        sp.add_argument("--height", type=int, default=10)
        sp.add_argument("--seed", default="meander")
        sp.add_argument("--svg", default=None, help="also write an SVG here")
        if name == "generate":
            sp.add_argument("--solution", action="store_true",
                            help="overlay the solution path")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"sample": _cmd_sample, "generate": _cmd_generate,
            "solve": _cmd_solve}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
