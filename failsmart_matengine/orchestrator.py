"""Multi-Agent State-Machine Campaign Orchestrator v2.0 with Blinded Redundancy & Runnable QE Decks."""

import json
from pathlib import Path
from typing import Any, Dict, List
from .independent_verifier import verify_candidate_dossier
from .inter_team_bus import InterTeamBus
from .ledger import ContrastiveFailureLedger
from .physics_calculators import IUPAC_ATOMIC_MASSES, compute_structure_from_cif
from .tools import (
    gate_a_adversarial_audit,
    stage1_generate_candidates,
    stage2_evaluate_stability,
    stage3_evaluate_synthesis_and_speciation,
    stage4_5_quantum_and_defects,
    stage5_optical_4t_tandem_simulation,
)


def generate_qe_hse06_soc_input(cand_dict: Dict[str, Any]) -> str:
    """Emit a complete, runnable Quantum ESPRESSO (pw.x) HSE06 + SOC input deck.

    Includes accurate IUPAC atomic weights in ATOMIC_SPECIES, explicit 3x3 lattice vectors
    in CELL_PARAMETERS (angstrom), and all unit-cell fractional coordinates in
    ATOMIC_POSITIONS (crystal) parsed directly from the verified CIF structure.
    """
    formula = cand_dict["formula_reduced"]
    els = cand_dict["elements"]
    struct = compute_structure_from_cif(cand_dict["cif_content"])
    nat = len(struct)
    ntyp = len(els)

    a_len, b_len, c_len = struct.lattice.abc
    kx = max(2, min(8, int(round(24.0 / max(a_len, 1.0)))))
    ky = max(2, min(8, int(round(24.0 / max(b_len, 1.0)))))
    kz = max(2, min(8, int(round(24.0 / max(c_len, 1.0)))))

    lines = [
        "! FailSmart-MatEngine v2.0 Auto-Generated Quantum ESPRESSO HSE06+SOC Input Deck",
        f"! Candidate: {cand_dict['candidate_id']} ({formula}) | Target: {cand_dict['target_layer']}",
        f"! Verified Space Group: {cand_dict['space_group_symbol']} (#{cand_dict['space_group_number']}) | nat = {nat}",
        "&CONTROL",
        "  calculation = 'scf',",
        f"  prefix = '{formula.lower()}',",
        "  outdir = './out/',",
        "  pseudo_dir = './pseudo_oncv_fr/',",
        "  tprnfor = .true.,",
        "  tstress = .true.,",
        "  etot_conv_thr = 1.0d-6,",
        "  forc_conv_thr = 1.0d-4,",
        "/",
        "&SYSTEM",
        "  ibrav = 0,",
        f"  nat = {nat},",
        f"  ntyp = {ntyp},",
        "  ecutwfc = 70.0,",
        "  ecutfock = 140.0,",
        "  noncolin = .true.,",
        "  lspinorb = .true.,",
        "  input_dft = 'hse',",
        "  nqx1 = 2, nqx2 = 2, nqx3 = 2,",
        "  x_gamma_extrapolation = .true.,",
        "/",
        "&ELECTRONS",
        "  conv_thr = 1.0d-8,",
        "  mixing_beta = 0.4,",
        "  adaptive_thr = .true.,",
        "/",
        "ATOMIC_SPECIES",
    ]
    for el in els:
        mass = IUPAC_ATOMIC_MASSES.get(el)
        if mass is None or mass <= 1.001:
            raise ValueError(f"Missing or invalid IUPAC atomic mass for element {el}: {mass}")
        lines.append(f"  {el:<3s}  {mass:10.4f}  {el}_ONCV_PBE_FR-1.2.upf")

    lines.append("CELL_PARAMETERS (angstrom)")
    for vec in struct.lattice.matrix:
        lines.append(f"  {vec[0]:14.8f}  {vec[1]:14.8f}  {vec[2]:14.8f}")

    lines.append("ATOMIC_POSITIONS (crystal)")
    for site in struct:
        fx, fy, fz = site.frac_coords % 1.0
        lines.append(f"  {site.specie.symbol:<3s}  {fx:12.8f}  {fy:12.8f}  {fz:12.8f}")

    lines.append("K_POINTS automatic")
    lines.append(f"  {kx} {ky} {kz} 0 0 0")
    return "\n".join(lines) + "\n"


def run_pilot_campaign(
    output_dir: str = "/home/antigravity/failsmart-matengine/outputs",
    include_ood: bool = True,
) -> Dict[str, Any]:
    """Execute Campaign v2.0 with Blinded Specification Redundancy, Stage 2b Gate & SMACT OOD Discovery."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    qe_dir = out_path / "qe_hse06_soc_decks"
    qe_dir.mkdir(parents=True, exist_ok=True)
    for old_f in qe_dir.glob("*"):
        old_f.unlink()

    bus = InterTeamBus()
    bus.reset_logs()

    ledger = ContrastiveFailureLedger()
    ledger.reset_to_historical_seeds()

    candidates = stage1_generate_candidates(include_ood=include_ood)

    bus.send_inter_team_message(
        sender_agent="pi_orchestrator",
        sender_division="Research",
        recipient_agent="chief_software_architect",
        recipient_division="Engineering",
        message_type="CAMPAIGN_V2_INIT",
        candidate_id=None,
        subject="Initialize Dual-Track v2.0 Campaign with Blinded Redundancy, Stage 2b Gate & SMACT OOD Sweep",
        payload={
            "total_candidates": len(candidates),
            "benchmark_candidates": 16,
            "smact_ood_candidates": len(candidates) - 16,
            "tracks": ["TOP_ACTIVE_GLASS_185EV", "BOTTOM_IR_075EV"],
        },
        model_tier="pro",
    )

    funnel_counts = {
        "stage1_generated": len(candidates),
        "stage2_dynamically_and_ion_stable": 0,
        "stage3_manufacturable": 0,
        "gate_a_promoted_to_dft": 0,
        "stage4_5_validated_finalists": 0,
        "redundancy_verifications_passed": 0,
    }

    campaign_records: List[Dict[str, Any]] = []
    finalists: List[Dict[str, Any]] = []

    for cand in candidates:
        cand_dump = cand.model_dump()
        stage1_dossier = {"candidate": cand_dump, "stage_reached": 1}
        ver_s1 = verify_candidate_dossier(stage1_dossier, raise_on_error=True)

        bus.send_inter_team_message(
            sender_agent="crystal_explorer",
            sender_division="Research",
            recipient_agent="physics_engine_engineer",
            recipient_division="Engineering",
            message_type="STAGE1_CRYSTAL_SPEC",
            candidate_id=cand.candidate_id,
            subject=f"Stage 1 Wyckoff 3D CIF & BVS GII for {cand.formula_reduced}",
            payload={
                "formula_reduced": cand.formula_reduced,
                "space_group_symbol": cand.space_group_symbol,
                "space_group_number": cand.space_group_number,
                "nsites_unit_cell": cand.nsites_unit_cell,
                "min_distance_ang": ver_s1["checks"]["cif_geometry"]["min_distance_ang"],
                "bvs_gii": cand.bond_valence_sum_deviation,
            },
            model_tier="pro",
        )

        # Stage 2 + Stage 2b: Hull, Born Elasticity, Phonopy, Debye & Cu+/Ag+ Ion Migration
        stab = stage2_evaluate_stability(cand)
        stab_dump = stab.model_dump()
        if not stab.passed_stage2:
            mode = stab.failure_reason.split(":")[0] if stab.failure_reason else "STAGE2_FAIL"
            s2_dossier = {
                "candidate": cand_dump,
                "stage_reached": 2,
                "stability": stab_dump,
            }
            ver_s2 = verify_candidate_dossier(s2_dossier, raise_on_error=True)
            bus.record_redundancy_verification(
                verifier_agent="redundancy_verifier_alpha",
                candidate_id=cand.candidate_id,
                formula=cand.formula_reduced,
                stage_evaluated=2,
                passed_all_checks=ver_s2["passed_all_redundancy_checks"],
                checks_detail=ver_s2["checks"],
                primary_sha256=bus.compute_sha256(stab_dump),
                independent_sha256=ver_s2["sha256_signature"],
            )
            funnel_counts["redundancy_verifications_passed"] += 1
            ledger.record_evaluation(
                candidate_id=cand.candidate_id,
                formula_reduced=cand.formula_reduced,
                target_layer=cand.target_layer,
                crystal_family=cand.crystal_family,
                space_group_number=cand.space_group_number,
                structural_dimensionality=cand.structural_dimensionality,
                cif_structure=cand.cif_content,
                embedding=cand.embedding_128d,
                stage_reached=2,
                status="REJECTED",
                primary_failure_mode=mode,
                e_above_hull_mev=stab.e_above_hull_0k_mev,
                min_phonon_freq_thz=stab.min_phonon_freq_thz,
                rxn_temp_celsius=0.0,
                competing_impurity_phases=stab.competing_hull_phases,
                pourbaix_max_dissolution_mol_l=0.0,
                active_layer_cost_usd_m2=0.0,
                adversarial_notes=stab.failure_reason or "",
            )
            campaign_records.append({
                "candidate": cand_dump,
                "stage_reached": 2,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": stab.failure_reason,
                "stability": stab_dump,
                "redundancy_verification": ver_s2,
            })
            continue

        funnel_counts["stage2_dynamically_and_ion_stable"] += 1

        # Stage 3: Synthesis Kinetics (<=500 C), Impurity Sinks, Pourbaix & $/m^2 Cost
        synth = stage3_evaluate_synthesis_and_speciation(cand, ledger)
        synth_dump = synth.model_dump()
        if not synth.passed_stage3:
            mode = synth.failure_reason.split(":")[0] if synth.failure_reason else "STAGE3_FAIL"
            s3_dossier = {
                "candidate": cand_dump,
                "stage_reached": 3,
                "stability": stab_dump,
                "synthesis": synth_dump,
            }
            ver_s3 = verify_candidate_dossier(s3_dossier, raise_on_error=True)
            bus.record_redundancy_verification(
                verifier_agent="redundancy_verifier_alpha",
                candidate_id=cand.candidate_id,
                formula=cand.formula_reduced,
                stage_evaluated=3,
                passed_all_checks=ver_s3["passed_all_redundancy_checks"],
                checks_detail=ver_s3["checks"],
                primary_sha256=bus.compute_sha256(synth_dump),
                independent_sha256=ver_s3["sha256_signature"],
            )
            funnel_counts["redundancy_verifications_passed"] += 1
            ledger.record_evaluation(
                candidate_id=cand.candidate_id,
                formula_reduced=cand.formula_reduced,
                target_layer=cand.target_layer,
                crystal_family=cand.crystal_family,
                space_group_number=cand.space_group_number,
                structural_dimensionality=cand.structural_dimensionality,
                cif_structure=cand.cif_content,
                embedding=cand.embedding_128d,
                stage_reached=3,
                status="REJECTED",
                primary_failure_mode=mode,
                e_above_hull_mev=stab.e_above_hull_0k_mev,
                min_phonon_freq_thz=stab.min_phonon_freq_thz,
                rxn_temp_celsius=synth.min_synthesis_temp_c,
                competing_impurity_phases=synth.competing_impurity_sinks,
                pourbaix_max_dissolution_mol_l=synth.pourbaix_max_dissolution_mol_l,
                active_layer_cost_usd_m2=synth.active_layer_cost_usd_m2,
                adversarial_notes=synth.failure_reason or "",
            )
            campaign_records.append({
                "candidate": cand_dump,
                "stage_reached": 3,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": synth.failure_reason,
                "stability": stab_dump,
                "synthesis": synth_dump,
                "redundancy_verification": ver_s3,
            })
            continue

        funnel_counts["stage3_manufacturable"] += 1

        # Gate A: Adversarial Red-Team Pre-DFT Audit
        audit_a = gate_a_adversarial_audit(cand, stab, synth)
        audit_a_dump = audit_a.model_dump()
        if audit_a.decision == "VETO_REJECT":
            mode = audit_a.primary_failure_mode or "ADVERSARIAL_VETO"
            ga_dossier = {
                "candidate": cand_dump,
                "stage_reached": 3,
                "stability": stab_dump,
                "synthesis": synth_dump,
                "gate_a": audit_a_dump,
            }
            ver_ga = verify_candidate_dossier(ga_dossier, raise_on_error=True)
            bus.record_redundancy_verification(
                verifier_agent="redundancy_verifier_alpha",
                candidate_id=cand.candidate_id,
                formula=cand.formula_reduced,
                stage_evaluated=3,
                passed_all_checks=ver_ga["passed_all_redundancy_checks"],
                checks_detail=ver_ga["checks"],
                primary_sha256=bus.compute_sha256(audit_a_dump),
                independent_sha256=ver_ga["sha256_signature"],
            )
            funnel_counts["redundancy_verifications_passed"] += 1
            ledger.record_evaluation(
                candidate_id=cand.candidate_id,
                formula_reduced=cand.formula_reduced,
                target_layer=cand.target_layer,
                crystal_family=cand.crystal_family,
                space_group_number=cand.space_group_number,
                structural_dimensionality=cand.structural_dimensionality,
                cif_structure=cand.cif_content,
                embedding=cand.embedding_128d,
                stage_reached=3,
                status="REJECTED",
                primary_failure_mode=mode,
                e_above_hull_mev=stab.e_above_hull_0k_mev,
                min_phonon_freq_thz=stab.min_phonon_freq_thz,
                rxn_temp_celsius=synth.min_synthesis_temp_c,
                competing_impurity_phases=synth.competing_impurity_sinks,
                pourbaix_max_dissolution_mol_l=synth.pourbaix_max_dissolution_mol_l,
                active_layer_cost_usd_m2=synth.active_layer_cost_usd_m2,
                adversarial_notes=audit_a.critique_summary,
            )
            campaign_records.append({
                "candidate": cand_dump,
                "stage_reached": 3,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": audit_a.critique_summary,
                "stability": stab_dump,
                "synthesis": synth_dump,
                "gate_a": audit_a_dump,
                "redundancy_verification": ver_ga,
            })
            continue

        funnel_counts["gate_a_promoted_to_dft"] += 1

        # Stage 4 & 5: Relativistic HSE06+SOC, Polaron, SRH Defects & Sequential 4T Optics
        elec = stage4_5_quantum_and_defects(cand)
        opt = stage5_optical_4t_tandem_simulation(cand, elec, synth)
        elec_dump = elec.model_dump()
        opt_dump = opt.model_dump()

        # Gate R2: Blinded Photon-Energy Simpson Quadrature, SQ Ceiling & Frohlich Verification
        full_dossier_for_ver = {
            "candidate": cand_dump,
            "stage_reached": 5,
            "stability": stab_dump,
            "synthesis": synth_dump,
            "gate_a": audit_a_dump,
            "electronics": elec_dump,
            "optics": opt_dump,
        }
        ver_s5 = verify_candidate_dossier(full_dossier_for_ver, raise_on_error=True)
        bus.record_redundancy_verification(
            verifier_agent="redundancy_verifier_alpha",
            candidate_id=cand.candidate_id,
            formula=cand.formula_reduced,
            stage_evaluated=5,
            passed_all_checks=ver_s5["passed_all_redundancy_checks"],
            checks_detail=ver_s5["checks"],
            primary_sha256=bus.compute_sha256(full_dossier_for_ver),
            independent_sha256=ver_s5["sha256_signature"],
        )
        funnel_counts["redundancy_verifications_passed"] += 1

        bus.send_inter_team_message(
            sender_agent="redundancy_verifier_alpha",
            sender_division="Engineering",
            recipient_agent="adversarial_critic",
            recipient_division="Research",
            message_type="GATE_R2_REDUNDANCY_CERTIFICATE",
            candidate_id=cand.candidate_id,
            subject=f"Blinded Dual-Redundancy Mathematical Certificate for {cand.formula_reduced}",
            payload={
                "passed_all_redundancy_checks": ver_s5["passed_all_redundancy_checks"],
                "slme_trapezoidal_vs_simpson_diff_pct": ver_s5["checks"]["slme_quadrature"]["abs_difference_percent"],
                "sq_ceiling_ok": ver_s5["checks"]["thermodynamic_sq_ceiling"]["passed"],
                "frohlich_alpha_diff": ver_s5["checks"]["frohlich_alpha"]["abs_difference"],
                "sha256_signature": ver_s5["sha256_signature"],
            },
            model_tier="pro",
        )

        if not elec.passed_stage4_and_5 or not opt.passed_optical_gate:
            reason = elec.failure_reason or opt.failure_reason or "STAGE4_5_FAIL"
            mode = reason.split(":")[0]
            ledger.record_evaluation(
                candidate_id=cand.candidate_id,
                formula_reduced=cand.formula_reduced,
                target_layer=cand.target_layer,
                crystal_family=cand.crystal_family,
                space_group_number=cand.space_group_number,
                structural_dimensionality=cand.structural_dimensionality,
                cif_structure=cand.cif_content,
                embedding=cand.embedding_128d,
                stage_reached=4,
                status="REJECTED",
                primary_failure_mode=mode,
                e_above_hull_mev=stab.e_above_hull_0k_mev,
                min_phonon_freq_thz=stab.min_phonon_freq_thz,
                rxn_temp_celsius=synth.min_synthesis_temp_c,
                competing_impurity_phases=synth.competing_impurity_sinks,
                pourbaix_max_dissolution_mol_l=synth.pourbaix_max_dissolution_mol_l,
                active_layer_cost_usd_m2=synth.active_layer_cost_usd_m2,
                hse06_soc_gap_ev=elec.hse06_soc_indirect_gap_ev,
                direct_gap_ev=elec.hse06_soc_direct_gap_ev,
                soc_splitting_ev=elec.soc_splitting_ev,
                max_carrier_eff_mass=max(elec.electron_eff_mass_m0, elec.hole_eff_mass_m0),
                frohlich_alpha=elec.frohlich_alpha,
                deepest_defect_ev=elec.deepest_defect_level_from_band_edge_ev,
                slme_percent=opt.standalone_slme_percent,
                sub_bandgap_transmittance_percent=opt.sub_bandgap_transmittance_percent,
                tandem_4t_efficiency_percent=opt.tandem_4t_total_eff_percent,
                adversarial_notes=reason,
            )
            campaign_records.append({
                "candidate": cand_dump,
                "stage_reached": 4,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": reason,
                "stability": stab_dump,
                "synthesis": synth_dump,
                "gate_a": audit_a_dump,
                "electronics": elec_dump,
                "optics": opt_dump,
                "redundancy_verification": ver_s5,
            })
            continue

        funnel_counts["stage4_5_validated_finalists"] += 1

        # Emit runnable Quantum ESPRESSO (pw.x) HSE06+SOC input deck & verified CIF
        qe_in = generate_qe_hse06_soc_input(cand_dump)
        (qe_dir / f"{cand.candidate_id}_{cand.formula_reduced}_hse06_soc.in").write_text(qe_in)
        (qe_dir / f"{cand.candidate_id}_{cand.formula_reduced}.cif").write_text(cand.cif_content)

        dossier = {
            "candidate": cand_dump,
            "stage_reached": 5,
            "status": "PROMOTED",
            "primary_failure_mode": None,
            "stability": stab_dump,
            "synthesis": synth_dump,
            "gate_a": audit_a_dump,
            "electronics": elec_dump,
            "optics": opt_dump,
            "redundancy_verification": ver_s5,
        }
        campaign_records.append(dossier)
        finalists.append(dossier)

        ledger.record_evaluation(
            candidate_id=cand.candidate_id,
            formula_reduced=cand.formula_reduced,
            target_layer=cand.target_layer,
            crystal_family=cand.crystal_family,
            space_group_number=cand.space_group_number,
            structural_dimensionality=cand.structural_dimensionality,
            cif_structure=cand.cif_content,
            embedding=cand.embedding_128d,
            stage_reached=5,
            status="PROMOTED",
            primary_failure_mode=None,
            e_above_hull_mev=stab.e_above_hull_0k_mev,
            min_phonon_freq_thz=stab.min_phonon_freq_thz,
            rxn_temp_celsius=synth.min_synthesis_temp_c,
            competing_impurity_phases=synth.competing_impurity_sinks,
            pourbaix_max_dissolution_mol_l=synth.pourbaix_max_dissolution_mol_l,
            active_layer_cost_usd_m2=synth.active_layer_cost_usd_m2,
            hse06_soc_gap_ev=elec.hse06_soc_indirect_gap_ev,
            direct_gap_ev=elec.hse06_soc_direct_gap_ev,
            soc_splitting_ev=elec.soc_splitting_ev,
            max_carrier_eff_mass=max(elec.electron_eff_mass_m0, elec.hole_eff_mass_m0),
            frohlich_alpha=elec.frohlich_alpha,
            deepest_defect_ev=elec.deepest_defect_level_from_band_edge_ev,
            slme_percent=opt.standalone_slme_percent,
            sub_bandgap_transmittance_percent=opt.sub_bandgap_transmittance_percent,
            tandem_4t_efficiency_percent=opt.tandem_4t_total_eff_percent,
            adversarial_notes=f"PASSED ALL GATES & BLINDED REDUNDANCY (SHA256: {ver_s5['sha256_signature'][:12]}): {audit_a.critique_summary}",
            full_dossier=dossier,
        )

    summary = {
        "version": "2.0.0",
        "funnel_counts": funnel_counts,
        "finalists": finalists,
        "all_campaign_records": campaign_records,
        "ledger_entries": ledger.fetch_all(),
    }
    (out_path / "pilot_campaign_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    res = run_pilot_campaign()
    print("Funnel Counts:", json.dumps(res["funnel_counts"], indent=2))
    print("\nPromoted Finalists (Blinded Dual-Redundancy Verified):")
    for f in res["finalists"]:
        c = f["candidate"]
        e = f["electronics"]
        o = f["optics"]
        s = f["synthesis"]
        st = f["stability"]
        v = f["redundancy_verification"]
        print(
            f"  - {c['candidate_id']} ({c['formula_reduced']}) [{c['target_layer']}]: "
            f"Eg={e['hse06_soc_indirect_gap_ev']:.2f} eV (dir {e['hse06_soc_direct_gap_ev']:.2f} eV), "
            f"E_mig={st['ion_migration_barrier_ev']:.2f} eV, T_synth={s['min_synthesis_temp_c']:.0f} C, "
            f"Cost=${s['active_layer_cost_usd_m2']:.4f}/m^2, SLME={o['standalone_slme_percent']:.2f}% "
            f"(SQ={o['shockley_queisser_limit_percent']:.2f}%), 2L={o['tandem_2layer_si_eff_percent']:.2f}%, "
            f"4T(std-Si)={o['tandem_4t_std_si_fca_eff_percent']:.2f}%, 4T(low-FCA)={o['tandem_4t_total_eff_percent']:.2f}%, "
            f"SHA256={v['sha256_signature'][:12]}"
        )
