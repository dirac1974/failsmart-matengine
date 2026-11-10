# Contrastive Failure Memory Ledger & Negative-Results Architecture

## 1. Why Negative Results Are First-Class Data

In computational and experimental materials science, over $90\%$ of candidate compounds fail not because of $0\text{ K}$ thermodynamic formation energy, but because of **kinetic impurity traps**, **dynamic phonon collapse**, **0D/1D small-polaron localization**, **halide photo-segregation**, **aqueous leaching**, or **deep Shockley-Read-Hall (SRH) point defects**.

`FailSmart-MatEngine` treats every rejected candidate as a **labeled physical boundary condition** inside `data/failure_memory.db` (`ContrastiveFailureLedger`).

---

## 2. Physical Taxonomy of Failure Modes

| Failure Code | Stage Caught | Physical Mechanism | Representative Compound |
| :--- | :--- | :--- | :--- |
| `IMAGINARY_PHONON` | Stage 2 | Harmonic phonon mode $\omega_{\min} < 0\text{ THz}$; crystal spontaneously distorts/shears at $T > 0\text{ K}$. | $\text{Zn}_2\text{SbS}_2\text{Br}$ ($\omega_{\min} = -1.42\text{ THz}$) |
| `HULL_INSTABILITY` | Stage 2 | $\Delta E_{\text{hull}} > 50\text{ meV/atom}$ and not vibrationally stabilized; phase separates into binaries. | $\text{Sr}_2\text{ZnS}_2\text{O}$ ($\Delta E_{\text{hull}} = 64.0\text{ meV/atom}$) |
| `OXIDE_IMPURITY_SINK` | Stage 3 | Refractory binary/oxide sink ($\text{ZrO}_2$, $\text{BaSO}_4$) consumes precursors unless $T > 500^\circ\text{C}$ (melts soda-lime glass). | $\text{BaZrS}_3$ ($T_{\text{synth}} = 950^\circ\text{C}$) |
| `AQUEOUS_LEACHING` | Stage 3 | Pourbaix diagram ($\text{pH } 4\text{–}9$) shows soluble metal-halide leaching $> 10^{-6}\text{ mol/L}$ in rainwater. | $\text{Pb}_2\text{BiS}_2\text{I}_3$ ($2.8\times 10^{-3}\text{ mol/L}$) |
| `TIER2_COST_EXCEEDED` | Stage 3 | Scarce Tier-2 element ($\text{Ag, In, Te, Ga}$) pushes active-layer material cost above $\$0.50/\text{m}^2$. | $\text{AgBiSe}_2$ ($\$0.58/\text{m}^2$) |
| `LOW_DIM_POLARON_RISK` | Gate A | 0D isolated polyhedra or 1D van der Waals chains trap carriers in self-induced lattice distortions. | $\text{Cs}_3\text{Bi}_2\text{I}_9$, $\text{BiSCl}$, $\text{SbSeI}$ |
| `ANION_PHASE_SEGREGATION` | Gate A | High configurational anion-mixing enthalpy ($\Delta H_{\text{mix}} \ge 35\text{ meV/atom}$) causes light-induced halide unmixing. | $\text{BiCuSeI}$ ($\Delta H_{\text{mix}} = 48.5\text{ meV/atom}$) |
| `BANDGAP_OUT_OF_WINDOW` | Stage 4 | Relativistic `HSE06+SOC` spin-orbit splitting shifts fundamental gap outside target spectral window. | $\text{BiCuOS}$ ($1.18\text{ eV}$), $\text{BaBiO}_2\text{Cl}$ ($2.94\text{ eV}$) |
| `DEEP_SRH_DEFECT` | Stage 5 | Intrinsic vacancy or antisite defect creates a mid-gap trap $> 0.15\text{ eV}$ from band edges, killing $V_{oc}$. | $\text{Bi}_2\text{SnSe}_3\text{I}_2$ ($\text{I}_{\text{Se}}$ trap at $0.36\text{ eV}$) |

---

## 3. Complete Contrastive Failure Memory Ledger (Pilot Campaign #1 + Seed Archetypes)

| ID | Formula | Target Track | Stage | Status | Primary Failure Mode / Outcome | $\Delta E_{\text{hull}}$ (meV) | $\omega_{\min}$ (THz) | $T_{\text{synth}}$ ($^\circ\text{C}$) | $E_g^{\text{HSE06+SOC}}$ (eV) | 4T Stack $\eta$ (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CAND-A06` | **$\text{BiZnSOCl}$** | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & 2 Red-Team gates | $18.2$ | $+1.29$ | $380$ | $1.85$ ($1.89$ dir) | **$44.17\%$** |
| `CAND-B04` | **$\text{Cu}_2\text{BiSe}_2\text{I}$** | Bottom ($0.75\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & 2 Red-Team gates | $11.2$ | $+1.09$ | $345$ | $0.74$ ($0.76$ dir) | **$44.16\%$** |
| `CAND-B02` | **$\text{Sn}_2\text{SbSe}_2\text{I}_3$** | Bottom ($0.75\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & 2 Red-Team gates | $12.6$ | $+0.88$ | $295$ | $0.75$ ($0.78$ dir) | **$44.11\%$** |
| `CAND-A02` | **$\text{Bi}_2\text{CuO}_2\text{SCl}$** | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & 2 Red-Team gates | $14.5$ | $+1.18$ | $365$ | $1.82$ ($1.86$ dir) | **$43.90\%$** |
| `CAND-A03` | **$\text{SbCuS}_2\text{Cl}$** | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & 2 Red-Team gates | $21.0$ | $+1.05$ | $320$ | $1.79$ ($1.83$ dir) | **$43.61\%$** |
| `CAND-A09` | **$\text{Cu}_3\text{BiS}_2\text{Cl}_2$** | Top ($1.85\text{ eV}$) | 5 | **PROMOTED** | Passed all 5 stages & 2 Red-Team gates | $16.8$ | $+1.14$ | $350$ | $1.76$ ($1.79$ dir) | **$43.57\%$** |
| `CAND-A01` | $\text{BiCuOS}$ | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` ($1.18\text{ eV}$ indirect) | $0.0$ | $+1.62$ | $340$ | $1.18$ ($1.52$ dir) | — |
| `CAND-A04` | $\text{BaBiO}_2\text{Cl}$ | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `BANDGAP_OUT_OF_WINDOW` ($2.94\text{ eV}$) + $V_{\text{O}}$ trap | $4.2$ | $+1.38$ | $440$ | $2.94$ ($3.12$ dir) | — |
| `CAND-B03` | $\text{Bi}_2\text{SnSe}_3\text{I}_2$ | Bottom ($0.75\text{ eV}$) | 5 | `REJECTED` | `DEEP_SRH_DEFECT` ($\text{I}_{\text{Se}}$ antisite at $0.36\text{ eV}$) | $15.1$ | $+0.91$ | $330$ | $0.77$ ($0.81$ dir) | — |
| `CAND-A08` | $\text{BiSCl}$ | Top ($1.85\text{ eV}$) | Gate A | `REJECTED` | `LOW_DIM_POLARON_RISK` (1D chain + $\text{BiCl}_3$ volatility) | $2.5$ | $+0.74$ | $290$ | — | — |
| `CAND-B06` | $\text{SbSeI}$ | Bottom ($0.75\text{ eV}$) | Gate A | `REJECTED` | `LOW_DIM_POLARON_RISK` (1D chain anisotropy) | $3.8$ | $+0.68$ | $275$ | — | — |
| `CAND-B01` | $\text{BiCuSeI}$ | Bottom ($0.75\text{ eV}$) | Gate A | `REJECTED` | `ANION_PHASE_SEGREGATION` ($\Delta H_{\text{mix}} = 48.5\text{ meV}$) | $19.4$ | $+0.94$ | $310$ | — | — |
| `CAND-A07` | $\text{BaZrS}_3$ | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` ($\text{ZrO}_2$ sink needs $950^\circ\text{C}$) | $0.0$ | $+1.48$ | $950$ | — | — |
| `CAND-B05` | $\text{AgBiSe}_2$ | Bottom ($0.75\text{ eV}$) | 3 | `REJECTED` | `TIER2_COST_EXCEEDED` ($\$0.58/\text{m}^2 > \$0.50/\text{m}^2$) | $0.0$ | $+1.15$ | $360$ | — | — |
| `CAND-A05` | $\text{Sr}_2\text{ZnS}_2\text{O}$ | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `HULL_INSTABILITY` ($\Delta E_{\text{hull}} = 64.0\text{ meV/atom}$) | $64.0$ | $+0.92$ | — | — | — |
| `CAND-A10` | $\text{Zn}_2\text{SbS}_2\text{Br}$ | Top ($1.85\text{ eV}$) | 2 | `REJECTED` | `IMAGINARY_PHONON` ($\omega_{\min} = -1.42\text{ THz}$) | $89.0$ | $-1.42$ | — | — | — |
| `LIT-FAIL-001` | $\text{BaZrS}_3$ (Seed) | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `OXIDE_IMPURITY_SINK` (LBNL 80k Impurity Dataset) | $0.0$ | $+1.45$ | $950$ | $1.82$ | — |
| `LIT-FAIL-002` | $\text{Cs}_3\text{Bi}_2\text{I}_9$ (Seed) | Top ($1.85\text{ eV}$) | 4 | `REJECTED` | `SMALL_POLARON_TRAP` ($m_h^* = 2.45\,m_0, \alpha_F = 7.8$) | $8.0$ | $+0.65$ | $180$ | $2.04$ | — |
| `LIT-FAIL-003` | $\text{Pb}_2\text{BiS}_2\text{I}_3$ (Seed) | Top ($1.85\text{ eV}$) | 3 | `REJECTED` | `AQUEOUS_LEACHING` ($\text{PbI}_2$ sublattice dissolution) | $19.0$ | $+0.82$ | $340$ | $1.71$ | — |
