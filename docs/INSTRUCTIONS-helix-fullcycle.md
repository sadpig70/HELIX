# INSTRUCTION — HELIX one full-cycle turn (explore⊕exploit → implement → close-loop → publish)

> HELIX를 **루트 워크스페이스**로 둔 어떤 AI 런타임(codex / kimi / gemini / grok / Claude Code / Fable 등)이
> **이 문서와 `skills/`·`core/`·`helix.py`만 읽고** 한 번의 HELIX 턴을 자율 수행할 수 있게 한 영속 지시문이다.
> 한 턴 = "상태 로드 → strand 결정 → 엔진 파이프라인 → 통합 ledger 게이트 → pgf 구현 → **close-loop(실제 ledger/corpus 쓰기)** → 검증 → (선택) 공개".
> 연속 무중단 반복은 [`INSTRUCTIONS-helix-loop-autonomous.md`](./INSTRUCTIONS-helix-loop-autonomous.md)(LOOP)가 이 문서를 inner turn으로 호출한다.

---

## 0. 환경·규약 (먼저 읽어라)

- 작업 루트: HELIX repo 루트(`.../HELIX`). Python은 경로 없이 `python`. UTF-8. 한국어 대화 / 코드·명령·식별자는 영어.
- **자기완결**: 외부 경로 의존 없음. 모든 스킬은 `skills/`에 vendor돼 있다 — 진입 전 다음을 읽는다:
  - `skills/pg/` (PG 표기 — Gantree/PPR/AI_/→/[parallel], parser-free) · `skills/pgf/` (실행 모드 design/plan/execute/verify/full-cycle/review)
  - **EXPLORE 엔진**: `skills/{sdx,sdxx,sdx_ci,tcx,idx,idxx,cix,cixx,evx,aox,sa-aox,sa-evx,sa-icx,collect_git_trand}/SKILL.md`
  - **EXPLOIT 엔진**: `skills/recreate/SKILL.md` (+ `reference/6종`), `skills/pgfr-combo/`
  - **백본**: `core/` (helix_ledger·helix_diversity·helix_provenance·helix_loop·helix_fingerprint·helix_validate), 드라이버 `helix.py`. 계약은 `docs/SUBSTRATE-CONTRACT.md`.
- **결정론 경계 (불가침)**: `core/`+`engines/`는 순수 stdlib(시계·네트워크·AI 없음, `now`/`sim` 주입). wall-clock은 **`helix.py` CLI 엣지에서만**(`--now` 주입 우선). 엔진 내부 LLM 단계는 **메타층**. exploit 생성물 verdict 경로는 결정론 불변.
- **단일 출처**: 재사용 차단·다양성·계보는 `core/` 백본이 정본이다. 엔진별 native 저장소(`.idea-ledger/`, `.recreate/registry.json`)는 **백본으로 투영**해 쓴다(중복 판정 금지).

## 1. 동적 상태 로드 (Dynamic Resolution — 하드코딩 금지)

실행 즉시 백본으로 현재 상태를 도출한다(문서·메모리 신뢰 금지):
```bash
python helix.py status --json
```
산출(JSON)에서 읽는다: `ledger_size`, `ledger_origins{explore,exploit}`, `pool_size`, `diversity{triggered,repair_required,sim_kind,breaches,signals}`, `winner{winner_id,title,already_consumed,lineage}`, `corpus_feedback[]`(구현된 explore winner→코퍼스), **`next_action{action,why[,target]}`**.
- 통합 ledger는 explore(`.evx/.cix/.idea-ledger`) + exploit(`.recreate/registry.json`)를 `engines.unify.build_unified_ledger`로 병합한 것이다(full `is_consumed` 계약 dedup).
- `semantic` 등급이 필요하면 `--sim module.path:function`으로 임베딩 sim을 주입(없으면 결정론 `lexical` 기본).

## 2. strand 결정 — `next_action`을 따른다

백본 `core/helix_loop.next_action`이 결정론으로 이번 턴의 행위를 정한다:

| next_action | 의미 | 이번 턴 |
|---|---|---|
| `RECORD_CONSUMED` | 구현된 winner가 ledger 미기록 | **§6 close-loop만 수행**(루프 폐쇄) 후 턴 종료 |
| `REFRESH_INPUTS` | `diversity.repair_required`(동질화/island collapse) | **§3 생성 전** `target` strand 입력 갱신(아래) 후 생성 |
| `RUN_EXPLORE` | 코퍼스 미성숙 또는 균형 회전 | §3 EXPLORE 파이프라인 |
| `RUN_EXPLOIT` | 신선 자산 누적 → 재조합 복리 | §3 EXPLOIT 파이프라인 |

**REFRESH_INPUTS 배선(복구효소 = 5점 다양성 게이트)**: `target=explore`면 채널/인사이트/카테고리를 갱신 — `/sdxx`(미보유 직교채널) → `/idxx`(미증류 인사이트) → `/cixx`(white-space 카테고리). `target=both`면 exploit측 회피(vocab/registry)도 강화. 근거는 `diversity.signals.breached` + `unique_ratio_below_floor`.

## 3. 엔진 파이프라인 실행 (winner 1개 산출)

### 3A. EXPLORE (가닥 A · IdeaFirst) — `next_action ∈ {RUN_EXPLORE, REFRESH_INPUTS:explore}`
`skills/aox/SKILL.md`의 오케스트레이션을 따라 `sdx → tcx → idx → cix → evx`를 수행한다(또는 단독환경이면 `sa-icx`/`sa-evx`로 교체 — aox `environment_capability_check`).
- 입력 시드: `seed/sdx-catalog/`(80채널), `seed/idea-ledger/consumed_ideas.yaml`. 런타임 산출은 `.sdx/.tcx/.idx/.cix/.evx/`(루트, gitignore).
- REFRESH면 위 sdxx/idxx/cixx 조향을 선적용.
- **산출 winner**: `.evx/latest/stage6_final.yaml`의 `consensus_winner`(+`innovation_winner`) + `final_idea.md`, 계보 `manifest.yaml.inputs`(cix→idx→tcx→sdx).

### 3B. EXPLOIT (가닥 B · recreate) — `next_action ∈ {RUN_EXPLOIT, REFRESH_INPUTS:exploit/both}`
`skills/recreate/SKILL.md` 파이프라인(Phase0~6)을 수행한다: 코퍼스(`seed/corpus/` + 구현된 explore winner 환류분) → 3축 ProjectGene → 3경로×8도구 후보 → 회피/차별화/선정/실증 → `DESIGN-SEED-{Name}.md`.
- 코퍼스에는 §6에서 환류된 explore winner(`origin=explore` 코퍼스 entry)가 포함된다 — **염기쌍**이 exploit 재료가 된다.
- 과밀어휘 금지, `parts≥2`, 정본 `skills/recreate/reference/*`.

### 공통: 백본 다양성 측정
생성 후보 pool로 `core/helix_diversity.measure_diversity`를 재확인(또는 `helix.py status` 재실행). `repair_required`면 island 재발산/조향 후 재생성(`skills/{sdxx,idxx,cixx}` 또는 recreate avoidance).

## 4. 통합 ledger 게이트 (★ 단일 출처 재사용 차단)

winner를 **엔진 자기 ledger가 아니라 통합 ledger**로 검사한다:
```python
from core.helix_ledger import is_consumed
# unified = engines.unify.build_unified_ledger(explore_ledger, exploit_ledger)
hit = is_consumed({"idea_id": W.id, "title": W.title, "sources": [...], "aliases":[...], "semantic_family": ...}, unified)
```
`hit.consumed`면(idea_id/normalized_title/aliases/semantic_family/source_fingerprint/generated_fingerprint 중 하나라도 충돌) → **이 winner 폐기**, §3으로 롤백해 재조향(REFRESH) 후 재생성. (cross-engine 중복도 여기서 잡힌다 — `helix.py status`의 `winner.already_consumed`와 동치.)

## 5. 구현 — pgf full-cycle --with-review

신선 winner(final_idea 또는 DesignSeed)를 DESIGN 입력으로 `skills/pgf` full-cycle을 돈다:
```
pgf full-cycle {Name} --with-review
```
산출 `.pgf/{DESIGN,REVIEW,WORKPLAN,VERIFY,status}-{Name}.*` + 프로젝트 `{Name}/`(단일 모듈 stdlib + README + LICENSE(MIT) + examples/3 + tests/≥10 + .gitignore). 구현 컨벤션·verify 게이트는 recreate BASE와 동형(결정론 verdict / hash-chain ledger 선택 / cli_triplet).
- **REVIEW 게이트**: `Critical=0, High≤2`면 plan 진행, 아니면 DESIGN revise(`skills/pgf/reference/design-review-reference.md`).

## 6. ★ 루프 폐쇄 (actuator — 실제 ledger/corpus 쓰기)

구현이 끝나면 백본 actuator로 **루프를 실제로 닫는다**(이게 HELIX를 보고서가 아닌 컨트롤러로 만든다). idempotent.
```bash
python helix.py close-loop --winner winner.json \
  --ledger .helix/ledger.json --corpus .helix/corpus.json [--now <injected-date>]
```
`winner.json` = `{"winner": {"id","title"[,"aliases","semantic_family"]}, "source_chain": {...}, "implementation": {"project_name","project_path","repo_url"}}`.
동작: `evx_winner_to_consumed_entry → is_consumed(통합) → append_consumed(ledger) → winner_to_corpus_entry → corpus append`. 반환 `closed`(신규) 또는 `already_recorded`(재실행).
- explore winner는 이로써 **exploit 코퍼스 source**가 된다(다음 EXPLOIT 턴의 재료 — base-pairing).
- 엔진 native 저장소(`.idea-ledger`/`registry`)도 그 엔진의 BASE 절차대로 자기 엔트리를 갱신한다(자기 엔트리 한정).

## 7. 검증 게이트 — GATE-EVIDENCE (자기보고 신뢰 금지)

`status`에 `passed`라 적기 전에 **실제 명령을 실행하고 그 출력**을 증거로 남긴다:
- 백본 무결성: `python -m unittest discover -s tests`(→OK) · `python core/helix_validate.py .`(→PASS) · `python -m compileall -q core engines helix.py`.
- 구현 프로젝트: `python -m py_compile {mod}.py tests/*.py` · `python -m unittest discover -s tests`(OK) · `python {mod}.py sample`(verdict 전부 출력) · `examples/*.json` 전부 `json.load` 성공 · 동일입력 2회 일치.
- 모든 항목을 `.helix/runs/{turn_id}/GATE-EVIDENCE.json`(필드 `command/cwd/exit_code/stdout_excerpt/stderr_excerpt/passed/artifact_checked`)에 기록. **전부 `passed:true`가 아니면 공개 금지**(seed-only로 강등, 루프는 계속).

## 8. (선택) GitHub 공개 — 가드레일

`policy.publish`가 참이고 §7 전부 통과일 때만:
- **idempotency 선검사**: `gh repo view sadpig70/{Name}` — 없으면 `gh repo create sadpig70/{Name} --public --source=. --remote=origin --push`, 있으면 **재생성 금지, push/reconcile만**(삭제·force-push 금지).
- topics + `--description`. 누출 0 재확인(타 런타임 식별자·미공개 내부명·PII 0).
- 실패 시 seed-only 유지.

## 9. 불변식 & 게이트 (반드시)

- **원본 불변**: `skills/`·`core/`·`engines/`·vendor된 스킬·기존 `.pgf` 정본·과거 run 산출을 **수정 금지**. 이번 턴은 **새 run/새 프로젝트/`.helix/` 상태만** 추가(자기 엔트리 status 전이는 허용).
- **단일 출처 게이트**: winner는 **통합 ledger** `is_consumed`로 검사(§4). 엔진 자기 ledger만 보고 통과시키지 말 것.
- **결정론·stdlib·누출0·parts≥2(exploit)**: 불가침. core/engines에 시계·난수·외부의존 0(시계는 CLI 엣지만).
- **REFRESH는 생성 전**: `repair_required`면 K를 늘리지 말고 sdxx/idxx/cixx·island 재발산으로 입력 갱신 후 생성.

## 10. 산출물 체크리스트 (한 턴)

- [ ] `helix.py status --json` 로 로드한 `next_action`에 따른 strand 수행
- [ ] (REFRESH) sdxx/idxx/cixx 또는 recreate 회피 조향 적용 근거 기록
- [ ] winner가 **통합 ledger** `is_consumed` 통과(아니면 폐기·재생성)
- [ ] `.pgf/{DESIGN,REVIEW,WORKPLAN,VERIFY,status}-{Name}.*` + `{Name}/`(모듈·README·LICENSE·examples/3·tests≥10 OK)
- [ ] `python helix.py close-loop ...` → `closed`/`already_recorded` (ledger+corpus 갱신; explore→corpus 환류)
- [ ] `.helix/runs/{turn_id}/GATE-EVIDENCE.json` (전부 passed:true)
- [ ] (공개 시) `https://github.com/sadpig70/{Name}` (PUBLIC, topics) — idempotency 선검사 후
- [ ] `.helix/HANDOFF.md`에 턴 기록(strand·winner·repo·게이트 결과). 성공/seed-only/실패 모두 사유와 함께.
