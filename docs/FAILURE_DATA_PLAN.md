# Failure Data: What It Is Used For, What It Is Worth, What To Build

**Date:** 2026-11-15. **Branch:** `failure-evidence` (new files only; stacked on `calibration-and-dft-kit`).

**Question from the owner:** are "failed experiments" being used as an extra input when ranking prospective materials, and what benefit should we expect?

**Related files:** [`MATERIAL_EVALUATION_RULES.md`](MATERIAL_EVALUATION_RULES.md) (the rules), [`../failsmart_matengine/failure_evidence.py`](../failsmart_matengine/failure_evidence.py) (the code), [`../tests/test_failure_evidence.py`](../tests/test_failure_evidence.py) (the tests), [`../outputs/material_scorecards.md`](../outputs/material_scorecards.md) (current cards).

---

## 1. Answer

Barely, until now. The data was in the repository; one slice acted as a blunt filter; nothing was fitted to it and it did not affect ranking.

| Dataset in the repository | How the pipeline used it |
|---|---|
| Published solid-state recipes with impurity outcomes, per chemical system (`chemsys_impurity_priors`) | One rule: reject if the system has at least 5 recipes and more than half were impure. Removes 5 of 100 candidates. |
| Autonomous-lab pairwise reactions (`alab_*`) | Loaded, never read. The stored samples are oxide and carbonate precursor pairs, a different chemistry from sulfide and selenide films. |
| The pipeline's own failure ledger | Wiped at the start of every run; its score feeds no decision (phase-2 gap G9). |
| Device failures in related materials | Not present at all. |

Two facts about the recipe data limit what it can do for this project:

- **Coverage is thin.** Of the 100 candidates, 48 have no recipes for their chemical system, 30 have one to four, and 22 have five or more. On the 30-entry shortlist only 4 have five or more.
- **It describes a different process.** The chalcogenide recipes (3,307 of them, 36% impure) have a median reported temperature of 800 C. The target is thin-film growth below 500 C on glass.

The file also holds 34,639 recipes, not the 80,806 its header and the README state (task F3).

---

## 2. Measured benefit (ablation)

Rule R8 says a data source must earn its place. `python -m failsmart_matengine.failure_evidence ablation` tests whether recipe outcomes in **related** chemical systems predict a held-out system's impurity rate better than simply using the global rate. Results are in `data/failure_ablation.json` (`COMPUTED_HERE`; leave-one-chemical-system-out; systems with at least 5 recipes; bootstrap over systems).

| Scope | Systems | Improvement in Brier score over the global rate | 95% interval |
|---|---|---|---|
| All chemistries | 1239 | 19.8% | 12.0% to 27.1% |
| Chalcogenides only | 142 | 12.1% | -12.5% to 31.3% |

Reading:

- Across all chemistries, related-system recipe outcomes carry real predictive information.
- The benefit is **not established for chalcogenides**: the interval includes zero. There are too few chalcogenide systems with enough recipes.
- Using the chalcogenide class average is worse than the global rate for chalcogenide systems, so "it is a chalcogenide, expect 36% impure" is not a useful prior on its own.

Conclusion: recipe failure data is worth keeping as **context for the person planning a synthesis** (expected impurity phases, how often related chemistries go wrong). It is not strong enough to rank or reject candidates in this chemical space.

---

## 3. Expected benefit by use

| Use | Expected benefit | Basis |
|---|---|---|
| Fitting the band gap | None | Synthesis outcomes carry no information about gaps |
| Rejecting candidates on recipe impurity rate | Negative | The current rule rejects CuSbS2 and SbSI, which are routinely made; and the ablation does not support it for chalcogenides |
| Flagging likely impurity phases for a planned synthesis | Moderate, cheap | Named phases are directly useful at the diffractometer |
| Ranking synthesizability across the shortlist | Small today | Thin coverage; could grow with task F3 |
| Device-failure records for related materials | Highest for the stated goal | Voltage loss and deep defects, not synthesis, are what limit this family (records DF01 to DF09) |
| The project's own failures, kept between runs | Unknown until there are any | Needs the run kit to produce real outcomes first |

---

## 4. What was built on this branch

All new files. Nothing existing was edited, so this does not collide with the phase-2 work.

| File | What it is |
|---|---|
| `failsmart_matengine/failure_evidence.py` | Synthesis evidence with shrinkage and 90% intervals; analog device evidence; four-axis scorecards; the ablation |
| `data/device_failure_records.csv` | 9 records on why related materials underperform, each with a source opened on the stated date |
| `data/failure_ablation.json` | The ablation result above (reproducible; a test compares it with a fresh run) |
| `outputs/material_scorecards.json`, `.md` | One card per shortlist entry, generated from the pipeline summary |
| `docs/MATERIAL_EVALUATION_RULES.md` | Rules R1 to R9, evidence tiers, thresholds |
| `tests/test_failure_evidence.py` | 19 passing tests of the rules, plus 5 strict expected-failure tests for tasks F1 to F5 |

### 4.1 Current scorecard summary

From `outputs/material_scorecards.json` (30 shortlist entries):

- **`CALCULATE_FIRST` (2):** `mp-1195160` Al2Bi2Cu2S3Cl8 and `mp-540644` Sn4SI6. Both are synthesised phases with no critical elements, near the hull, and no measured gap on file.
- **`CALCULATE_NEXT` (6):** `mp-1228961` AlCuSnS4, `mp-1227486` BiSbS3, `mp-1218912` SnSSe, `mp-861911` Sb2OS2, `mp-1225738` Bi5CuS8, `mp-1218960` Sn2SSe.
- **`PARK` (22):** mostly indium, gallium, germanium or silver content.

Every card carries `GAP_IS_AN_ESTIMATE`. The Sb and Bi sulfides also carry the relatives' problems: deep anion-vacancy traps and a 16% theoretical ceiling reported for Sb2S3.

---

## 5. What still needs implementing (tasks F1 to F5)

**Do these after the phase-2 gaps G1 to G9 are merged.** They touch files phase 2 is editing. Each has a strict expected-failure test in `tests/test_failure_evidence.py`; closing a task means the test passes and its `xfail` marker is deleted in the same commit. The ground rules in `AGENTS.md` apply.

| Task | Change | Files it touches | Test |
|---|---|---|---|
| **F1. Put scorecards in the pipeline output** | Call `failure_evidence.build_scorecards` at the end of the live run, store the result under `scorecards` in the summary, and include the card table in the generated README block from gap G2. Then delete the separate `outputs/material_scorecards.*` files. | `mp_live_discovery.py`, `report_blocks.py`, README | `test_f1_scorecards_are_part_of_the_pipeline_summary` |
| **F2. Turn the impurity rule into a flag** | Replace the `IMPURITY_SINK_PRIOR` rejection with `synthesis_evidence(...)` stored on the synthesis report (rate, interval, grade, named phases, flags). No candidate is rejected on recipe statistics. Update gate check in `test_24` accordingly and say so in the commit. | `mp_live_discovery.py`, `schemas.py`, `tests/test_scientific_integrity.py` | `test_f2_recipe_statistics_never_reject_a_candidate` |
| **F3. Rebuild the recipe data from source** | Commit a script that builds `negative_synthesis_priors.json` from the published dataset, so the totals in the header match the rows (today 34,639 against a stated 80,806). Keep per-recipe temperature and precursors, so routes at or below 500 C can be counted separately. Re-run the ablation. | `scripts/`, `data/` | `test_f3_recipe_totals_match_their_header` |
| **F4. Grow the device-failure table** | At least 30 records, each from a source opened by whoever adds it. Add measured gap, voltage and carrier lifetime where the source gives them. Cover families with no record yet: tin chalcogenides and chalcohalides (SnS, Sn2SbS2I3), Cu and Ag tin sulfides and selenides (kesterite relatives), AgBiS2, Bi2S3, BiOI, Sb2Se3. Extend `material_family` to match. | `data/device_failure_records.csv`, `failure_evidence.py` | `test_f4_device_table_covers_the_shortlist_families` |
| **F5. Literature check for the top of the queue (rule R9)** | For every `CALCULATE_FIRST` and `CALCULATE_NEXT` entry, record in `data/literature_checks.json`: whether the exact phase has been made, any measured gap, any reported solar device, the search terms, sources and date. A measured gap found here goes into `data/gap_benchmark.csv`, where the pipeline will pick it up. | `data/` | `test_f5_top_of_queue_has_a_literature_check` |

Later, once the run kit has produced outcomes: keep the project's own results (computed gaps that missed, films that came out impure) in the ledger with graded evidence, and repeat the ablation on them before they influence ranking.

---

## 6. Sources for the device records

Opened on 2026-11-15:

- Sb2S3 at 8.21%: https://english.cas.cn/newsroom/research_news/phys/202510/t20251023_1094727.shtml
- Sb2S3 voltage of 824 mV and deep traps: https://arxiv.org/abs/2512.18100v1
- Sulfur vacancies cap Sb2S3 at 16%: https://arxiv.org/abs/2410.10560
- Antimony chalcogenide at 10.7% certified: https://www.unsw.edu.au/newsroom/news/2026/01/engineers-set-efficiency-world-record-for-emerging-solar-cell-material
- Selenium vacancies cap BiSeI at 24%: https://arxiv.org/abs/2504.18089
- Cu-Sb and Cu-Bi chalcogenide review: https://link.springer.com/article/10.1557/mre.2018.10
