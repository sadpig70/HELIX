# GraphQuarantine

GraphQuarantine is a deterministic, stdlib-only quarantine engine for evidence graphs.

It receives a directed graph, contamination sources, and a baseline hash. It returns a receipt that quarantines only nodes reachable through blocking evidence paths, separates monitor-only exposure, and leaves clean branches explicit.

## Commands

```bash
python -m graphquarantine sample quarantined
python -m graphquarantine run examples/quarantined-case.json
python -m graphquarantine report ledger.jsonl
```

## Decisions

- `QUARANTINED`: one or more nodes are reachable from contamination sources through `block` paths.
- `CLEAR`: no quarantine path exists.
- `INVALID`: schema, baseline, edge, or source validation failed.

