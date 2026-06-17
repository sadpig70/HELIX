#!/usr/bin/env python3
"""CIX archive_rounds — move CIX rounds older than retention window into archive/{YYYY-Q[1-4]}/.

Mirrors TCX/IDX archive scripts with CIX round_id format `CIX-{YYYYMMDD}-{NNN}`.

Default invocation (from project root that contains `.cix/`):

    python skills/cix/scripts/archive_rounds.py                          # 90-day retention
    python skills/cix/scripts/archive_rounds.py --retain-days 180        # custom
    python skills/cix/scripts/archive_rounds.py --dry-run                # preview only
    python skills/cix/scripts/archive_rounds.py --cix-root /path/.cix    # override path

Behavior:
- Scans `.cix/rounds/CIX-{YYYYMMDD}-{NNN}/` directories.
- Any round whose date is older than `retain_days` is moved into `.cix/archive/{YYYY-Q[1-4]}/`.
- The current latest round (per `.cix/index.yaml`) is never archived even if its date is old.
- After moving, updates `.cix/index.yaml`: removes archived rounds from the `rounds:` list and
  increments `archive_policy.rounds_in_archive`, sets `last_archive_run`.
- Archive folder gets a `.READONLY` marker file (informational only; OS perms not enforced).
"""

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    yaml = None  # graceful fallback below

ROUND_ID_RE = re.compile(r"^CIX-(\d{8})-(\d{3})$")


def parse_round_date(round_id: str):
    """Return datetime.date for a CIX-YYYYMMDD-NNN id, or None if malformed."""
    m = ROUND_ID_RE.match(round_id)
    if not m:
        return None
    try:
        return dt.datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def quarter_label(d: dt.date) -> str:
    """e.g. date(2026, 5, 13) -> '2026-Q2'."""
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def load_yaml(path: Path):
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        return {"_raw_text": text}
    return yaml.safe_load(text) or {}


def dump_yaml(path: Path, data) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML required to update index.yaml; install with: pip install pyyaml")
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def find_rounds(rounds_dir: Path):
    """Yield (path, round_id, date) for each well-formed round dir."""
    if not rounds_dir.exists():
        return
    for child in sorted(rounds_dir.iterdir()):
        if not child.is_dir():
            continue
        d = parse_round_date(child.name)
        if d is None:
            continue
        yield child, child.name, d


def archive(cix_root: Path, retain_days: int, dry_run: bool, verbose: bool):
    rounds_dir = cix_root / "rounds"
    archive_dir = cix_root / "archive"
    index_path = cix_root / "index.yaml"

    if not rounds_dir.exists():
        print(f"[cix-archive] no rounds dir at {rounds_dir}; nothing to do.")
        return 0

    index = load_yaml(index_path) if index_path.exists() else {"cix_output": {"rounds": []}}
    output = index.setdefault("cix_output", {})
    latest_round_id = output.get("latest_round_id")

    cutoff = dt.date.today() - dt.timedelta(days=retain_days)
    candidates = []
    for round_path, round_id, round_date in find_rounds(rounds_dir):
        if round_id == latest_round_id:
            continue  # never archive the active latest
        if round_date <= cutoff:
            candidates.append((round_path, round_id, round_date))

    if not candidates:
        print(f"[cix-archive] no rounds older than {retain_days} days (cutoff={cutoff}).")
        if not dry_run and index_path.exists():
            output.setdefault("archive_policy", {})["last_archive_run"] = dt.datetime.utcnow().isoformat() + "Z"
            dump_yaml(index_path, index)
        return 0

    print(f"[cix-archive] retention={retain_days}d, cutoff={cutoff}, moving {len(candidates)} round(s).")
    moved_ids = set()
    for round_path, round_id, round_date in candidates:
        target_quarter = archive_dir / quarter_label(round_date)
        target = target_quarter / round_id
        action = "DRY-RUN move" if dry_run else "moving"
        print(f"  {action}: {round_path}  ->  {target}")
        if dry_run:
            continue
        target_quarter.mkdir(parents=True, exist_ok=True)
        readme = target_quarter / ".READONLY"
        if not readme.exists():
            readme.write_text(
                "Archived CIX rounds. Do not modify in place; clone if you need to replay.\n",
                encoding="utf-8",
            )
        if target.exists():
            print(f"    skip - target already exists: {target}", file=sys.stderr)
            continue
        shutil.move(str(round_path), str(target))
        moved_ids.add(round_id)

    if not dry_run and moved_ids:
        existing = output.get("rounds", []) or []
        output["rounds"] = [r for r in existing if r.get("id") not in moved_ids]
        ap = output.setdefault("archive_policy", {})
        ap["rounds_in_archive"] = int(ap.get("rounds_in_archive", 0) or 0) + len(moved_ids)
        ap["last_archive_run"] = dt.datetime.utcnow().isoformat() + "Z"
        ap.setdefault("retain_in_rounds_days", retain_days)
        ap.setdefault("archive_target_pattern", "archive/{YYYY-Q[1-4]}/")
        dump_yaml(index_path, index)
        print(f"[cix-archive] index updated; archived={len(moved_ids)}, in_archive={ap['rounds_in_archive']}.")

    return len(moved_ids)


def main():
    ap = argparse.ArgumentParser(description="Archive CIX rounds older than retention window.")
    ap.add_argument("--cix-root", default=".cix", help="Path to .cix/ directory (default: ./.cix)")
    ap.add_argument("--retain-days", type=int, default=90, help="Retention window in days (default 90)")
    ap.add_argument("--dry-run", action="store_true", help="Preview without moving anything")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cix_root = Path(args.cix_root)
    if not cix_root.exists():
        print(f"[cix-archive] {cix_root} does not exist.", file=sys.stderr)
        return 1
    archive(cix_root, args.retain_days, args.dry_run, args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
