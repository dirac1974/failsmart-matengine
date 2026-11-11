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

---

## 6. 3D Atomistic Harmonic Dynamical Matrix $\mathbf{D}(\mathbf{q}=\mathbf{0})$ & 3D Saddle-Point NEB Ion Migration (v4.0)

### 6.1 Exact $3N \times 3N$ Harmonic Dynamical Matrix at $\Gamma$ ($\mathbf{q} = \mathbf{0}$)
Given a 3D periodic crystal structure (`pymatgen.core.Structure` parsed from `cif_content` with $N = \text{len(struct)}$ sites) and formal oxidation states $z_i$:
1. **Periodic Cation-Anion & Interlayer Bond Network ($r_{\text{cut}} = 4.25\text{ \AA}$):**
   * For every site $i \in \{0, \dots, N-1\}$, enumerate all periodic neighbor images $(j, \mathbf{R})$ within $0.50\text{ \AA} < r_{ij} \le 4.25\text{ \AA}$ via `struct.get_neighbors(struct[i], r=4.25)`.
   * Unit bond vector $\hat{\mathbf{u}}_{ij} = (\mathbf{r}_j + \mathbf{R} - \mathbf{r}_i) / r_{ij}$.
   * Reference bond-valence length $r_{0,ij}$ from `BVS_R0_TABLE` if $(s_i, s_j)$ or $(s_j, s_i)$ is in `BVS_R0_TABLE`, else sum of covalent/ionic radii $r_{\text{cov}}(s_i) + r_{\text{cov}}(s_j)$ (with standard reference $r_{0,\text{default}} = 2.45\text{ \AA}$).
   * Longitudinal Born-Mayer bond-stretching stiffness ($k_{\parallel, ij}$ in $\text{eV/\AA}^2$) and transverse bond-bending stiffness ($k_{\perp, ij}$ in $\text{eV/\AA}^2$):
     $$k_{\parallel, ij} = 48.0 \cdot \exp\!\left(\frac{r_{0,ij} - r_{ij}}{0.37}\right), \quad k_{\perp, ij} = 0.18 \cdot k_{\parallel, ij}$$
2. **$3N \times 3N$ Force-Constant Hessian $\mathbf{\Phi}$ (Satisfying Exact Acoustic Sum Rule):**
   * For each neighbor bond $(i, j, \hat{\mathbf{u}}_{ij})$ ($3\times 3$ pairwise block $\mathbf{K}_{ij} = (k_{\parallel, ij} - k_{\perp, ij})\,\hat{\mathbf{u}}_{ij}\hat{\mathbf{u}}_{ij}^T + k_{\perp, ij}\,\mathbf{I}_3$):
     * Off-diagonal block $(3i:3i+3,\; 3j:3j+3)$: subtract $\mathbf{K}_{ij}$.
     * On-diagonal self-block $(3i:3i+3,\; 3i:3i+3)$: add $+\mathbf{K}_{ij}$ (enforcing exact translational invariance $\sum_j \mathbf{\Phi}_{ij} = \mathbf{0}$).
   * Symmetrize $\mathbf{\Phi} \leftarrow \frac{1}{2}(\mathbf{\Phi} + \mathbf{\Phi}^T)$.
3. **Mass-Weighted Dynamical Matrix $\mathbf{D}(\mathbf{0})$ & THz Conversion:**
   * Using `IUPAC_ATOMIC_MASSES[el]` ($m_i$ in amu):
     $$D_{3i+\alpha,\; 3j+\beta} = \frac{\Phi_{3i+\alpha,\; 3j+\beta}}{\sqrt{m_i \, m_j}} \quad [\text{eV / (\AA}^2 \cdot \text{amu)}]$$
   * Eigenvalues $\lambda_m$ ($m = 1, \dots, 3N$) sorted ascending:
     * Primary (`atomistic_and_tmm.py`): `np.linalg.eigh(D)[0]`
     * Blinded Verifier (`independent_verifier.py`): `scipy.linalg.eigvalsh(D)`
   * Frequency conversion factor from $\sqrt{\text{eV / (\AA}^2 \cdot \text{amu)}}$ to $\text{THz}$:
     $$f_{\text{THz}} = \frac{1}{2\pi} \sqrt{\frac{1.602176634\times 10^{-19}\text{ J/eV}}{1.66053906660\times 10^{-27}\text{ kg/amu} \times 10^{-20}\text{ m}^2/\text{\AA}^2}} \times 10^{-12} = 15.633302\text{ THz}$$
     $$\omega_m = \text{sign}(\lambda_m)\cdot 15.633302 \cdot \sqrt{|\lambda_m|} \quad [\text{THz}]$$
   * Modes $m = 0, 1, 2$ are the 3 acoustic translational zero-modes ($|\omega_m| < 0.05\text{ THz}$).
   * Reported optical phonon metrics (for $m \ge 3$):
     * `gamma_min_optical_freq_thz`: $\text{round}(\omega_3, 4)$
     * `gamma_max_lo_freq_thz`: $\text{round}(\omega_{3N-1}, 4)$
     * `imaginary_mode_count`: count of modes $m \ge 3$ with $\omega_m < -0.05\text{ THz}$ (must be `0` for dynamical stability).

### 6.2 3D Saddle-Point NEB Ion-Migration Pathway Solver
1. **Mobile Species & Shortest Periodic Hop Identification:**
   * Priority order of migrating species $s_{\text{mig}}$: `"Cu"` if `"Cu"` in stoichiometry, else `"Ag"` if `"Ag"` in stoichiometry, else `"O"` if `"O"` in stoichiometry, else `"S"` if `"S"` in stoichiometry, else `"Se"`.
   * Find the shortest periodic hop between two sites of species $s_{\text{mig}}$ in `struct` with $2.20\text{ \AA} \le d_{\text{hop}} \le 6.50\text{ \AA}$ via `struct.get_neighbors` over all sites of species $s_{\text{mig}}$ (let $\mathbf{r}_A$ be the origin site Cartesian coordinate and $\mathbf{r}_B$ be the target periodic image Cartesian coordinate, $d_{\text{hop}} = \|\mathbf{r}_B - \mathbf{r}_A\|$).
2. **11-Image Linearly Interpolated Pathway & Steric Cage Bottleneck:**
   * At the midpoint saddle image $\mathbf{r}_{\text{mid}} = \frac{1}{2}(\mathbf{r}_A + \mathbf{r}_B)$, compute the distance to all surrounding host framework atoms (excluding the endpoint images $\mathbf{r}_A$ and $\mathbf{r}_B$ within $0.25\text{ \AA}$) within $5.0\text{ \AA}$. Let $d_{\text{cage,min}}$ be the minimum distance from $\mathbf{r}_{\text{mid}}$ to any surrounding host atom (`bottleneck_clearance_ang = round(d_cage_min, 4)`).
   * Let $f_{\text{oxide}} = n_{\text{O}} / N_{\text{total}}$ and $f_{\text{mobile}} = (n_{\text{Cu}} + n_{\text{Ag}}) / N_{\text{total}}$.
   * The 11-image ($s_k = k/10,\; k=0,\dots,10$) steric + electrostatic migration profile $E_{\text{NEB}}(s)$ has saddle barrier at $s = 0.5$:
     $$E_{\text{mig}}^{\text{NEB}} = \text{round}\!\left(\text{clip}\!\left(0.42 + 0.14\,d_{\text{hop}} + \frac{0.68}{\max(1.20, d_{\text{cage,min}})^2} + 0.28\,f_{\text{oxide}} - 0.22\,f_{\text{mobile}},\; 0.35,\; 1.45\right),\; 4\right)\text{ [eV]}$$
   * Room-temperature ($T = 300\text{ K}$) Vineyard-Arrhenius ionic diffusivity ($\nu_0 = 10^{12}\text{ s}^{-1}$, $1\text{ \AA}^2 = 10^{-16}\text{ cm}^2$):
     $$D_{\text{ion}}(300\text{ K}) = \frac{1}{6} \nu_0 \left(d_{\text{hop}}^2 \times 10^{-16}\right) \exp\!\left(-\frac{E_{\text{mig}}^{\text{NEB}} \cdot q}{k_B \cdot 300.0}\right)\text{ [cm}^2\text{/s]}$$

---

## 7. Coherent Multilayer $2\times 2$ Abeles Transfer-Matrix Method (TMM) vs. Recursive Rouard/Airy Impedance Optics (v4.0)

For any cross-paired 4-Terminal stack `(Top Active Glass Layer 1, Middle c-Si Anchor Layer 2, Bottom IR Scavenger Layer 3)`:

### 7.1 Coherent Thin-Film Multilayer Stack Definition for Top Active Glass
At each wavelength $\lambda_{\text{nm}}$ (with $\lambda_{\mu\text{m}} = \lambda_{\text{nm}} / 1000.0$ and photon energy $E = \frac{hc/q\times 10^9}{\lambda_{\text{nm}}}$):
* **Medium 0 (Incident Air):** $\tilde{n}_0 = 1.000 + 0i$ (semi-infinite).
* **Layer 1 ($\text{MgF}_2$ Anti-Reflective Coating, $d_{\text{ARC}} = 98.0\text{ nm}$):**
  $$n_{\text{ARC}}(\lambda) = 1.377 + \frac{0.0032}{\lambda_{\mu\text{m}}^2}, \quad k_{\text{ARC}}(\lambda) = 0.0, \quad \tilde{n}_{\text{ARC}} = n_{\text{ARC}} + i\,k_{\text{ARC}}$$
* **Layer 2 (Front ITO Transparent Electrode, $d_{\text{ITO}} = 105.0\text{ nm}$):**
  $$n_{\text{ITO}}(\lambda) = \max\!\left(1.45,\; 1.92 - 0.085\,\lambda_{\mu\text{m}}^2\right), \quad k_{\text{ITO}}(\lambda) = 0.0018 + 0.0065\,\lambda_{\mu\text{m}}^3, \quad \tilde{n}_{\text{ITO}} = n_{\text{ITO}} + i\,k_{\text{ITO}}$$
* **Layer 3 (Top Active Absorber Film, thickness $d_{\text{top}} = \text{thickness\_nm\_1}$):**
  * Absorption coefficient $\alpha_1(E) = 1.2\times 10^5 \max(0, E - E_{g,\text{ind},1})^2 + 2.8\times 10^7 \sqrt{\max(0, E - E_{g,\text{dir},1})}\text{ [m}^{-1}\text{]}$.
  * Complex refractive index:
    $$n_{\text{act},1}(\lambda) = \sqrt{\varepsilon_{\infty,1}} + \frac{0.035}{\lambda_{\mu\text{m}}^2}, \quad k_{\text{act},1}(\lambda) = \frac{\alpha_1(E)\cdot (\lambda_{\text{nm}}\times 10^{-9})}{4\pi}, \quad \tilde{n}_{\text{act},1} = n_{\text{act},1} + i\,k_{\text{act},1}$$
* **Layer 4 (Rear $\text{SiO}_2/\text{ITO}$ Index-Matching Exit Buffer, $d_{\text{buf}} = 85.0\text{ nm}$):**
  $$n_{\text{buf}}(\lambda) = 1.720 + \frac{0.0040}{\lambda_{\mu\text{m}}^2}, \quad k_{\text{buf}}(\lambda) = 0.0012\,\lambda_{\mu\text{m}}^2, \quad \tilde{n}_{\text{buf}} = n_{\text{buf}} + i\,k_{\text{buf}}$$
* **Medium 5 (Optical Interlayer Couplant to Textured c-Si):** $\tilde{n}_5 = 1.520 + 0i$ (semi-infinite exit medium for the coherent thin-film top stack).

### 7.2 Dual Mathematical Formulations for Coherent Multilayer Reflectance $R_{\text{TMM}}(\lambda)$ & Transmittance $T_{\text{TMM}}(\lambda)$
Let the 6 media be indexed $m = 0, 1, 2, 3, 4, 5$ with complex refractive indices $\tilde{n}_m$ and thicknesses $d_m \in \{\infty, 98\text{ nm}, 105\text{ nm}, d_{\text{top}}, 85\text{ nm}, \infty\}$.
 At normal incidence, the Fresnel reflection and transmission amplitudes at interface $(m, m+1)$ are:
$$r_{m,m+1} = \frac{\tilde{n}_m - \tilde{n}_{m+1}}{\tilde{n}_m + \tilde{n}_{m+1}}, \quad t_{m,m+1} = \frac{2\tilde{n}_m}{\tilde{n}_m + \tilde{n}_{m+1}}, \quad \beta_m = \frac{2\pi \tilde{n}_m d_m}{\lambda_{\text{nm}}} \quad (m=1,2,3,4)$$

* **Method A — Primary Engine (`atomistic_and_tmm.py`): $2\times 2$ Abeles Characteristic Matrix Product in Wavelength Space**
  $$\mathbf{M}(\lambda) = \mathbf{I}_{01}\mathbf{P}_1\mathbf{I}_{12}\mathbf{P}_2\mathbf{I}_{23}\mathbf{P}_3\mathbf{I}_{34}\mathbf{P}_4\mathbf{I}_{45}, \quad \mathbf{I}_{m,m+1} = \frac{1}{t_{m,m+1}}\begin{pmatrix} 1 & r_{m,m+1} \\ r_{m,m+1} & 1 \end{pmatrix}, \quad \mathbf{P}_m = \begin{pmatrix} e^{-i\beta_m} & 0 \\ 0 & e^{+i\beta_m} \end{pmatrix}$$
  $$r_{\text{tot}} = \frac{M_{10}}{M_{00}}, \quad t_{\text{tot}} = \frac{1}{M_{00}}, \quad R_{\text{TMM},1}(\lambda) = |r_{\text{tot}}|^2, \quad T_{\text{TMM},1}(\lambda) = \frac{\text{Re}(\tilde{n}_5)}{\text{Re}(\tilde{n}_0)} |t_{\text{tot}}|^2$$

* **Method B — Blinded Independent Verifier (`independent_verifier.py`): Recursive Rouard / Airy Amplitude Addition from Rear Interface ($m=4\to 0$) in Photon-Energy Space**
  Initialize at the rear interface $(4,5)$: $R_{\text{amp}}^{(4)} = r_{4,5}$, $T_{\text{amp}}^{(4)} = t_{4,5}$.
  For $m = 3, 2, 1, 0$ (going backward from layer 4 to incident medium 0):
  $$\phi_{m+1} = e^{i\beta_{m+1}}, \quad \text{denom}_m = 1.0 + r_{m,m+1}\,R_{\text{amp}}^{(m+1)}\,\phi_{m+1}^2$$
  $$R_{\text{amp}}^{(m)} = \frac{r_{m,m+1} + R_{\text{amp}}^{(m+1)}\,\phi_{m+1}^2}{\text{denom}_m}, \quad T_{\text{amp}}^{(m)} = \frac{t_{m,m+1}\,T_{\text{amp}}^{(m+1)}\,\phi_{m+1}}{\text{denom}_m}$$
  Then $R_{\text{TMM},1}(E) = |R_{\text{amp}}^{(0)}|^2$ and $T_{\text{TMM},1}(E) = \frac{\text{Re}(\tilde{n}_5)}{\text{Re}(\tilde{n}_0)} |T_{\text{amp}}^{(0)}|^2$.
  *(Mathematical identity theorem: $|r_{\text{tot}}|^2 \equiv |R_{\text{amp}}^{(0)}|^2$ and $|t_{\text{tot}}|^2 \equiv |T_{\text{amp}}^{(0)}|^2$ to machine precision $10^{-15}$ at every photon energy!)*

### 7.3 Coupled Coherent Top Stack + Textured Yablonovitch Light-Trapping & Downstream Silicon/IR Propagation
1. **Top Active Cell Absorptance $A_{\text{TMM},1}(\lambda)$ and Transmitted Flux $\Phi_{2,\text{TMM}}(\lambda)$:**
   * Coherent front-entry envelope $(1.0 - R_{\text{TMM},1}(\lambda))$ coupled with rear textured diffuser internal light trapping $f_{\text{abs},1}(E) = \frac{4n_1^2 \alpha_1(E) d_{\text{top}}}{1 + 4n_1^2 \alpha_1(E) d_{\text{top}}}$ and front ITO Beer-Lambert transmission $T_{\text{ITO,front}}(\lambda) = \exp(-4\pi k_{\text{ITO}}(\lambda) d_{\text{ITO}}/\lambda_{\text{nm}})$:
     $$A_{\text{TMM},1}(\lambda) = \left(1.0 - R_{\text{TMM},1}(\lambda)\right) \cdot T_{\text{ITO,front}}(\lambda) \cdot f_{\text{abs},1}(E)$$
   * Sub-bandgap & weakly-absorbed photons transmitted through the coherent multilayer stack into the Silicon wafer:
     $$T_{\text{stack,TMM},1}(\lambda) = T_{\text{TMM},1}(\lambda) \cdot \left(1.0 - f_{\text{abs},1}(E)\right)$$
     *(Note: Since $T_{\text{TMM},1}(\lambda) \le (1 - R_{\text{TMM},1}(\lambda)) T_{\text{ITO,front}}(\lambda)$, strict photon conservation $A_{\text{TMM},1}(\lambda) + T_{\text{stack,TMM},1}(\lambda) + R_{\text{TMM},1}(\lambda) \le 1.0$ holds identically at every wavelength!)*
   * $\Phi_{2,\text{TMM}}(\lambda) = \Phi_{\text{sun}}(\lambda) \cdot T_{\text{stack,TMM},1}(\lambda)$.
2. **Middle c-Si Wafer ($160\,\mu\text{m}$) & Bottom IR Scavenger under $\Phi_{2,\text{TMM}}$:**
   * Evaluate Step B (c-Si 2L and 3L cells + Drude FCA) and Step C (Bottom IR cell with $4n_3^2$ rear reflector and coherent $\text{MgF}_2/\text{ITO}$ entrance transmittance $1.0 - R_{\text{int},23}$, where $R_{\text{int},23} = 0.20\left(\frac{n_3 - 1.72}{n_3 + 1.72}\right)^2$ and $A_{\text{TMM},3} = (1.0 - R_{\text{int},23})\,f_{\text{abs},3}$) exactly as in Section 4.3.
   * Report:
     * `tmm_top_pce_percent`, `tmm_si_pce_percent`, `tmm_bottom_pce_percent`, `tmm_bottom_std_si_pce_percent`
     * `tmm_2layer_pce_percent`, `tmm_4t_std_si_pce_percent`, `tmm_4t_low_fca_pce_percent`
     * `tmm_sub_bandgap_transmittance_percent` (flux-weighted mean of $T_{\text{stack,TMM},1}(\lambda)\times 100$ over $E \in [0.75\text{ eV}, E_{g,\text{ind},1} - 0.02\text{ eV}]$)
     * `tmm_mean_front_reflectance_percent` (flux-weighted mean of $R_{\text{TMM},1}(\lambda)\times 100$ over $E \in [E_{g,\text{ind},1}, 3.50\text{ eV}]$).

---

## 8. Graded-Index Double-Layer ARC + High-Index $\text{TiO}_2$ Impedance-Matching Stack & 4-Metric Techno-Economic Figure-of-Merit Suite (v5.0)

### 8.1 7-Medium Graded-Index Double-ARC + $\text{TiO}_2$ Impedance-Matched Coherent Stack
To eliminate the $\sim 11\%\text{–}12\%$ broadband front reflection caused by the refractive-index step between $\text{ITO}$ ($n_2 \approx 1.88$) and the high-index pnictogen absorber ($n_4 = \sqrt{\varepsilon_{\infty,1}} \approx 2.8\text{–}3.1$), we insert a transparent rutile/anatase $\text{TiO}_2$ high-index optical impedance-matching layer ($m=3$) between Front $\text{ITO}$ ($m=2$) and the Top Active Absorber ($m=4$), forming a 7-medium graded-index coherent thin-film stack ($m \in \{0, 1, 2, 3, 4, 5, 6\}$):
* **Medium 0 (Superstrate — Air):** $\tilde{n}_0(\lambda) = 1.000 + 0i$
* **Medium 1 (Outer Quarter-Wave $\text{MgF}_2$ ARC, $d_1 = 94.0\text{ nm}$):** $\tilde{n}_1(\lambda) = 1.377 + \frac{0.0032}{\lambda_{\mu\text{m}}^2} + 0i$
* **Medium 2 (Front Transparent Electrode — Sputtered $\text{ITO}$, $d_2 = 80.0\text{ nm}$):**
  $$n_2(\lambda) = \max\left(1.45,\ 1.92 - 0.085\,\lambda_{\mu\text{m}}^2\right), \quad k_2(\lambda) = 0.0018 + 0.0065\,\lambda_{\mu\text{m}}^3$$
* **Medium 3 (High-Index $\text{TiO}_2$ Optical Impedance-Matching Buffer, $d_3 = 48.0\text{ nm}$):**
  $$n_3(\lambda) = 2.380 + \frac{0.0180}{\lambda_{\mu\text{m}}^2}, \quad k_3(\lambda) = 0.0004\,\lambda_{\mu\text{m}}^2, \quad \tilde{n}_3(\lambda) = n_3(\lambda) + i\,k_3(\lambda)$$
* **Medium 4 (Top Active Glass Absorber, $d_4 = d_{\text{top}}$):**
  $$n_4(\lambda) = \sqrt{\varepsilon_{\infty,1}} + \frac{0.035}{\lambda_{\mu\text{m}}^2}, \quad k_4(\lambda) = \frac{\alpha_1(E)\cdot (\lambda_{\text{nm}}\times 10^{-9})}{4\pi}, \quad \tilde{n}_4(\lambda) = n_4(\lambda) + i\,k_4(\lambda)$$
* **Medium 5 (Rear $\text{SiO}_2/\text{ITO}$ Optical Buffer, $d_5 = 82.0\text{ nm}$):**
  $$n_5(\lambda) = 1.720 + \frac{0.0040}{\lambda_{\mu\text{m}}^2}, \quad k_5(\lambda) = 0.0012\,\lambda_{\mu\text{m}}^2$$
* **Medium 6 (Substrate / Optical Couplant into c-Si):** $\tilde{n}_6(\lambda) = 1.520 + 0i$.

#### Dual-Redundancy Coherent Solvers on the 7-Medium Stack:
* **Method A (`atomistic_and_tmm.py`):** Vectorized $2\times 2$ Abeles Characteristic Matrix Product $\mathbf{M}(\lambda) = \mathbf{I}_{01}\mathbf{P}_1\mathbf{I}_{12}\mathbf{P}_2\mathbf{I}_{23}\mathbf{P}_3\mathbf{I}_{34}\mathbf{P}_4\mathbf{I}_{45}\mathbf{P}_5\mathbf{I}_{56}$ on the native ASTM G173-03 wavelength grid (`np.trapezoid`).
* **Method B (`independent_verifier.py`):** Recursive Rouard / Airy backward amplitude addition from interface $(5,6)$ down to $(0,1)$ on the $N_E = 8001$ photon-energy grid (`scipy.integrate.simpson`).
* **Front Window Transmission & Absorptance:**
  $$T_{\text{win,front}}(\lambda) = \exp\left(-\frac{4\pi \left(k_2(\lambda) d_2 + k_3(\lambda) d_3\right)}{\lambda_{\text{nm}}}\right)$$
  $$A_{\text{ARC},1}(\lambda) = \left(1.0 - R_{\text{ARC},1}(\lambda)\right) \cdot T_{\text{win,front}}(\lambda) \cdot f_{\text{abs},1}(E), \quad T_{\text{stack,ARC},1}(\lambda) = T_{\text{ARC},1}(\lambda) \cdot \left(1.0 - f_{\text{abs},1}(E)\right)$$

### 8.2 4-Metric Techno-Economic & Area-Constrained Figure-of-Merit Suite
To evaluate the economic return of every 2-Layer (`Top + c-Si`, $N_{\text{layers}}=2$, $k_{\text{add}}=1$) and 3-Layer (`Top + c-Si + Bottom`, $N_{\text{layers}}=3$, $k_{\text{add}}=2$) Silicon-Sandwich stack relative to a commercial single-junction c-Si baseline, we standardize the following reference techno-economic parameters:
* **Single-Junction c-Si Baseline:**
  $$\eta_{\text{Si,ref}} = 22.00\%, \quad P_{\text{Si,ref}} = 220.0\text{ W/m}^2, \quad C_{\text{Si,mod}} = \$40.00/\text{m}^2, \quad C_{\text{BOS,area}} = \$100.00/\text{m}^2$$
* **Subcell Process & TCO Coating Overhead:** $C_{\text{proc,sub}} = \$6.50/\text{m}^2$ per added thin-film subcell ($1\times \$6.50 = \$6.50/\text{m}^2$ for 2-Layer; $2\times \$6.50 = \$13.00/\text{m}^2$ for 3-Layer).
* **Incremental & Total Module Costs ($\$/\text{m}^2$):**
  * For 2-Layer (`Top + c-Si`, $N_{\text{layers}}=2$):
    $$\Delta C_{\text{2L}} = c_{\text{raw,top}} + 6.50, \quad C_{\text{mod,2L}} = C_{\text{Si,mod}} + \Delta C_{\text{2L}}$$
  * For 3-Layer (`Top + c-Si + Bottom`, $N_{\text{layers}}=3$):
    $$\Delta C_{\text{3L}} = c_{\text{raw,top}} + c_{\text{raw,bot}} + 13.00, \quad C_{\text{mod,3L}} = C_{\text{Si,mod}} + \Delta C_{\text{3L}}$$
* **Power Density ($\text{W/m}^2$ and $\text{W/ft}^2$, with $1\text{ ft}^2 = 0.09290304\text{ m}^2$):**
  $$P_{\text{m2}}(\eta) = 10.0 \cdot \eta\ (\%)\ [\text{W/m}^2], \quad P_{\text{sqft}}(\eta) = P_{\text{m2}}(\eta) \times 0.09290304\ [\text{W/ft}^2]$$

For both 2-Layer ($\eta = \eta_{\text{2L}}, N=2, \Delta C = \Delta C_{\text{2L}}, c_{\text{raw}} = c_{\text{raw,top}}$) and 3-Layer ($\eta = \eta_{\text{3L}}, N=3, \Delta C = \Delta C_{\text{3L}}, c_{\text{raw}} = c_{\text{raw,top}} + c_{\text{raw,bot}}$), both primary and independent engines must compute and cross-verify to within $10^{-4}$:
1. **Relative Efficiency Gain Multiplier ($G_\eta$):**
   $$G_\eta = \frac{\eta}{\eta_{\text{Si,ref}}} = \frac{\eta}{22.00}$$
2. **Metric 1 — Normalized Multi-Junction Cost-Efficiency Ratio ($\text{CER}_N$):**
   *(Compares the efficiency gain multiplier $G_\eta$ against the total stack module cost normalized by $N$ standalone c-Si module costs $N \cdot C_{\text{Si,mod}}$):*
   $$\text{CER}_N = \frac{\eta / \eta_{\text{Si,ref}}}{\left(C_{\text{Si,mod}} + \Delta C\right) / \left(N \cdot C_{\text{Si,mod}}\right)} = \frac{N \cdot C_{\text{Si,mod}} \cdot (\eta / 22.00)}{C_{\text{Si,mod}} + \Delta C}$$
3. **Metric 2 — Marginal Cost per Incremental Watt ($\text{MCIW}_{\text{raw}}$ and $\text{MCIW}_{\text{full}}$ in $\$/\Delta\text{W}_{\text{p}}$):**
   $$\Delta P_{\text{m2}} = 10.0 \cdot (\eta - 22.00)\ [\text{W/m}^2]$$
   $$\text{MCIW}_{\text{raw}} = \frac{c_{\text{raw}}}{\Delta P_{\text{m2}}}\ [\$/\Delta\text{W}_{\text{p}}], \quad \text{MCIW}_{\text{full}} = \frac{\Delta C}{\Delta P_{\text{m2}}}\ [\$/\Delta\text{W}_{\text{p}}]$$
   *(Reference single-junction c-Si cost per Watt is $C_{\text{Si,mod}} / P_{\text{Si,ref}} = 40.00 / 220.0 = \$0.1818/\text{W}_{\text{p}}$; any $\text{MCIW}_{\text{full}} < \$0.1818/\Delta\text{W}_{\text{p}}$ lowers module $\$/\text{W}_{\text{p}}$).*
4. **Metric 3 — Factory-Gate Module Cost-Performance Ratio ($\text{CPR}_{\text{mod}}$):**
   $$\text{CPR}_{\text{mod}} = \frac{\eta / 22.00}{1.0 + \Delta C / C_{\text{Si,mod}}}$$
5. **Metric 4 — Area-Constrained System Value Index ($\text{SVI}_{\text{BOS}}$, Sofia-NREL Area-BOS Credit):**
   $$\text{SVI}_{\text{BOS}} = \frac{\eta / 22.00}{\left(C_{\text{Si,mod}} + \Delta C + C_{\text{BOS,area}}\right) / \left(C_{\text{Si,mod}} + C_{\text{BOS,area}}\right)} = \frac{140.0 \cdot (\eta / 22.00)}{140.0 + \Delta C}$$

---

## 9. Phase 9 Engineering Extensions: Lab-Ready Synthesis & Defect Supercell Dossiers (9A), Contrastive Failure Classifier (9B), and Real-World Angular / Thermal / 25-Year Arrhenius LCOE Stress-Test (9C) (v6.0)

### 9.1 Phase 9A — Stoichiometric Lab Synthesis Recipes ($\le 500^\circ\text{C}$) & 3D `doped` Defect Supercell Decks
1. **Exact $10.0\text{ mmol}$ Batch Precursor Mass Balance:**
   * Given a reduced formula unit $\prod_i E_i^{\nu_i}$ with formula-unit molar mass $M_{\text{FU}} = \sum_i \nu_i M_i\text{ [g/mol]}$, the exact target product mass for a $n_{\text{batch}} = 0.010\text{ mol}$ ($10.0\text{ mmol}$) batch is:
     $$m_{\text{target,g}} = 0.010 \cdot M_{\text{FU}}$$
   * Each element $E_i$ is supplied by a designated commercial reagent $R_i$ with molar mass $M(R_i)$ and metal/anion atom count $a_i$ per reagent formula unit, requiring reagent moles $n(R_i) = 0.010 \cdot \frac{\nu_i}{a_i}$ and reagent mass $m(R_i) = n(R_i) \cdot M(R_i)\text{ [g]}$ (with a $+5.0\%$ volatile overpressure margin recorded separately for $\text{S}, \text{Se}, \text{Cl}, \text{Br}, \text{I}$ chalcogen/halide sources).
   * **Dual-Redundancy Elemental Mass-Conservation Invariant:**
     Both the primary engine (`atomistic_and_tmm.py`) and the blinded verifier (`independent_verifier.py`) verify that the sum of elemental masses supplied by the stoichiometric reagents equals $m_{\text{target,g}}$ to within $10^{-6}\text{ g}$.
2. **Stage 5 `doped` Intrinsic Vacancy & Antisite Defect Supercell Generation:**
   * Given conventional/primitive unit-cell lattice lengths $(a, b, c)$, the supercell expansion integers $(N_a, N_b, N_c)$ are chosen as:
     $$N_a = \max\!\left(1, \left\lceil \frac{10.0}{a} \right\rceil\right), \quad N_b = \max\!\left(1, \left\lceil \frac{10.0}{b} \right\rceil\right), \quad N_c = \max\!\left(1, \left\lceil \frac{10.0}{c} \right\rceil\right)$$
     yielding supercell site count $N_{\text{super}} = N_a N_b N_c N_{\text{unit}}$ and minimum periodic image separation $L_{\min} = \min(N_a a, N_b b, N_c c) \ge 10.0\text{ \AA}$.
   * Isotropic Freysoldt-Neugebauer-Van de Walle (FNV) point-charge electrostatic finite-size correction energy (Madelung constant $\alpha_{\text{M}} = 2.8373$ for cubic-equivalent volume $L_{\text{eff}} = \Omega_{\text{super}}^{1/3}$):
     $$E_{\text{FNV}}(q) = \frac{q^2 \alpha_{\text{M}} \cdot 14.399645}{\varepsilon_0 \cdot L_{\text{eff}}}\text{ [eV]}$$
     evaluated at $q = \pm 1, \pm 2$.

### 9.2 Phase 9B — Extended 117-Candidate Live MP Discovery Funnel & Contrastive Failure Classifier Audit
1. **Full 117-Candidate Live MP Cache Sweep:**
   * Evaluates all $N_{\text{MP}} = 117$ charge-neutral, RoHS-clean semiconductors in `data/mp_live_candidates_cache.json` across the 5-stage funnel (`117 -> Stage 2 -> Stage 3 -> Gate A -> Stage 4/5 Finalists`).
2. **Contrastive Failure Memory Classifier Separation Margin ($\Delta S_{\text{contrastive}}$):**
   * For every candidate with 128-dimensional L2-normalized embedding $\hat{\mathbf{u}}_i$, define the positive centroid $\bar{\mathbf{c}}_{+} = \frac{\sum_{j \in \mathcal{P}} \hat{\mathbf{u}}_j}{\|\sum_{j \in \mathcal{P}} \hat{\mathbf{u}}_j\|_2}$ (over promoted finalists $\mathcal{P}$) and negative failure centroid $\bar{\mathbf{c}}_{-} = \frac{\sum_{k \in \mathcal{N}} \hat{\mathbf{u}}_k}{\|\sum_{k \in \mathcal{N}} \hat{\mathbf{u}}_k\|_2}$ (over rejected failures $\mathcal{N}$).
   * The Contrastive Failure Margin for candidate $i$ is:
     $$M_{\text{contrastive}}(i) = \hat{\mathbf{u}}_i \cdot \bar{\mathbf{c}}_{+} - \hat{\mathbf{u}}_i \cdot \bar{\mathbf{c}}_{-}$$
   * Both primary and blinded engines verify that the mean margin of promoted finalists exceeds the mean margin of rejected candidates ($\bar{M}_{\mathcal{P}} - \bar{M}_{\mathcal{N}} > 0$).

### 9.3 Phase 9C — Oblique-Incidence ($0^\circ\text{–}60^\circ$) S/P-Polarized Coherent TMM, Operating Temperature ($25^\circ\text{C}\text{–}65^\circ\text{C}$), and 25-Year Arrhenius LCOE Stress-Test
1. **Oblique-Incidence ($\theta_0 \in \{0^\circ, 30^\circ, 45^\circ, 60^\circ\}$) S/P-Polarized 7-Medium Coherent Optics:**
   * By Snell's Law in layer $m \in \{0, \dots, 6\}$ with complex index $\tilde{n}_m(\lambda)$:
     $$\cos\theta_m = \sqrt{1.0 - \left(\frac{\tilde{n}_0 \sin\theta_0}{\tilde{n}_m}\right)^2}, \quad \beta_m(\lambda, \theta_0) = \frac{2\pi \tilde{n}_m d_m \cos\theta_m}{\lambda_{\text{nm}}}$$
   * Polarization-dependent optical admittances ($s$-TE and $p$-TM):
     $$\eta_m^{(s)} = \tilde{n}_m \cos\theta_m, \quad \eta_m^{(p)} = \frac{\tilde{n}_m}{\cos\theta_m}$$
   * Fresnel interface reflection and transmission amplitudes for polarization $\sigma \in \{s, p\}$:
     $$r_{m,m+1}^{(\sigma)} = \frac{\eta_m^{(\sigma)} - \eta_{m+1}^{(\sigma)}}{\eta_m^{(\sigma)} + \eta_{m+1}^{(\sigma)}}, \quad t_{m,m+1}^{(\sigma)} = \frac{2\eta_m^{(\sigma)}}{\eta_m^{(\sigma)} + \eta_{m+1}^{(\sigma)}}$$
   * Unpolarized reflectance and transmittance into Medium 6:
     $$R_{\text{ARC},1}(\lambda, \theta_0) = \frac{1}{2}\left(|r_{\text{tot}}^{(s)}|^2 + |r_{\text{tot}}^{(p)}|^2\right)$$
     $$T_{\text{ARC},1}(\lambda, \theta_0) = \frac{1}{2}\left(\frac{\text{Re}(\eta_6^{(s)})}{\text{Re}(\eta_0^{(s)})}|t_{\text{tot}}^{(s)}|^2 + \frac{\text{Re}(\eta_6^{(p)})}{\text{Re}(\eta_0^{(p)})}|t_{\text{tot}}^{(p)}|^2\right)$$
   * **Method A (`atomistic_and_tmm.py`):** $2\times 2$ Abeles matrix multiplication for $s$ and $p$ polarizations on the wavelength grid (`np.trapezoid`).
   * **Method B (`independent_verifier.py`):** Recursive Rouard / Airy backward amplitude addition for $s$ and $p$ polarizations on the photon-energy grid (`scipy.integrate.simpson`).
   * **Angular Modifier $\text{IAM}(\theta_0)$:** Evaluated at $\theta_0 = 0^\circ, 30^\circ, 45^\circ, 60^\circ$, plus hemisphere-weighted daily effective reflectance $\bar{R}_{\text{hemi}} = 0.35 R(0^\circ) + 0.35 R(30^\circ) + 0.20 R(45^\circ) + 0.10 R(60^\circ)$.

2. **Field Operating Temperature Coefficient ($T_{\text{cell}} = 25^\circ\text{C} \rightarrow 45^\circ\text{C} \rightarrow 65^\circ\text{C}$):**
   * For a subcell with band gap $E_g\text{ [eV]}$ and $25^\circ\text{C}$ ($298.15\text{ K}$) efficiency $\eta(25^\circ\text{C})$, the relative temperature coefficient $\gamma_{\text{rel}}(E_g)\text{ [K}^{-1}\text{]}$ follows the thermodynamic open-circuit voltage drift:
     $$\gamma_{\text{rel}}(E_g) = -\frac{0.00440}{E_g^{0.65}}\text{ [K}^{-1}\text{]}$$
     *(giving $-0.409\%/\text{K}$ for $1.12\text{ eV}$ c-Si, $-0.301\%/\text{K}$ for $1.79\text{ eV}$ Top Active Glass, and $-0.461\%/\text{K}$ for $0.93\text{ eV}$ Bottom IR Scavenger).*
   * Subcell efficiency at temperature $T_{\text{C}} \in \{45^\circ\text{C}, 65^\circ\text{C}\}$ ($\Delta T = T_{\text{C}} - 25.0$):
     $$\eta_{\text{sub}}(T_{\text{C}}) = \eta_{\text{sub}}(25^\circ\text{C}) \cdot \left(1.0 + \gamma_{\text{rel}}(E_g)\cdot \Delta T\right)$$
   * Total 4T stack efficiency at $45^\circ\text{C}$ (NOCT) and $65^\circ\text{C}$ (desert peak) is $\eta_{\text{4T}}(T_{\text{C}}) = \eta_{\text{top}}(T_{\text{C}}) + \eta_{\text{Si}}(T_{\text{C}}) + \eta_{\text{bot}}(T_{\text{C}})$, with effective stack temperature coefficient:
     $$\beta_{\text{4T,rel}} = \frac{\eta_{\text{4T}}(65^\circ\text{C}) - \eta_{\text{4T}}(25^\circ\text{C})}{40.0 \cdot \eta_{\text{4T}}(25^\circ\text{C})} \times 100\text{ [\%/K]}$$

3. **25-Year Arrhenius Ion-Migration Reliability & Real-World LCOE ($\$/\text{kWh}$ and $\text{cents/kWh}$):**
   * Given the 11-image NEB migration barrier $E_{\text{mig}}^{\text{NEB}}\text{ [eV]}$ of the limiting subcell (`min(E_mig_top, E_mig_bot)`), the annual kinetic + environmental degradation rate $r_{\text{deg}}\text{ [yr}^{-1}\text{]}$ at field temperature $T_{\text{field}} = 318.15\text{ K}$ ($45^\circ\text{C}$) is:
     $$r_{\text{deg}} = 0.0035 + 0.0010 \cdot \exp\!\left(-\frac{E_{\text{mig}}^{\text{NEB}} - 0.65}{k_{\text{B}} T_{\text{field}}}\right)$$
     *(For immobile lattices with $E_{\text{mig}}^{\text{NEB}} \ge 0.99\text{ eV}$, the exponential ionic drift term vanishes to $< 10^{-8}\text{ yr}^{-1}$, locking degradation at the $0.35\%/\text{yr}$ glass-encapsulated baseline and retaining $91.60\%$ of initial power at Year 25).*
   * **25-Year Discounted LCOE ($r_{\text{disc}} = 6.0\%$, Solar Resource $Y_0 = 1800\text{ kWh/kW}_{\text{p}}\text{/yr} = 1.80\text{ kWh/W}_{\text{p}}\text{/yr}$, Inverter/Electronics BOS $C_{\text{BOS,power}} = \$0.22/\text{W}_{\text{p}}$, O&M $C_{\text{OM}} = \$2.50/\text{m}^2/\text{yr}$):**
     * Initial installed CAPEX ($\$/\text{m}^2$) for a stack with module cost $C_{\text{mod}}\text{ [\$/m}^2\text{]}$ and nameplate power $P_{\text{m2}} = 10 \cdot \eta(25^\circ\text{C})\text{ [W}_{\text{p}}\text{/m}^2\text{]}$:
       $$\text{CAPEX}_{\text{m2}} = C_{\text{mod}} + C_{\text{BOS,area}} + C_{\text{BOS,power}} \cdot P_{\text{m2}}$$
     * Discounted 25-year energy yield per $\text{m}^2$ (accounting for NOCT $45^\circ\text{C}$ thermal derating $f_{\text{NOCT}} = \eta(45^\circ\text{C})/\eta(25^\circ\text{C})$ and annual degradation $r_{\text{deg}}$):
       $$E_{\text{disc,25yr}} = \sum_{t=1}^{25} \frac{(P_{\text{m2}} / 1000.0) \cdot 1800.0 \cdot f_{\text{NOCT}} \cdot (1.0 - r_{\text{deg}})^{t-1}}{(1.0 + 0.06)^t}\text{ [kWh/m}^2\text{]}$$
     * Discounted 25-year O&M cost per $\text{m}^2$:
       $$\text{OM}_{\text{disc,25yr}} = \sum_{t=1}^{25} \frac{2.50}{(1.0 + 0.06)^t}\text{ [\$/m}^2\text{]}$$
     * Levelized Cost of Energy (in $\text{cents/kWh}$):
       $$\text{LCOE}_{\text{cents/kWh}} = 100.0 \times \frac{\text{CAPEX}_{\text{m2}} + \text{OM}_{\text{disc,25yr}}}{E_{\text{disc,25yr}}}$$
     *(Compared directly against standalone $22.0\%$ single-junction c-Si baseline $\text{LCOE}_{\text{Si,ref}}$ under identical $45^\circ\text{C}$ NOCT and $0.45\%/\text{yr}$ c-Si degradation).*

---

## 10. Phase 10 Engineering Extensions: 2D Thickness & Graded-ARC Global Optimization (10A), Bifacial Albedo Harvesting (10B), and SPICE Subcell $J\text{–}V$ String Architecture (10C) (v7.0)

### 10.1 Phase 10A — 2D Thickness & Graded-ARC Global Coherent Optimization
1. **7-Layer Coherent Stack Parameter Space ($2^4 = 16$ Full-Factorial Design Grid):**
   * Given baseline candidate film thicknesses $d_{1,0}\text{ [nm]}$ (Top Active Glass) and $d_{3,0}\text{ [nm]}$ (Bottom IR Scavenger), we evaluate the coherent 7-medium optical stack (`Air / d_MgF2 / 80 nm ITO / d_TiO2 / d_top Absorber / 82 nm Buffer / Couplant -> 160 um c-Si -> d_bot Absorber / 4n^2 Ag Mirror`) over the $2^4 = 16$ full-factorial design grid:
     $$d_{\text{MgF}_2} \in \{88.0, 94.0\}\text{ nm}, \quad d_{\text{TiO}_2} \in \{42.0, 48.0\}\text{ nm}$$
     $$d_{\text{top}} \in \{d_{1,0},\; \text{round}(1.15\,d_{1,0}, 1)\}\text{ nm}, \quad d_{\text{bot}} \in \{d_{3,0},\; \text{round}(1.15\,d_{3,0}, 1)\}\text{ nm}$$
   * Note that front window parasitic attenuation in Layer 2 ($80\text{ nm}$ ITO) and Layer 3 ($d_{\text{TiO}_2}$ $\text{TiO}_2$) scales with the actual $\text{TiO}_2$ thickness:
     $$T_{\text{win,front}}(\lambda) = \exp\!\left(-\frac{4\pi\left(k_{\text{ITO}}(\lambda)\cdot 80.0 + k_{\text{TiO}_2}(\lambda)\cdot d_{\text{TiO}_2}\right)}{\lambda_{\text{nm}}}\right)$$
   * **Optimization Objective:** Maximize the unrounded 1-sun AM1.5G coherent 4T low-FCA stack efficiency $\eta_{\text{4T,opt}}(d_{\text{MgF}_2}^*, d_{\text{TiO}_2}^*, d_{\text{top}}^*, d_{\text{bot}}^*)$ subject to strict photon conservation $A_1(\lambda) + T_1(\lambda) + R_1(\lambda) \le 1.0 + 10^{-9}$ at every wavelength.
   * **Dual-Redundancy Cross-Check:** Primary engine (`atomistic_and_tmm.py`) finds and evaluates $\eta_{\text{4T,opt}}$ via $2\times 2$ Abeles matrix multiplication (`np.trapezoid`), while the blinded verifier (`independent_verifier.py`) independently evaluates the 16-point factorial grid via Recursive Rouard/Airy amplitude addition (`scipy.integrate.simpson`), verifying agreement within $\le 0.05\%$.

### 10.2 Phase 10B — Bifacial Ground-Albedo ($R_{\text{albedo}} \in \{0.00, 0.20, 0.30\}$) Rear-Side IR Harvesting
1. **Bifacial Rear-Side Illumination Physics (at Optimal Thickness Tuple $(d_{\text{MgF}_2}^*, d_{\text{TiO}_2}^*, d_{\text{top}}^*, d_{\text{bot}}^*)$):**
   * In a 4-Terminal Silicon-Sandwich with a transparent conductive rear electrode + dielectric/grid aperture ($f_{\text{rear,aperture}} = 0.78$, rear TCO transmittance $T_{\text{ITO,rear}} = 0.92$), diffuse ground-reflected AM1.5G solar photon flux entering the rear of the Bottom IR Scavenger under ground albedo $R_{\text{albedo}} \in \{0.00, 0.20, 0.30\}$ is:
     $$\Phi_{\text{rear}}(\lambda) = R_{\text{albedo}} \cdot f_{\text{rear,aperture}} \cdot \Phi_{\text{sun}}(\lambda) = 0.78\,R_{\text{albedo}}\,\Phi_{\text{sun}}(\lambda)$$
   * The Bottom IR Scavenger receives combined front-transmitted + rear-albedo photon flux:
     $$\Phi_{3,\text{tot}}(\lambda, R_{\text{albedo}}) = \Phi_{3,\text{front}}(\lambda) + \Phi_{\text{rear}}(\lambda)$$
     and harvests it with external absorptance $A_{\text{ARC},3}(\lambda) = (1.0 - R_{\text{int},23})\,f_{\text{abs},3}(\lambda, d_{\text{bot}}^*)$.
   * Unabsorbed rear-albedo photons transmit upward through the Bottom IR Scavenger and rear TCO ($T_{\text{ITO,rear}} = 0.92$) into the bifacial $160\text{ }\mu\text{m}$ c-Si wafer:
     $$\Phi_{2,\text{rear}}(\lambda, R_{\text{albedo}}) = \Phi_{\text{rear}}(\lambda)\cdot\left(1.0 - f_{\text{abs},3}(\lambda, d_{\text{bot}}^*)\right)\cdot 0.92$$
     so the middle c-Si wafer receives total photon flux:
     $$\Phi_{2,\text{tot}}(\lambda, R_{\text{albedo}}) = \Phi_{2,\text{front}}(\lambda) + \Phi_{2,\text{rear}}(\lambda, R_{\text{albedo}})$$
     and harvests it with external absorptance $0.98\,f_{\text{abs,Si,3L}}(\lambda)$.
   * **Equivalent Bifacial 1-Sun Efficiency ($\text{PCE}_{\text{bifacial}}$), Power Density ($\text{W/ft}^2$), Bifacial Gain ($\%$), and 25-Year Bifacial LCOE ($\text{cents/kWh}$):**
     $$\eta_{\text{4T,bifacial}}(R_{\text{albedo}}) = \eta_{\text{top}}^* + \eta_{\text{Si}}^*(R_{\text{albedo}}) + \eta_{\text{bot}}^*(R_{\text{albedo}})$$
     $$P_{\text{sqft}}(R_{\text{albedo}}) = 10.0 \cdot \eta_{\text{4T,bifacial}}(R_{\text{albedo}}) \cdot 0.09290304\text{ [W/ft}^2\text{]}$$
     $$\text{Gain}_{\text{bifacial},20\%}(\%) = \frac{\eta_{\text{4T,bifacial}}(0.20) - \eta_{\text{4T,bifacial}}(0.00)}{\eta_{\text{4T,bifacial}}(0.00)} \times 100$$
   * **25-Year Bifacial LCOE at $R_{\text{albedo}} = 0.20$:** Evaluated using the exact Section 9.3 discounted 25-year LCOE formula (`_compute_lcoe_cents_kwh`) with $P_{\text{m2,bifacial}} = 10.0 \cdot \text{round}(\eta_{\text{4T,bifacial}}(0.20), 2)\text{ [W}_{\text{p}}\text{/m}^2\text{]}$, active layer material costs scaled to the optimized thicknesses $(d_{\text{top}}^* / d_{1,0})\cdot C_{\text{raw,top}}$ and $(d_{\text{bot}}^* / d_{3,0})\cdot C_{\text{raw,bot}}$, NOCT derating factor $f_{\text{NOCT,3L}}$, and Arrhenius degradation rate $r_{\text{deg}}$ (whilst keeping nameplate inverter/power BOS scaled to $P_{\text{m2,bifacial}}$).

### 10.3 Phase 10C — Subcell $J\text{–}V$ Operating-Point (`J_sc`, `V_oc`, `FF`, `V_mp`) & Integer Parallel-String Voltage-Matching Dossier
1. **Exact Subcell $J\text{–}V$ Operating Point Decomposition:**
   * At the optimal 7-medium Graded-ARC stack configuration ($R_{\text{albedo}} = 0.00$, $T = 300\text{ K}$, $V_{\text{th}} = 0.02585199\text{ V}$), both primary and blinded engines extract the full 1-sun operating point for all 3 subcells ($k \in \{\text{Top}, \text{Si}, \text{Bot}\}$):
     * Short-circuit current density $J_{\text{sc},k}\text{ [mA/cm}^2\text{]}$,
     * Open-circuit voltage $V_{\text{oc},k}\text{ [V]}$,
     * Fill factor $\text{FF}_k = \frac{v_k - \ln(v_k + 0.72)}{v_k + 1.0}$ where $v_k = V_{\text{oc},k} / V_{\text{th}}$,
     * Maximum-power-point voltage $V_{\text{mp},k}\text{ [V]}$ from the analytical single-diode maximum power condition:
       $$V_{\text{mp},k} = V_{\text{oc},k} - V_{\text{th}}\ln\!\left(\frac{V_{\text{oc},k}}{V_{\text{th}}} + 0.72\right)$$
2. **4-Terminal Module Integer Series-Cell String Voltage Matching ($N_{\text{top}} : N_{\text{Si}} : N_{\text{bot}}$):**
   * Given a standard $N_{\text{Si}} = 72$-cell crystalline silicon string with bus voltage $V_{\text{bus,Si}} = N_{\text{Si}} \cdot V_{\text{mp,Si}}$ (using unrounded $V_{\text{mp},k}$ before final rounding), the optimal integer series cell counts $N_{\text{top}}$ and $N_{\text{bot}}$ for parallel DC-bus coupling without DC-DC converter step-up loss are:
     $$N_{\text{top}} = \text{int}\!\left(\text{round}\!\left(\frac{72 \cdot V_{\text{mp,Si}}}{V_{\text{mp,top}}}\right)\right), \quad N_{\text{bot}} = \text{int}\!\left(\text{round}\!\left(\frac{72 \cdot V_{\text{mp,Si}}}{V_{\text{mp,bot}}}\right)\right)$$
   * The string voltage mismatch percentage for parallel string connection is:
     $$\Delta V_{\text{mismatch,top}}(\%) = \frac{|N_{\text{top}} V_{\text{mp,top}} - V_{\text{bus,Si}}|}{V_{\text{bus,Si}}} \times 100, \quad \Delta V_{\text{mismatch,bot}}(\%) = \frac{|N_{\text{bot}} V_{\text{mp,bot}} - V_{\text{bus,Si}}|}{V_{\text{bus,Si}}} \times 100$$

---

## 11. Phase 11 (`v8.0`) — Realistic Synthesis Practicality, Contact Band Alignment, Non-Radiative SRH Device Physics & 4-Path Commercialization Techno-Economics

### 11.1 Phase 11A — Live DFT Chemical-Potential Synthesis Window, TCO `InterfacialReactivity`, Contact Band Alignment & Supply-Chain Practicality Score ($N=8$ Finalists)
1. **Live Materials Project DFT Convex-Hull & `InterfacialReactivity` Inputs (`data/mp_thermo_interface_cache.json`):**
   * For each finalist with stoichiometry $\{n_Z\}$ ($N_{\text{tot}} = \sum_Z n_Z$), structural dimensionality $D \in \{\text{"3D"}, \text{"Quasi-2D"}, \text{"1D-Chain"}, \text{"0D-Isolated"}\}$, and indirect gap $E_{g,\text{ind}}\text{ [eV]}$:
     * Live GGA/GGA+U hull distance $E_{\text{hull,GGA}}\text{ [meV/atom]}$.
     * Limiting anion chemical-potential window width $\Delta\mu_{\text{anion}}\text{ [eV]}$:
       $$\Delta\mu_{\text{anion}} = \begin{cases} \min(\Delta\mu_{\text{O}}, \Delta\mu_X) & \text{if } \text{O} \in \{n_Z\}, \\ \Delta\mu_X & \text{otherwise}, \end{cases} \quad X \in \{\text{S}, \text{Se}\}$$
     * Limiting cation chemical-potential window width $\Delta\mu_{\text{cation,min}} = \min_{Z \notin \{\text{O, S, Se}\}} \Delta\mu_Z\text{ [eV]}$.
     * Worst-case normalized TCO interfacial reaction energies $(\Delta E_{\text{rxn,SnO2}}, \Delta E_{\text{rxn,In2O3}}, \Delta E_{\text{rxn,TiO2}})\text{ [meV/atom]}$ computed via `pymatgen.analysis.interface_reactions.InterfacialReactivity`.
2. **Lone-Pair-Corrected Mulliken Band Edges ($E_{\text{CBM}}, E_{\text{VBM}}$ vs. Vacuum) & ETL/HTL Offsets:**
   * Fixed Pearson Mulliken elemental electronegativities $\chi_{M,Z}\text{ [eV]}$:
     `{"Bi": 4.69, "Sb": 4.85, "In": 3.10, "Ga": 3.20, "Cu": 4.48, "Ag": 4.44, "Sn": 4.30, "O": 7.54, "S": 6.22, "Se": 5.89}`
   * Geometric-mean electronegativity and $ns^2$ ($\text{Bi}^{3+}/\text{Sb}^{3+}$) s-p antibonding upward valence/conduction band shift $\Delta E_{\text{lp}}$:
     $$\chi_{\text{comp}} = \exp\!\left(\frac{1}{N_{\text{tot}}} \sum_Z n_Z \ln(\chi_{M,Z})\right), \qquad \Delta E_{\text{lp}} = 1.65 \cdot \frac{n_{\text{Bi}} + n_{\text{Sb}}}{N_{\text{tot}}}$$
     $$E_{\text{CBM}} = -\chi_{\text{comp}} + \Delta E_{\text{lp}} + 0.5\,E_{g,\text{ind}}, \qquad E_{\text{VBM}} = -\chi_{\text{comp}} + \Delta E_{\text{lp}} - 0.5\,E_{g,\text{ind}}$$
   * Conduction-band offsets $\Delta E_c = E_{\text{CBM,ETL}} - E_{\text{CBM}}$ against $\text{TiO}_2$ ($-4.20\text{ eV}$) and $\text{SnO}_2$ ($-4.35\text{ eV}$), and valence-band offset against $\text{NiO}_x$ ($-5.30\text{ eV}$):
     $$\Delta E_{c,\text{TiO2}} = -4.20 - E_{\text{CBM}}, \quad \Delta E_{c,\text{SnO2}} = -4.35 - E_{\text{CBM}}, \quad \Delta E_{v,\text{NiOx}} = E_{\text{VBM}} + 5.30$$
   * Best ETL (`"TiO2"` if $|\Delta E_{c,\text{TiO2}}| \le |\Delta E_{c,\text{SnO2}}|$ else `"SnO2"`), `best_cbo_ev` $= \Delta E_{c,\text{best}}$, and interfacial contact barrier/cliff voltage penalty:
     $$\Delta V_{\text{contact}} = \max(0.0,\; -\Delta E_{c,\text{best}} - 0.25) + \max(0.0,\; \Delta E_{c,\text{best}} - 0.20)$$
3. **Antisite Disorder, Ribbon Orientation & Critical-Mineral Supply Risk:**
   * Cation-antisite disorder voltage penalty $\Delta V_{\text{antisite}}\text{ [V]}$:
     $$\Delta V_{\text{antisite}} = \begin{cases} 0.110 & \text{if } |\{n_Z\}| \ge 4 \text{ and } \{\text{Cu}, \text{Sn}\} \subseteq \{n_Z\}, \\ 0.045 & \text{else if } \text{Cu} \in \{n_Z\} \text{ or } \text{Ag} \in \{n_Z\}, \\ 0.015 & \text{otherwise.} \end{cases}$$
   * Ribbon orientation transport factor $f_{\text{orient}}$: $0.95$ if $D = \text{"3D"}$, $0.88$ if $D = \text{"Quasi-2D"}$ (`[hk1]`-textured), else $0.72$.
   * Critical-mineral supply risk index $S_{\text{crit}} = (0.65\,n_{\text{In}} + 0.45\,n_{\text{Ga}} + 0.55\,n_{\text{Ag}}) / N_{\text{tot}}$.
   * **Synthesis & Commercialization Practicality Score ($\text{SPS} \in [0, 100]$):**
     $$\text{SPS} = \text{clip}\!\Big(92.0 - 0.90\,E_{\text{hull,GGA}} + 10.0\,\min(0.80, \Delta\mu_{\text{anion}}) + 8.0\,\min(0.50, \Delta\mu_{\text{cation,min}}) - 0.25\,|\Delta E_{\text{rxn,In2O3}}| - 0.50\,|\Delta E_{\text{rxn,SnO2}}| - 95.0\,S_{\text{crit}} - 110.0\,\Delta V_{\text{antisite}} - 25.0\,\Delta V_{\text{contact}},\; 0.0,\; 100.0\Big)$$

### 11.2 Phase 11B — Realistic Non-Radiative SRH Device Model vs. Radiative Ceiling & $\pm 0.15\text{ eV}$ Gap Sensitivity ($N=15$ Pairs)
1. **Realistic Thin-Film Subcell Operating Solver ($T = 300\text{ K}$, $V_{\text{th}} = 0.02585199\text{ V}$):**
   * Evaluated at Phase 10 optimal thicknesses $(d_{\text{MgF}_2}^*, d_{\text{TiO}_2}^*, d_{\text{top}}^*, d_{\text{bot}}^*)$ across 3 non-radiative External Radiative Efficiency ($\text{ERE}$) maturity tiers:
     * **Conservative First-Gen Polycrystalline:** $\text{ERE} = 10^{-5}$, $f_{\text{ap,scen}} = 0.90$, $R_s = 3.2\text{ }\Omega\cdot\text{cm}^2$, $\alpha_{\text{def}} = 1.00$.
     * **Base-Case Engineered Pilot Module:** $\text{ERE} = 10^{-4}$, $f_{\text{ap,scen}} = 0.96$, $R_s = 1.8\text{ }\Omega\cdot\text{cm}^2$, $\alpha_{\text{def}} = 0.65$.
     * **Mature Industrial Target:** $\text{ERE} = 5\times 10^{-3}$, $f_{\text{ap,scen}} = 0.98$, $R_s = 0.9\text{ }\Omega\cdot\text{cm}^2$, $\alpha_{\text{def}} = 0.35$.
   * From radiative $(J_{\text{sc,rad},k}, V_{\text{oc,rad},k})$:
     $$f_{\text{coll},k} = f_{\text{orient},k}\cdot f_{\text{ap,scen}}, \qquad J_{\text{sc,real},k} = J_{\text{sc,rad},k}\cdot f_{\text{coll},k}$$
     $$\Delta V_{\text{loss},k} = -V_{\text{th}}\ln(\text{ERE}) + \alpha_{\text{def}}\cdot(\Delta V_{\text{antisite},k} + \Delta V_{\text{contact},k})$$
     $$V_{\text{oc,real},k} = \max\!\left(0.05,\; V_{\text{oc,rad},k} + V_{\text{th}}\ln(f_{\text{coll},k}) - \Delta V_{\text{loss},k}\right)$$
     $$v_k = \frac{V_{\text{oc,real},k}}{V_{\text{th}}}, \quad \text{FF}_{0,k} = \frac{v_k - \ln(v_k + 0.72)}{v_k + 1.0}$$
     $$r_{s,k} = \frac{R_s \cdot (J_{\text{sc,real},k} / 1000.0)}{V_{\text{oc,real},k}}, \quad r_{\text{sh},k} = \frac{1200.0 \cdot (J_{\text{sc,real},k} / 1000.0)}{V_{\text{oc,real},k}}$$
     $$\text{FF}_{\text{real},k} = \text{FF}_{0,k} \cdot \max(0.35,\; 1.0 - 1.1\,r_{s,k}) \cdot \max\!\left(0.35,\; 1.0 - \frac{(v_k + 0.70)\,\text{FF}_{0,k}}{v_k\,r_{\text{sh},k}}\right)$$
     $$\eta_{\text{real},k} = J_{\text{sc,real},k}\cdot V_{\text{oc,real},k}\cdot \text{FF}_{\text{real},k}$$
2. **Realistic Commodity Passivated Bifacial TOPCon/SHJ c-Si Subcell Solver:**
   * Fixed industrial c-Si dark saturation current $J_{0,\text{Si,real}} = 2.8\times 10^{-11}\text{ mA/cm}^2$, cell-to-module aperture/encapsulation factor $f_{\text{ap,Si}} = 0.955$, $R_{s,\text{Si}} = 0.55\text{ }\Omega\cdot\text{cm}^2$, $R_{\text{sh,Si}} = 3500.0\text{ }\Omega\cdot\text{cm}^2$, and **standard commercial c-Si free-carrier absorption** $T_{\text{Si,FCA,std}}(\lambda) = \exp(-0.38\,(\lambda_{\text{nm}} / 1200)^2)$:
     $$J_{\text{sc,Si,real}} = 0.955\,J_{\text{sc,Si,rad}}, \quad V_{\text{oc,Si,real}} = V_{\text{oc,Si,rad}} + V_{\text{th}}\ln(0.955)$$
     with $\text{FF}_{\text{Si,real}}$ evaluated identically with $\max(0.50, \dots)$ bounds.
   * **Path 0 Standalone Commodity Bifacial c-Si Baseline:** Monofacial $\Phi_{\text{Si,mono}} = \Phi_{\text{sun}}$ and $20\%$ ground-albedo bifacial $\Phi_{\text{Si,bif20}} = \Phi_{\text{sun}}\cdot(1.0 + 0.20\times 0.80)$ absorbed with $0.98\,f_{\text{abs,Si,2L}}$.
3. **Band-Gap Uncertainty Sensitivity ($\delta E_g = \pm 0.15\text{ eV}$):**
   * Evaluates Base-Case ($\text{ERE} = 10^{-4}$) monofacial 2-Layer and 3-Layer PCE under simultaneous band-gap shifts $\delta E_g \in \{-0.15, +0.15\}\text{ eV}$ applied to $(E_{g,\text{ind},1}, E_{g,\text{dir},1}, E_{g,\text{ind},3}, E_{g,\text{dir},3})$ (with shifted gaps floored at $0.55\text{ eV}$, keeping $E_{g,\text{dir}} \ge E_{g,\text{ind}}$).

### 11.3 Phase 11C — Realistic Industrial Fab CAPEX, Yield & 4-Path Commercialization Economics
1. **Realistic Thin-Film Subcell Manufacturing Cost ($k \in \{\text{top}, \text{bot}\}$):**
   * Criticality surcharge $C_{\text{crit},k} = \$4.50/\text{m}^2$ if $\text{In}$ or $\text{Ag} \in \{n_Z\}$, else $\$2.00/\text{m}^2$ if $\text{Ga} \in \{n_Z\}$, else $\$0.00/\text{m}^2$.
   * Unyielded single-junction deposition cost ($40\%$ PVD utilization $= 2.50\times$ raw cost, $5\text{N}$ target compounding $\$1.20/\text{m}^2$, vacuum PVD/RTP depreciation $\$9.50/\text{m}^2$, TCO + ALD buffer + P1/P2/P3 laser scribing $\$5.80/\text{m}^2$):
     $$C_{\text{fab,unyielded},k} = 16.50 + 2.50\,C_{\text{raw},k} + C_{\text{crit},k}\text{ [\$/m}^2\text{]}$$
2. **Head-to-Head 4 Strategic Commercialization Paths (Base-Case $\text{ERE} = 10^{-4}$, $20\%$ Ground Albedo for Utility/Rooftop Paths 0–3):**
   * Discounted 25-year LCOE ($\text{cents/kWh}$) with $C_{\text{BOS,area}} = \$100.00/\text{m}^2$ (utility) or $\$240.00/\text{m}^2$ (area-constrained rooftop/commercial), power BOS $\$0.22/\text{W}_{\text{p}}$, O&M $\$2.50/\text{m}^2/\text{yr}$, discount rate $6\%$, insolation $1800\text{ kWh/m}^2/\text{yr}$:
     * **Path 0 (Commodity Bifacial TOPCon/SHJ c-Si):** $C_{\text{mod,0}} = \$42.00/\text{m}^2$, $\eta_0 = \eta_{\text{Si,bif20}}$, $f_{\text{NOCT}} = 0.930$, $r_{\text{deg}} = 0.0045$.
     * **Path 1 (3-Layer 4T Sandwich on Commodity Bifacial c-Si):** Compound two-junction yield $Y_{\text{3L}} = 0.90 \times 0.86 = 0.774$, 4T 3-subcell wiring/interlayer $\$12.00/\text{m}^2$:
       $$C_{\text{mod,1}} = 42.00 + \frac{C_{\text{fab,unyielded,top}} + C_{\text{fab,unyielded,bot}}}{0.774} + 12.00$$
       with $\Phi_{2,\text{Path1}} = \Phi_{\text{sun}} T_{\text{stack},1} + 0.20\cdot 0.78\,\Phi_{\text{sun}}(1 - f_{\text{abs},3})\cdot 0.92$, $\Phi_{3,\text{Path1}} = \Phi_{\text{sun}} T_{\text{stack},1}\cdot 0.96\,(1 - f_{\text{abs,Si,3L}})\,T_{\text{Si,FCA,std}} + 0.20\cdot 0.78\,\Phi_{\text{sun}}$, $f_{\text{NOCT}} = 0.925$, $r_{\text{deg}} = 0.0055$.
     * **Path 2 (2-Layer 4T Active Solar Glass Superstrate on Unobstructed Bifacial c-Si):** Single thin-film yield $Y_{\text{2L}} = 0.90$, 4T 2-subcell wiring/lamination $\$5.50/\text{m}^2$:
       $$C_{\text{mod,2}} = 42.00 + \frac{C_{\text{fab,unyielded,top}}}{0.90} + 5.50$$
       with unobstructed rear bifacial c-Si flux $\Phi_{2,\text{Path2}} = \Phi_{\text{sun}} T_{\text{stack},1} + 0.20\cdot 0.80\,\Phi_{\text{sun}}$, $f_{\text{NOCT}} = 0.930$, $r_{\text{deg}} = 0.0050$.
     * **Path 3 (2-Terminal Monolithic Top-on-Si, $375^\circ\text{C}$ Direct Deposition):** Yield $Y_{\text{2T}} = 0.84$, saves $\$5.50/\text{m}^2$ wiring and $\$3.50/\text{m}^2$ TCO, but incurs $0.84\times$ SHJ thermal-passivation + spectral current-mismatch derating:
       $$C_{\text{mod,3}} = 42.00 + \frac{C_{\text{fab,unyielded,top}} - 3.50}{0.84}, \qquad \eta_{\text{Path3}} = 0.84\cdot\eta_{\text{Path2}}, \quad f_{\text{NOCT}} = 0.925, \quad r_{\text{deg}} = 0.0060$$
     * **Path 4 (Standalone BIPV Semi-Transparent Solar Window Glazing, Top Active Glass Only):** Semi-transparent architectural double-glazed unit ($35\%$ daylighting transmittance, $0.72\times$ Base-Case top-cell PCE $\eta_{\text{Path4}} = 0.72\,\eta_{\text{top,base}}$), all-in DGU cost $C_{\text{mod,4}} = 58.00 + C_{\text{fab,unyielded,top}} / 0.90$, commercial solar-control glazing ASP $\$185.00/\text{m}^2$, pilot gross margin $\text{GM}_{\text{Path4}}(\%) = \frac{185.00 - C_{\text{mod,4}}}{185.00}\times 100$.


