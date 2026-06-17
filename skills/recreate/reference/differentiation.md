# differentiation — 차별화 게이트 · 평가 · 수렴

> Recreate Phase 3~5 (`generate` 모드 후반 / `/recreate generate`)의 정본.
> 코퍼스가 README마다 수작업하던 "It differs from X"를 정량 자동화하고, 6축 평가로 선정한다.

---

## 1. 차별화 게이트 (Phase 3)

A의 정량 overlap + B의 derivative_tags 근거를 결합한다.

```python
Verdict = dict = {
    "candidate": str,
    "siblings": list[str],          # 의미 최근접 3개
    "overlap": float,               # 0(독립)~1(중복)
    "tag_clash": int,               # 공유 derivative_risk_tag 수
    "vocab_clash": bool,            # 과밀 어휘 충돌
    "verdict": Literal["distinct","needs_pivot","duplicate"],
    "pivot": Optional[str],
}

def differentiate(c, genes, vocab_registry) -> Verdict:
    siblings = AI_find_nearest(c, genes, k=3)               # 의미 최근접
    overlap  = AI_assess_overlap(c, siblings)               # 0~1 (A)
    tag_clash = AI_tag_overlap(c, siblings)                 # 공유 태그 수 (B)
    vocab_clash = any(t in vocab_registry
                      for t in AI_tokenize_naming(c["name"]))  # 결정론
    if overlap >= 0.7 or tag_clash >= 3:
        v, hint = "duplicate", AI_suggest_pivot(c, siblings)
    elif overlap >= 0.4 or tag_clash >= 2 or vocab_clash:
        v, hint = "needs_pivot", AI_suggest_pivot(c, siblings)
    else:
        v, hint = "distinct", None
    return {"candidate": c["name"], "siblings": siblings, "overlap": overlap,
            "tag_clash": tag_clash, "vocab_clash": vocab_clash,
            "verdict": v, "pivot": hint}
```

판정 규칙:

| 조건 | verdict | 처리 |
|---|---|---|
| `overlap ≥ 0.7` 또는 `tag_clash ≥ 3` | `duplicate` | 기각 또는 강제 pivot |
| `overlap ≥ 0.4` 또는 `tag_clash ≥ 2` 또는 `vocab_clash` | `needs_pivot` | 변형 후 재투입 |
| 그 외 | `distinct` | 통과 |

> **vocab_clash면 distinct여도 재명명 강제** (ContextCreep 교훈: 포화 어휘 회피).

### 1.1 동질화 연속신호 (idea-layer P1 보조)

`overlap`/`tag_clash`는 **후보↔코퍼스**의 이산 임계다. 여기에 **후보풀 내부**의 의미 동질화를 연속신호로
덧댄다 — 생성 규모를 키워도 고유 아이디어가 붕괴하는 현상(Si et al.)을 잡기 위함. 메타층이므로 `AI_` 임베딩 허용.

```python
# differentiate()의 verdict에 보조 필드로 병합 (이산 게이트는 불변)
unique_ratio = measure_homogenization(pool, genes).unique_ratio   # idea-layer §5.1
# unique_ratio < 0.5 (풀 절반 이상 의미중복) → K 늘리지 말고 enforce_diversity로 island 재발산
```

- 이산 verdict(distinct/needs_pivot/duplicate)는 그대로. `unique_ratio`는 **풀 수준** 보조신호로
  `avoidance_report.md`에 로깅된다(Phase2b DiversityGuard와 같은 측정, 다른 비교대상).
- 임계 0.8/0.5는 코퍼스 초기값(차용) — overlap 0.4/0.7과 **별개 축**, 성장 시 재보정. 정본 → `idea-layer.md §5.1`.

---

## 2. Vocab Registry (과밀 어휘 동적 충돌검사)

```python
OVERUSED_SEED = ["mesh","clearing","market","gate","escrow","veto",
                 "ledger","marketplace","option","clear"]

def build_vocab_registry(genes) -> list[str]:
    """코퍼스가 실제 사용한 이름 토큰을 누적. 결정론적."""
    return OVERUSED_SEED + flatten([g["vocab"] for g in genes])
```

- 코퍼스가 커질수록 레지스트리가 확장 → 차별화가 자동으로 강해진다 (공진화).
- GrammarMutation 신문법도 레지스트리에 누적되어 재포화를 완화한다.

---

## 3. Select-or-Integrate (Phase 4)

> **왜 select만으론 부족한가 (자기참조 근거).** 이 방법론 자신이 그 증거다 — recreate는
> `method_claude`(구조 강) 하나를 *고른* 게 아니라 `method_claude` + `chatgpf`(발산 강)를 *통합*해
> `method_integrated`가 되었고, 통합본이 양쪽을 능가했다. 여러 런타임/페르소나가 낸 후보가 **상보적**일 때,
> argmax(`select`)는 한쪽의 강점을 버린다. Phase 4는 먼저 상보 군집을 **통합**하고, 그 결과를 원본과 함께
> 6축으로 **선정**한다.

흐름: `차별화 통과 후보 → (4a) 상보성 탐지 → (4b) 통합 → (4c) 6축 선정`.

### 3.1 상보성 탐지 (4a) — `overlap`과 다른 신호

`overlap`(Phase 3)은 *결과물이 겹치는가*를 본다. `complementarity`는 *같은 문제를 다른 강점축으로 푸는가*를
본다. 한 후보쌍이 **overlap 낮음(distinct) + complementarity 높음**이면 통합 대상이다.

```python
Complementarity = dict = {
    "members": list[str],                 # 후보 이름들 (군집)
    "same_problem": float,                 # single_question/target_domain 의미 근접도 (0~1)
    "axis_divergence": float,              # 6축 점수 프로파일 거리 (서로 다른 축이 강함, 0~1)
    "score": float,                        # same_problem × axis_divergence
}

def detect_complementary(distinct_cands, scores) -> list[Complementarity]:
    """distinct 후보 중 '같은 문제·다른 강점' 군집을 찾는다."""
    clusters = []
    for group in AI_group_by_problem(distinct_cands):          # single_question/domain 근접끼리
        if len(group) < 2:
            continue
        same = AI_assess_problem_proximity(group)              # 같은 문제인가 (높을수록)
        div  = AI_axis_profile_distance([scores[c] for c in group])  # 강점축이 갈리는가
        comp = same * div
        if same >= 0.6 and div >= 0.5:                         # 같은 문제 + 강점 갈림
            clusters.append({"members": [c["name"] for c in group],
                             "same_problem": same, "axis_divergence": div, "score": comp})
    return clusters
    # 핵심 구분: overlap 높음 → duplicate(버림, Phase3). complementarity 높음 → integrate(합침, 여기).
    #            둘 다 낮음 → 무관한 독립 후보 (각자 select로).
```

### 3.2 통합 (4b) — `method_integrated` 생성 절차의 일반화

```python
def integrate(cluster: list[Candidate], scores) -> Optional[Candidate]:
    """상보 군집을 제3의 후보로 통합. 단순 병합이 아니라 골격+흡수의 위계 통합."""
    consensus = AI_extract_consensus(cluster)                  # 독립 수렴분 = 확정 기반
    strengths = AI_map_complementary_strengths(cluster, scores)# 각 후보의 강점축
    spine     = AI_pick_spine(cluster, by="구조적 직교성/골격 견고성")  # 등뼈 1개
    merged    = AI_make_absorb(spine, strengths, consensus)    # 골격에 나머지 강점 흡수(병합 아님)
    merged    = AI_resolve_conflicts(merged, cluster)          # 모순 해소 + 근거 명시
    merged["integrated_from"] = [c["name"] for c in cluster]   # 출처 보존
    merged["parents_gen_path"] = [c["gen_path"] for c in cluster]
    # 통합 게이트: 통합 후보가 원본 최고 6축점을 능가해야 채택. 아니면 폐기(원본을 select로).
    if AI_score_candidate(merged, SCORE_AXES) > max(scores[c["name"]] for c in cluster):
        return merged
    return None                                               # 통합 무익 → 원본 유지
    # 정박: method_claude+chatgpf 통합 = consensus(독립수렴 5가지) + spine(A의 3경로 골격)
    #       + absorb(B의 8발산도구) + conflict해소(경로 비직교성은 A채택). 결과가 양쪽 능가 → 채택.
```

`integrate`는 **항상 통합이 낫다고 가정하지 않는다** — 능가하지 못하면 폐기하고 원본을 살린다. 이 게이트가
"다양성을 위한 무분별한 합치기"를 막는다 (divergence ↔ convergence의 정직한 짝).

### 3.2a 통합 적용 조건 (언제 integrate가 부모를 능가하는가) — 실증 명문화

> 출처: run 006(양성)·run 007(음성) + 각각의 cross-model 합의 검증(`.recreate/crossmodel/CONSENSUS.md`,
> `round2/CONSENSUS-r2.md`). 통합 게이트(§3.2)는 **언제 통과하는가**를 경험적으로 좁힌 규칙이다.

**핵심 규칙**: 통합이 부모 최고 6축점을 능가하려면 **두 조건이 함께** 필요하다 —
1. **강한 same_problem** (`detect_complementary`의 통과는 하한일 뿐, 능가의 충분조건이 아님), 그리고
2. **구조적으로 정렬된(structurally-ordered) 상보축** — 부모들이 한 객체 위에서 자연스러운 순서/계열을
   이루는 축. 예: **시간축 lifecycle**(before→during→after), 인과 사슬, 파이프라인 단계.

```python
def integrate_likely_to_beat_parents(cluster) -> bool:
    same = AI_assess_problem_proximity(cluster)              # 0~1
    ordered = AI_has_structural_ordering(cluster)            # 시간/인과/계열 등 자연 순서 축인가
    unique = AI_integrated_unique_value(cluster)             # 부모 단독으로 못 보는 신가치(예: 단계 간 모순)
    # 능가 가능성: 자연 정렬축 + 통합 고유가치가 있어야 contract 확장 손실을 상쇄
    return same >= 0.6 and ordered and unique is not None
```

**메커니즘 (왜 그런가)**: 통합은 input contract를 넓혀 **buildability·boundary_clarity를 거의 항상 잃는다**.
이 손실은 통합 *전체*가 부모 단독으로는 불가능한 **고유가치**를 만들 때에만 상쇄된다.
- run 006(양성): lifecycle 정렬 → 통합이 **단계 간 모순(cross-stage inconsistency)**이라는 고유가치를 만들어
  손실을 상쇄. 합의 +0.150으로 채택.
- run 007(음성): 렌즈축/계층축은 자연 순서가 약해 통합이 **두 판정을 병렬 fold**할 뿐 새 고유가치가 없음 →
  contract만 넓어져 손실. 합의 −0.195로 기각. (D1 PolicyReleaseDutyWitness 4.645 < 부모 4.840.)

**실무 지침**:
- 통합 시도는 **자연 정렬축**(lifecycle/인과/파이프라인)을 가진 군집에 우선한다.
- **렌즈 ensemble**(같은 객체를 여러 판정으로 병렬 합성)·**임의 layer-stack**은 회의적으로 — 고유가치 없이
  contract만 넓히기 쉽다. 시도하더라도 게이트가 대개 기각함을 예상.
- 게이트 통과(부모 능가)는 **단일 평가자로 확정하지 말 것** — margin이 ±0.1 내로 근소하면 cross-model
  합의로 검증한다(`crossmodel/`). 합의는 단일 판정의 margin을 양방향으로 증폭해 결론을 선명히 한다
  (W6 +0.03→+0.150, D1 −0.06→−0.195).

### 3.3 6축 선정 (4c)

원본 distinct 후보 + 채택된 통합 후보를 **한 풀**에 넣고 평가한다.

```python
def select_or_integrate(cands, genes, vocab, k=5) -> list[Candidate]:
    # ① Phase 3 게이트 통과분 수집 + 점수
    distinct, scores = [], {}
    for c in cands:
        d = differentiate(c, genes, vocab)
        if d["verdict"] == "duplicate":
            continue
        if d["verdict"] == "needs_pivot":
            c = AI_make_pivot(c, d["pivot"])
            d = differentiate(c, genes, vocab)
            if d["verdict"] != "distinct":
                continue
        distinct.append(c)
        scores[c["name"]] = AI_score_candidate(c, axes=SCORE_AXES)
    # ② 4a 상보성 탐지 → 4b 통합 (채택 시 풀에 추가; 원본은 유지)
    pool = list(distinct)
    for cl in detect_complementary(distinct, scores):
        merged = integrate([c for c in distinct if c["name"] in cl["members"]], scores)
        if merged:
            pool.append(merged)
            scores[merged["name"]] = AI_score_candidate(merged, axes=SCORE_AXES)
    # ③ 6축 top-K (통합 후보가 보통 상위 — 양쪽 강점 → 높은 novelty+reuse_leverage)
    return AI_top_k([(scores[c["name"]], c) for c in pool], k)
    # acceptance_criteria:
    #   - 선정분은 verdict=distinct(또는 통합 후보) + 6축 모두 임계 이상
    #   - 통합 후보는 integrated_from 출처 + 원본 능가 근거를 보유
```

### 6축 루브릭

| 축 | 의미 | 임계 (0~1) | 출처 |
|---|---|---|---|
| `reuse_leverage` | 기존 부품 재사용 효율 (높을수록 빠른 MVP) | ≥ 0.5 | A |
| `novelty` | 코퍼스 대비 차별성 | ≥ 0.6 | A,B |
| `domain_demand` | 도메인 수요/시급성 | ≥ 0.4 | A |
| `buildability` | stdlib-only·15분 노드 분해성 (B: "≤2일") | ≥ 0.5 | A,B |
| `boundary_clarity` | "~가 아니다"를 명확히 그을 수 있는가 | ≥ 0.5 | A |
| `system_potential` | 단발 MVP보다 생성장치 가능성 | ≥ 0.3 | B |

> `novelty`가 최우선 가중. `domain_demand`·`system_potential`은 외부 신호 없이 AI 판단 → 보수적.
> 통합 후보는 보통 `novelty`(양쪽 발상)와 `reuse_leverage`(양쪽 부품)에서 원본을 능가한다.

### multi-runtime 결합

여러 런타임(codex/kimi/antigravity/grok/Claude)이 각자 `generate`를 돌려 후보 풀을 합치면, 상보성 탐지는
**모델 간 상보**까지 본다 — 한 모델이 구조적 후보를, 다른 모델이 발산적 후보를 냈을 때 `integrate`가 그 둘을
제3으로 합친다. 이는 recreate 자신이 만들어진 방식(Claude 산출 + codex 산출 → 통합)의 자동 재현이다.
단, 생성은 여러 모델이라도 `AI_score_candidate`·`integrate`를 한 모델이 단독 수행하면 그 평가자 편향이
다양성을 좁힌다 → 가능하면 점수·통합도 cross-model 합의로 굴린다.

### 3.4 토너먼트 교차검증 + idea_fit (idea-layer P2 보조)

6축 절대점수(argmax)는 캘리브레이션이 약하다. **pairwise Elo 토너먼트를 병행**해 절대점수 top과
토너먼트 top의 **불일치**를 드러내고, 갈리면 cross-model 합의(`§3.2a`/idea-layer P5)로 판정한다.
kernel이 있으면 `idea_fit` 보조점수(problem_fit·determinism·proofability 등)를 6축에 더한다.

```python
def select_with_tournament(pool, scores, kernel=None, k=5) -> list[Candidate]:
    abs_top = AI_top_k([(scores[c["name"]], c) for c in pool], k)   # 현행 6축 절대점수
    elo_top = tournament_select(pool, k_top=k)                      # idea-layer §5.2 pairwise Elo
    if set(map(name, abs_top)) != set(map(name, elo_top)):         # 불일치 → 단독 확정 금지
        return cross_model_resolve(abs_top, elo_top, pool)         # cross-model 합의로 판정
    final = abs_top
    if kernel:                                                     # idea_fit 보조점수 (대체 아님)
        final = AI_rerank_by_idea_fit(final, kernel)               # determinism·proofability·nonoverlap 가중
    return final
    # acceptance_criteria:
    #   - 절대점수 top과 토너먼트 top의 불일치를 candidates.md에 보고
    #   - margin < 0.10 → needs_cross_review (단일 평가자 확정 금지)
    #   - idea_fit은 6축을 대체하지 않고 보조 (determinism 가중 최상)
```

- 토너먼트는 **현행 6축 선정을 대체하지 않는다** — 병행해 불일치를 신호로 쓴다(둘 다 동의하면 그대로).
- kernel 없으면 기존 `select_or_integrate` 그대로(동작 불변). 정본 → `idea-layer.md §5.2`.

---

## 4. 실증 (Phase 5) — 필수 자기검증

**후보 0개 산출이면 방법론 실패로 본다.** top-K 각 후보를 brief로 풀어 5개 check를 강제한다.

```python
def prove(top: list[Candidate]) -> list[Candidate]:
    proven = []
    for c in top:
        brief = AI_write_candidate_brief(c)   # 조합·근거·차별점·single_question·예상 verdict_scheme
        ok = AI_verify_brief(brief, checks=[
            "uses >= 2 source projects",
            "no overused vocab in name/mechanism",
            "has explicit differentiation vs nearest siblings",
            "fits cli_triplet + stdlib-only skeleton",
            "single_question is answerable by a deterministic engine",   # ↓ EvaluatorGate로 승격
        ])
        if ok and evaluator_gate(c).ok:        # idea-layer P4: 결정론 답변가능을 게이트로 명문화
            proven.append({**c, "brief": brief})
    assert len(proven) >= 1, "RECREATE FAILED: zero proven candidates"
    return proven
```

> **EvaluatorGate (idea-layer P4)**: 5-check의 마지막 "결정론 엔진 답변가능"을 명시 게이트로 승격한다.
> `evaluator_gate`는 `engine_decidable ∧ verdict_machine_checkable ∧ evaluate_definable`을 검사 —
> FunSearch/AlphaEvolve의 "machine-verifiable evaluator가 있을 때만 자율생성 유효" 교훈을 recreate의
> 결정론 verdict engine에 부여한다. REJECT 시 Phase2 롤백(비싼 구현 전 차단). 정본 → `idea-layer.md §5.4`.

brief 형식 (각 후보):

```text
## {Name}
- gen_path / tool: {RECOMBINE|MUTATE|TRANSPLANT} / {tool}
- 조합 (parts): {source projects + reuse_cost}
- applied lenses: {L...}
- single_question: "{이 X에 대해 Y인가?}"
- 예상 verdict_scheme: {3/4-way}
- 차별점: {최근접 siblings 대비 왜 다른가}
- boundary: "이것은 ~가 아니다"
```

산출: `.recreate/candidates.md`에 차별화 verdict + 점수 + brief 누적.
