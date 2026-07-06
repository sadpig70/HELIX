# DESIGN-SlotSettleGate

> PGF design document for `/pgf full-cycle SlotSettleGate`.

## Gantree

```text
SlotSettleGate // Time-boxed settlement authorization gate (designing)
    Phase1_LoadPacket // JSON packet load and schema validation (designing)
        ValidatePacket // required fields for slot, settlement, veto_escrow (designing)
    Phase2_SlotGate // execution slot and re-authorization checks (designing)
        CheckSlotWindow // execution timestamp within slot bounds (designing)
        CheckReauth // reauth_required vs reauth_granted (designing)
        CheckAuthHash // authorization_hash sha256 format (designing)
    Phase3_SettleMesh // settlement compliance rule checks (designing)
        CheckRulesPassed // rules_passed vs rules_total quorum (designing)
        CheckComplianceScore // compliance_score threshold (designing)
    Phase4_VetoEscrow // high-risk interrupt bounds (designing)
        CheckRiskScore // risk_score vs veto_threshold (designing)
        CheckInterrupt // interrupt_requested flag (designing)
    Phase5_Aggregate // k-way verdict and audit log (designing)
        DetermineVerdict // authorized / review / vetoed (designing)
        AppendAuditLog // SHA-256 hash-chained ledger (designing)
        RenderOutputs // JSON + Markdown dual output (designing)
```

## scope

- `boundary`: Not a live payment processor, slot scheduler, or rule authoring engine. Static packet verification only.
- `stdlib_only`: Python 3.10+, zero external dependencies.
- `cli_triplet`: sample / evaluate / report