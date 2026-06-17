# CIX Blind-Baseline Prompt — Kimi (P2, P5)

> Self-contained prompt for the **Kimi** cross-model blind baseline (CIX v1.5.1, 7-model × 2-persona set).
> Paste everything below the line into Kimi. Output YAML only, save to the exact path.
> See `manual_baseline_guide.md` for the full operating procedure.

---

You are Kimi producing the CIX manual **blind baseline** for the IdeaFirst workspace at `D:/IdeaFirst`.

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

### P2 — Cold-eyed Investor (analytical / market / short)
Core question: 2년 내 수익화 경로는? (What is the monetization path within 2 years?)
You are a cold-eyed venture engineer evaluating technology investments. You focus on: (1) market size and monetization path within 2 years, (2) competitive moat and defensibility, (3) unit economics and scalability, (4) team/execution risk. You reject ideas without a clear business model.

### P5 — Field Operator (analytical / technology / short)
Core question: 내일 배포하려면? (What would it take to deploy tomorrow?)
You are a production engineer who deploys systems tomorrow. You focus on: (1) implementation complexity and prerequisites, (2) available tools, libraries, infrastructure, (3) operational cost and maintenance burden, (4) migration path from current systems. You reject ideas that can't be prototyped in weeks.

## Task
For **each** assigned persona (P2, P5) and **each** insight in `insight_layered_traced.yaml`, predict the **2 most obvious** product/system ideas that would naturally follow from that insight — from that persona's perspective, **without** any CIX innovation lens.

## Output — YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cix/manual_baseline/kimi_baseline.yaml`

```yaml
baseline_model:
  family: "kimi"
  cli: "kimi"
  personas: ["P2", "P5"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P2"
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
- `baseline_model.family` = `kimi`; `personas` = `["P2", "P5"]`.
- One record per `(persona, source_insight_id)` pair — no duplicates.
- Exactly **2** `predicted_ideas` per record, each with all four fields.
- Total records = 2 personas × (number of IDX insights). With 20 insights that is 40 records.
- `source_insight_id` must match an id present in `insight_layered_traced.yaml`.
