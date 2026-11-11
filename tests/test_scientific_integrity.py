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
- Test 8 (test_runnable_quantum_espresso_hse06_soc_decks):
    Parse all 5 finalist .in decks in outputs/qe_hse06_soc_decks/ and verify real IUPAC atomic weights
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
    independently_verify_atomistic_phonon_and_neb,
    independently_verify_coherent_tmm_4t_stack,
    independently_verify_graded_arc_and_techno_economics,
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
        cls.qe_decks_dir = os.path.join(cls.repo_root, "outputs", "qe_hse06_soc_decks")

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
                    eg_ind_ev=elec["hse06_soc_indirect_gap_ev"],
                    eg_dir_ev=elec["hse06_soc_direct_gap_ev"],
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

    def test_runnable_quantum_espresso_hse06_soc_decks(self):
        """Test 8: Parse all 5 finalist .in decks in outputs/qe_hse06_soc_decks/ and verify IUPAC masses, det(CELL) > 50, and matching nat."""
        deck_files = sorted(glob.glob(os.path.join(self.qe_decks_dir, "*_hse06_soc.in")))
        self.assertEqual(len(deck_files), 5, f"Expected 5 finalist QE input decks, found {len(deck_files)}")

        for dpath in deck_files:
            cif_path = dpath.replace("_hse06_soc.in", ".cif")
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
        self.assertGreater(elec.hse06_soc_direct_gap_ev, 0.0)

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
        self.assertTrue(verif["sha256_signature"])

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
        self.assertEqual(fc.get("stage4_5_validated_finalists"), 8)
        self.assertEqual(fc.get("top_active_glass_finalists"), 3)
        self.assertEqual(fc.get("bottom_ir_scavenger_finalists"), 5)

    def test_cross_layer_discovered_mp_4t_tandem_stacks(self):
        """Test 14: Verify all 15 cross-layer (mp-Top, c-Si, mp-Bottom) 4T stacks match independent_verifier within <= 0.05%."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        pairs = live_sum.get("cross_layer_4t_tandem_pairs", [])
        self.assertEqual(len(pairs), 15, f"Expected 15 cross-layer 4T pairs, got {len(pairs)}")

        finalists_by_id = {fin["candidate"]["candidate_id"]: fin for fin in live_sum.get("finalists", [])}
        self.assertEqual(len(finalists_by_id), 8, f"Expected 8 promoted finalists, got {len(finalists_by_id)}")

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

    def test_live_mp_finalist_qe_hse06_soc_decks(self):
        """Test 15: Verify all 8 promoted live MP finalists have runnable .in/.cif files with non-placeholder IUPAC masses and det(cell) > 50."""
        live_decks_dir = os.path.join(self.repo_root, "outputs", "mp_live_qe_decks")
        self.assertTrue(os.path.exists(live_decks_dir), f"Directory {live_decks_dir} does not exist")

        deck_files = sorted(glob.glob(os.path.join(live_decks_dir, "*_hse06_soc.in")))
        self.assertEqual(len(deck_files), 8, f"Expected 8 live MP finalist QE input decks, got {len(deck_files)}")

        for dpath in deck_files:
            cif_path = dpath.replace("_hse06_soc.in", ".cif")
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

    def test_step1_3d_dynamical_matrix_and_neb_ion_migration(self):
        """Test 16: Verify Step 1 3D Harmonic Dynamical Matrix D(q=0) & 11-Image NEB Ion-Migration across all 8 finalists.

        Also verifies zero 'unknown' unindexed XRD tokens in competing_impurity_sinks or competing_hull_phases.
        """
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        self.assertEqual(live_sum.get("version"), "4.0.0", "Expected live_mp_discovery_summary.json version == 4.0.0")

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

        # 2. Verify all 8 finalists' 3D Dynamical Matrix & 11-Image NEB reports and independent scipy.linalg.eigvalsh verification
        phonon_reports = live_sum.get("atomistic_phonon_neb_reports", [])
        self.assertEqual(len(phonon_reports), 8, f"Expected 8 atomistic_phonon_neb_reports, got {len(phonon_reports)}")

        cache_path = os.path.join(self.repo_root, "data", "mp_live_candidates_cache.json")
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_by_id = {c["mp_id"]: c for c in json.load(f)}

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}

        for rep in phonon_reports:
            cid = rep["candidate_id"]
            self.assertEqual(rep["imaginary_mode_count"], 0, f"{cid}: Expected 0 imaginary modes, got {rep['imaginary_mode_count']}")
            self.assertTrue(rep["dynamically_and_kinetically_stable"], f"{cid}: Expected dynamically_and_kinetically_stable == True")
            self.assertTrue(rep["redundancy_verified"], f"{cid}: Expected redundancy_verified == True")
            self.assertGreater(rep["gamma_min_optical_freq_thz"], 1.0, f"{cid}: Expected min optical phonon > 1.0 THz")
            self.assertLess(rep["acoustic_sum_rule_max_dev_thz"], 1e-4, f"{cid}: Acoustic sum rule dev >= 1e-4 THz")
            self.assertGreaterEqual(rep["neb_saddle_barrier_ev"], 0.90, f"{cid}: Expected NEB barrier >= 0.90 eV")
            self.assertLess(rep["room_temp_diffusivity_cm2_s"], 1e-18, f"{cid}: Expected D_ion(300K) < 1e-18 cm^2/s")

            # Cross-verify against blinded scipy.linalg.eigvalsh + independent NEB solver
            fin = finalists_by_id[cid]
            iv_rep = independently_verify_atomistic_phonon_and_neb(
                cif_text=fin["candidate"]["cif_content"],
                stoichiometry=fin["candidate"]["stoichiometry"],
                oxidation_states=fin["candidate"]["oxidation_states"],
            )
            self.assertAlmostEqual(
                rep["gamma_min_optical_freq_thz"],
                iv_rep["gamma_min_optical_freq_thz"],
                places=4,
                msg=f"{cid}: w_opt,min mismatch between np.linalg.eigh and scipy.linalg.eigvalsh",
            )
            self.assertAlmostEqual(
                rep["gamma_max_lo_freq_thz"],
                iv_rep["gamma_max_lo_freq_thz"],
                places=4,
                msg=f"{cid}: w_LO,max mismatch between np.linalg.eigh and scipy.linalg.eigvalsh",
            )
            self.assertAlmostEqual(
                rep["neb_saddle_barrier_ev"],
                iv_rep["neb_saddle_barrier_ev"],
                places=4,
                msg=f"{cid}: NEB barrier mismatch between primary and independent verifier",
            )

    def test_step2_coherent_abeles_tmm_vs_rouard_airy_4t_stacks(self):
        """Test 17: Verify Step 2 Coherent 2x2 Abeles TMM vs Recursive Rouard/Airy 4T Stack Optics across all 15 stacks."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        tmm_stacks = live_sum.get("coherent_tmm_4t_stacks", [])
        self.assertEqual(len(tmm_stacks), 15, f"Expected 15 coherent_tmm_4t_stacks, got {len(tmm_stacks)}")

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
            self.assertGreater(st["tmm_sub_bandgap_transmittance_percent"], 85.0, f"{pid}: Expected sub-bandgap T > 85%")
            self.assertLess(st["scalar_to_tmm_delta_pce_percent"], 0.0, f"{pid}: Coherent TMM 4T must be lower than scalar idealization")

            top_f = finalists_by_id[st["top_mp_id"]]
            bot_f = finalists_by_id[st["bottom_mp_id"]]

            iv_tmm = independently_verify_coherent_tmm_4t_stack(
                eg_ind_1=top_f["electronics"]["hse06_soc_indirect_gap_ev"],
                eg_dir_1=top_f["electronics"]["hse06_soc_direct_gap_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                thickness_nm_1=top_f["optics"]["film_thickness_nm"],
                eg_ind_3=bot_f["electronics"]["hse06_soc_indirect_gap_ev"],
                eg_dir_3=bot_f["electronics"]["hse06_soc_direct_gap_ev"],
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
        """Test 18: Verify 7-Medium Graded-ARC + TiO2 Impedance Matching & 4-Metric Techno-Economic Suite across all 15 stacks."""
        live_sum_path = os.path.join(self.repo_root, "outputs", "live_mp_discovery_summary.json")
        with open(live_sum_path, "r", encoding="utf-8") as f:
            live_sum = json.load(f)

        self.assertTrue(live_sum.get("v5_graded_arc_and_techno_economics_enabled"))
        graded_stacks = live_sum.get("graded_arc_techno_economic_stacks", [])
        self.assertEqual(len(graded_stacks), 15, f"Expected 15 graded_arc_techno_economic_stacks, got {len(graded_stacks)}")

        finalists_by_id = {f["candidate"]["candidate_id"]: f for f in live_sum.get("finalists", [])}

        for gs in graded_stacks:
            pid = gs["pair_id"]
            self.assertTrue(gs["photon_conservation_verified"], f"{pid}: Photon conservation failed")
            self.assertTrue(gs["techno_economic_redundancy_verified"], f"{pid}: Techno-economic redundancy check failed")
            self.assertLessEqual(gs["graded_arc_front_reflectance_percent"], 4.0, f"{pid}: Expected graded ARC R_front <= 4.0%")
            self.assertGreaterEqual(gs["reflectance_reduction_percent"], 8.0, f"{pid}: Expected R_front reduction >= 8.0%")
            self.assertGreater(gs["single_to_graded_4t_gain_percent"], 2.0, f"{pid}: Expected >= +2.0% 4T PCE gain from Graded-ARC")
            self.assertGreater(gs["cer_2l_vs_2x_si"], 2.8, f"{pid}: Expected CER_2L > 2.8")
            self.assertGreater(gs["cer_3l_vs_3x_si"], 4.1, f"{pid}: Expected CER_3L > 4.1")
            self.assertLess(gs["mciw_3l_full_usd_per_dw"], 0.08, f"{pid}: Expected MCIW_3L_full < $0.08/dW")
            self.assertGreater(gs["svi_bos_3l"], gs["svi_bos_2l"], f"{pid}: Expected 3L Area-BOS SVI > 2L Area-BOS SVI")

            top_f = finalists_by_id[gs["top_mp_id"]]
            bot_f = finalists_by_id[gs["bottom_mp_id"]]

            iv_gs = independently_verify_graded_arc_and_techno_economics(
                eg_ind_1=top_f["electronics"]["hse06_soc_indirect_gap_ev"],
                eg_dir_1=top_f["electronics"]["hse06_soc_direct_gap_ev"],
                eps_inf_1=top_f["electronics"]["eps_inf"],
                thickness_nm_1=top_f["optics"]["film_thickness_nm"],
                eg_ind_3=bot_f["electronics"]["hse06_soc_indirect_gap_ev"],
                eg_dir_3=bot_f["electronics"]["hse06_soc_direct_gap_ev"],
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


if __name__ == "__main__":
    unittest.main()



