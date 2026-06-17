"""Generate the 7 per-model IDXX steered-distillation prompts (steer_<model>.md).

Mirrors cixx/prompts structure, but the role is evidence-floored insight DISTILLATION
steered away from already-built insight themes. Idempotent.
"""
import os

PERSONAS = {
    'P1': ('파괴적 엔지니어 / Disruptive Engineer', 'creative', '기존을 완전히 뒤집으면?',
           'Surface the inverted-assumption insight the loud trend hides.'),
    'P2': ('냉정한 투자자 / Cold-eyed Investor', 'analytical', '2년 내 수익화 경로는?',
           'Surface insights about near-term value gaps in under-served niches.'),
    'P3': ('규제 설계자 / Regulatory Architect', 'critical', '사회적 리스크는?',
           'Surface governance/accountability GAP insights (L6) nobody yet owns.'),
    'P4': ('연결하는 과학자 / Connecting Scientist', 'intuitive', '다른 분야 원리와 연결?',
           'Surface CROSS-TREND insights linking two distant trends (counterfactual/generative).'),
    'P5': ('현장 운영자 / Field Operator', 'analytical', '내일 배포하려면?',
           'Surface operational-gap insights grounded in field evidence.'),
    'P6': ('미래 사회학자 / Future Sociologist', 'intuitive', '10년 후 행동 변화는?',
           'Surface long-horizon behavioral-shift insights the current discourse misses.'),
    'P7': ('반골 비평가 / Contrarian Critic', 'critical', '치명적 약점은?',
           'Surface TENSION insights (L7) where two forces collide and nobody resolves it.'),
    'P8': ('융합 아키텍트 / Convergence Architect', 'creative', '전혀 다른 둘을 합치면?',
           'Surface GENERATIVE insights (L10) from merging two unrelated trend surfaces.'),
    'P9': ('실천적 주체성 윤리학자 / Practical Agency Ethicist', 'critical', '인간 주체성·존엄 보존?',
           'Surface insights where automation silently erodes human agency.'),
    'P10': ('체화된 UX 인류학자 / Embodied UX Anthropologist', 'intuitive', '실제 환경에서 자연스럽게?',
            'Surface insights about real-world embodied friction the trend data overlooks.'),
    'P11': ('적대적 견고성 분석가 / Adversarial Robustness Analyst', 'critical', '어떻게 공격당하고 버티는가?',
            'Surface COUNTERFACTUAL insights (L9): what breaks under adversarial pressure?'),
    'P12': ('재생적 시스템 생태학자 / Regenerative Systems Ecologist', 'intuitive', '생태계와 공진화·재생?',
            'Surface insights about regenerative/co-evolution gaps in the trend.'),
    'P13': ('역사적 사이클 분석가 / Historical Cycle Analyst', 'analytical', '과거 사이클 반복, 이번엔 뭐가 다른가?',
            'Surface insights naming which historical cycle repeats and what is genuinely new now.'),
    'P14': ('메커니즘 디자이너 / Mechanism Designer', 'creative', '어떤 인센티브 메커니즘이 자생하는가?',
            'Surface insights about missing incentive/market mechanisms (generative).'),
}

MODELS = [
    ('grok', 'Grok', 'grok', ['P1', 'P6']),
    ('kimi', 'Kimi', 'kimi', ['P2', 'P5']),
    ('claude', 'Claude', 'claude.exe', ['P3', 'P7']),
    ('gemini', 'Gemini', 'agy.exe', ['P4', 'P8']),
    ('chatgpt', 'ChatGPT', 'chatgpt', ['P9', 'P10']),
    ('deepseek', 'DeepSeek', 'deepseek', ['P11', 'P12']),
    ('qwen', 'Qwen', 'Windows Chrome runtime', ['P13', 'P14']),
]

HERE = os.path.dirname(os.path.abspath(__file__))


def persona_block(pid):
    name, style, core, framing = PERSONAS[pid]
    return ('### {pid} — {name} ({style})\n'
            'Core question: {core}\n'
            'Distillation framing: {framing}\n').format(pid=pid, name=name, style=style, core=core, framing=framing)


def build(family, display, cli, personas):
    pid_str = ', '.join(personas)
    pblocks = '\n'.join(persona_block(p) for p in personas)
    return '''# IDXX Steered-Distillation Prompt — {display} ({pid_str})

> Self-contained IDXX **saturation-steered distillation** prompt ({display}, 7-model x 2-persona set).
> Paste everything below the line into {display}. Output YAML only, save to the exact path.
> Skill: `../SKILL.md` - steering overlay: `../strategies/steering_overlay.md`.

---

You are {display} performing IDXX **insight-saturation-steered distillation** for the IdeaFirst workspace at `D:/IdeaFirst`.

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

{pblocks}
## Task
For **each** assigned persona ({pid_str}), distill insights from the TCX trends that are
(a) evidence-traced, (b) NOT in built_upon themes, (c) under-distilled (weak-signal / cross-trend).
Produce **up to 3** such insights per persona. If only built-upon or weak-evidence themes remain, produce fewer and say why.

## Output - YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.idxx/manual_steer/{family}_steer.yaml`

```yaml
steer_model:
  family: "{family}"
  cli: "{cli}"
  personas: [{persona_list}]
  source_tcx_round: "<read from .tcx/latest/manifest.yaml>"
  saturation_map: ".idxx/insight_saturation_map.yaml"
candidates:
  - persona: "{first_persona}"
    layer: "L6_Gap"                    # one of L6_Gap / L7_Tension / L9_Counterfactual / L10_Generative (+L8 if active)
    statement: "One precise insight sentence."
    evidence:                          # ★ MANDATORY (evidence-floor) - from TCX
      - source_tcx_item: "<id/section>"
        quote: "verbatim supporting quote from TCX"
        confidence: 0.0
    why_it_matters: "..."
    what_is_missing: "..."
    idxx_steering: {{ built_upon_overlap: 0.NN, is_under_distilled: true, demoted: false }}
  # ... repeat per persona; up to 3 insights each
```

## Constraints (must all hold)
- YAML only. No Markdown fences in the saved file.
- `steer_model.family` = `{family}`; `personas` = [{persona_list}].
- ★ Every insight has a non-empty `evidence` list with a verbatim TCX quote (evidence-floor). No evidence -> drop.
- `idxx_steering.built_upon_overlap` honest; >=0.65 means too close to a built-upon theme -> drop it.
- `layer` must be a valid IDX deep layer; respect IDX layer floors across your output.
- Prefer `is_under_distilled: true`; do NOT restate a built_upon insight in the same layer.
'''.format(display=display, pid_str=pid_str, family=family, cli=cli, pblocks=pblocks,
           persona_list=', '.join('"{}"'.format(p) for p in personas), first_persona=personas[0])


for family, display, cli, personas in MODELS:
    path = os.path.join(HERE, 'steer_{}.md'.format(family))
    open(path, 'w', encoding='utf-8').write(build(family, display, cli, personas))
    print('wrote', path)
print('done:', len(MODELS), 'model prompts')
