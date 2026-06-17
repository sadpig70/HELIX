#!/usr/bin/env python3
"""Deterministic identity primitives for HELIX (stdlib only).

Promoted from ProjectGenome `scripts/fingerprint.py` to be the single source of
truth shared by both engines. Coding these as functions (rather than leaving them
to AI judgment each run) keeps ledger/avoidance behavior stable across runtimes.

usage as a library:
    from core.helix_fingerprint import normalize_name, source_fingerprint
usage as a CLI:
    python core/helix_fingerprint.py source ADPR ReleaseMesh PnR
    python core/helix_fingerprint.py name "MyCandidateName"
"""

import re
import sys


def normalize_name(name) -> str:
    """Lowercase, strip everything non-alphanumeric. For name/title collision checks.

    Unifies ProjectGenome `normalize_name` with IdeaFirst `normalized_title`.
    """
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def tokenize_name(name) -> list:
    """Split a CamelCase / delimited name into lowercase word tokens.

    e.g. 'DwellProvenanceGate' -> ['dwell', 'provenance', 'gate'].
    Deterministic basis for vocab/keyword overlap — no AI needed.
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", (name or ""))
    return [t for t in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if t]


def source_fingerprint(parts) -> str:
    """Canonical key for a set of corpus source projects (order-independent, dedup).

    exploit (recreate) namespace: which corpus parts a candidate reused.
    """
    return "+".join(sorted(set(p for p in (parts or []) if p)))


def generated_fingerprint(parents) -> str:
    """Canonical key for a set of parent *generated* projects (integration namespace)."""
    return "+".join(sorted(set(p for p in (parents or []) if p)))


def _main(argv) -> int:
    if len(argv) >= 3 and argv[1] == "source":
        print(source_fingerprint(argv[2:]))
        return 0
    if len(argv) >= 3 and argv[1] == "generated":
        print(generated_fingerprint(argv[2:]))
        return 0
    if len(argv) >= 3 and argv[1] == "name":
        print(normalize_name(argv[2]))
        return 0
    if len(argv) >= 3 and argv[1] == "tokens":
        print(" ".join(tokenize_name(argv[2])))
        return 0
    sys.stderr.write(
        "usage:\n"
        "  python core/helix_fingerprint.py source <SrcA> <SrcB> ...\n"
        "  python core/helix_fingerprint.py generated <ParentA> <ParentB> ...\n"
        "  python core/helix_fingerprint.py name \"<Name>\"\n"
        "  python core/helix_fingerprint.py tokens \"<Name>\"\n")
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
