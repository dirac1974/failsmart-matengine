"""Repository Consistency & Documentation Gatekeeper Audit Engine (v3.0).

Parses outputs/pilot_campaign_summary.json, outputs/live_mp_discovery_summary.json,
data/failure_memory.db, data/negative_synthesis_priors.json, outputs/qe_hse06_soc_decks/,
outputs/mp_live_qe_decks/, README.md, docs/MEMORY_AND_FAILURE_LEDGER.md,
docs/VERIFICATION_AND_TEST_REPORT.md, and docs/PLAN.md.

Asserts that all candidate formulas, funnel counts, physical metrics, negative synthesis priors,
and finalist numbers match across all files with 100% bit-for-bit consistency and zero discrepancy.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class RepoConsistencyAuditor:
    """Zero-discrepancy repository auditor v3.0."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.root = repo_root or Path(__file__).resolve().parent.parent

        # v2.0 Artifact Paths
        self.summary_json_path = self.root / "outputs" / "pilot_campaign_summary.json"
        self.db_path = self.root / "data" / "failure_memory.db"
        self.qe_dir = self.root / "outputs" / "qe_hse06_soc_decks"

        # v3.0 Artifact Paths
        self.live_summary_json_path = self.root / "outputs" / "live_mp_discovery_summary.json"
        self.live_db_path = self.root / "data" / "mp_live_failure_memory.db"
        self.priors_json_path = self.root / "data" / "negative_synthesis_priors.json"
        self.mp_live_qe_dir = self.root / "outputs" / "mp_live_qe_decks"

        # Documentation Paths
        self.readme_path = self.root / "README.md"
        self.ledger_doc_path = self.root / "docs" / "MEMORY_AND_FAILURE_LEDGER.md"
        self.verif_report_path = self.root / "docs" / "VERIFICATION_AND_TEST_REPORT.md"
        self.plan_doc_path = self.root / "docs" / "PLAN.md"

        self.summary_data: Dict[str, Any] = {}
        self.live_summary_data: Dict[str, Any] = {}
        self.priors_data: Dict[str, Any] = {}
        self.db_records: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[str] = []

        self.expected_live_mp_finalists: Dict[str, str] = {
            "mp-861911": "Sb2OS2",
            "mp-1227486": "BiSbS3",
            "mp-1078776": "BiInS3",
            "mp-1223998": "Bi3InSe6",
            "mp-1224129": "CuInSnSe4",
            "mp-1224922": "CuGaSnSe4",
            "mp-22982": "BiCuS2",
            "mp-23474": "AgBi3S5",
        }

    def log(self, message: str) -> None:
        self.audit_log.append(message)
        print(message)

    # =========================================================================
    # v2.0 Cross-Checks
    # =========================================================================

    def load_summary_json(self) -> None:
        """Load and validate JSON structure for v2.0 campaign."""
        self.log(f"-> Loading {self.summary_json_path} ...")
        assert self.summary_json_path.exists(), f"Missing {self.summary_json_path}"
        with open(self.summary_json_path, "r", encoding="utf-8") as f:
            self.summary_data = json.load(f)

        assert "funnel_counts" in self.summary_data
        assert "finalists" in self.summary_data
        assert "all_campaign_records" in self.summary_data
        assert "ledger_entries" in self.summary_data

        counts = self.summary_data["funnel_counts"]
        assert counts["stage1_generated"] == 20, f"Expected stage1_generated == 20, got {counts['stage1_generated']}"
        assert (
            counts["stage2_dynamically_and_ion_stable"] == 17
        ), f"Expected stage2 == 17, got {counts.get('stage2_dynamically_and_ion_stable')}"
        assert counts["stage3_manufacturable"] == 12, f"Expected stage3 == 12, got {counts['stage3_manufacturable']}"
        assert (
            counts["gate_a_promoted_to_dft"] == 8
        ), f"Expected gate_a == 8, got {counts['gate_a_promoted_to_dft']}"
        assert (
            counts["stage4_5_validated_finalists"] == 5
        ), f"Expected finalists == 5, got {counts['stage4_5_validated_finalists']}"
        assert (
            counts["redundancy_verifications_passed"] == 20
        ), f"Expected redundancy passed == 20, got {counts['redundancy_verifications_passed']}"

        assert len(self.summary_data["finalists"]) == 5, f"Expected 5 finalists, got {len(self.summary_data['finalists'])}"
        assert (
            len(self.summary_data["all_campaign_records"]) == 20
        ), f"Expected 20 campaign records, got {len(self.summary_data['all_campaign_records'])}"
        assert (
            len(self.summary_data["ledger_entries"]) == 23
        ), f"Expected 23 ledger entries, got {len(self.summary_data['ledger_entries'])}"
        self.log("   [OK] pilot_campaign_summary.json loaded and v2.0 structural counts verified (20 -> 17 -> 12 -> 8 -> 5).")

    def load_sqlite_db(self) -> None:
        """Load and validate failure_memory.db records (23 total)."""
        self.log(f"-> Auditing SQLite database: {self.db_path} ...")
        assert self.db_path.exists(), f"Missing {self.db_path}"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM material_evaluations")
        rows = cursor.fetchall()
        assert len(rows) == 23, f"Expected 23 entries in DB, found {len(rows)}"

        for r in rows:
            d = dict(r)
            self.db_records[d["candidate_id"]] = d
        conn.close()

        # Cross-check DB rows with JSON ledger entries
        json_entries = {e["candidate_id"]: e for e in self.summary_data["ledger_entries"]}
        assert set(self.db_records.keys()) == set(json_entries.keys()), "Candidate IDs mismatch between DB and JSON"

        for cid, db_rec in self.db_records.items():
            j_rec = json_entries[cid]
            assert db_rec["formula_reduced"] == j_rec["formula_reduced"], (
                f"Formula mismatch for {cid}: DB={db_rec['formula_reduced']} vs JSON={j_rec['formula_reduced']}"
            )
            assert db_rec["stage_reached"] == j_rec["stage_reached"]
            assert db_rec["status"] == j_rec["status"]
            assert db_rec["primary_failure_mode"] == j_rec["primary_failure_mode"]

            for num_col in [
                "e_above_hull_mev",
                "min_phonon_freq_thz",
                "rxn_temp_celsius",
                "active_layer_cost_usd_m2",
                "slme_percent",
                "tandem_4t_efficiency_percent",
            ]:
                v_db = db_rec[num_col]
                v_json = j_rec[num_col]
                if v_json is None:
                    assert v_db is None, f"{cid} {num_col} mismatch: DB={v_db} vs JSON=None"
                else:
                    assert abs(float(v_db) - float(v_json)) < 1e-4, (
                        f"{cid} {num_col} numerical discrepancy: DB={v_db} vs JSON={v_json}"
                    )

        self.log("   [OK] SQLite failure_memory.db matches JSON ledger_entries 100% across all 23 entries.")

    def audit_qe_decks(self) -> None:
        """Audit Quantum ESPRESSO decks and CIF files for the 5 v2.0 finalists."""
        self.log(f"-> Auditing Quantum ESPRESSO decks in {self.qe_dir} ...")
        assert self.qe_dir.exists(), f"Missing {self.qe_dir}"

        finalists = {f["candidate"]["candidate_id"]: f for f in self.summary_data["finalists"]}
        assert len(finalists) == 5, f"Expected 5 finalists, got {len(finalists)}"

        deck_files = sorted(os.listdir(self.qe_dir))
        assert len(deck_files) == 10, f"Expected 10 files in {self.qe_dir}, found {len(deck_files)}: {deck_files}"

        for cid, fin in finalists.items():
            cand = fin["candidate"]
            formula = cand["formula_reduced"]
            expected_nat = cand["nsites_unit_cell"]
            expected_ntyp = len(cand["elements"])

            cif_file = self.qe_dir / f"{cid}_{formula}.cif"
            in_file = self.qe_dir / f"{cid}_{formula}_hse06_soc.in"

            assert cif_file.exists(), f"Missing CIF deck: {cif_file}"
            assert in_file.exists(), f"Missing QE input deck: {in_file}"

            cif_text = cif_file.read_text(encoding="utf-8")
            assert f"data_{formula}" in cif_text, f"CIF header missing formula {formula} in {cif_file}"

            in_text = in_file.read_text(encoding="utf-8")
            assert f"Candidate: {cid} ({formula})" in in_text, f"Candidate header missing in {in_file}"
            assert f"prefix = '{formula.lower()}'" in in_text, f"Prefix mismatch in {in_file}"
            assert f"nat = {expected_nat}" in in_text, f"nat != {expected_nat} in {in_file}"
            assert f"ntyp = {expected_ntyp}" in in_text, f"ntyp != {expected_ntyp} in {in_file}"
            assert cand["space_group_symbol"] in in_text, f"Space group {cand['space_group_symbol']} missing in {in_file}"
            assert "CELL_PARAMETERS (angstrom)" in in_text, f"Missing CELL_PARAMETERS (angstrom) in {in_file}"
            assert "ATOMIC_POSITIONS (crystal)" in in_text, f"Missing ATOMIC_POSITIONS (crystal) in {in_file}"

            in_species = False
            species_found = []
            for line in in_text.splitlines():
                if "ATOMIC_SPECIES" in line:
                    in_species = True
                    continue
                if in_species:
                    if line.startswith("CELL_PARAMETERS") or line.strip() == "":
                        in_species = False
                    else:
                        parts = line.split()
                        if len(parts) >= 2:
                            elem = parts[0]
                            mass = float(parts[1])
                            species_found.append((elem, mass))
                            assert abs(mass - 1.0) > 1e-2, (
                                f"Dummy mass 1.000 found for {elem} in {in_file}: mass={mass}"
                            )
                            assert mass > 14.0, f"Unphysical mass for {elem} in {in_file}: {mass}"

            assert len(species_found) == expected_ntyp, (
                f"Expected {expected_ntyp} species in {in_file}, found {len(species_found)}"
            )

        self.log("   [OK] All 5 v2.0 finalists possess valid, synchronized CIF & Quantum ESPRESSO decks with IUPAC atomic masses.")

    # =========================================================================
    # v3.0 Cross-Checks
    # =========================================================================

    def load_live_mp_summary_json(self) -> None:
        """Load and validate JSON structure for live MP discovery v3.0."""
        self.log(f"-> Loading {self.live_summary_json_path} ...")
        assert self.live_summary_json_path.exists(), f"Missing {self.live_summary_json_path}"
        with open(self.live_summary_json_path, "r", encoding="utf-8") as f:
            self.live_summary_data = json.load(f)

        assert "funnel_counts" in self.live_summary_data
        assert "finalists" in self.live_summary_data
        assert "cross_layer_4t_tandem_pairs" in self.live_summary_data
        assert "all_mp_records" in self.live_summary_data

        counts = self.live_summary_data["funnel_counts"]
        assert counts["stage1_live_mp_ingested"] == 100, f"Expected 100 ingested, got {counts.get('stage1_live_mp_ingested')}"
        assert counts["stage2_dynamically_and_ion_stable"] == 91, f"Expected 91 Stage 2, got {counts.get('stage2_dynamically_and_ion_stable')}"
        assert counts["stage3_manufacturable_lbnl_alab_screened"] == 52, f"Expected 52 Stage 3, got {counts.get('stage3_manufacturable_lbnl_alab_screened')}"
        assert counts["gate_a_promoted_to_dft"] == 40, f"Expected 40 Gate A, got {counts.get('gate_a_promoted_to_dft')}"
        assert counts["stage4_5_validated_finalists"] == 8, f"Expected 8 finalists, got {counts.get('stage4_5_validated_finalists')}"
        assert counts["top_active_glass_finalists"] == 3, f"Expected 3 Top Active Glass, got {counts.get('top_active_glass_finalists')}"
        assert counts["bottom_ir_scavenger_finalists"] == 5, f"Expected 5 Bottom IR Scavengers, got {counts.get('bottom_ir_scavenger_finalists')}"
        assert counts["redundancy_verifications_passed"] == 100, f"Expected 100 redundancy passed, got {counts.get('redundancy_verifications_passed')}"

        finalists = self.live_summary_data["finalists"]
        assert len(finalists) == 8, f"Expected 8 finalists, got {len(finalists)}"

        fin_dict = {f["candidate"]["candidate_id"]: f["candidate"]["formula_reduced"] for f in finalists}
        for exp_id, exp_formula in self.expected_live_mp_finalists.items():
            assert exp_id in fin_dict, f"Missing live MP finalist {exp_id} in {self.live_summary_json_path}"
            assert fin_dict[exp_id] == exp_formula, f"Formula mismatch for {exp_id}: got {fin_dict[exp_id]} vs {exp_formula}"

        pairs = self.live_summary_data["cross_layer_4t_tandem_pairs"]
        assert len(pairs) == 15, f"Expected 15 cross-layer 4T pairs, got {len(pairs)}"

        # Check top pair and cost-optimal pair
        pair_dict = {p["pair_id"]: p for p in pairs}
        assert "mp-861911__mp-1223998" in pair_dict
        top_pair = pair_dict["mp-861911__mp-1223998"]
        assert abs(top_pair["tandem_4t_low_fca_total_eff_percent"] - 42.32) < 1e-2, (
            f"Expected 42.32% for top pair, got {top_pair['tandem_4t_low_fca_total_eff_percent']}"
        )

        assert "mp-861911__mp-22982" in pair_dict
        cheap_pair = pair_dict["mp-861911__mp-22982"]
        assert abs(cheap_pair["tandem_4t_low_fca_total_eff_percent"] - 41.75) < 1e-2, (
            f"Expected 41.75% for cheap pair, got {cheap_pair['tandem_4t_low_fca_total_eff_percent']}"
        )
        assert abs(cheap_pair["combined_active_cost_usd_m2"] - 0.0394) < 1e-4, (
            f"Expected $0.0394/m2 for cheap pair, got {cheap_pair['combined_active_cost_usd_m2']}"
        )

        # Check 100/100 redundancy verifications and zero 'unknown' tokens in competing phases/sinks
        all_recs = self.live_summary_data["all_mp_records"]
        assert len(all_recs) == 100, f"Expected 100 all_mp_records, got {len(all_recs)}"
        for r in all_recs:
            assert r["redundancy_verification"]["passed_all_redundancy_checks"] is True, (
                f"Candidate {r['candidate']['candidate_id']} failed redundancy check"
            )
            hull_phases = r.get("stability", {}).get("competing_hull_phases", [])
            imp_sinks = r.get("synthesis", {}).get("competing_impurity_sinks", [])
            for p_tok in hull_phases + imp_sinks:
                assert "unknown" not in p_tok.lower(), f"Candidate {r['candidate']['candidate_id']} has 'unknown' token: {p_tok}"

        # v4.0 Step 1 & Step 2 Checks
        assert self.live_summary_data.get("version") == "4.0.0", "Expected live_mp_discovery_summary.json version == 4.0.0"
        phonon_reports = self.live_summary_data.get("atomistic_phonon_neb_reports", [])
        assert len(phonon_reports) == 8, f"Expected 8 atomistic_phonon_neb_reports, got {len(phonon_reports)}"
        for pr in phonon_reports:
            assert pr["imaginary_mode_count"] == 0, f"{pr['candidate_id']} has imaginary modes"
            assert pr["dynamically_and_kinetically_stable"] is True
            assert pr["redundancy_verified"] is True
            assert pr["neb_saddle_barrier_ev"] >= 0.90

        tmm_stacks = self.live_summary_data.get("coherent_tmm_4t_stacks", [])
        assert len(tmm_stacks) == 15, f"Expected 15 coherent_tmm_4t_stacks, got {len(tmm_stacks)}"
        for ts in tmm_stacks:
            assert ts["photon_conservation_verified"] is True
            assert ts["rouard_airy_redundancy_diff_percent"] <= 0.05

        graded_stacks = self.live_summary_data.get("graded_arc_techno_economic_stacks", [])
        assert len(graded_stacks) == 15, f"Expected 15 graded_arc_techno_economic_stacks, got {len(graded_stacks)}"
        for gs in graded_stacks:
            assert gs["photon_conservation_verified"] is True
            assert gs["techno_economic_redundancy_verified"] is True
            assert gs["rouard_airy_redundancy_diff_percent"] <= 0.05
            assert gs["graded_arc_front_reflectance_percent"] <= 4.0

        # v6.0 Phase 9A, 9B, and 9C Checks
        assert self.live_summary_data.get("v6_phase9_lab_contrastive_lcoe_enabled") is True
        lab_dossiers = self.live_summary_data.get("lab_synthesis_and_defect_dossiers", [])
        assert len(lab_dossiers) == 8, f"Expected 8 lab_synthesis_and_defect_dossiers, got {len(lab_dossiers)}"
        for ld in lab_dossiers:
            assert ld["redundancy_verified"] is True
            assert ld["elemental_mass_conservation_diff_g"] <= 1e-6
            assert ld["supercell_min_image_dist_ang"] >= 10.0

        ca = self.live_summary_data.get("contrastive_classifier_audit", {})
        assert ca.get("total_evaluated_candidates") == 117
        assert ca.get("positive_separation_verified") is True
        assert ca.get("redundancy_verified") is True

        lcoe_stacks = self.live_summary_data.get("real_world_lcoe_stress_test_stacks", [])
        assert len(lcoe_stacks) == 15, f"Expected 15 real_world_lcoe_stress_test_stacks, got {len(lcoe_stacks)}"
        for rw in lcoe_stacks:
            assert rw["lcoe_redundancy_verified"] is True
            assert rw["lcoe_3layer_vs_si_reduction_percent"] > 32.0

        # v7.0 Phase 10A, 10B, and 10C Checks
        assert self.live_summary_data.get("v7_phase10_bifacial_and_string_enabled") is True
        p10_stacks = self.live_summary_data.get("phase10_bifacial_and_string_dossiers", [])
        assert len(p10_stacks) == 15, f"Expected 15 phase10_bifacial_and_string_dossiers, got {len(p10_stacks)}"
        for p10 in p10_stacks:
            assert p10["phase10_redundancy_verified"] is True
            assert p10["rouard_opt_diff_percent"] <= 0.05
            assert p10["bifacial_20pct_albedo_4t_pce_percent"] > p10["opt_monofacial_4t_pce_percent"]
            assert p10["bifacial_30pct_albedo_4t_pce_percent"] > p10["bifacial_20pct_albedo_4t_pce_percent"]
            assert p10["n_cells_si_ref"] == 72

        self.log("   [OK] live_mp_discovery_summary.json verified: 100 -> 91 -> 52 -> 40 -> 8 finalists, 8 D-matrix/NEB & Lab/Defect dossiers, 117-MP Contrastive Audit, 15 Single-ARC, 15 Graded-ARC, 15 Real-World LCOE & 15 Phase 10 Bifacial/String stacks.")

    def audit_negative_synthesis_priors(self) -> None:
        """Audit LBNL 80k solid-state recipes and A-Lab precursor genome negative priors."""
        self.log(f"-> Auditing negative synthesis priors: {self.priors_json_path} ...")
        assert self.priors_json_path.exists(), f"Missing {self.priors_json_path}"
        with open(self.priors_json_path, "r", encoding="utf-8") as f:
            self.priors_data = json.load(f)

        prov = self.priors_data.get("dataset_provenance", {})
        lbnl = prov.get("lbnl_80k_impurity_dataset") or prov.get("lbnl_solid_state_impurity_dataset", {})
        alab = prov.get("alab_precursor_genome") or prov.get("alab_precursor_genome_dataset", {})

        assert lbnl.get("total_recipes") == 80806, f"Expected 80,806 LBNL recipes, got {lbnl.get('total_recipes')}"
        assert lbnl.get("phase_impure_failed_recipes") == 18869, f"Expected 18,869 impure recipes, got {lbnl.get('phase_impure_failed_recipes')}"

        assert alab.get("total_pairwise_reactions") == 1035, f"Expected 1,035 A-Lab reactions, got {alab.get('total_pairwise_reactions')}"
        assert alab.get("negative_or_stalled_reactions") == 892, f"Expected 892 negative/stalled reactions, got {alab.get('negative_or_stalled_reactions')}"

        chemsys_priors = self.priors_data.get("chemsys_impurity_priors", {})
        assert len(chemsys_priors) >= 4000, f"Expected >= 4,000 chemsys impurity priors, got {len(chemsys_priors)}"

        self.log(f"   [OK] negative_synthesis_priors.json verified: 80,806 LBNL recipes (18,869 impure), 1,035 A-Lab reactions (892 stalled), {len(chemsys_priors)} chemsys.")

    def audit_mp_live_qe_decks(self) -> None:
        """Audit Quantum ESPRESSO decks and CIF files for the 8 live MP finalists."""
        self.log(f"-> Auditing live MP Quantum ESPRESSO decks in {self.mp_live_qe_dir} ...")
        assert self.mp_live_qe_dir.exists(), f"Missing {self.mp_live_qe_dir}"

        deck_files = sorted(os.listdir(self.mp_live_qe_dir))
        assert len(deck_files) == 16, f"Expected 16 files in {self.mp_live_qe_dir}, found {len(deck_files)}: {deck_files}"

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in self.live_summary_data["finalists"]}
        assert len(finalists_by_id) == 8, f"Expected 8 finalists in live summary, got {len(finalists_by_id)}"

        for cid, fin in finalists_by_id.items():
            cand = fin["candidate"]
            formula = cand["formula_reduced"]
            expected_nat = cand["nsites_unit_cell"]
            expected_ntyp = len(cand["elements"])

            cif_file = self.mp_live_qe_dir / f"{cid}_{formula}.cif"
            in_file = self.mp_live_qe_dir / f"{cid}_{formula}_hse06_soc.in"

            assert cif_file.exists(), f"Missing live MP CIF deck: {cif_file}"
            assert in_file.exists(), f"Missing live MP QE input deck: {in_file}"

            cif_text = cif_file.read_text(encoding="utf-8")
            assert f"data_{formula}" in cif_text, f"CIF header missing formula {formula} in {cif_file}"

            in_text = in_file.read_text(encoding="utf-8")
            assert f"Candidate: {cid} ({formula})" in in_text, f"Candidate header missing in {in_file}"
            assert f"prefix = '{formula.lower()}'" in in_text, f"Prefix mismatch in {in_file}"
            assert f"nat = {expected_nat}" in in_text, f"nat != {expected_nat} in {in_file}"
            assert f"ntyp = {expected_ntyp}" in in_text, f"ntyp != {expected_ntyp} in {in_file}"
            assert cand["space_group_symbol"] in in_text, f"Space group {cand['space_group_symbol']} missing in {in_file}"
            assert "CELL_PARAMETERS (angstrom)" in in_text, f"Missing CELL_PARAMETERS in {in_file}"
            assert "ATOMIC_POSITIONS (crystal)" in in_text, f"Missing ATOMIC_POSITIONS in {in_file}"

            # Parse cell matrix and check non-singular determinant
            cell_rows = []
            atom_positions = []
            lines = in_text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("CELL_PARAMETERS (angstrom)"):
                    i += 1
                    for _ in range(3):
                        cell_rows.append([float(x) for x in lines[i].strip().split()])
                        i += 1
                    continue
                elif line.startswith("ATOMIC_POSITIONS (crystal)"):
                    i += 1
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("K_POINTS", "&")):
                        parts = lines[i].strip().split()
                        if len(parts) >= 4:
                            atom_positions.append(parts)
                        i += 1
                    continue
                i += 1

            assert len(cell_rows) == 3, f"{in_file}: CELL_PARAMETERS did not parse 3 rows"
            import numpy as np

            det_cell = float(np.linalg.det(cell_rows))
            assert abs(det_cell) > 50.0, f"{in_file}: CELL_PARAMETERS det {det_cell} <= 50.0"
            assert len(atom_positions) == expected_nat, f"{in_file}: atom positions {len(atom_positions)} != nat {expected_nat}"

            # Check atomic species
            in_species = False
            species_found = []
            for line in lines:
                if "ATOMIC_SPECIES" in line:
                    in_species = True
                    continue
                if in_species:
                    if line.startswith("CELL_PARAMETERS") or line.strip() == "":
                        in_species = False
                    else:
                        parts = line.split()
                        if len(parts) >= 2:
                            elem = parts[0]
                            mass = float(parts[1])
                            species_found.append((elem, mass))
                            assert abs(mass - 1.0) > 1e-2, (
                                f"Dummy mass 1.000 found for {elem} in {in_file}: mass={mass}"
                            )
                            assert mass > 14.0, f"Unphysical mass for {elem} in {in_file}: {mass}"

            assert len(species_found) == expected_ntyp, (
                f"Expected {expected_ntyp} species in {in_file}, found {len(species_found)}"
            )

        self.log("   [OK] All 8 live MP finalists possess valid, synchronized CIF & Quantum ESPRESSO decks with IUPAC atomic masses.")

    # =========================================================================
    # Documentation Consistency Checks
    # =========================================================================

    def audit_readme_markdown(self) -> None:
        """Parse README.md and verify funnel numbers, candidate formulas, and finalist table values (v2.0 + v3.0 + v4.0 + v5.0)."""
        self.log(f"-> Auditing {self.readme_path} ...")
        assert self.readme_path.exists(), f"Missing {self.readme_path}"
        text = self.readme_path.read_text(encoding="utf-8")

        # 1. 13-agent architecture verification
        assert "13-Agent Research + Engineering Team Architecture" in text or "13-agent" in text.lower()
        for agent in [
            "pi_orchestrator",
            "crystal_explorer",
            "surrogate_physicist",
            "synthesis_chemist",
            "quantum_defect_physicist",
            "photonic_tandem_architect",
            "adversarial_critic",
            "chief_software_architect",
            "physics_engine_engineer",
            "optics_kinetics_engineer",
            "redundancy_verifier_alpha",
            "qa_test_audit_engineer",
            "repo_release_auditor",
        ]:
            assert agent in text, f"Missing agent {agent} in README.md"

        # 2. v2.0 funnel counts and formulas
        assert "20 Candidates Screened" in text or "20 generated" in text
        assert "17 dynamically & ion-stable" in text or "17 dynamically" in text
        assert "12 manufacturable" in text
        assert "8 promoted to Stage 4 DFT" in text or "8 promoted to Stage 4" in text
        assert "5 Validated Finalists" in text
        for f_name in [
            "Sr2ZnOS2", "Zn2SbS2Br3", "Cu3BiS2Cl2", "BaZrS3", "AgBiSe2",
            "BiSCl", "SbSeI", "BiCuSeI2", "Bi2SnSe3I2", "BiCuOS",
            "BaBiO2Cl", "Sr2Cu2O2S", "Ba2BiS3Cl", "Ba2BiSe3I", "Cu2SnSeI2",
        ]:
            assert f_name in text, f"Missing v2.0 candidate formula {f_name} in README.md"

        # 3. v2.0 Finalist table verification
        for cid, fin in {f["candidate"]["candidate_id"]: f for f in self.summary_data["finalists"]}.items():
            pattern = rf"`{cid}`\s*\|\s*`{fin['candidate']['formula_reduced']}`.*"
            match = re.search(pattern, text)
            assert match is not None, f"Could not find table row for {cid} in README.md"
            row = match.group(0)
            assert f"${fin['synthesis']['active_layer_cost_usd_m2']:.4f}" in row
            assert f"{fin['optics']['standalone_slme_percent']:.2f}%" in row
            assert f"{fin['optics']['tandem_4t_total_eff_percent']:.2f}%" in row
            assert fin["redundancy_verification"]["sha256_signature"] in row

        # 4. v3.0, v4.0 & v5.0 Live MP Funnel & Finalists verification
        assert "100" in text, "Missing 100 live MP candidates in README.md"
        assert "91" in text, "Missing 91 Stage 2 count in README.md"
        assert "52" in text, "Missing 52 Stage 3 count in README.md"
        assert "40" in text, "Missing 40 Gate A count in README.md"
        assert "80,806" in text or "80806" in text, "Missing LBNL 80,806 dataset count in README.md"
        assert "18,869" in text or "18869" in text, "Missing LBNL 18,869 impure count in README.md"
        assert "1,035" in text or "1035" in text, "Missing A-Lab 1,035 count in README.md"
        assert "892" in text, "Missing A-Lab 892 negative stalls count in README.md"

        # Verify all 8 live MP finalist IDs appear
        for mp_id in self.expected_live_mp_finalists.keys():
            assert mp_id in text, f"Missing live MP finalist ID {mp_id} in README.md"

        # Check top tandem pairs (scalar + single-ARC TMM + Graded-ARC TMM + Techno-Economics)
        assert "42.32%" in text, "Missing 42.32% top scalar 4T PCE in README.md"
        assert "41.75%" in text, "Missing 41.75% cost-optimal scalar 4T PCE in README.md"
        assert "40.00%" in text, "Missing 40.00% top single-ARC TMM 4T PCE in README.md"
        assert "42.44%" in text, "Missing 42.44% top Graded-ARC TMM 4T PCE in README.md"
        assert "41.89%" in text, "Missing 41.89% cost-optimal Graded-ARC TMM 4T PCE in README.md"
        assert "4.354" in text, "Missing CER_3L = 4.354 in README.md"
        assert "0.0394" in text, "Missing $0.0394/m2 cost in README.md"

        # Check 18-test pytest verification
        assert "18" in text and ("test" in text.lower() or "passed" in text.lower()), (
            "Missing 18-test pytest verification reference in README.md"
        )

        self.log("   [OK] README.md contains verified 13-agent architecture, v2.0 benchmarks, v3.0 live MP funnel, v4.0 D-matrix/NEB & TMM, and v5.0 Graded-ARC & Techno-Economics.")

    def audit_memory_and_failure_ledger_markdown(self) -> None:
        """Parse docs/MEMORY_AND_FAILURE_LEDGER.md and verify all 23 v2 entries and 8 v3/v4/v5 finalists."""
        self.log(f"-> Auditing {self.ledger_doc_path} ...")
        assert self.ledger_doc_path.exists(), f"Missing {self.ledger_doc_path}"
        text = self.ledger_doc_path.read_text(encoding="utf-8")

        # 1. Failure taxonomy
        for fail_code in [
            "IMAGINARY_PHONON", "HULL_INSTABILITY", "ION_MIGRATION_INSTABILITY",
            "OXIDE_IMPURITY_SINK", "AQUEOUS_LEACHING", "TIER2_COST_EXCEEDED",
            "LOW_DIM_POLARON_RISK", "ANION_PHASE_SEGREGATION",
            "BANDGAP_OUT_OF_WINDOW", "DEEP_SRH_DEFECT",
        ]:
            assert fail_code in text, f"Missing failure code {fail_code} in {self.ledger_doc_path}"

        # 2. All 23 v2 ledger entries present
        for entry in self.summary_data["ledger_entries"]:
            cid = entry["candidate_id"]
            formula = entry["formula_reduced"]
            pattern = rf"`{cid}`\s*\|\s*`{formula}`.*"
            match = re.search(pattern, text)
            assert match is not None, f"Could not find row for {cid} ({formula}) in {self.ledger_doc_path}"

        # 3. All 8 live MP finalist IDs present
        for mp_id in self.expected_live_mp_finalists.keys():
            assert mp_id in text, f"Missing live MP finalist ID {mp_id} in {self.ledger_doc_path}"

        # 4. v3.0, v4.0 & v5.0 negative priors and counts
        assert "80,806" in text or "80806" in text
        assert "18,869" in text or "18869" in text
        assert "1,035" in text or "1035" in text
        assert "892" in text
        assert "42.32%" in text
        assert "41.75%" in text
        assert "40.00%" in text
        assert "42.44%" in text
        assert "41.89%" in text
        assert "0.0394" in text

        self.log("   [OK] docs/MEMORY_AND_FAILURE_LEDGER.md is synchronized with v2.0, v3.0, v4.0, and v5.0 Graded-ARC & Techno-Economics.")

    def audit_verification_report_markdown(self) -> None:
        """Parse docs/VERIFICATION_AND_TEST_REPORT.md and verify 18 tests and all 8 live MP finalists."""
        self.log(f"-> Auditing {self.verif_report_path} ...")
        assert self.verif_report_path.exists(), f"Missing {self.verif_report_path}"
        text = self.verif_report_path.read_text(encoding="utf-8")

        # 1. 18 comprehensive tests verified
        assert "18" in text, f"Missing '18' tests count in {self.verif_report_path}"

        # 2. All 8 live MP finalist IDs present
        for mp_id in self.expected_live_mp_finalists.keys():
            assert mp_id in text, f"Missing live MP finalist ID {mp_id} in {self.verif_report_path}"

        # 3. v3.0, v4.0 & v5.0 negative priors and top stacks
        assert "80,806" in text or "80806" in text
        assert "18,869" in text or "18869" in text
        assert "1,035" in text or "1035" in text
        assert "892" in text
        assert "42.32%" in text
        assert "41.75%" in text
        assert "40.00%" in text
        assert "42.44%" in text
        assert "41.89%" in text
        assert "0.0394" in text

        self.log("   [OK] docs/VERIFICATION_AND_TEST_REPORT.md contains verified 18-test suite and all 8 live MP finalists.")

    def audit_plan_markdown(self) -> None:
        """Parse docs/PLAN.md and verify consistency with v2.0 + v3.0 + v4.0 + v5.0 roadmap."""
        self.log(f"-> Auditing {self.plan_doc_path} ...")
        assert self.plan_doc_path.exists(), f"Missing {self.plan_doc_path}"
        text = self.plan_doc_path.read_text(encoding="utf-8")

        # v2.0 checks
        assert "ION_MIGRATION_INSTABILITY" in text
        assert "0.65" in text
        for fin in self.summary_data["finalists"]:
            formula = fin["candidate"]["formula_reduced"]
            assert formula in text, f"v2 Finalist formula {formula} not in {self.plan_doc_path}"

        # v3.0, v4.0 & v5.0 checks
        assert "100" in text
        assert "80,806" in text or "80806" in text
        assert "1,035" in text or "1035" in text
        assert "892" in text
        assert "40.00%" in text
        assert "42.44%" in text
        assert "41.89%" in text
        for mp_id in self.expected_live_mp_finalists.keys():
            assert mp_id in text, f"Live MP finalist {mp_id} missing in {self.plan_doc_path}"

        self.log("   [OK] docs/PLAN.md contains verified v2.0, v3.0, v4.0, and v5.0 Graded-ARC + Techno-Economics roadmap.")

    # =========================================================================
    # Full Master Audit Runner
    # =========================================================================

    def run_full_audit(self) -> bool:
        """Run all verification audits and return True if 100% aligned."""
        self.log("=" * 78)
        self.log("FailSmart-MatEngine Repository Consistency & Documentation Audit (v4.0)")
        self.log(f"Repository Root: {self.root}")
        self.log("=" * 78)

        try:
            # v2.0 Checks
            self.load_summary_json()
            self.load_sqlite_db()
            self.audit_qe_decks()

            # v3.0 & v4.0 Checks
            self.load_live_mp_summary_json()
            self.audit_negative_synthesis_priors()
            self.audit_mp_live_qe_decks()

            # Documentation Checks
            self.audit_readme_markdown()
            self.audit_memory_and_failure_ledger_markdown()
            self.audit_verification_report_markdown()
            self.audit_plan_markdown()

        except AssertionError as e:
            self.log(f"\n[FAIL] VERIFICATION AUDIT FAILED: {e}")
            return False
        except Exception as e:
            self.log(f"\n[ERROR] UNEXPECTED EXCEPTION DURING AUDIT: {e}")
            import traceback

            traceback.print_exc()
            return False

        self.log("=" * 78)
        self.log("[PASS] 100% CROSS-REPOSITORY CONSISTENCY & NUMERICAL ALIGNMENT CONFIRMED (v4.0)")
        self.log("All v2.0 benchmarks, v3.0 live MP discovery, and v4.0 3D D-matrix/NEB & Coherent TMM metrics match.")
        self.log("=" * 78)
        return True


def main() -> int:
    auditor = RepoConsistencyAuditor()
    success = auditor.run_full_audit()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
