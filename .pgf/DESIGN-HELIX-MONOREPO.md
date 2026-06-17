# DESIGN-HELIX-MONOREPO — 자기완결 단일 repo (PGF design)

> 목표(정정): **HELIX repo 하나로 IdeaFirst의 모든 기능 + recreate_prj의 모든 스킬 기능을 수행**한다.
> → 직전의 "federate(참조)"가 아니라 **vendor(전부 포함)**가 정답. 단, 안에서는 공유 substrate(HELIX-Core)를
> 단일 출처로 두어 desync를 막는다 — *패키징은 융합, 로직은 단일출처*.

## 0. 근거 (인벤토리)

| 트리 | 고유 스킬 | 공유 표기 | 스크립트 | 런타임 산출 |
|---|---|---|---|---|
| IdeaFirst (.agents, 121f/1.7M) | sdx·sdxx·sdx_ci·tcx·idx·idxx·cix·cixx·evx·aox·sa-aox·sa-evx·sa-icx·collect_git_trand (14) | pg·pgf·pgxf | 12 py + tests | .aox/.cix/.sdx/.idea-ledger … |
| recreate_prj (.agents, 52f/501K) | recreate·pgfr-combo (2) | pg·pgf·pgxf (중복) | aggregate ×2 | .recreate |

- pg·pgf·pgxf는 **양 트리 중복** → HELIX에 **1벌만**(dedup). pgf 파일구조 동일, `pgf/discovery/personas.json`(aox/cix 의존) 양쪽 존재 → 보존.
- `.agents/skills` 경로참조 **36개 파일** → `skills/`로 정규화(B5).
- 런타임 산출(.aox 등)은 **생성물** → vendor 안 함(gitignore). 단 **durable 입력/상태**(sdx catalog, consumed ledger)는 `seed/`로 포함.

## 1. 타깃 레이아웃 (단일 `skills/` 네임스페이스)

```
HELIX/
├── skills/                  # ★ ALL 스킬 — 단일 평면 (각 트리 .agents/skills 미러 → skills/{name}/ 참조 유효)
│   ├── pg/ pgf/ pgxf/       #   공유 표기 (canonical 1벌, dedup)
│   ├── sdx/ sdxx/ sdx_ci/ tcx/ idx/ idxx/ cix/ cixx/ evx/ aox/    # explore(IdeaFirst)
│   │   sa-aox/ sa-evx/ sa-icx/ collect_git_trand/
│   └── recreate/ pgfr-combo/                                      # exploit(recreate_prj)
├── scripts/                 # 결정론 스크립트 (explore/ exploit/ 하위로 출처 분리)
│   ├── explore/             #   aox_full.py, tcx_full_emit.py, evx_finalize.py … (12) + tests
│   └── exploit/             #   aggregate_crossmodel*.py + ProjectGenome validate/concurrency
├── seed/                    # durable 입력/상태 (생성물 아님 — 재현용)
│   ├── sdx-catalog/         #   80채널 카탈로그 (.sdx/catalog) — TCX 입력
│   ├── idea-ledger/         #   consumed_ideas.yaml (소모 ledger 시드)
│   └── corpus/              #   recreate 코퍼스 (project_list + README 집합 or 포인터)
├── core/                    # ★ HELIX-Core 백본 — 단일 출처 결정론 substrate [이미 구현]
├── engines/                 # 어댑터 — vendored 스킬 ↔ core 배선 [이미 구현]
│   ├── explore/adapter.py   exploit/adapter.py  unify.py  loaders.py
├── helix.py                 # 드라이버 (한 회전: 상태→통합 ledger→diversity→next_action) [이미 구현]
├── schemas/  docs/  examples/  tests/   [이미 구현]
├── RUNBOOK.md               # ★ "HELIX 하나로 두 시스템 모든 기능 실행하는 법" (B6)
└── .pgf/                    # 설계·계획·상태·PGXF 인덱스
```

## 2. dedup / canonical 규칙

- **pg·pgf·pgxf**: recreate_prj 버전을 canonical로 채택(이번 세션에서 active 유지, pgf v2.5). 단 B1에서
  IdeaFirst 버전과 **content diff**를 떠 실차이가 있으면 보고·병합(특히 `pgf/discovery/personas.json`).
- **결정론 identity**: ProjectGenome `fingerprint.py`는 이미 `core/helix_fingerprint.py`로 승격 → 중복 vendor 금지(스킬은 core 참조).
- **ProjectGenome vs .agents/skills/recreate**: 로컬 `.agents/skills/recreate`(idea-layer 포함, 7파일)를 canonical로 vendor. ProjectGenome(공개 패키징본)은 별도 — 포함 안 함(중복).

## 3. 경로 정규화 규칙 (B5)

```
.agents/skills/{x}      →  skills/{x}            # 36개 파일
.agents/scripts/{y}     →  scripts/explore/{y}   # IdeaFirst 스크립트 참조
{SKILL_DIR}             →  (불변 — 런타임 상대경로 placeholder, 그대로 동작)
.sdx/catalog (입력)     →  seed/sdx-catalog (또는 런타임 생성 — 문서에 양쪽 명시)
```

## 4. 결정론 경계 (불변)

- HELIX-Core = 순수 결정론(stdlib, now/sim 주입). [유지]
- 엔진 스킬 내부 LLM 단계 = 메타층(각 SKILL.md 정본). vendor해도 경계 불변.
- exploit 생성물 verdict 경로 = 결정론 불변.

## 5. 완료 기준 (acceptance)

```text
MonorepoAcceptance
    AllSkillsVendored   // 16 고유 스킬 + 공유 pg/pgf/pgxf(1벌) 존재
    NoDanglingRefs      // '.agents/skills' 참조 0 (전부 skills/로 정규화)
    PersonasReachable   // skills/pgf/discovery/personas.json 존재 (aox/cix 의존)
    ScriptsVendored     // explore 12 + exploit 스크립트 존재
    SeedStatePresent    // sdx-catalog + idea-ledger 시드 존재
    CoreUnchanged       // 기존 core/engines/tests 64 green 유지
    RunbookComplete     // RUNBOOK.md 가 두 시스템 전 기능 호출법 매핑
    SelfContained       // HELIX 외부 경로 의존 0 (runtime placeholder 제외)
```
