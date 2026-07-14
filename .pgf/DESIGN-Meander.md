# Meander Design @v:1.0

## Provenance (full-cycle turn 3, co-evolution + domain-distance)

`next_action=RUN_EXPLOIT`. The corpus now contains the two projects this loop
already produced (ConcordGate, Confluence). Meander transplants Confluence's
"seeded deterministic generation" gene into a domain absent from everything so
far — **games / play** — keeping the domain-distance gate: it flips the corpus
centroid (verify/design → **play**; verdict → **playable artifact**; agent-ops →
**player**; judge → **generate + solve**).

Three distinct characters now demonstrated by the loop: verify (ConcordGate) ->
design (Confluence) -> play (Meander).

## Intent

A deterministic maze generator and solver. Given width, height, and a seed it
carves a **perfect maze** (a spanning tree — exactly one path between any two
cells, always solvable), finds the shortest solution, scores its playability, and
renders it as ASCII and SVG. Same seed -> same maze, always.

Honest boundary: a recreational tool, not a research artifact. Its value is a
clean, reproducible, self-contained generator+solver — and being the loop's third
distinct-character output.

## Gantree

```text
Meander // 결정론 미로 생성·해결 (designing) @v:1.0
    Generate // 시드 기반 완전미로(spanning tree) (designing)
        Carve // 결정론 DFS 통로 파기 (designing)
        Perfect // 모든 셀 연결·유일 경로 보장 (designing) @dep:Carve
    Solve // 최단 경로 BFS (designing) @dep:Generate
    Metrics // 난이도(경로장·막다른길·분기) (designing) @dep:Solve
    Render // ASCII + SVG(경로 오버레이) (designing) @dep:Solve
    Cli // sample|generate|solve (designing) @dep:Render
```

## PPR

```python
def generate(w, h, seed) -> Maze:
    """결정론 DFS로 완전미로를 판다.
    acceptance_criteria:
      - 동일 (w,h,seed) -> 동일 통로 집합 (결정론; no random/clock)
      - 모든 셀이 연결(spanning tree) -> 항상 풀린다
      - 통로는 무방향(대칭)
    """

def solve(maze) -> list:
    """(0,0)에서 (h-1,w-1)까지 최단 경로(BFS).
    acceptance_criteria: 완전미로에서 항상 존재하고 유일한 경로."""

def metrics(maze, path) -> dict:
    """cells·solution_length·dead_ends·junctions·difficulty(정규화)."""
```

## Invariants

- 결정론: 시드 SHA-256만 사용. 같은 입력 -> 같은 미로.
- 완전미로: 항상 solvable, 임의 두 셀 사이 유일 경로.
- stdlib only: no random, clock, network, subprocess, AI.
- 정직: 오락 도구. 연구 산출 주장 없음(README 명시).

## Verification plan

- 결정론: 동일 시드 -> 동일 통로/렌더.
- solvability: 임의 시드에서 solve가 start->goal 경로 반환.
- perfect maze: 통로 수 == cells-1 (spanning tree).
- 대칭: (a in P[b]) <=> (b in P[a]).
- render: ASCII 격자 정합, SVG well-formed.
- metrics 일관(경로장 >= 맨해튼 거리).
- CLI sample/generate/solve 왕복.
- >=10 tests + 결정론. helix_validate PASS(core 무관).
```
