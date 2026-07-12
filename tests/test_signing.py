import hashlib
import json
import os
import shutil
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_actuator import (
    append_actuation_ledger,
    read_actuation_ledger,
    verify_actuation_ledger,
)
from core.helix_holdout import canonical_json_bytes
from core.helix_signing import sign_bytes, verify_signature


KEY = "operator-secret-key-v1"
WRONG_KEY = "attacker-guess"


class TestSignPrimitive(unittest.TestCase):
    def test_sign_is_deterministic_and_verifies(self):
        sig = sign_bytes(KEY, b"hello")
        self.assertEqual(sig, sign_bytes(KEY, b"hello"))
        self.assertTrue(verify_signature(KEY, b"hello", sig))

    def test_wrong_key_or_data_fails(self):
        sig = sign_bytes(KEY, b"hello")
        self.assertFalse(verify_signature(WRONG_KEY, b"hello", sig))
        self.assertFalse(verify_signature(KEY, b"tampered", sig))
        self.assertFalse(verify_signature(KEY, b"hello", "not-a-real-sig"))

    def test_empty_key_and_bad_types_are_rejected(self):
        for bad in ("", b""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                sign_bytes(bad, b"x")
        with self.assertRaises(TypeError):
            sign_bytes(123, b"x")
        with self.assertRaises(TypeError):
            sign_bytes(KEY, "not-bytes")


class TestSignedLedger(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-signing-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ledger = "_sig/ledger.jsonl"

    def append(self, n=3, key=KEY):
        for i in range(n):
            append_actuation_ledger(self.root, self.ledger, "gate", f"REQ-{i}",
                                    {"decision": "ALLOW", "i": i},
                                    signing_key=key)

    def test_signed_ledger_verifies_with_the_key(self):
        self.append()
        self.assertEqual(verify_actuation_ledger(self.root, self.ledger), [])
        self.assertEqual(
            verify_actuation_ledger(self.root, self.ledger, signing_key=KEY), [])
        entries = read_actuation_ledger(self.root, self.ledger)
        self.assertTrue(all("entry_hmac" in e for e in entries))

    def test_wrong_key_is_rejected(self):
        self.append()
        problems = verify_actuation_ledger(self.root, self.ledger,
                                           signing_key=WRONG_KEY)
        self.assertTrue(all("keyed signature invalid" in p for p in problems))
        self.assertEqual(len(problems), 3)

    def test_adversary_rebuild_without_key_is_caught(self):
        # The security-persona attack: an adversary with write access rebuilds
        # the whole chain (recomputing seq/parent/entry_sha256) to launder an
        # entry. Unkeyed integrity passes; the keyed check does NOT.
        self.append()
        full = os.path.join(self.root, *self.ledger.split("/"))
        entries = [json.loads(l) for l in open(full, encoding="utf-8")
                   if l.strip()]
        entries[1]["receipt"]["decision"] = "DENY_laundered"
        # rebuild integrity (seq/parent/seal) but the adversary lacks the key,
        # so they cannot recompute a valid entry_hmac — leave/forge it.
        parent = None
        for i, e in enumerate(entries):
            e["seq"] = i
            e["parent_sha256"] = parent
            body = {k: v for k, v in e.items()
                    if k not in ("entry_sha256", "entry_hmac")}
            e["entry_sha256"] = hashlib.sha256(
                canonical_json_bytes(body)).hexdigest()
            # adversary forges a plausible-looking hmac (they don't have KEY)
            e["entry_hmac"] = hashlib.sha256(
                canonical_json_bytes(body)).hexdigest()
            parent = e["entry_sha256"]
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        # unkeyed integrity: the rebuilt chain passes (this is the vulnerability)
        self.assertEqual(verify_actuation_ledger(self.root, self.ledger), [])
        # keyed: the forgery is caught
        problems = verify_actuation_ledger(self.root, self.ledger,
                                           signing_key=KEY)
        self.assertTrue(problems)
        self.assertTrue(any("keyed signature invalid" in p for p in problems))

    def test_unsigned_ledger_is_backward_compatible(self):
        self.append(key=None)
        entries = read_actuation_ledger(self.root, self.ledger)
        self.assertTrue(all("entry_hmac" not in e for e in entries))
        self.assertEqual(verify_actuation_ledger(self.root, self.ledger), [])
        # verifying an unsigned ledger WITH a key correctly flags missing sigs
        problems = verify_actuation_ledger(self.root, self.ledger,
                                           signing_key=KEY)
        self.assertTrue(all("invalid or missing" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
