# FailSmart-MatEngine (`v0.8.0`)

**Heuristic pre-screening scaffold and failure ledger for 4-Terminal "Silicon-Sandwich" Tandem Photovoltaics**

> [!WARNING]
> **Status (independent audit, 2026-11): heuristic pre-screen scaffold (first-principles calculations not run).**
> No DFT, HSE06+SOC, r2SCAN, MACE machine-learned potential, phonon, NEB or doped defect calculation is executed anywhere in this repository (not run).
> Band gaps, pair-spring Gamma frequencies, migration barriers and defect levels are closed-form heuristic estimates (v3+) or hand-entered fixture constants (v2 pilot).
> Efficiencies are radiative-limit ceilings or assumed-ERE parameterizations on those estimates, and the cost, LCOE and commercialization figures are conditional on them.
> Sequential functions carry role labels in one deterministic Python script (no LLM calls), and the self-consistency checker re-computes the same formulas to check arithmetic rather than physics.
> Read [`docs/INDEPENDENT_AUDIT_2026-11.md`](docs/INDEPENDENT_AUDIT_2026-11.md) before using any number below, and [`docs/REMEDIATION_TASKS.md`](docs/REMEDIATION_TASKS.md) for the remediation task list.

---

## Overview

`FailSmart-MatEngine` is a deterministic screening scaffold that shortlists **earth-abundant, phase-stable, inorganic chalcohalides and oxychalcogenides** ($\text{Bi/Sb–Cu/Zn/Sn–S/Se/O–Cl/Br/I}$) for a mechanically decoupled (4-Terminal) **Silicon-Sandwich** solar architecture:

1. **Top "Active Glass" Layer ($E_g \in [1.75, 1.95]\text{ eV}$):** Coated directly on soda-lime cover glass ($T_{\text{synth}} \le 500^\circ\text{C}$), harvesting blue/green photons at high voltage while transmitting $>85\%$ of red/IR light ($>670\text{ nm}$).
2. **Middle Anchor ($E_g = 1.12\text{ eV}$):** Commercial bifacial crystalline silicon wafer.
3. **Bottom IR Scavenger ($E_g \in [0.70, 0.85]\text{ eV}$):** Decoupled narrow-gap thin film beneath silicon harvesting $1100\text{–}1750\text{ nm}$ sub-bandgap infrared photons.

Candidate pass/fail outcomes are logged to a SQLite **Failure Memory Ledger** (`data/failure_memory.db` and `data/mp_live_failure_memory.db`). Current state: the failure gates combine cached Materials Project convex-hull records with heuristic rules, the ledger is reset at the start of every run, and its composition-vector cosine similarity does not feed any gate yet (task T11).

---

## Pipeline Stages, Code Behaviour & Data Provenance

Every numeric quantity emitted in the campaign schemas carries an explicit `ProvenanceTag` (`MP_DFT`, `LITERATURE`, `COMPUTED_HERE`, `HEURISTIC`, or `ASSUMED`). The table below states what each pipeline stage actually executes in code:

| Stage | Module / Function | What the code does | Provenance |
| :--- | :--- | :--- | :--- |
| **Stage 1: Candidate Ingestion & Stoichiometry** | `orchestrator.py`, `mp_live_discovery.py`, `physics_calculators.py` | Generates 20 `pyxtal` fixture crystals (v2) or loads 100 cached Materials Project crystals (`data/mp_live_candidates_cache.json`), checks Pauling charge neutrality, RoHS element policy, and bond-graph dimensionality (`pymatgen` `CrystalNN` / covalent radii). | `MP_DFT` (MP structures), `ASSUMED` (v2 fixtures), `COMPUTED_HERE` (dimensionality & neutrality) |
| **Stage 2: Hull, Elasticity & Ion-Migration Heuristics** | `tools.py::stage2_evaluate_stability`, `mp_live_discovery.py` | Reads cached Materials Project `e_above_hull` and DFT elastic moduli where present, otherwise applies electronegativity/packing heuristics; evaluates closed-form ion-migration barrier estimate `emig_heuristic_ev` ($\ge 0.65\text{ eV}$); sets `dynamically_stable = None` (phonons not run). | `MP_DFT` (cached hull & elastic tensors), `HEURISTIC` (fallback moduli, $\omega_{\min}$ estimate & $E_{\text{mig}}$), `ASSUMED` (v2 fixtures) |
| **Stage 3: Retrosynthesis, Priors, Pourbaix & Raw Cost** | `kinetics_and_optics.py`, `mp_live_discovery.py` | Checks refractory binary oxide sinks ($\text{ZrO}_2, \text{BaO}, \text{SrO}$), empirical LBNL solid-state impurity rates (`data/negative_synthesis_priors.json`, rejecting `impurity_rate > 0.50` when $n \ge 5$), rule-based $\text{pH } 4\text{–}9$ aqueous leaching heuristic, and bulk raw-element active-layer cost ($\le \$0.50/\text{m}^2$). | `LITERATURE` (LBNL/A-Lab prior counts & USGS raw element prices), `HEURISTIC` (reaction kinetics & Pourbaix solubility), `COMPUTED_HERE` (stoichiometric mass cost) |
| **Gate A: Structural Dimensionality Pre-Screen** | `tools.py::gate_a_adversarial_audit`, `mp_live_discovery.py` | Rejects 0D-isolated and 1D-chain crystal topologies for small-polaron localization risk; sets `anion_mixing_enthalpy_mev` and `tco_interface_rxn_energy_mev` to `None` on live MP candidates unless computed in Phase 11A. | `COMPUTED_HERE` (bond-percolation dimensionality), `ASSUMED` (v2 fixtures) |
| **Stages 4 & 5: Gap Estimate, Defect Heuristic & Scalar 4T Optics** | `mp_live_discovery.py::_estimate_gap_from_mp_pbe`, `kinetics_and_optics.py` | Applies an uncalibrated linear composition shift (`gap_est_*`) to the cached MP PBE band gap (hybrid DFT not run), estimates dielectric/polaron/defect heuristics, and integrates AM1.5G detailed-balance SLME and 4T subcell currents. | `MP_DFT` (PBE gap & DFPT dielectric where cached), `HEURISTIC` (gap shift, effective mass & defect depth), `COMPUTED_HERE` (AM1.5G quadrature) |
| **Step 1 (v4): Pair-Spring $\Gamma$ Frequencies & Migration Heuristic** | `atomistic_and_tmm.py::evaluate_spring_and_migration_heuristics` | Builds a positive pair-spring $3N \times 3N$ Hessian from interatomic distances (`spring_model_gamma_freq_thz`; phonons not run) and evaluates a closed-form steric/composition hop expression (`emig_heuristic_ev`; NEB not run). | `HEURISTIC` (pair-spring force constants & hop barrier), `COMPUTED_HERE` (matrix eigenvalues & neighbor geometry) |
| **Steps 2–3 & Phases 9–10: Coherent TMM, Input Decks & LCOE** | `atomistic_and_tmm.py`, `orchestrator.py` | Solves $2 \times 2$ Abeles coherent multilayer transfer-matrix optics (normal & oblique S/P), emits unexecuted Quantum ESPRESSO SCF and neutral-vacancy supercell input decks (`.in`, not run), and evaluates parameterized 25-year LCOE & string-matching formulas. | `COMPUTED_HERE` (Abeles TMM, stoichiometric lab batch & deck geometry), `HEURISTIC` / `ASSUMED` (refractive-index dispersion, degradation & BOS cost inputs) |
| **Phase 11: Cached MP Phase/TCO Equilibria & ERE Scenarios** | `realistic_commercialization.py` | Evaluates `pymatgen` `PhaseDiagram` chemical-potential stability windows and `InterfacialReactivity` against $\text{SnO}_2 / \text{In}_2\text{O}_3 / \text{TiO}_2$ from `data/mp_thermo_interface_cache.json`, combined with assumed external radiative efficiency (`ERE`) device scenarios. | `MP_DFT` (cached phase-diagram & TCO entries), `COMPUTED_HERE` (`pymatgen` hull/interface algebra), `ASSUMED` (`ERE`, fab yield & module cost parameters) |
| **Self-Consistency & Repository Audit** | `independent_verifier.py`, `ledger.py`, `repo_auditor.py` | Re-implements the same formulas (`scipy` / Rouard-Airy) to check arithmetic self-consistency, writes unkeyed `sha256_digest` hashes to SQLite (`composition_embedding`) and JSONL logs, and checks cross-file table/KaTeX consistency. | `COMPUTED_HERE` (arithmetic regression checks & SHA-256 digests) |

### Audit & Self-Consistency Logs
- **Scripted Stage Log:** [`logs/inter_team_communication.jsonl`](logs/inter_team_communication.jsonl) records stage-transition messages with unkeyed SHA-256 payload digests.
- **Self-Consistency Audit Log:** [`logs/verification_audit_log.jsonl`](logs/verification_audit_log.jsonl) records arithmetic re-computations from `independent_verifier.py`.
- **Test Suite Report:** [`docs/VERIFICATION_AND_TEST_REPORT.md`](docs/VERIFICATION_AND_TEST_REPORT.md) documents the automated `pytest` suite (`tests/test_scientific_integrity.py`).

---

## Repository Structure

```text
failsmart-matengine/
├── README.md                              # Project documentation, stage/provenance table & campaign summaries
├── docs/
│   ├── PLAN.md                            # Original architectural & scientific design target
│   ├── AGENT_STRUCTURE.md                 # Stage role prompts & gate definitions
│   ├── ENGINEERING_AND_REDUNDANCY_PLAN.md # Software structure & self-consistency protocol
│   ├── MEMORY_AND_FAILURE_LEDGER.md       # Failure Memory Ledger & campaign summary tables
│   └── VERIFICATION_AND_TEST_REPORT.md    # Automated test suite execution report
├── failsmart_matengine/
│   ├── __init__.py
│   ├── schemas.py                         # Provenance-tagged Pydantic data contracts for all stages
│   ├── ledger.py                          # SQLite + 128D composition_embedding Failure Memory Ledger
│   ├── tools.py                           # Stage 2/3/Gate-A/4/5 screening functions
│   ├── physics_calculators.py             # Crystallographic, BVS, and heuristic electronic calculators
│   ├── kinetics_and_optics.py             # Retrosynthesis, Pourbaix heuristics, and AM1.5G 4T quadrature
│   ├── independent_verifier.py            # Secondary arithmetic self-consistency checker
│   ├── inter_team_bus.py                  # Structured JSONL stage-message logger (SHA-256 digests)
│   ├── orchestrator.py                    # v2 fixture runner & QE input-deck writer
│   └── repo_auditor.py                    # Cross-repository table and Markdown/KaTeX consistency auditor
├── data/
│   └── failure_memory.db                  # SQLite + 128D composition_embedding Failure Memory database
├── logs/
│   ├── inter_team_communication.jsonl     # Stage-transition JSONL transcript
│   └── verification_audit_log.jsonl       # Arithmetic self-consistency SHA-256 digest log
├── tests/
│   └── test_scientific_integrity.py       # Automated regression and deck-validity test suite
└── outputs/
    ├── pilot_campaign_summary.json        # v2 fixture summary (20 records + 23 ledger + 5 prescreen finalists)
    └── qe_hse06_soc_decks/                # Unexecuted Quantum ESPRESSO HSE06+SOC input decks & CIFs (not run)
        ├── CAND-A02_Bi2CuO2SCl.cif
        ├── CAND-A02_Bi2CuO2SCl_hse06_soc.in  # input deck only (not run)
        ├── CAND-A03_Cu2SbS2Cl.cif
        ├── CAND-A03_Cu2SbS2Cl_hse06_soc.in   # input deck only (not run)
        ├── CAND-A06_BiZnOSCl.cif
        ├── CAND-A06_BiZnOSCl_hse06_soc.in    # input deck only (not run)
        ├── CAND-B02_Sn2SbSe2I3.cif
        ├── CAND-B02_Sn2SbSe2I3_hse06_soc.in  # input deck only (not run)
        ├── CAND-B04_Cu2BiSe2I.cif
        └── CAND-B04_Cu2BiSe2I_hse06_soc.in   # input deck only (not run)
```

---

## Compute, Time & API Cost Guide

### 1. Database & API Key Costs: **\$0 (100% Free)**
* **The Materials Project (`MP_API_KEY`):** Completely **free** at [next-gen.materialsproject.org/api](https://next-gen.materialsproject.org/api) (requires only a free GitHub, Google, or ORCID login; no credit card or subscription).
* **Alexandria, OQMD, COD & LBNL 80k Solid-State Impurity Dataset:** 100% open-access and free to download.
* **Offline Built-In Mode:** `failsmart-matengine` ships with cached Materials Project structures, hull entries, and LBNL/A-Lab synthesis priors so the local pre-screen runs out-of-the-box with **zero API keys required**.

### 2. Compute & Wall-Clock Time Requirements by Tier

| Execution Tier | Stages Covered | Hardware Needed | Wall-Clock Time | Est. Compute Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0: Fast Local Pre-Screen (Included Here)** | Stages 1–3 + Gate A + Analytical Stage 4/5 Heuristics | 2-core CPU / 8 GB RAM (runs in this VM or any laptop) | **< 5 seconds** (for 16–100 candidates) | **\$0** |
| **Tier 1: External Generative + Potential Sweep (not run)** | External crystal generation + universal potential relaxation + `phonopy` (not run) | 1x Consumer GPU (RTX 3090/4090, 24 GB VRAM) | **4–6 hours** | **\$0 local** (~\$36 cloud spot) |
| **Tier 2: External Hybrid DFT + Defect Supercells (not run)** | External Quantum ESPRESSO `HSE06+SOC` + `doped` supercells (not run) | HPC / Cloud CPU-GPU Nodes | **See Task T7** | **Requires owner approval (Task T7)** |

---

## Pilot Campaign v2.0 Summary Results

Running `python3 -m failsmart_matengine.orchestrator` executes the v2.0 fixture campaign across **20 Candidates Screened** (`16` fixture + `4` `SMACT` compositions `Sr2Cu2O2S`, `Ba2BiS3Cl`, `Ba2BiSe3I`, `Cu2SnSeI2`):

* **Stage 1 (SMACT + 3-Tier Policy + Symmetry):** 20 generated
* **Stage 2 (Fixture Hull + Elasticity + Phonon + Stage 2b Ion-Migration Heuristics):** 17 dynamically & ion-stable (`Sr2ZnOS2` rejected for $\Delta E_{\text{hull}} = 64.0\text{ meV/atom}$; `Zn2SbS2Br3` rejected for fixture $\omega_{\min} = -1.42\text{ THz}$; `CAND-A09` `Cu3BiS2Cl2` rejected at Stage 2b `ION_MIGRATION_INSTABILITY` with $E_{\text{mig}} = 0.42\text{ eV} < 0.65\text{ eV}$)
* **Stage 3 ($<500^\circ\text{C}$ Kinetics + Pourbaix $\text{pH } 4\text{–}9$ + Cost $\le \$0.50/\text{m}^2$):** 12 manufacturable (`BaZrS3` rejected for $950.0^\circ\text{C}$ $\text{ZrO}_2$ sink; `AgBiSe2` rejected for $\$0.5795/\text{m}^2$ Tier-2 $\text{Ag}$ cost; `Sr2Cu2O2S`, `Ba2BiS3Cl`, and `Ba2BiSe3I` rejected for $650.0^\circ\text{C}$ refractory alkaline-earth oxide sinks)
* **Gate A (Structural Dimensionality & Fixture Pre-Screen):** 8 promoted to Stage 4 (`BiSCl` and `SbSeI` vetoed for 1D-chain small-polaron risk; `BiCuSeI2` and `Cu2SnSeI2` vetoed for heuristic anion mixing enthalpy $\Delta H_{\text{mix}} > 35\text{ meV/atom}$)
* **Stages 4 & 5 (fixture gap and defect values + radiative-limit 3-Layer 4T Tandem Optics; `HSE06+SOC` and `doped` calculations not run):** **5 Prescreen Finalists** (none is confirmed by DFT or experiment; `Bi2SnSe3I2` rejected for deep SRH defect at $0.36\text{ eV}$; `BiCuOS` and `BaBiO2Cl` rejected for band gaps outside target window)

### v2 Pilot Prescreen Finalists (synthetic fixture values)

> [!CAUTION]
> The v2 pilot structures are `pyxtal` random placements and every property in this table comes from hand-entered lookup tables in `physics_calculators.py` (`_RAW_STABILITY_DATA`, `_RAW_ELECTRONIC_DATA`) and `tools.py` (`_GATE_A_DATA`). Treat these rows as test fixtures, not as predictions. Band-gap estimates carry the T4 benchmark error bar ($\pm 0.37\text{ eV}$ LOOCV MAE; see [`docs/GAP_CALIBRATION.md`](docs/GAP_CALIBRATION.md)).

| Candidate ID | Formula | Target Layer | Space Group | $N_{\text{sites}}$ | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $E_g^{\text{est}}$ ($\pm 0.37\text{ eV}$ Ind / Dir; heuristic, HSE06+SOC not run) | Single-Layer SLME (%) | SQ Limit (%) | 2-Layer Si $\eta$ (%) | 4T Std Si FCA $\eta$ (%) | **3-Layer 4T Tandem $\eta$ (%)** | Self-consistency SHA-256 digest (unkeyed) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-A02` | `Bi2CuO2SCl` | Top Active Glass | `I4/mmm` (#139) | 28 | 365.0 | \$0.0195 | 14.5 | 1.18 | 0.88 | 1.82 / 1.86 +/- 0.37 eV (P=0.21) | 24.40% | 26.78% | 38.32% | 40.45% | **41.67%** | `a20a11b8a87356615ed2dbf1cf9d78b0a506da656b2f522035708a91eb2981e9` |
| `CAND-A03` | `Cu2SbS2Cl` | Top Active Glass | `Pnma` (#62) | 24 | 320.0 | \$0.0129 | 21.0 | 1.05 | 0.74 | 1.79 / 1.83 +/- 0.37 eV (P=0.21) | 25.06% | 27.32% | 38.43% | 40.56% | **41.78%** | `11d0cc71c0ff065d442fec434bb5920620a02c649ddb865e37a32b7695c36abc` |
| `CAND-A06` | `BiZnOSCl` | Top Active Glass | `P4/nmm` (#129) | 10 | 380.0 | \$0.0148 | 18.2 | 1.29 | 0.98 | 1.85 / 1.89 +/- 0.37 eV (P=0.21) | 23.79% | 26.11% | 38.20% | 40.33% | **41.56%** | `8185c04696a2a053f41545b6e8cc3c4ba50cbe9ea9d90840eca3f5b20c5c3775` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom IR Scavenger | `Cmcm` (#63) | 32 | 295.0 | \$0.0865 | 12.6 | 0.88 | 0.75 | 0.75 / 0.78 +/- 0.37 eV (P=0.16) | 23.58% | 25.00% | 38.31% | 40.56% | **41.86%** | `8d2a220da8b781d0d9c9b7685baf2befb20b2dd749671de821a322ae923b049e` |
| `CAND-B04` | `Cu2BiSe2I` | Bottom IR Scavenger | `Pnma` (#62) | 24 | 345.0 | \$0.0509 | 11.2 | 1.09 | 0.71 | 0.74 / 0.76 +/- 0.37 eV (P=0.16) | 23.70% | 24.79% | 38.31% | 40.69% | **42.10%** | `e5a66a7b95475eb68e1518917f2c358ff2b84052a6d0ef8974ad46ed2e48a4c3` |

---

## Live Materials Project Discovery Campaign v3.0 Summary Results

Running `python3 -m failsmart_matengine.mp_live_discovery` executes the v3.0 discovery funnel on Materials Project records (read from the committed cache `data/mp_live_candidates_cache.json` by default; the API is queried only on refresh) across **100 Live MP Candidates** restricted to RoHS-clean Mixed-Anion & Lone-Pair ($ns^2$) chemical spaces ($\text{Bi/Sb–Cu/Zn/Sn/In/Ga/Ag–S/Se/O–Cl/Br/I}$):

* **Stage 1 (Live Materials Project Query & RoHS Filtering):** `100` live MP candidates ingested with verified non-toxic elements and Pauling charge neutrality.
* **Stage 2 (Thermodynamic Hull, Elasticity & Stage 2b Ion-Migration):** `91` dynamically & ion-stable candidates surviving ($6$ elastic instabilities and $3$ superionic migration instabilities vetoed with $E_{\text{mig}} < 0.65\text{ eV}$).
* **Stage 3 (LBNL 80k Impurity & A-Lab Precursor Genome Retrosynthesis):** `47` manufacturable candidates passing reaction network driving-force and negative-synthesis prior screening ($26$ rejected for `OXIDE_IMPURITY_SINK` from refractory oxide reactions, $5$ rejected for `IMPURITY_SINK_PRIOR` where empirical LBNL `impurity_rate > 0.50` across $n \ge 5$ recipes, $13$ rejected for `TIER2_COST_EXCEEDED` $> \$0.50/\text{m}^2$).
* **Gate A (Structural Dimensionality Pre-Screen):** `40` promoted to Stage 4/5 ($7$ vetoed for `LOW_DIM_POLARON_RISK` 1D-chains; anion mixing enthalpy and TCO reaction energy are `None` / not evaluated at Gate A).
* **Stages 4 & 5 (T4 benchmark-calibrated gap error bar $\pm 0.37\text{ eV}$, 1-error-bar window gate & double-pass Beer-Lambert radiative-limit 4T Tandem Optics; `HSE06+SOC` calculation not run):** **15 Prescreen Finalists** ($7$ Top Active Glass + $8$ Bottom IR Scavengers; $10$ rejected for `BANDGAP_OUT_OF_WINDOW` outside 1-error-bar windows $[1.38, 2.32]\text{ eV}$ top or $[0.33, 1.22]\text{ eV}$ bottom, and $15$ rejected for `LOW_OPTICAL_EFFICIENCY`).
* **Self-consistency re-computation:** `100/100` re-computations matched. This confirms arithmetic agreement between two implementations of the same formulas; it does not confirm the inputs or the physics.

### Open-Access Negative Synthesis Priors Integration
The v3.0 engine integrates two massive open-access empirical negative-synthesis databases (`data/negative_synthesis_priors.json`):
1. **LBNL Solid-State Impurity Dataset:** `80,806` parsed solid-state recipes across `4,292` chemical systems with `18,869` phase-impure/failed reactions (Lee, Cruse, Baibakova, Ceder, Jain, *Sci. Data* 12:1969, 2025).
2. **LBNL A-Lab "Precursor Genome" Dataset:** `1,035` autonomous laboratory pairwise reactions with `892` negative/stalled reactions (369 unreacted, 384 transformed, 113 partially reacted) (Walters, Szymanski, Fei, Ceder et al., *Precursor Genome*, 2026).

### Band-Gap Benchmark Calibration & Finalist Literature Gate (`docs/GAP_CALIBRATION.md`)
Evaluating the heuristic gap formula against **50 Materials Project compounds** with measured room-temperature optical band gaps (`data/gap_benchmark.csv`, [`docs/GAP_CALIBRATION.md`](docs/GAP_CALIBRATION.md)) shows:
* **Original heuristic (`0.31 + 3.30 / eps_inf - 1.00 * soc`):** Overall MAE = `0.4522 eV` (RMSE = `0.5651 eV`, bias = `-0.1906 eV`); on $\text{Cu/Ag}$-containing compounds ($n=18$), MAE = `0.5839 eV` with a systematic negative bias of `-0.5350 eV` (e.g., $\text{CuBiS}_2$ `mp-22982` estimated at `0.85 eV` vs. measured `1.65 eV`).
* **Refitted 3-coefficient linear model (`c0 + c1 / eps_inf + c2 * soc`):** Leave-one-out cross-validation (LOOCV) MAE = **`0.3684 eV`** (`5`-fold CV MAE = `0.3654 eV`, LOOCV RMSE = `0.4362 eV`, Leave-One-Chemical-Family-Out CV MAE = `0.4187 eV`).
* **Probabilistic Window Gate:** Because the `0.37 eV` LOOCV MAE is wider than the target spectral windows ($0.20\text{ eV}$ top, $0.15\text{ eV}$ bottom), Stage 4 admits any candidate within $1\sigma$ (`0.37 eV`) of the target window and reports `window_probability` ($P \le 0.21$), promoting `15` prescreen finalists (`7` Top Active Glass + `8` Bottom IR Scavengers) instead of the previous `9`.
* **Finalist Literature Gate (`data/finalist_literature.json`):** Among the original finalists, only `mp-22982` ($\text{CuBiS}_2$, $Pnma$ emplectite, measured optical gap `1.65 eV`) and `mp-23474` ($\text{AgBi}_3\text{S}_5$, $C2/m$ pavonite, no measured optical gap found in opened literature) correspond to synthesised polymorphs; `mp-861911` ($\text{Sb}_2\text{OS}_2$, monoclinic $C2/m$) is distinct from experimental triclinic $P\bar{1}$ kermesite (`mp-28711`, measured gap `2.04 eV`).

### Promoted Materials Project Prescreen Finalists (15 Finalists: 7 Track A + 8 Track B)

All 15 finalists have generated Quantum ESPRESSO `HSE06+SOC` input decks and CIF files in `outputs/mp_live_qe_decks/` and neutral-vacancy supercell decks in `outputs/mp_live_neutral_vacancy_decks/` (`HSE06+SOC` not run). Every gap estimate is reported with the T4 LOOCV error bar ($\pm 0.37\text{ eV}$) and Gaussian window probability $P$, and thin-film absorptance uses double-pass Beer-Lambert ($1 - \exp(-2\alpha d)$, `path_length_factor = 2.0`):

| Candidate ID | Formula | Target Layer | Space Group | $N_{\text{sites}}$ | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $E_g^{\text{est}}$ ($\pm 0.37\text{ eV}$ Ind / Dir; heuristic, HSE06+SOC not run) | Single-Layer SLME (%) | SQ Limit (%) | 2-Layer Si $\eta$ (%) | 4T Std Si FCA $\eta$ (%) | **3-Layer 4T Tandem $\eta$ (%)** | Self-consistency SHA-256 digest (unkeyed) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `mp-861911` | `Sb2OS2` | Top Active Glass | `C2/m` (#12) | 10 | 375.0 | \$0.0157 | 7.07 | 1.40 | 1.18 | 1.76 / 1.80 +/- 0.37 eV (P=0.21) | 25.63% | 27.93% | 38.45% | 40.57% | **41.78%** | `ca8633a88b75efb39fa1a8961438e36e9a75b2fba1d200d00fb2bc6968b584c1` |
| `mp-1227486` | `BiSbS3` | Top Active Glass | `Pnma` (#62) | 20 | 375.0 | \$0.0182 | 2.30 | 1.20 | 1.18 | 1.79 / 1.83 +/- 0.37 eV (P=0.21) | 25.04% | 27.32% | 38.36% | 40.48% | **41.69%** | `b06b67e9b54f77e75af1658755fa8dc745d49de7967eaf35542e4052fed60be1` |
| `mp-1195160` | `Al2Bi2Cu2S3Cl8` | Top Active Glass | `P6_3/m` (#176) | 34 | 335.0 | \$0.0128 | 6.02 | 1.33 | 0.87 | 1.82 / 1.83 +/- 0.37 eV (P=0.21) | 25.57% | 26.78% | 38.91% | 41.04% | **42.25%** | `2504e7e4e5c3165c7d4c60642fc44883e5a4dd3fe8b1a4be4a44328eb835ea53` |
| `mp-1078776` | `BiInS3` | Top Active Glass | `P2_1/m` (#11) | 10 | 375.0 | \$0.2681 | 15.08 | 1.11 | 1.18 | 1.90 / 1.94 +/- 0.37 eV (P=0.21) | 22.79% | 25.00% | 37.88% | 39.99% | **41.21%** | `1acff904de905deb123a0304ec4229487386e25c507b3c25f435eb0eba7922fe` |
| `mp-715212` | `Bi3In5S12` | Top Active Glass | `P1` (#1) | 40 | 375.0 | \$0.3484 | 18.25 | 1.31 | 1.18 | 1.71 / 1.75 +/- 0.37 eV (P=0.20) | 26.53% | 28.85% | 38.51% | 40.63% | **41.84%** | `5edc9648a4bbd9c8513239cf86feecdc266ba2ab91a716439401cdb3bbe063ab` |
| `mp-1206068` | `Bi2InS4Br` | Top Active Glass | `C2/m` (#12) | 8 | 335.0 | \$0.1597 | 2.74 | 1.25 | 0.96 | 2.02 / 2.06 +/- 0.37 eV (P=0.19) | 20.36% | 22.39% | 37.11% | 39.22% | **40.44%** | `e23863d2320c89cf4ab9d315bbb936e689a90c74d9d2e34fe9c3fb6c67c6eef2` |
| `mp-1228963` | `AgAlSnSe4` | Top Active Glass | `I-4` (#82) | 7 | 375.0 | \$0.3093 | 0.00 | 1.27 | 0.98 | 1.59 / 1.60 +/- 0.37 eV (P=0.17) | 29.46% | 30.71% | 38.78% | 40.92% | **42.13%** | `5c31ec1fc067f26555e19bc8054766be21f863004e4404a9f205a8a0affa738a` |
| `mp-1223998` | `Bi3InSe6` | Bottom IR Scavenger | `R3m` (#160) | 10 | 375.0 | \$0.1507 | 17.99 | 1.33 | 1.18 | 0.75 / 0.76 +/- 0.37 eV (P=0.16) | 24.22% | 25.00% | 38.31% | 40.77% | **42.22%** | `bc1763b9c1fd5ca7bb3c229dab5cb71df78ebc934f8d7b4f541cc55e1f318165` |
| `mp-1224922` | `CuGaSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.1251 | 3.61 | 1.28 | 0.98 | 0.85 / 0.86 +/- 0.37 eV (P=0.16) | 26.72% | 27.20% | 38.31% | 40.62% | **41.75%** | `83d9eae3e9030497bd6cffc681af72366eb931445425778f8237b86ff54ad309` |
| `mp-22982` | `BiCuS2` | Bottom IR Scavenger | `Pnma` (#62) | 16 | 375.0 | \$0.0237 | 0.00 | 1.27 | 0.95 | 0.85 / 0.89 +/- 0.37 eV (P=0.16) | 26.59% | 27.20% | 38.31% | 40.59% | **41.71%** | `1343e05d0bac7ab69d6502e80c49fb1dc71d8664ee520300ba88a664d59dc394` |
| `mp-23474` | `AgBi3S5` | Bottom IR Scavenger | `C2/m` (#12) | 18 | 375.0 | \$0.2558 | 0.00 | 1.18 | 0.98 | 0.85 / 0.89 +/- 0.37 eV (P=0.16) | 26.59% | 27.20% | 38.31% | 40.59% | **41.71%** | `dba1689a432cf7c456d6a5b12a7cf5503b7ad8c901562f93a22bbef8964b5b26` |
| `mp-1224129` | `CuInSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.2664 | 5.17 | 1.21 | 0.98 | 0.78 / 0.82 +/- 0.37 eV (P=0.16) | 23.86% | 25.60% | 38.31% | 40.34% | **41.44%** | `2bbe21c2c192897a893c09e53d48e5fc373d4e0aa987dac6c58e95f0980a4eaa` |
| `mp-1224102` | `CuInSnS4` | Bottom IR Scavenger | `Imma` (#74) | 14 | 375.0 | \$0.3489 | 1.63 | 1.43 | 0.98 | 0.91 / 0.95 +/- 0.37 eV (P=0.15) | 28.57% | 29.89% | 38.31% | 40.59% | **41.66%** | `b357f6a40a24f92e42fb05b3463ff85a3897f15679b89a1b85e4f791fe372897` |
| `mp-20331` | `CuSbSe2` | Bottom IR Scavenger | `Pnma` (#62) | 16 | 375.0 | \$0.0348 | 14.68 | 1.12 | 0.96 | 0.92 / 0.96 +/- 0.37 eV (P=0.15) | 28.69% | 30.37% | 38.31% | 40.48% | **41.51%** | `8f055c904cb247479abc2adb0094fc9657e2703891d89c570b8e6d34b431a854` |
| `mp-1229027` | `AlCuSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.0438 | 0.00 | 1.34 | 0.98 | 0.99 / 1.00 +/- 0.37 eV (P=0.14) | 30.44% | 31.49% | 38.31% | 40.15% | **41.00%** | `ae36159dd978960a210a67cff56613f5fb2ce311f2f2b44279d5f612bd1d7c2c` |

### Top Cross-Layer 4-Terminal Tandem Stacks (56 Pairs Screened)

The 7 Top Active Glass and 8 Bottom IR Scavenger finalists yield `56` mechanically decoupled 4-terminal tandem stacks with middle crystalline silicon ($E_g = 1.12\text{ eV}$):

| Pair ID | Top MP Cell | Bottom MP Cell | Top $E_g$ (Ind/Dir) | Bottom $E_g$ (Ind/Dir) | Top PCE (%) | Middle c-Si PCE (%) | Bottom IR PCE (%) | Combined Cost ($\$/\text{m}^2$) | **4T Tandem Total PCE (%)** |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-1195160__mp-1223998` | `mp-1195160` (Al2Bi2Cu2S3Cl8) | `mp-1223998` (Bi3InSe6) | 1.82 / 1.83 eV | 0.75 / 0.76 eV | 25.57% | 12.40% | 4.81% | \$0.1635 | **42.79%** |
| `mp-1228963__mp-1223998` | `mp-1228963` (AgAlSnSe4) | `mp-1223998` (Bi3InSe6) | 1.59 / 1.60 eV | 0.75 / 0.76 eV | 29.46% | 8.43% | 4.78% | \$0.4600 | **42.67%** |
| `mp-715212__mp-1223998` | `mp-715212` (Bi3In5S12) | `mp-1223998` (Bi3InSe6) | 1.71 / 1.75 eV | 0.75 / 0.76 eV | 26.53% | 11.05% | 4.80% | \$0.4991 | **42.38%** |
| `mp-1195160__mp-1224922` | `mp-1195160` (Al2Bi2Cu2S3Cl8) | `mp-1224922` (CuGaSnSe4) | 1.82 / 1.83 eV | 0.85 / 0.86 eV | 25.57% | 12.40% | 4.34% | \$0.1379 | **42.32%** |
| `mp-861911__mp-1223998` | `mp-861911` (Sb2OS2) | `mp-1223998` (Bi3InSe6) | 1.76 / 1.80 eV | 0.75 / 0.76 eV | 25.63% | 11.89% | 4.80% | \$0.1664 | **42.32%** |
| `mp-1195160__mp-22982` | `mp-1195160` (Al2Bi2Cu2S3Cl8) | `mp-22982` (BiCuS2) | 1.82 / 1.83 eV | 0.85 / 0.89 eV | 25.57% | 12.40% | 4.30% | \$0.0365 | **42.28%** |
| `mp-1195160__mp-23474` | `mp-1195160` (Al2Bi2Cu2S3Cl8) | `mp-23474` (AgBi3S5) | 1.82 / 1.83 eV | 0.85 / 0.89 eV | 25.57% | 12.40% | 4.30% | \$0.2686 | **42.28%** |
| `mp-1195160__mp-1224102` | `mp-1195160` (Al2Bi2Cu2S3Cl8) | `mp-1224102` (CuInSnS4) | 1.82 / 1.83 eV | 0.91 / 0.95 eV | 25.57% | 12.40% | 4.25% | \$0.3617 | **42.23%** |
| `mp-1227486__mp-1223998` | `mp-1227486` (BiSbS3) | `mp-1223998` (Bi3InSe6) | 1.79 / 1.83 eV | 0.75 / 0.76 eV | 25.04% | 12.39% | 4.80% | \$0.1689 | **42.22%** |
| `mp-1228963__mp-1224922` | `mp-1228963` (AgAlSnSe4) | `mp-1224922` (CuGaSnSe4) | 1.59 / 1.60 eV | 0.85 / 0.86 eV | 29.46% | 8.43% | 4.31% | \$0.4344 | **42.20%** |
| `mp-1228963__mp-22982` | `mp-1228963` (AgAlSnSe4) | `mp-22982` (BiCuS2) | 1.59 / 1.60 eV | 0.85 / 0.89 eV | 29.46% | 8.43% | 4.27% | \$0.3330 | **42.15%** |
| `mp-1228963__mp-23474` | `mp-1228963` (AgAlSnSe4) | `mp-23474` (AgBi3S5) | 1.59 / 1.60 eV | 0.85 / 0.89 eV | 29.46% | 8.43% | 4.27% | \$0.5651 | **42.15%** |
| `mp-1228963__mp-1224102` | `mp-1228963` (AgAlSnSe4) | `mp-1224102` (CuInSnS4) | 1.59 / 1.60 eV | 0.91 / 0.95 eV | 29.46% | 8.43% | 4.22% | \$0.6582 | **42.10%** |
| `mp-1195160__mp-20331` | `mp-1195160` (Al2Bi2Cu2S3Cl8) | `mp-20331` (CuSbSe2) | 1.82 / 1.83 eV | 0.92 / 0.96 eV | 25.57% | 12.40% | 4.11% | \$0.0476 | **42.08%** |
| `mp-1195160__mp-1224129` | `mp-1195160` (Al2Bi2Cu2S3Cl8) | `mp-1224129` (CuInSnSe4) | 1.82 / 1.83 eV | 0.78 / 0.82 eV | 25.57% | 12.40% | 4.03% | \$0.2792 | **42.01%** |

*Key Efficiency / Cost Pareto Highlights:*
* **Highest radiative-limit pair (scalar idealization, not a device forecast):** `mp-1195160 Al2Bi2Cu2S3Cl8 + c-Si + mp-1223998 Bi3InSe6` achieves **42.79%** 4T PCE ($25.57\%$ top $+ 12.40\%$ middle $+ 4.81\%$ bottom IR; `38.91%` 2-layer default) at $\$0.1635/\text{m}^2$.
* **Lowest active-layer material cost pair (scalar idealization; material cost is a negligible share of module cost):** `mp-1195160 Al2Bi2Cu2S3Cl8 + c-Si + mp-22982 BiCuS2` delivers **42.28%** 4T PCE (`38.91%` 2-layer default) at an ultra-abundant active layer cost of **\$0.0365/m²** (`mp-861911 Sb2OS2 + c-Si + mp-22982 BiCuS2` at **\$0.0394/m²**).

---

## v4.0 Pair-Spring Gamma Heuristics, Migration Estimates & Coherent Multilayer TMM (Step 1 + Step 2)

### Step 1: Gamma-point pair-spring model & closed-form migration-barrier heuristic (phonons and NEB not run)

> [!CAUTION]
> The force constants are positive pair springs set by bond length, so `dynamically_stable` is reported as `None` (phonons not run). The migration barrier `emig_heuristic_ev` is a closed-form expression in hop distance, clearance and composition (NEB not run). Neither metric is evidence of dynamical stability or low ion mobility (task T7).

Every promoted Materials Project prescreen finalist is evaluated on its 3D periodic crystal structure via $3N \times 3N$ pair-spring Hessian eigenvalues (`spring_model_gamma_freq_thz`, `numpy.linalg.eigh` in `atomistic_and_tmm.py` vs. `scipy.linalg.eigvalsh` in `independent_verifier.py`) and the closed-form steric/composition migration heuristic `emig_heuristic_ev`:

| Candidate ID | Formula | Hessian Dim | $\omega_{\text{opt,min}}^{\text{spring}}$ (THz) | $\omega_{\text{LO,max}}^{\text{spring}}$ (THz) | Hop Species & $d_{\text{hop}}$ ($\text{\AA}$) | Bottleneck $r_{\text{clear}}$ ($\text{\AA}$) | `emig_heuristic_ev` (eV) | $D_{\text{ion}}(300\text{ K})$ ($\text{cm}^2/\text{s}$) | Digest Prefix |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `mp-861911` | `Sb2OS2` | $30\times 30$ | 5.80 | 35.90 | $\text{O}$ ($2.46\text{ \AA}$) | 1.69 | **1.058 eV** | $1.69\times 10^{-22}$ | `11f84cfc` |
| `mp-1227486` | `BiSbS3` | $60\times 60$ | 2.38 | 22.24 | $\text{S}$ ($3.43\text{ \AA}$) | 2.63 | **0.998 eV** | $3.41\times 10^{-21}$ | `960a304d` |
| `mp-1195160` | `Al2Bi2Cu2S3Cl8` | $102\times 102$ | 1.71 | 52.02 | $\text{Cu}$ ($3.82\text{ \AA}$) | 1.25 | **1.367 eV** | $2.64\times 10^{-27}$ | `e1462875` |
| `mp-1078776` | `BiInS3` | $30\times 30$ | 6.27 | 22.73 | $\text{S}$ ($3.64\text{ \AA}$) | 1.89 | **1.120 eV** | $3.35\times 10^{-23}$ | `9486d5fa` |
| `mp-1223998` | `Bi3InSe6` | $30\times 30$ | 1.36 | 16.11 | $\text{Se}$ ($3.67\text{ \AA}$) | 3.46 | **0.990 eV** | $5.18\times 10^{-21}$ | `a004f3dc` |
| `mp-1224922` | `CuGaSnSe4` | $21\times 21$ | 9.19 | 20.70 | $\text{Cu}$ ($5.68\text{ \AA}$) | 2.32 | **1.310 eV** | $5.33\times 10^{-26}$ | `56e7b978` |
| `mp-22982` | `BiCuS2` | $48\times 48$ | 3.90 | 26.21 | $\text{Cu}$ ($3.85\text{ \AA}$) | 1.24 | **1.348 eV** | $5.59\times 10^{-27}$ | `52e94916` |
| `mp-23474` | `AgBi3S5` | $54\times 54$ | 3.02 | 23.60 | $\text{Ag}$ ($4.03\text{ \AA}$) | 2.06 | **1.120 eV** | $4.15\times 10^{-23}$ | `87216e59` |
| `mp-1224129` | `CuInSnSe4` | $21\times 21$ | 8.44 | 19.38 | $\text{Cu}$ ($5.90\text{ \AA}$) | 2.47 | **1.326 eV** | $3.12\times 10^{-26}$ | `ba119440` |

### Step 2: Coherent Multilayer $2\times 2$ Abeles Transfer-Matrix Method (TMM) vs. Recursive Rouard/Airy 4T Stack Optics
Replacing scalar Fresnel idealizations with a full 6-medium coherent thin-film interference solver (`Air / 98 nm MgF2 ARC / 105 nm Front ITO / Active Absorber / 85 nm SiO2-ITO Buffer / Couplant -> Textured c-Si -> Bottom IR Scavenger / Double-Pass Ag Mirror`) cross-verified between $2\times 2$ Abeles matrix multiplication (`np.trapezoid`) and Recursive Rouard/Airy backward amplitude addition (`scipy.integrate.simpson`, $\le 0.01\%$ discrepancy):

| Pair ID | Top MP Cell | Bottom MP Cell | Mean Front $R_{\text{TMM}}$ (%) | Sub-Gap $T_{\text{TMM}}$ (%) | Top PCE (%) | Middle c-Si PCE (%) | Bottom IR PCE (%) | 2-Layer PCE (%) | 4T Std Si PCE (%) | **Coherent 4T Low-FCA PCE (%)** | Scalar $\rightarrow$ TMM $\Delta$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-1195160__mp-1223998` | `Al2Bi2Cu2S3Cl8` | `Bi3InSe6` | 11.04% | 89.08% | 23.02% | 12.75% | 4.94% | 36.73% | 39.22% | **40.71%** | $-2.08\%$ |
| `mp-1195160__mp-1224922` | `Al2Bi2Cu2S3Cl8` | `CuGaSnSe4` | 11.04% | 89.08% | 23.02% | 12.75% | 4.35% | 36.73% | 39.00% | **40.12%** | $-2.20\%$ |
| `mp-1195160__mp-22982` | `Al2Bi2Cu2S3Cl8` | `BiCuS2` | 11.04% | 89.08% | 23.02% | 12.75% | 4.31% | 36.73% | 38.97% | **40.07%** | $-2.21\%$ |
| `mp-1195160__mp-23474` | `Al2Bi2Cu2S3Cl8` | `AgBi3S5` | 11.04% | 89.08% | 23.02% | 12.75% | 4.31% | 36.73% | 38.97% | **40.07%** | $-2.21\%$ |
| `mp-715212__mp-1223998` | `Bi3In5S12` | `Bi3InSe6` | 11.44% | 88.67% | 23.74% | 11.45% | 4.88% | 36.14% | 38.61% | **40.07%** | $-2.31\%$ |
| `mp-1195160__mp-1224102` | `Al2Bi2Cu2S3Cl8` | `CuInSnS4` | 11.04% | 89.08% | 23.02% | 12.75% | 4.28% | 36.73% | 38.98% | **40.04%** | $-2.19\%$ |

*Key Physical Insight from Coherent TMM:* High refractive indices ($n_1 \approx 2.8\text{–}3.1$) of heavy pnictogen chalcohalides/oxychalcogenides produce $11.01\%\text{–}11.97\%$ broadband front reflectance despite a single-layer $\text{MgF}_2/\text{ITO}$ anti-reflection coating, while sub-bandgap IR transmittance rises to $88.25\%\text{–}89.08\%$. Under radiative-limit coherent optics, `mp-1195160 Al2Bi2Cu2S3Cl8 + c-Si + mp-1223998 Bi3InSe6` reaches **36.73% 2-Layer PCE** (**40.71% Coherent 4T PCE** with optional rear IR cell).

### Step 3: 7-Medium Graded-ARC + $\text{TiO}_2$ Impedance-Matching Stack & 4-Metric Techno-Economic Figure-of-Merit Suite
Inserting a $48\text{ nm}$ high-index $\text{TiO}_2$ optical impedance-matching layer ($n_3 \approx 2.38$) between Front $\text{ITO}$ ($80\text{ nm}$) and the Top Active Absorber (`Air / 94 nm MgF2 / 80 nm ITO / 48 nm TiO2 / Absorber / 82 nm Buffer / Couplant`) suppresses mean front reflection from **$11.04\%\text{–}11.97\%$ down to $2.42\%\text{–}3.33\%$** ($-8.57\%$ to $-8.75\%$ reduction), recovering **$+2.20\%$ to $+2.58\%$** in radiative-limit coherent efficiency (**39.12% 2-Layer PCE** / **43.08% 3-Layer 4T PCE**).

We simultaneously evaluate all 4 Techno-Economic Figures of Merit against a single-junction $22.0\%$ c-Si baseline ($C_{\text{Si,mod}} = \$40/\text{m}^2$, $C_{\text{BOS,area}} = \$100/\text{m}^2$, $\$6.50/\text{m}^2$ TCO/coating process overhead per added subcell):
1. **$\text{CER}_N$ (Normalized Multi-Junction Cost-Efficiency Ratio):** $\frac{\eta_{\text{stack}} / \eta_{\text{Si}}}{(C_{\text{Si,mod}} + \Delta C) / (N \cdot C_{\text{Si,mod}})}$ ($N=2$ or $3$).
2. **$\text{MCIW}_{\text{raw}}$ / $\text{MCIW}_{\text{full}}$ (Marginal Cost per Incremental Watt, $\$/\Delta\text{W}_{\text{p}}$):** $\frac{\Delta C}{1000(\eta_{\text{stack}} - \eta_{\text{Si}})}$ vs. $\$0.1818/\text{W}_{\text{p}}$ baseline Si.
3. **$\text{CPR}_{\text{mod}}$ (Factory-Gate Module Cost-Performance Ratio):** $\frac{\eta_{\text{stack}} / \eta_{\text{Si}}}{1 + \Delta C / C_{\text{Si,mod}}}$.
4. **$\text{SVI}_{\text{BOS}}$ (Area-Constrained System Value Index):** $\frac{\eta_{\text{stack}} / \eta_{\text{Si}}}{(C_{\text{Si,mod}} + \Delta C + C_{\text{BOS,area}}) / (C_{\text{Si,mod}} + C_{\text{BOS,area}})}$.

| Pair ID | Stack (`Top + c-Si + Bot`) | $R_{\text{front}}$ ($\text{1-ARC}\rightarrow\text{Graded}$) | Graded 2L PCE ($\text{W/ft}^2$) | **Graded 4T PCE ($\text{W/ft}^2$)** | $\text{CER}_{\text{2L}}$ / **$\text{CER}_{\text{3L}}$** | $\text{MCIW}_{\text{3L}}$ (Raw / Full $\$/\Delta\text{W}$) | $\text{CPR}_{\text{mod}}$ (2L / 3L) | **$\text{SVI}_{\text{BOS}}$ (2L / 3L)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-1195160__mp-1223998` | `Al2Bi2Cu2S3Cl8 + c-Si + Bi3InSe6` | $11.04\% \rightarrow \mathbf{2.47\%}$ | 39.12% ($36.3\text{ W/ft}^2$) | **43.08%** ($40.0\text{ W/ft}^2$) | $3.058$ / **$4.420$** | $\$0.0008$ / **$\$0.0624$** | $1.529$ / $1.473$ | $1.699$ / **$1.790$** |
| `mp-1228963__mp-1223998` | `AgAlSnSe4 + c-Si + Bi3InSe6` | $11.43\% \rightarrow \mathbf{2.98\%}$ | 38.74% ($36.0\text{ W/ft}^2$) | **42.66%** ($39.6\text{ W/ft}^2$) | $3.010$ / **$4.353$** | $\$0.0022$ / **$\$0.0652$** | $1.505$ / $1.451$ | $1.679$ / **$1.769$** |
| `mp-1195160__mp-1224922` | `Al2Bi2Cu2S3Cl8 + c-Si + CuGaSnSe4` | $11.04\% \rightarrow \mathbf{2.47\%}$ | 39.12% ($36.3\text{ W/ft}^2$) | **42.63%** ($39.6\text{ W/ft}^2$) | $3.058$ / **$4.376$** | $\$0.0007$ / **$\$0.0637$** | $1.529$ / $1.459$ | $1.699$ / **$1.772$** |
| `mp-1195160__mp-22982` | `Al2Bi2Cu2S3Cl8 + c-Si + BiCuS2` | $11.04\% \rightarrow \mathbf{2.47\%}$ | 39.12% ($36.3\text{ W/ft}^2$) | **42.58%** ($39.6\text{ W/ft}^2$) | $3.058$ / **$4.379$** | $\$0.0002$ / **$\$0.0633$** | $1.529$ / $1.460$ | $1.699$ / **$1.771$** |
| `mp-1195160__mp-23474` | `Al2Bi2Cu2S3Cl8 + c-Si + AgBi3S5` | $11.04\% \rightarrow \mathbf{2.47\%}$ | 39.12% ($36.3\text{ W/ft}^2$) | **42.58%** ($39.6\text{ W/ft}^2$) | $3.058$ / **$4.360$** | $\$0.0013$ / **$\$0.0645$** | $1.529$ / $1.453$ | $1.699$ / **$1.768$** |
| `mp-715212__mp-1223998` | `Bi3In5S12 + c-Si + Bi3InSe6` | $11.44\% \rightarrow \mathbf{3.27\%}$ | 38.63% ($35.9\text{ W/ft}^2$) | **42.57%** ($39.5\text{ W/ft}^2$) | $2.998$ / **$4.340$** | $\$0.0024$ / **$\$0.0656$** | $1.499$ / $1.447$ | $1.674$ / **$1.765$** |

> [!CAUTION]
> Phases 9 to 11 below stack device, cost and requirements models on the heuristic material properties above. In Phase 11B and `requirements_tea.py`, techno-economic outputs are framed as **break-even top-cell requirements** rather than forecasts: at demonstrated $\text{Sb}_2\text{S}_3 / \text{Sb}_2(\text{S,Se})_3$ external radiative efficiency (`ERE = 1e-9`, record $\sim 8\text{–}10.8\%$), a 2-layer stack produces **`20.27%–20.45%` monofacial PCE** — strictly below standalone silicon (`22.94%`) — and only breaks even with utility c-Si LCOE if the top cell reaches **`15.66%–15.83%` PCE** (`15.72%` at $T_{\text{sub}} = 0.88$, `13.0%–13.4%` optics-only break-even). The Phase 9A electrostatic term is a monopole point-charge image estimate (`point_charge_image_estimate_ev`), and the generated supercell decks represent neutral vacancy supercells (`tot_charge` unset). See the audit, sections 3 and 4.

### 6. Phase 9 (`v6.0`): 10 mmol Lab Synthesis & Supercells (9A) and Oblique/Thermal/25-Year LCOE Stress-Test (9C)
- **Phase 9A (10.0 mmol Stoichiometric Lab Batch & Neutral Vacancy Supercell Decks):** Generates exact elemental mass-balanced precursor recipes (`elemental_mass_conservation_diff_g == 0.0 g`), $5\%$ sulfur/selenium volatile overpressure ampoule charges, and Quantum ESPRESSO neutral vacancy supercell decks (`outputs/mp_live_neutral_vacancy_decks/`, perpendicular lattice spacing $d_{\perp,\min} \ge 10.0\text{ \AA}$, monopole point-charge image estimates `point_charge_image_estimate_ev` $\in [0.090, 0.190]\text{ eV}$).
- **Phase 9C (Oblique $0^\circ\text{–}60^\circ$ S/P Coherent TMM, Operating Temp $25^\circ\text{C}\text{–}65^\circ\text{C}$ & 25-Year Radiative-Ceiling LCOE Stress-Test):** Evaluates unpolarized $\frac{1}{2}(|r_s|^2+|r_p|^2)$ oblique optics ($\text{IAM}_{60^\circ} = 0.954$), NOCT ($45^\circ\text{C}$) and desert peak ($65^\circ\text{C}$) thermal derating ($\beta_{\text{4T}} = -0.358\%/\text{K}$ vs. $-0.409\%/\text{K}$ c-Si), and radiative-ceiling 25-year discounted LCOE (`3.139 ¢/kWh` vs. `4.936 ¢/kWh` baseline; see Phase 11B and `requirements_tea.py` for non-radiative break-even requirements).

### 7. Phase 10 (`v7.0`): $2^4=16$ Thickness/ARC Optimization (10A), Bifacial-Equivalent Power Density (10B), and Demonstrated-Case String & ITO Sheet-Resistance Check (10C)
Per IEC TS 60904-1-2, bifacial rear-albedo output is normalized by $100\text{ mW/cm}^2$ front irradiance Only and reported as **bifacial-equivalent power density (front-irradiance basis, $\text{mW/cm}^2$)** rather than thermodynamic PCE. String voltage matching ($N_{\text{top}} : N_{\text{Si}} : N_{\text{bot}}$) is evaluated at the `"demonstrated"` maturity case ($V_{\text{oc}}$ and $FF$ from `ERE = 1e-9`, $FF_{\text{cap}} = 0.73$), and checked against the ITO sheet-resistance strip-width limit ($\Delta P / P = J_{\text{mp}} R_{\text{sh}} w^2 / (3 V_{\text{mp}})$ at $R_{\text{sh}} = 10\,\Omega/\square$): because `61` monolithic strips over a $2.0\text{ m}$ module imply $w = 3.28\text{ cm}$ ($> 0.60\text{ cm}$ P1–P2–P3 laser-scribe limit), ungridded ITO strips suffer `87.7%–88.7%` resistive power loss (`strip_width_feasible = False`), requiring sub-centimeter laser scribing with parallel stringing or a metal collection grid.

| Pair ID | Stack (`Top + c-Si + Bot`) | Opt Thicknesses `(MgF2, TiO2, Top, Bot)` | Opt Mono 4T PCE | **Bifacial-Equiv Power Density 20% Alb ($\text{mW/cm}^2$ / $\text{W/ft}^2$)** | **Bifacial-Equiv Power Density 30% Alb ($\text{mW/cm}^2$ / $\text{W/ft}^2$)** | **Radiative 25-Yr LCOE (20% Alb)** | Demonstrated String Ratio ($N_{\text{top}} : N_{\text{Si}} : N_{\text{bot}}$) | Bus Voltage & ITO Strip Check ($w_{\text{strip}}$, $P_{\text{loss,ITO}}$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-1195160__mp-1224102` | `Al2Bi2Cu2S3Cl8 + c-Si + CuInSnS4` | `(94, 42, 299, 391 nm)` | 42.70% | **47.08 mW/cm²** (43.74 W/ft², +10.24%) | **49.30 mW/cm²** (45.80 W/ft²) | **2.959 ¢/kWh** | **`61 : 72 : 1003`** | 50.14 V ($w=3.28$ cm, $P_{\text{ITO}}=88.7\%$, infeasible without grid) |
| `mp-1195160__mp-20331` | `Al2Bi2Cu2S3Cl8 + c-Si + CuSbSe2` | `(94, 42, 299, 391 nm)` | 42.55% | **46.94 mW/cm²** (43.61 W/ft², +10.32%) | **49.18 mW/cm²** (45.69 W/ft²) | **2.961 ¢/kWh** | **`61 : 72 : 1003`** | 50.14 V ($w=3.28$ cm, $P_{\text{ITO}}=88.7\%$, infeasible without grid) |
| `mp-1195160__mp-1224922` | `Al2Bi2Cu2S3Cl8 + c-Si + CuGaSnSe4` | `(94, 48, 299, 340 nm)` | 42.75% | **46.84 mW/cm²** (43.52 W/ft², +9.58%) | **48.93 mW/cm²** (45.46 W/ft²) | **2.968 ¢/kWh** | **`61 : 72 : 1003`** | 50.14 V ($w=3.28$ cm, $P_{\text{ITO}}=88.7\%$, infeasible without grid) |
| `mp-1195160__mp-1223998` | `Al2Bi2Cu2S3Cl8 + c-Si + Bi3InSe6` | `(94, 42, 260, 391 nm)` | 43.12% | **46.84 mW/cm²** (43.52 W/ft², +8.64%) | **48.74 mW/cm²** (45.28 W/ft²) | **2.972 ¢/kWh** | **`61 : 72 : 1004`** | 50.18 V ($w=3.28$ cm, $P_{\text{ITO}}=87.7\%$, infeasible without grid) |
| `mp-1195160__mp-22982` | `Al2Bi2Cu2S3Cl8 + c-Si + BiCuS2` | `(94, 48, 299, 340 nm)` | 42.70% | **46.77 mW/cm²** (43.46 W/ft², +9.54%) | **48.85 mW/cm²** (45.38 W/ft²) | **2.969 ¢/kWh** | **`61 : 72 : 1003`** | 50.14 V ($w=3.28$ cm, $P_{\text{ITO}}=88.7\%$, infeasible without grid) |
| `mp-1195160__mp-23474` | `Al2Bi2Cu2S3Cl8 + c-Si + AgBi3S5` | `(94, 48, 299, 340 nm)` | 42.70% | **46.77 mW/cm²** (43.45 W/ft², +9.54%) | **48.85 mW/cm²** (45.38 W/ft²) | **2.972 ¢/kWh** | **`61 : 72 : 1003`** | 50.14 V ($w=3.28$ cm, $P_{\text{ITO}}=88.7\%$, infeasible without grid) |

### 8. Phase 11 & Requirements TEA (`v0.8.0`): Cached MP Hull/TCO Equilibria, Non-Radiative Maturity Cases (`demonstrated`, `stretch`, `ceiling`) & Break-Even Requirements (`requirements_tea.py`)
Phase 11 (`realistic_commercialization.py`, `requirements_tea.py`, [`docs/REALISTIC_COMMERCIALIZATION_AND_DEBATE_REPORT.md`](docs/REALISTIC_COMMERCIALIZATION_AND_DEBATE_REPORT.md)) evaluates cached Materials Project convex-hull stability windows and `pymatgen` `InterfacialReactivity` against `SnO2`/`In2O3`/`TiO2`, sets the **2-layer stack (`Top + c-Si`, `include_rear_ir_cell = False`)** as the default architecture (since the rear IR cell lowers bifacial output below the 2-layer stack at `20%` albedo), and evaluates three `ASSUMED` device-maturity parameterizations alongside inverse break-even requirements:

- **Top Synthesis Practicality (`SPS` out of `100` across 8 cached entries; `mp-1195160` `Al2Bi2Cu2S3Cl8` is `None` / not evaluated):** **`mp-1227486 BiSbS3` (`94.76/100`)** and **`mp-861911 Sb2OS2` (`94.44/100`)** lead the evaluated finalists (`0.00 meV/atom` reaction energy on `TiO2` and `SnO2` vs. exothermic `-13.16` and `-15.35 meV/atom` sulfidation on bare `In2O3`/ITO; zero In/Ga/Ag criticality), followed by `mp-22982 BiCuS2` (`89.54/100`), `AgBi3S5` (`88.96`), `BiInS3` (`83.42`), `Bi3InSe6` (`79.71`), `CuInSnSe4` (`61.66`), and `CuGaSnSe4` (`49.99`).
- **3-Case Non-Radiative 2-Layer Stack (`Top + c-Si`, default `default_stack_layers = 2`) vs. Standalone c-Si (`22.94%` mono, `26.65 mW/cm²` bifacial-equivalent at `\$42.00/m²`, `4.246 ¢/kWh` utility LCOE):**
  - **`"demonstrated"` (`ERE = 1e-9`, $FF_{\text{cap}} = 0.73$, matching record $\text{Sb}_2\text{S}_3 \approx 8\%$ / $\text{Sb}_2(\text{S,Se})_3 \approx 10.7\text{–}10.8\%$):** Top cell reaches **`8.63%`** (`BiSbS3`) / **`8.95%`** (`Sb2OS2`), giving a 2-layer monofacial PCE of **`20.45%`** (`BiSbS3 + c-Si`) / **`20.27%`** (`Sb2OS2 + c-Si`) — **strictly lower than standalone silicon (`22.94%`)** because top-stack reflection and sub-gap parasitic losses remove ~`11.1–11.6%` absolute from silicon while the top cell adds only `8.6–9.0%`. Utility LCOE rises to **`5.074–5.104 ¢/kWh`** (above standalone c-Si `4.246 ¢/kWh`).
  - **`"stretch"` (`ERE = 1e-7`, 2 orders of magnitude above demonstrated $\text{Sb}_2\text{S}_3$):** Top cell reaches **`11.99%`** (`BiSbS3`) / **`12.37%`** (`Sb2OS2`), giving **`23.83%`** / **`23.70%`** 2-layer monofacial PCE — barely above standalone silicon optically, and still more expensive on utility LCOE (`4.698 ¢/kWh` at `11.9%` top PCE).
  - **`"ceiling"` (`ERE = 1e-4`, 5 orders of magnitude above demonstrated $\text{Sb}_2\text{S}_3$, comparable to champion $\text{CdTe/CIGS}$):** Top cell reaches **`15.09%`** (`BiSbS3`) / **`15.57%`** (`Sb2OS2`), giving **`26.90%`** / **`26.88%`** 2-layer monofacial PCE and **`30.63`** / **`30.61 mW/cm²`** bifacial-equivalent power density (`20%` albedo) at `\$65.88/m²` (`4.232–4.234 ¢/kWh` utility LCOE).
- **Inverse Break-Even Requirements (`python -m failsmart_matengine.requirements_tea`):**
  - **Optics-only break-even top-cell efficiency:** $\eta_{\text{top}}^{\text{min,optics}}(T_{\text{sub}}) = 24.5 - 13.1\,T_{\text{sub}}$ (**`12.97%`** at $T_{\text{sub}} = 0.88$, **`13.37%`** at $T_{\text{sub}} = 0.85$).
  - **Utility & Rooftop LCOE break-even top-cell efficiency** (at $+\$23.88/\text{m}^2$ added module cost and $0.50\%/\text{yr}$ degradation): **`15.72%`** top-cell PCE at $T_{\text{sub}} = 0.88$ (**`15.83%`** for `BiSbS3` $T_{\text{sub}} = 0.871$, **`15.66%`** for `Sb2OS2` $T_{\text{sub}} = 0.884$) for utility scale, and **`14.02%`** (`14.00%–14.17%`) for rooftop scale.
  - **Allowable added module cost per efficiency point:** **`\$6.53/m²` per percentage point** of net efficiency gain over standalone c-Si in the utility case (**`\$11.78/m²` per point** in the rooftop case).

---

## Quick Start & Cross-Repository Verification

### Run the v2.0 Discovery Pipeline
```bash
python3 -m failsmart_matengine.orchestrator
```

### Run the Cached Materials Project Discovery + Pair-Spring/Migration Heuristics, Graded-ARC TMM, LCOE & Commercialization Engine
```bash
python3 -m failsmart_matengine.mp_live_discovery
```

### Run the Automated Test Suite (26 regression and deck/gate/provenance tests passed)
```bash
pytest -v
```

### Run the Repository Release & KaTeX Safety Auditor
```bash
python3 -m failsmart_matengine.repo_auditor
```
