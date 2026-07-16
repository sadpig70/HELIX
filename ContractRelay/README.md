# ContractRelay

ContractRelay is a deterministic, stdlib-only relay gate for federated data contracts.

It validates a payload, contract, and custody handoff before allowing a cross-system relay. Contract mismatch or ambiguous custody returns normalized errors and blocks the relay.

## Commands

```bash
python -m contractrelay sample relayed
python -m contractrelay run examples/relayed-case.json
python -m contractrelay report ledger.jsonl
```

## Decisions

- `RELAYED`: contract and custody are valid.
- `BLOCKED`: contract or custody failed with normalized errors.
- `INVALID`: schema or baseline validation failed.

