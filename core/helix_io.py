#!/usr/bin/env python3
"""HELIX atomic JSON I/O — the single crash-safe write primitive (stdlib only).

The actuator (close-loop) and the autonomous loop rely on idempotent, recoverable
writes (see docs/INSTRUCTIONS-helix-loop-autonomous.md §6). A plain `open(path,"w")`
leaves a half-written file if the process dies mid-dump, corrupting the ledger or
corpus. `scripts/exploit/concurrency.py` already had an atomic-write contract but
only for the exploit engine; the backbone needs one too and may depend only on
`core/`, so the primitive is promoted here as the single source of truth.

Atomicity: write to a temp file in the SAME directory (so `os.replace` is a same
-volume rename — atomic on POSIX and NTFS), then replace. On any failure the temp
file is removed and the original is left untouched. Deterministic: no clock/random
(the temp name comes from `tempfile.mkstemp`, which never affects the final path).
"""

import json
import os
import tempfile


def atomic_write_json(path: str, obj) -> None:
    """Serialize `obj` to `path` atomically (temp file + os.replace).

    After this returns, `path` holds the new content; if the process is killed
    mid-write, `path` is either the previous valid file or the new one — never a
    truncated half. JSON is pretty, UTF-8, sorted keys (stable diffs).
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)  # atomic same-volume rename
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def read_json(path: str, default=None):
    """Read a JSON file; return `default` if it does not exist."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
