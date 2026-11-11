"""Automated Test Suite for Scientific Integrity, Redundancy Invariants & Failure Memory (v2.0).

Mandated by FailSmart-MatEngine Multi-Agent Architecture (QA Test & Audit Engineer):
- Test 1 (test_ast_blinding_firewall_and_zero_empirical_multipliers):
    Parse failsmart_matengine/independent_verifier.py with Python ast and assert ZERO imports from
    physics_calculators, kinetics_and_optics, or tools. Also scan AST numeric constants in both
    kinetics_and_optics.py and independent_verifier.py to verify the v1.0 1.28 empirical SLME
    multiplier is completely absent!
- Test 2 (test_all_20_candidates_canonical_formula_and_charge_neutrality):
    Verify all 16 benchmark + 4 SMACT OOD candidates pass canonical formula, independent regex
    parsing, and exact sum(n_i * z_i) == 0 neutrality, plus negative tests on corrupted formulas
    (SbCuS2Cl, Zn2SbS2Br, BiCuSeI) raising ValueError and AssertionError("REDUNDANCY_MISMATCH_BLOCK...").
- Test 3 (test_pyxtal_wyckoff_cif_roundtrip_pbc_and_bvs):
    Verify every generated CIF round-trips cleanly via pymatgen.io.cif.CifParser, matches nsites_unit_cell,
    satisfies min_distance_ang >= 2.15 A across all 3D periodic images, and agrees on exact unscaled
    Brown-Altermatt BVS GII with independently_verify_cif_geometry within 0.02 v.u.
- Test 4 (test_astm_g173_am15g_reference_spectrum):
    Verify compute_am15g_irradiance_w_m2_nm matches official NREL ASTM G173-03 AM1.5G
    (~1000.37 W/m^2 via np.trapezoid over pvlib's grid).
- Test 5 (test_thermodynamic_shockley_queisser_ceiling_and_photon_conservation):
    Verify for EVERY candidate (including CAND-A09 Cu3BiS2Cl2 at 1.76 eV!) that
    standalone_slme_percent <= shockley_queisser_limit_percent strictly holds (regression-testing
    the v1.0 28.98% > 27.93% SQ violation!), and verify that passing a spoofed
    standalone_slme_percent > shockley_queisser_limit_percent into
    verify_candidate_dossier(..., raise_on_error=True) raises AssertionError.
- Test 6 (test_dual_quadrature_wavelength_trapezoid_vs_energy_simpson):
    Verify wavelength-space np.trapezoid and blinded photon-energy-space scipy.integrate.simpson
    agree within <= 0.05% on standalone_slme_percent, tandem_2layer_si_eff_percent,
    tandem_4t_std_si_fca_eff_percent, and tandem_4t_total_eff_percent, and verify that lowering
    top-cell Eg (1.85 -> 1.76 eV) reduces si_middle_cell_eff_percent monotonically
    (proving zero spectral double-counting!).
- Test 7 (test_stage2b_cu_ion_migration_gate):
    Verify CAND-A09 (Cu3BiS2Cl2) has ion_migration_barrier_ev == 0.42 < 0.65 and is rejected at
    Stage 2 with ION_MIGRATION_INSTABILITY, whereas oxide/covalently locked finalists
    (Bi2CuO2SCl, Cu2SbS2Cl, BiZnOSCl, Sn2SbSe2I3, Cu2BiSe2I) satisfy ion_migration_barrier_ev >= 0.65.
- Test 8 (test_runnable_quantum_espresso_hybrid_soc_decks):
    Parse all 5 finalist .in decks in outputs/qe_hse06_soc_decks/ (HSE06+SOC not run) and verify real IUPAC atomic weights
    (> 14.0, never 1.000), presence of CELL_PARAMETERS (angstrom) with a non-singular 3x3 matrix
    (abs(det) > 50.0), and ATOMIC_POSITIONS (crystal) with exact nat coordinate lines matching the .cif file!
- Test 9 (test_arbitrary_ood_novel_composition_no_keyerror):
    Construct a brand-new 21st unseen composition (e.g., CAND-TEST-21, ZnSn2S2Cl2, not in any dictionary)
    via build_candidate_from_spec and run stage2_evaluate_stability, stage3_evaluate_synthesis_and_speciation,
    gate_a_adversarial_audit, stage4_5_quantum_and_defects, stage5_optical_4t_tandem_simulation, and
    verify_candidate_dossier(..., raise_on_error=True) end-to-end without KeyError!
- Test 10 (test_full_v2_campaign_sqlite_and_audit_logs):
    Verify pilot_campaign_summary.json (20 candidates: 5 promoted finalists CAND-A02, CAND-A03, CAND-A06,
    CAND-B02, CAND-B04, 15 rejected), failure_memory.db (23 total rows = 20 campaign + 3 historical seeds,
    including fixed Cs3Bi2I9), inter_team_communication.jsonl, and verification_audit_log.jsonl
    (20/20 passed_all_checks == True).
"""

from __future__ import annotations

import ast
import copy
import glob
import json
import math
import os
import sqlite3
import sys
import unittest

# Ensure repo root is on sys.path so failsmart_matengine imports seamlessly
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pvlib.spectrum
from pymatgen.io.cif import CifParser

from failsmart_matengine.physics_calculators import (
    canonical_formula,
    verify_charge_neutrality,
    build_3d_crystal_cif_and_min_dist,
    get_verified_candidate_specs,
    generate_smact_ood_candidates,
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
    independently_verify_cross_layer_4t_pair,
    independently_verify_spring_and_migration_heuristics,
    independently_verify_coherent_tmm_4t_stack,
    independently_verify_graded_arc_and_techno_economics,
    independently_verify_phase9a_lab_and_defect_dossier,
    independently_verify_phase9c_oblique_thermal_lcoe,
    independently_verify_phase10_bifacial_and_string_dossier,
    independently_verify_phase11a_synthesis_and_contacts,
    independently_verify_phase11b_realistic_commercialization,
)
from pymatgen.core import Structure
import subprocess
from failsmart_matengine.mp_live_discovery import compute_covalent_dimensionality_from_structure
from failsmart_matengine.tools import (
    ContrastiveFailureLedger,
    build_candidate_from_spec,
    stage2_evaluate_stability,
    stage3_evaluate_synthesis_and_speciation,
    gate_a_adversarial_audit,
    stage4_5_quantum_and_defects,
    stage5_optical_4t_tandem_simulation,
)


class TestScientificIntegrityAndRedundancyV2(unittest.TestCase):
    """Rigorous scientific integrity, zero-trust mathematical verification & physical constraint test suite v4.0."""

    @classmethod
    def setUpClass(cls):
        """Set up file paths and load campaign artifacts."""
        cls.repo_root = _REPO_ROOT
        cls.summary_path = os.path.join(cls.repo_root, "outputs", "pilot_campaign_summary.json")
        cls.comms_log_path = os.path.join(cls.repo_root, "logs", "inter_team_communication.jsonl")
        cls.audit_log_path = os.path.join(cls.repo_root, "logs", "verification_audit_log.jsonl")
        cls.db_path = os.path.join(cls.repo_root, "data", "failure_memory.db")
        cls.qe_decks_dir = os.path.join(cls.repo_root, "outputs", "qe_hse06_soc_decks")  # HSE06+SOC not run

        with open(cls.summary_path, "r", encoding="utf-8") as f:
            cls.summary_data = json.load(f)

    def test_ast_blinding_firewall_and_zero_empirical_multipliers(self):
        """Test 1: Parse independent_verifier.py with AST and assert zero imports from engineering modules.

        Also assert zero empirical efficiency multipliers (1.28 or 0.80) in kinetics_and_optics.py
        and independent_verifier.py.
        """
        iv_path = os.path.join(self.repo_root, "failsmart_matengine", "independent_verifier.py")
        ko_path = os.path.join(self.repo_root, "failsmart_matengine", "kinetics_and_optics.py")

        with open(iv_path, "r", encoding="utf-8") as f:
            iv_tree = ast.parse(f.read(), filename="independent_verifier.py")

        banned_modules = {
            "physics_calculators",
            "kinetics_and_optics",
            "tools",
            "mp_live_discovery",
            "atomistic_and_tmm",
            "phase9_lab_and_lcoe",
            "phase10_bifacial_and_string",
            "realistic_commercialization",
        }
        for node in ast.walk(iv_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for b in banned_modules:
                        self.assertNotIn(
                            b,
                            alias.name,
                            f"Firewall violation: independent_verifier.py imports banned module '{alias.name}'",
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for b in banned_modules:
                        self.assertNotIn(
                            b,
                            node.module,
                            f"Firewall violation: independent_verifier.py imports from banned module '{node.module}'",
                        )

        # Scan for empirical multipliers (1.28 or 0.80) in AST
        with open(ko_path, "r", encoding="utf-8") as f:
            ko_tree = ast.parse(f.read(), filename="kinetics_and_optics.py")

        for tree, mod_name in [(ko_tree, "kinetics_and_optics.py"), (iv_tree, "independent_verifier.py")]:
            for node in ast.walk(tree):
                # Check for binary multiplication with empirical scale factors
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                    for operand in (node.left, node.right):
                        if isinstance(operand, ast.Constant) and operand.value in (1.28, 0.80):
                            self.fail(
                                f"Empirical multiplier {operand.value} found in {mod_name} at line {node.lineno}!"
                            )
                # Check for 1.28 inside any SLME or optics function definitions
                if isinstance(node, ast.FunctionDef) and any(kw in node.name.lower() for kw in ("slme", "tandem", "optics")):
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Constant) and sub.value in (1.28, 0.80):
                            self.fail(
                                f"Empirical constant {sub.value} found in {mod_name} function '{node.name}'!"
                            )

    def test_all_20_candidates_canonical_formula_and_charge_neutrality(self):
        """Test 2: Verify all 16 benchmark + 4 SMACT OOD candidates pass canonical formula, regex parsing, and neutrality.

        Also negative tests on corrupted formulas (SbCuS2Cl, Zn2SbS2Br, BiCuSeI) raising
        ValueError and AssertionError("REDUNDANCY_MISMATCH_BLOCK...").
        """
        benchmark_specs = list(get_verified_candidate_specs())
        ood_specs = list(generate_smact_ood_candidates(4))
        all_specs = benchmark_specs + ood_specs
        self.assertEqual(len(all_specs), 20, f"Expected 20 candidates (16 benchmark + 4 OOD), got {len(all_specs)}")

        for spec in all_specs:
            cid = spec["id"]
            formula = spec["formula"]
            stoich = spec["stoich"]
            ox = spec["ox"]

            # 1. Canonical formula generation matches formula
            cf = canonical_formula(stoich)
            self.assertEqual(cf, formula, f"{cid}: canonical_formula({stoich}) -> '{cf}' != '{formula}'")

            # 2. Independent regex-based formula parser matches stoichiometry exactly
            pf = independently_parse_formula(formula)
            self.assertEqual(pf, stoich, f"{cid}: independently_parse_formula('{formula}') -> {pf} != {stoich}")

            # 3. Exact charge neutrality verification returns 0
            net_charge = verify_charge_neutrality(stoich, ox)
            self.assertEqual(net_charge, 0, f"{cid}: Net charge sum(n_i * z_i) = {net_charge} != 0")

        # Negative tests: Intentionally corrupted prototype formulas must fail
        broken_cases = [
            {
                "name": "Old unneutral SbCuS2Cl",
                "formula": "SbCuS2Cl",
                "stoich": {"Sb": 1, "Cu": 1, "S": 2, "Cl": 1},
                "ox": {"Sb": 3, "Cu": 1, "S": -2, "Cl": -1},  # 3 + 1 - 4 - 1 = -1 != 0
            },
            {
                "name": "Old unneutral Zn2SbS2Br",
                "formula": "Zn2SbS2Br",
                "stoich": {"Zn": 2, "Sb": 1, "S": 2, "Br": 1},
                "ox": {"Zn": 2, "Sb": 3, "S": -2, "Br": -1},  # 4 + 3 - 4 - 1 = +2 != 0
            },
            {
                "name": "Old unneutral BiCuSeI",
                "formula": "BiCuSeI",
                "stoich": {"Bi": 1, "Cu": 1, "Se": 1, "I": 1},
                "ox": {"Bi": 3, "Cu": 1, "Se": -2, "I": -1},  # 3 + 1 - 2 - 1 = +1 != 0
            },
        ]

        for broken in broken_cases:
            with self.assertRaises(ValueError, msg=f"{broken['name']} failed to raise ValueError"):
                verify_charge_neutrality(broken["stoich"], broken["ox"])

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
            with self.assertRaises(AssertionError, msg=f"{broken['name']} failed to raise AssertionError") as ctx:
                verify_candidate_dossier(dossier, raise_on_error=True)
            self.assertIn("REDUNDANCY_MISMATCH_BLOCK", str(ctx.exception))

    def test_pyxtal_wyckoff_cif_roundtrip_pbc_and_bvs(self):
        """Test 3: Verify every generated CIF round-trips via CifParser, matches nsites_unit_cell, min_dist >= 2.15 A, and BVS GII."""
        all_specs = list(get_verified_candidate_specs()) + list(generate_smact_ood_candidates(4))

        for spec in all_specs:
            cid = spec["id"]
            formula = spec["formula"]
            stoich = spec["stoich"]
            ox = spec["ox"]
            cell = spec["cell"]
            sg_sym = spec["sg_sym"]
            sg_num = spec["sg_num"]

            cif_str, min_dist, bvs_gii, v_sg_sym, v_sg_num, nsites_uc = build_3d_crystal_cif_and_min_dist(
                formula=formula,
                sg_symbol=sg_sym,
                sg_num=sg_num,
                cell_abc=cell,
                stoich=stoich,
                ox_states=ox,
            )

            # Independent verification of CIF geometry and BVS GII under 3D periodic boundary conditions
            geom = independently_verify_cif_geometry(
                cif_str,
                expected_nsites=nsites_uc,
                expected_reduced_stoich=stoich,
                oxidation_states=ox,
            )

            self.assertTrue(geom["valid_geometry"], f"{cid} ({formula}): Geometry flagged invalid by independent verifier")
            self.assertEqual(geom["natoms"], nsites_uc, f"{cid} ({formula}): CIF natoms {geom['natoms']} != nsites_uc {nsites_uc}")
            self.assertGreaterEqual(geom["min_distance_ang"], 2.15, f"{cid} ({formula}): Min periodic distance {geom['min_distance_ang']} < 2.15 A")
            self.assertIsNotNone(geom["bvs_gii"], f"{cid} ({formula}): Missing BVS GII from independent verifier")

            # Check agreement on exact unscaled Brown-Altermatt BVS GII within 0.02 vu
            bvs_diff = abs(bvs_gii - geom["bvs_gii"])
            self.assertLessEqual(
                bvs_diff,
                0.02,
                f"{cid} ({formula}): BVS GII mismatch between calculator ({bvs_gii}) and verifier ({geom['bvs_gii']})",
            )

    def test_astm_g173_am15g_reference_spectrum(self):
        """Test 4: Verify compute_am15g_irradiance_w_m2_nm matches official NREL ASTM G173-03 AM1.5G (~1000.37 W/m^2 via np.trapezoid)."""
        ref_spec = pvlib.spectrum.get_reference_spectra()["global"]
        ref_wl = ref_spec.index.to_numpy(dtype=float)
        ref_irr = ref_spec.to_numpy(dtype=float)

        computed_irr = compute_am15g_irradiance_w_m2_nm(ref_wl)
        self.assertTrue(np.allclose(computed_irr, ref_irr, atol=1e-5))

        integrated_irradiance = float(np.trapezoid(computed_irr, ref_wl))
        self.assertAlmostEqual(
            integrated_irradiance,
            1000.37,
            delta=0.05,
            msg=f"Integrated AM1.5G irradiance {integrated_irradiance} W/m^2 does not match expected ~1000.37 W/m^2",
        )

    def test_thermodynamic_shockley_queisser_ceiling_and_photon_conservation(self):
        """Test 5: Verify standalone_slme_percent <= shockley_queisser_limit_percent holds strictly for every candidate.

        Also verifies CAND-A09 Cu3BiS2Cl2 at 1.76 eV regression-tests the v1.0 28.98% > 27.93% SQ violation,
        and verify_candidate_dossier raises AssertionError on spoofed SLME > SQ.
        """
        records = self.summary_data.get("all_campaign_records", [])

        for r in records:
            if "optics" in r and r["optics"]:
                cid = r["candidate"]["candidate_id"]
                slme = r["optics"]["standalone_slme_percent"]
                sq = r["optics"]["shockley_queisser_limit_percent"]
                self.assertLessEqual(
                    slme,
                    sq + 1e-6,
                    f"Candidate {cid}: Thermodynamic SQ violation! SLME {slme}% > SQ {sq}%",
                )

        # Specific regression test for CAND-A09 (Cu3BiS2Cl2 at 1.76 eV)
        opt_a09 = compute_4t_tandem_optics_wavelength_grid(
            target_layer="TOP_ACTIVE_GLASS_185EV",
            eg_ind_ev=1.76,
            eg_dir_ev=1.79,
            eps_inf=8.6,
            thickness_nm=240.0,
            candidate_id="CAND-A09",
        )
        self.assertLessEqual(
            opt_a09["standalone_slme_percent"],
            opt_a09["shockley_queisser_limit_percent"],
            f"CAND-A09 regression failure: SLME {opt_a09['standalone_slme_percent']}% > SQ {opt_a09['shockley_queisser_limit_percent']}%",
        )
        self.assertEqual(opt_a09["shockley_queisser_limit_percent"], 27.93)
        self.assertEqual(opt_a09["standalone_slme_percent"], 25.98)

        # Test spoofed SLME > SQ raises AssertionError in verify_candidate_dossier
        promoted_records = [r for r in records if r.get("status") == "PROMOTED"]
        self.assertGreater(len(promoted_records), 0)
        spoofed_dossier = copy.deepcopy(promoted_records[0])
        spoofed_dossier["optics"]["standalone_slme_percent"] = 99.9
        with self.assertRaises(AssertionError, msg="Failed to raise AssertionError on spoofed SLME > SQ ceiling") as ctx:
            verify_candidate_dossier(spoofed_dossier, raise_on_error=True)
        self.assertIn("violates thermodynamic SQ ceiling", str(ctx.exception))

    def test_dual_quadrature_wavelength_trapezoid_vs_energy_simpson(self):
        """Test 6: Verify dual quadrature agreement <= 0.05% on all 4 efficiencies and monotonic Si middle cell reduction."""
        records = self.summary_data.get("all_campaign_records", [])
        stage4_5_count = 0

        for r in records:
            if "optics" in r and r["optics"] and "electronics" in r and r["electronics"]:
                stage4_5_count += 1
                cid = r["candidate"]["candidate_id"]
                tlayer = r["candidate"]["target_layer"]
                elec = r["electronics"]
                opt = r["optics"]

                sim = independently_verify_energy_quadrature_slme(
                    eg_ind_ev=elec["gap_est_indirect_ev"],
                    eg_dir_ev=elec["gap_est_direct_ev"],
                    eps_inf=elec["eps_inf"],
                    thickness_nm=opt["film_thickness_nm"],
                    target_layer=tlayer,
                )

                for metric in [
                    "standalone_slme_percent",
                    "tandem_2layer_si_eff_percent",
                    "tandem_4t_std_si_fca_eff_percent",
                    "tandem_4t_total_eff_percent",
                ]:
                    diff = abs(opt[metric] - sim[metric])
                    self.assertLessEqual(
                        diff,
                        0.05,
                        f"Candidate {cid}: {metric} discrepancy {diff:.4f}% > 0.05% (trapezoid={opt[metric]}%, simpson={sim[metric]}%)",
                    )

        self.assertGreaterEqual(stage4_5_count, 5, "Expected at least 5 Stage 4/5 candidates to verify dual quadrature")

        # Test monotonic reduction of Si middle-cell efficiency when lowering top-cell Eg (1.82 -> 1.76 eV)
        opt_182 = compute_4t_tandem_optics_wavelength_grid(
            target_layer="TOP_ACTIVE_GLASS_185EV",
            eg_ind_ev=1.82,
            eg_dir_ev=1.86,
            eps_inf=7.8,
            thickness_nm=260.0,
            candidate_id="TOP-182",
        )
        opt_176 = compute_4t_tandem_optics_wavelength_grid(
            target_layer="TOP_ACTIVE_GLASS_185EV",
            eg_ind_ev=1.74,
            eg_dir_ev=1.76,
            eps_inf=7.8,
            thickness_nm=260.0,
            candidate_id="TOP-176",
        )
        self.assertLess(
            opt_176["si_middle_cell_eff_percent"],
            opt_182["si_middle_cell_eff_percent"],
            f"Monotonic spectral filtering failed: Si eff at 1.76 eV ({opt_176['si_middle_cell_eff_percent']}%) >= Si eff at 1.82 eV ({opt_182['si_middle_cell_eff_percent']}%)",
        )

    def test_stage2b_cu_ion_migration_gate(self):
        """Test 7: Verify CAND-A09 (Cu3BiS2Cl2) has barrier 0.42 < 0.65 eV and fails Stage 2, while finalists satisfy >= 0.65 eV."""
        records = self.summary_data.get("all_campaign_records", [])

        rec_dict = {r["candidate"]["candidate_id"]: r for r in records}
        self.assertIn("CAND-A09", rec_dict, "CAND-A09 missing from campaign records")

        a09 = rec_dict["CAND-A09"]
        self.assertEqual(a09["status"], "REJECTED", "CAND-A09 must be REJECTED")
        self.assertEqual(a09["stage_reached"], 2, "CAND-A09 must be rejected at Stage 2")
        self.assertEqual(a09["primary_failure_mode"], "ION_MIGRATION_INSTABILITY")
        self.assertEqual(a09["stability"]["ion_migration_barrier_ev"], 0.42)
        self.assertFalse(a09["stability"]["ion_migration_stable"])
        self.assertIn("ION_MIGRATION_INSTABILITY", a09.get("reason", ""))

        # Verify all 5 promoted finalists have ion migration barrier >= 0.65 eV
        finalist_ids = ["CAND-A02", "CAND-A03", "CAND-A06", "CAND-B02", "CAND-B04"]
        for fid in finalist_ids:
            self.assertIn(fid, rec_dict, f"Finalist {fid} missing from campaign records")
            frec = rec_dict[fid]
            self.assertEqual(frec["status"], "PROMOTED", f"Finalist {fid} is not PROMOTED")
            barrier = frec["stability"]["ion_migration_barrier_ev"]
            self.assertGreaterEqual(
                barrier,
                0.65,
                f"Finalist {fid} ({frec['candidate']['formula_reduced']}) has ion migration barrier {barrier} < 0.65 eV",
            )
            self.assertTrue(frec["stability"]["ion_migration_stable"])

    def test_runnable_quantum_espresso_hybrid_soc_decks(self):
        """Test 8: Parse all 5 finalist .in decks in outputs/qe_hse06_soc_decks/ (HSE06+SOC not run) and verify IUPAC masses, det(CELL) > 50, and matching nat."""
        deck_files = sorted(glob.glob(os.path.join(self.qe_decks_dir, "*_hse06_soc.in")))  # HSE06+SOC not run
        self.assertEqual(len(deck_files), 5, f"Expected 5 finalist QE input decks, found {len(deck_files)}")

        for dpath in deck_files:
            cif_path = dpath.replace("_hse06_soc.in", ".cif")  # HSE06+SOC not run
            self.assertTrue(os.path.exists(cif_path), f"Matching CIF file not found for deck {dpath}")

            with open(dpath, "r", encoding="utf-8") as f:
                deck_text = f.read()

            species_masses = {}
            cell_rows = []
            atom_positions = []
            lines = deck_text.splitlines()
            i = 0

            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("ATOMIC_SPECIES"):
                    i += 1
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("CELL_PARAMETERS", "ATOMIC_POSITIONS", "K_POINTS", "&")):
                        parts = lines[i].strip().split()
                        if len(parts) >= 2:
                            sym = parts[0]
                            mass = float(parts[1])
                            species_masses[sym] = mass
                            self.assertGreater(mass, 14.0, f"{dpath}: Atomic mass for {sym} ({mass}) is unphysically low")
                            self.assertNotEqual(mass, 1.000, f"{dpath}: Atomic mass for {sym} is dummy 1.000!")
                        i += 1
                    continue
                elif line.startswith("CELL_PARAMETERS (angstrom)"):
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

            # Assert CELL_PARAMETERS 3x3 matrix determinant > 50.0
            self.assertEqual(len(cell_rows), 3, f"{dpath}: CELL_PARAMETERS did not parse 3 rows")
            det_cell = float(np.linalg.det(cell_rows))
            self.assertGreater(abs(det_cell), 50.0, f"{dpath}: CELL_PARAMETERS determinant {det_cell} <= 50.0")

            # Assert ATOMIC_POSITIONS nat matches CifParser parsed CIF structure natoms exactly
            cif_struct = CifParser(cif_path).parse_structures(primitive=False)[0]
            self.assertEqual(
                len(atom_positions),
                len(cif_struct),
                f"{dpath}: Deck nat ({len(atom_positions)}) != CIF nat ({len(cif_struct)})",
            )

    def test_arbitrary_ood_novel_composition_no_keyerror(self):
        """Test 9: Construct unseen 21st composition CAND-TEST-21 (ZnSn2S2Cl2) and run pipeline end-to-end without KeyError."""
        spec_21 = {
            "id": "CAND-TEST-21",
            "formula": "ZnSn2S2Cl2",
            "layer": "TOP_ACTIVE_GLASS_185EV",
            "family": "Quaternary Chalcogen Halide Framework",
            "sg_sym": "P1",
            "sg_num": 1,
            "nsites": 7,
            "stoich": {"Zn": 1, "Sn": 2, "S": 2, "Cl": 2},
            "ox": {"Zn": 2, "Sn": 2, "S": -2, "Cl": -1},
            "chi_diff": 1.10,
            "dim": "3D",
            "tol": 0.90,
            "bvs_dev": 0.08,
            "cell": (5.8, 5.8, 6.2),
        }

        cand = build_candidate_from_spec(spec_21)
        self.assertEqual(cand.candidate_id, "CAND-TEST-21")
        self.assertEqual(cand.formula_reduced, "ZnSn2S2Cl2")

        st2 = stage2_evaluate_stability(cand)
        self.assertTrue(st2.passed_stage2)

        ledger = ContrastiveFailureLedger()
        st3 = stage3_evaluate_synthesis_and_speciation(cand, ledger)
        self.assertTrue(st3.passed_stage3)

        gate = gate_a_adversarial_audit(cand, st2, st3)
        self.assertEqual(gate.decision, "PROMOTE")

        elec = stage4_5_quantum_and_defects(cand)
        self.assertGreater(elec.gap_est_direct_ev, 0.0)

        opt = stage5_optical_4t_tandem_simulation(cand, elec, st3)
        self.assertGreater(opt.standalone_slme_percent, 0.0)

        dossier = {
            "candidate": cand.model_dump(),
            "stage_reached": 5,
            "status": "PROMOTED",
            "stability": st2.model_dump(),
            "synthesis": st3.model_dump(),
            "gate_a": gate.model_dump(),
            "electronics": elec.model_dump(),
            "optics": opt.model_dump(),
        }

        verif = verify_candidate_dossier(dossier, raise_on_error=True)
        self.assertTrue(verif["passed_all_redundancy_checks"])
        self.assertTrue(verif["sha256_digest"])

    def test_full_v2_campaign_sqlite_and_audit_logs(self):
        """Test 10: Verify pilot_campaign_summary.json (20 candidates: 5 finalists, 15 rejected), failure_memory.db (23 total rows), logs."""
        self.assertTrue(os.path.exists(self.summary_path))
        self.assertTrue(os.path.exists(self.comms_log_path))
        self.assertTrue(os.path.exists(self.audit_log_path))
        self.assertTrue(os.path.exists(self.db_path))

        # 1. Inspect pilot_campaign_summary.json
        records = self.summary_data.get("all_campaign_records", [])
        self.assertEqual(len(records), 20, f"Expected 20 records in campaign summary, got {len(records)}")

        promoted = [r for r in records if r.get("status") == "PROMOTED"]
        rejected = [r for r in records if r.get("status") == "REJECTED"]
        self.assertEqual(len(promoted), 5, f"Expected 5 promoted finalists, got {len(promoted)}")
        self.assertEqual(len(rejected), 15, f"Expected 15 rejected candidates, got {len(rejected)}")

        expected_promoted_ids = {"CAND-A02", "CAND-A03", "CAND-A06", "CAND-B02", "CAND-B04"}
        actual_promoted_ids = {r["candidate"]["candidate_id"] for r in promoted}
        self.assertEqual(actual_promoted_ids, expected_promoted_ids)

        for r in records:
            cid = r["candidate"]["candidate_id"]
            red_verif = r.get("redundancy_verification", {})
            self.assertTrue(red_verif.get("passed_all_redundancy_checks"), f"Candidate {cid}: redundancy checks failed")
            if r.get("status") == "REJECTED":
                self.assertIsNotNone(r.get("primary_failure_mode"), f"Rejected {cid} missing primary_failure_mode")
                self.assertIsNotNone(r.get("reason"), f"Rejected {cid} missing reason")

        # 2. Inspect failure_memory.db
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM material_evaluations")
        total_db_rows = cursor.fetchone()[0]
        self.assertEqual(total_db_rows, 23, f"Expected 23 total rows in failure_memory.db, got {total_db_rows}")

        # Check literature seeds
        cursor.execute("SELECT candidate_id, formula_reduced, status FROM material_evaluations WHERE candidate_id LIKE 'LIT-%'")
        lit_seeds = cursor.fetchall()
        self.assertEqual(len(lit_seeds), 3)
        lit_formulas = {r[1] for r in lit_seeds}
        self.assertIn("Cs3Bi2I9", lit_formulas)

        # Check campaign candidate rows
        cursor.execute("SELECT candidate_id, formula_reduced, status FROM material_evaluations WHERE candidate_id LIKE 'CAND-%'")
        cand_rows = cursor.fetchall()
        self.assertEqual(len(cand_rows), 20)
        conn.close()

        # 3. Inspect verification_audit_log.jsonl
        audit_entries = []
        with open(self.audit_log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    audit_entries.append(json.loads(line.strip()))

        self.assertEqual(len(audit_entries), 20, f"Expected 20 entries in verification audit log, got {len(audit_entries)}")
        for entry in audit_entries:
            self.assertTrue(entry.get("passed_all_checks"), f"Audit entry for {entry.get('candidate_id')} failed checks")
            self.assertTrue(entry.get("independent_sha256"), f"Audit entry for {entry.get('candidate_id')} missing SHA-256")

        # 4. Inspect inter_team_communication.jsonl
        comms_entries = []
        with open(self.comms_log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    comms_entries.append(json.loads(line.strip()))
        self.assertGreaterEqual(len(comms_entries), 20, f"Expected >= 20 comms entries, got {len(comms_entries)}")

    def test_zero_api_key_or_secret_leakage(self):
        """Test 11: Verify .env is git-ignored and MP_API_KEY/known hash fragments never appear in repo text files outside .env."""
        # 1. Verify .env is strictly ignored by git
        res = subprocess.run(
            ["git", "check-ignore", ".env"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            res.returncode,
            0,
            ".env must be strictly git-ignored (git check-ignore .env returned non-zero)",
        )
        self.assertIn(".env", res.stdout)

        # 2. Extract MP_API_KEY and its 8-char prefix dynamically from .env if it exists
        env_path = os.path.join(self.repo_root, ".env")
        banned_tokens = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("MP_API_KEY=") or line.startswith("MP_API_KEY ="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and len(val) >= 12:
                            banned_tokens.append(val)
                            banned_tokens.append(val[:10])

        # 3. Recursively scan repo text files outside .env
        exts = (".py", ".json", ".md", ".jsonl", ".in", ".cif")
        leaks = []
        for root, dirs, files in os.walk(self.repo_root):
            if any(skip in root for skip in [".git", ".venv", "__pycache__", ".pytest_cache"]):
                continue
            for fname in files:
                if fname.endswith(exts):
                    fpath = os.path.join(root, fname)
                    relpath = os.path.relpath(fpath, self.repo_root)
                    if relpath == ".env":
                        continue
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            for tok in banned_tokens:
                                if tok in content:
                                    leaks.append((relpath, tok))
                    except Exception:
                        pass

        self.assertEqual(
            leaks,
            [],
            f"Zero-trust credential leak detected outside .env: {leaks}",
        )

    def test_lbnl_80k_impurity_and_alab_precursor_genome_priors(self):
        """Test 12: Verify LBNL 80k impurity and A-Lab precursor genome negative priors dataset provenance and failure sink counts."""
        priors_path = os.path.join(self.repo_root, "data", "negative_synthesis_priors.json")
        self.assertTrue(os.path.exists(priors_path), "data/negative_synthesis_priors.json must exist")

        with open(priors_path, "r", encoding="utf-8") as f:
            priors_data = json.load(f)

        prov = priors_data.get("dataset_provenance", {})
        lbnl_prov = prov.get("lbnl_solid_state_impurity_dataset") or prov.get("lbnl_80k_impurity_dataset", {})
        alab_prov = prov.get("alab_precursor_genome_dataset") or prov.get("alab_precursor_genome", {})

        lbnl_total = lbnl_prov.get("total_reactions_parsed") or lbnl_prov.get("total_recipes")
        lbnl_impure = lbnl_prov.get("impure_failed_reactions_count") or lbnl_prov.get("phase_impure_failed_recipes")
        alab_total = alab_prov.get("total_pairwise_reactions_parsed") or alab_prov.get("total_pairwise_reactions")
        alab_neg = alab_prov.get("negative_stalled_or_impure_count") or alab_prov.get("negative_or_stalled_reactions")

        self.assertEqual(lbnl_total, 80806, f"Expected 80806 LBNL reactions, got {lbnl_total}")
        self.assertEqual(lbnl_impure, 18869, f"Expected 18869 impure failed recipes, got {lbnl_impure}")
        self.assertEqual(alab_total, 1035, f"Expected 1035 A-Lab pairwise reactions, got {alab_total}")
        self.assertEqual(alab_neg, 892, f"Expected 892 negative/stalled reactions, got {alab_neg}")

        chemsys_priors = priors_data.get("chemsys_impurity_priors", {})
        self.assertGreaterEqual(len(chemsys_priors), 4000, f"Expected >= 4000 chemsys impurity priors, got {len(chemsys_priors)}")

        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        self.assertTrue(os.path.exists(live_sum_path), "outputs/live_mp_discovery_summary.json must exist")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        fmode_breakdown = live_sum.get("failure_mode_breakdown", {})
        self.assertEqual(
            fmode_breakdown.get("OXIDE_IMPURITY_SINK"),
            26,
            f"Expected 26 OXIDE_IMPURITY_SINK rejections, got {fmode_breakdown.get('OXIDE_IMPURITY_SINK')}",
        )

    def test_live_mp_covalent_dimensionality_and_100_candidates_blinded_verification(self):
        """Test 13: Verify covalent dimensionality (BiSCl/SbSI as 1D-Chain), RoHS compliance, and 100/100 blinded verification."""
        cache_path = os.path.join(self.repo_root, "data", "mp_live_candidates_cache.json")
        self.assertTrue(os.path.exists(cache_path), "data/mp_live_candidates_cache.json must exist")
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_list = json.load(f)
        cache_by_id = {c["mp_id"]: c for c in cache_list}

        self.assertIn("mp-23318", cache_by_id, "mp-23318 (BiSCl) missing from MP cache")
        self.assertIn("mp-23041", cache_by_id, "mp-23041 (SbSI) missing from MP cache")

        st_biscl = Structure.from_dict(cache_by_id["mp-23318"]["structure_dict"])
        st_sbsi = Structure.from_dict(cache_by_id["mp-23041"]["structure_dict"])

        dim_biscl = compute_covalent_dimensionality_from_structure(st_biscl)
        dim_sbsi = compute_covalent_dimensionality_from_structure(st_sbsi)
        self.assertEqual(dim_biscl, "1D-Chain", f"BiSCl expected 1D-Chain, got {dim_biscl}")
        self.assertEqual(dim_sbsi, "1D-Chain", f"SbSI expected 1D-Chain, got {dim_sbsi}")

        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        all_mp_recs = live_sum.get("all_mp_records", [])
        self.assertEqual(len(all_mp_recs), 100, f"Expected 100 live MP candidate records, got {len(all_mp_recs)}")

        banned_rohs = {"Pb", "Cd", "Hg", "Tl", "As", "Te", "P"}
        for rec in all_mp_recs:
            cand = rec["candidate"]
            cid = cand["candidate_id"]
            stoich = cand["stoichiometry"]
            rohs_intersection = banned_rohs.intersection(stoich.keys())
            self.assertEqual(
                rohs_intersection,
                set(),
                f"Candidate {cid} violates RoHS whitelist with toxic elements: {rohs_intersection}",
            )

            ox = cand["oxidation_states"]
            net_charge = sum(stoich[el] * ox[el] for el in stoich)
            self.assertEqual(net_charge, 0, f"Candidate {cid} violates charge neutrality: net_charge={net_charge}")

            verif = verify_candidate_dossier(rec, raise_on_error=True)
            self.assertTrue(
                verif.get("passed_all_redundancy_checks"),
                f"Candidate {cid} failed blinded redundancy verification: {verif.get('mismatches')}",
            )

        fc = live_sum.get("funnel_counts", {})
        self.assertEqual(fc.get("stage1_live_mp_ingested"), 100)
        self.assertEqual(fc.get("stage2_dynamically_and_ion_stable"), 91)
        self.assertEqual(fc.get("stage3_manufacturable_lbnl_alab_screened"), 47)
        self.assertEqual(fc.get("gate_a_promoted_to_dft"), 40)
        self.assertEqual(fc.get("stage4_5_prescreen_finalists"), 15)
        self.assertEqual(fc.get("top_active_glass_finalists"), 7)
        self.assertEqual(fc.get("bottom_ir_scavenger_finalists"), 8)

    def test_cross_layer_discovered_mp_4t_tandem_stacks(self):
        """Test 14: Verify all 56 cross-layer (mp-Top, c-Si, mp-Bottom) 4T stacks match independent_verifier within <= 0.05%."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        pairs = live_sum.get("cross_layer_4t_tandem_pairs", [])
        self.assertEqual(len(pairs), 56, f"Expected 56 cross-layer 4T pairs, got {len(pairs)}")

        finalists_by_id = {fin["candidate"]["candidate_id"]: fin for fin in live_sum.get("finalists", [])}
        self.assertEqual(len(finalists_by_id), 15, f"Expected 15 promoted finalists, got {len(finalists_by_id)}")

        for p in pairs:
            pid = p["pair_id"]
            self.assertTrue(
                p.get("photon_conservation_verified"),
                f"Pair {pid} photon conservation check failed",
            )
            simpson_diff = p.get("redundancy_simpson_diff_percent", 999.0)
            self.assertLessEqual(
                simpson_diff,
                0.05,
                f"Pair {pid} simpson_diff {simpson_diff}% > 0.05%",
            )
            simpson_verification_passed = (simpson_diff <= 0.05) and (p.get("photon_conservation_verified") is True)
            self.assertTrue(simpson_verification_passed)

            top_f = finalists_by_id[p["top_mp_id"]]
            bot_f = finalists_by_id[p["bottom_mp_id"]]

            iv = independently_verify_cross_layer_4t_pair(
                eg_ind_1=p["top_eg_ind_ev"],
                eg_dir_1=p["top_eg_dir_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                thickness_nm_1=top_f["optics"]["film_thickness_nm"],
                eg_ind_3=p["bottom_eg_ind_ev"],
                eg_dir_3=p["bottom_eg_dir_ev"],
                eps_inf_3=bot_f["electronics"]["eps_inf"],
                thickness_nm_3=bot_f["optics"]["film_thickness_nm"],
            )

            diff_eff = abs(p["tandem_4t_low_fca_total_eff_percent"] - iv["tandem_4t_low_fca_total_eff_percent"])
            self.assertLessEqual(
                diff_eff,
                0.05,
                f"Pair {pid} independent verification mismatch: summary={p['tandem_4t_low_fca_total_eff_percent']}%, "
                f"iv={iv['tandem_4t_low_fca_total_eff_percent']}%, diff={diff_eff:.4f}% > 0.05%",
            )

    def test_live_mp_finalist_qe_hybrid_soc_decks(self):
        """Test 15: Verify all 15 promoted live MP finalists have runnable .in/.cif files (HSE06+SOC not run) with non-placeholder IUPAC masses and det(cell) > 50."""
        live_decks_dir = os.path.join(self.repo_root, "outputs", "mp_live_qe_decks")
        self.assertTrue(os.path.exists(live_decks_dir), f"Directory {live_decks_dir} does not exist")

        deck_files = sorted(glob.glob(os.path.join(live_decks_dir, "*_hse06_soc.in")))  # HSE06+SOC not run
        self.assertEqual(len(deck_files), 15, f"Expected 15 live MP finalist QE input decks, got {len(deck_files)}")

        for dpath in deck_files:
            cif_path = dpath.replace("_hse06_soc.in", ".cif")  # HSE06+SOC not run
            self.assertTrue(os.path.exists(cif_path), f"Matching CIF file not found for deck {dpath}")

            with open(dpath, "r", encoding="utf-8") as f:
                deck_text = f.read()

            species_masses = {}
            cell_rows = []
            atom_positions = []
            lines = deck_text.splitlines()
            i = 0
            nat_in_header = None

            while i < len(lines):
                line = lines[i].strip()
                if "nat" in line and "=" in line:
                    for part in line.replace(",", " ").split():
                        if part.startswith("nat="):
                            nat_in_header = int(part.split("=")[1])
                if line.startswith("ATOMIC_SPECIES"):
                    i += 1
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("CELL_PARAMETERS", "ATOMIC_POSITIONS", "K_POINTS", "&")):
                        parts = lines[i].strip().split()
                        if len(parts) >= 2:
                            sym = parts[0]
                            mass = float(parts[1])
                            species_masses[sym] = mass
                            self.assertGreater(mass, 14.0, f"{dpath}: Atomic mass for {sym} ({mass}) is unphysically low")
                            self.assertNotEqual(mass, 1.000, f"{dpath}: Atomic mass for {sym} is dummy placeholder 1.000!")
                        i += 1
                    continue
                elif line.startswith("CELL_PARAMETERS (angstrom)"):
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

            self.assertEqual(len(cell_rows), 3, f"{dpath}: CELL_PARAMETERS did not parse 3 rows")
            det_cell = float(np.linalg.det(cell_rows))
            self.assertGreater(abs(det_cell), 50.0, f"{dpath}: CELL_PARAMETERS determinant {det_cell} <= 50.0")

            cif_struct = CifParser(cif_path).parse_structures(primitive=False)[0]
            self.assertEqual(
                len(atom_positions),
                len(cif_struct),
                f"{dpath}: Deck nat ({len(atom_positions)}) != CIF nat ({len(cif_struct)})",
            )
            if nat_in_header is not None:
                self.assertEqual(
                    nat_in_header,
                    len(atom_positions),
                    f"{dpath}: Header nat ({nat_in_header}) != parsed positions ({len(atom_positions)})",
                )

    def test_step1_pair_spring_matrix_and_ion_migration_heuristic(self):
        """Test 16: Verify pair-spring Gamma frequencies & closed-form migration heuristic across all 15 finalists (DFT phonons and NEB not run).

        Also verifies zero 'unknown' unindexed XRD tokens in competing_impurity_sinks or competing_hull_phases.
        """
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        import failsmart_matengine
        self.assertEqual(
            live_sum.get("version"),
            failsmart_matengine.__version__,
            f"Expected live_mp_discovery_summary.json version == {failsmart_matengine.__version__}",
        )

        # 1. Verify zero 'unknown' tokens in any candidate's competing_impurity_sinks or competing_hull_phases
        for rec in live_sum.get("all_mp_records", []):
            cid = rec["candidate"]["candidate_id"]
            hull_phases = rec.get("stability", {}).get("competing_hull_phases", [])
            imp_sinks = rec.get("synthesis", {}).get("competing_impurity_sinks", [])
            for phase in hull_phases + imp_sinks:
                self.assertNotIn(
                    "unknown",
                    phase.lower(),
                    f"Candidate {cid} contains unindexed 'unknown' token in competing phase/sink: {phase}",
                )

        # 2. Verify all 15 finalists' pair-spring Gamma frequency & closed-form migration heuristic reports
        spring_reports = live_sum.get("spring_and_migration_reports", [])
        self.assertEqual(len(spring_reports), 15, f"Expected 15 spring_and_migration_reports, got {len(spring_reports)}")

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}

        for rep in spring_reports:
            cid = rep["candidate_id"]
            self.assertNotIn("imaginary_mode_count", rep)
            self.assertNotIn("acoustic_sum_rule_max_dev_thz", rep)
            self.assertIsNone(rep["dynamically_stable"], f"{cid}: Expected dynamically_stable is None")
            self.assertTrue(rep["emig_gate_passed"], f"{cid}: Expected emig_gate_passed == True")
            self.assertTrue(rep["redundancy_verified"], f"{cid}: Expected redundancy_verified == True")
            self.assertEqual(len(rep["spring_model_gamma_freq_thz"]), 2)
            self.assertGreater(rep["spring_model_gamma_freq_thz"][0], 1.0, f"{cid}: Expected min spring freq > 1.0 THz")
            self.assertGreaterEqual(rep["emig_heuristic_ev"], 0.90, f"{cid}: Expected emig_heuristic_ev >= 0.90 eV")
            self.assertLess(rep["room_temp_diffusivity_cm2_s"], 1e-18, f"{cid}: Expected D_ion(300K) < 1e-18 cm^2/s")

            # Cross-verify against scipy.linalg.eigvalsh + closed-form migration heuristic
            fin = finalists_by_id[cid]
            iv_rep = independently_verify_spring_and_migration_heuristics(
                cif_text=fin["candidate"]["cif_content"],
                stoichiometry=fin["candidate"]["stoichiometry"],
                oxidation_states=fin["candidate"]["oxidation_states"],
            )
            self.assertAlmostEqual(
                rep["spring_model_gamma_freq_thz"][0],
                iv_rep["spring_model_gamma_freq_thz"][0],
                places=4,
                msg=f"{cid}: min spring freq mismatch between np.linalg.eigh and scipy.linalg.eigvalsh",
            )
            self.assertAlmostEqual(
                rep["spring_model_gamma_freq_thz"][1],
                iv_rep["spring_model_gamma_freq_thz"][1],
                places=4,
                msg=f"{cid}: max spring freq mismatch between np.linalg.eigh and scipy.linalg.eigvalsh",
            )
            self.assertAlmostEqual(
                rep["emig_heuristic_ev"],
                iv_rep["emig_heuristic_ev"],
                places=4,
                msg=f"{cid}: emig_heuristic_ev mismatch between primary and verifier",
            )

    def test_step2_coherent_abeles_tmm_vs_rouard_airy_4t_stacks(self):
        """Test 17: Verify Step 2 Coherent 2x2 Abeles TMM vs Recursive Rouard/Airy 4T Stack Optics across all 56 stacks."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        tmm_stacks = live_sum.get("coherent_tmm_4t_stacks", [])
        self.assertEqual(len(tmm_stacks), 56, f"Expected 56 coherent_tmm_4t_stacks, got {len(tmm_stacks)}")

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}

        for st in tmm_stacks:
            pid = st["pair_id"]
            self.assertTrue(st["photon_conservation_verified"], f"{pid}: Photon conservation failed")
            self.assertLessEqual(
                st["rouard_airy_redundancy_diff_percent"],
                0.05,
                f"{pid}: Abeles TMM vs Rouard/Airy discrepancy {st['rouard_airy_redundancy_diff_percent']}% > 0.05%",
            )
            self.assertGreater(st["tmm_mean_front_reflectance_percent"], 8.0, f"{pid}: Expected realistic front reflectance > 8%")
            self.assertGreater(st["tmm_sub_bandgap_transmittance_percent"], 80.0, f"{pid}: Expected sub-bandgap T > 80%")
            self.assertLess(st["scalar_to_tmm_delta_pce_percent"], 0.0, f"{pid}: Coherent TMM 4T must be lower than scalar idealization")

            top_f = finalists_by_id[st["top_mp_id"]]
            bot_f = finalists_by_id[st["bottom_mp_id"]]

            iv_tmm = independently_verify_coherent_tmm_4t_stack(
                eg_ind_1=top_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_1=top_f["electronics"]["gap_est_direct_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                thickness_nm_1=top_f["optics"]["film_thickness_nm"],
                eg_ind_3=bot_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_3=bot_f["electronics"]["gap_est_direct_ev"],
                eps_inf_3=bot_f["electronics"]["eps_inf"],
                thickness_nm_3=bot_f["electronics"]["film_thickness_nm"] if "film_thickness_nm" in bot_f["electronics"] else bot_f["optics"]["film_thickness_nm"],
            )
            diff_total = abs(st["tmm_4t_low_fca_pce_percent"] - iv_tmm["tmm_4t_low_fca_pce_percent"])
            self.assertLessEqual(
                diff_total,
                0.05,
                f"{pid}: Independent Rouard/Airy verification diff {diff_total:.4f}% > 0.05%",
            )

    def test_step3_graded_arc_tio2_and_techno_economic_fom_suite(self):
        """Test 18: Verify 7-Medium Graded-ARC + TiO2 Impedance Matching & 4-Metric Techno-Economic Suite across all 56 stacks."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        self.assertTrue(live_sum.get("v5_graded_arc_and_techno_economics_enabled"))
        graded_stacks = live_sum.get("graded_arc_techno_economic_stacks", [])
        self.assertEqual(len(graded_stacks), 56, f"Expected 56 graded_arc_techno_economic_stacks, got {len(graded_stacks)}")

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}

        for gs in graded_stacks:
            pid = gs["pair_id"]
            self.assertTrue(gs["photon_conservation_verified"], f"{pid}: Photon conservation failed")
            self.assertTrue(gs["techno_economic_redundancy_verified"], f"{pid}: Techno-economic redundancy check failed")
            self.assertLessEqual(gs["graded_arc_front_reflectance_percent"], 4.0, f"{pid}: Expected graded ARC R_front <= 4.0%")
            self.assertGreaterEqual(gs["reflectance_reduction_percent"], 8.0, f"{pid}: Expected R_front reduction >= 8.0%")
            self.assertGreater(gs["single_to_graded_4t_gain_percent"], 1.8, f"{pid}: Expected >= +1.8% 4T PCE gain from Graded-ARC")
            self.assertGreater(gs["cer_2l_vs_2x_si"], 2.8, f"{pid}: Expected CER_2L > 2.8")
            self.assertGreater(gs["cer_3l_vs_3x_si"], 4.0, f"{pid}: Expected CER_3L > 4.0")
            self.assertLess(gs["mciw_3l_full_usd_per_dw"], 0.08, f"{pid}: Expected MCIW_3L_full < $0.08/dW")
            self.assertGreater(gs["svi_bos_3l"], gs["svi_bos_2l"], f"{pid}: Expected 3L Area-BOS SVI > 2L Area-BOS SVI")

            top_f = finalists_by_id[gs["top_mp_id"]]
            bot_f = finalists_by_id[gs["bottom_mp_id"]]

            iv_gs = independently_verify_graded_arc_and_techno_economics(
                eg_ind_1=top_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_1=top_f["electronics"]["gap_est_direct_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                thickness_nm_1=top_f["optics"]["film_thickness_nm"],
                eg_ind_3=bot_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_3=bot_f["electronics"]["gap_est_direct_ev"],
                eps_inf_3=bot_f["electronics"]["eps_inf"],
                thickness_nm_3=bot_f["optics"]["film_thickness_nm"],
                raw_cost_top_usd_m2=top_f["synthesis"]["active_layer_cost_usd_m2"],
                raw_cost_bot_usd_m2=bot_f["synthesis"]["active_layer_cost_usd_m2"],
            )
            self.assertLessEqual(
                abs(gs["graded_4t_low_fca_pce_percent"] - iv_gs["graded_4t_low_fca_pce_percent"]),
                0.05,
                f"{pid}: Graded-ARC 4T PCE diff > 0.05%",
            )
            self.assertLessEqual(
                abs(gs["cer_3l_vs_3x_si"] - iv_gs["cer_3l_vs_3x_si"]),
                2e-3,
                f"{pid}: CER_3L mismatch between primary and independent verifier",
            )

    def test_step4_phase9a_9b_9c_lab_contrastive_and_real_world_lcoe(self):
        """Test 19: Verify Phase 9A (Lab Synthesis & Defect Supercells) and Phase 9C (Oblique TMM, Thermal & 25-Yr LCOE), with Phase 9B contrastive margin removed."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        self.assertTrue(live_sum.get("v6_phase9_lab_and_lcoe_enabled"))
        self.assertNotIn("contrastive_classifier_audit", live_sum)

        # 1. Phase 9A: Verify 15 Lab Synthesis & Neutral Vacancy Supercell Dossiers + Deck Files
        lab_dossiers = live_sum.get("lab_synthesis_and_defect_dossiers", [])
        self.assertEqual(len(lab_dossiers), 15, f"Expected 15 lab_synthesis_and_defect_dossiers, got {len(lab_dossiers)}")
        defect_dir = os.path.join(self.repo_root, "outputs", "mp_live_neutral_vacancy_decks")
        self.assertTrue(os.path.isdir(defect_dir))

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}
        for ld in lab_dossiers:
            cid = ld["candidate_id"]
            self.assertTrue(ld["redundancy_verified"])
            self.assertLessEqual(ld["elemental_mass_conservation_diff_g"], 1e-6)
            self.assertGreaterEqual(ld["supercell_min_image_dist_ang"], 10.0)
            self.assertLessEqual(ld["synthesis_temperature_c"], 500.0)
            deck_path = os.path.join(defect_dir, ld["neutral_vacancy_deck_filename"])
            self.assertTrue(os.path.isfile(deck_path), f"Missing neutral vacancy supercell deck: {deck_path}")

            fin = finalists_by_id[cid]
            iv_9a = independently_verify_phase9a_lab_and_defect_dossier(
                cif_content=fin["candidate"]["cif_content"],
                stoichiometry=fin["candidate"]["stoichiometry"],
                eps_static=fin["electronics"]["eps_static"],
            )
            self.assertAlmostEqual(ld["formula_unit_molar_mass_g_mol"], iv_9a["formula_unit_molar_mass_g_mol"], places=3)
            self.assertEqual(ld["supercell_dims"], iv_9a["supercell_dims"])
            self.assertEqual(ld["supercell_total_sites"], iv_9a["supercell_total_sites"])
            self.assertAlmostEqual(
                ld["point_charge_image_estimate_ev"], iv_9a["point_charge_image_estimate_ev"], places=3
            )

        # 2. Phase 9C: Verify Oblique (0-60 deg) S/P TMM, Operating Temp (25-65 C) & 25-Year Arrhenius LCOE across 56 Stacks
        lcoe_stacks = live_sum.get("real_world_lcoe_stress_test_stacks", [])
        self.assertEqual(len(lcoe_stacks), 56, f"Expected 56 real_world_lcoe_stress_test_stacks, got {len(lcoe_stacks)}")
        for rw in lcoe_stacks:
            pid = rw["pair_id"]
            self.assertTrue(rw["lcoe_redundancy_verified"], f"{pid}: Phase 9C redundancy failed")
            self.assertGreater(rw["iam_60deg_ratio"], 0.93, f"{pid}: Expected IAM(60 deg) > 0.93")
            self.assertGreater(rw["year25_retained_power_fraction_percent"], 90.0, f"{pid}: Expected Year 25 retention > 90%")
            self.assertLess(rw["lcoe_3layer_4t_cents_kwh"], rw["lcoe_2layer_cents_kwh"], f"{pid}: Expected 3L LCOE < 2L LCOE")
            self.assertLess(rw["lcoe_2layer_cents_kwh"], rw["lcoe_baseline_si_cents_kwh"], f"{pid}: Expected 2L LCOE < Si LCOE")
            self.assertGreater(rw["lcoe_3layer_vs_si_reduction_percent"], 32.0, f"{pid}: Expected >= 32% LCOE reduction vs Si")

            top_f = finalists_by_id[rw["top_mp_id"]]
            bot_f = finalists_by_id[rw["bottom_mp_id"]]
            e_mig_lim = min(
                top_f["spring_and_migration_heuristics"]["emig_heuristic_ev"],
                bot_f["spring_and_migration_heuristics"]["emig_heuristic_ev"],
            )
            iv_9c = independently_verify_phase9c_oblique_thermal_lcoe(
                eg_ind_1=top_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_1=top_f["electronics"]["gap_est_direct_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                thickness_nm_1=top_f["optics"]["film_thickness_nm"],
                eg_ind_3=bot_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_3=bot_f["electronics"]["gap_est_direct_ev"],
                eps_inf_3=bot_f["electronics"]["eps_inf"],
                thickness_nm_3=bot_f["optics"]["film_thickness_nm"],
                raw_cost_top_usd_m2=top_f["synthesis"]["active_layer_cost_usd_m2"],
                raw_cost_bot_usd_m2=bot_f["synthesis"]["active_layer_cost_usd_m2"],
                limiting_emig_heuristic_ev=e_mig_lim,
            )
            self.assertLessEqual(
                abs(rw["pce_4t_60deg_25c_percent"] - iv_9c["pce_4t_60deg_25c_percent"]),
                0.05,
                f"{pid}: 60-deg oblique PCE diff > 0.05%",
            )
            self.assertLessEqual(
                abs(rw["lcoe_3layer_4t_cents_kwh"] - iv_9c["lcoe_3layer_4t_cents_kwh"]),
                0.01,
                f"{pid}: 3L LCOE diff > 0.01 c/kWh",
            )

    def test_step5_phase10_opt_thickness_bifacial_and_string_matching(self):
        """Test 20: Verify Phase 10A (16-grid Thickness/ARC Optimization), Phase 10B (Bifacial Albedo 20%/30% & LCOE), and Phase 10C (Subcell J-V & String Matching)."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        self.assertTrue(live_sum.get("v7_phase10_bifacial_and_string_enabled"))
        p10_stacks = live_sum.get("phase10_bifacial_and_string_dossiers", [])
        self.assertEqual(len(p10_stacks), 56, f"Expected 56 phase10_bifacial_and_string_dossiers, got {len(p10_stacks)}")

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}
        graded_by_id = {g["pair_id"]: g for g in live_sum.get("graded_arc_techno_economic_stacks", [])}

        for p10 in p10_stacks:
            pid = p10["pair_id"]
            self.assertTrue(p10["phase10_redundancy_verified"], f"{pid}: Phase 10 redundancy check failed")
            self.assertLessEqual(p10["rouard_opt_diff_percent"], 0.05, f"{pid}: Rouard opt diff > 0.05%")
            self.assertGreaterEqual(
                p10["opt_monofacial_4t_pce_percent"],
                graded_by_id[pid]["graded_4t_low_fca_pce_percent"],
                f"{pid}: Optimized monofacial PCE must be >= baseline Graded-ARC 4T PCE",
            )
            self.assertGreater(
                p10["bifacial_20pct_albedo_4t_pce_percent"],
                p10["opt_monofacial_4t_pce_percent"],
                f"{pid}: 20% albedo bifacial PCE must exceed monofacial PCE",
            )
            self.assertGreater(
                p10["bifacial_30pct_albedo_4t_pce_percent"],
                p10["bifacial_20pct_albedo_4t_pce_percent"],
                f"{pid}: 30% albedo bifacial PCE must exceed 20% albedo PCE",
            )
            self.assertEqual(p10["n_cells_si_ref"], 72)
            self.assertLess(p10["top_string_mismatch_percent"], 2.0, f"{pid}: Top string mismatch >= 2.0%")
            self.assertLess(p10["bot_string_mismatch_percent"], 2.0, f"{pid}: Bottom string mismatch >= 2.0%")

            top_f = finalists_by_id[p10["top_mp_id"]]
            bot_f = finalists_by_id[p10["bottom_mp_id"]]
            e_mig_lim = min(
                top_f["spring_and_migration_heuristics"]["emig_heuristic_ev"],
                bot_f["spring_and_migration_heuristics"]["emig_heuristic_ev"],
            )
            iv_10 = independently_verify_phase10_bifacial_and_string_dossier(
                eg_ind_1=top_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_1=top_f["electronics"]["gap_est_direct_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                thickness_nm_1=top_f["optics"]["film_thickness_nm"],
                eg_ind_3=bot_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_3=bot_f["electronics"]["gap_est_direct_ev"],
                eps_inf_3=bot_f["electronics"]["eps_inf"],
                thickness_nm_3=bot_f["optics"]["film_thickness_nm"],
                raw_cost_top_usd_m2=top_f["synthesis"]["active_layer_cost_usd_m2"],
                raw_cost_bot_usd_m2=bot_f["synthesis"]["active_layer_cost_usd_m2"],
                limiting_emig_heuristic_ev=e_mig_lim,
            )
            self.assertLessEqual(
                abs(p10["bifacial_20pct_albedo_4t_pce_percent"] - iv_10["bifacial_20pct_albedo_4t_pce_percent"]),
                0.05,
                f"{pid}: Bifacial 20% PCE diff > 0.05%",
            )
            self.assertLessEqual(
                abs(p10["bifacial_20pct_lcoe_cents_kwh"] - iv_10["bifacial_20pct_lcoe_cents_kwh"]),
                0.01,
                f"{pid}: Bifacial 20% LCOE diff > 0.01 c/kWh",
            )
            self.assertLessEqual(abs(p10["n_cells_top_matched"] - iv_10["n_cells_top_matched"]), 1)
            self.assertLessEqual(abs(p10["n_cells_bot_matched"] - iv_10["n_cells_bot_matched"]), 1)

    def test_markdown_katex_safety_no_undefined_macros(self):
        """Test 21: Scan all .md files in repo for undefined KaTeX macros (\\cent, \\celsius, \\degree, \\angstrom) and unescaped currency dollars."""
        import re

        md_paths = [os.path.join(self.repo_root, "README.md")] + sorted(
            glob.glob(os.path.join(self.repo_root, "docs", "*.md"))
        )
        banned_macros = [r"\cent", r"\celsius", r"\degree", r"\angstrom"]

        for md_path in md_paths:
            self.assertTrue(os.path.isfile(md_path), f"Missing markdown file: {md_path}")
            with open(md_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()

            in_fence = False
            for line_no, raw_line in enumerate(lines, start=1):
                stripped = raw_line.strip()
                if stripped.startswith("```") or stripped.startswith("~~~"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue

                no_code = re.sub(r"`[^`]*`", "", raw_line)
                for macro in banned_macros:
                    self.assertNotIn(
                        macro,
                        no_code,
                        f"Undefined KaTeX macro '{macro}' found in {os.path.basename(md_path)}:{line_no}",
                    )

                cleaned_single = no_code.replace(r"\$", "").replace("$$", "")
                single_dollars = cleaned_single.count("$")
                self.assertEqual(
                    single_dollars % 2,
                    0,
                    f"Odd unescaped '$' count ({single_dollars}) in {os.path.basename(md_path)}:{line_no}: {raw_line}",
                )
                for span in re.findall(r"\$([^$]+)\$", cleaned_single):
                    self.assertNotIn(
                        "**",
                        span,
                        f"Markdown '**' inside inline math in {os.path.basename(md_path)}:{line_no}",
                    )
                    self.assertNotIn(
                        "¢",
                        span,
                        f"Unicode '¢' inside inline math in {os.path.basename(md_path)}:{line_no}",
                    )

    def test_step6_phase11_realistic_synthesis_and_commercialization_audit(self):
        """Test 22: Verify Phase 11A (Live MP Hull Windows, TCO Reactivity & SPS across 15 Finalists; 8 cached + 7 not evaluated) and Phase 11B/11C across 15 evaluated stacks."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        self.assertTrue(live_sum.get("v8_phase11_realistic_commercialization_enabled"))

        p11a_list = live_sum.get("phase11a_synthesis_contact_dossiers", [])
        self.assertEqual(len(p11a_list), 15, f"Expected 15 phase11a_synthesis_contact_dossiers, got {len(p11a_list)}")
        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}

        p11a_by_id = {}
        evaluated_11a_count = 0
        for p11a in p11a_list:
            cid = p11a["candidate_id"]
            p11a_by_id[cid] = p11a
            if p11a["synthesis_practicality_score_100"] is None:
                self.assertIsNone(p11a["contact_voltage_penalty_v"])
                self.assertEqual(p11a["recommended_etl_barrier"], "not evaluated")
                continue

            evaluated_11a_count += 1
            self.assertTrue(p11a["redundancy_verified"], f"{cid}: Phase 11A redundancy check failed")
            self.assertGreaterEqual(p11a["synthesis_practicality_score_100"], 0.0)
            self.assertLessEqual(p11a["synthesis_practicality_score_100"], 100.0)
            self.assertAlmostEqual(p11a["rxn_tio2_mev_per_atom"], 0.0, places=2)

            fin = finalists_by_id[cid]
            iv_11a = independently_verify_phase11a_synthesis_and_contacts(
                stoichiometry=fin["candidate"]["stoichiometry"],
                structural_dimensionality=fin["candidate"]["structural_dimensionality"],
                eg_ind_ev=fin["electronics"]["gap_est_indirect_ev"],
                mp_gga_hull_mev_per_atom=p11a["mp_gga_hull_mev_per_atom"],
                anion_chempot_window_ev=p11a["anion_chempot_window_ev"],
                min_cation_chempot_window_ev=p11a["min_cation_chempot_window_ev"],
                rxn_sno2_mev_per_atom=p11a["rxn_sno2_mev_per_atom"],
                rxn_in2o3_mev_per_atom=p11a["rxn_in2o3_mev_per_atom"],
                rxn_tio2_mev_per_atom=p11a["rxn_tio2_mev_per_atom"],
            )
            self.assertAlmostEqual(
                p11a["synthesis_practicality_score_100"],
                iv_11a["synthesis_practicality_score_100"],
                places=2,
            )
            self.assertEqual(p11a["recommended_etl_barrier"], iv_11a["recommended_etl_barrier"])

        self.assertEqual(evaluated_11a_count, 8)

        # Top synthesis practicality candidates must be BiSbS3 (mp-1227486) and Sb2OS2 (mp-861911) > 94.0
        self.assertGreater(p11a_by_id["mp-1227486"]["synthesis_practicality_score_100"], 94.0)
        self.assertGreater(p11a_by_id["mp-861911"]["synthesis_practicality_score_100"], 94.0)

        p11b_list = live_sum.get("phase11b_realistic_commercialization_dossiers", [])
        self.assertEqual(len(p11b_list), 15, f"Expected 15 phase11b_realistic_commercialization_dossiers, got {len(p11b_list)}")
        p10_by_id = {p["pair_id"]: p for p in live_sum.get("phase10_bifacial_and_string_dossiers", [])}

        for p11b in p11b_list:
            pid = p11b["pair_id"]
            self.assertTrue(p11b["phase11_redundancy_verified"], f"{pid}: Phase 11B redundancy check failed")
            self.assertLessEqual(p11b["rouard_base_2l_diff_percent"], 0.05)
            self.assertLess(
                p11b["base_3l_mono_pce_percent"],
                p11b["radiative_3l_mono_pce_percent"],
                f"{pid}: Realistic SRH PCE must be strictly below radiative ceiling",
            )
            self.assertGreater(
                p11b["path2_2l_bif20_pce_percent"],
                p11b["path1_3l_bif20_pce_percent"],
                f"{pid}: Path 2 unobstructed bifacial 2L must exceed Path 1 rear-cannibalized 3L at Base-Case ERE=1e-4",
            )
            self.assertLess(
                p11b["path2_utility_lcoe_cents_kwh"],
                p11b["path1_utility_lcoe_cents_kwh"],
            )
            self.assertGreater(p11b["path4_gross_margin_percent"], 50.0)

            top_f = finalists_by_id[p11b["top_mp_id"]]
            bot_f = finalists_by_id[p11b["bottom_mp_id"]]
            p10 = p10_by_id[pid]
            t11a = p11a_by_id[p11b["top_mp_id"]]
            b11a = p11a_by_id[p11b["bottom_mp_id"]]

            iv_11b = independently_verify_phase11b_realistic_commercialization(
                eg_ind_1=top_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_1=top_f["electronics"]["gap_est_direct_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                opt_mgf2_nm=p10["opt_mgf2_nm"],
                opt_tio2_nm=p10["opt_tio2_nm"],
                opt_top_nm=p10["opt_top_nm"],
                f_orient_1=t11a["ribbon_orientation_factor"],
                v_antisite_1=t11a["antisite_voltage_penalty_v"],
                v_contact_1=t11a["contact_voltage_penalty_v"],
                raw_cost_top_usd_m2=top_f["synthesis"]["active_layer_cost_usd_m2"],
                stoich_1=top_f["candidate"]["stoichiometry"],
                eg_ind_3=bot_f["electronics"]["gap_est_indirect_ev"],
                eg_dir_3=bot_f["electronics"]["gap_est_direct_ev"],
                eps_inf_3=bot_f["electronics"]["eps_inf"],
                opt_bot_nm=p10["opt_bot_nm"],
                f_orient_3=b11a["ribbon_orientation_factor"],
                v_antisite_3=b11a["antisite_voltage_penalty_v"],
                v_contact_3=b11a["contact_voltage_penalty_v"],
                raw_cost_bot_usd_m2=bot_f["synthesis"]["active_layer_cost_usd_m2"],
                stoich_3=bot_f["candidate"]["stoichiometry"],
            )
            self.assertLessEqual(
                abs(p11b["path2_2l_bif20_pce_percent"] - iv_11b["path2_2l_bif20_pce_percent"]),
                0.05,
                f"{pid}: Path 2 Bifacial PCE diff > 0.05%",
            )
            self.assertLessEqual(
                abs(p11b["path2_utility_lcoe_cents_kwh"] - iv_11b["path2_utility_lcoe_cents_kwh"]),
                0.01,
                f"{pid}: Path 2 Utility LCOE diff > 0.01 c/kWh",
            )

    def test_23_portable_paths_and_single_package_version(self) -> None:
        """Verify unified package version across metadata/README and repo-relative default paths."""
        import importlib.metadata
        import inspect
        from pathlib import Path

        import failsmart_matengine
        from failsmart_matengine.inter_team_bus import InterTeamBus
        from failsmart_matengine.ledger import ContrastiveFailureLedger
        from failsmart_matengine.mp_live_discovery import run_live_mp_discovery_campaign
        from failsmart_matengine.orchestrator import run_pilot_campaign

        expected_root = Path(failsmart_matengine.__file__).resolve().parents[1]
        pkg_version = importlib.metadata.version("failsmart-matengine")
        self.assertEqual(pkg_version, failsmart_matengine.__version__)
        readme_text = (expected_root / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"v{failsmart_matengine.__version__}", readme_text)

        self.assertEqual(
            Path(inspect.signature(ContrastiveFailureLedger.__init__).parameters["db_path"].default),
            expected_root / "data" / "failure_memory.db",
        )
        self.assertEqual(
            Path(inspect.signature(InterTeamBus.__init__).parameters["logs_dir"].default),
            expected_root / "logs",
        )
        self.assertEqual(
            Path(inspect.signature(run_pilot_campaign).parameters["output_dir"].default),
            expected_root / "outputs",
        )
        self.assertEqual(
            Path(inspect.signature(run_live_mp_discovery_campaign).parameters["output_dir"].default),
            expected_root / "outputs",
        )

    def test_24_every_remaining_gate_can_fail(self) -> None:
        """T6 acceptance check: feed every remaining gate in mp_live_discovery and atomistic migration an input that must fail, and assert it fails."""
        import tempfile
        from pymatgen.core import Lattice
        from pymatgen.io.cif import CifWriter
        from failsmart_matengine.atomistic_and_tmm import evaluate_spring_and_migration_heuristics
        from failsmart_matengine.mp_live_discovery import (
            build_live_mp_candidate_dossier,
            load_negative_synthesis_priors,
        )

        cache_path = os.path.join(self.repo_root, "data", "mp_live_candidates_cache.json")
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_by_id = {c["mp_id"]: c for c in json.load(f)}

        priors = load_negative_synthesis_priors()
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = ContrastiveFailureLedger(os.path.join(tmpdir, "gate_test.db"))
            base = copy.deepcopy(cache_by_id["mp-861911"])  # Sb2OS2 promoted baseline

            d_pass = build_live_mp_candidate_dossier(base, priors, ledger)
            self.assertEqual(d_pass["status"], "PROMOTED")
            self.assertIsNone(d_pass["stability"]["dynamically_stable"])
            self.assertIsNone(d_pass["stability"]["g_above_hull_synth_mev"])
            self.assertNotIn("mlip_force_std_ev_ang", d_pass["stability"])
            self.assertIsNone(d_pass["gate_a"]["anion_mixing_enthalpy_mev"])
            self.assertIsNone(d_pass["gate_a"]["tco_interface_rxn_energy_mev"])
            self.assertIsNone(d_pass["gate_a"]["tco_compatible"])

            # 1. Stage 2 hull gate (ehull_mev > 50.0)
            r_hull = copy.deepcopy(base)
            r_hull["energy_above_hull_mev"] = 75.0
            d_hull = build_live_mp_candidate_dossier(r_hull, priors, ledger)
            self.assertEqual(d_hull["status"], "REJECTED")
            self.assertEqual(d_hull["primary_failure_mode"], "HULL_INSTABILITY")

            # 2. Stage 2 Born elasticity gate (k_gpa <= 15 or g_gpa <= 12)
            r_born = copy.deepcopy(base)
            r_born["dft_elasticity"] = {"k_vrh_gpa": 12.0, "g_vrh_gpa": 8.0}
            d_born = build_live_mp_candidate_dossier(r_born, priors, ledger)
            self.assertEqual(d_born["status"], "REJECTED")
            self.assertEqual(d_born["primary_failure_mode"], "ELASTIC_INSTABILITY")

            # 3. Stage 2 ion-migration barrier gate (emig_ev < 0.65)
            st_ion = Structure(
                Lattice.cubic(5.2),
                ["Cu", "Cu", "Cu", "Bi", "S", "S", "Cl", "Cl"],
                [
                    [0.0, 0.0, 0.0],
                    [0.5, 0.0, 0.0],
                    [0.0, 0.5, 0.0],
                    [0.5, 0.5, 0.5],
                    [0.25, 0.25, 0.25],
                    [0.75, 0.75, 0.25],
                    [0.25, 0.75, 0.75],
                    [0.75, 0.25, 0.75],
                ],
            )
            r_ion = copy.deepcopy(base)
            r_ion["mp_id"] = "mp-test-ion"
            r_ion["stoichiometry"] = {"Cu": 3, "Bi": 1, "S": 2, "Cl": 2}
            r_ion["oxidation_states"] = {"Cu": 1, "Bi": 3, "S": -2, "Cl": -1}
            r_ion["structure_dict"] = st_ion.as_dict()
            d_ion = build_live_mp_candidate_dossier(r_ion, priors, ledger)
            self.assertEqual(d_ion["status"], "REJECTED")
            self.assertEqual(d_ion["primary_failure_mode"], "ION_MIGRATION_INSTABILITY")

            # 4. Stage 3 synthesis temperature gate (temp_c > 500 C)
            d_temp = build_live_mp_candidate_dossier(cache_by_id["mp-1105202"], priors, ledger)
            self.assertEqual(d_temp["status"], "REJECTED")
            self.assertEqual(d_temp["primary_failure_mode"], "OXIDE_IMPURITY_SINK")

            # 5. Stage 3 empirical LBNL impurity-prior gate (n >= 5 and impurity_rate > 0.50)
            priors_fail = copy.deepcopy(priors)
            priors_fail["chemsys_impurity_priors"]["O-S-Sb"] = {
                "pure_count": 2,
                "impure_count": 8,
                "impurity_rate": 0.80,
            }
            d_prior = build_live_mp_candidate_dossier(base, priors_fail, ledger)
            self.assertEqual(d_prior["status"], "REJECTED")
            self.assertEqual(d_prior["primary_failure_mode"], "IMPURITY_SINK_PRIOR")

            # 6. Stage 3 Pourbaix aqueous dissolution gate (pbx_mol > 1e-6 M)
            st_pbx = Structure(
                Lattice.cubic(5.6),
                ["Cs", "Bi", "S", "S"],
                [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.25, 0.25, 0.25], [0.75, 0.75, 0.75]],
            )
            r_pbx = copy.deepcopy(base)
            r_pbx["mp_id"] = "mp-test-pbx"
            r_pbx["stoichiometry"] = {"Cs": 1, "Bi": 1, "S": 2}
            r_pbx["oxidation_states"] = {"Cs": 1, "Bi": 3, "S": -2}
            r_pbx["dft_elasticity"] = {"k_vrh_gpa": 40.0, "g_vrh_gpa": 22.0}
            r_pbx["structure_dict"] = st_pbx.as_dict()
            d_pbx = build_live_mp_candidate_dossier(r_pbx, priors, ledger)
            self.assertEqual(d_pbx["status"], "REJECTED")
            self.assertEqual(d_pbx["primary_failure_mode"], "AQUEOUS_LEACHING")

            # 7. Stage 3 active-layer cost gate (cost_m2 > $0.50/m^2)
            d_cost = build_live_mp_candidate_dossier(cache_by_id["mp-1079889"], priors, ledger)
            self.assertEqual(d_cost["status"], "REJECTED")
            self.assertEqual(d_cost["primary_failure_mode"], "TIER2_COST_EXCEEDED")

            # 8. Gate A covalent 0D/1D polaron connectivity gate
            d_pol = build_live_mp_candidate_dossier(cache_by_id["mp-21365"], priors, ledger)
            self.assertEqual(d_pol["status"], "REJECTED")
            self.assertEqual(d_pol["primary_failure_mode"], "LOW_DIM_POLARON_RISK")

            # 9. Stage 4 bandgap window gate
            r_gap = copy.deepcopy(base)
            r_gap["dft_pbe_band_gap_ev"] = 2.40
            d_gap = build_live_mp_candidate_dossier(r_gap, priors, ledger)
            self.assertEqual(d_gap["status"], "REJECTED")
            self.assertEqual(d_gap["primary_failure_mode"], "BANDGAP_OUT_OF_WINDOW")

            # 10. Stage 4 effective-mass / Frohlich-polaron gate
            r_mass = copy.deepcopy(base)
            r_mass["dft_pbe_band_gap_ev"] = 0.85
            r_mass["dfpt_dielectric"] = {"eps_inf": 2.6, "eps_static": 80.0}
            d_mass = build_live_mp_candidate_dossier(r_mass, priors, ledger)
            self.assertEqual(d_mass["status"], "REJECTED")
            self.assertEqual(d_mass["primary_failure_mode"], "HEAVY_CARRIER_MASS")

            # 11. Stage 4 deep-defect SRH gate
            st_srh = Structure(Lattice.cubic(3.6), ["Zn", "O"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
            r_srh = copy.deepcopy(base)
            r_srh["mp_id"] = "mp-test-srh"
            r_srh["stoichiometry"] = {"Zn": 1, "O": 1}
            r_srh["oxidation_states"] = {"Zn": 2, "O": -2}
            r_srh["dft_pbe_band_gap_ev"] = 1.15
            r_srh["structure_dict"] = st_srh.as_dict()
            d_srh = build_live_mp_candidate_dossier(r_srh, priors, ledger)
            self.assertEqual(d_srh["status"], "REJECTED")
            self.assertEqual(d_srh["primary_failure_mode"], "DEEP_SRH_DEFECT")

            # 12. Stage 5 optical SLME / sub-gap transmittance gate
            r_opt = copy.deepcopy(base)
            r_opt["dft_pbe_band_gap_ev"] = 1.63
            r_opt["dfpt_dielectric"] = {"eps_inf": 65.0, "eps_static": 80.0}
            d_opt = build_live_mp_candidate_dossier(r_opt, priors, ledger)
            self.assertEqual(d_opt["status"], "REJECTED")
            self.assertEqual(d_opt["primary_failure_mode"], "LOW_OPTICAL_EFFICIENCY")

            # 13. Closed-form migration heuristic gate in evaluate_spring_and_migration_heuristics
            st_emig = Structure(
                Lattice.cubic(10.0),
                ["Cu", "Cu", "S"],
                [[0.0, 0.0, 0.0], [0.185, 0.0, 0.0], [0.5, 0.5, 0.5]],
            )
            rep_emig = evaluate_spring_and_migration_heuristics(
                {
                    "candidate": {
                        "candidate_id": "mp-test-emig",
                        "formula_reduced": "Cu2S",
                        "target_layer": "BOTTOM_IR_075EV",
                        "cif_content": str(CifWriter(st_emig)),
                        "stoichiometry": {"Cu": 2, "S": 1},
                        "oxidation_states": {"Cu": 1, "S": -2},
                    }
                }
            )
            self.assertFalse(rep_emig.emig_gate_passed)
            self.assertIsNone(rep_emig.dynamically_stable)

    def test_25_all_generated_qe_decks_valid(self):
        """T3: Parse every generated QE .in deck and verify removed species, prefix, k-points/noncolin, q-mesh divisibility, and d_perp >= 10 A."""
        import copy
        import re
        import tempfile
        from collections import Counter
        from pathlib import Path
        from pymatgen.io.cif import CifParser
        from failsmart_matengine.atomistic_and_tmm import evaluate_phase9a_lab_synthesis_and_defect_supercell

        root = Path(self.repo_root)
        deck_dirs = [
            root / "outputs" / "qe_hse06_soc_decks",  # HSE06+SOC not run
            root / "outputs" / "mp_live_qe_decks",
            root / "outputs" / "mp_live_neutral_vacancy_decks",
        ]
        self.assertFalse((root / "outputs" / "mp_live_doped_supercell_decks").exists())  # doped not run

        all_decks = []
        for ddir in deck_dirs:
            self.assertTrue(ddir.is_dir(), f"Missing deck directory: {ddir}")
            decks = sorted(ddir.glob("*.in"))
            self.assertGreater(len(decks), 0, f"No .in decks in {ddir}")
            all_decks.extend(decks)

        self.assertEqual(len(all_decks), 35, f"Expected 5 + 15 + 15 = 35 .in decks, got {len(all_decks)}")

        for deck_path in all_decks:
            txt = deck_path.read_text(encoding="utf-8")
            lines = txt.splitlines()

            # 1. Prefix matches ^[A-Za-z0-9_]+$
            m_pref = re.search(r"prefix\s*=\s*'([^']*)'", txt)
            self.assertIsNotNone(m_pref, f"Missing prefix in {deck_path}")
            prefix_val = m_pref.group(1)
            self.assertRegex(prefix_val, r"^[A-Za-z0-9_]+$", f"Invalid prefix '{prefix_val}' in {deck_path}")

            # 2. No deck combines K_POINTS gamma with noncolin = .true.
            has_noncolin = bool(re.search(r"noncolin\s*=\s*\.true\.", txt, re.IGNORECASE))
            has_kpoints_gamma = bool(re.search(r"K_POINTS\s+\{?\s*gamma\s*\}?", txt, re.IGNORECASE))
            self.assertFalse(
                has_noncolin and has_kpoints_gamma,
                f"Deck {deck_path} combines noncolin=.true. with K_POINTS gamma",
            )

            # 3. Hybrid q-mesh divides k-mesh in every direction
            m_nqx1 = re.search(r"nqx1\s*=\s*(\d+)", txt)
            m_nqx2 = re.search(r"nqx2\s*=\s*(\d+)", txt)
            m_nqx3 = re.search(r"nqx3\s*=\s*(\d+)", txt)
            if m_nqx1 or m_nqx2 or m_nqx3:
                nqx = (int(m_nqx1.group(1)), int(m_nqx2.group(1)), int(m_nqx3.group(1)))
                k_idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith("K_POINTS"))
                k_vals = [int(x) for x in lines[k_idx + 1].split()[:3]]
                for axis_idx, (kv, qv) in enumerate(zip(k_vals, nqx)):
                    self.assertGreaterEqual(qv, 1)
                    self.assertEqual(
                        kv % qv,
                        0,
                        f"{deck_path}: k[{axis_idx}]={kv} not divisible by nqx[{axis_idx}]={qv}",
                    )

        # 4. Neutral vacancy supercell checks: removed species == labelled species & min perpendicular spacing >= 10.0 A
        live_sum = json.loads((root / "outputs" / "live_mp_discovery_summary.json").read_text(encoding="utf-8"))
        fins_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum["finalists"]}
        lab_by_id = {ld["candidate_id"]: ld for ld in live_sum["lab_synthesis_and_defect_dossiers"]}

        for cid, ld in lab_by_id.items():
            fin = fins_by_id[cid]
            deck_path = root / "outputs" / "mp_live_neutral_vacancy_decks" / ld["neutral_vacancy_deck_filename"]
            txt = deck_path.read_text(encoding="utf-8")
            lines = txt.splitlines()

            # Parse CELL_PARAMETERS and ATOMIC_POSITIONS directly from the .in deck
            cell_idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith("CELL_PARAMETERS"))
            smat = np.array(
                [[float(x) for x in lines[cell_idx + 1 + r].split()] for r in range(3)],
                dtype=float,
            )
            svol = abs(float(np.linalg.det(smat)))
            perp_spacings = [
                svol / float(np.linalg.norm(np.cross(smat[1], smat[2]))),
                svol / float(np.linalg.norm(np.cross(smat[2], smat[0]))),
                svol / float(np.linalg.norm(np.cross(smat[0], smat[1]))),
            ]
            min_perp = min(perp_spacings)
            self.assertGreaterEqual(
                min_perp,
                10.0,
                f"{deck_path}: min perpendicular spacing {min_perp:.4f} A < 10.0 A",
            )

            pos_idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith("ATOMIC_POSITIONS"))
            k_idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith("K_POINTS"))
            deck_counts: Counter = Counter()
            for ln in lines[pos_idx + 1 : k_idx]:
                parts = ln.split()
                if len(parts) >= 4:
                    deck_counts[parts[0]] += 1

            unit_struct = CifParser.from_str(fin["candidate"]["cif_content"]).parse_structures(primitive=False)[0]
            na, nb, nc = ld["supercell_dims"]
            mult = na * nb * nc
            unit_counts = Counter(site.specie.symbol for site in unit_struct)
            expected_host_counts = {el: cnt * mult for el, cnt in unit_counts.items()}

            diffs = {el: expected_host_counts[el] - deck_counts.get(el, 0) for el in expected_host_counts}
            removed_els = [el for el, d in diffs.items() if d != 0]
            self.assertEqual(len(removed_els), 1, f"{deck_path}: expected 1 species count to change, got {diffs}")
            removed_el = removed_els[0]
            self.assertEqual(diffs[removed_el], 1, f"{deck_path}: expected 1 atom removed, got {diffs}")

            # Check removed species equals labelled species in header, dossier, and defect label
            m_hdr = re.search(r"Removed Species:\s*([A-Za-z]+)", txt)
            self.assertIsNotNone(m_hdr, f"Missing Removed Species header in {deck_path}")
            self.assertEqual(removed_el, m_hdr.group(1))
            self.assertEqual(removed_el, ld["dominant_vacancy_element"])
            self.assertEqual(removed_el, fin["electronics"]["dominant_vacancy_element"])
            self.assertTrue(
                ld["dominant_vacancy_species"].startswith(f"V_{removed_el} "),
                f"Label '{ld['dominant_vacancy_species']}' does not match V_{removed_el}",
            )

        # 5. Absent species raises ValueError
        bad_fin = copy.deepcopy(next(iter(fins_by_id.values())))
        bad_fin["electronics"]["dominant_vacancy_element"] = "Xe"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                evaluate_phase9a_lab_synthesis_and_defect_supercell(bad_fin, td)

    def test_26_provenance_tags_and_no_false_method_labels(self):
        """T2: Verify provenance tags on every numeric dossier field, renamed SQLite columns, and zero false method labels."""
        import re
        from pathlib import Path
        from failsmart_matengine.schemas import ProvenanceTag

        valid_tags = {t.value for t in ProvenanceTag}
        root = Path(self.repo_root)

        def _assert_numeric_provenance(obj: dict, label: str) -> None:
            self.assertIn("provenance", obj, f"{label} missing 'provenance' dict")
            prov = obj["provenance"]
            self.assertIsInstance(prov, dict, f"{label} provenance must be a dict")
            for k, v in obj.items():
                if k == "provenance":
                    continue
                is_num = isinstance(v, (int, float)) and not isinstance(v, bool)
                is_num_seq = (
                    isinstance(v, list)
                    and len(v) > 0
                    and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)
                )
                if is_num or is_num_seq:
                    self.assertIn(k, prov, f"{label}.{k} missing provenance entry")
                    self.assertIn(prov[k], valid_tags, f"{label}.{k} has invalid provenance '{prov[k]}'")

        # 1. Check pilot_campaign_summary.json and live_mp_discovery_summary.json numeric provenance
        for rec in self.summary_data.get("all_campaign_records", []):
            cid = rec["candidate"]["candidate_id"]
            for sec in ("candidate", "stability", "synthesis", "gate_a", "electronics", "optics"):
                if rec.get(sec):
                    _assert_numeric_provenance(rec[sec], f"pilot.{cid}.{sec}")

        live_sum = json.loads((root / "outputs" / "live_mp_discovery_summary.json").read_text(encoding="utf-8"))
        for rec in live_sum.get("all_mp_records", []):
            cid = rec["candidate"]["candidate_id"]
            for sec in ("candidate", "stability", "synthesis", "gate_a", "electronics", "optics"):
                if rec.get(sec):
                    _assert_numeric_provenance(rec[sec], f"mp.{cid}.{sec}")

        for list_key in (
            "spring_and_migration_reports",
            "coherent_tmm_4t_stacks",
            "graded_arc_techno_economic_stacks",
            "lab_synthesis_and_defect_dossiers",
            "real_world_lcoe_stress_test_stacks",
            "phase10_bifacial_and_string_dossiers",
            "phase11a_synthesis_contact_dossiers",
            "phase11b_realistic_commercialization_dossiers",
        ):
            items = live_sum.get(list_key, [])
            self.assertGreater(len(items), 0, f"Expected non-empty {list_key}")
            for idx, item in enumerate(items):
                _assert_numeric_provenance(item, f"{list_key}[{idx}]")

        # 2. Check SQLite columns in both databases
        for db_rel in ("data/failure_memory.db", "data/mp_live_failure_memory.db"):
            conn = sqlite3.connect(str(root / db_rel))
            cols = {row[1] for row in conn.execute("PRAGMA table_info(material_evaluations)").fetchall()}
            conn.close()
            self.assertIn("composition_embedding", cols, f"{db_rel} missing composition_embedding")
            self.assertIn("gap_est_indirect_ev", cols, f"{db_rel} missing gap_est_indirect_ev")
            self.assertNotIn("mace" + "_embedding", cols, f"{db_rel} still has old embedding column")
            self.assertNotIn("hse06" + "_soc_gap_ev", cols, f"{db_rel} still has old gap column")

        # 3. Check T2 grep rule across README.md, docs/, failsmart_matengine/, and outputs/
        pattern = re.compile(r"hse06|r2scan|neb|fnv|mace|doped|cryptograph|validated", re.IGNORECASE)
        exempt_files = {
            root / "docs" / "INDEPENDENT_AUDIT_2026-11.md",
            root / "docs" / "REMEDIATION_TASKS.md",
            root / "docs" / "GAP_CALIBRATION.md",
        }
        scan_targets = [root / "README.md", root / "docs", root / "failsmart_matengine", root / "outputs"]
        violations = []
        for target in scan_targets:
            files = [target] if target.is_file() else sorted(p for p in target.rglob("*") if p.is_file())
            for fpath in files:
                if fpath in exempt_files or "__pycache__" in fpath.parts or fpath.suffix == ".pyc":
                    continue
                if fpath.suffix == ".in":
                    continue
                txt = fpath.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(txt.splitlines(), start=1):
                    if pattern.search(line) and "not run" not in line.lower():
                        violations.append(f"{fpath.relative_to(root)}:{line_no}: {line.strip()[:120]}")
        self.assertEqual(violations, [], f"T2 false-method-label violations:\n" + "\n".join(violations))

    def test_27_t4_gap_calibration_and_literature_gate(self):
        """T4: Verify data/finalist_literature.json, data/gap_benchmark.csv (>=50 compounds), docs/GAP_CALIBRATION.md, and error bars."""
        import csv
        from pathlib import Path

        root = Path(self.repo_root)
        lit_path = root / "data" / "finalist_literature.json"
        csv_path = root / "data" / "gap_benchmark.csv"
        doc_path = root / "docs" / "GAP_CALIBRATION.md"

        self.assertTrue(lit_path.is_file(), "Missing data/finalist_literature.json")
        self.assertTrue(csv_path.is_file(), "Missing data/gap_benchmark.csv")
        self.assertTrue(doc_path.is_file(), "Missing docs/GAP_CALIBRATION.md")

        # 1. Verify finalist_literature.json
        lit_data = json.loads(lit_path.read_text(encoding="utf-8"))
        fins = lit_data.get("finalists", [])
        self.assertGreaterEqual(len(fins), 8, "Expected at least 8 finalists in finalist_literature.json")
        fins_by_id = {f["mp_id"]: f for f in fins}
        for req_id in (
            "mp-861911",
            "mp-1227486",
            "mp-1078776",
            "mp-1223998",
            "mp-1224922",
            "mp-22982",
            "mp-23474",
            "mp-1224129",
        ):
            self.assertIn(req_id, fins_by_id, f"Missing {req_id} in finalist_literature.json")
            entry = fins_by_id[req_id]
            for k in (
                "mp_id",
                "formula",
                "mp_space_group_symbol",
                "mp_space_group_number",
                "mp_marked_experimentally_known",
                "corresponds_to_synthesised_phase",
                "measured_optical_gap_ev",
                "reported_pv_device",
                "citations",
                "provenance",
            ):
                self.assertIn(k, entry, f"{req_id} missing key {k} in finalist_literature.json")

        self.assertAlmostEqual(fins_by_id["mp-22982"]["measured_optical_gap_ev"], 1.65, places=2)
        self.assertTrue(fins_by_id["mp-22982"]["corresponds_to_synthesised_phase"])
        self.assertFalse(fins_by_id["mp-861911"]["corresponds_to_synthesised_phase"])

        # 2. Verify gap_benchmark.csv (>= 50 matched MP rows with citations)
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        matched_rows = [r for r in rows if r["mp_status"] == "matched"]
        self.assertGreaterEqual(len(matched_rows), 50, f"Expected >= 50 matched rows in gap_benchmark.csv, got {len(matched_rows)}")
        for r in matched_rows:
            self.assertTrue(r["mp_id"].startswith("mp-"), f"Invalid mp_id in benchmark row: {r}")
            self.assertGreater(float(r["measured_gap_ev"]), 0.0)
            self.assertTrue(r["source_doi"] or r["source_url"], f"Benchmark row {r['formula']} missing DOI/URL")

        # 3. Verify GAP_CALIBRATION.md contains calibration metrics
        doc_txt = doc_path.read_text(encoding="utf-8")
        for tok in ("0.4522", "-0.5350", "0.3684", "0.4362", "Morales"):
            self.assertIn(tok, doc_txt, f"Expected '{tok}' in docs/GAP_CALIBRATION.md")

        # 4. Verify gap_error_bar_ev and window_probability on all live MP finalists
        live_sum = json.loads((root / "outputs" / "live_mp_discovery_summary.json").read_text(encoding="utf-8"))
        for fin in live_sum.get("finalists", []):
            el = fin["electronics"]
            self.assertAlmostEqual(el["gap_error_bar_ev"], 0.37, places=2)
            self.assertGreater(el["window_probability"], 0.0)
            self.assertLessEqual(el["window_probability"], 0.25)


if __name__ == "__main__":
    unittest.main()
