# WORKPLAN - HELIXInternalControlPlane

```python
POLICY = {
    "max_retry": 3,
    "on_blocked": "halt",
    "design_modify_scope": ["impl", "internal_interface"],
    "completion": "all_done",
    "max_verify_cycles": 2,
    "max_iterations": 40,
}
```

HELIXInternalControlPlane // governed internal control plane (done)
    TrustClosure // fail-closed trust boundary (done)
    TransactionKernel // deterministic state machine (done) @dep:TrustClosure
    TransactionRuntime // atomic runtime and CLI (done) @dep:TransactionKernel
    CondenseAcceptance // deterministic meta-proposal gate (done) @dep:TransactionRuntime
    PlatformComposition // typed five-stage composition (done) @dep:CondenseAcceptance
    InternalMetrics // internal-only metrics (done) @dep:PlatformComposition
    Verification // acceptance, quality, architecture, regression (done) @dep:InternalMetrics

## Evidence Policy

각 노드는 변경 파일과 실행한 테스트를 status JSON outputs에 기록한다. runtime evidence가 이
WORKPLAN보다 우선하며 검증 실패 시 해당 노드와 후속 노드를 완료 처리하지 않는다.
