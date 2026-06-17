# IDXX Steered-Distillation Prompts — Index (7 models × 2 personas = 14)

Ready-to-paste **insight-saturation-steered distillation** prompts, one file per model. Each file is
**self-contained** (IDXX steering + ★evidence-floor + assigned personas + required YAML shape + save path).
Full skill: `../SKILL.md`. Steering overlay: `../strategies/steering_overlay.md`.

> ⚠️ Role: steer IDX **insight distillation** away from *already-built* insight themes (provenance walk)
> toward **under-distilled / weak-signal / cross-trend** insights — WITHOUT lowering IDX's evidence bar.

| Model | File | Personas | Output |
|---|---|---|---|
| Grok | `steer_grok.md` | P1, P6 | `.idxx/manual_steer/grok_steer.yaml` |
| Kimi | `steer_kimi.md` | P2, P5 | `.idxx/manual_steer/kimi_steer.yaml` |
| Claude | `steer_claude.md` | P3, P7 | `.idxx/manual_steer/claude_steer.yaml` |
| Gemini | `steer_gemini.md` | P4, P8 | `.idxx/manual_steer/gemini_steer.yaml` |
| ChatGPT | `steer_chatgpt.md` | P9, P10 | `.idxx/manual_steer/chatgpt_steer.yaml` |
| DeepSeek | `steer_deepseek.md` | P11, P12 | `.idxx/manual_steer/deepseek_steer.yaml` |
| Qwen | `steer_qwen.md` | P13, P14 | `.idxx/manual_steer/qwen_steer.yaml` |

Coverage: all 14 PGF discovery personas (IDX Persona↔Layer aligned), each by exactly one model.

## Shared inputs (every model reads)
- `D:/IdeaFirst/.tcx/latest/` — trend collection to distill from (with evidence)
- `D:/IdeaFirst/.idxx/insight_saturation_map.yaml` — ★ built-upon insight themes (steering input)
- `D:/IdeaFirst/skills/idx/SKILL.md` — 10-layer hierarchy + evidence-trace rules (canonical)
- `D:/IdeaFirst/skills/pgf/discovery/personas.json` — persona definitions

## Build the saturation map first (deterministic provenance walk)
```bash
python skills/idxx/scripts/build_insight_saturation_map.py --ledger .idea-ledger/consumed_ideas.yaml --out .idxx
# → .idxx/insight_saturation_map.yaml (built_upon_insights, recurring_topics, layer history)
```
Regenerate per round so steering reflects the **current** consumed ledger + IDX round history.

## Steering rule (every model — see steering_overlay.md)
1. Do NOT re-distill insight themes in `built_upon_insights` (already spawned built projects).
2. **covered ≠ forbidden**: a built-upon *topic* with a different layer/tension/angle is allowed.
3. Target **under-distilled**: weak-signal, cross-trend insights; under-used layers (keep IDX layer floors).
4. ★★ **EVIDENCE-FLOOR**: every output insight must carry IDX evidence trace (source_tcx_items + quote +
   confidence). Never promote a weak-evidence pattern to dodge recurrence. Evidence > novelty.

## Per-round reminder
Each round consumes the **current** TCX trends and the **current** `insight_saturation_map.yaml`.
`source_tcx_round` must match `.tcx/latest/manifest.yaml`.

## Downstream
Collected `*_steer.yaml` → IDXX merge (theme dedup, layer + evidence floor) → IDX
`insight_layered_traced` schema → CIX/CIXX/EVX/AOX unchanged.
