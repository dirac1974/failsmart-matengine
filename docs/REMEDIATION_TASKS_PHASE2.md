# Remediation Tasks, Phase 2 (agent-ready)

For an engineer or coding agent picking this up cold. Findings are in [`AUDIT_2026-11-15_READINESS.md`](AUDIT_2026-11-15_READINESS.md); lessons are in [`LESSONS_LEARNED.md`](LESSONS_LEARNED.md). Read both first.

## How to work

1. Branch from `calibration-and-dft-kit` (or `main` if it has been merged). Name it `phase2/<your-name>`.
2. Work in the order below. One gap per commit, message `G<n>: <summary>`.
3. A gap is closed when its test in `tests/test_gap_closure.py` passes **and** you have deleted its `@pytest.mark.xfail(strict=True, ...)` line in the same commit. Never edit the test body to make it pass; if a test is wrong, stop and explain why.
4. After every gap: `pytest -q`, `pytest -q tests/test_gap_closure.py -rxX`, and (from G1 on) `python -m failsmart_matengine.repo_auditor`. All must pass, with only the still-open gaps reported as `XFAIL`.
5. Update the Status table below with one line per gap.
6. Stop and ask the repository owner at every **HUMAN GATE**.
7. Before finishing, follow "Before you finish" in `AGENTS.md` (lessons file and memory).

## Ground rules

- Never write a number that no code or cited source produced. Use `None` and "not evaluated".
- Never name a field or heading after a method that was not run.
- Every reported quantity carries a provenance tag: `MP_DFT`, `LITERATURE`, `COMPUTED_HERE`, `HEURISTIC`, `ASSUMED`, and `MLIP` after G6.
- A check counts as verification only if it uses a different method or data source.
- Do not replace one pinned number with another. Assert consistency between files instead (lesson L8). Pin only external reference values (for example the AM1.5G integral or the SQ limit).
- Literature values need a source you opened (DOI or URL). Never fill a value from memory.
- In commits and comments, name the assistant only as "Claude".

## Status

| Gap | Title | Status | Notes |
|---|---|---|---|
| G1 | Auditor without pinned live results | todo | |
| G2 | Generated README results block | todo | |
| G3 | Flag measured polymorph gaps | todo | |
| G4 | Heuristics flag, never reject | todo | |
| G5 | DFT run kit | todo | HUMAN GATE before long runs |
| G6 | GPU screen with machine-learned potentials | todo | |
| G7 | Continuous integration | todo | |
| G8 | Quarantine the v2 pilot | todo | |
| G9 | Ledger persists between runs | todo | |

---

## G1. Repository auditor without pinned live results

**Problem.** `failsmart_matengine/repo_auditor.py` asserts exact values from one past run of the live funnel: counts at lines ~255-263, 308, 316, 322, 333, 340, 348, 360-370, 415-418; the "expected finalists" dictionaries at lines ~50-80; efficiencies and costs at lines ~273-290 and in the Markdown audits (~540-660: `42.32%`, `42.22%`, `41.71%`, `40.71%`, `43.08%`, `4.420`, `15.72%`, counts `47`, `40`). It now fails.

**Change.**
1. Replace every live-funnel pin with a consistency check against `outputs/live_mp_discovery_summary.json` itself, for example:
   - `len(finalists) == funnel_counts["stage4_5_prescreen_finalists"] == top + bottom`;
   - every finalist has `status == "PROMOTED"`; every `all_mp_records` entry with `PROMOTED` is in `finalists`;
   - the number of pairs equals `min(top, k) * min(bottom, k)` with `k = device_model_exemplars_per_layer`;
   - every finalist has a QE deck and CIF in `outputs/mp_live_qe_decks/`, and no other decks exist;
   - every `ranked_shortlist.not_excluded` row matches the corresponding record.
2. Keep checks on external or fixed data: the negative-synthesis prior totals, the v2 pilot fixtures (they are deterministic), deck syntax, KaTeX safety.
3. In the Markdown audits, drop the pinned live-run numbers; G2 replaces them with a generated-block check.
4. Remove the now-unused `expected_live_mp_finalists` and `core_live_mp_finalists` dictionaries, or derive them from the summary.
5. Apply the same principle to `tests/test_scientific_integrity.py`: the counts updated on this branch (`50`, `43`, `30`, `23`, `7`, `16`, `65`) should become consistency checks too.

**Acceptance.** `test_g1_repository_auditor_passes_without_hardcoded_live_results` passes; `python -m failsmart_matengine.repo_auditor` prints `[PASS]`.

---

## G2. Generated README results block

**Problem.** README and docs quote the previous run (15 finalists, 56 pairs, 42% figures).

**Change.**
1. Add `failsmart_matengine/report_blocks.py` with `render_results_block(summary: dict) -> str`. It renders, from the summary only: the funnel counts; the gap model (form, coefficients, leave-one-out MAE and RMSE, sigma); a table of `ranked_shortlist.not_excluded` (id, formula, layer, gap with error bar, basis, window probability, synthesised or theoretical); the entries excluded by a known gap; the DFT queue; the maximum achievable window probability. Plain Markdown, no inline math, so it passes the KaTeX test.
2. Add a CLI `python -m failsmart_matengine.report_blocks --write` that replaces the text between `<!-- BEGIN GENERATED RESULTS -->` and `<!-- END GENERATED RESULTS -->` in `README.md`.
3. Insert the markers in README under a heading "Current results (generated)". Move the old v3 to v8 result sections under a heading "Historical results (superseded, not regenerated)" with one sentence saying they predate the calibrated gap model.
4. Make the auditor check that the block equals a fresh render.
5. Correct `docs/MEMORY_AND_FAILURE_LEDGER.md`, `docs/VERIFICATION_AND_TEST_REPORT.md` and `docs/PLAN.md` the same way, or replace their live-result sections with a pointer to the README block.

**Acceptance.** `test_g2_readme_results_block_is_generated_from_outputs` passes; the auditor passes.

---

## G3. Flag measured polymorph gaps

**Problem.** `mp-861911` (Sb2OS2, C2/m, theoretical) is on the shortlist with an estimated 2.13 eV. The same composition's synthesised polymorph, kermesite (`mp-28711`, P-1), has a measured gap of 2.04 eV in `data/gap_benchmark.csv`. The pipeline does not notice.

**Change.**
1. In `gap_model.py`, build a lookup from reduced composition (use `pymatgen.core.Composition(...).reduced_formula`, so `Sb2OS2` and `Sb2S2O` match) to benchmark rows.
2. In `resolve_gap`, when there is no measured gap for the exact `mp_id` but there is one for another polymorph, keep the entry's own gap and basis, and return `measured_polymorph_mp_id` and `measured_polymorph_gap_ev`.
3. Add both as optional fields on `ElectronicDefectReport` (provenance `LITERATURE` for the gap), carry them into `ranked_shortlist` rows, and show them in the G2 block.
4. Do not gate on it. It is information for the person choosing what to calculate.

**Acceptance.** `test_g3_measured_polymorph_gap_is_flagged` passes.

---

## G4. Uncalibrated heuristics flag, never reject

**Problem.** In Stage 4, `mass_ok` (effective masses and Frohlich alpha from composition heuristics) and `srh_ok` (defect depth chosen from five constants) can reject a candidate (`mp_live_discovery.py`, search for `mass_ok` and `srh_ok`). These are uncalibrated (lessons L4, L7).

**Change.**
1. Add `heuristic_flags: List[str] = []` to `ElectronicDefectReport`.
2. When `mass_ok` or `srh_ok` is false and the inputs are `HEURISTIC`, append a flag (`HEAVY_CARRIER_MASS_HEURISTIC`, `DEEP_DEFECT_HEURISTIC`) instead of rejecting. Reject only if the inputs are `COMPUTED_HERE`, `MLIP` or `LITERATURE`.
3. Update gate checks 10 and 11 in `test_24_every_remaining_gate_can_fail` (`tests/test_scientific_integrity.py`): with heuristic inputs they must now produce a flag and `PROMOTED`; add a case where the input is marked `COMPUTED_HERE` and must reject. Say in the commit message that this test changed and why.
4. Show flags in the shortlist and the G2 block.

**Acceptance.** `test_g4_uncalibrated_heuristics_flag_but_never_reject` passes; `test_24` passes in its updated form.

---

## G5. DFT run kit (HUMAN GATE before long runs)

**Goal.** Let the owner compute real gaps on his own hardware and feed them back as `COMPUTED_HERE`. The pipeline already reads `data/dft_results.json` (`gap_model.dft_gap_table`).

**Module.** `failsmart_matengine/dft_slice.py`, with functions and a CLI (`python -m failsmart_matengine.dft_slice <command>`):

| Function / command | Behaviour |
|---|---|
| `prepare(ids, out_dir, level)` | Writes one run folder per id: structure, `pw.x` inputs, a `run.sh` that does not start anything by itself, and a `README.txt` stating level, k-mesh, cutoffs and expected cost. Returns `{"files": [...], ...}`. `ids` may be Materials Project ids from the cache or the benchmark. |
| `parse_pw_output(path)` | Reads a `pw.x` output: convergence ("convergence has been achieved"), total energy, `highest occupied, lowest unoccupied level` and the gap. Raises if there are no empty bands. |
| `collect(paths, out_path, candidate_ids)` | Parses outputs and writes `data/dft_results.json` (`{"results": {id: {...}}, "controls": {...}}`) with method, level, code version, pseudopotentials, k-mesh, input and output file hashes. |
| `benchmark` | Times one small case (silicon, then Sb2S3) on CPU and, if present, GPU, and writes the timings to `runs/benchmark.json`. |

**Levels.**
- `pbesol_soc`: noncollinear PBEsol with spin-orbit, fully relativistic norm-conserving pseudopotentials (PseudoDojo FR is the usual choice; confirm the files support `lspinorb`), `nbnd` set above the number of occupied bands, then an `nscf` on a denser k-mesh for the minimum gap.
- `hse_nosoc`: HSE06 without spin-orbit, scalar-relativistic pseudopotentials, `nqx` dividing the k-mesh (reuse the T3 logic in `orchestrator.py`).
- Best gap rule: `best_gap_ev = E_HSE(no SOC) - (E_PBEsol(no SOC) - E_PBEsol(SOC))`. Store all three components. A PBEsol gap alone is never written to `best_gap_ev` (it underestimates by 0.5 to 1 eV).

**Controls (run first).** Silicon (`mp-149`, measured 1.12 eV) and at least three benchmark compounds with measured gaps: Sb2S3 (`mp-2809`), Bi2S3 (`mp-22856`), CuBiS2 (`mp-22982`), AgBiS2 (`mp-29678`) or CuSbS2 (`mp-4468`). `collect` sets `sigma_ev` for computed gaps to the RMSE of the controls against their measured gaps, and refuses to set it from fewer than three.

**Queue.** Take candidates from `ranked_shortlist.dft_queue` in the summary, smallest cells first.

**Fixture.** Commit one real `pw.x` output for silicon at PBEsol (`tests/fixtures/qe/si_pbesol_bands.out`). Produce it by actually running QE on a small cell (seconds on any machine). Do not hand-write it.

**Docs.** `docs/DFT_RUN_KIT.md`, written for the owner:
- WSL2 setup on Windows (`wsl --install -d Ubuntu-24.04`; `.wslconfig` with `memory=` about 80% of RAM and `processors=`; CUDA comes from the NVIDIA Windows driver, do not install a Linux driver inside WSL).
- Quantum ESPRESSO, CPU: the conda-forge `qe` package with OpenMPI is the quickest route. GPU: NVIDIA HPC SDK plus the CMake build; QE 7.6 changed the GPU CMake options, so follow the current wiki rather than old guides.
- How to choose MPI ranks and threads; on hybrid Intel chips, compare 6, 8 and 16 ranks with `benchmark` before long runs.
- The same steps on another PC (for example a friend's RTX 5090): copy the run folders, run, copy outputs back, `collect`. Ask the owner before each long run on someone else's computer.
- Expected costs per level, from `benchmark` results, not guesses.

**HUMAN GATE.** Do not start any run longer than one hour, or any run on another person's computer, without the owner's approval.

**Acceptance.** `test_g5_dft_kit_collects_results_that_the_pipeline_uses` passes. Then, only with real results, re-run the pipeline: candidates with computed gaps show `gap_basis = COMPUTED_HERE`.

---

## G6. GPU screen with machine-learned potentials

**Goal.** Use the GPU for structure relaxation and phonons as **flags**, never gates (universal potentials soften lone-pair lattices; imaginary modes there are often real anharmonic physics).

**Change.**
1. Add `MLIP` to `ProvenanceTag` in `schemas.py`.
2. Add optional dependencies in `pyproject.toml`: `ml = ["torch", "mace-torch", "phonopy", "ase"]`. Check current package names and versions before pinning.
3. Add `failsmart_matengine/ml_screen.py`:
   - `select_device()` returns `"cuda"` if `torch.cuda.is_available()`, else `"cpu"`; returns `"cpu"` without error if torch is not installed (import inside the function).
   - `relax(structure, model=...)` and `phonons(structure, supercell=...)` using a current MACE foundation model (look up the recommended model name; do not hard-code one from memory without checking).
   - Outputs: relaxed lattice change, energy above the relaxed reference, minimum phonon frequency and count of imaginary modes, all tagged `MLIP`, written to `data/ml_screen_results.json`.
4. Wire results into dossiers as flags (`MLIP_IMAGINARY_MODES`, `MLIP_LARGE_RELAXATION`), shown in the shortlist and G2 block. No rejection.
5. Document the CUDA PyTorch install inside WSL2 in `docs/DFT_RUN_KIT.md`.

**Acceptance.** `test_g6_gpu_ml_screen_is_optional_and_tagged` passes with and without torch installed.

---

## G7. Continuous integration

Add `.github/workflows/ci.yml`: Python 3.11 and 3.12, `pip install -e ".[dev]"`, `pytest -q`, `python -m failsmart_matengine.repo_auditor`. Do not install the `ml` extra in CI. Add a lockfile or pinned constraints file so CI is reproducible.

**Acceptance.** `test_g7_ci_runs_tests_and_auditor` passes; the workflow runs green on the pull request.

---

## G8. Quarantine the v2 pilot (old task T9)

Move `outputs/pilot_campaign_summary.json` and `outputs/qe_hse06_soc_decks/` to `tests/fixtures/v2_pilot/` with a README stating they are synthetic. Rename `_RAW_STABILITY_DATA`, `_RAW_ELECTRONIC_DATA` (`physics_calculators.py`) and `_GATE_A_DATA` (`tools.py`) with a `_SYNTHETIC_FIXTURE_` prefix and delete the comment "Stability ground-truth lookup tables". Update paths in tests and the auditor.

**Acceptance.** `test_g8_v2_pilot_quarantined_as_fixtures` passes.

---

## G9. Ledger persists between runs (old task T11, first step)

Add `reset_ledger: bool = False` to `run_live_mp_discovery_campaign` and `run_pilot_campaign`; call `reset_to_historical_seeds()` only when it is true. Make the committed outputs reproducible by passing `reset_ledger=True` from the commands that regenerate them, and say so in the README. The rest of old task T11 (graded evidence, ablation) is out of scope here.

**Acceptance.** `test_g9_failure_ledger_persists_between_runs` passes.

---

## When all gaps are closed

- `pytest -q` passes with no `xfail` left in `tests/test_gap_closure.py`.
- The auditor passes.
- Open one pull request listing each gap, its commit, and the test now passing. Quote any numbers from the committed outputs with file paths (lesson L9).
