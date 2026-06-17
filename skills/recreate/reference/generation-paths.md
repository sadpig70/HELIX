# generation-paths — 3경로 × 8 발산도구

> Recreate Phase 2 (`generate` 모드 / `/recreate generate`)의 정본.
> 분류는 직교(3경로), 발상은 풍부(8도구). 각 도구는 코퍼스 실례로 정박된다.

---

## 0. 데이터 타입

```python
Candidate = dict = {
    "name": str,                    # working name (과밀 어휘 금지)
    "gen_path": Literal["RECOMBINE","MUTATE","TRANSPLANT"],
    "tool": str,                    # 사용한 발산 도구
    "parts": list[dict],            # 재사용한 부품 (source project + reuse_cost)
    "applied_lenses": list[str],    # 적용한 lens
    "target_domain": str,
    "single_question": str,         # 새 프로젝트의 한 질문
    "novelty_claim": str,           # 왜 새로운가
    "layers": Optional[list[str]],  # LayerFusion일 때 계층 stack
    "idea_trace": Optional[dict],   # idea-layer: {kernel_id, method_archetype, recombination_hypothesis}
}
```

전역 규칙:
- 각 후보 `parts ≥ 2` source projects. `parts`가 비면 **기각** (코퍼스 기반성 강제).
- 이름·mechanism에 과밀 어휘 금지: `OVERUSED = [mesh, clearing-market, generic ledger, simple gate, escrow, marketplace]`.
- 목표 산출 K=12 → 차별화·선정 후 top 5.

---

## 1. RECOMBINE — ≥2 부품 합성

### 1.1 DistantHybridization
먼 domain이지만 같은 구조(evidence grammar)를 가진 2~4개를 합친다.

```python
def AI_distant_hybridize(inv, min_domain_distance=0.65) -> list[Candidate]:
    pairs = AI_pick_pairs(inv["primitive"],
                          domain_distance=">=0.65",      # domain 멀고
                          evidence_similarity=">=0.5")    # evidence 유사
    return [AI_fuse_operating_model(p) for p in pairs]
```
- 정박: `DriftDossier + ThermalPlumeStage + PnR` — 도메인(임상/해양/거버넌스) 멀지만 evidence grammar 동일.
- 정박: `FailureFutures = DroughtDesk + OrphanX` — one engine, two adapters.

### 1.2 LayerFusion
5 기능 계층에서 1개씩 뽑아 stack을 쌓는다.

```python
def AI_layer_fusion(layer_shelf) -> list[Candidate]:
    sensing  = AI_select_underused(layer_shelf["Sensing"])
    evidence = AI_select_complementary(layer_shelf["Evidence"], sensing)
    control  = AI_select_non_derivative(layer_shelf["Control"], sensing, evidence)
    release  = AI_select_distant_domain(layer_shelf["Release"], control)
    return [AI_synthesize_stack([sensing, evidence, control, release])]
```
- 정박: ContextCreep(Sensing) + ADPR(Evidence) + AfferentCore(Control) + LazarettoStage(Release) → "Boundary Release Stack".

### 1.3 ConflictCompiler
충돌하는 두 프로젝트를 일부러 붙여 새 tension을 만든다 (코퍼스의 L7_Tension을 *생성 도구로* 역전).

```python
def AI_conflict_compile(primitive_shelf) -> list[Candidate]:
    clashes = AI_find_conflicting_pairs(primitive_shelf)   # 전제·목적이 상충하는 쌍
    return [AI_compile_tension(c) for c in clashes]         # 충돌을 새 질문으로
```
- 정박: PowerRoam(compute가 전력 따라 이동) ⨉ SovMesh(sovereignty 고정) → "roaming이 sovereignty를 깨는 첫 지점 탐지".
- 충돌쌍 예: BuyBloc⨉RefusalOption, GenCert⨉DriftDossier, SlotGate⨉LoopKit.

### 1.4 ABCLink (idea-layer P6)
Swanson 문헌연결: A-B(부품1)+B-C(부품2)→ 직접 엣지 없는 **미검증 신규 A-C**. `DistantHybridization`을
gene 그래프 위에서 연산화한 것 — "먼 domain + 중간 evidence 유사도"를 중간항(B) 탐색으로 구조화한다.

```python
def abc_link(genes) -> list[Candidate]:
    kg = build_gene_graph(genes)                   # gene-extraction.md §7
    for A, C in distant_pairs(kg):                 # 직접 엣지 없는(미연결) 쌍
        B = AI_find_bridge(A, C, kg)               # 공유 control_primitive 등 중간항
        if B and AI_is_nonobvious(A, C, B):
            yield make_candidate(parents=[A, B, C], path="ABCLink")
```
- 정박: DriftDossier(A: 임상 drift 감지) — PnR(B: 비-응답 점수화) — ReleaseMesh(C: 배포 게이트) →
  중간항 PnR의 "absence scoring"이 A·C를 잇는 비자명 다리 → "배포되지 *않은* drift 보고의무".
- parts ≥ 2 (ABC는 자연히 ≥3). A-C가 기존 fingerprint/코퍼스명과 충돌하면 Phase2b hard-reject로 회수.
- 정본 → `idea-layer.md §5.6`.

---

## 2. MUTATE — 1 부품 × 렌즈로 축 교체

### 2.1 LensApply
코퍼스 lens를 적용해 축(axis)을 바꾼다.

```python
def AI_make_lens_apply(primitive_shelf, lens_palette) -> list[Candidate]:
    out = []
    for proj in primitive_shelf:
        for lens in AI_relevant_lenses(proj, lens_palette):
            out.append(AI_apply_lens(proj, lens, rule="기능 유지, axis 교체"))
    return out
```
- 정박: PowerRoam(공간 차익) →[L1→L13 축교체]→ SeasonBat(시간 차익). 같은 lens stack, 다른 axis.
- 정박: GenCert(trust) →[목적 교체]→ EndowFront(financing). 같은 L1→L13, 다른 목적.

### 2.2 GrammarMutation
기능은 유지하되 product grammar(어휘)만 완전히 바꾼다.

| 과밀 문법 | 변형 문법 |
|---|---|
| `mesh` | atlas / compiler / protocol / calculus |
| `market / clearing` | allocation ritual / priority schedule / constraint router |
| `gate / escrow / veto` | reflex / rehearsal / cooldown / release stage |
| `ledger only` | dossier / witness model / obligation chain |

- 정박: ReserveFlow+BuyBloc+RefusalOption →[market→rehearsal]→ "ShockRoute Rehearsal" (위기 전 tabletop 훈련).
- 주의: 신문법도 재포화 가능 → `vocab_registry` 동적 충돌검사로 완화.

### 2.3 NegativeSpaceInversion
기존 프로젝트가 다루지 않는 "비어 있는 행위"를 제품화한다.

```python
def AI_invert_negative_space(primitive_shelf) -> list[Candidate]:
    questions = [
        "누가 응답하지 않았는가?",      # PnR 일반화
        "누가 승인하지 않았는가?",
        "누가 release하지 않았는가?",
        "어떤 위험이 아직 stage 안 됐는가?",
        "어떤 evidence가 아직 duty chain에 안 묶였나?",
    ]
    return [AI_productize_absence(q, primitive_shelf) for q in questions]
```
- 정박: PnR(비-응답 점수화) →[일반화]→ "Proof of Non-Release" (release하지 *않은* 것의 정당성 증명).

---

## 3. TRANSPLANT — 메커니즘을 새 도메인/OS로

### 3.1 DomainTransplant
mechanism만 추출 → 도메인 명사 제거 → 새 도메인에서 재명명.

```python
def AI_transplant_domain(inv, layer_shelf) -> list[Candidate]:
    out = []
    for proj in inv["primitive"]:
        mech = AI_strip_domain_nouns(proj["mechanism"])     # 추상 메커니즘
        for tgt in AI_pick_target_domains(proj, inv["layer"]):
            out.append(AI_rename_as_new_problem(mech, tgt))
    return out
```
- 정박: 결제사기 스코어링 →[L11]→ CoverGate(바이오 인수).
- 정박: ThermalPlumeStage(해양 열방류) →[이식]→ "ComputePlume Stage"(데이터센터 열/탄소/물 timing).
- 정박: DriftDossier(임상 protocol drift) →[이식]→ "PolicyDrift Dossier"(AI 배포 policy drift).

### 3.2 SystemIntegration
여러 도메인을 단일 OS로 통합 (L19_Aggregation의 OS형).

```python
def AI_integrate_system(primitive_shelf) -> list[Candidate]:
    triads = AI_pick_complementary_triads(primitive_shelf)  # 상보적 3도메인
    return [AI_unify_as_os(t) for t in triads]
```
- 정박: Bio + PQC + Regulatory →[L19 통합]→ Qvidence(단일 OS).

---

## 4. 생성 PPR (Phase 2 전체)

```python
def generate_candidates(inv: dict, kernel: Optional[dict] = None, k: int = 12) -> list[Candidate]:
    [parallel]
    recombine = (AI_distant_hybridize(inv, 0.65)
                 + AI_layer_fusion(inv["layer"])
                 + AI_conflict_compile(inv["primitive"])
                 + abc_link(inv["genes"]))                 # idea-layer P6 (RECOMBINE 합류)
    mutate    = (AI_make_lens_apply(inv["primitive"], inv["lens"])
                 + AI_mutate_grammar(inv, banned=OVERUSED)
                 + AI_invert_negative_space(inv["primitive"]))
    transplant= (AI_transplant_domain(inv, inv["layer"])
                 + AI_integrate_system(inv["primitive"]))
    [/parallel]
    cands = recombine + mutate + transplant
    if kernel:                                             # idea-layer: 무작위 아닌 의도 지향 편향
        cands = bias_by_kernel(cands, kernel)              # problem_frame·lens_stack·anti_examples 반영
    cands = [c for c in cands if len(c["parts"]) >= 2]      # 코퍼스 기반성 강제
    cands = AI_dedupe_candidates(cands)[:k]
    if kernel:
        cands = generate_debate_evolve(cands, max_rounds=2)  # idea-layer P3 (발산 뒤 비판→진화)
    return cands
    # acceptance_criteria:
    #   - 각 후보 gen_path·tool·applied_lenses·single_question 보유
    #   - parts ≥ 2 (B 권장 3, 하한 2 강제)
    #   - 이름/mechanism 과밀 어휘 없음
    #   - kernel 제공 시 각 후보 idea_trace.kernel_id 보유 (idea-layer)

OVERUSED = ["mesh","clearing-market","generic ledger","simple gate","escrow","marketplace"]
```

> **idea-layer 편향·진화 (가산, kernel 있을 때만)**: `bias_by_kernel`은 3경로×8도구를 무작위가 아니라
> `kernel.problem_frame`/`lens_stack`로 목적 지향 편향하고, `anti_examples`를 회피한다.
> `generate_debate_evolve`는 발산 1회로 끝내지 않고 `reflection_critic`(feasibility/novelty/verifiability/
> weakness)→ 진화(흡수 재조합, 병합 아님)를 `max_rounds` 반복하다 안정화 시 조기 종료. kernel이 없으면
> 기존 1-shot 발산 그대로(동작 불변). 정본·시그니처 → `idea-layer.md §4·§5.3`.

산출: `.recreate/candidates.md` (각 후보의 조합·도구·lens·질문 + idea_trace).
