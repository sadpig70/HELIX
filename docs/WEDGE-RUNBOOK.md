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

verdict만 편집해 다시 봉인하는 정직한 실수나 우연한 변조는 replay 검증(저장 packet
재hash + AHV 재평가)에서 탐지된다.

> **보안 한계 (정직 표기):** seal은 서명이 아니라 **무결성 체크**(unkeyed SHA-256)다.
> packet과 ledger store에 **write 권한이 있는 적대자**는 packet까지 일관되게 재구축해
> replay와 chain 검증을 **둘 다 통과**시킬 수 있다. 즉 이 도구는 우연 변조·정직한
> 실수를 탐지할 뿐, adversary-facing 위·변조 방지는 아니다. 그 방어에는 keyed 서명과
> 외부 anchoring이 필요하다(backlog). `valid` verdict는 기본적으로 packet의 **구조**가
> 완비되었음을 뜻한다. **evidence-truth 검증(opt-in):** `audit_handback`에
> `evidence_root`(참가자가 제출한 evidence 파일 디렉토리)를 주면 각 predicate의
> `evidence_path` 존재를(그리고 packet에 `evidence_hashes`가 있으면 hash를) 검증한다.
> `evidence_required=True`면 evidence가 `unverified`인 `valid` packet은 **thin으로
> 강등**되어 ADMIT 대신 SANDBOX_ONLY가 된다. evidence_root 미제공 시 wedge는 참가자
> 파일을 볼 수 없으므로 `evidence_check.status = not_provided`로 정직 기록한다.

## 5. Replay 검증 (판정 재현)

모든 decision receipt는 저장된 packet에서 재현 가능하다. CLI가 매 판정 직후 자동으로
replay 검증을 수행하며(`replay check: REPRODUCED`), 출력된 `replay:` 명령을 그대로
실행하면 제3자가 동일 판정을 독립 재현할 수 있다. ledger는 append-only hash chain이라
개별 라인의 삭제·변조는 탐지된다 — 단 전체 chain을 재구축할 write 권한을 가진 적대자는
탐지되지 않는다(위 보안 한계 참조: integrity이지 authenticity 아님). operator.id도
현재 self-asserted이며 인증되지 않는다.

## 6. 이의 제기 (appeal)

판정에 동의하지 않으면 판정은 바꾸지 않고 이의를 기록한다
(`core/helix_contestability.py:file_appeal` — decision의 gate receipt에 chain).
번복은 human의 reasoned override receipt로만 가능하며 원 판정은 불변 보존된다.

## 7. 측정 (North Star)

각 decision receipt에는 `metric.counts_toward = "weekly_real_admission_decisions"`가
내장되어 있어, ledger의 `wedge_decision` entry 수가 곧 실사용 판정 수다.
