# DESIGN-ThermalCascadeBound

> PGF 설계 문서. `/pgf full-cycle ThermalCascadeBound` 의 대상.

## Gantree

```text
ThermalCascadeBound // Co-located Green Datacenter Clearing & Thermal Plume Stage (designing)
    Phase1_Telemetry // 입력 데이터 수집 및 검증 (designing)
        LoadTelemetry // JSON 입력 로드 및 파싱 (designing)
            # criteria: telemetry JSON 형식 및 필드 존재 유무 검증
        ValidateBounds // telemetry 한계 범주 및 단위 검증 (designing)
            # criteria: 수치 범위 및 유효성 확인
    Phase2_Clearing // 전력 분배 및 IT 스케줄링 (designing)
        CalculateCoexistence // DAC 부하 vs AI 연산 가용 전력 산출 (designing)
            # criteria: 총 가용 전력 내에서 DAC 및 Compute 전력 합계 계산
        ApplyThrottling // 필요한 경우 compute throttling ratio 결정 (designing)
            # criteria: 전력 부족 시 compute 부하 제한 비율 계산
    Phase3_PlumeStage // 온배수 생태계 확산 검증 (designing)
        CalculatePlumeDeltaT // 온배수 방출 유량 및 온도 기반 delta T 추정 (designing)
            # criteria: 물리적 수식을 사용한 가상의 온도차(delta T) 시뮬레이션
        VerifyPlumeLimits // delta T 가 환경 임계값(1.5°C, 3.0°C)을 초과하는지 검증 (designing)
            # criteria: 규제 임계값과 비교
    Phase4_AggregateVerdict // 최종 판정 및 로깅 (designing)
        DetermineVerdict // compliant, restricted, violation 판정 (designing)
            # criteria: 전력 및 열 분배 검증 결과에 따라 k-way verdict 확정
        AppendAuditLog // SHA-256 감사 로그 체인 추가 (designing)
            # criteria: 이전 해시 및 현재 판정을 결합하여 SHA-256 해시 생성 및 파일 기록
        RenderOutputs // 기계용 JSON 및 사람용 Markdown 리포트 출력 (designing)
            # criteria: dual_output 규격 충족
```

## PPR

```python
def AI_design_verdicts(telemetry):
    # 전력 및 온배수 상태에 따른 compliant / restricted / violation 판정 논리
    pass
```

## scope
- `boundary`: 이것은 실시간 CFD 시뮬레이션이나 실제 그리드 하드웨어 제어기가 아니며, static telemetry 파일을 검증하는 stdlib-only CLI 도구이다.
