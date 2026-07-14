# Trellis Design @v:1.0

## Provenance (full-cycle turn 4, co-evolution + domain-distance)

`next_action=RUN_EXPLOIT`. The corpus now contains ConcordGate, Confluence,
Meander. Trellis is the loop's fourth distinct character — **learn/plan** —
after verify → design → play. It transplants Meander's graph-traversal gene
(BFS / ordering over a graph) into the learning domain: a skill dependency graph
instead of a maze grid.

Domain-distance gate: flips the corpus centroid (verify/gate → **teach/plan**;
verdict → **ordered learning path**; agent-ops → **learner**).

## Intent

A deterministic curriculum / skill-tree planner. Given skills with prerequisites
(a DAG) and a goal, Trellis produces a valid ordered learning path (topological
order, alphabetical tie-break), the minimal prerequisite closure for the goal,
and effort/depth metrics — and **fails closed on cycles or missing prerequisites**
(you cannot learn a cyclic prerequisite). Same graph → same plan, always.

Honest boundary: a planning/教學 tool over an explicit prerequisite graph — it
orders what you give it; it does not judge pedagogy or invent prerequisites.

## Gantree

```text
Trellis // 결정론 커리큘럼 계획 (designing) @v:1.0
    Graph // 스킬 -> 선수과목 DAG (designing)
        Validate // 미정의 선수·순환 탐지(fail-closed) (designing)
    Order // 위상정렬(알파 tie-break) (designing) @dep:Validate
    Plan // 목표까지 최소 선수 폐포의 학습 순서 (designing) @dep:Order
    Metrics // 스킬수·깊이(최장 선수사슬)·시작점 (designing) @dep:Order
    Render // 순서 계획(번호) + SVG 계층 DAG (designing) @dep:Plan
    Cli // sample|plan|check (designing) @dep:Render
```

## PPR

```python
def validate(graph) -> list:
    """미정의 선수과목·순환을 문제로 반환(빈 리스트=유효).
    acceptance_criteria:
      - 참조된 모든 선수과목이 정의되어야 한다
      - 순환은 학습 불가 -> 문제로 보고(fail-closed)
    """

def topo_order(graph) -> list:
    """Kahn 위상정렬, 알파벳 tie-break로 결정론. 순환이면 ValueError."""

def plan(graph, goal) -> list:
    """goal의 선수 폐포만 위상정렬한 학습 순서(goal로 끝남).
    acceptance_criteria: 순서 내 모든 스킬의 선수가 앞에 온다; 결정론."""
```

## Invariants

- 결정론: 알파벳 tie-break로 위상정렬·계획이 유일. 같은 그래프 -> 같은 계획.
- fail-closed: 순환/미정의 선수는 계획을 만들지 않고 문제로 보고.
- 계획 불변식: 모든 스킬의 선수는 그 스킬보다 앞선다(위상 정합).
- stdlib only: no random, clock, network, subprocess, AI.
- 정직: 명시된 선수 그래프를 정렬할 뿐, 교육학을 판단하거나 선수를 발명하지 않는다.

## Verification plan

- 위상 정합: 계획에서 각 선수가 앞선다.
- 결정론: 동일 그래프 -> 동일 계획/순서.
- 순환 fail-closed: 순환 그래프 -> validate 문제 + topo_order ValueError.
- 미정의 선수 탐지.
- 최소 폐포: plan(goal)은 goal에 불필요한 스킬을 포함하지 않는다.
- depth = 최장 선수 사슬 정확.
- render: ASCII 순서 계획 + SVG well-formed.
- CLI sample/plan/check 왕복.
- >=10 tests + 결정론. helix_validate PASS.
```
