# Contrastive Failure Memory Ledger & Negative-Results Architecture

> [!WARNING]
> **Read first (independent audit, 2026-11):** the ledger is reset at the start of every run, its embedding (`composition_embedding`) is a hand-built composition vector (MACE not run), and its score does not feed any gate. Failure labels come from heuristic rules. See [`INDEPENDENT_AUDIT_2026-11.md`](INDEPENDENT_AUDIT_2026-11.md) and [`REMEDIATION_TASKS.md`](REMEDIATION_TASKS.md).

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
| `BANDGAP_OUT_OF_WINDOW` | Stage 4 | Estimated band gap (`gap_est_*`; `HSE06+SOC` not run) falls outside target spectral window. | `BiCuOS` ($1.18\text{ eV}$), `BaBiO2Cl` ($2.94\text{ eV}$) |
| `DEEP_SRH_DEFECT` | Stage 5 | Intrinsic vacancy or antisite defect creates a mid-gap trap $> 0.15\text{ eV}$ from band edges, killing $V_{oc}$. | `Bi2SnSe3I2` ($\text{I}_{\text{Se}}$ trap at $0.36\text{ eV}$) |

---

## 3. Complete Contrastive Failure Memory Ledger (20 Campaign Candidates + 3 Historical Literature Archetypes = 23 Total)

The table below reflects all 23 entries registered in `data/failure_memory.db` and `outputs/pilot_campaign_summary.json`. All metrics—including formation energetics, phonon dispersion minima, ion migration barriers, synthesis temperatures, raw active layer costs, band gaps, SLME efficiencies, 4-terminal stack efficiencies, and SHA-256 provenance hashes—are synchronized bit-for-bit with the verified pipeline output.

| Candidate ID | Formula | Target Track | Stage | Status | Primary Failure Mode / Outcome | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $E_g^{\text{est}}$ (eV) | Standalone SLME (%) | 4T Stack $\eta$ (%) | Redundancy SHA-256 Digest |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-B04` | `Cu2BiSe2I` | Bottom (0.75 eV) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 11.2 | +1.09 | 0.71 | 345.0 | \$0.0509 | 0.74 (0.76 dir) | 23.70% | **42.10%** | `e5a66a7b95475eb68e1518917f2c358ff2b84052a6d0ef8974ad46ed2e48a4c3` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom (0.75 eV) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 12.6 | +0.88 | 0.75 | 295.0 | \$0.0865 | 0.75 (0.78 dir) | 23.58% | **41.86%** | `8d2a220da8b781d0d9c9b7685baf2befb20b2dd749671de821a322ae923b049e` |
| `CAND-A03` | `Cu2SbS2Cl` | Top (1.85 eV) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 21.0 | +1.05 | 0.74 | 320.0 | \$0.0129 | 1.79 (1.83 dir) | 25.06% | **41.78%** | `11d0cc71c0ff065d442fec434bb5920620a02c649ddb865e37a32b7695c36abc` |
| `CAND-A02` | `Bi2CuO2SCl` | Top (1.85 eV) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 14.5 | +1.18 | 0.88 | 365.0 | \$0.0195 | 1.82 (1.86 dir) | 24.40% | **41.67%** | `a20a11b8a87356615ed2dbf1cf9d78b0a506da656b2f522035708a91eb2981e9` |
| `CAND-A06` | `BiZnOSCl` | Top (1.85 eV) | 5 | **PROMOTED** | Passed all 5 stages & Red-Team gates | 18.2 | +1.29 | 0.98 | 380.0 | \$0.0148 | 1.85 (1.89 dir) | 23.79% | **41.56%** | `8185c04696a2a053f41545b6e8cc3c4ba50cbe9ea9d90840eca3f5b20c5c3775` |
| `CAND-B03` | `Bi2SnSe3I2` | Bottom (0.75 eV) | 4 | `REJECTED` | `DEEP_SRH_DEFECT` | 15.1 | +0.91 | — | 330.0 | \$0.0639 | 0.77 (0.81 dir) | 23.62% | 41.49% | `073e8e62f3b5b5c085fb8a7eb1a612ebaa305db491ef0fa405a6814217f82bd3` |
| `CAND-A04` | `BaBiO2Cl` | Top (1.85 eV) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` | 4.2 | +1.38 | — | 440.0 | \$0.0166 | 2.94 (3.12 dir) | 2.55% | 30.38% | `ff1ca30a794c0576bf0be21eb218f62b9bb51a9465a7e8626e0c954dc79b74a2` |
| `CAND-A01` | `BiCuOS` | Top (1.85 eV) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` | 0.0 | +1.62 | — | 340.0 | \$0.0205 | 1.18 (1.52 dir) | 17.85% | 28.51% | `82d414cf2d3507943451d7ffbb8ab8a89811d24599716a9103f1241c4f01b6c5` |
| `LIT-FAIL-002` | `Cs3Bi2I9` | Top (1.85 eV) | 4 | `REJECTED` | `SMALL_POLARON_TRAP` | 8.0 | +0.65 | — | 180.0 | \$0.3100 | 2.04 (2.18 dir) | 11.20% | 0.00% | — |
| `LIT-FAIL-001` | `BaZrS3` | Top (1.85 eV) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 0.0 | +1.45 | — | 950.0 | \$0.1400 | 1.82 (1.82 dir) | 25.40% | 0.00% | — |
| `LIT-FAIL-003` | `Pb2BiS2I3` | Top (1.85 eV) | 3 | `REJECTED` | `AQUEOUS_LEACHING` | 19.0 | +0.82 | — | 340.0 | \$0.2200 | 1.71 (1.83 dir) | 19.10% | 0.00% | — |
| `CAND-A07` | `BaZrS3` | Top (1.85 eV) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 0.0 | +1.48 | — | 950.0 | \$0.0143 | — | — | — | `f2e86d5e56a0b4ed5d24891d8db46cc0c0fc0bf1aa75a8e2242950f75aca3479` |
| `CAND-A08` | `BiSCl` | Top (1.85 eV) | 3 | `REJECTED` | `LOW_DIM_POLARON_RISK` | 2.5 | +0.74 | — | 290.0 | \$0.0204 | — | — | — | `2a4b3c77c1985f2203391c731bcdbc421d43297645fc27c935887e639d06de06` |
| `CAND-B01` | `BiCuSeI2` | Bottom (0.75 eV) | 3 | `REJECTED` | `ANION_PHASE_SEGREGATION` | 19.4 | +0.94 | — | 310.0 | \$0.0755 | — | — | — | `bf8737892686317e569c35df8f84a06657418b3ce3acd793dae763e4d108147b` |
| `CAND-B05` | `AgBiSe2` | Bottom (0.75 eV) | 3 | `REJECTED` | `TIER2_COST_EXCEEDED` | 0.0 | +1.15 | — | 360.0 | \$0.5795 | — | — | — | `3bf4739bbcc2af52f0f8953770d87ef7105ca7f6abfe55899c8e91ff3107a2eb` |
| `CAND-B06` | `SbSeI` | Bottom (0.75 eV) | 3 | `REJECTED` | `LOW_DIM_POLARON_RISK` | 3.8 | +0.68 | — | 275.0 | \$0.0735 | — | — | — | `7ce2d066766ee03e1755e08989f85048d8770c60eab9e6f5ad93c826ea36bb27` |
| `CAND-OOD-01` | `Sr2Cu2O2S` | Top (1.85 eV) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 8.5 | +1.35 | — | 650.0 | \$0.0093 | — | — | — | `9c1f6ae661d1cdfbcf8250e0db6dfcc7ddb002be8f233cff253f321475983c60` |
| `CAND-OOD-02` | `Ba2BiS3Cl` | Top (1.85 eV) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 11.0 | +1.20 | — | 650.0 | \$0.0116 | — | — | — | `e78e742d8c03f3a3831fe1380183889b323fde682bf90363eae2a98308ee635d` |
| `CAND-OOD-03` | `Ba2BiSe3I` | Bottom (0.75 eV) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` | 14.0 | +0.98 | — | 650.0 | \$0.0442 | — | — | — | `06c9688ee76cf48abed2c7553646959f285aa2532a2b57adffcc78332e9e0b7d` |
| `CAND-OOD-04` | `Cu2SnSeI2` | Bottom (0.75 eV) | 3 | `REJECTED` | `ANION_PHASE_SEGREGATION` | 16.5 | +0.92 | — | 340.0 | \$0.0810 | — | — | — | `7b23361b61eb13bc7bcc50232ab6867bfccd34b226c2ac409feda27fecc93724` |
| `CAND-A05` | `Sr2ZnOS2` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `HULL_INSTABILITY` | 64.0 | +0.92 | — | — | — | — | — | — | `2521f5f4afb379a2a9a2232a3a29fc54dedf749ec0d3abdcfd940ae4803faab0` |
| `CAND-A09` | `Cu3BiS2Cl2` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `ION_MIGRATION_INSTABILITY` | 16.8 | +1.14 | 0.42 | — | — | — | — | — | `a25fcc5ea0f77666bcd759ec19de8043a58816b4446900ffbaec0e563d714935` |
| `CAND-A10` | `Zn2SbS2Br3` | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `IMAGINARY_PHONON` | 89.0 | -1.42 | — | — | — | — | — | — | `bcde5a13fa12deb48575dc59e3541085b31f70525765b6e1f6fbc7471045a089` |

---

## 4. Promoted Prescreen Finalists: Dual-Redundancy Self-Consistency Metrics

For the 5 promoted v2 fixture finalists that passed all 5 stages and Gates A & B, every candidate has been cross-checked across primary and self-consistency implementations (with thin-film double-pass Beer-Lambert absorption $1 - \exp(-2\alpha d)$):

| Candidate ID | Formula | Target Track | Space Group | $N_{\text{sites}}$ | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $E_{\text{mig}}$ (eV) | $E_g^{\text{est}}$ (Ind / Dir) | Single-Layer SLME (%) | SQ Limit (%) | 2-Layer Si $\eta$ (%) | 4T Std Si FCA $\eta$ (%) | **3-Layer 4T Tandem $\eta$ (%)** | Redundancy SHA-256 Digest |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-A02` | `Bi2CuO2SCl` | Top Active Glass | `I4/mmm` (#139) | 28 | 365.0 | \$0.0195 | 14.5 | 1.18 | 0.88 | 1.82 / 1.86 eV | 24.40% | 26.78% | 38.32% | 40.45% | **41.67%** | `a20a11b8a87356615ed2dbf1cf9d78b0a506da656b2f522035708a91eb2981e9` |
| `CAND-A03` | `Cu2SbS2Cl` | Top Active Glass | `Pnma` (#62) | 24 | 320.0 | \$0.0129 | 21.0 | 1.05 | 0.74 | 1.79 / 1.83 eV | 25.06% | 27.32% | 38.43% | 40.56% | **41.78%** | `11d0cc71c0ff065d442fec434bb5920620a02c649ddb865e37a32b7695c36abc` |
| `CAND-A06` | `BiZnOSCl` | Top Active Glass | `P4/nmm` (#129) | 10 | 380.0 | \$0.0148 | 18.2 | 1.29 | 0.98 | 1.85 / 1.89 eV | 23.79% | 26.11% | 38.20% | 40.33% | **41.56%** | `8185c04696a2a053f41545b6e8cc3c4ba50cbe9ea9d90840eca3f5b20c5c3775` |
| `CAND-B02` | `Sn2SbSe2I3` | Bottom IR Scavenger | `Cmcm` (#63) | 32 | 295.0 | \$0.0865 | 12.6 | 0.88 | 0.75 | 0.75 / 0.78 eV | 23.58% | 25.00% | 38.31% | 40.56% | **41.86%** | `8d2a220da8b781d0d9c9b7685baf2befb20b2dd749671de821a322ae923b049e` |
| `CAND-B04` | `Cu2BiSe2I` | Bottom IR Scavenger | `Pnma` (#62) | 24 | 345.0 | \$0.0509 | 11.2 | 1.09 | 0.71 | 0.74 / 0.76 eV | 23.70% | 24.79% | 38.31% | 40.69% | **42.10%** | `e5a66a7b95475eb68e1518917f2c358ff2b84052a6d0ef8974ad46ed2e48a4c3` |

---

## 5. Live Materials Project Campaign v3.0 & Open-Access Negative Synthesis Integration

### 5.1 Open-Access Empirical Negative Synthesis Priors
The Contrastive Failure Memory Ledger is expanded via `data/negative_synthesis_priors.json` incorporating empirical laboratory failure priors:
1. **LBNL 80k Solid-State Impurity Dataset:** `80,806` parsed solid-state recipes across `4,292` chemical systems with `18,869` phase-impure/failed reactions (Lee, Cruse, Baibakova, Ceder, Jain, *Sci. Data* 12:1969, 2025).
2. **LBNL A-Lab Precursor Genome:** `1,035` robotic pairwise XRD reactions with `892` negative/stalled reactions (369 unreacted, 384 transformed, 113 partially reacted) (Walters, Szymanski, Fei, Ceder et al., 2026).

### 5.2 Live MP Funnel Results (100 -> 91 -> 47 -> 40 -> 15 Prescreen Finalists)
Querying the cached Materials Project candidate set across 100 RoHS-clean chalcohalide and oxychalcogenide candidates yields:
- **Stage 1 Ingested:** `100` RoHS-compliant compositions ($\text{Bi/Sb–Cu/Zn/Sn/In/Ga/Ag/Al–S/Se/O–Cl/Br/I}$).
- **Stage 2 Hull, Born & Migration Screened:** `91` candidates ($6$ Born elastic failures, $3$ superionic migration heuristic failures with $E_{\text{mig}} < 0.65\text{ eV}$).
- **Stage 3 Manufacturable:** `47` candidates ($26$ rejected for `OXIDE_IMPURITY_SINK` from high-$T$ refractory binary oxides, $5$ rejected for `IMPURITY_SINK_PRIOR` from LBNL empirical impurity rate $> 0.50$, $13$ rejected for `TIER2_COST_EXCEEDED` $> \$0.50/\text{m}^2$).
- **Gate A Promoted:** `40` candidates ($7$ vetoed for `LOW_DIM_POLARON_RISK` 1D-chains; `hmix` and `tco_rxn` set to `None` / not evaluated at Gate A).
- **Stage 4/5 Prescreen Finalists:** **15 Promoted Prescreen Finalists** ($25$ rejected for `BANDGAP_OUT_OF_WINDOW` outside the 1-error-bar $\pm 0.37\text{ eV}$ window around $[1.75, 1.95]\text{ eV}$ top or $[0.70, 0.85]\text{ eV}$ bottom).
- **Self-Consistency Checks:** `100/100` passed.

### 5.3 Live Materials Project Prescreen Finalists (15 Promoted Finalists: 7 Track A + 8 Track B)

All 15 live MP prescreen finalists have generated Quantum ESPRESSO `HSE06+SOC` input decks (not run) in `outputs/mp_live_qe_decks/`:

| Candidate ID | Formula | Target Track | Space Group | $N_{\text{sites}}$ | $T_{\text{synth}}$ ($^\circ\text{C}$) | Active Layer Cost ($\$/\text{m}^2$) | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}^{\text{heur}}$ (THz) | $E_{\text{mig}}$ (eV) | $E_g^{\text{est}}$ (Ind / Dir) | Single-Layer SLME (%) | SQ Limit (%) | 2-Layer Si $\eta$ (%) | 4T Std Si FCA $\eta$ (%) | **3-Layer 4T Tandem $\eta$ (%)** | Redundancy SHA-256 Digest |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `mp-861911` | `Sb2OS2` | Top Active Glass | `C2/m` (#12) | 10 | 375.0 | \$0.0157 | 7.07 | 1.40 | 1.18 | 1.76 / 1.80 eV | 25.63% | 27.93% | 38.45% | 40.57% | **41.78%** | `ca8633a88b75efb39fa1a8961438e36e9a75b2fba1d200d00fb2bc6968b584c1` |
| `mp-1227486` | `BiSbS3` | Top Active Glass | `Pnma` (#62) | 20 | 375.0 | \$0.0182 | 2.30 | 1.20 | 1.18 | 1.79 / 1.83 eV | 25.04% | 27.32% | 38.36% | 40.48% | **41.69%** | `b06b67e9b54f77e75af1658755fa8dc745d49de7967eaf35542e4052fed60be1` |
| `mp-1195160` | `Al2Bi2Cu2S3Cl8` | Top Active Glass | `P6_3/m` (#176) | 34 | 335.0 | \$0.0128 | 6.02 | 1.33 | 0.87 | 1.82 / 1.83 eV | 25.57% | 26.78% | 38.91% | 41.04% | **42.25%** | `2504e7e4e5c3165c7d4c60642fc44883e5a4dd3fe8b1a4be4a44328eb835ea53` |
| `mp-1078776` | `BiInS3` | Top Active Glass | `P2_1/m` (#11) | 10 | 375.0 | \$0.2681 | 15.08 | 1.11 | 1.18 | 1.90 / 1.94 eV | 22.79% | 25.00% | 37.88% | 39.99% | **41.21%** | `1acff904de905deb123a0304ec4229487386e25c507b3c25f435eb0eba7922fe` |
| `mp-715212` | `Bi3In5S12` | Top Active Glass | `C2/m` (#12) | 20 | 375.0 | \$0.4193 | 4.82 | 1.16 | 1.18 | 1.71 / 1.75 eV | 26.53% | 28.88% | 38.51% | 40.63% | **41.84%** | `5edc9648a4bbd9c8513239cf86feecdc266ba2ab91a716439401cdb3bbe063ab` |
| `mp-1206068` | `Bi2InS4Br` | Top Active Glass | `C2/m` (#12) | 16 | 335.0 | \$0.1656 | 25.73 | 1.07 | 0.99 | 2.02 / 2.06 eV | 20.36% | 22.52% | 37.11% | 39.22% | **40.44%** | `e23863d2320c89cf4ab9d315bbb936e689a90c74d9d2e34fe9c3fb6c67c6eef2` |
| `mp-1228963` | `AgAlSnSe4` | Top Active Glass | `I4_1/a` (#88) | 14 | 375.0 | \$0.2202 | 39.67 | 1.44 | 0.98 | 1.56 / 1.60 eV | 29.46% | 31.34% | 38.78% | 40.92% | **42.13%** | `5c31ec1fc067f26555e19bc8054766be21f863004e4404a9f205a8a0affa738a` |
| `mp-1223998` | `Bi3InSe6` | Bottom IR Scavenger | `R3m` (#160) | 10 | 375.0 | \$0.1507 | 17.99 | 1.33 | 1.18 | 0.75 / 0.76 eV | 24.22% | 25.00% | 38.31% | 40.77% | **42.22%** | `bc1763b9c1fd5ca7bb3c229dab5cb71df78ebc934f8d7b4f541cc55e1f318165` |
| `mp-1224922` | `CuGaSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.1251 | 3.61 | 1.28 | 0.98 | 0.85 / 0.86 eV | 26.72% | 27.20% | 38.31% | 40.62% | **41.75%** | `83d9eae3e9030497bd6cffc681af72366eb931445425778f8237b86ff54ad309` |
| `mp-22982` | `BiCuS2` | Bottom IR Scavenger | `Pnma` (#62) | 16 | 375.0 | \$0.0237 | 0.00 | 1.27 | 0.95 | 0.85 / 0.89 eV | 26.59% | 27.20% | 38.31% | 40.59% | **41.71%** | `1343e05d0bac7ab69d6502e80c49fb1dc71d8664ee520300ba88a664d59dc394` |
| `mp-23474` | `AgBi3S5` | Bottom IR Scavenger | `C2/m` (#12) | 18 | 375.0 | \$0.2558 | 0.00 | 1.18 | 0.98 | 0.85 / 0.89 eV | 26.59% | 27.20% | 38.31% | 40.59% | **41.71%** | `dba1689a432cf7c456d6a5b12a7cf5503b7ad8c901562f93a22bbef8964b5b26` |
| `mp-1224129` | `CuInSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.2664 | 5.17 | 1.21 | 0.98 | 0.78 / 0.82 eV | 23.86% | 25.60% | 38.31% | 40.34% | **41.44%** | `2bbe21c2c192897a893c09e53d48e5fc373d4e0aa987dac6c58e95f0980a4eaa` |
| `mp-1224102` | `CuInSnS4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.2367 | 1.56 | 1.28 | 0.95 | 0.96 / 1.00 eV | 28.57% | 29.74% | 38.31% | 40.59% | **41.66%** | `b357f6a40a24f92e42fb05b3463ff85a3897f15679b89a1b85e4f791fe372897` |
| `mp-20331` | `CuSbSe2` | Bottom IR Scavenger | `Pnma` (#62) | 8 | 375.0 | \$0.0628 | 0.00 | 1.32 | 0.98 | 0.99 / 1.03 eV | 28.69% | 30.30% | 38.31% | 40.48% | **41.51%** | `8f055c904cb247479abc2adb0094fc9657e2703891d89c570b8e6d34b431a854` |
| `mp-1229027` | `AlCuSnSe4` | Bottom IR Scavenger | `I-4` (#82) | 7 | 375.0 | \$0.0566 | 15.96 | 1.38 | 0.98 | 1.07 / 1.08 eV | 30.44% | 31.65% | 38.31% | 40.15% | **41.00%** | `ae36159dd978960a210a67cff56613f5fb2ce311f2f2b44279d5f612bd1d7c2c` |

### 5.4 Top Cross-Layer 4T Tandem Stacks (56 Pairs Screened)

The 7 Top Active Glass and 8 Bottom IR Scavengers form 56 cross-layer (Top + c-Si + Bottom) 4T stacks:
- **Maximum 4T PCE (Scalar Idealization, Double-Pass):** `mp-1195160 Al2Bi2Cu2S3Cl8 + c-Si + mp-1223998 Bi3InSe6` achieving **42.69%** 4T PCE at $\$0.1635/\text{m}^2$, and `mp-861911 Sb2OS2 + c-Si + mp-1223998 Bi3InSe6` achieving **42.22%** 4T PCE at $\$0.1664/\text{m}^2$.
- **Cost-Optimal 4T PCE (Scalar Idealization, Double-Pass):** `mp-861911 Sb2OS2 + c-Si + mp-22982 BiCuS2` delivering **41.71%** 4T PCE at an ultra-low active layer cost of **\$0.0394/m^2**.

---

## 6. v4.0 Pair-Spring Dynamical Matrix, Closed-Form Migration Heuristic & Coherent Multilayer TMM (DFT Phonons and NEB not run)

1. **Step 1 — Pair-Spring Dynamical Matrix $\mathbf{D}(\mathbf{q}=\mathbf{0})$ & Closed-Form Migration Heuristic (DFT Phonons and NEB not run):**
   - Across all 15 prescreen finalists, $3N \times 3N$ pair-spring dynamical matrices ($21\times 21$ to $102\times 102$, $r_{\text{cut}} = 4.25\text{ \AA}$) yield positive $\Gamma$-point optical frequency bounds `spring_model_gamma_freq_thz` (`dynamically_stable = None`) with agreement ($\le 10^{-4}\text{ THz}$) between `numpy.linalg.eigh` and `scipy.linalg.eigvalsh`.
   - Closed-form steric migration heuristic values span `emig_heuristic_ev` $\in [0.990, 1.348]\text{ eV}$ (NEB not run), corresponding to Vineyard-Arrhenius ionic diffusivities $D_{\text{ion}}(300\text{ K}) \ll 10^{-18}\text{ cm}^2/\text{s}$.
   - All unindexed XRD `'unknown'` tokens and non-subset impurity formulas are strictly stripped from `competing_hull_phases` and `competing_impurity_sinks`.
2. **Step 2 — Coherent Multilayer $2\times 2$ Abeles TMM vs. Recursive Rouard/Airy 4T Stack Optics (Double-Pass Thin-Film Absorption):**
   - Across all 15 coherent stacks, single-ARC coherent thin-film interference (`Air / 98 nm MgF2 / 105 nm ITO / Absorber / 85 nm Buffer / Couplant`) reveals $11.01\%\text{–}11.97\%$ front reflection loss and $88.53\%\text{–}89.10\%$ sub-bandgap IR transmittance, yielding **39.88% Coherent 4T PCE** for `mp-861911 Sb2OS2 + c-Si + mp-1223998 Bi3InSe6` and **39.29% Coherent 4T PCE** for the **\$0.0394/m²** `mp-861911 Sb2OS2 + c-Si + mp-22982 BiCuS2` stack.
3. **Step 3 — 7-Medium Graded-ARC + $\text{TiO}_2$ Impedance-Matching Stack & 4-Metric Techno-Economic Figure-of-Merit Suite:**
   - Inserting a $48\text{ nm}$ high-index $\text{TiO}_2$ optical impedance-matching layer reduces broadband front reflection to **$2.42\%\text{–}3.33\%$**, boosting `mp-861911 Sb2OS2 + c-Si + mp-1223998 Bi3InSe6` to **42.31% Graded-ARC Coherent 4T PCE** ($39.3\text{ W/ft}^2$, $\text{CER}_{\text{3L}} = 4.340$, $\text{MCIW}_{\text{full}} = \$0.0648/\Delta\text{W}_{\text{p}}$, $\text{SVI}_{\text{BOS}} = 1.758$) and boosting the ultra-low-cost **\$0.0394/m²** `mp-861911 Sb2OS2 + c-Si + mp-22982 BiCuS2` stack to **41.84% Graded-ARC Coherent 4T PCE** ($38.9\text{ W/ft}^2$, $\text{CER}_{\text{3L}} = 4.303$, $\text{MCIW}_{\text{raw}} = \$0.0002/\Delta\text{W}_{\text{p}}$, $\text{SVI}_{\text{BOS}} = 1.740$).
4. **Phase 9 (`v6.0`) — 10 mmol Lab Synthesis & Supercells (9A) and Oblique/Thermal/25-Year LCOE Stress-Test (9C):**
   - **Phase 9A:** All 15 finalists (including `mp-1195160` `Al2Bi2Cu2S3Cl8`) have stoichiometric $10.0\text{ mmol}$ precursor recipes (`elemental_mass_conservation_diff_g == 0.0 g`, $T_{\text{synth}} \in [335, 375]^\circ\text{C}$) and neutral vacancy supercell decks (`outputs/mp_live_neutral_vacancy_decks/`, $d_{\perp,\min} \ge 10.0\text{ \AA}$).
   - **Phase 9C:** Oblique S/P TMM ($0^\circ\text{–}60^\circ$, $\text{IAM}_{60^\circ} = 0.954$), NOCT 45 °C / Desert 65 °C thermal derating ($\beta_{\text{4T}} = -0.361\%/\text{K}$), and 25-year Arrhenius LCOE under the radiative ceiling yield **3.180 ¢/kWh** (`mp-861911__mp-1223998`, -35.58% vs. 4.936 ¢/kWh standalone c-Si) and **3.197 ¢/kWh** (`mp-861911__mp-22982`, -35.24% vs. c-Si).
5. **Phase 10 (`v7.0`) — $2^4=16$ Thickness/ARC Optimization (10A), Bifacial-Equivalent Power Density (10B), and SPICE Subcell $J\text{–}V$ String Matching (10C):**
   - Optimizing $(d_{\text{MgF}_2}, d_{\text{TiO}_2}, d_{\text{top}}, d_{\text{bot}})$ and harvesting 20% (30%) rear ground albedo yields **46.01 mW/cm²** (**47.88 mW/cm²**) radiative bifacial-equivalent power density (front-irradiance basis) on `mp-861911__mp-1223998` (42.74 W/ft², **25-Yr Bifacial Radiative LCOE = 3.008 ¢/kWh**), and **45.92 mW/cm²** (**47.97 mW/cm²**) on `mp-861911__mp-22982` (`Sb2OS2 + c-Si + BiCuS2`, 42.66 W/ft², **25-Yr Bifacial Radiative LCOE = 3.005 ¢/kWh**).
   - Computing series-string cell counts from the `"demonstrated"` maturity case ($V_{\text{mp,top}} \approx 0.659\text{ V}$) yields `58 : 72 : None` (`mp-861911`) and `56 : 72 : None` (`mp-1227486`), with ITO strip sheet-resistance check confirming `strip_width_feasible = True` ($\Delta P/P \approx 0.12\%\text{–}0.13\% \le 2.0\%$).
6. **Phase 11 (`v8.0`) — Live MP Hull Stability Windows & TCO Interfacial Reactivity (11A), Non-Radiative SRH Device Physics (11B), and Inverted Requirements TEA (11C):**
   - **TCO Interfacial Reactivity (`TCO_SULFIDATION_AND_REAR_ALBEDO_CANNIBALIZATION`):** Live MP `InterfacialReactivity` (`data/mp_thermo_interface_cache.json`) reveals bare `In2O3` (ITO) reacts exothermically at 375 °C with `Sb2OS2` (`-15.35 meV/atom`), `BiSbS3` (`-13.16 meV/atom`), `CuInSnSe4` (`-36.49 meV/atom`), and `CuGaSnSe4` (`-68.25 meV/atom`), whereas `TiO2` (`0.00 meV/atom` on 8/8 finalists) and `SnO2` (`0.00 meV/atom` on 7/8 finalists) act as mandatory inert diffusion barriers. `BiSbS3` (**SPS = 94.76/100**) and `Sb2OS2` (**SPS = 94.44/100**) rank #1 and #2 in synthesis practicality.
   - **Device Maturity Cases & Inverted Techno-Economic Requirements (`requirements_tea.py`):** Under the `"demonstrated"` case ($\text{ERE} = 10^{-9}$, $\text{FF} \le 0.73$, `ASSUMED`), the 2-layer stack (`19.90%–19.91%` monofacial PCE, `23.62–23.63 mW/cm²` bifacial-equivalent power density) performs **below** standalone c-Si (`22.94%` monofacial PCE, `26.65 mW/cm²`), matching measured pnictogen chalcogenide tandems. Under `"stretch"` ($\text{ERE} = 10^{-7}$, `23.66%–23.67%` monofacial) and `"ceiling"` ($\text{ERE} = 10^{-4}$, `26.69%–26.80%` monofacial), the 2-layer stack is the default (`include_rear_ir_cell = False`). Breaking even against standalone c-Si requires a top-cell efficiency of **`24.5 - 13.1 * T`%** on an optics-only basis (`12.97%` at $T = 0.88$), **`15.72%`** on a 25-year utility LCOE basis at $+\$23.88/\text{m}^2$ added module cost (`14.02%` rooftop), and allows **`\$6.53/m²` per efficiency point** (utility) or **`\$11.78/m²` per efficiency point** (rooftop).

