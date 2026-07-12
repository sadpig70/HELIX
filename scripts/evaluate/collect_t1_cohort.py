#!/usr/bin/env python3
"""Collect the T1 live holdout cohort per the sealed selection policy.

Reads the saved search-API evidence (declared topic order), applies the sealed
eligibility filters in fixed order with NO replacement, pins each passing
repository to its HEAD commit SHA, and locks real artifacts:

- source artifact  = README bytes at the pinned SHA
- license evidence = GitHub license API content bytes

Repositories excluded by filters 1-3 lock their verbatim search-metadata
record instead (sealed policy amendment: no non-allowlist README text is
vendored). Emits a processing manifest for the selection receipt.

This is a COLLECTION tool (network via `gh`/`git`); it runs before the cohort
lock and is not part of the deterministic runtime boundary.

CLI:
    python scripts/evaluate/collect_t1_cohort.py
"""

import base64
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TOPICS = ("audit-log", "policy-engine", "rate-limiting", "scoring",
          "feature-flags", "workflow-engine", "markdown-parser")
ALLOWLIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}
EVIDENCE_DIR = "_workspace/helix-direction/T1/selection-evidence"
HOLDOUT_DIR = "seed/evaluation/t1-holdout"
MANIFEST_REL = "_workspace/helix-direction/T1/collection-manifest.json"
CORPUS_OWNER = "sadpig70"
MIN_README_BYTES = 1024


def _full(rel):
    return os.path.join(ROOT, *rel.split("/"))


def _write_bytes(rel, data):
    full = _full(rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)
    return rel


def _gh(args, binary=False):
    result = subprocess.run(["gh"] + args, capture_output=True, check=True)
    return result.stdout if binary else result.stdout.decode("utf-8")


def _head_sha(clone_url):
    out = subprocess.run(["git", "ls-remote", clone_url, "HEAD"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    return out.split()[0]


def _collect_repo(cid, item):
    """Pin and fetch real artifacts for a repo that passed filters 1-3."""
    full_name = item["full_name"]
    sha = _head_sha(item["clone_url"])
    readme = _gh(["api", "-H", "Accept: application/vnd.github.raw",
                  f"repos/{full_name}/readme?ref={sha}"], binary=True)
    license_doc = json.loads(_gh(["api", f"repos/{full_name}/license"]))
    license_bytes = base64.b64decode(license_doc["content"])
    source_rel = _write_bytes(f"{HOLDOUT_DIR}/sources/{cid}.README.md", readme)
    license_rel = _write_bytes(f"{HOLDOUT_DIR}/licenses/{cid}.LICENSE.txt",
                               license_bytes)
    return {"sha": sha, "readme_bytes": len(readme), "source_rel": source_rel,
            "license_rel": license_rel,
            "license_spdx": (license_doc.get("license") or {}).get("spdx_id")}


def _metadata_artifact(cid, item):
    data = json.dumps(item, ensure_ascii=False, sort_keys=True,
                      indent=2).encode("utf-8")
    rel = _write_bytes(f"{HOLDOUT_DIR}/sources/{cid}.metadata.json", data)
    return rel


def collect():
    rows = []
    seen_owners = set()
    counter = 0
    for topic in TOPICS:
        with open(_full(f"{EVIDENCE_DIR}/search-{topic}.json"),
                  encoding="utf-8") as f:
            items = json.load(f)["items"]
        for item in items:
            counter += 1
            cid = f"T1-{counter:03d}"
            owner = item["owner"]["login"]
            spdx = (item.get("license") or {}).get("spdx_id")
            reasons = []
            if spdx not in ALLOWLIST:
                reasons.append(f"filter1: license {spdx!r} not in allowlist")
            if item.get("archived") or item.get("fork"):
                reasons.append("filter2: archived or fork")
            if owner in seen_owners:
                reasons.append(f"filter3: duplicate owner {owner}")
            if owner == CORPUS_OWNER:
                reasons.append("filter5: corpus-owner family overlap")
            seen_owners.add(owner)
            row = {"cid": cid, "topic": topic, "full_name": item["full_name"],
                   "owner": owner, "spdx": spdx, "stars": item.get("stargazers_count")}
            if reasons:
                row.update({"status": "excluded", "reasons": reasons,
                            "artifact": _metadata_artifact(cid, item),
                            "revision": "unpinned-excluded"})
                rows.append(row)
                print(f"  {cid} EXCLUDED {item['full_name']}: {reasons[0]}")
                continue
            try:
                fetched = _collect_repo(cid, item)
            except subprocess.CalledProcessError as e:
                reasons.append(f"filter4: artifact fetch failed ({e})")
                row.update({"status": "excluded", "reasons": reasons,
                            "artifact": _metadata_artifact(cid, item),
                            "revision": "unpinned-excluded"})
                rows.append(row)
                print(f"  {cid} EXCLUDED {item['full_name']}: fetch failed")
                continue
            if fetched["readme_bytes"] < MIN_README_BYTES:
                reasons.append(f"filter4: README {fetched['readme_bytes']}B < {MIN_README_BYTES}B")
            row.update({
                "status": "excluded" if reasons else "eligible",
                "reasons": reasons,
                "artifact": fetched["source_rel"],
                "license_evidence": fetched["license_rel"],
                "revision": fetched["sha"],
                "readme_bytes": fetched["readme_bytes"],
            })
            rows.append(row)
            print(f"  {cid} {'EXCLUDED' if reasons else 'eligible'} "
                  f"{item['full_name']} @ {fetched['sha'][:12]}")
    manifest = {"policy": "HELIX-HOLDOUT/1.0", "cohort_id": "T1-LIVE-001",
                "processed": len(rows),
                "eligible": sum(1 for r in rows if r["status"] == "eligible"),
                "rows": rows}
    with open(_full(MANIFEST_REL), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


if __name__ == "__main__":
    manifest = collect()
    print(f"processed={manifest['processed']} eligible={manifest['eligible']}")
    sys.exit(0 if manifest["eligible"] >= 20 else 1)
