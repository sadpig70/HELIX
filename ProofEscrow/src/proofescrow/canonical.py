"""Canonical encoding and signature primitives for ProofEscrow."""

import copy
import hashlib
import hmac
import json


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def signature_payload(step):
    value = copy.deepcopy(step)
    value.pop("signature", None)
    return canonical_json(value).encode("utf-8")


def sign_step(step, key):
    if not isinstance(key, str) or not key:
        raise ValueError("signing key must be a non-empty string")
    value = copy.deepcopy(step)
    value["signature"] = hmac.new(
        key.encode("utf-8"), signature_payload(value), hashlib.sha256).hexdigest()
    return value


def verify_step_signature(step, key):
    signature = str(step.get("signature", ""))
    if not signature or not isinstance(key, str) or not key:
        return False
    expected = hmac.new(
        key.encode("utf-8"), signature_payload(step), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
