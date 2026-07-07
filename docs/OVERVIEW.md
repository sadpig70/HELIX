# HELIX — 현황 브리핑 (외부 검토용 단일 진입점)

> 이 문서는 **외부 런타임 AI/리뷰어가 HELIX를 빠르게 파악하고 향후 방향을 제안**하도록
> 만든 단일 진입점이다. 무엇인지 → 현재 도달점 → 설계 불변식 → 정직한 한계·열린 질문 순.
> 코드/저장소 링크만 함께 보면 방향 제안이 가능하도록 구성했다.

---

## 1. HELIX가 무엇인가 (한 문단)

HELIX는 **자율 창조 시스템**이다. 두 상보 엔진을 하나의 자기완결 repo로 통합하고, 공유 백본
(HELIX-Core)을 단일 출처로 둔다.

- **가닥 A — explore** (`IdeaFirst`): 세계 신호에서 아이디어를 발산 생성 (sdx→tcx→idx→cix→evx).
- **가닥 B — exploit** (`recreate`/ProjectGenome): corpus를 재조합해 프로젝트를 생성.
- **백본 (HELIX-Core)**: `ledger`(재사용 차단) · `diversity`(동질화 차단) · `provenance`(winner→corpus
  환류) · `fingerprint` · `loop`. **순수 결정론**(stdlib only, 시계·네트워크·AI 없음; 시간은 `now`로 주입).
- **가닥 C — Condense (v0.5)**: corpus의 **machine-공유 클러스터**를 `kernel+plugin 플랫폼`으로 수렴시킨다.
  다양성 게이트가 *생성*의 발산을 지키듯, Condense는 *플랫폼 층*의 의도적 수렴을 담당한다.

핵심 명제: **HELIX는 "프로젝트 생성기"에서 "플랫폼 생성기"로 진화한다.**

---

## 2. 현재 도달점 (검증된 사실)

### 2.1 5개 `-stra` 플랫폼 (전부 public·CI green)
| 플랫폼 | 동사 | machine | 팩 | 방식 |
|---|---|---|---|---|
| [Attestra](https://github.com/sadpig70/Attestra) | attest | predicate 게이트 → verdict (M2/M3) | 23 | 손 |
| [Clearstra](https://github.com/sadpig70/Clearstra) | clear | 청산/가격 (M5~M8) | 12 | 손 |
| [Routestra](https://github.com/sadpig70/Routestra) | route | 자원 라우팅 score→select / bound (M9/M10) | 11 | 손 |
| [Certstra](https://github.com/sadpig70/Certstra) | certify | 인증 verdict + staged rollout (M2/M12) | 5 | **Condense emit #1** |
| [Scorestra](https://github.com/sadpig70/Scorestra) | score | 가중 score → 등급 tier → 집계 (M15) | 5 | **Condense emit #2** |

- 총 **56팩**. 각 팩은 원본 corpus 프로젝트의 로직을 **커널 무수정(zero-kernel-change)**으로 재현하며,
  원본과의 **parity 테스트**를 동봉한다(소스 있으면 실행, CI에선 skip).
- `-stra` 넷(attest/clear/certify/route)은 **verdict severity 대수를 공유**(valid/thin/breach ≅
  compliant/restricted/violation ≅ certifiable/needs_review/blocked)해 상호 조합·증언 가능.
  [stra-demo](https://github.com/sadpig70/stra-demo)가 route→clear→certify→attest를 한 결정으로 실행.

### 2.2 corpus 완전 라우팅
`helix.py status --layered-corpus`가 corpus 후보를 machine으로 판정해 **3분류로 완전 배정**:
- **흡수 20** (clean gate/primitive → 팩)
- **defer 2** (RouteSentinel·EndowFront — 어떤 커널에도 안 맞는 machine)
- **design-only 8** (코드 없음)

결과: `build_on_platform_candidate()`·`condense_candidate()` **모두 None** — 더 배정할 후보 없음.

### 2.3 Condense 두 성장 경로 모두 실증
- **BUILD_ON_PLATFORM**: 기존 4 플랫폼에 팩 추가 (커널 중복 방지). 예: "Compatibility Mesh" 5형제를
  이름이 아니라 **실코드 machine**으로 판정 → **3개 플랫폼에 분산** 흡수(새 커널 0개). 양방향 교정도 실증
  (AgentMesh: Attestra→Clearstra, SettleMesh: Clearstra→Attestra).
- **CONDENSE**: novel machine 클러스터 → **새 플랫폼 emit**. defer됐던 스코어링 5개가 4 커널에 없는
  **M15**(가중 score→tier→집계)를 공유함을 확정 → 루프가 CONDENSE 제안 → **Scorestra emit**해 클러스터
  5/5 흡수(2-D rule-ladder 커널 확장 포함). "defer = 버림"이 아니라 **미인식 novel-machine 클러스터**였음.

---

## 3. 설계 불변식 (지배 규율)

1. **단일 출처 백본.** 스킬은 `skills/`에 vendor하되 ledger/diversity/provenance/fingerprint/loop는
   `core/`에 한 번만 정의 → desync 불가.
2. **결정론 경계.** 커널+팩 = 순수 stdlib. 시계·네트워크·AI 없음. 시간은 `now` 주입, hash에서 시간 메타
   제외 → 시간 무관 재현. **LLM/휴리스틱은 전부 "메타층"**(경계 밖)으로 밀어낸다.
3. **machine-aware 라우팅.** 새 프로젝트를 흡수하기 전, 이름이 아니라 **실코드 machine**으로 판정.
   machine이 기존 커널에 있으면 BUILD_ON_PLATFORM(팩), 없으면 CONDENSE(새 플랫폼).
4. **parity anchor.** 각 팩은 원본과 동작 일치를 parity 테스트로 잠근다.
5. **federate-not-fuse.** 원본은 read-only, `source_project` 태그로 추적. 복사가 아니라 계약 연합.
6. **zero-kernel-change.** 팩 추가가 커널을 건드리면 안 된다(단, novel machine은 CONDENSE로 새 커널).

지식 베이스: `seed/condense/layered-corpus.json`(라우팅 단일 출처) · Mechanism Graph M1~M15.

---

## 4. 정직한 한계·열린 질문 (검토 요청 핵심)

리뷰어가 방향을 제안할 때 특히 아래를 다뤄주면 좋다.

1. **라우터가 수동이다.** HELIX 루프는 CONDENSE/BUILD_ON_PLATFORM을 *제안*하지만, 실제 machine 판정
   (각 프로젝트 코드 정독 → machine 분류 → 팩 작성 → parity)은 **사람/에이전트가** 한다.
   `layered-corpus.json`도 수작업 유지. → **판정·팩 emit을 HELIX가 자동화해야 하나?** 결정론 경계(커널에
   AI 금지)와 어떻게 양립? (판정은 메타층에서 AI로, 산출물은 결정론으로?)
2. **corpus 소진.** 모든 후보가 배정됐다. 추가 성장은 **새 corpus 생성**(explore⊕exploit 루프 재가동)이
   필요. 이 생성 루프는 존재하나 이번 작업에서 많이 돌리지 않았다. → **더 생성 vs 플랫폼 심화**, 어디에
   가치가 있나?
3. **defer 2개(RouteSentinel·EndowFront)** 는 M15 이후에도 안 맞았다(로봇 detour 시뮬 / 자금 projection).
   → 6번째 플랫폼(시뮬레이션 커널?)의 씨앗인가, 진짜 standalone인가?
4. **parity가 CI에서 skip.** 원본 저장소가 vendored 아니라 CI에선 parity 미실행(로컬만). → 신뢰 경계로
   수용 가능한가? 원본을 CI에 checkout해야 하나?
5. **플랫폼이 얇다.** 커널은 작고 정확(결정론)하지만, 팩은 대체로 원본 로직의 선언적 재현이다. → 조합
   (cross-platform pipeline)이나 실사용 제품으로 **더 깊은 가치**를 뽑을 여지는?
6. **결정론 vs 학습.** 모든 AI를 메타층으로 밀어낸 경계가 옳은가, 아니면 일부 플랫폼은 학습 성분을
   내장해야 하나?
7. **운영/스케일.** 7개 저장소(HELIX + 5 플랫폼 + demo) + 수동 레지스트리 정합. 더 늘리려면 툴링 필요.

---

## 5. 리뷰어에게 묻는 향후 방향 (택1 이상 의견 요청)

- **(가) Condense 라우터 자동화** — 판정→팩 emit 파이프라인을 HELIX가 스스로 실행.
- **(나) corpus 재생성 성장** — explore⊕exploit를 실제 돌려 새 프로젝트 → 다시 라우팅(본류 회귀).
- **(다) cross-platform 제품화** — 5 플랫폼 위에 실사용 조합(예: 실제 거버넌스/공급망 파이프라인) 구축.
- **(라) thesis 산출물화** — "project→platform generator" 명제를 논문/발표 데모로 패키징.
- **(마) 6번째 플랫폼** — simulation-class defer(RouteSentinel/EndowFront)를 위한 novel 커널 CONDENSE.
- **(바) 그 외** — 위 프레이밍 자체를 재고할 지점이 있으면 지적.

---

## 6. 빠른 확인 경로 (리뷰어용)

```bash
# HELIX 루프 상태 (라우팅 제안 — 현재 후보 없음 = 완전 라우팅)
python helix.py status --layered-corpus seed/condense/layered-corpus.json
# 백본 검증 + 테스트
python core/helix_validate.py . && python -m unittest discover -s tests -q
```

- 라우팅 지식 베이스: [`seed/condense/layered-corpus.json`](../seed/condense/layered-corpus.json)
- Condense 상세: [`docs/CONDENSE.md`](CONDENSE.md) · 아키텍처: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- 어댑터: `core/helix_condense.py` · 루프: `core/helix_loop.py` · 스킬: `skills/condense/SKILL.md`
- 플랫폼(각 README에 machine·팩·parity 설명): Attestra · Clearstra · Routestra · Certstra · Scorestra (github.com/sadpig70/*)
