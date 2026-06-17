# CALIBRATION — diversity thresholds (provenance + procedure)

> HELIX-Core thresholds are explicit, sourced, and overridable. This doc records
> where each default came from and how to recalibrate against a real corpus, so
> the defaults are an informed starting point — not an unexplained constant.

## 1. Defaults and provenance

`core/helix_diversity.DEFAULT_THRESHOLDS`:

| key | default | source | meaning |
|---|---|---|---|
| `keyword_coverage` | 0.80 | IdeaFirst `AOX_POLICY.homogenization` | top-k keywords dominate ≥80% of outputs |
| `max_pair_count` | 3 | IdeaFirst | same domain-pair repeats ≥3× over the window |
| `avg_embedding_sim` | 0.65 | IdeaFirst | mean pairwise similarity ceiling |
| `winner_embedding_similarity` | 0.50 | IdeaFirst | round N vs N-1 winner similarity ceiling |
| `dup_cos` | 0.80 | recreate (Si et al. cos>0.8) | a pair above this is a duplicate |
| `unique_ratio_floor` | 0.50 | recreate idea-layer | below this → island re-divergence |
| `min_breaches` | 2 | both | trigger when ≥2 of the 4 thresholds breach |

These are the two parent systems' working values. They are a calibrated-elsewhere
prior, not a guess — but the right values depend on the embedding/sim used.

## 2. Override (already supported)

```python
measure_diversity(pool, recent_winners, sim, thresholds={"avg_embedding_sim": 0.72})
```
`thresholds` shallow-merges over the defaults — pass any subset.

## 3. sim_kind selects the baseline thresholds (enforced in code)

`measure_diversity` ships a deterministic `lexical_sim` default (Jaccard over
tokens) so the report is always complete. The sim-based thresholds
(`avg_embedding_sim`, `winner_embedding_similarity`) were tuned for **embedding
cosine**, whose distribution differs from lexical Jaccard. Applying the cosine
ceilings to Jaccard data systematically under-triggers, so the baseline is now
**chosen by `sim_kind`** (not merely advised):

| threshold | semantic (`DEFAULT_THRESHOLDS`) | lexical (`LEXICAL_THRESHOLD_OVERRIDES`) |
|---|---|---|
| `avg_embedding_sim` | 0.65 | 0.45 |
| `winner_embedding_similarity` | 0.50 | 0.35 |
| `keyword_coverage`, `max_pair_count`, `dup_cos`, `unique_ratio_floor` | scale-free / same |

- `sim_kind == "lexical"` (no sim injected) → `base_thresholds("lexical")` applies
  the Jaccard-appropriate ceilings; count/coverage signals stay authoritative.
- `sim_kind == "semantic"` (sim injected) → the cosine-tuned `DEFAULT_THRESHOLDS` apply.
- An explicit `thresholds=` argument still overrides either baseline (back-compatible).

## 4. Calibration procedure (run once per corpus / sim)

```python
def calibrate_thresholds(history: list[Round], sim, target_trigger_rate=0.2) -> dict:
    """Pick thresholds so the guard fires on ~target_trigger_rate of historical rounds.
       Deterministic given (history, sim): no clock/network."""
    sims  = [avg_pairwise(r.pool, sim) for r in history if len(r.pool) > 1]
    wsims = [avg_pairwise(r.winners, sim) for r in history if len(r.winners) > 1]
    return {
        # set each ceiling at the (1 - target_trigger_rate) quantile of observed values
        "avg_embedding_sim": quantile(sims, 1 - target_trigger_rate),
        "winner_embedding_similarity": quantile(wsims, 1 - target_trigger_rate),
        "dup_cos": quantile(sims, 0.95),         # only the clearest pairs are "duplicates"
        # keyword/pair are scale-free counts → keep defaults unless domain set is unusual
    }
    # acceptance_criteria:
    #   - applying the result to `history` triggers on ~target_trigger_rate of rounds
    #   - quantiles computed from ≥ 20 rounds (else keep defaults + log low-confidence)
```

Re-run when: the embedding model changes, the corpus grows substantially, or the
trigger rate drifts from intent. Record the chosen set + the history window in the
run's status so calibration is auditable.
