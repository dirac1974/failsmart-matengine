# Work Order

**This is the plan.** It says where the project stands, what to do next, and in what order. The detailed steps for each task are in the task files linked below. Updated 2026-11-16.

If you are a coding agent: read `AGENTS.md`, then this file, then the task file for the task you are about to do. Do not work from `docs/PLAN.md`; that file is the original design target and is kept for history.

---

## 1. Where the project stands

| Area | State |
|---|---|
| Honest labelling of every number (phase 1, T0 to T8) | Done |
| Calibrated gap estimate used by the pipeline | Done |
| Failure-evidence module, scorecards, evaluation rules | Done |
| Methodology review, gate audit, queue and window analysis | Done |
| Reconciling `main` with the reviewed work | Done on branch `integrate-main`; **waiting for the owner to merge it** (M1) |
| Phase-2 gaps G1 to G9 | **Not started** |
| Failure-data tasks F1 to F5 | Not started |
| Methodology tasks V2 to V10 | Not started |
| Any first-principles calculation | None has been run |

What the pipeline can and cannot say today: it produces a queue of candidates for calculation, with flags. It does not identify a working absorber. In the current run, 68 of 70 rejections rest on rules of thumb (see `METHODOLOGY_REVIEW_2026-11-15.md`); task V2 changes that.

---

## 2. Rules that apply to every task

1. **Never commit to `main`.** Create a branch from the latest `main`, open a pull request, and stop. The owner merges.
2. **Before starting, run `git fetch` and `git log origin/main -1`.** If `main` does not contain `docs/WORK_ORDER.md`, stop: M1 has not happened, and you are about to work on the wrong code.
3. **One task per pull request**, in the order of section 3.
4. **Code and outputs change together.** If a change alters what the pipeline produces, rerun it (`python -m failsmart_matengine.mp_live_discovery`) and commit the regenerated outputs in the same commit. `test_committed_outputs_are_what_the_code_produces` fails otherwise.
5. **A task is closed when** its expected-failure test passes, you delete that test's `xfail` marker in the same commit, and `pytest -q` passes in full.
6. **Never edit a test body to make it pass.** Update a pinned value only when the change legitimately moves it, and name the test in the commit message.
7. **Do not add a gate that rejects candidates** unless its evidence is database DFT, a calculation run here, or a measurement (rules R2 and R10). Everything else is a flag.
8. **Do not add features that are not in this file.** If an audit of yours finds something new, write it up in the pull request and ask the owner. Do not implement it unasked.
9. **Stop and ask the owner** at every step marked HUMAN GATE.
10. A passing auditor or test suite is not proof that outputs are current or that a claim is true. Say what you ran and what it showed.
11. The rules in `AGENTS.md` and section 0 of `METHODOLOGY_TASKS_V.md` apply.

---

## 3. Order of work

| Order | Task | What | Task file | Acceptance test |
|---|---|---|---|---|
| 1 | **M1** | Owner merges `integrate-main` into `main` | this file | (owner action) |
| 2 | M2 | Year-25 retention uses 25 years | this file | `tests/test_integration_main.py` |
| 3 | M3 | Sourced electronegativity values for halides and alkaline earths | this file | `tests/test_integration_main.py` |
| 4 | M4 | Remove the double attenuation of transmitted light | this file | `tests/test_integration_main.py` |
| 5 | M5 | Check two reported inconsistencies | this file | (report) |
| 6 | G1 to G9 | Phase-2 gaps, in the order given there | `REMEDIATION_TASKS_PHASE2.md` | `tests/test_gap_closure.py` |
| 7 | F1 to F5 | Failure-data tasks | `FAILURE_DATA_PLAN.md` | `tests/test_failure_evidence.py` |
| 8 | V2, V3, V6, V4, V5, V7, V8, V9, V10 | Methodology tasks, in that order | `METHODOLOGY_TASKS_V.md` | `tests/test_methodology_v.py` |

Why this order: M2 to M4 are small and remove known errors before larger work builds on them. G comes before F and V because F and V edit files that G changes. Within G, the run kit (G5) is what finally reduces the 0.44 eV gap error, so do not let later tasks delay it.

HUMAN GATES ahead: G5 (before any long run), V3 (Materials Project key), V4 (window decision), V10 and the run kit (before using another person's computer), and any cloud spend.

---

## 4. Tasks M1 to M5

### M1. Merge the integration branch (owner)

The pull request from `integrate-main` into `main` contains pull requests #1 to #5 and the reconciliation with the three commits pushed to `main` on 2026-11-16. Background: `CARBON_REVIEW_2026-11-16.md`.

1. Merge that pull request.
2. Close pull requests #1 to #5 as superseded (their commits are inside it).
3. Optional and recommended: in the repository settings, protect `main` so that changes need a pull request.

No agent does this step.

### M2. Year-25 retention uses 25 years

**Problem.** `evaluate_phase9c_real_world_lcoe_stress_test` in `failsmart_matengine/atomistic_and_tmm.py` computes `yr25_ret_pct = ((1.0 - r_deg) ** 24) * 100.0`. The second implementation in `independent_verifier.py` and the specification use 25.

**Steps.**

1. Change `** 24` to `** 25` on that line. Change nothing else in the function.
2. Rerun the pipeline and commit the regenerated outputs.
3. Update any test or document that pins the old value (expect about 91.9 to become about 91.6) and name each in the commit message.

**Acceptance.** `test_m2_year_25_retention_uses_25_years` passes.

### M3. Sourced electronegativity values for halides and alkaline earths

**Problem.** `MULLIKEN_CHI_EV` in `failsmart_matengine/realistic_commercialization.py` has ten elements. Candidates containing other elements get no contact estimate.

**Steps.**

1. Add exactly these values, in eV: `"Zn": 4.45`, `"Ba": 2.4`, `"Sr": 2.0`, `"Cl": 8.30`, `"Br": 7.59`, `"I": 6.76`.
2. Above the table add the comment: `# LITERATURE: Pearson, Inorg. Chem. 27, 734 (1988), doi:10.1021/ic00277a030`.
3. Do not add a default for unknown elements. The existing check that returns "not evaluated" when an element is missing stays.
4. If `independent_verifier.py` has its own copy of the table, add the same six values there and remove its `.get(el, 4.50)` default in favour of the same "not evaluated" behaviour.
5. Rerun the pipeline, commit the regenerated outputs, update pins.

**Do not** use 2.50 for Sr. That value was on `main` and is wrong.

**Acceptance.** `test_m3_electronegativity_table_covers_halides_with_sourced_values` passes.

### M4. Remove the double attenuation of transmitted light

**Problem.** In `failsmart_matengine/atomistic_and_tmm.py`, the coherent transmission already includes absorption in the top cell (its refractive index has an extinction part). The code then multiplies it by `(1.0 - fabs1)` again, in lines of the form `t_stack_... = t_... * (1.0 - fabs1)`.

**Steps.**

1. Find every such line: `grep -n "(1.0 - fabs1)" failsmart_matengine/atomistic_and_tmm.py failsmart_matengine/independent_verifier.py`.
2. For each line where the left factor is a coherent transmission returned by a transfer-matrix function (`t_tmm_1`, `t_arc_1`, `t_u`, and the equivalent inside the thickness loop), delete the `* (1.0 - fabs1)` factor.
3. Leave alone any line where the left factor is not a coherent transmission (for example the incoherent expression in `independent_verifier.py` that starts with `(1.0 - 0.020 - 0.020 - r_fresnel_1)`). There the factor is the only attenuation and is correct.
4. Rerun the pipeline, commit the regenerated outputs, update pins. Expect the silicon cell's share to rise slightly.
5. In the pull request, state the largest change in any tandem efficiency.

**Acceptance.** `test_m4_transmitted_light_is_not_attenuated_twice` passes.

### M5. Check two reported inconsistencies

Carbon's audit reported these. They were not re-checked. Check each and report in a pull request description; change code only if the report is confirmed and the fix is a single line.

1. **60-degree incidence ratio.** `atomistic_and_tmm.py` computes `iam_60` as an efficiency ratio; `independent_verifier.py` computes it as a front-transmittance ratio. If so, they are two quantities under one name. Fix: rename the second implementation's key to `front_transmittance_ratio_60deg` and stop comparing the two.
2. **Input power.** Check whether any efficiency in `realistic_commercialization.py` divides by 100 where the rest of the code uses the integrated spectrum power of 100.037. If so, use the same constant everywhere.

---

## 5. Changes to existing task files

- **G2** (`REMEDIATION_TASKS_PHASE2.md`): also generate the result tables in `outputs/failsmart_dashboard.html` from the summary file, the same way as the README block. No hard-coded result arrays.
- **V8** (`METHODOLOGY_TASKS_V.md`): one added step, a flag for facet-dependent band edges on low-dimensional structures.
- **V10**: unchanged. It replaces the spring-model stability check that Carbon's audit also criticised.

---

## 6. Prompt to give the implementing agent

> Run `git fetch`, check out the latest `main`, and confirm that `docs/WORK_ORDER.md` exists there. If it does not, stop and tell me. Read `AGENTS.md`, then `docs/WORK_ORDER.md`, then `docs/CARBON_REVIEW_2026-11-16.md`. Do the tasks in the order of section 3 of the work order, starting at M2. For each task: create a branch from the latest `main`, follow the steps in the task file exactly, run `pytest -q`, open a pull request, and stop. Never commit to `main`. Do not add anything that is not in the work order; if you find something new, describe it in the pull request and ask me. Stop and ask me at every HUMAN GATE. In each pull request say which `xfail` marker you removed, which outputs you regenerated, and which pinned values changed and why.
