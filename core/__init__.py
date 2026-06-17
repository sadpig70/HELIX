"""HELIX-Core — shared deterministic substrate (the double-helix backbone).

Single source of truth for the machinery that the two engines
(explore = IdeaFirst, exploit = recreate/ProjectGenome) independently rebuilt:
identity fingerprints, the reuse-prevention ledger, homogenization/diversity
measurement, provenance + corpus feedback, and the explore<->exploit loop driver.

Determinism boundary: everything here is pure, stdlib-only, and free of
clock/network/AI. Time is injected (`now` args), semantic similarity is injected
(`sim` callables). Embeddings and LLM judgments live in the engines, not here.
"""

from .helix_fingerprint import (
    normalize_name,
    tokenize_name,
    source_fingerprint,
    generated_fingerprint,
)
from .helix_ledger import (
    is_consumed, append_consumed, load_ledger, save_ledger, reindex_ledger, empty_ledger,
)
from .helix_diversity import measure_diversity, lexical_sim, DEFAULT_THRESHOLDS
from .helix_provenance import trace_winner, winner_to_corpus_entry
from .helix_loop import next_action, DEFAULT_LOOP_POLICY

__all__ = [
    "normalize_name", "tokenize_name", "source_fingerprint", "generated_fingerprint",
    "is_consumed", "append_consumed", "load_ledger", "save_ledger",
    "reindex_ledger", "empty_ledger",
    "measure_diversity", "lexical_sim", "DEFAULT_THRESHOLDS",
    "trace_winner", "winner_to_corpus_entry",
    "next_action", "DEFAULT_LOOP_POLICY",
]
