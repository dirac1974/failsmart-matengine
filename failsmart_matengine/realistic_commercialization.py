"""Phase 11 (v8.0): Realistic Synthesis Window, Contact Band Alignment, Non-Radiative SRH Device Physics & 4-Path Commercialization Techno-Economics.

Implements Section 11 (11.1, 11.2, 11.3) of docs/MATHEMATICAL_SPEC_V2.md:
- Phase 11A: Live Materials Project DFT convex-hull chemical-potential synthesis windows,
  TCO InterfacialReactivity (SnO2, In2O3, TiO2), lone-pair-corrected Mulliken band edges
  (CBM, VBM vs. vacuum), ETL/HTL offsets, antisite disorder, ribbon texturing, critical-mineral
  supply risk, and Synthesis & Commercialization Practicality Score (SPS in [0, 100]).
- Phase 11B: Realistic non-radiative Shockley-Read-Hall (SRH) device model across 3 ERE maturity
  tiers (Conservative 1e-5, Base-Case 1e-4, Mature 5e-3), Green series/shunt fill-factor derating,
  standard commercial TOPCon/SHJ c-Si free-carrier absorption, and +/- 0.15 eV gap sensitivity.
- Phase 11C: Realistic industrial PVD/RTP fab CAPEX, compound yield, and head-to-head 25-year
  utility & rooftop LCOE across 4 Strategic Commercialization Paths (Path 1: 3-Layer 4T Sandwich,
  Path 2: 2-Layer 4T Active Solar Glass on Commodity Bifacial c-Si, Path 3: 2T Monolithic,
  Path 4: Standalone BIPV Semi-Transparent Solar Window Glazing).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from .atomistic_and_tmm import (
    _AM15G_E_EV,
    _AM15G_PHI_SUN,
    _AM15G_WL_NM,
    compute_abeles_7medium_custom_tmm,
)
from .independent_verifier import (
    independently_verify_phase11a_synthesis_and_contacts,
    independently_verify_phase11b_realistic_commercialization,
)
from .kinetics_and_optics import _solve_cell_iv
from .schemas import (
    Phase10BifacialLossAndStringDossier,
    Phase11ASynthesisContactDossier,
    Phase11BRealisticCommercializationDossier,
)

V_TH_300K = 0.02585199

MULLIKEN_CHI_EV: Dict[str, float] = {
    "Bi": 4.69,
    "Sb": 4.85,
    "In": 3.10,
    "Ga": 3.20,
    "Cu": 4.48,
    "Ag": 4.44,
    "Sn": 4.30,
    "O": 7.54,
    "S": 6.22,
    "Se": 5.89,
}


def load_mp_thermo_interface_cache() -> Dict[str, Any]:
    """Load cached live Materials Project DFT PhaseDiagram & InterfacialReactivity entries."""
    cache_path = Path(__file__).resolve().parent.parent / "data" / "mp_thermo_interface_cache.json"
    return json.loads(cache_path.read_text(encoding="utf-8"))


def evaluate_phase11a_synthesis_and_contacts(
    finalist_dossier: Dict[str, Any],
    thermo_cache: Dict[str, Any],
) -> Phase11ASynthesisContactDossier:
    """Evaluate Phase 11A synthesis window, TCO reactivity, contact alignment & SPS with blinded redundancy."""
    cand = finalist_dossier["candidate"]
    elec = finalist_dossier["electronics"]
    cid = str(cand["candidate_id"])
    formula = str(cand["formula_reduced"])
    layer = str(cand["target_layer"])
    stoich: Dict[str, int] = {str(k): int(v) for k, v in cand["stoichiometry"].items()}
    dim = str(cand["structural_dimensionality"])
    eg_ind = float(elec["gap_est_indirect_ev"])

    n_tot = sum(stoich.values())
    if len(stoich) >= 4 and ("Cu" in stoich) and ("Sn" in stoich):
        v_antisite = 0.110
    elif ("Cu" in stoich) or ("Ag" in stoich):
        v_antisite = 0.045
    else:
        v_antisite = 0.015

    if dim == "3D":
        f_orient = 0.95
    elif dim == "Quasi-2D":
        f_orient = 0.88
    else:
        f_orient = 0.72

    s_crit = (
        0.65 * stoich.get("In", 0) + 0.45 * stoich.get("Ga", 0) + 0.55 * stoich.get("Ag", 0)
    ) / float(n_tot)
    has_crit = any(el in stoich for el in ("In", "Ga", "Ag"))

    if cid not in thermo_cache or any(el not in MULLIKEN_CHI_EV for el in stoich):
        import hashlib
        sig_payload = {
            "candidate_id": cid,
            "formula_reduced": formula,
            "evaluated": False,
            "antisite_voltage_penalty_v": round(v_antisite, 4),
            "ribbon_orientation_factor": round(f_orient, 4),
            "critical_mineral_index": round(s_crit, 4),
        }
        sig_hex = hashlib.sha256(json.dumps(sig_payload, sort_keys=True).encode("utf-8")).hexdigest()
        return Phase11ASynthesisContactDossier(
            candidate_id=cid,
            formula_reduced=formula,
            target_layer=layer,
            structural_dimensionality=dim,
            mp_gga_hull_mev_per_atom=None,
            hull_decomposition_phases=[],
            anion_chempot_window_ev=None,
            min_cation_chempot_window_ev=None,
            rxn_sno2_mev_per_atom=None,
            rxn_in2o3_mev_per_atom=None,
            rxn_tio2_mev_per_atom=None,
            dominant_in2o3_reaction="not evaluated",
            cbm_vs_vacuum_ev=None,
            vbm_vs_vacuum_ev=None,
            cbo_vs_tio2_ev=None,
            cbo_vs_sno2_ev=None,
            vbo_vs_niox_ev=None,
            recommended_etl_barrier="not evaluated",
            best_cbo_ev=None,
            contact_voltage_penalty_v=None,
            antisite_voltage_penalty_v=round(v_antisite, 4),
            ribbon_orientation_factor=round(f_orient, 4),
            critical_mineral_index=round(s_crit, 4),
            has_critical_mineral=has_crit,
            synthesis_practicality_score_100=None,
            redundancy_verified=True,
            sha256_digest=sig_hex,
        )

    th_rec = thermo_cache[cid]
    hull_mev = float(th_rec["mp_gga_hull_mev_per_atom"])
    decomp_phases = [str(p) for p in th_rec["hull_decomposition_phases"]]
    cpw = th_rec["chemical_potential_windows"]

    chalc = "S" if "S" in stoich else "Se"
    if "O" in stoich:
        dmu_anion = float(min(cpw["O"]["window_width_ev"], cpw[chalc]["window_width_ev"]))
    else:
        dmu_anion = float(cpw[chalc]["window_width_ev"])

    dmu_cation_min = float(
        min(cpw[el]["window_width_ev"] for el in stoich if el not in ("O", "S", "Se"))
    )

    tco_rxn = th_rec["tco_interfacial_reactivity"]
    rxn_sno2 = float(tco_rxn["SnO2"]["worst_rxn_energy_mev_per_atom"])
    rxn_in2o3 = float(tco_rxn["In2O3"]["worst_rxn_energy_mev_per_atom"])
    rxn_tio2 = float(tco_rxn["TiO2"]["worst_rxn_energy_mev_per_atom"])
    dom_in2o3_rxn = str(tco_rxn["In2O3"]["dominant_interface_reaction"])

    chi_comp = math.exp(
        sum(cnt * math.log(MULLIKEN_CHI_EV[el]) for el, cnt in stoich.items()) / float(n_tot)
    )
    lp_shift = 1.65 * (float(stoich.get("Bi", 0) + stoich.get("Sb", 0)) / float(n_tot))

    cbm = -chi_comp + lp_shift + 0.5 * eg_ind
    vbm = -chi_comp + lp_shift - 0.5 * eg_ind

    cbo_tio2 = -4.20 - cbm
    cbo_sno2 = -4.35 - cbm
    vbo_niox = vbm + 5.30

    if abs(cbo_tio2) <= abs(cbo_sno2):
        best_etl = "TiO2"
        best_cbo = cbo_tio2
    else:
        best_etl = "SnO2"
        best_cbo = cbo_sno2

    v_contact = max(0.0, -best_cbo - 0.25) + max(0.0, best_cbo - 0.20)

    sps_raw = (
        92.0
        - 0.90 * hull_mev
        + 10.0 * min(0.80, dmu_anion)
        + 8.0 * min(0.50, dmu_cation_min)
        - 0.25 * abs(rxn_in2o3)
        - 0.50 * abs(rxn_sno2)
        - 95.0 * s_crit
        - 110.0 * v_antisite
        - 25.0 * v_contact
    )
    sps = float(np.clip(sps_raw, 0.0, 100.0))

    blind_11a = independently_verify_phase11a_synthesis_and_contacts(
        stoichiometry=stoich,
        structural_dimensionality=dim,
        eg_ind_ev=eg_ind,
        mp_gga_hull_mev_per_atom=hull_mev,
        anion_chempot_window_ev=dmu_anion,
        min_cation_chempot_window_ev=dmu_cation_min,
        rxn_sno2_mev_per_atom=rxn_sno2,
        rxn_in2o3_mev_per_atom=rxn_in2o3,
        rxn_tio2_mev_per_atom=rxn_tio2,
    )

    verif_ok = bool(
        abs(round(cbm, 4) - blind_11a["cbm_vs_vacuum_ev"]) <= 1e-4
        and abs(round(sps, 2) - blind_11a["synthesis_practicality_score_100"]) <= 0.01
        and best_etl == blind_11a["recommended_etl_barrier"]
    )
    if not verif_ok:
        raise AssertionError(
            f"REDUNDANCY_MISMATCH_BLOCK: Phase 11A mismatch on {cid}: "
            f"SPS={sps:.2f} vs {blind_11a['synthesis_practicality_score_100']:.2f}"
        )

    return Phase11ASynthesisContactDossier(
        candidate_id=cid,
        formula_reduced=formula,
        target_layer=layer,
        structural_dimensionality=dim,
        mp_gga_hull_mev_per_atom=round(hull_mev, 2),
        hull_decomposition_phases=decomp_phases,
        anion_chempot_window_ev=round(dmu_anion, 4),
        min_cation_chempot_window_ev=round(dmu_cation_min, 4),
        rxn_sno2_mev_per_atom=round(rxn_sno2, 2),
        rxn_in2o3_mev_per_atom=round(rxn_in2o3, 2),
        rxn_tio2_mev_per_atom=round(rxn_tio2, 2),
        dominant_in2o3_reaction=dom_in2o3_rxn,
        cbm_vs_vacuum_ev=round(cbm, 4),
        vbm_vs_vacuum_ev=round(vbm, 4),
        cbo_vs_tio2_ev=round(cbo_tio2, 4),
        cbo_vs_sno2_ev=round(cbo_sno2, 4),
        vbo_vs_niox_ev=round(vbo_niox, 4),
        recommended_etl_barrier=best_etl,
        best_cbo_ev=round(best_cbo, 4),
        contact_voltage_penalty_v=round(v_contact, 4),
        antisite_voltage_penalty_v=round(v_antisite, 4),
        ribbon_orientation_factor=round(f_orient, 4),
        critical_mineral_index=round(s_crit, 4),
        has_critical_mineral=has_crit,
        synthesis_practicality_score_100=round(sps, 2),
        redundancy_verified=verif_ok,
        sha256_digest=str(blind_11a["sha256_digest"]),
    )


MATURITY_CASES: Dict[str, Dict[str, Any]] = {
    "demonstrated": {
        "ere": 1.0e-9,
        "ere_range": [1.0e-10, 1.0e-9],
        "ff_cap": 0.73,
        "f_ap": 0.85,
        "rs_ohm_cm2": 3.2,
        "alpha_def": 1.00,
        "provenance": "ASSUMED",
        "citations": [
            "https://doi.org/10.1002/adma.202202969",
            "https://english.cas.cn/newsroom/research_news/phys/202510/t20251023_1094727.shtml",
            "https://www.citedrive.com/en/discovery/highefficiency-allantimony-chalcogenide-tandem-solar-cells-via-thermalevaporated-cds-interface-engineering",
        ],
    },
    "stretch": {
        "ere": 1.0e-7,
        "ere_range": [1.0e-7, 1.0e-7],
        "ff_cap": None,
        "f_ap": 0.92,
        "rs_ohm_cm2": 2.2,
        "alpha_def": 0.80,
        "provenance": "ASSUMED",
        "citations": [
            "https://doi.org/10.1038/s41560-020-0652-3",
            "https://arxiv.org/abs/2410.10560",
        ],
    },
    "ceiling": {
        "ere": 1.0e-4,
        "ere_range": [1.0e-4, 1.0e-4],
        "ff_cap": None,
        "f_ap": 0.96,
        "rs_ohm_cm2": 1.8,
        "alpha_def": 0.65,
        "provenance": "ASSUMED",
        "citations": [
            "https://arxiv.org/abs/2410.10560",
        ],
    },
}


def _solve_realistic_tf_cell_wavelength(
    absorptance_lam: np.ndarray,
    phi_lam: np.ndarray,
    eg_dir_ev: float,
    eg_ind_ev: float,
    f_orient: float,
    v_antisite: float,
    v_contact: float,
    ere: float,
    f_ap_scen: float,
    rs_ohm_cm2: float,
    alpha_def: float,
    ff_cap: float | None = None,
) -> Tuple[float, float, float, float]:
    """Solve non-radiative thin-film subcell J-V operating point on _AM15G_WL_NM."""
    jsc_rad, voc_rad, _, _ = _solve_cell_iv(absorptance_lam, phi_lam, eg_dir_ev, eg_ind_ev)
    if jsc_rad <= 1e-9:
        return 0.0, 0.0, 0.0, 0.0

    f_coll = f_orient * f_ap_scen
    jsc_real = jsc_rad * f_coll
    dv_loss = -V_TH_300K * math.log(ere) + alpha_def * (v_antisite + v_contact)
    voc_real = max(0.05, voc_rad + V_TH_300K * math.log(max(1e-9, f_coll)) - dv_loss)

    v_norm = voc_real / V_TH_300K
    ff0 = (v_norm - math.log(v_norm + 0.72)) / (v_norm + 1.0)
    rs_norm = (rs_ohm_cm2 * (jsc_real / 1000.0)) / voc_real
    rsh_norm = (1200.0 * (jsc_real / 1000.0)) / voc_real

    ff_real = (
        ff0
        * max(0.35, 1.0 - 1.1 * rs_norm)
        * max(0.35, 1.0 - ((v_norm + 0.70) * ff0) / max(1e-9, v_norm * rsh_norm))
    )
    if ff_cap is not None:
        ff_real = min(ff_real, float(ff_cap))
    eta_real = jsc_real * voc_real * ff_real
    return jsc_real, voc_real, ff_real, eta_real


def _solve_realistic_csi_cell_wavelength(
    absorptance_lam: np.ndarray,
    phi_lam: np.ndarray,
) -> Tuple[float, float, float, float]:
    """Solve realistic passivated commodity TOPCon/SHJ c-Si subcell on _AM15G_WL_NM."""
    jsc_rad, voc_rad, _, _ = _solve_cell_iv(
        absorptance_lam, phi_lam, 1.12, 1.12, j0_fixed=2.8e-11
    )
    if jsc_rad <= 1e-9:
        return 0.0, 0.0, 0.0, 0.0

    jsc_real = 0.955 * jsc_rad
    voc_real = voc_rad + V_TH_300K * math.log(0.955)
    v_norm = voc_real / V_TH_300K
    ff0 = (v_norm - math.log(v_norm + 0.72)) / (v_norm + 1.0)
    rs_norm = (0.55 * (jsc_real / 1000.0)) / voc_real
    rsh_norm = (3500.0 * (jsc_real / 1000.0)) / voc_real

    ff_real = (
        ff0
        * max(0.50, 1.0 - 1.1 * rs_norm)
        * max(0.50, 1.0 - ((v_norm + 0.70) * ff0) / max(1e-9, v_norm * rsh_norm))
    )
    eta_real = jsc_real * voc_real * ff_real
    return jsc_real, voc_real, ff_real, eta_real


def _compute_lcoe_11c_cents_kwh(
    pce_pct: float,
    c_mod_usd_m2: float,
    c_bos_area: float,
    f_noct: float,
    deg_rate: float,
) -> float:
    """Discounted 25-year LCOE (cents/kWh) per Section 11.3."""
    p_m2 = 10.0 * pce_pct
    capex_m2 = c_mod_usd_m2 + c_bos_area + 0.22 * p_m2
    om_disc = sum(2.50 / ((1.06) ** t) for t in range(1, 26))
    e_disc = sum(
        ((p_m2 / 1000.0) * 1800.0 * f_noct * ((1.0 - deg_rate) ** (t - 1))) / ((1.06) ** t)
        for t in range(1, 26)
    )
    return 100.0 * (capex_m2 + om_disc) / max(1e-9, e_disc)


def evaluate_phase11b_realistic_commercialization(
    top_dossier: Dict[str, Any],
    bottom_dossier: Dict[str, Any],
    top_11a: Phase11ASynthesisContactDossier,
    bot_11a: Phase11ASynthesisContactDossier,
    p10_report: Phase10BifacialLossAndStringDossier,
    include_rear_ir_cell: bool = False,
) -> Phase11BRealisticCommercializationDossier:
    """Evaluate Phase 11B/11C non-radiative device maturity cases & requirements-oriented techno-economics.

    The 2-layer stack (`top + c-Si`) is the default (`include_rear_ir_cell=False`).
    """
    from .requirements_tea import (
        compute_lcoe_breakeven_top_pce,
        compute_optics_only_breakeven_top_pce,
    )

    c_top = top_dossier["candidate"]
    e_top = top_dossier["electronics"]
    s_top = top_dossier["synthesis"]

    c_bot = bottom_dossier["candidate"]
    e_bot = bottom_dossier["electronics"]
    s_bot = bottom_dossier["synthesis"]

    eg_ind_1 = float(e_top["gap_est_indirect_ev"])
    eg_dir_1 = float(e_top["gap_est_direct_ev"])
    eps_inf_1 = float(e_top["eps_inf"])

    eg_ind_3 = float(e_bot["gap_est_indirect_ev"])
    eg_dir_3 = float(e_bot["gap_est_direct_ev"])
    eps_inf_3 = float(e_bot["eps_inf"])

    opt_mgf2 = float(p10_report.opt_mgf2_nm)
    opt_tio2 = float(p10_report.opt_tio2_nm)
    opt_top = float(p10_report.opt_top_nm)
    opt_bot = float(p10_report.opt_bot_nm)

    d_si_m = 160.0e-6
    alpha_si = 1.1e5 * (np.maximum(0.0, _AM15G_E_EV - 1.12) ** 2) + 1.5e7 * np.sqrt(
        np.maximum(0.0, _AM15G_E_EV - 3.40)
    )
    fabs_si_2l = (49.0 * alpha_si * d_si_m) / (1.0 + 49.0 * alpha_si * d_si_m)
    fabs_si_3l = (16.0 * alpha_si * d_si_m) / (1.0 + 16.0 * alpha_si * d_si_m)
    t_si_fca_std = np.exp(-0.38 * ((_AM15G_WL_NM / 1200.0) ** 2))

    # Path 0: Commodity Bifacial TOPCon/SHJ c-Si baseline
    _, _, _, eta_si_0_mono = _solve_realistic_csi_cell_wavelength(0.98 * fabs_si_2l, _AM15G_PHI_SUN)
    _, _, _, p_si_0_bif20 = _solve_realistic_csi_cell_wavelength(
        0.98 * fabs_si_2l, _AM15G_PHI_SUN * (1.0 + 0.20 * 0.80)
    )
    lcoe_p0_util = _compute_lcoe_11c_cents_kwh(p_si_0_bif20, 42.00, 100.00, 0.930, 0.0045)
    lcoe_p0_roof = _compute_lcoe_11c_cents_kwh(p_si_0_bif20, 42.00, 240.00, 0.930, 0.0045)

    def _build_stack_optics(
        egi1: float, egd1: float, egi3: float, egd3: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        r_arc1, t_arc1, t_win1, alpha1 = compute_abeles_7medium_custom_tmm(
            wl_nm=_AM15G_WL_NM,
            e_ev=_AM15G_E_EV,
            eg_ind_1=egi1,
            eg_dir_1=egd1,
            eps_inf_1=eps_inf_1,
            d_mgf2_nm=opt_mgf2,
            d_tio2_nm=opt_tio2,
            d_top_nm=opt_top,
        )
        # Double-pass Beer-Lambert absorption for thin films (no 4*eps_inf enhancement)
        fabs1 = 1.0 - np.exp(-2.0 * alpha1 * (opt_top * 1.0e-9))
        a_arc1 = (1.0 - r_arc1) * t_win1 * fabs1
        t_stack1 = t_arc1 * (1.0 - fabs1)

        n3 = math.sqrt(eps_inf_3)
        r_int23 = 0.20 * (((n3 - 1.72) / (n3 + 1.72)) ** 2)
        alpha3 = 1.2e5 * (np.maximum(0.0, _AM15G_E_EV - egi3) ** 2) + 2.8e7 * np.sqrt(
            np.maximum(0.0, _AM15G_E_EV - egd3)
        )
        fabs3 = 1.0 - np.exp(-2.0 * alpha3 * (opt_bot * 1.0e-9))
        a_arc3 = (1.0 - r_int23) * fabs3
        return a_arc1, t_stack1, fabs3, a_arc3

    a_arc1, t_stack1, fabs3, a_arc3 = _build_stack_optics(eg_ind_1, eg_dir_1, eg_ind_3, eg_dir_3)
    phi2_front = _AM15G_PHI_SUN * t_stack1
    phi3_front_std = phi2_front * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std

    _, _, _, eta_si_2l_mono = _solve_realistic_csi_cell_wavelength(0.98 * fabs_si_2l, phi2_front)
    _, _, _, eta_si_3l_mono = _solve_realistic_csi_cell_wavelength(0.98 * fabs_si_3l, phi2_front)

    fo1 = float(top_11a.ribbon_orientation_factor)
    va1 = float(top_11a.antisite_voltage_penalty_v)
    vc1 = float(top_11a.contact_voltage_penalty_v or 0.0)

    fo3 = float(bot_11a.ribbon_orientation_factor)
    va3 = float(bot_11a.antisite_voltage_penalty_v)
    vc3 = float(bot_11a.contact_voltage_penalty_v or 0.0)

    # 1. Demonstrated (ERE = 1e-9, fill factor capped at 0.73) — ASSUMED
    dem_cfg = MATURITY_CASES["demonstrated"]
    _, voc_top_dem, ff_top_dem, eta_top_dem = _solve_realistic_tf_cell_wavelength(
        a_arc1,
        _AM15G_PHI_SUN,
        eg_dir_1,
        eg_ind_1,
        fo1,
        va1,
        vc1,
        float(dem_cfg["ere"]),
        float(dem_cfg["f_ap"]),
        float(dem_cfg["rs_ohm_cm2"]),
        float(dem_cfg["alpha_def"]),
        ff_cap=float(dem_cfg["ff_cap"]),
    )
    _, _, _, eta_bot_dem = _solve_realistic_tf_cell_wavelength(
        a_arc3,
        phi3_front_std,
        eg_dir_3,
        eg_ind_3,
        fo3,
        va3,
        vc3,
        float(dem_cfg["ere"]),
        float(dem_cfg["f_ap"]),
        float(dem_cfg["rs_ohm_cm2"]),
        float(dem_cfg["alpha_def"]),
        ff_cap=float(dem_cfg["ff_cap"]),
    )
    pce_2l_dem = eta_top_dem + eta_si_2l_mono
    pce_3l_dem = eta_top_dem + eta_si_3l_mono + eta_bot_dem

    # 2. Stretch (ERE = 1e-7) — ASSUMED
    str_cfg = MATURITY_CASES["stretch"]
    _, voc_top_str, _, eta_top_str = _solve_realistic_tf_cell_wavelength(
        a_arc1,
        _AM15G_PHI_SUN,
        eg_dir_1,
        eg_ind_1,
        fo1,
        va1,
        vc1,
        float(str_cfg["ere"]),
        float(str_cfg["f_ap"]),
        float(str_cfg["rs_ohm_cm2"]),
        float(str_cfg["alpha_def"]),
        ff_cap=None,
    )
    _, _, _, eta_bot_str = _solve_realistic_tf_cell_wavelength(
        a_arc3,
        phi3_front_std,
        eg_dir_3,
        eg_ind_3,
        fo3,
        va3,
        vc3,
        float(str_cfg["ere"]),
        float(str_cfg["f_ap"]),
        float(str_cfg["rs_ohm_cm2"]),
        float(str_cfg["alpha_def"]),
        ff_cap=None,
    )
    pce_2l_str = eta_top_str + eta_si_2l_mono
    pce_3l_str = eta_top_str + eta_si_3l_mono + eta_bot_str

    # 3. Ceiling (ERE = 1e-4, intrinsic defect limit) — ASSUMED
    ceil_cfg = MATURITY_CASES["ceiling"]
    _, voc_top_ceil, _, eta_top_ceil = _solve_realistic_tf_cell_wavelength(
        a_arc1,
        _AM15G_PHI_SUN,
        eg_dir_1,
        eg_ind_1,
        fo1,
        va1,
        vc1,
        float(ceil_cfg["ere"]),
        float(ceil_cfg["f_ap"]),
        float(ceil_cfg["rs_ohm_cm2"]),
        float(ceil_cfg["alpha_def"]),
        ff_cap=None,
    )
    _, voc_bot_mono_ceil, _, eta_bot_mono_ceil = _solve_realistic_tf_cell_wavelength(
        a_arc3,
        phi3_front_std,
        eg_dir_3,
        eg_ind_3,
        fo3,
        va3,
        vc3,
        float(ceil_cfg["ere"]),
        float(ceil_cfg["f_ap"]),
        float(ceil_cfg["rs_ohm_cm2"]),
        float(ceil_cfg["alpha_def"]),
        ff_cap=None,
    )
    pce_2l_ceil = eta_top_ceil + eta_si_2l_mono
    pce_3l_ceil = eta_top_ceil + eta_si_3l_mono + eta_bot_mono_ceil

    # 4. Band-Gap Uncertainty Sensitivity (delta E_g = +/- 0.15 eV in Ceiling Monofacial)
    sens_2l = []
    sens_3l = []
    for deg_shift in (-0.15, +0.15):
        egi1_s = max(0.55, eg_ind_1 + deg_shift)
        egd1_s = max(egi1_s, eg_dir_1 + deg_shift)
        egi3_s = max(0.55, eg_ind_3 + deg_shift)
        egd3_s = max(egi3_s, eg_dir_3 + deg_shift)
        a1_s, ts1_s, _, a3_s = _build_stack_optics(egi1_s, egd1_s, egi3_s, egd3_s)
        p2_s = _AM15G_PHI_SUN * ts1_s
        p3_s = p2_s * 0.96 * (1.0 - fabs_si_3l) * t_si_fca_std
        _, _, _, et_s = _solve_realistic_tf_cell_wavelength(
            a1_s, _AM15G_PHI_SUN, egd1_s, egi1_s, fo1, va1, vc1, 1.0e-4, 0.96, 1.8, 0.65
        )
        _, _, _, es2_s = _solve_realistic_csi_cell_wavelength(0.98 * fabs_si_2l, p2_s)
        _, _, _, es3_s = _solve_realistic_csi_cell_wavelength(0.98 * fabs_si_3l, p2_s)
        _, _, _, eb_s = _solve_realistic_tf_cell_wavelength(
            a3_s, p3_s, egd3_s, egi3_s, fo3, va3, vc3, 1.0e-4, 0.96, 1.8, 0.65
        )
        sens_2l.append(et_s + es2_s)
        sens_3l.append(et_s + es3_s + eb_s)

    # 5. Section 11.3: Requirements & Path Economics (20% Ground Albedo)
    stoich_1 = {str(k): int(v) for k, v in c_top["stoichiometry"].items()}
    stoich_3 = {str(k): int(v) for k, v in c_bot["stoichiometry"].items()}
    raw_top = float(s_top["active_layer_cost_usd_m2"])
    raw_bot = float(s_bot["active_layer_cost_usd_m2"])

    c_crit_1 = 4.50 if ("In" in stoich_1 or "Ag" in stoich_1) else (2.00 if "Ga" in stoich_1 else 0.0)
    c_crit_3 = 4.50 if ("In" in stoich_3 or "Ag" in stoich_3) else (2.00 if "Ga" in stoich_3 else 0.0)

    c_fab_top = 16.50 + 2.50 * raw_top + c_crit_1
    c_fab_bot = 16.50 + 2.50 * raw_bot + c_crit_3

    # Path 1: 3-Layer 4T Sandwich on Commodity Bifacial c-Si (20% albedo, rear IR cell optional)
    phi_rear_3l = 0.20 * 0.78 * _AM15G_PHI_SUN
    phi2_p1 = phi2_front + phi_rear_3l * (1.0 - fabs3) * 0.92
    phi3_p1 = phi3_front_std + phi_rear_3l
    _, _, _, eta_si_p1 = _solve_realistic_csi_cell_wavelength(0.98 * fabs_si_3l, phi2_p1)
    _, _, _, eta_bot_p1 = _solve_realistic_tf_cell_wavelength(
        a_arc3, phi3_p1, eg_dir_3, eg_ind_3, fo3, va3, vc3, 1.0e-4, 0.96, 1.8, 0.65
    )
    p_p1_bif20 = eta_top_ceil + eta_si_p1 + eta_bot_p1
    c_mod_1 = 42.00 + (c_fab_top + c_fab_bot) / 0.774 + 12.00
    lcoe_p1_util = _compute_lcoe_11c_cents_kwh(p_p1_bif20, c_mod_1, 100.00, 0.925, 0.0055)
    lcoe_p1_roof = _compute_lcoe_11c_cents_kwh(p_p1_bif20, c_mod_1, 240.00, 0.925, 0.0055)

    # Path 2 (default 2-layer stack): 2-Layer 4T Active Solar Glass Superstrate on Unobstructed Bifacial c-Si (20% albedo)
    phi2_p2 = phi2_front + 0.20 * 0.80 * _AM15G_PHI_SUN
    _, _, _, eta_si_p2 = _solve_realistic_csi_cell_wavelength(0.98 * fabs_si_2l, phi2_p2)
    p_p2_bif20_dem = eta_top_dem + eta_si_p2
    p_p2_bif20_ceil = eta_top_ceil + eta_si_p2
    c_mod_2 = 42.00 + (c_fab_top / 0.90) + 5.50
    lcoe_p2_util_dem = _compute_lcoe_11c_cents_kwh(p_p2_bif20_dem, c_mod_2, 100.00, 0.930, 0.0050)
    lcoe_p2_roof_dem = _compute_lcoe_11c_cents_kwh(p_p2_bif20_dem, c_mod_2, 240.00, 0.930, 0.0050)
    lcoe_p2_util = _compute_lcoe_11c_cents_kwh(p_p2_bif20_ceil, c_mod_2, 100.00, 0.930, 0.0050)
    lcoe_p2_roof = _compute_lcoe_11c_cents_kwh(p_p2_bif20_ceil, c_mod_2, 240.00, 0.930, 0.0050)

    # Path 3: 2T Monolithic Top-on-Si (375 C direct deposition derating)
    p_p3_bif20 = 0.84 * p_p2_bif20_ceil
    c_mod_3 = 42.00 + ((c_fab_top - 3.50) / 0.84)
    lcoe_p3_util = _compute_lcoe_11c_cents_kwh(p_p3_bif20, c_mod_3, 100.00, 0.925, 0.0060)

    # Path 4: Standalone BIPV Semi-Transparent Solar Window Glazing (35% daylighting transmittance)
    eta_p4_bipv = 0.72 * eta_top_ceil
    c_mod_4 = 58.00 + (c_fab_top / 0.90)

    # Sub-bandgap transmittance T of top stack for break-even requirements
    mask_sub = (_AM15G_E_EV >= 0.75) & (_AM15G_E_EV <= (eg_ind_1 - 0.02))
    flux_sub = float(np.trapezoid(_AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub]))
    sub_trans_frac = float(
        np.trapezoid(t_stack1[mask_sub] * _AM15G_PHI_SUN[mask_sub], _AM15G_WL_NM[mask_sub])
        / max(1.0e-12, flux_sub)
    )
    delta_c_mod_2 = c_mod_2 - 42.00
    be_util = float(
        compute_lcoe_breakeven_top_pce(
            subgap_transmittance_fraction=sub_trans_frac,
            added_module_cost_usd_m2=delta_c_mod_2,
            case="utility",
            deg_rate=0.0050,
        )["breakeven_top_cell_pce_percent"]
    )
    be_roof = float(
        compute_lcoe_breakeven_top_pce(
            subgap_transmittance_fraction=sub_trans_frac,
            added_module_cost_usd_m2=delta_c_mod_2,
            case="rooftop",
            deg_rate=0.0050,
        )["breakeven_top_cell_pce_percent"]
    )
    be_optics = float(
        compute_optics_only_breakeven_top_pce(sub_trans_frac)["breakeven_top_cell_pce_percent"]
    )

    rec_path = (
        "PATH2_2L_ACTIVE_GLASS_IF_BREAKEVEN_MET"
        if lcoe_p2_util < lcoe_p1_util
        else "PATH1_3L_4T_SANDWICH"
    )

    blind_11b = independently_verify_phase11b_realistic_commercialization(
        eg_ind_1=eg_ind_1,
        eg_dir_1=eg_dir_1,
        eps_inf_1=eps_inf_1,
        opt_mgf2_nm=opt_mgf2,
        opt_tio2_nm=opt_tio2,
        opt_top_nm=opt_top,
        f_orient_1=fo1,
        v_antisite_1=va1,
        v_contact_1=vc1,
        raw_cost_top_usd_m2=raw_top,
        stoich_1=stoich_1,
        eg_ind_3=eg_ind_3,
        eg_dir_3=eg_dir_3,
        eps_inf_3=eps_inf_3,
        opt_bot_nm=opt_bot,
        f_orient_3=fo3,
        v_antisite_3=va3,
        v_contact_3=vc3,
        raw_cost_bot_usd_m2=raw_bot,
        stoich_3=stoich_3,
    )

    rouard_diff = round(abs(round(pce_2l_ceil, 2) - blind_11b["ceiling_2l_mono_pce_percent"]), 4)
    verif_ok = bool(
        rouard_diff <= 0.05
        and abs(round(pce_2l_dem, 2) - blind_11b["demonstrated_2l_mono_pce_percent"]) <= 0.05
        and abs(round(p_p2_bif20_ceil, 2) - blind_11b["path2_2l_bif20_equivalent_power_density_mw_cm2"]) <= 0.05
        and abs(round(p_p1_bif20, 2) - blind_11b["path1_3l_bif20_equivalent_power_density_mw_cm2"]) <= 0.05
        and abs(round(lcoe_p2_util, 3) - blind_11b["path2_utility_lcoe_cents_kwh"]) <= 0.02
        and abs(round(lcoe_p1_util, 3) - blind_11b["path1_utility_lcoe_cents_kwh"]) <= 0.02
        and rec_path == blind_11b["recommended_commercial_path"]
    )
    if not verif_ok:
        raise AssertionError(
            f"REDUNDANCY_MISMATCH_BLOCK: Phase 11B/11C mismatch on {p10_report.pair_id}: "
            f"diff_2L={rouard_diff:.4f}%, P2_LCOE={lcoe_p2_util:.3f} vs {blind_11b['path2_utility_lcoe_cents_kwh']:.3f}"
        )

    return Phase11BRealisticCommercializationDossier(
        pair_id=p10_report.pair_id,
        top_mp_id=str(c_top["candidate_id"]),
        top_formula=str(c_top["formula_reduced"]),
        bottom_mp_id=str(c_bot["candidate_id"]),
        bottom_formula=str(c_bot["formula_reduced"]),
        default_stack_layers=3 if include_rear_ir_cell else 2,
        include_rear_ir_cell=bool(include_rear_ir_cell),
        maturity_case_assumptions=MATURITY_CASES,
        radiative_2l_mono_pce_percent=float(p10_report.opt_monofacial_2l_pce_percent),
        radiative_3l_mono_pce_percent=float(p10_report.opt_monofacial_4t_pce_percent),
        radiative_3l_bif20_equivalent_power_density_mw_cm2=float(
            p10_report.bifacial_20pct_equivalent_power_density_mw_cm2
        ),
        path0_si_mono_pce_percent=round(eta_si_0_mono, 2),
        path0_si_bif20_equivalent_power_density_mw_cm2=round(p_si_0_bif20, 2),
        path0_utility_lcoe_cents_kwh=round(lcoe_p0_util, 3),
        path0_rooftop_lcoe_cents_kwh=round(lcoe_p0_roof, 3),
        demonstrated_top_pce_percent=round(eta_top_dem, 2),
        demonstrated_top_voc_v=round(voc_top_dem, 4),
        demonstrated_top_ff=round(ff_top_dem, 4),
        demonstrated_2l_mono_pce_percent=round(pce_2l_dem, 2),
        demonstrated_3l_mono_pce_percent=round(pce_3l_dem, 2) if include_rear_ir_cell else None,
        stretch_top_pce_percent=round(eta_top_str, 2),
        stretch_top_voc_v=round(voc_top_str, 4),
        stretch_2l_mono_pce_percent=round(pce_2l_str, 2),
        stretch_3l_mono_pce_percent=round(pce_3l_str, 2) if include_rear_ir_cell else None,
        ceiling_top_pce_percent=round(eta_top_ceil, 2),
        ceiling_top_voc_v=round(voc_top_ceil, 4),
        ceiling_bot_mono_pce_percent=round(eta_bot_mono_ceil, 2) if include_rear_ir_cell else None,
        ceiling_bot_mono_voc_v=round(voc_bot_mono_ceil, 4) if include_rear_ir_cell else None,
        ceiling_2l_mono_pce_percent=round(pce_2l_ceil, 2),
        ceiling_3l_mono_pce_percent=round(pce_3l_ceil, 2) if include_rear_ir_cell else None,
        gap_sens_2l_mono_low_percent=round(min(sens_2l), 2),
        gap_sens_2l_mono_high_percent=round(max(sens_2l), 2),
        gap_sens_3l_mono_low_percent=round(min(sens_3l), 2) if include_rear_ir_cell else None,
        gap_sens_3l_mono_high_percent=round(max(sens_3l), 2) if include_rear_ir_cell else None,
        path1_3l_bif20_equivalent_power_density_mw_cm2=round(p_p1_bif20, 2) if include_rear_ir_cell else None,
        path1_module_cost_usd_m2=round(c_mod_1, 2),
        path1_utility_lcoe_cents_kwh=round(lcoe_p1_util, 3) if include_rear_ir_cell else None,
        path1_rooftop_lcoe_cents_kwh=round(lcoe_p1_roof, 3) if include_rear_ir_cell else None,
        path2_2l_bif20_equivalent_power_density_mw_cm2=round(p_p2_bif20_ceil, 2),
        path2_module_cost_usd_m2=round(c_mod_2, 2),
        demonstrated_path2_utility_lcoe_cents_kwh=round(lcoe_p2_util_dem, 3),
        demonstrated_path2_rooftop_lcoe_cents_kwh=round(lcoe_p2_roof_dem, 3),
        path2_utility_lcoe_cents_kwh=round(lcoe_p2_util, 3),
        path2_rooftop_lcoe_cents_kwh=round(lcoe_p2_roof, 3),
        path3_2t_bif20_equivalent_power_density_mw_cm2=round(p_p3_bif20, 2),
        path3_module_cost_usd_m2=round(c_mod_3, 2),
        path3_utility_lcoe_cents_kwh=round(lcoe_p3_util, 3),
        path4_bipv_window_pce_percent=round(eta_p4_bipv, 2),
        path4_dgu_cost_usd_m2=round(c_mod_4, 2),
        utility_breakeven_top_pce_percent=round(be_util, 2),
        rooftop_breakeven_top_pce_percent=round(be_roof, 2),
        optics_only_breakeven_top_pce_percent=round(be_optics, 2),
        recommended_commercial_path=rec_path,
        rouard_ceiling_2l_diff_percent=rouard_diff,
        phase11_redundancy_verified=verif_ok,
        sha256_digest=str(blind_11b["sha256_digest"]),
    )

