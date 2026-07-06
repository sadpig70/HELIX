#!/usr/bin/env python3
"""Local project import-path helpers for HELIX integration tests and CLIs."""

import os
import sys


def ensure_project_src(root: str, project_name: str) -> str | None:
    """Make ``<root>/<project_name>/src`` importable when it exists."""
    src = os.path.join(root, project_name, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
        return src
    return src if os.path.isdir(src) else None
