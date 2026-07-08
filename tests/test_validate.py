import json
import os
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_validate import (
    validate_determinism_boundary, validate_ledger, validate_diversity_report,
    validate_forward_predict_gate,
    validate_loop_action, validate_machine_probe_dataset, validate_project,
    validate_probe_router, validate_zero_kernel_change,
)
from core.helix_diversity import measure_diversity
from core.helix_loop import next_action

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _kernel_lock_for(tmp, body="VALUE = 1\n"):
    import hashlib

    kernel_path = os.path.join(tmp, "FooStra", "foo_core", "kernel.py")
    _write(kernel_path, body)
    with open(kernel_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    lock = {
        "version": 1,
        "platforms": {
            "FooStra": {
                "kernel_dirs": ["foo_core"],
                "files": {"foo_core/kernel.py": digest},
            }
        },
    }
    _write(os.path.join(tmp, "seed", "condense", "platform-kernel-lock.json"),
           json.dumps(lock, indent=2, sort_keys=True))


def _machine_probe_gate_for(tmp, platforms=None):
    platforms = platforms or ["FooStra"]
    for platform in platforms:
        os.makedirs(os.path.join(tmp, platform), exist_ok=True)
    gate = {
        "version": 1,
        "required_platforms": platforms,
        "criteria": {
            "total_platform_packs": 1,
            "implemented_probe_cases": 2,
            "scored_claims": 2,
            "matched_claims": 2,
            "agreement": 1.0,
            "allow_errors": False,
            "allow_skipped_claims": False,
        },
    }
    _write(os.path.join(tmp, "seed", "condense", "machine-probe-gate.json"),
           json.dumps(gate, indent=2, sort_keys=True))


def _router_gate_for(tmp, platforms=None):
    platforms = platforms or ["FooStra"]
    for platform in platforms:
        os.makedirs(os.path.join(tmp, platform), exist_ok=True)
    layered = {
        "layer1_platforms": [
            {"name": "FooStra", "kernel_machines": ["M1"]},
        ]
    }
    gate = {
        "version": 1,
        "required_platforms": platforms,
        "layered_corpus": "seed/condense/layered-corpus.json",
        "criteria": {
            "decision_count": 3,
            "summary": {"BUILD_ON_PLATFORM": 2, "DEFER": 1},
            "deferred_machines": {"M3": 1},
        },
    }
    _write(os.path.join(tmp, "seed", "condense", "layered-corpus.json"),
           json.dumps(layered, indent=2, sort_keys=True))
    _write(os.path.join(tmp, "seed", "condense", "router-gate.json"),
           json.dumps(gate, indent=2, sort_keys=True))


def _forward_predict_gate_for(tmp, platforms=None, action="BUILD_ON_PLATFORM"):
    platforms = platforms or ["Scorestra"]
    for platform in platforms:
        os.makedirs(os.path.join(tmp, platform), exist_ok=True)
    layered = {"layer1_platforms": [{"name": "Scorestra", "kernel_machines": ["M15"]}]}
    candidate = {
        "id": "score",
        "expected": ["M15"],
        "artifact": {
            "operation": "assessment_scoring",
            "weights": {"impact": 1.0},
            "bands": [{"min": 0.8, "tier": "high"}, {"min": 0.0, "tier": "low"}],
            "scored": [{"id": "x", "score": 0.9, "tier": "high"}],
            "count_by_tier": {"high": 1, "low": 0},
        },
    }
    gate = {
        "version": 1,
        "required_platforms": platforms,
        "layered_corpus": "seed/condense/layered-corpus.json",
        "fixtures": [
            {"candidate": "examples/condense/score.json", "action": action, "platform": "Scorestra"},
        ],
    }
    _write(os.path.join(tmp, "seed", "condense", "layered-corpus.json"),
           json.dumps(layered, indent=2, sort_keys=True))
    _write(os.path.join(tmp, "examples", "condense", "score.json"),
           json.dumps(candidate, indent=2, sort_keys=True))
    _write(os.path.join(tmp, "seed", "condense", "forward-predict-gate.json"),
           json.dumps(gate, indent=2, sort_keys=True))


def _probe_dataset(agreement=1.0, errors=None, skipped=None):
    return {
        "total_platform_packs": 1,
        "implemented_probe_cases": 2,
        "errors": errors or [],
        "skipped_claims": skipped or [],
        "agreement": {
            "scored_claims": 2,
            "matched_claims": 2 if agreement == 1.0 else 1,
            "agreement": agreement,
        },
    }


def _router_dataset():
    return {
        "agreement": {
            "rows": [
                {"id": "kernel", "platform": "FooStra", "pack": "core", "matched": ["M1"]},
                {"id": "pack", "platform": "FooStra", "pack": "drift", "matched": ["M2"]},
                {"id": "reference", "platform": "HELIX", "pack": "core", "matched": ["M3"]},
            ]
        }
    }


class TestValidate(unittest.TestCase):
    def test_example_ledger_valid(self):
        with open(os.path.join(ROOT, "examples", "consumed_ledger.json"), encoding="utf-8") as f:
            ledger = json.load(f)
        self.assertEqual(validate_ledger(ledger), [])

    def test_bad_ledger_detected(self):
        problems = validate_ledger({"consumed": [{"title": "no id"}]})
        self.assertTrue(any("idea_id" in p for p in problems))

    def test_diversity_report_shape_valid(self):
        rep = measure_diversity([{"title": "a b", "domains": ["x", "y"]}], sim=None)
        self.assertEqual(validate_diversity_report(rep), [])

    def test_loop_action_shape_valid(self):
        self.assertEqual(validate_loop_action(next_action({"corpus_size": 0})), [])

    def test_invalid_loop_action_detected(self):
        problems = validate_loop_action({"action": "NONSENSE"})
        self.assertTrue(problems)

    def test_project_structure_valid(self):
        # the shipped project must validate cleanly
        self.assertEqual(validate_project(ROOT), [])

    def test_determinism_boundary_accepts_clean_runtime_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "core"))
            with open(os.path.join(tmp, "core", "clean.py"), "w", encoding="utf-8") as f:
                f.write("def choose(value):\n    return value\n")
            self.assertEqual(validate_determinism_boundary(tmp), [])

    def test_determinism_boundary_rejects_network_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "core"))
            with open(os.path.join(tmp, "core", "bad.py"), "w", encoding="utf-8") as f:
                f.write("import requests\n")
            problems = validate_determinism_boundary(tmp)
            self.assertTrue(any("forbidden import requests" in p for p in problems))

    def test_determinism_boundary_rejects_aliased_clock_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "core"))
            with open(os.path.join(tmp, "core", "bad.py"), "w", encoding="utf-8") as f:
                f.write("from datetime import datetime as dt\n\ndef stamp():\n    return dt.now()\n")
            problems = validate_determinism_boundary(tmp)
            self.assertTrue(any("forbidden call datetime.datetime.now" in p for p in problems))

    def test_zero_kernel_change_accepts_locked_kernel_and_pack_growth(self):
        with tempfile.TemporaryDirectory() as tmp:
            _kernel_lock_for(tmp)
            _write(os.path.join(tmp, "FooStra", "foo_packs", "new_pack.py"), "PACK = True\n")
            self.assertEqual(validate_zero_kernel_change(tmp), [])

    def test_zero_kernel_change_rejects_kernel_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            _kernel_lock_for(tmp)
            _write(os.path.join(tmp, "FooStra", "foo_core", "kernel.py"), "VALUE = 2\n")
            problems = validate_zero_kernel_change(tmp)
            self.assertTrue(any("kernel drift: foo_core/kernel.py" in p for p in problems))

    def test_zero_kernel_change_rejects_new_kernel_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _kernel_lock_for(tmp)
            _write(os.path.join(tmp, "FooStra", "foo_core", "new_kernel.py"), "VALUE = 2\n")
            problems = validate_zero_kernel_change(tmp)
            self.assertTrue(any("unlocked kernel file appeared: foo_core/new_kernel.py" in p
                                for p in problems))

    def test_machine_probe_dataset_accepts_locked_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            _machine_probe_gate_for(tmp)
            self.assertEqual(validate_machine_probe_dataset(tmp, _probe_dataset()), [])

    def test_machine_probe_dataset_rejects_agreement_drop(self):
        with tempfile.TemporaryDirectory() as tmp:
            _machine_probe_gate_for(tmp)
            problems = validate_machine_probe_dataset(tmp, _probe_dataset(agreement=0.5))
            self.assertTrue(any("agreement 0.5 != 1.0" in p for p in problems))
            self.assertTrue(any("matched_claims 1 != 2" in p for p in problems))

    def test_machine_probe_dataset_skips_when_platform_repos_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _machine_probe_gate_for(tmp, platforms=["MissingStra"])
            # Simulate a plain HELIX checkout where nested platform repos are not vendored.
            os.rmdir(os.path.join(tmp, "MissingStra"))
            problems = validate_machine_probe_dataset(tmp, _probe_dataset(agreement=0.0))
            self.assertEqual(problems, [])

    def test_probe_router_accepts_locked_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            _router_gate_for(tmp)
            self.assertEqual(validate_probe_router(tmp, _router_dataset()), [])

    def test_probe_router_rejects_summary_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            _router_gate_for(tmp)
            bad = {"agreement": {"rows": [_router_dataset()["agreement"]["rows"][0]]}}
            problems = validate_probe_router(tmp, bad)
            self.assertTrue(any("summary" in p for p in problems))
            self.assertTrue(any("decision_count" in p for p in problems))

    def test_probe_router_skips_when_platform_repos_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _router_gate_for(tmp, platforms=["MissingStra"])
            os.rmdir(os.path.join(tmp, "MissingStra"))
            self.assertEqual(validate_probe_router(tmp, {"agreement": {"rows": []}}), [])

    def test_forward_predict_gate_accepts_locked_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            _forward_predict_gate_for(tmp)
            self.assertEqual(validate_forward_predict_gate(tmp, {"agreement": {"rows": []}}), [])

    def test_forward_predict_gate_rejects_prediction_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            _forward_predict_gate_for(tmp, action="DEFER")
            problems = validate_forward_predict_gate(tmp, {"agreement": {"rows": []}})
            self.assertTrue(any("action 'BUILD_ON_PLATFORM' != 'DEFER'" in p for p in problems))

    def test_forward_predict_gate_skips_when_platform_repos_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _forward_predict_gate_for(tmp, platforms=["MissingStra"])
            os.rmdir(os.path.join(tmp, "MissingStra"))
            self.assertEqual(validate_forward_predict_gate(tmp, {"agreement": {"rows": []}}), [])


if __name__ == "__main__":
    unittest.main()
