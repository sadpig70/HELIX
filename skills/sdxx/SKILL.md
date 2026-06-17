---
name: sdxx
description: "SDXX (Source Discovery eXclusionary eXpansion) — 기존 채널 집합을 입력으로 받아, 그 집합에 '없는' orthogonal 신규 채널만 발굴하는 스킬. SDX의 사후 independence 필터를 발굴 *이전* 단계로 끌어올린 pre-discovery steering — 탐색기가 보유 채널을 재발굴하느라 예산을 낭비하지 않고 미지의 직교 영역만 탐색한다. SDX의 정본 자산(channel_entry 스키마, 5전략, 8축 메트릭, 4축 매트릭스, overlap 피처)을 재사용. 출력은 기존 카탈로그를 덮어쓰지 않는 additive delta. 동질화 탈출·채널 보강에 사용. Triggers: SDXX, 신규채널발굴, 기존채널제외, 없는채널, 직교확장, exclusionary discovery, channel delta, orthogonal expansion, 동질화탈출, novel channels only"
user-invocable: true
argument-hint: "discover --known=<index.yaml|channels.yaml> [--n=40] [--cells=cellA,cellB] [--out=dir]"
version: "1.0"
author: "양정욱 (sadpig70@gmail.com)"
---

# SDXX (Source Discovery eXclusionary eXpansion) v1.0

> SDX가 직교 기저 카탈로그를 *구축·유지*한다면, SDXX는 임의의 기존 채널 집합을 입력받아
> 그 **여집합(complement)** — 보유하지 않은 orthogonal 신규 채널 — 만 발굴한다.
> 합성의 다양성은 입력의 다양성을 초과할 수 없고, 입력의 *확장*은 이미 가진 것을 *제외*할 때 가장 빠르다.

## 존재 이유 (Why) — SDX와의 차이

SDX는 기존 채널과의 중복 회피 장치를 갖지만 **전부 사후(post-discovery) 필터**다:
- `independence`(가중치 2.0) = `10 − 10×max_overlap(기존)` → **점수 단계**
- `AI_select_orthogonal_basis_80`의 `max_overlap_cut` → **선택 단계**

발굴 전략 5개(`AI_explore_*`)는 **기존 카탈로그를 입력으로 받지 않는다.** 따라서 탐색기들이
보유 채널(현재 175개)을 모르고 발굴 → 같은 well-known 소스를 반복 재발굴하며 탐색 예산을
낭비하고, 진짜 미지의 직교 채널이 표면화되지 못한다. **이것이 동질화의 발굴-단계 근원.**

**SDXX = 배제를 발굴 단계로 끌어올린다 (pre-discovery steering).** "이미 가진 건 보지도 말고
다른 영역에서만 찾아라." SDX의 사후 independence 필터와 **상보가 아니라 상승작용**한다:
사전 배제(안 봄) + 사후 필터(여전히 겹치면 거부)의 이중 방어.

| | SDX | SDXX |
|---|---|---|
| 목적 | 직교 기저 80 카탈로그 구축·유지 | 임의 기존 집합의 **여집합** 발굴 |
| 기존채널 인지 | 사후(점수/선택) | **사전(발굴 steering) + 사후** |
| 출력 | 카탈로그 자체(전체) | **additive delta**(신규만, 비파괴) |
| 입력 | 없음(bootstrap) / 동질화 트리거(refresh) | **명시적 기존 채널 집합 `--known`** |

## 정본 재사용 (SDX 자산 — 중복 정의 금지)

SDXX는 다음을 SDX에서 **그대로 상속**한다. 재정의하지 않는다.

| 자산 | 정본 위치 |
|---|---|
| 채널 엔트리 스키마 | `skills/sdx/schemas/channel_entry.yaml` |
| 4-Axis 매트릭스 / `axis_system` / `required_coverage` | 위 스키마 `#axis_system` |
| 8축 평가 메트릭 / `metric_guide` | 위 스키마 `#metric_guide` |
| 5가지 발굴 전략 프롬프트 | `skills/sdx/strategies/01~05_*.md` |
| overlap 피처 공식 | SDX `AI_compute_pairwise_overlap` (axis_cell 0.4 + domain 0.3 + publisher_group 0.2 + language 0.1) |
| 운영 임계값 | SDX `SDX_POLICY` (http / selection / audit) |

SDXX가 추가하는 것은 **배제 입력(`exclude_known`)** 과 그것을 발굴 단계에 주입하는
**exclusion overlay** (`strategies/exclusion_overlay.md`) 뿐이다.

## 핵심 파라미터

```yaml
DEFAULT_N: 40                    # 1회 발굴 목표 신규 채널 수 (--n)
EXCLUSION_FEATURE: overlap_based # 이름/URL 완전일치 아님 — overlap 피처 기반(견고)
KNOWN_MATCH_THRESHOLD: 0.5       # candidate vs known overlap ≥ 0.5 → 이미 보유로 간주(=SDX max_overlap_cut)
URL_ACCEPTABLE_STATUS: [200, 301, 302]   # SDX_POLICY.http 상속
EMIT_MODE: additive_delta        # 기존 카탈로그 비파괴, 신규만 별도 산출
EMIT_FORMAT: sdx_catalog_root    # ★ 출력은 SDX Catalog Index Contract v1 준수 (index.yaml + channels/{format}.yaml)
                                 #   → sdx_ci integrate/union이 SDXX 산출물을 직접 입력으로 받음
```

> **★ sdx_ci 병합 호환 (멀티 에이전트):** SDXX 출력은 **SDX 카탈로그 루트**(`index.yaml` +
> 포맷별 `channels/{format}.yaml`)다. 따라서 SDX와 **동일하게** 여러 에이전트가 각자
> `--out=<고유>`로 독립 발굴한 뒤 `sdx_ci integrate`로 전역 직교 재선택 병합할 수 있다.
> 각 SDXX 에이전트가 같은 `--known`을 배제했으므로 병합 결과는 novel-vs-known을 보존하고,
> sdx_ci가 new-vs-new 직교를 보장한다. (§멀티 에이전트 참조)

## 배제 키 설계 (취약점 회피 — ★ 핵심)

이름/URL 완전일치 배제는 *같은 소스의 다른 URL*을 놓친다. SDXX는 SDX에 이미 정의된
**overlap 피처를 그대로 재사용**해 배제한다 (신규 taxonomy 도입 없음):

```
known_match(candidate, known_ch) = AI_compute_pairwise_overlap(candidate, known_ch)
  = axis_cell(0.4) + primary_domain(0.3) + publisher_group(0.2) + language(0.1)
candidate가 어떤 known_ch와도 overlap ≥ KNOWN_MATCH_THRESHOLD 이면 → '이미 보유'로 배제
```

→ 식별 다이제스트는 채널당 경량 키만 보관: `{name, url_host, publisher_group, primary_domain, axis_cell, language}`. (8축 메트릭 전체 아님 — 프롬프트 비대화 방지)

---

## DESIGN: Gantree

> 모든 흐름 제어는 PPR `def` 블록. Gantree는 노드 구조만.

```
SDXX_Main // 여집합 발굴 진입점 (in-progress) @v:1.0
    ModeDiscover // 기존 집합 입력 → 신규 직교 채널 발굴 (designing)
        Phase0_LoadKnown // 기존 채널 적재 + 경량 다이제스트 (designing)
            AI_load_known // --known 경로(index.yaml or channels.yaml) 적재
            AI_build_known_digest // 채널당 식별키만 추출(name/url_host/publisher_group/domain/axis_cell/language)
            AI_identify_known_coverage // 보유 집합의 4-Axis 셀 점유 → 빈 셀 식별
            # output: {OUT}/.work/known_digest.yaml

        Phase1_ExploreExcl // 5전략 병렬 발굴 — exclude_known 주입 (designing) @dep:Phase0_LoadKnown
            [parallel]
            AI_explore_reference_backtrack_excl
            AI_explore_cross_lingual_excl
            AI_explore_failure_archive_excl
            AI_explore_adjacent_borrow_excl
            AI_explore_weak_signal_excl
            [/parallel]
            AI_merge_candidates // 후보 간 중복 제거
            # overlay: strategies/exclusion_overlay.md (각 SDX 전략 프롬프트에 배제절 append)
            # output: {OUT}/.work/all_candidates.yaml

        Phase2_PrefilterKnown // 발굴 직후 known 재배제 (사전 steering 누수 차단) (designing) @dep:Phase1_ExploreExcl
            AI_drop_known // known_match ≥ THRESHOLD 후보 제거 (+ drop 사유 기록)
            # output: {OUT}/.work/novel_candidates.yaml + reports 내 known_rejected_count

        Phase3_LightValidation // URL 살아있음만 확인 (designing) @dep:Phase2_PrefilterKnown
            AI_check_url_alive // SDX_POLICY.http.acceptable_status 상속
            # output: {OUT}/.work/validated.yaml

        Phase4_OrthogonalSelect // known ∪ 신규후보 동시 직교 선택 (designing) @dep:Phase3_LightValidation
            AI_score_8axis_metrics // independence는 known 카탈로그 대비 산정
            AI_select_orthogonal_vs_known // 신규끼리 + known 대비 모두 max_overlap_cut 만족하는 N개
            # output: {OUT}/.work/selected_new.yaml (N개)

        Phase5_DeltaEmit // SDX 카탈로그 루트 포맷 delta 산출 (비파괴, sdx_ci 병합 가능) (designing) @dep:Phase4_OrthogonalSelect
            AI_assign_ids // 에이전트-로컬 CH-0001부터 연번 (sdx_ci가 병합 시 전역 재번호). discovery_skill=sdxx 부착
            AI_format_yaml_entries // sdx channel_entry.yaml 스키마 준수
            AI_shard_by_format // 채널을 format별 channels/{format}.yaml로 분할 (sdx_ci 입력 계약)
            AI_emit_index // index.yaml: SDX Catalog Index Contract v1 (catalog/shards/basis/reports/acceptance 필수)
            AI_emit_coverage_delta // 보유 대비 4-Axis 셀 커버리지 증가분
            AI_emit_discovery_report // 후보수/known배제수/신규수/커버리지델타
            # output_root: {OUT}  (기본 .sdxx/ ; 멀티에이전트는 {OUT}=.sdxx/shards/agent-N/)
            # output: index.yaml                       (★ Contract v1 — sdx_ci 진입점)
            # output: channels/{format}.yaml × M        (★ format별 샤딩 — sdx_ci가 walk)
            # output: reports/sdxx_discovery_v{N}.md
            # output: reports/coverage_delta_v{N}.md
```

---

## PPR: 핵심 함수

```python
def AI_load_known(source: str) -> list[ChannelEntry]:
    """--known 입력 적재. SDX index.yaml(샤드 walk) 또는 channels.yaml(평면 목록) 모두 허용.
    인라인 목록도 허용(테스트)."""
    # acceptance_criteria:
    #   - index.yaml이면 shards[].path 전부 walk해 채널 합침
    #   - channels.yaml이면 channels[] 직접 사용
    #   - 반환 채널 각각 최소 {name, url_pattern, axis, primary_domain, publisher_group, language} 보유

def AI_build_known_digest(known: list[ChannelEntry]) -> KnownDigest:
    """배제용 경량 다이제스트. 채널당 식별키만 (8축 메트릭 제외 — 프롬프트 경량화)."""
    # acceptance_criteria:
    #   - 각 항목 = {name, url_host, publisher_group, primary_domain, axis_cell, language}
    #   - url_host = AI_extract_host(url_pattern)  (스킴/경로 제거)
    return [
        {
            "name": ch["name"],
            "url_host": AI_extract_host(ch["url_pattern"]),
            "publisher_group": ch.get("publisher_group"),
            "primary_domain": ch.get("primary_domain"),
            "axis_cell": AI_axis_cell(ch["axis"]),
            "language": ch.get("language"),
        }
        for ch in known
    ]

def AI_is_known(candidate: ChannelCandidate, digest: KnownDigest) -> tuple[bool, Optional[str]]:
    """overlap 피처 기준 보유 여부. SDX AI_compute_pairwise_overlap 재사용 → 견고한 배제."""
    # acceptance_criteria:
    #   - url_host 동일 → 즉시 known (반환 사유 'url_host')
    #   - 그 외 max overlap ≥ KNOWN_MATCH_THRESHOLD → known (사유 'overlap:{feature}')
    #   - 아니면 (False, None)
    for k in digest:
        if candidate.url_host and candidate.url_host == k["url_host"]:
            return True, "url_host"
        ov = AI_compute_pairwise_overlap(candidate, k)   # SDX 정본 재사용
        if ov >= KNOWN_MATCH_THRESHOLD:
            return True, f"overlap:{round(ov,2)}"
    return False, None


# --- 5전략 wrapper: SDX 전략 프롬프트 + exclusion overlay -----------------------
# 각 함수는 SDX strategies/0X_*.md(정본) + strategies/exclusion_overlay.md(배제절)을
# 합쳐 프롬프트를 구성한다. exclude_known 다이제스트를 프롬프트에 주입해
# 탐색기가 보유 영역(publisher_group/domain/axis_cell)을 *처음부터* 피하게 한다.

def AI_explore_reference_backtrack_excl(seeds, exclude_known: KnownDigest) -> list[ChannelCandidate]:
    """SDX S1 + 배제절. prompt: sdx/strategies/01_reference_backtrack.md + strategies/exclusion_overlay.md"""
    # acceptance_criteria:
    #   - SDX S1 기준 전부 충족 (≥30 후보, non-US_EU ≥30%, trace_path)
    #   - 추가: 발굴 결과의 known 비율 < 0.2 (사전 steering 효과 검증)

def AI_explore_cross_lingual_excl(topic, exclude_known): ...   # SDX S2 + overlay
def AI_explore_failure_archive_excl(domain, exclude_known): ... # SDX S3 + overlay
def AI_explore_adjacent_borrow_excl(target, exclude_known): ... # SDX S4 + overlay
def AI_explore_weak_signal_excl(exclude_known): ...             # SDX S5 + overlay


def AI_select_orthogonal_vs_known(
    candidates: list[ChannelCandidate], known: list[ChannelEntry], n: int,
) -> list[ChannelEntry]:
    """신규 후보들끼리 + known 카탈로그 대비 모두 직교인 N개를 그리디 선택.
    SDX AI_select_orthogonal_basis_80과 동일 메커니즘이되, 선택 풀 = 신규만, 배제 기준 = known ∪ 기선택."""
    # acceptance_criteria:
    #   - len(result) <= n  (가능한 만큼; 모자라면 사유 로깅)
    #   - 모든 result는 known 전체와 overlap < SDX_POLICY.selection.max_overlap_cut
    #   - result 쌍끼리도 overlap < max_overlap_cut
    #   - --cells 지정 시 해당 빈 셀 우선 충원
    selected = []
    cut = SDX_POLICY["selection"]["max_overlap_cut"]
    for cand in sorted(candidates, key=lambda c: c.total_score, reverse=True):
        if len(selected) >= n:
            break
        if max((AI_compute_pairwise_overlap(cand, x) for x in known + selected), default=0) < cut:
            selected.append(cand)
    return selected


def mode_discover(known_source: str, n: int, target_cells: list = None, out: str = ".sdxx") -> Delta:
    """SDXX 메인. 기존 집합의 여집합에서 N개 직교 신규 채널 발굴 → additive delta."""
    # acceptance_criteria:
    #   - 산출 채널 전부 known과 overlap < max_overlap_cut (사전+사후 이중 배제)
    #   - 기존 카탈로그 파일 불변 (비파괴 — delta만 신규 기록)
    #   - reports에 {candidates, known_rejected, novel_selected, coverage_delta} 기록
    known   = AI_load_known(known_source)
    digest  = AI_build_known_digest(known)
    cands   = AI_merge_candidates(parallel_explore_5_excl(digest, target_cells))
    novel   = [c for c in cands if not AI_is_known(c, digest)[0]]      # Phase2 사전 누수 차단
    valid   = [c for c in novel if AI_check_url_alive(c)]
    for c in valid:
        c.metrics = AI_score_8axis_metrics(c, existing_catalog=known)  # independence는 known 대비
    selected = AI_select_orthogonal_vs_known(valid, known, n)
    return AI_emit_delta_catalog(selected, known, out)


def AI_emit_delta_catalog(selected: list[ChannelEntry], known: list[ChannelEntry], out: str) -> Delta:
    """신규 채널을 SDX 카탈로그 루트 포맷으로 산출 → sdx_ci가 직접 입력으로 받음.
    ★ 비파괴: {OUT}에만 쓰고 .sdx/catalog는 불변."""
    # acceptance_criteria:
    #   - {OUT}/index.yaml 이 SDX Catalog Index Contract v1 충족
    #     (catalog{version,policy_version,total_channels,acceptance{catalog_size,lock_eligible,required_coverage_passed}},
    #      shards[]{format,file,path,count,id_range}, basis, reports)
    #   - sum(shards[].count) == catalog.acceptance.catalog_size == total_channels  (계약 불변식)
    #   - 채널은 format별 {OUT}/channels/{format}.yaml 로 샤딩 (sdx_ci AI_load_agent_catalogs가 walk)
    #   - 작은 delta는 required_coverage 미충족이 정상 → lock_eligible=false (정직 신호; 병합 시 sdx_ci가 force_fill)
    #   - .sdx/catalog 경로는 일절 쓰지 않음 (비파괴)
    AI_assign_ids(selected)                       # 에이전트-로컬 CH-NNNN
    shards = AI_shard_by_format(selected)
    AI_write_format_shards(shards, f"{out}/channels/")
    AI_emit_index(selected, shards, out)          # Contract v1
    AI_emit_coverage_delta(selected, known, f"{out}/reports/coverage_delta_v1.md")
    AI_emit_discovery_report(selected, f"{out}/reports/sdxx_discovery_v1.md")
    return {"out": out, "new_channels": selected, "index": f"{out}/index.yaml"}
```

---

## 출력 스키마 — SDX 카탈로그 루트 (sdx_ci 입력 계약 준수)

SDXX delta는 **SDX 카탈로그 루트**로 산출된다 → `sdx_ci`가 다른 SDX/SDXX 산출물과 동일하게 병합.

```text
{OUT}/                                  # 기본 .sdxx/ ; 멀티에이전트는 .sdxx/shards/agent-N/
├── index.yaml                          # ★ SDX Catalog Index Contract v1 (sdx_ci 진입점)
├── channels/{format}.yaml × M          # ★ format별 샤딩 (sdx_ci AI_load_agent_catalogs가 walk)
├── reports/sdxx_discovery_v{N}.md
└── reports/coverage_delta_v{N}.md
```

### index.yaml (SDX Catalog Index Contract v1)

```yaml
catalog:
  version: "v1"
  policy_version: "sdx-1.5"             # SDX taxonomy 추론용 (소비자 계약)
  total_channels: int
  shard_key: "format"
  acceptance:
    catalog_size: int                   # == sum(shards[].count) == total_channels (불변식)
    lock_eligible: bool                 # 작은 delta는 보통 false (required_coverage 미충족 — 정직 신호)
    required_coverage_passed: bool
shards:
  - { format: str, file: "channels/{fmt}.yaml", path: "channels/{fmt}.yaml", count: int, id_range: str }
basis: { orthogonality_matrix: path, overlap_policy: path, selection_log: path }   # 선택(있으면)
reports: { coverage: "reports/coverage_delta_v1.md" }
sdxx:                                    # ★ SDXX provenance 확장 (계약 부가 — 금지 아님)
  source_known: "<--known 경로>"
  known_channel_count: int
  exclusion_threshold: 0.5
```

### channels/{format}.yaml (sdx channel_entry 스키마 + SDXX 메타 2필드)

```yaml
channels:
  - id: "CH-0001"                        # 에이전트-로컬 연번 (sdx_ci 병합 시 전역 재번호)
    name: "..."
    url_pattern: "..."
    axis: {temporal, geographic, format, scale}
    metrics: {independence, signal_density, ...}   # 8축 (independence는 known 대비)
    total_score: 7.x
    discovery_strategy: "S2_cross_lingual"
    discovery_skill: "sdxx"              # ★ provenance
    excluded_known_overlap_max: 0.x      # ★ known 대비 최대 overlap (배제 검증 흔적)
    novelty_vs_known: "..."              # overlay 부착: 보유 대비 무엇이 다른가
    ...
```

> `lock_eligible=false`는 정상이다 — SDXX delta는 *기저 보강분*이라 단독으로 required_coverage(geo 8/8 등)를
> 채우지 않는다. `sdx_ci integrate`가 병합 시 `force_fill_required_coverage`로 보정한다.

### reports/sdxx_discovery_v{N}.md

```markdown
## SDXX discovery — <UTC>
- known 입력: <경로> (175 channels)
- 발굴 후보: 210
- known 배제(사전 steering 누수): 18  ← 낮을수록 steering 효과 좋음
- URL 사망 제외: 12
- 직교 신규 선정: 40
- 4-Axis 커버리지 증가: format niche +3, geo AF +2, temporal T-100Y+ +1
```

---

## 사용법 (단일 에이전트)

```bash
# 현재 SDX 카탈로그(175채널)를 입력으로, 그에 없는 직교 신규 40개 발굴
/sdxx discover --known=.sdx/catalog/index.yaml --n=40

# 특정 빈 셀에 집중
/sdxx discover --known=.sdx/catalog/index.yaml --n=20 --cells="AF,T-100Y+,nature"

# 출력 루트 지정 (SDX --out 정규화 규칙과 동일: bare token → .sdxx/<token>/)
/sdxx discover --known=.sdx/catalog/index.yaml --out=round0609
```

`--out` 정규화·`{OUT}/.work/` 중간산출물·동시실행 격리는 SDX v1.4 규칙을 동일 적용
(기본 `{OUT}` = `.sdxx/`).

## 멀티 에이전트 발굴 + sdx_ci 병합 (★ .sdx_org 스냅샷 + 단순 union)

핵심 통찰: **SDXX가 `.sdx_org`에 *없는* 채널만 발굴하므로, 최종 병합은 전역 재선택이 아니라
단순 union으로 충분하다** (아래 논증). 이 방식은 원본을 **전량 보존**하고 다운스트림은
`.sdx`를 그대로 읽는다 — 기존 시스템(sdx_ci/TCX/AOX) 코드 무변경.

```bash
# 0) (1회 가드 스냅샷) 원본 보존 — .sdx_org 없을 때만. 이후 모든 발굴의 known 기준.
#    .sdx → .sdx_org   (이미 있으면 건너뜀: 원본 불멸. 재실행해도 안 덮음)

# 1) K개 에이전트가 같은 .sdx_org를 배제하고 각자 독립 발굴 (에이전트별 고유 --out)
/sdxx discover --known=.sdx_org/catalog/index.yaml --out=.sdxx/shards/agent-1/ --n=30
/sdxx discover --known=.sdx_org/catalog/index.yaml --out=.sdxx/shards/agent-2/ --n=30
/sdxx discover --known=.sdx_org/catalog/index.yaml --out=.sdxx/shards/agent-3/ --n=30
#   (PGF delegate / Agent 병렬 파견으로 동시 실행 — --out 격리로 race 없음)

# 2) sdx_ci로 신규끼리 통합 (new-vs-new 직교 재선택 + 에이전트간 dedup + 다양성 진단)
/sdx_ci integrate --in=.sdxx/shards/agent-1,.sdxx/shards/agent-2,.sdxx/shards/agent-3 \
                  --out=.sdxx/integrated/ --target=60

# 3) (나중에 필요시) 단순 union: .sdx_org ∪ integrated-new → .sdx  (원본 전량 보존 + 신규 덧붙임)
#    target을 (원본수 + 신규수) 이상으로 주면 모두 직교라 아무것도 안 버려짐 → union 효과 + ID재번호 + index.yaml
/sdx_ci integrate --in=.sdx_org/catalog,.sdxx/integrated --out=.sdx/catalog --target=999
#    → 다운스트림(TCX/AOX)은 변경 없이 .sdx/catalog/ 그대로 읽는다.
```

**왜 3단계가 단순 union으로 성립하는가 (직교성 보존 논증):**
- 각 SDXX 채널은 `.sdx_org`의 모든 채널과 overlap < `max_overlap_cut`(사전+사후 배제 보장) → **new-vs-known 직교는 구성상 이미 참**.
- 2단계 sdx_ci가 **new-vs-new 직교**를 보장. `.sdx_org`는 그 자체로 직교.
- ∴ `(.sdx_org) ∪ (integrated-new)`는 **재선택 없이 그대로 유효한 직교 카탈로그**. 3단계 integrate는
  target이 충분하면 **아무것도 evict하지 않는 no-op 선택**(=단순 union)이 되어 원본을 전량 보존한다.
- 단순 union이 다운스트림-유효하려면 ID 재번호·URL canonical dedup·index.yaml 카운트 재계산만 필요한데,
  이는 `sdx_ci integrate`가 자동 수행한다 → **별도 merge 도구·sdx_ci 변경 불요**.

> ★ `--target`을 작게 주면(예: 220) 원본이 evict될 수 있다. 원본 전량 보존이 목적이면
> `--target`을 (원본수+신규수) **이상**으로 줘서 단순 union 효과를 강제하라.

> `.sdx_org` 스냅샷 후 `.sdx`를 재생성하기 전까지, 다운스트림은 `.sdx_org`(원본) 또는 3단계 산출 `.sdx`를
> 가리키게 하면 된다. SDXX 자체는 `.sdx`/`.sdx_org`를 쓰지 않는다 — 스냅샷(0)·최종 union(3)은 운영 단계다.

## 파이프라인 통합 (동질화 탈출 흐름)

```
[출력 동질화 감지] (EVX pool이 발행 코퍼스의 derivative로 수렴)
    ↓
(1회) .sdx → .sdx_org                                   (원본 불멸 스냅샷)
    ↓
/sdxx discover --known=.sdx_org/catalog/index.yaml ...  (K 에이전트 병렬, 원본 채널 제외·신규 직교만)
    ↓
/sdx_ci integrate --in=.sdxx/shards/* --out=.sdxx/integrated/   (new-vs-new 직교 재선택)
    ↓
(나중에 필요시) /sdx_ci integrate --in=.sdx_org/catalog,.sdxx/integrated --out=.sdx/catalog --target=999
                = .sdx_org ∪ 신규 단순 union (원본 전량 보존) → 다운스트림은 .sdx 그대로
    ↓
aox_full --start-from tcx (또는 sdx)  → 새 채널 기반 TCX→IDX→CIX → fresh 아이디어
```

> SDXX는 **비파괴 delta**(SDX 카탈로그 루트 포맷)만 `.sdxx/`에 만든다. `.sdx_org`(원본 보존)·`.sdx`(최종
> union) 생성은 `sdx_ci`를 통한 운영 단계 — SDX의 "카탈로그 변경의 유일 경로는 SDX/sdx_ci" 경계를
> 침범하지 않는다. (SDXX = 발굴기, sdx_ci = 통합·병합기, SDX = 카탈로그 소유자)
> 신규는 원본에 *없던* 채널이라 최종 병합은 단순 union으로 충분하다 — 전역 재선택 불요.

## 신규성 / 경계

- SDX와의 경계: SDXX는 **발굴기**일 뿐 카탈로그 *소유자*가 아니다. delta 산출까지만 수행하고
  병합·yield·decay 등 카탈로그 거버넌스는 SDX가 관장한다.
- 기존 SDX는 일절 수정하지 않는다(보존). SDXX는 SDX 자산을 *읽어* 재사용만 한다.

## 의존 스킬

- `pg` — PPR/Gantree notation (정본)
- `pgf` — design/execute framework
- `sdx` — 채널 스키마·5전략·8축 메트릭·overlap 공식·SDX_POLICY 정본 (읽기 전용 재사용)
- `sdx_ci` — 멀티 에이전트 SDXX 산출물의 교차 통합(전역 직교 재선택·병합). SDXX 출력이 SDX 카탈로그 루트라 그대로 입력 가능
