---
name: pgfr-combo
description: "PGF-based project recombination methodology. 기존 프로젝트 포트폴리오를 분석·분해·재조합하여 새로운 프로젝트를 설계하는 PGF 스킬. Triggers: 프로젝트 재조합, 프로젝트 통합, 기존 프로젝트로 새 프로젝트, recombination, project combo, mesh of meshes, 프로젝트 믹스, 프로젝트 합성"
user-invocable: true
argument-hint: "recombine [portfolio-path] [goal]"
---

# PGFR-COMBO: PGF Project Recombination Methodology

> 기존 프로젝트를 부품처럼 분해하고, 의미 있는 조합을 발견하여 새 프로젝트로 만드는 PGF 기반 방법론.

## When to Use

- 기존 프로젝트 포트폴리오가 10개 이상이고, 중복·공통 인프라·시너지가 보일 때
- 새로운 시장/문제를 해결하기 위해 기존 자산을 재사용하고 싶을 때
- "Mesh of Meshes", "플랫폼화", "공통 레이어 추출" 같은 통합 전략을 설계할 때
- PGF `discover`/`create` 이전에, **기존 산출물을 원료로 삼는 사전 단계**로 활용

## Core Concepts

| Term | Meaning |
|------|---------|
| **Atom** | 프로젝트를 더 쪼갤 수 없는 한 가지 메커니즘 (예: `hash-only provenance log`, `sybil filtering`, `double auction`) |
| **Kernel** | 여러 프로젝트가 공유하는 핵심 인프라 역량 (예: `Attestation Kernel`, `Clearing Kernel`) |
| **Binding** | 두 Atom을 합쳐 새로운 기능이 되게 하는 인터페이스/규칙 |
| **Pattern** | 재조합의 반복 가능한 템플릿 (Vertical Stack, Horizontal Platform, Kernel Extraction, Mashup, Federation) |
| **Opportunity Card** | 하나의 재조합 아이디어를 요약한 1페이지 명세 |

## Gantree: Recombination Pipeline

```text
PGFR-COMBO
├── 1. Inventory
│   ├── 1.1 AI_scan_portfolio()          # 모든 README / DESIGN / spec 수집
│   └── 1.2 AI_extract_atoms()           # 프로젝트 → Atom 리스트
├── 2. Decomposition
│   ├── 2.1 AI_identify_mechanisms()     # 메커니즘 분류
│   ├── 2.2 AI_identify_assets()         # 코드, 스키마, 스펙, CLI 도구
│   └── 2.3 AI_tag_domains()             # 도메인/성숙도/의존성 태깅
├── 3. Affinity Mapping
│   ├── 3.1 AI_build_mechanism_matrix()  # Atom × Atom 공유/중복 매트릭스
│   ├── 3.2 AI_detect_gaps()             # 누락된 연결고리 탐지
│   └── 3.3 AI_find_kernels()            # 공통 Kernel 후보 도출
├── 4. Recombination
│   ├── 4.1 AI_apply_patterns()          # 5가지 패턴 적용
│   ├── 4.2 AI_score_opportunities()     # 시너지/실현가능성/전략적합도 평가
│   └── 4.3 AI_select_top_n(n=3)         # 상위 조합 선정
├── 5. Validation
│   ├── 5.1 AI_feasibility_check()       # 기술/법률/시장 실현 가능성
│   ├── 5.2 AI_conflict_resolution()     # 이름, 스코프, 라이선스 충돌 해결
│   └── 5.3 AI_strategic_fit_check()     # 포트폴리오 전체와의 적합성
└── 6. Launch Design
    ├── 6.1 AI_define_new_project()      # 새 프로젝트 이름, 범위, 차별점
    ├── 6.2 AI_inherit_from_sources()    # 원천 프로젝트로부터 자산 상속
    └── 6.3 AI_write_DESIGN()            # PGF DESIGN-{Name}.md 생성
```

## PPR: Core Functions

```python
def AI_scan_portfolio(portfolio_path):
  → Glob(["*/README.md", "*/DESIGN-*.md", "*/spec/*.md", "*/tools/*.py"])
  → AI_read(files)
  return project_catalog

# project_catalog = [{name, folder, readme, design, specs, tools, domain, maturity}]

def AI_extract_atoms(project_catalog):
  → AI_read(each.readme)
  → AI_summarize(
      atom = {
        name: project_name,
        problem: one_sentence,
        mechanisms: list of mechanism names,
        assets: {code, schemas, cli, tests},
        infra: list of shared infra assumptions,
        domain: domain_tag,
        maturity: prototype | mvp | alpha
      }
    )
  return atom_list

def AI_identify_mechanisms(atom_list):
  → AI_cluster(atoms, by=mechanism_similarity)
  → AI_label_clusters([
      "provenance/attestation",
      "market/clearing",
      "policy/governance",
      "identity/sovereignty",
      "energy/physical",
      "agent operations",
      "quantum-resistant crypto"
    ])
  return mechanism_groups

def AI_build_mechanism_matrix(atom_list):
  → AI_compare_pairs(atom_list)
  → AI_score(shared_mechanism, overlap, complementarity)
  return matrix  # N×N with scores

def AI_find_kernels(matrix, atom_list):
  → AI_detect_high_overlap_clusters(matrix)
  → AI_propose_kernel_candidates()
  return kernel_list  # [{name, shared_atoms, extracted_scope}]

def AI_apply_patterns(atom_list, matrix, kernels):
  → AI_pattern_match([
      pattern="vertical_stack",    # 같은 시나리오의 상하 레이어 통합
      pattern="horizontal_platform",  # 같은 메커니즘을 여러 도메인에 제공
      pattern="kernel_extraction",    # 공통 부분을 별도 프로젝트로 분리
      pattern="mashup",               # 두 프로젝트의 교차점에서 새 제품
      pattern="federation"            # 독립 프로젝트를 프로토콜로 연결
    ])
  return raw_opportunities

def AI_score_opportunities(opportunities, constraints):
  → AI_evaluate(each, criteria={
      synergy: 1-10,
      feasibility: 1-10,
      novelty: 1-10,
      strategic_fit: 1-10,
      risk: 1-10
    })
  → AI_rank(by=weighted_score)
  return scored_opportunities

def AI_select_top_n(scored_opportunities, n=3, constraints):
  → AI_filter(constraints)
  → AI_sort(descending=score)
  return opportunities[:n]

def AI_define_new_project(selected_opportunity):
  → AI_merge_names(selected_opportunity.source_projects)
  → AI_resolve_scope(selected_opportunity.pattern)
  → AI_write_positioning_statement()
  return project_brief

def AI_inherit_from_sources(project_brief, atom_list):
  → AI_map_assets(project_brief → source_projects)
  → AI_detect_license_conflicts()
  → AI_propose_reuse_plan()
  return inheritance_plan

def AI_write_DESIGN(project_brief, inheritance_plan):
  → AI_generate_gantree()
  → AI_generate_ppr()
  → AI_write("DESIGN-{Name}.md")
  return DESIGN.md
```

## 5 Recombination Patterns

### 1. Vertical Stack
> 같은 시나리오의 연속된 레이어를 하나의 스택으로 쌓는다.

Example: `AgentMesh` + `SpendMesh` + `VetoEscrow` + `SettleMesh` → **Agent Economy OS**
- AgentMesh: 에이전트 이벤트 정규화/원장
- SpendMesh: 에이전트 지출 통제
- VetoEscrow: 고위험 결재 차단
- SettleMesh: 스테이블코인 정산 규칙 검증

### 2. Horizontal Platform
> 같은 메커니즘을 여러 도메인에 제공하는 공통 레이어로 만든다.

Example: `ADPR` + `PnR` + `RoboTrace` + `CertMesh` → **TrustMesh**
- 공통: hash-chained attestation / provenance log
- 각 도메인: bio, non-response, robot incident, cert drift

### 3. Kernel Extraction
> 여러 프로젝트에 중복된 부분을 별도 프로젝트로 떼어낸다.

Example: 모든 Mesh/Registry가 사용하는 `authorization ledger`, `inclusion proof`, `policy engine` → **AuthKernel** / **PolicyKernel**

### 4. Mashup
> 두 프로젝트의 교차점에서 새로운 가치를 만든다.

Example: `ClimateMesh` + `FailureFutures` → **Climate Risk Derivatives**
- ClimateMesh가 산출한 리스크 점수를 FailureFutures의 청산/선물 메커니즘에 연결

### 5. Federation
> 독립 프로젝트를 하나의 프로토콜/네임스페이스로 연결한다.

Example: `WattMesh` + `PowerRoam` + `SeasonBat` + `WattWeaveAI` → **Planetary Energy Router Protocol**
- 각 프로젝트는 독립적으로 운영되지만, 라우팅/입찰/인증 프로토콜 공유

## Execution Workflow

1. **Trigger**: `/PGFR-COMBO recombine [portfolio-path] [goal]`
2. **Inventory & Decompose**: README/DESIGN를 읽고 Atom 추출
3. **Affinity Mapping**: 메커니즘 매트릭스 + Kernel 후보 도출
4. **Recombination**: 5가지 패턴 적용 → Opportunity Card 생성
5. **Validation**: 실현 가능성/충돌/전략적합도 검증
6. **Launch Design**: 상위 1~3개 조합에 대해 PGF DESIGN.md 생성

## Output Artifacts

```text
.pgfr-combo/
├── inventory.md              # 프로젝트 카탈로그 + Atom 리스트
├── mechanism-matrix.md       # Atom × Atom 매트릭스 + 시각화
├── kernels.md                # 공통 Kernel 후보
├── opportunities.md          # Opportunity Cards (Top N)
└── designs/
    ├── DESIGN-{ComboName1}.md
    └── DESIGN-{ComboName2}.md
```

## Acceptance Criteria

- [ ] 모든 기존 프로젝트가 Atom으로 분해됨
- [ ] 최소 3개 이상의 재조합 후보가 도출됨
- [ ] 각 후보가 어떤 source project에서 어떤 asset을 상속받는지 명시됨
- [ ] 각 후보가 5가지 패턴 중 하나로 분류됨
- [ ] 최우선 후보에 대해 PGF DESIGN.md가 생성됨

## Failure Strategy

- **Atom이 너무 커서 재조합이 안 됨** → 더 작은 mechanism 단위로 분해 (재귀)
- **후보가 너무 많음** → constraints(도메인, 성숙도, 리소스)로 필터링
- **Kernel 후보가 없음** → "Mashup"이나 "Federation" 패턴으로 전환
- **라이선스/이름 충돌** → `AI_conflict_resolution()`로 새 이름/스코프 정의

## Reference

- [PGF Skill](../../../../.claude/skills/pgf/SKILL.md) — Gantree + PPR execution modes
- [references/patterns.md](references/patterns.md) — Detailed pattern examples and decision tree
- [references/atom-template.md](references/atom-template.md) — Atom extraction template
