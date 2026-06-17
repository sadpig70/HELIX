# HELIX RUNBOOK — repo 하나로 두 시스템 전 기능 실행

> HELIX는 자기완결이다. `skills/`에 IdeaFirst(explore) + recreate(exploit)의 모든 스킬이,
> `scripts/`에 결정론 runner가, `core/`에 통합 백본이, `helix.py`에 루프 드라이버가 있다.
> 스킬은 **AI-native(parser-free)** — 해당 `SKILL.md`를 로드하면 AI 런타임이 그 기능을 수행한다.

## 0. 두 가지 실행 경로

| 경로 | 무엇 | 어떻게 |
|---|---|---|
| **AI-native (주 경로)** | 스킬 기능 (sdx~aox, recreate) | AI 런타임이 `skills/{name}/SKILL.md` 로드 후 모드 실행 (슬래시 또는 자연어) |
| **결정론 runner (선택)** | local emit/검증 | `python scripts/{explore,exploit}/*.py --project-root .` |
| **HELIX 루프 (통합)** | explore↔exploit 한 회전 | `python helix.py status` |

## 1. EXPLORE — IdeaFirst 전 기능 (`skills/`)

| 기능 | 스킬 | 호출 (슬래시 ≡ 자연어) | 산출 |
|---|---|---|---|
| 채널 발굴·카탈로그 | `sdx` | `/sdx bootstrap\|expand\|refresh\|audit` | `.sdx/catalog/` (시드: `seed/sdx-catalog/`) |
| 미보유 직교채널만 | `sdxx` | `/sdxx` | catalog delta |
| 멀티에이전트 카탈로그 통합 | `sdx_ci` | `/sdx_ci union ...` | 통합 카탈로그 |
| 트렌드 수집·분석 | `tcx` | `/tcx full --catalog=.sdx/catalog/index.yaml` | `news.md`, `industry_trend.md` |
| 깊은 인사이트 증류 | `idx` | `/idx distill` | `insight_layered_traced.yaml` (20 인사이트) |
| 미증류 인사이트 조향 | `idxx` | `/idxx` | 증류 steering |
| 혁신 시드 생성 | `cix` | `/cix innovate` | `idea_pool.yaml` (24 시드) |
| 카테고리 white-space 조향 | `cixx` | `/cixx` | 생성 steering |
| 평가·최종선정 | `evx` | `/evx evaluate` | `stage6_final.yaml`, `final_idea.md` |
| 전체 오케스트레이션 | `aox` | `/aox full\|partial\|resume\|dry-run` | `.aox/{run_id}/`, summary |
| GitHub 트렌딩 수집 | `collect_git_trand` | `/collect_git_trand daily\|weekly\|monthly` | MD/JSON/CSV |
| **단독(단일모델) 변형** | `sa-aox`·`sa-icx`·`sa-evx` | `/sa-aox`, `/sa-icx`, `/sa-evx` | `.sa-*/` (production 위장 안 함) |

결정론 runner (선택): `python scripts/explore/aox_full.py --project-root . --mode full`
(`tcx_full_emit.py`, `idx_distill_emit.py`, `cix_manual_emit.py`, `evx_finalize.py`, `sdx_ci.py`, `ledger_lint.py`, `pipeline_index.py` 등 동봉)

## 2. EXPLOIT — recreate 전 기능 (`skills/`)

| 기능 | 스킬 | 호출 | 산출 |
|---|---|---|---|
| 코퍼스→DesignSeed 풀파이프 | `recreate` | `/recreate run [corpus-dir]` | `.recreate/runs/{id}/DESIGN-SEED-*.md` |
| 코퍼스→ProjectGene 인벤토리 | `recreate` | `/recreate map` | `genes.json`, `inventory.md` |
| 후보 생성·차별화·선정 | `recreate` | `/recreate generate [--count N]` | `candidates.md` |
| seed 산출 + pgf 핸드오프 | `recreate` | `/recreate seed [candidate]` | `DESIGN-SEED-{Name}.md` |
| 진행 상태 | `recreate` | `/recreate status` | — |
| pgf+recreate 콤보 | `pgfr-combo` | (스킬 문서 참조) | — |

코퍼스: `seed/corpus/project_list.md` (전체 README는 원본 코퍼스에서 동기 — `recreate` SKILL.md §코퍼스 재료 참조).
결정론 스크립트: `python scripts/exploit/validate_projectgenome.py`, `aggregate_crossmodel.py`.

## 3. 공유 표기 (`skills/{pg,pgf,pgxf}`)

- `pg` — PPR/Gantree 표기 (모든 스킬의 기반 언어)
- `pgf` — 설계/계획/실행/발견/창조 프레임워크 (`pgf/discovery/personas.json` = 14 페르소나, explore 의존)
- `pgxf` — 초대형 PG 인덱스
- DesignSeed/final_idea → **pgf full-cycle**로 구현 위임: `/pgf full-cycle {Name}`

## 4. HELIX 통합 루프 (`core/` + `helix.py`)

```bash
# 한 회전(read): 두 엔진 상태 → 통합 ledger → diversity → 다음 액션
python helix.py status
python helix.py status --explore-root . --exploit-root .   # 라이브(.evx yaml 은 PyYAML 필요)
python helix.py status --sim core.helix_diversity:lexical_sim   # semantic sim 주입(mod:fn)

# ★ 루프 폐쇄(write, actuator): 구현된 winner를 ledger에 기록 + 코퍼스로 환류(염기쌍). idempotent.
python helix.py close-loop --winner winner.json --ledger .helix/ledger.json --corpus .helix/corpus.json
#   winner.json = {"winner": {...}, "source_chain": {...}, "implementation": {project_name,...}}

# 임계값 보정(history → thresholds JSON)
python scripts/calibrate_diversity.py rounds.jsonl --target 0.2 --out thresholds.json

# 백본 직접 사용
python core/helix_validate.py .
python core/helix_fingerprint.py source ADPR ReleaseMesh PnR
python -m unittest discover -s tests -q
```

루프 정책(`core/helix_loop.py`): `RECORD_CONSUMED`(구현 winner→ledger) → `REFRESH_INPUTS`(동질화 시) →
`RUN_EXPLORE`/`RUN_EXPLOIT`(균형). explore winner 구현분은 `winner_to_corpus_entry`로 exploit 코퍼스에 환류(염기쌍).

## 4.5 자율 실행 (문서만 읽고 풀사이클·연속 폐루프)

- **통합 설계도(pg/pgf)**: `docs/DESIGN-HELIX-UNIFIED-PIPELINE.pg.md` — aox·recreate **전 기능을 단일 폐루프로
  파이프라인**한 Gantree+PPR 설계(함수 커버리지 매트릭스 포함). *무엇을 어떻게 파이프라인하는가*.

런타임이 **HELIX를 루트로 두고 문서만 읽어** 자율 수행하려면(*어떻게 수행하는가*):
- **1회 풀사이클 턴**: `docs/INSTRUCTIONS-helix-fullcycle.md` (BASE) — 상태 로드 → `next_action` strand 결정 →
  엔진 파이프라인 → 통합 ledger 게이트 → `pgf full-cycle` 구현 → `helix.py close-loop` actuator → 검증 → (선택) 공개.
- **무중단 연속 폐루프**: `docs/INSTRUCTIONS-helix-loop-autonomous.md` (LOOP) — BASE를 inner turn으로 호출,
  `.helix/loop/loop-state.json` 체크포인트, 다양성 steering·자기진화·공개 가드레일·정지 조건·crash 재개.

## 5. 런타임 디렉토리 (생성물 — gitignore)

`.sdx/ .tcx/ .idx/ .cix/ .evx/ .aox/ .idea-ledger/ .recreate/ .sa-*/` 는 실행 중 HELIX 루트에 생성된다.
durable 시드는 `seed/`에서 복사(예: `seed/sdx-catalog/` → `.sdx/catalog/`).

## 6. 전체 흐름 (한 줄)

```
sdx(채널) → tcx(수집) → idx(인사이트) → cix(아이디어) → evx(선정) ─ final_idea ─┐  [EXPLORE: skills/]
                                                                                  ├─ pgf full-cycle → 새 프로젝트
recreate(코퍼스 재조합) ─ DESIGN-SEED ───────────────────────────────────────────┘  [EXPLOIT: skills/]
        └────── winner→corpus 환류(core/helix_provenance) ──────┘
   ▲ 매 단계 동질화 차단(sdxx/idxx/cixx + core/helix_diversity) · 통합 ledger(core/helix_ledger) · 루프(helix.py)
```
