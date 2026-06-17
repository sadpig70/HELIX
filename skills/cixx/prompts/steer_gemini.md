# CIXX Steered-Generation Prompt — Gemini (P4, P8)

> Self-contained CIXX **category-steered generation** prompt (Gemini, 7-model x 2-persona set).
> Paste everything below the line into Gemini. Output YAML only, save to the exact path.
> Skill: `../SKILL.md` - steering overlay: `../strategies/steering_overlay.md`.

---

You are Gemini performing CIXX **category-steered idea generation** for the IdeaFirst workspace at `D:/IdeaFirst`.

## Why this exists
The consumed-idea ledger shows which (domain x mechanism) categories are already built or saturated. CIXX generates ideas in **white-space** - under-explored categories. Apply CIX innovation lenses to the IDX insights to produce **novel** ideas that land **outside** the saturated cells. (This is NOT the CIX blind baseline; here you DO use lenses and you DO aim to be novel.)

## Read these files
- `D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml`  (insights to generate from)
- `D:/IdeaFirst/.idx/latest/manifest.yaml`  (source_idx_round)
- `D:/IdeaFirst/.cixx/category_map.yaml`  (★ steering input: overused_mechanisms, saturated_cells, white-space)
- `D:/IdeaFirst/skills/cix/prompts/lens_catalog.md`  (20 innovation lenses - canonical)

## Category steering (from category_map.yaml - STRICT)
1. Do NOT generate ideas in `saturated_cells`. Do NOT reapply an `overused_mechanism`
   (e.g. compatibility-mesh) to an existing domain - that exact pattern is the homogenization cause.
2. **covered != forbidden**: a saturated *domain* with a **genuinely different mechanism** is allowed and encouraged.
   Avoid by (domain x mechanism) **cell**, never by domain alone.
3. Actively target **white-space**: prefer `underused_mechanisms` and novel mechanism forms; fill uncovered cells.
4. Every idea must apply >=1 CIX lens with a traceable transformation. Do not force quantity into saturated cells -
   if an insight only yields saturated-category ideas from a persona, output fewer and say why.

## Your assigned personas
Generate strictly from each persona's viewpoint below.

### P4 — 연결하는 과학자 / Connecting Scientist (intuitive)
Core question: 다른 분야 원리와 연결? (Connect a principle from a distant field?)
Generation framing: Transplant a mechanism from a distant scientific domain into the insight to create something structurally new.

### P8 — 융합 아키텍트 / Convergence Architect (creative)
Core question: 전혀 다른 둘을 합치면? (What if we merge two unrelated things?)
Generation framing: Compose two unrelated domains/mechanisms into one system that neither field would build alone.

## Task
For **each** assigned persona (P4, P8) and **each** insight in `insight_layered_traced.yaml`,
produce **up to 2** white-space ideas: apply CIX lenses, avoid consumed/overused categories, target white-space.

## Output - YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cixx/manual_steer/gemini_steer.yaml`

```yaml
steer_model:
  family: "gemini"
  cli: "agy.exe"
  personas: ["P4", "P8"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
  category_map: ".cixx/category_map.yaml"
candidates:
  - persona: "P4"
    source_insight_id: "INS-..."        # an id from insight_layered_traced.yaml
    title: "Short idea title"
    system_description: "One concise paragraph describing the system."
    domains: ["domain one", "domain two", "domain three"]
    lens_application:
      primary_lens: "L.."               # a lens id from lens_catalog.md
      lens_stack: ["L..", "L.."]        # optional multi-lens
      transformation: "How the lens(es) turn the insight into this system."
    cixx_category: { domain: "...", mechanism: "...", is_white_space: true }
    category_saturation: 0.NN           # estimated overlap vs consumed categories (lower = more novel)
    novelty_vs_consumed: "One line: which mechanism/domain/cell makes this different from consumed ideas."
  # ... repeat per (persona, insight); up to 2 ideas each
```

## Constraints (must all hold)
- YAML only. No Markdown fences in the saved file.
- `steer_model.family` = `gemini`; `personas` = ["P4", "P8"].
- Each idea applies >=1 CIX lens (lens_application present and traceable).
- `cixx_category.mechanism` must NOT be an `overused_mechanism` applied to an existing domain (saturated cell).
- Prefer `is_white_space: true`; mark `category_saturation` honestly (>=0.65 means too close to consumed - drop it).
- `source_insight_id` must match an id in `insight_layered_traced.yaml`.
