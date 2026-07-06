ProvenanceStage // Staged AI Model Release Provenance Verifier (done) @v:1.0
    // 재조합: GenCert(증명상속) + ReleaseMesh(단계출시) + ADPR(해시출처로그)
    // 단일 질문: "Has this AI model release passed every provenance and safety stage?"
    CoreEngine // 결정론적 단계 검증 엔진 (done)
        LoadManifest // 모델 출시 매니페스트 로드 (done)
            # input: manifest JSON (model_hash, training_data_hash, eval_results, stages[])
            # process: validate manifest schema → normalize → return parsed manifest
            # output: parsed_manifest dict
            # criteria: schema validation passes, all required fields present
        VerifyIntegrityStage // Stage 1: 무결성 — 모델 해시가 birth certificate와 일치 (done)
            # input: manifest.model_hash, manifest.birth_certificate
            # process: SHA-256(manifest.model_hash) == birth_certificate.expected_hash
            # output: {stage: "integrity", verdict: "passed"|"failed", evidence: {...}}
            # criteria: hash comparison is exact, evidence logged
        VerifySafetyStage // Stage 2: 안전성 — safety eval 결과가 임계치 통과 (done)
            # input: manifest.eval_results[], manifest.safety_thresholds{}
            # process: each eval metric: value vs threshold, direction-aware (lte/gte)
            # output: {stage: "safety", verdict: "passed"|"failed", evidence: {...}}
            # criteria: all threshold checks deterministic, violations logged
        VerifyRolloutStage // Stage 3: 단계적 출시 — 각 rollout phase가 증거 보유 (done)
            # input: manifest.rollout_phases[]
            # process: each phase must have evidence_hash, success_rate >= min_rate
            # output: {stage: "rollout", verdict: "passed"|"failed"|"in_progress", evidence: {...}}
            # criteria: each phase checked, in_progress allowed if current phase not yet finished
        CompileVerdict // 전체 verdict 산출 (done)
            # input: results from all three stages
            # process:
            #   - all passed → "full_release"
            #   - safety+integrity passed, rollout in_progress → "conditional_release"
            #   - any passed → "staged"
            #   - safety failed → "held"
            #   - integrity failed → "revoked"
            # output: {certification: str, stages: [...], audit_hash: str}
            # criteria: verdict deterministic given inputs, all stages included
        AppendAuditLog // 해시 체인 감사 로그 추가 (done)
            # input: verdict dict, previous_log hash
            # process: SHA-256(prev_hash + json(verdict)) → chain appended
            # output: updated audit_log with new entry
            # criteria: hash chain unbroken, entries append-only
    CLI // 명령줄 인터페이스 (done)
        SampleCmd // sample: 샘플 매니페스트 생성 (done)
            # input: --out dir
            # process: write {valid,invalid}_{integrity,safety,rollout,in_progress}_manifest.json
            # output: sample files in output dir
        VerifyCmd // verify: 매니페스트 검증 (done)
            # input: --manifest path, [--audit-log path]
            # process: LoadManifest → VerifyIntegrity → VerifySafety → VerifyRollout → CompileVerdict → AppendAuditLog
            # output: JSON verdict to stdout + audit-log file
        ReportCmd // report: 검증 결과 리포트 (done)
            # input: --input verdict.json, [--out report.md]
            # process: render markdown report from verdict
            # output: markdown report
    PythonAPI // 프로그래밍 인터페이스 (done)
        verify_release(manifest: dict, audit_log: list[dict] | None = None) -> dict
            # process: full pipeline → returns verdict + updated audit_log
        render_report(verdict: dict) -> str
            # process: verdict dict → markdown string
    Tests // 단위 테스트 (done)
        test_verify_integrity // 무결성 단계 테스트
        test_verify_safety // 안전성 단계 테스트
        test_verify_rollout // 출시 단계 테스트
        test_compile_verdict // verdict 산출 테스트
        test_audit_log // 감사 로그 테스트
        test_full_pipeline // 통합 테스트
        test_cli // CLI 테스트
