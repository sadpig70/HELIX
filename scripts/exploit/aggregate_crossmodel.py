#!/usr/bin/env python3
"""Aggregate cross-model consensus scores (generic).

Deterministic portion of the cross-model scoring protocol: integrity check +
per-candidate/axis median/stdev + consensus_aggregate + disagreement + self-bias.
stdlib only.

This generic version derives the candidate list and runtimes FROM the score files
themselves (no hardcoded project or runtime names) so it works for any ProjectGenome
run. Drop one `<runtime>.scores.json` per runtime into the scores dir and run.

usage:
  python scripts/aggregate_crossmodel.py [scores_dir]
  (default scores_dir: .recreate/crossmodel/scores)

Each score file must match schemas/crossmodel-scores.template.json:
  { "runtime": str,
    "scores": { "<Candidate>": { "<axis>": 0..1, ..., "aggregate": float,
                                 "self_authored": bool, "rationale": str } } }
"""

import glob
import json
import os
import statistics
import sys

AXES = ["reuse_leverage", "novelty", "domain_demand", "buildability",
        "boundary_clarity", "system_potential"]


def load(scores_dir):
    data = {}
    for path in sorted(glob.glob(os.path.join(scores_dir, "*.scores.json"))):
        if os.path.basename(path).startswith(("_TEMPLATE", "_")):
            continue
        with open(path, "r", encoding="utf-8") as h:
            doc = json.load(h)
        data[doc["runtime"]] = doc
    return data


def integrity(data):
    problems = []
    candidates = set()
    for doc in data.values():
        candidates.update(doc["scores"].keys())
    for rt, doc in data.items():
        for c in candidates:
            s = doc["scores"].get(c)
            if not s:
                problems.append("%s: missing candidate %s" % (rt, c))
                continue
            for a in AXES:
                v = s.get(a)
                if not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
                    problems.append("%s/%s/%s out of range: %r" % (rt, c, a, v))
            recomputed = round(sum(s.get(a, 0) for a in AXES), 4)
            if abs(recomputed - s.get("aggregate", -1)) > 0.001:
                problems.append("%s/%s aggregate %.4f != sum %.4f"
                                % (rt, c, s.get("aggregate", -1), recomputed))
    return sorted(candidates), problems


def main():
    scores_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ".recreate", "crossmodel", "scores")
    data = load(scores_dir)
    n = len(data)
    if n == 0:
        print("no *.scores.json found in", scores_dir)
        return
    print("=== runtimes: %d ===" % n, sorted(data))

    candidates, problems = integrity(data)
    print("\n=== integrity ===")
    print("OK" if not problems else "\n".join(problems))

    median, consensus, disagree = {}, {}, {}
    for c in candidates:
        median[c] = {}
        for a in AXES:
            vals = [data[rt]["scores"][c][a] for rt in data]
            median[c][a] = statistics.median(vals)
        consensus[c] = round(sum(median[c].values()), 4)
        # pstdev (population): the scored runtimes ARE the full set being measured,
        # not a sample — disagreement describes their actual spread. Also avoids the
        # StatisticsError that stdev() raises when only one runtime is present.
        disagree[c] = round(sum(statistics.pstdev([data[rt]["scores"][c][a]
                            for rt in data]) for a in AXES), 4)

    print("\n=== consensus_aggregate (sum of per-axis medians) ===")
    for c in sorted(candidates, key=lambda x: -consensus[x]):
        print("  %-30s %.3f  (disagreement %.3f)" % (c, consensus[c], disagree[c]))

    print("\n=== self-bias (self aggregate - median of others) ===")
    any_self = False
    for c in candidates:
        for author in [rt for rt in data if data[rt]["scores"][c].get("self_authored")]:
            others = [data[rt]["scores"][c]["aggregate"] for rt in data if rt != author]
            if not others:
                continue
            any_self = True
            self_agg = data[author]["scores"][c]["aggregate"]
            print("  %-30s author=%-10s self=%.2f others_median=%.2f bias=%+.3f"
                  % (c, author, self_agg, statistics.median(others),
                     self_agg - statistics.median(others)))
    if not any_self:
        print("  (no self_authored candidates)")


if __name__ == "__main__":
    main()
