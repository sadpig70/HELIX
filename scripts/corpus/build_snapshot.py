#!/usr/bin/env python3
"""Build a deterministic, compact source-tree evidence snapshot."""

import argparse
import hashlib
import json
import os
import sys


DEFAULT_EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
DEFAULT_EXCLUDED_SUFFIXES = (".pyc", ".pyo")


def sha256_file(path):
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def build_snapshot(source, revision, excluded_dirs=None):
    source = os.path.abspath(source)
    if not os.path.isdir(source):
        raise ValueError(f"source is not a directory: {source}")
    excluded = set(DEFAULT_EXCLUDED_DIRS)
    excluded.update(excluded_dirs or [])
    files = []
    for base, dirs, names in os.walk(source, topdown=True, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in excluded)
        for name in sorted(names):
            if name.endswith(DEFAULT_EXCLUDED_SUFFIXES):
                continue
            path = os.path.join(base, name)
            relative = os.path.relpath(path, source).replace(os.sep, "/")
            if os.path.islink(path):
                raise ValueError(f"symbolic link is not allowed in evidence snapshot: {relative}")
            files.append({
                "path": relative,
                "size": os.path.getsize(path),
                "sha256": sha256_file(path),
            })
    return {
        "schema": "helix-corpus-source-snapshot/1.0",
        "revision": revision,
        "file_count": len(files),
        "bytes_total": sum(item["size"] for item in files),
        "files": files,
    }


def write_snapshot(path, snapshot):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    text = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--exclude-dir", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        snapshot = build_snapshot(args.source, args.revision, args.exclude_dir)
        evidence_sha256 = write_snapshot(args.out, snapshot)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 4
    print(json.dumps({
        "path": args.out,
        "source_sha256": evidence_sha256,
        "file_count": snapshot["file_count"],
        "bytes_total": snapshot["bytes_total"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
