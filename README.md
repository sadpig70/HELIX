# HELIX

> **두 상보 가닥을 공유 백본이 묶어, 환류하는 폐루프인데도 매 회전 동질화를 차단해
> 수렴 없이 복리로 성장하는 자율 창조 시스템.**

HELIX는 두 시스템을 **하나의 자기완결 repo로 통합**한다 — 모든 스킬을 `skills/`에 vendor하되,
내부 로직은 공유 백본(HELIX-Core)을 **단일 출처**로 두어 desync를 막는다.

<p align="center">
  <img src="assets/helix-loop.svg" alt="HELIX explore⊕exploit 폐쇄 제어 루프: IdeaFirst(가닥 A)와 recreate(가닥 B)가 새 프로젝트로 모이고 winner→corpus 환류(염기쌍)로 닫히며, 백본 HELIX-Core가 ledger·diversity·provenance·fingerprint·loop를 단일 출처로 받친다" width="92%">
</p>

<details><summary>같은 그림 (텍스트)</summary>

```
   세계(무한)                                   자산(유한)
      │ EXPLORE (가닥 A)                          │ EXPLOIT (가닥 B)
   IdeaFirst (sdx→tcx→idx→cix→evx, aox)        recreate / ProjectGenome (corpus→seed)
      │ final_idea ── pgf로 구현 ──► 새 프로젝트 ──┐
      └──────────── winner→corpus 환류(염기쌍) ◄──┘
              ▲ 백본(HELIX-Core): ledger · diversity · provenance · fingerprint · loop
```

</details>

원이 아니라 **나선**인 이유가 곧 가치다: 백본이 두 가닥의 desync를 없애고(단일 출처),
다양성 게이트가 회전마다 폭을 유지해(복구효소), 폐루프인데도 출력이 수렴하지 않는다.

## 왜 합쳤나 (한 줄)

두 엔진은 **explore↔exploit 상보쌍**이고, 각자 *동질화 차단·소모 ledger·cross-model 합의*라는
같은 기계를 **중복 구축**해 두었다. HELIX는 그 중복을 백본에 한 번만 정의해 desync를 제거하고,
`winner→corpus` 환류로 두 엔진을 하나의 상승 나선으로 잇는다.

## 구조

```
HELIX/
├── README.md
├── .pgf/                     # PGF 설계·계획·상태 (이 프로젝트는 pgf full-cycle로 지어졌다)
│   ├── DESIGN-HELIX.md
│   ├── WORKPLAN-HELIX.md
│   └── status-HELIX.json
├── core/                     # ★ HELIX-Core 백본 — 단일 출처 결정론 substrate (stdlib only)
│   ├── helix_fingerprint.py  #   정체성 primitive (ProjectGenome에서 승격)
│   ├── helix_ledger.py       #   통합 소모/등록 ledger — 재사용 차단 게이트
│   ├── helix_diversity.py    #   통합 동질화/다양성 측정 (복구효소)
│   ├── helix_provenance.py   #   계보 + winner→corpus 환류 (염기쌍)
│   ├── helix_loop.py         #   explore↔exploit 루프 드라이버 (나선 회전)
│   └── helix_validate.py     #   구조·계약 검증기
├── skills/                   # ★ ALL 스킬 (자기완결) — IdeaFirst 14 + recreate 2 + 공유 pg/pgf/pgxf
│   ├── pg/ pgf/ pgxf/        #   공유 표기 (1벌, dedup) — pgf/discovery/personas.json 포함
│   ├── sdx/ sdxx/ sdx_ci/ tcx/ idx/ idxx/ cix/ cixx/ evx/ aox/   # explore
│   │   sa-aox/ sa-evx/ sa-icx/ collect_git_trand/
│   └── recreate/ pgfr-combo/                                     # exploit
├── scripts/                  # 결정론 runner (explore/ 12+ · exploit/ 4)
├── seed/                     # durable 입력/상태 (sdx-catalog · idea-ledger · corpus)
├── RUNBOOK.md                # ★ 두 시스템 전 기능 호출법
├── MIGRATION.md              # vendoring 출처·결정 기록
├── helix.py                  # ★ 드라이버 — 두 엔진 상태→통합 ledger→diversity→next_action
├── engines/                  # 가닥 어댑터 — vendored 스킬 ↔ core 배선. 실코드 구현됨.
│   ├── explore/adapter.py    #   가닥 A — IdeaFirst(.evx/.cix/.idea-ledger) → 백본
│   ├── exploit/adapter.py    #   가닥 B — recreate(.recreate/registry.json) → 백본
│   ├── unify.py              #   두 엔진 ledger 병합 (단일 출처 join)
│   └── loaders.py            #   I/O glue (JSON; YAML은 PyYAML 있을 때만)
├── schemas/                  # 백본 데이터 계약 (JSON Schema 4종)
├── docs/
│   ├── ARCHITECTURE.md       # 이중나선 → 시스템 매핑 (정정판)
│   └── SUBSTRATE-CONTRACT.md # HELIX-Core 단일 출처 계약
├── examples/                 # 샘플 ledger + 1라운드 루프
└── tests/                    # 결정론 helper unittest (stdlib only)
```

## 결정론 경계

- **HELIX-Core = 순수 결정론**: stdlib only, 시계/네트워크/AI 없음. 시간은 주입(`now`),
  의미 유사도는 주입(`sim`). 임베딩·LLM은 엔진 책임.
- **exploit 생성물 verdict 경로 = 결정론 불변** (ProjectGenome 규율 계승).
- **엔진 내부 LLM 단계 = 메타층** — HELIX 경계 밖.

## 빠른 시작

```bash
# 한 회전 실행 (픽스처 위에서 — 두 엔진 상태 → 다음 액션)
python helix.py status

# 실제 엔진 위에서 (IdeaFirst .evx*.yaml 은 PyYAML 필요)
python helix.py status --explore-root D:/IdeaFirst --exploit-root D:/recreate_prj/ProjectGenome

# 백본 검증 (구조 + 예제 일관성) / 테스트 / fingerprint CLI
python core/helix_validate.py .
python -m unittest discover -s tests -q
python core/helix_fingerprint.py source ADPR ReleaseMesh PnR
```

`helix.py status` 출력 예 (픽스처):

```text
=== HELIX turn ===
  unified ledger: 2 entries (explore=1, exploit=1)
  diversity pool: 7 items | triggered=False (partial=True, breaches=1)
  latest explore winner: IDEA-018 "Time-Box Automation Enforcer" -> already_consumed=False
      lineage: IDEA-018 -> INS-L10-007 -> EVX-... -> CIX-... -> IDX-... -> TCX-... -> v2
  base-pairing (explore->corpus): AgentPACT
  NEXT ACTION: RUN_EXPLOIT  (fresh assets accumulated -> recombine (compound))
```

## 하위 네이밍

- **HELIX-A / HELIX-B** — 두 엔진 가닥 (explore / exploit)
- **HELIX-Core (Backbone)** — 공유 substrate
- **HELIX-Gate** — 5점 다양성/복구 게이트 (sdxx→idxx→cixx→avoidance→cross-model)
- **HELIX-Loop** — explore↔exploit 폐루프

## 정직한 경계

- HELIX는 **자기완결 모노레포**다 — 두 시스템의 모든 스킬을 `skills/`에 vendor했다(`MIGRATION.md` 출처 기록).
  단 내부 로직은 `core/` 백본을 **단일 출처**로 두어 desync를 막는다(*패키징은 융합, 로직은 단일출처*).
- pgf는 양 트리 내용이 일부 달랐다 — recreate_prj 버전을 canonical로 채택. aox/cix가 쓰는
  `pgf/discovery/personas.json`은 동일해 기계 의존성은 안전(상세 `MIGRATION.md`).
- 이중나선 은유는 2가닥에 최적. 향후 explore 소스가 3+로 늘면 삼중나선(collagen)으로 흡수하거나,
  가닥 수 무관하면 백본 중심 framing 유지.
- 임베딩 임계(cos 0.8/0.65 등)는 양측 차용값 — 통합 코퍼스에 맞춰 재보정 대상.

## 라이선스

[MIT License](LICENSE) © 2025–2026 sadpig70 (Jung Wook Yang)
