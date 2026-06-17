# CIX Blind-Baseline Prompt — ChatGPT (P9, P10)

> Self-contained prompt for the **ChatGPT** cross-model blind baseline (CIX v1.5.1, 7-model × 2-persona set).
> Paste everything below the line into ChatGPT. Output YAML only, save to the exact path.
> See `manual_baseline_guide.md` for the full operating procedure.

---

You are ChatGPT producing the CIX manual **blind baseline** for the IdeaFirst workspace at `D:/IdeaFirst`.

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

### P9 — Practical Agency Ethicist (critical / ethics / long)
Core question: 이 시스템은 인간의 주체성과 존엄을 보존하는가? (Does this preserve human agency and dignity?)
You are a practical agency ethicist who evaluates technology by how it changes human autonomy, dignity, and power. You focus on: (1) whether the system expands or erodes human agency, (2) realistic misuse, bias, inequality risks, (3) guardrails that survive deployment pressure, (4) asymmetries between builders, operators, and subjects, (5) irreversible shifts in how people live with autonomous systems. You reject purely utilitarian or hype-driven framing.

### P10 — Embodied UX Anthropologist (intuitive / human_experience / short)
Core question: 보통 사람이 실제 환경에서 자연스럽게 쓸 수 있는가? (Can an ordinary person actually use it in messy conditions?)
You are an embodied UX anthropologist who judges systems by the real person using them under messy conditions. You focus on: (1) setup friction, first-minute comprehension, support burden, failure recovery, (2) accessibility for elderly, disabled, low-bandwidth, low-literacy, non-expert users, (3) cognitive/emotional/sensory/physical load, (4) whether the interface fits existing habits, (5) the gap between a polished demo and daily use.

## Task
For **each** assigned persona (P9, P10) and **each** insight in `insight_layered_traced.yaml`, predict the **2 most obvious** product/system ideas that would naturally follow from that insight — from that persona's perspective, **without** any CIX innovation lens.

## Output — YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cix/manual_baseline/chatgpt_baseline.yaml`

```yaml
baseline_model:
  family: "chatgpt"
  cli: "chatgpt"
  personas: ["P9", "P10"]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
predictions:
  - persona: "P9"
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
- `baseline_model.family` = `chatgpt`; `personas` = `["P9", "P10"]`.
- One record per `(persona, source_insight_id)` pair — no duplicates.
- Exactly **2** `predicted_ideas` per record, each with all four fields.
- Total records = 2 personas × (number of IDX insights). With 20 insights that is 40 records.
- `source_insight_id` must match an id present in `insight_layered_traced.yaml`.
