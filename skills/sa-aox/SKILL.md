---
name: sa-aox
description: "SA-AOX (Stand-Alone IdeaFirst Orchestrator eXplorer) — cross-model 평가가 미가용인 단일 모델 런타임에서 SDX/TCX/IDX 산출물을 받아 SA-ICX와 SA-EVX를 순차 실행하고 standalone final summary와 production promotion package를 만드는 오케스트레이터. AOX production을 대체하지 않고 .aox production run을 completed로 위장하지 않으며 .sa-aox/에만 산출한다. Triggers: sa-aox, standalone aox, stand-alone aox, 단독 AOX, 독립 AOX, standalone full cycle, SA IdeaFirst"
user-invocable: true
argument-hint: "full|resume|dry-run|promote-package [--start-from=stage] [--run-id=...]"
version: "0.2"
author: "양정욱 (sadpig70@gmail.com)"
---

# SA-AOX (Stand-Alone IdeaFirst Orchestrator eXplorer) v0.2

SA-AOX는 cross-model 평가가 미가용인 단일 모델 런타임(Claude Code, Codex 등)에서 IdeaFirst exploratory loop를 끝까지 닫는 standalone 오케스트레이터다.

런타임이 subagent 병렬 파견을 지원하면 SA-ICX/SA-EVX의 페르소나 작업을 병렬 subagent로 실행하는 것이 기본이다(PGF discover 패턴, `pgf/agent-protocol.md`의 PG TaskSpec 사용). 단, subagent는 같은 모델이므로 결과는 여전히 single-model이며 standalone boundary는 변하지 않는다.

## Completion Definition

SA-AOX is complete when the standalone pipeline runs by composing official skills
only. SA-AOX must not become a duplicate implementation of SA-ICX or SA-EVX; it
must orchestrate them, verify their artifacts, enforce consumed-idea exclusion,
and write the standalone wrap-up.

```yaml
sa_aox_completion_criteria:
  source_of_truth:
    - "skills/sa-aox/SKILL.md"
    - "skills/sa-icx/SKILL.md"
    - "skills/sa-evx/SKILL.md"
    - "skills/pg/SKILL.md"
    - "skills/pgf/SKILL.md"
    - ".idea-ledger/consumed_ideas.yaml"
  excluded_from_pipeline_contract:
    - "aox_agents.md"
  complete_when:
    - "SA-AOX can run Stage0..Stage5 through skill contracts only"
    - "SA-ICX candidate_pool is produced or reused through SA-ICX contract"
    - "SA-EVX final_idea and dual winner are produced through SA-EVX contract"
    - "consumed winners are excluded before acceptance"
    - "implemented winners are recorded in the consumed idea ledger"
    - "all outputs stay under .sa-icx, .sa-evx, and .sa-aox"
  incomplete_when:
    - "SA-AOX depends on aox_agents.md or other handoff notes as policy"
    - "SA-AOX bypasses SA-ICX/SA-EVX contracts by inventing untracked outputs"
    - "SA-AOX repeats an idea already consumed into a project"
```

## Boundary

SA-AOX는 AOX production 결과가 아니다.

```yaml
result_class: "standalone_single_runtime"
cross_model_certified: false
production_aox_equivalent: false
may_write_aox_completed_summary: false
may_write_cix_latest: false
may_write_evx_latest: false
```

SA-AOX가 만드는 것은 최종 인증 결과가 아니라:
- standalone final idea
- standalone summary
- production promotion package
- CIX/EVX/AOX로 승격하기 위한 trace

## Pipeline

```text
SA_AOX_Full
    Stage0_Init
        create .sa-aox/{run_id}/status.json
        probe file_io and PGF personas
        record cross_model_capability but do not block standalone flow
        load .idea-ledger/consumed_ideas.yaml if present

    Stage1_UpstreamCheck
        verify .sdx/catalog/index.yaml
        verify .tcx/latest/
        verify .idx/latest/insight_layered_traced.yaml
        verify consumed idea ledger is readable when it exists

    Stage2_SA_ICX
        invoke or execute SA-ICX forge
        require consumed ideas to be excluded before candidate_pool.yaml is finalized
        output .sa-icx/rounds/{sa_icx_round_id}/candidate_pool.yaml

    Stage3_SA_EVX
        invoke or execute SA-EVX evaluate
        reject any consensus_winner or innovation_winner that appears in consumed_ideas.yaml
        output .sa-evx/rounds/{sa_evx_round_id}/final_idea.md

    Stage4_WrapUp
        write .sa-aox/{run_id}/summary.md
        write .sa-aox/{run_id}/PROMOTE_TO_PRODUCTION.md
        update .sa-aox/index.yaml

    Stage5_ConsumptionRecord
        when standalone winner is converted into a concrete project folder or MVP
        record it with the production ledger tool (never hand-roll the schema):
            python scripts/explore/aox_full.py --project-root . --mode wrapup --record-consumed
              --idea-id {winner id} --idea-title "{winner title}"
              --project-name {Name} --project-path {name}
              --repo-url {url} --aliases {Name},<alt> --semantic-family <slug>
        note: SA winner ids are absent from .cix/latest/idea_pool.yaml, so --idea-title is REQUIRED
        then validate: python scripts/explore/ledger_lint.py --project-root .
        do not record merely explored candidates that were not selected or implemented
        verify future SA-ICX/SA-EVX runs exclude the consumed winner
```

## Inputs

```yaml
required:
  sdx_catalog_index: ".sdx/catalog/index.yaml"
  tcx_latest: ".tcx/latest/manifest.yaml"
  idx_latest: ".idx/latest/insight_layered_traced.yaml"
  personas: "skills/pgf/discovery/personas.json"
  consumed_ideas_ledger: ".idea-ledger/consumed_ideas.yaml"

optional:
  existing_sa_icx_round: ".sa-icx/rounds/{round_id}"
  existing_sa_evx_round: ".sa-evx/rounds/{round_id}"
  category_map_builder: "skills/cixx/scripts/build_category_map.py"   # SA-ICX 조향용
  ledger_lint: "scripts/explore/ledger_lint.py"
  record_consumed_tool: "scripts/explore/aox_full.py (--record-consumed --idea-id --idea-title)"
```

## Outputs

```yaml
output_root: ".sa-aox"
run_id_format: "SA-AOX-{YYYYMMDD}-{NNN}"
files:
  - status.json
  - summary.md
  - standalone_kpis.yaml
  - PROMOTE_TO_PRODUCTION.md
  - run_manifest.yaml
  - optional consumed idea ledger update when a winner is implemented
```

## Status Contract

```yaml
status:
  run_id: "SA-AOX-{YYYYMMDD}-{NNN}"
  mode: "full | resume | dry-run"
  result_class: "standalone_single_runtime"
  stages:
    0_init: "completed | failed"
    1_upstream_check: "completed | failed"
    2_sa_icx: "completed | failed | skipped_reused"
    3_sa_evx: "completed | failed | skipped_reused"
    4_wrapup: "completed | failed"
  sub_round_ids:
    sa_icx_round_id: "SA-ICX-{YYYYMMDD}-{NNN}"
    sa_evx_round_id: "SA-EVX-{YYYYMMDD}-{NNN}"
  consumed_idea_gate:
    ledger_path: ".idea-ledger/consumed_ideas.yaml"
    excluded_count: integer
    exclusion_report: ".idea-ledger/exclusion_report_latest.md"
    winner_reuse_detected: false
  consumption_record:
    required_when_project_created: true
    ledger_path: ".idea-ledger/consumed_ideas.yaml"
    record_via: "aox_full.py --record-consumed --idea-id --idea-title (직접 append 금지)"
    lint_after_record: "scripts/explore/ledger_lint.py errors=0"
    reuse_policy: "exclude_same_or_derivative"
    recorded_idea_id: "string | null"
    recorded_project_path: "string | null"
  production_boundary:
    cross_model_certified: false
    cix_promotion_required: true
    evx_production_required: true
    aox_production_wrapup_required: true
```

## Standalone KPIs

SA-AOX may record analogous exploratory metrics, but they must not be confused with AOX v1.3.1 production KPIs.

```yaml
standalone_kpis:
  candidate_diversity_proxy: number
  layer_balance: {L6_Gap, L7_Tension, L9_Counterfactual, L10_Generative}
  persona_vote_breadth: number
  consensus_vs_innovation_split: boolean
  production_certification_status: "not_certified"
```

Forbidden KPI language:
- `novelty baseline failure rate` unless cross-model CIX has run
- `surprise pass rate` unless cross-model CIX has run
- `AOX KPI passed`

## Summary Contract

`summary.md` must include:

```markdown
# SA-AOX Standalone Summary

This is a standalone IdeaFirst result, not CIX/EVX/AOX production-certified output.
Cross-model CIX v1.5.1 promotion is required before production use.

## Outputs
- SA-ICX candidate pool
- SA-EVX final idea
- SA-EVX dual winner block

## Boundary
- cross_model_certified: false
- may_use_for_exploration: true
- may_use_for_final_certification: false

## Production promotion
```

## Promotion Package

`PROMOTE_TO_PRODUCTION.md` must give the exact next production path:

```text
1. Run CIX v1.5.1 cross_model surprise_validation using SA-ICX candidates as evidence.
2. Emit completed .cix/latest only after cross_model validation.
3. Run EVX v1.1 production evaluate.
4. Run AOX v1.3.1 wrap-up and collect production 5 KPIs.
```

If CIX import from `.sa-icx` is not implemented, state manual handoff:

```text
Use .sa-icx/rounds/{id}/candidate_pool.yaml and raw_seed_ideas.yaml as candidate evidence.
Do not copy them into .cix/latest without CIX v1.5.1 validation.
```

## PGF Execution Rule

Use inline PGF for a single run. Create durable `.pgf/` workplans only when changing this skill, running a multi-turn standalone campaign, or handing off to another environment.

## Consumed Idea Recording

If a selected SA-AOX winner is implemented as a project, MVP, repo, or durable PGF track, SA-AOX must record it in `.idea-ledger/consumed_ideas.yaml` before the task is considered complete.

Record via the production tool — the ledger schema is owned by AOX and enforced by `ledger_lint.py`; SA-AOX must not hand-roll entries:

```bash
python scripts/explore/aox_full.py --project-root . --mode wrapup --record-consumed \
  --idea-id {winner id} --idea-title "{winner title}" \
  --project-name {Name} --project-path {name} --repo-url {url} \
  --aliases {Name},<alt1> --semantic-family <slug>
python scripts/explore/ledger_lint.py --project-root .
```

The resulting entry follows the production schema (reference only — do not write by hand):

```yaml
- idea_id: "winner id"                       # SA round-local id
  title: "winner title"
  normalized_title: "kebab-case of title"
  aliases: ["{Name}", "<alt1>"]
  semantic_family: "single-slug-string"      # string, not list
  source_chain: {cix: "...", idx: "...", tcx: "...", evx: "...", sdx_catalog: "..."}
  consumed_at_utc: "ISO-8601"
  implementations:
  - {project_name: "{Name}", project_path: "{name}", repo_url: "{url}"}
  reuse_policy: "exclude_same_or_derivative"
```

SA round ids (`SA-AOX/SA-ICX/SA-EVX-...`)는 ledger 스키마 밖이므로 `.sa-aox/{run_id}/run_manifest.yaml`에 기록하고, ledger에는 위 정본 키만 남긴다.

Do not record candidates that were only generated, evaluated, or discussed. Record only after the idea has been consumed into concrete work.
