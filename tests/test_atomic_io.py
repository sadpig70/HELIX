"""Tests for v0.4 F2 AtomicActuator: crash-safe JSON writes + corpus write guard."""
import json
import os
import tempfile
import unittest
from unittest import mock

import tests._path  # noqa: F401
import helix
from core.helix_io import atomic_write_json, read_json


class TestAtomicWrite(unittest.TestCase):
    def test_write_then_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.json")
            atomic_write_json(p, {"b": 2, "a": 1})
            with open(p, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"a": 1, "b": 2})

    def test_sorted_keys_stable(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.json")
            atomic_write_json(p, {"z": 1, "a": 1})
            with open(p, encoding="utf-8") as f:
                text = f.read()
            self.assertLess(text.index('"a"'), text.index('"z"'))

    def test_creates_missing_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sub", "deep", "x.json")
            atomic_write_json(p, {"ok": True})
            self.assertTrue(os.path.exists(p))

    def test_failure_leaves_original_intact_and_no_temp(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.json")
            atomic_write_json(p, {"v": 1})                 # original valid file
            # force a failure during replace; original must survive, no .tmp left behind
            with mock.patch("core.helix_io.os.replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    atomic_write_json(p, {"v": 2})
            with open(p, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"v": 1})   # unchanged (atomic)
            leftover = [n for n in os.listdir(d) if n.endswith(".tmp")]
            self.assertEqual(leftover, [])

    def test_read_json_default_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_json(os.path.join(d, "nope.json"), default=[]), [])


class TestCorpusWriteGuard(unittest.TestCase):
    def test_rejects_invalid_entry(self):
        with tempfile.TemporaryDirectory() as d:
            cor = os.path.join(d, "corpus.json")
            with self.assertRaises(ValueError):
                helix.append_corpus_entry(cor, {"project": "", "origin": "explore"})
            with self.assertRaises(ValueError):
                helix.append_corpus_entry(cor, {"project": "P", "origin": "bogus"})
            self.assertFalse(os.path.exists(cor))  # nothing written on rejection

    def test_accepts_valid_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            cor = os.path.join(d, "corpus.json")
            e = {"project": "P", "origin": "explore"}
            self.assertTrue(helix.append_corpus_entry(cor, e))
            self.assertFalse(helix.append_corpus_entry(cor, e))


if __name__ == "__main__":
    unittest.main()
