import json
import os
import tempfile
import unittest

import tests._path  # noqa: F401
from core.helix_schema import schema_path, validate_against_schema
from scripts.corpus.parity_contract_runner import (
    build_proofescrow_contract,
    run_contract,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_ROOT = os.path.join(ROOT, "seed", "parity-provenance")
NOW = "2026-07-16T00:00:00Z"


class TestParityContractRunner(unittest.TestCase):
    def test_builds_and_runs_proofescrow_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract_path = os.path.join(tmp, "released-contract.json")
            receipt_path = os.path.join(tmp, "released-receipt.json")
            contract, problems = build_proofescrow_contract(ROOT, EVIDENCE_ROOT, contract_path)
            self.assertEqual(problems, [])
            self.assertEqual(validate_against_schema(contract, schema_path(ROOT, "parity-contract")), [])

            receipt, problems = run_contract(ROOT, contract_path, receipt_path, NOW)
            self.assertEqual(problems, [])
            self.assertEqual(receipt["decision"], "PASS")
            self.assertEqual(validate_against_schema(receipt, schema_path(ROOT, "parity-receipt")), [])
            self.assertEqual(receipt["observations"]["pack_receipt"]["decision"], "RELEASED")
            self.assertTrue(os.path.exists(receipt_path))

    def test_missing_input_is_unavailable_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract_path = os.path.join(tmp, "released-contract.json")
            receipt_path = os.path.join(tmp, "released-receipt.json")
            contract, _ = build_proofescrow_contract(ROOT, EVIDENCE_ROOT, contract_path)
            contract["inputs"]["request"] = "missing/request.json"
            with open(contract_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(contract, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")

            receipt, problems = run_contract(ROOT, contract_path, receipt_path, NOW)
            self.assertEqual(receipt["decision"], "UNAVAILABLE")
            self.assertTrue(problems)
            self.assertTrue(any("missing input" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
