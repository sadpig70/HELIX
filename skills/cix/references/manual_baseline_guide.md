# CIX Manual Baseline Guide

Version: 2026-06-08
Scope: `D:/IdeaFirst` local CIX v1.5.1 manual cross-model baseline

> **2026-06-08 update — 7-model × 14-persona.** The persona pool grew from 12 to 14
> (`P13` Historical Cycle Analyst, `P14` Mechanism Designer). The baseline now runs on
> **7 models × 2 personas = 14 personas, each covered exactly once**, adding Qwen as the
> 7th model. Assignment: grok=P1,P6 · kimi=P2,P5 · claude=P3,P7 · gemini=P4,P8 ·
> chatgpt=P9,P10 · deepseek=P11,P12 · qwen=P13,P14. `cix_manual_emit.py` auto-discovers
> every `*_baseline.yaml` by `baseline_model.family`, so filenames are free and the
> minimum-required set (`claude, gemini, kimi, grok`) is unchanged; the other three are
> recommended for full 14-persona coverage.

## 1. Purpose

CIX v1.5.1 requires a cross-model baseline for surprise validation. In local
Codex runs, Codex should not invent that baseline itself. A human operator runs
independent agent CLIs (Qwen 3.7 runs via the Windows Chrome runtime), saves their blind
predictions to standard YAML files, then CIX consumes those files through
`scripts/explore/cix_manual_emit.py`.

This guide is the single operational reference for that manual baseline step. The full
recommended run is 7 models covering all 14 PGF personas (2 each).

> **Ready-to-paste prompts.** Each model has a self-contained prompt file under
> `../prompts/` — paste it straight into the model, no assembly needed:
> `prompts/baseline_grok.md` (P1,P6) · `baseline_kimi.md` (P2,P5) · `baseline_claude.md` (P3,P7) ·
> `baseline_gemini.md` (P4,P8) · `baseline_chatgpt.md` (P9,P10) · `baseline_deepseek.md` (P11,P12) ·
> `baseline_qwen.md` (P13,P14). Index: `prompts/baseline_prompts_index.md`. The per-model prompt
> sections below (§6–§10.1) remain as the canonical source those files were generated from.

## 2. Standard Paths

Input files:

```text
D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml
D:/IdeaFirst/.idx/latest/manifest.yaml
D:/IdeaFirst/skills/pgf/discovery/personas.json
D:/IdeaFirst/skills/cix/prompts/lens_catalog.md
```

Output directory:

```text
D:/IdeaFirst/.cix/manual_baseline/
```

Output files (7-model recommended set; `claude, gemini, kimi, grok` are the required minimum):

```text
D:/IdeaFirst/.cix/manual_baseline/claude_baseline.yaml      # required
D:/IdeaFirst/.cix/manual_baseline/gemini_baseline.yaml      # required
D:/IdeaFirst/.cix/manual_baseline/kimi_baseline.yaml        # required
D:/IdeaFirst/.cix/manual_baseline/grok_baseline.yaml        # required
D:/IdeaFirst/.cix/manual_baseline/chatgpt_baseline.yaml     # recommended (P9, P10)
D:/IdeaFirst/.cix/manual_baseline/deepseek_baseline.yaml    # recommended (P11, P12)
D:/IdeaFirst/.cix/manual_baseline/qwen_baseline.yaml        # recommended (P13, P14)
```

## 3. Agent Assignment

```yaml
grok:
  cli: "grok"
  output: ".cix/manual_baseline/grok_baseline.yaml"
  personas: ["P1", "P6"]

kimi:
  cli: "kimi"
  output: ".cix/manual_baseline/kimi_baseline.yaml"
  personas: ["P2", "P5"]

claude:
  cli: "claude.exe"
  output: ".cix/manual_baseline/claude_baseline.yaml"
  personas: ["P3", "P7"]

gemini:
  cli: "agy.exe"
  output: ".cix/manual_baseline/gemini_baseline.yaml"
  personas: ["P4", "P8"]

chatgpt:
  cli: "chatgpt"
  output: ".cix/manual_baseline/chatgpt_baseline.yaml"
  personas: ["P9", "P10"]

deepseek:
  cli: "deepseek"
  output: ".cix/manual_baseline/deepseek_baseline.yaml"
  personas: ["P11", "P12"]

qwen:
  cli: "qwen-3.7 (Windows Chrome runtime)"
  output: ".cix/manual_baseline/qwen_baseline.yaml"
  personas: ["P13", "P14"]
```

7 models × 2 personas = all 14 PGF personas, each covered exactly once.

Each file should normally contain `2 personas × N insights` prediction records (e.g. with
20 IDX insights, 40 records). Read the actual insight count from the IDX round.

If an agent over-produces duplicate `(persona, source_insight_id)` records, the
current local CIX runner keeps the first record and drops later duplicates.
Agents should still be instructed to produce exactly 40 records.

## 4. Blind Baseline Rule

The external agent must predict obvious ideas from the IDX insight alone.

Do not reveal:

- CIX top ideas
- CIX lens assignments
- CIX scoring weights
- EVX winner
- AgentPACT/PACT project result

The goal is to measure whether CIX ideas are surprising compared with what an
independent model would naturally predict.

## 5. Required YAML Shape

```yaml
baseline_model:
  family: "claude"              # claude | gemini | kimi | grok | chatgpt | deepseek | qwen
  cli: "claude.exe"             # actual CLI or runner name
  personas: ["P3", "P7"]        # assigned personas only
  source_idx_round: "IDX-20260602-002"

predictions:
  - persona: "P3"
    source_insight_id: "INS-L6-001"
    predicted_ideas:
      - title: "Short obvious idea title"
        system_description: "One concise paragraph describing the obvious system."
        domains: ["domain one", "domain two", "domain three"]
        why_this_is_obvious_from_insight: "Explain why this naturally follows from the insight."
      - title: "Second obvious idea title"
        system_description: "One concise paragraph describing the second obvious system."
        domains: ["domain one", "domain two", "domain three"]
        why_this_is_obvious_from_insight: "Explain why this naturally follows from the insight."
```

Required constraints:

- YAML only. No Markdown wrapper.
- `baseline_model.family` must match the file family.
- `baseline_model.personas` must match the assigned personas.
- `predictions[].persona` must be one of the assigned personas.
- `predictions[].source_insight_id` must match an IDX insight id.
- Each `(persona, source_insight_id)` pair must appear once.
- Each prediction must contain exactly 2 `predicted_ideas`.
- Each `predicted_ideas[]` item must include all four fields shown above.

## 6. Common Prompt Block

Use this common block inside every agent prompt.

```text
You are producing a blind baseline for CIX surprise validation.

Workspace: D:/IdeaFirst

Read these files:
- D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml
- D:/IdeaFirst/.idx/latest/manifest.yaml
- D:/IdeaFirst/skills/pgf/discovery/personas.json

Do not read CIX, EVX, AOX, PACT, or GitHub project outputs.
Do not use CIX lens information or CIX scoring rules.

Task:
For each assigned PGF persona and each of the 20 IDX insights, predict the 2
most obvious product/system ideas that would naturally follow from that insight
without CIX innovation lenses.

Output YAML only. Do not wrap in Markdown. Save exactly to the requested file.
```

## 7. Claude Prompt

Save path:

```text
D:/IdeaFirst/.cix/manual_baseline/claude_baseline.yaml
```

Prompt:

```text
You are Claude producing the CIX manual blind baseline for IdeaFirst.

Use the common CIX manual baseline rules:
- Read only:
  - D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml
  - D:/IdeaFirst/.idx/latest/manifest.yaml
  - D:/IdeaFirst/skills/pgf/discovery/personas.json
- Do not read CIX, EVX, AOX, PACT, or GitHub project outputs.
- Do not use CIX lens information or CIX scoring rules.
- Output YAML only. No Markdown wrapper.

Assigned personas:
- P3
- P7

Output file:
D:/IdeaFirst/.cix/manual_baseline/claude_baseline.yaml

Required YAML:
baseline_model:
  family: "claude"
  cli: "claude.exe"
  personas: ["P3", "P7"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P3"
    source_insight_id: "INS-..."
    predicted_ideas:
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."

Produce exactly 40 prediction records:
2 personas x 20 insights.
Each record must have exactly 2 predicted_ideas.
```

## 8. Gemini / Antigravity `agy.exe` Prompt

Save path:

```text
D:/IdeaFirst/.cix/manual_baseline/gemini_baseline.yaml
```

Prompt:

```text
You are Gemini running through Antigravity CLI agy.exe, producing the CIX manual blind baseline for IdeaFirst.

Use the common CIX manual baseline rules:
- Read only:
  - D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml
  - D:/IdeaFirst/.idx/latest/manifest.yaml
  - D:/IdeaFirst/skills/pgf/discovery/personas.json
- Do not read CIX, EVX, AOX, PACT, or GitHub project outputs.
- Do not use CIX lens information or CIX scoring rules.
- Output YAML only. No Markdown wrapper.

Assigned personas:
- P4
- P8

Output file:
D:/IdeaFirst/.cix/manual_baseline/gemini_baseline.yaml

Required YAML:
baseline_model:
  family: "gemini"
  cli: "agy.exe"
  personas: ["P4", "P8"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P4"
    source_insight_id: "INS-..."
    predicted_ideas:
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."

Produce exactly 40 prediction records:
2 personas x 20 insights.
Each record must have exactly 2 predicted_ideas.
```

## 9. Kimi Prompt

Save path:

```text
D:/IdeaFirst/.cix/manual_baseline/kimi_baseline.yaml
```

Prompt:

```text
You are Kimi producing the CIX manual blind baseline for IdeaFirst.

Use the common CIX manual baseline rules:
- Read only:
  - D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml
  - D:/IdeaFirst/.idx/latest/manifest.yaml
  - D:/IdeaFirst/skills/pgf/discovery/personas.json
- Do not read CIX, EVX, AOX, PACT, or GitHub project outputs.
- Do not use CIX lens information or CIX scoring rules.
- Output YAML only. No Markdown wrapper.

Assigned personas:
- P2
- P5

Output file:
D:/IdeaFirst/.cix/manual_baseline/kimi_baseline.yaml

Required YAML:
baseline_model:
  family: "kimi"
  cli: "kimi"
  personas: ["P2", "P5"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P2"
    source_insight_id: "INS-..."
    predicted_ideas:
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."

Produce exactly 40 prediction records:
2 personas x 20 insights.
Each record must have exactly 2 predicted_ideas.
```

## 10. Grok Prompt

Save path:

```text
D:/IdeaFirst/.cix/manual_baseline/grok_baseline.yaml
```

Prompt:

```text
You are Grok producing the CIX manual blind baseline for IdeaFirst.

Use the common CIX manual baseline rules:
- Read only:
  - D:/IdeaFirst/.idx/latest/insight_layered_traced.yaml
  - D:/IdeaFirst/.idx/latest/manifest.yaml
  - D:/IdeaFirst/skills/pgf/discovery/personas.json
- Do not read CIX, EVX, AOX, PACT, or GitHub project outputs.
- Do not use CIX lens information or CIX scoring rules.
- Output YAML only. No Markdown wrapper.

Assigned personas:
- P1
- P6

Output file:
D:/IdeaFirst/.cix/manual_baseline/grok_baseline.yaml

Required YAML:
baseline_model:
  family: "grok"
  cli: "grok"
  personas: ["P1", "P6"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P1"
    source_insight_id: "INS-..."
    predicted_ideas:
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."

Produce exactly 40 prediction records:
2 personas x 20 insights.
Each record must have exactly 2 predicted_ideas.
Do not duplicate the same persona/source_insight_id pair.
```

## 10.1 ChatGPT / DeepSeek / Qwen Prompts (new personas P9–P14)

The three additional models cover the six newer personas. Reuse the **Common Prompt Block**
(§6) verbatim, changing only the family, CLI, output path, and the two assigned personas.
Qwen runs through the Windows Chrome runtime rather than a terminal CLI; produce the YAML in
that session and save it to the path below.

```yaml
chatgpt:
  output: ".cix/manual_baseline/chatgpt_baseline.yaml"
  family: "chatgpt"
  personas: ["P9", "P10"]      # Practical Agency Ethicist, Embodied UX Anthropologist

deepseek:
  output: ".cix/manual_baseline/deepseek_baseline.yaml"
  family: "deepseek"
  personas: ["P11", "P12"]     # Adversarial Robustness Analyst, Regenerative Systems Ecologist

qwen:
  output: ".cix/manual_baseline/qwen_baseline.yaml"
  family: "qwen"
  personas: ["P13", "P14"]     # Historical Cycle Analyst, Mechanism Designer
```

Required YAML (same shape as §5), e.g. for Qwen:

```yaml
baseline_model:
  family: "qwen"
  cli: "qwen-3.7 (Windows Chrome runtime)"
  personas: ["P13", "P14"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P13"
    source_insight_id: "INS-..."
    predicted_ideas:
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."
      - title: "..."
        system_description: "..."
        domains: ["...", "...", "..."]
        why_this_is_obvious_from_insight: "..."
```

Each of the three files must contain `2 personas × N insights` records (each record with
exactly 2 predicted_ideas), exactly as the four required models above. The blind baseline
rule (§4) applies identically: predict only from the IDX insight, never read CIX/EVX/AOX
outputs.

## 11. Completion Checklist

```text
Required (minimum quorum):
[ ] claude_baseline.yaml exists       (P3, P7)
[ ] gemini_baseline.yaml exists       (P4, P8)
[ ] kimi_baseline.yaml exists         (P2, P5)
[ ] grok_baseline.yaml exists         (P1, P6)
Recommended (full 14-persona coverage):
[ ] chatgpt_baseline.yaml exists      (P9, P10)
[ ] deepseek_baseline.yaml exists     (P11, P12)
[ ] qwen_baseline.yaml exists         (P13, P14)
[ ] all files parse as YAML
[ ] each file has baseline_model
[ ] each file has predictions
[ ] each assigned persona has N records (N = IDX insight count)
[ ] each record has exactly 2 predicted_ideas
[ ] across all files, personas P1–P14 are each covered once
```

## 12. Validation Commands

Basic parse check:

```powershell
cd D:/IdeaFirst
python -c "from pathlib import Path; import yaml; base=Path('.cix/manual_baseline'); files=sorted(p.name for p in base.glob('*_baseline.yaml')); [print(name, yaml.safe_load((base/name).read_text(encoding='utf-8'))['baseline_model']['family'], len(yaml.safe_load((base/name).read_text(encoding='utf-8')).get('predictions', []))) for name in files]"
```

CIX manual emit:

```powershell
cd D:/IdeaFirst
C:\Windows\py.exe scripts/explore/cix_manual_emit.py --project-root .
```

Then continue:

```powershell
C:\Windows\py.exe skills/evx/scripts/stage5_eval.py --evx-root .evx --verbose
C:\Windows\py.exe scripts/explore/evx_finalize.py --evx-root .evx --project-root .
C:\Windows\py.exe scripts/explore/aox_full.py --project-root . --mode full
C:\Windows\py.exe scripts/explore/aox_verify_latest.py --project-root .
```

## 13. AOX Behavior

When AOX reaches CIX and manual baseline files are missing or stale, it should
refer the operator to this guide:

```text
D:/IdeaFirst/skills/cix/references/manual_baseline_guide.md
```

AOX should not replace missing cross-model baseline with Codex-only heuristic
surprise scoring. If external baseline is required and unavailable, the honest
state is `blocked` or `manual_baseline_required`.
