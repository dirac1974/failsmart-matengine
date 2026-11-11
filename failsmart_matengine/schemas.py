"""Strict Pydantic v2 data contracts with per-quantity provenance tags."""

from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Union, get_args, get_origin
from pydantic import BaseModel, Field, model_validator


class ProvenanceTag(str, Enum):
    MP_DFT = "MP_DFT"
    LITERATURE = "LITERATURE"
    COMPUTED_HERE = "COMPUTED_HERE"
    HEURISTIC = "HEURISTIC"
    ASSUMED = "ASSUMED"


def _annotation_is_numeric(ann: Any) -> bool:
    if ann is bool:
        return False
    if ann in (int, float):
        return True
    origin = get_origin(ann)
    args = get_args(ann)
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        return bool(non_none) and all(_annotation_is_numeric(a) for a in non_none)
    if origin in (list, List):
        return bool(args) and _annotation_is_numeric(args[0])
    if origin in (dict, Dict):
        return len(args) == 2 and _annotation_is_numeric(args[1])
    return False


class _ProvenanceTaggedModel(BaseModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {}
    provenance: Dict[str, ProvenanceTag] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _populate_and_verify_provenance(self) -> "_ProvenanceTaggedModel":
        merged: Dict[str, ProvenanceTag] = dict(self._DEFAULT_PROVENANCE)
        for k, v in self.provenance.items():
            merged[k] = v if isinstance(v, ProvenanceTag) else ProvenanceTag(v)
        for fname, finfo in type(self).model_fields.items():
            if fname == "provenance":
                continue
            if _annotation_is_numeric(finfo.annotation) and fname not in merged:
                raise ValueError(
                    f"{type(self).__name__}.{fname} is numeric ({finfo.annotation}) "
                    "and requires a ProvenanceTag in `provenance`."
                )
        self.provenance = merged
        return self


class CandidateMaterial(_ProvenanceTaggedModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "space_group_number": ProvenanceTag.COMPUTED_HERE,
        "nsites_unit_cell": ProvenanceTag.COMPUTED_HERE,
        "stoichiometry": ProvenanceTag.COMPUTED_HERE,
        "oxidation_states": ProvenanceTag.HEURISTIC,
        "pauling_electronegativity_diff": ProvenanceTag.COMPUTED_HERE,
        "tolerance_factor": ProvenanceTag.HEURISTIC,
        "bond_valence_sum_deviation": ProvenanceTag.COMPUTED_HERE,
        "embedding_128d": ProvenanceTag.HEURISTIC,
        "dft_pbe_band_gap_ev": ProvenanceTag.MP_DFT,
    }

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


class StabilityReport(_ProvenanceTaggedModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "e_above_hull_0k_mev": ProvenanceTag.MP_DFT,
        "g_above_hull_synth_mev": ProvenanceTag.HEURISTIC,
        "bulk_modulus_gpa": ProvenanceTag.HEURISTIC,
        "shear_modulus_gpa": ProvenanceTag.HEURISTIC,
        "omega_min_heuristic_thz": ProvenanceTag.HEURISTIC,
        "debye_temperature_k": ProvenanceTag.COMPUTED_HERE,
        "ion_migration_barrier_ev": ProvenanceTag.HEURISTIC,
    }

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
    passed_stage2: bool
    failure_reason: Optional[str] = None


class SynthesisRouteReport(_ProvenanceTaggedModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "min_synthesis_temp_c": ProvenanceTag.HEURISTIC,
        "rxn_driving_force_mev_atom": ProvenanceTag.HEURISTIC,
        "impurity_sink_risk_score": ProvenanceTag.LITERATURE,
        "halide_volatility_pressure_pa": ProvenanceTag.HEURISTIC,
        "pourbaix_max_dissolution_mol_l": ProvenanceTag.HEURISTIC,
        "active_layer_cost_usd_m2": ProvenanceTag.COMPUTED_HERE,
        "contrastive_synthesizability_score": ProvenanceTag.HEURISTIC,
    }

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


class AdversarialAuditReport(_ProvenanceTaggedModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "anion_mixing_enthalpy_mev": ProvenanceTag.ASSUMED,
        "tco_interface_rxn_energy_mev": ProvenanceTag.ASSUMED,
    }

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


class ElectronicDefectReport(_ProvenanceTaggedModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "pbe_gap_ev": ProvenanceTag.MP_DFT,
        "gap_est_mgga_soc_ev": ProvenanceTag.HEURISTIC,
        "gap_est_nosoc_ev": ProvenanceTag.HEURISTIC,
        "gap_est_direct_ev": ProvenanceTag.HEURISTIC,
        "gap_est_indirect_ev": ProvenanceTag.HEURISTIC,
        "gap_error_bar_ev": ProvenanceTag.COMPUTED_HERE,
        "window_probability": ProvenanceTag.COMPUTED_HERE,
        "soc_splitting_ev": ProvenanceTag.HEURISTIC,
        "electron_eff_mass_m0": ProvenanceTag.HEURISTIC,
        "hole_eff_mass_m0": ProvenanceTag.HEURISTIC,
        "eps_inf": ProvenanceTag.HEURISTIC,
        "eps_static": ProvenanceTag.HEURISTIC,
        "lo_phonon_freq_thz": ProvenanceTag.HEURISTIC,
        "frohlich_alpha": ProvenanceTag.COMPUTED_HERE,
        "polaron_trapping_mev": ProvenanceTag.COMPUTED_HERE,
        "deepest_defect_level_from_band_edge_ev": ProvenanceTag.HEURISTIC,
    }

    candidate_id: str
    pbe_gap_ev: float
    gap_est_mgga_soc_ev: float
    gap_est_nosoc_ev: float
    gap_est_direct_ev: float
    gap_est_indirect_ev: float
    gap_error_bar_ev: Optional[float] = None
    window_probability: Optional[float] = None
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


class OpticalTandemReport(_ProvenanceTaggedModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "film_thickness_nm": ProvenanceTag.ASSUMED,
        "refractive_index_n": ProvenanceTag.HEURISTIC,
        "yablonovitch_4n2_factor": ProvenanceTag.COMPUTED_HERE,
        "dipole_forbidden_penalty_ev": ProvenanceTag.COMPUTED_HERE,
        "shockley_queisser_limit_percent": ProvenanceTag.COMPUTED_HERE,
        "standalone_slme_percent": ProvenanceTag.COMPUTED_HERE,
        "sub_bandgap_transmittance_percent": ProvenanceTag.COMPUTED_HERE,
        "tco_parasitic_loss_percent": ProvenanceTag.COMPUTED_HERE,
        "top_cell_jsc_ma_cm2": ProvenanceTag.COMPUTED_HERE,
        "top_cell_voc_v": ProvenanceTag.COMPUTED_HERE,
        "top_cell_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "si_middle_cell_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "bottom_ir_cell_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "tandem_2layer_si_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "tandem_4t_std_si_fca_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "tandem_4t_total_eff_percent": ProvenanceTag.COMPUTED_HERE,
    }

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


class CrossLayerTandemPair(_ProvenanceTaggedModel):
    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "top_eg_ind_ev": ProvenanceTag.HEURISTIC,
        "top_eg_dir_ev": ProvenanceTag.HEURISTIC,
        "bottom_eg_ind_ev": ProvenanceTag.HEURISTIC,
        "bottom_eg_dir_ev": ProvenanceTag.HEURISTIC,
        "top_cell_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "sub_bandgap_transmittance_percent": ProvenanceTag.COMPUTED_HERE,
        "si_middle_cell_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "bottom_ir_std_si_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "bottom_ir_low_fca_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "tandem_2layer_si_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "tandem_4t_std_si_fca_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "tandem_4t_low_fca_total_eff_percent": ProvenanceTag.COMPUTED_HERE,
        "combined_active_cost_usd_m2": ProvenanceTag.COMPUTED_HERE,
        "redundancy_simpson_diff_percent": ProvenanceTag.COMPUTED_HERE,
    }

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


class AtomisticSpringMigrationReport(_ProvenanceTaggedModel):
    """Pair-spring Gamma frequency heuristic and closed-form ion-migration barrier estimate."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "nsites_unit_cell": ProvenanceTag.MP_DFT,
        "dynamical_matrix_dim": ProvenanceTag.COMPUTED_HERE,
        "spring_model_gamma_freq_thz": ProvenanceTag.HEURISTIC,
        "shortest_hop_distance_ang": ProvenanceTag.COMPUTED_HERE,
        "bottleneck_clearance_ang": ProvenanceTag.COMPUTED_HERE,
        "emig_heuristic_ev": ProvenanceTag.HEURISTIC,
        "room_temp_diffusivity_cm2_s": ProvenanceTag.HEURISTIC,
    }

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
    sha256_digest: str


class CoherentTMM4TStackReport(_ProvenanceTaggedModel):
    """Wavelength-resolved coherent 2x2 Abeles TMM vs recursive Rouard/Airy 4T stack dossier."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "arc_mgf2_thickness_nm": ProvenanceTag.ASSUMED,
        "front_ito_thickness_nm": ProvenanceTag.ASSUMED,
        "top_absorber_thickness_nm": ProvenanceTag.ASSUMED,
        "rear_buffer_thickness_nm": ProvenanceTag.ASSUMED,
        "bottom_absorber_thickness_nm": ProvenanceTag.ASSUMED,
        "tmm_mean_front_reflectance_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_sub_bandgap_transmittance_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_top_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_si_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_bottom_std_si_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_bottom_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_2layer_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_4t_std_si_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "tmm_4t_low_fca_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "scalar_to_tmm_delta_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "combined_active_cost_usd_m2": ProvenanceTag.COMPUTED_HERE,
        "rouard_airy_redundancy_diff_percent": ProvenanceTag.COMPUTED_HERE,
    }

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
    sha256_digest: str


class GradedARCTechnoEconomicReport(_ProvenanceTaggedModel):
    """7-medium graded-ARC + TiO2 impedance-matching coherent stack & techno-economic dossier."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "arc_mgf2_thickness_nm": ProvenanceTag.ASSUMED,
        "front_ito_thickness_nm": ProvenanceTag.ASSUMED,
        "tio2_matcher_thickness_nm": ProvenanceTag.ASSUMED,
        "top_absorber_thickness_nm": ProvenanceTag.ASSUMED,
        "rear_buffer_thickness_nm": ProvenanceTag.ASSUMED,
        "bottom_absorber_thickness_nm": ProvenanceTag.ASSUMED,
        "single_arc_front_reflectance_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_arc_front_reflectance_percent": ProvenanceTag.COMPUTED_HERE,
        "reflectance_reduction_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_sub_bandgap_transmittance_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_top_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_si_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_bottom_std_si_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_bottom_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_2layer_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_4t_std_si_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "graded_4t_low_fca_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "single_to_graded_4t_gain_percent": ProvenanceTag.COMPUTED_HERE,
        "power_density_2l_w_m2": ProvenanceTag.COMPUTED_HERE,
        "power_density_2l_w_sqft": ProvenanceTag.COMPUTED_HERE,
        "power_density_3l_w_m2": ProvenanceTag.COMPUTED_HERE,
        "power_density_3l_w_sqft": ProvenanceTag.COMPUTED_HERE,
        "eff_gain_ratio_2l": ProvenanceTag.COMPUTED_HERE,
        "eff_gain_ratio_3l": ProvenanceTag.COMPUTED_HERE,
        "cer_2l_vs_2x_si": ProvenanceTag.COMPUTED_HERE,
        "cer_3l_vs_3x_si": ProvenanceTag.COMPUTED_HERE,
        "mciw_2l_raw_usd_per_dw": ProvenanceTag.COMPUTED_HERE,
        "mciw_2l_full_usd_per_dw": ProvenanceTag.COMPUTED_HERE,
        "mciw_3l_raw_usd_per_dw": ProvenanceTag.COMPUTED_HERE,
        "mciw_3l_full_usd_per_dw": ProvenanceTag.COMPUTED_HERE,
        "cpr_mod_2l": ProvenanceTag.COMPUTED_HERE,
        "cpr_mod_3l": ProvenanceTag.COMPUTED_HERE,
        "svi_bos_2l": ProvenanceTag.COMPUTED_HERE,
        "svi_bos_3l": ProvenanceTag.COMPUTED_HERE,
        "top_raw_cost_usd_m2": ProvenanceTag.COMPUTED_HERE,
        "combined_raw_cost_usd_m2": ProvenanceTag.COMPUTED_HERE,
        "rouard_airy_redundancy_diff_percent": ProvenanceTag.COMPUTED_HERE,
    }

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
    sha256_digest: str


class LabSynthesisAndDefectDossier(_ProvenanceTaggedModel):
    """Phase 9A: 10.0 mmol synthesis batch balance & neutral vacancy supercell dossier."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "formula_unit_molar_mass_g_mol": ProvenanceTag.COMPUTED_HERE,
        "target_batch_mmol": ProvenanceTag.ASSUMED,
        "target_product_mass_g": ProvenanceTag.COMPUTED_HERE,
        "reagent_masses_g": ProvenanceTag.COMPUTED_HERE,
        "volatile_overpressure_masses_g": ProvenanceTag.ASSUMED,
        "elemental_mass_conservation_diff_g": ProvenanceTag.COMPUTED_HERE,
        "synthesis_temperature_c": ProvenanceTag.HEURISTIC,
        "dwell_time_hours": ProvenanceTag.HEURISTIC,
        "supercell_dims": ProvenanceTag.COMPUTED_HERE,
        "supercell_total_sites": ProvenanceTag.COMPUTED_HERE,
        "supercell_min_image_dist_ang": ProvenanceTag.COMPUTED_HERE,
        "point_charge_image_estimate_ev": ProvenanceTag.HEURISTIC,
        "point_charge_image_estimate_q2_ev": ProvenanceTag.HEURISTIC,
    }

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
    sha256_digest: str


class RealWorldLCOEStressTestReport(_ProvenanceTaggedModel):
    """Phase 9C: Oblique-incidence (0-60 deg) S/P TMM, operating temp (25-65 C) & 25-year Arrhenius LCOE dossier."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "r_front_0deg_percent": ProvenanceTag.COMPUTED_HERE,
        "r_front_30deg_percent": ProvenanceTag.COMPUTED_HERE,
        "r_front_45deg_percent": ProvenanceTag.COMPUTED_HERE,
        "r_front_60deg_percent": ProvenanceTag.COMPUTED_HERE,
        "r_front_hemispheric_percent": ProvenanceTag.COMPUTED_HERE,
        "pce_4t_0deg_25c_percent": ProvenanceTag.COMPUTED_HERE,
        "pce_4t_30deg_25c_percent": ProvenanceTag.COMPUTED_HERE,
        "pce_4t_45deg_25c_percent": ProvenanceTag.COMPUTED_HERE,
        "pce_4t_60deg_25c_percent": ProvenanceTag.COMPUTED_HERE,
        "iam_60deg_ratio": ProvenanceTag.COMPUTED_HERE,
        "pce_4t_noct_45c_percent": ProvenanceTag.COMPUTED_HERE,
        "pce_4t_desert_65c_percent": ProvenanceTag.COMPUTED_HERE,
        "temp_coeff_rel_pct_per_k": ProvenanceTag.COMPUTED_HERE,
        "limiting_emig_heuristic_ev": ProvenanceTag.HEURISTIC,
        "annual_degradation_rate_pct_yr": ProvenanceTag.HEURISTIC,
        "year25_retained_power_fraction_percent": ProvenanceTag.HEURISTIC,
        "lcoe_baseline_si_cents_kwh": ProvenanceTag.ASSUMED,
        "lcoe_2layer_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "lcoe_3layer_4t_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "lcoe_3layer_vs_si_reduction_percent": ProvenanceTag.COMPUTED_HERE,
        "rouard_oblique_60deg_diff_percent": ProvenanceTag.COMPUTED_HERE,
    }

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
    limiting_emig_heuristic_ev: float
    annual_degradation_rate_pct_yr: float
    year25_retained_power_fraction_percent: float
    lcoe_baseline_si_cents_kwh: float
    lcoe_2layer_cents_kwh: float
    lcoe_3layer_4t_cents_kwh: float
    lcoe_3layer_vs_si_reduction_percent: float
    rouard_oblique_60deg_diff_percent: float
    lcoe_redundancy_verified: bool
    sha256_digest: str


class Phase10BifacialLossAndStringDossier(_ProvenanceTaggedModel):
    """Phase 10A/10B/10C: Thickness/ARC optimization, bifacial albedo harvesting & string matching dossier."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "opt_mgf2_nm": ProvenanceTag.COMPUTED_HERE,
        "opt_tio2_nm": ProvenanceTag.COMPUTED_HERE,
        "opt_top_nm": ProvenanceTag.COMPUTED_HERE,
        "opt_bot_nm": ProvenanceTag.COMPUTED_HERE,
        "opt_r_front_percent": ProvenanceTag.COMPUTED_HERE,
        "opt_monofacial_4t_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "bifacial_20pct_albedo_4t_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "bifacial_20pct_power_w_sqft": ProvenanceTag.COMPUTED_HERE,
        "bifacial_30pct_albedo_4t_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "bifacial_30pct_power_w_sqft": ProvenanceTag.COMPUTED_HERE,
        "bifacial_20pct_gain_percent": ProvenanceTag.COMPUTED_HERE,
        "bifacial_20pct_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "top_jsc_ma_cm2": ProvenanceTag.COMPUTED_HERE,
        "top_voc_v": ProvenanceTag.COMPUTED_HERE,
        "top_ff": ProvenanceTag.COMPUTED_HERE,
        "top_vmp_v": ProvenanceTag.COMPUTED_HERE,
        "si_jsc_ma_cm2": ProvenanceTag.COMPUTED_HERE,
        "si_voc_v": ProvenanceTag.COMPUTED_HERE,
        "si_ff": ProvenanceTag.COMPUTED_HERE,
        "si_vmp_v": ProvenanceTag.COMPUTED_HERE,
        "bot_jsc_ma_cm2": ProvenanceTag.COMPUTED_HERE,
        "bot_voc_v": ProvenanceTag.COMPUTED_HERE,
        "bot_ff": ProvenanceTag.COMPUTED_HERE,
        "bot_vmp_v": ProvenanceTag.COMPUTED_HERE,
        "n_cells_si_ref": ProvenanceTag.ASSUMED,
        "n_cells_top_matched": ProvenanceTag.COMPUTED_HERE,
        "n_cells_bot_matched": ProvenanceTag.COMPUTED_HERE,
        "v_bus_si_v": ProvenanceTag.COMPUTED_HERE,
        "top_string_mismatch_percent": ProvenanceTag.COMPUTED_HERE,
        "bot_string_mismatch_percent": ProvenanceTag.COMPUTED_HERE,
        "rouard_opt_diff_percent": ProvenanceTag.COMPUTED_HERE,
    }

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
    sha256_digest: str


class Phase11ASynthesisContactDossier(_ProvenanceTaggedModel):
    """Phase 11A: Cached MP DFT hull window, TCO interfacial reactivity & contact alignment dossier."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "mp_gga_hull_mev_per_atom": ProvenanceTag.MP_DFT,
        "anion_chempot_window_ev": ProvenanceTag.MP_DFT,
        "min_cation_chempot_window_ev": ProvenanceTag.MP_DFT,
        "rxn_sno2_mev_per_atom": ProvenanceTag.MP_DFT,
        "rxn_in2o3_mev_per_atom": ProvenanceTag.MP_DFT,
        "rxn_tio2_mev_per_atom": ProvenanceTag.MP_DFT,
        "cbm_vs_vacuum_ev": ProvenanceTag.HEURISTIC,
        "vbm_vs_vacuum_ev": ProvenanceTag.HEURISTIC,
        "cbo_vs_tio2_ev": ProvenanceTag.HEURISTIC,
        "cbo_vs_sno2_ev": ProvenanceTag.HEURISTIC,
        "vbo_vs_niox_ev": ProvenanceTag.HEURISTIC,
        "best_cbo_ev": ProvenanceTag.HEURISTIC,
        "contact_voltage_penalty_v": ProvenanceTag.HEURISTIC,
        "antisite_voltage_penalty_v": ProvenanceTag.HEURISTIC,
        "ribbon_orientation_factor": ProvenanceTag.HEURISTIC,
        "critical_mineral_index": ProvenanceTag.HEURISTIC,
        "synthesis_practicality_score_100": ProvenanceTag.HEURISTIC,
    }

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
    sha256_digest: str


class Phase11BRealisticCommercializationDossier(_ProvenanceTaggedModel):
    """Phase 11B/11C: Non-radiative device sensitivity & 4-path commercialization techno-economic dossier."""

    _DEFAULT_PROVENANCE: ClassVar[Dict[str, ProvenanceTag]] = {
        "radiative_3l_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "radiative_3l_bif20_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "path0_si_mono_pce_percent": ProvenanceTag.ASSUMED,
        "path0_si_bif20_pce_percent": ProvenanceTag.ASSUMED,
        "path0_utility_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "path0_rooftop_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "conservative_2l_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "conservative_3l_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "base_top_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "base_top_voc_v": ProvenanceTag.COMPUTED_HERE,
        "base_bot_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "base_bot_mono_voc_v": ProvenanceTag.COMPUTED_HERE,
        "base_2l_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "base_3l_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "mature_2l_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "mature_3l_mono_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "gap_sens_2l_mono_low_percent": ProvenanceTag.COMPUTED_HERE,
        "gap_sens_2l_mono_high_percent": ProvenanceTag.COMPUTED_HERE,
        "gap_sens_3l_mono_low_percent": ProvenanceTag.COMPUTED_HERE,
        "gap_sens_3l_mono_high_percent": ProvenanceTag.COMPUTED_HERE,
        "path1_3l_bif20_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "path1_module_cost_usd_m2": ProvenanceTag.ASSUMED,
        "path1_utility_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "path1_rooftop_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "path2_2l_bif20_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "path2_module_cost_usd_m2": ProvenanceTag.ASSUMED,
        "path2_utility_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "path2_rooftop_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "path3_2t_bif20_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "path3_module_cost_usd_m2": ProvenanceTag.ASSUMED,
        "path3_utility_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE,
        "path4_bipv_window_pce_percent": ProvenanceTag.COMPUTED_HERE,
        "path4_dgu_cost_usd_m2": ProvenanceTag.ASSUMED,
        "path4_gross_margin_percent": ProvenanceTag.COMPUTED_HERE,
        "rouard_base_2l_diff_percent": ProvenanceTag.COMPUTED_HERE,
    }

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
    sha256_digest: str
