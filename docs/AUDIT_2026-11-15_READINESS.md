# Readiness Audit and Calibration Fix (2026-11-15)

**Scope:** branch `calibration-and-dft-kit`, stacked on `remediation/t0-t8` (pull request #2), which is stacked on `audit/relabel-2026-11` (pull request #1). Nothing is merged to `main`.

**Method:** the code was installed and run. Results below come from `pytest`, the repository auditor and `python -m failsmart_matengine.mp_live_discovery`. Error statistics were recomputed independently from `data/gap_benchmark.csv`.

**Companion files:** [`REMEDIATION_TASKS_PHASE2.md`](REMEDIATION_TASKS_PHASE2.md) (what to do), [`../tests/test_gap_closure.py`](../tests/test_gap_closure.py) (how to prove it is done), [`LESSONS_LEARNED.md`](LESSONS_LEARNED.md) (how not to repeat it).

---

## 1. Verdict

The phase-1 remediation (pull request #2) made the repository honest: labels match what the code does, every number has a provenance tag, the deck generators are fixed, external-reference tests exist, and the cost model states requirements instead of forecasts.

It did not make the screen useful. The calibration was computed but not used, and measured gaps already in the repository were ignored. This branch fixes that. The remaining gaps are listed in section 4 and are all tested.

The scientific limit is unchanged: with only Materials Project PBE gaps and composition, the band-gap error is about 0.44 eV against target windows 0.15 to 0.20 eV wide. The pipeline can exclude candidates and order a calculation queue. It cannot predict absorbers until real first-principles gaps are computed (gap G5).

---

## 2. What was wrong with the phase-1 calibration

| # | Problem | Evidence | Effect |
|---|---|---|---|
| 1 | The pipeline used the old formula | `mp_live_discovery.py` Stage 4 applied `PBE + 0.31 + 3.30/eps - soc`; the refit lived only in `data/gap_benchmark.csv` | Mean error 0.45 eV, Cu/Ag bias -0.54 eV, in the shipped results |
| 2 | The error bar was a mean absolute error used as a standard deviation | `gap_err_bar = 0.37` (leave-one-out MAE) fed into a normal CDF | Window probabilities overstated |
| 3 | Measured gaps were ignored | `data/finalist_literature.json` and the benchmark's measured column were never read by the pipeline | CuBiS2 (measured 1.65 eV) and CuSbSe2 (1.10 eV) shipped as 0.70 to 0.85 eV bottom-cell finalists |
| 4 | Optical thresholds re-imposed a hard window | The optical gate (SLME, transmittance) depends only on the gap, and rejected candidates whose gap was estimated | Undid the probabilistic gate |
| 5 | Layer assignment used a hard 1.25 eV cut on the estimate | `target_layer = TOP if gap >= 1.25 else BOTTOM` | Arbitrary at the boundary |
| 6 | Pull request #2's description misstated results | Named `mp-556527` CuPbBi5S9 (not in outputs; the element policy bans Pb), gave a refit formula that is not the one in the code, and cited a 0.4522 eV MAE for the raw PBE gap (it is 0.7555 eV; 0.4522 eV is the old heuristic) | Owner reading the description gets wrong numbers |

---

## 3. What this branch fixed (closed gaps C1 to C7)

| ID | Fix | Where | Test |
|---|---|---|---|
| C1 | Reproducible gap model: `python -m failsmart_matengine.gap_model` refits from the benchmark and writes `data/gap_model.json` | `failsmart_matengine/gap_model.py` | `test_c1_committed_gap_model_matches_a_fresh_fit` |
| C2 | Error bar is the leave-one-out RMSE (0.44 eV) | `gap_model.fit_from_benchmark` | `test_c2_error_bar_is_leave_one_out_rmse_not_mae` |
| C3 | Pipeline uses the calibrated model | `_estimate_gap_from_mp_pbe` calls `gap_model.resolve_gap` | `test_c3_pipeline_uses_the_calibrated_model_for_estimated_gaps` |
| C4 | Measured gap for the same entry overrides the estimate (`gap_basis = LITERATURE`); computed gaps will too (`COMPUTED_HERE`, read from `data/dft_results.json`) | `gap_model.resolve_gap` | `test_c4_measured_gap_overrides_the_estimate` |
| C5 | Optical thresholds reject only measured or computed gaps; layer is the one with the higher window probability | `build_live_mp_candidate_dossier` | `test_c5_optical_thresholds_never_reject_an_estimated_gap` |
| C6 | Ranked shortlist: `ranked_shortlist` in the summary, ordered by window probability, with a DFT queue headed by synthesised phases and the maximum achievable probability stated | `build_ranked_shortlist` | `test_c6_shortlist_is_ranked_and_honest_about_resolution` |
| C7 | Lessons file and memory instructions for future agents | `docs/LESSONS_LEARNED.md`, `AGENTS.md` | `test_c7_lessons_file_and_memory_instructions_exist` |

### 3.1 Calibration figures (recomputed, 50 benchmark compounds)

| Model | Leave-one-out MAE (eV) | Leave-one-out RMSE (eV) | Leave-one-family-out MAE (eV) |
|---|---|---|---|
| Raw Materials Project PBE gap | 0.756 (in-sample) | 0.893 | not applicable |
| Old heuristic (shipped until now) | 0.452 (in-sample) | 0.565 | not applicable |
| Calibrated model (now used) | 0.367 | 0.436 | 0.419 |

Five alternative linear models with Cu/Ag, heavy-element, halide and oxygen terms were cross-validated; none beat the calibrated form on leave-one-family-out error. The non-negative fit sets the dielectric coefficient to zero, so the model is `E_PBE + 1.238 - 2.933 * soc_raw`.

### 3.2 Result on the cached Materials Project records

- Funnel `100 -> 91 -> 50 -> 43 -> 30` (was `100 -> 91 -> 47 -> 40 -> 15`).
- **30 not excluded** (23 top, 7 bottom). All have estimated gaps, with window probabilities 0.09 to 0.18. Maximum achievable: 0.18 (top), 0.14 (bottom).
- **3 excluded by a measured gap:** CuBiS2, CuSbSe2, AgBiSCl2.
- **DFT queue** (synthesised phases first): mp-1195160 Al2Bi2Cu2S3Cl8, mp-540644 Sn4SI6, mp-559521 Bi2InS4Cl, mp-23474 AgBi3S5, mp-27916 AgBiSe2, mp-559071 Ag2Bi2S3Cl2, mp-558368 AgBi2S3Cl, then theoretical entries.
- Device models (optics, cost) now run on 4 exemplars per layer (16 pairs). They add no selection power.

### 3.3 Verification status on this branch

| Check | Result |
|---|---|
| `pytest -q` (existing 41 tests, pins updated for the new funnel) | 41 passed |
| `pytest -q tests/test_gap_closure.py` | 7 passed, 9 expected failures (open gaps G1 to G9) |
| `python -m failsmart_matengine.repo_auditor` | **Fails** on pinned values from the previous run (gap G1) |

---

## 4. Open gaps (G1 to G9)

Each has a strict expected-failure test in `tests/test_gap_closure.py` and a task in `REMEDIATION_TASKS_PHASE2.md`.

| ID | Gap | Why it matters | Priority |
|---|---|---|---|
| G1 | The repository auditor pins dozens of numbers from one past run (funnel counts 47/40/15, 56 pairs, efficiencies 42.32%, 42.22%, 41.71%, 43.08%, 40.71%, `CER` 4.420) and now fails | The auditor cannot be used, and the pins invite editing numbers to pass (lesson L8) | 1 |
| G2 | README and docs quote the old run's results | Readers see stale figures | 2 |
| G3 | A theoretical entry whose composition has a measured polymorph is not flagged (Sb2OS2 C2/m vs kermesite P-1, 2.04 eV) | The most-cited top candidate's chemistry has a known gap outside the window | 3 |
| G4 | Carrier-mass, Frohlich and defect-depth heuristics still reject candidates | Uncalibrated heuristics act as gates (lessons L4, L7) | 4 |
| G5 | No DFT run kit; `data/dft_results.json` does not exist | The pipeline cannot improve beyond 0.44 eV without it | 5 |
| G6 | No GPU path; no `MLIP` provenance tag | The owner's GPU (8 GB laptop, possibly a friend's 32 GB card) is unused | 6 |
| G7 | No continuous integration | Regressions go unnoticed | 7 |
| G8 | v2 pilot tables still commented as "ground-truth" (old task T9) | Synthetic values look like data | 8 |
| G9 | Failure ledger wiped every run (old task T11) | "Learns from failure" remains false | 9 |

Also outstanding but outside the tests:

- **Pull request #2's description** needs the corrections in section 2, row 6. The owner (or an agent with GitHub access) should edit it before merging.
- **Old tasks T10 and T12** (rename the verifier to a self-consistency checker; lockfile and module splits) remain from phase 1.
- **The benchmark has 50 compounds.** Expanding it toward 80 to 100 would tighten the family-level error estimate; it will not remove the 0.44 eV floor.

---

## 5. Hardware notes for G5 and G6

The owner has a ThinkPad P16v Gen 3 (Core Ultra 7/9, 6 performance and 10 efficiency cores, 64 GB RAM, RTX PRO 1000 or 2000 Blackwell with 8 GB) that must keep its current operating system, and may have access to a friend's PC with an RTX 5090 (32 GB).

- Linux tools run under WSL2 (a lightweight VM built into Windows). CUDA works in WSL2 with the normal NVIDIA Windows driver.
- PyTorch-based machine-learned potentials (MACE) run on the GPU with little effort; 8 GB covers cells of a few hundred atoms.
- Quantum ESPRESSO has a GPU build (NVIDIA HPC SDK). Whether its hybrid-functional plus spin-orbit path is GPU-accelerated could not be confirmed from the release notes; the kit must benchmark CPU against GPU on a small case before long runs.
- PBEsol plus spin-orbit on 7 to 20 atom cells fits the laptop. Hybrid-functional runs on 10 to 40 atom cells are overnight-to-days jobs on the laptop and the main reason to use the 5090 or cloud.
- Long runs on the friend's computer need the owner's approval each time.

Sources for section 5: Quantum ESPRESSO releases (https://github.com/QEF/q-e/releases), NERSC Quantum ESPRESSO notes (https://portal.nersc.gov/cfs/m1660/ksa/wrfsig/nersc.gitlab.io/public/applications/quantum-espresso/), QE GPU build guide (https://github.com/QEF/q-e/blob/develop/README_GPU.md).
