# Contrastive Failure Memory Ledger & Negative-Results Architecture

## 1. Why Negative Results Are First-Class Data

In computational and experimental materials science, over $90\%$ of candidate compounds fail not because of $0\text{ K}$ thermodynamic formation energy, but because of **kinetic impurity traps**, **dynamic phonon collapse**, **0D/1D small-polaron localization**, **halide photo-segregation**, **aqueous leaching**, or **deep Shockley-Read-Hall (SRH) point defects**.

`FailSmart-MatEngine` treats every rejected candidate as a **labeled physical boundary condition** inside `data/failure_memory.db` (`ContrastiveFailureLedger`).

---

## 2. Physical Taxonomy of Failure Modes

| Failure Code | Stage Caught | Physical Mechanism | Representative Compound |
| :--- | :--- | :--- | :--- |
| `IMAGINARY_PHONON` | Stage 2 | Harmonic phonon mode $\omega_{\min} < 0\text{ THz}$; crystal spontaneously distorts/shears at $T > 0\text{ K}$. | `Zn2SbS2Br3` ($\omega_{\min} = -1.42\text{ THz}$) |
| `HULL_INSTABILITY` | Stage 2 | $\Delta E_{\text{hull}} > 50\text{ meV/atom}$ and not vibrationally stabilized; phase separates into binaries. | `Sr2ZnOS2` ($\Delta E_{\text{hull}} = 64.0\text{ meV/atom}$) |
| `OXIDE_IMPURITY_SINK` | Stage 3 | Refractory binary/oxide sink ($\text{ZrO}_2$, $\text{BaSO}_4$) consumes precursors unless $T > 500^\circ\text{C}$ (melts soda-lime glass). | `BaZrS3` ($T_{\text{synth}} = 950^\circ\text{C}$) |
| `AQUEOUS_LEACHING` | Stage 3 | Pourbaix diagram ($\text{pH } 4\text{–}9$) shows soluble metal-halide leaching $> 10^{-6}\text{ mol/L}$ in rainwater. | `Pb2BiS2I3` ($2.8\times 10^{-3}\text{ mol/L}$) |
| `TIER2_COST_EXCEEDED` | Stage 3 | Scarce Tier-2 element ($\text{Ag, In, Te, Ga}$) pushes active-layer material cost above $\$0.50/\text{m}^2$. | `AgBiSe2` ($\$0.5795/\text{m}^2$) |
| `LOW_DIM_POLARON_RISK` | Gate A | 0D isolated polyhedra or 1D van der Waals chains trap carriers in self-induced lattice distortions. | `Cs3Bi2I9`, `BiSCl`, `SbSeI` |
| `ANION_PHASE_SEGREGATION` | Gate A | High configurational anion-mixing enthalpy ($\Delta H_{\text{mix}} \ge 35\text{ meV/atom}$) causes light-induced halide unmixing. | `BiCuSeI2` ($\Delta H_{\text{mix}} = 48.5\text{ meV/atom}$) |
| `BANDGAP_OUT_OF_WINDOW` | Stage 4 | Relativistic `HSE06+SOC` spin-orbit splitting shifts fundamental gap outside target spectral window. | `BiCuOS` ($1.18\text{ eV}$), `BaBiO2Cl` ($2.94\text{ eV}$) |
| `DEEP_SRH_DEFECT` | Stage 5 | Intrinsic vacancy or antisite defect creates a mid-gap trap $> 0.15\text{ eV}$ from band edges, killing $V_{oc}$. | `Bi2SnSe3I2` ($\text{I}_{\text{Se}}$ trap at $0.36\text{ eV}$) |

---

## 3. Complete Contrastive Failure Memory Ledger (Pilot Campaign #1 + Seed Archetypes)

The table below reflects all 19 entries registered in `data/failure_memory.db` and `outputs/pilot_campaign_summary.json`. All metrics—including formation energetics, phonon dispersion minima, synthesis temperatures, raw active layer costs, band gaps, SLME efficiencies, 4-terminal stack efficiencies, and SHA-256 provenance hashes—are synchronized bit-for-bit with the verified pipeline output.

| Candidate ID | Formula | Target Track | Stage | Status | Primary Failure Mode / Outcome | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $E_g^{\text{HSE06+SOC}}$ (eV) | Standalone SLME (%) | 4T Stack $\eta$ (%) | Redundancy SHA-256 Verification Hash |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-A09` | `Cu3BiS2Cl2` | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 16.8 | +1.14 | 350.0 | $0.0136 | 1.76 (1.79 dir) | 28.98% | **46.27%** | `159c7df80650534e98ab4689f2a915823e1740d9519958e4b17e021d1e4741dd` |
| `CAND-A03` | `Cu2SbS2Cl` | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 21.0 | +1.05 | 320.0 | $0.0129 | 1.79 (1.83 dir) | 27.88% | **45.23%** | `5f8e08c6e4f27d66bce31638a1432b6ba20dcb0c14a6dc2272fff98b94a4bf72` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom ($0.75\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 12.6 | +0.88 | 295.0 | $0.0865 | 0.75 (0.78 dir) | 18.68% | **44.67%** | `579e58be674c42b0c374e7560780e9c98f7107bc85af119ff1c7d754d48685e8` |
| `CAND-B04` | `Cu2BiSe2I` | Bottom ($0.75\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 11.2 | +1.09 | 345.0 | $0.0509 | 0.74 (0.76 dir) | 18.77% | **44.62%** | `1f9e68b7b0630b7a0dbfde4058bce12558dcc686a07ed57719f9c45b21e97521` |
| `CAND-A02` | `Bi2CuO2SCl` | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 14.5 | +1.18 | 365.0 | $0.0195 | 1.82 (1.86 dir) | 27.02% | **44.42%** | `8b859404bbf87c1807bf90ec7409f780886cd50f95e6c1d691351ca6bbb731c7` |
| `CAND-A06` | `BiZnOSCl` | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 18.2 | +1.29 | 380.0 | $0.0148 | 1.85 (1.89 dir) | 26.16% | **43.60%** | `bf0b91ce3a7286db87ad3ee8e49d2c9321059e6073e792df7216cd555ce94f1c` |
| `CAND-B03` | `Bi2SnSe3I2` | Bottom ($0.75\text{ eV}$) | 4 | `REJECTED` | `DEEP_SRH_DEFECT` ($\text{I}_{\text{Se}}$ trap at $0.36\text{ eV}$) | 15.1 | +0.91 | 330.0 | $0.0639 | 0.77 (0.81 dir) | 18.73% | 44.82% | `832a485610f47d8cef6defca39e8d67029f24f55d3176ae870cc00d82a49134d` |
| `CAND-A01` | `BiCuOS` | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` ($1.18\text{ eV}$ indirect) | 0.0 | +1.62 | 340.0 | $0.0205 | 1.18 (1.52 dir) | 20.22% | 37.84% | `61f0241a5652403b5c765b7bc4c0aab68607cb95892d2cc2ad43936a623e7cc0` |
| `CAND-A04` | `BaBiO2Cl` | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` ($2.94\text{ eV}$) + $V_{\text{O}}$ trap | 4.2 | +1.38 | 440.0 | $0.0166 | 2.94 (3.12 dir) | 2.45% | 20.90% | `f18ee732f8f74bd28c6b227de7888091d8ac38262f6b5ca93f058ee6fee1bf24` |
| `LIT-FAIL-002` | `Cs3Bi2I9` | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `SMALL_POLARON_TRAP` ($m_h^* = 2.45\,m_0, \alpha_F = 7.8$) | 8.0 | +0.65 | 180.0 | $0.3100 | 2.04 (2.18 dir) | 11.20% | 0.00% | — |
| `LIT-FAIL-001` | `BaZrS3` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` (LBNL 80k Impurity Dataset) | 0.0 | +1.45 | 950.0 | $0.1400 | 1.82 (1.82 dir) | 25.40% | 0.00% | — |
| `LIT-FAIL-003` | `Pb2BiS2I3` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `AQUEOUS_LEACHING` ($\text{PbI}_2$ sublattice dissolution) | 19.0 | +0.82 | 340.0 | $0.2200 | 1.71 (1.83 dir) | 19.10% | 0.00% | — |
| `CAND-A07` | `BaZrS3` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` ($\text{ZrO}_2$ sink needs $950^\circ\text{C}$) | 0.0 | +1.48 | 950.0 | $0.0143 | — | — | — | `0d19239adaa13eb72f78af6d0a3164c5a3523d2e26a166a714bff7c7c0bbdf55` |
| `CAND-A08` | `BiSCl` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `LOW_DIM_POLARON_RISK` (1D chain + $\text{BiCl}_3$ volatility) | 2.5 | +0.74 | 290.0 | $0.0204 | — | — | — | `cdc37afd18a90741a5ae8d956bb3b956f9c81953f8ee4630a33eb4f636894435` |
| `CAND-B01` | `BiCuSeI2` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `ANION_PHASE_SEGREGATION` ($\Delta H_{\text{mix}} = 48.5\text{ meV}$) | 19.4 | +0.94 | 310.0 | $0.0755 | — | — | — | `df63147bd46be8457ee004ca07941ff12b523c4f2e07ec431ca25e98c6cd5616` |
| `CAND-B05` | `AgBiSe2` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `TIER2_COST_EXCEEDED` ($\$0.5795/\text{m}^2 > \$0.50/\text{m}^2$) | 0.0 | +1.15 | 360.0 | $0.5795 | — | — | — | `777d45b0278ebbd0637da55dc4b4f3221611ae7e44621d37f096adb730555398` |
| `CAND-B06` | `SbSeI` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `LOW_DIM_POLARON_RISK` (1D chain anisotropy) | 3.8 | +0.68 | 275.0 | $0.0735 | — | — | — | `09b93e4842b291fbe083fd0becf3afc9c00d4b7c8b0e863a2c3bc9a9b9e0ea15` |
| `CAND-A05` | `Sr2ZnOS2` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `HULL_INSTABILITY` ($\Delta E_{\text{hull}} = 64.0\text{ meV/atom}$) | 64.0 | +0.92 | — | — | — | — | — | `3cf1a4f84c5de2588d2cbe4b9774e56280bed6414f83f08e56de1b847bfc4815` |
| `CAND-A10` | `Zn2SbS2Br3` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `IMAGINARY_PHONON` ($\omega_{\min} = -1.42\text{ THz}$) | 89.0 | -1.42 | — | — | — | — | — | `7f18860c3549c1bdda74f5e491457ea01ae3ef84c2d9854c79626ff49b3ab2cd` |

---

## 4. Promoted Finalists: Dual-Redundancy Verified Physical Metrics

For the 6 promoted finalists that passed all 5 stages and Gates A & B, every candidate has been independently verified across two distinct physical engines:

| Candidate ID | Formula | Target Track | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_g^{\text{HSE06+SOC}}$ (Ind / Dir) | Single-Layer SLME (%) | **3-Layer 4T Tandem $\eta$ (%)** | Redundancy SHA-256 Hash |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-A09` | `Cu3BiS2Cl2` | Top Active Glass | 350.0 | $0.0136 | 16.8 | 1.14 | 1.76 / 1.79 eV | 28.98% | **46.27%** | `159c7df80650534e98ab4689f2a915823e1740d9519958e4b17e021d1e4741dd` |
| `CAND-A03` | `Cu2SbS2Cl` | Top Active Glass | 320.0 | $0.0129 | 21.0 | 1.05 | 1.79 / 1.83 eV | 27.88% | **45.23%** | `5f8e08c6e4f27d66bce31638a1432b6ba20dcb0c14a6dc2272fff98b94a4bf72` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom IR Scavenger | 295.0 | $0.0865 | 12.6 | 0.88 | 0.75 / 0.78 eV | 18.68% | **44.67%** | `579e58be674c42b0c374e7560780e9c98f7107bc85af119ff1c7d754d48685e8` |
| `CAND-B04` | `Cu2BiSe2I` | Bottom IR Scavenger | 345.0 | $0.0509 | 11.2 | 1.09 | 0.74 / 0.76 eV | 18.77% | **44.62%** | `1f9e68b7b0630b7a0dbfde4058bce12558dcc686a07ed57719f9c45b21e97521` |
| `CAND-A02` | `Bi2CuO2SCl` | Top Active Glass | 365.0 | $0.0195 | 14.5 | 1.18 | 1.82 / 1.86 eV | 27.02% | **44.42%** | `8b859404bbf87c1807bf90ec7409f780886cd50f95e6c1d691351ca6bbb731c7` |
| `CAND-A06` | `BiZnOSCl` | Top Active Glass | 380.0 | $0.0148 | 18.2 | 1.29 | 1.85 / 1.89 eV | 26.16% | **43.60%** | `bf0b91ce3a7286db87ad3ee8e49d2c9321059e6073e792df7216cd555ce94f1c` |
