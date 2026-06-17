"""Generate the 7 per-model CIXX steered-generation prompts (steer_<model>.md).

Mirrors cix/prompts/baseline_<model>.md structure, but the role is category-steered
white-space GENERATION (lenses used) rather than blind obvious prediction.
Run once to (re)emit the prompt files. Idempotent.
"""
import os

PERSONAS = {
    'P1': ('파괴적 엔지니어 / Disruptive Engineer', 'creative', '기존을 완전히 뒤집으면? (What if we fully invert the status quo?)',
           'Invert the dominant assumption of the insight and design the system that only makes sense after the inversion.'),
    'P2': ('냉정한 투자자 / Cold-eyed Investor', 'analytical', '2년 내 수익화 경로는? (What is the path to revenue within 2 years?)',
           'Design a system with a concrete near-term monetization path in an under-served niche, not a crowded market.'),
    'P3': ('규제 설계자 / Regulatory Architect', 'critical', '사회적 리스크는? (What is the societal risk?)',
           'Design a system that closes a governance/accountability gap nobody yet owns.'),
    'P4': ('연결하는 과학자 / Connecting Scientist', 'intuitive', '다른 분야 원리와 연결? (Connect a principle from a distant field?)',
           'Transplant a mechanism from a distant scientific domain into the insight to create something structurally new.'),
    'P5': ('현장 운영자 / Field Operator', 'analytical', '내일 배포하려면? (What would it take to deploy tomorrow?)',
           'Design a deployable system for an operational gap, favoring a beachhead that can ship fast.'),
    'P6': ('미래 사회학자 / Future Sociologist', 'intuitive', '10년 후 행동 변화는? (How will behavior change in 10 years?)',
           'Design for a long-horizon behavioral shift the current market has not built for.'),
    'P7': ('반골 비평가 / Contrarian Critic', 'critical', '치명적 약점은? (What is the fatal weakness?)',
           'Find the fatal weakness in the obvious idea, then design the system that exists precisely because of that weakness.'),
    'P8': ('융합 아키텍트 / Convergence Architect', 'creative', '전혀 다른 둘을 합치면? (What if we merge two unrelated things?)',
           'Compose two unrelated domains/mechanisms into one system that neither field would build alone.'),
    'P9': ('실천적 주체성 윤리학자 / Practical Agency Ethicist', 'critical', '인간의 주체성과 존엄을 보존하는가? (Does it preserve human agency and dignity?)',
           'Design a system whose core value is preserving human agency where automation erodes it.'),
    'P10': ('체화된 UX 인류학자 / Embodied UX Anthropologist', 'intuitive', '보통 사람이 실제 환경에서 자연스럽게 쓰는가? (Will ordinary people use it naturally in the real world?)',
            'Design for real-world, embodied everyday use that current systems ignore.'),
    'P11': ('적대적 견고성 분석가 / Adversarial Robustness Analyst', 'critical', '어떻게 공격당하고, 공격 후에도 버티는가? (How is it attacked, and how does it survive?)',
            'Design a system whose value is adversarial resilience — surviving and recovering from attack.'),
    'P12': ('재생적 시스템 생태학자 / Regenerative Systems Ecologist', 'intuitive', '생태계와 공진화하며 장기적으로 재생 가능한가? (Does it co-evolve and regenerate long-term?)',
            'Design a regenerative system that co-evolves with its ecosystem rather than extracting from it.'),
    'P13': ('역사적 사이클 분석가 / Historical Cycle Analyst', 'analytical', '과거 어떤 사이클의 반복이고, 이번엔 무엇이 진짜 다른가? (Which past cycle repeats, and what is truly different now?)',
            'Identify the historical cycle the insight repeats and design for what is genuinely different this time.'),
    'P14': ('메커니즘 디자이너 / Mechanism Designer', 'creative', '어떤 인센티브·시장 메커니즘이 이 가치를 자생적으로 창출·유지하는가? (What incentive/market mechanism sustains this value?)',
            'Design the incentive/market mechanism that makes the value self-sustaining — a mechanism not yet in the consumed ledger.'),
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
            'Generation framing: {framing}\n').format(pid=pid, name=name, style=style, core=core, framing=framing)


def build(family, display, cli, personas):
    pid_str = ', '.join(personas)
    pblocks = '\n'.join(persona_block(p) for p in personas)
    return '''# CIXX Steered-Generation Prompt — {display} ({pid_str})

> Self-contained CIXX **category-steered generation** prompt ({display}, 7-model x 2-persona set).
> Paste everything below the line into {display}. Output YAML only, save to the exact path.
> Skill: `../SKILL.md` - steering overlay: `../strategies/steering_overlay.md`.

---

You are {display} performing CIXX **category-steered idea generation** for the IdeaFirst workspace at `D:/IdeaFirst`.

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

{pblocks}
## Task
For **each** assigned persona ({pid_str}) and **each** insight in `insight_layered_traced.yaml`,
produce **up to 2** white-space ideas: apply CIX lenses, avoid consumed/overused categories, target white-space.

## Output - YAML only, no Markdown wrapper
Save exactly to: `D:/IdeaFirst/.cixx/manual_steer/{family}_steer.yaml`

```yaml
steer_model:
  family: "{family}"
  cli: "{cli}"
  personas: [{persona_list}]
  source_idx_round: "<read from .idx/latest/manifest.yaml>"
  category_map: ".cixx/category_map.yaml"
candidates:
  - persona: "{first_persona}"
    source_insight_id: "INS-..."        # an id from insight_layered_traced.yaml
    title: "Short idea title"
    system_description: "One concise paragraph describing the system."
    domains: ["domain one", "domain two", "domain three"]
    lens_application:
      primary_lens: "L.."               # a lens id from lens_catalog.md
      lens_stack: ["L..", "L.."]        # optional multi-lens
      transformation: "How the lens(es) turn the insight into this system."
    cixx_category: {{ domain: "...", mechanism: "...", is_white_space: true }}
    category_saturation: 0.NN           # estimated overlap vs consumed categories (lower = more novel)
    novelty_vs_consumed: "One line: which mechanism/domain/cell makes this different from consumed ideas."
  # ... repeat per (persona, insight); up to 2 ideas each
```

## Constraints (must all hold)
- YAML only. No Markdown fences in the saved file.
- `steer_model.family` = `{family}`; `personas` = [{persona_list}].
- Each idea applies >=1 CIX lens (lens_application present and traceable).
- `cixx_category.mechanism` must NOT be an `overused_mechanism` applied to an existing domain (saturated cell).
- Prefer `is_white_space: true`; mark `category_saturation` honestly (>=0.65 means too close to consumed - drop it).
- `source_insight_id` must match an id in `insight_layered_traced.yaml`.
'''.format(display=display, pid_str=pid_str, family=family, cli=cli, pblocks=pblocks,
           persona_list=', '.join('"{}"'.format(p) for p in personas), first_persona=personas[0])


for family, display, cli, personas in MODELS:
    path = os.path.join(HERE, 'steer_{}.md'.format(family))
    open(path, 'w', encoding='utf-8').write(build(family, display, cli, personas))
    print('wrote', path)
print('done:', len(MODELS), 'model prompts')
