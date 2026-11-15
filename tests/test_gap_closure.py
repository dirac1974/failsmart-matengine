"""Gap-closure acceptance tests (audit of 2026-11-15).

Each test checks one gap from `docs/AUDIT_2026-11-15_READINESS.md`, using the same ID.

- Tests for gaps that are already closed pass normally.
- Tests for open gaps are marked `xfail(strict=True)`. While the gap is open the test fails
  and pytest reports it as an expected failure. When an agent closes the gap the test passes,
  strict mode turns that into an error, and the agent must delete the marker in the same commit.
  A gap counts as closed only when its marker is gone and the test passes.

Run just these tests with:

    pytest -q tests/test_gap_closure.py -rxX

Never edit a test body to make it pass. If a test is wrong, explain why in the commit message.
"""

from __future__ import annotations

import csv
import importlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "outputs" / "live_mp_discovery_summary.json"
OPEN = "open gap, see docs/REMEDIATION_TASKS_PHASE2.md"


def _summary() -> dict:
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def _records_by_id() -> dict:
    return {r["candidate"]["candidate_id"]: r for r in _summary()["all_mp_records"]}


# ---------------------------------------------------------------------------
# Closed gaps (must keep passing)
# ---------------------------------------------------------------------------

def test_c1_committed_gap_model_matches_a_fresh_fit():
    """C1: data/gap_model.json is reproducible from data/gap_benchmark.csv."""
    from failsmart_matengine import gap_model

    committed = json.loads((ROOT / "data" / "gap_model.json").read_text(encoding="utf-8"))
    fresh = gap_model.fit_from_benchmark()
    for k in ("c0", "c1", "c2"):
        assert committed["coefficients"][k] == pytest.approx(fresh["coefficients"][k], abs=1e-4)
    assert committed["sigma_ev"] == pytest.approx(fresh["sigma_ev"], abs=1e-9)
    assert committed["n_benchmark"] == fresh["n_benchmark"] >= 50


def test_c2_error_bar_is_leave_one_out_rmse_not_mae():
    """C2: the pipeline's error bar is a standard deviation (leave-one-out RMSE)."""
    from failsmart_matengine import gap_model

    m = gap_model.fit_from_benchmark()
    assert m["sigma_basis"] == "leave-one-out RMSE"
    assert m["sigma_ev"] == pytest.approx(round(m["leave_one_out"]["rmse_ev"], 2))
    assert m["leave_one_out"]["rmse_ev"] > m["leave_one_out"]["mae_ev"]


def test_c3_pipeline_uses_the_calibrated_model_for_estimated_gaps():
    """C3: every HEURISTIC gap in the outputs equals the calibrated prediction."""
    from failsmart_matengine import gap_model

    cache = {r["mp_id"]: r for r in json.loads((ROOT / "data" / "mp_live_candidates_cache.json").read_text())}
    checked = 0
    for cid, rec in _records_by_id().items():
        el = rec.get("electronics")
        if not el or el["gap_basis"] != "HEURISTIC":
            continue
        raw = cache[cid]
        pred, sigma = gap_model.predict_gap(float(raw["dft_pbe_band_gap_ev"]), raw["stoichiometry"])
        assert el["gap_est_indirect_ev"] == pytest.approx(pred, abs=0.011), cid
        assert el["gap_error_bar_ev"] == pytest.approx(sigma), cid
        checked += 1
    assert checked >= 20


def test_c4_measured_gap_overrides_the_estimate():
    """C4: an entry with a measured gap uses it, and is judged on it."""
    recs = _records_by_id()
    cubis2 = recs["mp-22982"]
    assert cubis2["electronics"]["gap_basis"] == "LITERATURE"
    assert cubis2["electronics"]["gap_est_indirect_ev"] == pytest.approx(1.65, abs=0.01)
    assert cubis2["status"] == "REJECTED"
    cusbse2 = recs["mp-20331"]
    assert cusbse2["electronics"]["gap_basis"] == "LITERATURE"
    assert cusbse2["primary_failure_mode"] == "BANDGAP_OUT_OF_WINDOW"


def test_c5_optical_thresholds_never_reject_an_estimated_gap():
    """C5: optical thresholds are a function of the gap, so they only reject measured or computed gaps."""
    for cid, rec in _records_by_id().items():
        if rec.get("primary_failure_mode") == "LOW_OPTICAL_EFFICIENCY":
            assert rec["electronics"]["gap_basis"] != "HEURISTIC", cid


def test_c6_shortlist_is_ranked_and_honest_about_resolution():
    """C6: shortlist ordered by window probability; no estimated gap claims more than the ceiling."""
    s = _summary()["ranked_shortlist"]
    probs = [r["window_probability"] for r in s["not_excluded"]]
    assert probs == sorted(probs, reverse=True)
    ceiling = s["max_window_probability_for_estimated_gap"]
    for r in s["not_excluded"]:
        if r["gap_basis"] == "HEURISTIC":
            assert r["window_probability"] <= ceiling[r["target_layer"]] + 1e-4
    known_first = [r["is_experimentally_known"] for r in sorted(
        (r for r in s["not_excluded"] if r["gap_basis"] == "HEURISTIC"),
        key=lambda r: s["dft_queue"].index(r["candidate_id"]),
    )]
    assert known_first == sorted(known_first, reverse=True), "synthesised phases must head the DFT queue"


def test_c7_lessons_file_and_memory_instructions_exist():
    """C7: future agents are told to record lessons and update memory."""
    lessons = (ROOT / "docs" / "LESSONS_LEARNED.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "LESSONS_LEARNED.md" in agents
    assert re.search(r"memory", agents, re.IGNORECASE)
    assert len(re.findall(r"^### L\d+", lessons, re.MULTILINE)) >= 8


# ---------------------------------------------------------------------------
# Open gaps (strict expected failures; remove the marker when closed)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason=f"G1 {OPEN}")
def test_g1_repository_auditor_passes_without_hardcoded_live_results():
    """G1: the auditor passes and contains no pinned numbers from a past run of the live funnel."""
    proc = subprocess.run(
        [sys.executable, "-m", "failsmart_matengine.repo_auditor"],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0 and "[PASS]" in proc.stdout, proc.stdout[-2000:]
    src = (ROOT / "failsmart_matengine" / "repo_auditor.py").read_text(encoding="utf-8")
    for stale in ("== 47", "== 40,", "== 15", "== 56", "42.32", "42.22", "41.71", "43.08", "40.71", "4.420"):
        assert stale not in src, f"pinned live-run value {stale!r} still in repo_auditor.py"


@pytest.mark.xfail(strict=True, reason=f"G2 {OPEN}")
def test_g2_readme_results_block_is_generated_from_outputs():
    """G2: README holds a generated results block that matches the current summary exactly."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"<!-- BEGIN GENERATED RESULTS -->\n(.*?)<!-- END GENERATED RESULTS -->", readme, re.DOTALL)
    assert m, "README.md has no generated results block"
    mod = importlib.import_module("failsmart_matengine.report_blocks")
    assert m.group(1) == mod.render_results_block(_summary())


@pytest.mark.xfail(strict=True, reason=f"G3 {OPEN}")
def test_g3_measured_polymorph_gap_is_flagged():
    """G3: a theoretical entry whose composition has a measured polymorph carries that gap as a flag."""
    rec = _records_by_id()["mp-861911"]  # Sb2OS2, C2/m theoretical; kermesite mp-28711 measured 2.04 eV
    el = rec["electronics"]
    assert el.get("measured_polymorph_mp_id") == "mp-28711"
    assert el.get("measured_polymorph_gap_ev") == pytest.approx(2.04, abs=0.01)
    assert el["gap_basis"] == "HEURISTIC", "a different polymorph's gap must not replace this entry's gap"


@pytest.mark.xfail(strict=True, reason=f"G4 {OPEN}")
def test_g4_uncalibrated_heuristics_flag_but_never_reject():
    """G4: carrier-mass, Frohlich and defect-depth heuristics are flags, not gates."""
    flag_modes = {"HEAVY_CARRIER_MASS", "DEEP_SRH_DEFECT"}
    recs = _records_by_id()
    for cid, rec in recs.items():
        assert rec.get("primary_failure_mode") not in flag_modes or rec["electronics"]["provenance"].get(
            "deepest_defect_level_from_band_edge_ev"
        ) != "HEURISTIC", cid
    from failsmart_matengine.schemas import ElectronicDefectReport

    assert "heuristic_flags" in ElectronicDefectReport.model_fields


@pytest.mark.xfail(strict=True, reason=f"G5 {OPEN}")
def test_g5_dft_kit_collects_results_that_the_pipeline_uses(tmp_path):
    """G5: dft_slice turns a Quantum ESPRESSO output into data the gap model reads as COMPUTED_HERE."""
    dft = importlib.import_module("failsmart_matengine.dft_slice")
    fixture = ROOT / "tests" / "fixtures" / "qe" / "si_pbesol_bands.out"
    assert fixture.exists(), "commit a real pw.x output for silicon (see task G5)"
    parsed = dft.parse_pw_output(fixture)
    assert parsed["converged"] is True
    assert 0.3 < parsed["gap_ev"] < 0.8  # PBEsol underestimates the 1.12 eV gap of Si
    results = dft.collect([fixture], out_path=tmp_path / "dft_results.json", candidate_ids=["mp-149"])
    assert results["results"]["mp-149"]["best_gap_ev"] == pytest.approx(parsed["gap_ev"])
    plan = dft.prepare(["mp-22982"], out_dir=tmp_path / "decks", level="pbesol_soc")
    assert any(p.suffix == ".in" for p in plan["files"])


@pytest.mark.xfail(strict=True, reason=f"G6 {OPEN}")
def test_g6_gpu_ml_screen_is_optional_and_tagged():
    """G6: the GPU screen imports without torch, picks a device, and tags outputs as MLIP."""
    from failsmart_matengine.schemas import ProvenanceTag

    assert "MLIP" in ProvenanceTag.__members__
    ml = importlib.import_module("failsmart_matengine.ml_screen")
    assert ml.select_device() in ("cuda", "cpu")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r"^ml\s*=", pyproject, re.MULTILINE), "optional dependency group 'ml' missing"


@pytest.mark.xfail(strict=True, reason=f"G7 {OPEN}")
def test_g7_ci_runs_tests_and_auditor():
    """G7: continuous integration runs the test suite and the auditor."""
    wf = ROOT / ".github" / "workflows" / "ci.yml"
    assert wf.exists()
    text = wf.read_text(encoding="utf-8")
    assert "pytest" in text and "repo_auditor" in text


@pytest.mark.xfail(strict=True, reason=f"G8 {OPEN}")
def test_g8_v2_pilot_quarantined_as_fixtures():
    """G8 (old T9): the v2 pilot tables are labelled synthetic fixtures."""
    src = (ROOT / "failsmart_matengine" / "physics_calculators.py").read_text(encoding="utf-8")
    assert "ground-truth" not in src.lower()
    assert "_RAW_STABILITY_DATA" not in src
    assert (ROOT / "tests" / "fixtures" / "v2_pilot").is_dir()


@pytest.mark.xfail(strict=True, reason=f"G9 {OPEN}")
def test_g9_failure_ledger_persists_between_runs():
    """G9 (old T11): the ledger is only reset when the caller asks (a `reset_ledger` flag, default False)."""
    import inspect

    from failsmart_matengine import mp_live_discovery, orchestrator

    for fn in (mp_live_discovery.run_live_mp_discovery_campaign, orchestrator.run_pilot_campaign):
        params = inspect.signature(fn).parameters
        assert "reset_ledger" in params, f"{fn.__name__} has no reset_ledger flag"
        assert params["reset_ledger"].default is False, f"{fn.__name__} resets by default"
