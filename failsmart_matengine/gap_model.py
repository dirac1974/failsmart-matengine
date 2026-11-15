"""Calibrated band-gap model, measured-gap lookup and window probability.

This module is the single place the pipeline gets a band gap from. For a
Materials Project entry it returns the best available value, in this order:

1. ``LITERATURE``    a measured optical gap for that exact entry
                     (``data/gap_benchmark.csv``, rows with an ``mp_id``).
2. ``COMPUTED_HERE`` a first-principles gap computed with the DFT run kit
                     (``data/dft_results.json``, written by ``dft_slice collect``).
3. ``HEURISTIC``     the calibrated correction to the Materials Project PBE gap
                     (coefficients in ``data/gap_model.json``).

The calibrated correction is

    E_g = max(0, E_PBE + c0 + c1 / max(4.5, eps_inf) - c2 * soc_raw)

with non-negative coefficients fitted to the measured gaps in
``data/gap_benchmark.csv``. Its error bar is the leave-one-out RMSE, because a
normal error model needs a standard deviation, not a mean absolute error.

Run ``python -m failsmart_matengine.gap_model`` to refit and rewrite
``data/gap_model.json`` from the benchmark file.
"""

from __future__ import annotations

import csv
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_CSV = _REPO_ROOT / "data" / "gap_benchmark.csv"
MODEL_JSON = _REPO_ROOT / "data" / "gap_model.json"
DFT_RESULTS_JSON = _REPO_ROOT / "data" / "dft_results.json"

# Target windows (eV)
WINDOWS: Dict[str, Tuple[float, float]] = {
    "TOP_ACTIVE_GLASS_185EV": (1.75, 1.95),
    "BOTTOM_IR_075EV": (0.70, 0.85),
}

# Error bars (eV, one standard deviation) by basis.
# ASSUMED: spread between reported optical gaps of the same compound (method, temperature, film vs crystal).
SIGMA_LITERATURE_EV = 0.10
# ASSUMED until the DFT controls are run: typical hybrid-functional error for these chemistries.
# `dft_slice collect` replaces it with the error measured on the control compounds.
SIGMA_DFT_DEFAULT_EV = 0.25


# ----------------------------------------------------------------------------
# Features (HEURISTIC inputs to the correction)
# ----------------------------------------------------------------------------

def _frac(stoich: Dict[str, float], elements: Sequence[str]) -> float:
    total = max(1e-12, float(sum(stoich.values())))
    return float(sum(stoich.get(e, 0) for e in elements)) / total


def soc_raw_ev(stoich: Dict[str, float]) -> float:
    """Composition-weighted spin-orbit proxy (HEURISTIC)."""
    return round(
        0.03
        + 0.72 * _frac(stoich, ("Bi", "Pb"))
        + 0.42 * _frac(stoich, ("I", "Te"))
        + 0.20 * (_frac(stoich, ("Sb", "Sn")) + _frac(stoich, ("Br", "Se"))),
        3,
    )


def eps_inf_heuristic(pbe_gap_ev: float, stoich: Dict[str, float]) -> float:
    """Penn-style high-frequency dielectric constant proxy (HEURISTIC)."""
    val = (
        12.2
        - 2.6 * pbe_gap_ev
        - 1.8 * _frac(stoich, ("O",))
        + 2.2 * (_frac(stoich, ("Bi", "Pb")) + _frac(stoich, ("Sb", "Sn")))
    )
    return round(float(np.clip(val, 4.8, 15.5)), 2)


def _design_row(pbe_gap_ev: float, stoich: Dict[str, float], eps_inf: Optional[float] = None) -> List[float]:
    eps = eps_inf if eps_inf is not None else eps_inf_heuristic(pbe_gap_ev, stoich)
    return [1.0, 1.0 / max(4.5, eps), -soc_raw_ev(stoich)]


# ----------------------------------------------------------------------------
# Benchmark and fit
# ----------------------------------------------------------------------------

def load_benchmark(path: Path = BENCHMARK_CSV) -> List[Dict[str, Any]]:
    """Benchmark rows that have both a Materials Project PBE gap and a measured gap."""
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r.get("mp_pbe_gap_ev") or not r.get("measured_gap_ev") or not r.get("mp_id"):
                continue
            rows.append(
                {
                    "formula": r["formula"],
                    "mp_id": r["mp_id"].strip(),
                    "family": r["chemical_family"],
                    "stoich": {k: float(v) for k, v in json.loads(r["stoichiometry_json"]).items()},
                    "pbe": float(r["mp_pbe_gap_ev"]),
                    "measured": float(r["measured_gap_ev"]),
                    "doi": r.get("source_doi", ""),
                    "url": r.get("source_url", ""),
                }
            )
    return rows


def _nnls(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    from scipy.optimize import nnls

    coef, _ = nnls(a, b)
    return coef


def _cv_errors(x: np.ndarray, target: np.ndarray, groups: Sequence[Any]) -> np.ndarray:
    """Held-out residuals (prediction minus target) with each group left out in turn."""
    groups_arr = np.array([str(g) for g in groups])
    resid = np.zeros_like(target)
    for g in sorted(set(groups_arr)):
        test = groups_arr == g
        coef = _nnls(x[~test], target[~test])
        resid[test] = x[test] @ coef - target[test]
    return resid


def _summary(resid: np.ndarray) -> Dict[str, float]:
    return {
        "mae_ev": round(float(np.mean(np.abs(resid))), 4),
        "rmse_ev": round(float(np.sqrt(np.mean(resid ** 2))), 4),
        "bias_ev": round(float(np.mean(resid)), 4),
        "max_abs_ev": round(float(np.max(np.abs(resid))), 4),
    }


def fit_from_benchmark(path: Path = BENCHMARK_CSV) -> Dict[str, Any]:
    """Fit the correction and cross-validate it. Returns the model dictionary."""
    rows = load_benchmark(path)
    x = np.array([_design_row(r["pbe"], r["stoich"]) for r in rows], dtype=float)
    pbe = np.array([r["pbe"] for r in rows], dtype=float)
    measured = np.array([r["measured"] for r in rows], dtype=float)
    target = measured - pbe  # the correction to learn

    coef = _nnls(x, target)
    in_sample = np.maximum(0.0, pbe + x @ coef) - measured
    loo = _cv_errors(x, target, list(range(len(rows))))
    lofo = _cv_errors(x, target, [r["family"] for r in rows])
    has_cu_ag = np.array([(r["stoich"].get("Cu", 0) + r["stoich"].get("Ag", 0)) > 0 for r in rows])

    return {
        "form": "E_g = max(0, E_PBE + c0 + c1 / max(4.5, eps_inf) - c2 * soc_raw)",
        "coefficients": {"c0": round(float(coef[0]), 4), "c1": round(float(coef[1]), 4), "c2": round(float(coef[2]), 4)},
        "n_benchmark": len(rows),
        "benchmark_file": "data/gap_benchmark.csv",
        "in_sample": _summary(in_sample),
        "leave_one_out": _summary(loo),
        "leave_one_family_out": _summary(lofo),
        "leave_one_out_cu_ag": _summary(loo[has_cu_ag]),
        "leave_one_out_no_cu_ag": _summary(loo[~has_cu_ag]),
        "raw_pbe": _summary(pbe - measured),
        "sigma_ev": round(float(np.sqrt(np.mean(loo ** 2))), 2),
        "sigma_basis": "leave-one-out RMSE",
        "provenance": "COMPUTED_HERE (fit) on MP_DFT (PBE gaps) and LITERATURE (measured gaps)",
    }


@lru_cache(maxsize=1)
def load_model() -> Dict[str, Any]:
    """Load the committed model; refit from the benchmark if the file is missing."""
    if MODEL_JSON.exists():
        return json.loads(MODEL_JSON.read_text(encoding="utf-8"))
    return fit_from_benchmark()


def predict_gap(pbe_gap_ev: float, stoich: Dict[str, float], eps_inf: Optional[float] = None) -> Tuple[float, float]:
    """Calibrated gap estimate and its one-sigma error bar (eV). Provenance: HEURISTIC."""
    model = load_model()
    c = model["coefficients"]
    row = _design_row(pbe_gap_ev, stoich, eps_inf)
    eg = max(0.0, pbe_gap_ev + c["c0"] * row[0] + c["c1"] * row[1] + c["c2"] * row[2])
    return round(float(eg), 2), float(model["sigma_ev"])


# ----------------------------------------------------------------------------
# Measured and computed gaps
# ----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def measured_gap_table() -> Dict[str, Dict[str, Any]]:
    """Measured optical gaps keyed by Materials Project id (LITERATURE)."""
    table: Dict[str, Dict[str, Any]] = {}
    if BENCHMARK_CSV.exists():
        for r in load_benchmark():
            table[r["mp_id"]] = {"gap_ev": r["measured"], "doi": r["doi"], "url": r["url"], "formula": r["formula"]}
    return table


@lru_cache(maxsize=1)
def dft_gap_table() -> Dict[str, Dict[str, Any]]:
    """First-principles gaps computed with the DFT run kit, keyed by id (COMPUTED_HERE)."""
    if not DFT_RESULTS_JSON.exists():
        return {}
    data = json.loads(DFT_RESULTS_JSON.read_text(encoding="utf-8"))
    return {k: v for k, v in data.get("results", {}).items() if v.get("best_gap_ev") is not None}


def clear_caches() -> None:
    load_model.cache_clear()
    measured_gap_table.cache_clear()
    dft_gap_table.cache_clear()


def resolve_gap(mp_id: str, pbe_gap_ev: float, stoich: Dict[str, float], eps_inf: Optional[float] = None) -> Dict[str, Any]:
    """Best available gap for an entry, with error bar, basis and source."""
    est, est_sigma = predict_gap(pbe_gap_ev, stoich, eps_inf)
    out: Dict[str, Any] = {"gap_heuristic_ev": est, "gap_heuristic_sigma_ev": est_sigma}

    measured = measured_gap_table().get(mp_id)
    if measured:
        out.update(
            gap_ev=round(float(measured["gap_ev"]), 2),
            sigma_ev=SIGMA_LITERATURE_EV,
            basis="LITERATURE",
            source=measured["doi"] or measured["url"],
        )
        return out

    dft = dft_gap_table().get(mp_id)
    if dft:
        out.update(
            gap_ev=round(float(dft["best_gap_ev"]), 2),
            sigma_ev=float(dft.get("sigma_ev") or SIGMA_DFT_DEFAULT_EV),
            basis="COMPUTED_HERE",
            source=str(dft.get("method", "dft_slice")),
        )
        return out

    out.update(gap_ev=est, sigma_ev=est_sigma, basis="HEURISTIC", source="data/gap_model.json")
    return out


# ----------------------------------------------------------------------------
# Window probability and gate
# ----------------------------------------------------------------------------

def window_probability(gap_ev: float, sigma_ev: float, layer: str) -> float:
    """Probability that the true gap lies in the layer's target window, for a normal error model."""
    lo, hi = WINDOWS[layer]
    s = max(1e-9, sigma_ev) * math.sqrt(2.0)
    return round(0.5 * (math.erf((hi - gap_ev) / s) - math.erf((lo - gap_ev) / s)), 4)


def best_layer(gap_ev: float, sigma_ev: float) -> str:
    """Layer whose window the gap is more likely to be in."""
    return max(WINDOWS, key=lambda layer: window_probability(gap_ev, sigma_ev, layer))


def within_one_sigma(gap_ev: float, sigma_ev: float, layer: str) -> bool:
    """Gate rule: the target window lies within one error bar of the gap."""
    lo, hi = WINDOWS[layer]
    return (lo - sigma_ev) <= gap_ev <= (hi + sigma_ev)


def main() -> None:
    model = fit_from_benchmark()
    MODEL_JSON.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    clear_caches()
    print(json.dumps(model, indent=2))
    print(f"\nWrote {MODEL_JSON.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
