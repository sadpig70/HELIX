"""IDXX Insight Saturation Map builder (deterministic).

Builds the steering input for IDXX-guided IDX distillation:
  1. built_upon_insights  — insight statements that already spawned BUILT projects
     (provenance walk: consumed idea -> CIX round idea_pool -> source_insight_id
      -> IDX round insight statement). These themes get DEMOTED (re-distilling them is waste).
  2. recurring_topics     — topic keywords distilled across multiple IDX rounds (over-distilled).
  3. layer_history        — layer distribution per IDX round.
  4. under_distilled       — guidance toward weak-signal / cross-trend / under-used layers.

★ evidence-floor: this map only DEMOTES built-upon themes. It never asks IDX to promote a
  non-evidence-traced pattern. Novelty steering operates strictly within evidence-backed candidates.

Usage:
    python build_insight_saturation_map.py [--ledger PATH] [--out DIR]
"""

from __future__ import annotations

import argparse
import glob
import os
import re
from collections import Counter, OrderedDict
from datetime import datetime, timezone

import yaml


class OD(OrderedDict):
    pass


yaml.add_representer(OD, lambda d, x: d.represent_mapping('tag:yaml.org,2002:map', x.items()))

STOP = set('a an the of to in on for and or but with without is are be by from as at into not no '
           'this that these those it its their an more less than then also can could would should '
           'rarely does do not yet but while when which who where what how across over under most'.split())


def topics(text: str) -> list[str]:
    """Extract significant topic tokens (lowercased words >=4 chars, non-stopword)."""
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", (text or '').lower())
    return [w for w in words if w not in STOP]


def load_yaml(path):
    try:
        return yaml.safe_load(open(path, encoding='utf-8'))
    except Exception:
        return None


def find_round_dir(base, round_id):
    p = os.path.join(base, 'rounds', round_id)
    return p if os.path.isdir(p) else None


def insight_statement(idx_round, insight_id):
    d = find_round_dir('.idx', idx_round)
    if not d:
        return None
    doc = load_yaml(os.path.join(d, 'insight_layered_traced.yaml')) or {}
    ins = (doc.get('distillation') or {}).get('insights') or doc.get('insights') or []
    for it in ins:
        if it.get('id') == insight_id:
            return it.get('statement'), it.get('layer')
    return None


def idea_source_insight(cix_round, idea_id):
    d = find_round_dir('.cix', cix_round)
    if not d:
        return None
    doc = load_yaml(os.path.join(d, 'idea_pool.yaml')) or {}
    ideas = (doc.get('innovation') or {}).get('ideas') or doc.get('ideas') or []
    for it in ideas:
        if it.get('id') == idea_id:
            return it.get('source_insight_id')
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--ledger', default='.idea-ledger/consumed_ideas.yaml')
    ap.add_argument('--out', default='.idxx')
    ns = ap.parse_args()

    ledger = load_yaml(ns.ledger) or {}
    entries = ledger.get('consumed_ideas', []) or []
    implemented = [e for e in entries if e.get('implementations')]

    # 1) provenance walk: built-upon insight statements
    built_upon = []
    walk_ok = 0
    for e in implemented:
        sc = e.get('source_chain') or {}
        cix, idx = sc.get('cix'), sc.get('idx')
        proj = (e.get('implementations') or [{}])[0].get('project_name')
        stmt = layer = None
        if cix and idx:
            sid = idea_source_insight(cix, e.get('idea_id'))
            if sid:
                got = insight_statement(idx, sid)
                if got:
                    stmt, layer = got
                    walk_ok += 1
        if not stmt:  # fallback to consumed title/semantic_family theme
            stmt = e.get('title')
            layer = 'fallback'
        built_upon.append(OD([('project', proj), ('layer', layer), ('statement', stmt),
                              ('source_idx', idx), ('topics', topics(stmt)[:8])]))

    built_topics = Counter()
    for b in built_upon:
        built_topics.update(b['topics'])

    # 2) recurring topics across IDX rounds + layer history
    layer_history = OD()
    round_topic = Counter()
    rounds = sorted(glob.glob('.idx/rounds/*/insight_layered_traced.yaml'))
    for rp in rounds:
        rid = os.path.basename(os.path.dirname(rp))
        doc = load_yaml(rp) or {}
        ins = (doc.get('distillation') or {}).get('insights') or doc.get('insights') or []
        layer_history[rid] = dict(Counter(i.get('layer') for i in ins))
        seen = set()
        for i in ins:
            for t in set(topics(i.get('statement'))):
                if t not in seen:
                    round_topic[t] += 1
                    seen.add(t)
    recurring = [t for t, n in round_topic.most_common() if n >= 2]

    out_root = ns.out
    os.makedirs(out_root, exist_ok=True)
    smap = OD([
        ('insight_saturation_map', OD([
            ('built_at', datetime.now(timezone.utc).replace(microsecond=0).isoformat()),
            ('ledger', ns.ledger),
            ('implemented_count', len(implemented)),
            ('provenance_walk_resolved', walk_ok),
            ('built_upon_insights', built_upon),
            ('built_upon_topics', OD(sorted(built_topics.items(), key=lambda x: -x[1])[:25])),
            ('recurring_topics_across_rounds', recurring[:25]),
            ('layer_distribution_history', layer_history),
            ('guidance', OD([
                ('demote', 'Do NOT re-distill insight themes in built_upon_insights (already spawned built projects).'),
                ('promote', 'Prefer under-distilled / weak-signal / cross-trend insights and under-used layers.'),
                ('covered_not_forbidden', 'A built-upon topic with a genuinely different layer/tension/angle is allowed.'),
                ('evidence_floor', 'NEVER promote a non-evidence-traced pattern. Steer only WITHIN evidence-backed candidates (IDX evidence trace mandatory).'),
            ])),
        ])),
    ])
    path = os.path.join(out_root, 'insight_saturation_map.yaml')
    yaml.dump(smap, open(path, 'w', encoding='utf-8'), default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000)

    print('wrote', path)
    print('implemented:', len(implemented), '| provenance_walk_resolved:', walk_ok)
    print('built_upon insight themes:', len(built_upon))
    print('top built-upon topics:', [t for t, _ in built_topics.most_common(12)])
    print('recurring topics (>=2 IDX rounds):', recurring[:12])
    print('layer history rounds:', list(layer_history))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
