# PGFR-COMBO: Recombination Patterns

5가지 재조합 패턴의 상세 가이드.

## Decision Tree

```
같은 시나리오의 연속된 레이어인가?
  ├─ YES → Vertical Stack
  └─ NO
      같은 메커니즘이 3개 이상 반복되는가?
        ├─ YES → Kernel Extraction
        └─ NO
            두 프로젝트의 교차점에 명확한 새 가치가 있는가?
              ├─ YES → Mashup
              └─ NO
                  독립 운영이 유지되어야 하는가?
                    ├─ YES → Federation
                    └─ NO → Horizontal Platform
```

## 1. Vertical Stack

**정의**: 같은 최종 시나리오를 해결하는 여러 프로젝트를 상하 레이어로 쌓아 완전한 솔루션 스택을 만든다.

**사용 시점**:
- 각 프로젝트가 시나리오의 일부만 해결할 때
- 사용자가 end-to-end 경험을 원할 때
- 단일 제품으로 시장에 진입하고 싶을 때

**Binding 전략**:
- 상위 레이어의 출력 = 하위 레이어의 입력
- 공통 이벤트 스키마/원본 포맷 정의
- 레이어 간 계약(contract) 명시

**예시**:
- `AgentMesh`(관찰) → `SpendMesh`(통제) → `VetoEscrow`(차단) → `SettleMesh`(정산)

**리스크**:
- 한 레이어의 실패가 전체 스택을 멈추게 할 수 있음
- 레이어 간 결합도가 높아짐

---

## 2. Horizontal Platform

**정의**: 여러 도메인에 걸쳐 동일한 메커니즘을 제공하는 공통 레이어로 추상화한다.

**사용 시점**:
- 동일한 문제를 여러 도메인이 반복해서 풀고 있을 때
- API/SDK로 판매할 수 있는 인프라가 있을 때
- 중복 구현을 제거하고 싶을 때

**Binding 전략**:
- 도메인별 어댑터/플러그인 구조
- 핵심 메커니즘은 그대로, 입력/출력 포맷만 도메인별 변환

**예시**:
- `ADPR`(bio provenance) + `PnR`(non-response proof) + `RoboTrace`(robot evidence) → **TrustMesh**

**리스크**:
- 과도한 일반화로 인해 특정 도메인의 요구사항을 놓칠 수 있음
- "platform for everything"이 되어 초점 상실

---

## 3. Kernel Extraction

**정의**: 여러 프로젝트에 중복되어 있는 부분을 별도의 독립 프로젝트로 분리한다.

**사용 시점**:
- 3개 이상의 프로젝트가 같은 라이브러리/서비스를 구현하고 있을 때
- 이 중복 부분이 향후 더 많은 프로젝트에서 사용될 가능성이 있을 때
- 유지보수 부담이 클 때

**Binding 전략**:
- Kernel은 라이브러리/서비스 형태로 제공
- 기존 프로젝트는 Kernel을 의존성으로 사용
- Kernel 변경 시 하위 프로젝트 영향도 관리

**예시**:
- `authorization ledger`, `inclusion proof`, `policy engine`, `double auction`

**리스크**:
- Kernel 의존성이 많아질수록 변경의 파급력이 커짐
- 초기 분리 비용이 큼

---

## 4. Mashup

**정의**: 두 프로젝트의 교차점에서 완전히 새로운 제품이나 시장을 만든다.

**사용 시점**:
- 두 프로젝트의 메커니즘이 결합될 때 1+1>2의 가치가 생길 때
- 새로운 도메인/시장을 실험하고 싶을 때
- 빠른 프로토타입으로 시장 반응을 테스트하고 싶을 때

**Binding 전략**:
- 한 프로젝트의 출력을 다른 프로젝트의 입력/조건으로 사용
- 새로운 사용자 시나리오 정의
- 최소한의 통합 지점으로 시작

**예시**:
- `ClimateMesh`(리스크 점수) + `FailureFutures`(선물/청산) → 기후 리스크 파생상품
- `ENLI`(기술 확산 추적) + `MLX`(라이선스 메타데이터) → 기술 라이선스 추천 엔진

**리스크**:
- 두 도메인 모두에 대한 깊은 이해가 필요
- 교차점의 시장이 명확하지 않을 수 있음

---

## 5. Federation

**정의**: 독립적인 프로젝트들을 하나의 프로토콜/네임스페이스/생태계로 연결한다.

**사용 시점**:
- 각 프로젝트가 독립적으로 살아남아야 할 때
- 통합보다는 상호운용성이 더 중요할 때
- 생태계 확장을 원할 때

**Binding 전략**:
- 공통 프로토콜/스키마/신원 정의
- 각 프로젝트는 자율성 유지
- 게이트웨이/브리지로 연결

**예시**:
- `WattMesh` + `PowerRoam` + `SeasonBat` + `WasteStack` → 에너지 라우팅 프로토콜 연합
- 모든 `*Mesh` → **Mesh Federation Protocol**

**리스크**:
- 프로토콜 표준화가 어려움
- 각 참여 주체의 인센티브 정렬 필요

---

## Pattern Selection Checklist

- [ ] 이 조합이 단일 제품이 되어야 하는가? → Vertical Stack
- [ ] 여러 곳에서 쓰이는 인프라가 있는가? → Horizontal Platform / Kernel Extraction
- [ ] 두 프로젝트의 교차점이 새 시장을 여는가? → Mashup
- [ ] 독립성을 유지하면서 연결해야 하는가? → Federation
