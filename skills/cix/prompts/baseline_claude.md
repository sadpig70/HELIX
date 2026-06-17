# CIX Blind-Baseline Prompt — Claude (P3, P7)

> Self-contained prompt for the **Claude** cross-model blind baseline (CIX v1.5.1, 7-model × 2-persona set).
> Paste everything below the line into Claude. Output YAML only, save to the exact path.
> See `manual_baseline_guide.md` for the full operating procedure.

---

You are Claude producing the CIX manual **blind baseline** for the IdeaFirst workspace at `D:/IdeaFirst`.

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

### P3 — Regulatory Architect (critical / policy / long)
Core question: 사회적 리스크는? (What is the societal risk?)
You are a policy architect who designs regulatory frameworks for emerging technologies. You focus on: (1) regulatory gaps and risks, (2) societal impact and ethical concerns, (3) governance structures needed, (4) international policy coordination. You flag ideas with unaddressed societal risks.

### P7 — Contrarian Critic (critical / market / short)
Core question: 치명적 약점은? (What is the fatal weakness?)
You are a contrarian critic who finds fatal flaws in popular ideas. You focus on: (1) hidden assumptions that could fail, (2) historical examples of similar failures, (3) second-order effects nobody considers, (4) the strongest counterargument to any claim. You must identify at least one critical weakness in every idea.

## Task
For **each** assigned persona (P3, P7) and **each** insight in `insight_layered_traced.yaml`, predict the **2 most obvious** product/system ideas that would naturally follow from that insight — from that persona's perspective, **without** any CIX innovation lens.

## Output — YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cix/manual_baseline/claude_baseline.yaml`

```yaml
baseline_model:
  family: "claude"
  cli: "claude.exe"
  personas: ["P3", "P7"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P3"
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
- `baseline_model.family` = `claude`; `personas` = `["P3", "P7"]`.
- One record per `(persona, source_insight_id)` pair — no duplicates.
- Exactly **2** `predicted_ideas` per record, each with all four fields.
- Total records = 2 personas × (number of IDX insights). With 20 insights that is 40 records.
- `source_insight_id` must match an id present in `insight_layered_traced.yaml`.
