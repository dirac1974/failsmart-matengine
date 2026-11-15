"""Tests for failure_evidence.py and the evaluation rules (docs/MATERIAL_EVALUATION_RULES.md).

These tests depend only on new files plus `data/negative_synthesis_priors.json` and the
pipeline summary. They assert rules and consistency, not values from one run, so they
keep passing when the shortlist changes.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

from failsmart_matengine import failure_evidence as fe

ROOT = Path(__file__).resolve().parents[1]


def _summary() -> dict:
    return json.loads((ROOT / "outputs" / "live_mp_discovery_summary.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- synthesis evidence

def test_synthesis_evidence_never_rejects_and_reports_uncertainty():
    ev = fe.synthesis_evidence(["Bi", "S"])
    assert ev["recipes"] > 0
    lo, hi = ev["interval_90"]
    assert 0.0 <= lo < ev["estimated_impurity_rate"] < hi <= 1.0
    assert "reject" not in json.dumps(ev).lower()
    assert set(ev["flags"]) <= {"SYNTHESIS_IMPURITY_RISK", "REPORTED_ROUTES_ABOVE_GLASS_LIMIT"}


def test_no_recipes_means_no_risk_flag_and_a_wide_interval():
    ev = fe.synthesis_evidence(["Al", "Bi", "Cu", "S", "Cl"])
    assert ev["recipes"] == 0 and ev["evidence_grade"] == "none"
    assert "SYNTHESIS_IMPURITY_RISK" not in ev["flags"]
    if ev["interval_90"] is not None:
        assert ev["interval_90"][1] - ev["interval_90"][0] > 0.3, "an estimate with no own data must stay wide"


def test_risk_flag_needs_enough_recipes_and_a_high_lower_bound():
    flagged = 0
    for sysm, v in fe._systems().items():
        ev = fe.synthesis_evidence(sorted(sysm))
        if "SYNTHESIS_IMPURITY_RISK" in ev["flags"]:
            flagged += 1
            assert ev["recipes"] >= 5
            assert ev["interval_90"][0] > fe.RULES["impurity_flag_lower_bound"]
        if flagged >= 25:
            break
    assert flagged > 0, "the flag must be reachable"


def test_shrinkage_pulls_thin_data_toward_related_systems():
    for sysm, v in fe._systems().items():
        n = v["pure"] + v["impure"]
        ev = fe.synthesis_evidence(sorted(sysm))
        if 1 <= n <= 2 and ev["prior_rate"] is not None and ev["raw_impurity_rate"] in (0.0, 1.0):
            assert 0.0 < ev["estimated_impurity_rate"] < 1.0
            return
    pytest.fail("no thin-data system found to test shrinkage")


# ---------------------------------------------------------------- ablation

def test_committed_ablation_is_reproducible():
    committed = json.loads((ROOT / "data" / "failure_ablation.json").read_text(encoding="utf-8"))
    fresh = fe.run_ablation()
    assert committed == fresh


def test_ablation_conclusions_quoted_in_the_plan_match_the_data():
    """The plan may claim a benefit only where the bootstrap interval excludes zero."""
    ab = json.loads((ROOT / "data" / "failure_ablation.json").read_text(encoding="utf-8"))
    plan = (ROOT / "docs" / "FAILURE_DATA_PLAN.md").read_text(encoding="utf-8")
    for subset in ("all", "chalcogenide"):
        lo, hi = ab[subset]["improvement_bootstrap_95_percent"]
        assert f"{ab[subset]['related_brier_improvement_vs_global_percent']:.1f}%" in plan
        assert f"{lo:.1f}% to {hi:.1f}%" in plan
    assert ab["all"]["improvement_bootstrap_95_percent"][0] > 0
    if ab["chalcogenide"]["improvement_bootstrap_95_percent"][0] <= 0:
        assert "not established for chalcogenides" in plan


# ---------------------------------------------------------------- device records

def test_every_device_record_has_a_source_and_a_known_family():
    with open(ROOT / "data" / "device_failure_records.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) >= 9
    families = {"PNICTOGEN_CHALCOGENIDE", "PNICTOGEN_CHALCOHALIDE", "COINAGE_PNICTOGEN_CHALCOGENIDE"}
    for r in rows:
        assert r["source_url"].startswith("https://"), r["record_id"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["opened_on"]), r["record_id"]
        assert r["family"] in families
        float(r["value"])
        assert r["mechanism"].strip()


@pytest.mark.parametrize(
    "elements,family",
    [
        (["Bi", "Sb", "S"], "PNICTOGEN_CHALCOGENIDE"),
        (["Sb", "O", "S"], "PNICTOGEN_CHALCOGENIDE"),
        (["Bi", "Cu", "S"], "COINAGE_PNICTOGEN_CHALCOGENIDE"),
        (["Ag", "Bi", "S", "Cl"], "PNICTOGEN_CHALCOHALIDE"),
        (["Al", "Cu", "Sn", "S"], None),
    ],
)
def test_material_family_assignment(elements, family):
    assert fe.material_family(elements) == family


def test_analog_evidence_is_labelled_as_analogy_and_only_flags():
    ev = fe.analog_device_evidence(["Bi", "Sb", "S"])
    assert "analogy" in ev["basis"]
    assert ev["lowest_analog_theoretical_limit_percent"] == 16
    assert all(f.startswith("ANALOG_") for f in ev["flags"])
    assert fe.analog_device_evidence(["Al", "Cu", "Sn", "S"])["records"] == []


# ---------------------------------------------------------------- scorecards and rules

def test_every_shortlist_entry_gets_a_complete_scorecard():
    summary = _summary()
    cards = fe.build_scorecards(summary)
    assert len(cards) == len(summary["ranked_shortlist"]["not_excluded"])
    for c in cards:
        assert c["queue_class"] in ("CALCULATE_FIRST", "CALCULATE_NEXT", "PARK")
        for axis in ("effective", "cost", "stable", "synthesizable"):
            assert c[axis]["tier"] in fe.TIERS, (c["candidate_id"], axis)
            assert isinstance(c[axis]["flags"], list)


def test_rule_r2_an_estimated_gap_is_never_presented_as_strong_evidence():
    for c in fe.build_scorecards(_summary()):
        if "GAP_IS_AN_ESTIMATE" in c["effective"]["flags"]:
            assert c["effective"]["tier"] == "T1_HEURISTIC"
        else:
            assert c["effective"]["tier"] in ("T4_COMPUTED_HERE", "T5_MEASURED")


def test_rules_r5_to_r7_queue_classes_follow_the_stated_rules():
    crit = set(fe.RULES["critical_elements"])
    for c in fe.build_scorecards(_summary()):
        known = c["synthesizable"]["experimentally_known_phase"]
        has_crit = bool(c["cost"]["critical_elements"])
        near = c["stable"]["e_above_hull_mev"] <= fe.RULES["hull_near_mev"]
        if c["queue_class"] == "CALCULATE_FIRST":
            assert known and not has_crit and near
        elif c["queue_class"] == "CALCULATE_NEXT":
            assert not known and not has_crit and near and c["nsites"] <= fe.RULES["large_cell_sites"]
        assert set(c["cost"]["critical_elements"]) <= crit


def test_scorecards_are_ordered_by_class_then_window_probability():
    cards = fe.build_scorecards(_summary())
    order = {"CALCULATE_FIRST": 0, "CALCULATE_NEXT": 1, "PARK": 2}
    keys = [(order[c["queue_class"]], -c["effective"]["window_probability"]) for c in cards]
    assert keys == sorted(keys)


def test_committed_scorecards_match_the_summary_they_were_generated_from():
    """If the summary has changed since generation, regenerate; this test then checks equality."""
    committed = json.loads((ROOT / "outputs" / "material_scorecards.json").read_text(encoding="utf-8"))
    if committed["summary_sha256"] != fe.summary_digest():
        pytest.skip("summary changed: run `python -m failsmart_matengine.failure_evidence scorecards`")
    assert committed["scorecards"] == fe.build_scorecards(_summary())


def test_rules_guide_documents_every_threshold_and_tier():
    guide = (ROOT / "docs" / "MATERIAL_EVALUATION_RULES.md").read_text(encoding="utf-8")
    for tier in fe.TIERS:
        assert tier in guide
    for key in fe.RULES:
        assert f"`{key}`" in guide, f"threshold {key} is not documented in the guide"
    for rule in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"):
        assert re.search(rf"^### {rule}\.", guide, re.MULTILINE), rule


# ---------------------------------------------------------------- open tasks F1 to F5
# Strict expected failures. Close a task by making its test pass and deleting its marker
# in the same commit. Do these after the phase-2 gaps (G1 to G9) are merged.

OPEN_F = "open task, see docs/FAILURE_DATA_PLAN.md section 5"


@pytest.mark.xfail(strict=True, reason=f"F1 {OPEN_F}")
def test_f1_scorecards_are_part_of_the_pipeline_summary():
    summary = _summary()
    assert "scorecards" in summary
    assert summary["scorecards"] == fe.build_scorecards(summary)
    assert not (ROOT / "outputs" / "material_scorecards.json").exists()


@pytest.mark.xfail(strict=True, reason=f"F2 {OPEN_F}")
def test_f2_recipe_statistics_never_reject_a_candidate():
    summary = _summary()
    for rec in summary["all_mp_records"]:
        assert rec.get("primary_failure_mode") != "IMPURITY_SINK_PRIOR", rec["candidate"]["candidate_id"]
    with_evidence = [r for r in summary["all_mp_records"] if (r.get("synthesis") or {}).get("synthesis_evidence")]
    assert len(with_evidence) >= 40


@pytest.mark.xfail(strict=True, reason=f"F3 {OPEN_F}")
def test_f3_recipe_totals_match_their_header():
    raw = json.loads((ROOT / "data" / "negative_synthesis_priors.json").read_text(encoding="utf-8"))
    rows = sum(int(v.get("pure_count") or 0) + int(v.get("impure_count") or 0) for v in raw["chemsys_impurity_priors"].values())
    header = raw["dataset_provenance"]["lbnl_solid_state_impurity_dataset"]["total_recipes"]
    assert rows == header
    assert any((ROOT / "scripts").glob("build_negative_synthesis_priors*")), "commit the script that builds the file"


@pytest.mark.xfail(strict=True, reason=f"F4 {OPEN_F}")
def test_f4_device_table_covers_the_shortlist_families():
    assert len(fe.device_records()) >= 30
    cards = fe.build_scorecards(_summary())
    uncovered = [c["formula_reduced"] for c in cards if c["queue_class"] != "PARK" and c["analog_family"] is None]
    assert uncovered == [], f"no analog device records for: {uncovered}"


@pytest.mark.xfail(strict=True, reason=f"F5 {OPEN_F}")
def test_f5_top_of_queue_has_a_literature_check():
    checks = json.loads((ROOT / "data" / "literature_checks.json").read_text(encoding="utf-8"))["checks"]
    for c in fe.build_scorecards(_summary()):
        if c["queue_class"] == "PARK":
            continue
        entry = checks[c["candidate_id"]]
        for key in ("phase_synthesised", "measured_gap_ev", "reported_device", "search_terms", "sources", "checked_on"):
            assert key in entry, (c["candidate_id"], key)
        assert entry["sources"], c["candidate_id"]
