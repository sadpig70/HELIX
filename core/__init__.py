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
from .helix_diversity import (
    measure_diversity, lexical_sim, base_thresholds,
    DEFAULT_THRESHOLDS, LEXICAL_THRESHOLD_OVERRIDES,
)
from .helix_provenance import trace_winner, winner_to_corpus_entry
from .helix_loop import next_action, DEFAULT_LOOP_POLICY
from .helix_io import atomic_write_json, read_json
from .helix_schema import validate_against_schema, schema_features, schema_path
from .helix_loop_state import (
    should_stop, update_coverage, least_covered, rate_limit_ok,
    load_loop_state, checkpoint_loop_state, loop_status_report,
)

__all__ = [
    "normalize_name", "tokenize_name", "source_fingerprint", "generated_fingerprint",
    "is_consumed", "append_consumed", "load_ledger", "save_ledger",
    "reindex_ledger", "empty_ledger",
    "measure_diversity", "lexical_sim", "base_thresholds",
    "DEFAULT_THRESHOLDS", "LEXICAL_THRESHOLD_OVERRIDES",
    "trace_winner", "winner_to_corpus_entry",
    "next_action", "DEFAULT_LOOP_POLICY",
    "atomic_write_json", "read_json",
    "validate_against_schema", "schema_features", "schema_path",
    "should_stop", "update_coverage", "least_covered", "rate_limit_ok",
    "load_loop_state", "checkpoint_loop_state", "loop_status_report",
]
