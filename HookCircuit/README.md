# HookCircuit

HookCircuit is a deterministic, stdlib-only circuit breaker for plugin hook dispatch.

It does not execute hooks. It evaluates explicit dispatch observations against hook contracts and trips only failing hook circuits while preserving clean dispatch evidence.

## Commands

```bash
python -m hookcircuit sample tripped
python -m hookcircuit run examples/tripped-case.json
python -m hookcircuit report ledger.jsonl
```

## Decisions

- `ALLOWED`: all observed hooks remain dispatchable.
- `TRIPPED`: one or more hook circuits are isolated.
- `INVALID`: schema, baseline, hook contract, or observation validation failed.

