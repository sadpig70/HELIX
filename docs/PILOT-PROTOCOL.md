# HELIX Wedge Pilot Protocol (T4 external utility)

> 목적: agent handback/approval audit wedge를 **독립 외부 workflow 3곳**에서 8주 운영해
> T4 gate(실제 반복 의사결정의 효익)를 판정한다. 이 문서는 운영 프로토콜이며, wedge
> 사용법 자체는 `docs/WEDGE-RUNBOOK.md`, 판정 기준의 근거는
> `_workspace/HELIXDirection_process_plan.md §P5`에 있다.
>
> **개시 조건: 정욱님 승인** — 외부 참가자 모집, repo/kit 공개 범위, 운영 기간은 사용자
> 결정 사항이다. 이 문서와 킷·집계 도구는 승인 즉시 시작할 수 있도록 준비된 상태다.

## 1. Scope

- 참가자: 서로 독립적인 외부 workflow **3곳 이상**. 각 참가자는 자기 agent가 만든 실제
  handback packet을 wedge로 판정한다 (합성 데이터 금지 — 실제 반복 의사결정이어야 함).
- 기간: **8주**. 중간(4주) 점검, 종료 시 판정.
- 각 참가자는 자기 admission ledger(`*.jsonl`)를 보유하고 주간 스냅샷을 제출한다.

## 2. Onboarding (참가자당 목표 2시간 이내)

1. `docs/WEDGE-RUNBOOK.md`를 읽는다 (packet 형식, 판정 해석, replay, appeal).
2. `examples/wedge/`의 valid/thin/breach 샘플로 3회 판정을 재현한다.
3. 자기 agent handback을 packet으로 변환하는 어댑터를 작성한다 — 참가자 몫이며, packet
   5-predicate(delegation·custody·route·rollback·trace) 계약만 맞추면 된다. `trace.digest`는
   산출물 hash가 아니라 packet public surface self-binding hash임에 주의(내부 pilot의 실제
   함정, RUNBOOK 참조).
4. `python helix.py audit-handback --packet <p> --operator <participant-id>
   --provenance-class real --ledger <participant.jsonl> --packets-dir <dir>`로 판정을 시작한다.
   rehearsal은 반드시 `--provenance-class synthetic`과 별도 ledger를 사용한다.

## 3. 주간 운영

- 참가자는 실제 handback을 발생 즉시 판정한다 (배치 금지 — 실사용 신호가 목적).
- 매주 자기 ledger 스냅샷과 sidecar 신호를 제출한다:
  - **false_admit**: ADMIT됐으나 사후에 무효로 판명된 건수 (참가자가 자기 결과로 확인).
  - **review time**: wedge 도입 전 수동 검토 시간 vs wedge 사용 시간 (선택).
  - **retention**: 계속 사용 의사.
- 운영자(HELIX)는 제출된 ledger를 검증하고 집계한다 (§5).

## 4. Roles / 역할 분리 (내부 pilot 한계의 개선)

- **참가자**가 packet을 만들고 자기 handback을 판정한다.
- wedge(AHV + admission + Constitution)는 **결정론 판정만** 한다.
- **운영자(HELIX)**는 packet을 만들지 않는다 — 판정 로직과 집계만 제공한다.
- 이로써 내부 pilot에서 남았던 "작성·판정 동일 주체" 한계가 해소된다: packet 작성은
  참가자(제3자), 판정은 결정론 wedge, oracle(사후 false-admit 판단)도 참가자.

## 5. 측정 / 집계 (결정론)

```bash
# 참가자별 ledger + sidecar를 하나의 T4 리포트로 봉인
python scripts/evaluate/pilot_report.py --config pilot.json --out pilot-report.json
```

`core/helix_wedge_metrics.py`:
- `wedge_metrics(ledger)` — 참가자별: decisions, admission 분포, prevented_invalid_handbacks,
  **replay rate**(세탁된 판정은 replay율 하락으로 탐지), intervention.
- North Star와 T4 metrics는 receipt가 명시적으로 `provenance_class=real`인 decision만
  집계한다. synthetic·legacy/unclassified decision과 해당 participant는 자동 제외된다.
- `aggregate_pilot(participants, period, sidecar)` — 통합 + T4 gate 판정. 모든 수치는
  sealed ledger에서 재계산되며, ledger로 알 수 없는 것(false_admit, retention, review time)은
  sidecar로 명시 주입되고 없으면 정직하게 `unmeasured`로 남는다.

## 6. T4 Gate (완화 불가)

| 기준 | 목표 | 측정 원천 |
|---|---|---|
| throughput | **주 20 real decisions** 또는 수동 대비 **review time 50% 절감** | ledger + period / sidecar |
| false-admit | **<= 1%** | sidecar (참가자 사후 확인) |
| replay | **100%** | ledger 재계산 (결정론) |
| adoption | **3곳 중 2곳 지속 사용** | sidecar (retention) |

- 판정: 모든 *측정된* 기준이 pass이고 필수 기준에 `unmeasured`가 없어야 `passed`.
  하나라도 실패면 `failed`, 측정 미완이면 `incomplete`.
- **8주 내 gate 미달이면 제품 주장을 철회**하고 내부 R&D harness로 유지한다 (process plan
  §P5). gate를 threshold 완화로 통과시키지 않는다.

## 7. Governance / privacy

- packet과 판정 receipt는 append-only hash-chain ledger에 남으며 replay로 감사 가능하다.
- 참가자 packet은 참가자 소유다. HELIX 운영자는 판정에 필요한 범위만 받는다.
- 판정 이의(appeal)와 번복(override)은 `core/helix_contestability.py` 경로로 기록되며 원
  판정은 불변 보존된다.

## 8. Kill / downgrade

- gate 미달 → "GOVERNED INTERNAL SYSTEM"(현 thesis) 유지, 제품 주장 철회.
- gate 통과 → thesis를 **"Admission Plane(제품)"**으로 상향, T5 federation 진입 검토
  (추가로 외부 사용자 2 + machine claim 조건 필요).
