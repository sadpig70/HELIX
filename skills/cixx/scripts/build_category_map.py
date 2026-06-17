"""CIXX Category Map builder (deterministic).

Reads the consumed-idea ledger and emits a saturation map of (domain x mechanism)
cells, mechanism share, saturated cells, overused mechanisms, and white-space — the
steering input for CIXX-guided CIX generation.

Usage:
    python build_category_map.py [--ledger PATH] [--out DIR]
Defaults: --ledger .idea-ledger/consumed_ideas.yaml  --out .cixx
"""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter, OrderedDict
from datetime import datetime, timezone

import yaml


class OD(OrderedDict):
    pass


yaml.add_representer(OD, lambda d, x: d.represent_mapping('tag:yaml.org,2002:map', x.items()))

# Policy (mirror SKILL.md params)
CELL_SATURATED_COUNT = 3
MECHANISM_OVERUSE_RATIO = 0.30

# Mechanism clusters — keyword -> canonical mechanism. Order matters (specific first).
MECH_KEYWORDS = [
    ('compatibility-mesh', ['compatibility mesh', 'compatibility-mesh']),
    ('signal-exchange', ['byproduct signal exchange', 'signal exchange', 'signal-exchange']),
    ('operating-exchange', ['cross-domain operating exchange', 'operating exchange', 'operating-exchange']),
    ('failure-market', ['failure', 'failfutures', 'obsolescence-failure', 'key-person-failure']),
    ('clearing-market', ['clearing', 'two-sided clearing', 'clearinghouse']),
    ('roaming', ['roaming', 'compute follows power', 'follows-power']),
    ('battery-storage', ['battery', 'seasonal removal', 'storage']),
    ('endowment', ['endowment', 'capability endowment']),
    ('generation-cert', ['birth-cert', 'generator birth', 'one-time generator']),
    ('magnet-cartel', ['magnet cartel', 'demand-side magnet', 'cartel']),
    ('market-generic', ['market', 'exchange']),
]
KNOWN_DOMAINS = ['ai operations', 'agentops', 'quantum security', 'robotics', 'robot',
                 'energy infrastructure', 'inference grid', 'programmable finance', 'settlement',
                 'treasury', 'sovereign', 'sovereignty', 'climate', 'release', 'certifiable robot']


def mechanism_of(title: str, semantic_family: str) -> str:
    hay = '{} {}'.format(title or '', semantic_family or '').lower()
    for canon, kws in MECH_KEYWORDS:
        if any(k in hay for k in kws):
            return canon
    return 'other'


def domain_of(title: str, semantic_family: str) -> str:
    t = (title or '').strip()
    # cut at first mechanism marker or punctuation
    cut = re.split(r'(Autonomous|Compatibility|Byproduct|Cross-Domain|Failure|Market|Exchange|Mesh|Ledger|Battery|Endowment|:|\(|—|-)', t)
    dom = cut[0].strip() if cut else t
    if not dom or len(dom) < 3:
        # fall back to semantic_family prefix
        sf = (semantic_family or '').split('-')
        dom = ' '.join(sf[:2]) if sf else 'unknown'
    return dom.strip().lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--ledger', default='.idea-ledger/consumed_ideas.yaml')
    ap.add_argument('--out', default='.cixx')
    ns = ap.parse_args()

    data = yaml.safe_load(open(ns.ledger, encoding='utf-8')) or {}
    entries = data.get('consumed_ideas', []) or []
    implemented = [e for e in entries if e.get('implementations')]
    derivative = [e for e in entries if not e.get('implementations')]

    cells = Counter()
    cell_examples = {}
    for e in entries:
        dom = domain_of(e.get('title'), e.get('semantic_family'))
        mech = mechanism_of(e.get('title'), e.get('semantic_family'))
        key = '{} | {}'.format(dom, mech)
        cells[key] += 1
        cell_examples.setdefault(key, e.get('title'))

    total = sum(cells.values()) or 1
    mech_count = Counter()
    for key, n in cells.items():
        mech = key.split(' | ')[1]
        mech_count[mech] += n
    mech_share = {m: round(c / total, 3) for m, c in mech_count.most_common()}
    overused = [m for m, s in mech_share.items() if s >= MECHANISM_OVERUSE_RATIO]
    saturated = [k for k, n in cells.items() if n >= CELL_SATURATED_COUNT]
    underused = [m for m, s in mech_share.items() if s < MECHANISM_OVERUSE_RATIO / 2]

    published = []
    for e in implemented:
        for im in e.get('implementations', []):
            if im.get('project_name'):
                published.append(im['project_name'])

    out_root = ns.out
    os.makedirs(out_root, exist_ok=True)
    cmap = OD([
        ('category_map', OD([
            ('built_at', datetime.now(timezone.utc).replace(microsecond=0).isoformat()),
            ('ledger', ns.ledger),
            ('ledger_entries', len(entries)),
            ('implemented', len(implemented)),
            ('derivative_excluded', len(derivative)),
            ('policy', OD([('cell_saturated_count', CELL_SATURATED_COUNT),
                           ('mechanism_overuse_ratio', MECHANISM_OVERUSE_RATIO)])),
            ('mechanism_share', OD(sorted(mech_share.items(), key=lambda x: -x[1]))),
            ('overused_mechanisms', overused),
            ('underused_mechanisms', underused),
            ('saturated_cells', [OD([('cell', k), ('count', cells[k]), ('example', cell_examples[k])]) for k in saturated]),
            ('all_cells', OD(sorted(cells.items(), key=lambda x: -x[1]))),
            ('published_projects', sorted(set(published))),
            ('white_space', OD([
                ('underused_mechanisms', underused),
                ('guidance', 'Avoid OVERUSED mechanism on existing domains. Prefer underused/novel mechanisms; covered domain + different mechanism is allowed.'),
            ])),
        ])),
    ])
    path = os.path.join(out_root, 'category_map.yaml')
    yaml.dump(cmap, open(path, 'w', encoding='utf-8'), default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000)

    print('wrote', path)
    print('ledger entries:', len(entries), '(implemented', len(implemented), '+ derivative', len(derivative), ')')
    print('mechanism_share:', mech_share)
    print('OVERUSED mechanisms:', overused)
    print('saturated cells:', len(saturated))
    for k in saturated:
        print('  -', k, '({})'.format(cells[k]))
    print('underused mechanisms (white-space targets):', underused)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
