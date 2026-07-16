# WORKPLAN-RoutestraContractRelayPackLane

## Plan

1. Read source contract and sample receipts from `ContractRelay`.
2. Implement `Routestra` route pack with manifest and sample.
3. Add candidate schema and registry expectation.
4. Add parity test against live `ContractRelay` receipts.
5. Run Routestra targeted and full tests.
6. Run HELIX gates; update expected probe/router counts caused by one new live pack.
7. Run HELIX validator and full regression.
8. Save verification/report artifacts and set one next task.

## Done criteria

- `contract-relay` appears in Routestra pack registry.
- `RELAYED` receipt is route-eligible.
- `BLOCKED` and `INVALID` receipts are route-ineligible.
- HELIX `machine-probe` and `router` hard gates match live pack inventory.
- `python core/helix_validate.py .` passes.
- `python -m unittest discover -s tests -q` passes.
