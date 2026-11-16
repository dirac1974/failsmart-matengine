"""Methodology checks added by the 2026-11-15 review.

Background: docs/METHODOLOGY_REVIEW_2026-11-15.md. Tasks: docs/METHODOLOGY_TASKS_V.md.
Tests: tests/test_methodology_v.py.

Everything here is a pure function of its arguments or of the pipeline summary. This
module does not edit the pipeline. Wiring these functions into the pipeline is tasks
V2 to V10.

Contents
    1. Gate audit           which rejections rest on evidence too weak to reject (rule R2)
    2. Window analysis      how wide the target window is against the gap error, and how
                            the best top-cell gap moves with top-cell quality
    3. Calculation queue    expected in-window results per unit of compute
    4. Temperature          voltage temperature coefficient from the voltage deficit
    5. Contact alignment    classify a band offset only when it exceeds its error

Commands
    python -m failsmart_matengine.methodology_checks audit
    python -m failsmart_matengine.methodology_checks window
    python -m failsmart_matengine.methodology_checks queue
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_JSON = _REPO_ROOT / "outputs" / "live_mp_discovery_summary.json"

KB_EV_PER_K = 8.617333262e-5

# Judgement calls (ASSUMED). Change them here, never inline.
RULES_V: Dict[str, Any] = {
    # Cost of a hybrid-functional run grows roughly as (number of sites) ** exponent.
    # ASSUMED until task V6 step 4 fits it to wall times measured with the run kit.
    "cost_exponent": 2.0,
    "cost_reference_sites": 10,
    # Conduction-band offset (transport layer minus absorber, eV) with no penalty.
    # LITERATURE for Cu(In,Ga)Se2: Minemoto et al. 2001, as cited by Chen et al. 2017
    # (J. Electron. Mater., doi:10.1007/s11664-017-5850-9). ASSUMED to carry over to
    # other absorbers.
    "offset_ok_low_ev": 0.0,
    "offset_ok_high_ev": 0.4,
    # Temperature-coefficient term gamma in dVoc/dT; 3 is the textbook silicon value.
    "voc_gamma": 3.0,
    # Voltage deficit (Eg/q - Voc) of the best related cell on record. LITERATURE: Sb2S3 at
    # 824 mV (record DF02 in data/device_failure_records.csv) with a 1.70 eV gap
    # (data/gap_benchmark.csv).
    "reference_voltage_deficit_v": 0.876,
    # Elements whose toxicity complicates manufacture and sale. ASSUMED list.
    "toxic_elements": ("As", "Cd", "Hg", "Pb", "Tl"),
    # Tolerance (absolute efficiency points) that defines a window around the best gap.
    "window_tolerance_abs_pct": 1.0,
}

# ---------------------------------------------------------------- 1. gate audit

T1 = "T1_HEURISTIC"
T2 = "T2_ANALOGY"
T3 = "T3_DATABASE_DFT_OR_ML_POTENTIAL"
T5 = "T5_MEASURED"

# Every failure mode the funnel can emit, the evidence behind it, and whether evidence of
# that tier is allowed to reject (rule R2 in docs/MATERIAL_EVALUATION_RULES.md: only
# database DFT, a calculation run here, or a measurement can exclude).
#   replace_with: the flag that takes the gate's place when it may not reject.
#   owner: the task that makes the change.
GATE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "HULL_INSTABILITY": {
        "tier": T3, "may_reject": True, "replace_with": None, "owner": None,
        "basis": "Materials Project energy above the convex hull, more than 50 meV per atom",
    },
    "BANDGAP_OUT_OF_WINDOW": {
        "tier": T5, "may_reject": True, "replace_with": None, "owner": None,
        "basis": "gap measured, or computed here, and more than one error bar outside the window",
    },
    # Not a name the funnel emits: gate_audit files a BANDGAP_OUT_OF_WINDOW rejection here
    # when the gap behind it is the calibrated estimate (gap_basis == HEURISTIC).
    "BANDGAP_OUT_OF_WINDOW_ESTIMATED": {
        "tier": T1, "may_reject": False, "replace_with": "LOW_WINDOW_PROBABILITY", "owner": "V2",
        "basis": "calibrated estimate with a 0.44 eV error bar, more than one error bar outside "
                 "the window. Such an entry still has up to a 0.09 chance of being inside, against "
                 "0.18 for the best-placed estimate: lower priority, not grounds to reject.",
    },
    "ELASTIC_INSTABILITY": {
        "tier": T1, "may_reject": False, "replace_with": "SOFT_LATTICE", "owner": "V2",
        "basis": "bulk modulus below 15 GPa or shear modulus below 12 GPa. These thresholds are "
                 "not the Born stability conditions, and soft van der Waals crystals fail them "
                 "while existing.",
    },
    "ION_MIGRATION_INSTABILITY": {
        "tier": T1, "may_reject": False, "replace_with": "ION_MIGRATION_HEURISTIC", "owner": "V2",
        "basis": "closed-form migration-barrier estimate, no barrier calculation",
    },
    "OXIDE_IMPURITY_SINK": {
        "tier": T1, "may_reject": False, "replace_with": "HIGH_TEMPERATURE_ROUTE_EXPECTED", "owner": "V2",
        "basis": "process temperature assumed from the element list",
    },
    "IMPURITY_SINK_PRIOR": {
        "tier": T2, "may_reject": False, "replace_with": "SYNTHESIS_IMPURITY_RISK", "owner": "F2",
        "basis": "powder-recipe impurity statistics for the chemical system",
    },
    "AQUEOUS_LEACHING": {
        "tier": T1, "may_reject": False, "replace_with": "AQUEOUS_LEACHING_HEURISTIC", "owner": "V2",
        "basis": "solubility constant chosen from the element list",
    },
    "TIER2_COST_EXCEEDED": {
        "tier": T1, "may_reject": False, "replace_with": "HIGH_ELEMENT_COST", "owner": "V2",
        "basis": "element prices times an assumed film thickness against an assumed 0.50 USD per m2 limit",
    },
    "LOW_DIM_POLARON_RISK": {
        "tier": T1, "may_reject": False, "replace_with": "LOW_DIMENSIONAL_ORIENTATION_REQUIRED", "owner": "V2",
        "basis": "structure class only. The best-performing relatives (Sb2Se3, Sb2S3) are ribbon "
                 "structures that work when the ribbons stand on the substrate.",
    },
    "LOW_OPTICAL_EFFICIENCY": {
        "tier": T1, "may_reject": False, "replace_with": "LOW_MODELLED_ABSORPTION", "owner": "V2",
        "basis": "absorption coefficient from a closed-form expression, even when the gap is measured",
    },
    "HEAVY_CARRIER_MASS": {
        "tier": T1, "may_reject": False, "replace_with": "HEAVY_CARRIER_MASS_HEURISTIC", "owner": "G4",
        "basis": "effective masses from composition heuristics",
    },
    "DEEP_SRH_DEFECT": {
        "tier": T1, "may_reject": False, "replace_with": "DEEP_DEFECT_HEURISTIC", "owner": "G4",
        "basis": "defect depth chosen from five constants",
    },
}

# Which scorecard axis each replacement flag belongs to (task V2 step 6).
FLAG_AXIS: Dict[str, str] = {
    "SOFT_LATTICE": "stable",
    "ION_MIGRATION_HEURISTIC": "stable",
    "AQUEOUS_LEACHING_HEURISTIC": "stable",
    "HIGH_TEMPERATURE_ROUTE_EXPECTED": "synthesizable",
    "SYNTHESIS_IMPURITY_RISK": "synthesizable",
    "HIGH_ELEMENT_COST": "cost",
    "TOXIC_ELEMENT": "cost",
    "LOW_DIMENSIONAL_ORIENTATION_REQUIRED": "effective",
    "LOW_MODELLED_ABSORPTION": "effective",
    "LOW_WINDOW_PROBABILITY": "effective",
    "HEAVY_CARRIER_MASS_HEURISTIC": "effective",
    "DEEP_DEFECT_HEURISTIC": "effective",
}

# Modes that claim the phase cannot exist. An experimentally known phase contradicts them.
INSTABILITY_MODES = frozenset({"ELASTIC_INSTABILITY"})


def toxic_elements_present(elements: Iterable[str]) -> List[str]:
    """Elements of the candidate that are on the toxic list, sorted. Non-empty means the
    flag TOXIC_ELEMENT applies (task V2 step 5)."""
    return sorted(set(elements) & set(RULES_V["toxic_elements"]))


def load_summary(path: Path = SUMMARY_JSON) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def gate_audit(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Count rejections by gate and by the strength of the evidence behind the gate.

    Returns a dictionary with:
        gates                         one entry per failure mode seen in the run
        unregistered_modes            modes missing from GATE_REGISTRY (must be empty)
        rejected_total
        rejected_on_weak_evidence     rejections by gates that may not reject
        known_phases_rejected_as_unstable   candidate ids
        by_dimensionality             {class: {"total": n, "promoted": n}}
    """
    records = summary["all_mp_records"]
    gates: Dict[str, Dict[str, Any]] = {}
    unregistered: List[str] = []
    contradictions: List[str] = []
    by_dim: Dict[str, Dict[str, int]] = {}

    for rec in records:
        cand = rec["candidate"]
        dim = str(cand.get("structural_dimensionality"))
        slot = by_dim.setdefault(dim, {"total": 0, "promoted": 0})
        slot["total"] += 1
        mode = rec.get("primary_failure_mode")
        if mode is None:
            slot["promoted"] += 1
            continue
        if mode == "BANDGAP_OUT_OF_WINDOW" and (rec.get("electronics") or {}).get("gap_basis") == "HEURISTIC":
            mode = "BANDGAP_OUT_OF_WINDOW_ESTIMATED"
        reg = GATE_REGISTRY.get(mode)
        if reg is None:
            if mode not in unregistered:
                unregistered.append(mode)
            reg = {"tier": "UNREGISTERED", "may_reject": False, "replace_with": None, "owner": None, "basis": ""}
        g = gates.setdefault(mode, {
            "tier": reg["tier"], "may_reject": reg["may_reject"], "replace_with": reg["replace_with"],
            "owner": reg["owner"], "basis": reg["basis"],
            "rejected": 0, "rejected_experimentally_known": 0, "known_ids": [],
        })
        g["rejected"] += 1
        if cand.get("is_experimentally_known"):
            g["rejected_experimentally_known"] += 1
            g["known_ids"].append(cand["candidate_id"])
            if mode in INSTABILITY_MODES:
                contradictions.append(cand["candidate_id"])

    rejected_total = sum(g["rejected"] for g in gates.values())
    weak = sum(g["rejected"] for g in gates.values() if not g["may_reject"])
    return {
        "candidates": len(records),
        "gates": dict(sorted(gates.items())),
        "unregistered_modes": sorted(unregistered),
        "rejected_total": rejected_total,
        "rejected_on_weak_evidence": weak,
        "known_phases_rejected_as_unstable": sorted(contradictions),
        "by_dimensionality": dict(sorted(by_dim.items())),
    }


# ---------------------------------------------------------------- 2. window analysis

def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def window_probability_ceiling(width_ev: float, sigma_ev: float) -> float:
    """Best possible probability that the true gap is inside a window of this width.

    It is reached when the estimate sits at the centre of the window, with a normal error
    of standard deviation sigma_ev: 2 * Phi(width / (2 * sigma)) - 1.
    """
    if width_ev <= 0 or sigma_ev <= 0:
        raise ValueError("width_ev and sigma_ev must be positive")
    return 2.0 * _phi(width_ev / (2.0 * sigma_ev)) - 1.0


def tandem_curve(
    gaps_ev: Sequence[float],
    eps_inf: float = 9.0,
    thickness_nm: float = 260.0,
) -> List[Dict[str, float]]:
    """Top-cell and filtered-silicon efficiency against top-cell gap, from the repository's
    own two-layer (top cell on silicon, four-terminal) model.

    The model is idealised: radiative voltage, direct gap equal to the indirect gap, a
    closed-form absorption coefficient. Use it for the shape of the curve, not the values.
    """
    from .kinetics_and_optics import compute_4t_tandem_optics_wavelength_grid

    out: List[Dict[str, float]] = []
    for eg in gaps_ev:
        r = compute_4t_tandem_optics_wavelength_grid(
            "TOP_ACTIVE_GLASS_185EV", float(eg), float(eg), float(eps_inf), float(thickness_nm)
        )
        top = float(r["top_cell_eff_percent"])
        total = float(r["tandem_2layer_si_eff_percent"])
        out.append({"gap_ev": round(float(eg), 4), "top_pct": top, "si_filtered_pct": round(total - top, 4)})
    return out


def derive_top_window(
    quality: float = 1.0,
    tolerance_abs_pct: Optional[float] = None,
    gap_min_ev: float = 1.20,
    gap_max_ev: float = 2.60,
    step_ev: float = 0.01,
    curve: Optional[List[Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Gap range in which the two-layer tandem is within a tolerance of its best value.

    quality: the top cell's efficiency as a fraction of its modelled limit (1.0 is the
        idealised cell). The silicon cell underneath does not depend on it, so
        total(gap) = quality * top(gap) + si_filtered(gap).
    Returns the best gap, the window and whether the window touches the scanned range
    (in which case the true window is wider than reported).
    """
    if not 0.0 < quality <= 1.0:
        raise ValueError("quality must be in (0, 1]")
    tol = float(RULES_V["window_tolerance_abs_pct"] if tolerance_abs_pct is None else tolerance_abs_pct)
    if curve is None:
        n = int(round((gap_max_ev - gap_min_ev) / step_ev)) + 1
        curve = tandem_curve([gap_min_ev + i * step_ev for i in range(n)])
    totals = [quality * p["top_pct"] + p["si_filtered_pct"] for p in curve]
    best_i = max(range(len(curve)), key=lambda i: totals[i])
    lo_i = best_i
    while lo_i > 0 and totals[lo_i - 1] >= totals[best_i] - tol:
        lo_i -= 1
    hi_i = best_i
    while hi_i < len(curve) - 1 and totals[hi_i + 1] >= totals[best_i] - tol:
        hi_i += 1
    return {
        "quality": quality,
        "tolerance_abs_pct": tol,
        "best_gap_ev": curve[best_i]["gap_ev"],
        "best_total_pct": round(totals[best_i], 2),
        "window_ev": (curve[lo_i]["gap_ev"], curve[hi_i]["gap_ev"]),
        "window_width_ev": round(curve[hi_i]["gap_ev"] - curve[lo_i]["gap_ev"], 4),
        "touches_scan_limit": lo_i == 0 or hi_i == len(curve) - 1,
        "provenance": "COMPUTED_HERE from an idealised model; the shape is informative, the values are not",
    }


# ---------------------------------------------------------------- 3. calculation queue

_CLASS_ORDER = {"CALCULATE_FIRST": 0, "CALCULATE_NEXT": 1, "PARK": 2}


def relative_cost(nsites: int, exponent: Optional[float] = None, reference_sites: Optional[int] = None) -> float:
    """Cost of a hybrid-functional calculation relative to a cell of reference_sites sites."""
    if nsites <= 0:
        raise ValueError("nsites must be positive")
    e = float(RULES_V["cost_exponent"] if exponent is None else exponent)
    ref = int(RULES_V["cost_reference_sites"] if reference_sites is None else reference_sites)
    return (float(nsites) / float(ref)) ** e


def queue_priority(window_probability: float, nsites: int, exponent: Optional[float] = None) -> float:
    """Expected in-window results per unit of compute: probability divided by relative cost.

    While every window probability is below 0.5, the entry with the highest probability is
    also the one whose calculation is most informative, so dividing by cost is the only
    refinement that changes the order.
    """
    if not 0.0 <= window_probability <= 1.0:
        raise ValueError("window_probability must be in [0, 1]")
    return window_probability / relative_cost(nsites, exponent)


def order_queue(rows: Iterable[Dict[str, Any]], exponent: Optional[float] = None) -> List[Dict[str, Any]]:
    """Order rows by queue class, then by priority (highest first), then by candidate id.

    Each row needs candidate_id, window_probability, nsites and, optionally, queue_class
    (missing means CALCULATE_NEXT). Returns new rows with relative_cost, queue_priority,
    cumulative_cost and cumulative_expected_hits added.
    """
    enriched = []
    for r in rows:
        cls = r.get("queue_class") or "CALCULATE_NEXT"
        if cls not in _CLASS_ORDER:
            raise ValueError(f"unknown queue_class {cls!r}")
        cost = relative_cost(int(r["nsites"]), exponent)
        enriched.append({**r, "queue_class": cls, "relative_cost": round(cost, 4),
                         "queue_priority": round(float(r["window_probability"]) / cost, 6)})
    enriched.sort(key=lambda r: (_CLASS_ORDER[r["queue_class"]], -r["queue_priority"], str(r["candidate_id"])))
    cum_cost = 0.0
    cum_hits = 0.0
    for r in enriched:
        cum_cost += r["relative_cost"]
        cum_hits += float(r["window_probability"])
        r["cumulative_cost"] = round(cum_cost, 4)
        r["cumulative_expected_hits"] = round(cum_hits, 4)
    return enriched


def fit_cost_exponent(timings: Sequence[Tuple[int, float]]) -> Dict[str, Any]:
    """Least-squares slope of log(wall time) against log(number of sites).

    timings: (nsites, wall_seconds) for runs at the same level of theory. Needs at least
    5 runs covering at least a factor of two in nsites.
    """
    pts = [(int(n), float(t)) for n, t in timings if n > 0 and t > 0]
    if len(pts) < 5:
        raise ValueError("need at least 5 timed runs")
    ns = [n for n, _ in pts]
    if max(ns) < 2 * min(ns):
        raise ValueError("runs must cover at least a factor of two in nsites")
    xs = [math.log(n) for n, _ in pts]
    ys = [math.log(t) for _, t in pts]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return {"exponent": round(slope, 3), "runs": len(pts), "nsites_range": (min(ns), max(ns)),
            "provenance": "COMPUTED_HERE"}


def queue_from_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ordered queue for the current run: shortlist rows with an estimated gap, with the
    queue class from the scorecards."""
    from . import failure_evidence as fe

    classes = {c["candidate_id"]: c["queue_class"] for c in fe.build_scorecards(summary)}
    rows = [
        {**r, "queue_class": classes.get(r["candidate_id"], "CALCULATE_NEXT")}
        for r in summary["ranked_shortlist"]["not_excluded"]
        if r["gap_basis"] == "HEURISTIC"
    ]
    return order_queue(rows)


# ---------------------------------------------------------------- 4. temperature

def voc_temperature_coefficient(
    eg0_ev: float,
    voc_v: float,
    temp_k: float = 298.15,
    gamma: Optional[float] = None,
) -> Dict[str, float]:
    """Temperature coefficient of the open-circuit voltage from the voltage deficit.

        dVoc/dT = -(Eg0/q - Voc + gamma * k * T / q) / T

    eg0_ev: band gap linearly extrapolated to 0 K. If only the room-temperature gap is
        known, pass it and tag the result ASSUMED: the gap usually shrinks on heating, so
        this understates the size of the coefficient.
    voc_v: open-circuit voltage at temp_k.
    Source: M. A. Green, Prog. Photovolt. 11, 333 (2003); O. Dupre et al., Sol. Energy
    Mater. Sol. Cells 140, 92 (2015), eq. 18.

    A cell with a larger deficit (Eg0/q - Voc) loses more voltage per kelvin, whatever its
    gap. A wide-gap cell with a poor voltage is therefore worse than silicon, not better.
    """
    if voc_v <= 0 or temp_k <= 0:
        raise ValueError("voc_v and temp_k must be positive")
    if voc_v >= eg0_ev:
        raise ValueError("voc_v must be below eg0_ev")
    g = float(RULES_V["voc_gamma"] if gamma is None else gamma)
    dvoc_dt = -(eg0_ev - voc_v + g * KB_EV_PER_K * temp_k) / temp_k
    return {
        "dvoc_dt_mv_per_k": round(1000.0 * dvoc_dt, 4),
        "relative_pct_per_k": round(100.0 * dvoc_dt / voc_v, 4),
        "voltage_deficit_v": round(eg0_ev - voc_v, 4),
        "gamma": g,
    }


def rule_of_thumb_relative_pct_per_k(gap_ev: float) -> float:
    """The pipeline's existing efficiency temperature coefficient, -0.44 / Eg**0.65 percent
    per kelvin. HEURISTIC: it depends on the gap only and ignores the voltage deficit."""
    return -0.44 / (gap_ev ** 0.65)


def top_cell_temperature_report(gap_ev: float, temp_k: float = 298.15) -> Dict[str, Any]:
    """Voltage temperature coefficient of a top cell with this gap, if its voltage deficit
    equals that of the best related cell on record (RULES_V["reference_voltage_deficit_v"]).

    The room-temperature gap stands in for the 0 K gap (ASSUMED), which makes the result
    slightly optimistic. Adds the flag TEMPERATURE_RULE_OPTIMISTIC when the pipeline's
    rule of thumb predicts a smaller loss than the deficit formula.
    """
    deficit = float(RULES_V["reference_voltage_deficit_v"])
    if gap_ev <= deficit:
        raise ValueError("gap_ev must exceed the reference voltage deficit")
    coeff = voc_temperature_coefficient(gap_ev, gap_ev - deficit, temp_k=temp_k)
    thumb = rule_of_thumb_relative_pct_per_k(gap_ev)
    flags = ["TEMPERATURE_RULE_OPTIMISTIC"] if coeff["relative_pct_per_k"] < thumb else []
    return {
        "top_cell_voc_temp_coeff_from_deficit_mv_per_k": coeff["dvoc_dt_mv_per_k"],
        "top_cell_voc_temp_coeff_from_deficit_rel_pct_per_k": coeff["relative_pct_per_k"],
        "rule_of_thumb_rel_pct_per_k": round(thumb, 4),
        "assumed_voltage_deficit_v": deficit,
        "temperature_flags": flags,
    }


# ---------------------------------------------------------------- 5. contact alignment

def classify_band_offset(
    offset_ev: Optional[float],
    sigma_ev: Optional[float],
    ok_low_ev: Optional[float] = None,
    ok_high_ev: Optional[float] = None,
) -> str:
    """Classify a conduction-band offset (transport layer minus absorber) given its error.

    Returns one of
        NOT_EVALUATED   no offset or no error estimate
        IN_RANGE        the whole interval offset +/- sigma lies inside [ok_low, ok_high]
        CLIFF           the whole interval lies below ok_low (voltage loss at the interface)
        BARRIER         the whole interval lies above ok_high (blocks photocurrent)
        UNRESOLVED      the interval straddles a limit: the estimate cannot tell
    An estimate whose error is as large as the acceptable range can only return
    UNRESOLVED, which is the honest answer.
    """
    if offset_ev is None or sigma_ev is None:
        return "NOT_EVALUATED"
    if sigma_ev < 0:
        raise ValueError("sigma_ev must not be negative")
    lo = float(RULES_V["offset_ok_low_ev"] if ok_low_ev is None else ok_low_ev)
    hi = float(RULES_V["offset_ok_high_ev"] if ok_high_ev is None else ok_high_ev)
    a, b = offset_ev - sigma_ev, offset_ev + sigma_ev
    if a >= lo and b <= hi:
        return "IN_RANGE"
    if b < lo:
        return "CLIFF"
    if a > hi:
        return "BARRIER"
    return "UNRESOLVED"


# ---------------------------------------------------------------- command line

def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else ""
    if cmd == "audit":
        print(json.dumps(gate_audit(load_summary()), indent=2))
        return 0
    if cmd == "window":
        n = int(round((2.60 - 1.20) / 0.01)) + 1
        curve = tandem_curve([1.20 + i * 0.01 for i in range(n)])
        rows = [derive_top_window(quality=q, curve=curve) for q in (1.0, 0.75, 0.6, 0.5)]
        ceilings = {
            f"{w:.2f}": {f"{s:.2f}": round(window_probability_ceiling(w, s), 3) for s in (0.44, 0.36, 0.25, 0.10)}
            for w in (0.20, 0.30, 0.45, 0.60)
        }
        print(json.dumps({"windows_by_quality": rows, "probability_ceiling_by_width_and_sigma": ceilings}, indent=2))
        return 0
    if cmd == "queue":
        keep = ("candidate_id", "formula_reduced", "queue_class", "window_probability", "nsites",
                "relative_cost", "queue_priority", "cumulative_cost", "cumulative_expected_hits")
        print(json.dumps([{k: r.get(k) for k in keep} for r in queue_from_summary(load_summary())], indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
