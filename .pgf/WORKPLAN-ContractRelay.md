# WORKPLAN-ContractRelay

POLICY:
  max_verify_cycles: 2
  deterministic_boundary: stdlib_only
  handback_required: true
  close_loop_required: true

ContractRelay // fail-closed federated contract relay (done)
    DesignContract // write PGF design/review/workplan/status (done)
    ImplementCore // implement deterministic relay engine (done)
    ImplementCliLedger // implement CLI and append-only ledger (done)
    TestExamples // add examples and unittest coverage (done)
    VerifyHelixClosure // handback, close-loop, feedback, root regression (done)

