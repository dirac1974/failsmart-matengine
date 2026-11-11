# Notes for coding agents

Read these two files before changing anything:

1. `docs/INDEPENDENT_AUDIT_2026-11.md`: what in this repository is real, heuristic or synthetic, with file and line evidence.
2. `docs/REMEDIATION_TASKS.md`: the ordered task list (T0 to T13), with exact locations, acceptance checks and kill criteria. Update its Status table as you go.

## State of the repository

- No DFT, hybrid-functional, machine-learned-potential, phonon, NEB or defect calculation runs here. Values labelled that way are heuristics or constants.
- The "agents" are role labels in a deterministic script. There are no LLM calls.
- The README and docs were relabelled in November 2026. Code, schema field names and generated outputs still use the old names (task T2).
- The relabelling patch was not run against the test suite. Task T0 checks it.

## Rules

- Do not write a number that no code or cited source produced. Use `None` and "not evaluated".
- Do not name anything after a method that was not run.
- Tag every reported quantity with its provenance: `MP_DFT`, `LITERATURE`, `COMPUTED_HERE`, `HEURISTIC` or `ASSUMED`.
- A check is verification only if it uses a different method or data source.
- Do not weaken a test to make it pass. If a fix legitimately changes a pinned value, update it in the same commit and say so.
- `failsmart_matengine/repo_auditor.py` asserts on specific README and docs strings. The list is in `docs/REMEDIATION_TASKS.md`. Keep those strings until task T2 changes the assertions.
- Markdown in `README.md` and `docs/` must pass the dollar-sign and macro checks described in `docs/REMEDIATION_TASKS.md`.
- Ask the repository owner before tasks marked HUMAN GATE (cloud spend, project direction) and before deleting committed data.

## Commands

```bash
pip install -e ".[dev]"
pytest -q
python -m failsmart_matengine.repo_auditor
python -m failsmart_matengine.orchestrator          # v2 pilot (synthetic fixtures)
python -m failsmart_matengine.mp_live_discovery     # v3+ funnel on the cached Materials Project records
```

In commit messages and comments, refer to the assistant as "Claude" only, with no model name.
