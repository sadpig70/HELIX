ArticleGate // EU AI Act Compliance Gate for AI Agent Actions (done) @v:1.0
    // ★ EXPLORE 파이프라인 산출 — SDX→TCX→IDX→CIX→EVX
    // 핵심 인사이트: Regulatory Runtime Gap — 거버넌스 프레임워크는 있지만 런타임 집행은 없다
    // 단일 질문: "Does this AI agent action violate any Article of the EU AI Act?"
    CoreEngine // EU AI Act 5개 조항 결정론적 검증 엔진 (done)
        CheckArticle5 // Prohibited Practices — 금지된 AI 행위 (done)
            # rules: subliminal manipulation, social scoring, real-time biometric
        CheckArticle6 // High-Risk Classification — 고위험 분류 (done)
            # rules: context domain, action type, data category
        CheckArticle13 // Transparency Obligations — 투명성 의무 (done)
            # rules: high-risk + autonomous decisions need transparency
        CheckArticle14 // Human Oversight — 인간 감독 (done)
            # rules: HITL/HOTL/HIC oversight level validation
        CheckArticle50 // GPAI Transparency — 범용 AI 투명성 (done)
            # rules: AI-generated content labeling
        CompileVerdict // 판정 통합: compliant / risk_flagged / prohibited (done)
        AppendAuditLog // 해시 체인 감사 로그 (done)
    CLI // sample / evaluate / report (done)
    PythonAPI // evaluate_action() / render_report() (done)
    Tests // 24 tests passed (done)
