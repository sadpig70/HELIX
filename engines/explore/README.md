# HELIX-A — Explore strand (IdeaFirst adapter)

> The IdeaFirst engine is **vendored** under `skills/` (sdx, tcx, idx, cix, evx, aox,
> + sdxx/idxx/cixx, sa-*, collect_git_trand) — HELIX is self-contained (see `MIGRATION.md`).
> This adapter wires those vendored skills to the shared backbone (`core/`) so the
> engine stops keeping its *own* ledger/diversity logic (single source of truth).

## Role

EXPLORE — scan the external world (80 orthogonal channels) for fresh signal and
distil it into one novel winner per round:
`sdx → tcx → idx → cix → evx`, orchestrated by `aox`.

## Inputs HELIX reads from this engine

| HELIX needs | IdeaFirst artifact | Key fields |
|---|---|---|
| Winner | `.evx/latest/stage6_final.yaml` | `consensus_winner`, `innovation_winner` (`id`, `title`, `layer`, `votes`, `provenance_model`) |
| Pool (for diversity) | `.cix/latest/idea_pool.yaml` | `ideas[]` (`title`, `domains`, `system_description`, `source_insight_id`) |
| Provenance chain | `.evx/latest/manifest.yaml` | `inputs.{cix_round, idx_round, tcx_round, sdx_catalog}` |

## Adapter mapping → HELIX-Core

```text
EVX winner          ─► helix candidate {idea_id, title, aliases, semantic_family,
                                        source_chain, source_insight_id}
                       └─► core.helix_ledger.is_consumed(candidate, ledger)   # before selection
cix idea_pool.ideas ─► core.helix_diversity.measure_diversity(pool, winners, sim)
implemented winner  ─► core.helix_ledger.append_consumed(...)                 # after a project is built
                       └─► core.helix_provenance.winner_to_corpus_entry(...)  # ► hand to exploit strand
```

## What this adapter REPLACES in IdeaFirst (de-duplication)

- `.idea-ledger/consumed_ideas.yaml` semantics → unified `core.helix_ledger`
  (YAML view kept as an adapter projection; logic single-sourced).
- `AOX_POLICY.homogenization` + `sdxx/idxx/cixx` saturation triggers → fed by
  `core.helix_diversity` (one threshold set, no AOX/SDX copy → no desync).
- EVX cross-model consensus stays in the engine (LLM, meta-layer); HELIX only
  consumes its winner output.

## Boundary

LLM stages (collection, distillation, creation, evaluation) are the engine's own
and remain outside the determinism boundary. HELIX-Core never calls them; it only
ingests their artifacts and runs deterministic backbone logic.
