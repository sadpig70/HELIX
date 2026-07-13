#!/usr/bin/env python3
"""Deterministic preflight for independently provisioned HELIX projects."""

import os

REQUIRED_PROJECT_FILES = {
    "ActionHandbackVerifier": (
        "src/ActionHandbackVerifier/__init__.py",
        "src/ActionHandbackVerifier/verifier.py",
        "src/ActionHandbackVerifier/ledger.py",
        "src/ActionHandbackVerifier/cli.py",
    ),
}


def provisioning_report(root: str, projects=None) -> dict:
    names = sorted(projects or REQUIRED_PROJECT_FILES)
    rows = []
    for name in names:
        required = REQUIRED_PROJECT_FILES.get(name)
        if required is None:
            rows.append({"project": name, "ready": False,
                         "missing": ["unknown project contract"]})
            continue
        missing = [path for path in required
                   if not os.path.isfile(os.path.join(root, name, path))]
        rows.append({"project": name, "ready": not missing,
                     "missing": missing})
    return {"ready": all(row["ready"] for row in rows), "projects": rows}
