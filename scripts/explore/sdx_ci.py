#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SDX-CI runner — cross-integration of multiple SDX agent catalogs.
Implements the deterministic parts of the `sdx_ci` skill (PG: 정밀계산=코드).

Modes:
  union     : URL canonical dedup → union pool (최대 풍부, 직교 재선택 없음)
  (integrate/compare: 추후)

Usage:
  python scripts/explore/sdx_ci.py union --in chatgpt,gemini,grok,kimi --out integrated
Paths follow SDX v1.4 --out normalization: bare token -> .sdx/<token>/
"""
import sys, os, glob, re, argparse
import yaml

def resolve_out(val):
    """SDX v1.4 --out normalization."""
    if val is None:
        return ".sdx/integrated"
    if re.match(r"^([a-zA-Z]:[\\/]|/)", val):      # absolute
        return val.rstrip("/\\")
    if "/" in val or "\\" in val:                  # relative path
        return val.rstrip("/\\")
    return f".sdx/{val}"                           # bare token

def resolve_in(val):
    return resolve_out(val)  # same rule (bare token -> .sdx/<token>)

def norm_url(u):
    if not u: return None
    u = str(u).strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("?")[0].split("#")[0].rstrip("/")
    return u or None

def load_agent(agent_dir):
    """Defensive: glob channels/*.yaml directly (do not trust index.yaml)."""
    chans = []
    for f in sorted(glob.glob(os.path.join(agent_dir, "channels", "*.yaml"))):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"  WARN parse fail {f}: {e}"); continue
        if isinstance(d, dict) and isinstance(d.get("channels"), list):
            for ch in d["channels"]:
                if isinstance(ch, dict):
                    chans.append(ch)
    return chans

def get_url(ch):
    return ch.get("url_pattern") or ch.get("url")

def get_format(ch):
    ax = ch.get("axis") or {}
    return ax.get("format") or "unknown"

def coverage_check(pool):
    """SDX required_coverage 실측 (schemas/channel_entry.yaml#required_coverage).
    geo 8/8, format >=8/10, temporal 5/5, scale 3/3 → lock_eligible 판정 근거."""
    GEO = {"US_EU","CN","RU_EE","IN_SEA","JP_KR","LATAM","AF","MENA"}
    TMP = {"T-0","T-1Y","T-5Y","T-50Y","T-100Y+"}
    SCL = {"macro","meso","micro"}
    geo, fmt, tmp, scl = set(), set(), set(), set()
    for ch in pool:
        ax = ch.get("axis") or {}
        if ax.get("geographic"): geo.add(ax["geographic"])
        if ax.get("format"):     fmt.add(ax["format"])
        if ax.get("temporal"):   tmp.add(ax["temporal"])
        if ax.get("scale"):      scl.add(ax["scale"])
    detail = {"geographic": f"{len(geo & GEO)}/8", "format": f"{len(fmt)}/10",
              "temporal": f"{len(tmp & TMP)}/5", "scale": f"{len(scl & SCL)}/3",
              "geo_cells": sorted(geo)}
    passed = (len(geo & GEO) >= 8 and len(fmt) >= 8 and len(tmp & TMP) >= 5 and len(scl & SCL) >= 3)
    return passed, detail

def union_mode(in_dirs, out_root, agent_names):
    per_agent = {}
    for name, d in zip(agent_names, in_dirs):
        per_agent[name] = load_agent(d)
        print(f"  loaded {name}: {len(per_agent[name])} channels  (dir={d})")

    url_sets = {n: set(filter(None, (norm_url(get_url(c)) for c in per_agent[n])))
                for n in agent_names}

    by_url = {}
    no_url = []
    submitted = 0
    for name in agent_names:
        for ch in per_agent[name]:
            submitted += 1
            key = norm_url(get_url(ch))
            src = {"agent": name, "orig_id": ch.get("id")}
            score = ch.get("total_score") or 0
            if key is None:
                e = dict(ch); e["ci_provenance"] = {"sources": [src], "merged_count": 1}
                no_url.append(e); continue
            if key not in by_url:
                e = dict(ch)
                e["ci_provenance"] = {"sources": [src], "merged_count": 1}
                e["_score"] = score
                by_url[key] = e
            else:
                w = by_url[key]
                w["ci_provenance"]["sources"].append(src)
                w["ci_provenance"]["merged_count"] += 1
                # union language
                la = w.get("language") or []; lb = ch.get("language") or []
                if isinstance(la, str): la = [la]
                if isinstance(lb, str): lb = [lb]
                merged_lang = sorted(set(la) | set(lb))
                if score > (w.get("_score") or 0):   # higher score wins fields
                    prov = w["ci_provenance"]
                    e = dict(ch); e["ci_provenance"] = prov; e["_score"] = score
                    e["language"] = merged_lang
                    by_url[key] = e
                else:
                    if merged_lang: w["language"] = merged_lang

    pool = list(by_url.values()) + no_url
    pool.sort(key=lambda c: (c.get("_score") or 0), reverse=True)

    # renumber + clean temp fields
    for i, ch in enumerate(pool, 1):
        ch["id"] = f"CH-{i:04d}"
        ch.pop("_score", None)

    dedup_count = len(pool)
    redundancy = round((submitted - dedup_count) / max(1, submitted), 3)

    # cross-agent stats
    others = lambda n: set().union(*[url_sets[o] for o in agent_names if o != n]) if len(agent_names) > 1 else set()
    per_stats = {}
    for n in agent_names:
        uniq = url_sets[n] - others(n)
        per_stats[n] = {"submitted": len(per_agent[n]),
                        "distinct_urls": len(url_sets[n]),
                        "unique_to_agent": len(uniq)}
    pair = {a: {b: round(len(url_sets[a] & url_sets[b]) / max(1, len(url_sets[a] | url_sets[b])), 3)
                for b in agent_names if b != a} for a in agent_names}

    # format distribution
    fmt = {}
    for ch in pool:
        fmt[get_format(ch)] = fmt.get(get_format(ch), 0) + 1

    # ---- emit ----
    os.makedirs(os.path.join(out_root, "pool"), exist_ok=True)
    os.makedirs(os.path.join(out_root, "channels"), exist_ok=True)
    os.makedirs(os.path.join(out_root, "reports"), exist_ok=True)

    # union_pool.yaml
    with open(os.path.join(out_root, "pool", "union_pool.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump({"mode": "union", "total_channels": dedup_count,
                        "submitted": submitted, "dedup_removed": submitted - dedup_count,
                        "channels": pool}, fh, allow_unicode=True, sort_keys=False, width=4096)

    # per-format shards
    shard_counts = {}
    by_fmt = {}
    for ch in pool:
        by_fmt.setdefault(get_format(ch), []).append(ch)
    for f, chs in sorted(by_fmt.items()):
        shard_counts[f] = len(chs)
        with open(os.path.join(out_root, "channels", f"{f}.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump({"shard": f, "count": len(chs), "channels": chs},
                           fh, allow_unicode=True, sort_keys=False, width=4096)

    # index.yaml
    # SDX Catalog Index Contract v1
    # lock_eligible = required_coverage 실측(직교성과 무관 — contract 정의). basis는 union 미계산이라 생략.
    cov_passed, cov_detail = coverage_check(pool)
    shards_list = [{"format": f, "file": f"channels/{f}.yaml", "path": f"channels/{f}.yaml",
                    "count": shard_counts[f]} for f in sorted(shard_counts)]
    idx = {
        "catalog": {"version": "v1.0-union", "mode": "union",
                    "orthogonal_reselect": False,
                    "policy_version": "sdx-1.5",
                    "built_by": "sdx_ci union", "total_channels": dedup_count,
                    "shard_key": "format",
                    "acceptance": {"catalog_size": dedup_count,
                                   "lock_eligible": cov_passed,         # required_coverage 실측 (계약 정의)
                                   "required_coverage_passed": cov_passed,
                                   "coverage_detail": cov_detail},
                    "note": "union: dedup 합집합 전체 보존(최대 풍부). orthogonal_reselect=false(직교 매트릭스 미계산 → basis 생략). lock_eligible은 required_coverage 실측값."},
        "shards": shards_list,                                   # contract 필수 (path 병기)
        "inputs": {n: {"submitted": per_stats[n]["submitted"]} for n in agent_names},
        "dedup": {"submitted": submitted, "after_dedup": dedup_count,
                  "removed_duplicates": submitted - dedup_count, "global_redundancy": redundancy},
        "format_distribution": shard_counts,
        # basis: union은 orthogonality 미계산 → 생략 (integrate 모드에서만 산출)
        "reports": {"cross_agent_report": "reports/cross_agent_report.md"},
        "references": {"pool": "pool/union_pool.yaml"},
    }
    with open(os.path.join(out_root, "index.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump(idx, fh, allow_unicode=True, sort_keys=False, width=4096)

    return {"submitted": submitted, "dedup": dedup_count, "redundancy": redundancy,
            "per_stats": per_stats, "pair": pair, "fmt": shard_counts, "no_url": len(no_url),
            "lock_eligible": cov_passed, "coverage": cov_detail}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["union"])
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", default=None)
    a = ap.parse_args()
    names = [x.strip() for x in a.inp.split(",") if x.strip()]
    in_dirs = [resolve_in(n) for n in names]
    out_root = resolve_out(a.out)
    print(f"mode={a.mode} | in={in_dirs} | out={out_root}")
    r = union_mode(in_dirs, out_root, names)
    print("\n=== RESULT ===")
    print(f"submitted={r['submitted']} -> dedup_union={r['dedup']} (removed {r['submitted']-r['dedup']}, redundancy {r['redundancy']}, no_url {r['no_url']})")
    print("per-agent:", r["per_stats"])
    print("format:", r["fmt"])
    print("lock_eligible:", r["lock_eligible"], "| coverage:", r["coverage"])
    print("pairwise_jaccard:", r["pair"])

if __name__ == "__main__":
    main()
