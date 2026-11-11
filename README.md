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
> The v2 pilot structures are `pyxtal` random placements and every property in this table comes from hand-entered lookup tables in `physics_calculators.py` (`_RAW_STABILITY_DATA`, `_RAW_ELECTRONIC_DATA`) and `tools.py` (`_GATE_A_DATA`). Treat these rows as test fixtures, not as predictions.

| Candidate ID | Formula | Target Layer | Space Group | $N_{\text{sites}}$ | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $E_g^{\text{est}}$ (Ind / Dir; heuristic, HSE06+SOC not run) | Single-Layer SLME (%) | SQ Limit (%) | 2-Layer Si $\eta$ (%) | 4T Std Si FCA $\eta$ (%) | **3-Layer 4T Tandem $\eta$ (%)** | Self-consistency SHA-256 digest (unkeyed) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-A02` | `Bi2CuO2SCl` | Top Active Glass | `I4/mmm` (#139) | 28 | 365.0 | \$0.0195 | 14.5 | 1.18 | 0.88 | 1.82 / 1.86 eV | 24.43% | 26.78% | 38.29% | 40.43% | **41.66%** | `7327ea003865f07f05731062031db534816808ce0ee3ef6c9fe25352a3ebe11d` |
| `CAND-A03` | `Cu2SbS2Cl` | Top Active Glass | `Pnma` (#62) | 24 | 320.0 | \$0.0129 | 21.0 | 1.05 | 0.74 | 1.79 / 1.83 eV | 25.08% | 27.32% | 38.41% | 40.54% | **41.77%** | `a6cc389afeaa8cccac8901bd6ea208fe026d6671db2a7c58eefff54afb6b7033` |
| `CAND-A06` | `BiZnOSCl` | Top Active Glass | `P4/nmm` (#129) | 10 | 380.0 | \$0.0148 | 18.2 | 1.29 | 0.98 | 1.85 / 1.89 eV | 23.81% | 26.11% | 38.18% | 40.31% | **41.55%** | `f7228c7119f0512da697a81e39f7709621af9f891dfa6b9559405770662c75c3` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom IR Scavenger | `Cmcm` (#63) | 32 | 295.0 | \$0.0865 | 12.6 | 0.88 | 0.75 | 0.75 / 0.78 eV | 23.48% | 25.00% | 38.26% | 40.51% | **41.83%** | `24e5980fa55fb8a5e1a675ac6d5ac7d224cb55cc0a996f2a6a84977078f21350` |
| `CAND-B04` | `Cu2BiSe2I` | Bottom IR Scavenger | `Pnma` (#62) | 24 | 345.0 | \$0.0509 | 11.2 | 1.09 | 0.71 | 0.74 / 0.76 eV | 23.59% | 24.79% | 38.26% | 40.64% | **42.08%** | `83b3549e4805d11c3be55a82df02534f37e1ff926bf18a3bb3935492530ce9e9` |

---

## Live Materials Project Discovery Campaign v3.0 Summary Results

Running `python3 -m failsmart_matengine.mp_live_discovery` executes the v3.0 discovery funnel on Materials Project records (read from the committed cache `data/mp_live_candidates_cache.json` by default; the API is queried only on refresh) across **100 Live MP Candidates** restricted to RoHS-clean Mixed-Anion & Lone-Pair ($ns^2$) chemical spaces ($	ext{Bi/Sb–Cu/Zn/Sn/In/Ga/Ag–S/Se/O–Cl/Br/I}$):

* **Stage 1 (Live Materials Project Query & RoHS Filtering):** `100` live MP candidates ingested with verified non-toxic elements and Pauling charge neutrality.
* **Stage 2 (Thermodynamic Hull, Elasticity & Stage 2b Ion-Migration):** `91` dynamically & ion-stable candidates surviving ($6$ elastic instabilities and $3$ superionic migration instabilities vetoed with $E_{\text{mig}} < 0.65\text{ eV}$).
* **Stage 3 (LBNL 80k Impurity & A-Lab Precursor Genome Retrosynthesis):** `47` manufacturable candidates passing reaction network driving-force and negative-synthesis prior screening ($26$ rejected for `OXIDE_IMPURITY_SINK` from refractory oxide reactions, $5$ rejected for `IMPURITY_SINK_PRIOR` where empirical LBNL `impurity_rate > 0.50` across $n \ge 5$ recipes, $13$ rejected for `TIER2_COST_EXCEEDED` $> \$0.50/\text{m}^2$).
* **Gate A (Structural Dimensionality Pre-Screen):** `40` promoted to Stage 4/5 ($7$ vetoed for `LOW_DIM_POLARON_RISK` 1D-chains; anion mixing enthalpy and TCO reaction energy are `None` / not evaluated at Gate A).
* **Stages 4 & 5 (heuristic gap estimate from the MP PBE gap & radiative-limit 4T Tandem Optics; `HSE06+SOC` calculation not run):** **9 Prescreen Finalists** ($31$ rejected for `BANDGAP_OUT_OF_WINDOW` outside $[1.75, 1.95]\text{ eV}$ top or $[0.70, 0.85]\text{ eV}$ bottom windows).
* **Self-consistency re-computation:** `100/100` re-computations matched. This confirms arithmetic agreement between two implementations of the same formulas; it does not confirm the inputs or the physics.

### Open-Access Negative Synthesis Priors Integration
The v3.0 engine integrates two massive open-access empirical negative-synthesis databases (`data/negative_synthesis_priors.json`):
1. **LBNL Solid-State Impurity Dataset:** `80,806` parsed solid-state recipes across `4,292` chemical systems with `18,869` phase-impure/failed reactions (Lee, Cruse, Baibakova, Ceder, Jain, *Sci. Data* 12:1969, 2025).
2. **LBNL A-Lab "Precursor Genome" Dataset:** `1,035` autonomous laboratory pairwise reactions with `892` negative/stalled reactions (369 unreacted, 384 transformed, 113 partially reacted) (Walters, Szymanski, Fei, Ceder et al., *Precursor Genome*, 2026).

### Promoted Materials Project Prescreen Finalists (9 Finalists: 4 Track A + 5 Track B)

All 9 finalists have generated Quantum ESPRESSO `HSE06+SOC` input decks and CIF files in `outputs/mp_live_qe_decks/` (`HSE06+SOC` not run). Per the committed cache, only `mp-22982` and `mp-23474` are experimentally known phases; the other seven are theoretical Materials Project entries. The gap column is a heuristic estimate calibrated in task T4:

| Candidate ID | Formula | Target Layer | Space Group | $N_{\text{sites}}$ | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $E_g^{\text{est}}$ (Ind / Dir; heuristic, HSE06+SOC not run) | Single-Layer SLME (%) | SQ Limit (%) | 2-Layer Si $\eta$ (%) | 4T Std Si FCA $\eta$ (%) | **3-Layer 4T Tandem $\eta$ (%)** | Self-consistency SHA-256 digest (unkeyed) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `mp-861911` | `Sb2OS2` | Top Active Glass | `C2/m` (#12) | 10 | 375.0 | \$0.0157 | 7.07 | 1.40 | 1.18 | 1.76 / 1.80 eV | 25.66% | 27.93% | 38.43% | 40.55% | **41.78%** | `a09dbb1c343327cd5cbb5fe25b0409ec548a0f06b6168ca7feb5d47fc3ae68d1` |
| `mp-1227486` | `BiSbS3` | Top Active Glass | `Pnma` (#62) | 20 | 375.0 | \$0.0182 | 2.30 | 1.20 | 1.18 | 1.79 / 1.83 eV | 25.10% | 27.32% | 38.36% | 40.48% | **41.70%** | `d8f6b425fa2066a5062437ab9edb68a127d62b3ca1821a2645bbf4f07a9076cb` |
| `mp-1195160` | `Al2Bi2Cu2S3Cl8` | Top Active Glass | `P6_3/m` (#176) | 34 | 335.0 | \$0.0128 | 6.02 | 1.33 | 0.87 | 1.82 / 1.83 eV | 25.63% | 26.78% | 38.91% | 41.03% | **42.26%** | `b04a50d78a9aa16b7b274b19263ad7a7f6a8fb640603874e8d70b8cb607e05f5` |
| `mp-1078776` | `BiInS3` | Top Active Glass | `P2_1/m` (#11) | 10 | 375.0 | \$0.2681 | 15.08 | 1.11 | 1.18 | 1.90 / 1.94 eV | 22.87% | 25.00% | 37.89% | 40.00% | **41.23%** | `efd0e571e1da58bcc47487420264fbc3faad1689ffc3bd7e6a5edd8f817ec9f3` |
| `mp-1223998` | `Bi3InSe6` | Bottom IR Scavenger | `R3m` (#160) | 10 | 375.0 | \$0.1507 | 17.99 | 1.33 | 1.18 | 0.75 / 0.76 eV | 24.11% | 25.00% | 38.26% | 40.72% | **42.19%** | `0dae9392716774ac808f7d90ab583018289674f56443c20fd9ccbb69f01202d5` |
| `mp-1224922` | `CuGaSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.1251 | 3.61 | 1.28 | 0.98 | 0.85 / 0.86 eV | 26.50% | 27.20% | 38.26% | 40.53% | **41.66%** | `94e846fe365a26c374eab9715c63f9678401f11dbe6c757cc4f6608bd2464e5c` |
| `mp-22982` | `BiCuS2` | Bottom IR Scavenger | `Pnma` (#62) | 16 | 375.0 | \$0.0237 | 0.00 | 1.27 | 0.95 | 0.85 / 0.89 eV | 26.35% | 27.20% | 38.26% | 40.50% | **41.61%** | `4572d1324fa4eeafde04a92ab39f889912192afae5214cd9c08a90f83dce9303` |
| `mp-23474` | `AgBi3S5` | Bottom IR Scavenger | `C2/m` (#12) | 18 | 375.0 | \$0.2558 | 0.00 | 1.18 | 0.98 | 0.85 / 0.89 eV | 26.35% | 27.20% | 38.26% | 40.50% | **41.61%** | `28fffc7cc0a9332db420e8769ac9fb9a11b27285bc604d3ee1bd2f9732ceaa72` |
| `mp-1224129` | `CuInSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.2664 | 5.17 | 1.21 | 0.98 | 0.78 / 0.82 eV | 23.71% | 25.60% | 38.26% | 40.29% | **41.39%** | `e9f128da15956ed2693b7ddd9cf262a07696ca573313e2164f6491cf979d5d01` |

### Top Cross-Layer 4-Terminal Tandem Stacks (20 Pairs Screened)

The 4 Top Active Glass and 5 Bottom IR Scavenger finalists yield `20` mechanically decoupled 4-terminal tandem stacks with middle crystalline silicon ($E_g = 1.12\text{ eV}$):

| Pair ID | Top MP Cell | Bottom MP Cell | Top $E_g$ (Ind/Dir) | Bottom $E_g$ (Ind/Dir) | Top PCE (%) | Middle c-Si PCE (%) | Bottom IR PCE (%) | Combined Cost ($\$/\text{m}^2$) | **4T Tandem Total PCE (%)** |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-861911__mp-1223998` | `mp-861911` (Sb2OS2) | `mp-1223998` (Bi3InSe6) | 1.76 / 1.80 eV | 0.75 / 0.76 eV | 25.66% | 11.84% | 4.82% | \$0.1664 | **42.32%** |
| `mp-1227486__mp-1223998` | `mp-1227486` (BiSbS3) | `mp-1223998` (Bi3InSe6) | 1.79 / 1.83 eV | 0.75 / 0.76 eV | 25.10% | 12.32% | 4.82% | \$0.1689 | **42.25%** |
| `mp-861911__mp-1224922` | `mp-861911` (Sb2OS2) | `mp-1224922` (CuGaSnSe4) | 1.76 / 1.80 eV | 0.85 / 0.86 eV | 25.66% | 11.84% | 4.30% | \$0.1408 | **41.79%** |
| `mp-1078776__mp-1223998` | `mp-1078776` (BiInS3) | `mp-1223998` (Bi3InSe6) | 1.90 / 1.94 eV | 0.75 / 0.76 eV | 22.87% | 14.07% | 4.84% | \$0.4188 | **41.78%** |
| `mp-861911__mp-22982` | `mp-861911` (Sb2OS2) | `mp-22982` (BiCuS2) | 1.76 / 1.80 eV | 0.85 / 0.89 eV | 25.66% | 11.84% | 4.25% | \$0.0394 | **41.75%** |
| `mp-861911__mp-23474` | `mp-861911` (Sb2OS2) | `mp-23474` (AgBi3S5) | 1.76 / 1.80 eV | 0.85 / 0.89 eV | 25.66% | 11.84% | 4.25% | \$0.2715 | **41.75%** |
| `mp-1227486__mp-1224922` | `mp-1227486` (BiSbS3) | `mp-1224922` (CuGaSnSe4) | 1.79 / 1.83 eV | 0.85 / 0.86 eV | 25.10% | 12.32% | 4.30% | \$0.1433 | **41.72%** |
| `mp-1227486__mp-22982` | `mp-1227486` (BiSbS3) | `mp-22982` (BiCuS2) | 1.79 / 1.83 eV | 0.85 / 0.89 eV | 25.10% | 12.32% | 4.25% | \$0.0419 | **41.67%** |
| `mp-1227486__mp-23474` | `mp-1227486` (BiSbS3) | `mp-23474` (AgBi3S5) | 1.79 / 1.83 eV | 0.85 / 0.89 eV | 25.10% | 12.32% | 4.25% | \$0.2740 | **41.67%** |
| `mp-861911__mp-1224129` | `mp-861911` (Sb2OS2) | `mp-1224129` (CuInSnSe4) | 1.76 / 1.80 eV | 0.78 / 0.82 eV | 25.66% | 11.84% | 4.03% | \$0.2821 | **41.53%** |
| `mp-1227486__mp-1224129` | `mp-1227486` (BiSbS3) | `mp-1224129` (CuInSnSe4) | 1.79 / 1.83 eV | 0.78 / 0.82 eV | 25.10% | 12.32% | 4.03% | \$0.2846 | **41.45%** |
| `mp-1078776__mp-1224922` | `mp-1078776` (BiInS3) | `mp-1224922` (CuGaSnSe4) | 1.90 / 1.94 eV | 0.85 / 0.86 eV | 22.87% | 14.07% | 4.31% | \$0.3932 | **41.25%** |
| `mp-1078776__mp-22982` | `mp-1078776` (BiInS3) | `mp-22982` (BiCuS2) | 1.90 / 1.94 eV | 0.85 / 0.89 eV | 22.87% | 14.07% | 4.26% | \$0.2918 | **41.20%** |
| `mp-1078776__mp-23474` | `mp-1078776` (BiInS3) | `mp-23474` (AgBi3S5) | 1.90 / 1.94 eV | 0.85 / 0.89 eV | 22.87% | 14.07% | 4.26% | \$0.5239 | **41.20%** |
| `mp-1078776__mp-1224129` | `mp-1078776` (BiInS3) | `mp-1224129` (CuInSnSe4) | 1.90 / 1.94 eV | 0.78 / 0.82 eV | 22.87% | 14.07% | 4.04% | \$0.5345 | **40.98%** |

*Key Efficiency / Cost Pareto Highlights:*
* **Highest radiative-limit pair (scalar idealization, not a device forecast):** `mp-861911 Sb2OS2 + c-Si + mp-1223998 Bi3InSe6` achieves **42.32%** 4T PCE ($25.66\%$ top $+ 11.84\%$ middle $+ 4.82\%$ bottom IR) at $\$0.1664/\text{m}^2$.
* **Lowest active-layer material cost pair (scalar idealization; material cost is a negligible share of module cost):** `mp-861911 Sb2OS2 + c-Si + mp-22982 BiCuS2` delivers **41.75%** 4T PCE at an ultra-abundant active layer cost of **\$0.0394/m²**.

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
Replacing scalar Fresnel idealizations with a full 6-medium coherent thin-film interference solver (`Air / 98 nm MgF2 ARC / 105 nm Front ITO / Active Absorber / 85 nm SiO2-ITO Buffer / Couplant -> Textured c-Si -> Bottom IR Scavenger / 4n^2 Ag Mirror`) cross-verified between $2\times 2$ Abeles matrix multiplication (`np.trapezoid`) and Recursive Rouard/Airy backward amplitude addition (`scipy.integrate.simpson`, $\le 0.01\%$ discrepancy):

| Pair ID | Top MP Cell | Bottom MP Cell | Mean Front $R_{\text{TMM}}$ (%) | Sub-Gap $T_{\text{TMM}}$ (%) | Top PCE (%) | Middle c-Si PCE (%) | Bottom IR PCE (%) | 2-Layer PCE (%) | 4T Std Si PCE (%) | **Coherent 4T Low-FCA PCE (%)** | Scalar $\rightarrow$ TMM $\Delta$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-861911__mp-1223998` | `Sb2OS2` | `Bi3InSe6` | 11.97% | 88.25% | 23.22% | 12.16% | 4.62% | 36.06% | 38.52% | **40.00%** | $-2.32\%$ |
| `mp-1078776__mp-1223998` | `BiInS3` | `Bi3InSe6` | 11.01% | 88.92% | 20.89% | 14.43% | 4.64% | 36.06% | 38.48% | **39.96%** | $-1.82\%$ |
| `mp-1227486__mp-1223998` | `BiSbS3` | `Bi3InSe6` | 11.79% | 88.42% | 22.74% | 12.56% | 4.62% | 35.99% | 38.44% | **39.92%** | $-2.33\%$ |
| `mp-861911__mp-1224922` | `Sb2OS2` | `CuGaSnSe4` | 11.97% | 88.25% | 23.22% | 12.16% | 4.00% | 36.06% | 38.23% | **39.38%** | $-2.41\%$ |
| `mp-861911__mp-22982` | `Sb2OS2` | `BiCuS2` | 11.97% | 88.25% | 23.22% | 12.16% | 3.94% | 36.06% | 38.19% | **39.32%** | $-2.43\%$ |
| `mp-861911__mp-23474` | `Sb2OS2` | `AgBi3S5` | 11.97% | 88.25% | 23.22% | 12.16% | 3.94% | 36.06% | 38.19% | **39.32%** | $-2.43\%$ |

*Key Physical Insight from Coherent TMM:* High refractive indices ($n_1 \approx 2.8\text{–}3.1$) of heavy pnictogen chalcohalides/oxychalcogenides produce $11.01\%\text{–}11.97\%$ broadband front reflectance despite a single-layer $\text{MgF}_2/\text{ITO}$ anti-reflection coating, while sub-bandgap IR transmittance rises to $88.25\%\text{–}88.92\%$. Even with full coherent optical losses, `mp-861911 Sb2OS2 + c-Si + mp-1223998 Bi3InSe6` reaches **40.00% Coherent 4T PCE**, and the ultra-low-cost **\$0.0394/m²** `Sb2OS2 + c-Si + BiCuS2` stack achieves **39.32% Coherent 4T PCE**.

### Step 3: 7-Medium Graded-ARC + $\text{TiO}_2$ Impedance-Matching Stack & 4-Metric Techno-Economic Figure-of-Merit Suite
Inserting a $48\text{ nm}$ high-index $\text{TiO}_2$ optical impedance-matching layer ($n_3 \approx 2.38$) between Front $\text{ITO}$ ($80\text{ nm}$) and the Top Active Absorber (`Air / 94 nm MgF2 / 80 nm ITO / 48 nm TiO2 / Absorber / 82 nm Buffer / Couplant`) suppresses mean front reflection from **$11.90\%$ down to $2.42\%\text{–}3.33\%$** ($-8.57\%$ to $-8.75\%$ reduction), recovering **$+2.20\%$ to $+2.58\%$** in coherent 4T efficiency and reaching **42.44% Coherent 4T PCE** ($39.4\text{ W/ft}^2$)!

We simultaneously evaluate all 4 Techno-Economic Figures of Merit against a single-junction $22.0\%$ c-Si baseline ($C_{\text{Si,mod}} = \$40/\text{m}^2$, $C_{\text{BOS,area}} = \$100/\text{m}^2$, $\$6.50/\text{m}^2$ TCO/coating process overhead per added subcell):
1. **$\text{CER}_N$ (Your Normalized Multi-Junction Cost-Efficiency Ratio):** $\frac{\eta_{\text{stack}} / \eta_{\text{Si}}}{(C_{\text{Si,mod}} + \Delta C) / (N \cdot C_{\text{Si,mod}})}$ ($N=2$ or $3$).
2. **$\text{MCIW}_{\text{raw}}$ / $\text{MCIW}_{\text{full}}$ (Marginal Cost per Incremental Watt, $\$/\Delta\text{W}_{\text{p}}$):** $\frac{\Delta C}{1000(\eta_{\text{stack}} - \eta_{\text{Si}})}$ vs. $\$0.1818/\text{W}_{\text{p}}$ baseline Si.
3. **$\text{CPR}_{\text{mod}}$ (Factory-Gate Module Cost-Performance Ratio):** $\frac{\eta_{\text{stack}} / \eta_{\text{Si}}}{1 + \Delta C / C_{\text{Si,mod}}}$.
4. **$\text{SVI}_{\text{BOS}}$ (Area-Constrained System Value Index):** $\frac{\eta_{\text{stack}} / \eta_{\text{Si}}}{(C_{\text{Si,mod}} + \Delta C + C_{\text{BOS,area}}) / (C_{\text{Si,mod}} + C_{\text{BOS,area}})}$.

| Pair ID | Stack (`Top + c-Si + Bot`) | $R_{\text{front}}$ ($\text{1-ARC}\rightarrow\text{Graded}$) | Graded 2L PCE ($\text{W/ft}^2$) | **Graded 4T PCE ($\text{W/ft}^2$)** | $\text{CER}_{\text{2L}}$ / **$\text{CER}_{\text{3L}}$** | $\text{MCIW}_{\text{3L}}$ (Raw / Full $\$/\Delta\text{W}$) | $\text{CPR}_{\text{mod}}$ (2L / 3L) | **$\text{SVI}_{\text{BOS}}$ (2L / 3L)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-861911__mp-1223998` | `Sb2OS2 + c-Si + Bi3InSe6` | $11.90\% \rightarrow \mathbf{3.33\%}$ | 38.50% ($35.8\text{ W/ft}^2$) | **42.44%** ($39.4\text{ W/ft}^2$) | $3.010$ / **$4.354$** | $\$0.0008$ / **$\$0.0644$** | $1.505$ / $1.451$ | $1.672$ / **$1.763$** |
| `mp-1227486__mp-1223998` | `BiSbS3 + c-Si + Bi3InSe6` | $11.97\% \rightarrow \mathbf{3.22\%}$ | 38.42% ($35.7\text{ W/ft}^2$) | **42.36%** ($39.4\text{ W/ft}^2$) | $3.003$ / **$4.346$** | $\$0.0008$ / **$\$0.0647$** | $1.502$ / $1.449$ | $1.669$ / **$1.760$** |
| `mp-1078776__mp-1223998` | `BiInS3 + c-Si + Bi3InSe6` | $11.01\% \rightarrow \mathbf{2.42\%}$ | 38.16% ($35.5\text{ W/ft}^2$) | **42.16%** ($39.2\text{ W/ft}^2$) | $2.967$ / **$4.305$** | $\$0.0021$ / **$\$0.0666$** | $1.484$ / $1.435$ | $1.655$ / **$1.749$** |
| `mp-861911__mp-1224922` | `Sb2OS2 + c-Si + CuGaSnSe4` | $11.90\% \rightarrow \mathbf{3.33\%}$ | 38.50% ($35.8\text{ W/ft}^2$) | **41.94%** ($39.0\text{ W/ft}^2$) | $3.010$ / **$4.305$** | $\$0.0007$ / **$\$0.0659$** | $1.505$ / $1.435$ | $1.672$ / **$1.743$** |
| `mp-861911__mp-22982` | `Sb2OS2 + c-Si + BiCuS2` | $11.90\% \rightarrow \mathbf{3.33\%}$ | 38.50% ($35.8\text{ W/ft}^2$) | **41.89%** ($38.9\text{ W/ft}^2$) | $3.010$ / **$4.308$** | **$\$0.0002$** / **$\$0.0656$** | $1.505$ / $1.436$ | $1.672$ / **$1.742$** |
| `mp-1227486__mp-22982` | `BiSbS3 + c-Si + BiCuS2` | $11.97\% \rightarrow \mathbf{3.22\%}$ | 38.42% ($35.7\text{ W/ft}^2$) | **41.81%** ($38.8\text{ W/ft}^2$) | $3.003$ / **$4.300$** | **$\$0.0002$** / **$\$0.0658$** | $1.502$ / $1.433$ | $1.669$ / **$1.738$** |

> [!CAUTION]
> Phases 9 to 11 below stack device, cost and market models on the heuristic material properties above. The LCOE and efficiency figures are conditional on a top cell near 16% efficiency at an external radiative efficiency of `1e-4`; the best reported Sb2S3 cell is about 8%. The Phase 9A electrostatic term is a monopole point-charge image estimate (`point_charge_image_estimate_ev`), and the generated supercell decks represent neutral vacancy supercells (`tot_charge` unset). See the audit, sections 3 and 4.

### 6. Phase 9 (`v6.0`): 10 mmol Lab Synthesis & Supercells (9A) and Oblique/Thermal/25-Year LCOE Stress-Test (9C)
- **Phase 9A (10.0 mmol Stoichiometric Lab Batch & Neutral Vacancy Supercell Decks):** Generates exact elemental mass-balanced precursor recipes (`elemental_mass_conservation_diff_g == 0.0 g`), $5\%$ sulfur/selenium volatile overpressure ampoule charges, and Quantum ESPRESSO neutral vacancy supercell decks (`outputs/mp_live_neutral_vacancy_decks/`, perpendicular lattice spacing $d_{\perp,\min} \ge 10.0\text{ \AA}$, monopole point-charge image estimates `point_charge_image_estimate_ev` $\in [0.090, 0.190]\text{ eV}$).
- **Phase 9C (Oblique $0^\circ\text{–}60^\circ$ S/P Coherent TMM, Operating Temp $25^\circ\text{C}\text{–}65^\circ\text{C}$ & 25-Year Arrhenius LCOE):** Evaluates unpolarized $\frac{1}{2}(|r_s|^2+|r_p|^2)$ oblique optics ($\text{IAM}_{60^\circ} = 0.954$), NOCT ($45^\circ\text{C}$) and desert peak ($65^\circ\text{C}$) thermal derating ($\beta_{\text{4T}} = -0.361\%/\text{K}$ vs. $-0.409\%/\text{K}$ c-Si), and 25-year discounted LCOE (**3.172 ¢/kWh**, a **-35.74% reduction** vs. 4.936 ¢/kWh standalone c-Si).

### 7. Phase 10 (`v7.0`): $2^4=16$ Thickness/ARC Global Coherent Optimization (10A), Bifacial Ground-Albedo Harvesting (10B), and SPICE Subcell $J\text{–}V$ String Voltage Matching (10C)

| Pair ID | Stack (`Top + c-Si + Bot`) | Opt Thicknesses `(MgF2, TiO2, Top, Bot)` | Opt Mono 4T PCE | **Bifacial 20% Albedo PCE (W/ft²)** | **Bifacial 30% Albedo PCE (W/ft²)** | **25-Yr Bifacial LCOE (20% Alb)** | Matched String Ratio ($N_{\text{top}} : N_{\text{Si}} : N_{\text{bot}}$) | Bus Voltage $V_{\text{bus,Si}}$ (Mismatch Top / Bot) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mp-861911__mp-1223998` | `Sb2OS2 + c-Si + Bi3InSe6` | `(94, 48, 260, 391 nm)` | 42.45% | **46.17%** (42.89 W/ft², +8.76%) | **48.06%** (44.65 W/ft²) | **3.002 ¢/kWh** | **`37 : 72 : 120`** | 50.08 V (1.18% / 0.04%) |
| `mp-861911__mp-1224922` | `Sb2OS2 + c-Si + CuGaSnSe4` | `(94, 48, 299, 391 nm)` | 42.02% | **46.09%** (42.82 W/ft², +9.69%) | **48.17%** (44.75 W/ft²) | **3.001 ¢/kWh** | **`37 : 72 : 100`** | 50.05 V (1.15% / 0.02%) |
| `mp-1227486__mp-1223998` | `BiSbS3 + c-Si + Bi3InSe6` | `(94, 48, 299, 391 nm)` | 42.37% | **46.09%** (42.82 W/ft², +8.78%) | **47.98%** (44.58 W/ft²) | **3.005 ¢/kWh** | **`36 : 72 : 120`** | 50.12 V (0.19% / 0.08%) |
| `mp-1227486__mp-1224922` | `BiSbS3 + c-Si + CuGaSnSe4` | `(94, 48, 299, 391 nm)` | 42.01% | **46.08%** (42.81 W/ft², +9.69%) | **48.16%** (44.74 W/ft²) | **3.001 ¢/kWh** | **`36 : 72 : 100`** | 50.12 V (0.19% / 0.16%) |
| `mp-861911__mp-22982` | `Sb2OS2 + c-Si + BiCuS2` | `(94, 48, 299, 391 nm)` | 41.97% | **46.02%** (42.75 W/ft², +9.64%) | **48.08%** (44.67 W/ft²) | **3.002 ¢/kWh** | **`37 : 72 : 100`** | 50.05 V (1.15% / 0.44%) |
| `mp-1227486__mp-22982` | `BiSbS3 + c-Si + BiCuS2` | `(94, 48, 299, 391 nm)` | 41.96% | **46.01%** (42.74 W/ft², +9.64%) | **48.07%** (44.66 W/ft²) | **3.002 ¢/kWh** | **`36 : 72 : 101`** | 50.12 V (0.19% / 0.41%) |

### 8. Phase 11 (`v0.8.0`): Realistic Synthesis Practicality (`SPS`), Cached MP TCO Reactivity, Non-Radiative SRH Physics & 4-Path Commercialization Engine
To separate detailed-balance optical ceilings (`ERE = 1.0`) from near-term polycrystalline thin-film manufacturing reality (`ERE = 1e-5` to `5e-3`), Phase 11 (`realistic_commercialization.py` vs. `independent_verifier.py`, full debate in [`docs/REALISTIC_COMMERCIALIZATION_AND_DEBATE_REPORT.md`](docs/REALISTIC_COMMERCIALIZATION_AND_DEBATE_REPORT.md)) evaluates cached Materials Project convex-hull stability windows, `pymatgen` `InterfacialReactivity` against `SnO2`/`In2O3`/`TiO2`, non-radiative SRH + antisite/contact voltage deficits, commercial c-Si Drude FCA, and industrial PVD/RTP fab yield (`90.0%` 1-junction vs. `77.4%` 2-junction):

- **Top Synthesis Practicality (`SPS` out of `100`):** **`mp-1227486 BiSbS3` (`94.76/100`)** and **`mp-861911 Sb2OS2` (`94.44/100`)** lead the 8 evaluated finalists (`0.00 meV/atom` reaction energy on `TiO2` and `SnO2` vs. exothermic `-13.16` and `-15.35 meV/atom` sulfidation on bare `In2O3`/ITO; zero In/Ga/Ag criticality), followed by `mp-22982 BiCuS2` (`89.54/100`), `AgBi3S5` (`88.96`), `BiInS3` (`83.42`), `Bi3InSe6` (`79.71`), `CuInSnSe4` (`61.66`), and `CuGaSnSe4` (`49.99`) (`mp-1195160` `Al2Bi2Cu2S3Cl8` is `None` / not evaluated).
- **4-Path Commercialization Verdict (Base-Case Pilot `ERE = 1e-4`, 20% Albedo):**
  - **Path 0 (Commodity Bifacial TOPCon/SHJ c-Si):** **26.65%** bifacial (`22.94%` mono) at **\$42.00/m²** (`4.246 ¢/kWh` utility / `6.802 ¢/kWh` rooftop LCOE).
  - **Path 1 (3-Layer 4T Sandwich):** Drops to **28.30%–28.78%** bifacial because the `0.75–0.85 eV` rear cell (`V_oc,real = 0.23–0.30 V`) cannibalizes `300–1100 nm` rear albedo photons from `0.72 V` silicon while `77.4%` compound yield inflates cost to **\$96.76–\$109.62/m²** (`5.008–5.368 ¢/kWh` utility LCOE — deferred to Gen-3 `ERE >= 5e-3`).
  - **Path 2 (2-Layer 4T Active Solar Glass Drop-In on Unobstructed Bifacial c-Si — GW Tandem Winner):** **30.61%** (`BiSbS3`) / **30.58%** (`Sb2OS2`) bifacial PCE (`26.87%` mono Base-Case; `28.85%–28.90%` mono Mature) at **\$65.88/m²** (`90.0%` yield), beating Path 0 c-Si on both **utility LCOE (`4.234 ¢/kWh`)** and **rooftop LCOE (`6.470 ¢/kWh`, `-4.9%`)**.
  - **Path 4 (Standalone BIPV Semi-Transparent Solar Window Glazing — Immediate Pilot Beachhead):** **11.40%–11.62%** PCE at `35%` daylighting transmittance (**\$76.38/m²** DGU cost vs. **\$185.00/m²** architectural solar-control glass ASP = **58.7% gross margin**).

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
