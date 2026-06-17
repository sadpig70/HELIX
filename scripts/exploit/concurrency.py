#!/usr/bin/env python3
"""Deterministic OCC primitives for concurrent multi-runtime runs (stdlib only).

Implements the lock / claim / commit contract documented in
`docs/CONCURRENCY-POLICY.md` §3-§5 and `skills/recreate/reference/rerun-avoidance.md §10`.
The deterministic mechanics live here (registry lock, version CAS, atomic write,
hard-collision detection); the AI-side soft avoidance / pivot strategy stays with the
runtime. Coding them keeps Phase 0 (claim) and Phase 7 (commit) — the only two atomic
boundaries — stable across runtimes instead of leaving file I/O to AI judgment.

usage as a library:
    from concurrency import registry_lock, claim_run, commit_run
usage as a CLI:
    python scripts/concurrency.py claim .recreate/registry.json <runtime>
"""

import contextlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fingerprint import (  # noqa: E402
    normalize_name, source_fingerprint, generated_fingerprint,
)


@contextlib.contextmanager
def registry_lock(registry_path: str, timeout: float = 10.0, poll: float = 0.05):
    """Mutual exclusion on a registry via an O_EXCL lockfile (cross-platform CAS)."""
    lock = registry_path + ".lock"
    deadline = time.monotonic() + timeout
    fd = None
    while fd is None:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError("registry lock busy: %s" % lock)
            time.sleep(poll)
    try:
        yield
    finally:
        os.close(fd)
        with contextlib.suppress(FileNotFoundError):
            os.remove(lock)


def read_registry(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as h:
        return json.load(h)


def write_registry(path: str, reg: dict) -> None:
    """Atomic write: temp file in the same dir + os.replace."""
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as h:
        json.dump(reg, h, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def next_run_number(reg: dict, runs_dir: str = None) -> int:
    """max existing run number + 1 (deterministic; no wall-clock)."""
    nums = [0]
    for ar in reg.get("active_runs", []):
        m = re.match(r"(\d+)", ar.get("run_id", ""))
        if m:
            nums.append(int(m.group(1)))
    if runs_dir and os.path.isdir(runs_dir):
        for entry in os.listdir(runs_dir):
            m = re.match(r"(\d+)", entry)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1


def claim_run(registry_path: str, runtime: str, runs_dir: str = None) -> dict:
    """Phase 0 — atomic claim (CONCURRENCY-POLICY §4)."""
    with registry_lock(registry_path):
        reg = read_registry(registry_path)
        claim_seq = reg.setdefault("version", 0) + 1
        nnn = next_run_number(reg, runs_dir)
        run_id = "%03d-%s-pending" % (nnn, runtime)   # runtime suffix → no dir collision (H1)
        reg["version"] = claim_seq
        reg.setdefault("active_runs", []).append({
            "claim_seq": claim_seq, "run_id": run_id, "runtime": runtime,
            "baseline_version": claim_seq, "status": "active"})
        write_registry(registry_path, reg)
    return {"run_id": run_id, "baseline_version": claim_seq, "claim_seq": claim_seq}


def _namespace(winner: dict):
    """Return (namespace_key, fingerprint) — generated (integration) takes precedence."""
    if winner.get("parents"):
        return "generated_fingerprints", generated_fingerprint(winner["parents"])
    return "source_fingerprints", source_fingerprint(winner.get("consumed_sources", []))


def avoidance_recheck(winner: dict, reg: dict) -> str:
    """Deterministic hard collisions vs the CURRENT registry (None = clear)."""
    name_norm = normalize_name(winner["name"])
    if name_norm in {normalize_name(n) for n in reg.get("blocked_names", [])}:
        return "name collision: %s" % winner["name"]
    ns, fp = _namespace(winner)
    if fp and fp in (reg.get(ns) or {}):
        return "%s collision: %s" % (ns, fp)
    return None


def _mark(reg: dict, run_id: str, status: str) -> None:
    for ar in reg.get("active_runs", []):
        if ar.get("run_id") == run_id:
            ar["status"] = status


def commit_run(registry_path: str, run: dict, winner: dict, runs_dir: str = None) -> str:
    """Phase 7 — atomic OCC commit (CONCURRENCY-POLICY §5).

    Returns 'committed' on success, or 'collision' if a hard collision was found
    against the merged state (caller pivots/discards outside the lock — AI-side).
    """
    final_status = "collision"
    with registry_lock(registry_path):
        reg = read_registry(registry_path)
        reason = avoidance_recheck(winner, reg)
        if reason:
            _mark(reg, run["run_id"], "aborted")
            reg["version"] = reg.get("version", 0) + 1
            write_registry(registry_path, reg)
        else:
            name = winner["name"]
            ns, fp = _namespace(winner)
            reg.setdefault("generated_projects", {})[name] = winner.get("record", {
                "run_id": run["run_id"], "consumed_sources": winner.get("consumed_sources", []),
                "source_fingerprint": fp if ns == "source_fingerprints" else None})
            reg.setdefault("blocked_names", []).append(name)
            if fp:
                reg.setdefault(ns, {})[fp] = {"project": name, "run_id": run["run_id"]}
            sp = reg.setdefault("source_projects", {})
            for s in winner.get("consumed_sources", []):
                ent = sp.setdefault(s, {"use_count": 0, "used_by": []})
                ent["use_count"] += 1
                ent["used_by"].append(name)
            _mark(reg, run["run_id"], "committed")
            reg["version"] = reg.get("version", 0) + 1
            write_registry(registry_path, reg)
            latest = os.path.join(os.path.dirname(registry_path) or ".", "latest.json")
            write_registry(latest, {"run_id": run["run_id"], "winner": name,
                                    "version": reg["version"]})
            final_status = "committed"
    if final_status == "committed" and runs_dir and winner.get("slug"):
        nnn = re.match(r"(\d+)", run["run_id"])
        src = os.path.join(runs_dir, run["run_id"])
        if nnn and os.path.isdir(src):
            with contextlib.suppress(OSError):
                os.replace(src, os.path.join(runs_dir, "%s-%s" % (nnn.group(1), winner["slug"])))
    return final_status


def _main(argv) -> int:
    if len(argv) >= 4 and argv[1] == "claim":
        print(json.dumps(claim_run(argv[2], argv[3]), ensure_ascii=False))
        return 0
    sys.stderr.write(
        "usage:\n"
        "  python scripts/concurrency.py claim <registry.json> <runtime>\n"
        "  (commit_run is library-only — pass the winner record from the runtime)\n")
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
