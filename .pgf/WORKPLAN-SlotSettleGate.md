# WORKPLAN-SlotSettleGate

## POLICY

- stdlib-only, deterministic verdict path
- tests >= 20, all must pass before close-loop
- no modification to skills/ core/ engines/

## Nodes

| Node | Status | Depends |
|---|---|---|
| ScaffoldPackage | done | — |
| ImplementEngine | done | ScaffoldPackage |
| ImplementCLI | done | ImplementEngine |
| ImplementReport | done | ImplementEngine |
| WriteTests | done | ImplementCLI |
| RunVerification | pending | WriteTests |
| CloseLoop | pending | RunVerification |