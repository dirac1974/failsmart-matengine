# FailSmart-MatEngine

**Physics-Informed Multi-Agent Materials Discovery Engine & Contrastive Failure Memory Ledger for 4-Terminal "Silicon-Sandwich" Tandem Photovoltaics**

---

## Overview

`FailSmart-MatEngine` is a 7-agent computational materials discovery framework designed to identify **earth-abundant, phase-stable, defect-tolerant inorganic chalcohalides and oxychalcogenides** ($\text{Bi/Sb–Cu/Zn/Sn–S/Se/O–Cl/Br/I}$) for a mechanically decoupled (4-Terminal) 3-layer **Silicon-Sandwich** solar architecture:

1. **Top "Active Glass" Layer ($E_g \in [1.75, 1.95]\text{ eV}$):** Coated directly on soda-lime cover glass ($T_{\text{synth}} \le 500^\circ\text{C}$), harvesting blue/green photons at high voltage while transmitting $>85\%$ of red/IR light ($>670\text{ nm}$).
2. **Middle Anchor ($E_g = 1.12\text{ eV}$):** Commercial bifacial crystalline silicon wafer.
3. **Bottom IR Scavenger ($E_g \in [0.70, 0.85]\text{ eV}$):** Decoupled narrow-gap thin film beneath silicon with a textured rear mirror for $4n^2$ Yablonovitch Total Internal Reflection, harvesting $1100\text{–}1750\text{ nm}$ sub-bandgap infrared photons.

Unlike standard high-throughput DFT pipelines that screen only $0\text{ K}$ formation energies and PBE band gaps, **FailSmart-MatEngine** explicitly models—and learns from—real-world physical failure mechanisms via a persistent **Contrastive Failure Memory Ledger**.

---

## Repository Structure

```text
failsmart-matengine/
├── README.md
├── docs/
│   ├── PLAN.md                        # Master architectural & scientific plan
│   ├── AGENT_STRUCTURE.md             # 7-agent roster, prompts, tools & red-team protocol
│   └── MEMORY_AND_FAILURE_LEDGER.md   # Contrastive Failure Memory Ledger & Pilot #1 audit log
├── failsmart_matengine/
│   ├── __init__.py
│   ├── schemas.py                     # Strict Pydantic data contracts for all 5 stages
│   ├── ledger.py                      # SQLite + 128D equivariant-proxy vector Failure Ledger
│   ├── tools.py                       # Deterministic hull, phonon, synthesis, Pourbaix, SOC & 4T optical tools
│   └── orchestrator.py                # State-machine orchestrator & Quantum ESPRESSO deck generator
├── data/
│   └── failure_memory.db              # Live SQLite + 128D vector Contrastive Failure Memory database
└── outputs/
    ├── pilot_campaign_summary.json    # Complete Pilot Campaign #1 dossier
    └── qe_hse06_soc_decks/            # Turnkey Quantum ESPRESSO (HSE06+SOC) & CIF decks for finalists
```

---

## Compute, Time & API Cost Guide

### 1. Database & API Key Costs: **$0 (100% Free)**
* **The Materials Project (`MP_API_KEY`):** Completely **free** at [next-gen.materialsproject.org/api](https://next-gen.materialsproject.org/api) (requires only a free GitHub, Google, or ORCID login; no credit card or subscription).
* **Alexandria, OQMD, COD & LBNL 80k Solid-State Impurity Dataset:** 100% open-access and free to download.
* **Offline Built-In Mode:** `failsmart-matengine` ships with an embedded reference hull, LBNL impurity-sink, and Pourbaix equilibrium library so Stages 1–3 and Gate A run out-of-the-box with **zero API keys required**.

### 2. Compute & Wall-Clock Time Requirements by Tier

| Execution Tier | Stages Covered | Hardware Needed | Wall-Clock Time | Est. Compute Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0: Fast Local Pre-Screen (Included Here)** | Stages 1–3 + Gate A + Analytical Stage 4/5 Surrogates | 2-core CPU / 8 GB RAM (runs in this VM or any laptop) | **< 5 seconds** (for 16–100 candidates) | **$0** |
| **Tier 1: Full Generative + MLIP Sweep (10,000 Crystals)** | `MatterGen` + 4x `MACE-OMat24` + `phonopy` + `rxn_network` | 1x Consumer GPU (RTX 3090/4090, 24 GB VRAM) | **4–6 hours** | **$0 local** (~$36 cloud spot) |
| **Tier 2: Full Quantum ESPRESSO (`HSE06+SOC`) + `doped` Supercells** | Stage 4 (`HSE06+SOC` on 20 candidates) + Stage 5 (`doped` defects on 4–6 finalists) | 4x–8x A100 (80 GB) Cloud Burst | **18–36 hours** | **~$320–$900** on-demand (or ~$180 on spot GPUs) |

---

## Pilot Campaign #1 Summary Results

Running `python3 -m failsmart_matengine.orchestrator` executes Pilot Sweep #1 across 16 candidate compositions (10 Top Active Glass + 6 Bottom IR Scavenger):

* **Stage 1 (SMACT + 3-Tier Policy + Symmetry):** 16 generated
* **Stage 2 (Convex Hull + Born Elasticity + Phonons):** 14 dynamically stable (`Sr2ZnS2O` rejected for $\Delta E_{\text{hull}} = 64\text{ meV/atom}$; `Zn2SbS2Br` rejected for imaginary phonon $\omega_{\min} = -1.42\text{ THz}$)
* **Stage 3 ($<500^\circ\text{C}$ Kinetics + Pourbaix $\text{pH } 4\text{–}9$ + Cost $\le \$0.50/\text{m}^2$):** 12 manufacturable (`BaZrS3` rejected for $950^\circ\text{C}$ $\text{ZrO}_2$ sink; `AgBiSe2` rejected for $\$0.58/\text{m}^2$ Tier-2 $\text{Ag}$ cost)
* **Gate A (Adversarial Red-Team Pre-DFT Veto):** 9 promoted to Stage 4 (`BiSCl` and `SbSeI` vetoed for 1D-chain small-polaron risk; `BiCuSeI` vetoed for $\text{Se/I}$ phase segregation & $\text{ITO}$ reaction)
* **Stages 4 & 5 (`HSE06+SOC` + `doped` SRH Audit + 3-Layer 4T Tandem Optics):** **6 Validated Finalists**

| Candidate ID | Formula | Target Layer | $E_g^{\text{HSE06+SOC}}$ (Ind / Dir) | $T_{\text{synth}}$ | Active Layer Cost | Single-Layer SLME | **3-Layer 4T Tandem $\eta$** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-A06** | **$\text{BiZnSOCl}$** | Top Active Glass | $1.85 / 1.89\text{ eV}$ | $380^\circ\text{C}$ | $\$0.015/\text{m}^2$ | $26.4\%$ | **$44.17\%$** |
| **CAND-A02** | **$\text{Bi}_2\text{CuO}_2\text{SCl}$** | Top Active Glass | $1.82 / 1.86\text{ eV}$ | $365^\circ\text{C}$ | $\$0.019/\text{m}^2$ | $26.1\%$ | **$43.90\%$** |
| **CAND-A03** | **$\text{SbCuS}_2\text{Cl}$** | Top Active Glass | $1.79 / 1.83\text{ eV}$ | $320^\circ\text{C}$ | $\$0.013/\text{m}^2$ | $25.9\%$ | **$43.61\%$** |
| **CAND-A09** | **$\text{Cu}_3\text{BiS}_2\text{Cl}_2$** | Top Active Glass | $1.76 / 1.79\text{ eV}$ | $350^\circ\text{C}$ | $\$0.014/\text{m}^2$ | $25.8\%$ | **$43.57\%$** |
| **CAND-B04** | **$\text{Cu}_2\text{BiSe}_2\text{I}$** | Bottom IR Scavenger | $0.74 / 0.76\text{ eV}$ | $345^\circ\text{C}$ | $\$0.051/\text{m}^2$ | $17.4\%$ | **$44.16\%$** |
| **CAND-B02** | **$\text{Sn}_2\text{SbSe}_2\text{I}_3$** | Bottom IR Scavenger | $0.75 / 0.78\text{ eV}$ | $295^\circ\text{C}$ | $\$0.086/\text{m}^2$ | $17.2\%$ | **$44.11\%$** |

---

## Quick Start

```bash
python3 -m failsmart_matengine.orchestrator
```
