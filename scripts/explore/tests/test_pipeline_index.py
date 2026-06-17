"""Tests for pipeline_index — determinism, line accuracy, consumed cross-ref."""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # D:/IdeaFirst (tests → scripts → .agents → root)
SCRIPT = ROOT / "scripts" / "explore" / "pipeline_index.py"

spec = importlib.util.spec_from_file_location("pipeline_index", SCRIPT)
pi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi)


def test_build_is_deterministic():
    a = json.dumps(pi.build_index(ROOT), sort_keys=True)
    b = json.dumps(pi.build_index(ROOT), sort_keys=True)
    assert a == b


def test_line_index_matches_actual_id_lines():
    pool_path = ROOT / ".cix" / "latest" / "idea_pool.yaml"
    lines = pi.line_index(pool_path)
    text = pool_path.read_text(encoding="utf-8").splitlines()
    # every indexed line must actually be a '- id: X' line for that id
    for iid, ln in lines.items():
        assert re.match(rf"^\s*-\s*id:\s*{re.escape(iid)}\s*$", text[ln - 1]), (iid, ln)


def test_idea_pool_core_fields():
    pool = pi.index_idea_pool(ROOT / ".cix" / "latest")
    assert pool["count"] == 24
    e = pool["ideas"]["IDEA-016"]
    assert e["mechanism"] == "refusal-option-market"
    assert e["is_white_space"] is True
    assert e["source_insight_id"] == "INS-L10-003"
    assert e["line"] is not None


def test_consumed_crossref_marks_published_idea():
    pool = pi.index_idea_pool(ROOT / ".cix" / "latest")
    n = pi.crossref_consumed(pool, ROOT / ".idea-ledger" / "consumed_ideas.yaml")
    assert n >= 1
    # IDEA-016 was materialized as refusaloption in this same cix round
    consumed = pool["ideas"]["IDEA-016"]["consumed"]
    assert consumed and "refusaloption" in str(consumed)


def test_consumed_crossref_is_same_round_only():
    # an idea id NOT in the current pool's cix round must not be falsely marked
    pool = pi.index_idea_pool(ROOT / ".cix" / "latest")
    pool["round_id"] = "CIX-NONEXISTENT-999"
    n = pi.crossref_consumed(pool, ROOT / ".idea-ledger" / "consumed_ideas.yaml")
    assert n == 0


def test_aggregate_consistency():
    index = pi.build_index(ROOT)
    s = index["summary"]
    assert s["pool_total"] == s["pool_consumed"] + s["pool_eligible"]
    assert sum(index["summary"]["mechanism_distribution"].values()) == s["pool_total"]
    assert 0.0 <= s["white_space_share"] <= 1.0


def test_cli_build_then_lookup_no_full_load(tmp_path):
    # build writes the index; lookup reads only the index for the entry fields
    r = subprocess.run([sys.executable, str(SCRIPT), "build", "--project-root", str(ROOT)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r2 = subprocess.run([sys.executable, str(SCRIPT), "lookup", "IDEA-016", "--project-root", str(ROOT)],
                        capture_output=True, text=True)
    assert r2.returncode == 0
    assert "refusal-option-market" in r2.stdout
    assert "idea_pool.yaml:" in r2.stdout
    r3 = subprocess.run([sys.executable, str(SCRIPT), "lookup", "NOPE-999", "--project-root", str(ROOT)],
                        capture_output=True, text=True)
    assert r3.returncode == 1


def test_evx_winners_present():
    index = pi.build_index(ROOT)
    w = index["evx_winners"]
    assert w.get("final_1") == "IDEA-018"
