# FailSmart-MatEngine v2.0 — Blinded Mathematical & Physical Specification

> **FIREWALL MANDATE:** Primary Engineers (`physics_engine_engineer`, `optics_kinetics_engineer`) and the Independent Redundancy Verifier (`redundancy_verifier_alpha`) MUST implement solely from the physical equations, constants, and module contracts in this specification plus `failsmart_matengine/schemas.py`.
> - Empirical efficiency multipliers (such as `1.28x` or `0.80x`) are **strictly forbidden**.
> - `failsmart_matengine/independent_verifier.py` MUST NOT import from `physics_calculators.py`, `kinetics_and_optics.py`, or `tools.py`, and MUST NOT read those `.py` files during implementation. AST static analysis in `tests/test_scientific_integrity.py` enforces this zero-coupling firewall.

---

## 1. Fundamental Physical Constants (CODATA 2018)

* Elementary charge: $q = 1.602176634 \times 10^{-19}\text{ C}$
* Planck constant: $h = 6.62607015 \times 10^{-34}\text{ J}\cdot\text{s}$, $\hbar = h / (2\pi)$
* Speed of light: $c = 2.99792458 \times 10^8\text{ m/s}$
* Boltzmann constant: $k_B = 1.380649 \times 10^{-23}\text{ J/K}$
* Vacuum permittivity: $\varepsilon_0 = 8.8541878128 \times 10^{-12}\text{ F/m}$
* Electron rest mass: $m_0 = 9.1093837015 \times 10^{-31}\text{ kg}$
* Avogadro constant: $N_A = 6.02214076 \times 10^{23}\text{ mol}^{-1}$
* Cell operating temperature: $T_{\text{cell}} = 300.0\text{ K}$, $V_{\text{th}} = k_B T_{\text{cell}} / q \approx 0.02585199\text{ V}$
* Photon energy-wavelength conversion: $hc / q \times 10^9 = 1239.8419843320026\text{ eV}\cdot\text{nm}$

---

## 2. Crystallography, Wyckoff Symmetry, Bond-Valence Sum & Fröhlich Physics

1. **Canonical Formula & Exact Charge Neutrality (`physics_calculators.py`):**
   * Given integer stoichiometry $\{E_i: n_i\}$ and formal oxidation states $\{E_i: z_i\}$:
     $$\sum_i n_i z_i \equiv 0$$
   * Canonical reduced formula divides $n_i$ by $\gcd(\{n_i\})$, ordering cations first (in input dictionary key order) and anions second in strict order `["O", "S", "Se", "Te", "N", "P", "Cl", "Br", "I"]`.

2. **Genuine 3D Crystal Generation (`pyxtal` + `pymatgen` + `spglib`) & Live MP DFT Structures:**
   * Build genuine 3D `pymatgen.core.Structure` crystals using `pyxtal` (trying the target space group with $Z \in \{1, 2, 4\}$ formula units so Wyckoff multiplicities match, or falling back cleanly to a deterministic `pyxtal` / `pymatgen` `P1` 3D lattice), OR ingest DFT-relaxed crystal structures directly from the live Materials Project API (`MPRester`).
   * Enforce 3D periodic minimum interatomic distance across all periodic images (`struct.distance_matrix` + self-image lattice vector norm check): synthetic `PyXtal` non-oxide generators target $d_{\min} \ge 2.18\text{ \AA}$, while real DFT-relaxed oxychalcogenides/chalcohalides (e.g., $\text{Ti–O} \approx 1.81\text{ \AA}$, $\text{Fe–O} \approx 1.93\text{ \AA}$, $\text{Sb–O} \approx 2.05\text{ \AA}$) have true covalent/ionic bond lengths down to $1.75\text{ \AA}$. Therefore, `independently_verify_cif_geometry` validates `min_distance_ang >= 1.75` as physically clash-free across both DFT oxides and synthetic chalcohalides.
   * Analyze actual symmetry via `SpacegroupAnalyzer(struct, symprec=0.1)` so `space_group_symbol`, `space_group_number`, and `nsites_unit_cell = len(struct)` reflect the **true physical crystal structure** inside `cif_content`!
   * Export CIF via `CifWriter(struct)` (explicit unit-cell sites, parseable round-trip via `CifParser.from_str(cif_str).parse_structures(primitive=False)[0]` with exact `len(struct) == nsites_unit_cell` and matching reduced composition).

3. **True Brown-Altermatt Bond-Valence Sum Global Instability Index (`bvs_gii`):**
   * Standard empirical covalent/Shannon single-bond radii $r_0(E)$ ($\text{\AA}$) so $R_{0,ij} = r_0(i) + r_0(j)$ for cation-anion pairs:
     `{"Bi": 1.52, "Sb": 1.40, "Sn": 1.42, "Cu": 1.12, "Ag": 1.28, "Zn": 1.18, "Ba": 1.82, "Sr": 1.68, "Ca": 1.54, "Mg": 1.30, "Ti": 1.26, "Zr": 1.42, "Fe": 1.24, "In": 1.38, "Ga": 1.24, "Pb": 1.56, "Cd": 1.36, "O": 0.63, "S": 1.04, "Se": 1.17, "Te": 1.36, "N": 0.70, "P": 1.06, "Cl": 0.99, "Br": 1.14, "I": 1.33}`
   * For each site $i$ with target oxidation state $z_i$, sum over opposite-sign neighbors $j$ within $r_{ij} \le 4.0\text{ \AA}$ (`struct.get_neighbors(site, 4.0)`):
     $$V_i = \sum_{j:\, z_i z_j < 0} \exp\!\left(\frac{R_{0,ij} - r_{ij}}{0.37}\right), \quad \text{GII} = \sqrt{\frac{1}{N_{\text{sites}}} \sum_{i=1}^{N_{\text{sites}}} \left(V_i - |z_i|\right)^2}$$
     *(Note: calibrate equilibrium lattice volume during synthetic structure generation so stable prototypes achieve physically realistic bond lengths; for live MP DFT structures, compute exact unscaled GII directly on the DFT lattice).*

4. **Exact Fröhlich Polaron Coupling Constant (`frohlich_alpha`) & Trapping Energy:**
   * Given `electron_eff_mass_m0` ($m_e^*/m_0$), `hole_eff_mass_m0` ($m_h^*/m_0$), `eps_inf` ($\varepsilon_\infty$), `eps_static` ($\varepsilon_s$), and `lo_phonon_freq_thz` ($\nu_{\text{LO}}$ in $\text{THz}$, so $\omega_{\text{LO}} = 2\pi \nu_{\text{LO}} \times 10^{12}\text{ rad/s}$):
   * Using dominant band-edge effective mass $m^* = \max(m_e^*, m_h^*) \cdot m_0$:
     $$\alpha_F = \frac{q^2}{4\pi \varepsilon_0 \hbar} \left(\frac{1}{\varepsilon_\infty} - \frac{1}{\varepsilon_s}\right) \sqrt{\frac{m^*}{2 \hbar \omega_{\text{LO}}}}$$
   * Polaron self-trapping stabilization energy (Feynman-Schultz low/intermediate-coupling expansion, in $\text{meV}$):
     $$E_{\text{pol}}\text{ [meV]} = 1000 \cdot \left(\frac{\hbar \omega_{\text{LO}}}{q}\right) \left(\alpha_F + 0.0159196 \, \alpha_F^2\right)$$

5. **Anderson Acoustic Debye Temperature (`debye_temperature_k`):**
   * Given `bulk_modulus_gpa` ($K$ in GPa), `shear_modulus_gpa` ($G$ in GPa), unit cell volume $V_{\text{cell}}$ ($\text{\AA}^3$), `nsites_unit_cell` ($N_{\text{sites}}$), and formula molar mass:
     * Mass density $\rho = \frac{M_{\text{cell}}}{N_A V_{\text{cell}} \times 10^{-30}}\text{ [kg/m}^3\text{]}$.
     * Longitudinal & transverse sound speeds:
       $$v_l = \sqrt{\frac{(K + \frac{4}{3}G)\times 10^9}{\rho}}, \quad v_t = \sqrt{\frac{G\times 10^9}{\rho}}, \quad v_m = \left[\frac{1}{3}\left(\frac{2}{v_t^3} + \frac{1}{v_l^3}\right)\right]^{-1/3}$$
     * Debye temperature:
       $$\Theta_D = \frac{h}{k_B} \left(\frac{3 N_{\text{sites}}}{4\pi V_{\text{cell}} \times 10^{-30}}\right)^{1/3} v_m$$

---

## 3. Stage 2b Ion-Migration Gate ($\text{Cu}^+ / \text{Ag}^+$ Superionic Drift Filter)

To eliminate perovskite-like $J\text{–}V$ hysteresis and metallic $\text{Cu}^0/\text{Ag}^0$ filament shunting under solar operating fields ($\sim 5\times 10^4\text{ V/cm}$):
* Every candidate is evaluated for **minimum ion-migration activation barrier $E_{\text{mig}}$ (`ion_migration_barrier_ev`, eV)**:
  * Frameworks with high monovalent $d^{10}$ cation fraction ($\text{Cu}^+, \text{Ag}^+$) and percolating halide ($\text{Cl}^-, \text{Br}^-, \text{I}^-$) channels without rigid oxide slabs or corner-sharing covalent $[\text{MCh}_2]^-$ locking suffer low barriers ($E_{\text{mig}} < 0.65\text{ eV}$). Specifically, `Cu3BiS2Cl2` (`CAND-A09`, $37.5\text{ at}\%\text{ Cu}^+$ + dual $\text{Cl}^-$ channels) exhibits $E_{\text{mig}} = 0.42\text{ eV}$ and MUST fail Stage 2b!
  * **Hard Stage 2b Gate:** `ion_migration_stable = (ion_migration_barrier_ev >= 0.65)`. If `False`, reject in Stage 2 with failure prefix `ION_MIGRATION_INSTABILITY:`.

---

## 4. Exact Unscaled SLME & Sequential 3-Layer 4-Terminal Optics

1. **Official Reference Solar Spectrum:**
   * Load **ASTM G173-03 AM1.5G Global Tilt** spectral irradiance $I_\lambda(\lambda_{\text{nm}})$ ($\text{W}\cdot\text{m}^{-2}\cdot\text{nm}^{-1}$) from `pvlib.spectrum.get_reference_spectra()['global']` ($\lambda \in [280.0, 4000.0]\text{ nm}$).
   * Total incident 1-sun power density in $\text{mW/cm}^2$:
     $$P_{\text{in}} = 0.1 \int_{280}^{4000} I_\lambda(\lambda)\,d\lambda \approx 100.037\text{ mW/cm}^2$$
   * Spectral solar photon flux ($\text{photons}\cdot\text{m}^{-2}\cdot\text{s}^{-1}\cdot\text{nm}^{-1}$):
     $$\Phi_{\text{sun}}(\lambda) = \frac{I_\lambda(\lambda)}{h c / (\lambda \times 10^{-9})}$$

2. **Single-Layer Absorptance, Unscaled SLME & Exact Shockley-Queisser Ceiling:**
   * Given indirect gap $E_{g,\text{ind}}$ (eV), direct gap $E_{g,\text{dir}}$ (eV), $\varepsilon_\infty$, and film thickness $d = \text{thickness\_nm} \times 10^{-9}\text{ m}$:
   * Refractive index $n = \sqrt{\varepsilon_\infty}$, Yablonovitch factor $Y = 4 n^2$, front AR reflectance $R_{\text{front}} = 0.020$.
   * Absorption coefficient $\alpha(E)$ ($\text{m}^{-1}$) at photon energy $E = \frac{hc/q \times 10^9}{\lambda_{\text{nm}}}$ (eV):
     $$\alpha(E) = 1.2\times 10^5 \max(0, E - E_{g,\text{ind}})^2 + 2.8\times 10^7 \sqrt{\max(0, E - E_{g,\text{dir}})}$$
   * Internal light-trapping absorptance fraction & net external absorptance:
     $$f_{\text{abs}}(E) = \frac{4 n^2 \alpha(E) d}{1.0 + 4 n^2 \alpha(E) d}, \quad A(E) = (1.0 - R_{\text{front}}) f_{\text{abs}}(E)$$
   * Blackbody photon flux at $T_{\text{cell}} = 300.0\text{ K}$:
     * In wavelength space ($\text{photons}\cdot\text{m}^{-2}\cdot\text{s}^{-1}\cdot\text{nm}^{-1}$, with $\lambda_m = \lambda_{\text{nm}}\times 10^{-9}$):
       $$\Phi_{\text{bb},\lambda}(\lambda_{\text{nm}}) = \frac{2\pi c}{\lambda_m^4 \left[\exp\!\left(\min(500.0, \frac{hc}{\lambda_m k_B T_{\text{cell}}})\right) - 1\right]} \times 10^{-9}$$
     * Equivalently in photon-energy space ($\text{photons}\cdot\text{m}^{-2}\cdot\text{s}^{-1}\cdot\text{eV}^{-1}$):
       $$\Phi_{\text{bb},E}(E) = \frac{2\pi q^3 E^2}{h^3 c^2 \left[\exp\!\left(\min(500.0, \frac{q E}{k_B T_{\text{cell}}})\right) - 1\right]}$$
   * Dark saturation current density ($\text{mA/cm}^2$):
     $$J_{0,\text{rad}} = 0.1 \, q \int A \, \Phi_{\text{bb}} + 10^{-40}, \quad f_r = \exp\!\left(-\frac{\max(0, E_{g,\text{dir}} - E_{g,\text{ind}})}{V_{\text{th}}}\right), \quad J_0 = \frac{J_{0,\text{rad}}}{f_r}$$
   * For any incident photon flux $\Phi_{\text{inc}}$, cell $J_{\text{sc}}$ ($\text{mA/cm}^2$), $V_{\text{oc}}$ ($\text{V}$), Green's analytical $FF$, and **unscaled** efficiency (%):
     $$J_{\text{sc}} = 0.1 \, q \int A \, \Phi_{\text{inc}}, \quad V_{\text{oc}} = V_{\text{th}} \ln\!\left(\frac{J_{\text{sc}}}{J_0} + 1.0\right), \quad v = \frac{V_{\text{oc}}}{V_{\text{th}}}, \quad FF = \frac{v - \ln(v + 0.72)}{v + 1.0}$$
     $$\eta(\Phi_{\text{inc}}) = \frac{J_{\text{sc}} \cdot V_{\text{oc}} \cdot FF}{P_{\text{in}}} \times 100.0$$
     *(If $J_{\text{sc}} \le 10^{-9}$, $\eta = 0.0$.)*
   * **Exact 1-Sun Shockley-Queisser Limit `shockley_queisser_limit_percent`:**
     Evaluated at $\Phi_{\text{inc}} = \Phi_{\text{sun}}$ with step absorptance $A_{\text{SQ}}(E) = 1.0$ for $E \ge E_{g,\text{ind}}$ else $0.0$, and $f_r = 1.0$.
   * **Hard Thermodynamic Invariant:** `standalone_slme_percent <= shockley_queisser_limit_percent` MUST hold for every candidate.

3. **Sequential 3-Layer 4-Terminal Stack Propagation (Zero Double-Counting + Silicon FCA):**
   * Reference partner layers when evaluating a single candidate:
     * When `target_layer == "TOP_ACTIVE_GLASS_185EV"`: Layer 1 is the candidate; Layer 3 is `Ref-Bottom` ($E_{g,\text{ind},3} = 0.75\text{ eV}$, $E_{g,\text{dir},3} = 0.79\text{ eV}$, $\varepsilon_{\infty,3} = 8.50$, $d_3 = 350.0\text{ nm}$).
     * When `target_layer == "BOTTOM_IR_075EV"`: Layer 1 is `Ref-Top` ($E_{g,\text{ind},1} = 1.84\text{ eV}$, $E_{g,\text{dir},1} = 1.88\text{ eV}$, $\varepsilon_{\infty,1} = 6.10$, $d_1 = 260.0\text{ nm}$); Layer 3 is the candidate.
     * **Cross-Layer Discovered Pair (`independently_verify_cross_layer_4t_pair`):** When pairing an arbitrary discovered Track A candidate `(eg_ind_1, eg_dir_1, eps_inf_1, thickness_nm_1)` with an arbitrary discovered Track B candidate `(eg_ind_3, eg_dir_3, eps_inf_3, thickness_nm_3)`, Steps A–C below are evaluated using both candidates' exact parameters simultaneously.
   * **Step A — Layer 1 (Top Active Glass on Soda-Lime Glass):**
     * Incident flux $\Phi_1 = \Phi_{\text{sun}}$, yielding `top_cell_jsc_ma_cm2`, `top_cell_voc_v`, and `top_cell_eff_percent`.
     * Residual Fresnel mismatch & dual-TCO Drude transmittance:
       $$R_{\text{fresnel}}(n_1) = 0.25 \left(\frac{n_1 - 1.85}{n_1 + 1.85}\right)^2, \quad T_{\text{TCO}}(\lambda_{\text{nm}}) = \exp\!\left(-2.0 \left[0.015 + 0.028 \left(\frac{\lambda_{\text{nm}}}{1000.0}\right)^2\right]\right)$$
     * Wavelength-resolved Layer-1 transmittance & transmitted flux entering Silicon:
       $$T_{\text{stack},1}(\lambda) = \left(1.0 - 0.020 - 0.020 - R_{\text{fresnel}}(n_1)\right) \cdot \left(1.0 - f_{\text{abs},1}(E)\right) \cdot T_{\text{TCO}}(\lambda)$$
       $$\Phi_2(\lambda) = \Phi_1(\lambda) \cdot T_{\text{stack},1}(\lambda)$$
       *(Notice $A_1(\lambda) + T_{\text{stack},1}(\lambda) \le 0.98 < 1.0$ at every wavelength!)*
     * `sub_bandgap_transmittance_percent`: photon-flux-weighted mean of $T_{\text{stack},1}(\lambda) \times 100$ over the sub-bandgap Silicon/IR window $E \in [0.75\text{ eV}, E_{g,\text{ind},1} - 0.02\text{ eV}]$ (for Track B candidates, evaluate internal sub-gap window $E \in [0.40\text{ eV}, E_{g,\text{ind},3} - 0.02\text{ eV}]$ using $n_3$ and single-TCO transmittance $\sqrt{T_{\text{TCO}}(\lambda)}$).
     * `tco_parasitic_loss_percent`: photon-flux-weighted mean of $(1.0 - T_{\text{TCO}}(\lambda)) \times 100$ over the same sub-bandgap window.
   * **Step B — Layer 2 (Crystalline Silicon Wafer, $E_{g,\text{Si}} = 1.12\text{ eV}$, $d_{\text{Si}} = 160\times 10^{-6}\text{ m}$, $J_{0,\text{Si}} = 1.2\times 10^{-12}\text{ mA/cm}^2$):**
     * $\alpha_{\text{Si}}(E) = 1.1\times 10^5 \max(0, E - 1.12)^2 + 1.5\times 10^7 \sqrt{\max(0, E - 3.40)}$ ($\text{m}^{-1}$).
     * Rear-mirrored 2-Layer Si absorptance fraction: $f_{\text{abs,Si,2L}}(E) = \frac{49.0\,\alpha_{\text{Si}}(E) d_{\text{Si}}}{1.0 + 49.0\,\alpha_{\text{Si}}(E) d_{\text{Si}}}$, $A_{\text{Si,2L}} = 0.98\,f_{\text{abs,Si,2L}}$, giving $\eta_{\text{Si,2L}}(\Phi_2)$.
     * Bifacial 3-Layer Si absorptance fraction: $f_{\text{abs,Si,3L}}(E) = \frac{16.0\,\alpha_{\text{Si}}(E) d_{\text{Si}}}{1.0 + 16.0\,\alpha_{\text{Si}}(E) d_{\text{Si}}}$, $A_{\text{Si,3L}} = 0.98\,f_{\text{abs,Si,3L}}$, giving `si_middle_cell_eff_percent` $= \eta_{\text{Si,3L}}(\Phi_2)$.
     * Silicon Drude Free-Carrier Absorption (FCA) in sub-$1.12\text{ eV}$ IR:
       * Low-FCA local-contact Si: $T_{\text{Si,FCA,low}}(\lambda_{\text{nm}}) = \exp\!\left(-0.08 \left(\frac{\lambda_{\text{nm}}}{1200.0}\right)^2\right)$
       * Standard commercial TOPCon/PERC Si: $T_{\text{Si,FCA,std}}(\lambda_{\text{nm}}) = \exp\!\left(-0.38 \left(\frac{\lambda_{\text{nm}}}{1200.0}\right)^2\right)$
       * Transmitted IR photon fluxes entering Layer 3:
         $$\Phi_{3,\text{low}}(\lambda) = \Phi_2(\lambda) \cdot 0.96 \cdot \left(1.0 - f_{\text{abs,Si,3L}}(E)\right) \cdot T_{\text{Si,FCA,low}}(\lambda)$$
         $$\Phi_{3,\text{std}}(\lambda) = \Phi_2(\lambda) \cdot 0.96 \cdot \left(1.0 - f_{\text{abs,Si,3L}}(E)\right) \cdot T_{\text{Si,FCA,std}}(\lambda)$$
   * **Step C — Layer 3 (Bottom IR Scavenger with $4n_3^2$ Rear Mirror):**
     * `bottom_ir_cell_eff_percent` $= \eta_3(\Phi_{3,\text{low}})$, and `bottom_ir_std_si_eff_percent` $= \eta_3(\Phi_{3,\text{std}})$.
     * Stack totals:
       * `tandem_2layer_si_eff_percent` $= \eta_1(\Phi_1) + \eta_{\text{Si,2L}}(\Phi_2)$
       * `tandem_4t_std_si_fca_eff_percent` $= \eta_1(\Phi_1) + \eta_{\text{Si,3L}}(\Phi_2) + \eta_3(\Phi_{3,\text{std}})$
       * `tandem_4t_total_eff_percent` $= \eta_1(\Phi_1) + \eta_{\text{Si,3L}}(\Phi_2) + \eta_3(\Phi_{3,\text{low}})$
   * **Optical Gate (`passed_optical_gate`):**
     * Track A: `sub_bandgap_transmittance_percent >= 85.0 and standalone_slme_percent >= 20.0`
     * Track B: `standalone_slme_percent >= 18.0 and bottom_ir_cell_eff_percent >= 3.5`

---

## 5. Quadrature Separation & Redundancy Tolerances

* **Primary Engineers (`kinetics_and_optics.py` & `mp_live_discovery.py`):** Integrate in **wavelength space** ($\lambda \in [280, 4000]\text{ nm}$) on `pvlib`'s native ASTM G173-03 grid using `numpy.trapezoid`.
* **Blinded Independent Verifier (`independent_verifier.py`):** Integrate in **photon-energy space** ($E \in [hc/(4000 q), hc/(280 q)]\text{ eV}$, $N = 8001$ uniform points) using `scipy.integrate.simpson` and exact Jacobian $\left|\frac{d\lambda}{dE}\right| = \frac{hc/q \times 10^9}{E^2}$ — **strictly zero imports** from `physics_calculators`, `kinetics_and_optics`, `tools`, or `mp_live_discovery`.
* **Required Agreement:**
  * $|\eta_{\text{SLME, wl}} - \eta_{\text{SLME, E}}| \le 0.10\%$
  * $|\eta_{\text{4T, wl}} - \eta_{\text{4T, E}}| \le 0.10\%$ (both single-candidate reference partner and cross-layer `(Top, c-Si, Bottom)` pairs)
  * $|\alpha_{F,\text{primary}} - \alpha_{F,\text{verifier}}| \le 10^{-3}$
  * `standalone_slme_percent <= shockley_queisser_limit_percent` (0 violations tolerated).
