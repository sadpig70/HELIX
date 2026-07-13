#!/usr/bin/env python3
"""External ledger anchoring — the other half of tamper-evidence.

Keyed signing (core/helix_signing) stops a write-capable adversary WITHOUT
the signing key. It does not stop a key-holding insider who rewrites the whole
ledger and re-signs it. That is what external anchoring closes: periodically
the ledger's head + prefix digest is published OUTSIDE the ledger's own trust
domain (a git commit, a public timestamp service, a separate append-only log),
so a later rewrite of any anchored entry diverges from the externally-held
anchor and is detected — even by the insider who controls the ledger store.

Determinism boundary: the actual external publication (network, another
store) lives OUTSIDE this module. The core does only the deterministic part —
compute an anchor over the ledger, seal it, and later verify the ledger still
matches a given anchor. The ``external_ref`` (where the anchor was published)
is injected by the caller and recorded verbatim; the core does not fetch or
trust it, it only binds it into the sealed anchor so the operational record
says where the independent copy lives.

An anchor pins position ``seq``: the ledger must still contain, at that seq,
an entry whose seal equals ``head_sha256``, and the whole prefix (0..seq) must
reproduce ``prefix_digest``. Append-only growth after the anchor is fine
(the prefix is unchanged); rewriting or truncating any anchored entry is not.

Deterministic, stdlib-only: no clock, network, subprocess, randomness, or AI.
"""

import hashlib
import os
import sys

try:
    from .helix_actuator import read_actuation_ledger
    from .helix_holdout import canonical_json_bytes
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.helix_actuator import read_actuation_ledger
    from core.helix_holdout import canonical_json_bytes

SCHEMA_ID = "helix-ledger-anchor/1.0"


def _prefix_digest(entries: list, upto_seq: int) -> str:
    """Deterministic digest over the entry seals of the prefix 0..upto_seq."""
    seals = [e.get("entry_sha256") for e in entries[:upto_seq + 1]]
    return hashlib.sha256(canonical_json_bytes(seals)).hexdigest()


def _seal(doc: dict) -> dict:
    sealed = dict(doc)
    sealed.pop("anchor_sha256", None)
    sealed["anchor_sha256"] = hashlib.sha256(
        canonical_json_bytes(sealed)).hexdigest()
    return sealed


def verify_anchor_seal(anchor: dict) -> bool:
    expected = anchor.get("anchor_sha256")
    body = {k: v for k, v in anchor.items() if k != "anchor_sha256"}
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_json_bytes(body)).hexdigest()


def compute_anchor(root: str, ledger_rel: str) -> dict:
    """Snapshot the current ledger head + prefix digest (unsealed)."""
    entries = read_actuation_ledger(root, ledger_rel)
    if not entries:
        return None
    head = entries[-1]
    return {"seq": head["seq"], "head_sha256": head["entry_sha256"],
            "prefix_digest": _prefix_digest(entries, head["seq"])}


def seal_anchor(anchor: dict, external_ref: str, anchored_by: str) -> dict:
    """Seal an anchor with the external reference where it will be published.

    ``external_ref`` names the independent trust domain holding the copy
    (e.g. ``git-commit:<sha>``, ``timestamp:<id>``, ``public-log:<url>``); the
    core records it verbatim and does not fetch or trust it. Publishing there
    is the caller's job — that is what makes the anchor beat an insider.
    """
    if anchor is None:
        raise ValueError("cannot anchor an empty ledger")
    if not (external_ref or "").strip():
        raise ValueError("external_ref must name where the anchor is published")
    if not (anchored_by or "").strip():
        raise ValueError("anchored_by must be non-empty")
    return _seal({
        "schema": SCHEMA_ID,
        "seq": anchor["seq"],
        "head_sha256": anchor["head_sha256"],
        "prefix_digest": anchor["prefix_digest"],
        "external_ref": external_ref,
        "anchored_by": anchored_by,
    })


def verify_against_anchor(root: str, ledger_rel: str, anchor: dict) -> list:
    """Check the ledger still matches a sealed anchor. Empty == consistent.

    Catches an insider rewrite the keyed signature cannot: even a fully
    re-signed ledger whose anchored prefix changed diverges from the external
    anchor here.
    """
    problems = []
    if not verify_anchor_seal(anchor):
        problems.append("anchor seal is broken")
        return problems
    entries = read_actuation_ledger(root, ledger_rel)
    seq = anchor["seq"]
    if len(entries) <= seq:
        problems.append(f"ledger has {len(entries)} entries but the anchor pins "
                        f"seq {seq} — anchored entries were removed/truncated")
        return problems
    if entries[seq].get("entry_sha256") != anchor["head_sha256"]:
        problems.append(f"entry at anchored seq {seq} was rewritten "
                        "(seal diverged from the external anchor)")
    if _prefix_digest(entries, seq) != anchor["prefix_digest"]:
        problems.append(f"the anchored prefix (seq 0..{seq}) was rewritten")
    return sorted(problems)


if __name__ == "__main__":
    print("library module — compute_anchor / seal_anchor / "
          "verify_against_anchor")
    sys.exit(2)
