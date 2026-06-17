# rerun-avoidance — 재실행 격리 · 레지스트리 · 회피

> Recreate 재실행 안전의 정본. `run` 모드가 반복 실행될 때 산출물 격리 + 소비 이력 추적 + 중복 회피.
> 출처: codex 제안(`_workspace/recreate_rerun_registry_avoidance.md`)을 `.pgf/REVIEW-RerunRegistry.md`의
> 검토로 다듬은 최종안 (수정 M1~M3 반영).

---

## 1. 왜 필요한가 (4문제)

1. **산출물 충돌** — flat `.recreate/genes.json` 등을 재실행이 덮어쓴다.
2. **추적 불명** — 어떤 seed가 어떤 `.pgf/`·구현으로 이어졌는지 흐려진다.
3. **소비 이력 부재** — 다음 run이 같은 source 조합·같은 문제를 다시 만든다.
4. **코퍼스 오염** — 생성된 프로젝트 폴더가 다음 run의 코퍼스 스캔에 섞인다.

코퍼스가 작아서(48개) 3·4가 특히 실재한다.

---

## 2. 디렉터리 계약 (run-scoped)

```text
.recreate/
    latest.json              # 최신 run 포인터 (symlink 미사용)
    registry.json            # run을 넘어 누적되는 durable 기억
    runs/
        {run_id}/            # 불변 — 덮어쓰기 금지, 수정은 새 run으로
            input_manifest.json
            genes.json
            inventory.md
            candidates.md
            avoidance_report.md
            DESIGN-SEED-{Name}.md
            status.json
```

**run_id 규칙 (M2 — 결정론).** `{NNN}-{winner-slug}` 시퀀스. 예: `001-withheld-action-witness`.
- timestamp 자동생성(`Date.now`류) **금지** — PG 결정론 원칙. 정렬·재현 가능한 시퀀스 사용.
- winner가 정해지기 전 임시 run은 `{NNN}-pending`, seed 산출 후 rename.
- 날짜가 필요하면 세션 컨텍스트 날짜를 **입력으로** 받아 메타에만 기록.

---

## 3. 파일 계약

### 3.1 `latest.json`
```json
{
  "latest_run_id": "001-withheld-action-witness",
  "latest_run_path": ".recreate/runs/001-withheld-action-witness",
  "winner": "WithheldActionWitness",
  "seed_path": ".recreate/runs/001-withheld-action-witness/DESIGN-SEED-WithheldActionWitness.md"
}
```

### 3.2 `registry.json` (durable)
```json
{
  "schema_version": "1.0",
  "updated_at": "2026-06-12",
  "corpus_baseline": { "project_count": 48, "source": "_workspace/project_list.md" },
  "source_projects": {
    "PnR": { "use_count": 1, "used_by": ["WithheldActionWitness"],
             "roles": ["absence scoring"], "last_used_run": "001-withheld-action-witness",
             "last_reuse_cost": "parametrize" }
  },
  "generated_projects": {
    "WithheldActionWitness": {
      "created_by_run": "001-withheld-action-witness",
      "seed_path": ".recreate/runs/001-withheld-action-witness/DESIGN-SEED-WithheldActionWitness.md",
      "implementation_path": "WithheldActionWitness/",
      "pgf_status_path": ".pgf/status-WithheldActionWitness.json",
      "status": "implemented",
      "consumed_sources": ["PnR","ReleaseMesh","ForgeQuarantine","ADPR"],
      "source_fingerprint": "ADPR+ForgeQuarantine+PnR+ReleaseMesh",
      "single_question": "...", "archetype": "Gate+Ledger",
      "verdict_scheme": ["justified","thin","breach"]
    }
  },
  "blocked_names": ["WithheldActionWitness"],
  "source_fingerprints": {
    "ADPR+ForgeQuarantine+PnR+ReleaseMesh": { "project": "WithheldActionWitness",
                                              "run_id": "001-withheld-action-witness" }
  },
  "idea_kernels": {
    "IK-001": {
      "problem_frame": "...", "method_archetype": ["source_grounded_linking"],
      "winner": "WithheldActionWitness", "kernel_gap": { "diversity": 0.05, "determinism": 1.0 },
      "next_run_emphasis": ["diversity", "surrogate"], "strength_label": "claimed", "outcome": "seeded"
    }
  }
}
```
규칙:
- `generated_projects`에는 **실제 구현된 것만** 기록 (미선정 top-K는 run dir candidates.md에 보존).
- `updated_at`은 선택 필드 — 세션 날짜 주입 또는 생략 (M3).
- `source_projects`는 코퍼스 원본 단위 사용 이력; `source_fingerprints`는 조합 중복 검사 정규화 키.
- `idea_kernels`(idea-layer): run별 상류 의도 + `kernel_gap`(의도 대비 달성) + `next_run_emphasis`
  (다음 run 조향 신호). **환류 없이 run 종료 금지(NoOpenLoop)**. 정본 → `idea-layer.md §7`.

### 3.3 `input_manifest.json`
```json
{
  "run_id": "002-pending",
  "corpus_root": "D:/recreate_prj",
  "included_sources": ["ADPR","afferentcore", "..."],
  "excluded_generated_projects": ["WithheldActionWitness"],
  "registry_snapshot": { "generated_project_count": 1, "consumed_source_count": 4 },
  "avoidance_policy": {
    "block_generated_names": true,
    "reject_exact_source_fingerprint": true,
    "reject_corpus_name_collision": true,
    "penalize_consumed_sources": true,
    "penalize_generated_overlap": true
  },
  "idea_kernel": {
    "kernel_id": "IK-002",
    "problem_frame": "...",
    "method_archetype": ["source_grounded_linking", "program_search"],
    "target_nonoverlap": ["...", "...", "..."],
    "target_nonoverlap_score": 0.6,
    "source_search_queries": ["...", "...", "...", "...", "..."],
    "deterministic_engine_hint": "...",
    "kill_conditions": ["...", "...", "..."]
  }
}
```

> `idea_kernel`은 idea-layer의 상류 의도(Phase1.5). run의 6 primitive 목표를 선언하며, Phase7
> `kernel_gap`이 이를 *측정한 달성*과 대조해 다음 run을 조향한다(폐루프). 정본 → `idea-layer.md §4`.

### 3.4 `avoidance_report.md` — 모든 판단을 근거+점수로 로깅 (M1 핵심)
```markdown
# Avoidance Report — {run_id}
## Registry Snapshot
- generated_projects: 1 | consumed_sources: PnR, ReleaseMesh, ForgeQuarantine, ADPR
## Candidate Decisions
| candidate | decision | reason | score | unique_ratio | idea_kernel_collision |
|---|---|---|---:|---:|---|
| WithheldActionWitness2 | reject | name collision (hard) | — | — | — |
| ReleaseDutyWitness | needs_pivot | source overlap 3/4 + release-witness grammar | 0.38 | 0.42 | anti_example |
| HeatObligationCalendar | allow | no collision, low overlap | 0.10 | 0.71 | none |
```

> `unique_ratio`(풀 동질화)·`idea_kernel_collision`(anti_examples/kill_conditions 저촉)은 idea-layer
> DiversityGuard 보조신호. 이산 hard-reject는 불변, 이 점수들은 soft 계층에 병합·로깅된다(감사).

### 3.5 run `status.json` 추가 필드
`run_id`, `run_path`, `registry_path`, `input_manifest`, `avoidance_report`,
`consumed_sources`, `source_fingerprint`, `registry_updated`.

---

## 4. 파이프라인 편입

```text
Phase0_Corpus
    LoadRegistry          # .recreate/registry.json (없으면 빈 registry)
    CreateRunScope        # .recreate/runs/{NNN}-pending/
    BuildInputManifest    # included_sources(코퍼스) / excluded(생성 프로젝트) 고정
    BuildGenes            # 생성 프로젝트 제외한 코퍼스만 3축 환원
Phase1_Inventory          # + GeneGraph (idea-layer: ABCLink 기질)
Phase1_5_IdeaKernel       # ★ idea-layer — 상류 의도(input_manifest.idea_kernel) (NoNameFirst)
Phase2_Generate           # + kernel bias + GenerateDebateEvolve (idea-layer)
Phase2b_Avoidance         # ★ 신규 — 과거 run/생성물/소비 source 기반 회피
    RejectGeneratedNameCollision
    RejectSourceFingerprintCollision
    RejectCorpusNameCollision
    AssessConsumedSourcePenalty
    DiversityGuard          # idea-layer P1 — 동질화 연속신호 soft 병치 (이산 게이트 불변)
    EmitAvoidanceReport
Phase3_Differentiate      # 코퍼스 대비 의미 차별화 (역할 분리 — §5) + unique_ratio 보조
Phase4_SelectOrIntegrate  # + TournamentSelect/idea_fit (idea-layer P2)
Phase5_Prove              # + EvaluatorGate (idea-layer P4)
Phase6_SeedDesign         # seed 산출 후 run rename: {NNN}-pending → {NNN}-{winner-slug}; + idea_trace/CrossModelVerify
Phase7_UpdateRegistry     # ★ 신규 — winner·consumed_sources 누적 + latest.json 갱신
    MeasureKernelGap        # ★ idea-layer 폐루프 — 의도 대비 달성 gap → idea_kernels 누적 → 다음 kernel 조향
```

---

## 5. 두 게이트의 역할 분리 (중복 아님)

| 게이트 | 비교 대상 | 신호 | 본다 / 못 본다 |
|---|---|---|---|
| **Phase2b_Avoidance** | 과거 run + 생성 프로젝트 (registry) | name collision, source fingerprint, 소비강도, generated overlap | 생성물은 코퍼스 스캔에서 제외되므로 Phase3가 못 봄 → 여기서 본다 |
| **Phase3_Differentiate** | 원래 코퍼스 (genes) | overlap, tag_clash, vocab_clash | 이름/fingerprint 충돌은 Phase3가 안 봄 → Phase2b가 본다 |

순서: generate → **avoidance(과거 회피)** → differentiate(코퍼스 차별화) → select-or-integrate.

---

## 6. 회피 알고리즘

### 6.1 정규화 (결정론)
```python
def source_fingerprint(parts: list[str]) -> str:
    return "+".join(sorted(set(parts)))

def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())
```

### 6.2 Hard Reject (결정론 — 감사 명확, M1)
```python
if normalize_name(cand.name) in {normalize_name(n) for n in registry["blocked_names"]}:
    reject("generated project name collision")
if source_fingerprint(cand.parts) in registry["source_fingerprints"]:
    reject("exact source set already generated")
if normalize_name(cand.name) in {normalize_name(n) for n in corpus_source_names}:
    reject("name collides with original corpus project")
```

### 6.3 Soft 판정 — AI 우선, 공식은 가이드 (M1)
```python
def avoidance_decision(cand, registry) -> dict:
    """AI_가 판정하되, 아래 공식을 기본 가이드로 참조하고 모든 점수를 로깅한다."""
    score = AI_assess_avoidance(cand, registry, guide=AVOIDANCE_GUIDE)  # AI 우선
    # AVOIDANCE_GUIDE (codex 기본값, 동결 아닌 가이드):
    #   0.12*repeated_source + 0.35*max_generated_jaccard
    #   + 0.25*name_similarity + 0.10*same_archetype_and_domain
    #   reuse_weight: copy 0.18 / parametrize 0.12 / redesign 0.06 (copy가 더 강한 회피)
    verdict = ("reject"      if score >= 0.55
               else "needs_pivot" if score >= 0.30
               else "allow")
    log_to_avoidance_report(cand, verdict, score, reasons=AI_explain(cand, registry))
    return {"verdict": verdict, "score": score}
```

- `source`를 완전 금지하지 않는다 — 코퍼스 48개뿐, 좋은 부품은 재사용 가치가 있다. **같은 조합·같은
  문제**를 강하게 회피하되, 부품 단위 재사용은 penalty로만 억제.
- `reuse_cost`가 `copy`였던 source를 다시 `copy`하면 더 높은 penalty (구조 그대로 복제 = 파생 위험).
  `redesign`은 약한 penalty (개념만 재사용).
- **모든 판정(reject/needs_pivot/allow)은 점수·근거와 함께 `avoidance_report.md`에 기록** — 감사 가능성.

### 6.4 DiversityGuard — 동질화 연속신호 (idea-layer P1, soft)

`AssessConsumedSourcePenalty`와 **같은 AI-판정 계층**에 병치한다. §6.2 이산 hard-reject는 불변.

```python
def diversity_guard(pool, genes, kernel) -> dict:
    """후보풀의 의미 동질화를 연속신호로 측정 (이산 충돌검사 보완). 메타층 AI_ 허용."""
    report = measure_homogenization(pool, genes)              # idea-layer §5.1
    collisions = {c.name: AI_check_kernel_collision(c, kernel) # anti_examples/kill_conditions 저촉
                  for c in pool} if kernel else {}
    if report.unique_ratio < 0.5:                            # K 늘리지 말고 island 재발산
        pool = enforce_diversity(report, pool)
    log_to_avoidance_report(pool, report.unique_ratio, collisions)  # soft 점수 병합
    return {"pool": pool, "unique_ratio": report.unique_ratio, "collisions": collisions}
```

- 비교 대상이 다르다: Phase2b DiversityGuard = **후보풀 내부 + kernel 의도**, Phase3 unique_ratio =
  **후보↔코퍼스**. 둘 다 이산 게이트를 흐리지 않고 점수로만 병합. 정본 → `idea-layer.md §5.1`.

---

## 7. Phase7 — 레지스트리 갱신

```python
def update_registry(registry, run, winner):
    gp = registry.setdefault("generated_projects", {})
    gp[winner["name"]] = {
        "created_by_run": run.id, "seed_path": run.seed_path,
        "implementation_path": f"{winner['name']}/", "status": "seeded",  # 구현 후 "implemented"
        "consumed_sources": winner["sources"],
        "source_fingerprint": source_fingerprint(winner["sources"]),
        "single_question": winner["single_question"], "archetype": winner["archetype"],
        "verdict_scheme": winner["verdict_scheme"],
    }
    registry.setdefault("blocked_names", []).append(winner["name"])
    registry.setdefault("source_fingerprints", {})[source_fingerprint(winner["sources"])] = \
        {"project": winner["name"], "run_id": run.id}
    for s in winner["sources"]:                       # source 사용 이력 누적
        sp = registry.setdefault("source_projects", {}).setdefault(s, {"use_count": 0, "used_by": []})
        sp["use_count"] += 1; sp["used_by"].append(winner["name"])
        sp["last_used_run"] = run.id
    if run.idea_kernel:                               # ★ idea-layer 폐루프 — 환류 없이 종료 금지(NoOpenLoop)
        gap = AI_measure_kernel_gap(run.idea_kernel, run.diversity_report,
                                    run.verify_report, winner)        # 의도 대비 달성
        registry = update_registry_with_idea_outcome(registry, winner, run.idea_kernel, gap)  # idea-layer §7
    write_json(".recreate/registry.json", registry)
    write_json(".recreate/latest.json", {"latest_run_id": run.id, "latest_run_path": run.path,
               "winner": winner["name"], "seed_path": run.seed_path})
```

> **폐루프 (idea-layer)**: `AI_measure_kernel_gap`은 kernel이 *선언한* 목표(target_nonoverlap_score 등)와
> 게이트가 *측정한* 달성(unique_ratio·elo·evaluator_gate 등)을 primitive별로 대조해 gap을 내고,
> `next_run_emphasis`(gap 큰 primitive)를 `idea_kernels`에 누적한다. 다음 run의 `AI_make_idea_kernel`이
> 이 saturation을 입력받아 조향된다 — recreate가 자기 자신에 `closed_loop`를 적용. 정본 → `idea-layer.md §7`.

---

## 8. Acceptance Criteria

- 재실행이 기존 run 산출물을 덮어쓰지 않는다 (`runs/{run_id}/` 불변).
- `latest.json`만 최신 run을 가리킨다.
- `registry.json`이 생성 프로젝트·소비 source를 누적한다.
- 생성 프로젝트 폴더는 코퍼스 gene 추출에서 제외된다 (`input_manifest.excluded_generated_projects`).
- name / source-fingerprint / 코퍼스명 충돌 후보는 hard-reject.
- 소비 source가 많은 후보는 needs_pivot 또는 reject, 점수·근거가 `avoidance_report.md`에 기록.
- `pgf full-cycle`은 run-scoped seed path를 참조한다.
- run_id는 timestamp가 아닌 시퀀스 (`{NNN}-{winner-slug}`).
- `HANDOFF.md`에 run_id·winner·consumed_sources 기록.

---

## 9. 통합 예외 — cross-model integration (FLEET-SYNTHESIS §6.1 보강)

> **왜 필요한가.** §6의 회피는 후보를 신선한 코퍼스 source로 밀어내 다양성을 키운다. 그러나 그
> 압력은 fleet winner들을 **disjoint source**로 갈라놓아, Phase 4의 cross-model integrate("같은
> 문제·다른 강점축")를 구조적으로 막는다 (`.recreate/FLEET-SYNTHESIS.md §6.1의 긴장`). 이미
> *생성된 프로젝트들*을 부모로 한 통합은 원본 코퍼스 중복이 아니라 **상위 합성**이므로, 회피의
> 일반 penalty를 그대로 적용하면 방법론의 간판 명제(통합)를 스스로 차단한다.

### 9.1 통합 후보의 정의

`gen_path == "INTEGRATE"` 이고 `parents`가 **registry의 `generated_projects`**(원본 코퍼스가 아님)인
후보. `parts`는 부모 프로젝트가 transitively 들고 있는 source의 합집합이지만, **재사용 대상은
부모의 합성 설계**(seed/구현)이지 raw 코퍼스 부품이 아니다.

### 9.2 별도 네임스페이스 — `generated_fingerprint`

```python
def generated_fingerprint(parents: list[str]) -> str:
    return "+".join(sorted(set(parents)))   # 부모 = 생성 프로젝트명
```

- registry에 `generated_fingerprints` 맵 추가(코퍼스 `source_fingerprints`와 **별개 네임스페이스**).
- **hard-reject(결정론)**: `generated_fingerprint(cand.parents)`가 `generated_fingerprints`에 있으면
  reject — *같은 부모 조합의 재통합* 방지. 이름 충돌·코퍼스명 충돌 규칙(§6.2)은 그대로 적용.

### 9.3 penalty 면제와 그 한계

- 부모를 통해 **transitive 재사용되는 코퍼스 source**는 소비강도 penalty를 **면제**한다(통합 목적).
  단 후보의 `provenance`가 부모 프로젝트를 명시해야 한다(감사). `avoidance_report`에 면제 사유 로깅.
- 면제는 **통합 후보에만** 적용 — 일반 RECOMBINE/MUTATE/TRANSPLANT가 소비 source를 다시 쓰면
  §6의 penalty 그대로. (통합을 가장한 단순 재조합 회피 — `parents`가 실제 생성 프로젝트인지 검사.)

### 9.4 차별화·통합 게이트는 강화 적용

- Phase 3: 통합 후보는 코퍼스뿐 아니라 **각 부모 대비**도 distinct해야 한다 — lifecycle superset일 뿐
  한 부모의 copy면 기각.
- Phase 4: 통합 게이트(통합 후보가 부모 최고 6축점 능가 시만 채택)는 그대로. 부모 6축 재채점이
  통합 정당화의 전제 — `candidates.md`에 부모 점수 + 통합 점수 병기.

### 9.5 Phase 7 갱신

- winner가 통합 후보면 `generated_fingerprints[generated_fingerprint(parents)] = {project, run_id}` 기록.
- `source_projects` 사용 이력은 transitive source에 대해 누적하되 `via: "integration of {parents}"` 주석.

### 9.6 통합 인플레이션 가드

- 한 generated winner는 최대 2개 통합 후보의 부모까지만 허용한다. 이미 2개 통합의 부모로 쓰인 winner를
  다시 부모로 삼는 후보는 `needs_justification`으로 기록하고, 정당화가 없으면 Phase2b에서 탈락시킨다.
- 통합물(`gen_path == "INTEGRATE"`로 생성된 winner)을 다시 부모로 삼는 메타-통합은 별도 정당화와 후행
  cross-model 합의를 필수 조건으로 한다. 이 조건은 같은 부모 조합 중복 방지(§9.2)와 별개로 적용한다.
- 위 가드는 통합 후보에만 적용한다. 일반 RECOMBINE/MUTATE/TRANSPLANT 후보는 기존 §6 회피 규칙을 따른다.

### 9.7 적용 조건 — §9는 통합을 *허용*할 뿐, *채택*은 게이트가 정한다 (실증)

> §9의 예외(소비 source penalty 면제 등)는 통합을 **시도 가능하게** 만들 뿐, 통합이 좋은 결과라는
> 보장이 아니다. **언제 통합이 부모를 능가하는가**의 조건은 `differentiation.md §3.2a`에 정본화돼 있다.

- 통합이 부모 최고점을 능가하려면 **강한 same_problem + 구조적으로 정렬된 상보축**(시간축 lifecycle 등)
  + 부모 단독으로 못 보는 **통합 고유가치**가 필요하다. 이 조건이 없으면 contract만 넓어져 게이트에서 기각된다.
- 실증: run 006(lifecycle, 양성, 합의 +0.150 채택) ↔ run 007(렌즈/계층축, 음성, 합의 −0.195 기각).
  cross-model 합의 정본: `.recreate/crossmodel/CONSENSUS.md`(양성), `round2/CONSENSUS-r2.md`(음성).
- 따라서 §9로 회피를 풀어 통합을 *허용*하더라도, 대부분의 비-정렬축(렌즈 ensemble·임의 layer-stack)
  통합은 §9.4 게이트에서 폐기됨을 예상한다. 통합 시도는 자연 정렬축 군집에 집중하라.
- 게이트 margin이 근소(±0.1)하면 단일 평가자로 확정하지 말고 cross-model 합의로 검증한다(`crossmodel/`).

---

## 10. 동시 실행 계약 — concurrent multi-runtime (FLEET-SYNTHESIS §6.2 보강)

> §2~9는 **순차** 실행을 전제한다(한 run이 registry를 갱신해야 다음 run이 baseline을 읽음).
> 진짜 **동시** 실행에서는 둘이 같은 baseline을 읽고 같은 fingerprint/이름을 만들 수 있어, 락/버전/머지
> 없이는 충돌하거나 lost update가 난다. 설계 근거·위험 7종(H1~H7)·알고리즘 상세 → `.recreate/FOLLOWUP-E-concurrency-policy.md`.
> 지금까지 fleet은 순차였으므로 이 계약은 **첫 동시 실행 전 활성화**한다.

### 10.1 registry 스키마 확장 (forward-compatible)

- `version`: int, registry 변경마다 +1(monotonic). claim·commit이 올린다. 순차 run에서도 자연 증가(무해).
- `active_runs`: append-only claim 로그 — `{claim_seq, run_id, runtime, baseline_version, status}`.
  status ∈ `active | committed | aborted`.

### 10.2 원자적 경계 2곳 (그 사이는 락 없이 병렬)

- **Phase 0 claim (원자적)**: registry 락 → `version` 읽어 `claim_seq = version+1`, `run_id =
  {NNN}-{runtime}-pending`(★runtime 접미사로 디렉토리 충돌 H1 원천 차단), `active_runs` append, `version` 갱신.
- **Phase 7 commit (원자적 OCC)**: registry 락 → **현재 registry 대비** winner 재검증(`avoidance_recheck` —
  이름/source_fingerprint/generated_fingerprint 충돌, §6.2 hard 규칙). 충돌 없으면 커밋+`version`+1,
  충돌이면 abort 기록 후 **pivot(머지 상태 대비 Phase 2b/3 재실행) 또는 discard**.

### 10.3 충돌 해소 (결정론적 outcome)

- commit은 mutual-exclusion이라 **항상 먼저 커밋한 run이 fingerprint/이름을 보유**하고, 두 번째 도달자는
  OCC 재검사에서 충돌을 보고 pivot/discard한다 → 정확히 한 run만 각 fingerprint/이름 보유(H2/H3/H4/H6 해소).
- 어느 run이 이기는지는 락 획득 순서(스케줄)에 의존하나 **결과 정합성은 결정론**. 재현이 필요하면
  `claim_seq` 오름차순 직렬 replay로 동시성을 제거하면 동일 결과(§7 audit).
- `latest.json`은 `version` 최대인 commit을 가리킨다(H7 해소).

### 10.4 soft 정책 (선택, 정확성엔 불필요)

- H5(같은 신선 source 과소비): claim 시 신선 source 풀을 runtime별 결정론 샤딩(`hash(source)%active==idx`)하면
  충돌 확률 감소 — 최적화일 뿐, 정확성은 10.2 commit 게이트가 보장.

### 10.5 한계

- **공유 FS 전제**: lockfile/atomic-rename으로 CAS 구현. 공유 FS 없는 분산 런타임은 외부 조정(git-ref CAS,
  분산 락) 필요 — 범위 밖.
- **pivot 종료성**: 코퍼스 48개라 동시 run이 많으면 신선 조합 고갈로 pivot 실패→discard. **동시성 상한**:
  신선 source 수 대비 동시 run 수를 보수적으로(권고).
