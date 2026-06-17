#!/usr/bin/env python3
"""HELIX unified homogenization / diversity measurement (stdlib only).

The "DNA repair enzyme" of the helix: it measures whether repeated rounds are
collapsing onto the same outputs, so the loop can fire a refresh BEFORE the
lineage degrades. This unifies the two systems' separately-built guards:

  * IdeaFirst (AOX_POLICY.homogenization): keyword_coverage, max_pair_count,
        avg_embedding_sim, winner_embedding_similarity; trigger when >=2 of 4.
  * recreate (idea-layer DiversityGuard): unique_ratio (cos>0.8 duplicate pairs).

Determinism boundary: keyword/domain-pair signals are FULLY deterministic
(stdlib counting). Similarity signals use a `sim(a, b) -> float` callable; when
none is injected, a deterministic lexical default (`lexical_sim`, Jaccard over
tokens) is used so a complete report is always produced. Inject a semantic sim
(embeddings, run in the engines) for embedding-grade signal. The report's
`sim_kind` field records which was used ("lexical" | "semantic").
"""

from collections import Counter
from itertools import combinations

from .helix_fingerprint import tokenize_name

# Unified thresholds: IdeaFirst 4 + recreate dup_cos + min_breaches.
DEFAULT_THRESHOLDS = {
    "keyword_coverage": 0.80,            # IdeaFirst
    "max_pair_count": 3,                 # IdeaFirst (domain-pair repeat over window)
    "avg_embedding_sim": 0.65,           # IdeaFirst
    "winner_embedding_similarity": 0.50, # IdeaFirst (round N vs N-1 winners)
    "dup_cos": 0.80,                     # recreate (duplicate pair threshold)
    "unique_ratio_floor": 0.50,          # recreate (island re-divergence trigger)
    "min_breaches": 2,                   # trigger when >= this many of the 4 breached
}


def _item_text(item: dict) -> str:
    parts = [item.get("title", ""),
             item.get("system_description", ""),
             item.get("problem", ""),
             item.get("mechanism", "")]
    return " ".join(p for p in parts if p)


def keyword_coverage(pool, k=10) -> float:
    """Fraction of items dominated by the top-k most common keywords (DF-based).

    High coverage = the same few words run through most outputs = homogeneous.
    Fully deterministic (tokenize + document frequency, string tie-break).
    """
    n = len(pool)
    if n == 0:
        return 0.0
    token_sets = [set(tokenize_name(_item_text(it))) for it in pool]
    df = Counter()
    for ts in token_sets:
        df.update(ts)
    if not df:
        return 0.0
    # top-k by (frequency desc, token asc) -> deterministic
    top = [tok for tok, _ in sorted(df.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]
    top_set = set(top)
    covered = sum(1 for ts in token_sets if ts & top_set)
    return covered / n


def max_domain_pair_repeat(pool) -> int:
    """Largest number of items sharing the same unordered domain pair (deterministic)."""
    counter = Counter()
    for it in pool:
        domains = sorted({d for d in it.get("domains", []) if d})
        for pair in combinations(domains, 2):
            counter[pair] += 1
    return max(counter.values()) if counter else 0


def avg_pairwise(items, sim):
    """Mean pairwise similarity using injected sim(a, b)->float. None if not computable."""
    n = len(items)
    if n < 2 or sim is None:
        return None
    total = 0.0
    count = 0
    for a, b in combinations(items, 2):
        total += float(sim(a, b))
        count += 1
    return total / count if count else None


def unique_ratio(pool, sim, dup_cos):
    """1 - (duplicate items / n). A later item in a >dup_cos pair is a duplicate.

    Mirrors recreate's dup_pairs/{j} unique-ratio. None if sim not provided.
    """
    n = len(pool)
    if n == 0:
        return None
    if n == 1:
        return 1.0
    if sim is None:
        return None
    dup_idx = set()
    for i, j in combinations(range(n), 2):
        if float(sim(pool[i], pool[j])) > dup_cos:
            dup_idx.add(j)
    return (n - len(dup_idx)) / n


def lexical_sim(a, b) -> float:
    """Deterministic default similarity: Jaccard over title+description tokens, [0,1].

    A shallow but real (lexical) signal so diversity works with zero external
    dependencies. Inject a semantic `sim(a, b)` for embedding-grade comparison.
    """
    ta = set(tokenize_name(_item_text(a)))
    tb = set(tokenize_name(_item_text(b)))
    if not ta or not tb:
        return 0.0
    union = len(ta | tb)
    return len(ta & tb) / union if union else 0.0


def measure_diversity(pool, recent_winners=None, sim=None, thresholds=None) -> dict:
    """Unified diversity report. Aggregation deterministic; similarity pluggable.

    `sim(a, b) -> float` is injectable; when None, the deterministic `lexical_sim`
    default is used, so a complete report is ALWAYS produced (no omitted metrics).
    Returns {triggered, breaches, sim_kind, metrics{...}, signals{...}, thresholds}.
    `sim_kind` is "semantic" when a sim was injected, else "lexical".
    """
    P = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        P.update(thresholds)
    recent_winners = recent_winners or []
    sim_kind = "semantic" if sim is not None else "lexical"
    if sim is None:
        sim = lexical_sim

    kc = keyword_coverage(pool)
    mpc = max_domain_pair_repeat(pool)
    avg_sim = avg_pairwise(pool, sim)
    win_sim = avg_pairwise(recent_winners, sim)
    uniq = unique_ratio(pool, sim, P["dup_cos"])

    checks = [
        ("keyword_coverage", kc, kc >= P["keyword_coverage"]),
        ("max_pair_count", mpc, mpc >= P["max_pair_count"]),
        ("avg_embedding_sim", avg_sim, avg_sim is not None and avg_sim >= P["avg_embedding_sim"]),
        ("winner_embedding_similarity", win_sim, win_sim is not None and win_sim >= P["winner_embedding_similarity"]),
    ]
    breaches = sum(1 for _, _, b in checks if b)
    triggered = breaches >= P["min_breaches"]

    return {
        "triggered": triggered,
        "breaches": breaches,
        "sim_kind": sim_kind,
        "metrics": {name: val for name, val, _ in checks},
        "signals": {
            "unique_ratio": uniq,
            "unique_ratio_below_floor": (uniq is not None and uniq < P["unique_ratio_floor"]),
            "breached": [name for name, _, b in checks if b],
        },
        "thresholds": P,
    }
