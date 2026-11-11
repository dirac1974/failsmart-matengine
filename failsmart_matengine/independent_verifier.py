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
from pymatgen.core import Element, Structure
from pymatgen.io.cif import CifParser
import scipy.integrate
import scipy.linalg

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
# 2. IUPAC Atomic Masses & Brown-Altermatt Bond-Valence Sum Radii (Section 2.3 & 6.1)
# =============================================================================

IUPAC_ATOMIC_MASSES: Dict[str, float] = {
    el.symbol: float(el.atomic_mass) for el in Element
}

BVS_R0_RADII: Dict[str, float] = {
    "Bi": 1.52, "Sb": 1.40, "Sn": 1.42, "Cu": 1.12, "Ag": 1.28, "Zn": 1.18,
    "Ba": 1.82, "Sr": 1.68, "Ca": 1.54, "Mg": 1.30, "Ti": 1.26, "Zr": 1.42,
    "Fe": 1.24, "In": 1.38, "Ga": 1.24, "Pb": 1.56, "Cd": 1.36, "O": 0.63,
    "S": 1.04, "Se": 1.17, "Te": 1.36, "N": 0.70, "P": 1.06, "Cl": 0.99,
    "Br": 1.14, "I": 1.33,
}

BVS_R0_TABLE: Dict[Tuple[str, str], float] = {
    (e1, e2): round(r1 + r2, 4)
    for e1, r1 in BVS_R0_RADII.items()
    for e2, r2 in BVS_R0_RADII.items()
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
# 8. Independent Atomistic Phonon & NEB Solver (Section 6 - v4.0)
# =============================================================================

def independently_verify_atomistic_phonon_and_neb(
    cif_text: str,
    stoichiometry: Dict[str, int],
    oxidation_states: Dict[str, int],
) -> Dict[str, Any]:
    """Blinded independent verification of 3D Harmonic Dynamical Matrix D(q=0) & 11-Image NEB.

    Per Section 6 of docs/MATHEMATICAL_SPEC_V2.md:
    1. Parse struct = CifParser.from_str(cif_text, occupancy_tolerance=10.0).parse_structures(primitive=False)[0].
    2. Assemble 3N x 3N Harmonic Force-Constant Hessian Phi over all periodic neighbors 0.50 < r_ij <= 4.25 A.
    3. Symmetrize Phi and mass-weight using IUPAC atomic masses.
    4. Diagonalize strictly via scipy.linalg.eigvalsh(D) (sorted ascending) and convert to THz.
    5. 3D Saddle-Point NEB Migration Solver (Section 6.2).
    """
    struct = CifParser.from_str(cif_text, occupancy_tolerance=10.0).parse_structures(primitive=False)[0]
    n_sites = len(struct)
    dim = 3 * n_sites

    phi = np.zeros((dim, dim), dtype=float)
    eye3 = np.eye(3, dtype=float)

    for i in range(n_sites):
        site_i = struct[i]
        el_i = site_i.specie.symbol
        r_i = np.array(site_i.coords, dtype=float)
        neighbors = struct.get_neighbors(site_i, r=4.25)

        for nn in neighbors:
            dist = float(nn.nn_distance)
            if dist <= 0.50 or dist > 4.25:
                continue
            j = int(nn.index)
            el_j = nn.specie.symbol
            r_j = np.array(nn.coords, dtype=float)
            u_vec = (r_j - r_i) / dist

            r0 = BVS_R0_TABLE.get((el_i, el_j)) or BVS_R0_TABLE.get((el_j, el_i)) or 2.45
            k_par = 48.0 * math.exp((r0 - dist) / 0.37)
            k_perp = 0.18 * k_par

            k_block = (k_par - k_perp) * np.outer(u_vec, u_vec) + k_perp * eye3

            phi[3 * i : 3 * i + 3, 3 * j : 3 * j + 3] -= k_block
            phi[3 * i : 3 * i + 3, 3 * i : 3 * i + 3] += k_block

    # Symmetrize force-constant Hessian
    phi = 0.5 * (phi + phi.T)

    # Mass-weight by IUPAC atomic masses
    inv_sqrt_m = np.zeros(dim, dtype=float)
    for i in range(n_sites):
        el_i = struct[i].specie.symbol
        m_amu = IUPAC_ATOMIC_MASSES.get(el_i, 50.0)
        inv_sqrt_m[3 * i : 3 * i + 3] = 1.0 / math.sqrt(m_amu)

    dyn_mat = phi * np.outer(inv_sqrt_m, inv_sqrt_m)

    # Blinded diagonalization strictly via scipy.linalg.eigvalsh
    eigvals = scipy.linalg.eigvalsh(dyn_mat)
    freqs = np.sign(eigvals) * 15.633302 * np.sqrt(np.abs(eigvals))

    asr_dev = round(float(np.max(np.abs(freqs[:3]))), 6)
    opt_freqs = freqs[3:]
    min_opt_thz = round(float(opt_freqs[0]), 4) if len(opt_freqs) > 0 else 0.0
    max_lo_thz = round(float(opt_freqs[-1]), 4) if len(opt_freqs) > 0 else 0.0
    imag_count = int(np.sum(opt_freqs < -0.05))

    # 3D Saddle-Point NEB Migration Solver (Section 6.2)
    if "Cu" in stoichiometry:
        mig_sp = "Cu"
    elif "Ag" in stoichiometry:
        mig_sp = "Ag"
    elif "O" in stoichiometry:
        mig_sp = "O"
    elif "S" in stoichiometry:
        mig_sp = "S"
    else:
        mig_sp = "Se"

    target_indices = [idx for idx, site in enumerate(struct) if site.specie.symbol == mig_sp]
    best_hop_dist = 999.0
    best_r_a = np.zeros(3, dtype=float)
    best_r_b = np.zeros(3, dtype=float)

    for min_r, max_r in ((2.20, 6.50), (1.80, 9.50)):
        for idx in target_indices:
            site_i = struct[idx]
            nns = struct.get_neighbors(site_i, r=max_r)
            for nn in nns:
                if nn.specie.symbol != mig_sp:
                    continue
                d_val = float(nn.nn_distance)
                if min_r <= d_val <= max_r and d_val < best_hop_dist - 1e-6:
                    best_hop_dist = d_val
                    best_r_a = np.array(site_i.coords, dtype=float)
                    best_r_b = np.array(nn.coords, dtype=float)
        if best_hop_dist < 900.0:
            break

    r_mid = 0.5 * (best_r_a + best_r_b)
    cage_sites = struct.get_sites_in_sphere(r_mid, 5.0)
    d_cage_min = 5.0
    for cs in cage_sites:
        c_pos = np.array(cs.coords, dtype=float)
        if np.linalg.norm(c_pos - best_r_a) <= 0.25 or np.linalg.norm(c_pos - best_r_b) <= 0.25:
            continue
        d_mid = float(np.linalg.norm(c_pos - r_mid))
        if d_mid < d_cage_min:
            d_cage_min = d_mid

    d_hop = round(best_hop_dist, 4)
    clearance = round(d_cage_min, 4)

    n_tot = max(1, sum(stoichiometry.values()))
    f_oxide = stoichiometry.get("O", 0) / n_tot
    f_mobile = (stoichiometry.get("Cu", 0) + stoichiometry.get("Ag", 0)) / n_tot

    raw_barrier = (
        0.42
        + 0.14 * d_hop
        + (0.68 / (max(1.20, clearance) ** 2))
        + 0.28 * f_oxide
        - 0.22 * f_mobile
    )
    e_mig_neb = round(float(np.clip(raw_barrier, 0.35, 1.45)), 4)

    # Vineyard-Arrhenius 300 K ionic diffusivity (nu_0 = 1e12 s^-1, 1 A^2 = 1e-16 cm^2)
    d_ion_300k = (1.0 / 6.0) * 1.0e12 * ((d_hop ** 2) * 1.0e-16) * math.exp(
        -(e_mig_neb * Q_E) / (K_B * 300.0)
    )

    res: Dict[str, Any] = {
        "nsites_unit_cell": n_sites,
        "dynamical_matrix_dim": dim,
        "gamma_min_optical_freq_thz": min_opt_thz,
        "gamma_max_lo_freq_thz": max_lo_thz,
        "imaginary_mode_count": imag_count,
        "acoustic_sum_rule_max_dev_thz": asr_dev,
        "migrating_species": mig_sp,
        "shortest_hop_distance_ang": d_hop,
        "bottleneck_clearance_ang": clearance,
        "neb_saddle_barrier_ev": e_mig_neb,
        "room_temp_diffusivity_cm2_s": float(f"{d_ion_300k:.3e}"),
    }

    sig_payload = {
        "phonon": {
            "asr_dev": asr_dev,
            "gamma_min": min_opt_thz,
            "gamma_max": max_lo_thz,
            "imag_count": imag_count,
        },
        "neb": {
            "migrating_species": mig_sp,
            "shortest_hop_distance_ang": d_hop,
            "bottleneck_clearance_ang": clearance,
            "neb_saddle_barrier_ev": e_mig_neb,
        },
    }
    res["sha256_signature"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return res


# =============================================================================
# 9. Independent Coherent TMM vs Recursive Rouard/Airy 4T Stack (Section 7 - v4.0)
# =============================================================================

def independently_verify_coherent_tmm_4t_stack(
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    thickness_nm_1: float,
    eg_ind_3: float,
    eg_dir_3: float,
    eps_inf_3: float,
    thickness_nm_3: float,
) -> Dict[str, Any]:
    """Blinded independent verification of coherent multilayer optics via Method B.

    Per Section 7.2 of docs/MATHEMATICAL_SPEC_V2.md:
    Uses Recursive Rouard / Airy Amplitude Addition from Rear Interface (m=4 -> 0)
    strictly on the uniform photon-energy grid ENERGY_GRID_EV (N=8001 points) with
    Simpson 1/3 quadrature.
    """
    wl_nm = LAMBDA_GRID_NM
    wl_um = wl_nm / 1000.0

    # Complex refractive indices of the 6 media (m = 0..5) on the energy grid
    n0 = np.ones_like(wl_nm, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um ** 2)).astype(np.complex128)

    n_ito_real = np.maximum(1.45, 1.92 - 0.085 * (wl_um ** 2))
    k_ito = 0.0018 + 0.0065 * (wl_um ** 3)
    n2 = n_ito_real + 1j * k_ito

    alpha1 = 1.2e5 * (np.maximum(0.0, ENERGY_GRID_EV - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, ENERGY_GRID_EV - eg_dir_1))
    n_act_real = math.sqrt(eps_inf_1) + 0.035 / (wl_um ** 2)
    k_act = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n3 = n_act_real + 1j * k_act

    n_buf_real = 1.720 + 0.0040 / (wl_um ** 2)
    k_buf = 0.0012 * (wl_um ** 2)
    n4 = n_buf_real + 1j * k_buf

    n5 = np.full_like(wl_nm, 1.520, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5]
    d_list_nm = [0.0, 98.0, 105.0, float(thickness_nm_1), 85.0, 0.0]

    # Method B: Recursive Rouard / Airy amplitude addition from rear interface (4,5) to (0,1)
    r_amp = (n4 - n5) / (n4 + n5)
    t_amp = (2.0 * n4) / (n4 + n5)

    for m in (3, 2, 1, 0):
        nm_curr = n_list[m]
        nm_next = n_list[m + 1]
        r_m = (nm_curr - nm_next) / (nm_curr + nm_next)
        t_m = (2.0 * nm_curr) / (nm_curr + nm_next)
        beta_next = (2.0 * math.pi * nm_next * d_list_nm[m + 1]) / wl_nm
        phi_next = np.exp(1j * beta_next)
        denom = 1.0 + r_m * r_amp * (phi_next ** 2)
        r_amp = (r_m + r_amp * (phi_next ** 2)) / denom
        t_amp = (t_m * t_amp * phi_next) / denom

    r_tmm_1 = np.abs(r_amp) ** 2
    t_tmm_1 = (np.real(n5) / np.real(n0)) * (np.abs(t_amp) ** 2)
    t_ito_front = np.exp(-4.0 * math.pi * k_ito * 105.0 / wl_nm)

    # Top cell absorptance and stack transmittance
    yab1 = 4.0 * eps_inf_1
    d1_m = thickness_nm_1 * 1.0e-9
    fabs1 = (yab1 * alpha1 * d1_m) / (1.0 + yab1 * alpha1 * d1_m)
    a_tmm_1 = (1.0 - r_tmm_1) * t_ito_front * fabs1
    t_stack_tmm_1 = t_tmm_1 * (1.0 - fabs1)

    # Check photon conservation identically: A + T + R <= 1.0
    conservation_holds = bool(np.all(a_tmm_1 + t_stack_tmm_1 + r_tmm_1 <= 1.0 + 1e-12))

    # Mean front reflectance over above-bandgap solar window [eg_ind_1, 3.50] eV
    mask_above = (ENERGY_GRID_EV >= eg_ind_1) & (ENERGY_GRID_EV <= 3.50)
    flux_above = float(scipy.integrate.simpson(SOLAR_PHOTON_FLUX_E[mask_above], x=ENERGY_GRID_EV[mask_above]))
    mean_refl_pct = float(
        scipy.integrate.simpson(r_tmm_1[mask_above] * SOLAR_PHOTON_FLUX_E[mask_above], x=ENERGY_GRID_EV[mask_above])
        / max(1.0e-12, flux_above)
        * 100.0
    )

    # Sub-bandgap transmittance over [0.75, eg_ind_1 - 0.02] eV
    mask_sub = (ENERGY_GRID_EV >= 0.75) & (ENERGY_GRID_EV <= (eg_ind_1 - 0.02))
    flux_sub = float(scipy.integrate.simpson(SOLAR_PHOTON_FLUX_E[mask_sub], x=ENERGY_GRID_EV[mask_sub]))
    sub_trans_pct = float(
        scipy.integrate.simpson(t_stack_tmm_1[mask_sub] * SOLAR_PHOTON_FLUX_E[mask_sub], x=ENERGY_GRID_EV[mask_sub])
        / max(1.0e-12, flux_sub)
        * 100.0
    )

    # Step A — Layer 1 PCE
    cell1 = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_tmm_1,
        incident_photon_flux_e=SOLAR_PHOTON_FLUX_E,
        eg_ind_ev=eg_ind_1,
        eg_dir_ev=eg_dir_1,
    )
    eta_top = cell1["eff"]

    # Step B — Layer 2: c-Si Wafer under transmitted flux phi2_tmm
    phi2_tmm = SOLAR_PHOTON_FLUX_E * t_stack_tmm_1
    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, ENERGY_GRID_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(np.maximum(0.0, ENERGY_GRID_EV - 3.40))

    fabs_si_2l = (49.0 * alpha_si * d_si_m) / (1.0 + 49.0 * alpha_si * d_si_m)
    cell_si_2l = _solve_pv_cell_energy_quadrature(
        absorptance_e=0.98 * fabs_si_2l,
        incident_photon_flux_e=phi2_tmm,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    cell_si_3l = _solve_pv_cell_energy_quadrature(
        absorptance_e=0.98 * fabs_si_3l,
        incident_photon_flux_e=phi2_tmm,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    t_si_fca_low = np.exp(-0.08 * ((wl_nm / 1200.0) ** 2))
    t_si_fca_std = np.exp(-0.38 * ((wl_nm / 1200.0) ** 2))
    phi3_low = phi2_tmm * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
    phi3_std = phi2_tmm * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std

    # Step C — Layer 3: Bottom IR Scavenger
    d3_m = thickness_nm_3 * 1.0e-9
    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, ENERGY_GRID_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, ENERGY_GRID_EV - eg_dir_3))
    fabs3 = (yab3 * alpha3 * d3_m) / (1.0 + yab3 * alpha3 * d3_m)
    a_tmm_3 = (1.0 - r_int_23) * fabs3

    cell3_low = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_tmm_3,
        incident_photon_flux_e=phi3_low,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )
    cell3_std = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_tmm_3,
        incident_photon_flux_e=phi3_std,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )

    tmm_2l = round(eta_top + cell_si_2l["eff"], 2)
    tmm_4t_std = round(eta_top + cell_si_3l["eff"] + cell3_std["eff"], 2)
    tmm_4t_low = round(eta_top + cell_si_3l["eff"] + cell3_low["eff"], 2)

    res: Dict[str, Any] = {
        "tmm_mean_front_reflectance_percent": round(mean_refl_pct, 2),
        "tmm_sub_bandgap_transmittance_percent": round(sub_trans_pct, 2),
        "tmm_top_pce_percent": round(eta_top, 2),
        "tmm_si_pce_percent": round(cell_si_3l["eff"], 2),
        "tmm_bottom_std_si_pce_percent": round(cell3_std["eff"], 2),
        "tmm_bottom_pce_percent": round(cell3_low["eff"], 2),
        "tmm_2layer_pce_percent": tmm_2l,
        "tmm_4t_std_si_pce_percent": tmm_4t_std,
        "tmm_4t_low_fca_pce_percent": tmm_4t_low,
        "photon_conservation_holds": conservation_holds,
    }

    sig_payload = {
        "tmm_mean_front_reflectance_percent": res["tmm_mean_front_reflectance_percent"],
        "tmm_sub_bandgap_transmittance_percent": res["tmm_sub_bandgap_transmittance_percent"],
        "tmm_top_pce_percent": res["tmm_top_pce_percent"],
        "tmm_si_pce_percent": res["tmm_si_pce_percent"],
        "tmm_bottom_pce_percent": res["tmm_bottom_pce_percent"],
        "tmm_4t_low_fca_pce_percent": res["tmm_4t_low_fca_pce_percent"],
    }
    res["sha256_signature"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return res


# =============================================================================
# 10. Independent Graded-Index Double-Layer ARC + TiO2 Stack & 4-Metric Techno-Economic Suite (Section 8 - v5.0)
# =============================================================================

def independently_verify_graded_arc_and_techno_economics(
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    thickness_nm_1: float,
    eg_ind_3: float,
    eg_dir_3: float,
    eps_inf_3: float,
    thickness_nm_3: float,
    raw_cost_top_usd_m2: float,
    raw_cost_bot_usd_m2: float,
) -> Dict[str, Any]:
    """Blinded independent verification of 7-medium graded-ARC + TiO2 stack & techno-economic metrics.

    Per Section 8.1 and Section 8.2 of docs/MATHEMATICAL_SPEC_V2.md:
    - Solves the 7-medium coherent thin-film stack (m = 0..6: Air / 94.0 nm MgF2 / 80.0 nm ITO /
      48.0 nm TiO2 / d_top_nm Absorber / 82.0 nm Buffer / Couplant) using Method B (Recursive
      Rouard / Airy backward amplitude addition from interface (5,6) down to (0,1)) on the
      photon-energy grid ENERGY_GRID_EV (N_E = 8001 points) integrated via scipy.integrate.simpson.
    - Computes all Section 8.2 4-Metric Techno-Economic Figure-of-Merit quantities.
    """
    wl_nm = LAMBDA_GRID_NM
    wl_um = wl_nm / 1000.0

    # Complex refractive indices of the 7 media (m = 0..6) on the energy grid
    n0 = np.ones_like(wl_nm, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um ** 2)).astype(np.complex128)

    n_ito_real = np.maximum(1.45, 1.92 - 0.085 * (wl_um ** 2))
    k_ito = 0.0018 + 0.0065 * (wl_um ** 3)
    n2 = n_ito_real + 1j * k_ito

    n_tio2_real = 2.380 + 0.0180 / (wl_um ** 2)
    k_tio2 = 0.0004 * (wl_um ** 2)
    n3 = n_tio2_real + 1j * k_tio2

    alpha1 = 1.2e5 * (np.maximum(0.0, ENERGY_GRID_EV - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, ENERGY_GRID_EV - eg_dir_1))
    n_act_real = math.sqrt(eps_inf_1) + 0.035 / (wl_um ** 2)
    k_act = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n4 = n_act_real + 1j * k_act

    n_buf_real = 1.720 + 0.0040 / (wl_um ** 2)
    k_buf = 0.0012 * (wl_um ** 2)
    n5 = n_buf_real + 1j * k_buf

    n6 = np.full_like(wl_nm, 1.520, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5, n6]
    d_list_nm = [0.0, 94.0, 80.0, 48.0, float(thickness_nm_1), 82.0, 0.0]

    # Method B: Recursive Rouard / Airy backward amplitude addition from interface (5,6) down to (0,1)
    r_amp = (n5 - n6) / (n5 + n6)
    t_amp = (2.0 * n5) / (n5 + n6)

    for m in (4, 3, 2, 1, 0):
        nm_curr = n_list[m]
        nm_next = n_list[m + 1]
        r_m = (nm_curr - nm_next) / (nm_curr + nm_next)
        t_m = (2.0 * nm_curr) / (nm_curr + nm_next)
        beta_next = (2.0 * math.pi * nm_next * d_list_nm[m + 1]) / wl_nm
        phi_next = np.exp(1j * beta_next)
        denom = 1.0 + r_m * r_amp * (phi_next ** 2)
        r_amp = (r_m + r_amp * (phi_next ** 2)) / denom
        t_amp = (t_m * t_amp * phi_next) / denom

    r_arc_1 = np.abs(r_amp) ** 2
    t_arc_1 = (np.real(n6) / np.real(n0)) * (np.abs(t_amp) ** 2)
    t_win_front = np.exp(-4.0 * math.pi * (k_ito * 80.0 + k_tio2 * 48.0) / wl_nm)

    # Top cell absorptance and stack transmittance
    yab1 = 4.0 * eps_inf_1
    d1_m = thickness_nm_1 * 1.0e-9
    fabs1 = (yab1 * alpha1 * d1_m) / (1.0 + yab1 * alpha1 * d1_m)
    a_arc_1 = (1.0 - r_arc_1) * t_win_front * fabs1
    t_stack_arc_1 = t_arc_1 * (1.0 - fabs1)

    # Verify photon conservation identically: A + T + R <= 1.0
    conservation_holds = bool(np.all(a_arc_1 + t_stack_arc_1 + r_arc_1 <= 1.0 + 1e-12))

    # Mean front reflectance over above-bandgap solar window [eg_ind_1, 3.50] eV
    mask_above = (ENERGY_GRID_EV >= eg_ind_1) & (ENERGY_GRID_EV <= 3.50)
    flux_above = float(scipy.integrate.simpson(SOLAR_PHOTON_FLUX_E[mask_above], x=ENERGY_GRID_EV[mask_above]))
    mean_refl_pct = float(
        scipy.integrate.simpson(r_arc_1[mask_above] * SOLAR_PHOTON_FLUX_E[mask_above], x=ENERGY_GRID_EV[mask_above])
        / max(1.0e-12, flux_above)
        * 100.0
    )

    # Sub-bandgap transmittance over [0.75, eg_ind_1 - 0.02] eV
    mask_sub = (ENERGY_GRID_EV >= 0.75) & (ENERGY_GRID_EV <= (eg_ind_1 - 0.02))
    flux_sub = float(scipy.integrate.simpson(SOLAR_PHOTON_FLUX_E[mask_sub], x=ENERGY_GRID_EV[mask_sub]))
    sub_trans_pct = float(
        scipy.integrate.simpson(t_stack_arc_1[mask_sub] * SOLAR_PHOTON_FLUX_E[mask_sub], x=ENERGY_GRID_EV[mask_sub])
        / max(1.0e-12, flux_sub)
        * 100.0
    )

    # Step A — Layer 1 PCE
    cell1 = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_arc_1,
        incident_photon_flux_e=SOLAR_PHOTON_FLUX_E,
        eg_ind_ev=eg_ind_1,
        eg_dir_ev=eg_dir_1,
    )
    eta_top = cell1["eff"]

    # Step B — Layer 2: c-Si Wafer under transmitted flux phi2_arc
    phi2_arc = SOLAR_PHOTON_FLUX_E * t_stack_arc_1
    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, ENERGY_GRID_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(np.maximum(0.0, ENERGY_GRID_EV - 3.40))

    fabs_si_2l = (49.0 * alpha_si * d_si_m) / (1.0 + 49.0 * alpha_si * d_si_m)
    cell_si_2l = _solve_pv_cell_energy_quadrature(
        absorptance_e=0.98 * fabs_si_2l,
        incident_photon_flux_e=phi2_arc,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    cell_si_3l = _solve_pv_cell_energy_quadrature(
        absorptance_e=0.98 * fabs_si_3l,
        incident_photon_flux_e=phi2_arc,
        eg_ind_ev=1.12,
        eg_dir_ev=1.12,
        j0_rad_fixed=1.2e-12,
    )

    t_si_fca_low = np.exp(-0.08 * ((wl_nm / 1200.0) ** 2))
    t_si_fca_std = np.exp(-0.38 * ((wl_nm / 1200.0) ** 2))
    phi3_low = phi2_arc * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
    phi3_std = phi2_arc * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std

    # Step C — Layer 3: Bottom IR Scavenger
    d3_m = thickness_nm_3 * 1.0e-9
    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, ENERGY_GRID_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, ENERGY_GRID_EV - eg_dir_3))
    fabs3 = (yab3 * alpha3 * d3_m) / (1.0 + yab3 * alpha3 * d3_m)
    a_arc_3 = (1.0 - r_int_23) * fabs3

    cell3_low = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_arc_3,
        incident_photon_flux_e=phi3_low,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )
    cell3_std = _solve_pv_cell_energy_quadrature(
        absorptance_e=a_arc_3,
        incident_photon_flux_e=phi3_std,
        eg_ind_ev=eg_ind_3,
        eg_dir_ev=eg_dir_3,
    )

    graded_2l = round(eta_top + cell_si_2l["eff"], 2)
    graded_4t_std = round(eta_top + cell_si_3l["eff"] + cell3_std["eff"], 2)
    graded_4t_low = round(eta_top + cell_si_3l["eff"] + cell3_low["eff"], 2)

    # Section 8.2: 4-Metric Techno-Economic & Area-Constrained Figure-of-Merit Suite
    eta_si_ref = 22.00
    c_si_mod = 40.00
    c_bos_area = 100.00
    sqft_to_m2 = 0.09290304

    eta_2l = graded_2l
    eta_3l = graded_4t_low

    c_raw_top = float(raw_cost_top_usd_m2)
    c_raw_bot = float(raw_cost_bot_usd_m2)
    c_raw_comb = c_raw_top + c_raw_bot

    delta_c_2l = c_raw_top + 6.50
    delta_c_3l = c_raw_comb + 13.00

    p_m2_2l = 10.0 * eta_2l
    p_sqft_2l = p_m2_2l * sqft_to_m2
    p_m2_3l = 10.0 * eta_3l
    p_sqft_3l = p_m2_3l * sqft_to_m2

    g_eta_2l = eta_2l / eta_si_ref
    g_eta_3l = eta_3l / eta_si_ref

    cer_2l = (2.0 * c_si_mod * g_eta_2l) / (c_si_mod + delta_c_2l)
    cer_3l = (3.0 * c_si_mod * g_eta_3l) / (c_si_mod + delta_c_3l)

    delta_p_2l = max(1.0e-9, 10.0 * (eta_2l - eta_si_ref))
    delta_p_3l = max(1.0e-9, 10.0 * (eta_3l - eta_si_ref))

    mciw_2l_raw = c_raw_top / delta_p_2l
    mciw_2l_full = delta_c_2l / delta_p_2l
    mciw_3l_raw = c_raw_comb / delta_p_3l
    mciw_3l_full = delta_c_3l / delta_p_3l

    cpr_mod_2l = g_eta_2l / (1.0 + delta_c_2l / c_si_mod)
    cpr_mod_3l = g_eta_3l / (1.0 + delta_c_3l / c_si_mod)

    svi_bos_2l = ((c_si_mod + c_bos_area) * g_eta_2l) / (c_si_mod + c_bos_area + delta_c_2l)
    svi_bos_3l = ((c_si_mod + c_bos_area) * g_eta_3l) / (c_si_mod + c_bos_area + delta_c_3l)

    res: Dict[str, Any] = {
        "graded_arc_front_reflectance_percent": round(mean_refl_pct, 2),
        "graded_sub_bandgap_transmittance_percent": round(sub_trans_pct, 2),
        "graded_top_pce_percent": round(eta_top, 2),
        "graded_si_pce_percent": round(cell_si_3l["eff"], 2),
        "graded_bottom_std_si_pce_percent": round(cell3_std["eff"], 2),
        "graded_bottom_pce_percent": round(cell3_low["eff"], 2),
        "graded_2layer_pce_percent": graded_2l,
        "graded_4t_std_si_pce_percent": graded_4t_std,
        "graded_4t_low_fca_pce_percent": graded_4t_low,
        "power_density_2l_w_m2": round(p_m2_2l, 2),
        "power_density_2l_w_sqft": round(p_sqft_2l, 2),
        "power_density_3l_w_m2": round(p_m2_3l, 2),
        "power_density_3l_w_sqft": round(p_sqft_3l, 2),
        "eff_gain_ratio_2l": round(g_eta_2l, 4),
        "eff_gain_ratio_3l": round(g_eta_3l, 4),
        "cer_2l_vs_2x_si": round(cer_2l, 4),
        "cer_3l_vs_3x_si": round(cer_3l, 4),
        "mciw_2l_raw_usd_per_dw": round(mciw_2l_raw, 4),
        "mciw_2l_full_usd_per_dw": round(mciw_2l_full, 4),
        "mciw_3l_raw_usd_per_dw": round(mciw_3l_raw, 4),
        "mciw_3l_full_usd_per_dw": round(mciw_3l_full, 4),
        "cpr_mod_2l": round(cpr_mod_2l, 4),
        "cpr_mod_3l": round(cpr_mod_3l, 4),
        "svi_bos_2l": round(svi_bos_2l, 4),
        "svi_bos_3l": round(svi_bos_3l, 4),
        "top_raw_cost_usd_m2": round(c_raw_top, 4),
        "combined_raw_cost_usd_m2": round(c_raw_comb, 4),
        "photon_conservation_holds": conservation_holds,
    }

    sig_payload = {
        "graded_arc_front_reflectance_percent": res["graded_arc_front_reflectance_percent"],
        "graded_sub_bandgap_transmittance_percent": res["graded_sub_bandgap_transmittance_percent"],
        "graded_top_pce_percent": res["graded_top_pce_percent"],
        "graded_2layer_pce_percent": res["graded_2layer_pce_percent"],
        "graded_4t_low_fca_pce_percent": res["graded_4t_low_fca_pce_percent"],
        "cer_2l_vs_2x_si": res["cer_2l_vs_2x_si"],
        "cer_3l_vs_3x_si": res["cer_3l_vs_3x_si"],
        "svi_bos_2l": res["svi_bos_2l"],
        "svi_bos_3l": res["svi_bos_3l"],
    }
    res["sha256_signature"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return res


# =============================================================================
# 11. Phase 9 Engineering Extensions (9A, 9B, 9C - v6.0)
# =============================================================================

_BLIND_IUPAC_MASSES: Dict[str, float] = dict(IUPAC_ATOMIC_MASSES)



def independently_verify_phase9a_lab_and_defect_dossier(
    cif_content: str,
    stoichiometry: Dict[str, int],
    eps_static: float,
) -> Dict[str, Any]:
    """Blinded independent verification of Phase 9A 10.0 mmol synthesis mass balance & doped supercell FNV corrections."""
    formula_unit_molar_mass_g_mol = sum(
        cnt * _BLIND_IUPAC_MASSES[el] for el, cnt in stoichiometry.items()
    )
    target_product_mass_g = 0.010 * formula_unit_molar_mass_g_mol

    struct = CifParser.from_str(cif_content).parse_structures(primitive=False)[0]
    a, b, c = struct.lattice.abc
    na = max(1, math.ceil(10.0 / a))
    nb = max(1, math.ceil(10.0 / b))
    nc = max(1, math.ceil(10.0 / c))
    supercell_total_sites = int(na * nb * nc * len(struct))
    supercell_min_image_dist_ang = min(na * a, nb * b, nc * c)
    l_eff = (struct.volume * na * nb * nc) ** (1.0 / 3.0)

    fnv_charge_correction_q1_ev = (1.0 * 2.8373 * 14.399645) / (eps_static * l_eff)
    fnv_charge_correction_q2_ev = (4.0 * 2.8373 * 14.399645) / (eps_static * l_eff)

    res: Dict[str, Any] = {
        "formula_unit_molar_mass_g_mol": round(float(formula_unit_molar_mass_g_mol), 4),
        "target_product_mass_g": round(float(target_product_mass_g), 6),
        "supercell_dims": [int(na), int(nb), int(nc)],
        "supercell_total_sites": supercell_total_sites,
        "supercell_min_image_dist_ang": round(float(supercell_min_image_dist_ang), 4),
        "fnv_charge_correction_q1_ev": round(float(fnv_charge_correction_q1_ev), 4),
        "fnv_charge_correction_q2_ev": round(float(fnv_charge_correction_q2_ev), 4),
    }

    sig_payload = {
        "formula_unit_molar_mass_g_mol": res["formula_unit_molar_mass_g_mol"],
        "target_product_mass_g": res["target_product_mass_g"],
        "supercell_dims": res["supercell_dims"],
        "supercell_total_sites": res["supercell_total_sites"],
        "supercell_min_image_dist_ang": res["supercell_min_image_dist_ang"],
        "fnv_charge_correction_q1_ev": res["fnv_charge_correction_q1_ev"],
        "fnv_charge_correction_q2_ev": res["fnv_charge_correction_q2_ev"],
    }
    res["sha256_signature"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return res


def independently_verify_phase9b_contrastive_audit(
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Blinded independent verification of Phase 9B Contrastive Failure Memory Classifier margin."""
    pos_vecs: List[np.ndarray] = []
    neg_vecs: List[np.ndarray] = []

    for rec in records:
        status = rec.get("status", "")
        emb = np.array(rec.get("embedding_128d", []), dtype=np.float64)
        norm = float(np.linalg.norm(emb))
        u_hat = emb / max(1.0e-12, norm)
        if status == "PROMOTED":
            pos_vecs.append(u_hat)
        elif status == "REJECTED":
            neg_vecs.append(u_hat)

    pos_sum = np.sum(pos_vecs, axis=0)
    c_pos = pos_sum / max(1.0e-12, float(np.linalg.norm(pos_sum)))

    neg_sum = np.sum(neg_vecs, axis=0)
    c_neg = neg_sum / max(1.0e-12, float(np.linalg.norm(neg_sum)))

    pos_margins = [float(np.dot(u, c_pos) - np.dot(u, c_neg)) for u in pos_vecs]
    neg_margins = [float(np.dot(u, c_pos) - np.dot(u, c_neg)) for u in neg_vecs]

    mean_pos = float(np.mean(pos_margins)) if pos_margins else 0.0
    mean_neg = float(np.mean(neg_margins)) if neg_margins else 0.0
    delta_sep = mean_pos - mean_neg

    res: Dict[str, Any] = {
        "mean_promoted_contrastive_margin": round(mean_pos, 4),
        "mean_rejected_contrastive_margin": round(mean_neg, 4),
        "contrastive_separation_delta": round(delta_sep, 4),
    }

    sig_payload = {
        "mean_promoted_contrastive_margin": res["mean_promoted_contrastive_margin"],
        "mean_rejected_contrastive_margin": res["mean_rejected_contrastive_margin"],
        "contrastive_separation_delta": res["contrastive_separation_delta"],
    }
    res["sha256_signature"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return res


def _compute_rouard_airy_7medium_oblique_sp(
    e_grid: np.ndarray,
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    d_top_nm: float,
    theta_deg: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Recursive Rouard / Airy backward amplitude addition for s and p polarizations on the 7-medium stack."""
    wl_nm = HC_Q_NM / e_grid
    wl_um = wl_nm / 1000.0

    n0 = np.ones_like(wl_nm, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um ** 2)).astype(np.complex128)

    n_ito_real = np.maximum(1.45, 1.92 - 0.085 * (wl_um ** 2))
    k_ito = 0.0018 + 0.0065 * (wl_um ** 3)
    n2 = n_ito_real + 1j * k_ito

    n_tio2_real = 2.380 + 0.0180 / (wl_um ** 2)
    k_tio2 = 0.0004 * (wl_um ** 2)
    n3 = n_tio2_real + 1j * k_tio2

    alpha1 = 1.2e5 * (np.maximum(0.0, e_grid - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, e_grid - eg_dir_1)
    )
    n_act_real = math.sqrt(eps_inf_1) + 0.035 / (wl_um ** 2)
    k_act = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n4 = n_act_real + 1j * k_act

    n_buf_real = 1.720 + 0.0040 / (wl_um ** 2)
    k_buf = 0.0012 * (wl_um ** 2)
    n5 = n_buf_real + 1j * k_buf

    n6 = np.full_like(wl_nm, 1.520, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5, n6]
    d_list_nm = [0.0, 94.0, 80.0, 48.0, float(d_top_nm), 82.0, 0.0]

    theta_rad = math.radians(theta_deg)
    sin_theta0 = math.sin(theta_rad)

    cos_list: List[np.ndarray] = []
    eta_s_list: List[np.ndarray] = []
    eta_p_list: List[np.ndarray] = []

    for nm in n_list:
        cos_m = np.sqrt(1.0 - ((n0 * sin_theta0) / nm) ** 2)
        cos_list.append(cos_m)
        eta_s_list.append(nm * cos_m)
        eta_p_list.append(nm / cos_m)

    # s-polarization backward Rouard / Airy recursion from (5,6) down to (0,1)
    r_s = (eta_s_list[5] - eta_s_list[6]) / (eta_s_list[5] + eta_s_list[6])
    t_s = (2.0 * eta_s_list[5]) / (eta_s_list[5] + eta_s_list[6])
    for m in (4, 3, 2, 1, 0):
        es_curr = eta_s_list[m]
        es_next = eta_s_list[m + 1]
        r_m = (es_curr - es_next) / (es_curr + es_next)
        t_m = (2.0 * es_curr) / (es_curr + es_next)
        beta_next = (2.0 * math.pi * n_list[m + 1] * d_list_nm[m + 1] * cos_list[m + 1]) / wl_nm
        phi_next = np.exp(1j * beta_next)
        denom = 1.0 + r_m * r_s * (phi_next ** 2)
        r_s = (r_m + r_s * (phi_next ** 2)) / denom
        t_s = (t_m * t_s * phi_next) / denom

    # p-polarization backward Rouard / Airy recursion from (5,6) down to (0,1)
    r_p = (eta_p_list[5] - eta_p_list[6]) / (eta_p_list[5] + eta_p_list[6])
    t_p = (2.0 * eta_p_list[5]) / (eta_p_list[5] + eta_p_list[6])
    for m in (4, 3, 2, 1, 0):
        ep_curr = eta_p_list[m]
        ep_next = eta_p_list[m + 1]
        r_m = (ep_curr - ep_next) / (ep_curr + ep_next)
        t_m = (2.0 * ep_curr) / (ep_curr + ep_next)
        beta_next = (2.0 * math.pi * n_list[m + 1] * d_list_nm[m + 1] * cos_list[m + 1]) / wl_nm
        phi_next = np.exp(1j * beta_next)
        denom = 1.0 + r_m * r_p * (phi_next ** 2)
        r_p = (r_m + r_p * (phi_next ** 2)) / denom
        t_p = (t_m * t_p * phi_next) / denom

    r_unpol = 0.5 * ((np.abs(r_s) ** 2) + (np.abs(r_p) ** 2))
    t_unpol = 0.5 * (
        (np.real(eta_s_list[6]) / np.real(eta_s_list[0])) * (np.abs(t_s) ** 2)
        + (np.real(eta_p_list[6]) / np.real(eta_p_list[0])) * (np.abs(t_p) ** 2)
    )

    cos2_real = np.maximum(0.25, np.real(cos_list[2]))
    cos3_real = np.maximum(0.25, np.real(cos_list[3]))
    t_win_front = np.exp(
        -4.0 * math.pi * ((k_ito * 80.0 / cos2_real) + (k_tio2 * 48.0 / cos3_real)) / wl_nm
    )

    return r_unpol, t_unpol, t_win_front


def independently_verify_phase9c_oblique_thermal_lcoe(
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    thickness_nm_1: float,
    eg_ind_3: float,
    eg_dir_3: float,
    eps_inf_3: float,
    thickness_nm_3: float,
    raw_cost_top_usd_m2: float,
    raw_cost_bot_usd_m2: float,
    limiting_neb_barrier_ev: float,
) -> Dict[str, Any]:
    """Blinded independent verification of Phase 9C oblique-incidence S/P TMM, operating temp, and 25-year Arrhenius LCOE."""
    wl_nm = LAMBDA_GRID_NM
    alpha1 = 1.2e5 * (np.maximum(0.0, ENERGY_GRID_EV - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, ENERGY_GRID_EV - eg_dir_1)
    )
    yab1 = 4.0 * eps_inf_1
    d1_m = thickness_nm_1 * 1.0e-9
    fabs1 = (yab1 * alpha1 * d1_m) / (1.0 + yab1 * alpha1 * d1_m)

    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, ENERGY_GRID_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(
        np.maximum(0.0, ENERGY_GRID_EV - 3.40)
    )
    fabs_si_2l = (49.0 * alpha_si * d_si_m) / (1.0 + 49.0 * alpha_si * d_si_m)
    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    t_si_fca_low = np.exp(-0.08 * ((wl_nm / 1200.0) ** 2))

    d3_m = thickness_nm_3 * 1.0e-9
    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, ENERGY_GRID_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, ENERGY_GRID_EV - eg_dir_3)
    )
    fabs3 = (yab3 * alpha3 * d3_m) / (1.0 + yab3 * alpha3 * d3_m)
    a_arc_3 = (1.0 - r_int_23) * fabs3

    mask_above = (ENERGY_GRID_EV >= eg_ind_1) & (ENERGY_GRID_EV <= 3.50)
    flux_above = float(
        scipy.integrate.simpson(SOLAR_PHOTON_FLUX_E[mask_above], x=ENERGY_GRID_EV[mask_above])
    )

    r_front_by_angle: Dict[int, float] = {}
    pce_4t_by_angle: Dict[int, float] = {}
    subcells_0deg: Dict[str, float] = {}
    pce_2l_0deg: float = 0.0

    for theta_deg in (0, 30, 45, 60):
        r_unpol, t_unpol, t_win_front = _compute_rouard_airy_7medium_oblique_sp(
            e_grid=ENERGY_GRID_EV,
            eg_ind_1=eg_ind_1,
            eg_dir_1=eg_dir_1,
            eps_inf_1=eps_inf_1,
            d_top_nm=thickness_nm_1,
            theta_deg=float(theta_deg),
        )
        mean_refl_pct = float(
            scipy.integrate.simpson(
                r_unpol[mask_above] * SOLAR_PHOTON_FLUX_E[mask_above],
                x=ENERGY_GRID_EV[mask_above],
            )
            / max(1.0e-12, flux_above)
            * 100.0
        )
        r_front_by_angle[theta_deg] = mean_refl_pct

        a_arc_1 = (1.0 - r_unpol) * t_win_front * fabs1
        t_stack_arc_1 = t_unpol * (1.0 - fabs1)

        cell1 = _solve_pv_cell_energy_quadrature(
            absorptance_e=a_arc_1,
            incident_photon_flux_e=SOLAR_PHOTON_FLUX_E,
            eg_ind_ev=eg_ind_1,
            eg_dir_ev=eg_dir_1,
        )
        phi2 = SOLAR_PHOTON_FLUX_E * t_stack_arc_1
        cell_si_3l = _solve_pv_cell_energy_quadrature(
            absorptance_e=0.98 * fabs_si_3l,
            incident_photon_flux_e=phi2,
            eg_ind_ev=1.12,
            eg_dir_ev=1.12,
            j0_rad_fixed=1.2e-12,
        )
        phi3_low = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
        cell3_low = _solve_pv_cell_energy_quadrature(
            absorptance_e=a_arc_3,
            incident_photon_flux_e=phi3_low,
            eg_ind_ev=eg_ind_3,
            eg_dir_ev=eg_dir_3,
        )

        pce_4t = cell1["eff"] + cell_si_3l["eff"] + cell3_low["eff"]
        pce_4t_by_angle[theta_deg] = pce_4t

        if theta_deg == 0:
            cell_si_2l = _solve_pv_cell_energy_quadrature(
                absorptance_e=0.98 * fabs_si_2l,
                incident_photon_flux_e=phi2,
                eg_ind_ev=1.12,
                eg_dir_ev=1.12,
                j0_rad_fixed=1.2e-12,
            )
            pce_2l_0deg = cell1["eff"] + cell_si_2l["eff"]
            subcells_0deg = {
                "top": cell1["eff"],
                "si_3l": cell_si_3l["eff"],
                "si_2l": cell_si_2l["eff"],
                "bot": cell3_low["eff"],
            }

    r_hemi = (
        0.35 * r_front_by_angle[0]
        + 0.35 * r_front_by_angle[30]
        + 0.20 * r_front_by_angle[45]
        + 0.10 * r_front_by_angle[60]
    )
    iam_60 = (100.0 - r_front_by_angle[60]) / max(1.0e-9, 100.0 - r_front_by_angle[0])

    # Section 9.3.2: Field Operating Temperature Coefficient (25 C -> 45 C -> 65 C)
    gamma_top = -0.00440 / (eg_ind_1 ** 0.65)
    gamma_si = -0.00440 / (1.12 ** 0.65)
    gamma_bot = -0.00440 / (eg_ind_3 ** 0.65)

    eta_top_25 = subcells_0deg["top"]
    eta_si3l_25 = subcells_0deg["si_3l"]
    eta_si2l_25 = subcells_0deg["si_2l"]
    eta_bot_25 = subcells_0deg["bot"]
    eta_4t_25 = pce_4t_by_angle[0]
    eta_2l_25 = pce_2l_0deg

    eta_top_45 = eta_top_25 * (1.0 + gamma_top * 20.0)
    eta_si3l_45 = eta_si3l_25 * (1.0 + gamma_si * 20.0)
    eta_si2l_45 = eta_si2l_25 * (1.0 + gamma_si * 20.0)
    eta_bot_45 = eta_bot_25 * (1.0 + gamma_bot * 20.0)
    eta_4t_45 = eta_top_45 + eta_si3l_45 + eta_bot_45
    eta_2l_45 = eta_top_45 + eta_si2l_45

    eta_top_65 = eta_top_25 * (1.0 + gamma_top * 40.0)
    eta_si3l_65 = eta_si3l_25 * (1.0 + gamma_si * 40.0)
    eta_bot_65 = eta_bot_25 * (1.0 + gamma_bot * 40.0)
    eta_4t_65 = eta_top_65 + eta_si3l_65 + eta_bot_65

    beta_4t_rel = ((eta_4t_65 - eta_4t_25) / (40.0 * eta_4t_25)) * 100.0

    # Section 9.3.3: 25-Year Arrhenius Ion-Migration Reliability & Real-World LCOE
    kb_ev = K_B / Q_E
    t_field_k = 318.15
    r_deg = 0.0035 + 0.0010 * math.exp(-(limiting_neb_barrier_ev - 0.65) / (kb_ev * t_field_k))
    r_deg_pct = r_deg * 100.0
    year25_retained_pct = ((1.0 - r_deg) ** 25) * 100.0

    r_disc = 0.06
    c_bos_area = 100.0
    c_bos_power = 0.22
    c_om_yr = 2.50
    y0_kwh_kwp = 1800.0

    om_disc_25yr = sum(c_om_yr / ((1.0 + r_disc) ** t) for t in range(1, 26))

    # Standalone 22.0% c-Si baseline LCOE (0.45%/yr degradation, 45 C NOCT)
    eta_si_ref_25 = 22.00
    f_noct_si = 1.0 + gamma_si * 20.0
    r_deg_si = 0.0045
    p_m2_si = 10.0 * eta_si_ref_25
    capex_si = 40.00 + c_bos_area + c_bos_power * p_m2_si
    e_disc_si = sum(
        ((p_m2_si / 1000.0) * y0_kwh_kwp * f_noct_si * ((1.0 - r_deg_si) ** (t - 1)))
        / ((1.0 + r_disc) ** t)
        for t in range(1, 26)
    )
    lcoe_si_cents = 100.0 * (capex_si + om_disc_25yr) / e_disc_si

    # 2-Layer (Top + c-Si) LCOE
    c_mod_2l = 40.00 + float(raw_cost_top_usd_m2) + 6.50
    p_m2_2l = 10.0 * round(eta_2l_25, 2)
    f_noct_2l = eta_2l_45 / max(1.0e-9, eta_2l_25)
    capex_2l = c_mod_2l + c_bos_area + c_bos_power * p_m2_2l
    e_disc_2l = sum(
        ((p_m2_2l / 1000.0) * y0_kwh_kwp * f_noct_2l * ((1.0 - r_deg) ** (t - 1)))
        / ((1.0 + r_disc) ** t)
        for t in range(1, 26)
    )
    lcoe_2l_cents = 100.0 * (capex_2l + om_disc_25yr) / e_disc_2l

    # 3-Layer 4T (Top + c-Si + Bottom) LCOE
    c_mod_3l = 40.00 + float(raw_cost_top_usd_m2) + float(raw_cost_bot_usd_m2) + 13.00
    p_m2_3l = 10.0 * round(eta_4t_25, 2)
    f_noct_3l = eta_4t_45 / max(1.0e-9, eta_4t_25)
    capex_3l = c_mod_3l + c_bos_area + c_bos_power * p_m2_3l
    e_disc_3l = sum(
        ((p_m2_3l / 1000.0) * y0_kwh_kwp * f_noct_3l * ((1.0 - r_deg) ** (t - 1)))
        / ((1.0 + r_disc) ** t)
        for t in range(1, 26)
    )
    lcoe_3l_cents = 100.0 * (capex_3l + om_disc_25yr) / e_disc_3l

    lcoe_red_pct = ((lcoe_si_cents - lcoe_3l_cents) / lcoe_si_cents) * 100.0

    res: Dict[str, Any] = {
        "r_front_0deg_percent": round(r_front_by_angle[0], 2),
        "r_front_30deg_percent": round(r_front_by_angle[30], 2),
        "r_front_45deg_percent": round(r_front_by_angle[45], 2),
        "r_front_60deg_percent": round(r_front_by_angle[60], 2),
        "r_front_hemispheric_percent": round(r_hemi, 2),
        "pce_4t_0deg_25c_percent": round(pce_4t_by_angle[0], 2),
        "pce_4t_30deg_25c_percent": round(pce_4t_by_angle[30], 2),
        "pce_4t_45deg_25c_percent": round(pce_4t_by_angle[45], 2),
        "pce_4t_60deg_25c_percent": round(pce_4t_by_angle[60], 2),
        "iam_60deg_ratio": round(iam_60, 4),
        "pce_4t_noct_45c_percent": round(eta_4t_45, 2),
        "pce_4t_desert_65c_percent": round(eta_4t_65, 2),
        "temp_coeff_rel_pct_per_k": round(beta_4t_rel, 4),
        "limiting_neb_barrier_ev": round(float(limiting_neb_barrier_ev), 4),
        "annual_degradation_rate_pct_yr": round(r_deg_pct, 4),
        "year25_retained_power_fraction_percent": round(year25_retained_pct, 2),
        "lcoe_baseline_si_cents_kwh": round(lcoe_si_cents, 4),
        "lcoe_2layer_cents_kwh": round(lcoe_2l_cents, 4),
        "lcoe_3layer_4t_cents_kwh": round(lcoe_3l_cents, 4),
        "lcoe_3layer_vs_si_reduction_percent": round(lcoe_red_pct, 2),
    }

    sig_payload = {
        "r_front_0deg_percent": res["r_front_0deg_percent"],
        "r_front_60deg_percent": res["r_front_60deg_percent"],
        "pce_4t_0deg_25c_percent": res["pce_4t_0deg_25c_percent"],
        "pce_4t_60deg_25c_percent": res["pce_4t_60deg_25c_percent"],
        "pce_4t_noct_45c_percent": res["pce_4t_noct_45c_percent"],
        "lcoe_baseline_si_cents_kwh": res["lcoe_baseline_si_cents_kwh"],
        "lcoe_2layer_cents_kwh": res["lcoe_2layer_cents_kwh"],
        "lcoe_3layer_4t_cents_kwh": res["lcoe_3layer_4t_cents_kwh"],
        "lcoe_3layer_vs_si_reduction_percent": res["lcoe_3layer_vs_si_reduction_percent"],
    }
    res["sha256_signature"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return res


# =============================================================================
# 11B. Phase 10 Engineering Extensions (10A, 10B, 10C - v7.0)
# =============================================================================

_SIMP_E_EV: np.ndarray = ENERGY_GRID_EV
_SIMP_PHI_SUN_E: np.ndarray = SOLAR_PHOTON_FLUX_E


def independently_verify_phase10_bifacial_and_string_dossier(
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    thickness_nm_1: float,
    eg_ind_3: float,
    eg_dir_3: float,
    eps_inf_3: float,
    thickness_nm_3: float,
    raw_cost_top_usd_m2: float,
    raw_cost_bot_usd_m2: float,
    limiting_neb_barrier_ev: float,
) -> Dict[str, Any]:
    """Blinded independent verification of Phase 10A 2D thickness & ARC optimization,
    Phase 10B bifacial ground-albedo harvesting, and Phase 10C SPICE subcell J-V string matching.
    """
    wl_nm = LAMBDA_GRID_NM
    wl_um = wl_nm / 1000.0

    # Complex refractive indices of the 7 media (m = 0..6) on the energy grid
    n0 = np.ones_like(wl_nm, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um ** 2)).astype(np.complex128)

    n_ito_real = np.maximum(1.45, 1.92 - 0.085 * (wl_um ** 2))
    k_ito = 0.0018 + 0.0065 * (wl_um ** 3)
    n2 = n_ito_real + 1j * k_ito

    n_tio2_real = 2.380 + 0.0180 / (wl_um ** 2)
    k_tio2 = 0.0004 * (wl_um ** 2)
    n3 = n_tio2_real + 1j * k_tio2

    alpha1 = 1.2e5 * (np.maximum(0.0, _SIMP_E_EV - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, _SIMP_E_EV - eg_dir_1)
    )
    n_act_real = math.sqrt(eps_inf_1) + 0.035 / (wl_um ** 2)
    k_act = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n4 = n_act_real + 1j * k_act

    n_buf_real = 1.720 + 0.0040 / (wl_um ** 2)
    k_buf = 0.0012 * (wl_um ** 2)
    n5 = n_buf_real + 1j * k_buf

    n6 = np.full_like(wl_nm, 1.520, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5, n6]
    yab1 = 4.0 * eps_inf_1

    # Middle c-Si wafer and bottom IR properties
    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, _SIMP_E_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(
        np.maximum(0.0, _SIMP_E_EV - 3.40)
    )
    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    t_si_fca_low = np.exp(-0.08 * ((wl_nm / 1200.0) ** 2))

    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, _SIMP_E_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, _SIMP_E_EV - eg_dir_3)
    )

    d_mgf2_candidates = [88.0, 94.0]
    d_tio2_candidates = [42.0, 48.0]
    d_top_candidates = [float(thickness_nm_1), round(1.15 * float(thickness_nm_1), 1)]
    d_bot_candidates = [float(thickness_nm_3), round(1.15 * float(thickness_nm_3), 1)]

    best_eta_4t_0 = -1.0
    opt_tuple = (94.0, 48.0, float(thickness_nm_1), float(thickness_nm_3))
    opt_state: Dict[str, Any] = {}
    photon_conservation_holds = True

    for d_mgf2 in d_mgf2_candidates:
        for d_tio2 in d_tio2_candidates:
            for d_top in d_top_candidates:
                d_list_nm = [0.0, float(d_mgf2), 80.0, float(d_tio2), float(d_top), 82.0, 0.0]

                # Method B: Recursive Rouard / Airy backward amplitude addition from (5,6) down to (0,1)
                r_amp = (n5 - n6) / (n5 + n6)
                t_amp = (2.0 * n5) / (n5 + n6)

                for m in (4, 3, 2, 1, 0):
                    nm_curr = n_list[m]
                    nm_next = n_list[m + 1]
                    r_m = (nm_curr - nm_next) / (nm_curr + nm_next)
                    t_m = (2.0 * nm_curr) / (nm_curr + nm_next)
                    beta_next = (2.0 * math.pi * nm_next * d_list_nm[m + 1]) / wl_nm
                    phi_next = np.exp(1j * beta_next)
                    denom = 1.0 + r_m * r_amp * (phi_next ** 2)
                    r_amp = (r_m + r_amp * (phi_next ** 2)) / denom
                    t_amp = (t_m * t_amp * phi_next) / denom

                r_arc_1 = np.abs(r_amp) ** 2
                t_arc_1 = (np.real(n6) / np.real(n0)) * (np.abs(t_amp) ** 2)
                t_win_front = np.exp(-4.0 * math.pi * (k_ito * 80.0 + k_tio2 * float(d_tio2)) / wl_nm)

                d1_m = float(d_top) * 1.0e-9
                fabs1 = (yab1 * alpha1 * d1_m) / (1.0 + yab1 * alpha1 * d1_m)
                a_arc_1 = (1.0 - r_arc_1) * t_win_front * fabs1
                t_stack_1 = t_arc_1 * (1.0 - fabs1)

                if not bool(np.max(a_arc_1 + t_stack_1 + r_arc_1) <= 1.0 + 1e-9):
                    photon_conservation_holds = False

                cell_top = _solve_pv_cell_energy_quadrature(
                    absorptance_e=a_arc_1,
                    incident_photon_flux_e=_SIMP_PHI_SUN_E,
                    eg_ind_ev=eg_ind_1,
                    eg_dir_ev=eg_dir_1,
                )
                phi2_front = _SIMP_PHI_SUN_E * t_stack_1
                cell_si_0 = _solve_pv_cell_energy_quadrature(
                    absorptance_e=0.98 * fabs_si_3l,
                    incident_photon_flux_e=phi2_front,
                    eg_ind_ev=1.12,
                    eg_dir_ev=1.12,
                    j0_rad_fixed=1.2e-12,
                )
                phi3_front = phi2_front * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low

                for d_bot in d_bot_candidates:
                    d3_m = float(d_bot) * 1.0e-9
                    fabs3 = (yab3 * alpha3 * d3_m) / (1.0 + yab3 * alpha3 * d3_m)
                    a_arc_3 = (1.0 - r_int_23) * fabs3
                    cell_bot_0 = _solve_pv_cell_energy_quadrature(
                        absorptance_e=a_arc_3,
                        incident_photon_flux_e=phi3_front,
                        eg_ind_ev=eg_ind_3,
                        eg_dir_ev=eg_dir_3,
                    )

                    eta_4t_0 = cell_top["eff"] + cell_si_0["eff"] + cell_bot_0["eff"]
                    if eta_4t_0 > best_eta_4t_0:
                        best_eta_4t_0 = eta_4t_0
                        opt_tuple = (float(d_mgf2), float(d_tio2), float(d_top), float(d_bot))
                        opt_state = {
                            "r_arc_1": r_arc_1,
                            "a_arc_1": a_arc_1,
                            "t_stack_1": t_stack_1,
                            "phi2_front": phi2_front,
                            "phi3_front": phi3_front,
                            "fabs3_opt": fabs3,
                            "a_arc_3": a_arc_3,
                            "cell_top": cell_top,
                            "cell_si_0": cell_si_0,
                            "cell_bot_0": cell_bot_0,
                            "eta_4t_0": eta_4t_0,
                        }

    opt_mgf2, opt_tio2, opt_top, opt_bot = opt_tuple
    r_arc_1_opt = opt_state["r_arc_1"]
    phi2_front_opt = opt_state["phi2_front"]
    phi3_front_opt = opt_state["phi3_front"]
    fabs3_opt = opt_state["fabs3_opt"]
    a_arc_3_opt = opt_state["a_arc_3"]
    cell_top_opt = opt_state["cell_top"]
    cell_si_0_opt = opt_state["cell_si_0"]
    cell_bot_0_opt = opt_state["cell_bot_0"]
    eta_top_opt = cell_top_opt["eff"]
    eta_si_0 = cell_si_0_opt["eff"]
    eta_bot_0 = cell_bot_0_opt["eff"]
    eta_4t_0 = opt_state["eta_4t_0"]

    mask_above = (_SIMP_E_EV >= eg_ind_1) & (_SIMP_E_EV <= 3.50)
    flux_above = float(
        scipy.integrate.simpson(_SIMP_PHI_SUN_E[mask_above], x=_SIMP_E_EV[mask_above])
    )
    opt_r_front_pct = float(
        scipy.integrate.simpson(
            r_arc_1_opt[mask_above] * _SIMP_PHI_SUN_E[mask_above],
            x=_SIMP_E_EV[mask_above],
        )
        / max(1.0e-12, flux_above)
        * 100.0
    )

    # Section 10.2: Bifacial Ground-Albedo Harvesting (R_albedo = 0.20 and 0.30)
    bifacial_eta: Dict[float, float] = {}
    for r_alb in (0.20, 0.30):
        phi_rear = 0.78 * r_alb * _SIMP_PHI_SUN_E
        phi3_tot = phi3_front_opt + phi_rear
        cell_bot_bif = _solve_pv_cell_energy_quadrature(
            absorptance_e=a_arc_3_opt,
            incident_photon_flux_e=phi3_tot,
            eg_ind_ev=eg_ind_3,
            eg_dir_ev=eg_dir_3,
        )
        phi2_rear = phi_rear * (1.0 - fabs3_opt) * 0.92
        phi2_tot = phi2_front_opt + phi2_rear
        cell_si_bif = _solve_pv_cell_energy_quadrature(
            absorptance_e=0.98 * fabs_si_3l,
            incident_photon_flux_e=phi2_tot,
            eg_ind_ev=1.12,
            eg_dir_ev=1.12,
            j0_rad_fixed=1.2e-12,
        )
        bifacial_eta[r_alb] = eta_top_opt + cell_si_bif["eff"] + cell_bot_bif["eff"]

    eta_4t_20 = bifacial_eta[0.20]
    eta_4t_30 = bifacial_eta[0.30]

    # Section 9.3 Discounted 25-year LCOE at 20% Albedo
    p_m2 = 10.0 * round(eta_4t_20, 2)
    c_top_opt = float(raw_cost_top_usd_m2) * (opt_top / float(thickness_nm_1))
    c_bot_opt = float(raw_cost_bot_usd_m2) * (opt_bot / float(thickness_nm_3))
    c_mod_3l = 40.0 + c_top_opt + c_bot_opt + 13.0

    gamma_top = -0.00440 / (eg_ind_1 ** 0.65)
    gamma_si = -0.00440 / (1.12 ** 0.65)
    gamma_bot = -0.00440 / (eg_ind_3 ** 0.65)
    f_noct_3l = (
        eta_top_opt * (1.0 + gamma_top * 20.0)
        + eta_si_0 * (1.0 + gamma_si * 20.0)
        + eta_bot_0 * (1.0 + gamma_bot * 20.0)
    ) / eta_4t_0

    kb_ev = K_B / Q_E
    t_field_k = 318.15
    r_deg = 0.0035 + 0.0010 * math.exp(-(limiting_neb_barrier_ev - 0.65) / (kb_ev * t_field_k))

    r_disc = 0.06
    c_bos_area = 100.0
    c_bos_power = 0.22
    c_om_yr = 2.50
    y0_kwh_kwp = 1800.0

    om_disc_25yr = sum(c_om_yr / ((1.0 + r_disc) ** t) for t in range(1, 26))
    capex_3l = c_mod_3l + c_bos_area + c_bos_power * p_m2
    e_disc_3l = sum(
        ((p_m2 / 1000.0) * y0_kwh_kwp * f_noct_3l * ((1.0 - r_deg) ** (t - 1)))
        / ((1.0 + r_disc) ** t)
        for t in range(1, 26)
    )
    bifacial_20pct_lcoe_cents_kwh = round(100.0 * (capex_3l + om_disc_25yr) / e_disc_3l, 4)

    # Section 10.3: Subcell J-V Operating Point & Integer Parallel-String Voltage Matching
    top_vmp_raw = cell_top_opt["voc"] - V_TH * math.log((cell_top_opt["voc"] / V_TH) + 0.72)
    si_vmp_raw = cell_si_0_opt["voc"] - V_TH * math.log((cell_si_0_opt["voc"] / V_TH) + 0.72)
    bot_vmp_raw = cell_bot_0_opt["voc"] - V_TH * math.log((cell_bot_0_opt["voc"] / V_TH) + 0.72)

    n_cells_si_ref = 72
    v_bus_si = 72.0 * si_vmp_raw
    n_cells_top_matched = int(round(v_bus_si / top_vmp_raw))
    n_cells_bot_matched = int(round(v_bus_si / bot_vmp_raw))

    top_string_mismatch_percent = round(
        abs(n_cells_top_matched * top_vmp_raw - v_bus_si) / v_bus_si * 100.0, 2
    )
    bot_string_mismatch_percent = round(
        abs(n_cells_bot_matched * bot_vmp_raw - v_bus_si) / v_bus_si * 100.0, 2
    )

    res: Dict[str, Any] = {
        "opt_mgf2_nm": round(opt_mgf2, 1),
        "opt_tio2_nm": round(opt_tio2, 1),
        "opt_top_nm": round(opt_top, 1),
        "opt_bot_nm": round(opt_bot, 1),
        "opt_r_front_percent": round(opt_r_front_pct, 2),
        "opt_monofacial_4t_pce_percent": round(eta_4t_0, 2),
        "bifacial_20pct_albedo_4t_pce_percent": round(eta_4t_20, 2),
        "bifacial_20pct_power_w_sqft": round(10.0 * eta_4t_20 * 0.09290304, 2),
        "bifacial_30pct_albedo_4t_pce_percent": round(eta_4t_30, 2),
        "bifacial_30pct_power_w_sqft": round(10.0 * eta_4t_30 * 0.09290304, 2),
        "bifacial_20pct_gain_percent": round(((eta_4t_20 - eta_4t_0) / eta_4t_0) * 100.0, 2),
        "bifacial_20pct_lcoe_cents_kwh": bifacial_20pct_lcoe_cents_kwh,
        "top_jsc_ma_cm2": round(cell_top_opt["jsc"], 2),
        "top_voc_v": round(cell_top_opt["voc"], 4),
        "top_ff": round(cell_top_opt["ff"], 4),
        "top_vmp_v": round(top_vmp_raw, 4),
        "si_jsc_ma_cm2": round(cell_si_0_opt["jsc"], 2),
        "si_voc_v": round(cell_si_0_opt["voc"], 4),
        "si_ff": round(cell_si_0_opt["ff"], 4),
        "si_vmp_v": round(si_vmp_raw, 4),
        "bot_jsc_ma_cm2": round(cell_bot_0_opt["jsc"], 2),
        "bot_voc_v": round(cell_bot_0_opt["voc"], 4),
        "bot_ff": round(cell_bot_0_opt["ff"], 4),
        "bot_vmp_v": round(bot_vmp_raw, 4),
        "n_cells_si_ref": n_cells_si_ref,
        "n_cells_top_matched": n_cells_top_matched,
        "n_cells_bot_matched": n_cells_bot_matched,
        "v_bus_si_v": round(v_bus_si, 2),
        "top_string_mismatch_percent": top_string_mismatch_percent,
        "bot_string_mismatch_percent": bot_string_mismatch_percent,
        "photon_conservation_holds": photon_conservation_holds,
    }

    sig_payload = {k: v for k, v in res.items() if k != "sha256_signature"}
    res["sha256_signature"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return res


# =============================================================================
# 12. Top-Level Entrypoint: Candidate Dossier Zero-Trust Verifier
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
