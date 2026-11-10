"""Multi-Agent State-Machine Campaign Orchestrator & Quantum ESPRESSO Deck Generator."""

import json
from pathlib import Path
from typing import Any, Dict, List
from .ledger import ContrastiveFailureLedger
from .tools import (
    gate_a_adversarial_audit,
    stage1_generate_candidates,
    stage2_evaluate_stability,
    stage3_evaluate_synthesis_and_speciation,
    stage4_5_quantum_and_defects,
    stage5_optical_4t_tandem_simulation,
)


def generate_qe_hse06_soc_input(cand_dict: Dict[str, Any]) -> str:
    """Emit a custodian-compatible Quantum ESPRESSO (pw.x) HSE06 + SOC input deck."""
    formula = cand_dict["formula_reduced"]
    els = cand_dict["elements"]
    stoich = cand_dict["stoichiometry"]
    nat = sum(stoich.values())
    ntyp = len(els)

    lines = [
        f"! FailSmart-MatEngine Auto-Generated Quantum ESPRESSO HSE06+SOC Input Deck",
        f"! Candidate: {cand_dict['candidate_id']} ({formula}) | Target: {cand_dict['target_layer']}",
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
        lines.append(f"  {el}  1.000  {el}_ONCV_PBE_FR-1.2.upf")
    lines.append("K_POINTS automatic")
    lines.append("  6 6 4 0 0 0")
    return "\n".join(lines)


def run_pilot_campaign(output_dir: str = "/home/antigravity/failsmart-matengine/outputs") -> Dict[str, Any]:
    """Execute Pilot Campaign #1 across all 5 stages and 2 Adversarial Red-Team Gates."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    qe_dir = out_path / "qe_hse06_soc_decks"
    qe_dir.mkdir(parents=True, exist_ok=True)

    ledger = ContrastiveFailureLedger()
    candidates = stage1_generate_candidates()

    funnel_counts = {
        "stage1_generated": len(candidates),
        "stage2_dynamically_stable": 0,
        "stage3_manufacturable": 0,
        "gate_a_promoted_to_dft": 0,
        "stage4_5_validated_finalists": 0,
    }

    campaign_records: List[Dict[str, Any]] = []
    finalists: List[Dict[str, Any]] = []

    for cand in candidates:
        # Stage 2: Surrogate Physics (MACE + Phonopy + Convex Hull)
        stab = stage2_evaluate_stability(cand)
        if not stab.passed_stage2:
            mode = stab.failure_reason.split(":")[0] if stab.failure_reason else "STAGE2_FAIL"
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
                "candidate": cand.dict(),
                "stage_reached": 2,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": stab.failure_reason,
                "stability": stab.dict(),
            })
            continue

        funnel_counts["stage2_dynamically_stable"] += 1

        # Stage 3: Synthesis Kinetics (<500 C), Impurity Sinks, Pourbaix & $/m^2 Cost
        synth = stage3_evaluate_synthesis_and_speciation(cand, ledger)
        if not synth.passed_stage3:
            mode = synth.failure_reason.split(":")[0] if synth.failure_reason else "STAGE3_FAIL"
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
                "candidate": cand.dict(),
                "stage_reached": 3,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": synth.failure_reason,
                "stability": stab.dict(),
                "synthesis": synth.dict(),
            })
            continue

        funnel_counts["stage3_manufacturable"] += 1

        # Gate A: Adversarial Red-Team Pre-DFT Audit
        audit_a = gate_a_adversarial_audit(cand, stab, synth)
        if audit_a.decision == "VETO_REJECT":
            mode = audit_a.primary_failure_mode or "ADVERSARIAL_VETO"
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
                "candidate": cand.dict(),
                "stage_reached": 3,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": audit_a.critique_summary,
                "stability": stab.dict(),
                "synthesis": synth.dict(),
                "gate_a": audit_a.dict(),
            })
            continue

        funnel_counts["gate_a_promoted_to_dft"] += 1

        # Stage 4 & 5: Relativistic HSE06+SOC, Carrier Transport, Polaron & Killer Defect Audit
        elec = stage4_5_quantum_and_defects(cand)
        opt = stage5_optical_4t_tandem_simulation(cand, elec, synth)

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
                "candidate": cand.dict(),
                "stage_reached": 4,
                "status": "REJECTED",
                "primary_failure_mode": mode,
                "reason": reason,
                "stability": stab.dict(),
                "synthesis": synth.dict(),
                "gate_a": audit_a.dict(),
                "electronics": elec.dict(),
                "optics": opt.dict(),
            })
            continue

        funnel_counts["stage4_5_validated_finalists"] += 1

        # Write Quantum ESPRESSO HSE06+SOC input deck & CIF for promoted finalist
        qe_in = generate_qe_hse06_soc_input(cand.dict())
        (qe_dir / f"{cand.candidate_id}_{cand.formula_reduced}_hse06_soc.in").write_text(qe_in)
        (qe_dir / f"{cand.candidate_id}_{cand.formula_reduced}.cif").write_text(cand.cif_content)

        dossier = {
            "candidate": cand.dict(),
            "stage_reached": 5,
            "status": "PROMOTED",
            "primary_failure_mode": None,
            "stability": stab.dict(),
            "synthesis": synth.dict(),
            "gate_a": audit_a.dict(),
            "electronics": elec.dict(),
            "optics": opt.dict(),
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
            adversarial_notes=f"PASSED ALL GATES: {audit_a.critique_summary}",
            full_dossier=dossier,
        )

    summary = {
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
    print("\nPromoted Finalists:")
    for f in res["finalists"]:
        c = f["candidate"]
        e = f["electronics"]
        o = f["optics"]
        s = f["synthesis"]
        print(
            f"  - {c['candidate_id']} ({c['formula_reduced']}) [{c['target_layer']}]: "
            f"Eg(HSE06+SOC)={e['hse06_soc_indirect_gap_ev']:.2f} eV (dir {e['hse06_soc_direct_gap_ev']:.2f} eV), "
            f"T_synth={s['min_synthesis_temp_c']:.0f} C, Cost=${s['active_layer_cost_usd_m2']:.3f}/m^2, "
            f"SLME={o['standalone_slme_percent']:.1f}%, 4T Stack Eff={o['tandem_4t_total_eff_percent']:.2f}%"
        )
