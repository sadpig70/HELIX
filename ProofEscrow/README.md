# ProofEscrow

ProofEscrow releases an artifact only when two independent claims are bound into one deterministic receipt:

1. every artifact step carries valid HMAC-SHA256 metadata from a trusted signer;
2. observed behavior matches an approved, tested and deterministic baseline.

Any missing or conflicting evidence produces `HELD`. The trust store is supplied separately and is never copied into the request, receipt or ledger.

## Usage

```bash
python -m proofescrow sample --kind released
python -m proofescrow run examples/released-request.json \
  --trust-store examples/trust-store.json \
  --ledger ledger.jsonl --now 2026-07-15T22:00:00+09:00
python -m proofescrow report --ledger ledger.jsonl
```

From a source checkout, set `PYTHONPATH=src` or install with `python -m pip install -e .`.

Exit codes: `0` released/valid report, `2` held, `4` invalid ledger.

## Security boundary

- HMAC authenticates step metadata against the caller-provided trust store; it is not a public-key signature system.
- Artifact bytes and test execution remain upstream responsibilities. ProofEscrow binds their SHA-256 evidence and decision state.
- Verdict logic uses only Python stdlib and has no network, clock or randomness. Ledger time is explicitly injected.

## HELIX gene provenance

- `signed_step_metadata`: `HC-PILOT-EXT-001` (`in-toto` evidence baseline).
- `behavior_baseline_binding`: `HC-PILOT-HELIX-002` (`MethodBond` evidence baseline).
