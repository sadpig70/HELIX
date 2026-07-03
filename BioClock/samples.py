#!/usr/bin/env python3
"""Deterministic sample fixtures for BioClock.

  - VALID: no drift, full samples, quarantine passed -> certified
  - DRIFT: severe drift, short sample gap, quarantine failed -> revoked
"""

import copy
import json
import os

VALID_PROTOCOL = {
    "endpoint": "EFFICACY-CARDIAC-01",
    "target_effect_size": 0.50,
    "required_samples": 120,
}

VALID_EVIDENCE = {
    "observed_effect_size": 0.48,
    "actual_samples": 120,
    "data_freshness_days": 3,
}

VALID_QUARANTINE = {
    "organism_id": "ORG-BIO-0001",
    "stages": [
        {"name": "intake", "duration_days": 7, "observation_passed": True},
        {"name": "observation", "duration_days": 14, "observation_passed": True},
        {"name": "release", "duration_days": 3, "observation_passed": True},
    ],
}

DRIFT_PROTOCOL = {
    "endpoint": "EFFICACY-NEURO-09",
    "target_effect_size": 0.50,
    "required_samples": 100,
}

DRIFT_EVIDENCE = {
    "observed_effect_size": 0.05,
    "actual_samples": 60,
    "data_freshness_days": 45,
}

DRIFT_QUARANTINE = {
    "organism_id": "ORG-BIO-0042",
    "stages": [
        {"name": "intake", "duration_days": 7, "observation_passed": True},
        {"name": "observation", "duration_days": 14, "observation_passed": False},
        {"name": "release", "duration_days": 3, "observation_passed": False},
    ],
}


def samples():
    """Return deep copies of all sample fixtures keyed by scenario name."""
    return {
        "valid_protocol": copy.deepcopy(VALID_PROTOCOL),
        "valid_evidence": copy.deepcopy(VALID_EVIDENCE),
        "valid_quarantine": copy.deepcopy(VALID_QUARANTINE),
        "drift_protocol": copy.deepcopy(DRIFT_PROTOCOL),
        "drift_evidence": copy.deepcopy(DRIFT_EVIDENCE),
        "drift_quarantine": copy.deepcopy(DRIFT_QUARANTINE),
    }


def write_samples(out_dir):
    """Write every sample fixture to out_dir as sorted JSON. Returns {name: path}."""
    os.makedirs(out_dir, exist_ok=True)
    written = {}
    for name, doc in samples().items():
        path = os.path.join(out_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        written[name] = path
    return written
