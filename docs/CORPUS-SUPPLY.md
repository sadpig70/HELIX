# HELIX Corpus Supply Plane v1

HELIX의 신규 corpus 공급 기반이다. 생성 재료의 폭과 플랫폼 판정 근거의 신뢰도를 서로
오염시키지 않기 위해 두 admission tier를 독립 receipt로 기록한다.

```text
structurally valid manifest
    -> immutable revision snapshot
    -> Generative admission receipt
    -> implementation/evidence revision
    -> human review bound to manifest hash
    -> Evidence promotion receipt
```

`Evidence ADMITTED`는 `CONDENSE` 승인이 아니다. Condense 근거 수와 machine routing 권위는
계속 `core/helix_condense.py`와 evaluation plane에 있다.

## Contracts

- `schemas/corpus-manifest.schema.json`: identity, origin, character, genes, machine hypothesis,
  verification, safety and provenance.
- `schemas/corpus-review-receipt.schema.json`: human approval bound to one manifest SHA-256.
- `schemas/corpus-admission-receipt.schema.json`: append-only Generative/Evidence decision event.
- `seed/corpus/policy.json`: fail-closed v1 authority and non-Condense boundary.

Changed manifests require a monotonically increasing `revision`. Every revision is preserved at
`items/{corpus_id}/revisions/{revision}.json`; `items/{corpus_id}/manifest.json` is the latest
materialized pointer. Evidence revisions bind the prior Generative manifest with
`supersedes_manifest_sha256`.

## Evidence truth

Admission requires `--evidence-root`. `origin.source_evidence` and
`origin.license_evidence` are relative paths under that root. The core hashes the actual bytes and
compares them to the manifest. Absolute paths and root escapes are rejected.

The deterministic core does not clone repositories, call networks, run AI, or read wall-clock time.
Repository discovery and characterization remain meta-layer work; `--now` is injected.

## CLI

```bash
python helix.py corpus validate --manifest candidate.json
python helix.py corpus intake --manifest candidate.json --root seed/corpus
python helix.py corpus fingerprint --id HC-2026-0001 --root seed/corpus

python helix.py corpus admit --id HC-2026-0001 \
  --root seed/corpus --evidence-root .helix/corpus-cache/HC-2026-0001 \
  --now 2026-07-15T10:00:00+09:00

python helix.py corpus promote --id HC-2026-0001 --review human-review.json \
  --root seed/corpus --evidence-root .helix/corpus-cache/HC-2026-0001 \
  --now 2026-07-15T11:00:00+09:00

python helix.py corpus verify-ledger --root seed/corpus
python helix.py corpus status --root seed/corpus
python helix.py corpus health --root seed/corpus

# Preview only: emits no admission event.
python helix.py corpus migrate --legacy-list seed/corpus/project_list.md

# Emit structurally valid but deliberately unverified migration candidates.
python helix.py corpus migrate --legacy-list seed/corpus/project_list.md \
  --out .helix/corpus-migration
```

Exit codes: `0` success/admitted, `2` usage error, `4` invalid/quarantined/tampered.

## CI enforcement

The repository CI keeps this plane from drifting away from its committed corpus
state. On every push and pull request it now enforces:

```bash
python helix.py corpus verify-ledger --root seed/corpus
python helix.py corpus health --root seed/corpus
python scripts/corpus/phase3_registry.py validate \
  --registry seed/corpus/phase3-2026-01-experiments.json \
  --corpus-root seed/corpus
git status --short
```

The first two checks bind the append-only corpus ledger and current health
summary. The Phase 3 registry check keeps the frozen six-cycle plan tied to the
current corpus manifests, evidence baseline, lead verbs and domain-distance
policy. The final clean-tree gate fails CI if tests or validators leave generated
artifacts behind. This means corpus supply changes are accepted only when the
ledger, health summary, Phase 3 plan and workspace hygiene all remain
reproducible from tracked files.

## Fixed 24-item pilot

Phase 2 uses a frozen registry so failed candidates cannot be replaced after results are known. The
source mix is `external OSS 8 / HELIX generated 6 / operational problem 4 / failure 3 / research 3`.

```bash
# Create once. The command refuses to overwrite an existing registry.
python scripts/corpus/pilot_registry.py init \
  --out _workspace/corpus-pilot/registry.json

python scripts/corpus/pilot_registry.py validate \
  --registry _workspace/corpus-pilot/registry.json

# Build compact evidence from a checkout pinned to one revision.
python scripts/corpus/build_snapshot.py \
  --source .helix/corpus-worktrees/HC-PILOT-EXT-001 \
  --revision <commit-sha> \
  --out seed/corpus/sources/external_oss/HC-PILOT-EXT-001/source.snapshot.json

# Read ledger truth and emit the Phase 2 gate report.
python scripts/corpus/pilot_report.py \
  --registry _workspace/corpus-pilot/registry.json \
  --corpus-root seed/corpus \
  --out _workspace/corpus-pilot/pilot-report.json \
  --markdown _workspace/corpus-pilot/pilot-report.md
```

The registry fixes IDs, class counts, target tier and candidate identity (`locator + revision`).
Source acquisition, characterization and reproduction may run in parallel. `intake`, `admit` and
`promote` remain a serialized single-writer queue.

The report derives admission state from the hash-chained ledger rather than editable registry
status. `READY_FOR_PHASE_3` requires 24 structurally valid and provenance-bound manifests, at least
12 Generative admissions, at least 5 Evidence admissions, a valid ledger, recorded quarantine
reasons and a 24-item diversity baseline.

### Human authority points

Automation stops at two points:

1. A human chooses and freezes the actual 24 candidates. This is a scope/rights judgment, not a
   deterministic calculation.
2. A human inspects reproduction evidence and signs each Evidence review receipt. An automated or
   AI-authored approval is invalid.

The operator may reject a candidate or promotion. Rejection is retained in the frozen slot; it is
not repaired by substituting an easier candidate.

## Operator runbook

Use this order when adding or promoting corpus material. Steps 1-3 may be prepared in parallel,
but steps 4-8 are a serialized single-writer queue because they can append to the admission ledger.

1. **Acquire outside the deterministic core.** Clone or otherwise collect the source in a meta-layer
   workspace such as `.helix/corpus-worktrees/{corpus_id}`. Pin the exact revision or immutable
   artifact used for the manifest.
2. **Build evidence bytes.** Store compact source/license evidence under a dedicated evidence root,
   for example `.helix/corpus-cache/{corpus_id}`. Manifest paths must be relative to that root.
3. **Write or revise the manifest.** Increase `revision` monotonically for any changed manifest.
   For Evidence promotion revisions, set `supersedes_manifest_sha256` to the prior Generative
   manifest hash.
4. **Validate without mutation.**
   ```bash
   python helix.py corpus validate --manifest candidate.json
   ```
5. **Intake the immutable revision.**
   ```bash
   python helix.py corpus intake --manifest candidate.json --root seed/corpus
   python helix.py corpus fingerprint --id {corpus_id} --root seed/corpus
   ```
6. **Admit Generative material.** This appends one ledger event if the manifest and evidence bytes
   pass the hard gate.
   ```bash
   python helix.py corpus admit --id {corpus_id} --root seed/corpus \
     --evidence-root .helix/corpus-cache/{corpus_id} --now <iso8601>
   ```
7. **Promote Evidence only after human review.** The review receipt must bind the current manifest
   SHA-256 and use `verdict: "approved"`. A rejected or mismatched review intentionally records
   quarantine instead of being silently repaired.
   ```bash
   python helix.py corpus promote --id {corpus_id} --review human-review.json \
     --root seed/corpus --evidence-root .helix/corpus-cache/{corpus_id} \
     --now <iso8601>
   ```
8. **Close with the same checks as CI.**
   ```bash
   python helix.py corpus verify-ledger --root seed/corpus
   python helix.py corpus health --root seed/corpus
   python scripts/corpus/phase3_registry.py validate \
     --registry seed/corpus/phase3-2026-01-experiments.json \
     --corpus-root seed/corpus
   git status --short
   ```

### Failure handling

- `validate` failures are pre-admission defects. Fix the candidate file before intake.
- `intake` with an existing revision is not a reason to overwrite history. Create the next revision
  when the manifest changed.
- `admit` or `promote` exit code `4` means the decision is invalid, quarantined or tampered. Inspect
  `reasons`, keep the ledger event, and repair only by creating a new manifest/review revision.
- If `verify-ledger` reports a problem, stop all writes. Do not edit or truncate
  `seed/corpus/evidence/admission-ledger.jsonl`; recover from version control or a known-good copy,
  then replay only verifiable operations.
- Quarantine is evidence, not a dirty state. The fixed pilot keeps the slot and records the reason;
  it must not be replaced by an easier candidate.

## v1 boundaries

- Single writer ledger. Each append uses `flush+fsync`; the full chain is verified before and after.
- No automatic GitHub collection or checkout.
- No AI-generated characterization inside deterministic core.
- No automatic platform or pack creation.
- Legacy migration never fabricates license, safety, reproduction, or machine evidence.
