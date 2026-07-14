# Confluence Design @v:1.0

## Provenance (HELIX full-cycle, domain-distance steered)

The exploit/recreate strand is corpus-bound: recombining 70 governance/verification
projects structurally reverts to that character. To produce a project in a
completely different domain, this turn **augments the full-cycle with a
domain-distance gate** — the winner must sit on the opposite pole of the corpus
centroid on >=3 character axes.

| axis | corpus centroid | Confluence |
|---|---|---|
| purpose | verify / gate / clear | **generate / design / search** |
| output | verdict / ledger | **design candidates + artifacts (SVG/WAV/text)** |
| interaction | judge | **generator / evolver** |
| user | agent-ops / infra | **researcher / creator** |
| domain | governance | **hard-science + arts, unified** |

All 5 axes flip. Difference is measured, not merely claimed.

## Intent

A domain-agnostic generative **design-space explorer**. Define any domain as
`(positions, constraints, objectives, render)` and one deterministic engine
generates candidate designs, evaluates them on multiple objectives, keeps the
Pareto-optimal (non-dominated) set, and evolves it over generations. The SAME
engine spans pharma (molecule), materials (alloy), semiconductor (floorplan),
energy (mix), data (schema), and the arts (mandala SVG, melody WAV, story text)
— demonstrating that hard-science and creative design share one abstraction:
compose primitives under constraints toward objectives.

Honest boundary: the domain packs are **illustrative models**, not production R&D
tools — Confluence does not discover real drugs or design real chips. The value
is the unifying abstraction and the demonstration that one engine crosses
science and art. The README states this plainly.

## Gantree

```text
Confluence // 도메인-불가지 생성 설계 엔진 (designing) @v:1.0
    Engine // 결정론 다목적 진화 탐색 (designing)
        Genome // locus별 선택 인덱스 튜플 (designing)
        Generate // 시드 해시 기반 결정론 초기 개체군 (designing) @dep:Genome
        Evaluate // 도메인 objectives(모두 최대화) (designing) @dep:Generate
        Pareto // 비지배 집합 (designing) @dep:Evaluate
        Evolve // 엘리트 + 결정론 교차/변이 세대 반복 (designing) @dep:Pareto
    DomainPack // (positions, constraints, objectives, render) 계약 (designing)
        Science // molecule·alloy·floorplan·energy·schema (designing) @dep:Engine
        Arts // mandala(SVG)·melody(WAV)·story(text) (designing) @dep:Engine
    Report // sealed 실행 리포트(front·best) (designing) @dep:Evolve
    Cli // domains|run --domain|report (designing) @dep:Report,DomainPack
```

## PPR

```python
def evolve(domain, seed, population=24, generations=8) -> Run:
    """결정론 다목적 진화로 도메인의 Pareto 설계 집합을 찾는다.
    acceptance_criteria:
      - 동일 (domain,seed,params) -> 동일 sealed run (결정론; no randomness/clock)
      - 제약 위반 후보는 개체군에서 제외
      - Pareto front는 비지배 집합(도메인 objectives 벡터 기준)
      - 세대는 엘리트(front) + 결정론 교차/변이 자손으로 구성
    """

def pareto_front(evaluated) -> list:
    """a dominates b iff 모든 objective에서 a>=b 이고 하나 이상에서 a>b."""

def render_best(domain, run, objective=None) -> Artifact:
    """front에서 (선택 objective 기준) 최고 후보를 도메인 아티팩트로 렌더.
    format in {svg, wav, text, json}. 결정론.
    """
```

## Invariants

- 결정론: 시드 해시(hashlib)만 사용, `random`/clock 없음. 같은 입력 -> 같은 seal.
- 엔진은 도메인-불가지: 도메인 팩은 4개 함수만 제공, 엔진 로직 재사용(단일 출처).
- Pareto는 도메인 내 objective 벡터 기준(도메인 간 비교 아님).
- 정직: 팩은 illustrative 모델. 실제 R&D 산출 주장 없음(README 명시).
- stdlib only: engine·science 팩은 순수; mandala는 SVG 문자열, melody는 stdlib `wave`.
- fail-closed: 유효 후보 0이면 빈 front + 명시 problem(과대 성공 표기 없음).

## Verification plan

- 결정론: 동일 시드 -> 동일 run seal, 동일 front.
- Pareto 정확성: 지배 관계 단위 테스트.
- 제약: 위반 genome 제외 확인.
- 각 도메인 팩: 유효 후보 생성 + objectives dict 일관 + render 포맷 정상
  (mandala=well-formed SVG, melody=RIFF/WAVE 헤더, text=비어있지 않음).
- 진화가 front를 개선(또는 최소 비악화)하는지.
- CLI domains/run/report 왕복.
- >=10 tests + 결정론. helix_validate PASS(core 무관, 독립 프로젝트).
```
