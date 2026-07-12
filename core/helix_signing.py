#!/usr/bin/env python3
"""Keyed signing for HELIX seals (security backlog #2).

The persona conditional-adoption trial's security engineer found that the
unkeyed SHA-256 seals give INTEGRITY, not AUTHENTICITY: a write-capable
adversary who rebuilds packet+ledger together passes replay and chain
verification, because anyone can recompute a plain SHA-256. This module adds
keyed HMAC-SHA256 so that only a holder of the signing key can produce a
verifiable seal.

Design decisions (deterministic-core constraints):
- HMAC-SHA256 via stdlib ``hmac``/``hashlib``. Asymmetric signatures
  (Ed25519 etc.) are not in the standard library, and the deterministic core
  forbids third-party crypto packages — so this is a symmetric MAC: signer and
  verifier share the key.
- The key is INJECTED by the caller, never generated here. The core has no
  randomness, no key store, no clock; key management lives outside it.
- Threat model: an adversary with write access to the packet/ledger STORE but
  WITHOUT the signing key cannot forge a valid signature, so a rebuilt chain
  is detected. An insider who also holds the key is out of scope for this
  layer — external anchoring (a later layer) addresses that.
- Backward compatible: components take an optional key; key=None keeps the
  existing unkeyed integrity behavior, a key adds authenticity on top.

``hmac.compare_digest`` is used for constant-time comparison. Deterministic,
stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import hmac
import sys


def _key_bytes(key) -> bytes:
    if isinstance(key, bytes):
        if not key:
            raise ValueError("signing key must be non-empty")
        return key
    if isinstance(key, str):
        if not key:
            raise ValueError("signing key must be non-empty")
        return key.encode("utf-8")
    raise TypeError("signing key must be bytes or str")


def sign_bytes(key, data: bytes) -> str:
    """Keyed HMAC-SHA256 hexdigest over ``data``. Deterministic in (key, data)."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data to sign must be bytes")
    return hmac.new(_key_bytes(key), bytes(data), hashlib.sha256).hexdigest()


def verify_signature(key, data: bytes, signature) -> bool:
    """Constant-time verification of a keyed signature over ``data``."""
    if not isinstance(signature, str) or not signature:
        return False
    return hmac.compare_digest(sign_bytes(key, data), signature)


if __name__ == "__main__":
    print("library module — sign_bytes(key, data) / verify_signature(key, data, sig)")
    sys.exit(2)
