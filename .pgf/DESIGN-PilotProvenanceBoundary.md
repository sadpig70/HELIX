# PilotProvenanceBoundary Design @v:1.0

## Gantree

```text
PilotProvenanceBoundary // prevent synthetic wedge decisions from entering T4 metrics (in-progress) @v:1.0
    ReceiptContract // seal provenance_class into each wedge decision (in-progress)
    CliContract // expose --provenance-class with unclassified fail-closed default (designing) @dep:ReceiptContract
    MetricsBoundary // count only explicit real decisions and participants (designing) @dep:ReceiptContract
    ReplayBoundary // verify provenance and metric-marker binding (designing) @dep:ReceiptContract
    TestsAndDocs // regression tests and operator documentation (designing) @dep:CliContract,MetricsBoundary,ReplayBoundary
    FullVerification // validator and full unittest suite (designing) @dep:TestsAndDocs
```

## PPR

```python
def normalize_provenance(value: Optional[str]) -> Literal["real", "synthetic", "unclassified"]:
    """Fail closed when provenance is missing; reject unknown asserted values."""
    if value is None:
        return "unclassified"
    if value not in {"real", "synthetic"}:
        raise ValueError("provenance_class must be real or synthetic")
    return value

def metric_marker(provenance_class: str) -> dict:
    if provenance_class == "real":
        return {"counts_toward": "weekly_real_admission_decisions"}
    return {"counts_toward": None, "excluded_reason": f"provenance:{provenance_class}"}

def aggregate_real_metrics(decisions: list[Decision]) -> Metrics:
    all_decisions = verify_replay(decisions)
    eligible = [d for d in all_decisions if d.provenance_class == "real"]
    # acceptance_criteria:
    #   - synthetic and legacy/unclassified decisions never affect T4 throughput
    #   - only ledgers with real decisions count as real participants
    #   - all decisions remain visible and replay-verified
    return derive_metrics(all_decisions, eligible)
```
