# CIXX Steered-Generation Prompts — Index (7 models × 2 personas = 14)

Ready-to-paste **category-steered generation** prompts, one file per model. Each file is
**self-contained** (CIXX steering rule + assigned persona definitions + CIX lens reference +
required YAML shape + save path) — paste the content below its `---` line into the target model.
Full skill: `../SKILL.md`. Steering overlay: `../strategies/steering_overlay.md`.

> ⚠️ CIX `prompts/baseline_*.md` vs CIXX `prompts/steer_*.md` — **다른 역할**:
> - CIX baseline = lens 없이 *obvious* 예측 (surprise 측정용, blind).
> - CIXX steer = CIX 렌즈를 **사용**해 *white-space* 아이디어 생성 + 소모-카테고리 회피 (조향).

| Model | File | Personas | Output |
|---|---|---|---|
| Grok | `steer_grok.md` | P1, P6 | `.cixx/manual_steer/grok_steer.yaml` |
| Kimi | `steer_kimi.md` | P2, P5 | `.cixx/manual_steer/kimi_steer.yaml` |
| Claude | `steer_claude.md` | P3, P7 | `.cixx/manual_steer/claude_steer.yaml` |
| Gemini | `steer_gemini.md` | P4, P8 | `.cixx/manual_steer/gemini_steer.yaml` |
| ChatGPT | `steer_chatgpt.md` | P9, P10 | `.cixx/manual_steer/chatgpt_steer.yaml` |
| DeepSeek | `steer_deepseek.md` | P11, P12 | `.cixx/manual_steer/deepseek_steer.yaml` |
| Qwen | `steer_qwen.md` | P13, P14 | `.cixx/manual_steer/qwen_steer.yaml` |

Coverage: all 14 PGF discovery personas, each by exactly one model (same assignment as CIX baseline).

## Shared inputs (every model reads)
- `D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml` — insights to generate from
- `D:/IdeaFirst/.idx/latest/manifest.yaml` — `source_idx_round`
- `D:/IdeaFirst/.cixx/category_map.yaml` — ★ consumed-category saturation map (steering input)
- `D:/IdeaFirst/skills/cix/prompts/lens_catalog.md` — 20 innovation lenses (canonical)
- `D:/IdeaFirst/skills/pgf/discovery/personas.json` — persona definitions

## Build the category map first (deterministic)
```bash
python skills/cixx/scripts/build_category_map.py --ledger .idea-ledger/consumed_ideas.yaml --out .cixx
# → .cixx/category_map.yaml  (overused_mechanisms, saturated_cells, white-space targets)
```
Regenerate per round so the steering reflects the **current** consumed ledger.

## Steering rule (applies to every model — see steering_overlay.md)
1. **Do NOT** generate ideas in `saturated_cells`; **do NOT** reapply an `overused_mechanism`
   (e.g. compatibility-mesh) to an existing domain. ← this pattern is the homogenization cause.
2. **covered ≠ forbidden**: a saturated *domain* with a **genuinely different mechanism** is allowed/encouraged.
   Avoid by (domain × mechanism) cell, never by domain alone.
3. Actively target **white-space**: underused/novel mechanisms; uncovered (domain × mechanism) cells.
4. CIX quality holds: `lens_application_traceable` true, 6-axis quality intact. Do not force quantity into saturated cells.

## Per-round reminder
Each round consumes the **current** IDX insights and the **current** `category_map.yaml`
(rebuilt from the latest `.idea-ledger/consumed_ideas.yaml`). `source_idx_round` in each file
must match `.idx/latest/manifest.yaml`.

## Downstream
Collected `*_steer.yaml` → CIXX merge (dedup by category, white-space floor) → CIX `idea_pool`
schema → EVX/AOX unchanged. EVX's exact consumed filter stays as the post-generation safety net.
