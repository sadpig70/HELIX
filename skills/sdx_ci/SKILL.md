---
name: sdx_ci
description: "SDX-CI (Source Discovery eXplorer — Cross Integration) — 여러 에이전트가 독립적으로 산출한 SDX 채널 카탈로그를 교차 통합하는 메타 스킬. 직교성은 *전역* 속성이므로 단순 union이 아니라 전역 8축 재계산 + pairwise overlap 재계산 + 그리디 직교 재선택(SDX Phase4 재실행)으로 합친다. URL canonical dedup, provenance 보존, cross-agent redundancy(분산 발굴 다양성 지표) 산출. SDX의 메트릭·overlap·스키마를 정본으로 재사용. Triggers: SDX통합, 교차통합, cross integration, sdx_ci, sdx ci, 카탈로그 병합, 멀티에이전트 통합, agent catalog merge, 채널 통합, integrate catalogs, 직교 재선택"
user-invocable: true
argument-hint: "integrate|union|compare --in=dir1,dir2,... [--out=dir] [--target=N]"
version: "1.0"
author: "양정욱 (sadpig70@gmail.com)"
---

# SDX-CI (Cross Integration) v1.0

> SDX가 단일 에이전트의 채널 발굴 엔진이라면,
> SDX-CI는 여러 에이전트의 발굴 결과를 *전역 직교성* 기준으로 합치는 통합 엔진이다.
> 다양성은 union으로 늘지 않는다 — 전역 재선택으로 정제된다.

## 존재 이유 (Why)

한 에이전트는 같은 검색 패턴으로 회귀하는 편향이 있다(SDX `strategies/README.md`). 여러 에이전트가 각자 `sdx --out=<dir>`로 독립 발굴하면 후보 풀의 진짜 다양성이 커진다. 그러나:

- **직교성(`independence`, `pairwise_overlap`)은 전역 속성**이다. 에이전트 A의 "직교 기저"와 B의 "직교 기저"는 서로를 모른다 → 단순 합치면 A·B 간 중복이 대량 발생.
- 각 에이전트가 `CH-0001`부터 시작 → **ID 충돌**.

따라서 교차 통합은 **파일 병합이 아니라 전역 Phase4 재실행**이다. SDX-CI는 이 재계산·재선택·provenance 보존·다양성 측정을 담당한다.

## SDX 의존 (정본 재사용)

SDX-CI는 **SDX(`sdx` 스킬)를 정본 라이브러리로 재사용**한다. 다음을 재정의하지 않는다:

| 정본 | 출처 |
|---|---|
| 8축 메트릭 정의·가중치(`independence ×2.0`), `total_score` 공식 | `sdx` SKILL.md / `schemas/channel_entry.yaml#metric_guide` |
| `AI_compute_pairwise_overlap` (same_cell 0.4 / domain 0.3 / publisher 0.2 / lang 0.1) | `sdx` SKILL.md |
| `AI_select_orthogonal_basis` 그리디 직교 선택 | `sdx` SKILL.md |
| 4-Axis 셀 좌표 + `required_coverage` | `sdx` schemas/channel_entry.yaml |
| 채널 엔트리 스키마 | `sdx` schemas/channel_entry.yaml |

> 중복 발견 시 `sdx` 스킬이 canonical. SDX-CI는 그 함수들을 *전역 풀*에 적용하는 orchestration 계층이다.

기반 표기법은 `pg`(PPR/Gantree), 실행 프레임은 `pgf`.

## 핵심 파라미터

```yaml
INPUT: multiple SDX catalog dirs   # 각 에이전트의 --out 산출물
INTEGRATION_UNIT: global_orthogonal_basis
DEDUP_KEY: canonical_url
PROVENANCE: preserved              # 통합 채널이 어느 에이전트에서 왔는지 추적
DIVERSITY_METRIC: cross_agent_redundancy
```

## CI_POLICY (운영 임계값 단일 출처)

```yaml
selection:
  target_size: 100                 # 통합 직교 기저 목표 (integrate 모드). --target로 override
  basis_min: 80                    # 직교 기저 하한 (SDX 설계 의도)
  basis_max: 150                   # 상한 (초과 시 풍부함보다 직교성 흐려짐 경고)
  max_overlap_cut: 0.5             # = sdx SDX_POLICY.selection.max_overlap_cut (정합)
  cell_coverage_floor: 0.6         # = sdx 동일

dedup:
  url_normalize: true              # scheme소문자 + host소문자 + trailing slash 제거 + www 제거 + 쿼리/프래그먼트 제거
  same_url_policy: "keep_highest_total_score"   # 동일 URL 다중 제출 시 최고점 채택, 나머지 provenance 병합
  near_dup_overlap: 0.7            # url은 다르나 overlap≥0.7 → near-duplicate 후보(통합 시 1개만)

redundancy:                        # cross-agent 다양성 진단 (낮을수록 발굴 다양)
  warn_global_redundancy: 0.40     # 전체 제출 중 중복 url 비율 ≥0.40 → 분담/시드 다양화 권고
  warn_pair_jaccard: 0.50          # 두 에이전트 url 집합 Jaccard ≥0.50 → 두 에이전트가 같은 곳 탐색

required_coverage:                 # = sdx schemas/channel_entry.yaml#required_coverage
  geographic: "8개 모두 ≥1"
  format: "10개 중 ≥8"
  temporal: "5개 모두 ≥1"
  scale: "3개 모두 ≥1"
```

## 입력 규격

각 입력 디렉토리는 SDX 카탈로그 루트(`sdx --out=<dir>` 산출물)여야 한다:

```text
<agent_dir>/
    index.yaml                # 진입점 — total_channels, shards 참조
    channels/{format}.yaml    # 채널 본문 (SDX channel_entry 스키마)
    basis/ reports/ (선택)
```

`index.yaml` 부재 시 해당 입력은 skip + 경고 기록.

## 운영 모드 (3개)

| Mode | Action |
|------|--------|
| `integrate` | 전역 재계산 + 그리디 직교 재선택 → 통합 단일 기저(`target_size`) + dedup union pool 보존 |
| `union` | 직교 재선택 없이 URL dedup union 전체 보존 (최대 풍부 — 직교성 미보장, pool만) |
| `compare` | 통합 없이 cross-agent redundancy·커버리지 비교 분석만 (read-only) |

---

## DESIGN: Gantree

```
SDX_CI_Main // 교차 통합 진입점 (in-progress) @v:1.0
    ModeIntegrate // 전역 직교 재선택 통합 (designing)
        Phase1_Load // 에이전트 카탈로그 적재 (designing)
            AI_load_agent_catalogs // 각 index.yaml + channels/*.yaml 로드, provenance 태깅
            AI_validate_inputs // index.yaml 부재/스키마 불일치 skip + 경고
            # output: {OUT}/.work/loaded_agents.yaml

        Phase2_DedupUnion // URL 정규화 + 합집합 + 중복 병합 (designing) @dep:Phase1_Load
            AI_normalize_urls // canonical url (CI_POLICY.dedup.url_normalize)
            AI_merge_same_url // 동일 url → 최고점 채택, provenance/lang/notes 병합
            # output: {OUT}/pool/union_pool.yaml   (dedup 전체 보존)

        Phase3_GlobalRecompute // 전역 8축·overlap 재계산 (designing) @dep:Phase2_DedupUnion
            AI_recompute_independence // 전역 풀 대비 재산정 (★ 로컬→전역)
            AI_recompute_total_score  // sdx total_score 공식 재적용
            AI_recompute_pairwise_overlap // 전역 채널쌍
            # output: {OUT}/.work/rescored_pool.yaml

        Phase4_OrthogonalReselect // 그리디 직교 재선택 (designing) @dep:Phase3_GlobalRecompute
            AI_select_orthogonal_basis // sdx 정본 함수, target=CI_POLICY.selection.target_size
            AI_force_fill_required_coverage // geo/format/temporal/scale 보장
            AI_renumber_ids // CH-NNNN 재번호 + ci_provenance 부착
            # output: {OUT}/.work/integrated_basis.yaml

        Phase5_Emit // 통합 카탈로그 + 다양성 리포트 출력 (designing) @dep:Phase4_OrthogonalReselect
            AI_emit_sharded_catalog // sdx 포맷 준수 — index.yaml + channels/{format}.yaml
            AI_emit_cross_agent_report // 기여도·중복률·고유기여·다양성 판정
            AI_emit_selection_log // 채택/거절 + 출처 에이전트
            # output_root: {OUT}/   (기본 .sdx/integrated/)
            # output: index.yaml
            # output: channels/{format}.yaml
            # output: pool/union_pool.yaml            (Phase2 보존본)
            # output: basis/orthogonality_matrix.json
            # output: basis/selection_log.yaml
            # output: reports/cross_agent_report.md   (★ 다양성 진단)
            # output: reports/integration_coverage.md

    ModeUnion // dedup union 전체 보존 (designing)
        # process: Phase1_Load → Phase2_DedupUnion → emit pool only (직교 재선택 생략)
        # note: 최대 풍부함 목적 — 직교성 미보장, '입력 archive'용
        # output_root: {OUT}/
        # output: pool/union_pool.yaml
        # output: reports/cross_agent_report.md

    ModeCompare // 분석 전용 (designing)
        # process: Phase1_Load → AI_analyze_overlap_only (read-only, 통합 산출 없음)
        # output_root: {OUT}/
        # output: reports/cross_agent_report.md
```

---

## PPR: 핵심 함수

```python
def AI_load_agent_catalogs(in_dirs: list[Path]) -> list[AgentCatalog]:
    """각 SDX 카탈로그 루트를 적재. 채널마다 source provenance 태깅."""
    # acceptance_criteria:
    #   - index.yaml 부재 dir → skip + warning (전체 중단 금지)
    #   - 각 채널에 _src = {agent: dir_name, orig_id: ch.id} 부착
    catalogs = []
    for d in in_dirs:
        if not AI_path_exists(f"{d}/index.yaml"):
            AI_warn(f"skip {d}: no index.yaml"); continue
        idx = AI_read_yaml(f"{d}/index.yaml")
        chans = []
        for shard in idx["shards"]:
            for ch in AI_read_yaml(f"{d}/{shard['file']}")["channels"]:
                ch["_src"] = {"agent": AI_basename(d), "orig_id": ch["id"]}
                chans.append(ch)
        catalogs.append({"agent": AI_basename(d), "channels": chans})
    return catalogs


def AI_normalize_url(url: str) -> str:
    """canonical url — dedup 키. 결정론적이므로 실제 코드."""
    # acceptance_criteria:
    #   - scheme/host 소문자, www. 제거, 말미 / 제거, query·fragment 제거
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("?")[0].split("#")[0].rstrip("/")
    return u


def AI_merge_same_url(catalogs: list[AgentCatalog]) -> Pool:
    """전 에이전트 채널 합집합 → 동일 canonical url 병합.
    same_url_policy = keep_highest_total_score, provenance 누적."""
    # acceptance_criteria:
    #   - 동일 url 그룹은 정확히 1 엔트리로 축약
    #   - ci_provenance.sources 에 병합된 모든 (agent, orig_id) 기록
    #   - language/notes 는 합집합 보존
    by_url = {}
    for cat in catalogs:
        for ch in cat["channels"]:
            key = AI_normalize_url(ch["url_pattern"])
            if key not in by_url:
                ch["ci_provenance"] = {"sources": [], "merged_count": 0}
                by_url[key] = ch
            winner = by_url[key]
            if ch["total_score"] > winner["total_score"]:
                ch["ci_provenance"] = winner["ci_provenance"]
                by_url[key] = winner = ch
            winner["ci_provenance"]["sources"].append(ch["_src"])
            winner["ci_provenance"]["merged_count"] += 1
            winner["language"] = AI_union(winner["language"], ch["language"])
    return list(by_url.values())


def AI_recompute_global_metrics(pool: Pool) -> Pool:
    """전역 풀 기준 independence·total_score·orthogonality_drift 재계산.
    ★ 로컬(에이전트별) 직교성을 전역으로 교체 — CI의 핵심."""
    # acceptance_criteria:
    #   - independence = 10 - 10 × max_overlap(this, rest_of_pool)   (sdx 정의)
    #   - total_score = sdx 공식 (independence×2 + Σ7) / 9
    #   - 8축 중 independence·orthogonality_drift만 전역 재계산, 나머지(발굴시점 정적)는 보존
    for ch in pool:
        max_ov = max((AI_compute_pairwise_overlap(ch, o)   # sdx 정본 함수
                      for o in pool if o is not ch), default=0)
        ch["metrics"]["independence"] = round(10 - 10 * max_ov, 1)
        ch["orthogonality_drift"] = round(max_ov, 2)
        ch["total_score"] = AI_sdx_total_score(ch["metrics"])  # sdx 공식
    return pool


def AI_integrate(in_dirs: list[Path], out: Path, target: int = None) -> IntegratedCatalog:
    """ModeIntegrate 5-Phase 순차 실행."""
    # acceptance_criteria:
    #   - basis_min ≤ len(result.basis) ≤ basis_max
    #   - required_coverage 충족 (geo 8/8, format ≥8, temporal 5/5, scale 3/3)
    #   - 모든 채택 채널쌍 overlap < CI_POLICY.selection.max_overlap_cut
    #   - 모든 채택 채널에 ci_provenance 존재
    #   - {OUT}/pool/union_pool.yaml (dedup 전체) 와 {OUT}/ (직교 기저) 동시 산출
    P = CI_POLICY
    target = target or P["selection"]["target_size"]
    cats = AI_load_agent_catalogs(in_dirs)
    pool = AI_merge_same_url(cats)                      # Phase2 (= union pool 보존)
    pool = AI_recompute_global_metrics(pool)            # Phase3 ★
    basis = AI_select_orthogonal_basis(pool, target=target)   # sdx 정본, target 일반화
    basis = AI_force_fill_required_coverage(basis, pool)
    basis = AI_renumber_ids(basis)                      # CH-NNNN + ci_provenance
    report = AI_cross_agent_report(cats, pool, basis)
    AI_emit_sharded_catalog(basis, out)                 # sdx 포맷
    AI_emit_pool(pool, f"{out}/pool/union_pool.yaml")
    AI_emit_report(report, f"{out}/reports/cross_agent_report.md")
    return {"basis": basis, "pool": pool, "report": report}


def AI_cross_agent_report(cats: list[AgentCatalog], pool: Pool, basis: list) -> CrossAgentReport:
    """분산 발굴 다양성 진단 — redundancy 높으면 에이전트들이 같은 곳을 봤다는 신호."""
    # acceptance_criteria:
    #   - per_agent: {submitted, selected_into_basis, unique_urls}
    #   - global_redundancy = (Σsubmitted - len(pool)) / Σsubmitted
    #   - pairwise_jaccard[A][B] = |urlA ∩ urlB| / |urlA ∪ urlB|
    #   - verdict: redundancy/jaccard 임계 초과 시 분담·시드 다양화 권고
    url = lambda c: {AI_normalize_url(x["url_pattern"]) for x in c["channels"]}
    sets = {c["agent"]: url(c) for c in cats}
    submitted = sum(len(c["channels"]) for c in cats)
    global_red = round((submitted - len(pool)) / max(1, submitted), 3)
    per_agent = {}
    for c in cats:
        only = sets[c["agent"]] - set().union(*[sets[o] for o in sets if o != c["agent"]] or [set()])
        sel = sum(1 for b in basis if any(s["agent"] == c["agent"] for s in b["ci_provenance"]["sources"]))
        per_agent[c["agent"]] = {"submitted": len(c["channels"]),
                                 "selected_into_basis": sel, "unique_urls": len(only)}
    pair = {a: {b: round(len(sets[a] & sets[b]) / max(1, len(sets[a] | sets[b])), 3)
                for b in sets if b != a} for a in sets}
    P = CI_POLICY["redundancy"]
    verdict = ("diversify_recommended"
               if global_red >= P["warn_global_redundancy"]
               or any(j >= P["warn_pair_jaccard"] for a in pair for j in pair[a].values())
               else "healthy_diversity")
    return {"global_redundancy": global_red, "per_agent": per_agent,
            "pairwise_jaccard": pair, "verdict": verdict}
```

---

## index.yaml — SDX Catalog Index Contract v1 준수

sdx_ci의 emit `index.yaml`은 **SDX Catalog Index Contract v1**(`sdx` SKILL.md 정본)을 준수한다 — `catalog.acceptance`, `shards[].path`, `policy_version` 필수.

| 모드 | `acceptance.lock_eligible` | `basis` 키 | TCX 직접 소비 |
|---|---|---|---|
| `integrate` | required_coverage 전항 PASS 시 `true` | 산출(orthogonality_matrix 등) | **권장** (직교 기저) |
| `union` | **`false`** (직교 재선택 안 함) | 생략(미계산) | 비권장 — integrate로 승격 후 |

> `union`은 "최대 풍부 pool 보존"이 목적이라 직교 기저가 아니다. 따라서 `lock_eligible=false`로 **TCX에 '이건 직교 기저가 아님'을 신호**한다. TCX `lock_check`는 경고만 내고 진행하지만, 운영 입력은 `integrate` 결과를 쓰는 것이 계약 의도다.

## 출력 스키마

### 통합 채널 엔트리

`sdx schemas/channel_entry.yaml` 전 필드 + CI 확장:

```yaml
- id: "CH-0001"            # 통합 후 재번호
  # ... sdx channel_entry 전 필드 (axis, metrics, total_score, ...) ...
  ci_provenance:
    sources:               # 이 채널을 제출한 모든 에이전트
      - { agent: "agent-1", orig_id: "CH-0002" }
      - { agent: "agent-3", orig_id: "CH-0007" }
    merged_count: 2        # 동일 url로 병합된 제출 수
```

### reports/cross_agent_report.md (★ 다양성 진단)

```markdown
## SDX-CI Cross-Agent Report
- 입력 에이전트: N | 제출 합계: Σ | dedup pool: M | 통합 기저: K
- global_redundancy: 0.NN  (warn ≥ 0.40)
- verdict: healthy_diversity | diversify_recommended

| agent | submitted | selected_into_basis | unique_urls |
|---|---|---|---|
| agent-1 | 100 | 38 | 22 |

### pairwise Jaccard (url 집합 겹침; 높을수록 같은 곳 탐색)
|       | a-1 | a-2 | a-3 |
| a-1   |  -  | 0.31| 0.18|
```

> `global_redundancy`·`pairwise_jaccard`가 높으면 에이전트들이 같은 채널을 중복 발굴한 것 → 분담/시드 다양화로 다음 라운드 개선. 이 리포트 자체가 "분산 발굴이 실제로 다양했는가"의 검증 지표다.

---

## 사용법

```bash
# 3개 에이전트가 각자 독립 발굴 (SDX v1.4 --out)
/sdx bootstrap --out=.sdx/shards/agent-1/
/sdx bootstrap --out=.sdx/shards/agent-2/
/sdx bootstrap --out=.sdx/shards/agent-3/

# 교차 통합 → 전역 직교 기저 100 + union pool + 다양성 리포트
/sdx_ci integrate --in=.sdx/shards/agent-1,.sdx/shards/agent-2,.sdx/shards/agent-3 --out=.sdx/integrated/ --target=100

# 직교 재선택 없이 dedup union 전체 (최대 풍부)
/sdx_ci union   --in=.sdx/shards/agent-1,.sdx/shards/agent-2 --out=.sdx/integrated/

# 통합 안 하고 겹침/다양성만 분석
/sdx_ci compare --in=.sdx/shards/agent-1,.sdx/shards/agent-2,.sdx/shards/agent-3
```

## 동시 실행 / 경로 규칙

- 입력(`--in`)은 read-only — 원본 에이전트 카탈로그를 변경하지 않는다. `--in` 각 값도 `--out`과 동일 정규화 규칙(bare token → `.sdx/<token>/`)을 따른다.
- `{OUT}` = `--out`, **미지정 시 `.sdx/integrated/`**. `--out` 값 정규화는 **SDX v1.4 `--out` 값 정규화 규칙(정본)을 그대로 상속**한다: bare token → `.sdx/<token>/`, 경로/절대경로 → 그대로. `{OUT}`은 카탈로그 루트(`catalog/` 자동 미추가). 중간물은 `{OUT}/.work/`.
- 통합 산출물 루트는 입력 에이전트 디렉토리와 달라야 한다 (자기참조 방지).

## 신규성 검증

기존 데이터 병합 도구는 단순 dedup·concat에 머문다. SDX-CI는 **직교성을 전역 재계산하여 다양성을 정제하고, 에이전트 간 중복률을 분산 발굴 품질 지표로 환류**하는 통합 레이어다. SDX의 "입력 편향 면역"을 멀티 에이전트 차원으로 확장한다.

## 향후 확장

- **가중 통합**: realized-yield(SDX yield_log) 높은 채널에 통합 우선권
- **증분 통합**: 새 에이전트 카탈로그만 기존 통합본에 병합 (전체 재계산 회피)
- **분담 피드백 루프**: cross-agent redundancy → 다음 라운드 에이전트 분담(전략/지역) 자동 제안
- **PGF delegate 연계**: 통합을 delegate 모드 결과 회수(returned)와 결합

## 버전 변경 이력

- **v1.0** (2026-06-01): 최초 릴리스. integrate/union/compare 3모드, 전역 직교 재선택, URL canonical dedup, ci_provenance, cross-agent redundancy 진단.

## 의존 스킬

- `sdx` — 8축 메트릭·pairwise overlap·직교 선택·채널 스키마 (정본, 재사용)
- `pg` — PPR/Gantree notation (정본)
- `pgf` — design/plan/execute framework, delegate(향후)
