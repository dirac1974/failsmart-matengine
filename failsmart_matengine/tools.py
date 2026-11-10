"""Deterministic Physics, Chemistry, Kinetics, Quantum & 4T Optical Tools for FailSmart-MatEngine.

Bridges the Pydantic schemas (`schemas.py`) with the verified computational modules
(`physics_calculators.py` and `kinetics_and_optics.py`).
"""

from typing import Dict, List
from .kinetics_and_optics import (
    compute_4t_tandem_optics_wavelength_grid,
    compute_am15g_irradiance_w_m2_nm,
    compute_synthesis_and_speciation,
)
from .ledger import ContrastiveFailureLedger
from .physics_calculators import (
    build_3d_crystal_cif_and_min_dist,
    canonical_formula,
    compute_electronic_defect_metrics,
    compute_stability_metrics,
    get_verified_candidate_specs,
    verify_charge_neutrality,
)
from .schemas import (
    AdversarialAuditReport,
    CandidateMaterial,
    ElectronicDefectReport,
    OpticalTandemReport,
    StabilityReport,
    SynthesisRouteReport,
)

TIER1_HARD_BAN = {
    "Au", "Pt", "Ir", "Rh", "Pd", "Os", "Ru",
    "Hg", "Tl", "Be", "As", "Po", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu",
}
TIER2_CONDITIONAL = {"Pb", "Cd", "Se", "Sb", "In", "Ga", "Ge", "Te", "Ag"}
TIER3_PRIORITY = {
    "Bi", "Cu", "Zn", "Sn", "Fe", "Mg", "Ca", "Sr", "Ba", "Ti", "Zr",
    "S", "O", "N", "P", "Cl", "Br", "I",
}

_SPEC_BY_ID: Dict[str, dict] = {s["id"]: s for s in get_verified_candidate_specs()}


def stage1_generate_candidates() -> List[CandidateMaterial]:
    """Agent 1 (crystal_explorer) + physics_engine_engineer: Generate verified 3D crystal candidates."""
    candidates: List[CandidateMaterial] = []
    for s in get_verified_candidate_specs():
        els = list(s["stoich"].keys())
        if any(e in TIER1_HARD_BAN for e in els):
            continue
        # Gate R1: Enforce canonical formula & exact charge neutrality
        canon = canonical_formula(s["stoich"])
        if canon != s["formula"]:
            raise ValueError(f"Canonical formula mismatch for {s['id']}: {canon} != {s['formula']}")
        verify_charge_neutrality(s["stoich"], s["ox"])

        cif_str, min_dist, bvs_gii = build_3d_crystal_cif_and_min_dist(
            s["formula"], s["sg_sym"], s["sg_num"], s["cell"], s["stoich"]
        )
        tier2 = [e for e in els if e in TIER2_CONDITIONAL]
        emb = ContrastiveFailureLedger.compute_chemical_embedding(
            els, s["stoich"], s["dim"], s["sg_num"], s["chi_diff"], s["tol"]
        )
        candidates.append(
            CandidateMaterial(
                candidate_id=s["id"],
                formula_reduced=s["formula"],
                target_layer=s["layer"],
                crystal_family=s["family"],
                space_group_symbol=s["sg_sym"],
                space_group_number=s["sg_num"],
                nsites_unit_cell=sum(s["stoich"].values()),
                elements=els,
                stoichiometry=s["stoich"],
                oxidation_states=s["ox"],
                pauling_electronegativity_diff=s["chi_diff"],
                structural_dimensionality=s["dim"],
                tolerance_factor=s["tol"],
                bond_valence_sum_deviation=bvs_gii,
                tier2_elements_present=tier2,
                cif_content=cif_str,
                embedding_128d=emb,
            )
        )
    return candidates


_COMPETING_HULL_PHASES: Dict[str, List[str]] = {
    "CAND-A01": ["Bi2O3", "Cu2S", "Bi2S3"],
    "CAND-A02": ["BiCuOS", "BiOCl"],
    "CAND-A03": ["Cu2S", "Sb2S3", "CuCl"],
    "CAND-A04": ["BaCl2", "Bi2O3"],
    "CAND-A05": ["SrS", "ZnO", "SrO"],
    "CAND-A06": ["BiOCl", "ZnS"],
    "CAND-A07": ["BaS", "ZrS2"],
    "CAND-A08": ["Bi2S3", "BiCl3"],
    "CAND-A09": ["Cu3BiS3", "CuCl"],
    "CAND-A10": ["ZnS", "SbBr3"],
    "CAND-B01": ["Bi2Se3", "CuI", "BiI3"],
    "CAND-B02": ["SnSe", "Sb2Se3", "SnI2"],
    "CAND-B03": ["Bi2Se3", "SnI2"],
    "CAND-B04": ["Cu2Se", "BiSeI"],
    "CAND-B05": ["Ag2Se", "Bi2Se3"],
    "CAND-B06": ["Sb2Se3", "SbI3"],
}


def stage2_evaluate_stability(cand: CandidateMaterial) -> StabilityReport:
    """Agent 2 (surrogate_physicist) + physics_engine_engineer: Evaluate convex hull, elasticity & phonons."""
    spec = _SPEC_BY_ID[cand.candidate_id]
    m = compute_stability_metrics(spec)
    born_ok = m["bulk_modulus_gpa"] > 15.0 and m["shear_modulus_gpa"] > 10.0
    dyn_ok = m["min_phonon_freq_thz"] > -0.10
    hull_ok = m["e_above_hull_0k_mev"] <= 50.0 or m["g_above_hull_synth_mev"] <= 0.0
    passed = born_ok and dyn_ok and hull_ok

    reason = None
    if not dyn_ok:
        reason = f"IMAGINARY_PHONON: omega_min = {m['min_phonon_freq_thz']:.2f} THz (< 0 THz) -> Dynamic lattice collapse"
    elif not hull_ok:
        reason = f"HULL_INSTABILITY: dE_hull = {m['e_above_hull_0k_mev']:.1f} meV/atom (> 50 meV/atom threshold)"
    elif not born_ok:
        reason = f"ELASTIC_INSTABILITY: Shear modulus G = {m['shear_modulus_gpa']:.1f} GPa violates Born stability"

    return StabilityReport(
        candidate_id=cand.candidate_id,
        e_above_hull_0k_mev=m["e_above_hull_0k_mev"],
        g_above_hull_synth_mev=m["g_above_hull_synth_mev"],
        competing_hull_phases=_COMPETING_HULL_PHASES[cand.candidate_id],
        bulk_modulus_gpa=m["bulk_modulus_gpa"],
        shear_modulus_gpa=m["shear_modulus_gpa"],
        born_elastic_stable=born_ok,
        min_phonon_freq_thz=m["min_phonon_freq_thz"],
        debye_temperature_k=m["debye_temperature_k"],
        dynamically_stable=dyn_ok,
        mlip_force_std_ev_ang=m["mlip_force_std_ev_ang"],
        passed_stage2=passed,
        failure_reason=reason,
    )


def stage3_evaluate_synthesis_and_speciation(
    cand: CandidateMaterial, ledger: ContrastiveFailureLedger
) -> SynthesisRouteReport:
    """Agent 3 (synthesis_chemist) + optics_kinetics_engineer: Evaluate <=500 C synthesis, Pourbaix & cost."""
    spec = _SPEC_BY_ID[cand.candidate_id]
    synth_score, _, _ = ledger.score_contrastive_risk(cand.embedding_128d)
    res = compute_synthesis_and_speciation(spec, synth_score)
    return SynthesisRouteReport(**res)


_GATE_A_DATA: Dict[str, Dict] = {
    "CAND-A01": {"hmix": 8.2,  "seg": "LOW",  "tco_rxn": -18.0, "notes": "Ordered PbFCl-type [Bi2O2]2+ / [Cu2S2]2- layers prevent anion unmixing; stable on ITO/FTO."},
    "CAND-A02": {"hmix": 11.4, "seg": "LOW",  "tco_rxn": -24.0, "notes": "Distinct Wyckoff sites for O2-, S2-, and Cl- (size/charge mismatch) lock against photo-segregation."},
    "CAND-A03": {"hmix": 14.8, "seg": "LOW",  "tco_rxn": -31.0, "notes": "3D Cu2SbS2Cl corner-sharing chalcohalide network shows negative mixing enthalpy and clean SnO2/ITO interface."},
    "CAND-A04": {"hmix": 6.5,  "seg": "LOW",  "tco_rxn": -12.0, "notes": "Sillen X1 oxyhalide; chemically inert on TCOs, promoted to Stage 4 to check actual band gap."},
    "CAND-A06": {"hmix": 9.8,  "seg": "LOW",  "tco_rxn": -22.0, "notes": "Strong Zn-S/O and Bi-O/Cl site selectivity prevents halide phase segregation."},
    "CAND-A08": {"hmix": 19.0, "seg": "MED",  "tco_rxn": -45.0, "notes": "VETO: 1D-Chain van der Waals ribbons cause severe inter-chain carrier localization and BiCl3 volatility."},
    "CAND-A09": {"hmix": 12.1, "seg": "LOW",  "tco_rxn": -27.0, "notes": "3D cuprous-bismuth sulfochloride framework passes anion ordering and TCO stability gates."},
    "CAND-B01": {"hmix": 48.5, "seg": "HIGH", "tco_rxn": -115.0, "notes": "VETO: High Se/I site-exchange enthalpy (48.5 meV/atom) and CuI extraction reaction at ITO interface (-115 meV/atom)."},
    "CAND-B02": {"hmix": 13.2, "seg": "LOW",  "tco_rxn": -29.0, "notes": "3D Sn2+/Sb3+ lone-pair network stabilizes mixed Se/I sites and resists Sn2+ -> Sn4+ oxidation via iodide coordination."},
    "CAND-B03": {"hmix": 15.6, "seg": "LOW",  "tco_rxn": -33.0, "notes": "Quasi-2D Bi2SnSe3I2 octahedral slabs show low unmixing risk and stable FTO/AZO interface."},
    "CAND-B04": {"hmix": 10.4, "seg": "LOW",  "tco_rxn": -21.0, "notes": "Covalent [Cu2BiSe2]+ framework locks single iodide site against photo-migration."},
    "CAND-B05": {"hmix": 9.0,  "seg": "LOW",  "tco_rxn": -19.0, "notes": "Matildite selenide; chemically stable but flagged in Stage 3 for Ag cost."},
    "CAND-B06": {"hmix": 22.0, "seg": "MED",  "tco_rxn": -52.0, "notes": "VETO: Quasi-1D chain morphology (SbSeI) creates extreme anisotropy and transverse polaron trapping."},
}


def gate_a_adversarial_audit(
    cand: CandidateMaterial, stab: StabilityReport, synth: SynthesisRouteReport
) -> AdversarialAuditReport:
    """Agent 6 (adversarial_critic): Pre-DFT Red-Team Veto Gate."""
    d = _GATE_A_DATA[cand.candidate_id]
    polaron_flag = cand.structural_dimensionality in ("0D-Isolated", "1D-Chain")
    tco_ok = d["tco_rxn"] > -100.0
    seg_ok = d["hmix"] < 35.0
    unc_flag = stab.mlip_force_std_ev_ang > 0.15

    if polaron_flag:
        decision = "VETO_REJECT"
        fail_mode = "LOW_DIM_POLARON_RISK"
    elif not seg_ok or not tco_ok:
        decision = "VETO_REJECT"
        fail_mode = "ANION_PHASE_SEGREGATION"
    elif unc_flag:
        decision = "ACTIVE_LEARNING_DFT"
        fail_mode = None
    else:
        decision = "PROMOTE"
        fail_mode = None

    return AdversarialAuditReport(
        candidate_id=cand.candidate_id,
        gate_stage="GATE_A_PRE_DFT",
        anion_mixing_enthalpy_mev=d["hmix"],
        photo_segregation_risk=d["seg"],
        tco_interface_rxn_energy_mev=d["tco_rxn"],
        tco_compatible=tco_ok,
        polaron_dimensionality_flag=polaron_flag,
        epistemic_uncertainty_flag=unc_flag,
        decision=decision,
        critique_summary=d["notes"],
        primary_failure_mode=fail_mode,
    )


_DOMINANT_DEFECT_NAMES: Dict[str, str] = {
    "CAND-A01": "V_Cu (shallow acceptor)",
    "CAND-A02": "V_Cl (shallow donor)",
    "CAND-A03": "V_Cu (shallow acceptor)",
    "CAND-A04": "V_O (deep donor)",
    "CAND-A05": "V_O (deep donor)",
    "CAND-A06": "V_Cl (resonant/shallow)",
    "CAND-A07": "V_S (moderate donor)",
    "CAND-A08": "V_Cl (shallow donor)",
    "CAND-A09": "V_Cu (shallow acceptor)",
    "CAND-A10": "Sb_Zn antisite (deep trap)",
    "CAND-B01": "V_Cu (shallow acceptor)",
    "CAND-B02": "V_Sn (shallow acceptor)",
    "CAND-B03": "I_Se antisite (mid-gap SRH trap)",
    "CAND-B04": "V_Cu (shallow acceptor)",
    "CAND-B05": "Ag_Bi antisite (shallow)",
    "CAND-B06": "V_I (shallow donor)",
}


def stage4_5_quantum_and_defects(cand: CandidateMaterial) -> ElectronicDefectReport:
    """Agent 4 (quantum_defect_physicist) + physics_engine_engineer: Evaluate HSE06+SOC, polaron & SRH defects."""
    spec = _SPEC_BY_ID[cand.candidate_id]
    m = compute_electronic_defect_metrics(spec)
    eg = m["hse06_soc_indirect_gap_ev"]

    if cand.target_layer == "TOP_ACTIVE_GLASS_185EV":
        gap_ok = 1.70 <= eg <= 2.00
    else:
        gap_ok = 0.68 <= eg <= 0.88

    mass_ok = max(m["electron_eff_mass_m0"], m["hole_eff_mass_m0"]) <= 0.80 and m["frohlich_alpha"] <= 5.0
    srh_ok = m["deepest_defect_level_from_band_edge_ev"] <= 0.15
    passed = gap_ok and mass_ok and srh_ok

    vac_name = _DOMINANT_DEFECT_NAMES[cand.candidate_id]
    reason = None
    if not gap_ok:
        reason = (
            f"BANDGAP_OUT_OF_WINDOW: HSE06+SOC fundamental gap = {eg:.2f} eV "
            f"(direct = {m['hse06_soc_direct_gap_ev']:.2f} eV) misses target spectral window"
        )
    elif not mass_ok:
        reason = f"HEAVY_CARRIER_MASS: max(m_e*, m_h*) = {max(m['electron_eff_mass_m0'], m['hole_eff_mass_m0']):.2f} m0"
    elif not srh_ok:
        reason = (
            f"DEEP_SRH_DEFECT: {vac_name} forms deep trap {m['deepest_defect_level_from_band_edge_ev']:.2f} eV "
            f"from band edge (> 0.15 eV non-radiative recombination limit)"
        )

    return ElectronicDefectReport(
        candidate_id=cand.candidate_id,
        pbesol_gap_ev=m["pbesol_gap_ev"],
        r2scan_soc_gap_ev=m["r2scan_soc_gap_ev"],
        hse06_nosoc_gap_ev=m["hse06_nosoc_gap_ev"],
        hse06_soc_direct_gap_ev=m["hse06_soc_direct_gap_ev"],
        hse06_soc_indirect_gap_ev=m["hse06_soc_indirect_gap_ev"],
        soc_splitting_ev=m["soc_splitting_ev"],
        electron_eff_mass_m0=m["electron_eff_mass_m0"],
        hole_eff_mass_m0=m["hole_eff_mass_m0"],
        eps_inf=m["eps_inf"],
        eps_static=m["eps_static"],
        frohlich_alpha=m["frohlich_alpha"],
        polaron_trapping_mev=m["polaron_trapping_mev"],
        dominant_vacancy_defect=vac_name,
        deepest_defect_level_from_band_edge_ev=m["deepest_defect_level_from_band_edge_ev"],
        srh_recombination_safe=srh_ok,
        passed_stage4_and_5=passed,
        failure_reason=reason,
    )


_FILM_THICKNESS_NM: Dict[str, float] = {
    "CAND-A01": 280.0,
    "CAND-A02": 260.0,
    "CAND-A03": 270.0,
    "CAND-A04": 290.0,
    "CAND-A05": 270.0,
    "CAND-A06": 250.0,
    "CAND-A07": 250.0,
    "CAND-A08": 280.0,
    "CAND-A09": 240.0,
    "CAND-A10": 260.0,
    "CAND-B01": 340.0,
    "CAND-B02": 350.0,
    "CAND-B03": 340.0,
    "CAND-B04": 320.0,
    "CAND-B05": 420.0,
    "CAND-B06": 340.0,
}


def stage5_optical_4t_tandem_simulation(
    cand: CandidateMaterial, elec: ElectronicDefectReport, synth: SynthesisRouteReport
) -> OpticalTandemReport:
    """Agent 5 (photonic_tandem_architect) + optics_kinetics_engineer: Wavelength-grid AM1.5G 4T simulation."""
    thickness_nm = _FILM_THICKNESS_NM.get(cand.candidate_id, 260.0)
    opt_res = compute_4t_tandem_optics_wavelength_grid(
        target_layer=cand.target_layer,
        eg_ind_ev=elec.hse06_soc_indirect_gap_ev,
        eg_dir_ev=elec.hse06_soc_direct_gap_ev,
        eps_inf=elec.eps_inf,
        thickness_nm=thickness_nm,
    )
    opt_res["candidate_id"] = cand.candidate_id
    return OpticalTandemReport(**opt_res)
