import unittest

import tests._path  # noqa: F401
from core.helix_fingerprint import (
    normalize_name, tokenize_name, source_fingerprint, generated_fingerprint,
)


class TestFingerprint(unittest.TestCase):
    def test_normalize_name(self):
        self.assertEqual(normalize_name("Withheld Action-Witness!"), "withheldactionwitness")
        self.assertEqual(normalize_name(""), "")
        self.assertEqual(normalize_name(None), "")

    def test_tokenize_camelcase(self):
        self.assertEqual(tokenize_name("DwellProvenanceGate"), ["dwell", "provenance", "gate"])
        self.assertEqual(tokenize_name("agent-PACT_v2"), ["agent", "pact", "v2"])

    def test_source_fingerprint_order_independent(self):
        a = source_fingerprint(["ReleaseMesh", "ADPR", "PnR", "ADPR"])
        b = source_fingerprint(["PnR", "ADPR", "ReleaseMesh"])
        self.assertEqual(a, b)
        self.assertEqual(a, "ADPR+PnR+ReleaseMesh")

    def test_empty_fingerprints(self):
        self.assertEqual(source_fingerprint([]), "")
        self.assertEqual(generated_fingerprint(None), "")

    def test_deterministic(self):
        for _ in range(3):
            self.assertEqual(source_fingerprint(["b", "a"]), "a+b")


if __name__ == "__main__":
    unittest.main()
