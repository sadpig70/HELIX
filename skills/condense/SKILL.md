---
name: condense
description: "Condense — HELIX corpus의 machine-공유 클러스터를 kernel+plugin 플랫폼으로 압축하거나(CONDENSE) 기존 플랫폼의 팩으로 키우는(BUILD_ON_PLATFORM) 메타 스킬. project generator -> platform generator. 클러스터 탐지(mechanism graph) -> 성숙도 게이트 -> machine-aware 라우팅 -> kernel/contract/packs emit -> parity·determinism·zero-kernel-change 게이트. Triggers: condense, 압축, 플랫폼화, platformize, 클러스터 플랫폼, build on platform, 팩으로 추가, kernel plugin, 플랫폼 생성기, project to platform, mechanism graph, 층위 corpus, layered corpus, -stra"
user-invocable: true
argument-hint: "analyze | condense <cluster> | build-on-platform <project> <platform> | status [--layered-corpus PATH]"
depends-on:
  - pg
  - pgf
---

# Condense — HELIX project generator → platform generator

> HELIX는 `explore ⊕ exploit`로 *개별 프로젝트*를 생성한다. corpus는 같은 **machine**을 공유하는
> 클러스터로 스스로 조직화한다. Condense는 그 클러스터를 **kernel+plugin 플랫폼으로 수렴**시키는
> 제3 가닥이다 — 다양성 게이트가 생성 발산을 지키는 것과 대칭으로, **플랫폼 층의 의도적 수렴**.
>
> 실증: Attestra·Clearstra·Routestra는 손으로, **Certstra는 이 레시피로 emit**됨. corpus 규율(설계
> 근거): `_workspace/condense/U1~U5*.md`, `layered-corpus.json`.

---

## 실행 런타임 (모든 에이전트 공통)

런타임 중립. `{SKILL_DIR}` = `skills/condense/`. 슬래시(`/condense`)·frontmatter는 Claude Code 메타데이터.
슬래시가 없으면 모드를 자연어로 지시한다. 참조 데이터는 `_workspace/condense/`의 산출물(아래).

---

## 0. 핵심 명제 & 불변식

**하나의 결정론 커널 + N개 플러그인.** 클러스터의 공유 machine을 커널로 1회 정의하고, 각 프로젝트를
플러그인(팩)으로 얹는다. 3+회 실증한 **지배 불변식**(모두 하드 게이트):

- **Real-code parity anchor** — 레퍼런스 팩이 원본 실코드와 동일 출력 (예: cert-mesh==CertMesh.certify).
- **Zero-kernel-change** — 팩 추가 = 매니페스트+공식 파일만 (`git diff {name}_core` 비어야).
- **Determinism boundary** — 커널·팩 = 순수 stdlib, `now`/`sim` 주입, hash에서 시간 메타 제외.
- **Federate not fuse** — 원본 read-only, `source_project` 태그, 복사·포크 금지.
- **Severity 대수 정렬** — valid/thin/breach ≅ compliant/restricted/violation ≅ certifiable/needs_review/blocked
  (플랫폼 간 조합·증언 가능).

---

## 1. 모드

| 모드 | 트리거 | 동작 |
|---|---|---|
| `analyze` | "분석", "클러스터 탐지" | Mechanism Graph(machine 카탈로그) + Maturity(소스·anchor) + Layered Corpus 산출/갱신 |
| `condense <cluster>` | "플랫폼화", "condense" | **novel-machine** 클러스터 → 새 독립 플랫폼 emit (레시피 §2) |
| `build-on-platform <project> <platform>` | "팩으로 추가" | **machine-covered** 프로젝트 → 기존 플랫폼에 팩 추가 (레시피 §2 축약) |
| `status` | "다음 액션", "제안" | `layered-corpus.json` → CONDENSE/BUILD_ON_PLATFORM 제안 (`helix.py status --layered-corpus`) |

### ★ Machine-aware 라우팅 (필수 결정 규칙)

condense 전에 **반드시** 클러스터의 공유 machine이 기존 플랫폼 커널에 이미 있는지 확인한다:

```
if cluster.shared_machines ⊆ (existing platforms' kernel_machines):
    -> BUILD_ON_PLATFORM  (그 플랫폼에 팩 추가 — 커널 중복 금지)
else (novel machine 존재):
    -> CONDENSE           (새 플랫폼 emit)
```

> 근거(실사례): Compatibility Mesh(SovMesh 등)는 machine이 Attestra의 predicate-gate였다. 순진하게
> CONDENSE하면 커널을 중복 복제한다. machine-aware 라우팅이 이를 BUILD_ON_PLATFORM(sov-mesh 팩)으로
> 교정했다. `core/helix_condense.condense_candidate`가 이 규칙을 코드로 강제한다.

---

## 2. 레시피 (CONDENSE)

정본: `_workspace/condense/U2-condense-recipe.md`. 6 스텝 + canonical 구조.

```
CondenseRecipe(cluster, name):
  1. MachineExtract   공유 machine -> kernel spec. M1(ledger)·M14(fingerprint)·determinism 항상 재사용;
                      나머지는 기존 -stra 커널서 복사(reused) 또는 신규(new) 분리.
  2. ContractSynth    dominant machine -> 팩 stages/계약:
                        verdict-cluster  -> predicate(packet,P)->CheckResult
                        clearing-cluster -> price/priority/payoff/shock_model
                        routing-cluster  -> score(candidate,P) / bounds(telemetry,P)
                        (certify-cluster -> checks(packet,P) / schedule(release,P))
  3. PackProjection   substantiated 프로젝트(Maturity Grade A/B) -> 팩. 원본 read-only, source_project 태그.
                      레퍼런스 팩 = 최고 성숙도(parity 가능) 프로젝트.
  4. PlatformScaffold canonical 구조 emit (독립 git):
                        {name}_core/(determinism·fingerprint·ledger + machine 모듈)
                        {name}_packs/(_base·loader·팩) · {name}_run.py · cli.py
                        schemas/ · tests/ · docs/(ARCHITECTURE·*-CONTRACT·DETERMINISM) · .pgf/ · README · pyproject
                      reused 모듈은 기존 플랫폼서 복사(단일 출처 유지), pgf full-cycle로 신규분 구현.
  5. ParityHarness    레퍼런스 팩 stage 결과 == 원본 실코드 (cross-repo import, 샘플 다수).
  6. DeterminismGate  check_tree({name}_core, {name}_packs).clean == True.
```

### BUILD_ON_PLATFORM (축약)

기존 플랫폼 P에 프로젝트 X 추가: `PackProjection(X, P.contract)` → `{P}_packs/x.py`(매니페스트+공식) +
`schemas/*` → 게이트(parity·determinism·**zero-kernel-change**·tests). 커널 무수정. (예: sov-mesh → Attestra.)

---

## 3. Emit 게이트 (하드 — 실패 시 emit 중단)

```text
G1 zero-kernel-change : 팩 추가가 커널 무수정 (git diff {name}_core empty)
G2 reference-parity   : 레퍼런스 팩 == 원본 실코드 (cross-repo)
G3 determinism-clean  : check_tree clean
G4 tests-green        : unittest discover green
G5 structure-conform  : canonical 구조 준수 (§2.4)
```

---

## 4. 입력·산출물

| 산출물 | 위치 | 역할 |
|---|---|---|
| Mechanism Graph | `_workspace/condense/U1-mechanism-graph.md` | machine 카탈로그(M1~M14) + 클러스터 |
| Maturity Audit | `_workspace/condense/U1-maturity-audit.md` | 소스·anchor 등급(Grade A/B/C) |
| Layered Corpus | `_workspace/condense/layered-corpus.json` | 3-층 레지스트리 + build-on-platform 후보 |
| Recipe | `_workspace/condense/U2-condense-recipe.md` | 6-스텝 정본 |
| 루프 편입 | `core/helix_loop.py`(CONDENSE/BUILD_ON_PLATFORM), `core/helix_condense.py`(어댑터) | `helix.py status` 제안 |

**소스 root**: `D:/HELIX`(9) · `D:/recreate_prj`(exploit) · `D:/IdeaFirst`(explore). parity·PackProjection은
로컬 소스를 읽는다(read-only).

---

## 5. Exemplars (검증된 산출)

| 플랫폼 | 클러스터 | 레퍼런스 anchor | 방식 |
|---|---|---|---|
| Attestra | Governance/Trust | ActionHandbackVerifier | 손 |
| Clearstra | Clearing/Market | CryoFutures | 손 |
| Routestra | Routing/Siting | SkyGrid | 손 |
| **Certstra** | Robotics/Release | CertMesh | **이 레시피로 emit** |
| (Attestra 팩) sov-mesh | Compatibility Mesh | SovMesh | **BUILD_ON_PLATFORM** |

---

## 6. 체크리스트

- [ ] analyze로 클러스터·machine·maturity 최신화
- [ ] **machine-aware 라우팅** 판정 (covered → build-on-platform, novel → condense)
- [ ] 레퍼런스 팩 선정 (Grade A/B, parity 가능)
- [ ] PlatformScaffold: canonical 구조 + reused/new machine 분리
- [ ] 게이트 G1~G5 전부 통과 (하나라도 실패 시 중단)
- [ ] federate: 원본 read-only, source_project 태그, 커널 무수정
- [ ] (선택) ReleaseStrand(`U4-release-strand.md`)로 release-ready → 공개는 user-gated
