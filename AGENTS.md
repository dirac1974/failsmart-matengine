# Notes for coding agents

## Read first, in this order

1. `docs/LESSONS_LEARNED.md`: mistakes this project already made. Do not repeat them.
2. `docs/AUDIT_2026-11-15_READINESS.md`: current state, what is closed and what is open (gaps G1 to G9).
3. `docs/REMEDIATION_TASKS_PHASE2.md`: the task list for the open gaps, with acceptance checks.
4. `tests/test_gap_closure.py`: the acceptance tests. Open gaps are strict expected failures.

Older context: `docs/INDEPENDENT_AUDIT_2026-11.md` and `docs/REMEDIATION_TASKS.md` (phase 1, tasks T0 to T13).

## State of the repository

- The pipeline runs no first-principles calculation. Band gaps come from, in order: a measured value for the same Materials Project entry, a gap computed with the DFT run kit (once it exists), or a calibrated estimate with a 0.44 eV error bar (`failsmart_matengine/gap_model.py`).
- With an estimated gap the shortlist is a queue for calculation, not a list of predicted absorbers.
- The "agents" in the code are role labels in a deterministic script. There are no LLM calls.

## Rules

- Do not write a number that no code or cited source produced. Use `None` and "not evaluated".
- Do not name anything after a method that was not run.
- Tag every reported quantity with its provenance: `MP_DFT`, `LITERATURE`, `COMPUTED_HERE`, `HEURISTIC`, `ASSUMED` (and `MLIP` once task G6 adds it).
- A check is verification only if it uses a different method or data source.
- Do not edit a test body to make it pass. When a fix changes a value a test pins, update the pin in the same commit and say why. Prefer replacing pins with consistency checks (lesson L8).
- When you close a gap, delete its `xfail` marker in `tests/test_gap_closure.py` in the same commit.
- Markdown in `README.md` and `docs/` must pass the dollar-sign and macro checks (Test 21 in `tests/test_scientific_integrity.py`).
- Ask the repository owner before cloud spend, before long runs on someone else's computer, before deleting committed data, and before changing the project's direction.
- In commit messages and comments, refer to the assistant as "Claude" only, with no model name.

## Before you finish: record lessons and update memory

1. **Lessons file (always).** If you hit a mistake, a misleading result, a check that should have existed, or a rule in this file that was unclear, add an entry to `docs/LESSONS_LEARNED.md` in the format at the top of that file. If nothing new happened, say so in your final message.
2. **Your own memory (if your tool has one).** Save the rules from `docs/LESSONS_LEARNED.md` that would apply to other scientific-computing projects, phrased generally, for example "never label a heuristic with the name of a first-principles method" and "a re-implementation of the same formula is not verification". Save project facts only as project facts (this repository's state), not as general rules.
3. **Status.** Update the Status table in `docs/REMEDIATION_TASKS_PHASE2.md` and list in your pull request which gap tests now pass.

## Commands

```bash
pip install -e ".[dev]"
pytest -q                                   # all tests
pytest -q tests/test_gap_closure.py -rxX    # gap status: x = still open, X = closed but marker not removed
python -m failsmart_matengine.repo_auditor
python -m failsmart_matengine.gap_model     # refit the gap model from data/gap_benchmark.csv
python -m failsmart_matengine.mp_live_discovery
```
