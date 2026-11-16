# Material Evaluation Rules

How this project decides what a candidate material is worth, given the goal: an absorber that is **effective, cost-effective, stable, relatively easy to synthesise, and not already worked over by everyone else**.

These rules are implemented in [`failure_evidence.py`](../failsmart_matengine/failure_evidence.py) and tested in [`tests/test_failure_evidence.py`](../tests/test_failure_evidence.py). The current output is [`outputs/material_scorecards.md`](../outputs/material_scorecards.md).

---

## 1. The idea in one paragraph

Each candidate gets a card with four axes. Every axis states its **evidence tier**: how the number was obtained. Weak evidence can raise a flag but cannot remove a candidate; only strong evidence can exclude. Failure data (failed syntheses, underperforming devices in related materials) enters as evidence on two axes, never as a hidden score. The card ends with a **queue class** that says what to calculate first.

---

## 2. Evidence tiers

| Tier | Meaning | Can it exclude a candidate? |
|---|---|---|
| `T0_NOT_EVALUATED` | Nothing known | No |
| `T1_HEURISTIC` | Closed-form estimate or rule of thumb | No, flag only |
| `T2_ANALOGY` | Measured or computed for a related material, or recipe statistics for the same chemistry | No, flag only |
| `T3_DATABASE_DFT_OR_ML_POTENTIAL` | Database DFT value for this exact entry, or a machine-learned-potential result | Yes for database DFT (for example hull distance); machine-learned-potential results stay flags |
| `T4_COMPUTED_HERE` | First-principles calculation run for this entry at a suitable level, with controls | Yes |
| `T5_MEASURED` | Measurement on this phase, with a citation | Yes |

---

## 3. The four axes

| Axis | Question | Evidence used now | What would raise the tier |
|---|---|---|---|
| **Effective** | Is the band gap in the target window, and can carriers survive? | Gap with error bar and window probability; best efficiency and theoretical limit of the nearest studied relatives (analogy) | A computed gap (run kit), then defect calculations, then a film measurement |
| **Cost** | Can it be made at scale from available elements? | Active-layer material cost; critical elements | Process cost once a route exists |
| **Stable** | Does it stay the phase we want? | Distance from the convex hull (database DFT); decomposition reported for relatives (analogy) | Phonons and finite-temperature stability; damp-heat data |
| **Synthesizable** | Can it be made phase-pure, ideally below the glass limit? | Whether the phase has been made; impurity-rate evidence for its chemical system with a 90% interval; named impurity phases | A thin-film route below 500 C; a measured phase-pure film |

---

## 4. Rules

### R1. Every number carries a tier

A card field without a tier is a bug. A value moves up a tier only when a new source exists, never by relabelling.

### R2. Weak evidence flags, strong evidence excludes

Tiers T1 and T2 produce flags. Exclusion needs T3 database DFT, T4 or T5. An estimated gap always carries the flag `GAP_IS_AN_ESTIMATE` and tier `T1_HEURISTIC`.

### R3. Report the uncertainty next to the decision it supports

Gaps come with an error bar and the probability of being in the window. Impurity rates come with a 90% credible interval. A rate from fewer than 5 recipes is graded "weak" and cannot raise a risk flag.

### R4. Failure data is evidence, not a verdict

- **Failed syntheses** give an impurity-rate estimate for the candidate's chemical system, shrunk toward related systems when its own data are thin, plus the impurity phases to look for. The flag `SYNTHESIS_IMPURITY_RISK` is raised only when there are at least 5 recipes and the lower end of the 90% interval exceeds `impurity_flag_lower_bound`.
- **Failed or limited devices** in related materials give flags named `ANALOG_<mechanism>` and the relatives' best efficiency and theoretical limit. They describe the family's known problems, not this material.
- Published recipes are powder syntheses, mostly far above the glass limit; the flag `REPORTED_ROUTES_ABOVE_GLASS_LIMIT` says so when it applies.

### R5. Calculate synthesised phases first

Queue class `CALCULATE_FIRST`: the phase has been made, contains no critical elements, and is on or near the hull. These are the cheapest decisive calculations, and a known phase with no reported solar device is the best trade between "new" and "makeable".

### R6. Then small, clean theoretical entries

Queue class `CALCULATE_NEXT`: never synthesised, but no critical elements, near the hull, and a cell small enough for a hybrid-functional calculation on a workstation.

### R7. Park the rest, with the reason

Queue class `PARK`: critical elements, far from the hull, or a large never-synthesised cell. Parked is not rejected; the card states why, and changing a threshold in `RULES` moves entries between classes.

### R8. A data source must earn its place

Before any dataset influences ranking, an ablation must show it predicts held-out cases better than a simple baseline, with an interval. The plan may claim a benefit only where that interval excludes zero. The current ablation is `data/failure_ablation.json`.

### R9. Uniqueness is judged against the literature, not asserted

A candidate is "new" only after a literature check for that exact phase (existence, measured gap, reported devices). Record the search and its date. Related-material records in `data/device_failure_records.csv` each carry the source and the date it was opened.

### R10. The funnel obeys R2

R2 applies to every place a candidate can be removed, not only to the cards. `GATE_REGISTRY` in [`methodology_checks.py`](../failsmart_matengine/methodology_checks.py) lists every failure mode, its evidence tier and the flag that replaces it when the tier is too weak to reject. `python -m failsmart_matengine.methodology_checks audit` counts violations. A phase that has been synthesised is never rejected as unstable by an estimate.

### R11. Every screening rule is run on materials known to work

`data/positive_controls.csv` lists compounds with a published working cell. A rule that removes one of them on weak evidence is wrong until shown otherwise. Controls are never removed to make a rule pass.

### R12. An acceptance window is compared with the error of the evidence tested against it

Next to a window probability, report its ceiling: the best value any estimate with that error bar could reach (`window_probability_ceiling`). The top-cell window follows from the device model and an assumed top-cell quality; it is the owner's decision, recorded in `data/window_decision.json`.

### R13. No single score, no unsourced multiplier, no bonus for being unexplored

Cards keep four axes. Mitigations such as passivation are sourced records shown on the card, never a factor applied to a number. Few published attempts is not evidence of merit (see R9).

### R14. Calculations are ordered by expected result per unit of compute

Inside a queue class, order by window probability divided by relative cost (`queue_priority`). Compounds with measured gaps are calculated before any candidate, because they set the error bar.

### R15. Look for a published calculation before running one

A published value is tested on the measured benchmark first (R8) and used only if it beats the current estimate with an interval that excludes zero.

---

## 5. Thresholds

All are judgement calls (`ASSUMED`), kept in one dictionary, `RULES`, in `failure_evidence.py`.

| Key | Value | Why |
|---|---|---|
| `prior_strength_recipes` | 4 | Related systems count as about four recipes of prior evidence, so five or more of a system's own recipes outweigh them |
| `impurity_flag_lower_bound` | 0.50 | Flag only when more than half of attempts fail even at the optimistic end of the interval |
| `critical_elements` | In, Ga, Ge, Te, Ag | Cost or supply risk at very large scale |
| `hull_on_mev` | 1 | On the hull within numerical noise |
| `hull_near_mev` | 25 | Roughly room-temperature thermal energy; entries this close are commonly synthesised |
| `large_cell_sites` | 24 | Above this a hybrid-functional run is slow on a workstation |
| `glass_limit_c` | 500 | Soda-lime glass process ceiling |

---

## 6. What a card cannot tell you yet

- Whether the gap is right. Until the run kit produces computed gaps, the best window probability is about 0.18.
- Whether carriers survive. Defect and lifetime physics is what limits this family; the cards only carry the relatives' known problems.
- Whether a thin-film route exists. Recipe statistics describe powder synthesis.

---

## 7. Commands

```bash
python -m failsmart_matengine.failure_evidence ablation     # rewrite data/failure_ablation.json
python -m failsmart_matengine.failure_evidence scorecards   # rewrite outputs/material_scorecards.json and .md
pytest -q tests/test_failure_evidence.py
```
