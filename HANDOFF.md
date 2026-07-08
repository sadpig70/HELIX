# HANDOFF — HELIX 작업 연계 (Claude Opus 4.8 → Codex)

> 이 문서 하나 + 링크된 파일들로 이어서 작업할 수 있게 작성했다. 작성 2026-07-07, Codex 갱신 2026-07-08.
> **즉시 할 일: live forward manifest의 `MISSING_ARTIFACT`는 0으로 닫혔다. 다음은 push 후 GitHub CI 상태를 확인한다.**

---

## 0. TL;DR (30초)

- HELIX = 자율 창조 시스템. 이번 세션에 corpus를 **5개 `-stra` 플랫폼(56팩)**으로 완전 라우팅하고,
  루프가 스스로 제안한 CONDENSE로 **5번째 플랫폼 Scorestra**를 emit했다. 전부 public·CI green.
- 그 뒤 **8개 외부 런타임 AI에게 검토**를 받았고(`_workspace/external_runtime_helix_reviews.md`),
  그 통합 분석으로 **차기 업그레이드 방향 v0.6**을 설계했다(`_workspace/new_upgrade_plan2.md`).
- **v0.6 U6~U9 1차 구현 완료.** "human-labeled-machine-aware" 결함을 깨기 위해 M1~M15 결정론
  probe, live 56-pack dataset, static hard gates, probe router, forward prediction scaffold/report, manifest batch
  input, live deferred/future collector, RouteSentinel M16 probe/candidate, EndowFront M17 probe/candidate,
  ADPR M4 candidate, 그리고 남은 7개 후보(AgentPACT/GPOA/MLX/PnR/QVeil/Qvidence/WattMesh)
  normalized candidate를 추가했다.
- 현재 핵심 수치: U6 machine probe `95/95` agreement, U8 router `BUILD_ON_PLATFORM=94 / DEFER=1(M13)`,
  U9 forward prediction fixtures `BUILD_ON_PLATFORM=1 / DEFER=1 / CONDENSE=1`, live collector 후보
  `10`개(`deferred=2`, `future=8`, `BUILD_ON_PLATFORM=8` + `DEFER=2(M16/M17)` +
  `MISSING_ARTIFACT=0`), 전체 `281 tests` green.

---

## 1. 지금 당장 할 일 (다음 단계)

**목표:** push 후 GitHub Actions/CI 상태를 확인하고, 실패하면 로그 기반으로 수정한다.

**첫 3스텝:**
1. `git push` 후 GitHub Actions check run 상태를 확인한다.
2. 실패 시 실패 job log를 읽고 원인별 최소 수정만 적용한다.
3. 수정 후 local gates와 CI를 다시 맞춘다.

**하드 게이트:** `python core/helix_validate.py .` PASS · `python -m unittest discover -s tests -q` PASS ·
`python scripts/condense/machine_probe_dataset.py --out _workspace/condense/U6-machine-probe-report.json` 재생성 ·
`python scripts/condense/collect_forward_candidates.py --out _workspace/condense/U9-live-candidate-manifest.json` 재생성 ·
`python scripts/condense/forward_predict.py --manifest _workspace/condense/U9-live-candidate-manifest.json --out _workspace/condense/U9-live-forward-predict-report.json` 재생성.

---

## 2. 현재 상태 (사실)

### 생태계 (전부 github.com/sadpig70/*, public, CI green)
| 저장소 | 팩 | 로컬 경로 | 비고 |
|---|---|---|---|
| HELIX (허브) | — | `D:\HELIX` | 커널 + Condense v0.5 |
| Attestra | 23 | `D:\HELIX\Attestra` | predicate 게이트 |
| Clearstra | 12 | `D:\HELIX\Clearstra` | 청산/가격 |
| Routestra | 11 | `D:\HELIX\Routestra` | 라우팅/bound |
| Certstra | 5 | `D:\HELIX\Certstra` | 인증 (Condense emit #1) |
| Scorestra | 5 | `D:\HELIX\Scorestra` | 스코어링 M15 (Condense emit #2) |
| stra-demo | — | `D:\HELIX\stra-demo` | 생태계 데모 |

- corpus 라우팅 완결: `build_on_platform_candidate()` · `condense_candidate()` 둘 다 **None**.
  (흡수 20 / defer 2[RouteSentinel·EndowFront] / design-only 8)
- Mechanism Graph **M1~M15**는 `docs/MACHINE-GRAPH.md`로 승격됨. 모든 M1~M15는
  `core/helix_machine_probes.py` probe에 대응한다.
- U6 live dataset: `scripts/condense/machine_probe_dataset.py`, report
  `_workspace/condense/U6-machine-probe-report.json` = `implemented_probe_cases=95`, `matched/scored=95/95`,
  `agreement=1.0`.
- U7 hard gates in `core/helix_validate.py`:
  - determinism static gate: runtime boundary에서 `requests`/`urllib`/`socket`/`random`/`datetime.now`류 차단.
  - zero-kernel gate: `seed/condense/platform-kernel-lock.json`으로 5개 `-stra` `*_core/` 해시 잠금.
  - machine-probe gate: `seed/condense/machine-probe-gate.json`으로 U6 `95/95` 고정.
- U8 router:
  - `core/helix_router.py`가 probe-positive machine을 `kernel_machines` + live pack evidence로 라우팅.
  - current summary: `BUILD_ON_PLATFORM=94`, `DEFER=1`, `deferred_machines={"M13": 1}`.
  - hard gate: `seed/condense/router-gate.json`.
- U9 forward prediction:
  - `scripts/condense/forward_predict.py`.
  - fixtures: `examples/condense/candidate-scorestra-m15.json`, `candidate-m13-defer.json`,
    `candidate-m13-condense.json`.
  - manifest batch input: `examples/condense/forward-predict-manifest.json`, schema
    `helix-forward-predict-manifest/1.0`.
  - live collector: `scripts/condense/collect_forward_candidates.py` →
    `_workspace/condense/U9-live-candidate-manifest.json`.
  - live artifact catalog: `seed/condense/forward-candidate-artifacts.json`.
  - normalized live future artifacts:
    `candidate-adpr-m4.json` -> `M4 / Attestra`,
    `candidate-agentpact-m1.json` -> `M1 / Attestra`,
    `candidate-gpoa-m15.json` -> `M15 / Scorestra`,
    `candidate-mlx-m3.json` -> `M3 / Attestra`,
    `candidate-pnr-m15.json` -> `M15 / Scorestra`,
    `candidate-qveil-m3.json` -> `M3 / Attestra`,
    `candidate-qvidence-m4.json` -> `M4 / Attestra`,
    `candidate-wattmesh-m9.json` -> `M9 / Routestra`.
  - RouteSentinel source artifact: `examples/condense/candidate-routesentinel-m16.json` from
    `.recreate/runs/001-action-handback-verifier/genes.json`.
  - EndowFront source artifact: `examples/condense/candidate-endowfront-m17.json` from
    `github.com/sadpig70/endowfront`.
  - report: `_workspace/condense/U9-forward-predict-report.json` = `all_ok=True`,
    summary `{"BUILD_ON_PLATFORM": 1, "CONDENSE": 1, "DEFER": 1}`.
  - live report: `_workspace/condense/U9-live-forward-predict-report.json` =
    `{"BUILD_ON_PLATFORM": 8, "DEFER": 2}` after closing all normalized live artifacts.
  - hard gate: `seed/condense/forward-predict-gate.json`.

### git 상태
- **로컬 HELIX 브랜치 = `main`** (origin/main과 동기, 최신 커밋 `docs: add OVERVIEW.md`). feature 브랜치 없음.
- HELIX PR #1~#11 전부 병합됨. 현재 Codex 작업은 아직 미커밋이며, `core/`, `scripts/condense/`,
  `tests/`, `docs/`, `examples/condense/`, `seed/condense/*-gate.json`에 걸쳐 있음. 커밋/푸시는 사용자 승인 전 금지.
- **각 플랫폼은 독립 git repo**(D:\HELIX 하위, 각자 origin). HELIX `.gitignore`가 `/Attestra/`~`/Scorestra/`
  등 18개 nested repo를 무시 → HELIX에 embed되지 않음.

---

## 3. 운영 환경 & 필수 규칙

### 환경
- OS: Windows. 셸: **Git Bash**(POSIX sh) 주. PowerShell 7(`D:\Tools\PS7\...`, UTF-8) 가용. **PS 5.1 금지**(인코딩).
- Python: `python`(PATH). **절대경로 인터프리터 호출 금지.** `python -` heredoc에서 Windows 경로(`D:/HELIX/...`)
  사용(git-bash `/d/HELIX/...`는 Python이 이해 못 함).
- `gh` CLI: `workflow` 스코프 있음(이번 세션에 추가). GitHub 작업 가능.

### 결정론 경계 (지배 불변식 — 절대 위반 금지)
- 커널(`*_core/`)·팩 = **순수 stdlib, 시계/네트워크/AI 없음**. 시간은 `now` 주입, hash에서 시간 메타 제외.
- **AI/LLM/휴리스틱은 전부 "메타층"**(경계 밖). v0.6에서도: **AI는 proposal, 결정론 gate가 판정**.
- 팩 추가는 커널을 건드리면 안 됨(**zero-kernel-change**). novel machine만 CONDENSE로 새 커널.
- 각 팩은 원본과의 **parity 테스트** 동봉(소스 있으면 실행, CI에선 현재 skip — v0.6 U7이 이걸 강제로 바꿈).

### 검증 (작업 후 항상)
```bash
cd /d/HELIX
python core/helix_validate.py .              # 구조/계약/예제 PASS
python -m unittest discover -s tests -q       # 현재 281 tests
python scripts/condense/machine_probe_dataset.py --out _workspace/condense/U6-machine-probe-report.json
python scripts/condense/forward_predict.py --gate seed/condense/forward-predict-gate.json \
  --layered-corpus seed/condense/layered-corpus.json \
  --out _workspace/condense/U9-forward-predict-report.json
python scripts/condense/forward_predict.py --manifest examples/condense/forward-predict-manifest.json \
  --out _workspace/condense/U9-forward-predict-report.json
python scripts/condense/collect_forward_candidates.py \
  --out _workspace/condense/U9-live-candidate-manifest.json
python scripts/condense/forward_predict.py --manifest _workspace/condense/U9-live-candidate-manifest.json \
  --out _workspace/condense/U9-live-forward-predict-report.json
# 플랫폼 작업 시 해당 repo에서:
cd /d/HELIX/<Platform> && python -m unittest discover -s tests -q && python cli.py determinism
```

### git / 커밋 규칙
- 커밋·푸시는 **사용자가 요청할 때만**. main에서 작업 중이면 대규모 feature는 브랜치 먼저.
- **outward-facing(게이트, 승인 필수):** GitHub 저장소 공개(`gh repo create`), main 병합/PR merge,
  브랜치 삭제, 원격 push. — 사용자 승인 없이 하지 말 것.
- 로컬 코드·테스트·문서 작성은 자율 진행 가능.
- 커밋 메시지 co-author 라인: 각 런타임 자신의 것으로. (이전 커밋들은
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` 사용.)
- **`git add -A` 금지**(HELIX에서): nested repo가 embedded gitlink로 잘못 들어감. **명시 경로만 add.**

---

## 4. 핵심 참고 파일 (읽는 순서)

1. **`_workspace/new_upgrade_plan2.md`** ★ — v0.6 설계 전문(목표·아키텍처·단계·성공/철회 기준·리뷰 반영 매트릭스). **작업의 기준 문서.**
2. **`_workspace/external_runtime_helix_reviews.md`** — 8개 외부 AI 리뷰 원문(비판 근거).
3. `docs/OVERVIEW.md` — HELIX 현황 브리핑(외부 검토용 단일 진입점).
4. `docs/CONDENSE.md` — Condense 상세 + machine-aware 라우팅 실사례.
5. `docs/MACHINE-GRAPH.md` — M1~M15 정의, U6/U8/U9 probe/router/forward-predict 계약.
6. `seed/condense/layered-corpus.json` — platform coverage registry(`kernel_machines`) + routed corpus 상태.
7. `core/helix_machine_probes.py` · `scripts/condense/machine_probe_dataset.py`.
8. `core/helix_router.py` · `scripts/condense/forward_predict.py` · `helix.py`.
9. `core/helix_validate.py` · `seed/condense/*-gate.json`.
10. corpus 소스 루트: `D:/HELIX`(9) · `D:/recreate_prj`(exploit) · `D:/IdeaFirst`(explore, 실코드 다수).

---

## 5. 함정 (Gotchas — 시간 절약)

- **nested repo:** D:\HELIX 하위 플랫폼/프로젝트 18개는 각자 독립 git repo. HELIX에서 `git add -A`하면
  깨진 gitlink. 명시 경로만. (자세히: `memory` 또는 커밋 히스토리 `Decouple vendored corpus repos` 참고)
- **브랜치 staleness:** HELIX 문서를 main에 직접 커밋하는 패턴 때문에, 로컬이 뒤처진 작업 브랜치에 있으면
  파일이 "없어" 보인다. 지금은 로컬=main으로 정렬해 둠. feature 작업 시 브랜치 만들고 커밋을 그 브랜치에 일관되게.
- **parity CI-skip:** 원본이 vendored 아니라 CI에서 parity 전부 skip. U7에서 이를 완전히 CI 해결하지는 않았고,
  대신 HELIX 로컬 hard gate(`machine-probe`, `router`, `forward-predict`)로 결정론 acceptance surface를 세웠다.
- **layered-corpus.json은 수작업:** `(done)`/`(deferred:...)`/`(design-only)` 마커가 사람 판정.
  `build_on_platform_candidate()`는 `(`가 든 항목을 skip. — v0.6가 이 라벨을 프로브-검증으로 대체.
- **리뷰가 본 스냅샷과 현재 차이:** 에이전트 8의 "Scorestra 5/5는 거짓(live 1/5)" 지적은 **이미 해소**됨
  (현재 5팩 전부 완성: pqc-exposure·loop-kit·lazaretto-risk·detour-posture·field-posture). 플랜 §0 참고.
- **M11 정책:** `M11`은 Attestra kernel로 승격하지 않는다. `policy-drift` pack에서 실증된
  `pack_evidence` coverage로만 라우팅한다. `M13`은 live `-stra` pack coverage가 없어 현재 `DEFER`.
- **M16 정책:** `M16`은 RouteSentinel-style route deviation + rollback restoration simulation으로만 좁게
  정의했다. generic simulator로 넓히지 말 것. 현재 covered platform이 없어 `DEFER`.
- **M17 정책:** `M17`은 EndowFront-style one-time endowment corpus projection + sustainability/open-access
  verdict로만 좁게 정의했다. generic finance/pricing으로 넓히지 말 것. 현재 covered platform이 없어 `DEFER`.
- **manifest report semantics:** oracle 없는 manifest row는 `expectation="none"`이고 `ok=True`로 기록한다.
  hard gate로 쓰려면 `seed/condense/forward-predict-gate.json`처럼 `action`/`platform`을 명시한다.
  `missing_artifact=true` row는 `MISSING_ARTIFACT`로 report되며 probe를 실행하지 않는다.
- **relative `--out` 주의:** `scripts/condense/*`는 nested repo sample 실행 중 CWD를 바꿀 수 있다.
  현재는 테스트로 잡혀 있지만, 리포트 생성/검증은 가능하면 한 명령 안에서 순차 실행한다.

---

## 6. 작업 진행 방식 (사용자 선호)

- 사용자(정욱님)는 **한 번에 한 gated step**을 선호: 작업 실행 → 검증(테스트/CI 근거 제시) → 보고 →
  **다음 최우선 작업 1개 제시**. 자율 루프 지시("멈출 때까지 반복")를 받으면 승인 대기 없이 이어가되,
  **outward-facing은 게이트**. 한국어 대화, 코드/명령/식별자는 영어.
- 정직하게: 테스트 실패면 실패라고, 억지 매핑(force-fit) 금지, parity 없는 흡수 금지.

---

## 7. 한 줄 인수인계

> **U6~U9, manifest batch input, live candidate collector, RouteSentinel M16 normalization, EndowFront M17
> normalization, ADPR M4 normalization, 남은 7개 future 후보 normalization은 구현·검증 완료.
> 다음은 GitHub push 후 CI 상태를 확인하라.** 결정론 경계·zero-kernel-change·hard gates를 유지하고,
> GitHub 공개/병합은 사용자 승인 게이트로 남겨라.
