# PGF HELIX System Analysis - 2026-06-17

> Scope: `D:/HELIX` 전체 시스템을 PG/PGF 방식으로 역공학 분석하고, 수정/개선/추가 사항을 실행 가능한 backlog로 정리한다.
> Method: local `skills/pg`, `skills/pgf` 로드 후 PGF `design --analyze` + 3-perspective verify 관점 적용.

## 0. Verification Snapshot

```text
Target: D:/HELIX
Local AGENTS.md: 없음
Loaded local skills:
  - D:/HELIX/skills/pg/SKILL.md
  - D:/HELIX/skills/pgf/SKILL.md

Commands:
  python -m unittest discover -s tests -q
  -> Ran 66 tests in 0.022s / OK

  python core/helix_validate.py .
  -> PASS - HELIX structure + example artifacts consistent.

  python helix.py status --json
  -> ledger_size=2, pool_size=7, diversity.triggered=false, breaches=1,
     latest winner=IDEA-018, next_action=RUN_EXPLOIT

  python -m compileall -q core engines helix.py scripts tests
  -> OK

Git status:
  M .gitignore
  - 분석 전부터 존재한 변경으로 판단. 본 분석은 해당 파일을 수정하지 않음.
```

## 1. System Gantree

```text
HELIX // explore + exploit autonomous creation helix (done-needs-hardening) @v:0.2
    HelixCore // deterministic shared backbone (done)
        Fingerprint // identity primitives (done)
        Ledger // unified reuse-prevention gate (done-needs-hardening)
        Diversity // homogenization and repair signal (done-needs-hardening)
        Provenance // lineage and winner-to-corpus base-pairing (done-needs-actuator)
        Loop // deterministic next_action policy (done)
        Validate // structure and contract validator (done-needs-schema-depth)
    HelixEngines // federated adapters for both strands (done-needs-live-run)
        ExploreAdapter // IdeaFirst artifacts -> backbone projection (done)
        ExploitAdapter // recreate artifacts -> backbone projection (done)
        Loaders // JSON/YAML artifact loading boundary (done-needs-latest-resolver)
        Unify // merge projected ledgers (done-needs-collision-merge)
    RuntimeDriver // helix.py read-only status turn (done-needs-write-actions)
    Skills // vendored AI-native skill inventory (done)
    Schemas // JSON Schema contracts (done-passive)
    Docs // README/RUNBOOK/MIGRATION/ARCHITECTURE/CONTRACT (done-needs-status-sync)
    Tests // deterministic helper tests (done)
```

## 2. Architectural Finding

HELIX의 큰 구조는 타당하다. `core/`가 ledger, diversity, provenance, loop를 단일 출처로 잡고, `engines/`는 각 엔진의 native artifact를 백본 구조로 투영한다. 이 설계는 "federate, not fuse" 원칙과 맞고, 현재 테스트/검증도 통과한다.

하지만 현재 완성도는 **read-only control plane + deterministic substrate**에 가깝다. 실제 연속생산 시스템으로 올라가려면 `next_action`을 보여주는 것에서 끝나지 않고, `RECORD_CONSUMED`, `winner->corpus`, `REFRESH_INPUTS`, live artifact resolution을 실제 파일 상태로 닫는 actuator 층이 필요하다.

## 3. Priority Backlog

### P0-1. CloseLoopActuator 추가

문제:
- `core/helix_loop.next_action()`은 `RECORD_CONSUMED`를 최우선으로 설계했지만, `helix.py status`는 read-only라 실제 ledger append나 corpus feedback write를 수행하지 않는다.
- `build_report()`는 `pending_implemented_winner=False`를 고정한다. 구현 이벤트가 들어와도 현재 CLI 경로에서는 루프 폐쇄가 발생하지 않는다.

수정:
- `helix.py`에 `record-consumed` 또는 `close-loop` command 추가.
- 입력: implemented winner JSON, implementation metadata, target ledger path, optional corpus path.
- 동작: `evx_winner_to_consumed_entry()` -> `append_consumed()` -> `winner_to_corpus_entry()` -> exploit corpus append.
- 실패 조건: implementation 없음, 이미 consumed, corpus entry project 누락.

```python
def close_loop(explore_winner: dict, source_chain: dict, implementation: dict,
               ledger_path: str, corpus_path: str, now: str) -> dict:
    entry = evx_winner_to_consumed_entry(
        winner=explore_winner,
        source_chain=source_chain,
        implementations=[implementation],
    )
    ledger = load_ledger(ledger_path)
    if is_consumed(entry, ledger)["consumed"]:
        return {"status": "already_recorded"}
    ledger = append_consumed(ledger, entry, now=now)
    corpus_entry = winner_to_corpus_entry(entry)
    append_corpus_entry(corpus_path, corpus_entry)
    save_ledger(ledger_path, ledger)
    return {"status": "closed", "corpus_entry": corpus_entry}
    # acceptance_criteria:
    #   - implemented winner only
    #   - ledger and corpus both updated atomically enough for local files
    #   - rerun is idempotent
```

### P0-2. DiversityRepairSemantics 정정

문제:
- `measure_diversity()`는 `unique_ratio_below_floor`를 signals에만 넣고 `triggered` 계산에는 포함하지 않는다.
- recreate 쪽 island re-divergence 신호가 단독으로 발생해도 `next_action()`은 `REFRESH_INPUTS`를 실행하지 않는다.
- 예제에서도 `keyword_coverage=1.0`이 항상 breach가 되는데, pool size 7에서 top-k=10이면 지표가 과민할 수 있다.

수정:
- report에 `repair_required`를 추가하거나, policy로 `unique_ratio_below_floor`를 trigger에 포함.
- `keyword_coverage(pool, k=10)`는 작은 pool에서 top-k가 pool vocabulary를 거의 덮는 문제를 완화. 예: `k=min(10, max(3, int(sqrt(vocab_size))))` 또는 `min_pool_for_keyword_signal`.

```python
def diversity_repair_required(report: dict, policy: dict) -> bool:
    if report["breaches"] >= report["thresholds"]["min_breaches"]:
        return True
    if policy.get("unique_ratio_triggers_repair", True):
        return report["signals"].get("unique_ratio_below_floor", False)
    return False
    # acceptance_criteria:
    #   - recreate unique_ratio collapse cannot be ignored
    #   - existing IdeaFirst 4-threshold behavior remains configurable
```

### P1-1. LedgerMergeCollision 강화

문제:
- `engines/unify.py::merge_ledgers()`는 dedup 기준이 `idea_id or title`뿐이다.
- HELIX ledger의 실제 match contract는 `idea_id`, `normalized_title`, `aliases`, `semantic_family`, `source_fingerprint`, `generated_fingerprint`이다.
- 따라서 다른 `idea_id`를 가진 cross-engine duplicate가 병합 후 중복 entry로 남을 수 있다.

수정:
- merge 중 새 entry를 candidate로 변환해 기존 merged ledger의 `is_consumed()`로 검사.
- match가 있으면 duplicate를 drop하거나 `aliases/source_chain/implementations`를 merge하는 deterministic policy를 둔다.

```python
def merge_ledgers_by_contract(*ledgers) -> dict:
    merged = empty_ledger()
    for ledger in ledgers:
        for entry in ledger.get("consumed", []):
            if is_consumed(entry, merged)["consumed"]:
                merged = merge_duplicate_entry(merged, entry)
            else:
                merged["consumed"].append(dict(entry))
                reindex_ledger(merged)
    return reindex_ledger(merged)
```

### P1-2. LiveArtifactResolver 추가

문제:
- `engines/loaders.py`는 `.evx/latest/...`, `.cix/latest/...` 또는 root fixture 파일만 찾는다.
- 실제 run 디렉터리 구조가 latest symlink/copy를 항상 보장하지 않으면 live-run이 실패한다.

추가:
- `.evx/*/manifest`, `.cix/*/idea_pool`, `.recreate/runs/*`에서 최신 manifest를 선택하는 resolver.
- selection rule은 deterministic이어야 한다. 예: manifest timestamp 우선, 없으면 path lexicographic max.

### P1-3. SemanticSimInjection 경로 연결

문제:
- `measure_diversity(..., sim=...)` API는 좋지만 CLI/adapter에서 semantic sim 주입 경로가 없다.
- 현재 `helix.py status`는 lexical only라 README의 "semantic grade-up"이 실제 운영 CLI로 이어지지 않는다.

추가:
- `helix.py status --sim lexical|module:function`.
- 외부 embedding은 core 밖에서만 호출. core에는 callable만 전달.

### P2-1. SchemaValidator 깊이 강화

문제:
- `schemas/*.json`은 존재하지만 `helix_validate.py`는 JSON Schema 전체를 검증하지 않고 수동 subset만 확인한다.
- `winner_to_corpus_entry()`는 `project=None`도 반환할 수 있는데, schema의 required만으로는 non-empty 검증이 약하다.

수정:
- stdlib-only 원칙을 유지하려면 schema 전체 구현 대신 프로젝트 전용 validator를 명시적으로 확장.
- `validate_corpus_entry()`, `validate_loop_state()`, `validate_thresholds()` 추가.

### P2-2. CalibrationHarness 추가

문제:
- `docs/CALIBRATION.md`에는 보정 절차가 PPR로만 있다.
- 실제 history를 넣어 threshold 후보를 산출하는 deterministic script가 없다.

추가:
- `scripts/calibrate_diversity.py`.
- 입력: rounds JSONL, target_trigger_rate, metric kind.
- 출력: thresholds JSON + evidence summary.

### P3-1. StatusDocsSync

문제:
- `.pgf/status-HELIX.json`에는 `unittests: "64 passed"`라고 되어 있으나 현재 실측은 66 tests OK이다.

수정:
- status 문서와 README/RUNBOOK 검증 예시를 현재 테스트 수와 맞춘다.
- 또는 테스트 수를 문서에 고정하지 말고 "unittest discover OK"로 기록한다.

## 4. Suggested PGF Workplan

```text
ImproveHELIX // read-only control plane -> operational closed loop (in-progress) @v:0.3
    CloseLoopActuator // ledger append + corpus feedback writer (designing) #P0
        # input: implemented winner + source_chain + implementation + now
        # output: updated ledger + corpus entry
        # criteria: idempotent rerun, no append without implementation
    DiversityRepairSemantics // unique_ratio and small-pool repair semantics (designing) #P0
        # input: diversity report + policy
        # output: repair_required bool + target
        # criteria: unique_ratio collapse cannot be silently ignored
    LedgerMergeCollision // merge by full HELIX match contract (designing) #P1
        # input: projected explore/exploit ledgers
        # output: deduped unified ledger
        # criteria: collisions by alias/family/fingerprint merged or audited
    LiveArtifactResolver // latest run discovery without latest pointer (designing) #P1
        # criteria: deterministic latest selection
    SemanticSimInjection // CLI hook for external semantic sim (designing) #P1
        # criteria: core remains stdlib; sim called only outside core
    SchemaValidator // project-specific contract validation (designing) #P2
        # criteria: corpus entry project non-empty, loop action valid, thresholds sane
    CalibrationHarness // executable threshold calibration (designing) #P2
        # criteria: deterministic thresholds from history
    StatusDocsSync // measured test count/status sync (designing) #P3
        # criteria: docs do not drift from verification commands
```

## 5. Recommended Next Edit Order

1. Implement `CloseLoopActuator` first. This turns HELIX from analyzer/status reporter into an actual closed-loop controller.
2. Fix `DiversityRepairSemantics` next. Without this, exploit-side collapse can be visible but non-actionable.
3. Harden `LedgerMergeCollision`. This protects the single-source ledger promise.
4. Add `LiveArtifactResolver` and `SemanticSimInjection` for real operating runs.
5. Expand validators and calibration tooling after the loop is operational.

## 6. Final Verdict

```text
Current state: PASS as deterministic substrate + status/reporting loop.
Main gap: actuator layer missing for actual ledger/corpus mutation.
Risk level: Medium. Architecture is sound, but "closed loop" is partly declarative until close-loop writes exist.
Best next release target: HELIX v0.3 = operational closed-loop controller.
```
