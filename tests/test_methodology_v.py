"""Tests for methodology_checks.py and acceptance gates for tasks V2 to V10.

Background: docs/METHODOLOGY_REVIEW_2026-11-15.md. Tasks: docs/METHODOLOGY_TASKS_V.md.

The first group tests the functions and passes now. The second group is one strict
expected-failure test per open task. Closing a task means its test passes and its
`xfail` marker is deleted in the same commit. Do not edit a test body to make it pass.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from failsmart_matengine import methodology_checks as mc

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OPEN_V = "open task in docs/METHODOLOGY_TASKS_V.md"


def _summary() -> dict:
    return json.loads((ROOT / "outputs" / "live_mp_discovery_summary.json").read_text(encoding="utf-8"))


def _rows(name: str) -> list:
    with (DATA / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ================================================================ functions (pass now)

# ---------------------------------------------------------------- gate audit

def test_every_failure_mode_in_the_run_is_registered():
    audit = mc.gate_audit(_summary())
    assert audit["unregistered_modes"] == []
    assert audit["rejected_total"] == sum(g["rejected"] for g in audit["gates"].values())
    assert audit["candidates"] == sum(d["total"] for d in audit["by_dimensionality"].values())
    promoted = sum(d["promoted"] for d in audit["by_dimensionality"].values())
    assert audit["candidates"] == promoted + audit["rejected_total"]


def test_registry_is_consistent_with_rule_r2():
    strong = {mc.T3, "T4_COMPUTED_HERE", mc.T5}
    for mode, reg in mc.GATE_REGISTRY.items():
        assert reg["may_reject"] == (reg["tier"] in strong), mode
        if reg["may_reject"]:
            assert reg["replace_with"] is None and reg["owner"] is None, mode
        else:
            assert reg["replace_with"] in mc.FLAG_AXIS, mode
            assert reg["owner"] in {"V2", "G4", "F2"}, mode
    assert set(mc.FLAG_AXIS.values()) <= {"effective", "cost", "stable", "synthesizable"}


def test_toxic_elements_are_reported_sorted():
    assert mc.toxic_elements_present(["Sn", "Pb", "S", "Cd"]) == ["Cd", "Pb"]
    assert mc.toxic_elements_present(["Bi", "S", "I"]) == []


def test_audit_separates_estimated_from_measured_gap_rejections():
    summary = {
        "all_mp_records": [
            {"candidate": {"candidate_id": "a", "structural_dimensionality": "3D", "is_experimentally_known": True},
             "primary_failure_mode": "BANDGAP_OUT_OF_WINDOW", "electronics": {"gap_basis": "HEURISTIC"}},
            {"candidate": {"candidate_id": "b", "structural_dimensionality": "3D", "is_experimentally_known": True},
             "primary_failure_mode": "BANDGAP_OUT_OF_WINDOW", "electronics": {"gap_basis": "LITERATURE"}},
            {"candidate": {"candidate_id": "c", "structural_dimensionality": "1D-Chain", "is_experimentally_known": True},
             "primary_failure_mode": "ELASTIC_INSTABILITY"},
            {"candidate": {"candidate_id": "d", "structural_dimensionality": "3D", "is_experimentally_known": False},
             "primary_failure_mode": None},
        ]
    }
    audit = mc.gate_audit(summary)
    assert audit["gates"]["BANDGAP_OUT_OF_WINDOW"]["rejected"] == 1
    assert audit["gates"]["BANDGAP_OUT_OF_WINDOW_ESTIMATED"]["rejected"] == 1
    assert audit["rejected_on_weak_evidence"] == 2
    assert audit["known_phases_rejected_as_unstable"] == ["c"]
    assert audit["by_dimensionality"]["1D-Chain"] == {"total": 1, "promoted": 0}


# ---------------------------------------------------------------- window analysis

def test_window_probability_ceiling_matches_the_normal_distribution():
    assert mc.window_probability_ceiling(0.20, 0.44) == pytest.approx(0.1798, abs=5e-4)
    assert mc.window_probability_ceiling(0.20, 0.10) == pytest.approx(0.6827, abs=5e-4)
    assert mc.window_probability_ceiling(0.45, 0.44) > 2 * mc.window_probability_ceiling(0.20, 0.44)
    with pytest.raises(ValueError):
        mc.window_probability_ceiling(0.0, 0.44)


def test_current_top_window_ceiling_agrees_with_the_pipeline():
    from failsmart_matengine.gap_model import WINDOWS

    lo, hi = WINDOWS["TOP_ACTIVE_GLASS_185EV"]
    summary = _summary()
    sigma = float(summary["gap_model"]["sigma_ev"])
    reported = summary["ranked_shortlist"]["max_window_probability_for_estimated_gap"]["TOP_ACTIVE_GLASS_185EV"]
    assert mc.window_probability_ceiling(hi - lo, sigma) == pytest.approx(reported, abs=2e-3)


def test_best_top_gap_rises_as_top_cell_quality_falls():
    curve = mc.tandem_curve([1.20 + 0.02 * i for i in range(71)])
    ideal = mc.derive_top_window(quality=1.0, curve=curve)
    poorer = mc.derive_top_window(quality=0.6, curve=curve)
    assert ideal["window_ev"][0] <= ideal["best_gap_ev"] <= ideal["window_ev"][1]
    assert poorer["best_gap_ev"] > ideal["best_gap_ev"]
    assert poorer["window_ev"][0] > ideal["window_ev"][0]
    wide = mc.derive_top_window(quality=1.0, tolerance_abs_pct=2.0, curve=curve)
    assert wide["window_width_ev"] >= ideal["window_width_ev"]
    with pytest.raises(ValueError):
        mc.derive_top_window(quality=0.0, curve=curve)


# ---------------------------------------------------------------- calculation queue

def test_queue_priority_is_probability_per_unit_cost():
    assert mc.relative_cost(10) == pytest.approx(1.0)
    assert mc.relative_cost(20, exponent=2.0) == pytest.approx(4.0)
    assert mc.queue_priority(0.16, 20, exponent=2.0) == pytest.approx(0.04)
    assert mc.queue_priority(0.16, 5, exponent=2.0) > mc.queue_priority(0.16, 20, exponent=2.0)
    with pytest.raises(ValueError):
        mc.queue_priority(1.2, 10)


def test_order_queue_respects_class_then_priority():
    rows = [
        {"candidate_id": "big-known", "window_probability": 0.14, "nsites": 34, "queue_class": "CALCULATE_FIRST"},
        {"candidate_id": "small-known", "window_probability": 0.13, "nsites": 22, "queue_class": "CALCULATE_FIRST"},
        {"candidate_id": "tiny-new", "window_probability": 0.17, "nsites": 3, "queue_class": "CALCULATE_NEXT"},
        {"candidate_id": "parked", "window_probability": 0.18, "nsites": 7, "queue_class": "PARK"},
    ]
    out = mc.order_queue(rows, exponent=2.0)
    assert [r["candidate_id"] for r in out] == ["small-known", "big-known", "tiny-new", "parked"]
    assert out[-1]["cumulative_expected_hits"] == pytest.approx(0.62)
    assert all(out[i]["cumulative_cost"] < out[i + 1]["cumulative_cost"] for i in range(3))
    with pytest.raises(ValueError):
        mc.order_queue([{"candidate_id": "x", "window_probability": 0.1, "nsites": 4, "queue_class": "MAYBE"}])


def test_queue_from_summary_covers_exactly_the_estimated_gap_shortlist():
    summary = _summary()
    queue = mc.queue_from_summary(summary)
    assert sorted(r["candidate_id"] for r in queue) == sorted(summary["ranked_shortlist"]["dft_queue"])
    classes = [r["queue_class"] for r in queue]
    assert classes == sorted(classes, key=["CALCULATE_FIRST", "CALCULATE_NEXT", "PARK"].index)


def test_fit_cost_exponent_recovers_a_known_exponent():
    timings = [(n, 3.0 * n ** 2.4) for n in (4, 8, 12, 20, 32)]
    assert mc.fit_cost_exponent(timings)["exponent"] == pytest.approx(2.4, abs=1e-3)
    with pytest.raises(ValueError):
        mc.fit_cost_exponent(timings[:4])
    with pytest.raises(ValueError):
        mc.fit_cost_exponent([(10, 1.0), (11, 1.2), (12, 1.3), (13, 1.5), (14, 1.6)])


# ---------------------------------------------------------------- temperature

def test_voc_temperature_coefficient_reproduces_the_textbook_silicon_value():
    # Eg0 = 1.2 eV, gamma = 3, Voc = 0.6 V at 300 K gives about -2.2 mV/K (pveducation.org).
    si = mc.voc_temperature_coefficient(1.2, 0.6, temp_k=300.0, gamma=3.0)
    assert si["dvoc_dt_mv_per_k"] == pytest.approx(-2.26, abs=0.01)
    expected = -(1.2 - 0.6 + 3.0 * mc.KB_EV_PER_K * 300.0) / 300.0 * 1000.0
    assert si["dvoc_dt_mv_per_k"] == pytest.approx(expected, abs=1e-3)


def test_a_larger_voltage_deficit_means_a_worse_coefficient_whatever_the_gap():
    good_si = mc.voc_temperature_coefficient(1.2, 0.74)
    poor_wide_gap = mc.voc_temperature_coefficient(1.7, 0.824)
    assert poor_wide_gap["voltage_deficit_v"] > good_si["voltage_deficit_v"]
    assert poor_wide_gap["relative_pct_per_k"] < good_si["relative_pct_per_k"] < 0
    # The repository's rule of thumb, -0.44 / Eg**0.65 percent per kelvin, says the opposite.
    assert -0.44 / 1.7 ** 0.65 > -0.44 / 1.12 ** 0.65
    with pytest.raises(ValueError):
        mc.voc_temperature_coefficient(1.1, 1.2)


def test_top_cell_temperature_report_flags_the_optimistic_rule_of_thumb():
    rep = mc.top_cell_temperature_report(1.85)
    deficit = mc.RULES_V["reference_voltage_deficit_v"]
    direct = mc.voc_temperature_coefficient(1.85, 1.85 - deficit)
    assert rep["top_cell_voc_temp_coeff_from_deficit_mv_per_k"] == direct["dvoc_dt_mv_per_k"]
    assert rep["top_cell_voc_temp_coeff_from_deficit_mv_per_k"] == pytest.approx(-3.20, abs=0.01)
    assert rep["rule_of_thumb_rel_pct_per_k"] == pytest.approx(-0.295, abs=0.001)
    assert rep["temperature_flags"] == ["TEMPERATURE_RULE_OPTIMISTIC"]
    with pytest.raises(ValueError):
        mc.top_cell_temperature_report(0.8)


# ---------------------------------------------------------------- contact alignment

def test_band_offset_is_classified_only_when_it_exceeds_its_error():
    assert mc.classify_band_offset(None, 0.3) == "NOT_EVALUATED"
    assert mc.classify_band_offset(0.2, None) == "NOT_EVALUATED"
    assert mc.classify_band_offset(0.2, 0.1) == "IN_RANGE"
    assert mc.classify_band_offset(-0.5, 0.2) == "CLIFF"
    assert mc.classify_band_offset(0.9, 0.2) == "BARRIER"
    assert mc.classify_band_offset(0.1, 0.5) == "UNRESOLVED"
    assert mc.classify_band_offset(-0.1, 0.2) == "UNRESOLVED"
    # An error as large as the acceptable range can never resolve a favourable offset.
    width = mc.RULES_V["offset_ok_high_ev"] - mc.RULES_V["offset_ok_low_ev"]
    assert all(mc.classify_band_offset(x / 10.0, width) != "IN_RANGE" for x in range(-10, 15))


# ---------------------------------------------------------------- seed data

def test_seed_positive_controls_are_sourced():
    rows = _rows("positive_controls.csv")
    assert len(rows) >= 2
    bench_ids = {r["mp_id"] for r in _rows("gap_benchmark.csv")}
    for r in rows:
        assert r["mp_id"] in bench_ids, r["formula"]
        assert r["source_url"].startswith("https://"), r["formula"]
        assert r["opened_on"], r["formula"]
        assert float(r["best_efficiency_percent"]) > 0


# ================================================================ open tasks (strict xfail)

WEAK_MODES = {m for m, reg in mc.GATE_REGISTRY.items() if not reg["may_reject"]}


@pytest.mark.xfail(strict=True, reason=f"V2 {OPEN_V}")
def test_v2_no_candidate_is_rejected_on_weak_evidence():
    summary = _summary()
    audit = mc.gate_audit(summary)
    assert audit["rejected_on_weak_evidence"] == 0, audit["gates"]
    assert audit["known_phases_rejected_as_unstable"] == []
    assert not any("dynamically" in key for key in summary["funnel_counts"])
    flagged = [r for r in summary["all_mp_records"] if r.get("screening_flags")]
    assert flagged, "every record must carry a screening_flags list; some must be non-empty"
    for rec in summary["all_mp_records"]:
        assert isinstance(rec.get("screening_flags"), list), rec["candidate"]["candidate_id"]
        assert set(rec["screening_flags"]) <= set(mc.FLAG_AXIS), rec["candidate"]["candidate_id"]
    one_d = audit["by_dimensionality"].get("1D-Chain")
    if one_d:
        assert one_d["promoted"] > 0, "ribbon structures must be able to reach the shortlist"


@pytest.mark.xfail(strict=True, reason=f"V3 {OPEN_V}")
def test_v3_positive_controls_survive_every_gate_that_may_not_reject():
    controls = _rows("positive_controls.csv")
    assert len(controls) >= 10
    for r in controls:
        assert r["source_url"].startswith("https://") and r["opened_on"], r["formula"]
    results = json.loads((DATA / "positive_control_results.json").read_text(encoding="utf-8"))["results"]
    assert set(results) == {r["mp_id"] for r in controls}
    for mp_id, res in results.items():
        for key in ("formula", "structural_dimensionality", "primary_failure_mode", "screening_flags", "gap_basis"):
            assert key in res, (mp_id, key)
        assert res["primary_failure_mode"] not in WEAK_MODES, (mp_id, res["primary_failure_mode"])
        if res["primary_failure_mode"] != "HULL_INSTABILITY":
            assert res["gap_basis"] == "LITERATURE", mp_id
    assert any(ROOT.glob("scripts/run_positive_controls*")), "commit the script that produced the results"


@pytest.mark.xfail(strict=True, reason=f"V4 {OPEN_V} (owner decision)")
def test_v4_the_top_window_is_a_recorded_owner_decision():
    from failsmart_matengine.gap_model import WINDOWS

    decision = json.loads((DATA / "window_decision.json").read_text(encoding="utf-8"))
    for key in ("decided_by", "decided_on", "assumed_top_cell_quality", "tolerance_abs_pct", "top_window_ev",
                "keep_bottom_layer", "analysis"):
        assert key in decision, key
    assert decision["decided_by"] not in ("", None, "agent", "Claude", "Carbon")
    assert tuple(decision["top_window_ev"]) == tuple(WINDOWS["TOP_ACTIVE_GLASS_185EV"])
    assert isinstance(decision["keep_bottom_layer"], bool)


@pytest.mark.xfail(strict=True, reason=f"V5 {OPEN_V}")
def test_v5_published_hybrid_gaps_were_tested_before_use():
    from failsmart_matengine import gap_model

    ablation = json.loads((DATA / "hybrid_lookup_ablation.json").read_text(encoding="utf-8"))
    for key in ("source", "license", "downloaded_on", "n_overlap", "rmse_published_hybrid_ev",
                "rmse_calibrated_estimate_ev", "improvement_interval_95_ev", "adopted"):
        assert key in ablation, key
    lo, hi = ablation["improvement_interval_95_ev"]
    assert lo <= hi
    assert ablation["adopted"] == (ablation["n_overlap"] >= 15 and lo > 0.0)
    assert gap_model.SIGMA_DFT_DEFAULT_EV == pytest.approx(0.36)
    table = json.loads((DATA / "published_hybrid_gaps.json").read_text(encoding="utf-8"))
    assert "entries" in table
    if ablation["adopted"]:
        assert table["entries"], "adopted but no matched entries"
        some_id = next(iter(table["entries"]))
        assert gap_model.published_hybrid_gap_table()[some_id]["gap_ev"] == table["entries"][some_id]["gap_ev"]


@pytest.mark.xfail(strict=True, reason=f"V6 {OPEN_V}")
def test_v6_the_pipeline_queue_is_ordered_by_expected_results_per_unit_cost():
    summary = _summary()
    shortlist = summary["ranked_shortlist"]
    assert shortlist["dft_queue"] == [r["candidate_id"] for r in mc.queue_from_summary(summary)]
    by_id = {r["candidate_id"]: r for r in shortlist["not_excluded"]}
    for cid in shortlist["dft_queue"]:
        assert by_id[cid]["queue_priority"] == pytest.approx(
            mc.queue_priority(by_id[cid]["window_probability"], by_id[cid]["nsites"]), abs=1e-6
        )
    assert shortlist["queue_cost_exponent"] == mc.RULES_V["cost_exponent"]


@pytest.mark.xfail(strict=True, reason=f"V7 {OPEN_V}")
def test_v7_temperature_rule_of_thumb_is_labelled_and_the_deficit_formula_reported():
    from failsmart_matengine.schemas import ProvenanceTag, RealWorldLCOEStressTestReport

    prov = RealWorldLCOEStressTestReport._DEFAULT_PROVENANCE
    assert prov["temp_coeff_rel_pct_per_k"] == ProvenanceTag.HEURISTIC
    fields = RealWorldLCOEStressTestReport.model_fields
    assert "top_cell_voc_temp_coeff_from_deficit_mv_per_k" in fields
    assert "temperature_flags" in fields
    stacks = _summary()["real_world_lcoe_stress_test_stacks"]
    assert stacks
    for s in stacks:
        assert s["top_cell_voc_temp_coeff_from_deficit_mv_per_k"] < 0
        assert isinstance(s["temperature_flags"], list)


@pytest.mark.xfail(strict=True, reason=f"V8 {OPEN_V}")
def test_v8_band_edge_estimates_are_benchmarked_and_classified_with_their_error():
    rows = _rows("band_edge_benchmark.csv")
    assert len(rows) >= 10
    for r in rows:
        assert r["source_url"].startswith("https://") and r["opened_on"], r["formula"]
        assert r["method"], r["formula"]
        float(r["measured_electron_affinity_ev"])
    model = json.loads((DATA / "band_edge_model.json").read_text(encoding="utf-8"))
    for key in ("n", "mae_ev", "rmse_ev", "max_abs_ev"):
        assert key in model, key
    assert model["n"] == len(rows)
    from failsmart_matengine.schemas import Phase11ASynthesisContactDossier

    assert "contact_alignment_class" in Phase11ASynthesisContactDossier.model_fields
    allowed = {"NOT_EVALUATED", "IN_RANGE", "CLIFF", "BARRIER", "UNRESOLVED"}
    for d in _summary()["phase11a_synthesis_contact_dossiers"]:
        assert d["contact_alignment_class"] in allowed
        expected = mc.classify_band_offset(d["best_cbo_ev"], None if d["best_cbo_ev"] is None else model["rmse_ev"])
        assert d["contact_alignment_class"] == expected


@pytest.mark.xfail(strict=True, reason=f"V9 {OPEN_V}")
def test_v9_mitigations_are_records_with_sources_not_multipliers():
    from failsmart_matengine import failure_evidence as fe

    mitigations = [r for r in fe.device_records() if r["finding_type"] == "mitigation"]
    assert len(mitigations) >= 10
    for r in mitigations:
        assert r["source_url"].startswith("https://") and r["opened_on"], r["record_id"]
    cards = fe.build_scorecards(_summary())
    assert all("known_mitigations" in c for c in cards)
    assert any(c["known_mitigations"] for c in cards)
    source = (ROOT / "failsmart_matengine" / "failure_evidence.py").read_text(encoding="utf-8")
    assert "recovery_factor" not in source and "passivation_multiplier" not in source


@pytest.mark.xfail(strict=True, reason=f"V10 {OPEN_V}")
def test_v10_phonon_stability_is_checked_on_known_phases_first():
    controls = json.loads((DATA / "phonon_controls.json").read_text(encoding="utf-8"))
    for key in ("model", "model_version", "supercell_rule", "imaginary_threshold_thz", "n_controls",
                "false_unstable", "false_unstable_fraction", "results"):
        assert key in controls, key
    assert controls["n_controls"] >= 8
    assert len(controls["results"]) == controls["n_controls"]
    assert controls["false_unstable_fraction"] == pytest.approx(
        len(controls["false_unstable"]) / controls["n_controls"]
    )
    assert math.isfinite(controls["imaginary_threshold_thz"])
