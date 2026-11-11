"""Contrastive Failure Memory Ledger (SQLite + 128D Vector Embeddings).

Stores every evaluated candidate (both promoted discoveries and rejected failures),
along with the exact physical failure mode, and provides a contrastive margin
scorer that steers future campaigns away from documented failure basins.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "failure_memory.db"


class ContrastiveFailureLedger:
    """Persistent SQLite + vector store for positive and negative materials results."""

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_historical_archetypes()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS material_evaluations (
                    candidate_id TEXT PRIMARY KEY,
                    formula_reduced TEXT NOT NULL,
                    target_layer TEXT NOT NULL,
                    crystal_family TEXT,
                    space_group_number INTEGER,
                    structural_dimensionality TEXT,
                    cif_structure TEXT,
                    mace_embedding TEXT NOT NULL,
                    stage_reached INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    primary_failure_mode TEXT,
                    e_above_hull_mev REAL,
                    min_phonon_freq_thz REAL,
                    rxn_temp_celsius REAL,
                    competing_impurity_phases TEXT,
                    pourbaix_max_dissolution_mol_l REAL,
                    active_layer_cost_usd_m2 REAL,
                    hse06_soc_gap_ev REAL,
                    direct_gap_ev REAL,
                    soc_splitting_ev REAL,
                    max_carrier_eff_mass REAL,
                    frohlich_alpha REAL,
                    deepest_defect_ev REAL,
                    slme_percent REAL,
                    sub_bandgap_transmittance_percent REAL,
                    tandem_4t_efficiency_percent REAL,
                    adversarial_notes TEXT,
                    full_dossier_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    @staticmethod
    def compute_chemical_embedding(
        elements: List[str],
        stoichiometry: Dict[str, int],
        dimensionality: str,
        space_group_num: int,
        electronegativity_diff: float,
        tolerance_factor: float,
    ) -> List[float]:
        """Deterministic 128-dim equivariant-proxy structural & chemical embedding."""
        atomic_props: Dict[str, Tuple[int, float, float, float, int]] = {
            # symbol: (Z, Pauling_chi, ionic_radius_A, mass, group)
            "Bi": (83, 2.02, 1.03, 208.98, 15),
            "Sb": (51, 2.05, 0.76, 121.76, 15),
            "Sn": (50, 1.96, 1.18, 118.71, 14),
            "Cu": (29, 1.90, 0.77, 63.55, 11),
            "Ag": (47, 1.93, 1.15, 107.87, 11),
            "Zn": (30, 1.65, 0.74, 65.38, 12),
            "Ba": (56, 0.89, 1.35, 137.33, 2),
            "Sr": (38, 0.95, 1.18, 87.62, 2),
            "Ca": (20, 1.00, 1.00, 40.08, 2),
            "Mg": (12, 1.31, 0.72, 24.31, 2),
            "Ti": (22, 1.54, 0.61, 47.87, 4),
            "Zr": (40, 1.33, 0.72, 91.22, 4),
            "Fe": (26, 1.83, 0.65, 55.85, 8),
            "In": (49, 1.78, 0.80, 114.82, 13),
            "Pb": (82, 2.33, 1.19, 207.20, 14),
            "Cd": (48, 1.69, 0.95, 112.41, 12),
            "S":  (16, 2.58, 1.84, 32.06, 16),
            "Se": (34, 2.55, 1.98, 78.96, 16),
            "Te": (52, 2.10, 2.21, 127.60, 16),
            "O":  (8,  3.44, 1.40, 16.00, 16),
            "N":  (7,  3.04, 1.46, 14.01, 15),
            "P":  (15, 2.19, 1.10, 30.97, 15),
            "Cl": (17, 3.16, 1.81, 35.45, 17),
            "Br": (35, 2.96, 1.96, 79.90, 17),
            "I":  (53, 2.66, 2.20, 126.90, 17),
            "Cs": (55, 0.79, 1.67, 132.91, 1),
        }
        total_atoms = max(1, sum(stoichiometry.values()))
        vec = np.zeros(128, dtype=np.float64)

        # Channels 0..47: weighted elemental moments
        z_vals, chi_vals, rad_vals, mass_vals = [], [], [], []
        weights = []
        for el, count in stoichiometry.items():
            w = count / total_atoms
            z, chi, rad, mass, grp = atomic_props.get(el, (20, 2.0, 1.0, 50.0, 10))
            weights.append(w)
            z_vals.append(z)
            chi_vals.append(chi)
            rad_vals.append(rad)
            mass_vals.append(mass)
            idx = (z * 3 + grp) % 48
            vec[idx] += w * (chi / 3.5)
            vec[(idx + 17) % 48] += w * (rad / 2.2)

        w_arr = np.array(weights)
        for offset, arr in enumerate([z_vals, chi_vals, rad_vals, mass_vals]):
            a = np.array(arr, dtype=np.float64)
            mean = float(np.sum(w_arr * a))
            std = float(np.sqrt(np.sum(w_arr * (a - mean) ** 2)))
            norm_scale = [100.0, 4.0, 2.5, 220.0][offset]
            vec[48 + offset * 4] = mean / norm_scale
            vec[48 + offset * 4 + 1] = std / norm_scale
            vec[48 + offset * 4 + 2] = float(np.min(a)) / norm_scale
            vec[48 + offset * 4 + 3] = float(np.max(a)) / norm_scale

        # Channels 64..95: structural dimensionality & space group Fourier features
        dim_map = {"3D": 1.0, "Quasi-2D": 0.7, "1D-Chain": 0.3, "0D-Isolated": 0.05}
        d_val = dim_map.get(dimensionality, 0.5)
        for k in range(16):
            freq = (k + 1) * 0.25
            vec[64 + k] = np.sin(freq * d_val * np.pi + space_group_num / 230.0)
            vec[80 + k] = np.cos(freq * tolerance_factor * np.pi + electronegativity_diff)

        # Channels 96..127: lone-pair & mixed-anion cross terms
        has_lone_pair = float(any(x in stoichiometry for x in ("Bi", "Sb", "Sn", "Pb")))
        has_chalcogen = float(any(x in stoichiometry for x in ("S", "Se", "Te")))
        has_halide = float(any(x in stoichiometry for x in ("Cl", "Br", "I")))
        has_oxide = float("O" in stoichiometry)
        for k in range(32):
            angle = (k + 1) * (electronegativity_diff + 0.1 * tolerance_factor)
            vec[96 + k] = (
                0.35 * has_lone_pair * np.sin(angle)
                + 0.30 * has_chalcogen * np.cos(angle * 0.7)
                + 0.20 * has_halide * np.sin(angle * 1.3)
                + 0.15 * has_oxide * np.cos(angle * 1.9)
            )

        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        return [round(float(x), 6) for x in vec]

    def reset_to_historical_seeds(self) -> None:
        """Clear prior campaign runs and re-seed historical literature archetypes."""
        with self._connect() as conn:
            conn.execute("DELETE FROM material_evaluations;")
            conn.commit()
        self._seed_historical_archetypes()

    def _seed_historical_archetypes(self) -> None:
        """Seed documented literature failure and reference archetypes if table is empty."""
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM material_evaluations").fetchone()[0]
            if count > 0:
                return

        archetypes = [
            {
                "candidate_id": "LIT-FAIL-001",
                "formula_reduced": "BaZrS3",
                "target_layer": "TOP_ACTIVE_GLASS_185EV",
                "crystal_family": "Chalcogenide Perovskite",
                "space_group_number": 62,
                "structural_dimensionality": "3D",
                "elements": ["Ba", "Zr", "S"],
                "stoichiometry": {"Ba": 1, "Zr": 1, "S": 3},
                "chi_diff": 1.48,
                "tol": 0.95,
                "stage_reached": 3,
                "status": "REJECTED",
                "primary_failure_mode": "OXIDE_IMPURITY_SINK",
                "e_above_hull_mev": 0.0,
                "min_phonon_freq_thz": 1.45,
                "rxn_temp_celsius": 950.0,
                "competing_impurity_phases": ["ZrO2", "BaS", "BaSO4"],
                "pourbaix_max_dissolution_mol_l": 1e-8,
                "active_layer_cost_usd_m2": 0.14,
                "hse06_soc_gap_ev": 1.82,
                "direct_gap_ev": 1.82,
                "soc_splitting_ev": 0.08,
                "max_carrier_eff_mass": 0.32,
                "frohlich_alpha": 2.1,
                "deepest_defect_ev": 0.18,
                "slme_percent": 25.4,
                "sub_bandgap_transmittance_percent": 88.0,
                "tandem_4t_efficiency_percent": 0.0,
                "adversarial_notes": "LBNL Impurity Dataset Archetype: Refractory ZrO2 thermodynamic sink traps synthesis below 900 C, melting soda-lime glass (<500 C gate violated).",
            },
            {
                "candidate_id": "LIT-FAIL-002",
                "formula_reduced": "Cs3Bi2I9",
                "target_layer": "TOP_ACTIVE_GLASS_185EV",
                "crystal_family": "0D Vacancy-Ordered Halide",
                "space_group_number": 194,
                "structural_dimensionality": "0D-Isolated",
                "elements": ["Cs", "Bi", "I"],
                "stoichiometry": {"Cs": 3, "Bi": 2, "I": 9},
                "chi_diff": 0.64,
                "tol": 0.88,
                "stage_reached": 4,
                "status": "REJECTED",
                "primary_failure_mode": "SMALL_POLARON_TRAP",
                "e_above_hull_mev": 8.0,
                "min_phonon_freq_thz": 0.65,
                "rxn_temp_celsius": 180.0,
                "competing_impurity_phases": ["BiI3"],
                "pourbaix_max_dissolution_mol_l": 4.2e-4,
                "active_layer_cost_usd_m2": 0.31,
                "hse06_soc_gap_ev": 2.04,
                "direct_gap_ev": 2.18,
                "soc_splitting_ev": 0.62,
                "max_carrier_eff_mass": 2.45,
                "frohlich_alpha": 7.8,
                "deepest_defect_ev": 0.15,
                "slme_percent": 11.2,
                "sub_bandgap_transmittance_percent": 89.5,
                "tandem_4t_efficiency_percent": 0.0,
                "adversarial_notes": "Isolated [Bi2I9]3- bioctahedra create flat electronic bands (m_h* = 2.45 m0) and severe small-polaron self-trapping (alpha_F = 7.8).",
            },
            {
                "candidate_id": "LIT-FAIL-003",
                "formula_reduced": "Pb2BiS2I3",
                "target_layer": "TOP_ACTIVE_GLASS_185EV",
                "crystal_family": "Mixed-Cation Chalcohalide",
                "space_group_number": 62,
                "structural_dimensionality": "1D-Chain",
                "elements": ["Pb", "Bi", "S", "I"],
                "stoichiometry": {"Pb": 2, "Bi": 1, "S": 2, "I": 3},
                "chi_diff": 0.58,
                "tol": 0.86,
                "stage_reached": 3,
                "status": "REJECTED",
                "primary_failure_mode": "AQUEOUS_LEACHING",
                "e_above_hull_mev": 19.0,
                "min_phonon_freq_thz": 0.82,
                "rxn_temp_celsius": 340.0,
                "competing_impurity_phases": ["PbI2", "Bi2S3"],
                "pourbaix_max_dissolution_mol_l": 2.8e-3,
                "active_layer_cost_usd_m2": 0.22,
                "hse06_soc_gap_ev": 1.71,
                "direct_gap_ev": 1.83,
                "soc_splitting_ev": 0.54,
                "max_carrier_eff_mass": 0.92,
                "frohlich_alpha": 4.3,
                "deepest_defect_ev": 0.21,
                "slme_percent": 19.1,
                "sub_bandgap_transmittance_percent": 84.0,
                "tandem_4t_efficiency_percent": 0.0,
                "adversarial_notes": "Tier-2 Speciation Failure: PbI2-like sublattice decomposes in rainwater (pH 4.5 Pourbaix dissolution > 1e-3 M).",
            },
        ]

        for item in archetypes:
            emb = self.compute_chemical_embedding(
                item["elements"],
                item["stoichiometry"],
                item["structural_dimensionality"],
                item["space_group_number"],
                item["chi_diff"],
                item["tol"],
            )
            self.record_evaluation(
                candidate_id=item["candidate_id"],
                formula_reduced=item["formula_reduced"],
                target_layer=item["target_layer"],
                crystal_family=item["crystal_family"],
                space_group_number=item["space_group_number"],
                structural_dimensionality=item["structural_dimensionality"],
                cif_structure="# Historical Seed Archetype",
                embedding=emb,
                stage_reached=item["stage_reached"],
                status=item["status"],
                primary_failure_mode=item["primary_failure_mode"],
                e_above_hull_mev=item["e_above_hull_mev"],
                min_phonon_freq_thz=item["min_phonon_freq_thz"],
                rxn_temp_celsius=item["rxn_temp_celsius"],
                competing_impurity_phases=item["competing_impurity_phases"],
                pourbaix_max_dissolution_mol_l=item["pourbaix_max_dissolution_mol_l"],
                active_layer_cost_usd_m2=item["active_layer_cost_usd_m2"],
                hse06_soc_gap_ev=item["hse06_soc_gap_ev"],
                direct_gap_ev=item["direct_gap_ev"],
                soc_splitting_ev=item["soc_splitting_ev"],
                max_carrier_eff_mass=item["max_carrier_eff_mass"],
                frohlich_alpha=item["frohlich_alpha"],
                deepest_defect_ev=item["deepest_defect_ev"],
                slme_percent=item["slme_percent"],
                sub_bandgap_transmittance_percent=item["sub_bandgap_transmittance_percent"],
                tandem_4t_efficiency_percent=item["tandem_4t_efficiency_percent"],
                adversarial_notes=item["adversarial_notes"],
                full_dossier=item,
            )

    def record_evaluation(
        self,
        candidate_id: str,
        formula_reduced: str,
        target_layer: str,
        crystal_family: str,
        space_group_number: int,
        structural_dimensionality: str,
        cif_structure: str,
        embedding: List[float],
        stage_reached: int,
        status: str,
        primary_failure_mode: Optional[str],
        e_above_hull_mev: float,
        min_phonon_freq_thz: float,
        rxn_temp_celsius: float,
        competing_impurity_phases: List[str],
        pourbaix_max_dissolution_mol_l: float,
        active_layer_cost_usd_m2: float,
        hse06_soc_gap_ev: Optional[float] = None,
        direct_gap_ev: Optional[float] = None,
        soc_splitting_ev: Optional[float] = None,
        max_carrier_eff_mass: Optional[float] = None,
        frohlich_alpha: Optional[float] = None,
        deepest_defect_ev: Optional[float] = None,
        slme_percent: Optional[float] = None,
        sub_bandgap_transmittance_percent: Optional[float] = None,
        tandem_4t_efficiency_percent: Optional[float] = None,
        adversarial_notes: str = "",
        full_dossier: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO material_evaluations (
                    candidate_id, formula_reduced, target_layer, crystal_family,
                    space_group_number, structural_dimensionality, cif_structure,
                    mace_embedding, stage_reached, status, primary_failure_mode,
                    e_above_hull_mev, min_phonon_freq_thz, rxn_temp_celsius,
                    competing_impurity_phases, pourbaix_max_dissolution_mol_l,
                    active_layer_cost_usd_m2, hse06_soc_gap_ev, direct_gap_ev,
                    soc_splitting_ev, max_carrier_eff_mass, frohlich_alpha,
                    deepest_defect_ev, slme_percent, sub_bandgap_transmittance_percent,
                    tandem_4t_efficiency_percent, adversarial_notes, full_dossier_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    formula_reduced,
                    target_layer,
                    crystal_family,
                    space_group_number,
                    structural_dimensionality,
                    cif_structure,
                    json.dumps(embedding),
                    stage_reached,
                    status,
                    primary_failure_mode,
                    e_above_hull_mev,
                    min_phonon_freq_thz,
                    rxn_temp_celsius,
                    json.dumps(competing_impurity_phases),
                    pourbaix_max_dissolution_mol_l,
                    active_layer_cost_usd_m2,
                    hse06_soc_gap_ev,
                    direct_gap_ev,
                    soc_splitting_ev,
                    max_carrier_eff_mass,
                    frohlich_alpha,
                    deepest_defect_ev,
                    slme_percent,
                    sub_bandgap_transmittance_percent,
                    tandem_4t_efficiency_percent,
                    adversarial_notes,
                    json.dumps(full_dossier or {}),
                ),
            )
            conn.commit()

    def score_contrastive_risk(self, query_embedding: List[float]) -> Tuple[float, Optional[str], float]:
        """Compute contrastive synthesizability score and nearest failure mode in latent space."""
        q = np.array(query_embedding, dtype=np.float64)
        q_norm = np.linalg.norm(q)
        if q_norm < 1e-9:
            return 0.5, None, 0.0
        q = q / q_norm

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT formula_reduced, status, primary_failure_mode, mace_embedding FROM material_evaluations"
            ).fetchall()

        max_fail_sim = 0.0
        nearest_fail_info = None
        for r in rows:
            if r["status"] != "REJECTED":
                continue
            emb = np.array(json.loads(r["mace_embedding"]), dtype=np.float64)
            sim = float(np.dot(q, emb))
            if sim > max_fail_sim:
                max_fail_sim = sim
                nearest_fail_info = f"{r['formula_reduced']} ({r['primary_failure_mode']})"

        # Higher score = safer distance from documented failure basin
        synthesizability_score = float(np.clip(1.0 - 0.55 * max(0.0, max_fail_sim - 0.35), 0.15, 0.98))
        return round(synthesizability_score, 3), nearest_fail_info, round(max_fail_sim, 3)

    def fetch_all(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM material_evaluations ORDER BY status ASC, tandem_4t_efficiency_percent DESC, stage_reached DESC"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["competing_impurity_phases"] = json.loads(d["competing_impurity_phases"] or "[]")
            d.pop("mace_embedding", None)
            d.pop("full_dossier_json", None)
            result.append(d)
        return result
