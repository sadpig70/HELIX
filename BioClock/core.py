#!/usr/bin/env python3
"""Deterministic biological clock verification layer (stdlib only).

BioClock recombines three concerns:
  - DriftDossier: clinical evidence drift tracking
  - Qvidence: bio data pipeline health
  - LazarettoStage: biological quarantine staging

No wall-clock state is used; every computation is a pure function of its inputs.
"""

SEVERITY = {"none": 0, "moderate": 1, "severe": 2}


def _severity_for(drift_magnitude):
    if drift_magnitude < 0.1:
        return "none"
    if drift_magnitude < 0.3:
        return "moderate"
    return "severe"


def track_drift(protocol, evidence):
    """Measure clinical evidence drift against a trial protocol.

    protocol: {endpoint, target_effect_size, required_samples}
    evidence: {observed_effect_size, actual_samples, data_freshness_days}

    Returns a deterministic drift report dict.
    """
    target = protocol["target_effect_size"]
    observed = evidence["observed_effect_size"]
    required = protocol["required_samples"]
    actual = evidence["actual_samples"]

    drift_magnitude = abs(target - observed)
    sample_gap = max(0, required - actual)
    drift_severity = _severity_for(drift_magnitude)
    protocol_compliant = drift_severity == "none" and sample_gap == 0

    return {
        "endpoint": protocol["endpoint"],
        "drift_magnitude": drift_magnitude,
        "sample_gap": sample_gap,
        "data_freshness_days": evidence["data_freshness_days"],
        "drift_severity": drift_severity,
        "protocol_compliant": protocol_compliant,
    }


def certify_bio_clock(drift_report, quarantine_schedule):
    """Certify a biological clock from a drift report and quarantine stages.

    drift_report: output of track_drift (must carry drift_severity)
    quarantine_schedule: {organism_id, stages: [{name, duration_days, observation_passed}]}

    Returns a deterministic certification verdict dict.
    """
    drift_severity = drift_report["drift_severity"]
    stages = quarantine_schedule["stages"]
    all_stages_passed = bool(stages) and all(s["observation_passed"] for s in stages)

    if drift_severity == "none" and all_stages_passed:
        certification = "certified"
    elif drift_severity == "moderate":
        certification = "conditional"
    else:
        certification = "revoked"

    return {
        "organism_id": quarantine_schedule["organism_id"],
        "certification": certification,
        "drift_severity": drift_severity,
        "quarantine_complete": all_stages_passed,
        "bio_clock_valid": certification == "certified",
    }


def render_report(result):
    """Render a drift report and/or a certification verdict as Markdown."""
    lines = ["# BioClock Report", ""]

    if "drift_magnitude" in result:
        endpoint = result.get("endpoint", "")
        lines.append(f"## Drift Dossier — {endpoint}")
        lines.append("")
        lines.append(f"- drift_magnitude: {result['drift_magnitude']}")
        lines.append(f"- drift_severity: **{result['drift_severity']}**")
        lines.append(f"- sample_gap: {result['sample_gap']}")
        lines.append(f"- data_freshness_days: {result['data_freshness_days']}")
        lines.append(f"- protocol_compliant: {result['protocol_compliant']}")
        lines.append("")

    if "certification" in result:
        organism_id = result.get("organism_id", "")
        lines.append(f"## Bio Clock Certification — {organism_id}")
        lines.append("")
        lines.append(f"- certification: **{result['certification']}**")
        lines.append(f"- drift_severity: {result['drift_severity']}")
        lines.append(f"- quarantine_complete: {result['quarantine_complete']}")
        lines.append(f"- bio_clock_valid: {result['bio_clock_valid']}")
        lines.append("")

    return "\n".join(lines)
