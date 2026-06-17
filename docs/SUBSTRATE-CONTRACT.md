# HELIX-Core — Substrate Contract (single source of truth)

> 두 엔진이 *중복 구축*하던 기계를 백본에 **한 번만** 정의한다. 엔진은 이 계약을 호출할 뿐
> 자기 사본을 두지 않는다 → desync 제거. 모든 함수는 순수 결정론(stdlib, 주입식).

## 0. 결정론 규약

| 항목 | 규칙 |
|---|---|
| 시간 | 인자 `now`로 **주입**. `Date.now`/`datetime.now` 호출 금지 |
| 의미 유사도 | callable `sim(a, b) -> float`로 **주입**. 임베딩은 엔진/외부 책임 |
| 무작위 | 금지 (`random` 미사용) |
| 외부 의존 | 금지 (stdlib only — CI 무의존) |
| 부수효과 | load/save만 파일 I/O. 나머지 순수 함수 |

## 1. helix_fingerprint — 정체성 (단일 출처)

| 함수 | 계약 | 통합한 것 |
|---|---|---|
| `normalize_name(s)` | 소문자+영숫자만 | recreate `normalize_name` ≡ IdeaFirst `normalized_title` |
| `tokenize_name(s)` | CamelCase/구분자 → 토큰 | vocab/keyword 신호 기반 |
| `source_fingerprint(parts)` | 코퍼스 source 정규 키 | recreate exploit 네임스페이스 |
| `generated_fingerprint(parents)` | 통합 부모 정규 키 | recreate integration 네임스페이스 |

## 2. helix_ledger — 통합 재사용 차단 게이트

**병합점**: IdeaFirst `consumed_ideas.yaml` ⊕ ProjectGenome `registry.json`.

`exclude_match_on` (단일화):
```
idea_id · normalized_title · aliases · semantic_family
        · source_fingerprint · generated_fingerprint
```

| 함수 | 계약 |
|---|---|
| `candidate_keys(c)` | 후보 → 6개 결정론 match 키 |
| `is_consumed(c, ledger)` | `{consumed, match:{idea_id,on}, keys}` — 첫 일치 키 반환(감사) |
| `append_consumed(ledger, entry, now)` | 구현된 winner만 기록(record_only_when). `now` 주입 |
| `load_ledger / save_ledger` | JSON 정본 (stdlib). YAML view는 엔진 어댑터가 투영 |

**규율**: ledger는 품질 인증이 아니라 **재사용 방지 게이트**다. 구체 프로젝트/MVP/repo가 된
winner만 append (양 엔진 공통 `record_only_when`).

## 3. helix_diversity — 통합 동질화 측정 (복구효소)

**병합점**: aox `AOX_POLICY.homogenization` 4임계 ⊕ recreate `unique_ratio`.

| 신호 | 결정론? | 출처 |
|---|---|---|
| `keyword_coverage` | ✅ 완전 결정론 | IdeaFirst |
| `max_pair_count` (domain pair) | ✅ 완전 결정론 | IdeaFirst |
| `avg_embedding_sim` | 주입 `sim` 집계 | IdeaFirst |
| `winner_embedding_similarity` | 주입 `sim` 집계 | IdeaFirst (지속혁신) |
| `unique_ratio` | 주입 `sim` 집계 | recreate (island 재발산) |

`measure_diversity(pool, recent_winners, sim, thresholds)` →
`{triggered, breaches, sim_kind, metrics, signals, thresholds}`.
`triggered = breaches >= min_breaches(기본 2)`. `sim=None`이면 결정론 `lexical_sim`
기본을 써서 **완전한** report를 낸다(`sim_kind="lexical"`); 임베딩 sim 주입 시 `"semantic"`.
임계는 `DEFAULT_THRESHOLDS` 단일 정의 + override(`thresholds=`) + 보정 절차(`docs/CALIBRATION.md`).

## 4. helix_provenance — 계보 + 환류 (염기쌍)

| 함수 | 계약 |
|---|---|
| `trace_winner(winner)` | explore: winner→insight→cix→idx→tcx→channel / exploit: seed→kernel→sources→parents. 정규 lineage `[{layer,id}]` |
| `winner_to_corpus_entry(consumed_entry)` | ★구현된 explore winner → exploit 코퍼스 source stub. implementations 없으면 ValueError |

`winner_to_corpus_entry`가 **염기쌍 결합** — 두 가닥을 잇는 유일한 데이터 엣지.

## 5. helix_loop — 폐루프 드라이버 (나선 회전)

`next_action(state, policy)` 결정론 우선순위:
```
1. RECORD_CONSUMED  (구현 winner 미기록)      ← 최우선 (NoOpenLoop, 염기쌍 폐쇄)
2. REFRESH_INPUTS   (diversity.triggered)     ← 생성 전 복구
3. RUN_EXPLORE      (corpus_size < min)       ← 미성숙 → 외부 신선
4. RUN_EXPLOIT/EXPLORE (last_engine 기반 균형)
```
동일 state → 동일 action (재현 가능).

## 6. helix_validate — 구조·계약 검증기

`validate_ledger / validate_diversity_report / validate_loop_action / validate_project`.
jsonschema 미의존(ProjectGenome `validate_projectgenome.py`와 동일 철학). `validate_project`는
필수 파일 존재 + 예제 ledger 일관성 + 루프 smoke를 점검.

## 7. 엔진이 버리는 사본 (de-dup 결과)

| 엔진 사본 | → 대체 |
|---|---|
| recreate `scripts/fingerprint.py` | `core/helix_fingerprint.py` |
| recreate idea-layer `unique_ratio`, Phase2b 충돌 | `core/helix_diversity`, `core/helix_ledger` |
| IdeaFirst `consumed_ideas.yaml` 로직, `AOX/SDX` homogenization 임계 | `core/helix_ledger`, `core/helix_diversity` |

→ 임계·로직이 시스템 *사이*에서 갈라질 위험(desync) 제거.
