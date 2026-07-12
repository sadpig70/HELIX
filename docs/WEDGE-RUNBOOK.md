# HELIX Wedge Runbook — Agent Handback/Approval Audit

> 목표: agent가 위임받은 작업을 마치고 돌려준 **handback packet** 하나를 넣으면,
> 결정론 admission 판정과 재현 가능한 sealed receipt가 나온다. 연결 목표 시간: 2시간.

## 1. 무엇을 판정하는가

agent가 작업을 인계(handback)할 때 갖춰야 할 증거 5종을 검사하고(ActionHandbackVerifier),
그 결과를 admission class로 사상한 뒤, 판정 전 과정을 hash-chain receipt로 남긴다.

```text
handback packet ─→ AHV 5-predicate 검사 ─→ admission class ─→ sealed decision ─→ audit ledger
```

## 2. Packet 형식

JSON 객체, 필수 최상위 필드 (자세한 계약은 `ActionHandbackVerifier/`):

| field | 의미 |
|---|---|
| `handback_id` | 인계 식별자 |
| `handback_time` | 인계 시각 (audit metadata) |
| `delegation` | 누가 무엇을 위임했는가 (authority 증거) |
| `custody` | 산출물 인계·보관 경로 (custody 증거) |
| `route` | 실행 경로/승인 경로 (route 증거) |
| `rollback` | 되돌릴 수 있는가 (rollback 증거) |
| `trace` | 실행 추적 — `trace.digest`는 산출물 hash가 아니라 **packet public surface의 self-binding hash**다 (`ActionHandbackVerifier.verifier.digest_public_surface(packet, omit_trace_digest=True)`). 다른 값이면 breach, 필드 자체가 없으면 thin |

샘플 3종: `examples/wedge/` — `valid-packet.json`(전부 구비),
`thin-packet.json`(trace 없음), `breach-packet.json`(custody 없음).

## 3. 명령

```bash
python helix.py audit-handback --packet <packet.json> [--operator YOUR-ID] [--json]
# 기본 저장 위치: .helix/wedge/ledger.jsonl / .helix/wedge/packets/
# --state-receipt-hash H 를 생략하면 live state receipt를 계산해 anchor로 쓴다.
```

## 4. 판정 해석과 exit code

| verdict | admission | 의미 | exit |
|---|---|---|---:|
| `valid` | **ADMIT** | 증거 완비 — 인계 수용 가능 | 0 |
| `thin` | **SANDBOX_ONLY** | 증거 부족 — 격리 환경에서만 수용 | 3 |
| `breach` | **EXCLUDED** | 인계 경계 위반 — 수용 불가 | 4 |
| packet 없음(registry) | QUARANTINE | 증거 부재 — fail-closed (registry 경로: `registry_admissions`) | — |
| gate 거부 | — | 감사 자체가 거부됨 (사유 출력) | 1 |

판정을 "고쳐서" 받아낼 방법은 없다: verdict를 편집해 다시 봉인해도 replay 검증
(저장 packet 재hash + AHV 재평가)에서 탐지된다.

## 5. Replay 검증 (판정 재현)

모든 decision receipt는 저장된 packet에서 재현 가능하다. CLI가 매 판정 직후 자동으로
replay 검증을 수행하며(`replay check: REPRODUCED`), 출력된 `replay:` 명령을 그대로
실행하면 제3자가 동일 판정을 독립 재현할 수 있다. ledger는 append-only hash chain이라
과거 판정의 삭제·변조도 탐지된다.

## 6. 이의 제기 (appeal)

판정에 동의하지 않으면 판정은 바꾸지 않고 이의를 기록한다
(`core/helix_contestability.py:file_appeal` — decision의 gate receipt에 chain).
번복은 human의 reasoned override receipt로만 가능하며 원 판정은 불변 보존된다.

## 7. 측정 (North Star)

각 decision receipt에는 `metric.counts_toward = "weekly_real_admission_decisions"`가
내장되어 있어, ledger의 `wedge_decision` entry 수가 곧 실사용 판정 수다.
