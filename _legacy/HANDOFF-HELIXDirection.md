# HANDOFF — HELIXDirection 종결

> 갱신: 2026-07-12
> **최종 thesis: GOVERNED INTERNAL SYSTEM** — 검증된 Deterministic Admission Control
> Plane을 내부 runtime으로 보유. generator 주장은 internal corpus router로 강등 유지,
> 제품 주장은 보류.
> **정확한 다음 작업: 정욱님 결정 — (a) 미commit 작업의 commit 승인 여부,
> (b) P5_5 외부 pilot 진행 여부. 자율 진행 가능한 노드는 남아 있지 않다.**
> 상세 완료 계보: [`HANDOFF-HELIXDIRECTION-COMPLETE.md`](HANDOFF-HELIXDIRECTION-COMPLETE.md)
> (이전 Condense 계보: [`HANDOFF-CONDENSE-v0.6-COMPLETE.md`](HANDOFF-CONDENSE-v0.6-COMPLETE.md))

---

## 1. 최종 상태 (2026-07-12)

### Phase gate 계보 (전부 sealed evidence)

| Gate | Verdict | 핵심 사실 |
|---|---|---|
| **T0** State Authority | **PASSED** | canonical receipt `8ea2534ef8904ac7…` — P0부터 종결까지 전 구간 무결 |
| **T1** Blind Validity | **FAILED → 강등** | 실제 GitHub unseen 30: coverage 0.900✓, macro-F1 0.450✗ (M1/M3 정확, M10/M15 전멸). **autonomous CONDENSE emit 금지** |
| **T2** Governance Shadow | **PASSED** | 실역사 35 action, 독립 oracle: disagreement 0%, false-ALLOW 0, replay 35/35 |
| **T3** Closed Actuator | **PASSED** | ungated 0, stop-write 0, bypass 0, replay 100%, 적대 주입 13종 방어 |
| **T4** Utility | **NOT JUDGED** | 내부 pilot 10 decisions(prevented 4, replay 10/10)은 내부 실증; 외부 표본 없음 — 제품 주장 보류 |
| T5 Federation | 진입 불가 | 조건(T1~T4 통과 + 외부 사용자 2) 원천 미충족 |

### 최종 검증 (P7_1 sealed)

```text
python -m unittest discover -s tests -q   -> Ran 595 tests, OK   (세션 시작 329)
python core/helix_validate.py .           -> PASS
python helix.py state-receipt             -> hash == T0 canonical
git diff --check                          -> clean
nested repos (19)                         -> all clean (일절 미수정)
live blockers                             -> diversity_repair_required, unverifiable_report
                                             (완화 없이 유지, actuator_ready=false)
```

## 2. 산출 인벤토리 (전부 미commit — 승인 대기)

- **core 신규 15종**: helix_{state_receipt, holdout, prediction, novelty, constitution,
  evidence, risk_policy, authorization, stop_token, contestability, execution_plan,
  admission, side_effect_guard, actuator, impact_handback, wedge, wedge_metrics}
- **schemas 8종**: state-receipt, holdout-registry, trial-receipt, reduction-receipt,
  action-intent, evidence-manifest, gate-result, impact-handback
- **tests 17파일** (+266 tests), **CLI**: `helix.py state-receipt`, `helix.py audit-handback`
- **wedge 운영 킷**: `docs/WEDGE-RUNBOOK.md`, `examples/wedge/` (+ `docs/HOLDOUT-POLICY.md`,
  `examples/{holdout,constitution,state-receipt}/`)
- **seed**: `seed/evaluation/` — synthetic cohort + T1-LIVE-001 실 cohort (30 unseen,
  pinned SHA + license evidence)
- **scripts**: `scripts/evaluate/` (synthetic builder, T1 collector, blind trial,
  shadow replay), engines/exploit/adapter.py에 `registry_admissions` 추가
- 미commit 합계: modified 6 · untracked 60 (`_workspace/helix-direction/
  P7-regression.json`에 전체 목록 봉인)

## 3. Evidence 색인 (`_workspace/helix-direction/`)

- T0: `T0-verification.{json,md}` · T1: `T1-validity-report.md` + `T1/` + `trials/T1/`
- T2: `T2-verification.{json,md}` + `T2/` · T3: `T3-verification.{json,md}` + `T3/`
- T4: `T4-verification.md` + `T4/` (internal pilot report, sealed metrics, ledger)
- P7: `P7-regression.json` · `P7-architecture-review.md` · `P7-thesis-verdict.md`
- PGF 상태: `.pgf/status-HELIXDirection.json` (41 done / 2 blocked / 43 nodes)

## 4. Blocked 노드와 재개 조건

| 노드 | 사유 | 재개 조건 |
|---|---|---|
| `P5_5_ExternalPilots` | 외부 모집·공개는 명시 승인 필요 | 정욱님이 진행/공개 범위/대상 승인 — 킷·측정 체계 준비 완료, 즉시 시작 가능 |
| `P6_FederationPlane` | 진입 조건 원천 미충족 | T1 재도전 통과 + T4 판정 통과 + 외부 사용자 2 |

**T1 재도전 4요건** (완화 불가): 새 cohort + 독립 oracle author + M10/M15 계열 검출
보강 + novelty 구현·환원 실측 ≥3건.

## 5. 알려진 한계 / 이탈 (P7_2, 은폐 없음)

1. NoveltyTrial 실측(구현·환원 ≥3건) 미수행 — T1 재도전 조건.
2. stop token은 암호 서명이 아닌 canonical seal + ledger 정합 (서명 도입은 향후 과제).
3. 기존 exploit ledger의 fail-open 소비 경로가 migration flag 유예 하 잔존.
4. wedge latency/cost는 sidecar 설계만 (결정론 경계 준수의 의도적 선택).
5. FederationPlane 미구현 — DESIGN의 조건부 gate가 의도한 blocked.
6. (방법론) T1 oracle·T2 brief를 단일 운영자가 작성 — 격리는 predictor/classifier
   subagent 컨텍스트로만 확보. 제3자 역할 분리는 외부 pilot의 몫.

## 6. Rollback 상태

- 이 방향 작업 전체가 **미commit** — 승인 전 영속화 없음. 되돌리려면 untracked 산출물
  제거 + modified 6파일 revert로 충분하다 (P7-regression.json에 목록).
- nested 19 repos는 무변경(clean)이라 rollback 대상 자체가 없다.
- `_workspace/`는 gitignored durable evidence — 삭제 금지.

## 7. 운영 규율 (유지)

- 정욱님 호칭, 한국어 보고, code/command/identifier English.
- 한 번에 하나의 gated step, 다음 최우선 작업 하나만 보고.
- PowerShell 5.1 금지(Git Bash 또는 지정 PS7), PATH의 `python`만 사용.
- `git add -A` 금지 (nested repos), commit/push/merge/공개는 명시 승인 시에만.
- hard gate 실패를 threshold 완화나 문서 표현으로 숨기지 않는다.
- runtime evidence가 문서보다 우선하며 즉시 동기화한다.

## 8. 한 줄 인수인계

> **HELIXDirection이 종결됐다: GOVERNED INTERNAL SYSTEM — admission 폐루프
> (proposal→verification→authorization→actuation→handback→ledger)가 595 tests와
> sealed evidence로 고정된 내부 runtime이 됐고, 못한 것(T1 강등·T4 미판정·이탈 6건)은
> 전부 재상향 조건과 함께 봉인됐다. 다음 한 수는 정욱님의 것이다: 미commit 작업의
> 영속화(commit) 승인, 그리고/또는 P5_5 외부 pilot 개시.**
