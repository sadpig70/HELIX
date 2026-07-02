import json
import os
import tempfile
import unittest

import tests._path  # noqa: F401
from engines.unify import merge_ledgers, build_unified_ledger
from engines.explore import adapter as EX
from engines.exploit import adapter as XP
from core.helix_ledger import is_consumed
import helix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


class TestUnify(unittest.TestCase):
    def setUp(self):
        self.explore = EX.consumed_yaml_to_ledger(
            _load("examples", "explore_state", "consumed_ideas.json"))
        self.exploit = XP.registry_to_ledger(
            _load("examples", "exploit_state", "registry.json"))

    def test_merge_unions_both_origins(self):
        merged = build_unified_ledger(self.explore, self.exploit)
        origins = {e["origin"] for e in merged["consumed"]}
        self.assertEqual(origins, {"explore", "exploit"})
        self.assertEqual(len(merged["consumed"]), 2)

    def test_merge_dedups_by_idea_id(self):
        merged = merge_ledgers(self.explore, self.explore)  # same ledger twice
        self.assertEqual(len(merged["consumed"]), 1)

    def test_merged_indexes_detect_both(self):
        merged = build_unified_ledger(self.explore, self.exploit)
        self.assertTrue(is_consumed({"title": "AgentPACT"}, merged)["consumed"])
        self.assertTrue(is_consumed({"title": "WithheldActionWitness"}, merged)["consumed"])

    def test_merge_deterministic(self):
        a = build_unified_ledger(self.explore, self.exploit)
        b = build_unified_ledger(self.explore, self.exploit)
        self.assertEqual(a, b)


class TestDriver(unittest.TestCase):
    def test_build_report_over_fixtures(self):
        r = helix.build_report()  # defaults to examples/
        self.assertEqual(r["ledger_origins"], {"explore": 1, "exploit": 1})
        self.assertEqual(r["pool_size"], 4 + 3)  # 4 explore ideas + 3 exploit candidates
        # the explore winner (IDEA-018) is fresh -> not yet consumed
        self.assertFalse(r["winner"]["already_consumed"])
        # AgentPACT is an implemented explore winner -> base-pairing feedback to corpus
        self.assertTrue(any(c["project"] == "AgentPACT" for c in r["corpus_feedback"]))
        # corpus has matured (exploit entry + AgentPACT fed back) and last engine was
        # explore -> the loop recombines via exploit (compound), not re-explore.
        self.assertEqual(r["next_action"]["action"], "RUN_EXPLOIT")

    def test_report_deterministic(self):
        self.assertEqual(helix.build_report(), helix.build_report())

    def test_build_report_handback_gate_zero_on_fixtures(self):
        r = helix.build_report()
        self.assertEqual(r["handback_gate"],
                         {"checked": 0, "passed": 0, "excluded": 0})

    def test_build_report_handback_gate_with_packets(self):
        from ActionHandbackVerifier.samples import VALID_PACKET, BREACH_PACKET
        with tempfile.TemporaryDirectory() as d:
            _write_json(os.path.join(d, ".recreate", "registry.json"), {
                "schema_version": "1.0",
                "generated_projects": {
                    "ValidProject": {
                        "created_by_run": "001",
                        "status": "implemented",
                        "implementation_path": "valid",
                        "consumed_sources": ["A"],
                        "handback": VALID_PACKET,
                    },
                    "BreachedProject": {
                        "created_by_run": "002",
                        "status": "implemented",
                        "implementation_path": "breached",
                        "consumed_sources": ["B"],
                        "handback": BREACH_PACKET,
                    },
                },
                "blocked_names": [],
                "source_fingerprints": {},
                "generated_fingerprints": {}
            })
            r = helix.build_report(exploit_root=d)
        self.assertEqual(r["handback_gate"],
                         {"checked": 2, "passed": 1, "excluded": 1})
        # only the valid project made it into the unified ledger
        self.assertEqual(r["ledger_origins"]["exploit"], 1)

    def test_verify_handback_persists_verdict(self):
        from ActionHandbackVerifier.samples import VALID_PACKET
        with tempfile.TemporaryDirectory() as d:
            reg_path = os.path.join(d, "registry.json")
            pkt_path = os.path.join(d, "handback.json")
            _write_json(reg_path, {
                "schema_version": "1.0",
                "generated_projects": {
                    "TestProject": {
                        "status": "implemented",
                        "implementation_path": "test",
                        "consumed_sources": ["A"],
                    }
                },
                "blocked_names": [], "source_fingerprints": {}, "generated_fingerprints": {}
            })
            _write_json(pkt_path, VALID_PACKET)
            result = helix.verify_handback(reg_path, "TestProject", pkt_path)
            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["verdict"], "valid")
            self.assertTrue(result["persisted"])
            # re-read registry: verdict persisted
            with open(reg_path, encoding="utf-8") as f:
                reg = json.load(f)
            self.assertEqual(reg["generated_projects"]["TestProject"]["handback_verdict"], "valid")

    def test_verify_handback_breach_returns_nonzero_cli(self):
        import subprocess
        import sys
        from ActionHandbackVerifier.samples import BREACH_PACKET
        with tempfile.TemporaryDirectory() as d:
            reg_path = os.path.join(d, "registry.json")
            pkt_path = os.path.join(d, "handback.json")
            _write_json(reg_path, {
                "schema_version": "1.0",
                "generated_projects": {
                    "TestProject": {
                        "status": "implemented",
                        "implementation_path": "test",
                        "consumed_sources": ["A"],
                    }
                },
                "blocked_names": [], "source_fingerprints": {}, "generated_fingerprints": {}
            })
            _write_json(pkt_path, BREACH_PACKET)
            proc = subprocess.run(
                [sys.executable, "helix.py", "verify-handback",
                 "--registry", reg_path, "--project", "TestProject", "--packet", pkt_path],
                cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            result = json.loads(proc.stdout)
            self.assertEqual(result["verdict"], "breach")
            # breach still persisted so the reader excludes it next turn
            with open(reg_path, encoding="utf-8") as f:
                reg = json.load(f)
            self.assertEqual(reg["generated_projects"]["TestProject"]["handback_verdict"], "breach")

    def test_live_exploit_run_status_balances_back_to_explore(self):
        with tempfile.TemporaryDirectory() as d:
            _write_json(os.path.join(d, ".recreate", "registry.json"), {
                "schema_version": "1.0",
                "generated_projects": {
                    "ActionHandbackVerifier": {
                        "created_by_run": "001-action-handback-verifier",
                        "status": "implemented",
                        "implementation_path": "ActionHandbackVerifier/",
                        "consumed_sources": ["CustodyRelayDocket", "DelegationUnderwriter"],
                        "source_fingerprint": "CustodyRelayDocket+DelegationUnderwriter",
                    }
                },
                "blocked_names": ["ActionHandbackVerifier"],
                "source_fingerprints": {
                    "CustodyRelayDocket+DelegationUnderwriter": {
                        "project": "ActionHandbackVerifier",
                        "run_id": "001-action-handback-verifier"
                    }
                },
                "generated_fingerprints": {}
            })
            _write_json(os.path.join(d, ".recreate", "latest.json"), {
                "latest_run_path": ".recreate/runs/001-action-handback-verifier",
                "winner": "ActionHandbackVerifier"
            })
            _write_json(os.path.join(d, ".recreate", "runs", "001-action-handback-verifier", "status.json"), {
                "run_id": "001-action-handback-verifier",
                "phase": "implemented",
                "winner": "ActionHandbackVerifier",
                "implementation_path": "ActionHandbackVerifier/"
            })
            _write_json(os.path.join(d, ".recreate", "runs", "001-action-handback-verifier", "candidates.json"), [
                {"name": "ActionHandbackVerifier", "target_domain": "agentops",
                 "single_question": "Is a handback valid?"}
            ])

            r = helix.build_report(exploit_root=d)

        self.assertEqual(r["latest_exploit_run"]["phase"], "implemented")
        self.assertEqual(r["latest_exploit_run"]["winner"], "ActionHandbackVerifier")
        self.assertEqual(r["ledger_origins"], {"explore": 1, "exploit": 1})
        self.assertEqual(r["pool_size"], 4 + 1)
        self.assertEqual(r["next_action"]["action"], "RUN_EXPLORE")

    def _winner(self):
        return _load("examples", "explore_state", "stage6_final.json")["consensus_winner"]

    def test_close_loop_without_packet_backward_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.json")
            corpus_path = os.path.join(d, "corpus.json")
            result = helix.close_loop(
                explore_winner=self._winner(),
                source_chain={"cix": "CIX-1"},
                implementation={"project_name": "TestProj", "project_path": "test"},
                ledger_path=ledger_path, corpus_path=corpus_path,
                now="2026-07-02T00:00:00+00:00")
            self.assertEqual(result["status"], "closed")
            self.assertNotIn("handback", result)

    def test_close_loop_with_valid_handback(self):
        from ActionHandbackVerifier.samples import VALID_PACKET
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.json")
            corpus_path = os.path.join(d, "corpus.json")
            pkt_path = os.path.join(d, "handback.json")
            _write_json(pkt_path, VALID_PACKET)
            result = helix.close_loop(
                explore_winner=self._winner(),
                source_chain={"cix": "CIX-1"},
                implementation={"project_name": "TestProj", "project_path": "test"},
                ledger_path=ledger_path, corpus_path=corpus_path,
                now="2026-07-02T00:00:00+00:00",
                packet_path=pkt_path)
            self.assertEqual(result["status"], "closed")
            self.assertEqual(result["handback"]["verdict"], "valid")
            ledger = helix.load_ledger(ledger_path)
            self.assertEqual(ledger["consumed"][0]["handback_verdict"], "valid")

    def test_close_loop_with_breach_handback_aborts(self):
        from ActionHandbackVerifier.samples import BREACH_PACKET
        with tempfile.TemporaryDirectory() as d:
            ledger_path = os.path.join(d, "ledger.json")
            corpus_path = os.path.join(d, "corpus.json")
            pkt_path = os.path.join(d, "handback.json")
            _write_json(pkt_path, BREACH_PACKET)
            result = helix.close_loop(
                explore_winner=self._winner(),
                source_chain={"cix": "CIX-1"},
                implementation={"project_name": "TestProj", "project_path": "test"},
                ledger_path=ledger_path, corpus_path=corpus_path,
                now="2026-07-02T00:00:00+00:00",
                packet_path=pkt_path)
            self.assertEqual(result["status"], "handback_breach")
            self.assertEqual(result["handback"]["verdict"], "breach")
            # nothing was written
            ledger = helix.load_ledger(ledger_path)
            self.assertEqual(len(ledger["consumed"]), 0)


if __name__ == "__main__":
    unittest.main()
