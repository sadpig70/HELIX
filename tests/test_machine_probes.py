import hashlib
import json
import unittest

import tests._path  # noqa: F401
from core.helix_machine_probes import (
    agreement_report,
    probe_M1,
    probe_M2,
    probe_M3,
    probe_M4,
    probe_M5,
    probe_M6,
    probe_M7,
    probe_M8,
    probe_M9,
    probe_M10,
    probe_M11,
    probe_M12,
    probe_M13,
    probe_M14,
    probe_M15,
    probe_M16,
    probe_M17,
)


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(obj):
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def _ledger_record(index, result_hash, prev_hash="", now="T"):
    core = {"index": index, "subject": f"S{index}", "pack": "handback", "verdict": "valid",
            "result_hash": result_hash, "prev_hash": prev_hash}
    return {**core, "record_hash": _sha(core), "recorded_at": now}


M1_RECORD_0 = _ledger_record(0, "rh0")
M1_RECORD_1 = _ledger_record(1, "rh1", M1_RECORD_0["record_hash"])
M1_ARTIFACT = {"operation": "hash_chain_ledger", "records": [M1_RECORD_0, M1_RECORD_1]}

M2_ARTIFACT = {
    "operation": "predicate_gate",
    "severity_order": ["valid", "thin", "breach"],
    "merge": "max_severity",
    "checks": [
        {"gate": "authority", "verdict": "valid"},
        {"gate": "rollback", "verdict": "thin"},
        {"gate": "trace", "verdict": "breach"},
    ],
    "aggregate": {"verdict": "breach", "merge": "max_severity"},
}

M3_ARTIFACT = {
    "operation": "predicate_gate",
    "packet": {"packet_id": "P1", "evidence_hash": "e7"},
    "severity_order": ["valid", "thin", "breach"],
    "checks": [
        {"gate": "authority", "verdict": "valid", "reason": "predicate satisfied"},
        {"gate": "rollback", "verdict": "thin", "reason": "missing rollback drill"},
        {"gate": "trace", "verdict": "breach", "reason": "missing trace"},
    ],
    "aggregate": {"verdict": "breach", "worst": "trace", "merge": "max_severity"},
}

M4_ARTIFACT = {
    "operation": "provenance_verify",
    "record": {"evidence_hash": "e7"},
    "chain": [{"evidence_hash": "e6", "confirmed": True}, {"evidence_hash": "e7", "confirmed": True}],
    "result": {"provenance_valid": True, "chain_length": 2, "evidence_hash": "e7"},
}

M5_ARTIFACT = {
    "operation": "clearing",
    "supply": 800,
    "allocated": 800,
    "remaining": 0,
    "allocations": [
        {"party_id": "defense", "amount": 400, "priority": 80.0},
        {"party_id": "energy", "amount": 400, "priority": 30.0},
    ],
    "requests": [
        {"party_id": "defense", "amount": 400, "priority": 80.0},
        {"party_id": "energy", "amount": 400, "priority": 30.0},
        {"party_id": "consumer", "amount": 400, "priority": -60.0},
    ],
}

M6_ARTIFACT = {
    "operation": "pricing",
    "outputs": [
        {"id": "op-a", "units": 1000, "unit_cost": 0.002, "cost": 2.0},
        {"id": "op-b", "premium": 0.15},
    ],
}

M7_ARTIFACT = {
    "operation": "settlement",
    "settlement_amount": 100.0,
    "buyer_net": 50.0,
    "seller_net": -50.0,
    "actual_failure": True,
    "settled_at": "T",
}

M8_ARTIFACT = {
    "operation": "shock_rehearsal",
    "scenario": "dual-shock",
    "survival_days": 3.8461538461538463,
    "total_shortfall": 960.0,
    "affected": ["Li", "Co"],
    "per_item": [
        {"id": "Li", "coverage_days": 19.23076923076923, "shortfall": 280.0},
        {"id": "Co", "coverage_days": 3.8461538461538463, "shortfall": 680.0},
    ],
    "rehearsed_at": "T",
}

M10_ARTIFACT = {
    "operation": "threshold_bound",
    "verdict_order": ["compliant", "restricted", "violation"],
    "merge": "max_severity",
    "dimensions": [
        {"dimension": "ingest", "utilization": 0.4, "threshold": 0.85, "verdict": "compliant"},
        {"dimension": "compute", "utilization": 0.9, "threshold": 0.85, "verdict": "restricted"},
        {"dimension": "egress", "utilization": 1.2, "threshold": 1.0, "verdict": "violation"},
    ],
    "aggregate": {"verdict": "violation", "merge": "max_severity"},
}

M9_ARTIFACT = {
    "operation": "candidate_routing",
    "selected": "wind-farm-2",
    "selected_score": 90.0,
    "all_scores": [
        {"name": "solar-farm-1", "score": 40.0, "eligible": True, "verified": True, "reason": ""},
        {"name": "wind-farm-2", "score": 90.0, "eligible": True, "verified": True, "reason": ""},
        {"name": "coal-3", "score": 114.0, "eligible": False, "verified": True, "reason": "renewable_pct_below_min"},
    ],
    "demand": {"workload_tflops": 10},
}

M12_ARTIFACT = {
    "operation": "staged_release",
    "release": {"id": "OS-4.2", "stages": [
        {"name": "canary", "cohort_pct": 5, "observation_window": "48h",
         "observed_incidents": 0, "incident_threshold": 1},
        {"name": "early", "cohort_pct": 25, "observation_window": "72h",
         "observed_incidents": 1, "incident_threshold": 2},
        {"name": "broad", "cohort_pct": 70, "observation_window": "168h",
         "observed_incidents": 0, "incident_threshold": 3},
    ]},
    "stages": [
        {"stage": "canary", "cohort_pct": 5, "cumulative_pct": 5.0,
         "observation_window": "48h", "observed_incidents": 0, "incident_threshold": 1, "gate": "go"},
        {"stage": "early", "cohort_pct": 25, "cumulative_pct": 30.0,
         "observation_window": "72h", "observed_incidents": 1, "incident_threshold": 2, "gate": "go"},
        {"stage": "broad", "cohort_pct": 70, "cumulative_pct": 100.0,
         "observation_window": "168h", "observed_incidents": 0, "incident_threshold": 3, "gate": "go"},
    ],
    "halted": False,
    "rollout_complete": True,
    "planned_at": "T",
}

M13_ARTIFACT = {
    "operation": "compatibility_gap_scoring",
    "pairs": [
        {"source": "legacy-a", "target": "adapter-x", "compatibility_score": 0.8, "gap_score": 0.2},
        {"source": "legacy-b", "target": "adapter-x", "compatibility_score": 0.4, "gap_score": 0.6},
    ],
    "summary": {"pair_count": 2, "mean_compatibility": 0.6, "mean_gap": 0.4},
}

M11_ARTIFACT = {
    "operation": "drift_detection",
    "packet": {"packet_id": "PD-THIN-001", "policy": {
        "baseline_id": "base-1",
        "current_id": "cur-1",
        "drift": 0.22,
        "drift_threshold": 0.2,
        "approval_trace": "evidence/approval/a1.json",
    }},
    "checks": [
        {"gate": "baseline_match", "verdict": "valid", "reason": "predicate satisfied"},
        {"gate": "drift_magnitude", "verdict": "thin", "reason": "drift marginally over threshold"},
        {"gate": "approval_trace", "verdict": "valid", "reason": "predicate satisfied"},
    ],
}

M14_ARTIFACT = {
    "operation": "fingerprint_dedup",
    "items": [
        {"name": "alpha", "parts": ["schemas/packet-a.json", "authority", "trace"],
         "fingerprint": "pending"},
        {"name": "alpha-renamed", "parts": ["trace", "schemas/packet-a.json", "authority"],
         "fingerprint": "pending"},
        {"name": "beta", "parts": ["schemas/packet-b.json", "authority"],
         "fingerprint": "pending"},
    ],
}
M14_ARTIFACT["items"][0]["fingerprint"] = hashlib.sha256("authority|schemas packet a json|trace".encode("utf-8")).hexdigest()
M14_ARTIFACT["items"][1]["fingerprint"] = M14_ARTIFACT["items"][0]["fingerprint"]
M14_ARTIFACT["items"][2]["fingerprint"] = hashlib.sha256("authority|schemas packet b json".encode("utf-8")).hexdigest()
M14_ARTIFACT["duplicate_groups"] = [["alpha", "alpha-renamed"]]

M15_SCORE_ARTIFACT = {
    "operation": "assessment_scoring",
    "weights": {"a": 0.5, "b": 0.3, "c": 0.2},
    "bands": [{"min": 0.7, "tier": "high"}, {"min": 0.4, "tier": "mid"}, {"min": 0.0, "tier": "low"}],
    "scored": [
        {"id": "x", "score": 1.0, "tier": "high"},
        {"id": "z", "score": 0.55, "tier": "mid"},
        {"id": "y", "score": 0.3, "tier": "low"},
    ],
    "count_by_tier": {"high": 1, "mid": 1, "low": 1},
}

M15_RULE_ARTIFACT = {
    "operation": "assessment_scoring",
    "rules": [
        {"tier": "urgent", "all": [{"factor": "delay", "op": ">=", "value": 0.8}]},
        {"tier": "watch", "any": [{"factor": "reliability", "op": "<", "value": 0.6}]},
        {"tier": "clear"},
    ],
    "scored": [
        {"id": "detour-a", "tier": "urgent"},
        {"id": "detour-b", "tier": "watch"},
        {"id": "detour-c", "tier": "clear"},
    ],
    "count_by_tier": {"urgent": 1, "watch": 1, "clear": 1},
}

M16_ARTIFACT = {
    "operation": "route_deviation_simulation",
    "planned_route": ["dock", "hall", "lab"],
    "actual_route": ["dock", "storage", "lab"],
    "deviation_policy": {"blocked_zones": ["storage"], "max_deviation_count": 0},
    "rollback": {"required": True, "completed": True, "restored_route": ["dock", "hall", "lab"]},
    "simulation": {
        "deviation_count": 1,
        "blocked_zone_hits": 1,
        "rollback_required": True,
        "decision": "rollback",
    },
}

M17_ARTIFACT = {
    "operation": "endowment_funding_projection",
    "policy": {
        "real_return_rate": 0.1,
        "frontier_cost_year0": 5.0,
        "cost_growth_rate": 0.0,
        "horizon_years": 3,
        "min_coverage_ratio": 1.0,
        "require_open_access": True,
    },
    "pledges": [
        {"pledge_id": "p-univ", "name": "Research university", "amount": 100.0},
        {"pledge_id": "p-lab", "name": "National laboratory", "amount": 50.0},
    ],
    "schedule": [
        {"year": 1, "opening_corpus": 150.0, "payout": 15.0, "cost": 5.0, "closing_corpus": 160.0},
        {"year": 2, "opening_corpus": 160.0, "payout": 16.0, "cost": 5.0, "closing_corpus": 171.0},
        {"year": 3, "opening_corpus": 171.0, "payout": 17.1, "cost": 5.0, "closing_corpus": 183.1},
    ],
    "posture": {
        "verdict": "endowed",
        "pledge_count": 2,
        "corpus": 150.0,
        "payout_year0": 15.0,
        "frontier_cost_year0": 5.0,
        "coverage_year0": 3.0,
        "years_funded": 3,
        "horizon_years": 3,
        "min_corpus": 160.0,
        "final_corpus": 183.1,
        "preserved": True,
        "open_access_granted": True,
    },
    "evidence": [
        {"ref_id": "p-univ", "detail": "pledge 100", "source": "declared pledge book + endowment policy"},
        {"ref_id": "p-lab", "detail": "pledge 50", "source": "declared pledge book + endowment policy"},
    ],
}


class TestMachineProbes(unittest.TestCase):
    def test_probe_m1_detects_hash_chain(self):
        r = probe_M1(M1_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["valid_chain"])

    def test_probe_m1_rejects_broken_chain(self):
        bad = {"records": [M1_RECORD_0, {**M1_RECORD_1, "prev_hash": "bad"}]}
        self.assertFalse(probe_M1(bad)["holds"])

    def test_probe_m2_detects_predicate_severity(self):
        r = probe_M2(M2_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertEqual(r["evidence"]["severity_family"], ["valid", "thin", "breach"])

    def test_probe_m3_detects_predicate_gate(self):
        r = probe_M3(M3_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["aggregate_matches"])

    def test_probe_m3_rejects_private_payload(self):
        bad = {**M3_ARTIFACT, "packet": {"packet_id": "P1", "secret": "x"}}
        self.assertFalse(probe_M3(bad)["holds"])

    def test_probe_m4_detects_confirmed_provenance(self):
        r = probe_M4(M4_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["confirmed_match"])

    def test_probe_m4_rejects_false_positive_provenance(self):
        bad = {**M4_ARTIFACT, "chain": [{"evidence_hash": "e7", "confirmed": False}]}
        self.assertFalse(probe_M4(bad)["holds"])

    def test_probe_m6_detects_pricing_without_verdict_algebra(self):
        r = probe_M6(M6_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["verdict_algebra_absent"])
        self.assertFalse(probe_M6(M2_ARTIFACT)["holds"])

    def test_probe_m5_detects_priority_clearing(self):
        r = probe_M5(M5_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["conservation"])
        self.assertTrue(r["evidence"]["priority_allocation_matches"])

    def test_probe_m5_rejects_priority_violation(self):
        bad = {
            **M5_ARTIFACT,
            "allocations": [
                {"party_id": "consumer", "amount": 400, "priority": -60.0},
                {"party_id": "defense", "amount": 400, "priority": 80.0},
            ],
        }
        self.assertFalse(probe_M5(bad)["holds"])

    def test_probe_m7_detects_zero_sum_settlement(self):
        r = probe_M7(M7_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["zero_sum"])

    def test_probe_m7_rejects_non_zero_sum_settlement(self):
        bad = {**M7_ARTIFACT, "seller_net": -40.0}
        self.assertFalse(probe_M7(bad)["holds"])

    def test_probe_m8_detects_shock_rehearsal(self):
        r = probe_M8(M8_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["survival_matches_min_coverage"])
        self.assertTrue(r["evidence"]["shortfall_matches_sum"])

    def test_probe_m8_rejects_bad_shortfall_sum(self):
        bad = {**M8_ARTIFACT, "total_shortfall": 999.0}
        self.assertFalse(probe_M8(bad)["holds"])

    def test_probe_m12_detects_staged_release(self):
        r = probe_M12(M12_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["plan_matches_source"])
        self.assertTrue(r["evidence"]["complete_state_matches"])

    def test_probe_m12_rejects_bad_halt_state(self):
        bad = {
            **M12_ARTIFACT,
            "release": {"id": "OS-4.2", "stages": [
                {"name": "canary", "cohort_pct": 5, "observation_window": "48h",
                 "observed_incidents": 2, "incident_threshold": 1},
                {"name": "broad", "cohort_pct": 95, "observation_window": "168h",
                 "observed_incidents": 0, "incident_threshold": 3},
            ]},
        }
        self.assertFalse(probe_M12(bad)["holds"])

    def test_probe_m11_detects_drift_threshold(self):
        r = probe_M11(M11_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertEqual(r["evidence"]["expected_verdict"], "thin")

    def test_probe_m11_rejects_wrong_drift_verdict(self):
        bad = {**M11_ARTIFACT, "checks": [
            {"gate": "drift_magnitude", "verdict": "valid", "reason": "wrong"}
        ]}
        self.assertFalse(probe_M11(bad)["holds"])

    def test_probe_m13_detects_compatibility_gap_scoring(self):
        r = probe_M13(M13_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["summary_matches"])

    def test_probe_m13_rejects_route_or_tier_or_pricing_machines(self):
        self.assertFalse(probe_M13(M9_ARTIFACT)["holds"])
        self.assertFalse(probe_M13(M15_SCORE_ARTIFACT)["holds"])
        self.assertFalse(probe_M13(M6_ARTIFACT)["holds"])
        self.assertFalse(probe_M13(M10_ARTIFACT)["holds"])
        self.assertFalse(probe_M13(M2_ARTIFACT)["holds"])

    def test_probe_m14_detects_fingerprint_dedup(self):
        r = probe_M14(M14_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertEqual(r["evidence"]["duplicate_group_count"], 1)

    def test_probe_m14_rejects_bad_fingerprint(self):
        bad_items = [dict(x) for x in M14_ARTIFACT["items"]]
        bad_items[0]["fingerprint"] = "bad"
        self.assertFalse(probe_M14({**M14_ARTIFACT, "items": bad_items})["holds"])

    def test_probe_m10_requires_threshold_dimensions(self):
        r = probe_M10(M10_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertEqual(r["evidence"]["dimension_count"], 3)
        self.assertFalse(probe_M10(M2_ARTIFACT)["holds"])

    def test_probe_m9_detects_best_eligible_routing(self):
        r = probe_M9(M9_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertEqual(r["evidence"]["best_eligible"], "wind-farm-2")
        self.assertTrue(r["evidence"]["rejection_reasons_preserved"])

    def test_probe_m9_rejects_wrong_selected_candidate(self):
        bad = {**M9_ARTIFACT, "selected": "coal-3", "selected_score": 114.0}
        self.assertFalse(probe_M9(bad)["holds"])

    def test_probe_m15_detects_score_band_distribution(self):
        r = probe_M15(M15_SCORE_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["weighted_score_evidence"])
        self.assertEqual(r["evidence"]["distribution_keys"], ["high", "low", "mid"])

    def test_probe_m15_detects_rule_ladder_generalization(self):
        r = probe_M15(M15_RULE_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertTrue(r["evidence"]["rule_ladder_evidence"])

    def test_probe_m16_detects_route_deviation_rollback_simulation(self):
        r = probe_M16(M16_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertEqual(r["evidence"]["expected_decision"], "rollback")
        self.assertTrue(r["evidence"]["restored_matches"])

    def test_probe_m16_rejects_wrong_simulation_decision(self):
        bad = {**M16_ARTIFACT, "simulation": {**M16_ARTIFACT["simulation"], "decision": "clear"}}
        self.assertFalse(probe_M16(bad)["holds"])

    def test_probe_m17_detects_endowment_funding_projection(self):
        r = probe_M17(M17_ARTIFACT)
        self.assertTrue(r["holds"], r)
        self.assertEqual(r["evidence"]["expected_verdict"], "endowed")
        self.assertTrue(r["evidence"]["schedule_matches"])
        self.assertTrue(r["evidence"]["posture_matches"])

    def test_probe_m17_rejects_wrong_projection_verdict(self):
        bad = {**M17_ARTIFACT, "posture": {**M17_ARTIFACT["posture"], "verdict": "depleted"}}
        self.assertFalse(probe_M17(bad)["holds"])

    def test_compatibility_mesh_split_and_m15_cluster_agreement(self):
        cases = [
            {"id": "Ledger", "expected": ["M1"], "artifact": M1_ARTIFACT},
            {"id": "SovMesh", "expected": ["M2"], "artifact": M2_ARTIFACT},
            {"id": "PredicateGate", "expected": ["M3"], "artifact": M3_ARTIFACT},
            {"id": "Provenance", "expected": ["M4"], "artifact": M4_ARTIFACT},
            {"id": "PqcMesh", "expected": ["M2"], "artifact": M2_ARTIFACT},
            {"id": "SignalMesh", "expected": ["M2"], "artifact": M2_ARTIFACT},
            {"id": "ReserveFlow", "expected": ["M5"], "artifact": M5_ARTIFACT},
            {"id": "AgentMesh", "expected": ["M6"], "artifact": M6_ARTIFACT},
            {"id": "CryoFutures", "expected": ["M7"], "artifact": M7_ARTIFACT},
            {"id": "ShockRehearsal", "expected": ["M8"], "artifact": M8_ARTIFACT},
            {"id": "FlowMesh", "expected": ["M10"], "artifact": M10_ARTIFACT},
            {"id": "PolicyDrift", "expected": ["M11"], "artifact": M11_ARTIFACT},
            {"id": "ReleaseMesh", "expected": ["M12"], "artifact": M12_ARTIFACT},
            {"id": "CompatibilityGap", "expected": ["M13"], "artifact": M13_ARTIFACT},
            {"id": "Fingerprint", "expected": ["M14"], "artifact": M14_ARTIFACT},
            {"id": "SkyGrid", "expected": ["M9"], "artifact": M9_ARTIFACT},
            {"id": "ForgeQuarantine", "expected": ["M15"], "artifact": M15_SCORE_ARTIFACT},
            {"id": "LoopKit", "expected": ["M15"], "artifact": M15_SCORE_ARTIFACT},
            {"id": "LazarettoStage", "expected": ["M15"], "artifact": M15_SCORE_ARTIFACT},
            {"id": "DetourDesk", "expected": ["M15"], "artifact": M15_RULE_ARTIFACT},
            {"id": "FieldRoot", "expected": ["M15"], "artifact": M15_RULE_ARTIFACT},
            {"id": "RouteSentinel", "expected": ["M16"], "artifact": M16_ARTIFACT},
            {"id": "EndowFront", "expected": ["M17"], "artifact": M17_ARTIFACT},
        ]
        report = agreement_report(cases)
        self.assertEqual(report["cases"], 23)
        self.assertEqual(report["scored_claims"], 23)
        self.assertEqual(report["matched_claims"], 23)
        self.assertEqual(report["agreement"], 1.0)


if __name__ == "__main__":
    unittest.main()
