# PRODUCTION-LINE — HELIX 연속생산을 pg로 프로그래밍한 공장 도급 작업

> pg는 작업의 입출력을 타입으로 정의하고(데이터), 조건·분기·반복으로 흐름을 제어한다(제어).
> 그래서 여러 도급 단위(스킬=하청 contractor)가 타입 계약으로 자재를 넘기는 **공장 생산라인**도
> 프로그래밍 가능하다. 본 문서는 HELIX 연속생산을 그 형태로 짠 pg 프로그램이다.

---

## §1. 자재 정의 — 라인을 흐르는 타입 I/O (programming-level data)

```python
# 도급 단위가 주고받는 "자재(part)"를 타입으로 정의 — 계약의 핵심
Channel       = dict = {"id": str, "format": Literal["news","paper","patent","oss","std","vc","gov"],
                        "orthogonality": float}
ChannelCatalog= dict = {"version": str, "channels": list[Channel], "total": int}   # ≥80
TrendReport   = dict = {"industry_trend_md": str, "domains_covered": int}
Insight       = dict = {"id": str, "layer": Literal["L6_Gap","L7_Tension","L9_Counterfactual","L10_Generative"],
                        "evidence": list[dict]}
InsightSet    = dict = {"insights": list[Insight], "layer_dist": dict[str,int]}    # 5/5/5/5
Scores6       = dict = {"novelty": float, "generativity": float, "defensibility": float,
                        "compounding": float, "surprise": float, "coherence": float}
Idea          = dict = {"id": str, "title": str, "domains": list[str],
                        "source_insight_id": str, "scores": Scores6}
IdeaPool      = dict = {"ideas": list[Idea], "round_id": str}                      # top 24
Winner        = dict = {"id": str, "title": str, "votes": int, "provenance_model": str}
EvaluatedWin  = dict = {"consensus": Winner, "innovation": Winner}
DesignSeed    = dict = {"name": str, "single_question": str, "sources": list[str], "verdict_scheme": list[str]}
# 백본 자재 (core/)
LedgerEntry   = dict = {"idea_id": str, "title": str, "origin": Literal["explore","exploit"],
                        "implementations": list[dict]}
DiversityRep  = dict = {"triggered": bool, "breaches": int, "metrics": dict}
CorpusEntry   = dict = {"project": str, "origin": str, "semantic_family": str}     # 염기쌍 산출
```

## §2. 도급 단위(contractor) — TaskSpec: 입력계약 → 출력계약 + 검수 + 실패전략

```python
# 각 스킬 = 하청. 입력 타입을 받아 출력 타입을 납품. 검수(acceptance) 통과해야 다음 공정.
Contractor = dict = {
    "name": str, "input_type": type, "output_type": type,
    "acceptance": list[str], "failure_strategy": Literal["retry","redesign","handoff"],
    "max_retry": int,
}
LINE: list[Contractor] = [
    {"name":"sdx",  "input_type": None,          "output_type": ChannelCatalog,
     "acceptance":["total>=80","orthogonality 평균>=floor"], "failure_strategy":"retry","max_retry":2},
    {"name":"tcx",  "input_type": ChannelCatalog,"output_type": TrendReport,
     "acceptance":["domains_covered>=14"], "failure_strategy":"retry","max_retry":2},
    {"name":"idx",  "input_type": TrendReport,   "output_type": InsightSet,
     "acceptance":["layer_dist==5/5/5/5"], "failure_strategy":"retry","max_retry":2},
    {"name":"cix",  "input_type": InsightSet,    "output_type": IdeaPool,
     "acceptance":["len(ideas)==24","scores.pass>=6.0"], "failure_strategy":"redesign","max_retry":2},
    {"name":"evx",  "input_type": IdeaPool,      "output_type": EvaluatedWin,
     "acceptance":["consensus.votes>=2","5S/3R/3X"], "failure_strategy":"retry","max_retry":2},
]
```

## §3. 조건·분기 (condition / branch)

```python
def AI_route_by_capability(env: dict, line: list) -> list[Contractor]:
    """분기 ①: 환경 능력 — cross-model 가능하면 full, 아니면 standalone 라인으로 도급 교체."""
    if env["cross_model_baseline"] == "available":
        return line                                  # 정규 도급 (cix/evx)
    elif env["cross_model_baseline"] == "unavailable":
        return swap(line, {"cix": "sa-icx", "evx": "sa-evx"})   # 단독 하청으로 교체 (.sa-*)
    else:
        return mark_partial(line)                    # degraded → 부분 검수

def AI_route_by_diversity(rep: DiversityRep, last_strand: str) -> str:
    """분기 ②: 동질화 측정 결과로 어느 입력공정을 재가동할지 (복구효소 배선)."""
    if not rep["triggered"]:
        return "proceed"
    if "keyword_coverage" in rep["metrics_breached"]:   return "refresh:sdxx"   # 입력(채널)
    if "insight_repeat"  in rep["metrics_breached"]:    return "refresh:idxx"   # 인사이트
    return "refresh:cixx"                                                       # 출력(카테고리)

def AI_gate_winner(winner: Winner, ledger: dict) -> str:
    """분기 ③: 백본 ledger 검수 — 이미 소모면 반려, 신선이면 통과 (재사용 차단 게이트)."""
    if is_consumed({"idea_id": winner["id"], "title": winner["title"]}, ledger)["consumed"]:
        return "reject:re-steer"     # cixx 조향으로 재생성
    return "accept"
```

## §4. 반복 (loop) — 4종

```python
# 반복 ① 라인 재시도 (공정별 max_retry)
def run_stage(c: Contractor, material) -> Part:
    for attempt in range(c["max_retry"] + 1):
        out = AI_invoke(c["name"], material)
        if AI_verify(out, c["acceptance"]):
            return out
        if attempt >= 1 and c["failure_strategy"] == "redesign":
            c["ppr"] = AI_redesign(c, out.failure)        # pg로 도급 재설계
    raise StageFailure(c["name"])

# 반복 ② 수렴 루프 (cix 생성-비판-진화: 안정화까지)
def converge(pool: IdeaPool, max_rounds=2) -> IdeaPool:
    for r in range(max_rounds):
        weak = [i for i in pool["ideas"] if AI_critique(i).novelty < THRESH]
        if not weak: break                               # 안정화 → 조기 종료
        pool = evolve(pool, weak)
    return pool

# 반복 ③ island 재발산 (다양성 미달 시 미사용 도메인으로 재생성)
def enforce_diversity(pool, sim, floor=0.5):
    while unique_ratio(pool, sim) < floor:               # 복구효소 — K 늘리지 말고 재발산
        pool = regenerate(pool, focus=AI_find_untouched_axes(pool))
    return pool

# 반복 ④ 생산 라운드 (목표 winner 수 / 예산까지)
#   → §5 메인 프로그램에서 while로 구동
```

## §5. 메인 공장 프로그램 — 타입 I/O × 분기 × 반복 (전부 결합)

```python
def run_factory(target_winners: int, budget_tokens: int, env: dict) -> list[DesignSeed]:
    """HELIX 연속생산. 도급 라인을 라운드로 반복, 분기로 경로 결정, 백본으로 자재 관리."""
    ledger = load_ledger(".helix/ledger.json")           # 백본 자재고
    corpus: list[CorpusEntry] = load_corpus()
    seeds: list[DesignSeed] = []
    last_strand = None

    while len(seeds) < target_winners and budget_remaining(budget_tokens) > 0:   # 반복 ④
        action = next_action({"last_engine": last_strand, "corpus_size": len(corpus),
                              "diversity": last_diversity})                       # 백본 루프 드라이버
        # ─ 분기: explore 가닥 (세계 스캔 도급 라인) ─
        if action["action"] in ("RUN_EXPLORE", "REFRESH_INPUTS"):
            line = AI_route_by_capability(env, LINE)                              # 분기 ①
            if action["action"] == "REFRESH_INPUTS":
                inject_steering(line, action["target"])                          # sdxx/idxx/cixx 주입
            material = None
            for c in line:                                                       # 도급 라인 직렬
                material = run_stage(c, material)                                # 반복 ①(검수+재시도)
                if c["name"] == "cix":
                    material = enforce_diversity(converge(material), sim)        # 반복 ②③
            winner = material["consensus"]
            if AI_gate_winner(winner, ledger) == "reject:re-steer":              # 분기 ③
                last_diversity = {"triggered": True}; continue                   # 재조향 후 다음 라운드
            seed = AI_to_design_seed(winner); last_strand = "explore"
        # ─ 분기: exploit 가닥 (코퍼스 재조합 도급) ─
        else:  # RUN_EXPLOIT
            seed = run_recreate(corpus, ledger); last_strand = "exploit"

        # 공통 후공정: 구현 → 검수 → 자재고 환류 (염기쌍)
        seeds.append(seed)
        built = AI_handoff_to_pgf(seed)                  # transcription: seed → pgf full-cycle → 구현
        if built.implemented:
            append_consumed(ledger, to_entry(built), now=env["now"])            # 재사용 차단 등록
            if built.origin == "explore":
                corpus.append(winner_to_corpus_entry(to_entry(built)))           # explore winner → 코퍼스
        last_diversity = measure_diversity(recent_pools(), recent_winners(seeds), sim)

    return seeds
    # acceptance_criteria:
    #   - 각 도급 출력이 출력_type 계약·acceptance 충족 (공정 검수)
    #   - 모든 winner가 ledger 신선 (재사용 0)
    #   - 라운드마다 동질화 측정 → triggered면 다음 라운드 입력 갱신 (수렴 차단)
    #   - explore 구현분은 코퍼스 환류 (복리 — NoOpenLoop)
```

## §6. 실행 전 PPR 시뮬레이션 (사전검증 — 라인 멈춤 없이 미리 본다)

```python
def AI_simulate_factory(target=3, env={"cross_model_baseline":"unavailable"}) -> SimVerdict:
    # 심볼릭 실행: 자재 흐름·분기·반복을 돌려 병목/실패를 예측
    line = AI_route_by_capability(env, LINE)   # → cix/evx 가 sa-icx/sa-evx 로 교체될 것
    assert line_uses(line, "sa-icx"), "단독환경 → standalone 도급 라인 예측"
    # 반복④ 종료성: budget/target 중 먼저 닿는 쪽 → 무한루프 없음
    # 분기③ 재조향: 첫 라운드 winner가 코퍼스 소모분과 충돌하면 re-steer 1회 예측
    return SimVerdict(verdict="GO", predicted_path="standalone",
                      risks=["budget 소진 시 target 미달 가능 → 부분 산출 보존"])
    # → 라인 안 돌리고도 "단독환경이면 sa-* 도급으로 자동 교체"를 사전 확인
```

---

## 메타 명제

```text
공장 도급 작업 = 타입 자재(§1) + 도급 계약(§2) + 분기(§3) + 반복(§4) 을 메인 프로그램(§5)으로 결합.
pg는 이 전부를 programming-language 수준으로 표기하고, AI 런타임이 실행하며,
PPR 시뮬레이션(§6)으로 가동 전 검증한다. → 아무리 복잡한 다단계 도급도 설계·시뮬·수행 가능.
```
