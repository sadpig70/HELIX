# AuthorityArbiter Design @v:1.0

## Gantree

```text
AuthorityArbiter // delegated policy conflict arbitration (designing) @v:1.0
    Contract // facts, policies and authority remain separate data (designing)
        Canonicalization // stable JSON and SHA-256 (designing)
        FactResolver // safe dotted-path fact access (designing)
        ConditionEvaluator // fixed operators without eval (designing)
    AuthorityBoundary // delegated custody and route contract (designing) @dep:Contract
        DelegationCheck // action and authority chain (designing)
        CustodyCheck // delegated actor returns artifact to authority (designing)
        RouteCheck // planned and actual handback route match (designing)
    ArbitrationEngine // deterministic conflict resolution (designing) @dep:AuthorityBoundary
        PolicyMatch // evaluate data rules against facts (designing)
        RankResolution // authority rank then policy priority (designing)
        TieEscalation // opposite effects at equal rank fail closed (designing)
        ReceiptEmission // allow, deny or escalate with authority trace (designing)
    AuditLedger // append-only arbitration chain (designing) @dep:ArbitrationEngine
        AppendEvent (designing)
        ReplayVerification (designing)
    Interface // package, CLI, examples and docs (designing) @dep:AuditLedger
    Verification // tests, determinism and HELIX handback (designing) @dep:Interface
```

## PPR

```python
def arbitrate(request: ArbitrationRequest) -> ArbitrationReceipt:
    boundary = validate_delegation(request.delegation) → validate_custody → validate_route
    matched = evaluate_policy_data(request.policies, request.facts)
    ranked = stable_sort(matched, by=(-authority_rank, -policy_priority, policy_id))
    if not boundary.valid or not ranked:
        return ESCALATE(boundary.reasons)
    top = equal_precedence_group(ranked)
    if len({rule.effect for rule in top}) > 1:
        return ESCALATE("TIED_CONFLICT")
    return seal(top.effect, authority_trace=ranked)

# acceptance_criteria:
#   - policies and facts are data; no eval/exec or user-provided code
#   - authority rank and policy priority deterministically resolve conflicts
#   - equal-precedence opposite effects always ESCALATE
#   - invalid delegation, custody or route always ESCALATE
#   - receipt and ledger replay deterministically; stdlib only
#   - README, MIT LICENSE, >=3 examples and >=10 tests
```

## Gene provenance

- `policy_data_separation`: `HC-PILOT-EXT-002`
  `455f6abf3395655aa9e2e6d075a0014770b44ba7fddf12f43e974f2a0e7fc3a2`.
- `authority_custody_route`: `HC-PILOT-HELIX-001`
  `b40825717ed8d54a53211177a30efdc6082f1d75de79995ae48022974db2f6c6`.
