# CIX Baseline Prompts — Index (7 models × 2 personas = 14)

Ready-to-paste blind-baseline prompts, one file per model. Each file is **self-contained**
(blind rules + assigned persona definitions + required YAML shape + save path) — paste the
content below its `---` line into the target model. Full procedure: `../references/manual_baseline_guide.md`.

| Model | File | Personas | CLI / runtime | Output |
|---|---|---|---|---|
| Grok | `baseline_grok.md` | P1, P6 | `grok` | `.cix/manual_baseline/grok_baseline.yaml` |
| Kimi | `baseline_kimi.md` | P2, P5 | `kimi` | `.cix/manual_baseline/kimi_baseline.yaml` |
| Claude | `baseline_claude.md` | P3, P7 | `claude.exe` | `.cix/manual_baseline/claude_baseline.yaml` |
| Gemini | `baseline_gemini.md` | P4, P8 | `agy.exe` | `.cix/manual_baseline/gemini_baseline.yaml` |
| ChatGPT | `baseline_chatgpt.md` | P9, P10 | `chatgpt` | `.cix/manual_baseline/chatgpt_baseline.yaml` |
| DeepSeek | `baseline_deepseek.md` | P11, P12 | `deepseek` | `.cix/manual_baseline/deepseek_baseline.yaml` |
| Qwen 3.7 | `baseline_qwen.md` | P13, P14 | Windows Chrome runtime | `.cix/manual_baseline/qwen_baseline.yaml` |

Coverage: all 14 PGF personas, each by exactly one model.

## Required minimum vs recommended
- **Required minimum** (CIX round validates with these 4): Grok, Kimi, Claude, Gemini — covers P1–P8.
- **Recommended** for full 14-persona coverage: ChatGPT, DeepSeek, Qwen — covers P9–P14.
- `cix_manual_emit.py` auto-discovers every `*_baseline.yaml` by `baseline_model.family`, so adding the recommended three is purely additive.

## Per-round reminder
Each new CIX round consumes the **current** IDX insights. Regenerate all baseline files
against `.idx/latest/insight_layered_traced.yaml` for that round (do not reuse a previous
round's predictions). `source_idx_round` in each file must match `.idx/latest/manifest.yaml`.

## Blind rule (applies to every model)
Predict only from the IDX insight. Never read CIX / EVX / AOX / PACT / published project
outputs, and never use CIX lens information or scoring. The point is to measure how
surprising CIX ideas are versus what an independent model predicts naturally.
