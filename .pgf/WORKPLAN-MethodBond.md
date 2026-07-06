# WORKPLAN — MethodBond

## POLICY

- max_verify_cycles: 2
- stdlib_only: true
- min_tests: 20
- output_dir: D:\HELIX\MethodBond

## Nodes

1. CreateProjectDir (status: in-progress)
   # criteria: D:\HELIX\MethodBond exists with MethodBond/ and tests/ subdirs.

2. WriteEngine (status: in-progress) @dep:CreateProjectDir
   # criteria: MethodBond/engine.py implements CheckLicense, CheckReproducibility, CheckCertification, ComposeVerdict, evaluate().

3. WriteCLI (status: in-progress) @dep:WriteEngine
   # criteria: MethodBond/cli.py exposes sample/evaluate/report argparse subcommands.

4. WriteReport (status: in-progress) @dep:WriteEngine
   # criteria: MethodBond/report.py renders Markdown verdict report.

5. WriteLedger (status: in-progress) @dep:WriteEngine
   # criteria: MethodBond/ledger.py implements append-only SHA-256 chained log.

6. WriteInitAndMain (status: in-progress) @dep:WriteCLI
   # criteria: __init__.py exports engine.evaluate; __main__.py calls cli.main().

7. WriteTests (status: in-progress) @dep:WriteEngine,WriteCLI,WriteLedger
   # criteria: tests/test_engine.py and tests/test_cli.py together have ≥20 passing tests.

8. WritePackaging (status: in-progress) @dep:CreateProjectDir
   # criteria: pyproject.toml, README.md, LICENSE (MIT), .gitignore exist.

9. RunValidation (status: in-progress) @dep:WriteTests,WritePackaging
   # criteria: py_compile all .py; unittest discover passes; helix_validate.py . passes.

10. UpdateBackbone (status: in-progress) @dep:RunValidation
    # criteria: ledger.json, corpus.json, registry.json, latest.json updated; close-loop recorded.

11. GitInitAndPush (status: in-progress) @dep:UpdateBackbone
    # criteria: git init, commit, gh repo create, push, topics added.
