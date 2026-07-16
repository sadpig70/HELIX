# AttestraImplementationPatchPlan Design @v:1.0

## Gantree

```text
AttestraImplementationPatchPlan // implementation patch plan for five Phase 4 Attestra packs (designing) @v:1.0
    P0EntryGate // consume validated Attestra lane contract and target repo structure (designing)
    P1PatchSurface // identify exact Attestra files to add or modify (designing) @dep:P0EntryGate
    P2PackModulePlan // define pack module predicates and samples for five packs (designing) @dep:P1PatchSurface
    P3SchemaPlan // define structural packet schemas for five packs (designing) @dep:P2PackModulePlan
    P4ParityTestPlan // define source parity tests and registry tests (designing) @dep:P3SchemaPlan
    P5VerificationPlan // define commands and stop gates for implementation batch (designing) @dep:P4ParityTestPlan
```

## PPR

```python
def P0EntryGate(contract: dict, attestra_tree: dict) -> dict:
    """Authorize a patch plan only when the lane contract is validated and Attestra supports pack auto-discovery."""
    assert contract["target_platform"] == "Attestra"
    assert contract["decision"]["kernel_change_allowed"] is False
    assert "attestra_packs/loader.py" in attestra_tree["files"]
    return {"authorized": True, "mode": "plan_only"}

def P1PatchSurface(contract: dict) -> dict:
    """Map every pack to module, schema and parity test files."""
    patch = AI_map_contract_to_attestra_file_surface(contract)
    # criteria: 5 modules, 5 schemas, 5 parity tests, 1 registry test update, 0 kernel files
    return patch

def P2PackModulePlan(contract: dict) -> dict:
    """Design pure predicate functions and SAMPLES for Attestra pack modules."""
    modules = AI_design_predicates(contract)
    # criteria: MANIFEST/PREDICATES/SAMPLES present; valid/thin/breach samples aggregate correctly
    return modules

def P3SchemaPlan(contract: dict) -> dict:
    """Design structural-only JSON schemas for pack packets."""
    schemas = AI_design_structural_schemas(contract)
    # criteria: schema only validates shape/types; policy completeness remains in predicates
    return schemas

def P4ParityTestPlan(contract: dict) -> dict:
    """Define tests that compare source project examples to Attestra mapped verdicts."""
    tests = AI_design_parity_tests(contract)
    # criteria: 15 fixture rows, source import optional, CI skip when source unavailable
    return tests

def P5VerificationPlan(patch_plan: dict) -> dict:
    """Gate the future implementation batch."""
    return {
        "must_pass": [
            "python cli.py pack list",
            "python -m unittest discover -s tests -q",
            "git diff --check",
        ],
        "must_not_touch": patch_plan["kernel_files_forbidden"],
    }
```

## Acceptance criteria

- The plan names exact Attestra target files.
- The plan preserves `zero-kernel-change`.
- The plan maps all 15 validated source fixtures to Attestra verdicts.
- The plan declares implementation stop gates before modifying Attestra.
- Verification is based on executable Attestra and HELIX checks.

