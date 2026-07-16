# REVIEW-HELIXCorpusSupply

## Scope

- Target: `.pgf/DESIGN-HELIXCorpusSupply*.md`
- Date: 2026-07-15
- Mode: design-review, iterations 1-2/2
- Method: local sequential simulation of P5 Field Operator, P7 Contrarian Critic, P8 Convergence Architect

## Summary

세 관점 모두 구현 가능하다고 판정했다. 초기안에서 source 중복 우회, path traversal,
append 중단 복구, Condense threshold 권위 중복이 발견되었고 DESIGN에 반영했다.
PPR 사전 시뮬레이션에서 2회차에 manifest revision 전이 결함을 추가 발견해 반영했다.
수정 후 verdict는 `APPROVED`이며 `Critical=0`, `High=0`이다.

## Findings

### P5 Feasibility Reviewer — PASS after revision

- `[high][identity]` 동일 source를 다른 `corpus_id`로 등록하는 우회가 명시되지 않았다.
  `DuplicateSourceCheck`를 Generative Gate에 추가했다.
- `[medium][filesystem]` ID가 item path에 직접 사용된다. 안전한 ID 문법과 `SafeItemPath`를 추가했다.
- `[medium][evidence]` human review의 최소 계약이 불명확했다. `ReviewReceiptContract`를 추가했다.

### P7 Risk Reviewer — PASS after revision

- `[high][durability]` JSONL append가 중간 종료되면 tail 손상이 가능하다. v1을 single-writer로
  한정하고 `flush+fsync`, pre-append chain verification, malformed-tail fail-closed를 강제했다.
- `[medium][policy-drift]` 설계안의 3-project stop rule과 기존 Condense 5-project policy가
  충돌할 수 있다. 공급 plane은 threshold를 소유하지 않고 기존 router policy를 참조한다.
- `[high][evidence-truth][verify-rework-1]` 선언 SHA만으로는 존재하지 않는 source/license도
  admission될 수 있다. injected `evidence_root` 아래 실제 bytes hash 검증을 hard gate에 추가했다.
- `[high][revision-authority][verify-rework-1]` 새 revision이 prior Generative authority와 무관한
  내용을 치환할 수 있었다. `supersedes_manifest_sha256` binding을 Evidence gate에 추가했다.

### P8 Architecture Reviewer — PASS

- 기존 base-pairing corpus entry를 수정하지 않고 versioned 상위 plane을 추가한 경계가 적절하다.
- AI characterization과 deterministic admission이 분리되어 HELIX-Core 불변식과 일치한다.
- dual admission을 단일 mutable class가 아니라 독립 receipt로 모델링한 구조가 진화 가능하다.
- `[high][state-transition][iteration-2]` 단일 immutable manifest는 Generative admission 뒤
  구현 증거를 추가하는 Evidence promotion을 막는다. `revisions/N.json` immutable snapshot과
  latest `manifest.json` pointer, monotonic revision 계약으로 수정했다.

## Accepted Deferrals

- 다중 writer 직렬화는 v1 범위 밖이다. ledger verifier가 손상/경쟁 결과를 fail-closed한다.
- GitHub discovery와 repository checkout은 네트워크 meta-layer이며 이번 결정론 core에 포함하지 않는다.
- behavior probe 자동 생성과 machine clustering은 기존 Condense/evaluation plane에 남긴다.

## Review Verdict

```text
Critical: 0
High: 0 (5건 발견·전부 해소)
Medium unresolved: 0
Status: APPROVED
```

## Next Actions

1. WORKPLAN/status 생성
2. schema + deterministic core + CLI 구현
3. unit/CLI/full regression verification
