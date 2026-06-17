# MIGRATION — HELIX 자기완결화 (vendoring 출처·결정 기록)

> HELIX repo 하나로 IdeaFirst + recreate_prj의 모든 기능을 수행하기 위해 두 트리를 vendor한 기록.
> 실행 계획·검증은 `.pgf/{DESIGN,WORKPLAN,status}-HELIX-MONOREPO.*`.

## 출처 (provenance)

| HELIX 위치 | 출처 | 내용 |
|---|---|---|
| `skills/{pg,pgf,pgxf}` | `D:/recreate_prj/.agents/skills` (canonical) | 공유 표기 (1벌, dedup) |
| `skills/{sdx,sdxx,sdx_ci,tcx,idx,idxx,cix,cixx,evx,aox,sa-aox,sa-evx,sa-icx,collect_git_trand}` | `D:/IdeaFirst/.agents/skills` | explore 14 스킬 |
| `skills/{recreate,pgfr-combo}` | `D:/recreate_prj/.agents/skills` | exploit 2 스킬 |
| `scripts/explore/*` | `D:/IdeaFirst/.agents/scripts` | IdeaFirst 결정론 runner 12 + tests |
| `scripts/exploit/*` | `D:/recreate_prj/.agents/scripts` + `ProjectGenome/scripts` | aggregate + validate/concurrency |
| `seed/sdx-catalog/` | `D:/IdeaFirst/.sdx/catalog` | 80채널 카탈로그 (TCX 입력 시드) |
| `seed/idea-ledger/consumed_ideas.yaml` | `D:/IdeaFirst/.idea-ledger` | 소모 ledger 시드 |
| `seed/corpus/project_list.md` | `D:/recreate_prj/_workspace` | recreate 코퍼스 목록 |

## 결정 (decisions)

1. **공유 표기 dedup → recreate_prj canonical (의존성 폐쇄 검증 완료).** pg/pgf/pgxf는 양 트리 중복.
   recreate_prj 버전(pgf v2.5)을 채택했고, **vendored 스킬 전체의 pgf 기계 의존성 폐쇄를 검증**했다:
   - 전 explore 스킬(aox/cix/evx/tcx/idx/sdx/…)이 기계적으로 로드하는 pgf 파일은 **`pgf/discovery/personas.json` 단 하나**
     (`grep -roE "pgf/[^ ]+\.(json|yaml|py)"` 결과) — 이 파일은 **두 트리 동일**(`diff` 확인).
   - 두 트리의 pgf 차이(`SKILL.md`, `agents/pgf-persona-p1..p14.md`, `discovery/loop/reference`)는 **pgf 자신의 discover-mode 산문**이며,
     **어떤 vendored 스킬도 persona `.md`를 기계 로드하지 않는다**(`grep pgf-persona` 결과 0).
   - 결론: recreate_prj pgf는 vendored 스킬 전체의 기계 의존성을 **완전 충족**한다. 차이는 prose-only로 실행 영향 없음
     (재현: `diff <(grep -roE "pgf/[^ ]+\.(json|yaml|py)" skills/) ...` + `diff personas.json`).
2. **fingerprint 중복 금지.** ProjectGenome `fingerprint.py`는 이미 `core/helix_fingerprint.py`로 승격 → vendor 안 함(스킬/스크립트는 core 참조).
3. **recreate canonical = `.agents/skills/recreate`** (idea-layer 포함). 공개 패키징본 ProjectGenome은 미포함(중복 회피; 결정론 스크립트만 차용).
4. **런타임 산출물 미포함.** `.aox/.cix/.sdx(runs)/.idea-ledger(history)` 등 *생성물*은 vendor 안 함(`.gitignore`). 단 *durable 입력/상태*(catalog, ledger 시드)는 `seed/`로 포함.

## 경로 정규화 (B5)

vendored 45개 파일에서 다음을 HELIX 레이아웃으로 치환:
```
.agents/skills/        → skills/
.agents/scripts/       → scripts/explore/
"\.agents" / "skills"  → "skills"          (.py Path 파트)
"\.agents" / "scripts" → "scripts"/"explore"
```
- 검증: 깨진 의존성 참조 0. (남은 `.agents/skills` 1건은 `pgf/evolve-reference.md`의 **일반 설명용 예시** — 의존성 아님.)
- 전체 vendored `.py` py_compile 통과. HELIX 자체 64 테스트 회귀 없음.

## 경계

- 스킬은 **AI-native(parser-free)** — `skills/{name}/SKILL.md`를 로드하면 AI 런타임이 그 기능을 수행한다(주 실행 경로).
- `scripts/`의 결정론 runner는 **선택적 local emit 도구** — HELIX 루트를 project-root로 받아 런타임 산출 디렉토리(`.sdx/.cix/...`)를 생성. seed/는 그 입력 시드.
- HELIX-Core(`core/`)는 두 시스템의 ledger/diversity/provenance를 단일화한 백본 — vendored 스킬의 중복 로직을 대체하는 단일 출처.
