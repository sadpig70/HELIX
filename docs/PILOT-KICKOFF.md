# HELIX Wedge — P5_5 External Pilot Kickoff

> **현재 상태(2026-07-13): `PAUSED_BY_USER`.** 외부 모집·8주 운영은 시작하지 않는다.
> 재개 조건과 완료된 준비 범위는 `docs/PILOT-STATUS.md`가 권위다.

> 정욱님이 외부 pilot을 실제로 개시·운영하기 위한 실행 문서. 운영 프로토콜·목표는
> `docs/PILOT-PROTOCOL.md`, 판정 기능은 `docs/WEDGE-RUNBOOK.md`. 이 문서는 **모집 →
> 온보딩 → 8주 운영 → 증거 수집 → T4 판정**의 순서대로 필요한 것을 담는다.
>
> **왜 이 부분은 자율화되지 않는가:** T4 판정의 유효성 자체가 참가자의 *인과적 독립성*에서
> 나온다. 판정 대상(wedge)이 판정 근거(채택·손익)를 스스로 만들면 순환이며,
> `core/helix_t4.py`가 이를 코드로 차단한다. 따라서 실제 독립 외부 당사자를 모집하는
> 행위만이 T4 신호의 전제다. 이 문서의 §1~§3은 순수 실세계 행위다.

## 0. 개시 전 정욱님 결정 1건

- **kit 공개 범위**: HELIX repo를 public으로 둘지, wedge 킷만 별도 배포할지. 참가자에게
  필요한 최소 집합: `helix.py audit-handback` + `docs/WEDGE-RUNBOOK.md` +
  `examples/wedge/` + (검증용) `ActionHandbackVerifier` provisioning(`docs/WEDGE-OPERATIONS.md`).

## 1. 모집 대상 — 독립성 기준 (하드 요건)

`t4_verdict`가 통과시키는 최소 구성:

- **독립 외부 operator ≥ 3곳.** "독립"의 코드-강제 정의:
  - operator id ≠ 정욱님(wedge 저자) — self-dealing 자동 거부.
  - 서로 다른 org — 같은 주체가 여러 참가자로 위장하면 공유 operator로 전부 무효화.
  - 정욱님과 고용·지분 관계가 없는 별개 주체.
- **대상 유형**: AI agent에게 작업을 위임하고 결과를 인계(handback)받는 실제 워크플로를
  가진 팀 — 소규모 개발팀 / 자동화 파이프라인 DevOps / 배포 전 AI 산출 검토 팀. 3곳이
  서로 무관할수록 신호가 강하다.

## 2. 모집 아웃리치 (복붙용 초안)

> **제목:** 당신 팀의 AI agent 인계를 결정론적으로 감사하는 도구 — 8주 파일럿 참가 요청
>
> 안녕하세요. 저희는 AI agent가 위임 작업을 마치고 인계할 때, 그 인계를 **결정론적으로
> 판정**하고 **재현 가능한 증거(sealed receipt)**로 남기는 오픈 도구(HELIX wedge)를
> 만들었습니다. 대시보드가 아니라, 제3자가 동일 판정을 **독립 재현**할 수 있는 감사 도구입니다.
>
> 8주간 귀 팀의 **실제 agent 인계**로 무료로 써 보시고, 실효용(검토 시간 절감·잘못된 인계
> 차단 여부)을 알려주시면 됩니다. 필요한 건 인계 1건당 JSON packet 작성과 명령 한 줄입니다.
> 종료 시 "이 도구가 우리 실제 업무에 이런 결과를 냈다"는 짧은 서면 보증(owned-stakes
> attestation)을 요청드립니다.
>
> 참가에 관심 있으시면 회신 부탁드립니다. — [정욱님 연락처]

**동의 시 확인할 3가지**: (a) 자기 팀 실제 handback으로 운영, (b) 판정·false-admit 확인을
참가자가 직접 수행(역할 분리), (c) 종료 시 owned-stakes 보증 서명.

## 3. 참가자 온보딩 (팀당 ~2h)

전달할 것:

1. 명령:
   ```bash
   python helix.py audit-handback --packet <handback.json> \
     --ledger <team>.jsonl --packets-dir <team>-packets --operator <team-id> \
     --provenance-class real
   ```
2. packet 5-필드 작성법: delegation · custody · route · rollback · trace
   (`docs/WEDGE-RUNBOOK.md` §2, 샘플 `examples/wedge/valid-packet.json`).
3. 판정 해석: ADMIT / SANDBOX_ONLY / EXCLUDED / QUARANTINE (§4) + exit code.
4. **역할 분리 규율**: packet 작성·판정 실행·false-admit 확인을 참가자가 직접 — 내부
   pilot의 "동일 주체" 한계를 여기서 해소한다.

## 4. 8주 운영 — 참가자가 매주 하는 일

자기 실제 agent handback마다:
1. packet 작성 → `audit-handback` 실행 → 판정 + sealed receipt가 자기 ledger에 append.
2. 잘못 ADMIT된 실제 사례가 있으면 기록 → **false-admit** 집계.
3. 매주 real decision 수 누적. replay는 CLI가 매 판정 직후 자동 검증(`REPRODUCED`).

### T4 게이트 목표치 (판정 시 자동 검사)

| 항목 | 통과 기준 | 출처 |
|---|---|---|
| throughput | 합산 주 **≥20 real decisions** 또는 검토시간 **≥50% 절감** | metrics |
| false-admit | **≤1%** | sidecar |
| replay | **100%** | ledger |
| retention | **3곳 중 ≥2곳** 8주 유지 | sidecar |
| 독립 provenance | **≥2곳** 검증된 독립 `real_owned_stakes` | attestation |

## 5. 종료 시 수집할 증거 3종 (참가자별)

### 5.1 sealed ledger
`<team>.jsonl` — 그 팀의 모든 실 판정(append-only hash-chain). 그대로 수집.

### 5.2 owned-stakes attestation (operator가 서명)

각 operator가 아래 필드를 채워 서명한다. `core/helix_owned_stakes.py:attest_owned_stakes`가
받는 형태이며, **operator ≠ 정욱님**·**ledger_head가 그 팀 실 ledger의 head**여야 통과한다.

```json
{
  "operator":        {"id": "<그 팀 식별자>", "org": "<그 팀 조직명>"},
  "wedge_author_id": "<정욱님 식별자>",
  "real_work": {
    "ledger_ref":         "<team>/prod-handbacks",
    "ledger_head_sha256": "<그 팀 ledger 마지막 entry_sha256>",
    "decision_count":     0,
    "simulated":          false
  },
  "outcomes": {
    "prevented_invalid": 0,
    "admitted":          0,
    "replay_verified":   true
  },
  "stakes_owned": "<우리가 실제로 감수한 결과 — 예: 잘못된 배포 인계를 프로덕션 전에 막았다>"
}
```

> `ledger_head_sha256`는 그 팀 ledger의 마지막 `entry_sha256`. 계산: ledger 마지막 JSON
> 라인의 `entry_sha256` 값. outcomes는 **객관 측정치**(정수)여야 하며, 감정 서술만 있으면
> 거부된다.

### 5.3 sidecar (ledger로 알 수 없는 신호)

```json
{
  "false_admits":                 {"team-a": 0, "team-b": 0, "team-c": 0},
  "retained":                     ["team-a", "team-b"],
  "manual_review_baseline_minutes": {"team-a": 600},
  "wedge_review_minutes":           {"team-a": 120}
}
```

## 6. 종료 시 T4 판정 (자동화 — 정욱님이 증거만 전달)

```python
from core.helix_t4 import t4_verdict
verdict = t4_verdict(
    root, participant_ledgers,          # {team: ledger_rel}
    owned_stakes_attestations,          # {team: attestation}
    wedge_author_id="<정욱님 식별자>",
    period={"weeks": 8}, sidecar=sidecar)
# verdict["verdict"] == "passed"  ->  metrics ∧ 독립-provenance 모두 통과
```

`passed`는 metrics 게이트와 독립-provenance 게이트를 **모두** 통과할 때만 나온다
(self-dealing·단일·미검증 경로 불가). 통과 시 **"Governed Internal System" →
"Admission Plane(제품)"** 상향 근거가 된다.

## 7. Kill / Downgrade & 정직 규율

- 어느 게이트든 미충족 → `not_passed` + 구체 gap 기록. **임계값 완화·문서 은폐 금지.**
- 참가자 self-dealing / 데이터 위조 판명 → 그 참가자 무효, 재판정.
- ≥2 독립 검증 미달 → **T4는 미판정으로 정직 보류.** 제품 주장 금지.

## 8. 정욱님 실행 체크리스트

- [ ] §0 kit 공개 범위 결정
- [ ] §1~§2 서로 무관한 외부 팀 **3곳 이상** 모집·동의
- [ ] §3 각 팀 온보딩(2h)
- [ ] §4 8주 운영(각 팀 실 handback)
- [ ] §5 팀별 sealed ledger + owned-stakes 보증 + sidecar 수집
- [ ] §6 증거 전달 → `t4_verdict` 판정 (자동화)

§1~§5가 순수 실세계 행위, §6은 자동화됨.
