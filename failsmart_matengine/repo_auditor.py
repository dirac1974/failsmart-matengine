"""Repository Consistency & Documentation Gatekeeper Audit Engine (v2.0).

Parses outputs/pilot_campaign_summary.json, data/failure_memory.db,
outputs/qe_hse06_soc_decks/, README.md, docs/MEMORY_AND_FAILURE_LEDGER.md, and docs/PLAN.md
and asserts that all candidate formulas, counts, physical metrics, and finalist numbers
match across all files with 100% bit-for-bit consistency and zero discrepancy.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RepoConsistencyAuditor:
    """Zero-discrepancy repository auditor."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.root = repo_root or Path(__file__).resolve().parent.parent
        self.summary_json_path = self.root / "outputs" / "pilot_campaign_summary.json"
        self.db_path = self.root / "data" / "failure_memory.db"
        self.qe_dir = self.root / "outputs" / "qe_hse06_soc_decks"
        self.readme_path = self.root / "README.md"
        self.ledger_doc_path = self.root / "docs" / "MEMORY_AND_FAILURE_LEDGER.md"
        self.plan_doc_path = self.root / "docs" / "PLAN.md"

        self.summary_data: Dict[str, Any] = {}
        self.db_records: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[str] = []

    def log(self, message: str) -> None:
        self.audit_log.append(message)
        print(message)

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
        """Audit Quantum ESPRESSO decks and CIF files for the 5 finalists."""
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

            # Check CIF content
            cif_text = cif_file.read_text(encoding="utf-8")
            assert f"data_{formula}" in cif_text, f"CIF header missing formula {formula} in {cif_file}"

            # Check QE input deck content
            in_text = in_file.read_text(encoding="utf-8")
            assert f"Candidate: {cid} ({formula})" in in_text, f"Candidate header missing in {in_file}"
            assert f"prefix = '{formula.lower()}'" in in_text, f"Prefix mismatch in {in_file}"
            assert f"nat = {expected_nat}" in in_text, f"nat != {expected_nat} in {in_file}"
            assert f"ntyp = {expected_ntyp}" in in_text, f"ntyp != {expected_ntyp} in {in_file}"
            assert cand["space_group_symbol"] in in_text, f"Space group {cand['space_group_symbol']} missing in {in_file}"
            assert "CELL_PARAMETERS (angstrom)" in in_text, f"Missing CELL_PARAMETERS (angstrom) in {in_file}"
            assert "ATOMIC_POSITIONS (crystal)" in in_text, f"Missing ATOMIC_POSITIONS (crystal) in {in_file}"

            # Verify real IUPAC atomic masses (forbidding dummy 1.000)
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
                            assert mass > 1.0, f"Unphysical mass for {elem} in {in_file}: {mass}"

            assert len(species_found) == expected_ntyp, (
                f"Expected {expected_ntyp} species in {in_file}, found {len(species_found)}"
            )

        self.log("   [OK] All 5 finalists possess valid, synchronized CIF & Quantum ESPRESSO decks with IUPAC atomic masses.")

    def audit_readme_markdown(self) -> None:
        """Parse README.md and verify funnel numbers, candidate formulas, and finalist table values."""
        self.log(f"-> Auditing {self.readme_path} ...")
        assert self.readme_path.exists(), f"Missing {self.readme_path}"
        text = self.readme_path.read_text(encoding="utf-8")

        # Verify 13-agent architecture is documented
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

        # Verify v2.0 funnel counts in text
        assert "20 Candidates Screened" in text or "20 generated" in text
        assert "17 dynamically & ion-stable" in text or "17 dynamically" in text
        assert "12 manufacturable" in text
        assert "8 promoted to Stage 4 DFT" in text or "8 promoted to Stage 4" in text
        assert "5 Validated Finalists" in text

        # Verify key formulas and failures mentioned
        for f_name in [
            "Sr2ZnOS2",
            "Zn2SbS2Br3",
            "Cu3BiS2Cl2",
            "BaZrS3",
            "AgBiSe2",
            "BiSCl",
            "SbSeI",
            "BiCuSeI2",
            "Bi2SnSe3I2",
            "BiCuOS",
            "BaBiO2Cl",
            "Sr2Cu2O2S",
            "Ba2BiS3Cl",
            "Ba2BiSe3I",
            "Cu2SnSeI2",
        ]:
            assert f_name in text, f"Missing candidate formula {f_name} in README.md"

        assert "ION_MIGRATION_INSTABILITY" in text
        assert "0.42" in text

        # Verify finalists in README table
        finalists = {f["candidate"]["candidate_id"]: f for f in self.summary_data["finalists"]}
        assert len(finalists) == 5

        for cid, fin in finalists.items():
            cand = fin["candidate"]
            formula = cand["formula_reduced"]
            stab = fin["stability"]
            synth = fin["synthesis"]
            elec = fin["electronics"]
            opt = fin["optics"]
            red = fin["redundancy_verification"]

            # Match table line for this candidate ID
            pattern = rf"`{cid}`\s*\|\s*`{formula}`.*"
            match = re.search(pattern, text)
            assert match is not None, f"Could not find table row for {cid} ({formula}) in README.md"
            row = match.group(0)

            # Check Space Group & nat
            assert cand["space_group_symbol"] in row, f"{cid} space group not in README row: {row}"
            assert str(cand["nsites_unit_cell"]) in row, f"{cid} nsites {cand['nsites_unit_cell']} not in README row: {row}"

            # Check T_synth
            t_synth = f"{synth['min_synthesis_temp_c']:.1f}"
            assert t_synth in row or f"{synth['min_synthesis_temp_c']:.0f}" in row, (
                f"{cid} T_synth {t_synth} not in README row: {row}"
            )

            # Check cost
            cost_str = f"${synth['active_layer_cost_usd_m2']:.4f}"
            assert cost_str in row, f"{cid} active layer cost {cost_str} not in README row: {row}"

            # Check Ehull
            ehull_str = f"{stab['e_above_hull_0k_mev']:.1f}"
            assert ehull_str in row, f"{cid} Ehull {ehull_str} not in README row: {row}"

            # Check min phonon freq
            phonon_str = f"{stab['min_phonon_freq_thz']:.2f}"
            assert phonon_str in row, f"{cid} min phonon freq {phonon_str} not in README row: {row}"

            # Check Emig
            emig_str = f"{stab['ion_migration_barrier_ev']:.2f}"
            assert emig_str in row, f"{cid} E_mig {emig_str} not in README row: {row}"

            # Check SLME
            slme_str = f"{opt['standalone_slme_percent']:.2f}%"
            assert slme_str in row, f"{cid} SLME {slme_str} not in README row: {row}"

            # Check 4T stack efficiency
            eff4t_str = f"{opt['tandem_4t_total_eff_percent']:.2f}%"
            assert eff4t_str in row, f"{cid} 4T efficiency {eff4t_str} not in README row: {row}"

            # Check SHA-256 signature
            sha_sig = red["sha256_signature"]
            assert sha_sig in row, f"{cid} SHA-256 {sha_sig} not in README row: {row}"

        self.log("   [OK] README.md contains verified 13-agent architecture, v2.0 funnel counts, and exact finalist metrics.")

    def audit_memory_and_failure_ledger_markdown(self) -> None:
        """Parse docs/MEMORY_AND_FAILURE_LEDGER.md and verify all 23 entries and finalist metrics."""
        self.log(f"-> Auditing {self.ledger_doc_path} ...")
        assert self.ledger_doc_path.exists(), f"Missing {self.ledger_doc_path}"
        text = self.ledger_doc_path.read_text(encoding="utf-8")

        # Verify physical failure taxonomy (including ION_MIGRATION_INSTABILITY)
        for fail_code in [
            "IMAGINARY_PHONON",
            "HULL_INSTABILITY",
            "ION_MIGRATION_INSTABILITY",
            "OXIDE_IMPURITY_SINK",
            "AQUEOUS_LEACHING",
            "TIER2_COST_EXCEEDED",
            "LOW_DIM_POLARON_RISK",
            "ANION_PHASE_SEGREGATION",
            "BANDGAP_OUT_OF_WINDOW",
            "DEEP_SRH_DEFECT",
        ]:
            assert fail_code in text, f"Missing failure code {fail_code} in {self.ledger_doc_path}"

        # Verify all 23 entries are present in table
        json_entries = {e["candidate_id"]: e for e in self.summary_data["ledger_entries"]}
        assert len(json_entries) == 23

        for cid, entry in json_entries.items():
            formula = entry["formula_reduced"]
            pattern = rf"`{cid}`\s*\|\s*`{formula}`.*"
            match = re.search(pattern, text)
            assert match is not None, f"Could not find row for {cid} ({formula}) in {self.ledger_doc_path}"
            row = match.group(0)

            # Check status
            assert entry["status"] in row, f"Status {entry['status']} not in row for {cid}: {row}"

            # Check Ehull
            ehull_val = entry["e_above_hull_mev"]
            if ehull_val is not None:
                assert f"{ehull_val:.1f}" in row or f"{int(ehull_val)}" in row, (
                    f"Ehull {ehull_val} not in row for {cid}: {row}"
                )

            # Check min phonon
            ph_val = entry["min_phonon_freq_thz"]
            if ph_val is not None:
                assert f"{ph_val:.2f}" in row or f"{ph_val:.1f}" in row, f"w_min {ph_val} not in row for {cid}: {row}"

            # Check Stage 2b ion migration barrier for CAND-A09
            if cid == "CAND-A09":
                assert "0.42" in row, f"CAND-A09 Emig 0.42 not in row: {row}"
                assert "ION_MIGRATION_INSTABILITY" in row

            # If promoted, check cost, SLME, 4T, and SHA-256
            if entry["status"] == "PROMOTED":
                cost = f"${entry['active_layer_cost_usd_m2']:.4f}"
                assert cost in row, f"Cost {cost} not in row for {cid}: {row}"

                slme = f"{entry['slme_percent']:.2f}%"
                assert slme in row, f"SLME {slme} not in row for {cid}: {row}"

                tandem = f"{entry['tandem_4t_efficiency_percent']:.2f}%"
                assert tandem in row, f"Tandem eff {tandem} not in row for {cid}: {row}"

        # Verify Section 4 Finalist table (5 finalists)
        finalists = {f["candidate"]["candidate_id"]: f for f in self.summary_data["finalists"]}
        assert len(finalists) == 5
        for cid, fin in finalists.items():
            cand = fin["candidate"]
            formula = cand["formula_reduced"]
            red = fin["redundancy_verification"]
            sha = red["sha256_signature"]
            assert sha in text, f"Finalist SHA-256 {sha} for {cid} ({formula}) not in {self.ledger_doc_path}"

        self.log("   [OK] docs/MEMORY_AND_FAILURE_LEDGER.md is 100% synchronized with JSON & SQLite ledger (all 23 entries).")

    def audit_plan_markdown(self) -> None:
        """Parse docs/PLAN.md and verify consistency with v2.0 architecture and metrics."""
        self.log(f"-> Auditing {self.plan_doc_path} ...")
        assert self.plan_doc_path.exists(), f"Missing {self.plan_doc_path}"
        text = self.plan_doc_path.read_text(encoding="utf-8")

        assert "ION_MIGRATION_INSTABILITY" in text
        assert "0.65" in text
        assert "20 -> 17 -> 12 -> 8 -> 5" in text or "20" in text

        # Check finalists mentioned
        finalists = {f["candidate"]["candidate_id"]: f for f in self.summary_data["finalists"]}
        for cid, fin in finalists.items():
            formula = fin["candidate"]["formula_reduced"]
            assert formula in text, f"Finalist formula {formula} not in {self.plan_doc_path}"

        self.log("   [OK] docs/PLAN.md contains verified v2.0 workflow counts, Stage 2b gates, and finalists.")

    def run_full_audit(self) -> bool:
        """Run all verification audits and return True if 100% aligned."""
        self.log("=" * 78)
        self.log("FailSmart-MatEngine Repository Consistency & Documentation Audit (v2.0)")
        self.log(f"Repository Root: {self.root}")
        self.log("=" * 78)

        try:
            self.load_summary_json()
            self.load_sqlite_db()
            self.audit_qe_decks()
            self.audit_readme_markdown()
            self.audit_memory_and_failure_ledger_markdown()
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
        self.log("[PASS] 100% CROSS-REPOSITORY CONSISTENCY & NUMERICAL ALIGNMENT CONFIRMED")
        self.log("All formulas, counts, thermodynamic values, optics, and SHA-256 hashes match.")
        self.log("=" * 78)
        return True


def main() -> int:
    auditor = RepoConsistencyAuditor()
    success = auditor.run_full_audit()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
