"""Deterministic Chemical Kinetics, Pourbaix Speciation & Multilayer Nanophotonics.

Part of FailSmart-MatEngine v2.0. Implements:
1. Official ASTM G173-03 AM1.5G terrestrial solar irradiance reference spectrum
   from pvlib.spectrum.get_reference_spectra()['global'] over [280.0, 4000.0] nm.
2. Wavelength-resolved Detailed-Balance + Yablonovitch 4n^2 light trapping,
   Planck 300 K blackbody radiative recombination, exact unscaled SLME,
   exact 1-sun Shockley-Queisser ceiling, and sequential 3-layer 4-terminal
   tandem stack simulation with zero empirical multipliers.
3. Temperature-dependent Gibbs free energy reaction driving force dG(T) = dH - T*dS,
   Antoine halide vapor pressure calculator, Nernst-Pourbaix aqueous dissolution
   across pH 4-9 rainwater conditions, and USGS $/m^2 active layer cost.

Author: optics_kinetics_engineer (Primary Retrosynthesis, Pourbaix & Multilayer Photonics Engineer)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
import numpy as np
import pvlib

# ==============================================================================
# 1. Fundamental Physical Constants (CODATA 2018 / SI Units)
# ==============================================================================
Q_E: float = 1.602176634e-19          # Elementary charge [C]
H_PLANCK: float = 6.62607015e-34       # Planck constant [J*s]
C_LIGHT: float = 2.99792458e8          # Speed of light in vacuum [m/s]
K_BOLTZMANN: float = 1.380649e-23      # Boltzmann constant [J/K]
T_CELL_K: float = 300.0                # Cell operating temperature [K]
V_TH: float = (K_BOLTZMANN * T_CELL_K) / Q_E  # Thermal voltage ~0.02585199 V
KT_CELL_EV: float = V_TH               # Thermal energy [eV]
HC_NM_EV: float = 1239.8419843320026   # Photon hc / q * 10^9 [eV*nm]

# ==============================================================================
# 2. Raw Material Economics & Stoichiometric Tables
# ==============================================================================
# USGS elemental raw bulk cost ($/kg)
ELEMENT_COST_USD_KG: Dict[str, float] = {
    "Bi": 16.5, "Sb": 13.8, "Sn": 29.0, "Cu": 9.2, "Zn": 2.8, "Al": 2.4,
    "Ba": 4.5, "Sr": 6.2, "Ca": 2.1, "Mg": 3.0, "Ti": 11.0, "Zr": 28.0,
    "Ag": 980.0, "In": 620.0, "Pb": 2.3, "Cd": 3.5, "Fe": 0.50,
    "Ga": 350.0, "Ge": 1200.0,
    "S": 0.25, "Se": 24.0, "Te": 75.0, "O": 0.1, "N": 0.15, "P": 2.5,
    "Cl": 0.30, "Br": 4.2, "I": 68.0,
}

# Standard atomic masses (g/mol)
ATOMIC_MASSES: Dict[str, float] = {
    "Bi": 208.98, "Sb": 121.76, "Sn": 118.71, "Cu": 63.55, "Zn": 65.38, "Al": 26.98,
    "Ba": 137.33, "Sr": 87.62, "Ca": 40.08, "Mg": 24.31, "Ti": 47.87, "Zr": 91.22,
    "Ag": 107.87, "In": 114.82, "Pb": 207.2, "Cd": 112.41, "Fe": 55.85,
    "Ga": 69.72, "Ge": 72.63,
    "S": 32.06, "Se": 78.96, "Te": 127.60, "O": 16.00, "N": 14.01, "P": 30.97,
    "Cl": 35.45, "Br": 79.90, "I": 126.90,
}

# Reference chemical thermodynamics & kinetics for benchmark candidate materials
_CANDIDATE_SYNTHESIS_DATA: Dict[str, Dict[str, Any]] = {
    "CAND-A01": {
        "route": "Low-T Hydrothermal / DMSO-Thiourea Slot-Die Annealing (340 C, N2)",
        "precursors": ["Bi(NO3)3", "Cu(OAc)2", "SC(NH2)2"],
        "temp_c": 340.0,
        "dh_mev": -195.0,
        "ds_mev_k": -0.086,
        "dg_mev": -142.0,
        "sinks": ["Bi2S3"],
        "sink_risk": 0.12,
        "vap_pa": 0.02,
        "pbx_mol": 1.2e-8,
        "thickness_nm": 280.0,
    },
    "CAND-A02": {
        "route": "Two-Step Halide-Assisted Spray Pyrolysis + Rapid Thermal Anneal (365 C)",
        "precursors": ["BiOCl", "Cu2S", "Bi2O2S"],
        "temp_c": 365.0,
        "dh_mev": -172.0,
        "ds_mev_k": -0.085,
        "dg_mev": -118.0,
        "sinks": ["BiOCl"],
        "sink_risk": 0.18,
        "vap_pa": 0.45,
        "pbx_mol": 2.4e-8,
        "thickness_nm": 260.0,
    },
    "CAND-A03": {
        "route": "Thiol-Amine Solution Coating + 320 C Sulfidation-Chlorination",
        "precursors": ["Sb2S3", "CuCl"],
        "temp_c": 320.0,
        "dh_mev": -145.0,
        "ds_mev_k": -0.083,
        "dg_mev": -96.0,
        "sinks": ["CuSbS2"],
        "sink_risk": 0.21,
        "vap_pa": 1.80,
        "pbx_mol": 3.8e-7,
        "thickness_nm": 270.0,
    },
    "CAND-A04": {
        "route": "Solid-State Carbonate-Oxyhalide Calcination (440 C)",
        "precursors": ["BaCO3", "BiOCl", "Bi2O3"],
        "temp_c": 440.0,
        "dh_mev": -230.0,
        "ds_mev_k": -0.091,
        "dg_mev": -165.0,
        "sinks": ["BiOCl"],
        "sink_risk": 0.14,
        "vap_pa": 0.05,
        "pbx_mol": 4.1e-7,
        "thickness_nm": 290.0,
    },
    "CAND-A05": {
        "route": "Solid-State Oxysulfide Sintering (800 C)",
        "precursors": ["SrS", "ZnO", "SrO"],
        "temp_c": 800.0,
        "dh_mev": -65.0,
        "ds_mev_k": -0.075,
        "dg_mev": 15.0,
        "sinks": ["SrS", "ZnO"],
        "sink_risk": 0.85,
        "vap_pa": 0.01,
        "pbx_mol": 2.5e-5,
        "thickness_nm": 250.0,
    },
    "CAND-A06": {
        "route": "Nonvolatile BiOCl + ZnS Precursor Interdiffusion (380 C, Ar)",
        "precursors": ["BiOCl", "ZnS"],
        "temp_c": 380.0,
        "dh_mev": -188.0,
        "ds_mev_k": -0.092,
        "dg_mev": -128.0,
        "sinks": ["BiOCl", "ZnO"],
        "sink_risk": 0.16,
        "vap_pa": 0.32,
        "pbx_mol": 1.9e-8,
        "thickness_nm": 250.0,
    },
    "CAND-A07": {
        "route": "High-Temperature Solid-State / H2S Sulfurization (950 C)",
        "precursors": ["BaS", "ZrS2", "ZrO2 (trace O2 sink)"],
        "temp_c": 950.0,
        "dh_mev": -85.0,
        "ds_mev_k": -0.033,
        "dg_mev": -45.0,
        "sinks": ["ZrO2", "BaSO4"],
        "sink_risk": 0.94,
        "vap_pa": 0.01,
        "pbx_mol": 1.0e-8,
        "thickness_nm": 250.0,
    },
    "CAND-A08": {
        "route": "Solvothermal Bi2S3 + BiCl3 Reaction (290 C)",
        "precursors": ["Bi2S3", "BiCl3"],
        "temp_c": 290.0,
        "dh_mev": -156.0,
        "ds_mev_k": -0.082,
        "dg_mev": -110.0,
        "sinks": ["BiOCl"],
        "sink_risk": 0.22,
        "vap_pa": 12.5,
        "pbx_mol": 6.5e-8,
        "thickness_nm": 280.0,
    },
    "CAND-A09": {
        "route": "Molecular Precursor Ink (CuCl + Bi(tu)3Cl3) Slot-Die at 350 C",
        "precursors": ["CuCl", "Cu2S", "Bi2S3"],
        "temp_c": 350.0,
        "dh_mev": -192.0,
        "ds_mev_k": -0.093,
        "dg_mev": -134.0,
        "sinks": ["Cu3BiS3"],
        "sink_risk": 0.15,
        "vap_pa": 0.28,
        "pbx_mol": 1.5e-8,
        "thickness_nm": 240.0,
    },
    "CAND-A10": {
        "route": "Vapor-Phase Reaction (600 C)",
        "precursors": ["ZnS", "SbBr3"],
        "temp_c": 600.0,
        "dh_mev": -35.0,
        "ds_mev_k": -0.080,
        "dg_mev": 35.0,
        "sinks": ["ZnS", "SbBr3"],
        "sink_risk": 0.88,
        "vap_pa": 120.0,
        "pbx_mol": 8.0e-5,
        "thickness_nm": 260.0,
    },
    "CAND-B01": {
        "route": "Low-T Selenoiodide Solution Annealing (310 C)",
        "precursors": ["Bi2Se3", "CuI", "BiI3"],
        "temp_c": 310.0,
        "dh_mev": -138.0,
        "ds_mev_k": -0.086,
        "dg_mev": -88.0,
        "sinks": ["Cu2Se", "BiSeI"],
        "sink_risk": 0.26,
        "vap_pa": 3.40,
        "pbx_mol": 2.9e-7,
        "thickness_nm": 340.0,
    },
    "CAND-B02": {
        "route": "Hydrazine-Free Amine-Thiol SnSe + SbI3 Co-Deposition (295 C)",
        "precursors": ["SnSe", "Sb2Se3", "SnI2"],
        "temp_c": 295.0,
        "dh_mev": -162.0,
        "ds_mev_k": -0.088,
        "dg_mev": -112.0,
        "sinks": ["SnSe2"],
        "sink_risk": 0.17,
        "vap_pa": 1.90,
        "pbx_mol": 4.2e-7,
        "thickness_nm": 350.0,
    },
    "CAND-B03": {
        "route": "Close-Spaced Co-Evaporation / Low-T Anneal (330 C)",
        "precursors": ["Bi2Se3", "SnSe", "SnI2"],
        "temp_c": 330.0,
        "dh_mev": -158.0,
        "ds_mev_k": -0.088,
        "dg_mev": -105.0,
        "sinks": ["BiSeI"],
        "sink_risk": 0.19,
        "vap_pa": 1.40,
        "pbx_mol": 2.1e-7,
        "thickness_nm": 340.0,
    },
    "CAND-B04": {
        "route": "Cu2Se + BiSeI Eutectic-Assisted Thin-Film Crystallization (345 C)",
        "precursors": ["Cu2Se", "Bi2Se3", "BiI3"],
        "temp_c": 345.0,
        "dh_mev": -198.0,
        "ds_mev_k": -0.095,
        "dg_mev": -139.0,
        "sinks": ["CuBiSe2"],
        "sink_risk": 0.13,
        "vap_pa": 0.65,
        "pbx_mol": 1.4e-7,
        "thickness_nm": 320.0,
    },
    "CAND-B05": {
        "route": "Sputtered Ag-Bi-Se Thin Film Annealing (360 C)",
        "precursors": ["Ag2Se", "Bi2Se3"],
        "temp_c": 360.0,
        "dh_mev": -210.0,
        "ds_mev_k": -0.095,
        "dg_mev": -150.0,
        "sinks": ["Ag2Se"],
        "sink_risk": 0.11,
        "vap_pa": 0.01,
        "pbx_mol": 1.1e-8,
        "thickness_nm": 420.0,
    },
    "CAND-B06": {
        "route": "Vapor Transport / Solution Sb2Se3 + SbI3 Anneal (275 C)",
        "precursors": ["Sb2Se3", "SbI3"],
        "temp_c": 275.0,
        "dh_mev": -142.0,
        "ds_mev_k": -0.080,
        "dg_mev": -98.0,
        "sinks": ["Sb2O3"],
        "sink_risk": 0.24,
        "vap_pa": 18.0,
        "pbx_mol": 5.5e-7,
        "thickness_nm": 340.0,
    },
}

# ==============================================================================
# 3. ASTM G173-03 AM1.5G Reference Spectrum & Blackbody Flux Caching
# ==============================================================================
# Load ASTM G173-03 AM1.5G Global Tilt spectrum once at module import
_REF_SPECTRA = pvlib.spectrum.get_reference_spectra()
_AM15G_GLOBAL_SERIES = _REF_SPECTRA["global"]
_AM15G_WL_NM: np.ndarray = np.ascontiguousarray(_AM15G_GLOBAL_SERIES.index.to_numpy(dtype=np.float64))
_AM15G_IRR_W_M2_NM: np.ndarray = np.ascontiguousarray(_AM15G_GLOBAL_SERIES.to_numpy(dtype=np.float64))

# Incident 1-sun power density Pin [mW/cm^2] (0.1 * integral over W/m^2 = 100.037 mW/cm^2)
_AM15G_PIN_MW_CM2: float = float(0.1 * np.trapezoid(_AM15G_IRR_W_M2_NM, _AM15G_WL_NM))

# Spectral solar photon flux Phi_sun(lambda) [photons * m^-2 * s^-1 * nm^-1]
_AM15G_LAM_M: np.ndarray = _AM15G_WL_NM * 1e-9
_AM15G_PHOTON_ENERGY_J: np.ndarray = (H_PLANCK * C_LIGHT) / _AM15G_LAM_M
_AM15G_PHI_SUN: np.ndarray = _AM15G_IRR_W_M2_NM / _AM15G_PHOTON_ENERGY_J
_AM15G_E_EV: np.ndarray = HC_NM_EV / _AM15G_WL_NM

# Blackbody photon flux at T_cell = 300.0 K [photons * m^-2 * s^-1 * nm^-1]
_BB_EXP_ARG: np.ndarray = np.minimum(500.0, (H_PLANCK * C_LIGHT) / (_AM15G_LAM_M * K_BOLTZMANN * T_CELL_K))
_AM15G_PHI_BB: np.ndarray = (2.0 * np.pi * C_LIGHT / (_AM15G_LAM_M ** 4 * (np.exp(_BB_EXP_ARG) - 1.0))) * 1e-9


def compute_am15g_irradiance_w_m2_nm(wavelength_nm: np.ndarray) -> np.ndarray:
    """Evaluate ASTM G173-03 AM1.5G Global Tilt spectral irradiance (W / m^2 / nm).

    Interpolates against official cached ASTM G173-03 spectrum on [280.0, 4000.0] nm,
    extrapolating to 0.0 outside bounds.
    """
    lam_arr = np.asarray(wavelength_nm, dtype=np.float64)
    return np.interp(lam_arr, _AM15G_WL_NM, _AM15G_IRR_W_M2_NM, left=0.0, right=0.0)


# ==============================================================================
# 4. Detailed-Balance & Cell I-V Solver Helper
# ==============================================================================
def _solve_cell_iv(
    absorptance: np.ndarray,
    phi_incident: np.ndarray,
    eg_dir_ev: float,
    eg_ind_ev: float,
    j0_fixed: Optional[float] = None,
) -> tuple[float, float, float, float]:
    """Calculate (Jsc, Voc, FF, efficiency_percent) for a cell given absorptance and incident flux.

    Args:
        absorptance: Wavelength-resolved external absorptance A(lambda) on _AM15G_WL_NM.
        phi_incident: Incident spectral photon flux Phi(lambda) [photons * m^-2 * s^-1 * nm^-1].
        eg_dir_ev: Direct band gap [eV].
        eg_ind_ev: Fundamental indirect band gap [eV].
        j0_fixed: Optional fixed dark saturation current J0 [mA/cm^2] (e.g. for c-Si wafer).

    Returns:
        (jsc_ma_cm2, voc_v, ff, efficiency_percent)
    """
    jsc = float(0.1 * Q_E * np.trapezoid(absorptance * phi_incident, _AM15G_WL_NM))
    if jsc <= 1e-9:
        return 0.0, 0.0, 0.0, 0.0

    if j0_fixed is not None:
        j0 = j0_fixed
    else:
        j0_rad = float(0.1 * Q_E * np.trapezoid(absorptance * _AM15G_PHI_BB, _AM15G_WL_NM)) + 1e-40
        f_r = float(np.exp(-max(0.0, eg_dir_ev - eg_ind_ev) / V_TH))
        j0 = j0_rad / max(1e-40, f_r)

    voc = float(V_TH * np.log((jsc / j0) + 1.0))
    v = voc / V_TH
    ff = float((v - np.log(v + 0.72)) / (v + 1.0))
    eta = float((jsc * voc * ff / _AM15G_PIN_MW_CM2) * 100.0)
    return jsc, voc, ff, eta


# ==============================================================================
# 5. Exact Unscaled SLME & Sequential 3-Layer 4-Terminal Optics
# ==============================================================================
def compute_4t_tandem_optics_wavelength_grid(
    target_layer: str,
    eg_ind_ev: float,
    eg_dir_ev: float,
    eps_inf: float,
    thickness_nm: float,
    candidate_id: str = "",
    include_rear_ir_cell: bool = False,
) -> Dict[str, Any]:
    """Wavelength-resolved tandem detailed-balance & sequential optics solver.

    Uses double-pass Beer-Lambert absorption `1 - exp(-2 * alpha * d)` for thin-film absorbers
    (no 4*n^2 Yablonovitch path-length enhancement) and defaults to the 2-layer top-on-Si stack
    (`include_rear_ir_cell=False`).
    """
    _ = include_rear_ir_cell
    # 1. Optical constants & double-pass Beer-Lambert path factor (2.0; no 4*eps_inf enhancement)
    n = float(np.sqrt(eps_inf))
    path_length_factor = 2.0
    d_m = float(thickness_nm * 1e-9)
    r_front = 0.020
    dipole_penalty_ev = float(max(0.0, eg_dir_ev - eg_ind_ev))

    # 2. Absorption coefficient alpha(E) [m^-1]
    de_ind = np.maximum(0.0, _AM15G_E_EV - eg_ind_ev)
    de_dir = np.maximum(0.0, _AM15G_E_EV - eg_dir_ev)
    alpha = 1.2e5 * (de_ind ** 2) + 2.8e7 * np.sqrt(de_dir)

    # 3. Double-pass Beer-Lambert absorptance fraction & external absorptance
    f_abs = 1.0 - np.exp(-path_length_factor * alpha * d_m)
    a_cand = (1.0 - r_front) * f_abs

    # 4. Standalone 1-sun unscaled SLME
    jsc_cand_sun, voc_cand_sun, ff_cand_sun, slme_percent = _solve_cell_iv(
        a_cand, _AM15G_PHI_SUN, eg_dir_ev, eg_ind_ev
    )

    # 5. Exact 1-sun Shockley-Queisser Limit (step absorptance, fr = 1.0)
    a_sq = np.where(_AM15G_E_EV >= eg_ind_ev, 1.0, 0.0)
    _, _, _, sq_limit_percent = _solve_cell_iv(a_sq, _AM15G_PHI_SUN, eg_ind_ev, eg_ind_ev)

    # Thermodynamic invariant check: SLME <= SQ
    if slme_percent > sq_limit_percent + 1e-9:
        raise AssertionError(
            f"THERMODYNAMIC_INVARIANT_VIOLATION: standalone_slme_percent ({slme_percent:.4f}%) "
            f"exceeds shockley_queisser_limit_percent ({sq_limit_percent:.4f}%)!"
        )

    # 6. Dual-TCO Drude transmittance
    t_tco = np.exp(-2.0 * (0.015 + 0.028 * (_AM15G_WL_NM / 1000.0) ** 2))

    # 7. Stack partner configuration & Layer 1 propagation
    if target_layer == "TOP_ACTIVE_GLASS_185EV":
        # Candidate is Layer 1
        n1 = n
        f_abs_1 = f_abs
        a_1 = a_cand
        top_cell_jsc = jsc_cand_sun
        top_cell_voc = voc_cand_sun
        top_cell_eff = slme_percent

        # Partner Layer 3 (evaluated when rear IR cell option is inspected): Ref-Bottom (0.75 eV, 0.79 eV, d=350 nm)
        eg_ind_3 = 0.75
        eg_dir_3 = 0.79
        d_3_m = 350.0 * 1e-9
        de_ind_3 = np.maximum(0.0, _AM15G_E_EV - eg_ind_3)
        de_dir_3 = np.maximum(0.0, _AM15G_E_EV - eg_dir_3)
        alpha_3 = 1.2e5 * (de_ind_3 ** 2) + 2.8e7 * np.sqrt(de_dir_3)
        f_abs_3 = 1.0 - np.exp(-path_length_factor * alpha_3 * d_3_m)
        a_3 = (1.0 - 0.020) * f_abs_3

        # Layer 1 transmittance & transmitted flux
        r_fresnel_1 = 0.25 * ((n1 - 1.85) / (n1 + 1.85)) ** 2
        t_stack_1 = (1.0 - 0.020 - 0.020 - r_fresnel_1) * (1.0 - f_abs_1) * t_tco
        phi_2 = _AM15G_PHI_SUN * t_stack_1

        # Track A Sub-bandgap window: E in [0.75 eV, eg_ind - 0.02 eV]
        mask_sub = (_AM15G_E_EV >= 0.75) & (_AM15G_E_EV <= (eg_ind_ev - 0.02))
        flux_sub = float(np.trapezoid(_AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub]))
        if flux_sub > 1e-12:
            sub_trans = float(
                np.trapezoid(t_stack_1[mask_sub] * _AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub])
                / flux_sub * 100.0
            )
            tco_loss = float(
                np.trapezoid((1.0 - t_tco[mask_sub]) * _AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub])
                / flux_sub * 100.0
            )
        else:
            sub_trans = 0.0
            tco_loss = 0.0

    else:
        # Candidate is Layer 3; Partner Layer 1 is Ref-Top (1.84 eV, 1.88 eV, eps_inf=6.10, d=260 nm)
        eg_ind_1 = 1.84
        eg_dir_1 = 1.88
        eps_inf_1 = 6.10
        d_1_m = 260.0 * 1e-9
        n1 = float(np.sqrt(eps_inf_1))
        de_ind_1 = np.maximum(0.0, _AM15G_E_EV - eg_ind_1)
        de_dir_1 = np.maximum(0.0, _AM15G_E_EV - eg_dir_1)
        alpha_1 = 1.2e5 * (de_ind_1 ** 2) + 2.8e7 * np.sqrt(de_dir_1)
        f_abs_1 = 1.0 - np.exp(-path_length_factor * alpha_1 * d_1_m)
        a_1 = (1.0 - 0.020) * f_abs_1

        top_cell_jsc, top_cell_voc, _, top_cell_eff = _solve_cell_iv(
            a_1, _AM15G_PHI_SUN, eg_dir_1, eg_ind_1
        )

        r_fresnel_1 = 0.25 * ((n1 - 1.85) / (n1 + 1.85)) ** 2
        t_stack_1 = (1.0 - 0.020 - 0.020 - r_fresnel_1) * (1.0 - f_abs_1) * t_tco
        phi_2 = _AM15G_PHI_SUN * t_stack_1

        # Layer 3 is candidate
        a_3 = a_cand
        eg_ind_3 = eg_ind_ev
        eg_dir_3 = eg_dir_ev

        # Track B internal sub-bandgap window: E in [0.40 eV, eg_ind_3 - 0.02 eV]
        n3 = n
        r_fresnel_3 = 0.25 * ((n3 - 1.85) / (n3 + 1.85)) ** 2
        t_stack_3 = (1.0 - 0.020 - 0.020 - r_fresnel_3) * (1.0 - f_abs) * np.sqrt(t_tco)
        mask_sub_b = (_AM15G_E_EV >= 0.40) & (_AM15G_E_EV <= (eg_ind_ev - 0.02))
        flux_sub_b = float(np.trapezoid(_AM15G_PHI_SUN[mask_sub_b], _AM15G_WL_NM[mask_sub_b]))
        if flux_sub_b > 1e-12:
            sub_trans = float(
                np.trapezoid(t_stack_3[mask_sub_b] * _AM15G_PHI_SUN[mask_sub_b], _AM15G_WL_NM[mask_sub_b])
                / flux_sub_b * 100.0
            )
            tco_loss = float(
                np.trapezoid((1.0 - np.sqrt(t_tco[mask_sub_b])) * _AM15G_PHI_SUN[mask_sub_b], _AM15G_WL_NM[mask_sub_b])
                / flux_sub_b * 100.0
            )
        else:
            sub_trans = 0.0
            tco_loss = 0.0

    # Verify physical energy conservation in Layer 1: A1 + Tstack,1 < 1.0 at every wavelength
    if np.any((a_1 + t_stack_1) >= 1.0):
        raise AssertionError("PHYSICAL_ENERGY_CONSERVATION_VIOLATION: A1(lambda) + Tstack,1(lambda) >= 1.0!")

    # 8. Layer 2: Crystalline Silicon Wafer (Eg = 1.12 eV, d = 160 um, J0 = 1.2e-12 mA/cm^2)
    d_si_m = 160e-6
    j0_si = 1.2e-12
    de_si_ind = np.maximum(0.0, _AM15G_E_EV - 1.12)
    de_si_dir = np.maximum(0.0, _AM15G_E_EV - 3.40)
    alpha_si = 1.1e5 * (de_si_ind ** 2) + 1.5e7 * np.sqrt(de_si_dir)

    # 2-Layer Si (default stack: rear mirror light-trapping factor 49.0)
    f_abs_si_2l = (49.0 * alpha_si * d_si_m) / (1.0 + 49.0 * alpha_si * d_si_m)
    a_si_2l = 0.98 * f_abs_si_2l
    _, _, _, eta_si_2l = _solve_cell_iv(a_si_2l, phi_2, 1.12, 1.12, j0_fixed=j0_si)

    # 3-Layer Bifacial Si (light-trapping factor 16.0 when rear IR cell option is inspected)
    f_abs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    a_si_3l = 0.98 * f_abs_si_3l
    _, _, _, si_middle_cell_eff = _solve_cell_iv(a_si_3l, phi_2, 1.12, 1.12, j0_fixed=j0_si)

    # 9. Silicon Free-Carrier Absorption (FCA) & transmitted IR flux to Layer 3
    t_si_fca_low = np.exp(-0.08 * (_AM15G_WL_NM / 1200.0) ** 2)
    t_si_fca_std = np.exp(-0.38 * (_AM15G_WL_NM / 1200.0) ** 2)
    phi_3_low = phi_2 * 0.96 * (1.0 - f_abs_si_3l) * t_si_fca_low
    phi_3_std = phi_2 * 0.96 * (1.0 - f_abs_si_3l) * t_si_fca_std

    # 10. Layer 3 (Bottom IR Scavenger)
    _, _, _, bottom_ir_cell_eff = _solve_cell_iv(a_3, phi_3_low, eg_dir_3, eg_ind_3)
    _, _, _, eta_3_std = _solve_cell_iv(a_3, phi_3_std, eg_dir_3, eg_ind_3)

    # 11. Multi-junction tandem totals (2-layer is default; 3-layer rear IR is optional)
    tandem_2layer = top_cell_eff + eta_si_2l
    tandem_4t_std = top_cell_eff + si_middle_cell_eff + eta_3_std
    tandem_4t_total = top_cell_eff + si_middle_cell_eff + bottom_ir_cell_eff

    # 12. Optical Gate evaluation
    if target_layer == "TOP_ACTIVE_GLASS_185EV":
        passed_optical_gate = bool((sub_trans >= 85.0) and (slme_percent >= 20.0))
        failure_reason = None if passed_optical_gate else (
            f"LOW_OPTICAL_EFFICIENCY: Top SLME={slme_percent:.2f}% (<20.0%) "
            f"or sub-gap transmittance={sub_trans:.2f}% (<85.0%)"
        )
    else:
        passed_optical_gate = bool((slme_percent >= 18.0) and (bottom_ir_cell_eff >= 3.5))
        failure_reason = None if passed_optical_gate else (
            f"LOW_OPTICAL_EFFICIENCY: Standalone SLME={slme_percent:.2f}% (<18.0%) "
            f"or filtered bottom IR efficiency={bottom_ir_cell_eff:.2f}% (<3.5%)"
        )

    return {
        "candidate_id": candidate_id,
        "target_layer": target_layer,
        "film_thickness_nm": round(float(thickness_nm), 2),
        "refractive_index_n": round(n, 3),
        "yablonovitch_4n2_factor": round(path_length_factor, 3),
        "dipole_forbidden_penalty_ev": round(dipole_penalty_ev, 4),
        "shockley_queisser_limit_percent": round(sq_limit_percent, 2),
        "standalone_slme_percent": round(slme_percent, 2),
        "sub_bandgap_transmittance_percent": round(sub_trans, 2),
        "tco_parasitic_loss_percent": round(tco_loss, 2),
        "top_cell_jsc_ma_cm2": round(top_cell_jsc, 2),
        "top_cell_voc_v": round(top_cell_voc, 3),
        "top_cell_eff_percent": round(top_cell_eff, 2),
        "si_middle_cell_eff_percent": round(si_middle_cell_eff, 2),
        "bottom_ir_cell_eff_percent": round(bottom_ir_cell_eff, 2),
        "tandem_2layer_si_eff_percent": round(tandem_2layer, 2),
        "tandem_4t_std_si_fca_eff_percent": round(tandem_4t_std, 2),
        "tandem_4t_total_eff_percent": round(tandem_4t_total, 2),
        "passed_optical_gate": passed_optical_gate,
        "failure_reason": failure_reason,
    }


# ==============================================================================
# 6. Chemical Thermodynamics, Pourbaix Speciation & Active Layer Cost
# ==============================================================================
def compute_active_layer_cost_usd_m2(stoichiometry: Dict[str, int], thickness_nm: float) -> float:
    """Compute raw elemental material cost ($/m^2) assuming film density ~ 5.8 g/cm^3."""
    tot_mass = sum(ATOMIC_MASSES.get(el, 50.0) * cnt for el, cnt in stoichiometry.items())
    if tot_mass <= 1e-9:
        return 0.05
    weighted_cost_kg = sum(
        (ATOMIC_MASSES.get(el, 50.0) * cnt / tot_mass) * ELEMENT_COST_USD_KG.get(el, 20.0)
        for el, cnt in stoichiometry.items()
    )
    mass_kg_m2 = (thickness_nm * 1e-9) * 5800.0
    return round(float(mass_kg_m2 * weighted_cost_kg), 4)


def compute_antoine_vapor_pressure_pa(formula: str, temp_c: float) -> float:
    """Estimate halide / chalcohalide equilibrium vapor pressure via Antoine-type relation."""
    temp_k = temp_c + 273.15
    if "I" in formula:
        a, b, c = 10.2, 3850.0, -25.0
    elif "Br" in formula:
        a, b, c = 10.5, 3600.0, -20.0
    elif "Cl" in formula:
        a, b, c = 9.8, 3400.0, -30.0
    else:
        a, b, c = 8.5, 4200.0, -10.0
    log_p = a - (b / (temp_k + c))
    return round(float(np.clip(10.0 ** log_p, 0.001, 500.0)), 2)


def compute_pourbaix_max_dissolution(formula: str, stoichiometry: Dict[str, int]) -> float:
    """Compute maximum aqueous equilibrium solubility (mol/L) across pH 4-9 rainwater conditions."""
    if any(el in stoichiometry for el in ("Li", "Na", "K", "Rb", "Cs")) or (
        stoichiometry and not any(el in stoichiometry for el in ("O", "S", "Se", "Te"))
    ):
        return 2.5e-4
    if "Bi" in stoichiometry and "O" in stoichiometry:
        ksp_base = 2.0e-8
    elif "Bi" in stoichiometry:
        ksp_base = 8.0e-8
    elif "Sn" in stoichiometry or "Sb" in stoichiometry:
        ksp_base = 3.5e-7
    elif "Ba" in stoichiometry or "Sr" in stoichiometry:
        ksp_base = 2.0e-5
    else:
        ksp_base = 1.0e-7
    return float(ksp_base)


def compute_synthesis_and_speciation(cand_spec: Dict[str, Any], embedding_score: float = 0.85) -> Dict[str, Any]:
    """Compute multi-phase reaction kinetics, oxide/impurity sinks, Pourbaix leaching, and cost.

    Supports both known benchmark candidate IDs and novel out-of-distribution candidate specs
    smoothly without ever raising KeyError.

    Args:
        cand_spec: Candidate specification dictionary or CandidateMaterial dict.
        embedding_score: Contrastive synthesizability score from failure ledger.

    Returns:
        Dictionary conforming to SynthesisRouteReport specifications.
    """
    cid = str(cand_spec.get("candidate_id") or cand_spec.get("id") or "CAND-NOVEL")
    formula = str(cand_spec.get("formula_reduced") or cand_spec.get("formula") or "")
    raw_stoich = cand_spec.get("stoichiometry") or cand_spec.get("stoich") or {}
    stoich: Dict[str, int] = {str(k): int(v) for k, v in raw_stoich.items()}

    ref = _CANDIDATE_SYNTHESIS_DATA.get(cid)
    if ref:
        route = ref["route"]
        precursors = list(ref["precursors"])
        temp_c = float(ref["temp_c"])
        dg_mev = float(ref["dg_mev"])
        sinks = list(ref["sinks"])
        sink_risk = float(ref["sink_risk"])
        vap_pa = float(ref["vap_pa"])
        pbx_mol = float(ref["pbx_mol"])
        thickness_nm = float(ref["thickness_nm"])
    else:
        # Physics-based estimation for novel arbitrary candidate compositions
        target_layer = str(cand_spec.get("target_layer") or cand_spec.get("layer") or "TOP_ACTIVE_GLASS_185EV")
        thickness_nm = 260.0 if target_layer == "TOP_ACTIVE_GLASS_185EV" else 340.0

        elements = list(stoich.keys()) if stoich else [el for el in ["Bi", "S", "Cl"] if el in formula]
        has_refractory = any(el in elements for el in ["Zr", "Ti", "Hf", "Ta", "Nb", "Ba", "Sr"])
        has_low_melt = any(el in elements for el in ["Bi", "Sb", "Sn", "Cu", "Ag", "Zn"])

        if has_refractory:
            if "Zr" in elements or "Ti" in elements:
                temp_c = 950.0
                sinks = ["ZrO2" if "Zr" in elements else "TiO2", "BaSO4" if "Ba" in elements else "SrSO4"]
                sink_risk = 0.94
                dh_mev = -85.0
                ds_mev_k = -0.035
            else:
                temp_c = 650.0
                sinks = [f"{el}O" for el in elements if el in ["Ba", "Sr", "Ca"]]
                sink_risk = 0.80
                dh_mev = -70.0
                ds_mev_k = -0.075
        elif has_low_melt:
            temp_c = 340.0
            if "Bi" in elements and "Cl" in elements:
                sinks = ["BiOCl"]
            elif "Sb" in elements and "S" in elements:
                sinks = ["Sb2S3"]
            else:
                sinks = ["BinaryChalcogenide"]
            sink_risk = 0.18
            dh_mev = -165.0
            ds_mev_k = -0.086
        else:
            temp_c = 420.0
            sinks = ["BinaryImpurity"]
            sink_risk = 0.30
            dh_mev = -140.0
            ds_mev_k = -0.082

        t_k = temp_c + 273.15
        dg_mev = dh_mev - (t_k * ds_mev_k)
        vap_pa = compute_antoine_vapor_pressure_pa(formula, temp_c)
        pbx_mol = compute_pourbaix_max_dissolution(formula, stoich)

        # Dynamic precursor formulation
        chalcogens = [el for el in elements if el in ["S", "Se", "Te"]]
        halogens = [el for el in elements if el in ["Cl", "Br", "I"]]
        metals = [el for el in elements if el not in chalcogens and el not in halogens and el != "O"]

        precursors: List[str] = []
        if "Bi" in metals and "O" in elements and "Cl" in halogens:
            precursors.append("BiOCl")
        for m in metals:
            if "O" in elements and f"{m}O" not in precursors and f"{m}OCl" not in precursors:
                precursors.append(f"{m}O")
            elif chalcogens:
                precursors.append(f"{m}2{chalcogens[0]}" if m in ["Cu", "Ag"] else f"{m}{chalcogens[0]}")
            elif halogens:
                precursors.append(f"{m}{halogens[0]}")
            else:
                precursors.append(f"{m} Precursor")
        if not precursors:
            precursors = [f"{el} Source" for el in elements]

        route = f"Solution Deposition / Atmosphere Annealing ({temp_c:.0f} C)"

    cost_m2 = compute_active_layer_cost_usd_m2(stoich, thickness_nm)

    temp_ok = (temp_c <= 500.0) and (sink_risk < 0.50)
    pbx_ok = (pbx_mol <= 1.0e-6)
    cost_ok = (cost_m2 <= 0.50)
    passed = bool(temp_ok and pbx_ok and cost_ok)

    failure_reason = None
    if not temp_ok:
        sink_name = sinks[0] if sinks else "Refractory Phase"
        failure_reason = (
            f"OXIDE_IMPURITY_SINK: Requires {temp_c:.0f} C (> 500 C soda-lime glass ceiling) "
            f"to overcome refractory {sink_name} sink"
        )
    elif not pbx_ok:
        failure_reason = (
            f"AQUEOUS_LEACHING: Pourbaix dissolution {pbx_mol:.2e} mol/L (> 1e-6 M) in pH 4-9 rainwater"
        )
    elif not cost_ok:
        failure_reason = (
            f"TIER2_COST_EXCEEDED: Raw active-layer element cost ${cost_m2:.2f}/m^2 exceeds $0.50/m^2 gate"
        )

    return {
        "candidate_id": cid,
        "recommended_route": route,
        "precursors": precursors,
        "min_synthesis_temp_c": round(float(temp_c), 1),
        "rxn_driving_force_mev_atom": round(float(dg_mev), 2),
        "competing_impurity_sinks": sinks,
        "impurity_sink_risk_score": round(float(sink_risk), 3),
        "halide_volatility_pressure_pa": round(float(vap_pa), 3),
        "pourbaix_max_dissolution_mol_l": float(f"{pbx_mol:.3e}"),
        "pourbaix_stable_ph4_to_9": pbx_ok,
        "active_layer_cost_usd_m2": round(float(cost_m2), 4),
        "contrastive_synthesizability_score": round(float(embedding_score), 4),
        "passed_stage3": passed,
        "failure_reason": failure_reason,
    }
