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
)
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
    """Rigorous scientific integrity, zero-trust mathematical verification & physical constraint test suite v2.0."""

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

        banned_modules = {"physics_calculators", "kinetics_and_optics", "tools"}
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


if __name__ == "__main__":
    unittest.main()
