import copy,json,os,subprocess,sys,tempfile,unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SRC=os.path.join(ROOT,"src"); sys.path.insert(0,SRC)
from driftisolator import *  # noqa: E402,F403
from driftisolator.samples import sample_case  # noqa: E402


class DriftIsolatorTests(unittest.TestCase):
    def test_baseline_digest_stable(self): self.assertEqual(baseline_digest({"a":1},{"b":2}),baseline_digest({"a":1},{"b":2}))
    def test_set_event(self): self.assertEqual("b",apply_event({"x":"a"},{"event_id":"1","op":"set","path":"x","value":"b"})["x"])
    def test_increment_event(self): self.assertEqual(3,apply_event({"n":1},{"event_id":"1","op":"increment","path":"n","value":2})["n"])
    def test_append_event(self): self.assertEqual([1],apply_event({"a":[]},{"event_id":"1","op":"append","path":"a","value":1})["a"])
    def test_invalid_op(self):
        with self.assertRaises(ValueError): apply_event({}, {"event_id":"1","op":"eval","path":"x","value":1})
    def test_replay_does_not_mutate_input(self):
        state={"x":1}; replay(state,[{"event_id":"1","op":"set","path":"x","value":2}]); self.assertEqual({"x":1},state)
    def test_isolates_single_culprit(self):
        r=isolate(sample_case()); self.assertEqual("ISOLATED",r["decision"]); self.assertEqual(["e3"],[e["event_id"] for e in r["minimal_events"]]); self.assertTrue(r["one_minimal"])
    def test_no_drift(self): self.assertEqual("NO_DRIFT",isolate(sample_case("no-drift"))["decision"])
    def test_invalid_baseline(self): self.assertEqual("INVALID",isolate(sample_case("invalid-baseline"))["decision"])
    def test_invalid_event(self):
        c=sample_case(); c["events"][0]["op"]="exec"; self.assertEqual("INVALID",isolate(c)["decision"])
    def test_receipt_deterministic_and_replayable(self):
        c=sample_case(); r=isolate(c); self.assertEqual(r,isolate(c)); self.assertTrue(verify_receipt(c,r)); r["decision"]="INVALID"; self.assertFalse(verify_receipt(c,r))
    def test_shrink_generic(self): self.assertEqual([3],shrink([1,2,3,4],lambda rows:3 in rows))
    def test_ledger_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,"l.jsonl"); append_receipt(p,isolate(sample_case()),"2026-07-15T23:00:00+09:00"); self.assertEqual([],verify_ledger(p)); self.assertEqual(1,ledger_report(p)["isolated"])
    def test_ledger_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,"l.jsonl"); append_receipt(p,isolate(sample_case()),"2026-07-15T23:00:00+09:00")
            with open(p,encoding="utf-8") as h: e=json.load(h)
            e["receipt"]["decision"]="NO_DRIFT"
            with open(p,"w",encoding="utf-8") as h: json.dump(e,h); h.write("\n")
            self.assertTrue(verify_ledger(p))
    def test_cli_invalid_exit(self):
        env=dict(os.environ,PYTHONPATH=SRC)
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,"c.json")
            with open(p,"w",encoding="utf-8") as handle: json.dump(sample_case("invalid-baseline"),handle)
            run=subprocess.run([sys.executable,"-m","driftisolator","run",p],cwd=ROOT,env=env,capture_output=True,text=True); self.assertEqual(2,run.returncode)


if __name__=="__main__": unittest.main()
