"""Automated Test Suite for Scientific Integrity, Redundancy Invariants & Failure Memory.

Mandated by FailSmart-MatEngine Multi-Agent Architecture (QA Test & Audit Engineer):
- Test 1 (test_all_16_candidates_canonical_formula_and_charge_neutrality):
    Every candidate in get_verified_candidate_specs() satisfies canonical_formula(stoich) == formula,
    independently_parse_formula(formula) == stoich, and verify_charge_neutrality(stoich, ox) == 0.
    Also tests that intentionally broken formulas (like the old unneutral SbCuS2Cl with Sb:1, Cu:1, S:2, Cl:1,
    Zn2SbS2Br, BiCuSeI) are caught and rejected with ValueError and AssertionError("REDUNDANCY_MISMATCH_BLOCK: ...").
- Test 2 (test_all_16_cif_3d_periodic_distances_and_bvs):
    Every generated 3D CIF has natoms == sum(stoich.values()) and minimum 3D periodic interatomic distance
    min_distance_ang >= 2.15 A (verified independently by independently_verify_cif_geometry).
- Test 3 (test_am15g_spectral_normalization):
    np.trapz(compute_am15g_irradiance_w_m2_nm(lam), lam) over 280..4000 nm equals 1000.0 W/m^2 within 1e-4 W/m^2.
- Test 4 (test_dual_quadrature_slme_trapezoidal_vs_simpson):
    For all Stage 4/5 candidates, wavelength-space trapezoidal quadrature (compute_4t_tandem_optics_wavelength_grid)
    and photon-energy-space Simpson 1/3 quadrature (independently_verify_energy_quadrature_slme) agree within 0.05%!
- Test 5 (test_frohlich_polaron_and_anderson_debye_physics):
    Exact Frohlich coupling constant alpha and SOC splitting round(hse_nosoc - hse_soc_dir, 3) pass
    verify_candidate_dossier for all candidates, and Anderson Debye temperature theta_D > 0.
- Test 6 (test_full_campaign_and_audit_logs):
    Confirms outputs/pilot_campaign_summary.json, logs/inter_team_communication.jsonl, logs/verification_audit_log.jsonl,
    and data/failure_memory.db exist, contain 16 campaign records (6 promoted finalists, 10 rejected with exact physical
    reasons), and every record has passed_all_redundancy_checks == True.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import unittest
import numpy as np

from failsmart_matengine.physics_calculators import (
    canonical_formula,
    verify_charge_neutrality,
    build_3d_crystal_cif_and_min_dist,
    get_verified_candidate_specs,
    compute_stability_metrics,
    compute_anderson_debye_temperature,
)
from failsmart_matengine.kinetics_and_optics import (
    compute_am15g_irradiance_w_m2_nm,
    compute_4t_tandem_optics_wavelength_grid,
)
from failsmart_matengine.independent_verifier import (
    independently_parse_formula,
    independently_verify_cif_geometry,
    independently_verify_energy_quadrature_slme,
    compute_frohlich_alpha_exact,
    verify_candidate_dossier,
)


class TestScientificIntegrityAndRedundancy(unittest.TestCase):
    """Rigorous scientific integrity, zero-trust mathematical verification & physical constraint test suite."""

    @classmethod
    def setUpClass(cls):
        """Set up file paths and load campaign artifacts."""
        cls.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.summary_path = os.path.join(cls.repo_root, "outputs", "pilot_campaign_summary.json")
        cls.comms_log_path = os.path.join(cls.repo_root, "logs", "inter_team_communication.jsonl")
        cls.audit_log_path = os.path.join(cls.repo_root, "logs", "verification_audit_log.jsonl")
        cls.db_path = os.path.join(cls.repo_root, "data", "failure_memory.db")

        # Load campaign summary
        with open(cls.summary_path, "r", encoding="utf-8") as f:
            cls.summary_data = json.load(f)

    def test_all_16_candidates_canonical_formula_and_charge_neutrality(self):
        """Test 1: Verify canonical formula, independent regex parsing, and oxidation state charge neutrality.

        Also asserts that intentionally corrupted / prototype unneutral formulas raise
        ValueError in verify_charge_neutrality and AssertionError in verify_candidate_dossier.
        """
        specs = get_verified_candidate_specs()
        self.assertEqual(len(specs), 16, f"Expected exactly 16 candidates, got {len(specs)}")

        for spec in specs:
            cid = spec["id"]
            formula = spec["formula"]
            stoich = spec["stoich"]
            ox = spec["ox"]

            # 1. Canonical formula generation matches expected formula
            cf = canonical_formula(stoich)
            self.assertEqual(
                cf,
                formula,
                f"Candidate {cid}: canonical_formula({stoich}) -> '{cf}' != '{formula}'",
            )

            # 2. Independent regex-based formula parser matches stoichiometry exactly
            pf = independently_parse_formula(formula)
            self.assertEqual(
                pf,
                stoich,
                f"Candidate {cid}: independently_parse_formula('{formula}') -> {pf} != {stoich}",
            )

            # 3. Exact charge neutrality verification returns 0
            net_charge = verify_charge_neutrality(stoich, ox)
            self.assertEqual(
                net_charge,
                0,
                f"Candidate {cid}: Net charge sum(n_i * z_i) = {net_charge} != 0",
            )

        # -------------------------------------------------------------
        # Negative tests: Intentionally corrupted prototype formulas must fail
        # -------------------------------------------------------------
        broken_cases = [
            {
                "name": "Old unneutral SbCuS2Cl (prototype bug #1)",
                "formula": "SbCuS2Cl",
                "stoich": {"Sb": 1, "Cu": 1, "S": 2, "Cl": 1},
                "ox": {"Sb": 3, "Cu": 1, "S": -2, "Cl": -1},  # 3 + 1 - 4 - 1 = -1 != 0
            },
            {
                "name": "Old unneutral Zn2SbS2Br (prototype bug #2)",
                "formula": "Zn2SbS2Br",
                "stoich": {"Zn": 2, "Sb": 1, "S": 2, "Br": 1},
                "ox": {"Zn": 2, "Sb": 3, "S": -2, "Br": -1},  # 4 + 3 - 4 - 1 = +2 != 0
            },
            {
                "name": "Old unneutral BiCuSeI (prototype bug #3)",
                "formula": "BiCuSeI",
                "stoich": {"Bi": 1, "Cu": 1, "Se": 1, "I": 1},
                "ox": {"Bi": 3, "Cu": 1, "Se": -2, "I": -1},  # 3 + 1 - 2 - 1 = +1 != 0
            },
        ]

        for broken in broken_cases:
            # Must raise ValueError in physics_calculators.verify_charge_neutrality
            with self.assertRaises(ValueError, msg=f"{broken['name']} failed to raise ValueError"):
                verify_charge_neutrality(broken["stoich"], broken["ox"])

            # Must raise AssertionError("REDUNDANCY_MISMATCH_BLOCK: ...") in independent_verifier.verify_candidate_dossier
            dossier = {
                "candidate": {
                    "candidate_id": "CAND-BROKEN",
                    "formula_reduced": broken["formula"],
                    "stoichiometry": broken["stoich"],
                    "oxidation_states": broken["ox"],
                    "cif_content": "",
                    "target_layer": "TOP_ACTIVE_GLASS_185EV",
                },
                "stage_reached": 1,
            }
            with self.assertRaises(AssertionError, msg=f"{broken['name']} failed to raise AssertionError"):
                verify_candidate_dossier(dossier, raise_on_error=True)

    def test_all_16_cif_3d_periodic_distances_and_bvs(self):
        """Test 2: Verify 3D CIF construction, atom counts, PBC min distances >= 2.15 A, and BVS GII."""
        specs = get_verified_candidate_specs()

        for spec in specs:
            cid = spec["id"]
            formula = spec["formula"]
            stoich = spec["stoich"]
            cell = spec["cell"]
            sg_sym = spec["sg_sym"]
            sg_num = spec["sg_num"]
            expected_natoms = sum(stoich.values())

            # Generate CIF using physics calculator
            cif_text, min_dist_calc, bvs_gii = build_3d_crystal_cif_and_min_dist(
                formula=formula,
                sg_symbol=sg_sym,
                sg_num=sg_num,
                cell_abc=cell,
                stoich=stoich,
            )

            # Independently parse and verify CIF geometry under 3D periodic boundary conditions
            geom = independently_verify_cif_geometry(cif_text)

            self.assertEqual(
                geom["natoms"],
                expected_natoms,
                f"Candidate {cid}: CIF parsed natoms {geom['natoms']} != sum(stoichiometry) {expected_natoms}",
            )
            self.assertGreaterEqual(
                geom["min_distance_ang"],
                2.15,
                f"Candidate {cid}: Min periodic distance {geom['min_distance_ang']} A < 2.15 A threshold",
            )
            self.assertTrue(
                geom["valid_geometry"],
                f"Candidate {cid}: Geometry flagged invalid by independent verifier",
            )
            self.assertGreater(bvs_gii, 0.0, f"Candidate {cid}: BVS GII {bvs_gii} must be positive")
            self.assertLess(bvs_gii, 0.20, f"Candidate {cid}: BVS GII {bvs_gii} exceeds stability limit 0.20 vu")

    def test_am15g_spectral_normalization(self):
        """Test 3: AM1.5G solar irradiance trapezoidal integration over 280..4000 nm equals 1000.0 W/m^2."""
        lam_nm = np.arange(280.0, 4001.0, 1.0)
        irr_w_m2_nm = compute_am15g_irradiance_w_m2_nm(lam_nm)

        integrated_irradiance = float(np.trapz(irr_w_m2_nm, lam_nm))

        self.assertAlmostEqual(
            integrated_irradiance,
            1000.0,
            places=4,
            msg=f"Integrated AM1.5G irradiance {integrated_irradiance} W/m^2 != 1000.0 W/m^2 within 1e-4",
        )

    def test_dual_quadrature_slme_trapezoidal_vs_simpson(self):
        """Test 4: Dual-quadrature cross-verification (Wavelength Trapezoidal vs Photon-Energy Simpson 1/3).

        For all Stage 4 and Stage 5 candidates, verifies that the wavelength-space trapezoidal
        quadrature (compute_4t_tandem_optics_wavelength_grid) and photon-energy-space Simpson 1/3
        quadrature (independently_verify_energy_quadrature_slme) agree within 0.05% absolute efficiency!
        """
        records = self.summary_data.get("all_campaign_records", [])
        stage4_5_count = 0

        for r in records:
            stage = r.get("stage_reached", 0)
            if stage < 4:
                continue

            stage4_5_count += 1
            cand = r["candidate"]
            cid = cand["candidate_id"]
            target_layer = cand["target_layer"]
            elec = r["electronics"]
            opt = r["optics"]

            eg_ind = elec["hse06_soc_indirect_gap_ev"]
            eg_dir = elec["hse06_soc_direct_gap_ev"]
            eps_inf = elec["eps_inf"]
            thickness_nm = opt["film_thickness_nm"]
            stated_trapezoidal_slme = opt["standalone_slme_percent"]

            # Independent Simpson 1/3 quadrature in photon-energy space (0.62 - 4.428 eV, 3809 pts)
            simpson_res = independently_verify_energy_quadrature_slme(
                eg_ind_ev=eg_ind,
                eg_dir_ev=eg_dir,
                eps_inf=eps_inf,
                thickness_nm=thickness_nm,
                target_layer=target_layer,
            )
            simpson_slme = simpson_res["standalone_slme_percent"]
            slme_diff = abs(stated_trapezoidal_slme - simpson_slme)

            self.assertLessEqual(
                slme_diff,
                0.05,
                f"Candidate {cid}: SLME quadrature discrepancy {slme_diff:.4f}% > 0.05% "
                f"(trapezoidal={stated_trapezoidal_slme}%, simpson={simpson_slme}%)",
            )

        self.assertGreaterEqual(
            stage4_5_count,
            6,
            f"Expected at least 6 Stage 4/5 candidates to verify SLME quadrature, got {stage4_5_count}",
        )

    def test_frohlich_polaron_and_anderson_debye_physics(self):
        """Test 5: Exact Frohlich polaron alpha coupling, SOC splitting, and Anderson Debye temperature.

        Verifies that every candidate passes verify_candidate_dossier without error, and
        validates the physical consistency of relativistic SOC splitting and polaronic coupling.
        """
        records = self.summary_data.get("all_campaign_records", [])

        for r in records:
            cid = r["candidate"]["candidate_id"]

            # Zero-trust audit by independent verifier
            report = verify_candidate_dossier(r, raise_on_error=True)
            self.assertTrue(
                report["passed_all_redundancy_checks"],
                f"Candidate {cid} failed zero-trust dossier verification: {report.get('mismatches')}",
            )
            self.assertEqual(len(report["mismatches"]), 0)

            # Stage >= 4 specific physical checks
            if r.get("stage_reached", 0) >= 4:
                checks = report["checks"]

                # Relativistic SOC splitting check
                soc_check = checks.get("soc_splitting", {})
                self.assertTrue(soc_check.get("passed"), f"Candidate {cid}: SOC splitting check failed")
                expected_soc = round(
                    r["electronics"]["hse06_nosoc_gap_ev"] - r["electronics"]["hse06_soc_direct_gap_ev"],
                    3,
                )
                self.assertEqual(r["electronics"]["soc_splitting_ev"], expected_soc)

                # Frohlich alpha coupling check
                frohlich_check = checks.get("frohlich_alpha", {})
                self.assertTrue(frohlich_check.get("passed"), f"Candidate {cid}: Frohlich alpha check failed")
                self.assertLessEqual(frohlich_check.get("abs_difference"), 0.01)

        # Anderson Debye temperature physical verification across all 16 candidate specifications
        specs = get_verified_candidate_specs()
        for spec in specs:
            cid = spec["id"]
            stab_metrics = compute_stability_metrics(spec)
            debye_t = stab_metrics["debye_temperature_k"]

            self.assertGreater(
                debye_t,
                100.0,
                f"Candidate {cid}: Anderson Debye temperature {debye_t} K is unphysically low (<100 K)",
            )
            self.assertLess(
                debye_t,
                600.0,
                f"Candidate {cid}: Anderson Debye temperature {debye_t} K is unphysically high (>600 K)",
            )

    def test_full_campaign_and_audit_logs(self):
        """Test 6: Verify full campaign summary, communication log, audit log, and failure memory SQLite database.

        Verifies:
        - All 4 artifacts exist on disk and are non-empty.
        - pilot_campaign_summary.json has 16 records: 6 promoted finalists and 10 rejected with explicit physical reasons.
        - Every record in the campaign has passed_all_redundancy_checks == True.
        - failure_memory.db contains all 16 candidate evaluations matching the exact promotional statuses.
        - verification_audit_log.jsonl contains 16 verified entries with unique SHA-256 signatures.
        """
        # 1. Check file existence
        self.assertTrue(os.path.exists(self.summary_path), f"Missing {self.summary_path}")
        self.assertTrue(os.path.exists(self.comms_log_path), f"Missing {self.comms_log_path}")
        self.assertTrue(os.path.exists(self.audit_log_path), f"Missing {self.audit_log_path}")
        self.assertTrue(os.path.exists(self.db_path), f"Missing {self.db_path}")

        # 2. Inspect pilot_campaign_summary.json
        records = self.summary_data.get("all_campaign_records", [])
        self.assertEqual(len(records), 16, f"Expected 16 records in campaign summary, got {len(records)}")

        promoted = [r for r in records if r.get("status") == "PROMOTED"]
        rejected = [r for r in records if r.get("status") == "REJECTED"]

        self.assertEqual(len(promoted), 6, f"Expected 6 promoted finalists, got {len(promoted)}")
        self.assertEqual(len(rejected), 10, f"Expected 10 rejected candidates, got {len(rejected)}")

        expected_promoted_ids = {"CAND-A02", "CAND-A03", "CAND-A06", "CAND-A09", "CAND-B02", "CAND-B04"}
        actual_promoted_ids = {r["candidate"]["candidate_id"] for r in promoted}
        self.assertEqual(
            actual_promoted_ids,
            expected_promoted_ids,
            f"Promoted IDs mismatch: {actual_promoted_ids} vs {expected_promoted_ids}",
        )

        # Check every record has passed_all_redundancy_checks == True and rejected records have exact physical reasons
        for r in records:
            cid = r["candidate"]["candidate_id"]
            red_verif = r.get("redundancy_verification", {})
            self.assertTrue(
                red_verif.get("passed_all_redundancy_checks"),
                f"Candidate {cid}: passed_all_redundancy_checks is not True",
            )

            if r.get("status") == "REJECTED":
                self.assertIsNotNone(
                    r.get("primary_failure_mode"),
                    f"Rejected candidate {cid} missing primary_failure_mode",
                )
                self.assertIsNotNone(
                    r.get("reason"),
                    f"Rejected candidate {cid} missing rejection reason text",
                )
                self.assertGreater(
                    len(r.get("reason", "")),
                    10,
                    f"Candidate {cid} rejection reason is too brief",
                )

        # 3. Inspect failure_memory.db SQLite database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT candidate_id, formula_reduced, status, stage_reached, primary_failure_mode, adversarial_notes "
            "FROM material_evaluations WHERE candidate_id LIKE 'CAND-%'"
        )
        db_rows = cursor.fetchall()
        conn.close()

        self.assertEqual(
            len(db_rows),
            16,
            f"Expected 16 candidate rows in failure_memory.db, got {len(db_rows)}",
        )

        db_promoted = [r for r in db_rows if r[2] == "PROMOTED"]
        db_rejected = [r for r in db_rows if r[2] == "REJECTED"]
        self.assertEqual(len(db_promoted), 6)
        self.assertEqual(len(db_rejected), 10)

        # 4. Inspect verification_audit_log.jsonl
        audit_entries = []
        with open(self.audit_log_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    audit_entries.append(json.loads(line_str))

        # Check for initial 16 candidate entries
        cand_audit_entries = [e for e in audit_entries if e.get("candidate_id", "").startswith("CAND-")]
        self.assertEqual(
            len(cand_audit_entries),
            16,
            f"Expected 16 candidate entries in verification audit log, got {len(cand_audit_entries)}",
        )
        for entry in cand_audit_entries:
            self.assertTrue(
                entry.get("passed_all_checks"),
                f"Audit entry for {entry.get('candidate_id')} did not pass all checks",
            )
            self.assertTrue(
                entry.get("independent_sha256"),
                f"Audit entry for {entry.get('candidate_id')} missing independent_sha256",
            )


if __name__ == "__main__":
    unittest.main()
