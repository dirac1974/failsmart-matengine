"""Independent Code & Mathematical Verification Engine (FailSmart-MatEngine v2.0).

STRICT ZERO-TRUST FIREWALL MANDATE:
- Blinded independent verification solely derived from MATHEMATICAL_SPEC_V2.md and schemas.py.
- Zero imports from physics_calculators, kinetics_and_optics, or tools.
- Evaluates canonical reduced formulas, integer stoichiometry GCD, exact charge neutrality,
  pymatgen CIF round-trip under 3D periodic boundary conditions, Brown-Altermatt Bond-Valence
  Sum Global Instability Index (GII), photon-energy space Simpson 1/3 quadrature for SLME,
  Shockley-Queisser thermodynamic limits, 4-terminal tandem optical propagation,
  Frohlich polaron coupling physics, and Stage 2b ion-migration stability.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pvlib.spectrum
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser
import scipy.integrate

# =============================================================================
# 1. Fundamental Physical Constants (CODATA 2018 - Section 1)
# =============================================================================

Q_E: float = 1.602176634e-19           # Elementary charge (C)
PLANCK_H: float = 6.62607015e-34       # Planck constant (J*s)
HBAR: float = PLANCK_H / (2.0 * math.pi) # Reduced Planck constant (J*s)
SPEED_C: float = 2.99792458e8          # Speed of light (m/s)
K_B: float = 1.380649e-23              # Boltzmann constant (J/K)
EPS_0: float = 8.8541878128e-12        # Vacuum permittivity (F/m)
M_0: float = 9.1093837015e-31          # Electron rest mass (kg)
N_A: float = 6.02214076e23             # Avogadro constant (mol^-1)
T_CELL: float = 300.0                  # Cell operating temperature (K)
V_TH: float = K_B * T_CELL / Q_E       # Thermal voltage (~0.02585199 V)
HC_Q_NM: float = 1239.8419843320026    # Photon energy-wavelength conversion (eV*nm)

# =============================================================================
# 2. Brown-Altermatt Bond-Valence Sum Radii (Section 2.3)
# =============================================================================

BVS_R0_RADII: Dict[str, float] = {
    "Bi": 1.52, "Sb": 1.40, "Sn": 1.42, "Cu": 1.12, "Ag": 1.28, "Zn": 1.18,
    "Ba": 1.82, "Sr": 1.68, "Ca": 1.54, "Mg": 1.30, "Ti": 1.26, "Zr": 1.42,
    "Fe": 1.24, "In": 1.38, "Ga": 1.24, "Pb": 1.56, "Cd": 1.36, "O": 0.63,
    "S": 1.04, "Se": 1.17, "Te": 1.36, "N": 0.70, "P": 1.06, "Cl": 0.99,
    "Br": 1.14, "I": 1.33,
}

# =============================================================================
# 3. Reference Solar Spectrum & Uniform Photon-Energy Grid (Section 4 & 5)
# =============================================================================

N_ENERGY_POINTS: int = 8001
E_MIN_EV: float = HC_Q_NM / 4000.0  # ~0.309960 eV (4000 nm)
E_MAX_EV: float = HC_Q_NM / 280.0   # ~4.428007 eV (280 nm)

ENERGY_GRID_EV: np.ndarray = np.linspace(E_MIN_EV, E_MAX_EV, N_ENERGY_POINTS)
LAMBDA_GRID_NM: np.ndarray = HC_Q_NM / ENERGY_GRID_EV

_ASTRM_SPEC = pvlib.spectrum.get_reference_spectra()["global"]
_LAMBDA_REF_NM = _ASTRM_SPEC.index.to_numpy(dtype=float)
_IRR_REF_W_M2_NM = _ASTRM_SPEC.to_numpy(dtype=float)

# Interpolate reference AM1.5G irradiance onto energy-grid wavelength coordinates
_I_LAMBDA_GRID = np.interp(LAMBDA_GRID_NM, _LAMBDA_REF_NM, _IRR_REF_W_M2_NM)

# Exact Jacobian mapping: I_E(E) = I_lambda(lambda(E)) * |dlambda/dE|
# |dlambda/dE| = (hc/q * 1e9) / E^2
_JACOBIAN_E = HC_Q_NM / (ENERGY_GRID_EV ** 2)
SOLAR_IRRADIANCE_E: np.ndarray = _I_LAMBDA_GRID * _JACOBIAN_E

# Solar spectral photon flux per eV: Phi_sun,E(E) = I_E(E) / (q * E)
SOLAR_PHOTON_FLUX_E: np.ndarray = SOLAR_IRRADIANCE_E / (Q_E * ENERGY_GRID_EV)

# Reference 1-sun incident power density via photon-energy Simpson integration (mW/cm^2)
P_IN_MW_CM2: float = float(0.1 * scipy.integrate.simpson(SOLAR_IRRADIANCE_E, x=ENERGY_GRID_EV))

# Blackbody spectral photon flux per eV at T_cell = 300.0 K (Section 4.2)
_ARG_BB = np.minimum(500.0, (Q_E * ENERGY_GRID_EV) / (K_B * T_CELL))
BLACKBODY_PHOTON_FLUX_E: np.ndarray = (
    2.0 * math.pi * (Q_E ** 3) * (ENERGY_GRID_EV ** 2)
) / (
    (PLANCK_H ** 3) * (SPEED_C ** 2) * (np.exp(_ARG_BB) - 1.0)
)


# =============================================================================
# 4. Independent Formula, GCD & Stoichiometry Parser
# =============================================================================

def simpson_13(y: np.ndarray, x: np.ndarray) -> float:
    """Simpson 1/3 numerical quadrature wrapper over scipy.integrate.simpson."""
    return float(scipy.integrate.simpson(y, x=x))


def independently_parse_formula(formula: str) -> Dict[str, int]:
    """Parse chemical formula string into an elemental stoichiometry dictionary via regex."""
    if not formula:
        return {}
    pattern = r"([A-Z][a-z]?)([0-9]*)"
    matches = re.findall(pattern, formula)
    stoich: Dict[str, int] = {}
    for elem, count in matches:
        if not elem:
            continue
        c = int(count) if count else 1
        stoich[elem] = stoich.get(elem, 0) + c
    return stoich


def gcd_reduced(stoich: Dict[str, int]) -> Dict[str, int]:
    """Reduce integer stoichiometry dictionary by its greatest common divisor (GCD)."""
    if not stoich:
        return {}
    values = list(stoich.values())
    g = values[0]
    for v in values[1:]:
        g = math.gcd(g, v)
    if g <= 1:
        return dict(stoich)
    return {elem: count // g for elem, count in stoich.items()}


# =============================================================================
# 5. Independent CIF Round-Trip, 3D PBC Distance & BVS GII Verifier
# =============================================================================

def independently_verify_cif_geometry(
    cif_text: str,
    oxidation_states: Optional[Dict[str, int]] = None,
    expected_nsites: Optional[int] = None,
    expected_reduced_stoich: Optional[Dict[str, int]] = None,
    min_dist_floor_ang: float = 1.75,
) -> Dict[str, Any]:
    """Parse CIF text via pymatgen and independently verify 3D periodic geometry & BVS GII."""
    if not cif_text or not cif_text.strip():
        return {
            "natoms": 0,
            "min_distance_ang": 0.0,
            "valid_distance": False,
            "valid_geometry": False,
            "passed": False,
            "reason": "Empty CIF content",
        }

    parser = CifParser.from_str(cif_text, occupancy_tolerance=10.0)
    structs = parser.parse_structures(primitive=False)
    if not structs:
        return {
            "natoms": 0,
            "min_distance_ang": 0.0,
            "valid_distance": False,
            "valid_geometry": False,
            "passed": False,
            "reason": "CifParser produced no structures",
        }

    struct: Structure = structs[0]
    natoms = len(struct)

    # Off-diagonal 3D periodic distances
    dm = struct.distance_matrix
    if natoms > 1:
        off_diag_dists = [dm[i, j] for i in range(natoms) for j in range(natoms) if i != j]
        min_off_diag = float(min(off_diag_dists)) if off_diag_dists else float("inf")
    else:
        min_off_diag = float("inf")

    # Periodic self-image distance (minimum lattice translation norm)
    min_self = float(min(struct.lattice.abc))
    min_distance_ang = round(min(min_off_diag, min_self), 3)
    valid_distance = bool(min_distance_ang >= min_dist_floor_ang)

    # Check atom count if expected_nsites provided
    valid_nsites = True
    if expected_nsites is not None and natoms != expected_nsites:
        valid_nsites = False

    # Check reduced composition if expected_reduced_stoich provided
    valid_comp = True
    if expected_reduced_stoich is not None:
        struct_comp = {elem.symbol: int(round(count)) for elem, count in struct.composition.items()}
        struct_reduced = gcd_reduced(struct_comp)
        exp_reduced = gcd_reduced(expected_reduced_stoich)
        if struct_reduced != exp_reduced:
            valid_comp = False

    # Compute Brown-Altermatt Bond-Valence Sum Global Instability Index (GII)
    bvs_gii: Optional[float] = None
    if oxidation_states:
        diff_sq_sum = 0.0
        b_const = 0.37
        for site in struct:
            elem_i = site.specie.symbol
            z_i = oxidation_states.get(elem_i, 0)
            r0_i = BVS_R0_RADII.get(elem_i, 1.40)
            neighbors = struct.get_neighbors(site, 4.0)
            v_i = 0.0
            for neighbor in neighbors:
                elem_j = neighbor.specie.symbol
                z_j = oxidation_states.get(elem_j, 0)
                if z_i * z_j < 0:
                    r0_j = BVS_R0_RADII.get(elem_j, 1.40)
                    r0_ij = r0_i + r0_j
                    r_ij = neighbor.nn_distance
                    v_i += math.exp((r0_ij - r_ij) / b_const)
            diff_sq_sum += (v_i - abs(z_i)) ** 2
        bvs_gii = round(math.sqrt(diff_sq_sum / natoms), 4)

    is_valid = valid_distance and valid_nsites and valid_comp

    return {
        "natoms": natoms,
        "expected_natoms": expected_nsites if expected_nsites is not None else natoms,
        "min_distance_ang": min_distance_ang,
        "valid_distance": valid_distance,
        "bvs_gii": bvs_gii,
        "valid_geometry": is_valid,
        "passed": is_valid,
    }


# =============================================================================
# 6. Independent Fröhlich Polaron & Anderson Debye Physics
# =============================================================================

def compute_frohlich_alpha_exact(
    electron_eff_mass_m0: float,
    hole_eff_mass_m0: float,
    eps_inf: float,
    eps_static: float,
    lo_phonon_freq_thz: float = 2.1,
) -> float:
    """Independently compute exact Fröhlich polaron coupling constant alpha_F (Section 2.4)."""
    m_star = max(electron_eff_mass_m0, hole_eff_mass_m0) * M_0
    omega_lo = 2.0 * math.pi * lo_phonon_freq_thz * 1e12

    term1 = (Q_E ** 2) / (4.0 * math.pi * EPS_0 * HBAR)
    term2 = (1.0 / eps_inf) - (1.0 / eps_static)
    term3 = math.sqrt(m_star / (2.0 * HBAR * omega_lo))
    alpha_f = term1 * term2 * term3
    return float(round(alpha_f, 4))


def compute_polaron_trapping_energy_mev(
    alpha_f: float,
    lo_phonon_freq_thz: float = 2.1,
) -> float:
    """Independently compute polaron self-trapping stabilization energy in meV (Section 2.4)."""
    omega_lo = 2.0 * math.pi * lo_phonon_freq_thz * 1e12
    hbar_omega_lo_ev = (HBAR * omega_lo) / Q_E
    e_pol_mev = 1000.0 * hbar_omega_lo_ev * (alpha_f + 0.0159196 * (alpha_f ** 2))
    return float(round(e_pol_mev, 2))


# =============================================================================
# 7. Independent Photon-Energy Space Cell Solver & 4T Stack Integrals
# =============================================================================

def _absorption_coefficient_e(
    eg_ind_ev: float,
    eg_dir_ev: float,
    e_grid: np.ndarray,
) -> np.ndarray:
    """Absorption coefficient alpha(E) [m^-1] per Section 4.2."""
    delta_ind = np.maximum(0.0, e_grid - eg_ind_ev)
    delta_dir = np.maximum(0.0, e_grid - eg_dir_ev)
    return 1.2e5 * (delta_ind ** 2) + 2.8e7 * np.sqrt(delta_dir)


def _light_trapping_fabs(
    alpha_e: np.ndarray,
    eps_inf: float,
    thickness_m: float,
) -> np.ndarray:
    """Internal light-trapping absorptance fraction f_abs(E) with Y = 4*n^2."""
    n_refr = math.sqrt(eps_inf)
    yab = 4.0 * (n_refr ** 2)
    term = yab * alpha_e * thickness_m
    return term / (1.0 + term)


def _solve_pv_cell_energy_quadrature(
    absorptance_e: np.ndarray,
    incident_photon_flux_e: np.ndarray,
    eg_ind_ev: float,
    eg_dir_ev: float,
    j0_rad_fixed: Optional[float] = None,
) -> Dict[str, float]:
    """Solve J_sc, V_oc, analytical FF, and efficiency using Simpson 1/3 quadrature in energy space."""
    # J_sc (mA/cm^2) = 0.1 * q * integral(A(E) * Phi_inc(E) dE)
    jsc = float(0.1 * Q_E * scipy.integrate.simpson(absorptance_e * incident_photon_flux_e, x=ENERGY_GRID_EV))
    if jsc <= 1e-9:
        return {"jsc": 0.0, "voc": 0.0, "ff": 0.0, "eff": 0.0}

    if j0_rad_fixed is not None:
        j0_rad = j0_rad_fixed
    else:
        # J_0,rad = 0.1 * q * integral(A(E) * Phi_bb(E) dE) + 1e-40
        j0_rad = float(0.1 * Q_E * scipy.integrate.simpson(absorptance_e * BLACKBODY_PHOTON_FLUX_E, x=ENERGY_GRID_EV)) + 1e-40

    delta_gap = max(0.0, eg_dir_ev - eg_ind_ev)
    fr = math.exp(-delta_gap / V_TH)
    j0 = j0_rad / fr

    voc = float(V_TH * math.log(jsc / j0 + 1.0))
    v = voc / V_TH
    ff = float((v - math.log(v + 0.72)) / (v + 1.0))
    eff = float((jsc * voc * ff / P_IN_MW_CM2) * 100.0)

    return {"jsc": jsc, "voc": voc, "ff": ff, "eff": eff}


def independently_verify_energy_quadrature_slme(
    eg_ind_ev: float,
    eg_dir_ev: float,
    eps_inf: float,
    thickness_nm: float,
    target_layer: str = "TOP_ACTIVE_GLASS_185EV",
) -> Dict[str, Any]:
    """Independently compute SLME, SQ limit & sequential 4T stack in photon-energy space."""
    d_cand_m = thickness_nm * 1e-9
    alpha_cand = _absorption_coefficient_e(eg_ind_ev, eg_dir_ev, ENERGY_GRID_EV)
    fabs_cand = _light_trapping_fabs(alpha_cand, eps_inf, d_cand_m)
    a_cand = (1.0 - 0.020) * fabs_cand

    # Standalone SLME
    cell_cand_slme = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_cand,
        incident_photon_flux_e=SOLAR_PHOTON_FLUX_E,
        eg_ind_ev=eg_ind_ev,
        eg_dir_ev=eg_dir_ev,
    )
    slme_percent = round(cell_cand_slme["eff"], 2)

    # Exact 1-Sun Shockley-Queisser Limit (step absorptance, fr = 1.0)
    a_sq = np.where(ENERGY_GRID_EV >= eg_ind_ev, 1.0, 0.0)
    cell_cand_sq = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_sq,
        incident_photon_flux_e=SOLAR_PHOTON_FLUX_E,
        eg_ind_ev=eg_ind_ev,
        eg_dir_ev=eg_ind_ev,
    )
    sq_percent = round(cell_cand_sq["eff"], 2)

    # Sequential 3-Layer 4-Terminal Stack Propagation (Section 4.3)
    if target_layer == "TOP_ACTIVE_GLASS_185EV":
        eg_ind_1, eg_dir_1, eps_inf_1, d1_m = eg_ind_ev, eg_dir_ev, eps_inf, d_cand_m
        eg_ind_3, eg_dir_3, eps_inf_3, d3_m = 0.75, 0.79, 8.50, 350.0 * 1e-9
    else:
        eg_ind_1, eg_dir_1, eps_inf_1, d1_m = 1.84, 1.88, 6.10, 260.0 * 1e-9
        eg_ind_3, eg_dir_3, eps_inf_3, d3_m = eg_ind_ev, eg_dir_ev, eps_inf, d_cand_m

    # Step A — Layer 1
    n1 = math.sqrt(eps_inf_1)
    alpha1 = _absorption_coefficient_e(eg_ind_1, eg_dir_1, ENERGY_GRID_EV)
    fabs1 = _light_trapping_fabs(alpha1, eps_inf_1, d1_m)
    a1 = (1.0 - 0.020) * fabs1
    cell1 = _solve_pv_cell_energy_quadrature(
        absorptance_e=a1,
        incident_photon_flux_e=SOLAR_PHOTON_FLUX_E,
        eg_ind_ev=eg_ind_1,
        eg_dir_ev=eg_dir_1,
    )

    r_fresnel_1 = 0.25 * (((n1 - 1.85) / (n1 + 1.85)) ** 2)
    t_tco = np.exp(-2.0 * (0.015 + 0.028 * ((LAMBDA_GRID_NM / 1000.0) ** 2)))
    t_stack_1 = (1.0 - 0.020 - 0.020 - r_fresnel_1) * (1.0 - fabs1) * t_tco
    phi2 = SOLAR_PHOTON_FLUX_E * t_stack_1

    # Photon conservation check across energy grid: A_1(E) + T_stack,1(E) < 1.0
    conservation_passed = bool(np.all(a1 + t_stack_1 < 1.0))

    # Sub-bandgap transmittance & TCO parasitic loss
    if target_layer == "TOP_ACTIVE_GLASS_185EV":
        sub_mask = (ENERGY_GRID_EV >= 0.75) & (ENERGY_GRID_EV <= (eg_ind_1 - 0.02))
        flux_sub = SOLAR_PHOTON_FLUX_E[sub_mask]
        e_sub = ENERGY_GRID_EV[sub_mask]
        sub_t_percent = float(scipy.integrate.simpson(t_stack_1[sub_mask] * flux_sub, x=e_sub) / scipy.integrate.simpson(flux_sub, x=e_sub) * 100.0)
        tco_loss_percent = float(scipy.integrate.simpson((1.0 - t_tco[sub_mask]) * flux_sub, x=e_sub) / scipy.integrate.simpson(flux_sub, x=e_sub) * 100.0)
    else:
        sub_mask = (ENERGY_GRID_EV >= 0.40) & (ENERGY_GRID_EV <= (eg_ind_3 - 0.02))
        flux_sub = SOLAR_PHOTON_FLUX_E[sub_mask]
        e_sub = ENERGY_GRID_EV[sub_mask]
        n3 = math.sqrt(eps_inf_3)
        r_fresnel_3 = 0.25 * (((n3 - 1.85) / (n3 + 1.85)) ** 2)
        t_tco_single = np.sqrt(t_tco)
        t_stack_3 = (1.0 - 0.020 - 0.020 - r_fresnel_3) * (1.0 - fabs_cand) * t_tco_single
        sub_t_percent = float(scipy.integrate.simpson(t_stack_3[sub_mask] * flux_sub, x=e_sub) / scipy.integrate.simpson(flux_sub, x=e_sub) * 100.0)
        tco_loss_percent = float(scipy.integrate.simpson((1.0 - t_tco_single[sub_mask]) * flux_sub, x=e_sub) / scipy.integrate.simpson(flux_sub, x=e_sub) * 100.0)

    # Step B — Layer 2 (Crystalline Silicon Wafer, Eg=1.12 eV, d=160 um, J0=1.2e-12 mA/cm^2)
    delta_ind_si = np.maximum(0.0, ENERGY_GRID_EV - 1.12)
    delta_dir_si = np.maximum(0.0, ENERGY_GRID_EV - 3.40)
    alpha_si = 1.1e5 * (delta_ind_si ** 2) + 1.5e7 * np.sqrt(delta_dir_si)
    d_si = 160.0 * 1e-6

    term_si_2l = 49.0 * alpha_si * d_si
    fabs_si_2l = term_si_2l / (1.0 + term_si_2l)
    a_si_2l = 0.98 * fabs_si_2l
    cell_si_2l = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_si_2l,
        incident_photon_flux_e=phi2,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    term_si_3l = 16.0 * alpha_si * d_si
    fabs_si_3l = term_si_3l / (1.0 + term_si_3l)
    a_si_3l = 0.98 * fabs_si_3l
    cell_si_3l = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_si_3l,
        incident_photon_flux_e=phi2,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    # Silicon Drude FCA & Transmitted Flux to Layer 3
    t_si_fca_low = np.exp(-0.08 * ((LAMBDA_GRID_NM / 1200.0) ** 2))
    t_si_fca_std = np.exp(-0.38 * ((LAMBDA_GRID_NM / 1200.0) ** 2))
    phi3_low = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
    phi3_std = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std

    # Step C — Layer 3 (Bottom IR Scavenger)
    alpha3 = _absorption_coefficient_e(eg_ind_3, eg_dir_3, ENERGY_GRID_EV)
    fabs3 = _light_trapping_fabs(alpha3, eps_inf_3, d3_m)
    a3 = (1.0 - 0.020) * fabs3
    cell3_low = _solve_pv_cell_energy_quadrature(
        absorptance_e=a3,
        incident_photon_flux_e=phi3_low,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )
    cell3_std = _solve_pv_cell_energy_quadrature(
        absorptance_e=a3,
        incident_photon_flux_e=phi3_std,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )

    tandem_2layer = round(cell1["eff"] + cell_si_2l["eff"], 2)
    tandem_4t_std = round(cell1["eff"] + cell_si_3l["eff"] + cell3_std["eff"], 2)
    tandem_4t_total = round(cell1["eff"] + cell_si_3l["eff"] + cell3_low["eff"], 2)

    return {
        "standalone_slme_percent": slme_percent,
        "shockley_queisser_limit_percent": sq_percent,
        "sub_bandgap_transmittance_percent": round(sub_t_percent, 2),
        "tco_parasitic_loss_percent": round(tco_loss_percent, 2),
        "top_cell_jsc_ma_cm2": round(cell1["jsc"], 2),
        "top_cell_voc_v": round(cell1["voc"], 3),
        "top_cell_eff_percent": round(cell1["eff"], 2),
        "si_middle_cell_eff_percent": round(cell_si_3l["eff"], 2),
        "bottom_ir_cell_eff_percent": round(cell3_low["eff"], 2),
        "tandem_2layer_si_eff_percent": tandem_2layer,
        "tandem_4t_std_si_fca_eff_percent": tandem_4t_std,
        "tandem_4t_total_eff_percent": tandem_4t_total,
        "photon_conservation_holds": conservation_passed,
    }


def independently_verify_cross_layer_4t_pair(
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    thickness_nm_1: float,
    eg_ind_3: float,
    eg_dir_3: float,
    eps_inf_3: float,
    thickness_nm_3: float,
) -> Dict[str, Any]:
    """Independently compute and verify sequential 3-layer 4-terminal tandem stack optics.

    Per Section 4.3 of docs/MATHEMATICAL_SPEC_V2.md:
    Uses the exact Section 4.3 sequential 3-layer 4-terminal stack propagation equations:
    - Step A — Layer 1 (Top Active Glass): fabs1 = _light_trapping_fabs(alpha1, eps_inf_1, d1_m),
      a1 = (1.0 - 0.020) * fabs1, r_fresnel_1 = 0.25 * (((n1 - 1.85) / (n1 + 1.85)) ** 2),
      t_tco = exp(-2.0 * (0.015 + 0.028 * ((LAMBDA_GRID_NM / 1000.0) ** 2))),
      t_stack_1 = (1.0 - 0.020 - 0.020 - r_fresnel_1) * (1.0 - fabs1) * t_tco,
      phi2 = SOLAR_PHOTON_FLUX_E * t_stack_1.
    - Step B — Layer 2 (c-Si Wafer, Eg=1.12 eV, d=160 um, J0=1.2e-12 mA/cm^2):
      term_si_2l = 49.0 * alpha_si * d_si, fabs_si_2l = term_si_2l / (1.0 + term_si_2l),
      term_si_3l = 16.0 * alpha_si * d_si, fabs_si_3l = term_si_3l / (1.0 + term_si_3l),
      t_si_fca_low = exp(-0.08 * ((LAMBDA_GRID_NM / 1200.0) ** 2)),
      t_si_fca_std = exp(-0.38 * ((LAMBDA_GRID_NM / 1200.0) ** 2)),
      phi3_low = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low,
      phi3_std = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std.
    - Step C — Layer 3 (Bottom IR Scavenger):
      fabs3 = _light_trapping_fabs(alpha3, eps_inf_3, d3_m),
      a3 = (1.0 - 0.020) * fabs3, solved under phi3_low and phi3_std.
    """
    d1_m = thickness_nm_1 * 1e-9
    d3_m = thickness_nm_3 * 1e-9

    # Step A — Layer 1
    n1 = math.sqrt(eps_inf_1)
    alpha1 = _absorption_coefficient_e(eg_ind_1, eg_dir_1, ENERGY_GRID_EV)
    fabs1 = _light_trapping_fabs(alpha1, eps_inf_1, d1_m)
    a1 = (1.0 - 0.020) * fabs1
    cell1 = _solve_pv_cell_energy_quadrature(
        absorptance_e=a1,
        incident_photon_flux_e=SOLAR_PHOTON_FLUX_E,
        eg_ind_ev=eg_ind_1,
        eg_dir_ev=eg_dir_1,
    )

    r_fresnel_1 = 0.25 * (((n1 - 1.85) / (n1 + 1.85)) ** 2)
    t_tco = np.exp(-2.0 * (0.015 + 0.028 * ((LAMBDA_GRID_NM / 1000.0) ** 2)))
    t_stack_1 = (1.0 - 0.020 - 0.020 - r_fresnel_1) * (1.0 - fabs1) * t_tco
    phi2 = SOLAR_PHOTON_FLUX_E * t_stack_1

    # Photon conservation check across energy grid: A_1(E) + T_stack,1(E) < 1.0
    conservation_passed = bool(np.all(a1 + t_stack_1 < 1.0))

    # Sub-bandgap transmittance of Layer 1 over [0.75, eg_ind_1 - 0.02] eV
    sub_mask = (ENERGY_GRID_EV >= 0.75) & (ENERGY_GRID_EV <= (eg_ind_1 - 0.02))
    flux_sub = SOLAR_PHOTON_FLUX_E[sub_mask]
    e_sub = ENERGY_GRID_EV[sub_mask]
    if np.any(sub_mask):
        sub_t_percent = float(
            scipy.integrate.simpson(t_stack_1[sub_mask] * flux_sub, x=e_sub)
            / scipy.integrate.simpson(flux_sub, x=e_sub)
            * 100.0
        )
    else:
        sub_t_percent = 0.0

    # Step B — Layer 2 (Crystalline Silicon Wafer, Eg=1.12 eV, d=160 um, J0=1.2e-12 mA/cm^2)
    delta_ind_si = np.maximum(0.0, ENERGY_GRID_EV - 1.12)
    delta_dir_si = np.maximum(0.0, ENERGY_GRID_EV - 3.40)
    alpha_si = 1.1e5 * (delta_ind_si ** 2) + 1.5e7 * np.sqrt(delta_dir_si)
    d_si = 160.0 * 1e-6

    term_si_2l = 49.0 * alpha_si * d_si
    fabs_si_2l = term_si_2l / (1.0 + term_si_2l)
    a_si_2l = 0.98 * fabs_si_2l
    cell_si_2l = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_si_2l,
        incident_photon_flux_e=phi2,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    term_si_3l = 16.0 * alpha_si * d_si
    fabs_si_3l = term_si_3l / (1.0 + term_si_3l)
    a_si_3l = 0.98 * fabs_si_3l
    cell_si_3l = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_si_3l,
        incident_photon_flux_e=phi2,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    # Silicon Drude FCA & Transmitted Flux to Layer 3
    t_si_fca_low = np.exp(-0.08 * ((LAMBDA_GRID_NM / 1200.0) ** 2))
    t_si_fca_std = np.exp(-0.38 * ((LAMBDA_GRID_NM / 1200.0) ** 2))
    phi3_low = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
    phi3_std = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std

    # Step C — Layer 3 (Bottom IR Scavenger)
    alpha3 = _absorption_coefficient_e(eg_ind_3, eg_dir_3, ENERGY_GRID_EV)
    fabs3 = _light_trapping_fabs(alpha3, eps_inf_3, d3_m)
    a3 = (1.0 - 0.020) * fabs3
    cell3_low = _solve_pv_cell_energy_quadrature(
        absorptance_e=a3,
        incident_photon_flux_e=phi3_low,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )
    cell3_std = _solve_pv_cell_energy_quadrature(
        absorptance_e=a3,
        incident_photon_flux_e=phi3_std,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )

    tandem_2layer = round(cell1["eff"] + cell_si_2l["eff"], 2)
    tandem_4t_std = round(cell1["eff"] + cell_si_3l["eff"] + cell3_std["eff"], 2)
    tandem_4t_total = round(cell1["eff"] + cell_si_3l["eff"] + cell3_low["eff"], 2)

    return {
        "top_cell_eff_percent": round(cell1["eff"], 2),
        "sub_bandgap_transmittance_percent": round(sub_t_percent, 2),
        "si_middle_cell_eff_percent": round(cell_si_3l["eff"], 2),
        "bottom_ir_cell_eff_percent": round(cell3_low["eff"], 2),
        "bottom_ir_std_si_eff_percent": round(cell3_std["eff"], 2),
        "tandem_2layer_si_eff_percent": tandem_2layer,
        "tandem_4t_std_si_fca_eff_percent": tandem_4t_std,
        "tandem_4t_low_fca_total_eff_percent": tandem_4t_total,
        "total_4t_pce_percent": tandem_4t_total,
        "photon_conservation_holds": conservation_passed,
    }


# =============================================================================
# 8. Top-Level Entrypoint: Candidate Dossier Zero-Trust Verifier
# =============================================================================

def verify_candidate_dossier(
    dossier: Dict[str, Any],
    _unused_spectrum_fn: Any = None,
    raise_on_error: bool = False,
) -> Dict[str, Any]:
    """Zero-trust independent verification of a candidate evaluation dossier.

    Verifies stoichiometry GCD, exact charge neutrality, CIF periodic distance and BVS GII,
    energy-space Simpson SLME, SQ ceiling, sequential 4T stack, Fröhlich polaron physics,
    and Stage 2b ion-migration stability.
    """
    cand = dossier.get("candidate", {})
    cid = cand.get("candidate_id", "UNKNOWN")
    formula = cand.get("formula_reduced", "")
    stoich = cand.get("stoichiometry", {})
    ox_states = cand.get("oxidation_states", {})
    cif_text = cand.get("cif_content", "")
    target_layer = cand.get("target_layer", "TOP_ACTIVE_GLASS_185EV")
    stage_reached = dossier.get("stage_reached", 1)

    checks: Dict[str, Any] = {}
    mismatches: List[str] = []

    # -------------------------------------------------------------------------
    # Check 1: Formula Regex Parsing & GCD Reduction Synchronization
    # -------------------------------------------------------------------------
    parsed_stoich = independently_parse_formula(formula)
    reduced_stoich = gcd_reduced(stoich)
    formula_matches = (parsed_stoich == reduced_stoich)
    checks["formula_reduced_sync"] = {
        "formula_reduced": formula,
        "parsed_formula": parsed_stoich,
        "reduced_stoichiometry": reduced_stoich,
        "passed": formula_matches,
    }
    if not formula_matches:
        mismatches.append(f"REDUNDANCY_MISMATCH_BLOCK: Formula '{formula}' parsed {parsed_stoich} != reduced {reduced_stoich}")

    # -------------------------------------------------------------------------
    # Check 2: Exact Charge Neutrality (sum(n_i * z_i) == 0)
    # -------------------------------------------------------------------------
    net_charge = sum(stoich.get(elem, 0) * ox_states.get(elem, 0) for elem in stoich)
    charge_neutral = (net_charge == 0)
    checks["charge_neutrality"] = {
        "stoichiometry": stoich,
        "oxidation_states": ox_states,
        "sum_oxidation_states": net_charge,
        "passed": charge_neutral,
    }
    if not charge_neutral:
        mismatches.append(f"REDUNDANCY_MISMATCH_BLOCK: Net charge sum(n_i * z_i) = {net_charge} != 0 for {cid}")

    # -------------------------------------------------------------------------
    # Check 3: CIF Round-Trip, 3D PBC Distance & BVS GII
    # -------------------------------------------------------------------------
    if cif_text and cif_text.strip():
        expected_nsites = cand.get("nsites_unit_cell", sum(stoich.values()))
        cif_result = independently_verify_cif_geometry(
            cif_text=cif_text,
            oxidation_states=ox_states,
            expected_nsites=expected_nsites,
            expected_reduced_stoich=reduced_stoich,
        )
        checks["cif_geometry"] = cif_result
        if not cif_result.get("passed"):
            mismatches.append(
                f"REDUNDANCY_MISMATCH_BLOCK: CIF geometry verification failed for {cid} (min_dist={cif_result.get('min_distance_ang')} A)"
            )

        # Check BVS GII agreement if reported in candidate
        stated_bvs = cand.get("bond_valence_sum_deviation")
        calc_bvs = cif_result.get("bvs_gii")
        if stated_bvs is not None and calc_bvs is not None:
            bvs_diff = abs(stated_bvs - calc_bvs)
            checks["bond_valence_sum"] = {
                "stated_bvs_gii": stated_bvs,
                "calculated_bvs_gii": calc_bvs,
                "abs_difference": round(bvs_diff, 4),
                "passed": bvs_diff <= 0.02,
            }
            if bvs_diff > 0.02:
                mismatches.append(
                    f"REDUNDANCY_MISMATCH_BLOCK: BVS GII discrepancy {bvs_diff:.4f} > 0.02 vu for {cid}"
                )

    # -------------------------------------------------------------------------
    # Check 4: Stage 2 Stability & Stage 2b Ion-Migration Gate
    # -------------------------------------------------------------------------
    if "stability" in dossier and dossier["stability"]:
        stab = dossier["stability"]
        barrier = stab.get("ion_migration_barrier_ev")
        stable_flag = stab.get("ion_migration_stable")
        debye_t = stab.get("debye_temperature_k", 0.0)

        debye_valid = debye_t > 0.0
        checks["anderson_debye_temperature"] = {
            "debye_temperature_k": debye_t,
            "passed": debye_valid,
        }
        if not debye_valid:
            mismatches.append(f"REDUNDANCY_MISMATCH_BLOCK: Debye temperature {debye_t} <= 0 for {cid}")

        if barrier is not None and stable_flag is not None:
            expected_stable = (barrier >= 0.65)
            ion_mig_pass = (stable_flag == expected_stable)
            checks["ion_migration_gate"] = {
                "ion_migration_barrier_ev": barrier,
                "ion_migration_stable": stable_flag,
                "expected_stable": expected_stable,
                "passed": ion_mig_pass,
            }
            if not ion_mig_pass:
                mismatches.append(
                    f"REDUNDANCY_MISMATCH_BLOCK: Ion migration gate mismatch for {cid}: barrier={barrier} eV but stable={stable_flag}"
                )

    # -------------------------------------------------------------------------
    # Check 5: Stage 4 Electronics, SOC Splitting & Fröhlich Polaron Physics
    # -------------------------------------------------------------------------
    if "electronics" in dossier and dossier["electronics"]:
        elec = dossier["electronics"]

        # Relativistic SOC splitting
        hse_nosoc = elec.get("hse06_nosoc_gap_ev")
        hse_soc_dir = elec.get("hse06_soc_direct_gap_ev")
        stated_soc = elec.get("soc_splitting_ev")
        if hse_nosoc is not None and hse_soc_dir is not None and stated_soc is not None:
            expected_soc = round(hse_nosoc - hse_soc_dir, 3)
            soc_pass = abs(stated_soc - expected_soc) <= 0.005
            checks["soc_splitting"] = {
                "stated_soc_ev": stated_soc,
                "expected_soc_ev": expected_soc,
                "passed": soc_pass,
            }
            if not soc_pass:
                mismatches.append(
                    f"REDUNDANCY_MISMATCH_BLOCK: SOC splitting mismatch for {cid}: stated={stated_soc} vs expected={expected_soc}"
                )

        # Fröhlich Polaron Coupling Constant & Trapping Energy
        m_e = elec.get("electron_eff_mass_m0")
        m_h = elec.get("hole_eff_mass_m0")
        eps_inf = elec.get("eps_inf")
        eps_static = elec.get("eps_static")
        stated_alpha = elec.get("frohlich_alpha")
        stated_e_pol = elec.get("polaron_trapping_mev")
        lo_phonon_thz = elec.get("lo_phonon_freq_thz", 2.1)

        if None not in (m_e, m_h, eps_inf, eps_static, stated_alpha):
            exact_alpha = compute_frohlich_alpha_exact(
                electron_eff_mass_m0=m_e,
                hole_eff_mass_m0=m_h,
                eps_inf=eps_inf,
                eps_static=eps_static,
                lo_phonon_freq_thz=lo_phonon_thz,
            )
            alpha_diff = abs(stated_alpha - exact_alpha)
            alpha_pass = alpha_diff <= 0.01
            checks["frohlich_alpha"] = {
                "stated_frohlich_alpha": stated_alpha,
                "exact_frohlich_alpha": exact_alpha,
                "abs_difference": round(alpha_diff, 5),
                "passed": alpha_pass,
            }
            if not alpha_pass:
                mismatches.append(
                    f"REDUNDANCY_MISMATCH_BLOCK: Frohlich alpha discrepancy {alpha_diff:.5f} > 0.01 for {cid}"
                )

            if stated_e_pol is not None:
                exact_e_pol = compute_polaron_trapping_energy_mev(exact_alpha, lo_phonon_freq_thz=lo_phonon_thz)
                e_pol_diff = abs(stated_e_pol - exact_e_pol)
                checks["polaron_trapping"] = {
                    "stated_polaron_trapping_mev": stated_e_pol,
                    "exact_polaron_trapping_mev": exact_e_pol,
                    "abs_difference": round(e_pol_diff, 3),
                    "passed": e_pol_diff <= 1.0,
                }

    # -------------------------------------------------------------------------
    # Check 6: Stage 5 Optics, Energy-Space Simpson SLME & Sequential 4T Stack
    # -------------------------------------------------------------------------
    if "optics" in dossier and dossier["optics"] and "electronics" in dossier and dossier["electronics"]:
        opt = dossier["optics"]
        elec = dossier["electronics"]
        eg_ind = elec.get("hse06_soc_indirect_gap_ev")
        eg_dir = elec.get("hse06_soc_direct_gap_ev")
        eps_inf = elec.get("eps_inf")
        thickness_nm = opt.get("film_thickness_nm", 260.0)
        stated_slme = opt.get("standalone_slme_percent")

        if None not in (eg_ind, eg_dir, eps_inf, stated_slme):
            simpson_res = independently_verify_energy_quadrature_slme(
                eg_ind_ev=eg_ind,
                eg_dir_ev=eg_dir,
                eps_inf=eps_inf,
                thickness_nm=thickness_nm,
                target_layer=target_layer,
            )
            calc_slme = simpson_res["standalone_slme_percent"]
            slme_diff = abs(stated_slme - calc_slme)
            slme_pass = slme_diff <= 0.10

            checks["slme_quadrature"] = {
                "stated_trapezoidal_slme_percent": stated_slme,
                "simpson_energy_slme_percent": calc_slme,
                "abs_difference_percent": round(slme_diff, 4),
                "passed": slme_pass,
            }
            if not slme_pass:
                mismatches.append(
                    f"REDUNDANCY_MISMATCH_BLOCK: SLME quadrature discrepancy {slme_diff:.4f}% > 0.10% for {cid}"
                )

            # Thermodynamic Shockley-Queisser ceiling invariant
            calc_sq = simpson_res["shockley_queisser_limit_percent"]
            thermo_pass = (stated_slme <= calc_sq + 1e-6)
            checks["thermodynamic_sq_ceiling"] = {
                "stated_slme_percent": stated_slme,
                "shockley_queisser_limit_percent": calc_sq,
                "passed": thermo_pass,
            }
            if not thermo_pass:
                mismatches.append(
                    f"REDUNDANCY_MISMATCH_BLOCK: Stated SLME {stated_slme}% violates thermodynamic SQ ceiling {calc_sq}% for {cid}"
                )

            # Sequential 4-Terminal Tandem Stack verification
            stated_tandem = opt.get("tandem_4t_total_eff_percent")
            calc_tandem = simpson_res["tandem_4t_total_eff_percent"]
            if stated_tandem is not None:
                tandem_diff = abs(stated_tandem - calc_tandem)
                tandem_pass = tandem_diff <= 0.10
                checks["sequential_4t_quadrature"] = {
                    "stated_tandem_4t_total_eff_percent": stated_tandem,
                    "simpson_tandem_4t_total_eff_percent": calc_tandem,
                    "abs_difference_percent": round(tandem_diff, 4),
                    "passed": tandem_pass,
                }
                if not tandem_pass:
                    mismatches.append(
                        f"REDUNDANCY_MISMATCH_BLOCK: 4T Tandem efficiency discrepancy {tandem_diff:.4f}% > 0.10% for {cid}"
                    )

    # -------------------------------------------------------------------------
    # Overall Redundancy Verification Assessment
    # -------------------------------------------------------------------------
    passed_all = len(mismatches) == 0

    if raise_on_error and not passed_all:
        raise AssertionError("; ".join(mismatches))

    # Generate deterministic SHA-256 signature over verified checks
    signature_payload = {
        "candidate_id": cid,
        "formula_reduced": formula,
        "checks": checks,
    }
    sha256_hex = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "candidate_id": cid,
        "formula_reduced": formula,
        "stage_verified": stage_reached,
        "passed_all_redundancy_checks": passed_all,
        "checks": checks,
        "mismatches": mismatches,
        "sha256_signature": sha256_hex,
    }
