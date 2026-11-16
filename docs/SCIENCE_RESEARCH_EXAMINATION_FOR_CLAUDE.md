# FailSmart-MatEngine: Full `/science` Research Examination & Audit Report for Claude Fable

**Prepared by:** Antigravity Research & Engineering Team (with 3 independent audit subagents)  
**Literature Skills Used:** `literature-search-openalex` (OpenAlex CLI) and `literature-search-arxiv` (arXiv API CLI)  
**Target Repository:** `failsmart-matengine` (`v8.0` / `460f3dc`)

> [!IMPORTANT]
> **Executive Summary:** `failsmart-matengine` implements a well-structured, deterministic Tier-0 analytical/surrogate discovery pipeline with an impressive dual-algorithm verification architecture (`independent_verifier.py` vs. primary modules) and a realistic strategic pivot in v8.0 (`Path 4` BIPV $\rightarrow$ `Path 2` 2-Layer Active Solar Glass on unobstructed bifacial c-Si). However, our `/science` literature examination and 3-subagent code/math audit uncovered **6 concrete mathematical/code bugs**, **4 major peer-review scientific vulnerabilities**, **broken packaging (`pyproject.toml`)**, **hardcoded `/home/antigravity/` Linux paths that fail on Windows**, and **several unimplemented plan items** (notably **Gate B** and **active-learning `UNCERTAIN_DFT_QUEUE` branching**).

---

## 1. Peer-Reviewed Literature & Preprint Cross-Examination (`/science` Skills)

All literature queries were executed using the installed `literature-search-openalex` and `literature-search-arxiv` skills. Every URL/DOI below was retrieved directly during this examination.

### 1.1 Non-Radiative Voltage Loss ($\text{ERE}$) & Defect Chemistry in Pnictogen Chalcogenides/Chalcohalides

1. **Record $\text{Sb}_2\text{S}_3$ $V_{\text{oc}}$ vs. `failsmart-matengine` Phase 11B `ERE` Tiers:**
   - **Literature Evidence:**
     - Wang, Kavanagh & Walsh (2024/2025), *"Sulfur Vacancies Limit the Open-circuit Voltage of Sb2S3 Solar Cells"*, *ACS Energy Lett.* (`arXiv:2410.10560v1`, `https://arxiv.org/pdf/2410.10560v1`, DOI: `https://doi.org/10.1021/acsenergylett.4c02722`) shows that sulfur vacancies ($V_{\text{S}}$) act as effective non-radiative recombination centers with high equilibrium concentrations regardless of growth conditions, capping $\text{Sb}_2\text{S}_3$ efficiency at $\sim 16\%$.
     - Zhou, Wang, Shi, Wan, Ye, Li, Walsh, Hoye & Zhou (2025/2026), *"Breaking the 800 mV open-circuit voltage barrier in antimony sulfide photovoltaics"*, *Nature Communications* (`arXiv:2512.18100v1`, `https://arxiv.org/pdf/2512.18100v1`, DOI: `https://doi.org/10.1038/s41467-026-76845-1`) reports the **world-record** $\text{Sb}_2\text{S}_3$ open-circuit voltage of **`824 mV`** by reducing grain boundary density from $1114 \pm 52\text{ nm}/\mu\text{m}^2$ to $585 \pm 10\text{ nm}/\mu\text{m}^2$ and suppressing deep traps ($0.4\text{–}0.7\text{ eV}$ above VBM, attributed to $V_{\text{S}}$ or $\text{Sb}_{\text{S}}$ antisites).
     - López, Kavanagh, Benítez, Saucedo, Walsh, Scanlon & Cazorla (Dec 2025), *"Defect-Limited Efficiency of Pnictogen Chalcohalide Solar Cells"* (`arXiv:2512.01531v1`, `https://arxiv.org/pdf/2512.01531v1`) confirms that Bi-based chalcohalide solar cells remain below $10\%$ PCE due to low-formation-energy chalcogen vacancies acting as deep non-radiative recombination centers.
     - Review: *"Open-Circuit Voltage Loss of Antimony Chalcogenide Solar Cells: Status, Origin, and Possible Solutions"* (2020, `https://doi.org/10.1021/acsenergylett.0c00940`, 255 citations).
   - **Audit Finding:** `failsmart-matengine` (`realistic_commercialization.py:390–409`, `docs/REALISTIC_COMMERCIALIZATION_AND_DEBATE_REPORT.md:36`) models "Base-Case Engineered Pilot Module" at $\text{ERE} = 10^{-4}$ ($\Delta V_{\text{oc,non-rad}} \approx 0.238\text{ V}$), predicting $V_{\text{oc,real}} = 1.222\text{–}1.248\text{ V}$ for `Sb2OS2` and `BiSbS3` ($E_g \approx 1.76\text{–}1.79\text{ eV}$), and even `1.10–1.19 V` at "Conservative" $\text{ERE} = 10^{-5}$. Because the real-world $\text{Sb}_2\text{S}_3$ record is `0.824 V` ($\Delta V_{\text{oc,non-rad}} \approx 0.55\text{–}0.65\text{ V}$, corresponding to $\text{ERE} \sim 10^{-11}\text{–}10^{-9}$), **an additional $\text{ERE} = 10^{-8}$ "Current Experimental Baseline" tier is needed** so reviewers do not dismiss $\text{ERE} = 10^{-5}$ as an uncalibrated floor.

2. **Facet-Dependent Surface Dipoles ($0.8\text{ eV}$ Band-Edge Shifts) vs. Scalar Mulliken Band Edges:**
   - **Literature Evidence:**
     - López, Rovira, Jiménez-Arguijo, Jehl, Saucedo & Cazorla (Oct 2026), *"Surface Physics of Low-Dimensional Pnictogen Chalcohalides and Its Impact on Photovoltaic Technologies"* (`arXiv:2610.10136v1`, `https://arxiv.org/pdf/2610.10136v1`) demonstrates that `(011)` and `(010)` terminations in low-dimensional pnictogen chalcohalides differ in formation energy by only $0.01\text{–}0.03\text{ J/m}^2$ yet exhibit rigid band-edge shifts of **up to $0.8\text{ eV}$**, causing up to a **$0.6\text{ V}$ $V_{\text{oc}}$ collapse** in drift-diffusion simulations even in defect-free absorbers.
   - **Audit Finding:** `realistic_commercialization.py:101–118` computes $E_{\text{CBM}}, E_{\text{VBM}}$ solely from bulk geometric-mean Mulliken electronegativity plus a linear lone-pair shift `1.65 * (Bi + Sb) / N_tot`, omitting facet-dependent surface dipoles and `[hk1]` vs. `[hk0]` grain-orientation band-offset variance.

### 1.2 Experimental Maturity of Lead Finalists (`BiSbS3`, `Sb2OS2`, `BiCuS2`, `AgBi3S5`, `Sn2SbSe2I3`)

- **`BiSbS3`:** OpenAlex (`46` works) shows `BiSbS3` has been studied primarily in photoelectrochemical water splitting (`https://doi.org/10.1016/j.seta.2021.101775`, `https://doi.org/10.1021/acs.chemmater.6b04266`) and sodium storage (`https://doi.org/10.1021/acsnano.3c02138`), **not** validated thin-film PV modules.
- **`Sb2OS2` (Kermesite):** OpenAlex (`3` works for `Sb2OS2`, e.g., W-doped `Sb2OS2` for $\text{N}_2$ photoreduction `https://doi.org/10.1021/acsami.4c16630`) shows essentially **zero** thin-film PV device literature to date.
- **`AgBi3S5` & `CuBiS2`:** `AgBi3S5` is primarily a thermoelectric (`https://doi.org/10.1021/jacs.7b02399`, 214 citations; `https://doi.org/10.1021/cm0502931`), while `CuBiS2` / `CuSbS2` was proposed for thin-film PV (`https://doi.org/10.1039/c2cp40916j`, 168 citations).
- **Quaternary $M(\text{II})_2 M(\text{III}) \text{Ch}_2 X_3$ (including `Sn2SbSe2I3`):** Henkel, Li & Rinke (2025), *"Design Rules for Optimizing Quaternary Mixed-Metal Chalcohalides"*, *Phys. Rev. Materials* 9, 115405 (`arXiv:2505.19882v2`, `https://arxiv.org/pdf/2505.19882v2`, DOI: `https://doi.org/10.1103/qjwt-29w9`) confirms that `P21/c` is often the low-$T$ equilibrium phase relative to `Cmcm`/`Cmc21`, with significantly larger electron effective masses in `P21/c`.
- **Negative-Synthesis Datasets:**
  - Lee, Cruse, Baibakova, Ceder & Jain (2025), *"Text-mined dataset of solid-state syntheses with impurity phases using Large Language Model"*, *Scientific Data* (`https://doi.org/10.1038/s41597-025-06222-y`) validates the LBNL 80k impurity dataset citation.
- **Semi-Transparent $\text{Sb}_2\text{S}_3$ BIPV & Tandem Literature:**
  - *Joule* 2018 (`https://doi.org/10.1016/j.joule.2018.04.003`, 628 citations); *Adv. Funct. Mater.* 2021 (`https://doi.org/10.1002/adfm.202100265`); *Solar RRL* 2021 (`https://doi.org/10.1002/solr.202000800`); *ACS Appl. Energy Mater.* 2020 (`https://doi.org/10.1021/acsaem.0c02552`); *Beilstein J. Nanotechnol.* 2019 (`https://doi.org/10.3762/bjnano.10.230`).

---

## 2. Mathematical & Physical Code Audit Findings

1. **Year-25 Retention Exponent Mismatch (`** 24` vs. `** 25`):**
   - `failsmart_matengine/atomistic_and_tmm.py:1198` uses `((1.0 - r_deg) ** 24) * 100.0`, whereas `failsmart_matengine/independent_verifier.py:1576` and `docs/MATHEMATICAL_SPEC_V2.md` §9.3.3 use `** 25`. `lcoe_ok` does not assert `year25_power_retention_percent`, so the discrepancy passes silently.
2. **`iam_60deg_ratio` Definition Mismatch:**
   - `atomistic_and_tmm.py:1174` computes `pce_by_angle[60.0] / pce_by_angle[0.0]`, whereas `independent_verifier.py:1543` computes `(100.0 - r_front_by_angle[60]) / (100.0 - r_front_by_angle[0])`.
3. **Vacancy Element Parsing Bug in Defect Supercell Generator:**
   - `atomistic_and_tmm.py:836–837` does `vac_el = dom_vac.replace("V_", "").strip()`, which fails when `dominant_vacancy_defect` contains annotations (e.g., `"V_Cu (shallow acceptor)"`), causing `removed_idx` to silently default to `0`.
4. **Missing Halide/Alkaline-Earth Keys in `MULLIKEN_CHI_EV`:**
   - `realistic_commercialization.py:45–56, 102` uses `MULLIKEN_CHI_EV[el]` (only 10 elements), raising `KeyError` on halides (`Cl, Br, I`) or alkaline earths (`Ba, Sr`), unlike `independent_verifier.py:2007` (`.get(el, 4.50)`).
5. **Clamped vs. Unclamped Arrhenius Degradation Rate:**
   - `atomistic_and_tmm.py:1197, 1532` clamps `max(0.0, e_mig_lim - 0.65)`, whereas `independent_verifier.py:1574, 1892` does not.
6. **Implicit $P_{\text{in}} = 100.0$ vs. $100.037\text{ mW/cm}^2$ in Phase 11B:**
   - `realistic_commercialization.py:241, 268` and `independent_verifier.py:2116, 2146` omit `/ 100.037 * 100.0`.
7. **Tautological / Circular Verifications & Optical Double-Counting:**
   - Dynamical matrix pair-spring blocks (`atomistic_and_tmm.py:57–123`) form a positive semi-definite weighted graph Laplacian, making `imaginary_mode_count == 0` mathematically guaranteed.
   - Coherent `T_TMM` (already attenuating via `k_act`) is multiplied by `(1 - f_abs)` from incoherent $4n^2$ Yablonovitch trapping (`atomistic_and_tmm.py:371–375`).

---

## 3. Software Engineering, Packaging & Plan Gap Findings

1. **Broken `pyproject.toml` Flat-Layout Discovery:** `pip install -e .` fails with `Multiple top-level packages discovered in a flat-layout: ['data', 'logs', 'outputs', 'failsmart_matengine']`. Missing `[tool.setuptools.packages.find]` and `[project.scripts]` CLI entrypoints.
2. **Hardcoded `/home/antigravity/...` Linux Paths (4 modules):** `ledger.py:18`, `inter_team_bus.py:18`, `orchestrator.py:92`, and `mp_live_discovery.py:1080` default to `/home/antigravity/failsmart-matengine/...` instead of `Path(__file__).resolve().parent.parent`, writing outside the repo on Windows (even during `tests/test_scientific_integrity.py:544`).
3. **Missing `encoding="utf-8"` in `Path.write_text()`:** `mp_live_discovery.py:369` and `orchestrator.py:433, 434, 489` omit `encoding="utf-8"`.
4. **Eager Heavy Imports in `failsmart_matengine/__init__.py`:** Importing any submodule eagerly imports `independent_verifier.py` (`pvlib`, `scipy`, `pymatgen`).
5. **Stale Checks & Dead-Code Assertions:**
   - `tests/test_scientific_integrity.py:860–863` checks `part.startswith("nat=")` against `  nat = {nat},` (spaces around `=`), so `nat_in_header` is always `None`.
   - `repo_auditor.py:545–548, 599–600` checks for `"18"` tests instead of `22`, and `docs/VERIFICATION_AND_TEST_REPORT.md:8, 249` still says `10` / `20/20` tests in headers.
6. **Plan Gaps (`docs/PLAN.md`):**
   - **Gate B (`GATE_B_FINAL`)** is defined in `schemas.py:73` and `docs/PLAN.md:51–52, 139`, but is **never implemented or called** in `orchestrator.py` or `mp_live_discovery.py`.
   - **Epistemic Uncertainty Active-Learning Route (`UNCERTAIN_DFT_QUEUE` / `ACTIVE_LEARNING_DFT`)** is defined in `docs/PLAN.md:66, 142, 159` and `schemas.py:81`, but `orchestrator.py` never routes uncertain candidates to `UNCERTAIN_DFT_QUEUE`.
   - **External DFT/MLIP packages** (`MatterGen`, `MACE-OMat24`, `CHGNet`, `phonopy`, `rxn_network`, `doped`, `LangGraph`, `botorch`) listed in `docs/PLAN.md` are represented by deterministic Tier-0 analytical surrogates (should be clearly documented as Tier-0 surrogates vs. Tier-1/2 external tools).

---

## 4. Literature Sources Retrieved (URLs & DOIs)

- `https://arxiv.org/pdf/2410.10560v1` | `https://doi.org/10.1021/acsenergylett.4c02722`
- `https://arxiv.org/pdf/2512.18100v1` | `https://doi.org/10.1038/s41467-026-76845-1`
- `https://arxiv.org/pdf/2512.01531v1`
- `https://arxiv.org/pdf/2610.10136v1`
- `https://arxiv.org/pdf/2505.19882v2` | `https://doi.org/10.1103/qjwt-29w9`
- `https://doi.org/10.1038/s41597-025-06222-y`
- `https://doi.org/10.1021/acsenergylett.0c00940`
- `https://doi.org/10.1016/j.joule.2018.04.003`
- `https://doi.org/10.1002/adfm.202100265`
- `https://doi.org/10.1002/solr.202000800`
- `https://doi.org/10.1021/acsaem.0c02552`
- `https://doi.org/10.3762/bjnano.10.230`
- `https://doi.org/10.1016/j.seta.2021.101775`
- `https://doi.org/10.1021/acs.chemmater.6b04266`
- `https://doi.org/10.1021/acsami.4c16630`
- `https://doi.org/10.1021/jacs.7b02399`
- `https://doi.org/10.1039/c2cp40916j`
