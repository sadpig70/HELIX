#!/usr/bin/env python3
"""Calibrate HELIX diversity thresholds from history (stdlib only, deterministic).

Implements docs/CALIBRATION.md §4 as an executable tool: read rounds, compute the
sim-based thresholds as quantiles of observed similarities so the guard fires on
~target_trigger_rate of historical rounds.

Input  : a JSONL file, one round per line:
           {"pool_sims": [..], "winner_sims": [..]}
         (precomputed pairwise similarities for that round's pool / consecutive
          winners; computing them needs the chosen sim/embedding, done upstream.)
Output : JSON {thresholds: {...}, evidence: {...}} to stdout (or --out).

usage:
    python scripts/calibrate_diversity.py rounds.jsonl --target 0.2 --out thr.json
"""

import json
import sys


def quantile(xs, q):
    """Deterministic linear-interpolated quantile of a list (q in [0,1])."""
    s = sorted(x for x in xs if x is not None)
    if not s:
        return None
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def calibrate(rounds, target_trigger_rate=0.2):
    pool_sims, win_sims = [], []
    for r in rounds:
        pool_sims += [v for v in r.get("pool_sims", []) if v is not None]
        win_sims += [v for v in r.get("winner_sims", []) if v is not None]
    thr = {}
    ev = {"n_rounds": len(rounds), "n_pool_sims": len(pool_sims),
          "n_winner_sims": len(win_sims), "target_trigger_rate": target_trigger_rate}
    if pool_sims:
        thr["avg_embedding_sim"] = round(quantile(pool_sims, 1 - target_trigger_rate), 4)
        thr["dup_cos"] = round(quantile(pool_sims, 0.95), 4)
    if win_sims:
        thr["winner_embedding_similarity"] = round(quantile(win_sims, 1 - target_trigger_rate), 4)
    if len(rounds) < 20:
        ev["confidence"] = "low (<20 rounds) — keep defaults unless intentional"
    else:
        ev["confidence"] = "ok"
    # keyword_coverage / max_pair_count are scale-free counts -> not calibrated here
    return {"thresholds": thr, "evidence": ev}


def _main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: python scripts/calibrate_diversity.py rounds.jsonl "
                         "[--target 0.2] [--out thr.json]\n")
        return 2
    path = argv[1]
    target = float(_opt(argv, "--target", "0.2"))
    out = _opt(argv, "--out")
    rounds = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rounds.append(json.loads(line))
    result = calibrate(rounds, target)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {out}")
    else:
        print(text)
    return 0


def _opt(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
    return default


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
