# Independent Audit of FailSmart-MatEngine (2026-11-11)

**Scope:** repository at commit `460f3dc`. Four specialist reviews (code integrity, PV device physics, techno-economics, research strategy), each followed by an adversarial review that tried to overturn it. This file records what survived.

**Method and limits:** static analysis of the code and committed data, small standalone re-derivations, and literature checks. The repository's own modules and test suite were **not executed** (dependencies could not be installed in the review environment). Literature values marked "unconfirmed" were not verified against an opened primary source.

**Companion file:** [`REMEDIATION_TASKS.md`](REMEDIATION_TASKS.md) turns every finding below into an ordered task with acceptance checks.

---

## 1. Verdict

The repository is a tidy, well-structured screening scaffold whose headline results are not real.

- No DFT, HSE06+SOC, machine-learned potential, phonon, NEB or defect calculation is executed anywhere. `pyproject.toml` lists no MACE, CHGNet, phonopy, doped, atomate2, Quantum ESPRESSO wrapper or LangGraph.
- The only real physics inputs are Materials Project PBE records (structures, PBE gaps, hull energies, read from a committed cache) and the AM1.5G spectrum.
- Everything presented as "HSE06+SOC", "dynamical matrix", "NEB", "FNV" or "doped" is a closed-form heuristic or a constant.
- Device, cost and commercialization layers (versions 4 to 8) are stacked on those unvalidated inputs.

**Fair wording, after the adversarial round:**

- v3 and later: *mislabelled heuristic surrogates on real Materials Project inputs*. The formulas are printed openly in `MATHEMATICAL_SPEC_V2.md`.
- v2 pilot: *unsourced synthetic constants on random structures, published under "validated" and "HSE06+SOC" labels*.

---

## 2. What each headline quantity really is

Paths are relative to `failsmart_matengine/`.

| README quantity | What the code does | Evidence |
|---|---|---|
| Hull energy, v2 pilot | Hand-entered table | `physics_calculators.py:771-792` (`_RAW_STABILITY_DATA`) |
| Hull energy, v3 | Real Materials Project PBE value from cache; "G_hull" is hull minus 10.5 | `mp_live_discovery.py:669-670` |
| "HSE06+SOC" gaps, v2 | Hand-entered table; fallback formula is centred on the target window | `physics_calculators.py:909-1190`, `:1226-1229` |
| "HSE06+SOC" gaps, v3 | PBE gap + 0.31 + 3.30/eps_inf minus a linear spin-orbit term in element fractions | `mp_live_discovery.py:451-477` |
| eps_inf, v3 | Always the clipped heuristic: 0 of 117 cache records carry DFPT dielectric data | `mp_live_discovery.py:455-461` |
| Direct vs indirect gap | Direct = indirect + 0.01 or + 0.04 | `mp_live_discovery.py:468-473` |
| Effective masses, LO frequency, defect level | Composition heuristics; defect depth is one of five constants | `mp_live_discovery.py:479-515` |
| Minimum phonon frequency, v3 | `clip(0.55 + 0.0032*theta_D - 0.008*ehull, 0.35, 2.40)`; the gate is `> -0.10`, so it cannot fail | `mp_live_discovery.py:685`, `:689` |
| "3D dynamical matrix" | Positive pair springs `k = 48*exp((r0-d)/0.37)`, transverse `0.18k`, Gamma point only. Positive semi-definite by construction: zero imaginary modes for any structure | `atomistic_and_tmm.py:81-92` |
| "11-image NEB" barrier | One clipped closed-form expression; no images, energies or forces | `atomistic_and_tmm.py:180-187` |
| Migration barrier, v3 gate | If/else ladder on composition and shortest Cu/Ag distance | `mp_live_discovery.py:536-576` |
| "MLIP force std" | `0.038 + 0.0006*ehull`; there is no MLIP | `mp_live_discovery.py:759` |
| Mixing enthalpy, TCO reaction (gate A) | v2: hand-entered with pre-written veto notes. v3: `hmix` is 38.4 or 12.6, `tco_rxn = -26.0` | `tools.py:189-203`, `mp_live_discovery.py:855-857` |
| "FNV" correction | Point-charge `q^2 * alpha_M * 14.4 / (eps * L)`; no potential alignment | `atomistic_and_tmm.py:831-834` |
| "128D equivariant embedding" | Hashed composition features plus sin/cos of space-group number; no coordinates. Stored in a column named `mace_embedding` | `ledger.py:69-161` |
| Contrastive margin | Centroids are built from the same labels they score; the margin is non-negative for any labelling | `atomistic_and_tmm.py:959-970` |
| SLME, SQ limit | Real detailed-balance code on real AM1.5G; absorption is one generic curve set by the two gaps | `kinetics_and_optics.py:381` |
| TMM optics | Correct Abeles matrices on invented n,k dispersion models | `atomistic_and_tmm.py:273-291` |
| 4T efficiency 41 to 42% | Sum of radiative limits (ERE = 1) on the estimated gaps | `kinetics_and_optics.py:499-529` |
| LCOE and cost ratios | Standard discounting on assumed costs | `realistic_commercialization.py:272-287`, `:432-473` |
| Synthesis practicality score | Hand-weighted sum | `realistic_commercialization.py:141-151` |

---

## 3. Integrity findings

Each finding lists the adversary's verdict.

1. **Labels name methods that were never run.** "HSE06+SOC", "NEB", "dynamical matrix", "FNV", "doped" appear in README tables, schema field names and deck comments. *Upheld.*
2. **v2 "Validated Finalists" are fixtures.** Structures come from `pyxtal` random placement (`physics_calculators.py:276-300`); properties are typed in. *Upheld; "fabricated" softened to "synthetic constants under false labels".*
3. **Stability gates that cannot fail.** The v3 phonon gate, the spring-model mode count and the contrastive margin all pass by construction. The adversary confirmed numerically: 300 random periodic cells gave zero imaginary modes; 20,000 random labellings gave a positive margin. *Upheld.*
4. **The "independent verifier" is a second copy.** `independent_verifier.py:620-763` repeats the primary spring and barrier formulas. `verify_candidate_dossier` (`:2522-2792`) does recompute derived values (bond-valence index, neutrality, Frohlich alpha, SLME, SQ ceiling), so it catches coding slips, but it never examines the inputs. *Partly upheld.*
5. **Nothing is signed.** SHA-256 values are unkeyed digests of the verifier's own output (`independent_verifier.py:2775-2782`). *Upheld.*
6. **No agents exist.** No LLM or HTTP client is imported. "Agents" are string arguments to one sequential loop. `logs/team_checkins_and_debate.jsonl` is written by no code in the repository. *Upheld.*
7. **The failure ledger does not learn.** It is reset at the start of every run (`orchestrator.py:107`, `mp_live_discovery.py:1095`); its score is stored but feeds no gate (`ledger.py:392-418`). *Upheld.*
8. **Negative-synthesis priors change no decision.** A refractory element forces a temperature of at least 580 C (always rejected); otherwise risk is clipped to at most 0.42 (always passes) (`mp_live_discovery.py:782-790`). The per-system counts in `data/negative_synthesis_priors.json` sum to 34,639 recipes, not the cited 80,806. *Upheld.*
9. **Generated decks are not runnable workflows.**
   - Defect decks: `vac_el` holds the full label text, never matches an element, so site 0 is always removed (`atomistic_and_tmm.py:836-854`). The wrong species is removed in 7 of 8 decks.
   - The same label, with spaces and parentheses, becomes the `prefix` (`atomistic_and_tmm.py:864`).
   - `K_POINTS gamma` is combined with `noncolin` (`atomistic_and_tmm.py:874`, `:891`).
   - The minimum image distance uses lattice-vector lengths, so some "supercells" are primitive cells (`atomistic_and_tmm.py:826`).
   - HSE decks fix `nqx = 2 2 2` regardless of k-mesh; 6 of 13 are non-commensurate (`orchestrator.py:61`).
   - *Partly upheld (the q-mesh fault affects 6 of 13, not all).*
10. **Tests certify self-agreement.** Of 22 tests, roughly 16 pin the repository's own outputs or README strings, 2 are physical invariants, 2 are hygiene, and about 1.5 touch external truth. `repo_auditor.py:523-541` implements "bit-for-bit" as substring checks such as `assert "91" in text`. *Partly upheld (direction confirmed, exact count not re-derived).*
11. **Engineering.**
    - Three different versions: `__init__.py` 0.1.0, `pyproject.toml` 4.0.0, README v8.0.
    - Default paths point at `/home/antigravity/...` (`ledger.py:18`, `inter_team_bus.py:18`, `orchestrator.py:92`, `mp_live_discovery.py:1080`).
    - "Live" discovery reads the cache by default (`mp_live_discovery.py:234-237`).
    - Single commit; no lockfile; no CI; SQLite binaries and about 3.8 MB of generated JSON are committed; `ase` and `spglib` are declared but unused.
    - A docstring stated different coefficients from the code (fixed in this patch).

---

## 4. Science findings

### 4.1 The finalists

From the committed cache (`data/mp_live_candidates_cache.json`):

| ID | Formula | Marked experimentally known | Hull (meV/atom) | PBE gap (eV) | Claimed gap (eV) |
|---|---|---|---|---|---|
| mp-861911 | Sb2OS2 | No | 7.07 | 1.21 | 1.76 |
| mp-1227486 | BiSbS3 | No | 2.30 | 1.35 | 1.79 |
| mp-1078776 | BiInS3 | No | 15.08 | 1.40 | 1.90 |
| mp-1223998 | Bi3InSe6 | No | 17.99 | 0.52 | 0.75 |
| mp-1224922 | CuGaSnSe4 | No | 3.61 | 0.42 | 0.85 |
| mp-22982 | CuBiS2 | Yes | 0.00 | 0.47 | 0.85 |
| mp-23474 | AgBi3S5 | Yes | 0.00 | 0.53 | 0.85 |
| mp-1224129 | CuInSnSe4 | No | 5.17 | 0.36 | 0.78 |

- Six of eight are theoretical entries. None is a new discovery; CuBiS2 was proposed as an absorber in 2012.
- **CuBiS2:** literature puts the gap near 1.3 to 1.65 eV (unconfirmed exact values). If so it is transparent to the infrared it is meant to harvest. Check this first.
- **Sb2OS2:** one reviewer applied the gap of the mineral kermesite (about 2.0 eV). The adversary showed the entry is C2/m with 10 atoms while kermesite is triclinic, so the entry may be a different polymorph. Its gap is unknown.
- **BiSbS3:** an ordered cell of the known (Bi,Sb)2S3 solid solution. A gap of 1.4 to 1.55 eV is expected from the end members (unconfirmed), below the target window.
- **Cu compounds:** the surrogate adds about 0.4 eV to the PBE gap; the real correction for Cu-d chalcogenides is nearer 1 eV (reviewer's estimate, not benchmarked).

### 4.2 The "realistic" case is not realistic

- The base case assumes an external radiative efficiency of 1e-4, a top-cell open-circuit voltage of 1.22 to 1.25 V, fill factor 0.825 and about 16% efficiency.
- Best reported devices: Sb2S3 8.21%; Sb2(S,Se)3 11.02% lab and 10.7% certified (the same device). Implied radiative efficiencies are about 1e-9 to 3e-11, five to six and a half orders of magnitude below the assumption.
- Fill factors above about 0.73 have not been reported for this family (unconfirmed).
- First-principles capture calculations put sulfur vacancies as an intrinsic cap near 16% for Sb2S3. The repository's "base case" is therefore the theoretical ceiling.
- Honest base case: voltage 0.90 to 0.95 V, 7 to 9% opaque, 6 to 8% semi-transparent (7.46% demonstrated).

### 4.3 Architecture

- **Break-even.** A top cell near 1.8 eV takes roughly half of silicon's current. Break-even against a 24.5% silicon cell is about `24.5 - 13.1*T` percent, where T is sub-gap transmittance: 12.9% at the repository's own T of 0.88, 13.4% at 0.85. Demonstrated semi-transparent cells are near 7.5%, so a 4-terminal stack is net-negative today.
- **Rear infrared cell.** About 13% of AM1.5G power lies between 1100 and 1750 nm. The radiative ceiling is about 5 points; after realistic voltage losses about 1 remains, and an opaque rear cell removes bifacial gain. The repository's own Phase 11 and its test at `tests/test_scientific_integrity.py:1335` concede this. Drop it for these materials.
- **4n^2 light trapping** (`kinetics_and_optics.py:373-384`) is applied to a strongly absorbing film behind a wafer, where the limit does not apply.
- **"Bifacial 46 to 48% PCE"** adds rear irradiance to output while normalising to front irradiance only. Report it as bifacial-equivalent power density.
- **42% radiative figure** is not thermodynamically illegal, only uninformative: every subcell at ERE = 1 on unverified gaps.
- **Screening logic.** The lone-pair defect-tolerance argument is contradicted by experiment for Sb chalcogenides. Interfacial reaction energies of -13 to -15 meV/atom are within DFT noise, so the "ITO decomposes the absorber" result is not established either way.
- **Missing screens.** Non-radiative capture coefficients, dopability, measured band offsets, real absorption spectra, ribbon anisotropy, grain boundaries, cation disorder.

---

## 5. Techno-economic findings

Both the reviewer and the adversary reproduced the repository's LCOE numbers from the formula at `realistic_commercialization.py:272-287`.

- **The headline win is noise.** Path 2 at 4.234 against 4.246 cents/kWh is a 0.3% margin. Break-even top-cell efficiency in the repository's own model is 15.7%, against an assumed 15.83%.
- **Sensitivity (utility, repository formula):**

| Top-cell efficiency | LCOE (cents/kWh) | vs silicon alone |
|---|---|---|
| 6% | 5.73 | +35% |
| 8% | 5.32 | +25% |
| 10% | 4.98 | +17% |
| 11.9% | 4.70 | +11% |
| 15.83% (assumed) | 4.234 | -0.3% |

- **Rooftop is more favourable** (about 5% ahead, break-even near 14%), but still requires a cell that does not exist.
- **Omitted costs:** second junction box, rear transparent contact, coupling layer, pilot-scale capital, bankability premium. Adding 10 to 20 USD per square metre moves break-even to about 17 to 19%.
- **Degradation** is asserted at 0.50% per year for a material with no device.
- **String matching is internally inconsistent.** The 36:72 ratio is computed from a radiative operating voltage of 1.39 V per cell (`atomistic_and_tmm.py:1555-1560`), above the same report's "realistic" open-circuit voltage of 1.248 V. A consistent ratio is about 45 to 47 : 72. Strips 3 to 6 cm wide on thin ITO are resistively unworkable.
- **BIPV plan.** A 58.7% gross margin in months 6 to 18 has no device behind it. A long-standing listed competitor booked about 250 thousand AUD revenue against an 11.6 million AUD loss in FY2025. A 1.8 eV absorber gives red-brown glazing.
- **Competition.** Perovskite/silicon is at 35.5% certified (cell) and about 29% (full-size module), with commercial shipments since 2024.
- **Timeline.** Computed candidate to certified mini-module is historically 5 to 10 years and tens of millions of dollars (reviewer's estimate), against the plan's 6 to 36 months.

---

## 6. Strategy findings

- **Pattern.** Each version added downstream modelling without validating upstream inputs; verification compared the code with itself; names of real tools were attached to stand-ins.
- **Novelty.** The chemical space is actively worked by groups running the real calculations. A failure-aware screen is a legitimate idea (defect-aware screening has produced an experimentally confirmed absorber elsewhere), but only with real, mechanism-labelled failures and a demonstrated out-of-sample gain.
- **Overturned reviewer advice** (do not adopt):
  - A 30-material retrospective benchmark is too small: a rank correlation of 0.5 at n = 30 has a 95% interval of roughly 0.17 to 0.73.
  - Pivoting to indoor PV swaps one crowded field for another.
  - Full hybrid-functional defect calculations on three low-symmetry materials are one to two orders of magnitude beyond a 1 to 2 thousand USD budget.
  - Universal machine-learned potentials soften lone-pair lattices; use their phonons as a flag, never as a pass/fail gate.

---

## 7. What is real and worth keeping

- Materials Project query, filter and cache code, with element-policy and oxidation-state screening.
- Structure-derived dimensionality classification.
- AM1.5G detailed-balance, SQ-limit and transfer-matrix code (normal and oblique incidence).
- LCOE arithmetic, usable as an inverted requirements model.
- Pydantic schemas and the SQLite ledger schema.
- The negative-synthesis prior aggregation (as data, once its counts are reconciled).
- The Quantum ESPRESSO deck writer skeleton.
- The Phase 11 self-critique, which correctly kills the three-layer stack.

---

## 8. Prospects (panel judgement, not derived from data)

| Outcome | Probability |
|---|---|
| Venture as written | below 0.5% |
| A named finalist reaching 13% semi-transparent within 5 years | below 1 to 2% |
| Any finalist in a commercial module | below 1% |
| Current repository taken seriously by domain experts | below 2% |
| Journal methods paper within 9 months after re-scope | 8 to 30% (reviewer 30%, adversary 8 to 12%) |
| Useful open-source tool with real users, if rebuilt honestly | 5 to 20% |
| Value as a learning or portfolio project, once relabelled | about 80% |

---

## 9. Sources

- LONGi 35.5% tandem cell: https://www.longi.com/en/news/crystalline-silicon-perovskite-tandem-solar-cell-new-world-efficiency-2026/
- UNSW 11.02% antimony chalcogenide cell: https://www.unsw.edu.au/newsroom/news/2026/01/engineers-set-efficiency-world-record-for-emerging-solar-cell-material
- CAS 8.21% Sb2S3 cell: https://english.cas.cn/newsroom/research_news/phys/202510/t20251023_1094727.shtml
- Sulfur-vacancy efficiency limit for Sb2S3: https://arxiv.org/abs/2410.10560
- CuSbS2 and CuBiS2 as absorbers (2012): https://pubs.rsc.org/en/content/articlehtml/2012/cp/c2cp40916j
- Cu-Sb and Cu-Bi chalcogenide review: https://link.springer.com/article/10.1557/mre.2018.10
- Semi-transparent Sb2S3 7.46%: https://www.citedrive.com/en/discovery/highefficiency-allantimony-chalcogenide-tandem-solar-cells-via-thermalevaporated-cds-interface-engineering
- Defect-aware screen leading to BaCd2P2: https://pdf.arxiv.org/abs/2310.18188
- Charged-defect potentials for Sb2Se3: https://arxiv.org/abs/2603.05238
- Softening in universal potentials: https://arxiv.org/pdf/2405.07105
- Matbench Discovery leaderboard: https://matbench-discovery.materialsproject.org/
- ClearVue FY2025 annual report: https://www.clearvuepv.com/wp-content/uploads/2025/10/ClearVue-Annual-Report-FY-2025.pdf
- Trina 29.2% tandem module: https://www.trinasolar.com/en-glb/newsroom202606091645/
- Oxford PV first shipments: https://www.pv-tech.org/oxford-pv-ships-first-commercial-perovskite-tandem-modules/
- LBNL impurity-phase synthesis dataset: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12717135/
- Precursor Genome dataset: https://arxiv.org/abs/2607.09903
