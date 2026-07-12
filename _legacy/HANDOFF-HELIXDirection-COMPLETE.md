# HANDOFF — HELIXDirection 완료 계보 (보존본)

> 이 문서는 HELIXDirection 방향 작업(P0~P7)의 **상세 완료 계보 보존본**이다.
> 현재 상태의 정본은 `HANDOFF.md`와 `.pgf/status-HELIXDirection.json`이며,
> 최종 판정은 `_workspace/helix-direction/P7-thesis-verdict.md`다.
> 종결 시점: 2026-07-12, thesis = GOVERNED INTERNAL SYSTEM.

---

# HANDOFF — HELIXDirection 작업 연계

> 갱신: 2026-07-11
> 현재 방향: HELIX를 `advisor + human actuator`에서 **Deterministic Admission Control Plane**으로 전환한다.
> **정확한 다음 작업: `P7_4_Handoff`를 수행한다.**
> **최종 thesis: GOVERNED INTERNAL SYSTEM (T0✓ T1✗강등 T2✓ T3✓ T4미판정).**
> **T4 판정: NOT JUDGED — 외부 pilot은 사용자 승인 대기로 blocked (승인 시 즉시 재개 가능).
> 제품 주장은 보류. thesis 경로는 "Governed Internal System"이다.**
> **T1 판정: FAILED — `platform generator` 주장은 `internal corpus router`로 강등됨.
> autonomous CONDENSE emit 금지. 이 판정을 완화하거나 미화하지 말 것.**
> **T2 판정: PASSED — Constitution은 enforce-candidate.**
> **T3 판정: PASSED — closed actuator 성립. enforce 범위는 R0/R1 로컬 actuation이며 R2+는
> human 승인 필수 (T3-S7 승인은 synthetic rehearsal).**
> Runtime transfer detail: `_workspace/runtime-handoff-HELIXDirection-P2.md`

---

## 0. 이전 계보

Condense v0.6, U6~U9, forward closure, CI fix까지의 완료 상태와 운영 지식은
[`HANDOFF-CONDENSE-v0.6-COMPLETE.md`](HANDOFF-CONDENSE-v0.6-COMPLETE.md)에 보존했다.

이전 문서의 `RUN_EXPLOIT`는 당시 snapshot의 다음 action이다. 현재 작업 방향의 next task로 사용하지 않는다.

---

## 1. 현재 상태

### 완료

- HELIX 전반 구조와 현재 구현을 분석했다.
- PGF P1~P14 멀티페르소나 분석을 통합했다.
- 향후 방향을 `Truth Plane -> Constitution -> Actuation -> Utility -> Federation`으로 설계했다.
- 단계별 PG 실행 계획을 작성했다.
- 현재 검증 기준에서 `python core/helix_validate.py .` PASS, `281 tests` OK를 확인했다.
- `P0_BaselineFreeze`를 완료했다. 15개 canonical input/gate/report/document hash의 독립 재계산이
  모두 일치했다.
- `P1_1_ReceiptSchema`를 완료했다. `helix-state-receipt/1.0` Draft-07 schema, canonical example,
  stdlib-compatible 계약 테스트를 추가했고 전체 288 tests가 통과했다.
- `P1_2_FreshnessRules`를 완료했다. report/source의 sealed SHA256만으로
  `fresh|stale|missing|unverifiable`을 판정하며 mtime·wall clock을 사용하지 않는다. 전체 298 tests가
  통과했다.
- `P1_3_ReceiptBuilder`를 완료했다. 명시적으로 선택된 input/gate/report와 runtime report를
  schema-valid receipt로 조립하고 canonical JSON SHA256으로 봉인한다. 전체 306 tests가 통과했다.
- `P1_4_StatusCLI`를 완료했다. `python helix.py state-receipt [--out P]`가 실제 loader 선택 경로와
  runtime state를 receipt로 출력한다. 현재 receipt는 `REFRESH_INPUTS`, diversity blocker와 unsealed
  reports의 `unverifiable_report`를 기록하며 전체 312 tests가 통과했다.
- `P1_5_DriftGate`를 완료했다. `state-receipt --compare P`가 input/gate/report/runtime/action/authority
  drift와 receipt integrity를 분류하고 drift 시 `state_drift`로 fail-closed한다. 실제 current 비교는
  `drifted=false`, 전체 321 tests가 통과했다.
- `P1_6_T0Verify`를 완료했다. 실제 root 반복 hash, stale source, stored receipt tamper, action drift,
  HANDOFF 정합을 통합 검증했다. T0 verdict는 `passed`, canonical receipt hash는
  `8ea2534ef8904ac7e42142fa0ca3726d372e5db3e1d745a8f668884f33ec67f7`이다.
- `P2_1_HoldoutPolicy`를 완료했다. unseen selection, license evidence, candidate/oracle isolation,
  prediction-before-reveal, missing/abstain 무득점 규율과 Draft-07 registry schema를 고정했다. 전체
  329 tests가 통과했다.
- `P2_2_LockedRegistry`를 완료했다. `core/helix_holdout.py`가 policy-compliant cohort manifest를
  실제 artifact hash로 조립하고 canonical JSON commitment로 봉인·검증한다. synthetic live-size
  registry(`seed/evaluation/holdout-registry.json`, locked eligible 20/22, commitment
  `2450602affaac3cb8f0e9dfdb8224b8360f44399c6adf907a5e36c9c3a7e7e22`)는
  `scripts/evaluate/build_synthetic_holdout.py`로 결정론 재생성된다. lock 이후 candidate
  삭제·교체·selection rule 변경·excluded→eligible 승격은 commitment mismatch로 fail하고,
  prediction seal·reveal·scored 전이는 lock을 깨지 않는다. reveal-before-prediction은 validator가
  거부한다. 전체 350 tests가 통과했다.
- `P2_3_PredictionReceipt`를 완료했다. `core/helix_prediction.py`가 prediction/reveal receipt를
  `schemas/helix-trial-receipt.schema.json` 계약으로 봉인한다. prediction receipt의 parent는 cohort
  commitment, reveal receipt의 parent는 sealed prediction hash로 append-only hash chain을 이룬다
  (wall clock 불사용). `ABSTAIN`/`MISSING_ARTIFACT`는 label 없는 명시적 sealed outcome이다.
  excluded 후보 예측, oracle revealed 후 예측(blindness 상실), double-seal, drift된 candidate view,
  sealed prediction 없는 reveal, approver 부족/비허용 role/중복, commitment와 다른 oracle bytes는
  전부 거부된다. `verify_receipt_chain`이 registry 대비 chain을 독립 재검증하며 전체 369 tests가
  통과했다.
- `P2_4_BlindRunner`를 완료했다. `scripts/evaluate/blind_machine_trial.py`가 locked cohort 위에서
  view→주입 predictor→seal→reveal approval→oracle reveal→`core/helix_prediction.py:score_cohort`
  결정론 scoring 한 회전을 닫는다. predictor는 parsed candidate view만 받는다(구조적 blind).
  복수 시스템이 같은 cohort·같은 locked eligible denominator(20)로 비교되며 `ABSTAIN`/
  `MISSING_ARTIFACT`/protocol violation/missing prediction은 denominator에 남고 credit 0이다.
  macro-F1은 machine id 다중라벨 기준. synthetic evidence: perfect predictor 20/20 coverage 1.0
  macro-F1 1.0 gates PASS, baseline-abstain 0/20, baseline-constant 1/20 gates FAIL(정직 보고).
  report: `_workspace/helix-direction/trials/synthetic-blind-trial/blind-trial-report.json`.
  전체 380 tests가 통과했다.
- `P2_5_NoveltyTrial`을 완료했다. `core/helix_novelty.py`가 novelty 주장(`CONDENSE`/`DEFER`
  sealed prediction)에 대한 reduction receipt를 `schemas/helix-reduction-receipt.schema.json`
  계약으로 봉인한다. chain은 `commitment→prediction→reveal→reduction`으로 연장되어 완결된
  blind trial 없이는 reduction verdict가 존재할 수 없다. 구현 실험은 외부 evidence
  (path+hash 주입)이며 verdict는 `novel_confirmed`/`reduced_to_existing`(=false-CONDENSE)/
  `not_implemented`로 결정론 유도된다. `aggregate_novelty`가 false-CONDENSE count·estimated
  implementation cost·novelty precision(resolved 분모)·novelty yield(전체 claims 분모)를
  공개하고, 미구현 주장은 어떤 지표도 부풀릴 수 없다. runner report에 시스템별 novelty 섹션이
  추가됐다. 전체 393 tests가 통과했다.
- `P2_6_T1Verify`를 완료했다 — **T1 gate FAILED, 정직 판정**. sealed selection policy로 GitHub
  42개 repo를 처리해 30개 eligible을 pinned SHA + README artifact + license evidence로 잠갔다
  (cohort `T1-LIVE-001`, commitment `f0794d15…`). oracle 30개를 prediction 전에 봉인하고, 격리
  subagent(candidate view만 접근) + 결정론 `forward_predict`로 blind 예측했다. 결과: exact 25/30,
  coverage 0.900(PASS), **macro-F1 0.450(FAIL)** — M1/M3(gate 계열)은 정확(F1 1.0/0.8), M10/M15
  (threshold-bound/score-tier)는 전멸(F1 0). 두 baseline은 크게 넘었으나 절대 gate 미달. kill
  criteria대로 thesis를 `internal corpus router`로 강등, autonomous emit 금지. novelty 구현 추적
  (최소 3건)은 미수행으로 정직 공개(23 claims 전부 `not_implemented`). 한계(단일 운영자 oracle
  authorship, oracle 품질, 선택 편향)는 report에 명시. 증거:
  `_workspace/helix-direction/T1-validity-report.md`. 전체 394 tests가 통과했다.
- `P3_1_ActionIntent`를 완료했다. `schemas/action-intent.schema.json`(Draft-07, stdlib subset)과
  `core/helix_constitution.py`가 intent 계약을 고정한다: proposer, risk_class R0~R3, scope
  (write_paths/remote_mutation/publish), impact(authority/economic/physical/broad_public),
  reversibility(rollback_plan 강제), budget, justification. `classify_risk`가 선언된 효과에서
  최소 정직 risk class를 결정론 유도하며 **under-classification은 fail-closed로 거부**된다
  (상향 선언은 허용). `intent_digest`가 canonical SHA256 정체성을 제공한다. R0~R3 예제 4종
  (`examples/constitution/`)과 실패 주입 테스트 18종. 전체 412 tests가 통과했다.
- `P3_2_EvidenceManifest`를 완료했다. `schemas/evidence-manifest.schema.json`과
  `core/helix_evidence.py`가 evidence 계약을 고정한다: action을 정당화하는 artifact들의 content
  hash/bytes, issuer, provenance(origin+reference — receipt 계열 origin은 reference 필수),
  policy version을 canonical seal로 봉인하고 `intent_digest`로 정확히 하나의 ActionIntent에
  바인딩한다. 검증은 fail-closed: 빈 evidence, disk상 missing artifact, hash/bytes mismatch,
  seal 파손, intent binding mismatch는 전부 DENY 근거 문제로 보고되며 재봉인(reseal) 후에도
  실제 bytes 대비 검증에서 탐지된다. 전체 427 tests가 통과했다.
- `P3_3_RiskPolicy`를 완료했다. `core/helix_risk_policy.py`가 approval/separation/expiry matrix를
  순수 함수로 고정한다: R0/R1 승인 0(자동), R2 human 1인, R3 two-party human 2인 + dry-run
  evidence(`role="dry_run"` artifact). separation of duties(proposer 자기승인 금지), human만
  승인 가능, 중복 approver 무효. **expiry는 wall clock이 아니라 state-receipt anchor** — 승인이
  발행 시점의 receipt hash에 고정되며 state drift가 승인을 자동 만료시킨다(P1 drift gate와 동일
  semantics). `effective_risk_class`는 declared/derived 중 높은 쪽을 취해 라벨을 신뢰하지 않고,
  승인 집합에 무효 승인이 하나라도 있으면 전체 평가가 fail한다(fail-closed). 전체 444 tests가
  통과했다.
- `P3_4_AuthorizationGate`를 완료했다. `core/helix_authorization.py`의 `authorize()`가 세 계약을
  하나의 sealed GateResult(`schemas/gate-result.schema.json`)로 결합한다:
  `ALLOW|SANDBOX|HUMAN|DENY|RETIRE`, 우선순위 고정. intent 무효·evidence
  missing/mismatch/binding 위반·승인 위반(자기승인 등)은 **DENY**(missing/mismatched evidence는
  절대 ALLOW 불가), 다른 policy version으로 발행된 evidence는 **RETIRE**(재발행 요구), 승인
  부족·dry-run 부재·state-drift 만료 승인은 **HUMAN**(갱신 대기), 계약·승인은 유효하나 전
  artifact가 external-only provenance면 **SANDBOX**(thin evidence). 동일 입력 → 동일 sealed
  결과이며 모든 결과가 reason·policy version·입력 digest(replay 근거)를 기록한다. 전체 460
  tests가 통과했다.
- `P3_5_StopResume`를 완료했다. `core/helix_stop_token.py`가 stop/resume protocol을 고정한다:
  stop token은 issuer/reason/scope(global 또는 write-path prefix)/state-receipt anchor를 가진
  **불변 sealed 문서**이고, resume은 token hash에 chain된 별도 sealed receipt다
  (prediction→reveal과 동일한 append-only 패턴). **authority 분리**: issuer는 자기 stop을
  resume할 수 없고 issuer가 승인 집합에 포함되기만 해도 거부된다. **변조된 token은 계속
  차단**되며(원본 복원 전 resume 불가), 변조된 resume receipt는 아무것도 해제하지 못한다.
  `authorize()`에 stop 검사가 결합되어 scope에 걸린 side-effect intent는 evidence/승인과
  무관하게 DENY("stopped: …")가 된다 — read-only intent는 stop 중에도 통과(T3: stop 이후
  write/publish=0). wall clock 없이 anchor/chain으로만 순서를 증명한다. 전체 479 tests가
  통과했다.
- `P3_6_Contestability`를 완료했다. `core/helix_contestability.py`가 세 receipt를 고정한다.
  **replay**: 저장된 GateResult를 기록된 입력으로 재평가해 seal 단위로 비교 — 입력이 기록과
  다르면 replay가 아니고, divergence는 필드별로 분류 보고된다. **appeal**: 판정 seal에 chain된
  sealed 이의 기록 — 판정을 절대 바꾸지 않는다. **override**: human 전용, 비어있지 않은 reason
  필수(reason 없는 override는 존재 불가), 결정이 실제로 달라야 하며 state-receipt anchor를
  갖는 sealed receipt — 원 GateResult는 불변 보존. `effective_decision`은 유효 override만
  접고, 무효 override는 보고 후 무시, **상충하는 유효 override는 DENY로 fail-closed**. 전체
  498 tests가 통과했다.
- `P3_7_ShadowReplay`를 완료했다. 실제 프로젝트 역사에서 **35개 action을 재구성**하고
  (R0 read-only 5 · R1 local write 21 · R2 publish/remote 6 · R3 authority 3), 격리 subagent가
  declared 라벨 없는 brief만 보고 독립 risk oracle을 지정했다. 승인 0 상태 shadow gate 결과:
  **risk disagreement 0/35 (0%), high-risk false-ALLOW 0, oracle-expected 대비 decision
  mismatch 0, deterministic replay 35/35, missing/tampered evidence 주입 DENY/DENY** — T2
  shadow gate 전부 PASS. 한계(operator 서술 편향, shadow≠enforce, 내부 표본 한정)는 report에
  명시. 증거: `_workspace/helix-direction/T2/shadow-replay-report.{md,json}`, harness
  `scripts/evaluate/shadow_replay.py`.
- `P3_8_T2Verify`를 완료했다 — **T2 gate PASSED**. report 집계를 신뢰하지 않고 source에서
  독립 재계산(disagreement 0, false-ALLOW 0, replay 35/35), 연속 2회 재실행 byte-identical
  (결정론), stored-vs-fresh semantic 동일성 검증. 검증 중 흥미로운 실증: P3_7 실행 후
  HANDOFF.md 편집이 evidence seal 이동을 유발했고 content-addressed manifest가 이를 정확히
  탐지 — living document를 evidence로 쓰는 한계로 기록, P4 actuation evidence는 불변 스냅샷
  경로를 쓴다. verdict: Constitution shadow → **enforce-candidate 승격** (enforcement는
  P4/T3에서만). T1 강등은 유지. 증거: `_workspace/helix-direction/T2-verification.json` +
  `T2-verification-report.md`. 전체 498 tests OK.
- `P4_1_ExecutionPlan`를 완료했다. `core/helix_execution_plan.py`가 승인된 intent의 실행 계획을
  sealed 계약으로 고정한다: path별 create/modify/delete effect + planned bytes, **intent
  scope/budget 초과는 build fail-fast**, dry-run precondition(create 대상 존재/modify·delete
  대상 부재) 위반도 fail-fast. rollback evidence는 실행 전 bytes를 **content-addressed 불변
  스냅샷 경로**(`{sha256}.bin`)에 저장해 living-document seal 이동 문제를 원천 차단(T2 교훈).
  plan은 ALLOW/SANDBOX GateResult에만 chain되며(gate 없이 plan 없음), `verify_execution_plan
  (check_preconditions=True)`가 actuation 직전 filesystem drift(대상 bytes 변경, create 대상
  선점)를 탐지한다. 전체 510 tests가 통과했다.
- `P4_2_FailClosedAdmission`을 완료했다. `core/helix_admission.py`가 handback verdict를
  admission class로 결정론 사상한다: `valid→ADMIT`, `thin→SANDBOX_ONLY`, `breach→EXCLUDED`,
  `absent→QUARANTINE`(unknown verdict도 QUARANTINE — fail-closed). 유일한 예외는 명시적
  **migration flag**: sealed·reason 필수·state-receipt anchor를 가진 유예로 absent만 임시
  ADMIT하며(thin/breach 격상 불가), state drift 시 자동 만료되고 변조 시 무효다. 판정은
  sealed admission receipt(flag chain 기록)로 남는다. adapter에 additive 진입점
  `registry_admissions()`를 추가했고 **기존 `registry_to_ledger` fail-open 경로는 무변경**
  (테스트로 고정) — 소비 전환은 P4_5 unified command에서 수행한다. 전체 523 tests가 통과했다.
- `P4_3_SideEffectGuard`를 완료했다. `core/helix_side_effect_guard.py`의
  `guard_side_effects()`가 실행 직전 4중 재검사를 한 번에 판정한다: (1) plan
  seal/binding/chain/scope/budget/rollback 스냅샷 재검증, (2) **authority currency** — gate가
  현재 state receipt에 anchor되어 있지 않으면(state drift) plan 권한 만료("expired authority는
  consumed로 전환 불가" invariant의 실행 지점), (3) 실행 시점 active stop 재검사(T3: stop 이후
  write/publish=0), (4) filesystem precondition drift 재검사. guard는 판정만 하고 절대 실행하지
  않으며, sealed receipt가 plan seal에 chain되어 actuator가 "이 plan을 이 상태에서 clear받고
  실행했다"를 증명할 수 있다. 복수 실패는 전부 분류 보고된다. 전체 534 tests가 통과했다.
- `P4_4_ImpactHandback`을 완료했다. `core/helix_impact_handback.py` +
  `schemas/impact-handback.schema.json`이 실행 후 상태를 반증 가능하게 봉인한다:
  **outcome delta**(effect별 실제 post hash/bytes; 미적용 effect는 `not_applied`로 정직 기록),
  **actual use vs budget**(실제 초과는 deviated), **undeclared 검출**(pre/post scope snapshot
  제공 시 plan에 없는 in-scope 변경은 위반; 미제공 시 `checked=false`로 정직 표기),
  **rollback proof**(`perform_rollback`이 content-addressed 스냅샷으로 원상복구 후 pre_sha256
  재현을 증명; 손상 스냅샷은 unprovable), **trace chain**(intent→gate→plan→guard→handback).
  cleared guard 없이는 handback이 존재할 수 없고, deviations는 `verdict=deviated`로 봉인되며
  세탁되지 않는다. handback 이후 재변경도 검증기가 drift로 탐지한다. 전체 547 tests가
  통과했다.
- `P4_5_UnifiedCommand`를 완료했다. `core/helix_actuator.py`의 `run_admission()`이
  `propose→gate→plan→guard→execute→handback→ledger` 폐루프를 한 함수로 닫는다. 모든 거부
  (HUMAN/DENY gate, stop token, plan 거부, guard 미clear)는 **side effect 0**으로 종료되고
  그 거부 자체가 ledger에 남는다. deviated handback은 자동 rollback + 증거 기록(rollback
  실패는 recovered=false로 정직 기록). **consumable = ALLOW + clean일 때만** — SANDBOX
  실행과 deviated 실행은 절대 소비되지 않는다(P4_2 admission 의미론의 소비 전환점).
  actuation ledger는 append-only JSONL hash chain(parent→entry seal)으로 어떤 라인 변조도
  chain 파손으로 탐지된다. 전체 557 tests가 통과했다.
- `P4_6_FailureInjection`을 완료했다. 적대적 주입 13종이 전부 "side effect 0" 또는 "정직
  기록"으로 끝남을 실증했다: **bypass**(위조 guard handback, 미기록 guard, HUMAN gate 후
  실행 receipt, plan 거부 후 실행, 무근거 rollback — 신규 `verify_actuation_chain` ledger
  audit이 전부 탐지; canonical seal은 무결성일 뿐 서명이 아니므로 위조 탐지는 ledger 정합이
  담당), **expiry**(gate 후 state drift → guard 차단 + handback 생성 불가),
  **stop**(gate 통과 후 발행된 stop → 차단 → resume 재개), **rollback 실패**(손상 스냅샷 →
  guard가 사전 차단, 사후엔 recovered=false 정직 기록), **ledger 공격**(삭제/재정렬 →
  chain 파손). 주입 설계 중 실결함 1건 발견·수정: `_snapshot`이 content-addressed 경로의
  선점 오염 파일을 검증 없이 신뢰하던 것을 재hash 검증으로 방어. 전체 570 tests가 통과했다.
- `P4_7_T3Verify`를 완료했다 — **T3 gate PASSED**. 7개 시나리오(clean ALLOW·HUMAN 거부·stop
  거부·plan 거부·deviated+rollback·SANDBOX·승인된 R2)를 하나의 hash-chained actuation
  ledger(21 entries)로 실행하고, run 결과를 신뢰하지 않고 **stored ledger에서 독립
  재집계**했다: ungated admission 0, stop 이후 write 0, bypass audit 0, rollback failure의
  성공 기록 0, gate replay 7/7 seal 재현 + ledgered receipt seal 19/19 재검증. 첫 실행의
  FAIL은 검증 스크립트의 seal-key 선택 오탐(guard/handback의 참조 필드 `plan_sha256`)이었고
  대상 시스템 결함이 아니었음을 기록했다. **함의**: Constitution enforce는 `run_admission`
  경로의 R0/R1 로컬 actuation에서 켜질 수 있고, R2+는 human 승인 필수(T3-S7은 synthetic
  rehearsal), T1 강등은 유지. 증거: `_workspace/helix-direction/T3-verification.{json}` +
  `T3-verification-report.md`. 전체 570 tests OK.
- `P5_1_WedgeContract`를 완료했다. `core/helix_wedge.py`의 `audit_handback()`이 첫 wedge
  여정을 단일 진입으로 닫는다: 제출된 handback packet을 content-addressed 불변 경로에 저장
  → AHV 5-predicate verdict → P4_2 admission class(valid=ADMIT/thin=SANDBOX_ONLY/
  breach=EXCLUDED; 제출된 packet에는 migration flag 무관) → R0 audit intent의 Constitution
  gate(외부 제출물이라 정직하게 SANDBOX 판정) → sealed wedge decision을 actuation ledger에
  chain 기록. decision은 T4 North Star marker(`weekly_real_admission_decisions`)를 내장한다.
  `verify_wedge_decision()`이 저장 packet 재hash + AHV 재평가 + admission 재분류로 replay를
  증명하며, 세탁된 verdict(breach→valid reseal)는 replay에서 탐지된다. 새 판정 로직 0 —
  전부 기존 백본 재사용. 전체 582 tests가 통과했다.
- `P5_2_IntegrationKit`을 완료했다. `python helix.py audit-handback --packet <file>`
  서브커맨드(anchor 미지정 시 live state receipt 자동 계산; exit code 0=ADMIT,
  3=SANDBOX_ONLY, 4=QUARANTINE/EXCLUDED, 1=gate 거부/replay 실패, 2=usage), sample packet
  3종(`examples/wedge/` valid/thin/breach), operator runbook(`docs/WEDGE-RUNBOOK.md` —
  packet 형식, 판정 해석, replay 검증, appeal 경로, North Star 측정), RUNBOOK.md 진입 링크.
  CLI가 매 판정 직후 replay 검증을 자동 수행하고 제3자 재현용 replay 명령을 출력한다.
  subprocess E2E 5종(3판정+exit code, JSON 출력, ledger chain, **출력된 replay 명령 실행 시
  동일 decision seal 재현**, usage)이 통과. 전체 587 tests가 통과했다.
- `P5_3_MetricsLedger`를 완료했다. `core/helix_wedge_metrics.py`의 `wedge_metrics()`가 T4
  지표 전부를 **sealed ledger에서 재계산**한다(별도 mutable counter 없음): decisions_total
  (North Star 분자), admission/verdict 분포, `prevented_invalid_handbacks`(EXCLUDED+
  QUARANTINE), gate refusals, distinct operators, **replay rate**(전 decision을
  `verify_wedge_decision`으로 재검증 — 세탁된 receipt는 chain을 재구축해도 replay율을
  떨어뜨림), intervention rate(ledger의 gate에 chain된 검증 가능한 appeal/override만 집계,
  무효/외부 receipt는 보고만). 오염된 ledger는 `metrics_valid=false`(깨진 chain 위 지표
  불신). latency/cost는 wall-clock이라 sealed receipt 밖 sidecar audit metadata로
  설계 명문화. report는 ledger head hash에 anchor된 sealed 문서로 동일 ledger → 동일
  report. 전체 595 tests가 통과했다.
- `P5_4_InternalPilot`을 완료했다. 실제 작업 6건(exploit 실구현 handback 1 + HELIXDirection
  세션 실작업 5)을 packet화해 wedge로 판정했다 — 총 **10 decisions** (교정 재제출 포함,
  1차/2차 모두 append-only ledger 보존): ADMIT 5 · SANDBOX_ONLY 1 · EXCLUDED 4,
  `prevented_invalid_handbacks=4`, replay 10/10. **정직한 발견**: (1) 1차 제출 4건의
  breach는 operator(runtime)의 trace 계약 오해였고 wedge가 정확히 차단 — 함정을
  WEDGE-RUNBOOK에 반영, (2) wedge는 수동 검토(6/6 수용)보다 엄격하며(1차 기준 2/6 수용)
  불일치는 전부 "증거 더 요구" 방향, false-admit 방향 0건, (3) 문서 동기화처럼 결정론
  trace 없는 작업은 thin/SANDBOX_ONLY로 정직 격리. 한계: 작성·판정 동일 주체, 표본
  6건/이틀(T4 gate 표본 아님). 증거: `_workspace/helix-direction/T4/
  internal-pilot-report.md` + `pilot-metrics.json`(sealed) + `pilot-ledger.jsonl`.
- `P5_6_T4Verify`를 완료했다 — **T4 NOT JUDGED**를 정직하게 봉인했다. T4 gate는 독립 외부
  pilot 3개를 요구하는데 외부 모집/공개는 명시 승인 필요 행위이고 승인이 없었으므로,
  Failure Strategy 규율대로 `P5_5_ExternalPilots`를 **blocked**(승인 시 재개 가능)로,
  T4를 성공도 실패도 아닌 **미판정**으로 기록하고 제품 주장을 보류했다. 내부 실증은
  시장 검증이 아님을 명시. 이로써 완료 정의 경로 2(**Governed Internal System**: T0~T3
  통과, T4 미판정, 내부 admission runtime 유지)가 현재 사실과 일치한다.
  P6(T5)은 진입 조건 원천 미충족으로 blocked 유지. 증거:
  `_workspace/helix-direction/T4-verification.md`.
- `P7_1_Regression`을 완료했다 — **PASSED**. 595 tests OK, `helix_validate` PASS,
  `git diff --check` clean, live state receipt가 T0 canonical `8ea2534e…`과 동일
  (P0 이후 전 작업이 state authority를 훼손하지 않음), **nested 19 repos 전부 clean**
  (이번 HELIXDirection 작업이 nested repo를 일절 수정하지 않음), 미commit 인벤토리
  (modified 6 · untracked 60 — 전부 이번 작업 산출물)를 sealed record로 봉인. 증거:
  `_workspace/helix-direction/P7-regression.json` (seal `e150f083…`).
- `P7_2_ArchitectureReview`를 완료했다. DESIGN Gantree 20노드 전부를 실구현에 대조했다:
  **검증 가능한 전 노드 구현·검증 완료**, PPR 3함수(admit/blind_machine_trial/
  execute_authorized)의 acceptance_criteria 전 항목이 코드·테스트에 매핑됨, Invariants
  6개 전부 준수(일부는 강화 — autonomous emit 금지). **이탈 5건 정직 분류**: novelty
  실측 미수행(T1 재도전 조건), stop token은 서명이 아닌 seal+ledger 정합, 기존 fail-open
  소비 경로가 migration 유예 하 잔존, latency/cost sidecar 미구현(결정론 경계의 의도적
  선택), FederationPlane은 DESIGN의 조건부 gate가 의도한 blocked. 증거:
  `_workspace/helix-direction/P7-architecture-review.md`.
- `P7_3_ThesisVerdict`를 완료했다 — **최종 판정: GOVERNED INTERNAL SYSTEM** (완료 정의
  경로 2). 주장하는 것: proposal→verification→authorization→actuation→handback→ledger
  폐루프가 이 repo 안에서 결정론 작동하며 595 tests + 주입 13종 + 실데이터 검증으로
  고정됨; 모든 부정적 사실(T1 강등, T4 미판정, 이탈 5건)이 sealed evidence로 보존됨.
  주장하지 않는 것: platform-generator 능력(T1 FAILED), 시장 효용(T4 NOT JUDGED),
  암호 서명 authenticity. 재상향 조건(T1 재도전 4요건, T4 외부 pilot, T5 진입 조건)을
  완화 불가로 봉인. 증거: `_workspace/helix-direction/P7-thesis-verdict.md`.

### 핵심 판단

HELIX의 다음 단계는 platform/pack 수 확대가 아니다.

```text
AI proposal
    -> blind evidence verification
    -> constitutional authorization
    -> bounded actuation
    -> impact handback
    -> replayable ledger
```

현재 `HANDOFF-CONDENSE-v0.6-COMPLETE.md`의 historical action은 `RUN_EXPLOIT`지만,
2026-07-11 live `python helix.py status --explore-root . --exploit-root .`는 diversity breach 때문에
`REFRESH_INPUTS`를 반환했다. 이 드리프트가 `HELIX State Receipt`를 먼저 만들어야 하는 직접 근거다.

---

## 2. 정본 문서

1. `.pgf/DESIGN-HELIXDirection.md`
   향후 시스템 방향, Gantree, PPR, T0~T5 phase gate, 불변식.
2. `_workspace/HELIX-direction-report.md`
   현재 상태 실증, 멀티페르소나 합의·충돌, 권고 아키텍처.
3. `_workspace/HELIXDirection_process_plan.md`
   단계별 실행 계획, atomic node, 의존성, 검증, Failure Strategy, Convergence Loop.
4. `HANDOFF-CONDENSE-v0.6-COMPLETE.md`
   이전 Condense v0.6 완료 상태와 historical runbook.

---

## 3. 완료된 첫 작업

```text
DONE: P0_BaselineFreeze
VERDICT: passed
```

### 결과

- `_workspace/helix-direction/baseline.json`
- `_workspace/helix-direction/baseline-report.md`
- canonical commands 모두 exit 0.
- SHA256/byte length 15건 모두 재계산 일치.
- live action `REFRESH_INPUTS`, blocker `diversity_repair_required` 보존.

## 4. 완료된 T0 검증

- Evidence: `_workspace/helix-direction/T0-verification.json`
- Report: `_workspace/helix-direction/T0-verification-report.md`
- PGF status: `.pgf/status-HELIXDirection.json`
- Live action: `REFRESH_INPUTS`
- Receipt hash: `8ea2534ef8904ac7e42142fa0ca3726d372e5db3e1d745a8f668884f33ec67f7`
- T0 verdict: `passed`

## 5. 정확한 다음 작업

```text
NEXT: P7_4_Handoff
MODE: record-and-close
```

HELIXDirection 방향 작업을 종결하는 최종 인수인계 (process plan P7_4 "exact state,
evidence, next task 1개"):

1. HANDOFF.md를 최종 상태로 정리한다: thesis verdict, gate 계보, 산출 인벤토리,
   evidence 색인, blocked 노드 2개(P5_5 승인 대기, P6 조건 미충족)의 재개 조건.
2. `.pgf/status-HELIXDirection.json`과 HANDOFF의 완전 일치를 확인한다.
3. 종결 후 "정확한 다음 작업 1개"를 기록한다 — 후보 판단: 정욱님 결정 사항
   (a) worktree 전체 commit 승인 여부 (미commit 66파일 — 이 방향 작업의 영속화),
   (b) P5_5 외부 pilot 진행 여부. 자율 진행 가능한 작업은 이 방향에는 남아 있지 않다.
4. 전체 gate 최종 1회 (tests + validate + receipt).

T1 강등(autonomous emit 금지) 유지.

---

## 5. 운영 규율

- 한국어로 보고하고 code/command/identifier는 English를 유지한다.
- 한 번에 하나의 gated step을 실행하고 정확한 다음 작업 하나만 남긴다.
- PowerShell 5.1은 사용하지 않는다. Git Bash 또는 지정된 PowerShell 7을 사용한다.
- Python은 PATH의 `python`만 호출한다.
- `git add -A`를 사용하지 않는다. nested repo를 명시적으로 분리한다.
- commit, push, merge, repo 공개는 정욱님이 요청할 때만 수행한다.
- hard gate 실패를 threshold 완화나 문서 표현 변경으로 숨기지 않는다.
- runtime state와 문서가 다르면 runtime evidence를 우선하고 문서를 즉시 동기화한다.

---

## 6. 한 줄 인수인계

> **thesis 확정: GOVERNED INTERNAL SYSTEM — 검증된 결정론 admission control plane을 내부
> runtime으로 보유하되, generator 주장은 강등 유지·제품 주장은 보류. 재상향 조건은 봉인됨.
> 다음은 `P7_4_Handoff` 하나 — 최종 인수인계로 이 방향 작업을 종결한다.**
