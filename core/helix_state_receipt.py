"""Deterministic evidence primitives for HELIX state receipts.

This module intentionally has no clock, network, subprocess, or AI dependency.
Freshness means content-addressed reproducibility, not recency: the current report
and every declared source must match the hashes recorded when the report was made.
"""

import hashlib
import json
import os


FRESHNESS_STATES = ("fresh", "stale", "missing", "unverifiable")
BUILDER_VERSION = "helix-state-receipt-builder/1.0"


def _portable_path(path: str) -> str:
    return path.replace("\\", "/")


def _display_path(root: str, path: str) -> str:
    """Prefer root-relative evidence paths; preserve cross-volume paths portably."""
    try:
        return _portable_path(os.path.relpath(path, root))
    except ValueError:  # Windows paths on different drives cannot be relativized.
        return _portable_path(os.path.abspath(path))


def _evidence_file(root: str, role: str, path: str) -> dict:
    """Build one content-addressed evidence row, including explicit absence."""
    full_path = path if os.path.isabs(path) else os.path.join(root, path)
    display_path = _display_path(root, full_path)
    if not os.path.isfile(full_path):
        return {"role": role, "path": display_path, "sha256": None,
                "bytes": None, "status": "missing"}
    return {"role": role, "path": display_path, "sha256": sha256_file(full_path),
            "bytes": os.path.getsize(full_path), "status": "present"}


def _report_evidence(root: str, binding: dict) -> dict:
    """Evaluate a caller-sealed report binding and normalize paths for receipts."""
    path = binding["path"]
    full_path = path if os.path.isabs(path) else os.path.join(root, path)
    sources = []
    for source in binding.get("sources", []):
        source_path = source["path"]
        source_full = source_path if os.path.isabs(source_path) else os.path.join(root, source_path)
        sources.append({"path": source_full, "sha256": source.get("sha256")})
    result = assess_report_freshness(
        binding["report"], full_path, binding.get("expected_sha256"), sources)
    result["path"] = _display_path(root, full_path)
    result["source_paths"] = [
        _display_path(root, source_path)
        for source_path in result["source_paths"]
    ]
    normalized_reasons = []
    for reason in result["reasons"]:
        code, separator, reason_path = reason.partition(":")
        normalized_reasons.append(
            f"{code}:{_display_path(root, reason_path)}" if separator else reason)
    result["reasons"] = normalized_reasons
    return result


def _runtime_state(report: dict) -> dict:
    """Project build_report output onto the state contract used by next_action."""
    latest_run = report.get("latest_exploit_run") or {}
    last_engine = "exploit" if latest_run.get("phase") else (
        "explore" if report.get("winner") else (
            "exploit" if report.get("ledger_origins", {}).get("exploit", 0) else None
        )
    )
    diversity = report.get("diversity") or {}
    winner = report.get("winner") or {}
    corpus_size = int(report.get("ledger_origins", {}).get("exploit", 0)) + len(
        report.get("corpus_feedback") or [])
    return {
        "last_engine": last_engine,
        "corpus_size": corpus_size,
        "unified_ledger_entries": int(report.get("ledger_size", 0)),
        "pending_implemented_winner": False,
        "winner_in_ledger": bool(winner.get("already_consumed", False)),
        "diversity": {
            "triggered": bool(diversity.get("triggered", False)),
            "repair_required": bool(diversity.get(
                "repair_required", diversity.get("triggered", False))),
            "breaches": int(diversity.get("breaches", 0)),
        },
    }


def _blockers(inputs: list, gates: list, reports: list, runtime_state: dict) -> list:
    blockers = []
    for row in inputs:
        if row["status"] == "missing":
            blockers.append({
                "code": "missing_input", "severity": "blocking",
                "evidence": [row["path"]], "effect": "state is incomplete",
            })
    for row in gates:
        if row["status"] == "missing":
            blockers.append({
                "code": "missing_gate", "severity": "blocking",
                "evidence": [row["path"]], "effect": "policy authority is incomplete",
            })
    freshness_code = {
        "missing": "missing_report",
        "stale": "stale_report",
        "unverifiable": "unverifiable_report",
    }
    for row in reports:
        if row["status"] != "fresh":
            blockers.append({
                "code": freshness_code[row["status"]], "severity": "blocking",
                "evidence": [row["path"]] + row["reasons"],
                "effect": "derived report cannot authorize actuation",
            })
    if runtime_state["diversity"]["repair_required"]:
        blockers.append({
            "code": "diversity_repair_required", "severity": "blocking",
            "evidence": [f"breaches={runtime_state['diversity']['breaches']}"],
            "effect": "refresh inputs before generation or actuation",
        })
    return sorted(blockers, key=lambda item: (item["code"], item["evidence"]))


def canonical_receipt_bytes(receipt: dict) -> bytes:
    """Canonical JSON bytes with receipt_hash omitted."""
    body = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def seal_receipt(receipt: dict) -> dict:
    """Return a copy sealed by SHA256 over canonical_receipt_bytes."""
    sealed = dict(receipt)
    sealed.pop("receipt_hash", None)
    sealed["receipt_hash"] = hashlib.sha256(canonical_receipt_bytes(sealed)).hexdigest()
    return sealed


def verify_receipt_hash(receipt: dict) -> bool:
    expected = receipt.get("receipt_hash")
    return isinstance(expected, str) and expected == hashlib.sha256(
        canonical_receipt_bytes(receipt)).hexdigest()


def _value_sha256(value) -> str:
    if value is None:
        return None
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _indexed(rows, key_name) -> dict:
    return {str(row.get(key_name)): row for row in rows or []}


def compare_receipts(stored: dict, current: dict) -> dict:
    """Compare authority-relevant receipt sections in deterministic key order."""
    changes = []

    def add(category, key, before, after):
        if before != after:
            changes.append({
                "category": category,
                "key": key,
                "before_sha256": _value_sha256(before),
                "after_sha256": _value_sha256(after),
            })

    if not verify_receipt_hash(stored):
        add("receipt_integrity", "stored_receipt_hash",
            {"valid": False, "receipt_hash": stored.get("receipt_hash")}, {"valid": True})
    if not verify_receipt_hash(current):
        add("receipt_integrity", "current_receipt_hash",
            {"valid": False, "receipt_hash": current.get("receipt_hash")}, {"valid": True})

    indexed_sections = (
        ("canonical_inputs", "canonical_inputs", "role"),
        ("gate_hashes", "gate_hashes", "gate"),
        ("report_freshness", "report_freshness", "report"),
    )
    for category, section, key_name in indexed_sections:
        before_rows = _indexed(stored.get(section), key_name)
        after_rows = _indexed(current.get(section), key_name)
        for key in sorted(set(before_rows) | set(after_rows)):
            add(category, key, before_rows.get(key), after_rows.get(key))

    scalar_sections = (
        ("generated_from", "generated_from"),
        ("runtime_state", "runtime_state"),
        ("next_action", "next_action"),
        ("authority", "authority"),
    )
    for category, section in scalar_sections:
        add(category, section, stored.get(section), current.get(section))

    changes.sort(key=lambda item: (item["category"], item["key"]))
    categories = sorted({item["category"] for item in changes})
    return {
        "drifted": bool(changes),
        "stored_receipt_hash": stored.get("receipt_hash"),
        "categories": categories,
        "changes": changes,
    }


def apply_drift_gate(current: dict, drift: dict) -> dict:
    """Attach drift evidence and fail closed when any authority-relevant value changed."""
    gated = json.loads(json.dumps(current))
    gated["drift"] = drift
    blockers = [item for item in gated.get("blockers", [])
                if item.get("code") != "state_drift"]
    if drift.get("drifted"):
        blockers.append({
            "code": "state_drift",
            "severity": "blocking",
            "evidence": [f"category:{name}" for name in drift.get("categories", [])],
            "effect": "stored authority is stale; actuator must not proceed",
        })
    blockers.sort(key=lambda item: (item["code"], item["evidence"]))
    gated["blockers"] = blockers
    clearances = sorted({item["code"] for item in blockers
                         if item.get("severity") == "blocking"})
    gated["authority"] = {
        "actuator_ready": not clearances,
        "basis": "clear" if not clearances else "blocked",
        "required_clearances": clearances,
    }
    return seal_receipt(gated)


def build_state_receipt(root: str, runtime_report: dict, input_paths: dict,
                        gate_paths: dict, report_bindings: list, git_head=None,
                        replay_argv=None) -> dict:
    """Build and seal one schema-shaped HELIX state receipt.

    All selected paths and Git identity are explicit inputs. The builder does not
    consult a clock, subprocess, loader fallback, network, or AI service.
    """
    root = os.path.abspath(root)
    inputs = [_evidence_file(root, role, path)
              for role, path in sorted(input_paths.items())]
    gates = []
    for gate, path in sorted(gate_paths.items()):
        row = _evidence_file(root, gate, path)
        row["gate"] = row.pop("role")
        gates.append(row)
    reports = [_report_evidence(root, binding) for binding in report_bindings]
    reports.sort(key=lambda item: (item["report"], item["path"]))
    state = _runtime_state(runtime_report)
    blockers = _blockers(inputs, gates, reports, state)
    action = runtime_report.get("next_action") or {}
    next_action = {
        "action": action.get("action"),
        "why": action.get("why", ""),
        "target": action.get("target"),
    }
    clearances = sorted({item["code"] for item in blockers
                         if item["severity"] == "blocking"})
    receipt = {
        "schema": "helix-state-receipt/1.0",
        "generated_from": {
            "root": _portable_path(root),
            "git_head": git_head,
            "builder_version": BUILDER_VERSION,
        },
        "canonical_inputs": inputs,
        "gate_hashes": gates,
        "report_freshness": reports,
        "runtime_state": state,
        "blockers": blockers,
        "next_action": next_action,
        "authority": {
            "actuator_ready": not clearances,
            "basis": "clear" if not clearances else "blocked",
            "required_clearances": clearances,
        },
        "replay_command": {
            "cwd": _portable_path(root),
            "argv": list(replay_argv or ["python", "helix.py", "status"]),
        },
    }
    return seal_receipt(receipt)


def sha256_file(path: str) -> str:
    """Return lowercase SHA256 for a file without loading it all into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_bindings(source_bindings) -> list:
    """Normalize source bindings into deterministic path order."""
    normalized = []
    seen = set()
    for binding in source_bindings or []:
        if not isinstance(binding, dict):
            raise TypeError("source binding must be an object")
        path = binding.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("source binding path must be a non-empty string")
        if path in seen:
            raise ValueError(f"duplicate source binding: {path}")
        seen.add(path)
        normalized.append({"path": path, "sha256": binding.get("sha256")})
    return sorted(normalized, key=lambda item: item["path"])


def assess_report_freshness(report: str, path: str, expected_report_sha256: str,
                            source_bindings: list) -> dict:
    """Classify a report as fresh, stale, missing, or unverifiable.

    Rules, in precedence order:
    1. Missing report -> missing.
    2. Missing report hash/bindings, missing source, or missing source hash -> unverifiable.
    3. Report or source content hash mismatch -> stale.
    4. Every declared content hash matches -> fresh.

    Paths are evidence identifiers supplied by the caller. No mtime, wall clock, Git
    metadata, or environment state participates in the decision.
    """
    bindings = _normalized_bindings(source_bindings)
    source_paths = [item["path"] for item in bindings]
    source_hashes = [item["sha256"] for item in bindings if isinstance(item["sha256"], str)]

    if not os.path.isfile(path):
        return {
            "report": report,
            "path": path,
            "sha256": None,
            "expected_sha256": expected_report_sha256,
            "source_paths": source_paths,
            "source_hashes": source_hashes,
            "status": "missing",
            "reasons": ["report_missing"],
        }

    actual_report_sha256 = sha256_file(path)
    reasons = []
    unverifiable = False
    stale = False

    if not isinstance(expected_report_sha256, str) or not expected_report_sha256:
        reasons.append("report_hash_unbound")
        unverifiable = True
    elif actual_report_sha256 != expected_report_sha256:
        reasons.append("report_hash_mismatch")
        stale = True

    if not bindings:
        reasons.append("source_bindings_absent")
        unverifiable = True

    for binding in bindings:
        source_path = binding["path"]
        expected_source_sha256 = binding["sha256"]
        if not os.path.isfile(source_path):
            reasons.append(f"source_missing:{source_path}")
            unverifiable = True
        elif not isinstance(expected_source_sha256, str) or not expected_source_sha256:
            reasons.append(f"source_hash_unbound:{source_path}")
            unverifiable = True
        elif sha256_file(source_path) != expected_source_sha256:
            reasons.append(f"source_hash_mismatch:{source_path}")
            stale = True

    status = "stale" if stale else ("unverifiable" if unverifiable else "fresh")
    return {
        "report": report,
        "path": path,
        "sha256": actual_report_sha256,
        "expected_sha256": expected_report_sha256,
        "source_paths": source_paths,
        "source_hashes": source_hashes,
        "status": status,
        "reasons": reasons,
    }
