# AuthorityArbiter

AuthorityArbiter resolves conflicting delegated policies using deterministic authority rank and policy priority while preserving a reversible custody/route handback trace.

Policies are structured data, not executable expressions. Opposite effects at equal precedence, invalid delegation, custody mismatch or route deviation return `ESCALATE`.

## Usage

```bash
python -m authorityarbiter sample --kind allow
python -m authorityarbiter run examples/allow-request.json \
  --ledger ledger.jsonl --now 2026-07-15T22:00:00+09:00
python -m authorityarbiter report --ledger ledger.jsonl
```

From a source checkout, set `PYTHONPATH=src` or install with `python -m pip install -e .`.

Exit codes: `0` arbitrated/valid report, `3` escalation, `4` invalid ledger.

## Resolution order

1. validate delegation, custody and handback route;
2. match fixed structured conditions against separate facts;
3. sort by authority rank, policy priority and stable policy ID;
4. escalate equal-precedence conflicts; otherwise emit allow or deny.

## HELIX gene provenance

- `policy_data_separation`: `HC-PILOT-EXT-002`.
- `authority_custody_route`: `HC-PILOT-HELIX-001`.
