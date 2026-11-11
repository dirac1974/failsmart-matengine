"""Pair-Spring Gamma Frequency Heuristic, Ion-Migration Barrier Estimate & Coherent 2x2 Abeles TMM Optics.

Implements:
- Step 1 (Section 6 of MATHEMATICAL_SPEC_V2.md):
  * 3N x 3N pair-spring force-constant matrix D(q=0) assembled over the 3D periodic crystal
    lattice with `np.linalg.eigh` diagonalization for `spring_model_gamma_freq_thz` (phonons not run).
  * Closed-form geometric + compositional ion-migration barrier heuristic `emig_heuristic_ev`
    and 300 K Vineyard-Arrhenius ionic diffusivity D_ion(300 K) (NEB not run).
- Step 2 (Section 7 of MATHEMATICAL_SPEC_V2.md):
  * Wavelength-resolved Coherent 2x2 Abeles Characteristic Transfer-Matrix Method (TMM)
    multilayer thin-film solver (`Air / MgF2 ARC / ITO / Active Chalcohalide-Oxysulfide /
    SiO2-ITO Buffer / Optical Couplant -> Textured c-Si -> Bottom IR Scavenger / Ag Mirror`)
    integrated in wavelength space via `np.trapezoid` and cross-checked against the
    Recursive Rouard/Airy photon-energy solver in `independent_verifier.py`.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import numpy as np
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser

from .kinetics_and_optics import (
    _AM15G_E_EV,
    _AM15G_PHI_SUN,
    _AM15G_WL_NM,
    _solve_cell_iv,
)
from .physics_calculators import (
    BROWN_ALTERMATT_R0,
    E_CHARGE,
    IUPAC_ATOMIC_MASSES,
)
from .schemas import (
    AtomisticSpringMigrationReport,
    CoherentTMM4TStackReport,
    GradedARCTechnoEconomicReport,
    LabSynthesisAndDefectDossier,
    Phase10BifacialLossAndStringDossier,
    RealWorldLCOEStressTestReport,
)

# Exact CODATA 2018 Boltzmann constant (J/K) and THz conversion factor (Section 6.1)
KB_J = 1.380649e-23
THZ_CONV_FACTOR = 15.633302
SQFT_TO_M2 = 0.09290304
SI_REF_EFF_PCT = 22.00
SI_REF_MOD_COST_USD_M2 = 40.00
BOS_AREA_COST_USD_M2 = 100.00
SUBCELL_PROCESS_TCO_COST_USD_M2 = 6.50


def compute_3d_harmonic_dynamical_matrix_gamma(
    struct: Structure,
) -> Dict[str, Any]:
    """Assemble and diagonalize the 3N x 3N mass-weighted Dynamical Matrix D(q=0) via np.linalg.eigh."""
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

            if el_i in BROWN_ALTERMATT_R0 and el_j in BROWN_ALTERMATT_R0:
                r0 = round(BROWN_ALTERMATT_R0[el_i] + BROWN_ALTERMATT_R0[el_j], 4)
            else:
                r0 = 2.45
            k_par = 48.0 * math.exp((r0 - dist) / 0.37)
            k_perp = 0.18 * k_par

            k_block = (k_par - k_perp) * np.outer(u_vec, u_vec) + k_perp * eye3

            # Off-diagonal (3i:3i+3, 3j:3j+3) and Acoustic Sum Rule on-diagonal (3i:3i+3, 3i:3i+3)
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

    # Primary diagonalization via numpy.linalg.eigh
    eigvals, _ = np.linalg.eigh(dyn_mat)
    freqs_thz = np.sign(eigvals) * THZ_CONV_FACTOR * np.sqrt(np.abs(eigvals))

    opt_freqs = freqs_thz[3:]
    min_opt_thz = float(opt_freqs[0]) if len(opt_freqs) > 0 else 0.0
    max_lo_thz = float(opt_freqs[-1]) if len(opt_freqs) > 0 else 0.0

    return {
        "nsites_unit_cell": n_sites,
        "dynamical_matrix_dim": dim,
        "spring_model_gamma_freq_thz": [round(min_opt_thz, 4), round(max_lo_thz, 4)],
    }


def compute_ion_migration_heuristic(
    struct: Structure,
    stoichiometry: Dict[str, int],
) -> Dict[str, Any]:
    """Compute closed-form geometric ion-migration barrier heuristic and 300 K diffusivity."""
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

    target_indices = [i for i, site in enumerate(struct) if site.specie.symbol == mig_sp]
    best_hop_dist = 999.0
    best_r_a = np.zeros(3, dtype=float)
    best_r_b = np.zeros(3, dtype=float)

    for min_r, max_r in ((2.20, 6.50), (1.80, 9.50)):
        for i in target_indices:
            site_i = struct[i]
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
    emig_heur = round(float(np.clip(raw_barrier, 0.35, 1.45)), 4)

    # Vineyard-Arrhenius 300 K ionic diffusivity (nu_0 = 1e12 s^-1, 1 A^2 = 1e-16 cm^2)
    d_ion_300k = (1.0 / 6.0) * 1.0e12 * ((d_hop ** 2) * 1.0e-16) * math.exp(
        -(emig_heur * E_CHARGE) / (KB_J * 300.0)
    )

    return {
        "migrating_species": mig_sp,
        "shortest_hop_distance_ang": d_hop,
        "bottleneck_clearance_ang": clearance,
        "emig_heuristic_ev": emig_heur,
        "room_temp_diffusivity_cm2_s": float(f"{d_ion_300k:.3e}"),
    }


def evaluate_spring_and_migration_heuristics(
    dossier: Dict[str, Any],
) -> AtomisticSpringMigrationReport:
    """Evaluate pair-spring Gamma frequencies and closed-form migration barrier heuristic."""
    from .independent_verifier import independently_verify_spring_and_migration_heuristics

    cand = dossier["candidate"]
    cif_text = cand["cif_content"]
    stoich = cand["stoichiometry"]
    ox = cand["oxidation_states"]

    struct = CifParser.from_str(cif_text, occupancy_tolerance=10.0).parse_structures(primitive=False)[0]
    ph_res = compute_3d_harmonic_dynamical_matrix_gamma(struct)
    mig_res = compute_ion_migration_heuristic(struct, stoich)

    blind_res = independently_verify_spring_and_migration_heuristics(
        cif_text=cif_text,
        stoichiometry=stoich,
        oxidation_states=ox,
    )

    if (
        abs(ph_res["spring_model_gamma_freq_thz"][0] - blind_res["spring_model_gamma_freq_thz"][0]) > 1e-3
        or abs(ph_res["spring_model_gamma_freq_thz"][1] - blind_res["spring_model_gamma_freq_thz"][1]) > 1e-3
        or abs(mig_res["emig_heuristic_ev"] - blind_res["emig_heuristic_ev"]) > 1e-3
    ):
        raise AssertionError(
            f"REDUNDANCY_MISMATCH_BLOCK: Spring/migration heuristic mismatch on {cand['candidate_id']}: "
            f"primary={(ph_res, mig_res)} vs verifier={blind_res}"
        )

    emig_ok = bool(mig_res["emig_heuristic_ev"] >= 0.65)

    return AtomisticSpringMigrationReport(
        candidate_id=cand["candidate_id"],
        formula_reduced=cand["formula_reduced"],
        target_layer=cand["target_layer"],
        nsites_unit_cell=ph_res["nsites_unit_cell"],
        dynamical_matrix_dim=ph_res["dynamical_matrix_dim"],
        spring_model_gamma_freq_thz=ph_res["spring_model_gamma_freq_thz"],
        migrating_species=mig_res["migrating_species"],
        shortest_hop_distance_ang=mig_res["shortest_hop_distance_ang"],
        bottleneck_clearance_ang=mig_res["bottleneck_clearance_ang"],
        emig_heuristic_ev=mig_res["emig_heuristic_ev"],
        room_temp_diffusivity_cm2_s=mig_res["room_temp_diffusivity_cm2_s"],
        dynamically_stable=None,
        emig_gate_passed=emig_ok,
        redundancy_verified=True,
        sha256_digest=blind_res["sha256_digest"],
    )


def compute_general_abeles_tmm_reflectance_transmittance(
    n_list: List[np.ndarray],
    d_list_nm: List[float],
    wl_nm: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """General normal-incidence 2x2 Abeles characteristic matrix solver for an N-medium stack.

    Args:
        n_list: List of complex refractive-index arrays [n_0, n_1, ..., n_M], each of shape (N_wl,).
                Medium 0 is the semi-infinite incident medium; medium M is the semi-infinite substrate.
        d_list_nm: Layer thicknesses [0.0, d_1, ..., d_{M-1}, 0.0] in nm.
        wl_nm: Wavelength array in nm, shape (N_wl,).

    Returns:
        (reflectance_r, transmittance_t) arrays of shape (N_wl,) in [0, 1].
    """
    n_pts = len(wl_nm)
    m_tot = np.zeros((n_pts, 2, 2), dtype=np.complex128)
    m_tot[:, 0, 0] = 1.0
    m_tot[:, 1, 1] = 1.0
    last_idx = len(n_list) - 1

    for m in range(last_idx):
        nm_curr = n_list[m]
        nm_next = n_list[m + 1]
        r_m = (nm_curr - nm_next) / (nm_curr + nm_next)
        t_m = (2.0 * nm_curr) / (nm_curr + nm_next)

        i_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
        i_mat[:, 0, 0] = 1.0 / t_m
        i_mat[:, 0, 1] = r_m / t_m
        i_mat[:, 1, 0] = r_m / t_m
        i_mat[:, 1, 1] = 1.0 / t_m

        m_tot = np.matmul(m_tot, i_mat)

        if m + 1 < last_idx and d_list_nm[m + 1] > 0.0:
            beta = (2.0 * math.pi * n_list[m + 1] * d_list_nm[m + 1]) / wl_nm
            p_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
            p_mat[:, 0, 0] = np.exp(-1j * beta)
            p_mat[:, 1, 1] = np.exp(1j * beta)
            m_tot = np.matmul(m_tot, p_mat)

    r_tot = m_tot[:, 1, 0] / m_tot[:, 0, 0]
    t_tot = 1.0 / m_tot[:, 0, 0]

    r_tmm = np.abs(r_tot) ** 2
    t_tmm = (np.real(n_list[-1]) / np.real(n_list[0])) * (np.abs(t_tot) ** 2)
    return r_tmm, t_tmm


def compute_abeles_2x2_tmm_reflectance_transmittance(
    wl_nm: np.ndarray,
    e_ev: np.ndarray,
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    d_top_nm: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Method A (Section 7.2): Vectorized 2x2 Abeles Characteristic Matrix Product M = I01 P1 I12 P2 I23 P3 I34 P4 I45."""
    wl_um = wl_nm / 1000.0

    # Complex refractive indices of the 6 media (m = 0..5)
    n0 = np.ones_like(wl_nm, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um ** 2)).astype(np.complex128)

    n_ito_real = np.maximum(1.45, 1.92 - 0.085 * (wl_um ** 2))
    k_ito = 0.0018 + 0.0065 * (wl_um ** 3)
    n2 = n_ito_real + 1j * k_ito

    alpha1 = 1.2e5 * (np.maximum(0.0, e_ev - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, e_ev - eg_dir_1))
    n_act_real = math.sqrt(eps_inf_1) + 0.035 / (wl_um ** 2)
    k_act = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n3 = n_act_real + 1j * k_act

    n_buf_real = 1.720 + 0.0040 / (wl_um ** 2)
    k_buf = 0.0012 * (wl_um ** 2)
    n4 = n_buf_real + 1j * k_buf

    n5 = np.full_like(wl_nm, 1.520, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5]
    d_list_nm = [0.0, 98.0, 105.0, float(d_top_nm), 85.0, 0.0]

    r_tmm_1, t_tmm_1 = compute_general_abeles_tmm_reflectance_transmittance(n_list, d_list_nm, wl_nm)
    t_ito_front = np.exp(-4.0 * math.pi * k_ito * 105.0 / wl_nm)

    return r_tmm_1, t_tmm_1, t_ito_front, alpha1


def evaluate_coherent_abeles_tmm_4t_stack(
    top_dossier: Dict[str, Any],
    bottom_dossier: Dict[str, Any],
    scalar_pair: Dict[str, Any],
) -> CoherentTMM4TStackReport:
    """Evaluate 3-layer 4T Silicon-Sandwich stack using Method A (2x2 Abeles TMM) and verify against Method B (Rouard/Airy)."""
    from .independent_verifier import independently_verify_coherent_tmm_4t_stack

    c_top = top_dossier["candidate"]
    e_top = top_dossier["electronics"]
    o_top = top_dossier["optics"]
    s_top = top_dossier["synthesis"]

    c_bot = bottom_dossier["candidate"]
    e_bot = bottom_dossier["electronics"]
    o_bot = bottom_dossier["optics"]
    s_bot = bottom_dossier["synthesis"]

    eg_ind_1 = float(e_top["gap_est_indirect_ev"])
    eg_dir_1 = float(e_top["gap_est_direct_ev"])
    eps_inf_1 = float(e_top["eps_inf"])
    d1_nm = float(o_top["film_thickness_nm"])
    d1_m = d1_nm * 1.0e-9

    eg_ind_3 = float(e_bot["gap_est_indirect_ev"])
    eg_dir_3 = float(e_bot["gap_est_direct_ev"])
    eps_inf_3 = float(e_bot["eps_inf"])
    d3_nm = float(o_bot["film_thickness_nm"])
    d3_m = d3_nm * 1.0e-9

    r_tmm_1, t_tmm_1, t_ito_front, alpha1 = compute_abeles_2x2_tmm_reflectance_transmittance(
        wl_nm=_AM15G_WL_NM,
        e_ev=_AM15G_E_EV,
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        d_top_nm=d1_nm,
    )

    yab1 = 4.0 * eps_inf_1
    fabs1 = (yab1 * alpha1 * d1_m) / (1.0 + yab1 * alpha1 * d1_m)
    a_tmm_1 = (1.0 - r_tmm_1) * t_ito_front * fabs1
    t_stack_tmm_1 = t_tmm_1 * (1.0 - fabs1)

    _, _, _, eta_top_tmm = _solve_cell_iv(a_tmm_1, _AM15G_PHI_SUN, eg_dir_1, eg_ind_1)

    # Mean front reflectance over above-bandgap solar window [eg_ind_1, 3.50] eV
    mask_above = (_AM15G_E_EV >= eg_ind_1) & (_AM15G_E_EV <= 3.50)
    flux_above = float(np.trapezoid(_AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above]))
    mean_refl_pct = float(
        np.trapezoid(r_tmm_1[mask_above] * _AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above])
        / max(1.0e-12, flux_above)
        * 100.0
    )

    # Sub-bandgap transmittance over [0.75, eg_ind_1 - 0.02] eV
    mask_sub = (_AM15G_E_EV >= 0.75) & (_AM15G_E_EV <= (eg_ind_1 - 0.02))
    flux_sub = float(np.trapezoid(_AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub]))
    sub_trans_pct = float(
        np.trapezoid(t_stack_tmm_1[mask_sub] * _AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub])
        / max(1.0e-12, flux_sub)
        * 100.0
    )

    phi2_tmm = _AM15G_PHI_SUN * t_stack_tmm_1

    # Step B: Middle c-Si Wafer (160 um)
    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, _AM15G_E_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(np.maximum(0.0, _AM15G_E_EV - 3.40))
    fabs_si_2l = (49.0 * alpha_si * d_si_m) / (1.0 + 49.0 * alpha_si * d_si_m)
    _, _, _, eta_si_2l_tmm = _solve_cell_iv(0.98 * fabs_si_2l, phi2_tmm, 1.12, 1.12, j0_fixed=1.2e-12)

    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    _, _, _, eta_si_3l_tmm = _solve_cell_iv(0.98 * fabs_si_3l, phi2_tmm, 1.12, 1.12, j0_fixed=1.2e-12)

    t_si_fca_low = np.exp(-0.08 * ((_AM15G_WL_NM / 1200.0) ** 2))
    t_si_fca_std = np.exp(-0.38 * ((_AM15G_WL_NM / 1200.0) ** 2))
    phi3_low_tmm = phi2_tmm * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
    phi3_std_tmm = phi2_tmm * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std

    # Step C: Bottom IR Scavenger with index-matched buffer entrance
    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, _AM15G_E_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, _AM15G_E_EV - eg_dir_3))
    fabs3 = (yab3 * alpha3 * d3_m) / (1.0 + yab3 * alpha3 * d3_m)
    a_tmm_3 = (1.0 - r_int_23) * fabs3

    _, _, _, eta_bot_low_tmm = _solve_cell_iv(a_tmm_3, phi3_low_tmm, eg_dir_3, eg_ind_3)
    _, _, _, eta_bot_std_tmm = _solve_cell_iv(a_tmm_3, phi3_std_tmm, eg_dir_3, eg_ind_3)

    tmm_2l = round(eta_top_tmm + eta_si_2l_tmm, 2)
    tmm_4t_std = round(eta_top_tmm + eta_si_3l_tmm + eta_bot_std_tmm, 2)
    tmm_4t_low = round(eta_top_tmm + eta_si_3l_tmm + eta_bot_low_tmm, 2)
    delta_vs_scalar = round(tmm_4t_low - float(scalar_pair["tandem_4t_low_fca_total_eff_percent"]), 2)

    # Blinded Cross-Check against Method B (Recursive Rouard/Airy in Photon-Energy Space)
    blind_tmm = independently_verify_coherent_tmm_4t_stack(
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        thickness_nm_1=d1_nm,
        eg_ind_3=eg_ind_3,
        eg_dir_3=eg_dir_3,
        eps_inf_3=eps_inf_3,
        thickness_nm_3=d3_nm,
    )
    rouard_diff = round(abs(tmm_4t_low - blind_tmm["tmm_4t_low_fca_pce_percent"]), 4)
    if rouard_diff > 0.05 or not blind_tmm["photon_conservation_holds"]:
        raise AssertionError(
            f"REDUNDANCY_MISMATCH_BLOCK: Coherent 2x2 Abeles TMM vs Recursive Rouard/Airy discrepancy "
            f"{rouard_diff:.4f}% > 0.05% on {scalar_pair['pair_id']}"
        )

    return CoherentTMM4TStackReport(
        pair_id=scalar_pair["pair_id"],
        top_mp_id=c_top["candidate_id"],
        top_formula=c_top["formula_reduced"],
        bottom_mp_id=c_bot["candidate_id"],
        bottom_formula=c_bot["formula_reduced"],
        arc_mgf2_thickness_nm=98.0,
        front_ito_thickness_nm=105.0,
        top_absorber_thickness_nm=d1_nm,
        rear_buffer_thickness_nm=85.0,
        bottom_absorber_thickness_nm=d3_nm,
        tmm_mean_front_reflectance_percent=round(mean_refl_pct, 2),
        tmm_sub_bandgap_transmittance_percent=round(sub_trans_pct, 2),
        tmm_top_pce_percent=round(eta_top_tmm, 2),
        tmm_si_pce_percent=round(eta_si_3l_tmm, 2),
        tmm_bottom_std_si_pce_percent=round(eta_bot_std_tmm, 2),
        tmm_bottom_pce_percent=round(eta_bot_low_tmm, 2),
        tmm_2layer_pce_percent=tmm_2l,
        tmm_4t_std_si_pce_percent=tmm_4t_std,
        tmm_4t_low_fca_pce_percent=tmm_4t_low,
        scalar_to_tmm_delta_pce_percent=delta_vs_scalar,
        combined_active_cost_usd_m2=round(s_top["active_layer_cost_usd_m2"] + s_bot["active_layer_cost_usd_m2"], 4),
        photon_conservation_verified=blind_tmm["photon_conservation_holds"],
        rouard_airy_redundancy_diff_percent=rouard_diff,
        sha256_digest=blind_tmm["sha256_digest"],
    )


def compute_abeles_7medium_graded_arc_tmm(
    wl_nm: np.ndarray,
    e_ev: np.ndarray,
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    d_top_nm: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Method A (Section 8.1): Vectorized 2x2 Abeles Characteristic Matrix on 7-Medium Graded-ARC + TiO2 Stack.

    Media:
      0: Air (n0 = 1.000)
      1: Outer MgF2 ARC (d1 = 94.0 nm)
      2: Front ITO (d2 = 80.0 nm)
      3: High-Index TiO2 Impedance Matcher (d3 = 48.0 nm, n3 = 2.380 + 0.0180/wl_um^2 + i*0.0004*wl_um^2)
      4: Top Active Absorber (d4 = d_top_nm)
      5: Rear SiO2/ITO Buffer (d5 = 82.0 nm)
      6: Optical Couplant (n6 = 1.520)
    """
    wl_um = wl_nm / 1000.0

    n0 = np.ones_like(wl_nm, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um ** 2)).astype(np.complex128)

    n_ito_real = np.maximum(1.45, 1.92 - 0.085 * (wl_um ** 2))
    k_ito = 0.0018 + 0.0065 * (wl_um ** 3)
    n2 = n_ito_real + 1j * k_ito

    n_tio2_real = 2.380 + 0.0180 / (wl_um ** 2)
    k_tio2 = 0.0004 * (wl_um ** 2)
    n3 = n_tio2_real + 1j * k_tio2

    alpha1 = 1.2e5 * (np.maximum(0.0, e_ev - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, e_ev - eg_dir_1))
    n_act_real = math.sqrt(eps_inf_1) + 0.035 / (wl_um ** 2)
    k_act = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n4 = n_act_real + 1j * k_act

    n_buf_real = 1.720 + 0.0040 / (wl_um ** 2)
    k_buf = 0.0012 * (wl_um ** 2)
    n5 = n_buf_real + 1j * k_buf

    n6 = np.full_like(wl_nm, 1.520, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5, n6]
    d_list_nm = [0.0, 94.0, 80.0, 48.0, float(d_top_nm), 82.0, 0.0]

    n_pts = len(wl_nm)
    m_tot = np.zeros((n_pts, 2, 2), dtype=np.complex128)
    m_tot[:, 0, 0] = 1.0
    m_tot[:, 1, 1] = 1.0

    for m in range(6):
        nm_curr = n_list[m]
        nm_next = n_list[m + 1]
        r_m = (nm_curr - nm_next) / (nm_curr + nm_next)
        t_m = (2.0 * nm_curr) / (nm_curr + nm_next)

        i_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
        i_mat[:, 0, 0] = 1.0 / t_m
        i_mat[:, 0, 1] = r_m / t_m
        i_mat[:, 1, 0] = r_m / t_m
        i_mat[:, 1, 1] = 1.0 / t_m

        m_tot = np.matmul(m_tot, i_mat)

        if m + 1 <= 5:
            beta = (2.0 * math.pi * n_list[m + 1] * d_list_nm[m + 1]) / wl_nm
            p_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
            p_mat[:, 0, 0] = np.exp(-1j * beta)
            p_mat[:, 1, 1] = np.exp(1j * beta)
            m_tot = np.matmul(m_tot, p_mat)

    r_tot = m_tot[:, 1, 0] / m_tot[:, 0, 0]
    t_tot = 1.0 / m_tot[:, 0, 0]

    r_arc_1 = np.abs(r_tot) ** 2
    t_arc_1 = (np.real(n6) / np.real(n0)) * (np.abs(t_tot) ** 2)
    t_win_front = np.exp(-4.0 * math.pi * (k_ito * 80.0 + k_tio2 * 48.0) / wl_nm)

    return r_arc_1, t_arc_1, t_win_front, alpha1


def compute_techno_economic_fom_suite(
    eta_2l_pct: float,
    eta_3l_pct: float,
    raw_cost_top_usd_m2: float,
    raw_cost_bot_usd_m2: float,
) -> Dict[str, float]:
    """Compute the 4-Metric Techno-Economic & Area-Value Suite (Section 8.2 of MATHEMATICAL_SPEC_V2.md)."""
    raw_2l = float(raw_cost_top_usd_m2)
    raw_3l = float(raw_cost_top_usd_m2 + raw_cost_bot_usd_m2)

    delta_c_2l = raw_2l + SUBCELL_PROCESS_TCO_COST_USD_M2
    delta_c_3l = raw_3l + 2.0 * SUBCELL_PROCESS_TCO_COST_USD_M2

    p_2l_m2 = 10.0 * eta_2l_pct
    p_2l_sqft = p_2l_m2 * SQFT_TO_M2
    p_3l_m2 = 10.0 * eta_3l_pct
    p_3l_sqft = p_3l_m2 * SQFT_TO_M2

    g_2l = eta_2l_pct / SI_REF_EFF_PCT
    g_3l = eta_3l_pct / SI_REF_EFF_PCT

    # Metric 1: Normalized Multi-Junction Cost-Efficiency Ratio (CER_N)
    cer_2l = (2.0 * SI_REF_MOD_COST_USD_M2 * g_2l) / (SI_REF_MOD_COST_USD_M2 + delta_c_2l)
    cer_3l = (3.0 * SI_REF_MOD_COST_USD_M2 * g_3l) / (SI_REF_MOD_COST_USD_M2 + delta_c_3l)

    # Metric 2: Marginal Cost per Incremental Watt (MCIW_raw & MCIW_full in $/dW_p)
    dp_2l = max(1e-6, 10.0 * (eta_2l_pct - SI_REF_EFF_PCT))
    dp_3l = max(1e-6, 10.0 * (eta_3l_pct - SI_REF_EFF_PCT))
    mciw_2l_raw = raw_2l / dp_2l
    mciw_2l_full = delta_c_2l / dp_2l
    mciw_3l_raw = raw_3l / dp_3l
    mciw_3l_full = delta_c_3l / dp_3l

    # Metric 3: Factory-Gate Module Cost-Performance Ratio (CPR_mod)
    cpr_2l = g_2l / (1.0 + delta_c_2l / SI_REF_MOD_COST_USD_M2)
    cpr_3l = g_3l / (1.0 + delta_c_3l / SI_REF_MOD_COST_USD_M2)

    # Metric 4: Area-Constrained System Value Index (SVI_BOS)
    base_sys = SI_REF_MOD_COST_USD_M2 + BOS_AREA_COST_USD_M2
    svi_2l = (base_sys * g_2l) / (base_sys + delta_c_2l)
    svi_3l = (base_sys * g_3l) / (base_sys + delta_c_3l)

    return {
        "power_density_2l_w_m2": round(p_2l_m2, 2),
        "power_density_2l_w_sqft": round(p_2l_sqft, 2),
        "power_density_3l_w_m2": round(p_3l_m2, 2),
        "power_density_3l_w_sqft": round(p_3l_sqft, 2),
        "eff_gain_ratio_2l": round(g_2l, 4),
        "eff_gain_ratio_3l": round(g_3l, 4),
        "cer_2l_vs_2x_si": round(cer_2l, 4),
        "cer_3l_vs_3x_si": round(cer_3l, 4),
        "mciw_2l_raw_usd_per_dw": round(mciw_2l_raw, 5),
        "mciw_2l_full_usd_per_dw": round(mciw_2l_full, 4),
        "mciw_3l_raw_usd_per_dw": round(mciw_3l_raw, 5),
        "mciw_3l_full_usd_per_dw": round(mciw_3l_full, 4),
        "cpr_mod_2l": round(cpr_2l, 4),
        "cpr_mod_3l": round(cpr_3l, 4),
        "svi_bos_2l": round(svi_2l, 4),
        "svi_bos_3l": round(svi_3l, 4),
        "top_raw_cost_usd_m2": round(raw_2l, 4),
        "combined_raw_cost_usd_m2": round(raw_3l, 4),
    }


def evaluate_graded_arc_and_techno_economics_4t_stack(
    top_dossier: Dict[str, Any],
    bottom_dossier: Dict[str, Any],
    single_arc_report: CoherentTMM4TStackReport,
) -> GradedARCTechnoEconomicReport:
    """Evaluate 7-Medium Graded-ARC + TiO2 Impedance-Matching 4T Stack & 4-Metric Techno-Economics (v5.0)."""
    from .independent_verifier import independently_verify_graded_arc_and_techno_economics

    c_top = top_dossier["candidate"]
    e_top = top_dossier["electronics"]
    o_top = top_dossier["optics"]
    s_top = top_dossier["synthesis"]

    c_bot = bottom_dossier["candidate"]
    e_bot = bottom_dossier["electronics"]
    o_bot = bottom_dossier["optics"]
    s_bot = bottom_dossier["synthesis"]

    eg_ind_1 = float(e_top["gap_est_indirect_ev"])
    eg_dir_1 = float(e_top["gap_est_direct_ev"])
    eps_inf_1 = float(e_top["eps_inf"])
    d1_nm = float(o_top["film_thickness_nm"])
    d1_m = d1_nm * 1.0e-9

    eg_ind_3 = float(e_bot["gap_est_indirect_ev"])
    eg_dir_3 = float(e_bot["gap_est_direct_ev"])
    eps_inf_3 = float(e_bot["eps_inf"])
    d3_nm = float(o_bot["film_thickness_nm"])
    d3_m = d3_nm * 1.0e-9

    r_arc_1, t_arc_1, t_win_front, alpha1 = compute_abeles_7medium_graded_arc_tmm(
        wl_nm=_AM15G_WL_NM,
        e_ev=_AM15G_E_EV,
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        d_top_nm=d1_nm,
    )

    yab1 = 4.0 * eps_inf_1
    fabs1 = (yab1 * alpha1 * d1_m) / (1.0 + yab1 * alpha1 * d1_m)
    a_arc_1 = (1.0 - r_arc_1) * t_win_front * fabs1
    t_stack_arc_1 = t_arc_1 * (1.0 - fabs1)

    _, _, _, eta_top_arc = _solve_cell_iv(a_arc_1, _AM15G_PHI_SUN, eg_dir_1, eg_ind_1)

    mask_above = (_AM15G_E_EV >= eg_ind_1) & (_AM15G_E_EV <= 3.50)
    flux_above = float(np.trapezoid(_AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above]))
    mean_refl_pct = float(
        np.trapezoid(r_arc_1[mask_above] * _AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above])
        / max(1.0e-12, flux_above)
        * 100.0
    )

    mask_sub = (_AM15G_E_EV >= 0.75) & (_AM15G_E_EV <= (eg_ind_1 - 0.02))
    flux_sub = float(np.trapezoid(_AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub]))
    sub_trans_pct = float(
        np.trapezoid(t_stack_arc_1[mask_sub] * _AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub])
        / max(1.0e-12, flux_sub)
        * 100.0
    )

    phi2_arc = _AM15G_PHI_SUN * t_stack_arc_1

    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, _AM15G_E_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(np.maximum(0.0, _AM15G_E_EV - 3.40))
    fabs_si_2l = (49.0 * alpha_si * d_si_m) / (1.0 + 49.0 * alpha_si * d_si_m)
    _, _, _, eta_si_2l_arc = _solve_cell_iv(0.98 * fabs_si_2l, phi2_arc, 1.12, 1.12, j0_fixed=1.2e-12)

    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    _, _, _, eta_si_3l_arc = _solve_cell_iv(0.98 * fabs_si_3l, phi2_arc, 1.12, 1.12, j0_fixed=1.2e-12)

    t_si_fca_low = np.exp(-0.08 * ((_AM15G_WL_NM / 1200.0) ** 2))
    t_si_fca_std = np.exp(-0.38 * ((_AM15G_WL_NM / 1200.0) ** 2))
    phi3_low_arc = phi2_arc * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
    phi3_std_arc = phi2_arc * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std

    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, _AM15G_E_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, _AM15G_E_EV - eg_dir_3))
    fabs3 = (yab3 * alpha3 * d3_m) / (1.0 + yab3 * alpha3 * d3_m)
    a_arc_3 = (1.0 - r_int_23) * fabs3

    _, _, _, eta_bot_low_arc = _solve_cell_iv(a_arc_3, phi3_low_arc, eg_dir_3, eg_ind_3)
    _, _, _, eta_bot_std_arc = _solve_cell_iv(a_arc_3, phi3_std_arc, eg_dir_3, eg_ind_3)

    graded_2l = round(eta_top_arc + eta_si_2l_arc, 2)
    graded_4t_std = round(eta_top_arc + eta_si_3l_arc + eta_bot_std_arc, 2)
    graded_4t_low = round(eta_top_arc + eta_si_3l_arc + eta_bot_low_arc, 2)

    raw_top = float(s_top["active_layer_cost_usd_m2"])
    raw_bot = float(s_bot["active_layer_cost_usd_m2"])
    te_fom = compute_techno_economic_fom_suite(
        eta_2l_pct=graded_2l,
        eta_3l_pct=graded_4t_low,
        raw_cost_top_usd_m2=raw_top,
        raw_cost_bot_usd_m2=raw_bot,
    )

    blind_arc = independently_verify_graded_arc_and_techno_economics(
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        thickness_nm_1=d1_nm,
        eg_ind_3=eg_ind_3,
        eg_dir_3=eg_dir_3,
        eps_inf_3=eps_inf_3,
        thickness_nm_3=d3_nm,
        raw_cost_top_usd_m2=raw_top,
        raw_cost_bot_usd_m2=raw_bot,
    )

    rouard_diff = round(abs(graded_4t_low - blind_arc["graded_4t_low_fca_pce_percent"]), 4)
    te_ok = bool(
        abs(te_fom["cer_2l_vs_2x_si"] - blind_arc["cer_2l_vs_2x_si"]) <= 2e-3
        and abs(te_fom["cer_3l_vs_3x_si"] - blind_arc["cer_3l_vs_3x_si"]) <= 2e-3
        and abs(te_fom["mciw_3l_full_usd_per_dw"] - blind_arc["mciw_3l_full_usd_per_dw"]) <= 2e-3
        and abs(te_fom["cpr_mod_3l"] - blind_arc["cpr_mod_3l"]) <= 2e-3
        and abs(te_fom["svi_bos_3l"] - blind_arc["svi_bos_3l"]) <= 2e-3
    )
    if rouard_diff > 0.05 or not blind_arc["photon_conservation_holds"] or not te_ok:
        raise AssertionError(
            f"REDUNDANCY_MISMATCH_BLOCK: Graded-ARC or Techno-Economic mismatch on {single_arc_report.pair_id}: "
            f"rouard_diff={rouard_diff:.4f}%, te_ok={te_ok}"
        )

    refl_red = round(single_arc_report.tmm_mean_front_reflectance_percent - round(mean_refl_pct, 2), 2)
    gain_4t = round(graded_4t_low - single_arc_report.tmm_4t_low_fca_pce_percent, 2)

    return GradedARCTechnoEconomicReport(
        pair_id=single_arc_report.pair_id,
        top_mp_id=c_top["candidate_id"],
        top_formula=c_top["formula_reduced"],
        bottom_mp_id=c_bot["candidate_id"],
        bottom_formula=c_bot["formula_reduced"],
        arc_mgf2_thickness_nm=94.0,
        front_ito_thickness_nm=80.0,
        tio2_matcher_thickness_nm=48.0,
        top_absorber_thickness_nm=d1_nm,
        rear_buffer_thickness_nm=82.0,
        bottom_absorber_thickness_nm=d3_nm,
        single_arc_front_reflectance_percent=single_arc_report.tmm_mean_front_reflectance_percent,
        graded_arc_front_reflectance_percent=round(mean_refl_pct, 2),
        reflectance_reduction_percent=refl_red,
        graded_sub_bandgap_transmittance_percent=round(sub_trans_pct, 2),
        graded_top_pce_percent=round(eta_top_arc, 2),
        graded_si_pce_percent=round(eta_si_3l_arc, 2),
        graded_bottom_std_si_pce_percent=round(eta_bot_std_arc, 2),
        graded_bottom_pce_percent=round(eta_bot_low_arc, 2),
        graded_2layer_pce_percent=graded_2l,
        graded_4t_std_si_pce_percent=graded_4t_std,
        graded_4t_low_fca_pce_percent=graded_4t_low,
        single_to_graded_4t_gain_percent=gain_4t,
        **te_fom,
        photon_conservation_verified=blind_arc["photon_conservation_holds"],
        rouard_airy_redundancy_diff_percent=rouard_diff,
        techno_economic_redundancy_verified=te_ok,
        sha256_digest=blind_arc["sha256_digest"],
    )


def evaluate_phase9a_lab_synthesis_and_defect_supercell(
    finalist_dossier: Dict[str, Any],
    defect_deck_dir: str,
) -> LabSynthesisAndDefectDossier:
    """Phase 9A: Generate 10.0 mmol Stoichiometric Lab Synthesis Recipe & Neutral Vacancy Supercell Deck."""
    import re
    from pathlib import Path
    from .independent_verifier import independently_verify_phase9a_lab_and_defect_dossier

    cand = finalist_dossier["candidate"]
    synth = finalist_dossier["synthesis"]
    elec = finalist_dossier["electronics"]

    cid = str(cand["candidate_id"])
    formula = str(cand["formula_reduced"])
    stoich: Dict[str, int] = {str(k): int(v) for k, v in cand["stoichiometry"].items()}
    struct = CifParser.from_str(cand["cif_content"]).parse_structures(primitive=False)[0]

    # 1. Exact 10.0 mmol (0.010 mol) batch precursor mass balance using IUPAC_ATOMIC_MASSES
    batch_mol = 0.010
    fu_molar_mass = sum(cnt * IUPAC_ATOMIC_MASSES[el] for el, cnt in stoich.items())
    target_mass_g = batch_mol * fu_molar_mass

    reagent_masses: Dict[str, float] = {}
    volatile_overpressure_masses: Dict[str, float] = {}
    supplied_elemental_mass_g = 0.0

    volatile_elements = {"S", "Se", "Cl", "Br", "I"}
    for el, cnt in stoich.items():
        el_moles = batch_mol * float(cnt)
        el_mass_g = el_moles * IUPAC_ATOMIC_MASSES[el]
        reagent_label = f"{el}_stoich_source"
        reagent_masses[reagent_label] = round(el_mass_g, 6)
        supplied_elemental_mass_g += el_mass_g
        if el in volatile_elements:
            volatile_overpressure_masses[f"{el}_5pct_overpressure"] = round(1.05 * el_mass_g, 6)

    mass_diff_g = abs(supplied_elemental_mass_g - target_mass_g)

    # 2. Neutral Vacancy Supercell Expansion using perpendicular lattice-plane spacings >= 10.0 A
    mat = np.array(struct.lattice.matrix, dtype=float)
    vol = abs(float(np.linalg.det(mat)))
    d_perp_a = vol / float(np.linalg.norm(np.cross(mat[1], mat[2])))
    d_perp_b = vol / float(np.linalg.norm(np.cross(mat[2], mat[0])))
    d_perp_c = vol / float(np.linalg.norm(np.cross(mat[0], mat[1])))
    na = max(1, int(math.ceil(10.0 / d_perp_a)))
    if na * d_perp_a < 10.0:
        na += 1
    nb = max(1, int(math.ceil(10.0 / d_perp_b)))
    if nb * d_perp_b < 10.0:
        nb += 1
    nc = max(1, int(math.ceil(10.0 / d_perp_c)))
    if nc * d_perp_c < 10.0:
        nc += 1

    n_super = na * nb * nc * len(struct)
    omega_super = float(struct.volume) * (na * nb * nc)
    l_eff = omega_super ** (1.0 / 3.0)

    eps_0 = float(elec["eps_static"])
    madelung_alpha = 2.8373
    coulomb_ev_ang = 14.399645
    pc_q1 = (1.0 * madelung_alpha * coulomb_ev_ang) / (eps_0 * l_eff)
    pc_q2 = (4.0 * madelung_alpha * coulomb_ev_ang) / (eps_0 * l_eff)

    dom_vac = str(elec["dominant_vacancy_defect"])
    vac_el = str(elec.get("dominant_vacancy_element") or "").strip()
    if not vac_el:
        raise ValueError(f"Missing explicit dominant_vacancy_element on {cid} ({formula}) for label '{dom_vac}'")

    # Write Stage 5 Neutral Vacancy Supercell QE Input Deck
    out_dir = Path(defect_deck_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    deck_fname = f"{cid}_{formula}_neutral_vacancy_{na}x{nb}x{nc}.in"
    deck_path = out_dir / deck_fname

    super_struct = struct.copy()
    super_struct.make_supercell([na, nb, nc])

    smat = np.array(super_struct.lattice.matrix, dtype=float)
    svol = abs(float(np.linalg.det(smat)))
    s_perp_a = svol / float(np.linalg.norm(np.cross(smat[1], smat[2])))
    s_perp_b = svol / float(np.linalg.norm(np.cross(smat[2], smat[0])))
    s_perp_c = svol / float(np.linalg.norm(np.cross(smat[0], smat[1])))
    min_img_dist = min(s_perp_a, s_perp_b, s_perp_c)
    assert min_img_dist >= 10.0, (
        f"Supercell minimum perpendicular spacing {min_img_dist:.4f} A < 10.0 A for {cid} ({formula})"
    )

    # Remove first occurrence of vac_el to create the explicit neutral vacancy supercell
    removed_idx = None
    for idx_s, site in enumerate(super_struct):
        if site.specie.symbol == vac_el:
            removed_idx = idx_s
            break
    if removed_idx is None:
        raise ValueError(
            f"Vacancy species '{vac_el}' (label '{dom_vac}') is absent from structure of {cid} ({formula})"
        )
    vac_frac = super_struct[removed_idx].frac_coords
    super_struct.remove_sites([removed_idx])

    safe_formula = re.sub(r"[^A-Za-z0-9_]", "", formula).lower()
    safe_el = re.sub(r"[^A-Za-z0-9_]", "", vac_el).lower()
    deck_prefix = f"{safe_formula}_v_{safe_el}"
    if not re.fullmatch(r"[A-Za-z0-9_]+", deck_prefix):
        raise ValueError(f"Invalid QE prefix '{deck_prefix}' for {cid} ({formula})")

    present_species = [el for el in stoich if any(site.specie.symbol == el for site in super_struct)]

    lines = [
        f"! FailSmart-MatEngine Neutral Vacancy Supercell QE Deck ({na}x{nb}x{nc})",
        f"! Candidate: {cid} ({formula}) | Removed Species: {vac_el} | Label: {dom_vac} at frac=({vac_frac[0]:.5f}, {vac_frac[1]:.5f}, {vac_frac[2]:.5f})",
        f"! Supercell sites (with neutral vacancy): {len(super_struct)} (host={n_super}) | d_perp_min = {min_img_dist:.3f} A",
        f"! Point-Charge Image Estimate: E_pc(|q|=1) = {pc_q1:.4f} eV, E_pc(|q|=2) = {pc_q2:.4f} eV",
        f"! Lab Synthesis Batch (10.0 mmol): Target Mass = {target_mass_g:.4f} g at T = {synth['min_synthesis_temp_c']:.1f} C",
        "&CONTROL",
        "  calculation = 'relax',",
        f"  prefix = '{deck_prefix}',",
        "  outdir = './out_defect/',",
        "  pseudo_dir = './pseudo_oncv_fr/',",
        "  tprnfor = .true.,",
        "/",
        "&SYSTEM",
        "  ibrav = 0,",
        f"  nat = {len(super_struct)},",
        f"  ntyp = {len(present_species)},",
        "  ecutwfc = 65.0,",
        "  noncolin = .true.,",
        "  lspinorb = .true.,",
        "/",
        "&ELECTRONS",
        "  conv_thr = 1.0d-7,",
        "/",
        "ATOMIC_SPECIES",
    ]
    for el in present_species:
        lines.append(f"  {el:<3s}  {IUPAC_ATOMIC_MASSES[el]:10.4f}  {el}_ONCV_PBE_FR-1.2.upf")
    lines.append("CELL_PARAMETERS (angstrom)")
    for vec in super_struct.lattice.matrix:
        lines.append(f"  {vec[0]:14.8f}  {vec[1]:14.8f}  {vec[2]:14.8f}")
    lines.append("ATOMIC_POSITIONS (crystal)")
    for site in super_struct:
        fx, fy, fz = site.frac_coords % 1.0
        lines.append(f"  {site.specie.symbol:<3s}  {fx:12.8f}  {fy:12.8f}  {fz:12.8f}")
    lines.append("K_POINTS automatic")
    lines.append("  1 1 1 0 0 0")
    deck_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    blind_9a = independently_verify_phase9a_lab_and_defect_dossier(
        cif_content=cand["cif_content"],
        stoichiometry=stoich,
        eps_static=eps_0,
    )
    ok_9a = bool(
        abs(fu_molar_mass - blind_9a["formula_unit_molar_mass_g_mol"]) <= 1e-4
        and abs(target_mass_g - blind_9a["target_product_mass_g"]) <= 1e-5
        and mass_diff_g <= 1e-6
        and [na, nb, nc] == blind_9a["supercell_dims"]
        and n_super == blind_9a["supercell_total_sites"]
        and abs(min_img_dist - blind_9a["supercell_min_image_dist_ang"]) <= 1e-3
        and abs(pc_q1 - blind_9a["point_charge_image_estimate_ev"]) <= 1e-4
        and abs(pc_q2 - blind_9a["point_charge_image_estimate_q2_ev"]) <= 1e-4
    )
    if not ok_9a:
        raise AssertionError(f"REDUNDANCY_MISMATCH_BLOCK: Phase 9A Lab/Defect mismatch on {cid}")

    t_synth = float(synth["min_synthesis_temp_c"])
    dwell_hr = round(6.0 + max(0.0, (500.0 - t_synth) / 25.0), 1)

    return LabSynthesisAndDefectDossier(
        candidate_id=cid,
        formula_reduced=formula,
        target_layer=str(cand["target_layer"]),
        formula_unit_molar_mass_g_mol=round(fu_molar_mass, 4),
        target_batch_mmol=10.0,
        target_product_mass_g=round(target_mass_g, 5),
        reagent_masses_g=reagent_masses,
        volatile_overpressure_masses_g=volatile_overpressure_masses,
        elemental_mass_conservation_diff_g=round(mass_diff_g, 8),
        synthesis_temperature_c=round(t_synth, 1),
        dwell_time_hours=dwell_hr,
        supercell_dims=[na, nb, nc],
        supercell_total_sites=n_super,
        supercell_min_image_dist_ang=round(min_img_dist, 3),
        dominant_vacancy_element=vac_el,
        dominant_vacancy_species=dom_vac,
        point_charge_image_estimate_ev=round(pc_q1, 4),
        point_charge_image_estimate_q2_ev=round(pc_q2, 4),
        neutral_vacancy_deck_filename=deck_fname,
        redundancy_verified=ok_9a,
        sha256_digest=blind_9a["sha256_digest"],
    )


def compute_abeles_7medium_oblique_sp_tmm(
    wl_nm: np.ndarray,
    e_ev: np.ndarray,
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    d_top_nm: float,
    theta_deg: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute unpolarized (0.5*(s + p)) reflectance & transmittance for the 7-medium Graded-ARC stack at angle theta_deg."""
    wl_um = wl_nm / 1000.0
    n_pts = len(wl_nm)
    theta_rad = math.radians(theta_deg)
    sin_t0 = math.sin(theta_rad)

    n0 = np.full(n_pts, 1.000 + 0.0j, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um**2)).astype(np.complex128)
    n_ito = np.maximum(1.45, 1.92 - 0.085 * (wl_um**2))
    k_ito = 0.0018 + 0.0065 * (wl_um**3)
    n2 = n_ito + 1j * k_ito
    n_tio2 = 2.380 + 0.0180 / (wl_um**2)
    k_tio2 = 0.0004 * (wl_um**2)
    n3 = n_tio2 + 1j * k_tio2

    alpha1 = 1.2e5 * (np.maximum(0.0, e_ev - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, e_ev - eg_dir_1)
    )
    n_act1 = math.sqrt(eps_inf_1) + 0.035 / (wl_um**2)
    k_act1 = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n4 = n_act1 + 1j * k_act1

    n_buf = 1.720 + 0.0040 / (wl_um**2)
    k_buf = 0.0012 * (wl_um**2)
    n5 = n_buf + 1j * k_buf
    n6 = np.full(n_pts, 1.520 + 0.0j, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5, n6]
    d_list_nm = [0.0, 94.0, 80.0, 48.0, float(d_top_nm), 82.0, 0.0]

    cos_list = [np.sqrt(1.0 - ((n0 * sin_t0) / nm) ** 2) for nm in n_list]

    def _solve_pol(pol: str) -> Tuple[np.ndarray, np.ndarray]:
        if pol == "s":
            eta = [n_list[m] * cos_list[m] for m in range(7)]
        else:
            eta = [n_list[m] / cos_list[m] for m in range(7)]

        m_tot = np.zeros((n_pts, 2, 2), dtype=np.complex128)
        m_tot[:, 0, 0] = 1.0
        m_tot[:, 1, 1] = 1.0

        for m in range(6):
            em = eta[m]
            emp1 = eta[m + 1]
            r_m = (em - emp1) / (em + emp1)
            t_m = (2.0 * em) / (em + emp1)

            i_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
            i_mat[:, 0, 0] = 1.0 / t_m
            i_mat[:, 0, 1] = r_m / t_m
            i_mat[:, 1, 0] = r_m / t_m
            i_mat[:, 1, 1] = 1.0 / t_m
            m_tot = np.matmul(m_tot, i_mat)

            if m + 1 <= 5:
                dm = d_list_nm[m + 1]
                beta_m = (2.0 * math.pi * n_list[m + 1] * dm * cos_list[m + 1]) / wl_nm
                p_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
                p_mat[:, 0, 0] = np.exp(-1j * beta_m)
                p_mat[:, 1, 1] = np.exp(1j * beta_m)
                m_tot = np.matmul(m_tot, p_mat)

        r_amp = m_tot[:, 1, 0] / m_tot[:, 0, 0]
        t_amp = 1.0 / m_tot[:, 0, 0]
        r_pow = np.abs(r_amp) ** 2
        t_pow = (np.real(eta[6]) / np.real(eta[0])) * (np.abs(t_amp) ** 2)
        return r_pow, t_pow

    r_s, t_s = _solve_pol("s")
    r_p, t_p = _solve_pol("p")
    r_unpol = 0.5 * (r_s + r_p)
    t_unpol = 0.5 * (t_s + t_p)

    # Effective path length through ITO (80 nm) and TiO2 (48 nm)
    path_ito = 80.0 / np.maximum(0.25, np.real(cos_list[2]))
    path_tio2 = 48.0 / np.maximum(0.25, np.real(cos_list[3]))
    t_win_front = np.exp(-4.0 * math.pi * (k_ito * path_ito + k_tio2 * path_tio2) / wl_nm)

    return r_unpol, t_unpol, t_win_front, alpha1


def evaluate_phase9c_real_world_lcoe_stress_test(
    top_dossier: Dict[str, Any],
    bottom_dossier: Dict[str, Any],
    graded_report: GradedARCTechnoEconomicReport,
) -> RealWorldLCOEStressTestReport:
    """Phase 9C: Evaluate Oblique-Incidence (0-60 deg) S/P TMM, Operating Temp (25-65 C) & 25-Year Arrhenius LCOE."""
    from .independent_verifier import independently_verify_phase9c_oblique_thermal_lcoe

    c_top = top_dossier["candidate"]
    e_top = top_dossier["electronics"]
    o_top = top_dossier["optics"]
    s_top = top_dossier["synthesis"]
    at_top = top_dossier["spring_and_migration_heuristics"]

    c_bot = bottom_dossier["candidate"]
    e_bot = bottom_dossier["electronics"]
    o_bot = bottom_dossier["optics"]
    s_bot = bottom_dossier["synthesis"]
    at_bot = bottom_dossier["spring_and_migration_heuristics"]

    eg_ind_1 = float(e_top["gap_est_indirect_ev"])
    eg_dir_1 = float(e_top["gap_est_direct_ev"])
    eps_inf_1 = float(e_top["eps_inf"])
    d1_nm = float(o_top["film_thickness_nm"])
    d1_m = d1_nm * 1.0e-9

    eg_ind_3 = float(e_bot["gap_est_indirect_ev"])
    eg_dir_3 = float(e_bot["gap_est_direct_ev"])
    eps_inf_3 = float(e_bot["eps_inf"])
    d3_nm = float(o_bot["film_thickness_nm"])
    d3_m = d3_nm * 1.0e-9

    angles = [0.0, 30.0, 45.0, 60.0]
    r_by_angle: Dict[float, float] = {}
    pce_by_angle: Dict[float, float] = {}
    subcell_0deg: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    mask_above = (_AM15G_E_EV >= eg_ind_1) & (_AM15G_E_EV <= 3.50)
    flux_above = float(np.trapezoid(_AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above]))

    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, _AM15G_E_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(np.maximum(0.0, _AM15G_E_EV - 3.40))
    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    t_si_fca_low = np.exp(-0.08 * ((_AM15G_WL_NM / 1200.0) ** 2))

    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, _AM15G_E_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(np.maximum(0.0, _AM15G_E_EV - eg_dir_3))
    fabs3 = (yab3 * alpha3 * d3_m) / (1.0 + yab3 * alpha3 * d3_m)
    a_arc_3 = (1.0 - r_int_23) * fabs3

    for ang in angles:
        r_u, t_u, t_win, alpha1 = compute_abeles_7medium_oblique_sp_tmm(
            wl_nm=_AM15G_WL_NM,
            e_ev=_AM15G_E_EV,
            eg_ind_1=eg_ind_1,
            eg_dir_1=eg_dir_1,
            eps_inf_1=eps_inf_1,
            d_top_nm=d1_nm,
            theta_deg=ang,
        )
        mean_r = float(
            np.trapezoid(r_u[mask_above] * _AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above])
            / max(1.0e-12, flux_above)
            * 100.0
        )
        r_by_angle[ang] = round(mean_r, 2)

        yab1 = 4.0 * eps_inf_1
        fabs1 = (yab1 * alpha1 * d1_m) / (1.0 + yab1 * alpha1 * d1_m)
        a_arc_1 = (1.0 - r_u) * t_win * fabs1
        t_stack_1 = t_u * (1.0 - fabs1)

        _, _, _, eta_top = _solve_cell_iv(a_arc_1, _AM15G_PHI_SUN, eg_dir_1, eg_ind_1)
        phi2 = _AM15G_PHI_SUN * t_stack_1
        _, _, _, eta_si = _solve_cell_iv(0.98 * fabs_si_3l, phi2, 1.12, 1.12, j0_fixed=1.2e-12)
        phi3 = phi2 * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
        _, _, _, eta_bot = _solve_cell_iv(a_arc_3, phi3, eg_dir_3, eg_ind_3)

        pce_by_angle[ang] = round(eta_top + eta_si + eta_bot, 2)
        if ang == 0.0:
            subcell_0deg = (eta_top, eta_si, eta_bot)

    r_hemi = round(
        0.35 * r_by_angle[0.0] + 0.35 * r_by_angle[30.0] + 0.20 * r_by_angle[45.0] + 0.10 * r_by_angle[60.0],
        2,
    )
    iam_60 = round(pce_by_angle[60.0] / max(1e-9, pce_by_angle[0.0]), 4)

    # 2. Field Operating Temperature Coefficient (25 C -> 45 C NOCT -> 65 C Desert Peak)
    eta_top_25, eta_si_25, eta_bot_25 = subcell_0deg
    gamma_top = -0.00440 / (eg_ind_1 ** 0.65)
    gamma_si = -0.00440 / (1.12 ** 0.65)
    gamma_bot = -0.00440 / (eg_ind_3 ** 0.65)

    def _pce_at_temp(tc: float) -> float:
        dt = tc - 25.0
        e_t = eta_top_25 * (1.0 + gamma_top * dt)
        e_s = eta_si_25 * (1.0 + gamma_si * dt)
        e_b = eta_bot_25 * (1.0 + gamma_bot * dt)
        return e_t + e_s + e_b

    pce_25c_raw = eta_top_25 + eta_si_25 + eta_bot_25
    pce_45c_raw = _pce_at_temp(45.0)
    pce_65c_raw = _pce_at_temp(65.0)
    beta_rel_pct_k = ((pce_65c_raw - pce_25c_raw) / (40.0 * pce_25c_raw)) * 100.0

    # 3. 25-Year Arrhenius Ion-Migration Reliability & Real-World LCOE (cents/kWh)
    e_mig_lim = min(float(at_top["emig_heuristic_ev"]), float(at_bot["emig_heuristic_ev"]))
    kb_t_318 = (KB_J * 318.15) / E_CHARGE
    r_deg = 0.0035 + 0.0010 * math.exp(-max(0.0, e_mig_lim - 0.65) / kb_t_318)
    yr25_ret_pct = ((1.0 - r_deg) ** 24) * 100.0

    raw_top = float(s_top["active_layer_cost_usd_m2"])
    raw_bot = float(s_bot["active_layer_cost_usd_m2"])

    def _compute_lcoe_cents_kwh(
        pce_25_pct: float,
        c_mod_usd_m2: float,
        f_noct: float,
        deg_rate: float,
    ) -> float:
        p_m2 = 10.0 * pce_25_pct
        capex_m2 = c_mod_usd_m2 + BOS_AREA_COST_USD_M2 + 0.22 * p_m2
        om_disc = sum(2.50 / ((1.0 + 0.06) ** t) for t in range(1, 26))
        e_disc = sum(
            ((p_m2 / 1000.0) * 1800.0 * f_noct * ((1.0 - deg_rate) ** (t - 1))) / ((1.0 + 0.06) ** t)
            for t in range(1, 26)
        )
        return 100.0 * (capex_m2 + om_disc) / max(1e-9, e_disc)

    f_noct_si = 1.0 + gamma_si * 20.0
    lcoe_si = _compute_lcoe_cents_kwh(22.00, 40.00, f_noct_si, 0.0045)

    # 2-Layer NOCT ratio
    eta_si_2l_25 = graded_report.graded_2layer_pce_percent - round(eta_top_25, 2)
    f_noct_2l = (
        eta_top_25 * (1.0 + gamma_top * 20.0) + eta_si_2l_25 * (1.0 + gamma_si * 20.0)
    ) / max(1e-9, eta_top_25 + eta_si_2l_25)
    c_mod_2l = 40.00 + raw_top + SUBCELL_PROCESS_TCO_COST_USD_M2
    lcoe_2l = _compute_lcoe_cents_kwh(graded_report.graded_2layer_pce_percent, c_mod_2l, f_noct_2l, r_deg)

    # 3-Layer 4T NOCT ratio
    f_noct_3l = pce_45c_raw / max(1e-9, pce_25c_raw)
    c_mod_3l = 40.00 + raw_top + raw_bot + 2.0 * SUBCELL_PROCESS_TCO_COST_USD_M2
    lcoe_3l = _compute_lcoe_cents_kwh(graded_report.graded_4t_low_fca_pce_percent, c_mod_3l, f_noct_3l, r_deg)
    lcoe_red_pct = ((lcoe_si - lcoe_3l) / lcoe_si) * 100.0

    blind_9c = independently_verify_phase9c_oblique_thermal_lcoe(
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        thickness_nm_1=d1_nm,
        eg_ind_3=eg_ind_3,
        eg_dir_3=eg_dir_3,
        eps_inf_3=eps_inf_3,
        thickness_nm_3=d3_nm,
        raw_cost_top_usd_m2=raw_top,
        raw_cost_bot_usd_m2=raw_bot,
        limiting_emig_heuristic_ev=e_mig_lim,
    )

    diff_60 = round(abs(pce_by_angle[60.0] - blind_9c["pce_4t_60deg_25c_percent"]), 4)
    lcoe_ok = bool(
        diff_60 <= 0.05
        and abs(round(lcoe_3l, 4) - blind_9c["lcoe_3layer_4t_cents_kwh"]) <= 0.01
        and abs(round(pce_45c_raw, 2) - blind_9c["pce_4t_noct_45c_percent"]) <= 0.05
    )
    if not lcoe_ok:
        raise AssertionError(
            f"REDUNDANCY_MISMATCH_BLOCK: Phase 9C Oblique/Thermal/LCOE mismatch on {graded_report.pair_id}: "
            f"diff_60={diff_60:.4f}%, lcoe_3l={lcoe_3l:.4f} vs {blind_9c['lcoe_3layer_4t_cents_kwh']:.4f}"
        )

    return RealWorldLCOEStressTestReport(
        pair_id=graded_report.pair_id,
        top_mp_id=c_top["candidate_id"],
        top_formula=c_top["formula_reduced"],
        bottom_mp_id=c_bot["candidate_id"],
        bottom_formula=c_bot["formula_reduced"],
        r_front_0deg_percent=r_by_angle[0.0],
        r_front_30deg_percent=r_by_angle[30.0],
        r_front_45deg_percent=r_by_angle[45.0],
        r_front_60deg_percent=r_by_angle[60.0],
        r_front_hemispheric_percent=r_hemi,
        pce_4t_0deg_25c_percent=pce_by_angle[0.0],
        pce_4t_30deg_25c_percent=pce_by_angle[30.0],
        pce_4t_45deg_25c_percent=pce_by_angle[45.0],
        pce_4t_60deg_25c_percent=pce_by_angle[60.0],
        iam_60deg_ratio=iam_60,
        pce_4t_noct_45c_percent=round(pce_45c_raw, 2),
        pce_4t_desert_65c_percent=round(pce_65c_raw, 2),
        temp_coeff_rel_pct_per_k=round(beta_rel_pct_k, 4),
        limiting_emig_heuristic_ev=round(e_mig_lim, 4),
        annual_degradation_rate_pct_yr=round(r_deg * 100.0, 4),
        year25_retained_power_fraction_percent=round(yr25_ret_pct, 2),
        lcoe_baseline_si_cents_kwh=round(lcoe_si, 4),
        lcoe_2layer_cents_kwh=round(lcoe_2l, 4),
        lcoe_3layer_4t_cents_kwh=round(lcoe_3l, 4),
        lcoe_3layer_vs_si_reduction_percent=round(lcoe_red_pct, 2),
        rouard_oblique_60deg_diff_percent=diff_60,
        lcoe_redundancy_verified=lcoe_ok,
        sha256_digest=blind_9c["sha256_digest"],
    )


def compute_abeles_7medium_custom_tmm(
    wl_nm: np.ndarray,
    e_ev: np.ndarray,
    eg_ind_1: float,
    eg_dir_1: float,
    eps_inf_1: float,
    d_mgf2_nm: float,
    d_tio2_nm: float,
    d_top_nm: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Method A (Section 10.1): Vectorized 2x2 Abeles TMM on 7-Medium Stack with custom (d_MgF2, d_TiO2, d_top)."""
    wl_um = wl_nm / 1000.0
    n_pts = len(wl_nm)

    n0 = np.ones_like(wl_nm, dtype=np.complex128)
    n1 = (1.377 + 0.0032 / (wl_um**2)).astype(np.complex128)

    n_ito_real = np.maximum(1.45, 1.92 - 0.085 * (wl_um**2))
    k_ito = 0.0018 + 0.0065 * (wl_um**3)
    n2 = n_ito_real + 1j * k_ito

    n_tio2_real = 2.380 + 0.0180 / (wl_um**2)
    k_tio2 = 0.0004 * (wl_um**2)
    n3 = n_tio2_real + 1j * k_tio2

    alpha1 = 1.2e5 * (np.maximum(0.0, e_ev - eg_ind_1) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, e_ev - eg_dir_1)
    )
    n_act_real = math.sqrt(eps_inf_1) + 0.035 / (wl_um**2)
    k_act = (alpha1 * (wl_nm * 1.0e-9)) / (4.0 * math.pi)
    n4 = n_act_real + 1j * k_act

    n_buf_real = 1.720 + 0.0040 / (wl_um**2)
    k_buf = 0.0012 * (wl_um**2)
    n5 = n_buf_real + 1j * k_buf
    n6 = np.full_like(wl_nm, 1.520, dtype=np.complex128)

    n_list = [n0, n1, n2, n3, n4, n5, n6]
    d_list_nm = [0.0, float(d_mgf2_nm), 80.0, float(d_tio2_nm), float(d_top_nm), 82.0, 0.0]

    m_tot = np.zeros((n_pts, 2, 2), dtype=np.complex128)
    m_tot[:, 0, 0] = 1.0
    m_tot[:, 1, 1] = 1.0

    for m in range(6):
        nm_curr = n_list[m]
        nm_next = n_list[m + 1]
        r_m = (nm_curr - nm_next) / (nm_curr + nm_next)
        t_m = (2.0 * nm_curr) / (nm_curr + nm_next)

        i_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
        i_mat[:, 0, 0] = 1.0 / t_m
        i_mat[:, 0, 1] = r_m / t_m
        i_mat[:, 1, 0] = r_m / t_m
        i_mat[:, 1, 1] = 1.0 / t_m
        m_tot = np.matmul(m_tot, i_mat)

        if m + 1 <= 5:
            beta = (2.0 * math.pi * n_list[m + 1] * d_list_nm[m + 1]) / wl_nm
            p_mat = np.zeros((n_pts, 2, 2), dtype=np.complex128)
            p_mat[:, 0, 0] = np.exp(-1j * beta)
            p_mat[:, 1, 1] = np.exp(1j * beta)
            m_tot = np.matmul(m_tot, p_mat)

    r_tot = m_tot[:, 1, 0] / m_tot[:, 0, 0]
    t_tot = 1.0 / m_tot[:, 0, 0]

    r_arc_1 = np.abs(r_tot) ** 2
    t_arc_1 = (np.real(n6) / np.real(n0)) * (np.abs(t_tot) ** 2)
    t_win_front = np.exp(-4.0 * math.pi * (k_ito * 80.0 + k_tio2 * float(d_tio2_nm)) / wl_nm)

    return r_arc_1, t_arc_1, t_win_front, alpha1


def evaluate_phase10_bifacial_and_string_dossier(
    top_dossier: Dict[str, Any],
    bottom_dossier: Dict[str, Any],
    pair_id: str,
) -> Phase10BifacialLossAndStringDossier:
    """Phase 10A/10B/10C: Evaluate 2^4=16 Thickness/ARC Optimization, Bifacial Albedo & String Matching."""
    from .independent_verifier import independently_verify_phase10_bifacial_and_string_dossier

    c_top = top_dossier["candidate"]
    e_top = top_dossier["electronics"]
    o_top = top_dossier["optics"]
    s_top = top_dossier["synthesis"]
    at_top = top_dossier["spring_and_migration_heuristics"]

    c_bot = bottom_dossier["candidate"]
    e_bot = bottom_dossier["electronics"]
    o_bot = bottom_dossier["optics"]
    s_bot = bottom_dossier["synthesis"]
    at_bot = bottom_dossier["spring_and_migration_heuristics"]

    eg_ind_1 = float(e_top["gap_est_indirect_ev"])
    eg_dir_1 = float(e_top["gap_est_direct_ev"])
    eps_inf_1 = float(e_top["eps_inf"])
    d1_base = float(o_top["film_thickness_nm"])

    eg_ind_3 = float(e_bot["gap_est_indirect_ev"])
    eg_dir_3 = float(e_bot["gap_est_direct_ev"])
    eps_inf_3 = float(e_bot["eps_inf"])
    d3_base = float(o_bot["film_thickness_nm"])

    raw_top = float(s_top["active_layer_cost_usd_m2"])
    raw_bot = float(s_bot["active_layer_cost_usd_m2"])
    e_mig_lim = min(float(at_top["emig_heuristic_ev"]), float(at_bot["emig_heuristic_ev"]))

    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, _AM15G_E_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(
        np.maximum(0.0, _AM15G_E_EV - 3.40)
    )
    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    t_si_fca_low = np.exp(-0.08 * ((_AM15G_WL_NM / 1200.0) ** 2))

    n3_bot = math.sqrt(eps_inf_3)
    r_int_23 = 0.20 * (((n3_bot - 1.72) / (n3_bot + 1.72)) ** 2)
    yab3 = 4.0 * eps_inf_3
    alpha3 = 1.2e5 * (np.maximum(0.0, _AM15G_E_EV - eg_ind_3) ** 2) + 2.8e7 * np.sqrt(
        np.maximum(0.0, _AM15G_E_EV - eg_dir_3)
    )

    mgf2_grid = [88.0, 94.0]
    tio2_grid = [42.0, 48.0]
    top_grid = [d1_base, round(1.15 * d1_base, 1)]
    bot_grid = [d3_base, round(1.15 * d3_base, 1)]

    best_eta_4t = -1.0
    best_tuple = (94.0, 48.0, d1_base, d3_base)
    photon_ok_all = True

    for d_mgf2 in mgf2_grid:
        for d_tio2 in tio2_grid:
            for d_top in top_grid:
                r_arc_1, t_arc_1, t_win, alpha1 = compute_abeles_7medium_custom_tmm(
                    wl_nm=_AM15G_WL_NM,
                    e_ev=_AM15G_E_EV,
                    eg_ind_1=eg_ind_1,
                    eg_dir_1=eg_dir_1,
                    eps_inf_1=eps_inf_1,
                    d_mgf2_nm=d_mgf2,
                    d_tio2_nm=d_tio2,
                    d_top_nm=d_top,
                )
                yab1 = 4.0 * eps_inf_1
                fabs1 = (yab1 * alpha1 * (d_top * 1.0e-9)) / (1.0 + yab1 * alpha1 * (d_top * 1.0e-9))
                a_arc_1 = (1.0 - r_arc_1) * t_win * fabs1
                t_stack_1 = t_arc_1 * (1.0 - fabs1)
                if float(np.max(a_arc_1 + t_stack_1 + r_arc_1)) > 1.0 + 1.0e-9:
                    photon_ok_all = False

                _, _, _, eta_top = _solve_cell_iv(a_arc_1, _AM15G_PHI_SUN, eg_dir_1, eg_ind_1)
                phi2_front = _AM15G_PHI_SUN * t_stack_1
                _, _, _, eta_si = _solve_cell_iv(
                    0.98 * fabs_si_3l, phi2_front, 1.12, 1.12, j0_fixed=1.2e-12
                )
                phi3_front = phi2_front * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low

                for d_bot in bot_grid:
                    fabs3 = (yab3 * alpha3 * (d_bot * 1.0e-9)) / (
                        1.0 + yab3 * alpha3 * (d_bot * 1.0e-9)
                    )
                    a_arc_3 = (1.0 - r_int_23) * fabs3
                    _, _, _, eta_bot = _solve_cell_iv(a_arc_3, phi3_front, eg_dir_3, eg_ind_3)
                    eta_tot = eta_top + eta_si + eta_bot
                    if eta_tot > best_eta_4t:
                        best_eta_4t = eta_tot
                        best_tuple = (d_mgf2, d_tio2, d_top, d_bot)

    opt_mgf2, opt_tio2, opt_top, opt_bot = best_tuple
    r_arc_1, t_arc_1, t_win, alpha1 = compute_abeles_7medium_custom_tmm(
        wl_nm=_AM15G_WL_NM,
        e_ev=_AM15G_E_EV,
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        d_mgf2_nm=opt_mgf2,
        d_tio2_nm=opt_tio2,
        d_top_nm=opt_top,
    )
    yab1 = 4.0 * eps_inf_1
    fabs1 = (yab1 * alpha1 * (opt_top * 1.0e-9)) / (1.0 + yab1 * alpha1 * (opt_top * 1.0e-9))
    a_arc_1 = (1.0 - r_arc_1) * t_win * fabs1
    t_stack_1 = t_arc_1 * (1.0 - fabs1)

    mask_above = (_AM15G_E_EV >= eg_ind_1) & (_AM15G_E_EV <= 3.50)
    flux_above = float(np.trapezoid(_AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above]))
    opt_r_front = float(
        np.trapezoid(r_arc_1[mask_above] * _AM15G_PHI_SUN[mask_above], _AM15G_WL_NM[mask_above])
        / max(1.0e-12, flux_above)
        * 100.0
    )

    fabs3_opt = (yab3 * alpha3 * (opt_bot * 1.0e-9)) / (1.0 + yab3 * alpha3 * (opt_bot * 1.0e-9))
    a_arc_3_opt = (1.0 - r_int_23) * fabs3_opt

    top_jsc, top_voc, top_ff, eta_top_opt = _solve_cell_iv(
        a_arc_1, _AM15G_PHI_SUN, eg_dir_1, eg_ind_1
    )
    phi2_front = _AM15G_PHI_SUN * t_stack_1
    si_jsc_0, si_voc_0, si_ff_0, eta_si_0 = _solve_cell_iv(
        0.98 * fabs_si_3l, phi2_front, 1.12, 1.12, j0_fixed=1.2e-12
    )
    phi3_front = phi2_front * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_low
    bot_jsc_0, bot_voc_0, bot_ff_0, eta_bot_0 = _solve_cell_iv(
        a_arc_3_opt, phi3_front, eg_dir_3, eg_ind_3
    )
    eta_4t_0 = eta_top_opt + eta_si_0 + eta_bot_0

    # Phase 10B: Bifacial Albedo Harvesting (R_albedo = 0.20 and 0.30)
    def _eval_albedo(r_alb: float) -> float:
        phi_rear = 0.78 * r_alb * _AM15G_PHI_SUN
        phi3_tot = phi3_front + phi_rear
        _, _, _, e_bot_alb = _solve_cell_iv(a_arc_3_opt, phi3_tot, eg_dir_3, eg_ind_3)
        phi2_rear = phi_rear * (1.0 - fabs3_opt) * 0.92
        phi2_tot = phi2_front + phi2_rear
        _, _, _, e_si_alb = _solve_cell_iv(
            0.98 * fabs_si_3l, phi2_tot, 1.12, 1.12, j0_fixed=1.2e-12
        )
        return eta_top_opt + e_si_alb + e_bot_alb

    eta_4t_20 = _eval_albedo(0.20)
    eta_4t_30 = _eval_albedo(0.30)

    p_sqft_20 = 10.0 * eta_4t_20 * SQFT_TO_M2
    p_sqft_30 = 10.0 * eta_4t_30 * SQFT_TO_M2
    bifacial_gain_20 = ((eta_4t_20 - eta_4t_0) / max(1e-9, eta_4t_0)) * 100.0

    # 25-Year Bifacial LCOE at R_albedo = 0.20
    gamma_top = -0.00440 / (eg_ind_1**0.65)
    gamma_si = -0.00440 / (1.12**0.65)
    gamma_bot = -0.00440 / (eg_ind_3**0.65)
    f_noct_3l = (
        eta_top_opt * (1.0 + gamma_top * 20.0)
        + eta_si_0 * (1.0 + gamma_si * 20.0)
        + eta_bot_0 * (1.0 + gamma_bot * 20.0)
    ) / max(1e-9, eta_4t_0)

    kb_t_318 = (KB_J * 318.15) / E_CHARGE
    r_deg = 0.0035 + 0.0010 * math.exp(-max(0.0, e_mig_lim - 0.65) / kb_t_318)

    c_top_opt = raw_top * (opt_top / d1_base)
    c_bot_opt = raw_bot * (opt_bot / d3_base)
    c_mod_3l = 40.00 + c_top_opt + c_bot_opt + 2.0 * SUBCELL_PROCESS_TCO_COST_USD_M2

    p_m2_bif20 = 10.0 * round(eta_4t_20, 2)
    capex_m2 = c_mod_3l + BOS_AREA_COST_USD_M2 + 0.22 * p_m2_bif20
    om_disc = sum(2.50 / ((1.0 + 0.06) ** t) for t in range(1, 26))
    e_disc = sum(
        ((p_m2_bif20 / 1000.0) * 1800.0 * f_noct_3l * ((1.0 - r_deg) ** (t - 1)))
        / ((1.0 + 0.06) ** t)
        for t in range(1, 26)
    )
    lcoe_bif20 = 100.0 * (capex_m2 + om_disc) / max(1e-9, e_disc)

    # Phase 10C: Subcell J-V Operating Point & Integer Parallel-String Voltage Matching
    v_th = 0.02585199
    top_vmp_raw = top_voc - v_th * math.log((top_voc / v_th) + 0.72)
    si_vmp_raw = si_voc_0 - v_th * math.log((si_voc_0 / v_th) + 0.72)
    bot_vmp_raw = bot_voc_0 - v_th * math.log((bot_voc_0 / v_th) + 0.72)

    n_si_ref = 72
    v_bus_si = n_si_ref * si_vmp_raw
    n_top_match = int(round(v_bus_si / top_vmp_raw))
    n_bot_match = int(round(v_bus_si / bot_vmp_raw))

    mismatch_top_pct = abs(n_top_match * top_vmp_raw - v_bus_si) / v_bus_si * 100.0
    mismatch_bot_pct = abs(n_bot_match * bot_vmp_raw - v_bus_si) / v_bus_si * 100.0

    blind_10 = independently_verify_phase10_bifacial_and_string_dossier(
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        thickness_nm_1=d1_base,
        eg_ind_3=eg_ind_3,
        eg_dir_3=eg_dir_3,
        eps_inf_3=eps_inf_3,
        thickness_nm_3=d3_base,
        raw_cost_top_usd_m2=raw_top,
        raw_cost_bot_usd_m2=raw_bot,
        limiting_emig_heuristic_ev=e_mig_lim,
    )

    rouard_opt_diff = round(
        abs(round(eta_4t_0, 2) - blind_10["opt_monofacial_4t_pce_percent"]), 4
    )
    ok_10 = bool(
        photon_ok_all
        and blind_10["photon_conservation_holds"]
        and rouard_opt_diff <= 0.05
        and abs(round(eta_4t_20, 2) - blind_10["bifacial_20pct_albedo_4t_pce_percent"]) <= 0.05
        and abs(round(lcoe_bif20, 4) - blind_10["bifacial_20pct_lcoe_cents_kwh"]) <= 0.01
        and abs(n_top_match - blind_10["n_cells_top_matched"]) <= 1
        and abs(n_bot_match - blind_10["n_cells_bot_matched"]) <= 1
    )
    if not ok_10:
        raise AssertionError(
            f"REDUNDANCY_MISMATCH_BLOCK: Phase 10 mismatch on {pair_id}: "
            f"rouard_opt_diff={rouard_opt_diff:.4f}%, ok_10={ok_10}"
        )

    return Phase10BifacialLossAndStringDossier(
        pair_id=pair_id,
        top_mp_id=c_top["candidate_id"],
        top_formula=c_top["formula_reduced"],
        bottom_mp_id=c_bot["candidate_id"],
        bottom_formula=c_bot["formula_reduced"],
        opt_mgf2_nm=opt_mgf2,
        opt_tio2_nm=opt_tio2,
        opt_top_nm=opt_top,
        opt_bot_nm=opt_bot,
        opt_r_front_percent=round(opt_r_front, 2),
        opt_monofacial_4t_pce_percent=round(eta_4t_0, 2),
        bifacial_20pct_albedo_4t_pce_percent=round(eta_4t_20, 2),
        bifacial_20pct_power_w_sqft=round(p_sqft_20, 2),
        bifacial_30pct_albedo_4t_pce_percent=round(eta_4t_30, 2),
        bifacial_30pct_power_w_sqft=round(p_sqft_30, 2),
        bifacial_20pct_gain_percent=round(bifacial_gain_20, 2),
        bifacial_20pct_lcoe_cents_kwh=round(lcoe_bif20, 4),
        top_jsc_ma_cm2=round(top_jsc, 2),
        top_voc_v=round(top_voc, 4),
        top_ff=round(top_ff, 4),
        top_vmp_v=round(top_vmp_raw, 4),
        si_jsc_ma_cm2=round(si_jsc_0, 2),
        si_voc_v=round(si_voc_0, 4),
        si_ff=round(si_ff_0, 4),
        si_vmp_v=round(si_vmp_raw, 4),
        bot_jsc_ma_cm2=round(bot_jsc_0, 2),
        bot_voc_v=round(bot_voc_0, 4),
        bot_ff=round(bot_ff_0, 4),
        bot_vmp_v=round(bot_vmp_raw, 4),
        n_cells_si_ref=n_si_ref,
        n_cells_top_matched=n_top_match,
        n_cells_bot_matched=n_bot_match,
        v_bus_si_v=round(v_bus_si, 2),
        top_string_mismatch_percent=round(mismatch_top_pct, 2),
        bot_string_mismatch_percent=round(mismatch_bot_pct, 2),
        rouard_opt_diff_percent=rouard_opt_diff,
        phase10_redundancy_verified=ok_10,
        sha256_digest=blind_10["sha256_digest"],
    )



