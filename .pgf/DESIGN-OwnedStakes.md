# OwnedStakes Design @v:1.0

## Intent

Complete the provenance ladder's top rung. `real_owned_stakes` is the ONLY grade
that flips `is_t4_utility` true, so an *asserted* (unbacked) claim would fabricate
a T4 utility signal — the highest-stakes forgery in the system. This layer makes
the grade **earnable, not assertable**, exactly as `core/helix_fidelity.py` did
for `fidelity_attested`, but with a stricter independence rule.

The methodological pivot (why independence differs from fidelity):

> `fidelity_attested` is about the *authenticity of a reproduced judgment* — the
> wedge author CAN validly attest whether an AI reproduced HIS perspective, so
> dogfooding is allowed with a conflict flag (weak-but-real).
>
> `real_owned_stakes` is about *utility under owned consequences*. If the party
> judging utility is the party who built/owns the wedge, it is self-dealing, not
> a market signal. So independence is a HARD requirement here: an operator who is
> the wedge author is DISQUALIFIED, not merely flagged. This is the causal-
> independence axis applied to its sharpest case.

Honest ceiling (unchanged): a single verified `real_owned_stakes` receipt is a
`utility_candidate`, NOT a T4 pass. The full T4 verdict still requires the
multi-participant pilot gate (`docs/PILOT-PROTOCOL.md`). This layer verifies one
operator's owned-stakes evidence is real and independent; it does not, by itself,
declare T4 passed.

## Gantree

```text
OwnedStakes // real_owned_stakes 등급을 획득으로 (designing) @v:1.0
    OperatorIndependence // 판정 주체 != wedge 소유자 (designing)
        HardIndependence // operator.id != wedge_author_id, 예외 없음 (designing)
        NoDogfooding // dogfooding = 자격 박탈 (fidelity와 반대) (designing)
    RealWork // 실제 업무 증거 (designing)
        LedgerBinding // 실 actuation ledger head hash + decision_count>0 (designing)
        NotSimulated // stakes=real 강제, simulated 거부 (designing)
    ObjectiveOutcomes // 자기서술 아닌 객관 측정 (designing)
        Measures // prevented_invalid/admitted/excluded 정수 (designing)
        ReplayVerified // 실 판정이 재현됨 (designing)
    OwnedStakesGrade // 위 전부 만족 시에만 real_owned_stakes (designing) @dep:OperatorIndependence,RealWork,ObjectiveOutcomes
        UtilityGuard // 획득 시 is_t4_utility 자격; 단일 operator=candidate (designing)
        DowngradeUnbacked // 뒷받침 없는 주장은 aggregate에서 강등 (designing)
```

## PPR

```python
def attest_owned_stakes(operator, wedge_author_id, real_work, outcomes,
                        stakes_owned) -> OwnedStakesAttestation:
    """An independent operator attests running the wedge on real work.

    acceptance_criteria:
      - operator.id non-empty and != wedge_author_id (HARD independence, no
        dogfooding exception — self-use is not a utility signal)
      - real_work.decision_count > 0, bound to a real ledger head sha256,
        not simulated
      - outcomes are objective measures (integer counts) + replay_verified,
        not self-reported adoption sentiment
      - stakes_owned is a non-empty statement of the real consequence borne
    """
    require(operator["id"] != wedge_author_id)
    require(real_work["decision_count"] > 0 and not real_work.get("simulated"))
    require(outcomes["replay_verified"] is True)
    return seal({operator, wedge_author_id, real_work, outcomes, stakes_owned})


def owned_stakes_grade(attestation) -> str:
    """The grade earned. real_owned_stakes only when independent + real + objective.

    acceptance_criteria:
      - attestation seal valid
      - operator independent of author
      - real ledger binding present, decision_count>0, not simulated
      - replay_verified true
      - else -> simulated_unverified (an unbacked/self-dealing claim earns nothing)
    """


def earn_owned_provenance(attestation) -> dict:
    """provenance dict with a DERIVED grade + real stakes, for the adoption trial.

    acceptance_criteria:
      - grade derived from attestation, never asserted
      - stakes == "real" (this is the rung where stakes are genuinely owned)
      - carries attestation_sha256 so aggregate can verify the claim
    """
```

## Invariants

- Independence is HARD for real_owned_stakes (operator != author, no dogfooding),
  in deliberate contrast to fidelity_attested where dogfooding is allowed+flagged.
- Only VERIFIED owned-stakes evidence flips is_t4_utility. aggregate_adoption,
  when given attestations, downgrades unbacked real_owned_stakes claims — a bare
  label cannot fabricate a T4 utility signal.
- A single operator's real_owned_stakes = utility_candidate, not T4 passed. The
  multi-participant T4 gate lives in the pilot protocol, not here.
- Deterministic, stdlib only: no clock/network/subprocess/randomness/AI. The
  module validates, seals, binds, and grades; it does not fetch external ledgers
  (the ledger head hash is recorded/verified where the ledger is present).
- The trial never upgrades its own grade — the upgrade is a function of an
  external, independent operator's attestation.

## Verification plan

- Determinism: same inputs -> same seal.
- operator == author -> ValueError (hard independence).
- simulated real_work / decision_count 0 -> rejected.
- replay_verified false -> not real_owned_stakes.
- valid independent attestation -> real_owned_stakes; earn_owned_provenance
  stakes == "real".
- integration: earned receipt -> aggregate honors it (is_t4_utility true,
  utility_candidate); unbacked claim -> downgraded to simulated_unverified.
- fidelity path unaffected (regression).
- full regression + helix_validate.
```
