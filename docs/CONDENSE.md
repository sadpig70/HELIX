# HELIX Condense — project generator → platform generator (v0.5)

> HELIX v0.4는 `explore ⊕ exploit`로 **개별 프로젝트**를 생성했다. v0.5는 제3 가닥 **Condense**를
> 더한다: corpus의 machine-공유 클러스터를 **kernel+plugin 플랫폼으로 수렴**시켜, 프로젝트 → 플랫폼 →
> 생태계로 층이 쌓이는 나선을 만든다. 다양성 게이트가 생성의 발산을 지키듯, Condense는 플랫폼 층의
> **의도적 수렴**을 담당한다.

## 왜

corpus(69 프로젝트)는 무작위가 아니라 같은 **machine**(hash-chain ledger·verdict severity·predicate
gate·provenance·clearing·routing…)을 도메인만 바꿔 반복한다. 이 반복을 클러스터별로 커널 1벌 +
플러그인 N벌로 압축하면 플랫폼이 된다. 손으로 3회(Attestra·Clearstra·Routestra) 반복한 레시피를
정식화·자동화한 것이 Condense다.

## 산출된 플랫폼 (전부 독립 저장소·public, 원본 실코드 parity 검증)

| 플랫폼 | 동사 | 클러스터 | 레퍼런스 anchor | 방식 |
|---|---|---|---|---|
| [Attestra](https://github.com/sadpig70/Attestra) | attest | Governance/Trust | ActionHandbackVerifier | 손 |
| [Clearstra](https://github.com/sadpig70/Clearstra) | clear | Clearing/Market | CryoFutures | 손 |
| [Routestra](https://github.com/sadpig70/Routestra) | route | Routing/Siting | SkyGrid | 손 |
| [Certstra](https://github.com/sadpig70/Certstra) | certify | Robotics/Release | CertMesh | **Condense 레시피로 emit** |

네 플랫폼은 **verdict severity 대수를 공유**한다(valid/thin/breach ≅ compliant/restricted/violation ≅
certifiable/needs_review/blocked) → 상호 조합·증언 가능(예: `Clearstra.clear() → Attestra verdict=valid`).

## 단계 (U1~U5)

| Phase | 산출 | 게이트 |
|---|---|---|
| U1 | Mechanism Graph(M1~M14) + Maturity 감사 | 클러스터 탐지가 기존 3플랫폼 군집 자동 재현 |
| U2 | Condense 레시피 정식화(6 스텝) | 3플랫폼 역적용 회귀 100% |
| U3 | 자동 emit 파일럿 → **Certstra** | CERTMESH PARITY + zero-kernel-change |
| U4 | Layered Corpus(36 흡수·24 후보) + Release Strand | Certstra release-ready |
| U5 | 루프 편입 + `helix.py status` live 제안 | 결정론 불변 + 시나리오 재현 |

상세 산출물(scratch): `_workspace/condense/U1~U5*.md`.

## Machine-aware 라우팅 (재발명 방지)

condense 전에 클러스터의 machine이 기존 플랫폼 커널에 이미 있는지 확인한다:

```
if cluster.shared_machines ⊆ (existing platforms' kernel_machines):
    -> BUILD_ON_PLATFORM   (그 플랫폼에 팩 추가 — 커널 중복 금지)
else:
    -> CONDENSE            (새 플랫폼 emit)
```

**실사례 — Compatibility Mesh 5형제 (실코드로 완결 검증):** 이름이 같은 "Compatibility Mesh"
클러스터(SovMesh·PqcMesh·SignalMesh·AgentMesh·FlowMesh)를 순진하게 보면 "새 플랫폼 1개"로 CONDENSE하기
쉽다. 하지만 각 프로젝트의 **실코드를 읽어 machine을 판정**하면 이름만 같을 뿐 machine이 서로 다르고,
**전부 기존 커널로 환원**된다 — 새 플랫폼 0개, 3개 플랫폼에 분산:

| 프로젝트 | machine (실코드) | 귀속 | 팩 |
|---|---|---|---|
| SovMesh | M2+M3 정책 audit → severity verdict | Attestra | `sov-mesh` |
| PqcMesh | M2+M3 자산 assess → severity verdict | Attestra | `pqc-mesh` |
| SignalMesh | M2+M3 admissibility → exchange posture | Attestra | `signal-mesh` |
| FlowMesh | M10 utilization threshold-bound | Routestra | `flow-mesh` |
| AgentMesh | M6+M5 cost pricing + rollup (verdict 없음) | Clearstra | `agent-ops` |

라우팅은 **양방향**으로 작동한다: SovMesh는 Attestra로 *끌어들이고*, AgentMesh는 (verdict 대수가 없으므로)
Attestra에서 *밀어내* Clearstra pricing으로 보낸다. 각 팩은 원본과의 **parity 테스트**를 동봉한다
(`test_*_mesh_parity.py`; 소스 있으면 실행, CI에선 skip). 결론: **한 클러스터가 이름은 같아도 machine
기준으로 여러 플랫폼에 분산될 수 있으며, 새 커널을 짓기 전에 실코드 machine 판정이 선행돼야 한다.**

## 사용

```bash
# helix.py가 layered-corpus를 읽어 CONDENSE/BUILD_ON_PLATFORM을 제안 (opt-in)
python helix.py status --layered-corpus seed/condense/layered-corpus.json

# 레시피 실행 (런타임 스킬)
/condense analyze
/condense condense <cluster>              # novel machine -> 새 플랫폼
/condense build-on-platform <project> <platform>   # covered machine -> 팩 추가
```

- 어댑터(제안): `core/helix_condense.py` (순수 결정론) + `core/helix_loop.py`(CONDENSE/BUILD_ON_PLATFORM 액션).
- 레시피(실행): `skills/condense/SKILL.md`.
- 하드 게이트: zero-kernel-change · reference-parity · determinism-clean · tests-green · structure-conform.

## 지배 불변식

parity anchor · zero-kernel-change · determinism boundary(now/sim 주입, hash에서 시간 메타 제외) ·
federate(원본 read-only·source_project 태그) · severity 대수 정렬.
