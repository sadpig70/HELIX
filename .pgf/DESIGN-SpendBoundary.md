SpendBoundary // AI Agent Context-Boundary Spend Gate (done) @v:1.0
    // 재조합: ContextCreep(컨텍스트경계) + SpendMesh(지출통제) + VetoEscrow(거부권게이트)
    // 단일 질문: "Does this AI agent spend cross a context boundary that requires re-authorization?"
    CoreEngine // 결정론적 경계-지출 게이트 (done)
        ValidateSpend // 지출 요청 스키마 검증 (done)
            # input: {agent_id, amount, currency, recipient, current_context, spend_context, tool_name}
            # criteria: 4-level context 체계 (session/task/tool/external)
        CheckBoundary // 컨텍스트 경계 초과 여부 확인 (done)
            # process: spend_context index < current_context index → boundary crossed
            # output: {boundary_crossed: bool, gap: int}
        ApplyVetoPolicy // VetoEscrow 정책 적용 (done)
            # rules: amount+gap combo, blocked_recipients, restricted_tools
            # output: {verdict: vetoed|boundary_crossed, reasons: []}
        AppendAuditLog // 해시 체인 감사 로그 (done)
    CLI // sample / evaluate / report (done)
    PythonAPI // evaluate_spend() / render_report() (done)
    Tests // 25 tests passed (done)
