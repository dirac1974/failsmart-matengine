"""Deterministic Physics, Chemistry, Kinetics, Quantum & 4T Optical Tools for FailSmart-MatEngine v2.0.

Bridges the Pydantic v2 schemas (`schemas.py`) with the verified computational modules
(`physics_calculators.py` and `kinetics_and_optics.py`), supporting both benchmark
candidates and arbitrary out-of-distribution (OOD) generative compositions with zero KeyErrors.
"""

from typing import Any, Dict, List, Optional
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
    generate_smact_ood_candidates,
    get_verified_candidate_specs,
    verify_charge_neutrality,
)
from .schemas import (
    AdversarialAuditReport,
    CandidateMaterial,
    ElectronicDefectReport,
    OpticalTandemReport,
    ProvenanceTag,
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

_SPEC_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _refresh_registry(specs: List[Dict[str, Any]]) -> None:
    for s in specs:
        _SPEC_REGISTRY[s["id"]] = s


_refresh_registry(get_verified_candidate_specs())
_refresh_registry(generate_smact_ood_candidates(4))


def _spec_from_candidate(cand: CandidateMaterial) -> Dict[str, Any]:
    """Retrieve registered spec or synthesize a complete spec dict dynamically from CandidateMaterial."""
    if cand.candidate_id in _SPEC_REGISTRY:
        return _SPEC_REGISTRY[cand.candidate_id]
    return {
        "id": cand.candidate_id,
        "formula": cand.formula_reduced,
        "layer": cand.target_layer,
        "family": cand.crystal_family,
        "sg_sym": cand.space_group_symbol,
        "sg_num": cand.space_group_number,
        "nsites": cand.nsites_unit_cell,
        "stoich": dict(cand.stoichiometry),
        "ox": dict(cand.oxidation_states),
        "chi_diff": cand.pauling_electronegativity_diff,
        "dim": cand.structural_dimensionality,
        "tol": cand.tolerance_factor,
        "bvs_dev": cand.bond_valence_sum_deviation,
        "cell": (5.5, 5.5, 9.5),
    }


def build_candidate_from_spec(s: Dict[str, Any]) -> CandidateMaterial:
    """Construct a verified CandidateMaterial from a raw candidate specification dictionary."""
    _SPEC_REGISTRY[s["id"]] = s
    els = list(s["stoich"].keys())
    if any(e in TIER1_HARD_BAN for e in els):
        raise ValueError(f"Tier-1 banned element present in {s['id']}: {els}")

    canon = canonical_formula(s["stoich"])
    if canon != s["formula"]:
        raise ValueError(f"Canonical formula mismatch for {s['id']}: {canon} != {s['formula']}")
    verify_charge_neutrality(s["stoich"], s["ox"])

    cif_str, min_dist, bvs_gii, v_sg_sym, v_sg_num, nsites_uc = build_3d_crystal_cif_and_min_dist(
        s["formula"], s["sg_sym"], s["sg_num"], s["cell"], s["stoich"], s["ox"]
    )
    tier2 = [e for e in els if e in TIER2_CONDITIONAL]
    emb = ContrastiveFailureLedger.compute_chemical_embedding(
        els, s["stoich"], s["dim"], v_sg_num, s["chi_diff"], s["tol"]
    )
    return CandidateMaterial(
        candidate_id=s["id"],
        formula_reduced=s["formula"],
        target_layer=s["layer"],
        crystal_family=s["family"],
        space_group_symbol=v_sg_sym,
        space_group_number=v_sg_num,
        nsites_unit_cell=nsites_uc,
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


def stage1_generate_candidates(
    include_ood: bool = True, extra_specs: Optional[List[Dict[str, Any]]] = None
) -> List[CandidateMaterial]:
    """Agent 1 (crystal_explorer) + physics_engine_engineer: Generate verified 3D crystal candidates."""
    raw_list = list(get_verified_candidate_specs())
    if include_ood:
        raw_list.extend(generate_smact_ood_candidates(4))
    if extra_specs:
        raw_list.extend(extra_specs)

    candidates: List[CandidateMaterial] = []
    for s in raw_list:
        els = list(s["stoich"].keys())
        if any(e in TIER1_HARD_BAN for e in els):
            continue
        candidates.append(build_candidate_from_spec(s))
    return candidates


def stage2_evaluate_stability(cand: CandidateMaterial) -> StabilityReport:
    """Agent 2 (surrogate_physicist) + physics_engine_engineer: Evaluate convex hull, elasticity, phonons & Stage 2b ion migration."""
    spec = _spec_from_candidate(cand)
    m = compute_stability_metrics(spec)
    born_ok = m["bulk_modulus_gpa"] > 15.0 and m["shear_modulus_gpa"] > 10.0
    dyn_ok = m["omega_min_heuristic_thz"] > -0.10
    hull_ok = m["e_above_hull_0k_mev"] <= 50.0 or m["g_above_hull_synth_mev"] <= 0.0
    emig = float(m["ion_migration_barrier_ev"])
    ion_ok = emig >= 0.65
    passed = born_ok and dyn_ok and hull_ok and ion_ok

    reason = None
    if not dyn_ok:
        reason = f"IMAGINARY_PHONON: omega_min = {m['omega_min_heuristic_thz']:.2f} THz (< 0 THz) -> Dynamic lattice collapse"
    elif not hull_ok:
        reason = f"HULL_INSTABILITY: dE_hull = {m['e_above_hull_0k_mev']:.1f} meV/atom (> 50 meV/atom threshold)"
    elif not born_ok:
        reason = f"ELASTIC_INSTABILITY: Shear modulus G = {m['shear_modulus_gpa']:.1f} GPa violates Born stability"
    elif not ion_ok:
        reason = (
            f"ION_MIGRATION_INSTABILITY: E_mig = {emig:.2f} eV (< 0.65 eV Stage 2b threshold) -> "
            "Superionic Cu+/Ag+/halide drift & solar-bias hysteresis risk"
        )

    base_tag = ProvenanceTag.ASSUMED if m.get("is_fixture_lookup") else ProvenanceTag.HEURISTIC
    return StabilityReport(
        candidate_id=cand.candidate_id,
        e_above_hull_0k_mev=m["e_above_hull_0k_mev"],
        g_above_hull_synth_mev=m["g_above_hull_synth_mev"],
        competing_hull_phases=m.get("competing_hull_phases", ["Binary-Chalcogenide", "Binary-Halide"]),
        bulk_modulus_gpa=m["bulk_modulus_gpa"],
        shear_modulus_gpa=m["shear_modulus_gpa"],
        born_elastic_stable=born_ok,
        omega_min_heuristic_thz=m["omega_min_heuristic_thz"],
        debye_temperature_k=m["debye_temperature_k"],
        dynamically_stable=dyn_ok,
        ion_migration_barrier_ev=emig,
        ion_migration_stable=ion_ok,
        passed_stage2=passed,
        failure_reason=reason,
        provenance={
            "e_above_hull_0k_mev": base_tag,
            "g_above_hull_synth_mev": base_tag,
            "bulk_modulus_gpa": base_tag,
            "shear_modulus_gpa": base_tag,
            "omega_min_heuristic_thz": base_tag,
            "debye_temperature_k": ProvenanceTag.COMPUTED_HERE,
            "ion_migration_barrier_ev": base_tag,
        },
    )


def stage3_evaluate_synthesis_and_speciation(
    cand: CandidateMaterial, ledger: ContrastiveFailureLedger
) -> SynthesisRouteReport:
    """Agent 3 (synthesis_chemist) + optics_kinetics_engineer: Evaluate <=500 C synthesis, Pourbaix & cost."""
    spec = _spec_from_candidate(cand)
    synth_score, _, _ = ledger.score_contrastive_risk(cand.embedding_128d)
    res = compute_synthesis_and_speciation(spec, synth_score)
    return SynthesisRouteReport(**res)


_GATE_A_DATA: Dict[str, Dict[str, Any]] = {
    "CAND-A01": {"hmix": 8.2,  "seg": "LOW",  "tco_rxn": -18.0, "notes": "Ordered PbFCl-type [Bi2O2]2+ / [Cu2S2]2- layers prevent anion unmixing; stable on ITO/FTO."},
    "CAND-A02": {"hmix": 11.4, "seg": "LOW",  "tco_rxn": -24.0, "notes": "Distinct Wyckoff sites for O2-, S2-, and Cl- (size/charge mismatch) lock against photo-segregation."},
    "CAND-A03": {"hmix": 14.8, "seg": "LOW",  "tco_rxn": -31.0, "notes": "3D Cu2SbS2Cl corner-sharing chalcohalide network shows low mixing enthalpy and clean SnO2/ITO interface."},
    "CAND-A04": {"hmix": 6.5,  "seg": "LOW",  "tco_rxn": -12.0, "notes": "Sillen X1 oxyhalide; chemically inert on TCOs, promoted to Stage 4 to check actual band gap."},
    "CAND-A06": {"hmix": 9.8,  "seg": "LOW",  "tco_rxn": -22.0, "notes": "Strong Zn-S/O and Bi-O/Cl site selectivity prevents halide phase segregation."},
    "CAND-A08": {"hmix": 19.0, "seg": "MED",  "tco_rxn": -45.0, "notes": "VETO: 1D-Chain van der Waals ribbons cause severe inter-chain carrier localization and BiCl3 volatility."},
    "CAND-A09": {"hmix": 12.1, "seg": "LOW",  "tco_rxn": -27.0, "notes": "3D cuprous-bismuth sulfochloride framework passes anion ordering; gated by Stage 2b Cu+ migration."},
    "CAND-B01": {"hmix": 48.5, "seg": "HIGH", "tco_rxn": -115.0, "notes": "VETO: High Se/I site-exchange enthalpy (48.5 meV/atom) and CuI extraction reaction at ITO interface (-115 meV/atom)."},
    "CAND-B02": {"hmix": 13.2, "seg": "LOW",  "tco_rxn": -29.0, "notes": "3D Sn2+/Sb3+ lone-pair network stabilizes mixed Se/I sites and resists Sn2+ -> Sn4+ oxidation via iodide coordination."},
    "CAND-B03": {"hmix": 15.6, "seg": "LOW",  "tco_rxn": -33.0, "notes": "Quasi-2D Bi2SnSe3I2 octahedral slabs show low unmixing risk and stable FTO/AZO interface."},
    "CAND-B04": {"hmix": 10.4, "seg": "LOW",  "tco_rxn": -21.0, "notes": "Covalent [Cu2BiSe2]+ framework locks single iodide site against photo-migration."},
    "CAND-B05": {"hmix": 9.0,  "seg": "LOW",  "tco_rxn": -19.0, "notes": "Matildite selenide; chemically stable but flagged in Stage 3 for Ag cost."},
    "CAND-B06": {"hmix": 22.0, "seg": "MED",  "tco_rxn": -52.0, "notes": "VETO: Quasi-1D chain morphology (SbSeI) creates extreme anisotropy and transverse polaron trapping."},
}


def _infer_ood_gate_a(cand: CandidateMaterial) -> Dict[str, Any]:
    """Deterministic physical red-team audit for novel out-of-distribution compositions."""
    anions = [e for e in cand.elements if e in {"O", "S", "Se", "Te", "N", "P", "Cl", "Br", "I"}]
    heavy_hal_cnt = cand.stoichiometry.get("Br", 0) + cand.stoichiometry.get("I", 0)
    chalc_cnt = cand.stoichiometry.get("S", 0) + cand.stoichiometry.get("Se", 0) + cand.stoichiometry.get("Te", 0)
    ox_cnt = cand.stoichiometry.get("O", 0)

    hmix = 11.5
    if heavy_hal_cnt > 0 and chalc_cnt > 0:
        hal_to_chalc = heavy_hal_cnt / max(1, chalc_cnt)
        # Halide-rich selenoiodides/sulfobromides (halide/chalcogen >= 1.5 without oxide locking) suffer unmixing
        if hal_to_chalc >= 1.5 and ox_cnt == 0:
            hmix = 41.2
        else:
            hmix = 14.2
    seg = "HIGH" if hmix >= 35.0 else ("MED" if hmix >= 20.0 else "LOW")
    has_cu_i = ("Cu" in cand.stoichiometry and "I" in cand.stoichiometry and heavy_hal_cnt >= 2 * max(1, chalc_cnt))
    tco_rxn = -108.0 if has_cu_i else (-24.0 - 3.5 * len(anions))
    return {
        "hmix": round(hmix, 1),
        "seg": seg,
        "tco_rxn": round(tco_rxn, 1),
        "notes": (
            f"Dynamic Gate-A audit on {cand.formula_reduced} ({cand.structural_dimensionality}): "
            f"anion mixing enthalpy {hmix:.1f} meV/atom ({seg} photo-segregation risk), "
            f"TCO interface reaction {tco_rxn:.1f} meV/atom."
        ),
    }


def gate_a_adversarial_audit(
    cand: CandidateMaterial, stab: StabilityReport, synth: SynthesisRouteReport
) -> AdversarialAuditReport:
    """Agent 6 (adversarial_critic): Pre-DFT Red-Team Veto Gate."""
    is_fixture = cand.candidate_id in _GATE_A_DATA
    d = _GATE_A_DATA.get(cand.candidate_id) or _infer_ood_gate_a(cand)
    polaron_flag = cand.structural_dimensionality in ("0D-Isolated", "1D-Chain")
    tco_ok = d["tco_rxn"] > -100.0
    seg_ok = d["hmix"] < 35.0
    unc_flag = False
    prov_tag = ProvenanceTag.ASSUMED if is_fixture else ProvenanceTag.HEURISTIC

    if polaron_flag:
        decision = "VETO_REJECT"
        fail_mode = "LOW_DIM_POLARON_RISK"
    elif not seg_ok or not tco_ok:
        decision = "VETO_REJECT"
        fail_mode = "ANION_PHASE_SEGREGATION"
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
        provenance={
            "anion_mixing_enthalpy_mev": prov_tag,
            "tco_interface_rxn_energy_mev": prov_tag,
        },
    )


def stage4_5_quantum_and_defects(cand: CandidateMaterial) -> ElectronicDefectReport:
    """Evaluate fixture/heuristic band gap estimates, Frohlich polaron coupling & SRH defect trap estimates."""
    spec = _spec_from_candidate(cand)
    m = compute_electronic_defect_metrics(spec)
    eg = m["gap_est_indirect_ev"]

    if cand.target_layer == "TOP_ACTIVE_GLASS_185EV":
        gap_ok = 1.70 <= eg <= 2.00
    else:
        gap_ok = 0.68 <= eg <= 0.88

    mass_ok = max(m["electron_eff_mass_m0"], m["hole_eff_mass_m0"]) <= 0.80 and m["frohlich_alpha"] <= 5.0
    srh_ok = m["deepest_defect_level_from_band_edge_ev"] <= 0.15
    passed = gap_ok and mass_ok and srh_ok

    vac_name = m.get("dominant_vacancy_defect", "V_site (shallow)")
    reason = None
    if not gap_ok:
        reason = (
            f"BANDGAP_OUT_OF_WINDOW: estimated indirect gap = {eg:.2f} eV "
            f"(direct = {m['gap_est_direct_ev']:.2f} eV) misses target spectral window"
        )
    elif not mass_ok:
        reason = f"HEAVY_CARRIER_MASS: max(m_e*, m_h*) = {max(m['electron_eff_mass_m0'], m['hole_eff_mass_m0']):.2f} m0"
    elif not srh_ok:
        reason = (
            f"DEEP_SRH_DEFECT: {vac_name} forms deep trap {m['deepest_defect_level_from_band_edge_ev']:.2f} eV "
            f"from band edge (> 0.15 eV non-radiative recombination limit)"
        )

    base_tag = ProvenanceTag.ASSUMED if m.get("is_fixture_lookup") else ProvenanceTag.HEURISTIC
    return ElectronicDefectReport(
        candidate_id=cand.candidate_id,
        pbe_gap_ev=m["pbe_gap_ev"],
        gap_est_mgga_soc_ev=m["gap_est_mgga_soc_ev"],
        gap_est_nosoc_ev=m["gap_est_nosoc_ev"],
        gap_est_direct_ev=m["gap_est_direct_ev"],
        gap_est_indirect_ev=m["gap_est_indirect_ev"],
        soc_splitting_ev=m["soc_splitting_ev"],
        electron_eff_mass_m0=m["electron_eff_mass_m0"],
        hole_eff_mass_m0=m["hole_eff_mass_m0"],
        eps_inf=m["eps_inf"],
        eps_static=m["eps_static"],
        lo_phonon_freq_thz=m["lo_phonon_freq_thz"],
        frohlich_alpha=m["frohlich_alpha"],
        polaron_trapping_mev=m["polaron_trapping_mev"],
        dominant_vacancy_element=m["dominant_vacancy_element"],
        dominant_vacancy_defect=vac_name,
        deepest_defect_level_from_band_edge_ev=m["deepest_defect_level_from_band_edge_ev"],
        srh_recombination_safe=srh_ok,
        passed_stage4_and_5=passed,
        failure_reason=reason,
        provenance={
            "pbe_gap_ev": base_tag,
            "gap_est_mgga_soc_ev": base_tag,
            "gap_est_nosoc_ev": base_tag,
            "gap_est_direct_ev": base_tag,
            "gap_est_indirect_ev": base_tag,
            "soc_splitting_ev": ProvenanceTag.COMPUTED_HERE,
            "electron_eff_mass_m0": base_tag,
            "hole_eff_mass_m0": base_tag,
            "eps_inf": base_tag,
            "eps_static": base_tag,
            "lo_phonon_freq_thz": base_tag,
            "frohlich_alpha": ProvenanceTag.COMPUTED_HERE,
            "polaron_trapping_mev": ProvenanceTag.COMPUTED_HERE,
            "deepest_defect_level_from_band_edge_ev": base_tag,
        },
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
    """Wavelength-grid AM1.5G 4T radiative-limit optical simulation."""
    default_d = 260.0 if cand.target_layer == "TOP_ACTIVE_GLASS_185EV" else 340.0
    thickness_nm = _FILM_THICKNESS_NM.get(cand.candidate_id, default_d)
    opt_res = compute_4t_tandem_optics_wavelength_grid(
        target_layer=cand.target_layer,
        eg_ind_ev=elec.gap_est_indirect_ev,
        eg_dir_ev=elec.gap_est_direct_ev,
        eps_inf=elec.eps_inf,
        thickness_nm=thickness_nm,
    )
    opt_res["candidate_id"] = cand.candidate_id
    return OpticalTandemReport(**opt_res)
