"""Checks for the 2026-11-16 integration of `main` into the reviewed branch chain.

Background: docs/CARBON_REVIEW_2026-11-16.md. Each test covers one thing that was ported
from `main`, or one thing from `main` that was deliberately left out.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "failsmart_matengine"


def test_importing_the_package_does_not_load_the_heavy_verifier():
    code = (
        "import sys, failsmart_matengine as f; "
        "assert 'failsmart_matengine.independent_verifier' not in sys.modules; "
        "assert callable(f.simpson_13); "
        "assert 'failsmart_matengine.independent_verifier' in sys.modules; "
        "print(f.__version__)"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "0.8.0"


def test_every_lazy_export_exists():
    import failsmart_matengine as f
    from failsmart_matengine import independent_verifier as iv

    for name in f._VERIFIER_EXPORTS:
        assert hasattr(iv, name), name


def test_command_line_entry_points_resolve():
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert set(scripts) == {"failsmart-audit", "failsmart-pilot", "failsmart-mp-live"}
    for target in scripts.values():
        module, func = target.split(":")
        source = (ROOT / (module.replace(".", "/") + ".py")).read_text(encoding="utf-8")
        assert re.search(rf"^def {func}\(", source, re.M), target


def test_text_files_are_written_as_utf8():
    missing = []
    for path in sorted(PKG.glob("*.py")):
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if ".write_text(" in line and "encoding" not in line:
                missing.append(f"{path.name}:{no}")
    assert missing == []


def test_no_absolute_home_paths_in_the_package():
    for path in sorted(PKG.glob("*.py")):
        assert "/home/" not in path.read_text(encoding="utf-8"), path.name


def test_second_heuristic_veto_gate_from_main_was_not_adopted():
    # main added a "Gate B" that rejects on the same heuristics rule R2 forbids.
    for name in ("tools.py", "orchestrator.py", "mp_live_discovery.py"):
        assert "gate_b_final_red_team_audit" not in (PKG / name).read_text(encoding="utf-8"), name


def test_electronegativity_table_has_no_silent_default():
    source = (PKG / "realistic_commercialization.py").read_text(encoding="utf-8")
    assert "MULLIKEN_CHI_EV.get(" not in source


def _walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _walk(a.get(k, "<missing>"), b.get(k, "<missing>"), path + [k], out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _walk(x, y, path + [i], out)
    elif a != b:
        out.append("/".join(str(p) for p in path))


def test_committed_outputs_are_what_the_code_produces(tmp_path):
    """Guard against changing code without regenerating outputs (as happened on main,
    where 15 committed values no longer matched the code and the auditor still passed)."""
    import json

    from failsmart_matengine.mp_live_discovery import run_live_mp_discovery_campaign

    ledger_db = ROOT / "data" / "mp_live_failure_memory.db"
    saved = ledger_db.read_bytes() if ledger_db.exists() else None
    try:
        fresh = run_live_mp_discovery_campaign(output_dir=tmp_path)
    finally:
        if saved is not None:
            ledger_db.write_bytes(saved)
    committed = json.loads((ROOT / "outputs" / "live_mp_discovery_summary.json").read_text(encoding="utf-8"))
    differing: list = []
    _walk(committed, json.loads(json.dumps(fresh)), [], differing)
    assert differing == [], f"{len(differing)} values differ, first: {differing[:5]}"


# ================================================================ open tasks (strict xfail)
# Task list: docs/WORK_ORDER.md. Delete a marker in the commit that closes the task.

import pytest  # noqa: E402

OPEN_M = "open task in docs/WORK_ORDER.md"


def _summary():
    import json

    return json.loads((ROOT / "outputs" / "live_mp_discovery_summary.json").read_text(encoding="utf-8"))


@pytest.mark.xfail(strict=True, reason=f"M2 {OPEN_M}")
def test_m2_year_25_retention_uses_25_years():
    source = (PKG / "atomistic_and_tmm.py").read_text(encoding="utf-8")
    assert "** 24)" not in source
    stacks = _summary()["real_world_lcoe_stress_test_stacks"]
    assert stacks
    for s in stacks:
        rate = s["annual_degradation_rate_pct_yr"] / 100.0
        assert abs(s["year25_retained_power_fraction_percent"] - (1.0 - rate) ** 25 * 100.0) <= 0.02


@pytest.mark.xfail(strict=True, reason=f"M3 {OPEN_M}")
def test_m3_electronegativity_table_covers_halides_with_sourced_values():
    from failsmart_matengine.realistic_commercialization import MULLIKEN_CHI_EV

    # Pearson, Inorg. Chem. 27, 734 (1988), doi:10.1021/ic00277a030
    expected = {"Zn": 4.45, "Ba": 2.4, "Sr": 2.0, "Cl": 8.30, "Br": 7.59, "I": 6.76}
    for el, value in expected.items():
        assert MULLIKEN_CHI_EV.get(el) == value, el
    source = (PKG / "realistic_commercialization.py").read_text(encoding="utf-8")
    assert "10.1021/ic00277a030" in source


@pytest.mark.xfail(strict=True, reason=f"M4 {OPEN_M}")
def test_m4_transmitted_light_is_not_attenuated_twice():
    pattern = re.compile(r"=\s*t_\w+\s*\*\s*\(1\.0\s*-\s*fabs1\)")
    for name in ("atomistic_and_tmm.py", "independent_verifier.py"):
        hits = [ln for ln in (PKG / name).read_text(encoding="utf-8").splitlines() if pattern.search(ln)]
        assert hits == [], (name, hits[:3])
