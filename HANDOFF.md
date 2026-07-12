# HANDOFF — HELIX

> 갱신: 2026-07-12
> **현재 상태:** Condense 라인(5 platforms · 56 packs)과 HELIXDirection 라인(Deterministic
> Admission Control Plane) 모두 구축 완료. 595 tests OK, `helix_validate` PASS.
> **영속화 완료(2026-07-12):** HELIXDirection 작업 전체를 branch
> `helixdirection-admission-plane`에 commit+push, **CI green** (commit `5f0f91d` +
> CI fix `dcd475f`). PR/merge는 아직 미실행 — 정욱님 결정.
> **정확한 다음 최우선 작업: `P5_5_ExternalPilots` 개시** — 준비(온보딩/프로토콜 문서)는
> 자율 진행 가능, **공개·모집·운영 개시는 정욱님 승인 필요**.
> 이전 완료 계보: [`_legacy/`](_legacy/) (Condense v0.6 · HELIXDirection 종결본/상세본)

---

## 1. 프로젝트 현황

### Condense 라인 (기존 완료, 유지)

explore⊕exploit⊕condense 삼중나선. corpus 클러스터를 kernel+plugin 플랫폼으로 수렴 —
실증된 5 플랫폼 전부 독립 저장소·public·CI green:
Attestra(23) · Clearstra(12) · Routestra(11) · Certstra(5) · Scorestra(5) = **56 packs**.
corpus 완전 라우팅(흡수 20 · defer 2 · design-only 8). 상세: `docs/CONDENSE.md`,
계보 백업 `_legacy/HANDOFF-CONDENSE-v0.6-COMPLETE.md`.

### HELIXDirection 라인 (이번 방향, 완료)

HELIX를 `advisor + human actuator`에서 **Deterministic Admission Control Plane**으로 전환.
폐루프 `proposal → blind verification → constitutional authorization → bounded actuation
→ impact handback → replayable ledger`를 결정론으로 구현·검증했다.

**최종 thesis: GOVERNED INTERNAL SYSTEM** (완료 정의 경로 2) — 검증된 admission control
plane을 내부 runtime으로 보유. generator 주장은 internal corpus router로 강등 유지,
제품 주장은 보류.

| Gate | Verdict | 핵심 사실 |
|---|---|---|
| **T0** State Authority | **PASSED** | canonical receipt `8ea2534ef8904ac7…`, 전 구간 무결 |
| **T1** Blind Validity | **FAILED → 강등** | 실제 unseen 30: coverage 0.900✓, macro-F1 0.450✗ (M10/M15 전멸). autonomous CONDENSE emit 금지 |
| **T2** Governance Shadow | **PASSED** | 실역사 35 action: disagreement 0%, false-ALLOW 0, replay 35/35 |
| **T3** Closed Actuator | **PASSED** | ungated 0, stop-write 0, bypass 0, replay 100%, 적대 주입 13종 방어 |
| **T4** Utility | **NOT JUDGED** | 내부 pilot 10 decisions(prevented 4, replay 10/10)은 내부 실증; 외부 표본 없음 |
| T5 Federation | 진입 불가 | 조건(T1~T4 통과 + 외부 사용자 2) 미충족 |

## 2. 해야 할 작업 (우선순위 — 내 판단)

### ① commit 영속화 — 완료 (2026-07-12)

HELIXDirection 방향 작업(303 files, 30310 insertions)을 branch
`helixdirection-admission-plane`에 commit(`5f0f91d`)+push했고 CI green.
CI에서 환경 의존 테스트 1건(`test_state_receipt_cli`, _workspace report 부재 시
missing vs unverifiable)이 드러나 fix commit(`dcd475f`)으로 해결. nested 19 repos·
`_workspace`는 격리 유지. **남은 것은 정욱님 결정**: PR 생성 및 main merge 여부.

### ② P5_5 외부 pilot 개시 — T4 판정으로 직결 (최우선 방향)

wedge(agent handback/approval audit)는 실증 완료 상태이며(내부 pilot 10 decisions, wedge가
수동 검토보다 엄격·false-admit 방향 불일치 0), 연결 킷도 준비됐다:
`helix.py audit-handback` + `docs/WEDGE-RUNBOOK.md` + `examples/wedge/` + sealed metrics.

**자율 진행 가능(공개 전에도):**
- pilot 운영 프로토콜 문서 — 목표(주 20 real decisions 또는 검토시간 50% 절감,
  false-admit ≤1%, 8주 판정), 참가 절차, 측정·집계 방법.
- 외부 참가자 온보딩 가이드 — packet 작성부터 판정·replay·appeal까지.
- pilot 결과 집계 자동화(여러 참가자 ledger → `wedge_metrics` 통합 리포트).

**정욱님 승인 필요:**
- repo/kit 공개 범위(commit/push — ①과 연결), 외부 workflow 3개 모집, 8주 운영 개시.

T4 gate 통과 시 "Governed Internal System"에서 **"Admission Plane(제품)"**으로 상향 가능.

### ③ [선택] T1 재도전 — generator 주장 재상향

T1 강등을 되돌리려면(완화 불가 4요건): 새 cohort + **독립 oracle author** + M10/M15 계열
검출 보강 + novelty 구현·환원 실측 ≥3건. 통과 전 autonomous CONDENSE emit 금지 유지.
큰 작업이며 ②와 독립적이다.

## 3. 산출 인벤토리 (HELIXDirection, 전부 미commit)

- **core 신규 15종**: helix_{state_receipt, holdout, prediction, novelty, constitution,
  evidence, risk_policy, authorization, stop_token, contestability, execution_plan,
  admission, side_effect_guard, actuator, impact_handback, wedge, wedge_metrics}
- **schemas 8종**, **tests 17파일**(329→595), **CLI**: `state-receipt`, `audit-handback`
- **wedge 킷**: `docs/WEDGE-RUNBOOK.md`, `examples/wedge/`; **policy**: `docs/HOLDOUT-POLICY.md`
- **seed**: `seed/evaluation/` (synthetic + T1-LIVE-001 실 cohort — 30 unseen, pinned SHA)
- **scripts**: `scripts/evaluate/` (synthetic builder · T1 collector · blind trial ·
  shadow replay); `engines/exploit/adapter.py`에 `registry_admissions` 추가

## 4. Evidence 색인 (`_workspace/helix-direction/`, gitignored durable)

- T0 `T0-verification.*` · T1 `T1-validity-report.md`+`T1/`+`trials/T1/`
- T2 `T2-verification.*`+`T2/` · T3 `T3-verification.*`+`T3/`
- T4 `T4-verification.md`+`T4/`(internal pilot report · sealed metrics · ledger)
- P7 `P7-regression.json` · `P7-architecture-review.md` · `P7-thesis-verdict.md`
- PGF 상태: `.pgf/status-HELIXDirection.json` (41 done / 2 blocked / 43 nodes)

## 5. Blocked 노드 재개 조건

| 노드 | 사유 | 재개 조건 |
|---|---|---|
| `P5_5_ExternalPilots` | 외부 모집·공개는 명시 승인 필요 | 정욱님이 공개 범위·대상·개시 승인 — 킷 준비 완료 |
| `P6_FederationPlane` | 진입 조건 미충족 | T1 재도전 통과 + T4 판정 통과 + 외부 사용자 2 |

## 6. 알려진 한계 / 이탈 (은폐 없음)

1. NoveltyTrial 실측(구현·환원 ≥3건) 미수행 — T1 재도전 조건.
2. stop token은 암호 서명이 아닌 canonical seal + ledger 정합 (서명 도입은 향후 과제).
3. 기존 exploit ledger의 fail-open 소비 경로가 migration flag 유예 하 잔존.
4. wedge latency/cost는 sidecar 설계만 (결정론 경계 준수의 의도적 선택).
5. FederationPlane 미구현 — DESIGN의 조건부 gate가 의도한 blocked.
6. (방법론) T1 oracle·T2 brief를 단일 운영자 작성; 격리는 predictor/classifier subagent
   컨텍스트로만 확보. 제3자 역할 분리는 외부 pilot의 몫.

## 7. Rollback 상태

이 방향 작업은 branch `helixdirection-admission-plane`에 committed (main 미merge).
되돌리려면 해당 branch를 삭제/미merge로 두면 main은 무영향. nested 19 repos는
무변경(clean). `_workspace/`는 gitignored durable evidence — 삭제 금지.

## 8. 운영 규율 (유지)

- 정욱님 호칭, 한국어 보고, code/command/identifier English.
- 한 번에 하나의 gated step, 다음 최우선 작업 하나만 보고.
- PowerShell 5.1 금지(Git Bash 또는 지정 PS7), PATH의 `python`만 사용.
- `git add -A` 금지(nested repos), commit/push/merge/공개는 명시 승인 시에만.
- hard gate 실패를 threshold 완화나 문서 표현으로 숨기지 않는다.
- runtime evidence가 문서보다 우선하며 즉시 동기화한다.

## 9. 한 줄 인수인계

> **HELIXDirection이 GOVERNED INTERNAL SYSTEM으로 종결됐고(595 tests·sealed evidence),
> Condense 5 플랫폼 라인도 유지된다. 다음 최우선은 `P5_5 외부 pilot 개시`로 T4를 판정하는
> 것 — 준비 문서는 지금 자율로 시작할 수 있고, 공개·모집·운영과 그 선행인 commit 영속화는
> 정욱님 승인이 필요하다.**
