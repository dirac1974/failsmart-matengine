"""Strict Pydantic v2 data contracts for the 13-agent FailSmart-MatEngine v2.0 pipeline."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CandidateMaterial(BaseModel):
    candidate_id: str
    formula_reduced: str
    target_layer: str = Field(
        ..., description="TOP_ACTIVE_GLASS_185EV or BOTTOM_IR_075EV"
    )
    crystal_family: str
    space_group_symbol: str
    space_group_number: int
    nsites_unit_cell: int
    elements: List[str]
    stoichiometry: Dict[str, int]
    oxidation_states: Dict[str, int]
    pauling_electronegativity_diff: float
    structural_dimensionality: str = Field(
        ..., description="3D, Quasi-2D, 1D-Chain, or 0D-Isolated"
    )
    tolerance_factor: float
    bond_valence_sum_deviation: float
    tier2_elements_present: List[str]
    cif_content: str
    embedding_128d: List[float]
    mp_id: Optional[str] = None
    dft_pbe_band_gap_ev: Optional[float] = None
    dft_is_gap_direct: Optional[bool] = None
    is_experimentally_known: Optional[bool] = None
    data_source: str = "SYNTHETIC_BENCHMARK"


class StabilityReport(BaseModel):
    candidate_id: str
    e_above_hull_0k_mev: float
    g_above_hull_synth_mev: Optional[float] = None
    competing_hull_phases: List[str]
    bulk_modulus_gpa: float
    shear_modulus_gpa: float
    born_elastic_stable: bool
    omega_min_heuristic_thz: Optional[float] = None
    debye_temperature_k: float
    dynamically_stable: Optional[bool] = None
    ion_migration_barrier_ev: float
    ion_migration_stable: bool
    mlip_force_std_ev_ang: Optional[float] = None
    passed_stage2: bool
    failure_reason: Optional[str] = None


class SynthesisRouteReport(BaseModel):
    candidate_id: str
    recommended_route: str
    precursors: List[str]
    min_synthesis_temp_c: float
    rxn_driving_force_mev_atom: float
    competing_impurity_sinks: List[str]
    impurity_sink_risk_score: Optional[float] = None
    halide_volatility_pressure_pa: float
    pourbaix_max_dissolution_mol_l: float
    pourbaix_stable_ph4_to_9: bool
    active_layer_cost_usd_m2: float
    contrastive_synthesizability_score: float
    passed_stage3: bool
    failure_reason: Optional[str] = None


class AdversarialAuditReport(BaseModel):
    candidate_id: str
    gate_stage: str = Field(..., description="GATE_A_PRE_DFT or GATE_B_FINAL")
    anion_mixing_enthalpy_mev: Optional[float] = None
    photo_segregation_risk: str = "NOT_EVALUATED"
    tco_interface_rxn_energy_mev: Optional[float] = None
    tco_compatible: Optional[bool] = None
    polaron_dimensionality_flag: bool
    epistemic_uncertainty_flag: bool
    decision: str = Field(
        ..., description="PROMOTE, VETO_REJECT, or ACTIVE_LEARNING_DFT"
    )
    critique_summary: str
    primary_failure_mode: Optional[str] = None


class ElectronicDefectReport(BaseModel):
    candidate_id: str
    pbesol_gap_ev: float
    r2scan_soc_gap_ev: float
    hse06_nosoc_gap_ev: float
    hse06_soc_direct_gap_ev: float
    hse06_soc_indirect_gap_ev: float
    soc_splitting_ev: float
    electron_eff_mass_m0: float
    hole_eff_mass_m0: float
    eps_inf: float
    eps_static: float
    lo_phonon_freq_thz: float
    frohlich_alpha: float
    polaron_trapping_mev: float
    dominant_vacancy_element: str
    dominant_vacancy_defect: str
    deepest_defect_level_from_band_edge_ev: float
    srh_recombination_safe: bool
    passed_stage4_and_5: bool
    failure_reason: Optional[str] = None


class OpticalTandemReport(BaseModel):
    candidate_id: str
    target_layer: str
    film_thickness_nm: float
    refractive_index_n: float
    yablonovitch_4n2_factor: float
    dipole_forbidden_penalty_ev: float
    shockley_queisser_limit_percent: float
    standalone_slme_percent: float
    sub_bandgap_transmittance_percent: float
    tco_parasitic_loss_percent: float
    top_cell_jsc_ma_cm2: float
    top_cell_voc_v: float
    top_cell_eff_percent: float
    si_middle_cell_eff_percent: float
    bottom_ir_cell_eff_percent: float
    tandem_2layer_si_eff_percent: float
    tandem_4t_std_si_fca_eff_percent: float
    tandem_4t_total_eff_percent: float
    passed_optical_gate: bool
    failure_reason: Optional[str] = None


class CrossLayerTandemPair(BaseModel):
    pair_id: str
    top_mp_id: str
    top_formula: str
    top_eg_ind_ev: float
    top_eg_dir_ev: float
    bottom_mp_id: str
    bottom_formula: str
    bottom_eg_ind_ev: float
    bottom_eg_dir_ev: float
    top_cell_eff_percent: float
    sub_bandgap_transmittance_percent: float
    si_middle_cell_eff_percent: float
    bottom_ir_std_si_eff_percent: float
    bottom_ir_low_fca_eff_percent: float
    tandem_2layer_si_eff_percent: float
    tandem_4t_std_si_fca_eff_percent: float
    tandem_4t_low_fca_total_eff_percent: float
    combined_active_cost_usd_m2: float
    photon_conservation_verified: bool
    redundancy_simpson_diff_percent: float


class AtomisticPhononNEBReport(BaseModel):
    """Pair-spring Gamma frequency heuristic and closed-form ion-migration barrier estimate."""
    candidate_id: str
    formula_reduced: str
    target_layer: str
    nsites_unit_cell: int
    dynamical_matrix_dim: int
    spring_model_gamma_freq_thz: List[float]
    migrating_species: str
    shortest_hop_distance_ang: float
    bottleneck_clearance_ang: float
    emig_heuristic_ev: float
    room_temp_diffusivity_cm2_s: float
    dynamically_stable: Optional[bool] = None
    emig_gate_passed: bool
    redundancy_verified: bool
    sha256_signature: str


class CoherentTMM4TStackReport(BaseModel):
    """Wavelength-Resolved Coherent 2x2 Abeles TMM vs Recursive Rouard/Airy 4T Stack Dossier (v4.0)."""
    pair_id: str
    top_mp_id: str
    top_formula: str
    bottom_mp_id: str
    bottom_formula: str
    arc_mgf2_thickness_nm: float
    front_ito_thickness_nm: float
    top_absorber_thickness_nm: float
    rear_buffer_thickness_nm: float
    bottom_absorber_thickness_nm: float
    tmm_mean_front_reflectance_percent: float
    tmm_sub_bandgap_transmittance_percent: float
    tmm_top_pce_percent: float
    tmm_si_pce_percent: float
    tmm_bottom_std_si_pce_percent: float
    tmm_bottom_pce_percent: float
    tmm_2layer_pce_percent: float
    tmm_4t_std_si_pce_percent: float
    tmm_4t_low_fca_pce_percent: float
    scalar_to_tmm_delta_pce_percent: float
    combined_active_cost_usd_m2: float
    photon_conservation_verified: bool
    rouard_airy_redundancy_diff_percent: float
    sha256_signature: str


class GradedARCTechnoEconomicReport(BaseModel):
    """7-Medium Graded-ARC + TiO2 Impedance-Matching Coherent Stack & 4-Metric Techno-Economic Dossier (v5.0)."""
    pair_id: str
    top_mp_id: str
    top_formula: str
    bottom_mp_id: str
    bottom_formula: str
    arc_mgf2_thickness_nm: float
    front_ito_thickness_nm: float
    tio2_matcher_thickness_nm: float
    top_absorber_thickness_nm: float
    rear_buffer_thickness_nm: float
    bottom_absorber_thickness_nm: float
    single_arc_front_reflectance_percent: float
    graded_arc_front_reflectance_percent: float
    reflectance_reduction_percent: float
    graded_sub_bandgap_transmittance_percent: float
    graded_top_pce_percent: float
    graded_si_pce_percent: float
    graded_bottom_std_si_pce_percent: float
    graded_bottom_pce_percent: float
    graded_2layer_pce_percent: float
    graded_4t_std_si_pce_percent: float
    graded_4t_low_fca_pce_percent: float
    single_to_graded_4t_gain_percent: float
    power_density_2l_w_m2: float
    power_density_2l_w_sqft: float
    power_density_3l_w_m2: float
    power_density_3l_w_sqft: float
    eff_gain_ratio_2l: float
    eff_gain_ratio_3l: float
    cer_2l_vs_2x_si: float
    cer_3l_vs_3x_si: float
    mciw_2l_raw_usd_per_dw: float
    mciw_2l_full_usd_per_dw: float
    mciw_3l_raw_usd_per_dw: float
    mciw_3l_full_usd_per_dw: float
    cpr_mod_2l: float
    cpr_mod_3l: float
    svi_bos_2l: float
    svi_bos_3l: float
    top_raw_cost_usd_m2: float
    combined_raw_cost_usd_m2: float
    photon_conservation_verified: bool
    rouard_airy_redundancy_diff_percent: float
    techno_economic_redundancy_verified: bool
    sha256_signature: str


class LabSynthesisAndDefectDossier(BaseModel):
    """Phase 9A: Lab-Ready 10.0 mmol Synthesis Recipe & Neutral Vacancy Supercell Dossier."""
    candidate_id: str
    formula_reduced: str
    target_layer: str
    formula_unit_molar_mass_g_mol: float
    target_batch_mmol: float
    target_product_mass_g: float
    reagent_masses_g: Dict[str, float]
    volatile_overpressure_masses_g: Dict[str, float]
    elemental_mass_conservation_diff_g: float
    synthesis_temperature_c: float
    dwell_time_hours: float
    supercell_dims: List[int]
    supercell_total_sites: int
    supercell_min_image_dist_ang: float
    dominant_vacancy_element: str
    dominant_vacancy_species: str
    point_charge_image_estimate_ev: float
    point_charge_image_estimate_q2_ev: float
    neutral_vacancy_deck_filename: str
    redundancy_verified: bool
    sha256_signature: str


class RealWorldLCOEStressTestReport(BaseModel):
    """Phase 9C: Oblique-Incidence (0-60 deg) S/P TMM, Operating Temp (25-65 C) & 25-Year Arrhenius LCOE Dossier (v6.0)."""
    pair_id: str
    top_mp_id: str
    top_formula: str
    bottom_mp_id: str
    bottom_formula: str
    r_front_0deg_percent: float
    r_front_30deg_percent: float
    r_front_45deg_percent: float
    r_front_60deg_percent: float
    r_front_hemispheric_percent: float
    pce_4t_0deg_25c_percent: float
    pce_4t_30deg_25c_percent: float
    pce_4t_45deg_25c_percent: float
    pce_4t_60deg_25c_percent: float
    iam_60deg_ratio: float
    pce_4t_noct_45c_percent: float
    pce_4t_desert_65c_percent: float
    temp_coeff_rel_pct_per_k: float
    limiting_neb_barrier_ev: float
    annual_degradation_rate_pct_yr: float
    year25_retained_power_fraction_percent: float
    lcoe_baseline_si_cents_kwh: float
    lcoe_2layer_cents_kwh: float
    lcoe_3layer_4t_cents_kwh: float
    lcoe_3layer_vs_si_reduction_percent: float
    rouard_oblique_60deg_diff_percent: float
    lcoe_redundancy_verified: bool
    sha256_signature: str


class Phase10BifacialLossAndStringDossier(BaseModel):
    """Phase 10A/10B/10C: Thickness/ARC Global Optimization, Bifacial Albedo Harvesting & SPICE String Dossier (v7.0)."""
    pair_id: str
    top_mp_id: str
    top_formula: str
    bottom_mp_id: str
    bottom_formula: str
    opt_mgf2_nm: float
    opt_tio2_nm: float
    opt_top_nm: float
    opt_bot_nm: float
    opt_r_front_percent: float
    opt_monofacial_4t_pce_percent: float
    bifacial_20pct_albedo_4t_pce_percent: float
    bifacial_20pct_power_w_sqft: float
    bifacial_30pct_albedo_4t_pce_percent: float
    bifacial_30pct_power_w_sqft: float
    bifacial_20pct_gain_percent: float
    bifacial_20pct_lcoe_cents_kwh: float
    top_jsc_ma_cm2: float
    top_voc_v: float
    top_ff: float
    top_vmp_v: float
    si_jsc_ma_cm2: float
    si_voc_v: float
    si_ff: float
    si_vmp_v: float
    bot_jsc_ma_cm2: float
    bot_voc_v: float
    bot_ff: float
    bot_vmp_v: float
    n_cells_si_ref: int
    n_cells_top_matched: int
    n_cells_bot_matched: int
    v_bus_si_v: float
    top_string_mismatch_percent: float
    bot_string_mismatch_percent: float
    rouard_opt_diff_percent: float
    phase10_redundancy_verified: bool
    sha256_signature: str


class Phase11ASynthesisContactDossier(BaseModel):
    """Phase 11A: Live DFT Synthesis Window, TCO InterfacialReactivity, Contact Alignment & Practicality Dossier (v8.0)."""
    candidate_id: str
    formula_reduced: str
    target_layer: str
    structural_dimensionality: str
    mp_gga_hull_mev_per_atom: Optional[float] = None
    hull_decomposition_phases: List[str]
    anion_chempot_window_ev: Optional[float] = None
    min_cation_chempot_window_ev: Optional[float] = None
    rxn_sno2_mev_per_atom: Optional[float] = None
    rxn_in2o3_mev_per_atom: Optional[float] = None
    rxn_tio2_mev_per_atom: Optional[float] = None
    dominant_in2o3_reaction: str
    cbm_vs_vacuum_ev: Optional[float] = None
    vbm_vs_vacuum_ev: Optional[float] = None
    cbo_vs_tio2_ev: Optional[float] = None
    cbo_vs_sno2_ev: Optional[float] = None
    vbo_vs_niox_ev: Optional[float] = None
    recommended_etl_barrier: str
    best_cbo_ev: Optional[float] = None
    contact_voltage_penalty_v: Optional[float] = None
    antisite_voltage_penalty_v: float
    ribbon_orientation_factor: float
    critical_mineral_index: float
    has_critical_mineral: bool
    synthesis_practicality_score_100: Optional[float] = None
    redundancy_verified: bool
    sha256_signature: str


class Phase11BRealisticCommercializationDossier(BaseModel):
    """Phase 11B/11C: Realistic Non-Radiative SRH Device Physics & 4-Path Commercialization Techno-Economics (v8.0)."""
    pair_id: str
    top_mp_id: str
    top_formula: str
    bottom_mp_id: str
    bottom_formula: str
    radiative_3l_mono_pce_percent: float
    radiative_3l_bif20_pce_percent: float
    path0_si_mono_pce_percent: float
    path0_si_bif20_pce_percent: float
    path0_utility_lcoe_cents_kwh: float
    path0_rooftop_lcoe_cents_kwh: float
    conservative_2l_mono_pce_percent: float
    conservative_3l_mono_pce_percent: float
    base_top_pce_percent: float
    base_top_voc_v: float
    base_bot_mono_pce_percent: float
    base_bot_mono_voc_v: float
    base_2l_mono_pce_percent: float
    base_3l_mono_pce_percent: float
    mature_2l_mono_pce_percent: float
    mature_3l_mono_pce_percent: float
    gap_sens_2l_mono_low_percent: float
    gap_sens_2l_mono_high_percent: float
    gap_sens_3l_mono_low_percent: float
    gap_sens_3l_mono_high_percent: float
    path1_3l_bif20_pce_percent: float
    path1_module_cost_usd_m2: float
    path1_utility_lcoe_cents_kwh: float
    path1_rooftop_lcoe_cents_kwh: float
    path2_2l_bif20_pce_percent: float
    path2_module_cost_usd_m2: float
    path2_utility_lcoe_cents_kwh: float
    path2_rooftop_lcoe_cents_kwh: float
    path3_2t_bif20_pce_percent: float
    path3_module_cost_usd_m2: float
    path3_utility_lcoe_cents_kwh: float
    path4_bipv_window_pce_percent: float
    path4_dgu_cost_usd_m2: float
    path4_gross_margin_percent: float
    recommended_commercial_path: str
    rouard_base_2l_diff_percent: float
    phase11_redundancy_verified: bool
    sha256_signature: str
