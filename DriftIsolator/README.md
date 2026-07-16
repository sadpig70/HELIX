# DriftIsolator

DriftIsolator replays a constrained runtime event trace and deterministically shrinks it to a 1-minimal counterexample that still diverges from a hash-bound expected baseline.

Supported event operations are `set`, `increment`, and `append`. No request-supplied code is evaluated.

```bash
python -m driftisolator sample --kind drift
python -m driftisolator run examples/drift-case.json --ledger ledger.jsonl --now 2026-07-15T23:00:00+09:00
python -m driftisolator report --ledger ledger.jsonl
```

Set `PYTHONPATH=src` from a source checkout or install with `python -m pip install -e .`.

HELIX genes: `counterexample_shrinking` from `HC-PILOT-EXT-003` and `baseline_drift` from `HC-PILOT-HELIX-003`.
