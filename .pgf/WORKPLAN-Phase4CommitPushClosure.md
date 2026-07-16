# WORKPLAN-Phase4CommitPushClosure

## Steps

1. Verify nested repos:
   - `Attestra`: `python -m unittest discover -s tests -q`, `git diff --check`
   - `Routestra`: `python -m unittest discover -s tests -q`, `git diff --check`
2. Verify root repo:
   - `python core\helix_validate.py .`
   - `python -m unittest discover -s tests -q`
   - `git diff --check`
3. Commit and push nested repos.
4. Commit and push root `HELIX`.
5. Verify pushed branch state.

## Acceptance criteria

- `Attestra/main` pushed.
- `Routestra/main` pushed.
- `HELIX/main` pushed.
- Final report includes exact commit hashes.
- Next task is exactly one CI verification task.
