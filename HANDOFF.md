# HANDOFF — HELIX

> 갱신: 2026-07-13
> **현재 상태:** Condense(5 platforms·56 packs) + HELIXDirection(Deterministic Admission
> Control Plane) + persona-trial 파생 security 강화 + **provenance 사다리 3층 + T4 verdict
> 판정 기계 + pilot provenance fail-closed 경계**. **695 tests OK**, `helix_validate` PASS.
> **영속화 완료: PR #12~#23 전부 main merged (CI green).** admission plane(P0~P7) ·
> line-ending fix · grounding gate + persona adoption trial · wedge security 4건(정직성 정정
> · evidence-truth 검증 · keyed HMAC signing · external anchoring) · wedge operations 계약(#18)
> · **fidelity_attested 층(#19)** · **real_owned_stakes 층(#21)** · **T4 verdict gate(#23)**.
> **thesis: GOVERNED INTERNAL SYSTEM** — T1 강등 **구조적 확정**(재상향 미추진), T4 미판정.
> 어떤 주장도 부풀리지 않음.
> **provenance 사다리 3/3 칸 코드/계약 완성**: `simulated_unverified`✅ · `fidelity_attested`✅
> (코드+위조불가 계약+실제 receipt 1건) · `real_owned_stakes`✅(코드+위조불가 계약, hard
> independence — 실존 독립 operator 데이터 대기). **어떤 칸도 검증 가능한 뒷받침 없이 주장 불가.**
> **외부 pilot track: `PAUSED_BY_USER` (2026-07-13).** 외부 모집·8주 운영은 시작하지
> 않는다. 실패나 T4 판정이 아니라 정욱님의 현재 작업 상황에 따른 명시적 범위 결정이다.
> 재개 전 정확한 다음 작업은 **없음**이며, 새 명시 지시가 있을 때만 `docs/PILOT-STATUS.md`
> 순서로 재개한다. thesis는 `GOVERNED INTERNAL SYSTEM`, T4는 `NOT JUDGED`를 유지한다.
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

### ①-b T1 재도전 조사 — 완결·merged (PR #14)

T1 강등이 구조적 한계임을 4단계(post-mortem → grounding gate → 독립 재채점 0.20 →
feasibility)로 확정(`_workspace/helix-direction/T1-retry-verdict.md`). 유효 산출물
**grounding gate**(`core/helix_oracle_grounding.py`)를 main에 merge — oracle/predictor의
machine 라벨이 view 인용으로 grounding되도록 강제해 topic-기반 over-claim을 차단.

### ①-c 페르소나 conditional-adoption trial — merged (PR #14)

방법론 논의(비결정론 페르소나 + 인과적 독립성 + provenance 정직 라벨)를 코드로 실체화
(`core/helix_adoption_trial.py`). 4 페르소나(격리 subagent, wedge-무관 이익 함수)가 wedge를
독립 평가: adopt 0 · reject 1 · conditional 3, **is_t4_utility=false**(simulated provenance —
utility 아님, 코드가 격상 금지). 19개 결함 독립 발견. 상세:
`_workspace/helix-direction/persona-trial-report.md`.

### ①-d wedge security 강화 — 페르소나 trial 발견 4건 전부 해소·merged (PR #14~#16)

| # | 결함 (발견: security-engineer 페르소나) | 해소 |
|---|---|---|
| 1 | "tamper-evident" 문서 과대주장 | 정직 정정 (integrity≠authenticity 명시) — PR #14 |
| 2 | evidence_path 실제 파일 미검증 → 가짜 evidence도 ADMIT | opt-in evidence-truth 검증(`evidence_root`) — PR #14 |
| 3 | unkeyed seal → 키 없는 외부 적대자가 chain 재구축 통과 | **keyed HMAC signing**(`core/helix_signing.py`) — PR #15 |
| 4 | 키 보유 내부자가 ledger 재작성·재서명 | **external anchoring**(`core/helix_anchor.py`) — PR #16 |

signing + anchoring 두 층으로 tamper-evidence의 양쪽(외부/내부)이 닫혔다. 전부
결정론 경계 유지(stdlib hmac/hashlib, 키·external_ref 주입).

### ② P5_5 외부 pilot — `PAUSED_BY_USER` (2026-07-13)

wedge(agent handback/approval audit)는 실증 완료 상태이며(내부 pilot 10 decisions, wedge가
수동 검토보다 엄격·false-admit 방향 불일치 0), 연결 킷도 준비됐다:
`helix.py audit-handback` + `docs/WEDGE-RUNBOOK.md` + `examples/wedge/` + sealed metrics.

**자율 준비 완료 (판정 경로 end-to-end, 2026-07-13):**
- pilot 운영 프로토콜: `docs/PILOT-PROTOCOL.md` — 목표(주 20 real decisions 또는 검토시간
  50% 절감, false-admit ≤1%, replay 100%, 3곳 중 2곳 retention, 8주), 온보딩(2h), **역할
  분리**(참가자가 packet 작성·판정·false-admit 확인 → 내부 pilot의 "동일 주체" 한계 해소),
  kill/downgrade 조건.
- 집계 도구: `core/helix_wedge_metrics.py:aggregate_pilot` + `scripts/evaluate/pilot_report.py`
  — 다중 참가자 ledger를 sealed T4 리포트로 통합, gate 판정. ledger로 알 수 없는 신호
  (false-admit·retention·review time)는 sidecar 명시 주입, 없으면 `unmeasured` 정직 표기.
- **T4 verdict 판정 기계**: `core/helix_t4.py:t4_verdict`(PR #23) — metrics 게이트
  (aggregate_pilot)와 **독립-provenance 게이트**(참가자별 검증된 real_owned_stakes가 그
  참가자의 실 ledger head에 바인딩; operator 상호 독립·decoy-author 교차검증)를 **AND**로
  합성. T4는 둘 다 통과할 때만 passed(fail-closed). self-dealing·단일·미검증 경로로 T4 위조
  불가. **판정 경로 완성**: `audit_handback → wedge_metrics → aggregate_pilot →
  owned_stakes → t4_verdict`.

**현재 결정:** 외부 모집·8주 운영을 시작하지 않고 여기서 중지한다. `PILOT-SIM`은 3 persona
21 decisions와 replay 21/21을 완료했으며, 새 `provenance_class` 경계가 synthetic·legacy/
unclassified decision을 real metrics에서 fail-closed로 제외한다. 기존 합성 ledger 재집계는
`21 total / 0 real / 21 excluded`, metrics `failed`, T4 `not_passed`다.

재개 조건·완료 범위의 권위 문서: `docs/PILOT-STATUS.md`.

T4 gate 통과 시 "Governed Internal System"에서 **"Admission Plane(제품)"**으로 상향 가능.

### ③ 페르소나 utility trial — fidelity_attested 층 완성·merged (PR #19)

방법론 논의(비결정론 페르소나 + 인과적 독립성 + provenance)의 결론을 코드·계약·실제
데이터로 실체화. `core/helix_fidelity.py`가 `fidelity_attested` 등급을 **주장이 아니라
획득**으로 만든다: persona source(실존 자료 hash 바인딩) → reproduction sample(격리
subagent의 sealed 판단) → attestation(실존 인물의 sealed 보증; attester≠재현주체 독립성
강제, 이해상충 은폐 없이 기록). `earn_provenance`가 seal-valid + hash-바인딩 + faithful일
때만 격상하고, `aggregate_adoption(attestations=)`가 뒷받침 없는 주장을 강등한다(wedge
evidence_required 관용구).

**실제 receipt 1건 실증**(`_workspace/helix-direction/fidelity/jwy-reproduction-r1.json`):
실존 자료 3건(CLAUDE.md/HANDOFF.md/DESIGN sha256) → 격리 subagent가 정욱님 관점을
비결정론적으로 재현해 wedge를 `conditional`로 판정(rubber-stamp 아님, 5-field 오버헤드·
integrity-only seal을 결함으로 지목) → 정욱님(실존 인물)이 `faithful` 보증 → 등급 획득.
위조불가 실증: 동일 receipt를 attestation 없이 집계하면 `simulated_unverified`로 강등.
**정직한 상한 유지: is_t4_utility=false**(재현 충실도 보증은 authenticity를 올릴 뿐, 손익은
여전히 simulated). 설계/상태: `.pgf/{DESIGN,status}-FidelityAttestation.*`.

### ③-b provenance 사다리 마지막 칸 — real_owned_stakes 층 완성·merged (PR #21)

`core/helix_owned_stakes.py`가 사다리의 최상단이자 **`is_t4_utility`를 flip시키는 유일한
등급**을 위조불가로 만든다. 위조된 주장은 곧 T4 효용 날조이므로 최고위험 — 그래서
**independence를 hard 요건**으로 강제한다: operator == wedge 저자면 **거부**(자기사용은
효용 신호 아님; fidelity가 dogfooding을 허용한 것과 원리적으로 반대). real work(simulated
거부·decision_count>0·실 ledger head 바인딩) + objective outcomes(정수 측정+replay_verified,
감정서술 거부) + 소유 손익 명시일 때만 `owned_stakes_grade`가 격상. `aggregate_adoption`이
뒷받침 없는 real_owned_stakes 주장을 강등("cannot fabricate a T4 utility signal").
**정직한 상한**: 단일 operator = utility_candidate이지 T4 pass 아님 — 완전 T4는 다중 참가자
pilot 게이트(`docs/PILOT-PROTOCOL.md`) 필요. 이 층은 등급을 위조불가로 만들 뿐 실 데이터를
*생성하지 않는다*(그것은 외부 pilot이라는 실세계 사건). 설계/상태:
`.pgf/{DESIGN,status}-OwnedStakes.*`.

### (종결) T1 재도전 — 재상향 미추진

구조적 한계로 확정(①-b). generator 주장 재상향은 추진하지 않는다. blind trial 방법론은
grounding gate로 강화됨.

## 3. 산출 인벤토리 (HELIXDirection + 후속, **main merged PR #12~#23**)

- **core 신규 24종**: helix_{state_receipt, holdout, prediction, novelty, constitution,
  evidence, risk_policy, authorization, stop_token, contestability, execution_plan,
  admission, side_effect_guard, actuator, impact_handback, wedge, wedge_metrics,
  oracle_grounding, adoption_trial, signing, anchor, fidelity, owned_stakes, **t4**}
- **schemas 8종**, tests 329→**695**, **CLI**: `state-receipt`, `audit-handback`
- **wedge 킷**: `docs/WEDGE-RUNBOOK.md`(정직 security-boundary 포함), `examples/wedge/`,
  `docs/PILOT-PROTOCOL.md`, `docs/WEDGE-OPERATIONS.md`(운영 계약); **policy**: `docs/HOLDOUT-POLICY.md`
- **security**: `helix_signing`(keyed HMAC) · `helix_anchor`(external anchoring) —
  actuation ledger에 opt-in 적용
- **seed**: `seed/evaluation/` (synthetic + T1-LIVE-001 실 cohort — 30 unseen, pinned SHA)
- **scripts**: `scripts/evaluate/` (synthetic builder · T1 collector · blind trial ·
  shadow replay · pilot_report); `engines/exploit/adapter.py`에 `registry_admissions` 추가

## 4. Evidence 색인 (`_workspace/helix-direction/`, gitignored durable)

- T0 `T0-verification.*` · T1 `T1-validity-report.md`+`T1/`+`trials/T1/`
- T2 `T2-verification.*`+`T2/` · T3 `T3-verification.*`+`T3/`
- T4 `T4-verification.md`+`T4/`(internal pilot report · sealed metrics · ledger)
- P7 `P7-regression.json` · `P7-architecture-review.md` · `P7-thesis-verdict.md`
- PGF 상태: `.pgf/status-HELIXDirection.json` (41 done / 2 blocked / 43 nodes)

## 5. Blocked 노드 재개 조건

| 노드 | 사유 | 재개 조건 |
|---|---|---|
| `P5_5_ExternalPilots` | `PAUSED_BY_USER`; 외부 모집·8주 운영 미개시 | 정욱님의 새 명시 재개 지시 |
| `P6_FederationPlane` | 진입 조건 미충족 | T1 재도전 통과 + T4 판정 통과 + 외부 사용자 2 |

## 6. 알려진 한계 / 이탈 (은폐 없음)

1. NoveltyTrial 실측(구현·환원 ≥3건) 미수행 — T1 재도전 조건(단 T1은 구조적 한계로 종결).
2. actuation ledger는 keyed HMAC signing + external anchoring **구현**(opt-in). stop token 등
   나머지 seal은 아직 unkeyed — 필요 시 동일 signing 패턴 적용 가능(backlog).
3. 기존 exploit ledger의 fail-open 소비 경로가 migration flag 유예 하 잔존.
4. wedge latency/cost는 sidecar 설계만 (결정론 경계 준수의 의도적 선택).
5. FederationPlane 미구현 — DESIGN의 조건부 gate가 의도한 blocked.
6. wedge 운영 backlog 3건은 `docs/WEDGE-OPERATIONS.md`에 계약으로 명시(코드 버그 아님):
   AHV는 명확 실패로 fail-closed, ledger 동시성은 single-writer 계약 + verify 탐지(실증),
   컴플라이언스는 evidence 제공(인증 주장 없음). 다중 writer 직렬화 어댑터는 결정론 core
   밖 backlog로 잔존.
7. 페르소나 trial provenance 사다리 3/3 코드/계약 완성: simulated_unverified ·
   fidelity_attested(실제 receipt 1건) · real_owned_stakes(hard independence, 위조불가).
   앞 둘은 is_t4_utility=false. real_owned_stakes만 utility 신호이며 위조불가 계약은 완성됐으나
   실 데이터(독립 외부 operator)는 미보유 — 데이터 생성은 P5_5 외부 pilot(실세계 사건).
6. (방법론) T1 oracle·T2 brief를 단일 운영자 작성; 격리는 predictor/classifier subagent
   컨텍스트로만 확보. 제3자 역할 분리는 외부 pilot의 몫.
8. **두 액추에이션 표면의 게이트 디커플링** (풀사이클 실행 검토, 2026-07-14 확인):
   `helix.py close-loop`(명시 winner write)는 **handback 검증만**으로 게이트되고
   (`ActionHandbackVerifier`, breach=write 중단), `state-receipt`의 `actuator_ready`
   (diversity_repair·unverifiable_report·state_drift 기반 fail-closed) authority를 **참조하지
   않는다**. 즉 state authority가 `blocked`여도 명시 close-loop write는 진행된다. 명시
   operator write + 독립 handback 게이트로 방어된다는 점에서 방어 가능하나, **close-loop이
   state_drift를 존중하지 않는 것**이 의도인지(명시 override) 갭인지는 정욱님 결정 사항.
   미결정 항목으로 기록. (RUNBOOK §4에도 표기.)

## 7. Rollback 상태

기존 방향 작업은 **main에 merged**(PR #12~#23). PILOT-SIM·provenance boundary·pause 기록은
baseline commit `f2eb20c`로 `origin/main`에 push됐고 CI run `29230457241`이 success다.
되돌리려면 해당 커밋들을 revert.
nested 19 repos는 무변경(clean). `_workspace/`는 gitignored durable evidence — 삭제 금지.
미merge branch 없음.

## 8. 운영 규율 (유지)

- 정욱님 호칭, 한국어 보고, code/command/identifier English.
- 한 번에 하나의 gated step, 다음 최우선 작업 하나만 보고.
- PowerShell 5.1 금지(Git Bash 또는 지정 PS7), PATH의 `python`만 사용.
- `git add -A` 금지(nested repos), commit/push/merge/공개는 명시 승인 시에만.
- hard gate 실패를 threshold 완화나 문서 표현으로 숨기지 않는다.
- runtime evidence가 문서보다 우선하며 즉시 동기화한다.

## 9. 한 줄 인수인계

> **HELIXDirection이 GOVERNED INTERNAL SYSTEM으로 종결됐고(695 tests·sealed evidence,
> PR #12~#23 main merged), Condense 5 플랫폼 라인도 유지된다. T1 강등은 구조적 한계로
> 확정, T4는 미판정. 페르소나 conditional-adoption trial이 wedge security 4건을 발견·해소
> (keyed signing + external anchoring 포함)하고, provenance 사다리 3/3 칸(simulated ·
> fidelity_attested[실제 receipt 1건] · real_owned_stakes[hard independence])과 T4 verdict
> 판정 기계(metrics ∧ 독립-provenance)가 전부 위조불가로 완성됐다. PILOT-SIM 21건과
> provenance fail-closed 경계까지 검증됐으며, 외부 pilot은 `PAUSED_BY_USER`다. T4는
> `NOT JUDGED`, 제품 주장은 보류하며 새 명시 지시 전에는 외부 pilot 다음 작업이 없다.**
