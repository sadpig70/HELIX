# DESIGN-RoutestraContractRelayPackLane

## Gantree

```text
RoutestraContractRelayPackLane
├─ intent: absorb ContractRelay into existing Routestra pack plane
├─ source machine: ContractRelay receipt relay(case)
│  ├─ RELAYED: valid baseline + contract + custody + normalized errors empty
│  ├─ BLOCKED: contract/custody defects, fail_closed true
│  └─ INVALID: baseline/schema defects, fail_closed true
├─ target platform: Routestra
│  └─ stage: route
├─ invariant
│  ├─ no new platform kernel
│  ├─ no synthetic evidence promoted as external evidence
│  └─ live source parity must anchor eligibility
└─ output
   ├─ routestra_packs/contract_relay.py
   ├─ schemas/candidate-contractrelay.schema.json
   ├─ tests/test_contract_relay_parity.py
   └─ HELIX gate snapshot update
```

## PPR

```text
def RoutestraContractRelayPackLane:
  AI_Inspect(ContractRelay.core.relay, ContractRelay.samples)
  → AI_ClassifyMachine(receipt_decision as route_eligibility)
  → AI_ImplementPack(stage="route", no_kernel_change=True)
  → AI_VerifyParity(relayed=True, blocked=False, invalid=False)
  → AI_UpdateHELIXGates(total_platform_packs += 1, probe_cases += 1)
  → AI_Report(next_task="execute Phase4 closeout report")
```

## Machine decision

`ContractRelay` is not a policy predicate pack. Its runtime emits deterministic handoff receipts and a fail-closed decision. The useful platform primitive is route selection: a candidate route is eligible only when receipt decision is `RELAYED`, `fail_closed == false`, normalized `errors/reasons` are empty, relay token is present, and demanded source/target/contract constraints match.
