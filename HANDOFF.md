# HANDOFF — HELIX

> 갱신: 2026-07-12
> **현재 상태:** Condense 라인(5 platforms · 56 packs)과 HELIXDirection 라인(Deterministic
> Admission Control Plane) 모두 구축 완료. **613 tests OK**, `helix_validate` PASS.
> **영속화 완료:** HELIXDirection P0~P7이 **main에 merge됨** (PR #12 + line-ending fix PR #13,
> CI green). 그 이후 T1 재도전 조사 산출물(grounding gate 등)은 미commit — 정욱님 결정.
> **T1 재도전 완결:** 4단계 조사로 강등이 **구조적 한계**임을 확정 (재상향 미추진). thesis
> "internal corpus router" 최종화 — 완화 없음.
> **정확한 다음 최우선 작업: 정욱님 방향 결정** — (i) grounding gate 등 유효 산출물 commit,
> (ii) P5_5 외부 pilot 개시, (iii) 페르소나 utility trial. 자율 순수 실무는 종결됨.
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
| **T1** Blind Validity | **FAILED → 강등 (구조적 확정)** | unseen 30: macro-F1 0.450✗. **재도전 4단계 조사**: 독립 view-grounded 재채점 0.20, 9/17 machine이 corpus-specific, 외부 groundable base rate 3.3% → 강등은 구조적 한계, 재상향 미추진. autonomous CONDENSE emit 금지 |
| **T2** Governance Shadow | **PASSED** | 실역사 35 action: disagreement 0%, false-ALLOW 0, replay 35/35 |
| **T3** Closed Actuator | **PASSED** | ungated 0, stop-write 0, bypass 0, replay 100%, 적대 주입 13종 방어 |
| **T4** Utility | **NOT JUDGED** | 내부 pilot 10 decisions(prevented 4, replay 10/10)은 내부 실증; 외부 표본 없음 |
| T5 Federation | 진입 불가 | 조건(T1~T4 통과 + 외부 사용자 2) 미충족 |

## 2. 해야 할 작업 (우선순위 — 내 판단)

### ① commit 영속화 + main merge — 완료 (2026-07-12)

HELIXDirection P0~P7(303 files)을 PR #12로 main에 merge. Windows CRLF가
content-addressed evidence hash를 깨뜨린 결함을 `.gitattributes`로 잡아 PR #13(hotfix)로
merge. **CI green, main 안정.** nested 19 repos·`_workspace`는 격리 유지.

### ①-b T1 재도전 조사 — 완결, 산출물 미commit

T1 강등이 구조적 한계임을 4단계로 확정(`_workspace/helix-direction/T1-retry-verdict.md`).
유효 산출물 **grounding gate**(`core/helix_oracle_grounding.py` + `tests/test_oracle_grounding.py`,
613 tests에 포함)와 pilot kit 이후 산출물은 아직 미commit. **정욱님 결정**: 이 유효
도구들을 새 branch로 commit할지.

### ② P5_5 외부 pilot 개시 — T4 판정으로 직결 (최우선 방향)

wedge(agent handback/approval audit)는 실증 완료 상태이며(내부 pilot 10 decisions, wedge가
수동 검토보다 엄격·false-admit 방향 불일치 0), 연결 킷도 준비됐다:
`helix.py audit-handback` + `docs/WEDGE-RUNBOOK.md` + `examples/wedge/` + sealed metrics.

**자율 준비 완료 (2026-07-12):**
- pilot 운영 프로토콜: `docs/PILOT-PROTOCOL.md` — 목표(주 20 real decisions 또는 검토시간
  50% 절감, false-admit ≤1%, replay 100%, 3곳 중 2곳 retention, 8주), 온보딩(2h), **역할
  분리**(참가자가 packet 작성·판정·false-admit 확인 → 내부 pilot의 "동일 주체" 한계 해소),
  kill/downgrade 조건.
- 집계 도구: `core/helix_wedge_metrics.py:aggregate_pilot` + `scripts/evaluate/pilot_report.py`
  — 다중 참가자 ledger를 sealed T4 리포트로 통합, gate 판정. ledger로 알 수 없는 신호
  (false-admit·retention·review time)는 sidecar 명시 주입, 없으면 `unmeasured` 정직 표기.

**정욱님 승인 필요 (개시):**
- repo/kit 공개 범위, 외부 workflow 3개 모집, 8주 운영 개시. 승인 즉시 시작 가능.

T4 gate 통과 시 "Governed Internal System"에서 **"Admission Plane(제품)"**으로 상향 가능.

### ③ 페르소나 utility trial — 방법론 정합 완료, provenance 입력 대기

방법론 논의(비결정론 페르소나 + 인과적 독립성 + provenance)로 "AI 페르소나를 인간 pilot과
동등한 지위·동등한 독립성 규율 하에 두는 conditional-adoption trial"이 정합해졌다. 실행
전제: **실존 인물의 관점 자료 + 그 인물의 재현 충실도 보증**(정욱님이 대상·자료·보증 방식
지정). 지정되면 자율 구현 가능.

### (종결) T1 재도전 — 재상향 미추진

구조적 한계로 확정(①-b). generator 주장 재상향은 추진하지 않는다. blind trial 방법론은
grounding gate로 강화됨.

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
