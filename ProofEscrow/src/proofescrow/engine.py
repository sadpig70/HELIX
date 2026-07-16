"""Fail-closed artifact release escrow engine."""

import copy
import re

from .canonical import digest, verify_step_signature


REQUEST_SCHEMA = "proofescrow-request/1.0"
RECEIPT_SCHEMA = "proofescrow-receipt/1.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(value):
    return bool(SHA256_RE.fullmatch(str(value or "")))


def _reason(reasons, code, path):
    reasons.append({"code": code, "path": path})


def evaluate(request, trust_store):
    """Return a deterministic RELEASED/HELD receipt for one request."""
    request = copy.deepcopy(request)
    trust_store = trust_store if isinstance(trust_store, dict) else {}
    reasons = []
    if request.get("schema") != REQUEST_SCHEMA:
        _reason(reasons, "INVALID_SCHEMA", "schema")
    for key in ("escrow_id", "artifact", "behavior", "policy"):
        if key not in request or request[key] in (None, ""):
            _reason(reasons, "MISSING_FIELD", key)

    artifact = request.get("artifact") if isinstance(request.get("artifact"), dict) else {}
    behavior = request.get("behavior") if isinstance(request.get("behavior"), dict) else {}
    policy = request.get("policy") if isinstance(request.get("policy"), dict) else {}
    artifact_sha = artifact.get("sha256")
    if not _sha256(artifact_sha):
        _reason(reasons, "INVALID_ARTIFACT_SHA256", "artifact.sha256")

    steps = artifact.get("steps") if isinstance(artifact.get("steps"), list) else []
    if not steps:
        _reason(reasons, "MISSING_STEPS", "artifact.steps")
    verified_steps = []
    signer_ids = set()
    step_ids = set()
    for index, step in enumerate(steps):
        path = f"artifact.steps[{index}]"
        if not isinstance(step, dict):
            _reason(reasons, "INVALID_STEP", path)
            continue
        missing = [key for key in ("step_id", "command", "materials", "products", "signer", "signature")
                   if key not in step or step[key] in (None, "")]
        for key in missing:
            _reason(reasons, "MISSING_STEP_FIELD", f"{path}.{key}")
        step_id = step.get("step_id")
        if step_id in step_ids:
            _reason(reasons, "DUPLICATE_STEP_ID", f"{path}.step_id")
        if step_id:
            step_ids.add(step_id)
        signer = step.get("signer")
        key = trust_store.get(signer)
        if key is None:
            _reason(reasons, "UNTRUSTED_SIGNER", f"{path}.signer")
        elif not verify_step_signature(step, key):
            _reason(reasons, "INVALID_STEP_SIGNATURE", f"{path}.signature")
        else:
            verified_steps.append(step_id)
            signer_ids.add(signer)

    required_signers = policy.get("required_signers") if isinstance(policy.get("required_signers"), list) else []
    for signer in sorted(set(required_signers) - signer_ids):
        _reason(reasons, "REQUIRED_SIGNER_MISSING", f"policy.required_signers:{signer}")
    if steps and _sha256(artifact_sha):
        products = steps[-1].get("products", []) if isinstance(steps[-1], dict) else []
        if artifact_sha not in products:
            _reason(reasons, "FINAL_PRODUCT_NOT_BOUND", "artifact.steps[-1].products")

    approved = policy.get("approved_behavior_sha256")
    baseline = behavior.get("baseline_sha256")
    observed = behavior.get("observed_sha256")
    for value, path in ((approved, "policy.approved_behavior_sha256"),
                        (baseline, "behavior.baseline_sha256"),
                        (observed, "behavior.observed_sha256")):
        if not _sha256(value):
            _reason(reasons, "INVALID_BEHAVIOR_SHA256", path)
    if approved != baseline:
        _reason(reasons, "UNAPPROVED_BASELINE", "behavior.baseline_sha256")
    if baseline != observed:
        _reason(reasons, "BEHAVIOR_DRIFT", "behavior.observed_sha256")
    if behavior.get("tests_passed") is not True:
        _reason(reasons, "TESTS_NOT_PASSED", "behavior.tests_passed")
    if behavior.get("deterministic") is not True:
        _reason(reasons, "NONDETERMINISTIC_BEHAVIOR", "behavior.deterministic")

    reasons = sorted({(item["code"], item["path"]) for item in reasons})
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "escrow_id": str(request.get("escrow_id", "")),
        "request_sha256": digest(request),
        "decision": "RELEASED" if not reasons else "HELD",
        "reasons": [{"code": code, "path": path} for code, path in reasons],
        "artifact_sha256": str(artifact_sha or ""),
        "verified_steps": verified_steps,
        "trusted_signers": sorted(signer_ids),
        "behavior_binding": {
            "approved_sha256": str(approved or ""),
            "baseline_sha256": str(baseline or ""),
            "observed_sha256": str(observed or ""),
        },
        "gene_provenance": {
            "signed_step_metadata": "HC-PILOT-EXT-001",
            "behavior_baseline_binding": "HC-PILOT-HELIX-002",
        },
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(request, trust_store, receipt):
    """Replay a receipt; trust secrets never become part of the receipt."""
    return evaluate(request, trust_store) == receipt
