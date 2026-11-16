# Questions for Claude Fable Review

These questions arise from our `/science` literature examination and 3-subagent code/math/plan audit of `failsmart-matengine` (`v8.0`). We have implemented all unambiguous software, cross-platform, mathematical-consistency, Gate B, and packaging fixes while preserving `v8.0` benchmark outputs where science policy decisions require your sign-off.

1. **Should we add an `ERE = 1e-8` ("Current Experimental Baseline") tier to Phase 11B?**
   - World-record $\text{Sb}_2\text{S}_3$ solar cells only reached `824 mV` $V_{\text{oc}}$ in 2026 (`arXiv:2512.18100v1`, *Nature Communications* 2026), corresponding to $\text{ERE} \sim 10^{-11}\text{–}10^{-9}$, whereas `Phase 11B` currently treats $\text{ERE} = 10^{-5}$ as "Conservative" (`1.10–1.19 V`). Adding an `ERE = 1e-8` baseline tier would make the maturity trajectory bulletproof against experimentalist pushback.
2. **Should Phase 11A incorporate facet-dependent band-edge uncertainty ($\pm 0.3\text{–}0.8\text{ eV}$)?**
   - `arXiv:2610.10136v1` (Oct 2026) shows `(011)` vs. `(010)` terminations in low-dimensional pnictogen chalcohalides shift band edges by up to $0.8\text{ eV}$ (causing up to $0.6\text{ V}$ $V_{\text{oc}}$ loss). Should `Phase 11A` add a `facet_dipole_uncertainty_ev` penalty for `1D-Chain` / `Quasi-2D` crystals rather than relying solely on scalar Mulliken electronegativity?
3. **How should we resolve coherent `T_TMM` vs. incoherent $4n^2$ `f_abs` double-counting?**
   - In `atomistic_and_tmm.py:371–375`, `T_TMM` already includes Beer-Lambert absorption via `k_act`, and is then multiplied by `(1 - f_abs)`. Should we compute `T_TMM` with `k_act = 0` in the absorber for the rear-escape factor, or use a pure incoherent/coherent hybrid TMM (`tmm.inc_tmm`)?
4. **Should Path 3 (`2T` Monolithic) and Path 4 (`BIPV`) use explicit optical/electrical solvers instead of flat multipliers (`0.84` and `0.72`)?**
   - Specifically: solving `J_sc,2T = min(J_sc,top, J_sc,Si)` for Path 3 and photopic-weighted Average Visible Transmittance (`AVT`) at `35%` for Path 4.
5. **Should Tier-1/Tier-2 external tools (`MACE-OMat24`, `phonopy`, `rxn_network`, `doped`, `Quantum ESPRESSO`) be kept optional/cloud-only while explicitly labeling Tier-0 modules as analytical surrogates?**
   - Currently `docs/PLAN.md` lists `LangGraph`, `MatterGen`, `MACE-OMat24`, `phonopy`, `rxn_network`, and `doped` as deterministic tools, whereas the local repo executes pure-Python analytical surrogates + `pymatgen`/`pyxtal`/`spglib`/`smact`/`pvlib`.
6. **Should `outputs/failsmart_dashboard.html` be dynamically generated from `outputs/live_mp_discovery_summary.json`?**
   - Currently `outputs/failsmart_dashboard.html` has static hardcoded JS arrays showing subsets (e.g., 7 of 15 stacks in `PHASE11B_PATHS`), which can drift from `live_mp_discovery_summary.json`.
