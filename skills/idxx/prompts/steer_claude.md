# IDXX Steered-Distillation Prompt — Claude (P3, P7)

> Self-contained IDXX **saturation-steered distillation** prompt (Claude, 7-model x 2-persona set).
> Paste everything below the line into Claude. Output YAML only, save to the exact path.
> Skill: `../SKILL.md` - steering overlay: `../strategies/steering_overlay.md`.

---

You are Claude performing IDXX **insight-saturation-steered distillation** for the IdeaFirst workspace at `D:/IdeaFirst`.

## Why this exists
IDX keeps re-distilling the same loud macro-trends, re-surfacing insights that have ALREADY spawned built projects. IDXX steers distillation toward **under-explored** insights. The saturation map (built via provenance walk: consumed idea -> source insight) lists insight themes already built upon. Your job: distill insights from the TCX trends that land **outside** those built-upon themes - WITHOUT lowering IDX's evidence bar.

## Read these files
- `D:/IdeaFirst/.tcx/latest/`  (trend collection to distill from, WITH evidence)
- `D:/IdeaFirst/.idxx/insight_saturation_map.yaml`  (★ steering input: built_upon_insights, recurring_topics, layer history)
- `D:/IdeaFirst/skills/idx/SKILL.md`  (10-layer hierarchy + evidence-trace rules - canonical)

## Saturation steering (from insight_saturation_map.yaml - STRICT)
1. Do NOT re-distill insight themes in `built_upon_insights` (already spawned built projects).
2. **covered != forbidden**: a built-upon *topic* with a different layer/tension/angle is allowed and encouraged.
   Demote by (topic x layer) cell, never block a whole macro-trend.
3. Target **under-distilled**: weak-signal insights drowned out by loud trends; cross-trend insights linking
   two trends; under-used layers (but keep IDX layer floors L6/L7/L9/L10).
4. ★★ **EVIDENCE-FLOOR (absolute)**: every output insight MUST carry IDX evidence trace
   (source_tcx_items + quote + confidence). NEVER promote a weak-evidence pattern just to be novel.
   If an under-distilled angle lacks evidence in TCX, drop it. Evidence > novelty.

## Your assigned personas
Distill strictly from each persona's viewpoint below (IDX Persona<->Layer aligned).

### P3 — 규제 설계자 / Regulatory Architect (critical)
Core question: 사회적 리스크는?
Distillation framing: Surface governance/accountability GAP insights (L6) nobody yet owns.

### P7 — 반골 비평가 / Contrarian Critic (critical)
Core question: 치명적 약점은?
Distillation framing: Surface TENSION insights (L7) where two forces collide and nobody resolves it.

## Task
For **each** assigned persona (P3, P7), distill insights from the TCX trends that are
(a) evidence-traced, (b) NOT in built_upon themes, (c) under-distilled (weak-signal / cross-trend).
Produce **up to 3** such insights per persona. If only built-upon or weak-evidence themes remain, produce fewer and say why.

## Output - YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.idxx/manual_steer/claude_steer.yaml`

```yaml
steer_model:
  family: "claude"
  cli: "claude.exe"
  personas: ["P3", "P7"]
  source_tcx_round: "<read from .tcx/latest/manifest.yaml>"
  saturation_map: ".idxx/insight_saturation_map.yaml"
candidates:
  - persona: "P3"
    layer: "L6_Gap"                    # one of L6_Gap / L7_Tension / L9_Counterfactual / L10_Generative (+L8 if active)
    statement: "One precise insight sentence."
    evidence:                          # ★ MANDATORY (evidence-floor) - from TCX
      - source_tcx_item: "<id/section>"
        quote: "verbatim supporting quote from TCX"
        confidence: 0.0
    why_it_matters: "..."
    what_is_missing: "..."
    idxx_steering: { built_upon_overlap: 0.NN, is_under_distilled: true, demoted: false }
  # ... repeat per persona; up to 3 insights each
```

## Constraints (must all hold)
- YAML only. No Markdown fences in the saved file.
- `steer_model.family` = `claude`; `personas` = ["P3", "P7"].
- ★ Every insight has a non-empty `evidence` list with a verbatim TCX quote (evidence-floor). No evidence -> drop.
- `idxx_steering.built_upon_overlap` honest; >=0.65 means too close to a built-upon theme -> drop it.
- `layer` must be a valid IDX deep layer; respect IDX layer floors across your output.
- Prefer `is_under_distilled: true`; do NOT restate a built_upon insight in the same layer.
