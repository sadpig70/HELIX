# PilotProvenanceBoundary Work Plan

## POLICY

```python
POLICY = {
    "max_retry": 3,
    "on_blocked": "stop_and_report",
    "completion": "all_done_or_blocked",
    "compatibility": "legacy receipts replay but are unclassified and metric-ineligible",
}
```

## Execution Tree

```text
PilotProvenanceBoundary // prevent synthetic wedge decisions from entering T4 metrics (done) @v:1.0
    ReceiptContract // seal provenance_class into each wedge decision (done)
    CliContract // expose --provenance-class with unclassified fail-closed default (done) @dep:ReceiptContract
    MetricsBoundary // count only explicit real decisions and participants (done) @dep:ReceiptContract
    ReplayBoundary // verify provenance and metric-marker binding (done) @dep:ReceiptContract
    TestsAndDocs // regression tests and operator documentation (done) @dep:CliContract,MetricsBoundary,ReplayBoundary
    FullVerification // validator and full unittest suite (done) @dep:TestsAndDocs
```
