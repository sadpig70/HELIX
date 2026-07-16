# DESIGN-Phase4FinalRuntimeHandoff

## Gantree

```text
Phase4FinalRuntimeHandoff // durable transfer packet for Phase4 corpus supply closure
    SourceState // read Phase4 status, closeout, public docs sync, git status (done)
    HandoffArtifact // write exact read order, verified state, dirty tree context, next task (done)
    PGFClosure // update status and verification artifacts (done)
    Verification // json validity, validator, unittest, diff hygiene (needs-verify)
```

## PPR

```text
def phase4_final_runtime_handoff(state, validation, git_status) -> Handoff:
    assert state["HELIXCorpusPhase4"].phase == "complete"
    assert state["HELIXCorpusPhase4"].verify_status == "passed"
    assert validation["helix_validate"] == "PASS"
    return save("_workspace/runtime-handoff-HELIXCorpusPhase4.md", {
        "read_order": [...],
        "done": state.phase4_completed_batches,
        "verified": validation,
        "dirty_tree": git_status.summary,
        "next_task": "commit and push Phase4 corpus supply closure changes",
    })
```

## Boundary

This task creates a transfer artifact only. It does not stage, commit, push, rewrite root `HANDOFF.md`, or change platform/runtime logic.
