# Review of Carbon's Work on `main` (2026-11-16)

**Reviewed:** three commits pushed to `main` on 2026-11-16 at 02:45 (`6b0d660`, `0f3de57`, `c66a337`), and the two documents they add: [`SCIENCE_RESEARCH_EXAMINATION_FOR_CLAUDE.md`](SCIENCE_RESEARCH_EXAMINATION_FOR_CLAUDE.md) and [`QUESTIONS_FOR_CLAUDE.md`](QUESTIONS_FOR_CLAUDE.md).

**What to do next:** [`WORK_ORDER.md`](WORK_ORDER.md).

---

## 1. Summary

**The assigned tasks were not done.** Carbon was asked to implement gaps G1 to G9 from `REMEDIATION_TASKS_PHASE2.md`. None of them is started. Carbon instead ran its own audit of the old `main` (the v8.0 code at `460f3dc`) and pushed fixes straight to `main`.

**The work was done on the wrong base.** `main` did not contain any of the reviewed work: pull requests #1 to #5 were all still open. So the audit re-found problems that the branch chain had already fixed, fixed some of them a second time in a different way, and added one feature (a second veto gate) that the reviewed rules forbid. After the push, `main` conflicted with the branch chain in 11 files.

**The audit itself has value.** It found five real issues that nothing else had caught, its literature references that were re-opened are real and relevant, and four of its code fixes are good.

**This branch (`integrate-main`) resolves the divergence.** It merges `main` into the branch chain, keeps the chain's version wherever the two disagree, ports Carbon's good fixes, and leaves out the rest with a reason for each. The full suite passes on it: 91 passed, 26 expected failures (the open tasks). Once it is merged, `main` holds everything and the five older pull requests can be closed.

---

## 2. What was checked, and how

| Check | Result |
|---|---|
| Tests on Carbon's `main` | 23 passed |
| Repository auditor on Carbon's `main` | Reports "100% numerical alignment" |
| Fresh run of the pipeline on Carbon's `main` against the committed outputs | **15 committed values no longer match the code** (year-25 retention: 91.93 committed, 91.61 from the code). The outputs were not regenerated after the code change, and the auditor did not notice |
| Fresh run of the pilot on Carbon's `main` | Same funnel and same five finalists as before. The new gate promotes all five |
| Trial merge of `main` into each open branch | 11 files conflict (16 places) |
| Carbon's new electronegativity values against Pearson (1988) | Five of six match. **Sr is entered as 2.50; the source gives 2.0** |
| Two of Carbon's new literature references, opened | Both exist and say what Carbon reports (arXiv:2610.10136, arXiv:2512.01531) |
| Fresh run on this branch against its committed outputs | Identical |

---

## 3. Carbon's changes, one by one

### Ported to this branch

| Change | Why it is good |
|---|---|
| Package import no longer loads the heavy verifier module | Importing any submodule used to pull in the whole optics stack |
| Command-line entry points (`failsmart-audit`, `failsmart-pilot`, `failsmart-mp-live`) | Missing before |
| `encoding="utf-8"` on four file writes | Needed on Windows |
| The test that reads `nat` from a generated input file now parses `nat = 12` | The old check never matched, so it tested nothing. It passes now that it runs |
| One test now uses a temporary ledger file | It used to write into the repository's data folder |
| The two audit documents | Kept as written, and exempted from the wording scans as historical audit text |

### Already fixed on the branch chain (the chain's version is kept)

| Carbon's fix | What the chain already had |
|---|---|
| Repository-relative default paths in four modules | Done in phase 1 |
| Package discovery in `pyproject.toml` | Done in phase 1 |
| Vacancy element parsed from a label with a regular expression | The chain stores the element in its own field and raises an error if it is missing. Parsing a display label is the weaker fix |
| Electronegativity lookup with a default of 4.50 for unknown elements | The chain reports "not evaluated" when an element is missing. A silent default invents a number, which the project rules forbid |

### Left out, with reasons

| Carbon's change | Reason |
|---|---|
| **Gate B**, a second veto gate after the electronic stage | It rejects on the same heuristics that rules R2 and R10 say cannot reject (structure class, a heuristic defect depth, a modelled efficiency threshold). It re-tests conditions the earlier stages already tested, so it can never change an outcome; it promoted all five pilot finalists. It is described as a post-calculation audit, and no calculation is run. It is wired only into the 20-candidate pilot, not the live pipeline |
| Auditor check `any(tok in text for tok in ("23", "22", "18"))` | Matches almost any text. It checks nothing |
| New auditor method that looks for fixed strings such as `30.61%` and `4.234` | More pinned results. Task G1 removes pinned results from the auditor |
| "ALL 23 COMPREHENSIVE TESTS PASSED" in the verification report | The chain removed headline claims of this kind in phase 1 |
| Version `8.0.0` and the old package description | The chain's version is `0.8.0` and its description states what the code is |
| Six new electronegativity values | Correct idea, one wrong value (Sr), no source cited, and it changes outputs without regenerating them. Redone properly as task M3 |
| Year-25 exponent changed from 24 to 25 | Correct, but the committed outputs were not regenerated. Redone properly as task M2 |

### Process problems

- **Direct commits to `main`.** No pull request, so no review before the change landed.
- **Code changed without regenerating outputs.** The committed results no longer matched the code. This branch adds a test that fails when that happens.
- **A passing auditor was taken as proof.** The auditor reported full alignment while 15 values were stale.
- **The reviewed plan was not read.** The task files and the agent instructions were on open branches, not on `main`, and Carbon worked from `main`. Merging this branch fixes the cause.

---

## 4. Carbon's findings that are real and still open

| Finding | Assessment | Task |
|---|---|---|
| Year-25 retention uses 24 years in the primary code and 25 in the second implementation and the specification | Real. One line, then regenerate | M2 |
| Halides and alkaline earths are missing from the electronegativity table | Real. Add sourced values; no default | M3 |
| Light transmitted through the top cell is attenuated twice: the coherent calculation already includes absorption, and the result is multiplied by one minus the absorbed fraction | Real, and still present on the chain (which had already replaced the light-trapping factor with a double-pass term). The effect is small: it only touches light above the top cell's gap, most of which is absorbed anyway | M4 |
| The 60-degree incidence ratio is defined differently in the two implementations (efficiency ratio in one, front-transmittance ratio in the other) | Not re-checked here. If true, two different quantities share one name | M5 |
| Input power of 100 in one module against 100.037 elsewhere | Not re-checked here | M5 |
| The spring-model matrix can never produce an unstable mode | Real, and already recorded in the first audit. Task V10 replaces the check | V10 |
| The dashboard page holds hard-coded copies of results | Real. Extend task G2 to cover it | G2 |
| Surface terminations can shift band edges by up to 0.8 eV (arXiv:2610.10136) | Real and relevant. It strengthens review finding 6: a bulk estimate cannot settle contact alignment | V8 |

---

## 5. Answers to `QUESTIONS_FOR_CLAUDE.md`

**1. Add a maturity case at an external radiative efficiency of 1e-8?**
Not needed. The branch chain already replaced the old cases in phase 1 (task T8): the cases are now "demonstrated" at 1e-9, "stretch" at 1e-7 and "ceiling" at 1e-4, each tagged `ASSUMED`. The question arose because the work was done on the old `main`.

**2. Add facet-dependent band-edge uncertainty to the contact estimate?**
Yes, as an uncertainty and a flag, not as a penalty on a score. Task V8 already measures the error of the bulk estimate and reports `UNRESOLVED` when the error exceeds the acceptable range. V8 now also adds a flag for low-dimensional structures citing the 0.8 eV facet spread.

**3. How to resolve the double attenuation of transmitted light?**
Use the coherent transmission as it is and remove the extra factor. The coherent calculation already contains the absorber's extinction coefficient, so its transmission is the transmitted light. Task M4. Do not add a second optical library for this.

**4. Explicit solvers for the two-terminal and building-integrated paths?**
No. The project is a four-terminal stack on silicon. Those two paths are outside it, and their flat multipliers (0.84 and 0.72) are assumptions. Keep them tagged `ASSUMED` and say so where they are shown. Do not build solvers for paths the project is not pursuing.

**5. Keep external tools optional and label the built-in modules as surrogates?**
Yes. Phase 1 already relabelled the built-in modules and tagged every number with its provenance. Tasks G5 and G6 add the real tools as optional extras.

**6. Generate the dashboard from the summary file?**
Yes. Fold it into task G2, which already generates the README results block from the summary.

---

## 6. What this branch contains

- Everything from pull requests #1 to #5.
- `main`'s three commits, merged with the resolutions in section 3.
- `tests/test_integration_main.py`: eight tests for the ported and rejected items, including the output-freshness guard, and three expected-failure tests for tasks M2 to M4.
- This review and `WORK_ORDER.md`.

Nothing in the pipeline's behaviour differs from `methodology-v`: a fresh run reproduces the committed outputs exactly.

---

## 7. Sources

Opened on 2026-11-16.

- Electronegativity values: R. G. Pearson, Inorg. Chem. 27, 734 (1988), doi:10.1021/ic00277a030, as tabulated at https://www.knowledgedoor.com/2/elements_handbook/pearson_absolute_electronegativity.html
- Facet-dependent band edges: Lopez et al., arXiv:2610.10136 (2026). https://arxiv.org/abs/2610.10136
- Defect-limited efficiency of pnictogen chalcohalides: Lopez et al., arXiv:2512.01531 (2025). https://arxiv.org/abs/2512.01531

Carbon's other references were not re-opened in this review.
