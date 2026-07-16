"""Deterministic sample inputs."""

import copy

from .canonical import sign_step


TEST_KEY = "proofescrow-demo-key-v1"
ARTIFACT_SHA = "a" * 64
BEHAVIOR_SHA = "b" * 64


def sample_bundle(kind="released"):
    trust_store = {"builder-1": TEST_KEY}
    step = sign_step({
        "step_id": "build-1",
        "command": ["python", "-m", "build"],
        "materials": ["c" * 64],
        "products": [ARTIFACT_SHA],
        "signer": "builder-1",
    }, TEST_KEY)
    request = {
        "schema": "proofescrow-request/1.0",
        "escrow_id": "PE-DEMO-001",
        "artifact": {"name": "demo-wheel", "sha256": ARTIFACT_SHA, "steps": [step]},
        "behavior": {
            "baseline_sha256": BEHAVIOR_SHA,
            "observed_sha256": BEHAVIOR_SHA,
            "tests_passed": True,
            "deterministic": True,
        },
        "policy": {
            "approved_behavior_sha256": BEHAVIOR_SHA,
            "required_signers": ["builder-1"],
        },
    }
    if kind == "held-signature":
        request["artifact"]["steps"][0]["command"] = ["python", "tampered.py"]
    elif kind == "held-behavior":
        request["behavior"]["observed_sha256"] = "d" * 64
    elif kind != "released":
        raise ValueError(f"unknown sample kind: {kind}")
    return {"request": copy.deepcopy(request), "trust_store": trust_store}
