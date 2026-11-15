"""Failure evidence: what failed syntheses and failed devices say about a candidate.

Standalone module. It reads committed data and the pipeline's summary file; it does not
change pipeline decisions. Everything it produces is a flag or a ranking aid, never a
rejection (see docs/MATERIAL_EVALUATION_RULES.md for why).

Three parts:

1. Synthesis evidence from published solid-state recipes
   (`data/negative_synthesis_priors.json`): impurity rate for the candidate's chemical
   system with a credible interval, shrunk toward related systems when data are thin.
2. Device evidence from analog materials (`data/device_failure_records.csv`):
   why the nearest studied relatives underperform, with citations.
3. Scorecards: one four-axis card per shortlist entry (effective, cost, stable,
   synthesizable), each axis with an evidence tier and flags, plus a queue class.

Commands:

    python -m failsmart_matengine.failure_evidence ablation     # does the recipe data predict anything?
    python -m failsmart_matengine.failure_evidence scorecards   # write outputs/material_scorecards.{json,md}
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
PRIORS_JSON = _REPO_ROOT / "data" / "negative_synthesis_priors.json"
DEVICE_CSV = _REPO_ROOT / "data" / "device_failure_records.csv"
ABLATION_JSON = _REPO_ROOT / "data" / "failure_ablation.json"
SUMMARY_JSON = _REPO_ROOT / "outputs" / "live_mp_discovery_summary.json"
SCORECARDS_JSON = _REPO_ROOT / "outputs" / "material_scorecards.json"
SCORECARDS_MD = _REPO_ROOT / "outputs" / "material_scorecards.md"

CHALCOGENS = frozenset({"S", "Se", "Te"})
HALOGENS = frozenset({"Cl", "Br", "I"})
PNICTOGENS = frozenset({"Bi", "Sb"})
COINAGE = frozenset({"Cu", "Ag"})

# Judgement thresholds (ASSUMED). Change them here, not in the logic below.
RULES: Dict[str, Any] = {
    # Strength of the shrinkage prior, in pseudo-recipes
    "prior_strength_recipes": 4.0,
    # Flag a synthesis risk only if the lower end of the 90% interval is above this
    "impurity_flag_lower_bound": 0.50,
    # Elements that raise cost or supply risk for terawatt-scale use
    "critical_elements": ("In", "Ga", "Ge", "Te", "Ag"),
    # Hull distance bands (meV/atom) for the stability axis
    "hull_on_mev": 1.0,
    "hull_near_mev": 25.0,
    # Cell size above which a hybrid-functional calculation is slow on a workstation
    "large_cell_sites": 24,
    # Process ceiling for coating on soda-lime glass
    "glass_limit_c": 500.0,
}

# Evidence tiers, lowest to highest. An axis may only exclude a candidate at tier 3 or above.
TIERS = (
    "T0_NOT_EVALUATED",
    "T1_HEURISTIC",
    "T2_ANALOGY",
    "T3_DATABASE_DFT_OR_ML_POTENTIAL",
    "T4_COMPUTED_HERE",
    "T5_MEASURED",
)


# ----------------------------------------------------------------------------
# 1. Synthesis evidence
# ----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _systems() -> Dict[FrozenSet[str], Dict[str, Any]]:
    raw = json.loads(PRIORS_JSON.read_text(encoding="utf-8"))["chemsys_impurity_priors"]
    out: Dict[FrozenSet[str], Dict[str, Any]] = {}
    for key, v in raw.items():
        n_pure, n_imp = int(v.get("pure_count") or 0), int(v.get("impure_count") or 0)
        if n_pure + n_imp == 0:
            continue
        out[frozenset(key.split("-"))] = {
            "pure": n_pure,
            "impure": n_imp,
            "median_temp_c": v.get("median_temp_c"),
            "top_impurities": [s for s in (v.get("top_impurities") or []) if s and s.lower() != "unknown"],
        }
    return out


@lru_cache(maxsize=1)
def _neighbour_index() -> Dict[FrozenSet[str], List[FrozenSet[str]]]:
    """Map each (k-1)-element subset, and each system itself, to the systems that contain it."""
    idx: Dict[FrozenSet[str], List[FrozenSet[str]]] = {}
    for sysm in _systems():
        idx.setdefault(sysm, []).append(sysm)
        if len(sysm) > 1:
            for sub in itertools.combinations(sorted(sysm), len(sysm) - 1):
                idx.setdefault(frozenset(sub), []).append(sysm)
    return idx


def _anion_class(elements: Iterable[str]) -> str:
    els = set(elements)
    if els & CHALCOGENS:
        return "chalcogenide"
    if "O" in els:
        return "oxide"
    return "other"


@lru_cache(maxsize=1)
def _class_totals() -> Dict[str, Tuple[int, int]]:
    tot: Dict[str, List[int]] = {}
    for sysm, v in _systems().items():
        t = tot.setdefault(_anion_class(sysm), [0, 0])
        t[0] += v["impure"]
        t[1] += v["pure"] + v["impure"]
    return {k: (a, b) for k, (a, b) in tot.items()}


def _related_rate(target: FrozenSet[str]) -> Tuple[Optional[float], int, str]:
    """Pooled impurity rate of related systems, excluding the target itself.

    Related means: shares all but one element with the target and is no larger than it.
    Falls back to the anion class (chalcogenide, oxide, other), then to nothing.
    """
    idx, systems = _neighbour_index(), _systems()
    seen: set = set()
    imp = n = 0
    subsets = [frozenset(s) for s in itertools.combinations(sorted(target), max(1, len(target) - 1))]
    for sub in subsets:
        for other in idx.get(sub, []):
            if other == target or other in seen or len(other) > len(target):
                continue
            seen.add(other)
            imp += systems[other]["impure"]
            n += systems[other]["pure"] + systems[other]["impure"]
    if n >= 5:
        return imp / n, n, "related chemical systems"
    c_imp, c_n = _class_totals().get(_anion_class(target), (0, 0))
    own = systems.get(target)
    if own:
        c_imp, c_n = c_imp - own["impure"], c_n - own["pure"] - own["impure"]
    if c_n > 0:
        return c_imp / c_n, c_n, f"all {_anion_class(target)} systems"
    return None, 0, "none"


def _beta_interval(a: float, b: float, level: float = 0.90) -> Tuple[float, float]:
    from scipy.stats import beta

    lo, hi = beta.ppf([(1 - level) / 2, 1 - (1 - level) / 2], a, b)
    return float(lo), float(hi)


def synthesis_evidence(elements: Sequence[str]) -> Dict[str, Any]:
    """Impurity-rate evidence for a chemical system from published solid-state recipes.

    Returns the raw counts, a shrunk estimate with a 90% credible interval, the named
    impurity phases, an evidence grade and (rarely) a risk flag. Never a rejection.
    Provenance: LITERATURE (counts), COMPUTED_HERE (estimate and interval).
    """
    target = frozenset(elements)
    own = _systems().get(target)
    n_imp = own["impure"] if own else 0
    n = (own["pure"] + own["impure"]) if own else 0
    prior_rate, prior_n, prior_basis = _related_rate(target)

    k = float(RULES["prior_strength_recipes"]) if prior_rate is not None else 0.0
    if n == 0 and prior_rate is None:
        estimate, interval = None, None
    else:
        # Beta posterior: own counts + shrinkage prior + a Jeffreys half-count on each side,
        # so a prior built from a few all-pure or all-impure neighbours cannot give a zero-width interval
        a = n_imp + (prior_rate or 0.0) * k + 0.5
        b = (n - n_imp) + (1.0 - (prior_rate or 0.0)) * k + 0.5
        estimate = a / (a + b)
        interval = _beta_interval(a, b)

    grade = "none" if n == 0 else "weak" if n < 5 else "moderate" if n < 20 else "strong"
    flags: List[str] = []
    if interval and grade in ("moderate", "strong") and interval[0] > float(RULES["impurity_flag_lower_bound"]):
        flags.append("SYNTHESIS_IMPURITY_RISK")
    temp = own.get("median_temp_c") if own else None
    if temp is not None and float(temp) > float(RULES["glass_limit_c"]):
        flags.append("REPORTED_ROUTES_ABOVE_GLASS_LIMIT")

    return {
        "chemical_system": "-".join(sorted(target)),
        "recipes": n,
        "impure_recipes": n_imp,
        "raw_impurity_rate": round(n_imp / n, 4) if n else None,
        "estimated_impurity_rate": round(estimate, 4) if estimate is not None else None,
        "estimate_basis": "no data" if estimate is None else ("related systems only" if n == 0 else "own recipes shrunk toward related systems"),
        "interval_90": [round(interval[0], 4), round(interval[1], 4)] if interval else None,
        "prior_rate": round(prior_rate, 4) if prior_rate is not None else None,
        "prior_basis": prior_basis,
        "prior_recipes": prior_n,
        "median_reported_temp_c": temp,
        "likely_impurity_phases": (own or {}).get("top_impurities", [])[:4],
        "evidence_grade": grade,
        "flags": flags,
        "caveat": "published solid-state powder recipes, mostly far above 500 C; weak proxy for thin-film growth",
    }


# ----------------------------------------------------------------------------
# Ablation: does the recipe data predict held-out systems?
# ----------------------------------------------------------------------------

def _score(pairs: List[Tuple[float, int, int]]) -> Dict[str, float]:
    """pairs = (predicted rate, impure, total). Recipe-weighted Brier score and log loss."""
    n_tot = sum(n for _, _, n in pairs)
    brier = sum(n * (p - i / n) ** 2 for p, i, n in pairs) / n_tot
    eps = 1e-3
    ll = -sum(
        i * math.log(min(1 - eps, max(eps, p))) + (n - i) * math.log(min(1 - eps, max(eps, 1 - p)))
        for p, i, n in pairs
    ) / n_tot
    return {"brier": round(brier, 5), "log_loss": round(ll, 5)}


def run_ablation(min_recipes: int = 5) -> Dict[str, Any]:
    """Leave-one-system-out test of three predictors of a system's impurity rate.

    Predictors: the global rate, the anion-class rate, and the pooled rate of related
    systems (the prior used by `synthesis_evidence`). Scored on every system with at
    least `min_recipes` recipes, and on the chalcogenide subset.
    """
    systems = _systems()
    g_imp = sum(v["impure"] for v in systems.values())
    g_n = sum(v["pure"] + v["impure"] for v in systems.values())
    cls = _class_totals()

    rows: Dict[str, Dict[str, List[Tuple[float, int, int]]]] = {
        "all": {"global": [], "anion_class": [], "related": []},
        "chalcogenide": {"global": [], "anion_class": [], "related": []},
    }
    used_related = 0
    for sysm, v in systems.items():
        n, i = v["pure"] + v["impure"], v["impure"]
        if n < min_recipes:
            continue
        p_global = (g_imp - i) / (g_n - n)
        c_imp, c_n = cls[_anion_class(sysm)]
        p_class = (c_imp - i) / (c_n - n) if c_n > n else p_global
        p_rel, _, basis = _related_rate(sysm)
        if basis == "related chemical systems":
            used_related += 1
        p_rel = p_rel if p_rel is not None else p_global
        for subset in ("all", "chalcogenide"):
            if subset == "chalcogenide" and _anion_class(sysm) != "chalcogenide":
                continue
            rows[subset]["global"].append((p_global, i, n))
            rows[subset]["anion_class"].append((p_class, i, n))
            rows[subset]["related"].append((p_rel, i, n))

    out: Dict[str, Any] = {
        "method": "leave-one-chemical-system-out; recipe-weighted Brier score and log loss (lower is better)",
        "min_recipes": min_recipes,
        "data": "data/negative_synthesis_priors.json",
        "total_systems": len(systems),
        "total_recipes": g_n,
        "global_impurity_rate": round(g_imp / g_n, 4),
        "class_impurity_rate": {k: round(a / b, 4) for k, (a, b) in cls.items()},
        "class_recipes": {k: b for k, (_, b) in cls.items()},
        "systems_scored_with_related_prior": used_related,
        "provenance": "COMPUTED_HERE on LITERATURE counts",
    }
    import numpy as np

    rng = np.random.default_rng(20261115)
    for subset, preds in rows.items():
        n_sys = len(preds["global"])
        res = {name: _score(p) for name, p in preds.items()}
        base = res["global"]["brier"]
        # Bootstrap over chemical systems for the improvement of the related-systems predictor
        boots = []
        for _ in range(2000):
            pick = rng.integers(0, n_sys, n_sys)
            b_glob = _score([preds["global"][j] for j in pick])["brier"]
            b_rel = _score([preds["related"][j] for j in pick])["brier"]
            boots.append(100.0 * (b_glob - b_rel) / b_glob)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[subset] = {
            "systems": n_sys,
            "recipes": sum(n for _, _, n in preds["global"]),
            **res,
            "related_brier_improvement_vs_global_percent": round(100.0 * (base - res["related"]["brier"]) / base, 2),
            "improvement_bootstrap_95_percent": [round(float(lo), 2), round(float(hi), 2)],
        }
    return out


# ----------------------------------------------------------------------------
# 2. Device evidence from analog materials
# ----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def device_records() -> List[Dict[str, Any]]:
    with open(DEVICE_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["value"] = float(r["value"])
    return rows


def material_family(elements: Iterable[str]) -> Optional[str]:
    """Family used to look up analog device records. None if no studied relatives are on file."""
    els = set(elements)
    if not (els & PNICTOGENS) or not (els & CHALCOGENS):
        return None
    if els & HALOGENS:
        return "PNICTOGEN_CHALCOHALIDE"
    if els & COINAGE:
        return "COINAGE_PNICTOGEN_CHALCOGENIDE"
    return "PNICTOGEN_CHALCOGENIDE"


def analog_device_evidence(elements: Sequence[str]) -> Dict[str, Any]:
    """What is known about why the nearest studied relatives underperform.

    This is evidence by analogy (tier T2). It produces flags and context, never a rejection.
    """
    fam = material_family(elements)
    recs = [r for r in device_records() if r["family"] == fam] if fam else []
    eff = [r["value"] for r in recs if r["finding_type"] in ("record_efficiency", "certified_efficiency")]
    lim = [r["value"] for r in recs if r["finding_type"] == "theoretical_efficiency_limit"]
    mechanisms = sorted({r["mechanism_class"] for r in recs})
    flags = [f"ANALOG_{m}" for m in mechanisms]
    return {
        "family": fam,
        "records": [r["record_id"] for r in recs],
        "best_analog_efficiency_percent": max(eff) if eff else None,
        "lowest_analog_theoretical_limit_percent": min(lim) if lim else None,
        "analog_mechanisms": mechanisms,
        "flags": flags,
        "sources": sorted({r["source_doi"] or r["source_url"] for r in recs}),
        "basis": "analogy to studied relatives (LITERATURE records; the inference is not a measurement of this material)",
    }


# ----------------------------------------------------------------------------
# 3. Scorecards
# ----------------------------------------------------------------------------

def _gap_tier(basis: str) -> str:
    return {"LITERATURE": TIERS[5], "COMPUTED_HERE": TIERS[4], "HEURISTIC": TIERS[1]}.get(basis, TIERS[0])


def scorecard(dossier: Dict[str, Any], shortlist_row: Dict[str, Any]) -> Dict[str, Any]:
    """Four-axis evaluation of one shortlist entry. See docs/MATERIAL_EVALUATION_RULES.md."""
    cand, elec = dossier["candidate"], dossier["electronics"]
    synth = dossier.get("synthesis") or {}
    elements = list(cand["elements"])
    known = bool(shortlist_row["is_experimentally_known"])
    hull = float(shortlist_row["e_above_hull_mev"])
    nsites = int(shortlist_row["nsites"])

    syn = synthesis_evidence(elements)
    dev = analog_device_evidence(elements)
    critical = [e for e in elements if e in RULES["critical_elements"]]

    # Effective: is the gap right, and what do relatives achieve?
    eff_flags = list(dev["flags"])
    if elec["gap_basis"] == "HEURISTIC":
        eff_flags.append("GAP_IS_AN_ESTIMATE")
    effective = {
        "tier": _gap_tier(elec["gap_basis"]),
        "gap_ev": elec["gap_est_indirect_ev"],
        "gap_sigma_ev": elec["gap_error_bar_ev"],
        "window_probability": elec["window_probability"],
        "best_analog_efficiency_percent": dev["best_analog_efficiency_percent"],
        "lowest_analog_theoretical_limit_percent": dev["lowest_analog_theoretical_limit_percent"],
        "flags": eff_flags,
    }

    # Cost: raw active-layer cost is negligible; element criticality is what matters at scale
    cost = {
        "tier": TIERS[4],
        "active_layer_cost_usd_m2": synth.get("active_layer_cost_usd_m2"),
        "critical_elements": critical,
        "flags": ["CRITICAL_ELEMENTS"] if critical else [],
    }

    # Stable: hull distance from the database; relatives' decomposition as analogy
    stab_flags: List[str] = []
    if hull > RULES["hull_near_mev"]:
        stab_flags.append("FAR_FROM_HULL")
    if "ANALOG_THERMAL_DECOMPOSITION" in dev["flags"]:
        stab_flags.append("ANALOG_THERMAL_DECOMPOSITION")
    stable = {
        "tier": TIERS[3],
        "e_above_hull_mev": hull,
        "hull_band": "on" if hull <= RULES["hull_on_mev"] else "near" if hull <= RULES["hull_near_mev"] else "far",
        "flags": stab_flags,
    }

    # Synthesizable: has it been made, and what do recipes for this chemistry say?
    synthesizable = {
        "tier": TIERS[5] if known else (TIERS[2] if syn["recipes"] else TIERS[0]),
        "experimentally_known_phase": known,
        "recipes_in_system": syn["recipes"],
        "estimated_impurity_rate": syn["estimated_impurity_rate"],
        "estimate_basis": syn["estimate_basis"],
        "interval_90": syn["interval_90"],
        "likely_impurity_phases": syn["likely_impurity_phases"],
        "evidence_grade": syn["evidence_grade"],
        "flags": syn["flags"] + ([] if known else ["NEVER_SYNTHESISED"]),
    }

    # Queue class (rules R5 to R7 in the guide)
    if known and not critical and hull <= RULES["hull_near_mev"]:
        queue_class = "CALCULATE_FIRST"
        reason = "synthesised phase, no critical elements, on or near the hull"
    elif not critical and hull <= RULES["hull_near_mev"] and nsites <= RULES["large_cell_sites"]:
        queue_class = "CALCULATE_NEXT"
        reason = "never synthesised, but no critical elements, near the hull and a small cell"
    else:
        queue_class = "PARK"
        why = []
        if critical:
            why.append("critical elements " + ", ".join(critical))
        if hull > RULES["hull_near_mev"]:
            why.append("far from the hull")
        if nsites > RULES["large_cell_sites"] and not known:
            why.append("large cell and never synthesised")
        reason = "; ".join(why) or "does not meet the first two classes"

    return {
        "candidate_id": cand["candidate_id"],
        "formula_reduced": cand["formula_reduced"],
        "target_layer": cand["target_layer"],
        "queue_class": queue_class,
        "queue_reason": reason,
        "nsites": nsites,
        "effective": effective,
        "cost": cost,
        "stable": stable,
        "synthesizable": synthesizable,
        "analog_family": dev["family"],
        "analog_records": dev["records"],
    }


_CLASS_ORDER = {"CALCULATE_FIRST": 0, "CALCULATE_NEXT": 1, "PARK": 2}


def build_scorecards(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scorecards for every shortlist entry, ordered by queue class, then window probability."""
    by_id = {d["candidate"]["candidate_id"]: d for d in summary["finalists"]}
    cards = [scorecard(by_id[row["candidate_id"]], row) for row in summary["ranked_shortlist"]["not_excluded"]]
    cards.sort(key=lambda c: (_CLASS_ORDER[c["queue_class"]], -c["effective"]["window_probability"], c["nsites"]))
    return cards


def summary_digest(path: Path = SUMMARY_JSON) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_scorecards_markdown(cards: List[Dict[str, Any]], digest: str) -> str:
    lines = [
        "# Material scorecards (generated)",
        "",
        "Generated by `python -m failsmart_matengine.failure_evidence scorecards` from",
        f"`outputs/live_mp_discovery_summary.json` (sha256 `{digest[:16]}`). Do not edit by hand.",
        "Rules and tiers: `docs/MATERIAL_EVALUATION_RULES.md`.",
        "",
        "| Class | ID | Formula | Layer | Gap (eV) | P(window) | Made before | Hull (meV) | Critical | Recipes | Impurity rate (90%) | Analog best / limit (%) | Flags |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in cards:
        e, s, st, co = c["effective"], c["synthesizable"], c["stable"], c["cost"]
        iv = s["interval_90"]
        rate = "no data" if s["estimated_impurity_rate"] is None else (
            f"{s['estimated_impurity_rate']:.2f} ({iv[0]:.2f} to {iv[1]:.2f})"
            + (" from related systems only" if s["recipes_in_system"] == 0 else "")
        )
        analog = "none on file" if c["analog_family"] is None else (
            f"{e['best_analog_efficiency_percent'] if e['best_analog_efficiency_percent'] is not None else '-'} / "
            f"{e['lowest_analog_theoretical_limit_percent'] if e['lowest_analog_theoretical_limit_percent'] is not None else '-'}"
        )
        flags = sorted(set(e["flags"] + s["flags"] + st["flags"] + co["flags"]))
        lines.append(
            f"| {c['queue_class']} | {c['candidate_id']} | {c['formula_reduced']} | "
            f"{'top' if c['target_layer'].startswith('TOP') else 'bottom'} | "
            f"{e['gap_ev']:.2f} +/- {e['gap_sigma_ev']:.2f} | {e['window_probability']:.2f} | "
            f"{'yes' if s['experimentally_known_phase'] else 'no'} | {st['e_above_hull_mev']:.1f} | "
            f"{', '.join(co['critical_elements']) or '-'} | {s['recipes_in_system']} | {rate} | {analog} | "
            f"{', '.join(flags) or '-'} |"
        )
    return "\n".join(lines) + "\n"


def write_scorecards() -> Dict[str, Any]:
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    digest = summary_digest()
    cards = build_scorecards(summary)
    payload = {
        "generated_from": "outputs/live_mp_discovery_summary.json",
        "summary_sha256": digest,
        "rules": RULES,
        "tiers": list(TIERS),
        "class_counts": {k: sum(1 for c in cards if c["queue_class"] == k) for k in _CLASS_ORDER},
        "scorecards": cards,
    }
    SCORECARDS_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    SCORECARDS_MD.write_text(render_scorecards_markdown(cards, digest), encoding="utf-8")
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else "scorecards"
    if cmd == "ablation":
        res = run_ablation()
        ABLATION_JSON.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(res, indent=2))
        return 0
    if cmd == "scorecards":
        payload = write_scorecards()
        print(json.dumps(payload["class_counts"], indent=2))
        print(f"Wrote {SCORECARDS_JSON.relative_to(_REPO_ROOT)} and {SCORECARDS_MD.relative_to(_REPO_ROOT)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
