# gene-extraction — 3축 ProjectGene 추출

> Recreate Phase 0~1 (`map` 모드 / `/recreate map`)의 정본.
> 코퍼스의 각 프로젝트를 형태·속성·기능 3축으로 동시에 환원한다.
>
> **재료 출처**: 1차는 각 폴더 `README.md`(코드 없음). `mechanism`/`verdict_scheme`/`adapter_contract`가
> README만으로 모호하면 2차로 `github.com/sadpig70/{repo}`(=폴더명)의 코드·`.pgf/DESIGN-*.md`를 fetch해
> 보강한다. 보강분은 gene에 출처를 표기한다.

---

## 1. ProjectGene 스키마

```python
from typing import Literal, Optional

ProjectGene = dict = {
    # --- 식별 ---
    "project": str,                 # 표시명
    "repo": str,                    # 폴더/repo명
    "domain": str,                  # 적용 도메인 (bio/energy/robotics/finance/AI-ops/...)

    # --- 축 1: 형태 (archetype) — 어떤 엔진 골격을 재사용하는가 ---
    "archetype": Literal["Gate","Mesh","Clearing","Index","Ledger","Stage","Appraisal"],

    # --- 축 2: 속성 (primitive) — 부품의 인터페이스와 어휘 ---
    "mechanism": str,               # 실제 작동 원리 (한 줄)
    "evidence_model": str,          # 입력 데이터 구조
    "control_primitive": str,       # 시스템이 개입하는 방식
    "artifact_type": str,           # 출력물 형태
    "grammar": str,                 # product grammar (어휘)

    # --- 축 3: 기능 (layer) — stack의 어느 계층 슬롯인가 ---
    "layer": Literal["Sensing","Evidence","Control","Allocation","Release"],

    # --- 변형/검증 메타 ---
    "lens_stack": list[str],        # 코퍼스 Provenance에서 역추출한 L1~L25
    "verdict_scheme": list[str],    # skeleton k-way verdict 토큰
    "adapter_contract": Optional[str],  # 도메인 차이를 격리하는 단일 계약 (예: FragilitySignal)
    "has_ledger": bool,             # hash-chained ledger 유무
    "boundary": str,                # "~가 아니다" 선언
    "vocab": list[str],             # 이름 어휘 토큰 (중복 회피용)
    "derivative_risk_tags": list[str],  # 파생성 검사 태그
}
```

---

## 2. 축 1 — 7 아키타입 (형태)

코퍼스는 7개 형태로 수렴한다. 이 카탈로그가 재조합·이식의 부품 목록이다.

| Archetype | 골격 (engine shape) | 코퍼스 실례 |
|---|---|---|
| **Gate** | 입력 → 독립 규칙 N개 → 가장 심각한 verdict | SettleMesh, SlotGate, VetoEscrow, SpendMesh, ReleaseMesh |
| **Mesh** | heterogeneous → normalize → assess → price → ledger | AgentMesh, PqcMesh |
| **Clearing** | supply/demand → 우선순위 청산 → posture | ColdMkh, ReserveFlow, BuyBloc |
| **Index** | observations → score → tier | ENLI, PnR, ClimateMesh, FlowMesh, LoopKit |
| **Ledger** | envelope → hash → attestation | ADPR, AgentPACT, RoboTrace |
| **Stage** | profile → 단계화 스케줄 | LazarettoStage, ThermalPlumeStage |
| **Appraisal** | asset → simulate → bankability | WasteStack, SeasonBat, EndowFront, FailureFutures, GenCert, CoverGate |

분류 휴리스틱:
- verdict가 "가장 심각한 규칙 채택"이면 → **Gate**.
- 이종 입력을 한 canonical record로 정규화 + 역할 배정 + ledger면 → **Mesh**.
- supply·demand 두 책을 우선순위로 매칭하면 → **Clearing**.
- 관측 → 점수 → tier/band면 → **Index**.
- 핵심 산출이 tamper-evident hash chain 자체면 → **Ledger**.
- 시간축 단계 스케줄·rollback trigger면 → **Stage**.
- 자산을 시뮬레이션해 수익성/지속성 판정이면 → **Appraisal**.

> 경계 사례는 주축 1개 + 보조축 표기 허용 (예: `Appraisal+Ledger`).

---

## 3. 축 2 — primitive (속성) 추출 규칙

| 필드 | 추출 소스 | 예 (ContextCreep) |
|---|---|---|
| `mechanism` | "How It Works"/엔진 요약 | boundary-crossing path ranking |
| `evidence_model` | 입력 스펙(JSON/CSV/YAML 스키마) | manifest + tool policy + context schema |
| `control_primitive` | 시스템 개입 방식 | mitigation cut point |
| `artifact_type` | 출력물 형태 | ranked attack-path report |
| `grammar` | 이름·문법 어휘 | dossier / path analysis |

`mechanism`은 **도메인 명사를 제거한 추상형**으로 쓴다 — TRANSPLANT 도구가 이 추상형을 재사용한다.
예: "robot OS 업데이트 staged rollout" → mechanism: "staged admission with rollback gate".

---

## 4. 축 3 — 5 기능 계층 (layer)

stack 조립 시 각 계층에서 1개씩 뽑는다 (LayerFusion 도구의 입력).

| Layer | 역할 | 후보 프로젝트 |
|---|---|---|
| **Sensing** | 위험/변화 감지 | ENLI, ContextCreep, ClimateMesh, DriftDossier, FlowMesh |
| **Evidence** | 증거/출처 고정 | ADPR, Qvidence, RoboTrace, PnR, AgentPACT |
| **Control** | 개입/중단/우회 | AfferentCore, SlotGate, VetoEscrow, LoopKit, SpendMesh |
| **Allocation** | 자원/권리 배분 | ReserveFlow, BuyBloc, PowerRoam, ColdMkh, CoverGate |
| **Release** | 배포/방출/스테이징 | LazarettoStage, ThermalPlumeStage, ReleaseMesh, ForgeQuarantine |

> 형태(archetype)와 기능(layer)은 **직교 축**이다. 예: ClimateMesh는 형태=Index, 기능=Sensing.

---

## 5. Lens Palette (L1~L25) — 코퍼스에서 역추출

변형 연산자는 임의 생성하지 않는다. 코퍼스가 Provenance에 명시한 것을 그대로 쓴다.

| Lens | 의미 | 코퍼스 실례 |
|---|---|---|
| `L1_DirectionReversal` | 누가 비용/증명/공급하는가 반전 | CoverGate, GenCert, EndowFront, SeasonBat, BuyBloc, PowerRoam |
| `L3_CostInversion` | 비용 부담 주체 반전 | CoverGate |
| `L6_Gap` | 아무도 책임 안 지는 공백 메움 | InferMesh, AgentMesh |
| `L7_Tension` / `L7_FailureAsFeature` | 긴장·실패를 자산화 | CertMesh, SettleMesh, FailureFutures |
| `L8_SideEffectMining` | 부산물을 제품으로 | WasteStack, SignalMesh |
| `L9_Counterfactual` | "만약 X가 Y처럼 규제/성숙했다면" | SpendMesh, ReleaseMesh, ClimateMesh |
| `L9_ScaleShift` | 단일 → 스웜/블록 | PowerRoam, BuyBloc |
| `L10_Generative` | 추상 상품화 → 희소 기질로 이동 | ColdMkh, FlowMesh, SovMesh |
| `L11_DomainTransplant` | A 메커니즘을 B로 이식 | CoverGate(결제사기→바이오), ClimateMesh(사이버→기후) |
| `L13_FrequencyShift` | 연속 → 1회/계절 | GenCert, EndowFront, SeasonBat |
| `L17_ConstraintSubstitute` | 구속 제약을 다른 제약으로 | PowerRoam, SlotGate, WasteStack |
| `L19_Aggregation` | 분산 → 단일 책/거래소 | ColdMkh, ReserveFlow, PqcMesh |
| `L24_BoundaryRedraw` | 경계(궤도/지상) 재설정 | OrbiRoam |
| `L25_StockToFlow` | 재고 → 흐름권 | ReserveFlow |

> 새 코퍼스에서 미등록 lens를 만나면 팔레트에 추가하되 `(inferred)` 플래그를 단다.

---

## 6. 추출 PPR

```python
def build_genes(readmes: list[str]) -> list[ProjectGene]:
    """각 README를 3축 ProjectGene으로 환원."""
    genes = []
    for md in readmes:
        g = {
            "archetype": AI_classify_archetype(md),        # 축1
            "mechanism": AI_summarize_mechanism(md),        # 축2 (도메인명사 제거 추상형)
            "evidence_model": AI_extract_evidence(md),
            "control_primitive": AI_extract_control(md),
            "artifact_type": AI_extract_artifact(md),
            "grammar": AI_tag_grammar(md),
            "layer": AI_assign_layer(md),                   # 축3
            "lens_stack": AI_reverse_lens(md),              # Provenance 역추출, 미기재 시 (inferred)
            "verdict_scheme": AI_extract_verdicts(md),
            "adapter_contract": AI_detect_contract(md),
            "has_ledger": AI_detect_ledger(md),
            "boundary": AI_extract_boundary(md),
            "vocab": AI_tokenize_naming(md),
            "derivative_risk_tags": AI_tag_derivative(md),
        }
        genes.append(g)
    return genes
    # acceptance_criteria:
    #   - 코퍼스 전체 3축(archetype/primitive/layer) 비어있지 않음
    #   - lens_stack 추론분은 (inferred) 플래그
    #   - vocab은 결정론적 토큰화 (소문자, 구분자 분리)

def build_inventory(genes: list[ProjectGene]) -> dict:
    [parallel]
    archetype_shelf = AI_group_by(genes, "archetype")
    primitive_shelf = AI_extract_reusable_parts(genes)     # engine/contract/verdict/ledger
    layer_shelf     = AI_group_by(genes, "layer")
    lens_palette    = AI_dedupe_lenses(genes)
    [/parallel]
    vocab_registry  = flatten([g["vocab"] for g in genes]) # 결정론: 코드로
    return {"archetype": archetype_shelf, "primitive": primitive_shelf,
            "layer": layer_shelf, "lens": lens_palette, "vocab": vocab_registry}
```

산출: `.recreate/genes.json` + `.recreate/inventory.md`.

---

## 7. Gene Graph — ABCLink 기질 (idea-layer P6)

`genes`를 경량 지식그래프(KG)로 올리면 RECOMBINE의 `ABCLink`(Swanson A-B-C)가 *직접 엣지 없는* 두
gene 사이의 중간항을 연산으로 찾는다 — 기존 `DistantHybridization`("먼 domain + 중간 evidence 유사도")의
**구조화**다. 메타 파이프라인층이므로 `AI_` 허용(생성물 verdict 경로 아님).

```python
def build_gene_graph(genes: list[ProjectGene]) -> GeneGraph:
    """SciAgents식 경량 온톨로지. 노드=gene, 엣지=공유 (mechanism/control_primitive/vocab/lens)."""
    g = GeneGraph()
    for gene in genes:
        g.add_node(gene["project"], axes=(gene["archetype"], gene["layer"]))
    for a, b in all_pairs(genes):
        shared = AI_shared_primitives(a, b)        # 공유 mechanism/control/vocab/lens
        if shared:
            g.add_edge(a["project"], b["project"], via=shared)
    return g
    # acceptance_criteria:
    #   - 엣지는 공유 근거(via)를 보유 (감사 가능)
    #   - 직접 엣지 없는 쌍 = ABCLink 후보 (generation-paths.md §1.1 abc_link 입력)
```

산출: `.recreate/inventory.md`에 gene_graph 요약(노드/엣지 수 + distant_pairs 후보). 정본 → `idea-layer.md §5.6`.
