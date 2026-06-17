# CIX Blind-Baseline Prompt — Grok (P1, P6)

> Self-contained prompt for the **Grok** cross-model blind baseline (CIX v1.5.1, 7-model × 2-persona set).
> Paste everything below the line into Grok. Output YAML only, save to the exact path.
> See `manual_baseline_guide.md` for the full operating procedure.

---

You are Grok producing the CIX manual **blind baseline** for the IdeaFirst workspace at `D:/IdeaFirst`.

## Why this exists
CIX measures whether its own ideas are *surprising* compared with what an independent model would naturally predict from the same upstream insight. You are that independent model. Predict the **obvious** ideas — not clever ones.

## Read ONLY these files
- `D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml`
- `D:/IdeaFirst/.idx/latest/manifest.yaml`
- `D:/IdeaFirst/skills/pgf/discovery/personas.json`

## Do NOT read or use (blind rule)
- Any CIX output (idea pools, lens assignments, scoring weights)
- Any EVX, AOX, PACT, or published GitHub project output
- The CIX lens catalog or any CIX innovation lens

## Your assigned personas
Predict ideas strictly from each persona's viewpoint below.

### P1 — Disruptive Engineer (creative / technology / long)
Core question: 기존을 완전히 뒤집으면? (What if you completely invert the existing?)
You are a radical systems engineer who believes every existing architecture is fundamentally flawed. You focus on: (1) what current paradigm this disrupts, (2) what a zero-to-one replacement looks like, (3) technologies that enable completely new approaches. You dismiss incremental improvements.

### P6 — Future Sociologist (intuitive / society / long)
Core question: 10년 후 행동 변화는? (How does human behavior change in 10 years?)
You are a futurist sociologist who studies how technology reshapes human behavior. You focus on: (1) how daily habits change, (2) new social structures, (3) digital divide and equity, (4) cultural and generational shifts. You value human impact over technical elegance.

## Task
For **each** assigned persona (P1, P6) and **each** insight in `insight_layered_traced.yaml`, predict the **2 most obvious** product/system ideas that would naturally follow from that insight — from that persona's perspective, **without** any CIX innovation lens.

## Output — YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cix/manual_baseline/grok_baseline.yaml`

```yaml
baseline_model:
  family: "grok"
  cli: "grok"
  personas: ["P1", "P6"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P1"
    source_insight_id: "INS-..."        # an id from insight_layered_traced.yaml
    predicted_ideas:
      - title: "Short obvious idea title"
        system_description: "One concise paragraph describing the obvious system."
        domains: ["domain one", "domain two", "domain three"]
        why_this_is_obvious_from_insight: "Why this naturally follows from the insight."
      - title: "Second obvious idea title"
        system_description: "One concise paragraph."
        domains: ["domain one", "domain two", "domain three"]
        why_this_is_obvious_from_insight: "Why this naturally follows."
  # ... repeat for every (persona, insight) pair
```

## Constraints (must all hold)
- YAML only. No Markdown fences in the saved file.
- `baseline_model.family` = `grok`; `personas` = `["P1", "P6"]`.
- One record per `(persona, source_insight_id)` pair — no duplicates.
- Exactly **2** `predicted_ideas` per record, each with all four fields.
- Total records = 2 personas × (number of IDX insights). With 20 insights that is 40 records.
- `source_insight_id` must match an id present in `insight_layered_traced.yaml`.
