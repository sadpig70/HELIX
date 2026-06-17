# INSTRUCTION (LOOP) — autonomous continuous HELIX factory (explore↔exploit closed loop)

> **장시간 무중단 자율 에이전트용 폐루프.** 1회 턴 사양은 [`INSTRUCTIONS-helix-fullcycle.md`](./INSTRUCTIONS-helix-fullcycle.md)(이하 **BASE**)를
> 그대로 쓰고, 이 문서는 그것을 **inner turn**으로 호출해 turn N → N+1 → … 를 **정지 조건까지 무중단 반복**한다.
> HELIX의 폐루프는 곧 `core/helix_loop.next_action`이 매 턴 explore↔exploit를 번갈고(RECORD_CONSUMED·REFRESH_INPUTS 우선),
> 구현된 explore winner를 코퍼스로 환류(염기쌍)해 **수렴 없이 복리로 도는 나선**이다. **BASE/skills/core는 수정하지 않는다.**
>
> 설계 원칙: ① 모든 상태는 파일(`.helix/ledger.json` + `.helix/loop/` + 백본 `helix.py status`)에서 **매 turn 재로딩**(하드코딩 금지)
> ② 한 turn의 실패가 루프·누적 상태를 오염시키지 않음(격리·롤백, close-loop idempotency) ③ 능력↑ 시 깊이·폭 **자동 확장**
> ④ 되돌리기 어려운 외부 행위는 게이트 통과 후에만 + 가드레일.

---

## 0. 환경·규약
BASE §0과 동일(루트=HELIX, `skills/{pg,pgf,...}`·`core/`·`helix.py`, UTF-8, 결정론 경계, wall-clock은 CLI 엣지만).
추가: 루프는 PG/PGF의 loop 정신을 따른다 — 매 turn 후 `.helix/loop/loop-state.json` 체크포인트, 런타임의 지속수단(hook/heartbeat/scheduler/manual continuation)으로 다음 turn 재진입.

## 1. 루프 아키텍처 (outer loop = factory)

```text
HelixFactoryLoop // explore⊕exploit 무중단 생산 나선 (in-progress) @v:1.0
    InitOrResume // loop-state 로드(없으면 생성) + 미완 run 복구·격리
    while not should_stop(state, policy):
        LoadState        // python helix.py status --json → next_action·diversity·ledger·corpus_feedback
        Steer            // coverage 히스토그램(explore/exploit·archetype·layer·domain) → 편중축 보정
        RunTurn          // = BASE 한 턴 (next_action 따라 explore|exploit|refresh|record), 통합 ledger 게이트
        CloseLoop        // python helix.py close-loop (구현 winner → ledger append + corpus 환류; idempotent)
        Gate&Publish     // GATE-EVIDENCE 전부 passed만 공개(아니면 seed-only); rate-limit
        RecordOutcome    // loop-state 갱신 + coverage 재계산 + heartbeat
        MaybeEvolve      // 매 M회: calibrate + 정책 자기수정(policy 한정)
        Reenter          // 런타임 지속수단으로 다음 turn 재진입
    Finalize // loop-report.md + status=stopped
```
핵심: **RunTurn 본체는 BASE 전체를 1회 수행**(여기서 재정의 금지). 루프는 그 바깥의 제어·상태·안전·진화 계층이다.
HELIX는 strand 선택을 백본 `next_action`에 위임하므로, 루프는 그 결정을 따르고 coverage/공개만 통제한다.

## 2. 루프 상태 파일 — `.helix/loop/loop-state.json`

```jsonc
{
  "loop_id": "loop-<seq>",                 // timestamp 금지; 시퀀스
  "status": "active|paused|stopped",
  "started_at": "<date injected>",
  "turn": 0,                                // 완료한 turn 수
  "last_next_action": null,                 // 직전 turn의 next_action (균형 추적)
  "strand_counts": {"explore":0,"exploit":0},
  "current_turn_id": null,                  // 진행 중 turn (없으면 null)
  "pending_run_path": null,                 // 미완 run/pgf 경로(복구 대상)
  "completed_this_loop": [],                // 이 루프가 만든 turn_id·winner
  "consecutive_failures": 0,
  "consecutive_dry": 0,
  "publish_window_id": "<injected-date>",   // wall-clock 금지
  "published_this_window": 0,
  "coverage": { "strand": {}, "archetype": {}, "layer": {}, "domain": {} },  // ledger에서 재계산
  "policy": { /* §3 */ },
  "stop": { /* §5 */ },
  "next_step": "preflight|steer|turn|evolve|finalize"
}
```
- per-turn 정본은 BASE의 `.helix/runs/{turn_id}/`(GATE-EVIDENCE 등) + `.pgf/*` + 통합 `.helix/ledger.json`. 루프는 요약만 누적.
- **매 turn 시작 시 `helix.py status --json`을 다시 호출**해 next_action·diversity·coverage를 재계산(문서·메모리 신뢰 금지).

## 3. 루프 정책 (capability-adaptive 기본값)

| 키 | 기본 | 의미 / 스케일 |
|---|---|---|
| `max_turns` | null(무제한) | 정지 카운트 |
| `candidates_K` | 8 | 엔진 후보 수. 능력/예산↑ → ↑(12~20) |
| `verify_depth` | "standard" | deep 시 cross-model 합의(evx multi-runtime) + adversarial |
| `sim` | "lexical" | semantic 등급이면 `module:function` 임베딩 주입(`helix.py status --sim`) |
| `publish` | true | false면 seed+구현+검증까지(공개 보류) |
| `publish_rate_limit` | 6 / rolling-day | 무인 폭주 상한(초과분 seed-only 강등) |
| `evolve_every` | 5 | M회마다 메타리뷰 + threshold 보정 |
| `backoff_base_sec` | 60 | 실패 후 지수 backoff |
| `min_corpus_for_exploit` | 2 | `next_action`의 explore↔exploit 전환 임계(백본 policy) |
| `diversity_thresholds` | DEFAULT | `core/helix_diversity.DEFAULT_THRESHOLDS` override(§8 보정 산출) |

> **자기진화 스케일**: 능력↑일수록 `candidates_K`↑·`verify_depth=deep`·`sim=semantic`로 자동 상향(보수적, 불확실하면 기본 유지).
> 정책 변경은 `loop-state.policy`에만 기록(BASE/skills/core/정본 자동수정 금지). 근거는 loop-report에.

## 4. 다양성 steering (anti-collapse) — 매 turn 선행

장기 반복의 최대 리스크는 mode-collapse(한 strand/archetype/도메인 수렴). 백본이 1차 방어하고(`next_action`·`repair_required`), 루프가 2차 보정한다:
1. `helix.py status --json`의 `diversity.repair_required`가 참이면 → BASE §2 REFRESH 경로(sdxx→idxx→cixx 또는 exploit 회피)를 **생성 전** 강제.
2. `.helix/ledger.json`에서 **strand·archetype·layer·domain 히스토그램** 계산 → **최소 커버리지 축**을 이번 turn의 `exploration_focus`로 주입.
   - 예: explore가 exploit보다 과다하거나 Gate 편중·Sensing 희소 → 다음은 RUN_EXPLOIT 우선 또는 non-Gate/Sensing 타겟.
3. 직전 K개 winner의 single_question 의미축과 **다른 축** 우선(연속 동일축 금지).
4. steering 결정·근거를 `.helix/runs/{turn_id}/input_manifest.json`의 `exploration_focus`에 명시(감사).

## 5. 정지 조건 (should_stop) — 하나라도 참이면 Finalize

- `max_turns` 도달 · **예산 소진**(런타임 budget 신호).
- **dry**: `consecutive_dry ≥ 2` — 두 turn 연속 (a) explore 신선 소스 0건(sdx/sdxx broaden 후에도) 또는 exploit 후보 0개, (b) **통합 ledger 게이트가 모든 후보 폐기**(채택 가능한 신선 winner 없음).
- **연속 실패**: `consecutive_failures ≥ 3`(구현/검증/publish 비복구 실패).
- **인적 정지**: `.helix/loop/STOP` 파일 또는 사용자 인터럽트 → 현재 turn 안전 마감 후 정지.
- **무결성 경보**: `helix_validate` 실패 / ledger 파싱 불일치 / 원본(skills·core) 오염 감지 → 즉시 정지·보고(자동 복구 금지).

## 6. Crash recovery / resume (재진입 안전)

루프 (재)시작 시:
0. **LoopPreflight (필수 선검사)** — 하나라도 실패면 turn 진입 금지·보고:
   ① `.helix/loop/STOP` 부재 ② `python -m unittest discover -s tests`→OK + `python core/helix_validate.py .`→PASS
   ③ `python helix.py status --json` 파싱 성공 ④ (publish 시) `gh auth status` OK ⑤ `.helix/ledger.json` JSON 유효.
1. `.helix/loop/loop-state.json` 있으면 로드, 없으면 생성.
2. **미완 turn 복구·격리**: `.helix/runs/{turn_id}-pending/` 또는 미완 `.pgf/*` 존재 시 —
   - 마지막 완료 단계가 BASE status로 명확하면 그 다음부터 이어가기 가능.
   - 모호하면 `.helix/runs/_quarantine/`로 격리하고 다음 turn으로 재시작. **이미 커밋된 ledger·기존 프로젝트는 불변.**
3. **close-loop idempotency가 안전망**: RECORD가 중복되면 `already_recorded`로 무해 — 컨텍스트 단절 후에도 §6으로 무손실 재개.

## 7. 장기 실행 보호 (pacing · checkpoint · 재진입)

- **체크포인트**: 매 turn 종료 시 loop-state 갱신 + (compaction 지원 시) loop-state/WORKPLAN 경로 보존 후 압축.
- **재진입(runtime-neutral)**: 가진 지속수단 택1 — hook/Stop-hook(PGF loop), heartbeat/scheduler(cron·ScheduleWakeup), 수동 continuation(다음 turn 프롬프트 emit). **상태는 파일에 있으므로** 끊겨도 §6으로 재개.
- **heartbeat**: `.helix/loop/heartbeat.log`에 turn·주입시각·next_action·상태 1줄씩.

## 8. 자기진화 (evolve) — 매 M turn

`evolve_every`마다 메타리뷰(PGF evolve 정신):
1. 직전 M개 winner의 6축/다양성/strand 균형/반복 실패 사유 분석.
2. **threshold 보정(실행형)**: 누적 라운드 유사도 history로 `python scripts/calibrate_diversity.py rounds.jsonl --target 0.2 --out thresholds.json` → 산출을 `loop-state.policy.diversity_thresholds`로 반영(`measure_diversity(..., thresholds=...)`). 능력↑ 시 `candidates_K`↑·`verify_depth=deep`·`sim=semantic`.
3. 변경은 **diff 형식**(키: old→new + 근거)으로 `.helix/loop/evolve-{turn}.md`에 기록. **`loop-state.policy`로만 자동수정**(BASE/skills/core/정본·DEFAULT_THRESHOLDS 소스 자동수정 금지).

## 9. 무인 외부공개 가드레일 (★ 되돌리기 어려운 행위)

- **신규 생성만 + idempotency 선검사**: `gh repo view sadpig70/{Name}` — 없으면 `--public` 생성, **있으면 push/reconcile만**(삭제·force-push 금지).
- **게이트 우선**: BASE §7의 모든 게이트(unittest OK·validate PASS·결정론·stdlib·누출0·sample verdict·통합 ledger 신선) **전부 통과 turn만** publish. 하나라도 실패 → **seed-only**, 루프는 계속.
- **검증 증명 의무(자기보고 금지)**: `.helix/runs/{turn_id}/GATE-EVIDENCE.json`에 실측 `command/exit_code/passed`. **전부 passed:true 아니면 공개 금지.**
- **rate-limit (window_id)**: 주입 날짜 기반 `publish_window_id`로 카운트. window 바뀌면 0 리셋. 초과분 seed-only.
- **누출 재검사**: publish 직전 코드/문서/커밋에 타 런타임 식별자·미공개 내부명·PII 0.
- 공개 승인 전제: sadpig70 신규 공개 repo 생성은 사전 승인된 활동. 그 외 외부 행위(타 계정·삭제 등) 금지.

## 10. 감사(audit) 산출물

- `.helix/loop/loop-state.json` — 단일 진실 상태 · `.helix/loop/heartbeat.log` — turn 1줄 로그.
- `.helix/ledger.json`·`.helix/corpus.json` — 통합 ledger + 코퍼스 환류(염기쌍) 정본.
- `.helix/runs/{turn_id}/GATE-EVIDENCE.json` — 게이트 실측 증거(전부 passed:true).
- `.helix/loop/evolve-{n}.md` — 자기진화·threshold diff · `.helix/loop/loop-report.md` — 종료 롤업(turn·winner·repo·strand 균형·coverage 변화·정책 변천·실패/스킵 사유).
- 각 turn의 BASE 산출(`.pgf/*` + `{Name}/*` + 엔진 native 산출)은 그대로 정본.

## 11. 불변식 (루프 전체 — 절대)

- **원본 HELIX 불변**: `skills/`·`core/`·`engines/`·vendor 스킬·BASE/이 문서·기존 `.pgf` 정본을 **수정 금지**. 루프는 **새 turn/새 프로젝트/`.helix/` 상태만** 추가.
- **매 turn 재계산**: 회피·다양성·coverage를 `helix.py status`/`.helix/ledger.json`에서 live 재확인. 한 turn의 부주의가 다음을 오염시키지 않게 격리.
- **결정론·stdlib·누출0·parts≥2(exploit)·단일출처 ledger 게이트**는 매 turn 불가침.
- 실패는 **fail-safe**: 손상 산출은 커밋 말고 격리/폐기, 루프는 계속(또는 §5 정지). 의심 시 **정지 후 보고**.

## 12. Quick-start (PPR)

```python
def helix_factory_loop(policy=DEFAULT_POLICY):
    state = load_or_init_loop_state()                 # §2, §6
    while not should_stop(state, policy):              # §5
        st = run("python helix.py status --json")      # §1 백본 상태(재로딩)
        steer = steer_focus(st, state.coverage)        # §4 다양성 보정
        try:
            turn = run_BASE_turn(st.next_action, steer, policy)   # = BASE 1회 (explore|exploit|refresh|record)
            #   BASE 내부: 통합 ledger is_consumed 게이트 → 미달이면 폐기·재조향·재생성(dry면 DryError)
            close = run(f"python helix.py close-loop --winner {turn.winner_json} "
                        f"--ledger .helix/ledger.json --corpus .helix/corpus.json --now {injected_date}")
            gates = run_all_gates(turn)                # §9 실측 GATE-EVIDENCE
            if gates.passed and policy.publish and under_rate_limit(state):
                publish_github(turn); set_status(turn, "implemented")     # 신규 공개만
            else:
                set_status(turn, "seeded")             # 공개 보류, 루프 계속
            record_outcome(state, turn); update_coverage(state); state.consecutive_failures = 0
        except DryError:
            state.consecutive_dry += 1
        except Exception:
            state.consecutive_failures += 1; backoff(state, policy)       # 손상분 격리
        if state.turn % policy.evolve_every == 0:
            evolve_policy(state)                       # §8 calibrate + policy 한정 자기수정
        checkpoint(state); heartbeat(state)            # §7
        reenter_via_runtime_continuation()             # §7
    finalize_loop_report(state)                        # §10
```

실행 지시(자연어 등가): **"`docs/INSTRUCTIONS-helix-loop-autonomous.md`의 루프를 시작하라 — 정지 조건까지 매 turn `helix.py status`로 next_action을 읽어 BASE 한 턴을 수행하고, close-loop으로 ledger/corpus를 닫으며, 게이트 통과분만 공개하고, loop-state에 체크포인트하라."** 정지: `.helix/loop/STOP` 생성 또는 인터럽트.

---

**한 줄 요약**: BASE(1회 턴)를 inner cycle로 호출하는 **무중단 HELIX 팩토리 루프** — 매 turn `helix.py status`로 백본 `next_action`(explore↔exploit·REFRESH·RECORD)을 읽어 BASE를 수행하고, `close-loop`으로 통합 ledger 기록 + winner→corpus 환류(염기쌍)해 수렴 없이 복리로 돌며, 게이트 통과분만 공개하고, loop-state로 crash·단절에 무손실 재개하며, 능력↑ 시 깊이·폭 자동확장·M회마다 threshold 보정, dry/실패/예산/인적정지에서 안전 종료한다. 원본 불변·단일출처 ledger·외부공개 가드레일은 매 turn 불가침.
