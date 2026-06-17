---
name: sa-evx
description: "SA-EVX (Stand-Alone Evaluation eXplorer) — SA-ICX candidate_pool을 입력으로 14 PGF 페르소나 병렬 평가, consumed-ledger 사전 배제, dual winner(consensus + innovation), derivative challenge, 5S/3R/3X 보고서를 생성하는 standalone 평가 스킬. EVX production을 대체하지 않고 .evx/latest를 쓰지 않으며 .sa-evx/에만 산출한다. Triggers: sa-evx, standalone evx, stand-alone evx, 단독 EVX, 독립 EVX, standalone evaluation, sa 평가"
user-invocable: true
argument-hint: "evaluate|rerank|compare [--input=.sa-icx/latest/candidate_pool.yaml] [--round-id=...]"
version: "0.2"
author: "양정욱 (sadpig70@gmail.com)"
---

# SA-EVX (Stand-Alone Evaluation eXplorer) v0.2

SA-EVX는 SA-ICX 후보를 standalone 방식으로 평가해 final idea report를 만든다.

런타임이 subagent를 지원하면 14 페르소나 투표를 병렬 subagent로 실행하는 것이 기본이다 (PG TaskSpec, `pgf/agent-protocol.md`). 단일 모델이므로 production EVX의 cross-model deep-semantic derivative 검출(7-model이 자동 필터가 놓친 derivative를 잡은 사례)을 대체할 수 없다 — 그 부분 완화책이 아래 DerivativeChallenge다.

## Boundary

SA-EVX는 EVX production 결과가 아니다.

```yaml
validation_level: "single_model_multi_persona"
cross_model_certified: false
may_write_evx_latest: false
may_write_cix_latest: false
may_write_aox_summary_as_production: false
production_promotion_required: "CIX v1.5.1 -> EVX v1.1 -> AOX v1.3.1"
```

금지:
- `.evx/latest/` 쓰기
- `.aox/{run_id}/summary.md` production 완료로 위장
- SA-ICX `surprise_proxy`를 CIX cross-model surprise처럼 해석
- `cross_model_certified: true` 표기
- consumed ledger와 매칭되는 후보를 winner로 선정 (사전 배제 필수)

허용:
- `.sa-evx/rounds/{round_id}/`에 standalone 평가 산출
- PGF P1-P14 evaluation_bias로 top-3 투표
- consensus_winner와 innovation_winner를 둘 다 산출
- standalone 5S/3R/3X 보고

## Inputs

```yaml
input:
  candidate_pool: ".sa-icx/latest/candidate_pool.yaml"
  manifest: ".sa-icx/latest/manifest.yaml"
  personas: "skills/pgf/discovery/personas.json"   # 14 personas (P1-P14) — 정본
  consumed_ideas_ledger: ".idea-ledger/consumed_ideas.yaml"   # winner 선정 전 필독
  explicit_round_override: ".sa-icx/rounds/{SA-ICX-ID}/candidate_pool.yaml"
```

입력 후보는 24개를 권장한다. 24개 미만이면 평가 가능하지만 manifest에 `candidate_count_below_24: true`를 기록한다.

## Outputs

```yaml
output_root: ".sa-evx"
round_id_format: "SA-EVX-{YYYYMMDD}-{NNN}"
files:
  - stage5_candidates.yaml     # P1-P14 top-3
  - stage6_final.yaml          # dual winner
  - final_idea.md              # standalone 5S/3R/3X
  - manifest.yaml
  - PROMOTE_TO_PRODUCTION.md
```

## Evaluation Policy

SA-EVX maps standalone candidate scores into PGF 4 axes:

```yaml
axis_mapping:
  novelty: "candidate.novelty"
  feasibility: "candidate.defensibility"
  impact: "(candidate.generativity + candidate.compounding) / 2"
  integrity: "candidate.coherence"
  surprise: "internal_hint_only; not used as certification"
```

Persona scoring:

```text
persona_score = sum(evaluation_bias[axis] * pgf_axis[axis]) / sum(evaluation_bias)
```

Dual winner:

```yaml
consensus_winner:
  tiebreak_order: [votes, cognitive_style_breadth, mean_persona_score]
innovation_winner:
  tiebreak_order: [max_persona_score, novelty_axis, votes, mean_persona_score]
winners_identical: boolean
```

## Execution

```text
SA_EVX_Evaluate
    LoadInputs
        read SA-ICX candidate_pool
        read SA-ICX manifest
        read PGF personas (14)
        read .idea-ledger/consumed_ideas.yaml if present

    LedgerExclude
        remove candidates matching consumed ideas on the canonical keys:
            idea_id (same-round only), normalized_title, aliases, semantic_family
        record consumed_excluded_count in manifest

    MapAxes
        convert candidate axes to PGF novelty/feasibility/impact/integrity

    PersonaVote
        P1-P14 each select top 3 (parallel subagents when available)
        output stage5_candidates.yaml

    DualWinner
        compute consensus_winner
        compute innovation_winner
        output stage6_final.yaml

    DerivativeChallenge
        for each winner: 3 cross-style personas (critical + analytical + intuitive)
        attempt to REFUTE: "is this a deep-semantic derivative of a consumed sibling
        (same mechanism + same lens move, different nouns)?"
        majority refuted -> demote winner, promote next ranked candidate, repeat once
        record challenge verdicts in stage6_final.yaml
        limitation: single-model challenge은 cross-model 검증의 대체가 아님 (manifest에 명시)

    Report
        write final_idea.md with:
          - standalone boundary note
          - consensus winner block
          - innovation winner block if different
          - 5 strengths
          - 3 risks with mitigations
          - 3 expansion scenarios
          - source chain

    EmitRound
        write .sa-evx/rounds/{round_id}/
        optionally mirror to .sa-evx/latest/
```

## Manifest Contract

```yaml
round:
  id: "SA-EVX-{YYYYMMDD}-{NNN}"
  version: "0.2"
  mode: "evaluate"
  status: "completed | blocked"

validation:
  level: "single_model_multi_persona"
  cross_model_certified: false
  evx_production_equivalent: false
  derivative_challenge_is_cross_model_equivalent: false

inputs:
  source_sa_icx_round: "SA-ICX-{YYYYMMDD}-{NNN}"
  source_idx_round: "IDX-{YYYYMMDD}-{NNN}"
  source_tcx_round: "TCX-{YYYYMMDD}-{NNN}"
  sdx_catalog: "현재 .sdx/catalog/index.yaml의 version 값을 기록"

outputs:
  consensus_winner_id: "string"
  innovation_winner_id: "string"
  winners_identical: boolean
  consumed_excluded_count: integer
  derivative_challenge:
    challenged: ["winner ids"]
    demoted: ["winner ids | empty"]

policy:
  may_write_evx_latest: false
  may_feed_aox_production: false
  may_feed_sa_aox: true
```

## Promotion

`PROMOTE_TO_PRODUCTION.md` must state that SA-EVX output is useful as evaluation evidence only. Production promotion still requires:

```text
CIX v1.5.1 cross_model surprise_validation
-> .cix/latest completed
-> EVX v1.1 production evaluate
-> AOX v1.3.1 wrap-up
```
