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

**실사례:** Compatibility Mesh(SovMesh 등)는 machine이 Attestra의 predicate-gate였다. 순진하게
CONDENSE하면 커널을 복제한다. machine-aware 라우팅이 이를 BUILD_ON_PLATFORM(Attestra `sov-mesh` 팩,
SovMesh.audit parity)으로 교정했다.

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
