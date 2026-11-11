"""External-truth physics and crystal-chemistry test suite (Task T5).

Each test compares a `failsmart_matengine` calculator output against an independent
external analytical result, published standard table, or experimental crystal-chemistry
reference with an explicit tolerance. None of these tests pin internal campaign funnel
snapshots; they run standalone via `pytest -m "not regression"`.
"""

from __future__ import annotations

import csv
import json
import math
import unittest
from pathlib import Path

import numpy as np
from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram
from pymatgen.core import Composition, Lattice, Structure

from failsmart_matengine.atomistic_and_tmm import (
    compute_general_abeles_tmm_reflectance_transmittance,
)
from failsmart_matengine.independent_verifier import independently_verify_cif_geometry
from failsmart_matengine.kinetics_and_optics import (
    Q_E,
    _AM15G_E_EV,
    _AM15G_PHI_SUN,
    _AM15G_WL_NM,
    compute_4t_tandem_optics_wavelength_grid,
)
from failsmart_matengine.mp_live_discovery import (
    _estimate_gap_from_mp_pbe,
    compute_covalent_dimensionality_from_structure,
)
from failsmart_matengine.physics_calculators import verify_charge_neutrality

_REPO_ROOT = Path(__file__).resolve().parents[1]


class TestExternalPhysicsTruth(unittest.TestCase):
    """External-truth tests against published physical limits, analytic optics, and crystal chemistry."""

    def test_01_sq_radiative_limit_at_134_ev_matches_ruhle_2016(self) -> None:
        """SQ radiative efficiency limit at 1.34 eV is close to 33.7% under AM1.5G (Ruhle 2016, DOI: 10.1016/j.solener.2016.02.015)."""
        res = compute_4t_tandem_optics_wavelength_grid(
            target_layer="TOP_ACTIVE_GLASS_185EV",
            eg_ind_ev=1.34,
            eg_dir_ev=1.34,
            eps_inf=10.0,
            thickness_nm=300.0,
        )
        sq_134 = res["shockley_queisser_limit_percent"]
        # Published 1-sun AM1.5G global (1000 W/m^2, T_cell=298.15-300 K) detailed-balance peak is 33.7% at 1.34 eV
        self.assertAlmostEqual(
            sq_134,
            33.7,
            delta=0.6,
            msg=f"Expected SQ limit at 1.34 eV within 33.7 +/- 0.6%, got {sq_134:.2f}%",
        )

    def test_02_sq_radiative_limit_at_112_ev_matches_silicon_bandgap(self) -> None:
        """SQ radiative efficiency limit at 1.12 eV (c-Si bandgap) lies in 32-33.5% (Ruhle 2016, DOI: 10.1016/j.solener.2016.02.015)."""
        res = compute_4t_tandem_optics_wavelength_grid(
            target_layer="TOP_ACTIVE_GLASS_185EV",
            eg_ind_ev=1.12,
            eg_dir_ev=1.12,
            eps_inf=11.7,
            thickness_nm=300.0,
        )
        sq_112 = res["shockley_queisser_limit_percent"]
        self.assertGreaterEqual(sq_112, 32.0, f"Expected SQ(1.12 eV) >= 32.0%, got {sq_112:.2f}%")
        self.assertLessEqual(sq_112, 33.5, f"Expected SQ(1.12 eV) <= 33.5%, got {sq_112:.2f}%")

    def test_03_am15g_integrated_photon_current_above_112_ev(self) -> None:
        """Integrated ASTM G173-03 AM1.5G photon current above 1.12 eV is 43-44 mA/cm^2 (Ruhle 2016 Table 1: 43.8 mA/cm^2)."""
        step_abs = np.where(_AM15G_E_EV >= 1.12, 1.0, 0.0)
        jsc_112_ma_cm2 = float(0.1 * Q_E * np.trapezoid(step_abs * _AM15G_PHI_SUN, _AM15G_WL_NM))
        self.assertGreaterEqual(
            jsc_112_ma_cm2,
            43.0,
            f"Expected integrated AM1.5G J_sc(>=1.12 eV) >= 43.0 mA/cm^2, got {jsc_112_ma_cm2:.2f}",
        )
        self.assertLessEqual(
            jsc_112_ma_cm2,
            44.5,
            f"Expected integrated AM1.5G J_sc(>=1.12 eV) <= 44.5 mA/cm^2, got {jsc_112_ma_cm2:.2f}",
        )

    def test_04_tmm_bare_glass_interface_matches_analytic_fresnel(self) -> None:
        """Normal-incidence Abeles TMM on bare air/glass (n=1.50) matches Fresnel R = ((n-1)/(n+1))^2 = 4.000% (Born & Wolf Sec. 1.5.2)."""
        wl_nm = np.linspace(400.0, 1000.0, 25)
        n_air = np.ones_like(wl_nm, dtype=np.complex128)
        n_glass = np.full_like(wl_nm, 1.50, dtype=np.complex128)
        r_tmm, t_tmm = compute_general_abeles_tmm_reflectance_transmittance(
            n_list=[n_air, n_glass],
            d_list_nm=[0.0, 0.0],
            wl_nm=wl_nm,
        )
        r_analytic = ((1.50 - 1.0) / (1.50 + 1.0)) ** 2  # 0.04
        t_analytic = 4.0 * 1.0 * 1.50 / ((1.50 + 1.0) ** 2)  # 0.96
        np.testing.assert_allclose(r_tmm, r_analytic, atol=1e-12)
        np.testing.assert_allclose(t_tmm, t_analytic, atol=1e-12)

    def test_05_tmm_quarter_wave_antireflection_coating_matches_analytic_formula(self) -> None:
        """Quarter-wave coating d = lambda0 / (4*n1) matches R(lambda0) = ((n1^2 - n0*ns)/(n1^2 + n0*ns))^2 (Hecht Optics Sec. 9.4)."""
        lambda0_nm = 600.0
        wl_nm = np.array([lambda0_nm], dtype=float)
        n0_val = 1.00
        ns_val = 2.25

        # Case A: Ideal index-matched quarter-wave film n1 = sqrt(n0 * ns) = 1.50 -> R = 0, T = 1
        n1_ideal = math.sqrt(n0_val * ns_val)
        d1_ideal_nm = lambda0_nm / (4.0 * n1_ideal)
        r_ideal, t_ideal = compute_general_abeles_tmm_reflectance_transmittance(
            n_list=[
                np.array([n0_val], dtype=np.complex128),
                np.array([n1_ideal], dtype=np.complex128),
                np.array([ns_val], dtype=np.complex128),
            ],
            d_list_nm=[0.0, d1_ideal_nm, 0.0],
            wl_nm=wl_nm,
        )
        self.assertAlmostEqual(float(r_ideal[0]), 0.0, places=12)
        self.assertAlmostEqual(float(t_ideal[0]), 1.0, places=12)

        # Case B: MgF2 (n1 = 1.38) quarter-wave film on crown glass (ns = 1.52) -> R = ((1.38^2 - 1.52)/(1.38^2 + 1.52))^2
        n1_mgf2 = 1.38
        ns_glass = 1.52
        d1_mgf2_nm = lambda0_nm / (4.0 * n1_mgf2)
        r_mgf2, t_mgf2 = compute_general_abeles_tmm_reflectance_transmittance(
            n_list=[
                np.array([n0_val], dtype=np.complex128),
                np.array([n1_mgf2], dtype=np.complex128),
                np.array([ns_glass], dtype=np.complex128),
            ],
            d_list_nm=[0.0, d1_mgf2_nm, 0.0],
            wl_nm=wl_nm,
        )
        r_expected = ((n1_mgf2 ** 2 - n0_val * ns_glass) / (n1_mgf2 ** 2 + n0_val * ns_glass)) ** 2
        self.assertAlmostEqual(float(r_mgf2[0]), r_expected, places=12)
        self.assertAlmostEqual(float(r_mgf2[0] + t_mgf2[0]), 1.0, places=12)

    def test_06_dimensionality_classifier_known_1d_chain_structures(self) -> None:
        """Known 1D-ribbon structures BiSCl (mp-23318) and SbSI (mp-23041) classify as '1D-Chain' (Voutsas & Rentzeperis 1980, Z. Kristallogr. 152:109)."""
        cache_path = _REPO_ROOT / "data" / "mp_live_candidates_cache.json"
        cache_by_id = {c["mp_id"]: c for c in json.loads(cache_path.read_text(encoding="utf-8"))}

        for mp_id, expected_formula in (("mp-23318", "BiSCl"), ("mp-23041", "SbSI")):
            self.assertIn(mp_id, cache_by_id)
            struct = Structure.from_dict(cache_by_id[mp_id]["structure_dict"])
            self.assertEqual(struct.composition.reduced_formula, expected_formula)
            dim = compute_covalent_dimensionality_from_structure(struct)
            self.assertEqual(dim, "1D-Chain", f"Expected {expected_formula} ({mp_id}) to be 1D-Chain, got {dim}")

    def test_07_dimensionality_classifier_known_2d_layered_matlockite(self) -> None:
        """Known 2D-layered matlockite BiOI (P4/nmm, Bannister 1935 Mineral. Mag. 24:49; Ganose et al. 2016 DOI: 10.1039/C6TC01164K) classifies as 'Quasi-2D'."""
        # Experimental tetragonal P4/nmm BiOI structure: a = 3.994 A, c = 9.149 A
        struct_bioi = Structure(
            Lattice.tetragonal(3.994, 9.149),
            ["Bi", "Bi", "O", "O", "I", "I"],
            [
                [0.0, 0.5, 0.132],
                [0.5, 0.0, 0.868],
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.0],
                [0.0, 0.5, 0.668],
                [0.5, 0.0, 0.332],
            ],
        )
        dim = compute_covalent_dimensionality_from_structure(struct_bioi)
        self.assertEqual(dim, "Quasi-2D", f"Expected layered matlockite BiOI to classify as Quasi-2D, got {dim}")

    def test_08_dimensionality_classifier_known_3d_framework_structures(self) -> None:
        """Known 3D-framework structures BaZrS3 perovskite (Lelieveld & IJdo 1980, DOI: 10.1107/S056774088000845X) and stannite CuInSnSe4 classify as '3D'."""
        struct_bazrs3 = Structure(
            Lattice.cubic(4.99),
            ["Ba", "Zr", "S", "S", "S"],
            [
                [0.0, 0.0, 0.0],
                [0.5, 0.5, 0.5],
                [0.5, 0.5, 0.0],
                [0.5, 0.0, 0.5],
                [0.0, 0.5, 0.5],
            ],
        )
        self.assertEqual(compute_covalent_dimensionality_from_structure(struct_bazrs3), "3D")

        cache_path = _REPO_ROOT / "data" / "mp_live_candidates_cache.json"
        cache_by_id = {c["mp_id"]: c for c in json.loads(cache_path.read_text(encoding="utf-8"))}
        for mp_id in ("mp-1224922", "mp-1224129"):
            struct = Structure.from_dict(cache_by_id[mp_id]["structure_dict"])
            self.assertEqual(compute_covalent_dimensionality_from_structure(struct), "3D")

    def test_09_gap_estimate_on_five_t4_benchmark_materials_within_error_bar(self) -> None:
        """Gap estimate on 5 experimental pnictogen chalcogenide/chalcohalide absorbers lies within the T4 LOOCV MAE (0.37 eV)."""
        csv_path = _REPO_ROOT / "data" / "gap_benchmark.csv"
        with open(csv_path, "r", encoding="utf-8") as f:
            rows_by_formula = {r["formula"]: r for r in csv.DictReader(f) if r["mp_status"] == "matched"}

        cache_path = _REPO_ROOT / "data" / "mp_live_candidates_cache.json"
        cache_by_id = {c["mp_id"]: c for c in json.loads(cache_path.read_text(encoding="utf-8"))}

        target_benchmarks = ("CuSbS2", "CuSbSe2", "AgBiS2", "SbSI", "Sb2S2O")
        t4_error_bar_ev = 0.37

        for formula in target_benchmarks:
            self.assertIn(formula, rows_by_formula, f"Benchmark compound {formula} missing from gap_benchmark.csv")
            row = rows_by_formula[formula]
            mp_id = row["mp_id"]
            self.assertIn(mp_id, cache_by_id, f"MP entry {mp_id} ({formula}) missing from mp_live_candidates_cache.json")
            rec = cache_by_id[mp_id]
            stoich = {str(k): int(v) for k, v in rec["stoichiometry"].items()}
            struct = Structure.from_dict(rec["structure_dict"])
            measured_gap = float(row["measured_gap_ev"])

            res = _estimate_gap_from_mp_pbe(rec, stoich, struct)
            est_gap = float(res["gap_est_indirect_ev"])
            abs_err = abs(est_gap - measured_gap)
            self.assertLessEqual(
                abs_err,
                t4_error_bar_ev,
                f"{formula} ({mp_id}): |est ({est_gap:.2f} eV) - measured ({measured_gap:.2f} eV)| = {abs_err:.3f} eV > {t4_error_bar_ev} eV",
            )

    def test_10_pauling_charge_neutrality_known_stable_and_aliovalent_compositions(self) -> None:
        """Pauling electrostatic valence neutrality (Pauling 1929, DOI: 10.1021/ja01379a006) holds for stable compounds and rejects imbalanced ones."""
        # Known charge-neutral compounds return net charge == 0
        self.assertEqual(verify_charge_neutrality({"Sb": 2, "S": 3}, {"Sb": 3, "S": -2}), 0)
        self.assertEqual(verify_charge_neutrality({"Cu": 1, "Bi": 1, "S": 2}, {"Cu": 1, "Bi": 3, "S": -2}), 0)
        self.assertEqual(verify_charge_neutrality({"Ba": 1, "Zr": 1, "S": 3}, {"Ba": 2, "Zr": 4, "S": -2}), 0)
        self.assertEqual(verify_charge_neutrality({"Bi": 1, "O": 1, "I": 1}, {"Bi": 3, "O": -2, "I": -1}), 0)
        self.assertEqual(verify_charge_neutrality({"Cu": 2, "Zn": 1, "Sn": 1, "S": 4}, {"Cu": 1, "Zn": 2, "Sn": 4, "S": -2}), 0)

        # Non-neutral stoichiometries must raise ValueError
        with self.assertRaises(ValueError):
            verify_charge_neutrality({"Cu": 1, "Bi": 1, "S": 3}, {"Cu": 1, "Bi": 3, "S": -2})
        with self.assertRaises(ValueError):
            verify_charge_neutrality({"Sb": 2, "S": 2, "Cl": 3}, {"Sb": 3, "S": -2, "Cl": -1})

    def test_11_convex_hull_lookup_on_known_ground_state_minerals(self) -> None:
        """Known ground-state minerals CuBiS2 (mp-22982, emplectite) and AgBi3S5 (mp-23474, pavonite) sit on the 0 K convex hull (Ong et al. 2008, DOI: 10.1021/cm702327g)."""
        from failsmart_matengine.realistic_commercialization import (
            evaluate_phase11a_synthesis_and_contacts,
            load_mp_thermo_interface_cache,
        )

        thermo_cache = load_mp_thermo_interface_cache()
        live_sum_path = _REPO_ROOT / "outputs" / "live_mp_discovery_summary.json"
        live_sum = json.loads(live_sum_path.read_text(encoding="utf-8"))
        records_by_id = {r["candidate"]["candidate_id"]: r for r in live_sum["all_mp_records"]}

        for mp_id, expected_phase in (
            ("mp-22982", "CuBiS2"),
            ("mp-23474", "AgBi3S5"),
        ):
            self.assertIn(mp_id, thermo_cache)
            dossier = evaluate_phase11a_synthesis_and_contacts(records_by_id[mp_id], thermo_cache)
            self.assertEqual(
                dossier.mp_gga_hull_mev_per_atom,
                0.0,
                f"Expected ground-state {expected_phase} ({mp_id}) to have E_hull = 0.0 meV/atom, got {dossier.mp_gga_hull_mev_per_atom}",
            )
            self.assertEqual(dossier.hull_decomposition_phases, [expected_phase])
            self.assertIsNotNone(dossier.anion_chempot_window_ev)
            self.assertGreater(float(dossier.anion_chempot_window_ev or 0.0), 0.15)
            self.assertIsNotNone(dossier.min_cation_chempot_window_ev)
            self.assertGreater(float(dossier.min_cation_chempot_window_ev or 0.0), 0.05)

    def test_12_brown_altermatt_bond_valence_sum_on_experimental_chalcohalides(self) -> None:
        """Experimental BiSCl (mp-23318, Voutsas & Rentzeperis 1980, DOI: 10.1524/zkri.1980.152.1-2.109) and BiSBr (mp-23324) satisfy d_min >= 2.15 A and BVS GII < 0.20 v.u. (Brown & Altermatt 1985, DOI: 10.1107/S0108768185002063)."""
        live_sum_path = _REPO_ROOT / "outputs" / "live_mp_discovery_summary.json"
        live_sum = json.loads(live_sum_path.read_text(encoding="utf-8"))
        records_by_id = {r["candidate"]["candidate_id"]: r for r in live_sum["all_mp_records"]}

        for mp_id, stoich, ox_states in (
            ("mp-23318", {"Bi": 1, "S": 1, "Cl": 1}, {"Bi": 3, "S": -2, "Cl": -1}),
            ("mp-23324", {"Bi": 1, "S": 1, "Br": 1}, {"Bi": 3, "S": -2, "Br": -1}),
        ):
            rec = records_by_id[mp_id]
            geom = independently_verify_cif_geometry(
                cif_text=rec["candidate"]["cif_content"],
                expected_nsites=12,
                expected_reduced_stoich=stoich,
                oxidation_states=ox_states,
            )
            self.assertTrue(geom["passed"])
            self.assertGreaterEqual(geom["min_distance_ang"], 2.15)
            self.assertIsNotNone(geom["bvs_gii"])
            self.assertLess(geom["bvs_gii"], 0.20, f"Expected {mp_id} BVS GII < 0.20 v.u., got {geom['bvs_gii']}")


if __name__ == "__main__":
    unittest.main()

