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
from core.helix_anchor import (
    compute_anchor,
    seal_anchor,
    verify_against_anchor,
    verify_anchor_seal,
)
from core.helix_holdout import canonical_json_bytes
from core.helix_signing import sign_bytes


KEY = "insider-signing-key"


class AnchorFixtureCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="helix-anchor-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ledger = "_anch/ledger.jsonl"

    def append(self, n, start=0, key=KEY):
        for i in range(start, start + n):
            append_actuation_ledger(self.root, self.ledger, "gate", f"REQ-{i}",
                                    {"decision": "ALLOW", "i": i},
                                    signing_key=key)

    def anchor(self, external_ref="git-commit:abc123", by="operator-1"):
        return seal_anchor(compute_anchor(self.root, self.ledger),
                           external_ref, by)


class TestAnchorBasics(AnchorFixtureCase):
    def test_seal_and_verify(self):
        self.append(3)
        anchor = self.anchor()
        self.assertTrue(verify_anchor_seal(anchor))
        self.assertEqual(anchor["seq"], 2)
        self.assertEqual(verify_against_anchor(self.root, self.ledger, anchor), [])

    def test_append_only_growth_stays_consistent(self):
        self.append(3)
        anchor = self.anchor()  # seq 2
        self.append(2, start=3)  # grow to seq 4
        # the anchored prefix is unchanged, so the anchor still holds
        self.assertEqual(verify_against_anchor(self.root, self.ledger, anchor), [])

    def test_empty_ledger_cannot_be_anchored(self):
        with self.assertRaisesRegex(ValueError, "empty ledger"):
            self.anchor()
        with self.assertRaisesRegex(ValueError, "external_ref"):
            seal_anchor({"seq": 0, "head_sha256": "x", "prefix_digest": "y"},
                        "", "op")


class TestInsiderRewriteCaught(AnchorFixtureCase):
    def rebuild_ledger_resigned(self, mutate):
        """Simulate a KEY-HOLDING insider: rewrite entries and fully re-sign,
        so keyed verification passes but the external anchor should not."""
        full = os.path.join(self.root, *self.ledger.split("/"))
        entries = [json.loads(l) for l in open(full, encoding="utf-8") if l.strip()]
        mutate(entries)
        parent = None
        for i, e in enumerate(entries):
            e["seq"] = i
            e["parent_sha256"] = parent
            body = {k: v for k, v in e.items()
                    if k not in ("entry_sha256", "entry_hmac")}
            e["entry_sha256"] = hashlib.sha256(
                canonical_json_bytes(body)).hexdigest()
            e["entry_hmac"] = sign_bytes(KEY, canonical_json_bytes(body))
            parent = e["entry_sha256"]
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    def test_resigned_rewrite_passes_keyed_but_fails_anchor(self):
        self.append(3)
        anchor = self.anchor()  # externally published at seq 2

        def launder(entries):
            entries[1]["receipt"]["decision"] = "DENY_laundered"

        self.rebuild_ledger_resigned(launder)
        # insider re-signed, so keyed verification is fooled:
        self.assertEqual(
            verify_actuation_ledger(self.root, self.ledger, signing_key=KEY), [])
        # but the external anchor catches the prefix rewrite:
        problems = verify_against_anchor(self.root, self.ledger, anchor)
        self.assertTrue(problems)
        self.assertTrue(any("rewritten" in p for p in problems))

    def test_truncation_below_anchor_is_caught(self):
        self.append(4)
        anchor = self.anchor()  # seq 3
        full = os.path.join(self.root, *self.ledger.split("/"))
        entries = [json.loads(l) for l in open(full, encoding="utf-8") if l.strip()]
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            for e in entries[:2]:  # drop below the anchor
                f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        problems = verify_against_anchor(self.root, self.ledger, anchor)
        self.assertTrue(any("removed/truncated" in p for p in problems), problems)

    def test_broken_anchor_seal_is_reported(self):
        self.append(2)
        anchor = dict(self.anchor())
        anchor["head_sha256"] = "0" * 64  # tamper without resealing
        problems = verify_against_anchor(self.root, self.ledger, anchor)
        self.assertTrue(any("anchor seal is broken" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
