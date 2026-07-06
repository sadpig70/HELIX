"""Make HELIX and its local src-layout projects importable for unittest."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

for project in (
    "ActionHandbackVerifier",
    "BioClock",
    "CryoFutures",
    "MineralShock",
    "SkyGrid",
    "SoilBond",
):
    src = os.path.join(ROOT, project, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
