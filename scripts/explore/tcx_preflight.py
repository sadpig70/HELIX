#!/usr/bin/env python3
"""TCX preflight checker for IdeaFirst.

This script validates the local inputs needed before a TCX full run:
catalog manifest, shard files, SDX axis compatibility, basis references,
PGF personas, TCX domain set, assignment script, network reachability, and
output write/lock state. It writes evidence under .tcx/preflight/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("[tcx_preflight] PyYAML is required.", file=sys.stderr)
    sys.exit(2)


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def record(results: list[dict[str, Any]], check: str, status: str, message: str, **extra: Any) -> None:
    results.append({"check": check, "status": status, "message": message, **extra})


def status_counts(results: list[dict[str, Any]]) -> Counter:
    return Counter(item["status"] for item in results)


def next_preflight_id(preflight_dir: Path, now: datetime) -> str:
    day = now.strftime("%Y%m%d")
    existing = sorted(preflight_dir.glob(f"TCX-PREFLIGHT-{day}-*.json"))
    return f"TCX-PREFLIGHT-{day}-{len(existing) + 1:03d}"


def as_list_from_shard(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("channels", "items", "entries"):
        val = data.get(key)
        if isinstance(val, list):
            return val
    if all(isinstance(v, dict) for v in data.values()):
        return list(data.values())
    return []


def channel_geo(channel: dict[str, Any]) -> str | None:
    axis = channel.get("axis")
    if isinstance(axis, dict) and axis.get("geographic"):
        return str(axis["geographic"])
    for key in ("geographic", "geo"):
        if channel.get(key):
            return str(channel[key])
    return None


def channel_format(channel: dict[str, Any], fallback: str) -> str:
    axis = channel.get("axis")
    if isinstance(axis, dict) and axis.get("format"):
        return str(axis["format"])
    if channel.get("format"):
        return str(channel["format"])
    return fallback


def collect_channels(project_root: Path, index: dict[str, Any], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog_root = project_root / ".sdx" / "catalog"
    channels: list[dict[str, Any]] = []
    actual_counts: dict[str, int] = {}
    missing: list[str] = []

    for shard in index.get("shards", []):
        rel = shard.get("path") or shard.get("file")
        fmt = str(shard.get("format") or Path(str(rel)).stem)
        shard_path = catalog_root / str(rel)
        if not shard_path.is_file():
            missing.append(str(rel))
            continue
        items = as_list_from_shard(load_yaml(shard_path))
        actual_counts[fmt] = len(items)
        for item in items:
            if isinstance(item, dict):
                enriched = dict(item)
                enriched["_shard_format"] = fmt
                channels.append(enriched)

    if missing:
        record(results, "shard_completeness", "FAIL", "Missing shard files.", missing=missing)
    else:
        record(results, "shard_completeness", "PASS", "All shard files exist.")

    expected_total = index.get("catalog", {}).get("acceptance", {}).get("catalog_size")
    actual_total = sum(actual_counts.values())
    if actual_total == expected_total:
        record(results, "shard_counts", "PASS", f"Shard item total matches catalog_size ({actual_total}).", counts=actual_counts)
    else:
        record(results, "shard_counts", "FAIL", f"Shard item total {actual_total} != catalog_size {expected_total}.", counts=actual_counts)
    return channels


def check_catalog(project_root: Path, catalog_index: Path, results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not catalog_index.is_file():
        record(results, "catalog_index", "FAIL", f"Catalog index not found: {catalog_index}")
        return {}, []

    index = load_yaml(catalog_index)
    record(results, "catalog_index", "PASS", f"Loaded catalog index: {catalog_index}")

    catalog = index.get("catalog", {})
    acceptance = catalog.get("acceptance", {})
    total_channels = catalog.get("total_channels")
    catalog_size = acceptance.get("catalog_size")
    shard_sum = sum(int(s.get("count", 0)) for s in index.get("shards", []))
    if shard_sum == catalog_size == total_channels:
        record(results, "catalog_consistency", "PASS", f"total_channels, catalog_size, and shard sum all equal {catalog_size}.")
    else:
        record(
            results,
            "catalog_consistency",
            "FAIL",
            "Catalog counts disagree.",
            total_channels=total_channels,
            catalog_size=catalog_size,
            shard_sum=shard_sum,
        )

    if acceptance.get("lock_eligible") is True:
        record(results, "lock_eligible", "PASS", "catalog.acceptance.lock_eligible is true.")
    else:
        record(results, "lock_eligible", "WARN", "catalog.acceptance.lock_eligible is not true.", value=acceptance.get("lock_eligible"))

    reports = index.get("reports")
    if isinstance(reports, dict) and reports:
        missing_reports = [rel for rel in reports.values() if not (catalog_index.parent / str(rel)).is_file()]
        if missing_reports:
            record(results, "reports", "WARN", "Some report references are missing.", missing=missing_reports)
        else:
            record(results, "reports", "PASS", "Report references exist.")
    else:
        record(results, "reports", "WARN", "No reports block found.")

    channels = collect_channels(project_root, index, results)
    return index, channels


def check_basis(catalog_index: Path, index: dict[str, Any], results: list[dict[str, Any]]) -> None:
    basis = index.get("basis")
    if not isinstance(basis, dict):
        record(results, "basis", "WARN", "No basis block found in catalog index.")
        return

    expected = ("orthogonality_matrix", "overlap_policy", "selection_log", "rejected")
    missing_keys = [key for key in expected if key not in basis]
    missing_files = [basis[key] for key in expected if key in basis and not (catalog_index.parent / str(basis[key])).is_file()]
    if missing_keys or missing_files:
        record(results, "basis", "FAIL", "Basis references are incomplete.", missing_keys=missing_keys, missing_files=missing_files)
        return

    status = basis.get("status", "unspecified")
    scope = basis.get("scope", "unspecified")
    message = f"Basis references exist; status={status}, scope={scope}."
    if status == "partial_reference":
        record(results, "basis", "PASS", message)
    else:
        record(results, "basis", "WARN", message)


def check_axis(project_root: Path, channels: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    schema_path = project_root / "skills" / "sdx" / "schemas" / "channel_entry.yaml"
    if not schema_path.is_file():
        record(results, "axis_schema", "FAIL", f"SDX axis schema not found: {schema_path}")
        return
    schema = load_yaml(schema_path)
    axis = schema.get("axis_system", {})
    geo_allowed = set(axis.get("geographic", []))
    format_allowed = set(axis.get("format", []))

    invalid_geo = []
    missing_geo = []
    formats_used = Counter()
    geos_used = Counter()
    for channel in channels:
        cid = channel.get("id") or channel.get("channel_id") or "UNKNOWN"
        name = channel.get("name") or channel.get("title") or channel.get("url") or ""
        geo = channel_geo(channel)
        fmt = channel_format(channel, channel.get("_shard_format", "unknown"))
        formats_used[fmt] += 1
        if geo is None:
            missing_geo.append({"id": cid, "name": name})
            continue
        geos_used[geo] += 1
        if geo not in geo_allowed:
            invalid_geo.append({"id": cid, "name": name, "geographic": geo})

    if missing_geo:
        record(results, "axis_missing_geo", "FAIL", "Some channels have no geographic axis.", channels=missing_geo)
    else:
        record(results, "axis_missing_geo", "PASS", "All channels have a geographic axis.")

    if invalid_geo:
        record(
            results,
            "axis_enum",
            "WARN",
            "Some geographic values are outside the SDX schema enum; TCX should warn or skip them during strict axis attribution.",
            invalid_geo=invalid_geo,
            allowed=sorted(geo_allowed),
        )
    else:
        record(results, "axis_enum", "PASS", "All geographic values match the SDX schema enum.")

    if set(formats_used) >= format_allowed:
        record(results, "format_coverage", "PASS", f"All {len(format_allowed)} format shards are represented.", formats=dict(formats_used))
    else:
        missing_formats = sorted(format_allowed - set(formats_used))
        record(results, "format_coverage", "FAIL", "Some format shards are not represented.", missing=missing_formats, formats=dict(formats_used))

    geo_covered = set(geos_used) & geo_allowed
    if len(geo_covered) >= 6:
        record(results, "geo_diversity_floor", "PASS", f"Geographic diversity floor met: {len(geo_covered)} schema cells.", geos=dict(geos_used))
    else:
        record(results, "geo_diversity_floor", "FAIL", f"Geographic diversity floor not met: {len(geo_covered)} schema cells.", geos=dict(geos_used))


def check_personas(project_root: Path, results: list[dict[str, Any]]) -> None:
    personas_path = project_root / "skills" / "pgf" / "discovery" / "personas.json"
    domains_path = project_root / "skills" / "tcx" / "domain_sets" / "default.yaml"
    assign_script = project_root / "skills" / "tcx" / "scripts" / "assign_personas.py"

    if not personas_path.is_file() or not domains_path.is_file():
        record(results, "persona_inputs", "FAIL", "Persona or domain-set input file is missing.")
        return

    personas = load_json(personas_path)
    domains = load_yaml(domains_path)
    persona_count = len(personas.get("personas", []))
    domain_count = len(domains.get("domain_set", {}).get("domains", []))
    if personas.get("version") == "1.0" and persona_count == 8 and domain_count == 14:
        record(results, "persona_inputs", "PASS", "Loaded PGF personas v1.0 and TCX default 14-domain set.")
    else:
        record(
            results,
            "persona_inputs",
            "WARN",
            "Persona or domain-set shape differs from TCX v1.5 default.",
            persona_version=personas.get("version"),
            persona_count=persona_count,
            domain_count=domain_count,
        )

    if not assign_script.is_file():
        record(results, "persona_assignment", "FAIL", f"Assignment script not found: {assign_script}")
        return

    proc = subprocess.run(
        [
            sys.executable,
            str(assign_script),
            "--personas",
            str(personas_path),
            "--domains",
            str(domains_path),
        ],
        cwd=str(project_root),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode == 0:
        record(results, "persona_assignment", "PASS", "assign_personas.py completed with no validation issues.", stderr=proc.stderr.strip())
    else:
        record(results, "persona_assignment", "FAIL", "assign_personas.py reported validation issues.", stderr=proc.stderr.strip())


def check_runtime(project_root: Path, results: list[dict[str, Any]], skip_network: bool) -> None:
    tcx_root = project_root / ".tcx"
    lock_path = tcx_root / ".lock"
    if lock_path.exists():
        record(results, "tcx_lock", "FAIL", f"Existing TCX lock found: {lock_path}")
    else:
        record(results, "tcx_lock", "PASS", "No TCX lock file exists.")

    tcx_root.mkdir(exist_ok=True)
    probe = tcx_root / "_preflight_write_probe.tmp"
    try:
        probe.write_text("ok", encoding="utf-8")
        value = probe.read_text(encoding="utf-8").strip()
        probe.unlink()
        if value == "ok":
            record(results, "write_probe", "PASS", ".tcx is writable.")
        else:
            record(results, "write_probe", "FAIL", "Write probe readback mismatch.", value=value)
    except Exception as exc:
        record(results, "write_probe", "FAIL", f".tcx write probe failed: {exc}")

    if skip_network:
        record(results, "network", "WARN", "Network check skipped by flag.")
        return
    try:
        with urllib.request.urlopen("https://example.com", timeout=8) as response:
            code = getattr(response, "status", None)
            if code == 200:
                record(results, "network", "PASS", "Network reachable via https://example.com.")
            else:
                record(results, "network", "WARN", f"Network check returned status {code}.")
    except Exception as exc:
        record(results, "network", "WARN", f"Network check failed: {exc}")


def verdict(results: list[dict[str, Any]]) -> str:
    counts = status_counts(results)
    if counts["FAIL"]:
        return "blocked"
    if counts["WARN"]:
        return "ready_with_warnings"
    return "ready"


def write_reports(project_root: Path, preflight_id: str, results: list[dict[str, Any]], args: argparse.Namespace) -> tuple[Path, Path]:
    preflight_dir = project_root / ".tcx" / "preflight"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "id": preflight_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_index": str(args.catalog),
        "verdict": verdict(results),
        "counts": dict(status_counts(results)),
        "results": results,
    }

    json_path = preflight_dir / f"{preflight_id}.json"
    md_path = preflight_dir / f"{preflight_id}.md"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# TCX Preflight — {preflight_id}",
        "",
        f"- Verdict: `{summary['verdict']}`",
        f"- Catalog: `{args.catalog}`",
        f"- Counts: `{summary['counts']}`",
        "",
        "## Checks",
        "",
    ]
    for item in results:
        lines.append(f"- `{item['status']}` `{item['check']}` — {item['message']}")
    lines.append("")
    lines.append("## TCX Start Policy")
    lines.append("")
    if summary["verdict"] == "blocked":
        lines.append("Do not start TCX full until FAIL checks are fixed.")
    else:
        lines.append("TCX full may start. WARN checks must be carried into quality_report.md.")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    latest_json = preflight_dir / "latest_preflight.json"
    latest_md = preflight_dir / "latest_preflight.md"
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate inputs before TCX full.")
    parser.add_argument("--project-root", default=".", type=Path)
    parser.add_argument("--catalog", default=Path(".sdx/catalog/index.yaml"), type=Path)
    parser.add_argument("--skip-network", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    args.catalog = (project_root / args.catalog).resolve() if not args.catalog.is_absolute() else args.catalog.resolve()
    results: list[dict[str, Any]] = []

    index, channels = check_catalog(project_root, args.catalog, results)
    if index:
        check_basis(args.catalog, index, results)
    if channels:
        check_axis(project_root, channels, results)
    check_personas(project_root, results)
    check_runtime(project_root, results, args.skip_network)

    preflight_dir = project_root / ".tcx" / "preflight"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    preflight_id = next_preflight_id(preflight_dir, datetime.now())
    json_path, md_path = write_reports(project_root, preflight_id, results, args)

    final_verdict = verdict(results)
    print(f"[tcx_preflight] verdict={final_verdict}")
    print(f"[tcx_preflight] json={json_path}")
    print(f"[tcx_preflight] report={md_path}")
    for item in results:
        print(f"[{item['status']}] {item['check']}: {item['message']}")
    return 1 if final_verdict == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
