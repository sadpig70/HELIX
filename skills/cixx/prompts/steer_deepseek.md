# CIXX Steered-Generation Prompt — DeepSeek (P11, P12)

> Self-contained CIXX **category-steered generation** prompt (DeepSeek, 7-model x 2-persona set).
> Paste everything below the line into DeepSeek. Output YAML only, save to the exact path.
> Skill: `../SKILL.md` - steering overlay: `../strategies/steering_overlay.md`.

---

You are DeepSeek performing CIXX **category-steered idea generation** for the IdeaFirst workspace at `D:/IdeaFirst`.

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

### P11 — 적대적 견고성 분석가 / Adversarial Robustness Analyst (critical)
Core question: 어떻게 공격당하고, 공격 후에도 버티는가? (How is it attacked, and how does it survive?)
Generation framing: Design a system whose value is adversarial resilience — surviving and recovering from attack.

### P12 — 재생적 시스템 생태학자 / Regenerative Systems Ecologist (intuitive)
Core question: 생태계와 공진화하며 장기적으로 재생 가능한가? (Does it co-evolve and regenerate long-term?)
Generation framing: Design a regenerative system that co-evolves with its ecosystem rather than extracting from it.

## Task
For **each** assigned persona (P11, P12) and **each** insight in `insight_layered_traced.yaml`,
produce **up to 2** white-space ideas: apply CIX lenses, avoid consumed/overused categories, target white-space.

## Output - YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cixx/manual_steer/deepseek_steer.yaml`

```yaml
steer_model:
  family: "deepseek"
  cli: "deepseek"
  personas: ["P11", "P12"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
  category_map: ".cixx/category_map.yaml"
candidates:
  - persona: "P11"
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
- `steer_model.family` = `deepseek`; `personas` = ["P11", "P12"].
- Each idea applies >=1 CIX lens (lens_application present and traceable).
- `cixx_category.mechanism` must NOT be an `overused_mechanism` applied to an existing domain (saturated cell).
- Prefer `is_white_space: true`; mark `category_saturation` honestly (>=0.65 means too close to consumed - drop it).
- `source_insight_id` must match an id in `insight_layered_traced.yaml`.
