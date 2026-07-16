#!/usr/bin/env python3
"""Deterministic dual-corpus supply plane for HELIX.

The meta layer may propose genes and machine hypotheses.  This module only
validates declared evidence, stores immutable manifests, and issues replayable
Generative/Evidence admission receipts.  It is stdlib-only and performs no
network, clock, random, or AI operations; ``now`` is injected by the caller.
"""

import hashlib
import json
import os
import re

try:
    from .helix_io import atomic_write_json, read_json
    from .helix_schema import schema_path, validate_against_schema
except ImportError:  # direct execution/import from repo root
    from core.helix_io import atomic_write_json, read_json
    from core.helix_schema import schema_path, validate_against_schema


MANIFEST_SCHEMA = "helix-corpus-manifest/1.0"
ADMISSION_SCHEMA = "helix-corpus-admission-receipt/1.0"
REVIEW_SCHEMA = "helix-corpus-review-receipt/1.0"
SAFE_ID = re.compile(r"^HC-[A-Z0-9][A-Z0-9-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LEGACY_ROW = re.compile(r"^- \*\*(.+?)\*\* \((.*?)\):\s*(.*)$")


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def digest(value) -> str:
    if not isinstance(value, str):
        value = canonical_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def manifest_digest(manifest: dict) -> str:
    return digest(manifest)


def _nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha_problem(value, field) -> list:
    return [] if isinstance(value, str) and SHA256.fullmatch(value) else [f"{field}: invalid sha256"]


def validate_manifest(repo_root: str, manifest: dict) -> list:
    """Structural validation for an intake candidate (not an admission verdict)."""
    problems = validate_against_schema(
        manifest, schema_path(repo_root, "corpus-manifest"))
    if not isinstance(manifest, dict):
        return sorted(set(problems))
    corpus_id = manifest.get("corpus_id")
    if not isinstance(corpus_id, str) or not SAFE_ID.fullmatch(corpus_id):
        problems.append("corpus_id: must match HC-[A-Z0-9-]+")
    for field in ("name", "summary"):
        if not _nonempty(manifest.get(field)):
            problems.append(f"{field}: empty")
    origin = manifest.get("origin", {})
    for field in ("locator", "revision", "license"):
        if not _nonempty(origin.get(field)):
            problems.append(f"origin.{field}: empty")
    for field in ("source_evidence", "license_evidence"):
        if not _nonempty(origin.get(field)):
            problems.append(f"origin.{field}: empty")
    problems += _sha_problem(origin.get("source_sha256"), "origin.source_sha256")
    problems += _sha_problem(origin.get("license_evidence_sha256"),
                             "origin.license_evidence_sha256")
    character = manifest.get("character", {})
    for field in ("domain", "primary_verb", "input_shape", "output_shape"):
        if not _nonempty(character.get(field)):
            problems.append(f"character.{field}: empty")
    machine = manifest.get("machine", {})
    if not _nonempty(machine.get("label")):
        problems.append("machine.label: empty")
    verification = manifest.get("verification", {})
    behavior = verification.get("behavior_sha256")
    if behavior and not SHA256.fullmatch(str(behavior)):
        problems.append("verification.behavior_sha256: invalid sha256")
    if int(manifest.get("revision", 0) or 0) > 1:
        problems += _sha_problem(manifest.get("supersedes_manifest_sha256"),
                                 "supersedes_manifest_sha256")
    return sorted(set(problems))


def validate_review(repo_root: str, review: dict) -> list:
    problems = validate_against_schema(
        review, schema_path(repo_root, "corpus-review-receipt"))
    if not isinstance(review, dict):
        return sorted(set(problems))
    if not SAFE_ID.fullmatch(str(review.get("corpus_id", ""))):
        problems.append("corpus_id: invalid")
    problems += _sha_problem(review.get("manifest_sha256"), "manifest_sha256")
    reviewer = review.get("reviewer", {})
    if not _nonempty(reviewer.get("id")):
        problems.append("reviewer.id: empty")
    if not _nonempty(review.get("reviewed_at")):
        problems.append("reviewed_at: empty")
    return sorted(set(problems))


def fingerprints(manifest: dict) -> dict:
    """Five stable identity surfaces; declared behavior hash is never invented."""
    character = manifest.get("character", {})
    machine = manifest.get("machine", {})
    verification = manifest.get("verification", {})
    return {
        "source": manifest.get("origin", {}).get("source_sha256", ""),
        "interface": digest({
            "input_shape": character.get("input_shape", ""),
            "output_shape": character.get("output_shape", ""),
        }),
        "behavior": verification.get("behavior_sha256", ""),
        "machine": digest({
            "label": machine.get("label", ""),
            "evidence": sorted(machine.get("evidence", [])),
        }),
        "gene": digest(sorted(set(manifest.get("genes", [])))),
        "dependency": digest(sorted(set(manifest.get("dependencies", [])))),
    }


def corpus_paths(corpus_root: str) -> dict:
    root = os.path.abspath(corpus_root)
    return {
        "root": root,
        "items": os.path.join(root, "items"),
        "ledger": os.path.join(root, "evidence", "admission-ledger.jsonl"),
    }


def item_path(corpus_root: str, corpus_id: str) -> str:
    if not isinstance(corpus_id, str) or not SAFE_ID.fullmatch(corpus_id):
        raise ValueError("unsafe corpus_id")
    paths = corpus_paths(corpus_root)
    target = os.path.abspath(os.path.join(paths["items"], corpus_id, "manifest.json"))
    expected_parent = os.path.abspath(paths["items"]) + os.sep
    if not target.startswith(expected_parent):
        raise ValueError("corpus item path escapes corpus root")
    return target


def revision_path(corpus_root: str, corpus_id: str, revision: int) -> str:
    if not isinstance(revision, int) or revision < 1:
        raise ValueError("revision must be a positive integer")
    current = item_path(corpus_root, corpus_id)
    return os.path.join(os.path.dirname(current), "revisions", f"{revision}.json")


def intake_manifest(repo_root: str, corpus_root: str, manifest: dict) -> dict:
    problems = validate_manifest(repo_root, manifest)
    if problems:
        return {"status": "INVALID", "problems": problems, "created": False}
    path = item_path(corpus_root, manifest["corpus_id"])
    existing = read_json(path)
    if existing is not None:
        if manifest_digest(existing) == manifest_digest(manifest):
            return {"status": "EXISTS", "created": False, "path": path,
                    "manifest_sha256": manifest_digest(manifest)}
        old_revision = existing.get("revision")
        new_revision = manifest.get("revision")
        if not isinstance(old_revision, int) or new_revision <= old_revision:
            raise ValueError("corpus_id conflict: changed manifest requires a higher revision")
    snapshot = revision_path(corpus_root, manifest["corpus_id"], manifest["revision"])
    prior_snapshot = read_json(snapshot)
    if prior_snapshot is not None and manifest_digest(prior_snapshot) != manifest_digest(manifest):
        raise ValueError("manifest revision conflict: immutable snapshot differs")
    if prior_snapshot is None:
        atomic_write_json(snapshot, manifest)
    atomic_write_json(path, manifest)
    return {"status": "INTAKEN", "created": True, "path": path,
            "snapshot": snapshot, "manifest_sha256": manifest_digest(manifest)}


def load_item(corpus_root: str, corpus_id: str) -> dict:
    path = item_path(corpus_root, corpus_id)
    manifest = read_json(path)
    if manifest is None:
        raise FileNotFoundError(f"corpus item not found: {corpus_id}")
    return manifest


def list_items(corpus_root: str) -> list:
    items_dir = corpus_paths(corpus_root)["items"]
    if not os.path.isdir(items_dir):
        return []
    rows = []
    for name in sorted(os.listdir(items_dir)):
        if not SAFE_ID.fullmatch(name):
            continue
        manifest = read_json(os.path.join(items_dir, name, "manifest.json"))
        if isinstance(manifest, dict):
            rows.append(manifest)
    return rows


def duplicate_source_ids(corpus_root: str, manifest: dict) -> list:
    source = manifest.get("origin", {}).get("source_sha256")
    current = manifest.get("corpus_id")
    return sorted(
        item.get("corpus_id") for item in list_items(corpus_root)
        if item.get("corpus_id") != current
        and item.get("origin", {}).get("source_sha256") == source
    )


def _sha256_file(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _evidence_problem(evidence_root: str, rel: str, expected: str, label: str) -> list:
    if not evidence_root:
        return ["evidence_root_required"]
    if not _nonempty(rel) or os.path.isabs(rel):
        return [f"{label}_evidence_path_invalid"]
    root = os.path.realpath(evidence_root)
    path = os.path.realpath(os.path.join(root, rel))
    if not path.startswith(root + os.sep):
        return [f"{label}_evidence_path_escape"]
    if not os.path.isfile(path):
        return [f"{label}_evidence_missing"]
    if _sha256_file(path) != expected:
        return [f"{label}_evidence_hash_mismatch"]
    return []


def hard_gate(manifest: dict, evidence_root: str = None) -> list:
    reasons = []
    origin = manifest.get("origin", {})
    safety = manifest.get("safety", {})
    if not origin.get("license_verified"):
        reasons.append("license_unverified")
    if str(origin.get("license", "")).upper() in ("", "UNKNOWN", "NOASSERTION"):
        reasons.append("license_not_identified")
    if str(origin.get("revision", "")).lower() in ("", "unversioned", "latest", "head"):
        reasons.append("source_revision_not_pinned")
    if not manifest.get("provenance"):
        reasons.append("provenance_missing")
    reasons += _evidence_problem(
        evidence_root, origin.get("source_evidence"), origin.get("source_sha256"), "source")
    reasons += _evidence_problem(
        evidence_root, origin.get("license_evidence"),
        origin.get("license_evidence_sha256"), "license")
    for key in ("secret_scan_passed", "pii_scan_passed", "malware_scan_passed",
                "execution_isolated"):
        if safety.get(key) is not True:
            reasons.append(key.replace("_passed", "") + "_required")
    return sorted(set(reasons))


def generative_gate(manifest: dict, duplicate_ids=None, evidence_root=None) -> list:
    reasons = hard_gate(manifest, evidence_root)
    if not manifest.get("genes"):
        reasons.append("no_reusable_gene")
    if not _nonempty(manifest.get("machine", {}).get("label")):
        reasons.append("machine_hypothesis_missing")
    if duplicate_ids:
        reasons.append("duplicate_source:" + ",".join(sorted(duplicate_ids)))
    return sorted(set(reasons))


def read_ledger(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = []
            for number, line in enumerate(f, 1):
                if not line.endswith("\n"):
                    raise ValueError(f"ledger line {number}: incomplete tail")
                if not line.strip():
                    raise ValueError(f"ledger line {number}: blank event")
                try:
                    rows.append(json.loads(line))
                except ValueError as error:
                    raise ValueError(f"ledger line {number}: invalid JSON: {error}")
            return rows
    except FileNotFoundError:
        return []


def verify_ledger(repo_root: str, ledger_path: str) -> list:
    problems = []
    try:
        rows = read_ledger(ledger_path)
    except ValueError as error:
        return [str(error)]
    previous = None
    for index, row in enumerate(rows):
        problems += [f"event[{index}]: {p}" for p in validate_against_schema(
            row, schema_path(repo_root, "corpus-admission-receipt"))]
        if row.get("previous_event_sha256") != previous:
            problems.append(f"event[{index}]: previous_event_sha256 mismatch")
        body = dict(row)
        claimed = body.pop("event_sha256", None)
        actual = digest(body)
        if claimed != actual:
            problems.append(f"event[{index}]: event_sha256 mismatch")
        previous = claimed
    return sorted(set(problems))


def materialize_state(repo_root: str, corpus_root: str) -> dict:
    ledger_path = corpus_paths(corpus_root)["ledger"]
    problems = verify_ledger(repo_root, ledger_path)
    rows = [] if problems else read_ledger(ledger_path)
    state = {}
    for row in rows:
        state.setdefault(row["corpus_id"], {})[row["tier"]] = row
    return {"events": rows, "state": state, "ledger_problems": problems}


def _review_digest(review) -> str:
    return digest(review) if review is not None else None


def decide_admission(repo_root: str, corpus_root: str, manifest: dict, tier: str,
                     review=None, evidence_root: str = None) -> dict:
    if tier not in ("generative", "evidence"):
        raise ValueError("tier must be generative or evidence")
    structure = validate_manifest(repo_root, manifest)
    reasons = list(structure)
    if not reasons:
        if tier == "generative":
            reasons += generative_gate(
                manifest, duplicate_source_ids(corpus_root, manifest), evidence_root)
        else:
            reasons += hard_gate(manifest, evidence_root)
            current = materialize_state(repo_root, corpus_root)
            if current["ledger_problems"]:
                reasons.append("admission_ledger_invalid")
            prior = current["state"].get(manifest["corpus_id"], {}).get("generative")
            if not prior or prior.get("decision") != "ADMITTED":
                reasons.append("prior_generative_admission_required")
            elif manifest.get("supersedes_manifest_sha256") != prior.get("manifest_sha256"):
                reasons.append("prior_manifest_binding_mismatch")
            verification = manifest.get("verification", {})
            for key in ("reproducible", "tests_passed", "deterministic"):
                if verification.get(key) is not True:
                    reasons.append(key + "_required")
            if not _nonempty(verification.get("reproduction_command")):
                reasons.append("reproduction_command_required")
            if not SHA256.fullmatch(str(verification.get("behavior_sha256", ""))):
                reasons.append("behavior_fingerprint_required")
            if not verification.get("supporting_files"):
                reasons.append("supporting_files_required")
            if not verification.get("supporting_symbols"):
                reasons.append("supporting_symbols_required")
            machine = manifest.get("machine", {})
            if machine.get("status") != "substantiated":
                reasons.append("substantiated_machine_required")
            if not machine.get("evidence"):
                reasons.append("machine_evidence_required")
            if review is None:
                reasons.append("human_review_required")
            else:
                reasons += validate_review(repo_root, review)
                if review.get("corpus_id") != manifest.get("corpus_id"):
                    reasons.append("review_corpus_id_mismatch")
                if review.get("manifest_sha256") != manifest_digest(manifest):
                    reasons.append("review_manifest_hash_mismatch")
                if review.get("verdict") != "approved":
                    reasons.append("human_review_not_approved")
    reasons = sorted(set(reasons))
    return {
        "tier": tier,
        "decision": "ADMITTED" if not reasons else "QUARANTINED",
        "reasons": reasons,
        "manifest_sha256": manifest_digest(manifest),
        "fingerprints": fingerprints(manifest),
        "review_sha256": _review_digest(review),
    }


def _event_identity(corpus_id: str, decision: dict) -> str:
    return digest({
        "corpus_id": corpus_id,
        "tier": decision["tier"],
        "decision": decision["decision"],
        "reasons": decision["reasons"],
        "manifest_sha256": decision["manifest_sha256"],
        "review_sha256": decision["review_sha256"],
    })


def append_decision(repo_root: str, corpus_root: str, corpus_id: str,
                    decision: dict, now: str) -> dict:
    if not _nonempty(now):
        raise ValueError("now must be injected")
    ledger_path = corpus_paths(corpus_root)["ledger"]
    problems = verify_ledger(repo_root, ledger_path)
    if problems:
        raise ValueError("admission ledger invalid: " + "; ".join(problems))
    rows = read_ledger(ledger_path)
    identity = _event_identity(corpus_id, decision)
    event_id = "CSE-" + identity[:20].upper()
    for row in rows:
        if row.get("event_id") == event_id:
            return {"added": False, "event": row}
        if (row.get("corpus_id") == corpus_id
                and row.get("tier") == decision["tier"]
                and row.get("decision") == "ADMITTED"
                and row.get("manifest_sha256") != decision["manifest_sha256"]):
            raise ValueError("admitted tier is bound to a different manifest revision")
    event = {
        "schema": ADMISSION_SCHEMA,
        "event_id": event_id,
        "corpus_id": corpus_id,
        "tier": decision["tier"],
        "decision": decision["decision"],
        "reasons": decision["reasons"],
        "manifest_sha256": decision["manifest_sha256"],
        "fingerprints": decision["fingerprints"],
        "review_sha256": decision["review_sha256"],
        "previous_event_sha256": rows[-1]["event_sha256"] if rows else None,
        "recorded_at": now,
    }
    event["event_sha256"] = digest(event)
    problems = validate_against_schema(
        event, schema_path(repo_root, "corpus-admission-receipt"))
    if problems:
        raise ValueError("invalid admission event: " + "; ".join(problems))
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(canonical_json(event) + "\n")
        f.flush()
        os.fsync(f.fileno())
    replay_problems = verify_ledger(repo_root, ledger_path)
    if replay_problems:
        raise ValueError("appended admission event failed replay: " +
                         "; ".join(replay_problems))
    return {"added": True, "event": event}


def admit_item(repo_root: str, corpus_root: str, corpus_id: str, tier: str,
               now: str, review=None, evidence_root: str = None) -> dict:
    manifest = load_item(corpus_root, corpus_id)
    decision = decide_admission(
        repo_root, corpus_root, manifest, tier, review, evidence_root)
    appended = append_decision(repo_root, corpus_root, corpus_id, decision, now)
    return {"decision": decision, **appended}


def corpus_status(repo_root: str, corpus_root: str) -> dict:
    materialized = materialize_state(repo_root, corpus_root)
    items = []
    for manifest in list_items(corpus_root):
        corpus_id = manifest["corpus_id"]
        tiers = materialized["state"].get(corpus_id, {})
        items.append({
            "corpus_id": corpus_id,
            "name": manifest.get("name"),
            "manifest_sha256": manifest_digest(manifest),
            "generative": tiers.get("generative", {}).get("decision", "NOT_REVIEWED"),
            "evidence": tiers.get("evidence", {}).get("decision", "NOT_REVIEWED"),
        })
    return {
        "schema": "helix-corpus-status/1.0",
        "items": items,
        "event_count": len(materialized["events"]),
        "ledger_valid": not materialized["ledger_problems"],
        "ledger_problems": materialized["ledger_problems"],
    }


def corpus_health(repo_root: str, corpus_root: str) -> dict:
    status = corpus_status(repo_root, corpus_root)
    counts = {
        "items": len(status["items"]),
        "generative_admitted": 0,
        "evidence_admitted": 0,
        "quarantined": 0,
    }
    for item in status["items"]:
        counts["generative_admitted"] += item["generative"] == "ADMITTED"
        counts["evidence_admitted"] += item["evidence"] == "ADMITTED"
        counts["quarantined"] += (
            item["generative"] == "QUARANTINED"
            or item["evidence"] == "QUARANTINED")
    return {
        "schema": "helix-corpus-health/1.0",
        "counts": counts,
        "event_count": status["event_count"],
        "ledger_valid": status["ledger_valid"],
        "ledger_problems": status["ledger_problems"],
    }


def corpus_quarantine_report(repo_root: str, corpus_root: str) -> dict:
    materialized = materialize_state(repo_root, corpus_root)
    events = []
    reason_counts = {}
    for row in materialized["events"]:
        if row.get("decision") != "QUARANTINED":
            continue
        event = {
            "event_id": row.get("event_id"),
            "corpus_id": row.get("corpus_id"),
            "tier": row.get("tier"),
            "manifest_sha256": row.get("manifest_sha256"),
            "recorded_at": row.get("recorded_at"),
            "reasons": row.get("reasons", []),
        }
        events.append(event)
        for reason in event["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    status = corpus_status(repo_root, corpus_root)
    items = [
        item for item in status["items"]
        if item["generative"] == "QUARANTINED" or item["evidence"] == "QUARANTINED"
    ]
    return {
        "schema": "helix-corpus-quarantine-report/1.0",
        "counts": {
            "items": len(items),
            "events": len(events),
            "reasons": sum(reason_counts.values()),
        },
        "ledger_valid": status["ledger_valid"],
        "ledger_problems": status["ledger_problems"],
        "reason_counts": dict(sorted(reason_counts.items())),
        "items": items,
        "events": events,
    }


def migrate_legacy_project_list(path: str) -> list:
    manifests = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            match = LEGACY_ROW.match(line.rstrip("\n"))
            if not match:
                continue
            name, slug, summary = match.groups()
            row_hash = digest(line.rstrip("\n"))
            corpus_id = "HC-LEGACY-" + digest(slug or name)[:12].upper()
            manifests.append({
                "schema": MANIFEST_SCHEMA,
                "corpus_id": corpus_id,
                "revision": 1,
                "name": name,
                "summary": summary or "Legacy inventory entry",
                "origin": {
                    "kind": "legacy_inventory",
                    "locator": path.replace("\\", "/"),
                    "revision": "unversioned",
                    "license": "NOASSERTION",
                    "license_verified": False,
                    "license_evidence": "missing-license-evidence",
                    "license_evidence_sha256": "0" * 64,
                    "source_evidence": "missing-source-evidence",
                    "source_sha256": row_hash,
                },
                "character": {
                    "domain": "unclassified",
                    "primary_verb": "unknown",
                    "input_shape": "unknown",
                    "output_shape": "unknown",
                },
                "genes": ["legacy_uncharacterized"],
                "dependencies": [],
                "restrictions": ["migration_candidate_only", "no_auto_admission"],
                "machine": {"status": "hypothesis", "label": "unclassified",
                            "evidence": []},
                "verification": {
                    "reproducible": False,
                    "tests_passed": False,
                    "deterministic": False,
                    "parity_available": False,
                    "reproduction_command": "",
                    "behavior_sha256": "",
                    "supporting_files": [],
                    "supporting_symbols": [],
                },
                "safety": {
                    "secret_scan_passed": False,
                    "pii_scan_passed": False,
                    "malware_scan_passed": False,
                    "execution_isolated": False,
                },
                "provenance": [f"legacy-project-list:{name}"],
            })
    return manifests


def emit_migration(manifests: list, out_dir: str) -> list:
    written = []
    for manifest in manifests:
        path = os.path.join(out_dir, manifest["corpus_id"] + ".json")
        existing = read_json(path)
        if existing is not None and manifest_digest(existing) != manifest_digest(manifest):
            raise ValueError(f"migration output conflict: {path}")
        if existing is None:
            atomic_write_json(path, manifest)
        written.append(path)
    return written


def _arg(argv, name, default=None):
    try:
        return argv[argv.index(name) + 1]
    except (ValueError, IndexError):
        return default


def corpus_cli(argv: list, repo_root: str) -> tuple:
    """Return ``(exit_code, JSON-serializable payload)`` for a corpus subcommand."""
    if not argv:
        return 2, {"error": "missing corpus subcommand"}
    command = argv[0]
    corpus_root = _arg(argv, "--root", os.path.join(repo_root, "seed", "corpus"))
    try:
        if command == "validate":
            path = _arg(argv, "--manifest")
            if not path:
                return 2, {"error": "--manifest required"}
            manifest = read_json(path)
            if manifest is None:
                raise FileNotFoundError(path)
            problems = validate_manifest(repo_root, manifest)
            return (0 if not problems else 4), {"valid": not problems, "problems": problems,
                                                "manifest_sha256": manifest_digest(manifest)}
        if command == "intake":
            path = _arg(argv, "--manifest")
            if not path:
                return 2, {"error": "--manifest required"}
            manifest = read_json(path)
            if manifest is None:
                raise FileNotFoundError(path)
            result = intake_manifest(repo_root, corpus_root, manifest)
            return (0 if result["status"] != "INVALID" else 4), result
        if command in ("admit", "promote"):
            corpus_id = _arg(argv, "--id")
            now = _arg(argv, "--now")
            if not corpus_id or not now:
                return 2, {"error": "--id and --now required"}
            evidence_root = _arg(argv, "--evidence-root")
            if not evidence_root:
                return 2, {"error": "--evidence-root required"}
            tier = "generative" if command == "admit" else "evidence"
            review = None
            if tier == "evidence":
                review_path = _arg(argv, "--review")
                if not review_path:
                    return 2, {"error": "--review required for promote"}
                review = read_json(review_path)
                if review is None:
                    raise FileNotFoundError(review_path)
            result = admit_item(
                repo_root, corpus_root, corpus_id, tier, now, review, evidence_root)
            return (0 if result["decision"]["decision"] == "ADMITTED" else 4), result
        if command == "fingerprint":
            corpus_id = _arg(argv, "--id")
            if not corpus_id:
                return 2, {"error": "--id required"}
            manifest = load_item(corpus_root, corpus_id)
            return 0, {"corpus_id": corpus_id, "manifest_sha256": manifest_digest(manifest),
                       "fingerprints": fingerprints(manifest)}
        if command == "verify-ledger":
            problems = verify_ledger(repo_root, corpus_paths(corpus_root)["ledger"])
            return (0 if not problems else 4), {"valid": not problems, "problems": problems}
        if command == "status":
            return 0, corpus_status(repo_root, corpus_root)
        if command == "health":
            result = corpus_health(repo_root, corpus_root)
            return (0 if result["ledger_valid"] else 4), result
        if command == "quarantine-report":
            result = corpus_quarantine_report(repo_root, corpus_root)
            return (0 if result["ledger_valid"] else 4), result
        if command == "migrate":
            path = _arg(argv, "--legacy-list")
            if not path:
                return 2, {"error": "--legacy-list required"}
            manifests = migrate_legacy_project_list(path)
            out = _arg(argv, "--out")
            written = emit_migration(manifests, out) if out else []
            return 0, {"count": len(manifests), "written": written,
                       "manifests": [] if out else manifests}
        return 2, {"error": f"unknown corpus subcommand: {command}"}
    except (FileNotFoundError, KeyError, ValueError) as error:
        return 4, {"error": str(error)}
