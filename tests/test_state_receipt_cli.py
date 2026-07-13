import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import tests._path  # noqa: F401
import helix
from core.helix_schema import validate_against_schema
from core.helix_state_receipt import seal_receipt, sha256_file, verify_receipt_hash
from engines.loaders import resolve_exploit_paths, resolve_explore_paths


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "schemas", "helix-state-receipt.schema.json")
EXPLORE = os.path.join(ROOT, "examples", "explore_state")
EXPLOIT = os.path.join(ROOT, "examples", "exploit_state")


def _write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


class TestSelectedLoaderPaths(unittest.TestCase):
    def test_explore_paths_match_fixture_inputs(self):
        paths = resolve_explore_paths(EXPLORE)
        self.assertEqual(os.path.basename(paths["explore_winner"]), "stage6_final.json")
        self.assertEqual(os.path.basename(paths["explore_manifest"]), "manifest.json")
        self.assertEqual(os.path.basename(paths["explore_pool"]), "idea_pool.json")
        self.assertEqual(os.path.basename(paths["explore_consumed"]), "consumed_ideas.json")

    def test_exploit_paths_match_fixture_inputs(self):
        paths = resolve_exploit_paths(EXPLOIT)
        self.assertEqual(os.path.basename(paths["exploit_registry"]), "registry.json")
        self.assertEqual(os.path.basename(paths["exploit_candidates"]), "candidates.json")
        self.assertNotIn("exploit_run_status", paths)


class TestStateReceiptCli(unittest.TestCase):
    def base_argv(self):
        return [
            "helix.py", "state-receipt",
            "--explore-root", EXPLORE,
            "--exploit-root", EXPLOIT,
            "--layered-corpus", os.path.join(ROOT, "does-not-exist.json"),
        ]

    def test_stdout_is_schema_valid_sealed_receipt(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = helix._main(self.base_argv())
        self.assertEqual(rc, 0)
        receipt = json.loads(buf.getvalue())
        self.assertEqual(validate_against_schema(receipt, SCHEMA), [])
        self.assertTrue(verify_receipt_hash(receipt))
        self.assertEqual(receipt["next_action"]["action"], "RUN_EXPLORE")
        # Default reports carry no sealed hash, so none can be fresh. Whether a
        # given report is "unverifiable" (present but unbound, e.g. local
        # _workspace) or "missing" (absent, e.g. CI) is environment-dependent;
        # either way it is non-fresh and must block actuation.
        statuses = [row["status"] for row in receipt["report_freshness"]]
        self.assertTrue(all(s in ("unverifiable", "missing") for s in statuses),
                        statuses)
        clearances = receipt["authority"]["required_clearances"]
        self.assertTrue("unverifiable_report" in clearances
                        or "missing_report" in clearances, clearances)
        self.assertFalse(receipt["authority"]["actuator_ready"])

    def test_out_is_atomic_json_and_excluded_from_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "receipt.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = helix._main(self.base_argv() + ["--out", out])
            self.assertEqual(rc, 0)
            self.assertEqual(buf.getvalue(), "")
            with open(out, encoding="utf-8") as f:
                receipt = json.load(f)
            self.assertTrue(verify_receipt_hash(receipt))
            self.assertNotIn("--out", receipt["replay_command"]["argv"])
            self.assertNotIn(out, receipt["replay_command"]["argv"])

    def test_complete_report_seals_can_be_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.json")
            report = os.path.join(tmp, "report.json")
            seals = os.path.join(tmp, "seals.json")
            _write_json(source, {"source": 1})
            _write_json(report, {"result": "ok"})
            binding = lambda name: {
                "report": name,
                "path": report,
                "expected_sha256": sha256_file(report),
                "sources": [{"path": source, "sha256": sha256_file(source)}],
            }
            _write_json(seals, {"reports": [
                binding("machine_probe"),
                binding("forward_candidate_manifest"),
                binding("forward_prediction"),
            ]})
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = helix._main(self.base_argv() + ["--report-seals", seals])
            self.assertEqual(rc, 0)
            receipt = json.loads(buf.getvalue())
            self.assertEqual([row["status"] for row in receipt["report_freshness"]],
                             ["fresh", "fresh", "fresh"])
            self.assertTrue(all("\\" not in path for row in receipt["report_freshness"]
                                for path in row["source_paths"]))
            self.assertNotIn("unverifiable_report",
                             receipt["authority"]["required_clearances"])

    def test_invalid_report_seals_shape_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seals = os.path.join(tmp, "seals.json")
            _write_json(seals, {"not_reports": []})
            with self.assertRaisesRegex(ValueError, "reports array"):
                helix._main(self.base_argv() + ["--report-seals", seals])

    def test_compare_identical_state_has_no_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            stored = os.path.join(tmp, "stored.json")
            self.assertEqual(helix._main(self.base_argv() + ["--out", stored]), 0)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = helix._main(self.base_argv() + ["--compare", stored])
            self.assertEqual(rc, 0)
            receipt = json.loads(buf.getvalue())
            self.assertFalse(receipt["drift"]["drifted"])
            self.assertNotIn("state_drift", receipt["authority"]["required_clearances"])
            self.assertTrue(verify_receipt_hash(receipt))

    def test_compare_action_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            stored = os.path.join(tmp, "stored.json")
            self.assertEqual(helix._main(self.base_argv() + ["--out", stored]), 0)
            with open(stored, encoding="utf-8") as f:
                old = json.load(f)
            old["next_action"] = {"action": "RUN_EXPLORE", "why": "old", "target": None}
            _write_json(stored, seal_receipt(old))
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = helix._main(self.base_argv() + ["--compare", stored])
            self.assertEqual(rc, 0)
            receipt = json.loads(buf.getvalue())
            self.assertIn("next_action", receipt["drift"]["categories"])
            self.assertIn("state_drift", receipt["authority"]["required_clearances"])
            self.assertFalse(receipt["authority"]["actuator_ready"])


if __name__ == "__main__":
    unittest.main()
