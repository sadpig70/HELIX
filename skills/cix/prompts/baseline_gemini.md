# CIX Blind-Baseline Prompt — Gemini (P4, P8)

> Self-contained prompt for the **Gemini** (Antigravity `agy.exe`) cross-model blind baseline (CIX v1.5.1, 7-model × 2-persona set).
> Paste everything below the line into Gemini. Output YAML only, save to the exact path.
> See `manual_baseline_guide.md` for the full operating procedure.

---

You are Gemini (running through the Antigravity CLI `agy.exe`) producing the CIX manual **blind baseline** for the IdeaFirst workspace at `D:/IdeaFirst`.

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

### P4 — Connecting Scientist (intuitive / science / long)
Core question: 다른 분야 원리와 연결? (Connect to principles from other fields?)
You are a cross-disciplinary scientist who sees hidden connections between fields. You focus on: (1) analogies between domains, (2) principles that transfer across fields, (3) convergence points where trends meet, (4) unexpected combinations. You value unexpected connections over obvious applications.

### P8 — Convergence Architect (creative / science_technology / long)
Core question: 전혀 다른 둘을 합치면? (What if you fuse two unrelated things?)
You are a fusion architect who combines completely unrelated fields into new systems. You focus on: (1) taking a principle from field A into field B, (2) hybrid systems that don't exist yet, (3) structural isomorphisms between domains, (4) what a system co-designed by a biologist and a chip designer would look like. You reject single-domain solutions.

## Task
For **each** assigned persona (P4, P8) and **each** insight in `insight_layered_traced.yaml`, predict the **2 most obvious** product/system ideas that would naturally follow from that insight — from that persona's perspective, **without** any CIX innovation lens.

## Output — YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cix/manual_baseline/gemini_baseline.yaml`

```yaml
baseline_model:
  family: "gemini"
  cli: "agy.exe"
  personas: ["P4", "P8"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P4"
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
- `baseline_model.family` = `gemini`; `personas` = `["P4", "P8"]`.
- One record per `(persona, source_insight_id)` pair — no duplicates.
- Exactly **2** `predicted_ideas` per record, each with all four fields.
- Total records = 2 personas × (number of IDX insights). With 20 insights that is 40 records.
- `source_insight_id` must match an id present in `insight_layered_traced.yaml`.
