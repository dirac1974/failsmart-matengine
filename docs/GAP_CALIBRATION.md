# Band-Gap Surrogate Calibration and Literature Gate (`T4`)

**Provenance notice:** This document reports the empirical calibration of the repository's closed-form PBE-to-fundamental band-gap heuristic (`_estimate_gap_from_mp_pbe` in [`mp_live_discovery.py`](../failsmart_matengine/mp_live_discovery.py)) against **50 Materials Project semiconductors** with opened primary/review experimental optical band-gap sources (`data/gap_benchmark.csv`), together with the literature audit of all promoted Materials Project finalists (`data/finalist_literature.json`). Every reported quantity carries an explicit provenance tag (`MP_DFT`, `LITERATURE`, `COMPUTED_HERE`, `HEURISTIC`, or `ASSUMED`).

---

## 1. Literature Gate on Promoted Materials Project Finalists (`data/finalist_literature.json`)

The eight original Materials Project finalists (`v3`–`v8`) plus `mp-1195160` (`Al2Bi2Cu2S3Cl8`, promoted after `T6`) were checked against Materials Project crystal-structure metadata (`MP_DFT`) and opened experimental literature sources (`LITERATURE`). Where a quantity was not verified in an opened primary or review source, it is stored as `null` ("not evaluated") and listed in `unresolved_fields`.

| MP ID | Formula | MP Space Group (Sites) | MP `theoretical` (`MP_DFT`) | ICSD IDs (`MP_DFT`) | Synthesised Phase Match? (`LITERATURE`) | MP PBE Gap (`MP_DFT`, eV) | Heuristic Gap Est. (`HEURISTIC`, eV) | Measured Optical Gap (`LITERATURE`, eV) | Reported PV Device (`LITERATURE`) | Primary Source / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mp-861911` | `Sb2OS2` | `C2/m` (10) | `True` | none | **No** (`C2/m` is an un-synthesised polymorph; mineral kermesite is triclinic `P-1`, `mp-28711`, 20 sites, `icsd-12120`, bulk gap `2.04 eV`) | `1.21` | `1.76 +/- 0.37` (refit `2.13`) | `null` (`2.04` for `P-1` `mp-28711`) | `null` | `10.48550/arXiv.2602.08622`; Mindat min-2187 |
| `mp-1227486` | `BiSbS3` | `Pnma` (20) | `True` | none | **No** (theoretical site-ordered 1:1 `Pnma` cell; experiment forms disordered `(Bi,Sb)2S3` solid solution between `Bi2S3` `1.32 eV` and `Sb2S3` `1.70 eV`) | `1.35` | `1.79 +/- 0.37` (refit `1.96`) | `null` | `null` | `10.3390/nano12020198`; `10.1007/s40820-022-00822-8` |
| `mp-1078776` | `BiInS3` | `P2_1/m` (10) | `True` | `icsd-290195` | `null` (linked to `icsd-290195` in MP metadata but flagged `theoretical=True`; primary crystal paper not open-access) | `1.40` | `1.90 +/- 0.37` (refit `2.13`) | `null` | `null` | Unresolved in opened sources |
| `mp-1223998` | `Bi3InSe6` | `R3m` (10) | `True` | none | **No** (theoretical `R3m` substitution structure) | `0.52` | `0.75 +/- 0.37` (refit `0.68`) | `null` | `null` | Un-synthesised theoretical entry |
| `mp-1224922` | `CuGaSnSe4` | `I-4` (7) | `True` | none | **No** (ordered defect-chalcopyrite cell with no ICSD entry) | `0.42` | `0.85 +/- 0.37` (refit `1.15`) | `null` | `null` | Unresolved in opened sources |
| `mp-22982` | `CuBiS2` | `Pnma` (16) | `False` | `icsd-85134`, `34936`, `38779`, `171052` | **Yes** (orthorhombic `Pnma` emplectite) | `0.47` | `0.85 +/- 0.37` (refit `1.09`) | **`1.65`** (lit. range `1.50`–`1.65`) | `null` | Temple et al., *Phys. Chem. Chem. Phys.* 2012 (`10.1039/c2cp40916j`): measured gap is `1.65 eV`, transparent to the `0.70`–`0.85 eV` IR window |
| `mp-23474` | `AgBi3S5` | `C2/m` (18) | `False` | `icsd-200110`, `171229` | **Yes** (monoclinic `C2/m` pavonite on the `Ag2S`–`Bi2S3` tie-line) | `0.53` | `0.85 +/- 0.37` (refit `0.97`) | `null` | `null` | Phase confirmed in `10.3390/mi14122211` (`PMC10746013`); optical gap unresolved in opened full texts |
| `mp-1224129` | `CuInSnSe4` | `I-4` (7) | `True` | none | **No** (ordered defect-chalcopyrite cell with no ICSD entry) | `0.36` | `0.78 +/- 0.37` (refit `1.08`) | `null` | `null` | Unresolved in opened sources |
| `mp-1195160` | `Al2Bi2Cu2S3Cl8` | `P6_3/m` (34) | `False` | `icsd-428727` | **Yes** (hexagonal `P6_3/m` `CuBiSCl2(AlCl3)`) | `1.27` | `1.82 +/- 0.37` (refit `2.18`) | `null` (explicitly listed as unmeasured `-`) | `null` | *Adv. Sci.* 2025 (`10.1002/advs.202413131`, `PMC12097054` Table 1: Theory `1.27 eV`, Exp. `-`) |

---

## 2. Benchmark Set (`data/gap_benchmark.csv`)

`data/gap_benchmark.csv` contains **50 Materials Project-matched compounds** (`mp_status = matched`, exceeding the $\ge 40$ requirement) plus **`BiCuOS`** (`mp_status = not_in_mp`, included because it is named in `REMEDIATION_TASKS.md` Step 2 from the synthetic v2 pilot `CAND-A01`, whereas live Materials Project has zero `BiCuOS` entries and only metallic `Cu2BiSO2` `mp-1206303`; its isostructural `P4/nmm` oxyselenide `BiCuSeO` `mp-23116` is included as row 20).

The 50 MP-matched compounds span:
- **Binary pnictogen chalcogenides ($n = 4$):** `Sb2S3` (`mp-2809`, `1.70 eV`), `Sb2Se3` (`mp-2160`, `1.18 eV`), `Bi2S3` (`mp-22856`, `1.32 eV`), `Bi2Se3` (`mp-541837`, `0.30 eV`).
- **IV–VI monochalcogenides ($n = 5$):** `SnS` (`mp-2231`, `1.28 eV`), `GeS` (`mp-2242`, `1.60 eV`), `PbS` (`mp-21276`, `0.41 eV`), `PbSe` (`mp-2201`, `0.28 eV`), `PbTe` (`mp-19717`, `0.31 eV`).
- **Cu/Ag pnictogen chalcogenides ($n = 4$):** `CuSbS2` (`mp-4468`, `1.52 eV`), `CuSbSe2` (`mp-20331`, `1.10 eV`), `CuBiS2` (`mp-22982`, `1.65 eV`), `AgBiS2` (`mp-29678`, `0.98 eV`).
- **Chalcopyrites and kesterites ($n = 9$):** `CuInSe2` (`mp-22811`, `1.04 eV`), `CuGaSe2` (`mp-4840`, `1.66 eV`), `CuInS2` (`mp-22736`, `1.55 eV`), `AgInS2` (`mp-19833`, `1.87 eV`), `AgInSe2` (`mp-20554`, `1.24 eV`), `AgGaS2` (`mp-5342`, `2.65 eV`), `AgGaSe2` (`mp-5518`, `1.80 eV`), `Cu2ZnSnS4` (`mp-1079541`, `1.50 eV`), `Cu2ZnSnSe4` (`mp-1078918`, `1.00 eV`).
- **Alkali thiogallates and thiogermanates ($n = 3$):** `LiGaS2` (`mp-3647`, `3.70 eV`), `Na2ZnGe2S6` (`mp-1190399`, `3.20 eV`), `Na2Ga2GeS6` (`mp-1190388`, `3.10 eV`).
- **II–VI chalcogenides ($n = 6$):** `CdTe` (`mp-406`, `1.50 eV`), `ZnS` (`mp-10695`, `3.60 eV`), `CdS` (`mp-672`, `2.42 eV`), `CdSe` (`mp-1070`, `1.73 eV`), `ZnSe` (`mp-1190`, `2.82 eV`), `ZnTe` (`mp-2176`, `2.25 eV`).
- **Oxyhalides and oxychalcogenides ($n = 5$):** `BiOI` (`mp-22987`, `1.80 eV`), `BiOCl` (`mp-22939`, `3.30 eV`), `BiOBr` (`mp-23072`, `2.70 eV`), `BiCuSeO` (`mp-23116`, `0.80 eV`), `Sb2S2O` (`mp-28711`, `2.04 eV`).
- **Pnictogen and coinage-metal chalcohalides ($n = 12$):** `BiSI` (`mp-23514`, `1.67 eV`), `SbSI` (`mp-23041`, `2.05 eV`), `BiSeI` (`mp-23020`, `1.29 eV`), `BiSBr` (`mp-23324`, `1.71 eV`), `SbSeI` (`mp-22996`, `1.74 eV`), `BiTeI` (`mp-22965`, `0.33 eV`), `Ag3SI` (`mp-22995`, `0.88 eV`), `Ag3SBr` (`mp-1105645`, `0.97 eV`), `Pb2SbS2I3` (`mp-578882`, `2.19 eV`), `Sn2SbS2I3` (`mp-561134`, `1.50 eV`), `CuBiSCl2` (`mp-554238`, `1.44 eV`), `AgBiSCl2` (`mp-556094`, `1.27 eV`).
- **Chalcogenide perovskites ($n = 2$):** `BaZrS3` (`mp-540771`, `1.78 eV`), `BaTiS3` (`mp-7073`, `0.20 eV`).

---

## 3. Existing Heuristic Error (`Step 3`)

The existing estimator in `_estimate_gap_from_mp_pbe` computes (`HEURISTIC`):

$$\hat{E}_{g,\text{old}} = \max\!\left(0.45,\; \text{round}\!\left(E_{\text{PBE}} + 0.31 + \frac{3.30}{\max(4.5, \varepsilon_\infty)},\; 2\right) - \Delta_{\text{SOC}}\right)$$

where $\Delta_{\text{SOC}} = 0.03 + 0.72 f_{\text{Bi,Pb}} + 0.42 f_{\text{I,Te}} + 0.20 (f_{\text{Sb,Sn}} + f_{\text{Br,Se}})$ and $\varepsilon_\infty = \text{clip}(12.2 - 2.6 E_{\text{PBE}} - 1.8 f_{\text{O}} + 2.2 (f_{\text{Bi,Pb}} + f_{\text{Sb,Sn}}), 4.8, 15.5)$.

Evaluated across the $n = 50$ MP-matched benchmark compounds (`COMPUTED_HERE`):

| Subset | Count ($n$) | Mean Absolute Error (MAE, eV) | Mean Bias ($\hat{E}_g - E_{\text{exp}}$, eV) | Root-Mean-Square Error (RMSE, eV) |
| :--- | :---: | :---: | :---: | :---: |
| **All MP-matched benchmark compounds** | `50` | **`0.4522`** | **`-0.1906`** | **`0.5651`** |
| **Contains `Cu` or `Ag`** ($d^{10}$ $p$–$d$ repulsion) | `18` | **`0.5839`** | **`-0.5350`** | **`0.6930`** |
| **No `Cu` or `Ag`** | `32` | **`0.3781`** | **`+0.0031`** | **`0.4783`** |

**Physical cause of the `Cu`/`Ag` failure:** Semi-local GGA-PBE places the filled $\text{Cu } 3d^{10}$ and $\text{Ag } 4d^{10}$ shells too shallow in energy, over-hybridizing them with the anion $p$ valence band and severely underestimating the PBE gap (often by $0.8$–$1.2\text{ eV}$). Adding only $+0.31 + 3.30/\varepsilon_\infty \approx +0.55\text{ eV}$ leaves a systematic **$-0.535\text{ eV}$** negative bias on `Cu`/`Ag` compounds (`CuBiS2`: PBE `0.47 eV`, heuristic `0.85 eV`, measured `1.65 eV`).

---

## 4. Cross-Validated Refit and Comparison with Published Correction (`Step 4`)

We refit the three linear coefficients $(c_0, c_1, c_2)$ of the model

$$\hat{E}_g = \max\!\left(0,\; E_{\text{PBE}} + c_0 + \frac{c_1}{\max(4.5, \varepsilon_\infty)} - c_2\,\Delta_{\text{SOC}}\right)$$

using non-negative least squares ($c_0, c_1, c_2 \ge 0$ so dielectric screening opening and spin-orbit narrowing retain their physical signs) as well as unconstrained ordinary least squares (OLS), and compare against the published Morales-García et al. (*J. Phys. Chem. C* 2017, DOI: `10.1021/acs.jpcc.7b07421`) PBE-to-HSE06 linear relation $E_{\text{HSE06}} = 1.138\,E_{\text{PBE}} + 0.653\text{ eV}$ (`COMPUTED_HERE`):

| Model / Validation Protocol | Fitted Coefficients $(c_0, c_1, c_2)$ | Overall MAE (eV) | Overall Bias (eV) | Overall RMSE (eV) | `Cu`/`Ag` MAE (eV) | No-`Cu`/`Ag` MAE (eV) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Existing heuristic (`Step 3`)** | `(0.3100, 3.3000, 1.0000)` | `0.4522` | `-0.1906` | `0.5651` | `0.5839` | `0.3781` |
| **Refitted 3-coeff (non-neg OLS, LOOCV)** | `(1.2093, 0.3763, 2.9709)` | **`0.3684`** | `+0.0021` | **`0.4362`** | `0.3671` | `0.3691` |
| **Refitted 3-coeff (unconstrained OLS, LOOCV)** | `(1.5445, -2.8257, 2.9765)` | **`0.3623`** | `+0.0025` | `0.4366` | `0.3646` | `0.3610` |
| **Refitted 3-coeff (non-neg OLS, 5-fold stratified CV)** | `(1.2093, 0.3763, 2.9709)` | **`0.3654`** | `+0.0018` | `0.4369` | `0.3650` | `0.3656` |
| **Refitted 3-coeff (non-neg OLS, leave-one-family-out CV)** | per-fold | `0.4187` | $+0.0094$ | `0.4887` | `0.4312` | `0.4117` |
| **Morales-García 2017 (`1.138*E_PBE + 0.653`)** | published (`10.1021/acs.jpcc.7b07421`) | `0.5486` | $+0.4328$ | `0.6644` | `0.3418` | `0.6649` |
| **Morales-García 2017 minus $\Delta_{\text{SOC}}$** | published + SOC | `0.4525` | $+0.2421$ | `0.5538` | `0.2966` | `0.5402` |

- Under **Leave-One-Out Cross-Validation (LOOCV)** and **5-fold cross-validation**, the refitted 3-coefficient model achieves **$\text{MAE}_{\text{CV}} = 0.368\text{ eV}$** ($\le 0.40\text{ eV}$ stopping threshold on the Step 3 MAE metric), while **$\text{RMSE}_{\text{CV}} = 0.436\text{ eV}$** and **leave-one-chemical-family-out MAE $= 0.419\text{ eV}$** remain above $0.40\text{ eV}$.
- Because even a $\pm 0.37\text{ eV}$ MAE ($\pm 0.44\text{ eV}$ RMSE) is wider than the $0.20\text{ eV}$ top-cell window ($1.75$–$1.95\text{ eV}$) and $0.15\text{ eV}$ bottom-cell window ($0.70$–$0.85\text{ eV}$), **point-estimate rankings within those narrow windows have low statistical resolution** until first-principles hybrid+SOC calculations (`T7`) are run.

---

## 5. Probabilistic Window Gate (`Step 5`)

In `mp_live_discovery.py` (`Stage 4`), the hard window gate (`1.75 <= eg <= 1.95` or `0.70 <= eg <= 0.85`) is replaced with a **probabilistic 1-error-bar gate** using $\sigma_{\text{gap}} = 0.37\text{ eV}$ (`LOOCV MAE = 0.3684 eV`):

1. **Gate rule (`COMPUTED_HERE`):** Keep a candidate at Stage 4 if the target window $[w_{\text{lo}}, w_{\text{hi}}]$ lies within one error bar $\sigma_{\text{gap}} = 0.37\text{ eV}$ of the estimated gap $\hat{E}_g$:
   $$w_{\text{lo}} - \sigma_{\text{gap}} \le \hat{E}_g \le w_{\text{hi}} + \sigma_{\text{gap}}$$
   i.e., $[1.38, 2.32]\text{ eV}$ for `TOP_ACTIVE_GLASS_185EV` ($[1.75, 1.95]\text{ eV}$) and $[0.33, 1.22]\text{ eV}$ for `BOTTOM_IR_075EV` ($[0.70, 0.85]\text{ eV}$).
2. **Window probability (`COMPUTED_HERE`):** Every `ElectronicDefectReport` records `gap_error_bar_ev = 0.37` and `window_probability`:
   $$P_{\text{win}} = \Phi\!\left(\frac{w_{\text{hi}} - \hat{E}_g}{\sigma_{\text{gap}}}\right) - \Phi\!\left(\frac{w_{\text{lo}} - \hat{E}_g}{\sigma_{\text{gap}}}\right)$$
   Under $\sigma_{\text{gap}} = 0.37\text{ eV}$, even a candidate centered in the middle of the $0.20\text{ eV}$ top window ($\hat{E}_g = 1.85\text{ eV}$) has $P_{\text{win}} = 21.4\%$, and a candidate centered in the $0.15\text{ eV}$ bottom window ($\hat{E}_g = 0.775\text{ eV}$) has $P_{\text{win}} = 16.1\%$.
3. **Impact on Funnel Counts:** Widening the Stage 4 band-gap gate to one error bar ($\pm 0.37\text{ eV}$) increases the number of Stage 4+5 promoted prescreen finalists from **9 to 15** (`7` Top Active Glass: `mp-861911` `Sb2OS2`, `mp-1227486` `BiSbS3`, `mp-1195160` `Al2Bi2Cu2S3Cl8`, `mp-1078776` `BiInS3`, `mp-1228963` `AgAlSnSe4`, `mp-1206068` `Bi2InS4Br`, `mp-715212` `Bi3In5S12`; `8` Bottom IR: `mp-1223998` `Bi3InSe6`, `mp-1224129` `CuInSnSe4`, `mp-1224922` `CuGaSnSe4`, `mp-22982` `BiCuS2`, `mp-23474` `AgBi3S5`, `mp-1229027` `AlCuSnSe4`, `mp-1224102` `CuInSnS4`, `mp-20331` `CuSbSe2`), producing $7 \times 8 = 56$ cross-layer pairs (`100 -> 91 -> 47 -> 40 -> 15`).
