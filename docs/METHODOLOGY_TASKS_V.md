# Methodology Tasks V1 to V10

**For:** the coding agent implementing the 2026-11-15 methodology review. **Why:** [`METHODOLOGY_REVIEW_2026-11-15.md`](METHODOLOGY_REVIEW_2026-11-15.md). Read that file first; this file only says what to do.

**Code already built for you:** [`../failsmart_matengine/methodology_checks.py`](../failsmart_matengine/methodology_checks.py). Use its functions. Do not re-implement them.

**Acceptance tests:** [`../tests/test_methodology_v.py`](../tests/test_methodology_v.py). Each open task has one strict expected-failure test.

---

## 0. Ground rules (read every time)

1. **Start only after the phase-2 tasks (G1 to G9) and the failure-data tasks (F1 to F5) are merged into the branch you work on.** V2, V6, V7 and V8 edit files those tasks edit.
2. **One task per pull request.** Do the tasks in the order of the Status table.
3. **A task is closed when** its test in `tests/test_methodology_v.py` passes, you delete that test's `@pytest.mark.xfail` line in the same commit, and `pytest -q` passes in full.
4. **Never edit the body of a test in `tests/test_methodology_v.py`.** If a test seems wrong, stop and tell the owner.
5. **When a change moves a value another test pins,** update the pin in the same commit and name the test in the commit message.
6. **Never write a number that no code or opened source produced.** If you cannot open a source, leave the row out. Do not fill it from memory.
7. **All thresholds live in `RULES_V`** in `methodology_checks.py`. Do not write a threshold inline.
8. **The words in Test 26's scan** (`tests/test_scientific_integrity.py`, search for `T2 grep rule`) may not appear in `README.md`, `docs/`, `failsmart_matengine/` or `outputs/` outside the exempt files. Name functionals and models generically ("screened hybrid functional", "machine-learned potential"), as this file does.
9. **No dollar signs in Markdown** (Test 21). Write "USD".
10. **Stop and ask the owner** at every step marked **HUMAN GATE**. Do not guess the answer and continue.
11. The rules in `AGENTS.md` apply, including recording lessons and using "Claude" with no model name in commits.

### Commands

```bash
pip install -e ".[dev]"
pytest -q                                              # everything
pytest -q tests/test_methodology_v.py -rxX             # x = task open, X = done but marker not removed
python -m failsmart_matengine.methodology_checks audit    # rejections by strength of evidence
python -m failsmart_matengine.methodology_checks window   # window width against error; best gap against quality
python -m failsmart_matengine.methodology_checks queue    # calculation order
python -m failsmart_matengine.mp_live_discovery           # rerun the funnel (uses the cache; no key needed)
```

---

## Status

Update this table in every pull request.

| Task | What | Status | Needs |
|---|---|---|---|
| V1 | Gate audit and review | **done** (this branch) | |
| V2 | The funnel rejects only on strong evidence | todo | G4, F2 merged |
| V3 | Positive controls | todo | V2; **HUMAN GATE** (Materials Project key) |
| V6 | Queue ordered by expected results per unit cost | todo | F1 merged |
| V4 | Top window: analysis, then owner decision | todo | V2; **HUMAN GATE** (decision) |
| V5 | Published hybrid-functional gaps, tested before use | todo | network access to figshare |
| V7 | Temperature: fix the label, report the deficit formula | todo | |
| V8 | Benchmark the band-edge estimate | todo | |
| V9 | Mitigations as sourced records | todo | F4 merged |
| V10 | Phonon check, known phases first | todo | G6 merged; **HUMAN GATE** before runs on another person's computer |

---

## V1. Gate audit and review (done)

Delivered on this branch: the review, `methodology_checks.py`, 16 passing tests, 9 open-task tests, `data/positive_controls.csv` with 2 sourced rows, rules R10 to R15.

Nothing to do. Keep `python -m failsmart_matengine.methodology_checks audit` working after every later task.

---

## V2. The funnel rejects only on strong evidence

**Problem.** `build_live_mp_candidate_dossier` in `failsmart_matengine/mp_live_discovery.py` rejects candidates on heuristics. Rule R2 forbids that. The registry `GATE_REGISTRY` in `methodology_checks.py` lists every failure mode, its evidence tier and the flag that replaces it.

**After this task, exactly two things can reject a candidate:**

- `HULL_INSTABILITY`: energy above hull over 50 meV per atom (unchanged).
- `BANDGAP_OUT_OF_WINDOW`: only when `gap_basis` is not `"HEURISTIC"` (the existing one-error-bar rule, unchanged for measured and computed gaps).

Everything else becomes a flag.

**Steps.**

1. Copy the five lessons from section 7 of the review into `docs/LESSONS_LEARNED.md`, in that file's format.
2. In `build_live_mp_candidate_dossier`, directly after `cand_dump = cand.model_dump()`, add `screening_flags: List[str] = []`.
3. **Stage 2.** Keep computing `born_ok`, `hull_ok`, `ion_ok` and keep storing them in `StabilityReport`. Change:
   - `passed_s2 = bool(hull_ok)`.
   - `s2_reason` is set only when `hull_ok` is false.
   - If `born_ok` is false, append `"SOFT_LATTICE"` to `screening_flags`.
   - If `ion_ok` is false, append `"ION_MIGRATION_HEURISTIC"`.
4. **Stage 3.** Keep computing `temp_ok`, `pbx_ok`, `cost_ok` and keep storing the numbers. Change:
   - `passed_s3 = True` and `s3_reason = None`, always.
   - If `temp_ok` is false, append `"HIGH_TEMPERATURE_ROUTE_EXPECTED"`.
   - If `pbx_ok` is false, append `"AQUEOUS_LEACHING_HEURISTIC"`.
   - If `cost_ok` is false, append `"HIGH_ELEMENT_COST"`.
   - If task F2's synthesis evidence for this candidate carries `SYNTHESIS_IMPURITY_RISK`, append `"SYNTHESIS_IMPURITY_RISK"`.
5. **Toxic elements.** If `methodology_checks.toxic_elements_present(els)` is not empty, append `"TOXIC_ELEMENT"`.
6. **Gate A.** `decision` is always `"PROMOTE"` and `fail_mode` is always `None`. If `polaron_flag` is true, append `"LOW_DIMENSIONAL_ORIENTATION_REQUIRED"` and start `critique` with `"FLAG:"` in place of `"VETO:"`. Delete the `if decision == "VETO_REJECT":` block that returns early.
7. **Stage 4.**
   - Only the gap term changes. Define `gap_rejects = (not gap_ok) and gap_basis != "HEURISTIC"` and use `not gap_rejects` in `passed_s4` in place of `gap_ok`. Leave the carrier-mass and defect-depth terms exactly as task G4 left them.
   - If `gap_ok` is false and `gap_basis == "HEURISTIC"`, append `"LOW_WINDOW_PROBABILITY"`.
   - The `BANDGAP_OUT_OF_WINDOW` reason is set only when `gap_rejects` is true.
   - Extend `screening_flags` with the `heuristic_flags` that task G4 put on the electronics report.
   - Note on the registry: `GATE_REGISTRY` marks `HEAVY_CARRIER_MASS` and `DEEP_SRH_DEFECT` as unable to reject because their inputs are heuristic today. If a later task feeds them computed inputs and G4's rule then rejects, tell the owner; the registry entry must be split the way `BANDGAP_OUT_OF_WINDOW` is.
8. **Optics.** `passed_all_stages = bool(elec.passed_stage4_and_5)`. If `opt.passed_optical_gate` is false and `elec.gap_basis != "HEURISTIC"`, append `"LOW_MODELLED_ABSORPTION"`. The optical gate no longer rejects.
9. **Every `return dossier` in the function** must first set `dossier["screening_flags"] = sorted(set(screening_flags))`. There are several return paths; check each one.
10. `verify_candidate_dossier` (`independent_verifier.py`) re-derives some of these decisions. Where it re-derives a rejection you removed, change it the same way. List each such place in the commit message.
11. In `build_ranked_shortlist`, copy `screening_flags` into every `not_excluded` row.
12. In `failure_evidence.scorecard`, add each of the row's `screening_flags` to the `flags` list of the axis given by `methodology_checks.FLAG_AXIS`. Do not change how `queue_class` is decided.
13. **Funnel keys.** Rename `stage2_dynamically_and_ion_stable` to `stage2_hull_stable` and `stage3_manufacturable_lbnl_alab_screened` to `stage3_synthesis_flags_assigned`, everywhere they occur (`mp_live_discovery.py`, `orchestrator.py`, `repo_auditor.py`, `tests/test_scientific_integrity.py`, the dashboard text, the generated README block).
14. Add `screening_flag_counts` to the summary: a dictionary from flag name to the number of records carrying it.
15. Update `test_24_every_remaining_gate_can_fail`: each gate you demoted must now yield a flag and a candidate that is not rejected by it.
16. Run `python -m failsmart_matengine.mp_live_discovery`, then regenerate everything derived from the summary (scorecards, generated README block).
17. Run `python -m failsmart_matengine.methodology_checks audit`. `rejected_on_weak_evidence` must be 0 and `known_phases_rejected_as_unstable` must be empty.

**Do not.**

- Do not delete the heuristic calculations or their report fields. They stay as information.
- Do not add a rule that parks or re-orders candidates by flag count. Flags are shown; the owner decides what they mean.
- Do not catch and hide an exception from a later stage that now runs on candidates it never saw before. If a stage cannot evaluate a candidate, store `None` for its fields, state "not evaluated", and record the case in `docs/LESSONS_LEARNED.md`.
- Do not pin the new funnel counts in a test. Expect most of the 100 candidates to remain; the exact number is whatever the run produces.

**Acceptance.** `test_v2_no_candidate_is_rejected_on_weak_evidence` passes.

---

## V3. Positive controls

**Problem.** No screening rule has ever been run on a material known to work. The live query asks only for compounds with three to five elements, so Sb2S3, Sb2Se3, CdTe and SnS have never been through the funnel.

**Steps.**

1. **HUMAN GATE.** This task needs a Materials Project key in the environment variable `MP_API_KEY`. If it is not set, stop and ask the owner. Never write the key to a file, a log, a commit or a message.
2. Extend `data/positive_controls.csv` to at least 10 rows. Keep the existing columns. Rules for a row:
   - The compound has a published working solar cell with an efficiency of at least 1%.
   - `mp_id` is copied from `data/gap_benchmark.csv` (column `mp_id`). Use only compounds that are in that file, so each has a measured gap.
   - `source_url` is a page you opened today that states the efficiency. `opened_on` is today's date.
   - Candidates to look up (ids from `data/gap_benchmark.csv`): CdTe `mp-406`, CuInSe2 `mp-22811`, CuGaSe2 `mp-4840`, Cu2ZnSnS4 `mp-1079541`, Cu2ZnSnSe4 `mp-1078918`, SnS `mp-2231`, Bi2S3 `mp-22856`, CuSbS2 `mp-4468`, CuSbSe2 `mp-20331`, AgBiS2 `mp-29678`, BiOI `mp-22987`.
   - If you cannot open a source for one of them, leave it out. Ten rows are enough.
3. In `mp_live_discovery.py`, move the code that turns one Materials Project document (plus its dielectric and elasticity documents) into a record out of `fetch_live_mp_semiconductors` into a helper, and add `fetch_mp_records_by_id(ids: List[str]) -> List[Dict[str, Any]]` that uses the same helper. The existing function must return exactly what it returned before (the cache file must not change).
4. Write `scripts/run_positive_controls.py`. It:
   - reads the ids from `data/positive_controls.csv`;
   - loads records from `data/positive_controls_cache.json` if that file exists, otherwise fetches them with `fetch_mp_records_by_id` and writes that file;
   - runs `build_live_mp_candidate_dossier` on each record, with a failure ledger opened on a temporary file (never the committed databases in `data/`);
   - writes `data/positive_control_results.json` with the shape below. Every entry has every key; use `null` where a stage did not run.
5. Commit the script, the cache and the results.

```json
{
  "generated_on": "YYYY-MM-DD",
  "results": {
    "mp-2809": {
      "formula": "Sb2S3",
      "structural_dimensionality": "...",
      "target_layer": "...",
      "gap_basis": "LITERATURE",
      "primary_failure_mode": null,
      "screening_flags": ["..."]
    }
  }
}
```

6. Add a section "Positive controls" to this file's end with a table: formula, structure class, failure mode, flags. State in one sentence how Sb2S3 and Sb2Se3 were classified.

**How to read the result.**

- A control rejected by `BANDGAP_OUT_OF_WINDOW` is fine: its measured gap is outside this project's window. That is not a fault of the gates.
- A control rejected by `HULL_INSTABILITY` is a finding. Record it and tell the owner; do not change the hull rule.
- A control rejected by any other mode means task V2 is incomplete. Fix the gate. Never remove the control.

**Do not** add the controls to the candidate cache, the shortlist or the scorecards.

**Acceptance.** `test_v3_positive_controls_survive_every_gate_that_may_not_reject` passes.

---

## V6. Queue ordered by expected results per unit cost

**Problem.** `build_ranked_shortlist` sorts the calculation queue by synthesised-first, then window probability, then cell size. Cell size, which sets the cost, only breaks ties.

**Steps.**

1. In `run_live_mp_discovery_campaign`, after the `summary` dictionary is complete and before it is written to disk, add:

```python
from .methodology_checks import RULES_V, queue_from_summary

ordered = queue_from_summary(summary)
by_id = {r["candidate_id"]: r for r in ordered}
for row in summary["ranked_shortlist"]["not_excluded"]:
    q = by_id.get(row["candidate_id"])
    if q is not None:
        row["queue_class"] = q["queue_class"]
        row["relative_cost"] = q["relative_cost"]
        row["queue_priority"] = q["queue_priority"]
summary["ranked_shortlist"]["dft_queue"] = [r["candidate_id"] for r in ordered]
summary["ranked_shortlist"]["queue_cost_exponent"] = RULES_V["cost_exponent"]
```

2. Show `queue_class`, `relative_cost` and `queue_priority` in the generated README block and the scorecard table.
3. In the run kit's instructions (task G5), state the order of work: first the controls (compounds with measured gaps), then candidates in `dft_queue` order.
4. Later, when the run kit has at least 5 timed runs at one level of theory covering a factor of two in cell size: call `methodology_checks.fit_cost_exponent`, set `RULES_V["cost_exponent"]` to the fitted value, and cite the timing file in the comment. This step is not needed to close the task.

**Do not** change `order_queue` or `queue_priority`. Do not move entries between queue classes.

**Acceptance.** `test_v6_the_pipeline_queue_is_ordered_by_expected_results_per_unit_cost` passes.

---

## V4. Top window: analysis, then owner decision

**Problem.** The top window is 1.75 to 1.95 eV. It is narrower than any calculation can resolve. It is also a robust choice: it is close to the range that stays good whether the top cell reaches 60% or 100% of its limit. Widening it trades that robustness for the ability to tell candidates apart (review section 3.2). That trade is the owner's to make.

**Steps.**

1. Run `python -m failsmart_matengine.methodology_checks window` and save the output.
2. Write `docs/WINDOW_DECISION_BRIEF.md`, at most one page, containing:
   - the two tables from review section 3.2, regenerated from step 1;
   - for each option below, the number of shortlist entries whose gap estimate lies inside the window, and the probability ceiling from `window_probability_ceiling` at sigma 0.44, 0.36 and 0.10;
   - which measured compounds in `data/gap_benchmark.csv` fall inside each option.

   | Option | Top window (eV) | Meaning |
   |---|---|---|
   | A | 1.75 to 1.95 | Keep as is: robust to top-cell quality between 60% and 100% of the limit |
   | B | 1.49 to 1.95 | Within 1 point of the best for an ideal top cell |
   | C | 1.61 to 2.24 | Within 1 point of the best for a top cell at 75% of its limit |

   Regenerate the numbers for B and C from step 1; if they differ from this table, use the regenerated ones and say so. Present both readings from review section 3.2 (for and against the current window) without recommending one.
3. **HUMAN GATE.** Send the brief to the owner and ask two questions: which option (or another window), and whether to keep the bottom layer (`BOTTOM_IR_075EV`). Stop until the owner answers.
4. Write `data/window_decision.json`:

```json
{
  "decided_by": "<the owner's name, as he gives it>",
  "decided_on": "YYYY-MM-DD",
  "assumed_top_cell_quality": 1.0,
  "tolerance_abs_pct": 1.0,
  "top_window_ev": [1.75, 1.95],
  "keep_bottom_layer": true,
  "analysis": "docs/WINDOW_DECISION_BRIEF.md"
}
```

5. Set `WINDOWS["TOP_ACTIVE_GLASS_185EV"]` in `gap_model.py` to the decided window. Do not rename the key, even if the window no longer contains 1.85.
6. Rerun the funnel and regenerate derived outputs.

**Do not.**

- Do not choose the window yourself. `decided_by` must be a person.
- Do not remove the bottom layer from the code in this task, whatever the answer. If the owner says to drop it, record `"keep_bottom_layer": false` and open a separate task with him.

**Acceptance.** `test_v4_the_top_window_is_a_recorded_owner_decision` passes.

---

## V5. Published hybrid-functional gaps, tested before use

**Problem.** Kim et al. (Sci. Data 7, 387, 2020) published screened-hybrid gaps for 10,481 synthesised compounds. Rule R8 says a data source must be tested before it influences ranking.

**Data.** figshare DOI `10.6084/m9.figshare.12839240`. JSON files named `<formula>_<collection code>.json` with keys including `Band_gap_HSE`, `Band_gap_GGA`, `Structure_rlx` (a POSCAR string), `Space_group_rlx`, `SOC`.

**Steps.**

1. Download the dataset to a folder outside the repository. Read the licence on the figshare page. If the licence does not allow redistribution of extracted values, stop and tell the owner. Do not commit the raw dataset.
2. Write `scripts/build_published_hybrid_gaps.py`. It matches:
   - **candidates** (`data/mp_live_candidates_cache.json`): same reduced formula, then `pymatgen.analysis.structure_matcher.StructureMatcher()` with default tolerances between the candidate structure and `Structure_rlx`;
   - **benchmark compounds** (`data/gap_benchmark.csv`): same reduced formula and same space-group symbol (`space_group` against `Space_group_rlx`). Skip rows with an empty `mp_id`.
   - If more than one database entry matches, skip the compound and list it under `"ambiguous"`.
3. The script writes `data/published_hybrid_gaps.json`:

```json
{
  "source": "Kim et al., Sci. Data 7, 387 (2020), doi:10.6084/m9.figshare.12839240",
  "entries": {"mp-xxxx": {"gap_ev": 0.0, "soc_included": false, "database_file": "..."}},
  "benchmark_matches": {"mp-yyyy": {"gap_ev": 0.0, "soc_included": false, "database_file": "..."}},
  "ambiguous": []
}
```

4. **Ablation.** For every benchmark match with a measured gap: `err_pub = gap_ev - measured_gap_ev` and `err_est = loocv_gap_est_ev - measured_gap_ev` (both columns are in `data/gap_benchmark.csv`). Let `d = abs(err_est) - abs(err_pub)` per compound. Bootstrap the mean of `d` with 10,000 resamples and seed 0; the 95% interval is the 2.5th and 97.5th percentiles. Write `data/hybrid_lookup_ablation.json` with keys `source`, `license`, `downloaded_on`, `n_overlap`, `rmse_published_hybrid_ev`, `rmse_calibrated_estimate_ev`, `bias_published_hybrid_ev`, `improvement_interval_95_ev` (a two-element list), `adopted`.
5. **Decision rule, no judgement:** `adopted` is true if and only if `n_overlap >= 15` and the lower end of the interval is above 0.
6. **If adopted:**
   - In `gap_model.py` add `published_hybrid_gap_table()` returning `{id: {"gap_ev", "sigma_ev", "source", "soc_included"}}` from the `entries` of `data/published_hybrid_gaps.json`, with `sigma_ev` equal to `rmse_published_hybrid_ev`.
   - In `resolve_gap`, the order becomes: measured (`LITERATURE`), computed here (`COMPUTED_HERE`), published hybrid (`gap_basis = "DATABASE_HYBRID"`), calibrated estimate (`HEURISTIC`).
   - Map `DATABASE_HYBRID` to tier `T3_DATABASE_DFT_OR_ML_POTENTIAL` in `failure_evidence._gap_tier`.
   - Rerun the funnel and regenerate derived outputs.
7. **If not adopted:** commit both JSON files and change nothing in the pipeline.
8. **In both cases:** in `gap_model.py` set `SIGMA_DFT_DEFAULT_EV = 0.36` and replace its comment with: `# LITERATURE: RMSE of one-shot screened-hybrid gaps against 116 measured gaps (Kim et al., Sci. Data 7, 387, 2020). Replaced by the run kit's own controls once they exist.`

**Do not** fit any correction to the published gaps in this task. Report the bias; do not remove it.

**Acceptance.** `test_v5_published_hybrid_gaps_were_tested_before_use` passes.

---

## V7. Temperature: fix the label, report the deficit formula

**Problem.** `temp_coeff_rel_pct_per_k` in `RealWorldLCOEStressTestReport` comes from the rule of thumb `-0.44 / Eg**0.65` percent per kelvin and is tagged `COMPUTED_HERE`. The rule has the trend reversed for a cell with a large voltage deficit (review section 3.5).

**Steps.**

1. In `schemas.py`, class `RealWorldLCOEStressTestReport`:
   - change the provenance of `temp_coeff_rel_pct_per_k` to `ProvenanceTag.HEURISTIC`;
   - add `top_cell_voc_temp_coeff_from_deficit_mv_per_k: float` with provenance `ProvenanceTag.ASSUMED`;
   - add `temperature_flags: List[str] = []`.
2. In `atomistic_and_tmm.py`, function `evaluate_phase9c_real_world_lcoe_stress_test`, next to the lines that define `gamma_top`:

```python
from .methodology_checks import top_cell_temperature_report

temp_rep = top_cell_temperature_report(eg_ind_1)
```

   and pass `top_cell_voc_temp_coeff_from_deficit_mv_per_k=temp_rep["top_cell_voc_temp_coeff_from_deficit_mv_per_k"]` and `temperature_flags=temp_rep["temperature_flags"]` to the report constructor.
3. Rerun the funnel.

**Do not.**

- Do not change `gamma_top`, `gamma_si`, `gamma_bot` or any efficiency, yield or cost figure. They are pinned in several tests and the gain is small.
- Do not add the same formula to `independent_verifier.py`. A copy of a formula is not a check.

**Acceptance.** `test_v7_temperature_rule_of_thumb_is_labelled_and_the_deficit_formula_reported` passes.

---

## V8. Benchmark the band-edge estimate

**Problem.** The conduction-band estimate in `evaluate_phase11a_synthesis_and_contacts` (`realistic_commercialization.py`) has never been compared with a measurement.

**Steps.**

1. Refactor without changing any number: move the lines that compute `chi_comp`, `lp_shift`, `cbm` and `vbm` into `estimate_band_edges(stoich: Dict[str, int], gap_ev: float) -> Tuple[float, float]` (returns `cbm`, `vbm`, in eV relative to vacuum, negative numbers) and call it from the original place. All tests must pass unchanged after this step. Commit it alone.
2. Build `data/band_edge_benchmark.csv` with at least 10 rows and these columns: `formula, measured_electron_affinity_ev, measured_gap_ev, method, sample, source_doi, source_url, opened_on, note`.
   - Use only compounds whose elements are all keys of `MULLIKEN_CHI_EV`: Bi, Sb, In, Ga, Cu, Ag, Sn, O, S, Se. Examples to look up: Sb2S3, Sb2Se3, Bi2S3, SnS, SnS2, CuInSe2, CuInS2, CuGaSe2, CuSbS2, AgBiS2, Cu2O, SnO2, In2S3, In2O3.
   - `measured_electron_affinity_ev` is a positive number from a source you opened. If the source gives only the ionisation energy, subtract the measured gap and say so in `note`.
   - `method` names the technique (for example photoemission). `sample` says film, crystal or surface orientation when the source does.
3. Write `scripts/benchmark_band_edges.py`. For each row: get `stoich` from `pymatgen.core.Composition(formula)` as integer counts, then `cbm, _ = estimate_band_edges(stoich, measured_gap_ev)`; error is `(-cbm) - measured_electron_affinity_ev`. Write `data/band_edge_model.json` with `n`, `mae_ev`, `rmse_ev`, `bias_ev`, `max_abs_ev` and a `per_compound` list.
4. In `schemas.py`, class `Phase11ASynthesisContactDossier`, add `contact_alignment_class: str = "NOT_EVALUATED"`.
5. In `evaluate_phase11a_synthesis_and_contacts`, set it with `methodology_checks.classify_band_offset(best_cbo, rmse)` where `rmse` is `rmse_ev` read from `data/band_edge_model.json`. In the early-return branch where `best_cbo_ev=None`, leave it `"NOT_EVALUATED"`.
6. Rerun the funnel.

**Expect** many dossiers to read `UNRESOLVED`. If the error is as large as the acceptable range, that is the correct answer.

**Do not** change `contact_voltage_penalty_v` or the practicality score in this task. If `rmse_ev` is 0.4 eV or more, tell the owner in the pull request that the contact term in the practicality score rests on an estimate that cannot resolve it, and let him decide.

**Acceptance.** `test_v8_band_edge_estimates_are_benchmarked_and_classified_with_their_error` passes.

---

## V9. Mitigations as sourced records

**Problem.** The outside outline proposes a passivation "recovery factor". There is no source for such a number. What exists are specific measures with measured effects.

**Steps.**

1. Add at least 10 rows to `data/device_failure_records.csv` with `finding_type` equal to `mitigation`, from at least 3 material families. Columns as they are:
   - `mechanism_class`: the failure mechanism the measure addresses, using a class already in the file where one fits.
   - `mechanism`: what was done, in one sentence.
   - `value` and `unit`: the measured effect the source reports (for example efficiency after treatment, in percent). If the source is a calculation, set `evidence_kind` to `THEORY`.
   - `source_url`, `opened_on`: a page you opened. `quote`: exact words from it, or empty.
   - A first candidate to check: Wang et al., Joule 8, 2105 (2024) proposes oxygen exposure to fill selenium vacancies in Sb2Se3, and shows intermediate growth conditions give the fewest defects.
2. In `failure_evidence.analog_device_evidence`: rows with `finding_type == "mitigation"` must not create `ANALOG_` flags and must not count toward the best efficiency or the theoretical limit. Return their `record_id`s under a new key `known_mitigations`.
3. In `failure_evidence.scorecard`: add `known_mitigations` (the list from step 2, empty if the card has no analog family) at the top level of every card.
4. Regenerate the scorecards.

**Do not** introduce any multiplier, recovery factor or score built from mitigation records. They are shown, not computed with.

**Acceptance.** `test_v9_mitigations_are_records_with_sources_not_multipliers` passes.

---

## V10. Phonon check, known phases first

**Problem.** The funnel never computes vibrational stability. Machine-learned potentials can, but their accuracy for phonons varies between models (Loew et al. 2025).

**Steps.**

1. Use the model and loader that task G6 added. Do not add a second model.
2. Write `failsmart_matengine/phonon_check.py` with `phonon_stability(structure) -> Dict[str, Any]`: relax the cell with the potential, build the smallest supercell whose three lattice vectors are all at least 10 angstrom, compute harmonic phonons by finite displacements with `phonopy`, and return the lowest frequency in THz over an 8x8x8 q-point mesh, plus `stable` (true when the lowest frequency is above `-0.5` THz). Put `10` and `-0.5` in `RULES_V` as `phonon_min_supercell_angstrom` and `phonon_imaginary_threshold_thz`.
3. **Controls first.** Run it on at least 8 synthesised phases that are stable at room temperature, taken from `data/positive_controls_cache.json` (task V3). Do not use SbSI or BiSI as controls: both have known structural transitions near room temperature.
4. Write `data/phonon_controls.json` with `model`, `model_version`, `supercell_rule`, `imaginary_threshold_thz`, `n_controls`, `false_unstable` (list of ids reported unstable), `false_unstable_fraction`, `results` (one entry per control with its lowest frequency).
5. **Decision rule:** if `false_unstable_fraction` is above 0.125 (more than 1 in 8), do not run candidates. Report to the owner that this model is not usable for the purpose.
6. Otherwise run the candidates in `dft_queue` order, add `"IMAGINARY_PHONON_MODES"` to `FLAG_AXIS` (axis `stable`) and to `screening_flags` of unstable candidates. It is a flag: results from a machine-learned potential never reject (tier table, rule R2).
7. **HUMAN GATE.** Ask the owner before running on any computer that is not his own.

**Acceptance.** `test_v10_phonon_stability_is_checked_on_known_phases_first` passes.

---

## Not to be built

These were considered and rejected or deferred. Do not start them without the owner asking.

| Item | Decision | Reason |
|---|---|---|
| One weighted score or "success probability" per material | Rejected | Nothing to calibrate it against; weights hide which evidence is weak |
| Passivation recovery multiplier | Rejected | No source for the number (V9 replaces it) |
| Bonus for materials nobody has tried | Rejected | Few attempts is weak evidence (rule R9) |
| Defect-tolerance points for lone-pair chemistry or a high dielectric constant | Rejected | Sb2Se3 has both and has deep, voltage-limiting defects |
| Hard gap filter on an estimated gap | Rejected | The error bar is larger than the filter |
| Charged-defect calculations | Deferred | Hybrid-functional supercells of 60 to 120 atoms are beyond the available hardware. Revisit with a cost estimate once the run kit has timings. Any cloud spend is a **HUMAN GATE** |
| A new machine-learned gap model | Deferred | V5 tests an existing published table first |
| Replacing the temperature rule of thumb in the yield and cost models | Deferred | Moves many pinned values for a second-order effect (V7 reports the better number beside it) |
| Removing the bottom layer from the code | Deferred | Depends on the owner's answer in V4 |
| Effective masses along and across ribbons | Deferred | Needs band structures from the run kit (G5) |

---

## Prompt to give the implementing agent

> Read `AGENTS.md`, then `docs/METHODOLOGY_REVIEW_2026-11-15.md`, then `docs/METHODOLOGY_TASKS_V.md`. Confirm that tasks G1 to G9 and F1 to F5 are merged; if they are not, stop and say which are missing. Then do the V tasks in the order of the Status table, one pull request per task. Follow section 0 of the task file exactly. Use the functions in `failsmart_matengine/methodology_checks.py`; do not rewrite them. Never edit a test body in `tests/test_methodology_v.py`. Stop and ask me at every step marked HUMAN GATE. In each pull request, say which `xfail` marker you removed, which pinned values changed and why, and what you added to `docs/LESSONS_LEARNED.md`.
