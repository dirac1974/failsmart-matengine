# Contrastive Failure Memory Ledger & Negative-Results Architecture

## 1. Why Negative Results Are First-Class Data

In computational and experimental materials science, over $90\%$ of candidate compounds fail not because of $0\text{ K}$ thermodynamic formation energy, but because of **kinetic impurity traps**, **dynamic phonon collapse**, **superionic ion migration**, **0D/1D small-polaron localization**, **halide photo-segregation**, **aqueous leaching**, or **deep Shockley-Read-Hall (SRH) point defects**.

`FailSmart-MatEngine` treats every rejected candidate as a **labeled physical boundary condition** inside `data/failure_memory.db` (`ContrastiveFailureLedger`).

---

## 2. Physical Taxonomy of Failure Modes

| Failure Code | Stage Caught | Physical Mechanism | Representative Compound |
| :--- | :--- | :--- | :--- |
| `IMAGINARY_PHONON` | Stage 2a | Harmonic phonon mode $\omega_{\min} < 0\text{ THz}$; crystal spontaneously distorts/shears at $T > 0\text{ K}$. | `Zn2SbS2Br3` ($\omega_{\min} = -1.42\text{ THz}$) |
| `HULL_INSTABILITY` | Stage 2a | $\Delta E_{\text{hull}} > 50\text{ meV/atom}$ and not vibrationally stabilized; phase separates into binaries. | `Sr2ZnOS2` ($\Delta E_{\text{hull}} = 64.0\text{ meV/atom}$) |
| `ION_MIGRATION_INSTABILITY` | Stage 2b | Ion migration barrier $E_{\text{mig}} < 0.65\text{ eV}$; superionic $\text{Cu}^+/\text{Ag}^+$/halide drift causes severe hysteresis and degradation under 1-sun bias. | `Cu3BiS2Cl2` ($E_{\text{mig}} = 0.42\text{ eV}$) |
| `OXIDE_IMPURITY_SINK` | Stage 3 | Refractory binary/oxide sink ($\text{ZrO}_2$, $\text{BaO}$, $\text{SrO}$) consumes precursors unless $T > 500^\circ\text{C}$ (melts soda-lime glass). | `BaZrS3` ($950^\circ\text{C}$), `Sr2Cu2O2S` ($650^\circ\text{C}$) |
| `AQUEOUS_LEACHING` | Stage 3 | Pourbaix diagram ($\text{pH } 4\text{–}9$) shows soluble metal-halide leaching $> 10^{-6}\text{ mol/L}$ in rainwater. | `Pb2BiS2I3` ($2.8\times 10^{-3}\text{ mol/L}$) |
| `TIER2_COST_EXCEEDED` | Stage 3 | Scarce Tier-2 element ($\text{Ag, In, Te, Ga}$) pushes active-layer material cost above $\$0.50/\text{m}^2$. | `AgBiSe2` ($\$0.5795/\text{m}^2$) |
| `LOW_DIM_POLARON_RISK` | Gate A | 0D isolated polyhedra or 1D van der Waals chains trap carriers in self-induced lattice distortions. | `Cs3Bi2I9`, `BiSCl`, `SbSeI` |
| `ANION_PHASE_SEGREGATION` | Gate A | High configurational anion-mixing enthalpy ($\Delta H_{\text{mix}} \ge 35\text{ meV/atom}$) causes light-induced halide unmixing. | `BiCuSeI2` ($48.5\text{ meV}$), `Cu2SnSeI2` ($41.2\text{ meV}$) |
| `BANDGAP_OUT_OF_WINDOW` | Stage 4 | Relativistic `HSE06+SOC` spin-orbit splitting shifts fundamental gap outside target spectral window. | `BiCuOS` ($1.18\text{ eV}$), `BaBiO2Cl` ($2.94\text{ eV}$) |
| `DEEP_SRH_DEFECT` | Stage 5 | Intrinsic vacancy or antisite defect creates a mid-gap trap $> 0.15\text{ eV}$ from band edges, killing $V_{oc}$. | `Bi2SnSe3I2` ($\text{I}_{\text{Se}}$ trap at $0.36\text{ eV}$) |

---

## 3. Complete Contrastive Failure Memory Ledger (20 Campaign Candidates + 3 Historical Literature Archetypes = 23 Total)

The table below reflects all 23 entries registered in `data/failure_memory.db` and `outputs/pilot_campaign_summary.json`. All metrics—including formation energetics, phonon dispersion minima, ion migration barriers, synthesis temperatures, raw active layer costs, band gaps, SLME efficiencies, 4-terminal stack efficiencies, and SHA-256 provenance hashes—are synchronized bit-for-bit with the verified pipeline output.

| Candidate ID | Formula | Target Track | Stage | Status | Primary Failure Mode / Outcome | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $E_g^{\text{HSE06+SOC}}$ (eV) | Standalone SLME (%) | 4T Stack $\eta$ (%) | Redundancy SHA-256 Verification Hash |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-B04` | `Cu2BiSe2I` | Bottom ($0.75\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 11.2 | +1.09 | 0.71 | 345.0 | $0.0509 | 0.74 (0.76 dir) | 23.59% | **42.08%** | `f8c3fe9aabede259ea5158ff04fdf38b65ade2b6656f194a79cade99337623c2` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom ($0.75\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 12.6 | +0.88 | 0.75 | 295.0 | $0.0865 | 0.75 (0.78 dir) | 23.48% | **41.83%** | `0e7d2cff9087e81f64923a3627923828046e0899fcf3f854cd24fb9d43913f52` |
| `CAND-A03` | `Cu2SbS2Cl` | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 21.0 | +1.05 | 0.74 | 320.0 | $0.0129 | 1.79 (1.83 dir) | 25.08% | **41.77%** | `badee394a07f1aef7074748fa8673dae56c245f2a7b46aeef2ec09c66bb83df6` |
| `CAND-A02` | `Bi2CuO2SCl` | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 14.5 | +1.18 | 0.88 | 365.0 | $0.0195 | 1.82 (1.86 dir) | 24.43% | **41.66%** | `1df52efdd58d0e055ac198a8332ce11a8b0d61dc8c760738c93cf33ff0afc763` |
| `CAND-A06` | `BiZnOSCl` | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 18.2 | +1.29 | 0.98 | 380.0 | $0.0148 | 1.85 (1.89 dir) | 23.81% | **41.55%** | `161eb8f206f732cdd034ca55584620c623da5d2130b28da5414d99d8aeb311b1` |
| `CAND-B03` | `Bi2SnSe3I2` | Bottom ($0.75\text{ eV}$) | 4 | `REJECTED` | `DEEP_SRH_DEFECT` | 15.1 | +0.91 | — | 330.0 | $0.0639 | 0.77 (0.81 dir) | 23.52% | 41.47% | `c07da04bef5cb9b64319623b919a7a5c2b13987fad5ec319a6d100ebf0001d22` |
| `CAND-A04` | `BaBiO2Cl` | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` | 4.2 | +1.38 | — | 440.0 | $0.0166 | 2.94 (3.12 dir) | 2.55% | 30.37% | `d5b2d6a80ed458384106b62bb11f48ac2a0ff358f0d8b0a13365f94eeee01d71` |
| `CAND-A01` | `BiCuOS` | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` | 0.0 | +1.62 | — | 340.0 | $0.0205 | 1.18 (1.52 dir) | 17.88% | 28.51% | `3e200d6f6616f52707c5bae4c1c73da652b4eedefd932dede4e73624ce343419` |
| `LIT-FAIL-002` | `Cs3Bi2I9` | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `SMALL_POLARON_TRAP` | 8.0 | +0.65 | — | 180.0 | $0.3100 | 2.04 (2.18 dir) | 11.20% | 0.00% | — |
| `LIT-FAIL-001` | `BaZrS3` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 0.0 | +1.45 | — | 950.0 | $0.1400 | 1.82 (1.82 dir) | 25.40% | 0.00% | — |
| `LIT-FAIL-003` | `Pb2BiS2I3` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `AQUEOUS_LEACHING` | 19.0 | +0.82 | — | 340.0 | $0.2200 | 1.71 (1.83 dir) | 19.10% | 0.00% | — |
| `CAND-A07` | `BaZrS3` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 0.0 | +1.48 | — | 950.0 | $0.0143 | — | — | — | `0cd5750d91bc156167298d428b69087a3e73ba56340c0c586a95ad4664861b12` |
| `CAND-A08` | `BiSCl` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `LOW_DIM_POLARON_RISK` | 2.5 | +0.74 | — | 290.0 | $0.0204 | — | — | — | `95f80ffde8ce7b524e07b38352249236bac46e1ed64482c9ff0e9883401bfefe` |
| `CAND-B01` | `BiCuSeI2` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `ANION_PHASE_SEGREGATION` | 19.4 | +0.94 | — | 310.0 | $0.0755 | — | — | — | `0b3e6fd58f87eb3f9cbba8f8830a3de9893dcc54a92cdbdbff46632bd35c12bf` |
| `CAND-B05` | `AgBiSe2` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `TIER2_COST_EXCEEDED` | 0.0 | +1.15 | — | 360.0 | $0.5795 | — | — | — | `9f3c95f57707fd6fa142fc301e5b8f8b732d842f9ee7e2586695fbabd4cafbf3` |
| `CAND-B06` | `SbSeI` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `LOW_DIM_POLARON_RISK` | 3.8 | +0.68 | — | 275.0 | $0.0735 | — | — | — | `7cf80961ae033734a9f5763a7e460243ca3954cfb273d2a5ff65bdb4ad8e8c77` |
| `CAND-OOD-01` | `Sr2Cu2O2S` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 8.5 | +1.35 | — | 650.0 | $0.0093 | — | — | — | `67167988a1954b1ab812e79663cad1bd9705abb3c5724b41ddd0d7917721fa9f` |
| `CAND-OOD-02` | `Ba2BiS3Cl` | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 11.0 | +1.20 | — | 650.0 | $0.0116 | — | — | — | `a0ba3a282e2cc64ede21389084d7b501e220999d0e975028cd9547dc9a08a14a` |
| `CAND-OOD-03` | `Ba2BiSe3I` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 14.0 | +0.98 | — | 650.0 | $0.0442 | — | — | — | `33ebfa66679526ecfb84dd0e70f0bd868252e6194939291264b83b817c66043c` |
| `CAND-OOD-04` | `Cu2SnSeI2` | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `ANION_PHASE_SEGREGATION` | 16.5 | +0.92 | — | 340.0 | $0.0810 | — | — | — | `c942b57e1123890d69985cd98c625826f63fe42db065e3e704529503a641b94c` |
| `CAND-A05` | `Sr2ZnOS2` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `HULL_INSTABILITY` | 64.0 | +0.92 | — | — | — | — | — | — | `d97ea461d5fc6f5ff64d62890cde4b4d0c3128adabaaf60b597abeb591bfb556` |
| `CAND-A09` | `Cu3BiS2Cl2` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `ION_MIGRATION_INSTABILITY` | 16.8 | +1.14 | 0.42 | — | — | — | — | — | `6a0ee951c51a6e3257bdc58bf3ff3760630b6dc7a8f613aa75a97954233b98ed` |
| `CAND-A10` | `Zn2SbS2Br3` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `IMAGINARY_PHONON` | 89.0 | -1.42 | — | — | — | — | — | — | `d44362cdb5639442e0a497b52e6bc96675e6f3f2af5bfee441b47c5040810881` |

---

## 4. Promoted Finalists: Dual-Redundancy Verified Physical Metrics

For the 5 promoted finalists that passed all 5 stages and Gates A & B, every candidate has been independently verified across two distinct physical engines:

| Candidate ID | Formula | Target Track | Space Group | $N_{\text{sites}}$ | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $E_g^{\text{HSE06+SOC}}$ (Ind / Dir) | Single-Layer SLME (%) | SQ Limit (%) | 2-Layer Si $\eta$ (%) | 4T Std Si FCA $\eta$ (%) | **3-Layer 4T Tandem $\eta$ (%)** | Redundancy SHA-256 Hash |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-A02` | `Bi2CuO2SCl` | Top Active Glass | `I4/mmm` (#139) | 28 | 365.0 | $0.0195 | 14.5 | 1.18 | 0.88 | 1.82 / 1.86 eV | 24.43% | 26.78% | 38.29% | 40.43% | **41.66%** | `1df52efdd58d0e055ac198a8332ce11a8b0d61dc8c760738c93cf33ff0afc763` |
| `CAND-A03` | `Cu2SbS2Cl` | Top Active Glass | `Pnma` (#62) | 24 | 320.0 | $0.0129 | 21.0 | 1.05 | 0.74 | 1.79 / 1.83 eV | 25.08% | 27.32% | 38.41% | 40.54% | **41.77%** | `badee394a07f1aef7074748fa8673dae56c245f2a7b46aeef2ec09c66bb83df6` |
| `CAND-A06` | `BiZnOSCl` | Top Active Glass | `P4/nmm` (#129) | 10 | 380.0 | $0.0148 | 18.2 | 1.29 | 0.98 | 1.85 / 1.89 eV | 23.81% | 26.11% | 38.18% | 40.31% | **41.55%** | `161eb8f206f732cdd034ca55584620c623da5d2130b28da5414d99d8aeb311b1` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom IR Scavenger | `Cmcm` (#63) | 32 | 295.0 | $0.0865 | 12.6 | 0.88 | 0.75 | 0.75 / 0.78 eV | 23.48% | 25.00% | 38.26% | 40.51% | **41.83%** | `0e7d2cff9087e81f64923a3627923828046e0899fcf3f854cd24fb9d43913f52` |
| `CAND-B04` | `Cu2BiSe2I` | Bottom IR Scavenger | `Pnma` (#62) | 24 | 345.0 | $0.0509 | 11.2 | 1.09 | 0.71 | 0.74 / 0.76 eV | 23.59% | 24.79% | 38.26% | 40.64% | **42.08%** | `f8c3fe9aabede259ea5158ff04fdf38b65ade2b6656f194a79cade99337623c2` |
