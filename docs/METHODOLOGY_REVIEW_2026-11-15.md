# Methodology Review: an outside pipeline outline against this repository

**Date:** 2026-11-15. **Branch:** `methodology-v` (new files only, plus added rules in `MATERIAL_EVALUATION_RULES.md`; stacked on `failure-evidence`).

**Question from the owner:** an outline for a multi-junction screening pipeline was produced by another assistant (Grok). Is this project missing anything in it, and how should the methodology change?

**Related files:** [`METHODOLOGY_TASKS_V.md`](METHODOLOGY_TASKS_V.md) (what to implement), [`../failsmart_matengine/methodology_checks.py`](../failsmart_matengine/methodology_checks.py) (code built in this review), [`../tests/test_methodology_v.py`](../tests/test_methodology_v.py) (tests and acceptance gates), [`MATERIAL_EVALUATION_RULES.md`](MATERIAL_EVALUATION_RULES.md) (rules R10 to R15 added).

---

## 1. Answer

The outline is a sound generic funnel, and most of its stages already exist here in some form. Its distinctive ideas (one calibrated success probability, a passivation recovery factor, a bonus for unexplored materials, a hard gap filter of 0.2 eV) should not be adopted; section 5 says why.

Checking the outline against the code and the literature did expose six real problems in this project. The first two matter far more than the rest.

| # | Finding | Consequence | Task |
|---|---|---|---|
| 1 | The funnel rejects on evidence that the project's own rule R2 says cannot reject. Of 70 rejections in the current run, 68 rest on heuristics or analogy. | Every ribbon-structure candidate is removed (13 of 13), although the best related cells (Sb2Se3, Sb2S3) are ribbon structures. Six synthesised phases are rejected as mechanically unstable. | V2, V3 |
| 2 | The top window is 0.20 eV wide. No calculation can place a gap inside it with a probability above about 0.3. A wider window is defensible, but which one depends on how good the top cell is assumed to be. | Running hybrid-functional calculations cannot confirm a candidate; it can only rule out clear misses. The width of the window needs an owner decision. | V4 |
| 3 | A published database of hybrid-functional gaps for 10,481 known compounds exists and is not used. | Some of the planned calculations may already have been done by others. | V5 |
| 4 | The calculation queue ignores cost. A 3-site cell and a 40-site cell with the same window probability are treated alike. | Compute is spent on large cells first. | V6 |
| 5 | The temperature rule of thumb says a wide-gap top cell loses less than silicon when hot. For a cell with a large voltage deficit the opposite holds. It is also tagged `COMPUTED_HERE`. | Field-yield figures are optimistic, and a heuristic is mislabelled. | V7 |
| 6 | The contact-alignment estimate was never compared with a measurement, and its acceptance range differs from the published one. | A contact penalty feeds a practicality score with an unknown error. | V8 |

Two further items are smaller: passivation belongs in the evidence table as sourced records (V9), and the stability stage is named after a property it does not compute (V2 renames it, V10 adds a real check).

---

## 2. What was checked

- **Code:** every gate in `build_live_mp_candidate_dossier` (`mp_live_discovery.py`), the tandem model in `kinetics_and_optics.py`, the contact estimate in `realistic_commercialization.py`, the temperature rule in `atomistic_and_tmm.py` and `independent_verifier.py`, and the queue in `build_ranked_shortlist`.
- **Run data:** `outputs/live_mp_discovery_summary.json` as committed on this branch (100 candidates).
- **Literature:** the sources in section 8, each opened on 2026-11-15.

### Correction to the first reply given to the owner

The first reply said this project had no contact-alignment step and no temperature coefficients. Both statements were wrong. The code has a conduction-band offset estimate against TiO2 and SnO2 and a temperature coefficient. Both are heuristics that were never benchmarked, which is the actual gap. The lesson is in section 7.

---

## 3. Findings in detail

### 3.1 The funnel rejects on weak evidence

Rule R2 says only database DFT, a calculation run here, or a measurement may exclude a candidate. The scorecards obey it. The funnel that feeds them does not. `python -m failsmart_matengine.methodology_checks audit` on the current run (`COMPUTED_HERE`):

| Failure mode | Evidence behind it | May reject under R2 | Rejected | Of which synthesised phases |
|---|---|---|---|---|
| `OXIDE_IMPURITY_SINK` | process temperature assumed from the element list | no | 26 | 23 |
| `BANDGAP_OUT_OF_WINDOW` with an estimated gap | calibrated estimate, 0.44 eV error bar | no | 10 | 7 |
| `TIER2_COST_EXCEEDED` | element prices, assumed thickness, assumed limit | no | 10 | 5 |
| `LOW_DIM_POLARON_RISK` | structure class alone | no | 7 | 7 |
| `ELASTIC_INSTABILITY` | modulus thresholds | no | 6 | 6 |
| `IMPURITY_SINK_PRIOR` | powder-recipe statistics | no (task F2) | 5 | 4 |
| `ION_MIGRATION_INSTABILITY` | closed-form barrier estimate | no | 3 | 3 |
| `LOW_OPTICAL_EFFICIENCY` | closed-form absorption coefficient | no | 1 | 1 |
| `BANDGAP_OUT_OF_WINDOW` with a measured gap | measurement | yes | 2 | 2 |
| **Total** | | | **70** | **58** |

Three results stand out.

- **Ribbon structures never survive.** All 13 candidates classed `1D-Chain` are rejected: 7 by the structure-class veto, 4 as elastically unstable, 2 by other gates. Sb2Se3 holds the family's efficiency record and its predicted efficiency limit depends on crystal direction; films with ribbons standing on the substrate outperform films with ribbons lying flat (Zhou et al. 2015: 5.6% against 3.2%). The structure class calls for a growth-orientation requirement, not a rejection.
- **Existing compounds are rejected as unstable.** SbSI (two entries), BiSI, SbSBr, Sb2OS2 and BiCu3S3 are synthesised phases rejected by `ELASTIC_INSTABILITY`. The gate tests whether the bulk modulus exceeds 15 GPa and the shear modulus 12 GPa. Those are not the Born stability conditions, and soft van der Waals crystals fail them while existing.
- **An estimated gap rejects.** Ten entries are rejected because the estimate lies more than one error bar outside the window. Such an entry still has up to a 0.09 chance of being inside; the best-placed estimate has 0.18. That difference should lower priority, not remove the entry.

Whether Sb2S3 and Sb2Se3 themselves would be classed `1D-Chain` is not yet known: the live query asks only for compounds of three to five elements, so no binary has ever been through the funnel. Task V3 runs them.

### 3.2 The window is too narrow for a calculation to confirm, and it depends on top-cell quality

**Probability ceiling.** With a normal error of standard deviation sigma, the best possible probability of lying in a window of width w is `2 * Phi(w / (2 * sigma)) - 1`.

| Window width (eV) | Estimate, sigma 0.44 | Published hybrid, sigma 0.36 | Assumed kit default, sigma 0.25 | Measurement, sigma 0.10 |
|---|---|---|---|---|
| 0.20 (current top window, 1.75 to 1.95) | 0.18 | 0.22 | 0.31 | 0.68 |
| 0.30 | 0.27 | 0.32 | 0.45 | 0.87 |
| 0.45 | 0.39 | 0.47 | 0.63 | 0.98 |
| 0.60 | 0.51 | 0.60 | 0.77 | 1.00 |

Published benchmarks put hybrid-functional gaps at a root-mean-square error of 0.36 eV on 116 compounds (Kim et al. 2020) and a mean absolute error of 0.53 eV on 472 (Borlido et al. 2019). The 0.25 eV default assumed for the run kit is optimistic until the kit's own controls say otherwise.

So with the current window, a full hybrid-functional calculation raises the best achievable probability from 0.18 to about 0.22 to 0.31. A calculation is still worth running, because it can show that a gap is far outside the window. It cannot show that a gap is inside.

**The best gap depends on how good the top cell is.** Using the repository's own two-layer model (idealised; the shape is informative, the values are not), with the top cell scaled to a fraction of its modelled limit:

| Top cell, fraction of its limit | Best top gap (eV) | Window within 1.0 point of the best (eV) |
|---|---|---|
| 1.00 | 1.73 | 1.49 to 1.95 |
| 0.75 | 1.90 | 1.61 to 2.24 |
| 0.60 | 2.06 | 1.73 to 2.53 |
| 0.50 | 2.28 | 1.86 to above 2.60 |

A poorer top cell should have a wider gap, so that more light reaches the silicon cell that converts it better. This is the same fact as the break-even result in the earlier audit, seen from the window side.

Two readings of the table, both fair:

- **For the current window.** 1.75 to 1.95 eV is close to the overlap of the first three rows (1.73 to 1.95 eV). It is the range that stays within 1 point of the best whether the top cell reaches 60% or 100% of its limit. It is a robust choice, not an arbitrary one.
- **Against it.** It is less than half as wide as the band for any single assumed quality, and so narrow that the probability ceiling stays below 0.31 for any calculation. Widening it trades robustness to top-cell quality for the ability to tell candidates apart.

At 50% of the limit the band starts at 1.86 eV and runs past the top of the scanned range, so half of the current window falls outside it. The best Sb2S3 cell on record (8.21% at a 1.70 eV gap) is at about 29% of the modelled limit for that gap.

This is a decision about the project's direction, so it is the owner's (task V4). The bottom "IR" layer, which the earlier audit recommended dropping, is part of the same decision.

### 3.3 Published hybrid-functional gaps exist

Kim et al. (2020) computed screened-hybrid gaps for 10,481 compounds taken from the Inorganic Crystal Structure Database, with cells up to 40 atoms, and published them as JSON files with relaxed structures. Of this project's 100 candidates, 65 are synthesised phases, so many may be in it.

Limits that matter here: spin-orbit coupling is included only for Tl, Pb or Bi compounds whose gap without it is below 1 eV, so Bi compounds with wider gaps will be too high; the gap is a one-shot evaluation at the band-edge k-points of the semilocal calculation; entries carry database collection codes, not Materials Project ids, so matching must be by structure.

Rule R8 applies: the data must be tested on the measured benchmark before it influences anything (task V5).

### 3.4 Queue order: information gain adds nothing here, cost does

The first reply recommended ordering the queue by information gain. On reflection that changes nothing in this pipeline. The decision is binary (in the window or not), and the information from resolving a binary outcome grows with its probability up to 0.5. Every window probability here is below 0.18, so the most informative calculation is always the one with the highest probability, which is how the queue is already sorted.

What the queue ignores is cost. Cells on the shortlist run from 3 to 40 sites, and a hybrid-functional run grows steeply with size. Ordering by window probability divided by relative cost, inside each queue class, changes the order materially. With the provisional exponent of 2 (`ASSUMED`, to be fitted to measured wall times): Sn4SI6 (22 sites) moves ahead of Al2Bi2Cu2S3Cl8 (34 sites); SnSSe (3 sites) moves to the front of its class; the 40-site entries move to the end. Summed over the 30 entries, the expected number of in-window gaps is about 4.

Calculations on compounds with measured gaps (the kit's controls) come before any candidate: they set the error bar for everything computed afterwards.

### 3.5 The temperature rule of thumb has the trend reversed

The pipeline uses an efficiency coefficient of `-0.44 / Eg**0.65` percent per kelvin, which makes wider gaps look better. The standard result (Green 2003; Dupre et al. 2015) is

`dVoc/dT = -(Eg0/q - Voc + gamma * k * T / q) / T`

so the loss per kelvin grows with the voltage deficit `Eg0/q - Voc`, not with the gap.

| Cell | Voltage deficit (V) | From the deficit formula, voltage only (% per K) | Rule of thumb, efficiency (% per K) |
|---|---|---|---|
| Good silicon, Voc 0.74 V | 0.46 | -0.24 | -0.41 |
| Sb2S3 record, Voc 0.824 V, gap 1.70 eV | 0.88 | -0.39 | -0.31 |

The voltage term is most, not all, of the efficiency coefficient, so the comparison favours the rule of thumb and it still comes out optimistic for the top cell. No measured temperature coefficient for an Sb or Bi chalcogenide cell was found in this review's searches; that is a gap in the literature check, not evidence of absence.

The field is also tagged `COMPUTED_HERE` in `RealWorldLCOEStressTestReport`. It is a rule of thumb and should be `HEURISTIC`.

### 3.6 The contact estimate was never benchmarked

`realistic_commercialization.py` places the conduction band at minus the geometric mean of the elements' Mulliken electronegativities, plus 1.65 eV times the Bi and Sb fraction, plus half the gap, and compares it with fixed values for TiO2 and SnO2. No penalty applies for offsets between -0.25 and +0.20 eV.

- The estimate has never been compared with a measured electron affinity, so its error is unknown. Measured values themselves vary with surface and preparation.
- The published acceptance range for Cu(In,Ga)Se2 is 0 to +0.4 eV (Minemoto et al. 2001, as cited by Chen et al. 2017), and a CdTe study recommends +0.3 eV. The code accepts a cliff of 0.25 eV, which the literature associates with voltage loss.
- Temperature moves offsets too: for kesterite with CdS a computed offset rises from 0.10 eV to 0.17 eV between a static lattice and 300 K (first-principles study, arXiv:1805.00022).

An estimate whose error is as large as the acceptable range cannot say whether an offset is favourable. Task V8 measures the error and reports `UNRESOLVED` when that is the case.

### 3.7 Defects and passivation

- **No bonus for lone-pair chemistry.** The outline's "intrinsically defect-tolerant" idea is usually argued from lone-pair cations and a high dielectric constant. Sb2Se3 has both, and a first-principles study finds that its lowest-energy defects have very deep levels, that vacancies cause a non-radiative voltage loss of 0.35 to 0.54 V, and that the trap-limited efficiency is 26% only under optimal growth conditions (18% when Sb-rich) (Wang et al. 2024). Chemistry-based tolerance rules have a known false positive in exactly this family.
- **No passivation multiplier.** The outline's "30% to 70% reduction in recombination" has no source. What the literature does give is specific measures with measured effects, for example oxygen exposure filling selenium vacancies and intermediate growth conditions (Wang et al. 2024). Those belong in the evidence table as records with sources (task V9).
- **Charged-defect calculations are out of reach locally.** They need hybrid-functional supercells of 60 to 120 atoms in several charge states. That is not a laptop job. The decision is deferred until the run kit has timing data (see "Not to be built" in the task file).

### 3.8 Vibrational stability

The funnel label `stage2_dynamically_and_ion_stable` names a property the stage does not compute; the stage uses a closed-form frequency estimate. Universal machine-learned potentials can now give useful harmonic phonons, but a benchmark on about 10,000 phonon calculations found that some models are accurate and others are not, including models that do well on energies and forces (Loew et al. 2025). A phonon check must therefore be run first on phases known to exist, to measure how often the chosen model wrongly reports instability (task V10).

---

## 4. What this project already has that the outline lacks

- A provenance tag on every number and an evidence tier on every card field.
- A gap estimate with a measured error bar and a window probability, instead of a hard filter.
- A stated success criterion: the top cell must clear the break-even efficiency against silicon alone.
- Cost, critical elements and the glass temperature limit.
- An ablation requirement before any dataset influences ranking (rule R8).
- Acceptance tests that fail until a task is really done.

---

## 5. The outline item by item

| Outline item | Status here | Verdict |
|---|---|---|
| Staged funnel, cheap to expensive | Present | Keep |
| Gap windows 0.4 eV wide (top 1.7 to 2.1) | Top window is 0.20 eV wide | The outline's width matches the band for one assumed top-cell quality; ours is the range that is robust to quality. Owner decision. Task V4 |
| Hard pre-filter at +/-0.2 eV on a predicted gap | Replaced by window probability | **Reject.** The error bar is 0.44 eV; such a filter discards good entries at random |
| "Required accuracy +/-0.1 to 0.2 eV" from hybrid functionals | Not assumed | **Reject as a premise.** Published errors are 0.36 to 0.53 eV |
| Machine-learned gap surrogate | Calibrated three-term model on 50 measured gaps | A published hybrid-gap table is a better next step than a new surrogate. Task V5 |
| Direct gap preferred, effective mass below 0.5 to 1 | Heuristic masses, being demoted to flags (G4) | Keep as flags only. Anisotropy matters more for ribbon structures |
| Hull distance below 50 to 100 meV | 50 meV rejects, 25 meV is "near" | Keep |
| Abundance and toxicity | Critical elements and cost | Keep. Toxicity (Pb, Cd, Tl) is not flagged yet: added to V2 as a flag |
| Failure-log match | Synthesis and device evidence, with ablation | Keep ours |
| "Under-explored bonus" | Rule R9: uniqueness is checked, not rewarded | **Reject.** Few attempts is weak evidence, and often means others already failed |
| Passivation recovery factor of 30% to 70% | Absent | **Reject.** No source. Use sourced mitigation records. Task V9 |
| Defect formation energies and transition levels | Heuristic depth, being demoted (G4) | Deferred: not feasible on local hardware |
| Temperature 25 to 80 C | Rule of thumb, mislabelled | Fix label, add the deficit formula. Task V7 |
| Phonons or molecular dynamics for stability | Closed-form estimate under a misleading name | Rename (V2), then a controlled check (V10) |
| Band alignment, tunnel junctions | Heuristic offset, never benchmarked. Tunnel junctions do not apply to a four-terminal stack | Benchmark it. Task V8 |
| Transfer-matrix optics, reflection losses | Present (Abeles method, graded coatings, oblique incidence) | Keep. Inputs are estimated optical constants |
| Thermal expansion, process compatibility | Glass limit only | Not added: a mechanically stacked four-terminal cell decouples the two processes |
| One weighted score and a "calibrated success probability" | Four axes and a queue class | **Reject.** There is nothing to calibrate against, and weights hide which evidence is weak |
| Bayesian optimisation or active learning for the queue | Sorted by probability | Reduces to probability per unit cost here. Task V6 |
| Uncertainty propagation | Gap only | Extended to the window ceiling (V4) and contact offsets (V8) |

---

## 6. How the recommendations changed from the first reply

| First reply | Now | Why |
|---|---|---|
| Add a contact-alignment step | Benchmark the one that exists | It exists |
| Add temperature coefficients | Fix the label and report the deficit formula beside the rule of thumb | It exists; changing it everywhere would move many pinned values for little gain |
| Add cheap defect-tolerance proxies | Do not | The best-studied relative is a counterexample |
| Order the queue by information gain | Order by probability per unit cost | Information gain is the same as probability here |
| Retrospective validation as one of six items | It is the first priority, and it already has a result | The audit shows 68 of 70 rejections rest on weak evidence |
| (not raised) | Window width and its dependence on top-cell quality | Found while checking the outline's wider windows against the device model |
| (not raised) | Published hybrid-gap database | Found while checking the outline's "selective hybrid" step |

---

## 7. Lessons to record

These were added to `docs/LESSONS_LEARNED.md` as L11 to L15 on 2026-11-16.

- **A rule written for the report was not applied to the code that feeds the report.** R2 governed the scorecards while the funnel rejected 68 of 100 candidates on heuristics. Whenever a rule is added, search for every place a decision of that kind is made, and add an audit that counts violations.
- **A screening rule was never run on a material known to work.** No gate had been tried on Sb2S3 or Sb2Se3. Keep a list of positive controls and run every rule on it.
- **"The project lacks X" was asserted without searching the code.** Two such statements in a review were wrong. Before saying something is missing, search for it by several names.
- **A target window was narrower than any available method could resolve.** Compare the width of every acceptance window with the error of the evidence that will be tested against it, before spending compute.
- **A sensible-sounding refinement was a no-op.** "Order by information gain" changes nothing when every probability is below one half. Work a refinement through on the real numbers before recommending it.

---

## 8. Sources

Opened on 2026-11-15.

- Hybrid-functional gap database, 10,481 compounds, error 0.36 eV on 116: Kim et al., Sci. Data 7, 387 (2020). https://pmc.ncbi.nlm.nih.gov/articles/PMC7658987/
- Functional benchmark on 472 compounds: Borlido et al., J. Chem. Theory Comput. 15, 5069 (2019). https://pmc.ncbi.nlm.nih.gov/articles/PMC6739738
- Sb2Se3 defects, 26% limit, growth conditions, oxygen: Wang, Kavanagh, Scanlon and Walsh, Joule 8, 2105 (2024). https://wmd-group.github.io/publications/2024/joule_sb2se3_24.pdf
- Sb2Se3 film orientation: Zhou et al., Nat. Photonics 9, 409 (2015). https://light.utoronto.ca/wp-content/uploads/2019/02/nphoton_2015_78.pdf
- Voltage temperature coefficient: Dupre, Vaillon and Green, Sol. Energy Mater. Sol. Cells 140, 92 (2015). https://www.researchgate.net/profile/Olivier-Dupre-2/publication/274071417_Physics_of_the_temperature_coefficients_of_solar_cells/links/59f0c8deaca272cdc7cdfecf/Physics-of-the-temperature-coefficients-of-solar-cells.pdf
- Silicon worked example (Eg0 1.2 eV, gamma 3, about 2.2 mV per degree): https://pveducation.org/es/node/127
- Conduction-band offset ranges: Chen et al., J. Electron. Mater. (2017), doi:10.1007/s11664-017-5850-9, citing Minemoto et al. (2001). https://physics.njit.edu/sites/physics/files/The%20Influence%20of%20Conduction%20Band%20Offset%20on%20CdTe%20Solar%20Cells.pdf
- Temperature dependence of a kesterite offset: arXiv:1805.00022. https://arxiv.org/pdf/1805.00022
- Machine-learned potentials for phonons: Loew et al. (2025). https://arxiv.org/abs/2412.16551
- Dimensionality scoring from structure: Larsen et al. (2019). https://arxiv.org/abs/1808.02114v1
- Sb2S3 at 8.21%: https://english.cas.cn/newsroom/research_news/phys/202510/t20251023_1094727.shtml

Not opened (publisher blocked the request), so not relied on for any number above: the 2025 and 2026 solar-cell efficiency tables and the 2026 emerging-photovoltaics report. Task V3 needs record efficiencies for the remaining controls and must open a source for each.
