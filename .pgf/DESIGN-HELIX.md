# DESIGN-HELIX — 자율 창조 폐루프 시스템 (PGF design)

> PGF design mode 산출. HELIX = IdeaFirst(explore) ⊕ recreate/ProjectGenome(exploit)를
> 공유 substrate 위에 연합한 자율 창조 시스템. 설계 근거: `docs/ARCHITECTURE.md`, 분석 정본은
> `D:/recreate_prj/_workspace/` 의 통합 분석. pg/pgf 표기는 `pg`·`pgf` 스킬 정본.

---

## 0. 핵심 명제

> **두 상보 가닥(explore=세계 스캔, exploit=코퍼스 재조합)을 단일 백본(공유 substrate)이 묶어,
> 환류하는 폐루프임에도 매 회전 동질화를 차단해 수렴(근친교배) 없이 복리 성장하는 나선.**

설계 원칙(분석 정본에서 계승):
1. **융합 아님, 연합(federate)** — 두 엔진은 분리 가능. HELIX는 *백본*을 신설하고 엔진은 어댑터로 연결.
2. **단일 출처(single source of truth)** — 양측이 중복 구축한 ledger·diversity·provenance를 백본에 한 번만 정의 → desync 제거.
3. **결정론 경계** — 백본 helper는 순수 결정론(stdlib only, 시계·네트워크·AI 없음). 의미 판단(임베딩 등)은 **주입(inject)**. 엔진 내부의 LLM 단계는 메타층.

---

## 1. 이중나선 → 시스템 매핑 (정정판)

| 나선 구성 | 시스템 요소 | 결정론 클래스 |
|---|---|---|
| 가닥 A (sense) | **explore** = IdeaFirst (sdx→tcx→idx→cix→evx, aox) | 엔진 내부 LLM (메타) |
| 가닥 B (antisense) | **exploit** = recreate/ProjectGenome (corpus→seed) | 엔진 내부 LLM (메타), 생성물 verdict 결정론 |
| 역평행(antiparallel) | A=outside-in(세계→아이디어), B=inside-out(자산→seed) | — |
| 백본(backbone) | **HELIX-Core** substrate: ledger·diversity·provenance·fingerprint·loop | **순수 결정론** |
| 염기쌍 결합(base-pairing) | **winner→corpus 환류** + 공유 ledger (두 가닥을 잇는 결합) | 결정론(transform) |
| 전사/번역(transcription) | final_idea / DesignSeed → pgf full-cycle (가닥→산물) | pgf 위임 |
| 복제(replication) | 새 프로젝트 산출 | pgf |
| 복구효소(repair) | 5점 다양성 게이트 → 세대 퇴화 방지 | 측정=결정론, 판단=주입 |
| 나선 상승(pitch) | 회전마다 다양성 유지 → 폐루프인데 수렴 안 함 | — |

> §1 정정: base-pairing은 **엔진 간 결합(winner→corpus·공유 ledger)**에 매핑한다(가닥을 *묶는* 결합).
> pgf 핸드오프는 가닥에서 *나오는* 산물이므로 transcription에 매핑.

---

## 2. Gantree — HELIX 구조

```
HELIX // 자율 창조 폐루프 (explore⊕exploit + 공유 백본) (in-progress) @v:0.1
    HelixCore // 백본 — 단일 출처 결정론 substrate (in-progress)
        Fingerprint // 정체성 primitive (normalize/tokenize/fingerprint) (done) #core
            # 출처: ProjectGenome scripts/fingerprint.py 재사용 (정본 승격)
        Ledger // 통합 소모/등록 ledger — 재사용 차단 게이트 (in-progress) #core
            # IdeaFirst consumed_ideas.yaml + ProjectGenome registry.json 단일화
            # exclude_match_on: idea_id·normalized_title·aliases·semantic_family
            #                   ·source_fingerprint·generated_fingerprint
        Diversity // 통합 동질화/다양성 측정 (in-progress) #core
            # aox 4임계(keyword_coverage·domain_pair·avg_sim·winner_sim)
            #   + recreate unique_ratio 단일화. ≥2/N breach → triggered
            # 임베딩=주입(결정론 외부), 집계=결정론
        Provenance // 계보 추적 + winner→corpus 환류 (in-progress) #core
            # trace_winner: EVX→CIX(source_insight_id)→IDX→TCX→CH / recreate kernel→seed
            # winner_to_corpus_entry: 구현된 explore winner → exploit 코퍼스 source (염기쌍)
        Loop // explore↔exploit 폐루프 드라이버 (in-progress) #core
            # next_action(state) 결정론 정책: record_consumed / refresh_inputs /
            #   run_explore / run_exploit
        Validate // 구조·스키마·계약 검증기 (in-progress) #core
    HelixEngines // 두 가닥 어댑터 (연합 — 복사 아님) (in-progress)
        ExploreAdapter // IdeaFirst 계약 어댑터 (designing) @dep:HelixCore #engine
            # 입력: .evx/latest/stage6_final.yaml → HELIX Winner
            # 출력: HELIX-Core ledger/diversity/provenance 호출 계약
        ExploitAdapter // recreate/ProjectGenome 계약 어댑터 (designing) @dep:HelixCore #engine
            # 입력: .recreate registry + DESIGN-SEED → HELIX Winner
            # 코퍼스 환류 수신: winner_to_corpus_entry 산출을 corpus source로 적재
    HelixSchemas // 백본 데이터 계약 (JSON Schema) (in-progress)
        LedgerSchema
        DiversityReportSchema
        LoopStateSchema
        CorpusEntrySchema
    HelixDocs // README + ARCHITECTURE + SUBSTRATE-CONTRACT (in-progress)
    HelixTests // 결정론 helper unittest 6종 (in-progress) @dep:HelixCore
    HelixExamples // 샘플 ledger + 1라운드 루프 산출 (designing)
```

---

## 3. PPR — 백본 핵심 함수 (계약)

### 3.1 Ledger — 통합 재사용 차단 (P: provenance_memory + diversity_guard)

```python
def is_consumed(candidate: dict, ledger: dict) -> dict:
    """후보가 이미 소모/생성된 것과 충돌하는지 결정론 판정.
       IdeaFirst exclude_match_on + ProjectGenome fingerprint를 단일 게이트로."""
    keys = {
        "idea_id":        candidate.get("idea_id"),
        "normalized_title": normalize_name(candidate.get("title", "")),
        "aliases":        [normalize_name(a) for a in candidate.get("aliases", [])],
        "semantic_family": candidate.get("semantic_family"),
        "source_fingerprint":    source_fingerprint(candidate.get("sources", [])),
        "generated_fingerprint": generated_fingerprint(candidate.get("parents", [])),
    }
    hit = match_any(keys, ledger)          # 결정론 — 정확/별칭/family/fingerprint 일치
    return {"consumed": hit is not None, "match": hit, "keys": keys}
    # acceptance_criteria:
    #   - 같은 idea_id/normalized_title/alias/family/fingerprint 중 하나라도 일치 → consumed=True
    #   - 결정론: 동일 입력 → 동일 출력 (시계/AI 없음)

def append_consumed(ledger: dict, entry: dict, now: str) -> dict:
    """winner가 구체 프로젝트/MVP/repo가 됐을 때만 기록 (record_only_when 규율).
       now는 주입 (결정론 — Date.now 금지)."""
```

### 3.2 Diversity — 통합 동질화 측정 (P: diversity_guard, 복구효소)

```python
def measure_diversity(pool: list, recent_winners: list, sim, P: dict) -> dict:
    """집계는 결정론, 의미 유사도 sim(a,b)는 주입(임베딩=엔진/외부 책임).
       aox 4임계 + recreate unique_ratio 단일화."""
    keyword_coverage = top_k_coverage(pool, k=10)              # 결정론
    max_pair_count   = max_domain_pair_repeat(pool)            # 결정론 (Counter)
    avg_sim          = avg_pairwise(pool, sim)                 # 주입 sim 집계
    unique_ratio     = 1 - dup_ratio(pool, sim, thr=P["dup_cos"])  # recreate 신호
    winner_sim       = avg_pairwise(recent_winners, sim)       # aox 지속혁신 신호
    breaches = (
        (keyword_coverage >= P["keyword_coverage"]) +
        (max_pair_count   >= P["max_pair_count"]) +
        (avg_sim          >= P["avg_embedding_sim"]) +
        (winner_sim       >= P["winner_embedding_similarity"])
    )
    return {"triggered": breaches >= P["min_breaches"],
            "unique_ratio": unique_ratio, "winner_similarity": winner_sim,
            "metrics": {...}, "breaches": breaches}
    # acceptance_criteria:
    #   - ≥min_breaches(기본 2) 임계 초과 → triggered
    #   - unique_ratio < 0.5 별도 신호 (recreate island 재발산 트리거)
    #   - sim 주입 없이도 keyword/pair 신호는 산출 (부분 결정론)
```

### 3.3 Provenance — 계보 + 환류 (염기쌍 결합)

```python
def trace_winner(winner: dict, chain: dict) -> list:
    """explore: EVX winner → cix source_insight_id → idx → tcx → channel(CH-NNNN).
       exploit: seed → idea_trace kernel → genes(source projects). 결정론 walk."""

def winner_to_corpus_entry(consumed_entry: dict) -> dict:
    """★염기쌍: 구현된 explore winner → exploit 코퍼스 source stub.
       explore가 발굴·구현한 프로젝트를 recreate가 재조합할 재료로 변환."""
    return {
        "project": consumed_entry["implementations"][0]["project_name"],
        "repo": consumed_entry["implementations"][0].get("repo_url"),
        "origin": "explore",
        "source_chain": consumed_entry["source_chain"],
        "semantic_family": consumed_entry.get("semantic_family"),
        "readme_hint": consumed_entry["title"],
    }
    # acceptance_criteria:
    #   - 구현(implementations 존재)된 winner만 코퍼스 진입
    #   - origin=explore 태그로 exploit이 출처 추적 가능
```

### 3.4 Loop — 폐루프 드라이버 (나선 회전)

```python
def next_action(state: dict, P: dict) -> dict:
    """결정론 정책. explore↔exploit를 번갈되, 환류·다양성 게이트를 우선."""
    if state.get("pending_implemented_winner") and not state["winner_in_ledger"]:
        return {"action": "RECORD_CONSUMED", "why": "winner 구현됨 → 계보 폐쇄 (염기쌍)"}
    if state["diversity"]["triggered"]:
        return {"action": "REFRESH_INPUTS", "why": "동질화 → 입력 갱신(복구효소)",
                "target": "explore" if state["last_engine"] == "exploit" else "both"}
    if state["corpus_size"] < P["min_corpus_for_exploit"]:
        return {"action": "RUN_EXPLORE", "why": "코퍼스 미성숙 → 외부 신선 신호 우선"}
    if state["last_engine"] == "explore":
        return {"action": "RUN_EXPLOIT", "why": "신선 자산 누적 → 재조합 복리"}
    return {"action": "RUN_EXPLORE", "why": "explore↔exploit 균형 회전"}
    # acceptance_criteria:
    #   - 환류(RECORD_CONSUMED)가 최우선 — NoOpenLoop
    #   - diversity.triggered면 생성 전 REFRESH (수렴 차단)
    #   - 결정론: 동일 state → 동일 action
```

---

## 4. 결정론 경계 (지배 제약)

```text
HELIX-Core helper          → 순수 결정론 (stdlib only, 시계/네트워크/AI 없음)
  - 시간은 주입(now 인자), 의미유사도는 주입(sim 함수), 임베딩은 엔진/외부 책임
엔진 내부 (explore/exploit) → LLM 단계 = 메타층 (HELIX 경계 밖, 각 스킬 정본)
exploit 생성물 verdict 경로 → 결정론 불변 (ProjectGenome 규율 계승)
```

---

## 5. 완료 기준 (acceptance)

```text
HelixAcceptance
    SingleSourceLedger // 두 엔진이 한 ledger 계약 공유 (중복 0)
    UnifiedDiversity // aox 4임계 + recreate unique_ratio 한 함수
    ClosedLoopEdge // winner_to_corpus_entry로 explore→exploit 환류 존재 (염기쌍)
    DeterministicCore // core helper 전부 stdlib·주입식·시계 없음
    Federated // 엔진은 어댑터로 연결 (복사·흡수 아님)
    Tested // core 6종 unittest green + validate PASS
```
