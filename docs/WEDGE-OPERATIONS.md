# HELIX Wedge — Operations Notes

> 페르소나 conditional-adoption trial이 지목한 운영상 backlog 3건을 정직하게 다룬다.
> 이들은 코드 버그가 아니라 **운영 계약**이므로, 여기서 계약을 명시한다. 판정 기능·
> 사용법은 `docs/WEDGE-RUNBOOK.md`, pilot 운영은 `docs/PILOT-PROTOCOL.md`.

## 1. ActionHandbackVerifier(AHV) provisioning

wedge의 5-predicate 검사는 **vendored nested repo** `ActionHandbackVerifier`에 의존한다
(`core/helix_wedge.py:_ahv_verdict`). 없으면 감사가 `ValueError("ActionHandbackVerifier
is required for handback audits and is not available")`로 **명확히 실패**한다 — silent
degradation은 없다.

**요구사항 (운영):**
- `ActionHandbackVerifier/src/ActionHandbackVerifier/`가 존재해야 한다 (CI는 이를 checkout).
  이 디렉토리는 HELIX가 vendoring하지 않는 독립 nested repo이므로(`git add -A` 금지 대상),
  clone 후 별도 provisioning이 필요할 수 있다.
- `tests/_path.py`가 그 `src`를 `sys.path`에 넣는다. 감사 실행 전 이 경로 존재를 확인하라.
- 부재 시 대응: 감사를 실행하지 말고 provisioning을 먼저 하라. wedge는 AHV 로직을
  중복 구현하지 않는다 (단일 출처 유지).

## 2. 동시성 — local exclusive lock

actuation ledger는 로컬 append-only JSONL이며 `append_actuation_ledger`가 ledger별
exclusive lock을 획득한 뒤 read→append→flush/fsync한다. lock 충돌은 대기·우회하지 않고
명시적으로 fail-closed한다.

- 참가자·operator별 별도 ledger 원칙은 유지한다. 같은 filesystem에서 동시 append는 lock으로
  직렬화된다.
- **동시 위반은 silent하지 않다:** 두 writer가 같은 seq로 append하면
  `verify_actuation_ledger`가 `seq broken` + `parent chain broken`으로 **탐지**한다
  (실증됨). keyed signing/external anchor 검증도 그 위에서 작동한다. 즉 최악의 경우
  손상이 조용히 통과하는 것이 아니라 검증에서 드러난다.
- distributed filesystem이나 다중 host writer에는 lock-file 원자성이 보장되지 않을 수 있다.
  이 경우 외부 queue/DB writer로 직렬화해야 하며 HELIX는 이를 지원한다고 주장하지 않는다.

## 3. 컴플라이언스 프레임워크 매핑 — 가이드 (인증 주장 아님)

wedge는 **replayable·keyed-signed·externally-anchored admission evidence**를 생산한다.
이것을 SOC2·PCI-DSS 등 특정 프레임워크의 통제에 매핑하는 것은 **각 조직의 규제 책임**이며,
HELIX는 어떤 인증도 주장하지 않는다. 아래는 통제 *개념*과의 대응 관점일 뿐, 인증 매핑이
아니다:

| wedge 산출 | 일반 통제 개념 (프레임워크 인증 아님) |
|---|---|
| EXCLUDED / QUARANTINE 판정 | 무효 인계 차단 = access/change control의 예방 통제 evidence |
| sealed decision receipt | 감사 추적(audit trail) — 누가·무엇을·왜 판정했는가 |
| replay 재현 | 통제 작동의 재현 가능 증거 |
| keyed HMAC + external anchor | 추적의 무결성·진본성 (내부자 재작성 탐지) |
| `evidence_check` (opt-in) | evidence 존재 검증; 단 evidence 진위 판단은 조직 몫 |

**정직한 한계:** wedge는 통제가 *존재하고 재현 가능함*을 뒷받침할 뿐, 그 통제가 특정
프레임워크의 인증 요건을 *충족함*을 주장하지 않는다. 프레임워크 매핑·인증은 조직의
규제 전문가 검토를 거쳐야 한다. HELIX가 임의로 "이것은 SOC2 CC6.1"이라 라벨하는 것은
과대주장이며 하지 않는다.

## 요약

세 항목 모두 운영 계약이다: AHV는 명확 실패로 fail-closed, 로컬 동시성은 exclusive lock +
chain verify, 분산 writer는 외부 직렬화, 컴플라이언스는 evidence 제공(인증 주장 없음)이다.
