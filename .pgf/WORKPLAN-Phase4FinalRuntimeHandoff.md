# WORKPLAN-Phase4FinalRuntimeHandoff

## Steps

1. Confirm Phase4 status and latest closeout reports.
2. Confirm current validation state.
3. Capture dirty worktree context without modifying unrelated files.
4. Write `_workspace/runtime-handoff-HELIXCorpusPhase4.md`.
5. Update PGF status/verify artifacts.
6. Re-run JSON validity, HELIX validator, full unittest suite, and diff hygiene.

## Acceptance criteria

- Handoff file exists on disk.
- Handoff includes read order, what is done, verified commands, dirty/untracked state warning, and exactly one next task.
- `.pgf/status-HELIXCorpusPhase4.json` no longer points to handoff creation as next task.
- `python core/helix_validate.py .` passes.
- `python -m unittest discover -s tests -q` passes.
- `git diff --check` passes.
