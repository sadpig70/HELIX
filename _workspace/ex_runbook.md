===============================================================================
  HELIX FULL-CYCLE RUNTIME BOOTSTRAP — 새 런타임용 지시문
  대상: AI 에이전트 (Claude Code, Codex, Kimi, Gemini, Grok 등 모든 런타임)
  목표: 이 문서만 읽고 HELIX 풀사이클(아이디어 발굴→프로젝트 구현→GitHub 푸시) 완료
===============================================================================

1. HELIX란?

   두 가닥(explore·exploit)이 단일 백본으로 묶여 매 회전마다 새 프로젝트를
   생성하는 자율 창조 시스템. 모든 스킬은 skills/에 vendor되어 있다.

   explore (가닥 A): 외부 세계에서 새 아이디어 발굴
       SDX → TCX → IDX → CIX → EVX → final_idea

   exploit (가닥 B): 기존 코퍼스 재조합해 새 프로젝트 생성
       recreate: corpus 분해 → 3축 재조합 → DesignSeed → 구현

2. 진입: 어떤 파일을 먼저 읽어야 하는가 (10분 소요)

   필수:
     README.md               ← 프로젝트 개요, 구조
     AGENTS.md               ← 런타임 환경 설정
     RUNBOOK.md              ← 모든 기능 호출법 (슬래시 커맨드)
     helix.py                ← 통합 루프 드라이버 (status/close-loop)
     skills/recreate/SKILL.md ← exploit 경로 상세 (6 Phase)
     skills/pgf/SKILL.md      ← 설계·구현 프레임워크

   선택 (explore 경로 사용 시):
     skills/aox/SKILL.md      ← 전체 오케스트레이터
     skills/sdx/SKILL.md      ← 채널 발굴
     skills/tcx/SKILL.md      ← 트렌드 수집
     skills/idx/SKILL.md      ← 인사이트 증류
     skills/cix/SKILL.md      ← 아이디어 생성
     skills/evx/SKILL.md      ← 평가·선정

3. 두 가지 경로

   ┌────────────────────────────────────────────────────────────┐
   │ 경로 A: exploit (빠름, 10~30분)                            │
   │                                                            │
   │   helix.py status → RUN_EXPLOIT 확인                       │
   │   seed/corpus/project_list.md 읽고 코퍼스 파악              │
   │   2~3개 프로젝트를 재조합할 갭 찾기                         │
   │   pgf full-cycle: DESIGN → 구현 → 테스트                   │
   │   helix.py close-loop → ledger 기록                        │
   │                                                            │
   │ 경로 B: explore (깊음, 30~60분)                            │
   │                                                            │
   │   web_search로 2026년 트렌드 수집 (6채널 이상)              │
   │   IDX: Gap/Tension/Counterfactual 인사이트 도출              │
   │   CIX: 20렌즈 × 아이디어 시드 생성, 6축 평가                │
   │   EVX: 14 페르소나 평가 → 최종 1개 선정                     │
   │   pgf full-cycle: DESIGN → 구현 → 테스트                   │
   │   helix.py close-loop → ledger 기록                        │
   └────────────────────────────────────────────────────────────┘

4. 프로젝트 생성 규칙 (반드시 지킬 것)

   모든 HELIX 산출 프로젝트는 아래 패턴을 따른다:

   [1] stdlib-only — Python 3.10+, 외부 패키지 0개
   [2] cli_triplet — sample / evaluate(or verify) / report
   [3] k-way verdict — 결정론적 판정 (예: cleared/flagged/blocked)
   [4] hash-chained audit log — 모든 판정에 SHA-256 감사 로그
   [5] single_question — "Does this X have Y?" 한 줄 질문
   [6] boundary_clause — "What it is not" 명시
   [7] dual_output — JSON(기계) + Markdown(사람)

   구조:
       ProjectName/
       ├── ProjectName/
       │   ├── __init__.py    # from .engine import ...
       │   ├── engine.py      # 결정론적 엔진
       │   ├── cli.py         # argparse: sample/evaluate/report
       │   ├── report.py      # Markdown 리포트 렌더링
       │   └── __main__.py    # cli.main() 호출
       ├── tests/
       │   └── test_*.py      # unittest: 엔진 + CLI 통합
       ├── pyproject.toml     # setuptools, project.scripts
       ├── README.md
       ├── LICENSE            # MIT
       └── .gitignore

5. 참조용: GitHub에 올라간 예시 프로젝트

   https://github.com/sadpig70/ProvenanceStage   ← exploit: GenCert+ReleaseMesh+ADPR
   https://github.com/sadpig70/SpendBoundary      ← exploit: ContextCreep+SpendMesh+VetoEscrow
   https://github.com/sadpig70/ArticleGate        ← explore: EU AI Act Article 5/6/13/14/50 게이트
   https://github.com/sadpig70/BioClock           ← exploit: DriftDossier+Qvidence+LazarettoStage
   https://github.com/sadpig70/SkyGrid             ← exploit: WattMesh+OrbiRoam+PowerRoam
   https://github.com/sadpig70/SoilBond            ← exploit: FieldRoot+ClimateMesh+QuadraticCarbonFund

   각 README.md를 열어 패턴을 확인할 것.

6. 코퍼스 (exploit 경로 재료)

   seed/corpus/project_list.md — 60+개 기존 프로젝트 목록.
   각 프로젝트는 단일 질문 + 결정론적 엔진 + 판정 체계를 가진다.
   README.md를 읽어 archetype / mechanism / layer / verdict_scheme 파악.

   이미 사용된 조합 (중복 금지):
     GenCert+ReleaseMesh+ADPR → ProvenanceStage
     ContextCreep+SpendMesh+VetoEscrow → SpendBoundary
     DriftDossier+Qvidence+LazarettoStage → BioClock
     WattMesh+OrbiRoam+PowerRoam → SkyGrid
     FieldRoot+ClimateMesh+QuadraticCarbonFund → SoilBond
     ADPR+ForgeQuarantine+PnR+ReleaseMesh → WithheldActionWitness

   .helix/ledger.json 에서 consumed 항목 확인 후 중복 회피할 것.

7. 완료 후 (저장 및 기록 규약 — 반드시 지킬 것)

   [1] 프로젝트 물리적 저장 및 코퍼스 환류 (염기쌍 이식)
       - 주 개발 경로 생성: `D:\HELIX\{ProjectName}`
       - 코퍼스 이식: 다음 회전(Recreate)에서 재조합 재료로 활용될 수 있도록 전체 소스 폴더를 아래 두 코퍼스 데이터베이스 경로로 복사
         - `D:\tmp\{ProjectName}`
         - `D:\recreate_prj\{ProjectName}`
       - 코퍼스 장부 동기화: 아래 두 파일에 정렬 규칙(알파벳 순)을 준수하여 프로젝트 단일 질문 및 요약 추가
         - `D:\tmp\project_list.md`
         - `D:\HELIX\seed\corpus\project_list.md`

   [2] HELIX 통합 백본 레코딩 (close-loop)
       - `.helix/ledger.json` 의 `consumed` 항목에 구현 정보를 수동 또는 `close-loop` 로 기재하고, `blocked_names` 와 `source_fingerprints` 갱신
       - `.helix/corpus.json` 에 `origin="exploit"`, `lineage`, `semantic_family` 이력 피드백 추가
       - `.recreate/registry.json` 의 `"status": "implemented"` 로 변경 및 `.recreate/latest.json` 업데이트

   [3] PGF 및 검증 게이트 증거 제출 (GATE-EVIDENCE)
       - `.pgf/DESIGN-{Name}.md`, `WORKPLAN-{Name}.md`, `status-{Name}.json` 작성 및 노드 Terminal 상태(`done`) 마감
       - `.helix/runs/{turn_id}/GATE-EVIDENCE.json` 에 CLI 작동 여부, `py_compile`, 백본 무결성 검증(`helix_validate.py .`) 및 테스트 수행 증거를 `passed: true` 로 기록
       - `.helix/HANDOFF.md` 에 턴 결과(strand, winner, repo, 게이트 상태) 최종 갱신

   [4] 깃허브 공개 및 퍼블리싱
       - 프로젝트 디렉토리(`D:\HELIX\{ProjectName}`) 내에서 `git init` → `commit` 실행
       - `gh repo create sadpig70/{ProjectName} --public --source=. --push` 실행으로 원격 저장소 생성 및 푸시
       - `gh repo edit sadpig70/{ProjectName} --add-topic` 을 통해 topics(helix, exploit 등) 추가

8. 빠른 체크리스트

   □ README.md, AGENTS.md, RUNBOOK.md 읽었는가
   □ 경로 결정: exploit (recreate) vs explore (IdeaFirst)
   □ 코퍼스/트렌드 분석 완료
   □ 새 프로젝트 이름이 기존 60+개와 충돌하지 않는가
   □ stdlib-only · cli_triplet · k-way verdict 충족
   □ 테스트 20개 이상 통과
   □ ledger + corpus 기록 완료
   □ GitHub push 완료

===============================================================================
