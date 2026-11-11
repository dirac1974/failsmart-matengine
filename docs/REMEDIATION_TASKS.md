# Remediation Tasks (agent-ready)

This file is written for an engineer or coding agent picking the work up cold. Findings and evidence are in [`INDEPENDENT_AUDIT_2026-11.md`](INDEPENDENT_AUDIT_2026-11.md). Paths are relative to the repository root.

## How to use this file

1. Do **T0** first. Then work in the order shown in "Order and dependencies".
2. One task per commit. Commit message: `T<n>: <summary>`.
3. Tick the task in the "Status" table when its acceptance checks pass, and add one line of notes.
4. Stop and ask the repository owner where a task says **HUMAN GATE**.

## Ground rules

- **Never write a number that no code or cited source produced.** If a value cannot be computed, store `None` and label it "not evaluated".
- **Never name a field, column, file or heading after a method that was not run.** Stand-ins get stand-in names (`gap_est_*`, `spring_model_*`, `emig_heuristic_*`).
- **Every reported quantity carries a provenance tag:** `MP_DFT`, `LITERATURE` (with DOI or URL), `COMPUTED_HERE` (with code path), `HEURISTIC`, or `ASSUMED`.
- **A check counts as verification only if it uses a different method or data source.** Re-implementing the same formula is a regression test; call it that.
- **Do not weaken a test to make it pass.** If a test pins a value that a fix legitimately changes, update the pinned value in the same commit and say so in the message.
- **Markdown rules enforced by the test suite** (`tests/test_scientific_integrity.py:1225-1270`, applied to `README.md` and `docs/*.md`): no odd count of unescaped dollar signs on a line; no cent sign or `**` inside inline math; none of the macros `\cent`, `\celsius`, `\degree`, `\angstrom`.
- Do not commit secrets. `MP_API_KEY` belongs in `.env` (already git-ignored).

## Strings the repository's own auditor asserts on

`failsmart_matengine/repo_auditor.py:474-550` checks `README.md` by substring. Until T2 edits those assertions, the README must keep all of these:

- `13-Agent Research + Engineering Team Architecture` or `13-agent` (line 480)
- all thirteen role names such as `pi_orchestrator` (lines 481-496)
- `20 Candidates Screened` or `20 generated`; `17 dynamically`; `12 manufacturable`; `8 promoted to Stage 4`; **`5 Validated Finalists`** (lines 499-503)
- the fifteen v2 formulas listed at lines 504-509
- every v2 finalist table row, including cost, SLME, tandem efficiency and SHA-256 digest (lines 511-520)
- `100`, `91`, `52`, `40`, `80,806`, `18,869`, `1,035`, `892` (lines 523-530)
- all eight `mp-` identifiers (lines 532-534)
- `42.32%`, `41.75%`, `40.00%`, `42.44%`, `41.89%`, `4.354`, `0.0394` (lines 537-543)
- `18` together with the word `test` (lines 546-548)

Similar checks apply to `docs/MEMORY_AND_FAILURE_LEDGER.md` (lines 552-594), `docs/VERIFICATION_AND_TEST_REPORT.md` (lines 596-619) and `docs/PLAN.md` (lines 621-644).

The relabelling patch that introduced this file kept every one of those strings; the phrase "5 Validated Finalists" survives only inside a "legacy label" note.

## Order and dependencies

```text
T0 -> T1 -> T6 -> T3 -> T2 -> T4 -> T5 -> T8 -> [HUMAN GATE] T7 -> T9 -> T10 -> T11 -> T12 -> [HUMAN GATE] T13
```

- T2 depends on T6 and T3 because all three change generated outputs; regenerate once.
- T8 depends on T4 (it needs the gap error).
- T7 spends money; it needs the owner's approval and the T4 result.

## Status

| Task | Title | Status | Notes |
|---|---|---|---|
| T0 | Baseline | done | Editable install fixed (`[tool.setuptools.packages.find]`); `pytest -q`: 22 passed; `repo_auditor`: PASS (11 Markdown files, 0 errors) |
| T1 | Paths and version | done | Repo-relative `Path(__file__).resolve().parents[1]` defaults; unified version `0.8.0`; removed broken `IMG_1087.png` link; verified in fresh `/tmp` clone (`23 passed`, auditor `PASS`) |
| T2 | Finish relabelling in code and data | done | Renamed `gap_est_*`, `sha256_digest`, `composition_embedding`, `_estimate_gap_from_mp_pbe`, `spring_and_migration*`; added `ProvenanceTag` + `provenance` dicts on all schemas; replaced README role list with stage/provenance table; regenerated JSON/DB/HTML/docs (`26 passed`, auditor `PASS`) |
| T3 | Fix deck generators | done | Explicit vacancy element (`ValueError` if absent), `^[A-Za-z0-9_]+$` prefix, `K_POINTS automatic 1 1 1 0 0 0` with `noncolin`, perpendicular spacing `>= 10 A` (`Bi3InSe6` `1x1x1->3x3x3`, `Sb2OS2` `2x2x1->3x3x1`), commensurate `nqx1..3`, renamed `mp_live_neutral_vacancy_decks` & `point_charge_image_estimate_ev`; `test_25` checks all 23 decks (`25 passed`, auditor `PASS`) |
| T4 | Calibrate the gap estimate; literature gate | done | Added `data/finalist_literature.json`, 50-compound `data/gap_benchmark.csv`, and `docs/GAP_CALIBRATION.md` (old MAE `0.4522 eV`, Cu/Ag bias `-0.5350 eV`; refit LOOCV MAE `0.3684 eV`, LOOCV RMSE `0.4362 eV`, LOFO MAE `0.4187 eV`); added `+/- 0.37 eV` error bars and 1-sigma probabilistic window gate (`100->91->47->40->9` updated to `100->91->47->40->15`, `27 passed`, auditor `PASS`) |
| T5 | External-truth tests | todo | |
| T6 | Remove gates that cannot fail | done | Removed non-failing gates (`dynamically_stable=None`, `g_above_hull_synth_mev=None`, `mlip_force_std_ev_ang=None`, `tco_rxn/hmix=None`, deleted contrastive audit, enabled LBNL prior gate `IMPURITY_SINK_PRIOR`); funnel `100->91->52->40->8` updated to `100->91->47->40->9`; `test_24` verifies all 13 remaining gates fail; `24 passed`, auditor `PASS` |
| T7 | One real vertical slice | todo | HUMAN GATE |
| T8 | Correct device assumptions; invert the cost model | todo | |
| T9 | Quarantine the v2 pilot | todo | |
| T10 | Make verification mean something | todo | |
| T11 | Ledger that persists and is tested | todo | |
| T12 | Engineering hygiene | todo | |
| T13 | Decide the project's goal | todo | HUMAN GATE |

---

## T0. Baseline

**Goal:** a reproducible starting point, and confirmation that the relabelling patch broke nothing. The audit could not run the code.

**Steps**

1. Create a virtual environment with Python 3.11 or newer.
2. `pip install -e ".[dev]"`
3. `pytest -q 2>&1 | tee baseline_pytest.txt`
4. `python -m failsmart_matengine.repo_auditor 2>&1 | tee baseline_auditor.txt`
5. If either fails, find out whether the cause is the hardcoded `/home/antigravity` paths (fixed in T1) or the relabelling patch. For the latter, restore the missing string from the list above; do not edit the assertion yet.

**Acceptance:** both commands' results recorded in the Status notes (pass counts or the specific failures).

---

## T1. Paths and version

**Goal:** the package runs from any checkout and has one version.

**Files and changes**

- `failsmart_matengine/ledger.py:18`, `inter_team_bus.py:18`, `orchestrator.py:92`, `mp_live_discovery.py:1080`: replace the `/home/antigravity/failsmart-matengine/...` defaults with paths derived from `Path(__file__).resolve().parents[1]`.
- `failsmart_matengine/__init__.py:20` (0.1.0), `pyproject.toml` (4.0.0), README (v8.0): choose one version and read it from one place.
- `docs/REALISTIC_COMMERCIALIZATION_AND_DEBATE_REPORT.md:18`: remove the link to `IMG_1087.png`, which is not in the repository.

**Acceptance**

- `grep -rn "antigravity" failsmart_matengine tests` returns nothing.
- T0 commands give the same results from a fresh clone in a different directory.

---

## T6. Remove gates that cannot fail

**Goal:** every gate can fail, or is removed and reported as "not evaluated".

**Changes**

| Location | Problem | Change |
|---|---|---|
| `mp_live_discovery.py:685`, `:689` | Minimum phonon frequency is clipped to at least 0.35 while the gate is `> -0.10` | Remove the gate; set `dynamically_stable=None`; rename the value `omega_min_heuristic_thz` |
| `atomistic_and_tmm.py:81-92` and its callers | Positive springs always give zero imaginary modes | Stop reporting "imaginary modes" and "ASR deviation"; keep the frequencies only as `spring_model_gamma_freq_thz` |
| `atomistic_and_tmm.py:180-187` | "NEB" is one closed-form expression | Rename outputs `emig_heuristic_ev`; drop "NEB", "11-image", "saddle point" |
| `atomistic_and_tmm.py:959-970` | Contrastive margin is non-negative for any labelling | Delete the metric and its README and docs mentions, or replace with a held-out evaluation in T11 |
| `mp_live_discovery.py:759` | Invented "MLIP force std" | Set to `None` |
| `mp_live_discovery.py:855-857` | `tco_rxn = -26.0` constant; `hmix` one of two constants | Set to `None` unless computed; a `None` cannot trigger or clear a veto |
| `mp_live_discovery.py:782-790` | Negative-synthesis priors cannot change a decision | Either let the prior move the decision (state the rule) or record it as informational only and say so |
| `mp_live_discovery.py:670` | "G_hull" is hull minus 10.5 | Remove, or label `HEURISTIC` and take it out of the `hull_ok` condition at `:690` |

**Acceptance**

- A unit test feeds each remaining gate an input that must fail, and it fails.
- Funnel counts change; record old and new counts in the commit message. (The current 100, 91, 52, 40, 8 are pinned by tests and by `repo_auditor.py`; update both.)

---

## T3. Fix deck generators

**Goal:** generated Quantum ESPRESSO inputs are syntactically valid and describe what their names say.

**Changes**

1. **Vacancy species** (`atomistic_and_tmm.py:836-854`). `vac_el` is derived from a label such as `V_Chalcogen (shallow donor, ns2 antibonding)` and never matches an element, so site 0 is removed. Carry an explicit element symbol through from the place the label is created (`mp_live_discovery.py:497-515`). Raise an error if the species is absent from the structure.
2. **Prefix** (`atomistic_and_tmm.py:864`). Build it from the formula and element symbol only (letters, digits, underscore).
3. **K-points** (`atomistic_and_tmm.py:874`, `:891`). `K_POINTS gamma` selects the Gamma-only code path, which does not support `noncolin`. Write `K_POINTS automatic` with `1 1 1 0 0 0`.
4. **Supercell size** (`atomistic_and_tmm.py:826`). The minimum image distance must be the smallest perpendicular spacing of the supercell, not the smallest lattice-vector length. Choose the expansion so that spacing is at least 10 Angstrom, and assert it.
5. **Charge states.** Defect decks have no `tot_charge`. Either generate one deck per charge state or rename the output directory and README text to "neutral vacancy supercell".
6. **Hybrid q-mesh** (`orchestrator.py:61`). `nqx1..3` must divide the k-mesh in each direction. Derive it from the k-mesh instead of fixing 2 2 2.
7. **Naming.** These files do not come from the `doped` package. Rename `outputs/mp_live_doped_supercell_decks/` and remove "doped" from descriptions until T7 uses the package.
8. **"FNV"** (`atomistic_and_tmm.py:831-834`). Rename to `point_charge_image_estimate_ev`.

**Acceptance**

- A test parses every generated deck and asserts: the removed species equals the labelled species; the prefix matches `^[A-Za-z0-9_]+$`; no deck combines `gamma` with `noncolin`; q-mesh divides k-mesh; minimum perpendicular spacing is at least 10 Angstrom.
- Regenerated decks are committed in place of the old ones.

---

## T2. Finish relabelling in code and data

**Goal:** no method name is attached to a value that method did not produce, anywhere.

**Already done by the relabelling patch:** README banner and headings, banners on all docs, relative links, one corrected docstring.

**Still to do**

1. Edit `repo_auditor.py:480`, `:503` and `:550` so they no longer require "5 Validated Finalists" or praise a "verified 13-agent architecture". Then delete the "legacy label" notes from `README.md`.
2. Rename schema fields in `failsmart_matengine/schemas.py` and every producer and consumer:
   - `hse06_soc_direct_gap_ev`, `hse06_soc_indirect_gap_ev`, `hse06_nosoc_gap_ev`, `r2scan_soc_gap_ev` to `gap_est_*`
   - `mlip_force_std_ev_ang` removed (T6)
   - `sha256_signature` to `sha256_digest`
   - SQLite column `mace_embedding` to `composition_embedding` (`ledger.py`)
3. Add a `provenance` field (enum from "Ground rules") next to every numeric result in the dossier schema, and populate it.
4. Rename the function `_estimate_hse06_soc_electronics_from_mp` to `_estimate_gap_from_mp_pbe`.
5. Regenerate `outputs/*.json`, the dashboard and the docs tables from the code.
6. README: replace the role-by-role descriptions with a table of "stage, what the code does, provenance".

**Acceptance**

- `grep -rniE "hse06|r2scan|neb|fnv|mace|doped|cryptograph|validated" README.md docs failsmart_matengine outputs` returns only (a) deck files that really request that functional, (b) the audit and this file, (c) explicit "not run" statements.
- `pytest -q` and the repository auditor pass.

---

## T4. Calibrate the gap estimate; literature gate

**Goal:** know how wrong the gap estimate is, and stop selecting on a window narrower than its error.

**Steps**

1. **Literature gate on the eight finalists.** For each, record with a citation: whether the Materials Project entry corresponds to a synthesised phase and which one; measured optical gap; any reported device. Write to `data/finalist_literature.json`. Do not fill values from memory; a missing value is `null`.
   - Known from the cache: only `mp-22982` (CuBiS2) and `mp-23474` (AgBi3S5) are marked experimentally known.
   - Check first: CuBiS2 (claimed 0.85 eV; literature suggests about 1.3 to 1.65 eV) and whether `mp-861911` matches the mineral kermesite (the entry is C2/m with 10 atoms; kermesite is reported as triclinic).
2. **Benchmark set.** Build `data/gap_benchmark.csv` with at least 40 chalcogenides, oxychalcogenides and chalcohalides that have a Materials Project PBE gap and a measured gap. Include, at minimum: Sb2S3, Sb2Se3, Bi2S3, SnS, CuSbS2, CuSbSe2, CuBiS2, AgBiS2, CuInSe2, CuGaSe2, Cu2ZnSnS4, Cu2ZnSnSe4, CdTe, BiOI, BiSI, SbSI, BiOCl, BaZrS3, BiCuOS, ZnS. Each row needs a source.
3. Run the existing estimate over the set. Report mean absolute error, bias, and error split by "contains Cu or Ag" versus not.
4. Refit the three coefficients by cross-validation, or replace the estimate with a published PBE-to-hybrid correction. Report cross-validated error.
5. Replace the hard window gate with a probabilistic one: keep a candidate if the window lies within one error bar of the estimate, and report the probability that it is in the window.

**Acceptance**

- `docs/GAP_CALIBRATION.md` states the error figures and the method.
- The README's finalist tables show the error bar next to each gap.

**Kill criterion:** if cross-validated error stays above 0.4 eV, state in the README that the v3 to v8 rankings carry no information and stop presenting finalists until T7.

---

## T5. External-truth tests

**Goal:** tests that can catch wrong physics.

**Steps**

1. Add `tests/test_external_truth.py`. Each test compares a code output with a cited external value and a stated tolerance:
   - SQ limit at 1.34 eV close to 33.7%; at 1.12 eV close to 32 to 33%.
   - Integrated AM1.5G photon current above 1.12 eV close to 43 to 44 mA per square centimetre.
   - Transfer-matrix reflectance of a bare glass interface, and of a quarter-wave coating, against the analytic result (and against the `tmm` package if installed).
   - Dimensionality classifier: known chain, layered and framework structures.
   - Gap estimate on five T4 benchmark materials within the T4 error bar.
   - Charge-neutrality and hull lookups on known stable compounds.
2. Mark existing tests that pin repository outputs with `@pytest.mark.regression`, so the two kinds are reported separately.

**Acceptance:** at least 10 external-truth tests pass; `pytest -m "not regression"` runs them alone.

---

## T8. Correct device assumptions; invert the cost model

**Goal:** device and cost outputs state requirements, not forecasts.

**Changes**

1. `realistic_commercialization.py:380-400`: the three maturity cases use external radiative efficiencies of 1e-5, 1e-4 and 5e-3. Replace with "demonstrated" (1e-10 to 1e-9, fill factor at most 0.73), "stretch" (1e-7) and "ceiling" (1e-4), each labelled `ASSUMED` with the citations from the audit.
2. `kinetics_and_optics.py:373-384`, `:421`, `:456`: remove the `4 * eps_inf` path-length enhancement for the thin films; use single- or double-pass absorption.
3. Rename every "bifacial PCE" output to "bifacial-equivalent power density (front-irradiance basis)".
4. `atomistic_and_tmm.py:1555-1560`: compute string ratios from the operating voltage of the selected maturity case, not the radiative one. Add a resistive-loss check for the implied strip width and flag infeasible widths.
5. Make the two-layer stack the default; move the rear infrared cell behind an option that is off by default.
6. Add `python -m failsmart_matengine.requirements_tea`, which outputs, for utility and rooftop cases:
   - break-even top-cell efficiency as a function of sub-gap transmittance and added module cost;
   - allowable added cost per efficiency point;
   - sensitivity to degradation rate.
7. Remove from the README and docs: the 58.7% margin, month-based horizons, "beats c-Si", "GW Tandem Winner", "World-Record".

**Acceptance**

- With the "demonstrated" case the two-layer stack reports lower efficiency than silicon alone (this matches measured tandems; if not, find the bug).
- The requirements output reproduces the audit's figures: break-even near 15.7% in the original utility model, and about `24.5 - 13.1*T` percent on an optics-only basis.

---

## T7. One real vertical slice (HUMAN GATE)

**Goal:** real hybrid-functional gaps for the finalists and a few known absorbers, to replace the estimate.

**Before starting:** send the owner a cost estimate and get approval. Rough scale (auditor's estimate, unverified): 2 to 10 thousand core-hours per 20-atom cell for a hybrid functional with spin-orbit coupling.

**Steps**

1. Relax each structure first (PBEsol, or a universal machine-learned potential followed by a PBEsol check).
2. Run PBEsol with spin-orbit coupling on all eight finalists plus Sb2S3, Sb2Se3, Bi2S3, CuSbS2 and CuInSe2 as controls.
3. Run the hybrid functional with spin-orbit coupling on primitive cells using the T3-fixed decks. Start with the smallest cells (7 to 10 atoms).
4. Compare the controls with measured gaps before trusting the finalists.
5. Store results with provenance `COMPUTED_HERE`, input and output files, code version and pseudopotential names.
6. Optional: relaxation and phonons from a machine-learned potential as a **flag** only. Never gate on them; these potentials soften lone-pair lattices, and imaginary modes there are often real anharmonic physics.

**Acceptance:** a table of estimate versus computed versus measured gap for the controls and finalists, committed with raw outputs.

**Kill criteria**

- Controls miss measured gaps by more than 0.3 eV: fix the setup before reporting anything.
- No finalist lands in its target window: say so in the README and close the "finalists" claim.

---

## T9. Quarantine the v2 pilot

**Goal:** synthetic fixtures are not presented as results.

**Steps**

1. Move `outputs/pilot_campaign_summary.json` and `outputs/qe_hse06_soc_decks/` to `tests/fixtures/v2_pilot/` with a README stating they are synthetic.
2. Rename `_RAW_STABILITY_DATA`, `_RAW_ELECTRONIC_DATA` (`physics_calculators.py:771`, `:909`) and `_GATE_A_DATA` (`tools.py:189`) with a `_SYNTHETIC_FIXTURE_` prefix. Remove the comment "Stability ground-truth lookup tables" (`physics_calculators.py:770`).
3. Remove the v2 results section from the README (after T2 has freed the auditor assertions); link to the fixture README instead.

**Acceptance:** no v2 pilot number appears in the README; regression tests still run from the fixtures.

---

## T10. Make verification mean something

**Goal:** "verified" means checked by a different method.

**Steps**

1. Rename `independent_verifier.py` to `self_consistency.py`; describe it as a regression checker. Delete sections that duplicate the heuristics removed in T6.
2. Rename "signature" to "digest" everywhere. If tamper evidence is wanted, hash-chain the log records; do not call it signing without a key.
3. Add cross-method checks where a second method exists: transfer-matrix against the `tmm` package; detailed balance against a published SQ table; hull energy against a `pymatgen` phase diagram built from the cache.
4. Delete `logs/team_checkins_and_debate.jsonl`, or move it to `docs/` labelled as authored commentary, since no code produces it.
5. Remove "13-agent", "debate", "consensus" and "sign-off" language from code and docs unless a real agent runtime is added. If one is added later: tools are called, every number links to a tool call, and the critic must run a falsifying check.

**Acceptance:** each remaining "verified" statement in the README names the second method.

---

## T11. Ledger that persists and is tested

**Goal:** either the failure ledger improves decisions measurably, or the claim is dropped.

**Steps**

1. Stop resetting the ledger on every run (`orchestrator.py:107`, `mp_live_discovery.py:1095`); make reset an explicit flag.
2. Extend the schema: failure mechanism, evidence type (provenance enum), source DOI or code path, quantitative margin to threshold, confidence, re-test policy. Verdicts are graded, never a permanent binary.
3. Seed it with literature failures that have citations, not hand-written archetypes (`ledger.py:170` onward).
4. Reconcile `data/negative_synthesis_priors.json` with its cited sources: per-system counts sum to 34,639 recipes and 10,143 impure, while the README states 80,806 and 18,869; the "892 negative" figure counts every reaction that was not fully complete. Correct the README or the data.
5. Ablation: on a labelled set of at least 80 materials, with a leave-one-chemical-family-out split, compare failure prediction with the ledger, without it, with shuffled labels, and with a nearest-neighbour baseline.

**Acceptance:** `docs/LEDGER_ABLATION.md` reports the comparison with bootstrap intervals.

**Kill criterion:** no out-of-sample lift over the baselines means removing "learns from failure" from the project description.

---

## T12. Engineering hygiene

- Add a lockfile and a CI workflow that runs `pytest` and the repository auditor.
- CI fails if the README names a tool that is absent from the lockfile.
- Remove unused dependencies (`ase`, `spglib`) or use them.
- Move generated outputs and SQLite files out of version control, or regenerate them in CI and diff.
- Commit the script that builds `data/mp_thermo_interface_cache.json` (no generating code exists in the repository).
- Rename "live" discovery to reflect that it reads the cache unless refreshed (`mp_live_discovery.py:234-237`).
- Split modules above about 800 lines.
- Fix stale counts in docs (message counts, test counts).

**Acceptance:** CI green on a clean clone.

---

## T13. Decide the project's goal (HUMAN GATE)

Bring the owner the T4 and T7 results and ask which branch to take. The work differs by branch.

| Branch | Next step | Stop condition |
|---|---|---|
| Learning | Stop after T7; write up one material end to end | none |
| Research tool | Publish the provenance-tagged screening harness and the T4 calibration; consider a benchmark of 80 to 100 materials with a frozen scorer and a temporal holdout | no lift over an SLME-plus-hull baseline |
| Company | Find an experimental thin-film collaborator before anything else; offer co-authorship using T4 and T7 results | no collaborator within 60 days |

Do not raise money, quote margins or publish timelines before a certified device exists.
