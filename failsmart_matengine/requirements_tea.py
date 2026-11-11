"""Inverted Techno-Economic Requirements Model (`python -m failsmart_matengine.requirements_tea`).

States conditional engineering requirements (break-even top-cell efficiency, maximum allowable
added module cost per efficiency point, and degradation-rate sensitivity) rather than commercial
forecasts. Every parameter carries an explicit provenance tag (`ASSUMED` or `COMPUTED_HERE`).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from failsmart_matengine.schemas import ProvenanceTag

# =============================================================================
# Baseline Reference Parameters (tagged ASSUMED from Section 11.3 & Audit)
# =============================================================================
SI_MONOFACIAL_REFERENCE_PCE_PCT: float = 24.50
SI_SUBGAP_CURRENT_FRACTION_COEFF_PCT: float = 13.10  # 24.5 - 13.1 * T optics-only break-even

PATH0_BIFACIAL_SI_EQUIV_POWER_MW_CM2: float = 26.6486
PATH0_SI_MODULE_COST_USD_M2: float = 42.00
UTILITY_BOS_AREA_COST_USD_M2: float = 100.00
ROOFTOP_BOS_AREA_COST_USD_M2: float = 240.00
POWER_SCALING_BOS_USD_PER_W: float = 0.22
ANNUAL_OM_USD_M2_YR: float = 2.50
DISCOUNT_RATE: float = 0.06
PROJECT_LIFETIME_YRS: int = 25
INSOLATION_KWH_M2_YR: float = 1800.0
NOCT_DERATING_2L: float = 0.930
SI_BASELINE_DEG_RATE: float = 0.0045
TANDEM_DEFAULT_DEG_RATE: float = 0.0050
DEFAULT_ADDED_MODULE_COST_2L_USD_M2: float = 23.88  # $65.88/m^2 - $42.00/m^2 in original utility model

# Filtered c-Si contribution in Path 2 (20% ground albedo):
# At reference sub-gap transmittance T_0 = 0.88, filtered c-Si delivers 14.78%
# (3.725% from unobstructed rear 20% albedo + 12.5625 * T from transmitted front sub-gap light).
SI_REAR_ALBEDO_20PCT_CONTRIB_MW_CM2: float = 3.725
SI_FRONT_SUBGAP_SLOPE_MW_CM2: float = 12.5625


def _discounted_om_usd_m2() -> float:
    return sum(
        ANNUAL_OM_USD_M2_YR / ((1.0 + DISCOUNT_RATE) ** t)
        for t in range(1, PROJECT_LIFETIME_YRS + 1)
    )


def _discounted_energy_per_pce_point(f_noct: float, deg_rate: float) -> float:
    """Discounted 25-year energy yield (kWh/m^2) per 1% (10 W/m^2) of front-irradiance-normalized output."""
    return sum(
        ((10.0 / 1000.0) * INSOLATION_KWH_M2_YR * f_noct * ((1.0 - deg_rate) ** (t - 1)))
        / ((1.0 + DISCOUNT_RATE) ** t)
        for t in range(1, PROJECT_LIFETIME_YRS + 1)
    )


def compute_lcoe_cents_kwh(
    equiv_power_mw_cm2: float,
    module_cost_usd_m2: float,
    bos_area_cost_usd_m2: float,
    f_noct: float = NOCT_DERATING_2L,
    deg_rate: float = TANDEM_DEFAULT_DEG_RATE,
) -> float:
    """Discounted 25-year LCOE (cents/kWh) matching `realistic_commercialization._compute_lcoe_11c_cents_kwh`."""
    p_m2 = 10.0 * equiv_power_mw_cm2
    capex_m2 = module_cost_usd_m2 + bos_area_cost_usd_m2 + POWER_SCALING_BOS_USD_PER_W * p_m2
    om_disc = _discounted_om_usd_m2()
    e_disc = equiv_power_mw_cm2 * _discounted_energy_per_pce_point(f_noct, deg_rate)
    return 100.0 * (capex_m2 + om_disc) / max(1e-9, e_disc)


def compute_optics_only_breakeven_top_pce(
    subgap_transmittance_fraction: float,
    si_baseline_pce_percent: float = SI_MONOFACIAL_REFERENCE_PCE_PCT,
    subgap_si_coeff_percent: float = SI_SUBGAP_CURRENT_FRACTION_COEFF_PCT,
) -> Dict[str, Any]:
    """Compute optics-only monofacial break-even top-cell efficiency: `24.5 - 13.1 * T` (%).

    Against a 24.5% monofacial silicon baseline, a ~1.8 eV top cell blocks the >1.8 eV half of
    silicon's photocurrent and transmits fraction `T` of sub-gap photons (1.12 <= E < 1.8 eV),
    leaving `13.1 * T` % from the silicon bottom cell.
    """
    t_clamped = max(0.0, min(1.0, float(subgap_transmittance_fraction)))
    filtered_si_pce = subgap_si_coeff_percent * t_clamped
    breakeven_top_pce = si_baseline_pce_percent - filtered_si_pce
    return {
        "formula": "24.5 - 13.1 * T",
        "subgap_transmittance_fraction": round(t_clamped, 4),
        "si_monofacial_baseline_pce_percent": round(si_baseline_pce_percent, 2),
        "filtered_si_bottom_pce_percent": round(filtered_si_pce, 3),
        "breakeven_top_cell_pce_percent": round(breakeven_top_pce, 3),
        "provenance": {
            "si_monofacial_baseline_pce_percent": ProvenanceTag.ASSUMED.value,
            "subgap_transmittance_fraction": ProvenanceTag.ASSUMED.value,
            "filtered_si_bottom_pce_percent": ProvenanceTag.COMPUTED_HERE.value,
            "breakeven_top_cell_pce_percent": ProvenanceTag.COMPUTED_HERE.value,
        },
    }


def compute_lcoe_breakeven_top_pce(
    subgap_transmittance_fraction: float = 0.88,
    added_module_cost_usd_m2: float = DEFAULT_ADDED_MODULE_COST_2L_USD_M2,
    case: str = "utility",
    deg_rate: float = TANDEM_DEFAULT_DEG_RATE,
) -> Dict[str, Any]:
    """Invert the 25-year LCOE equation to solve for break-even top-cell efficiency.

    At `subgap_transmittance_fraction = 0.88`, `added_module_cost_usd_m2 = 23.88` ($65.88 vs $42.00/m^2),
    and `deg_rate = 0.0050`:
    - Utility case (`$100/m^2` area BOS): break-even top-cell efficiency = `15.72%` (`~15.7%`).
    - Rooftop case (`$240/m^2` area BOS): break-even top-cell efficiency = `14.02%` (`~14.0%`).
    """
    bos_area = UTILITY_BOS_AREA_COST_USD_M2 if case.lower() == "utility" else ROOFTOP_BOS_AREA_COST_USD_M2
    lcoe_si_baseline = compute_lcoe_cents_kwh(
        equiv_power_mw_cm2=PATH0_BIFACIAL_SI_EQUIV_POWER_MW_CM2,
        module_cost_usd_m2=PATH0_SI_MODULE_COST_USD_M2,
        bos_area_cost_usd_m2=bos_area,
        f_noct=NOCT_DERATING_2L,
        deg_rate=SI_BASELINE_DEG_RATE,
    )

    c_mod_stack = PATH0_SI_MODULE_COST_USD_M2 + float(added_module_cost_usd_m2)
    om_disc = _discounted_om_usd_m2()
    e_unit = _discounted_energy_per_pce_point(NOCT_DERATING_2L, deg_rate)

    # Solve 100 * (c_mod_stack + bos_area + om_disc + 2.20 * eta_stack) / (eta_stack * e_unit) = lcoe_si_baseline
    denom = (lcoe_si_baseline / 100.0) * e_unit - 10.0 * POWER_SCALING_BOS_USD_PER_W
    eta_stack_breakeven = (c_mod_stack + bos_area + om_disc) / max(1e-9, denom)

    t_clamped = max(0.0, min(1.0, float(subgap_transmittance_fraction)))
    eta_si_filtered = SI_REAR_ALBEDO_20PCT_CONTRIB_MW_CM2 + SI_FRONT_SUBGAP_SLOPE_MW_CM2 * t_clamped
    eta_top_breakeven = eta_stack_breakeven - eta_si_filtered

    return {
        "case": case.lower(),
        "bos_area_cost_usd_m2": round(bos_area, 2),
        "subgap_transmittance_fraction": round(t_clamped, 4),
        "added_module_cost_usd_m2": round(float(added_module_cost_usd_m2), 2),
        "total_module_cost_usd_m2": round(c_mod_stack, 2),
        "annual_degradation_rate": round(deg_rate, 5),
        "baseline_si_lcoe_cents_kwh": round(lcoe_si_baseline, 3),
        "filtered_si_equiv_power_mw_cm2": round(eta_si_filtered, 2),
        "breakeven_stack_equiv_power_mw_cm2": round(eta_stack_breakeven, 2),
        "breakeven_top_cell_pce_percent": round(eta_top_breakeven, 2),
        "provenance": {
            "bos_area_cost_usd_m2": ProvenanceTag.ASSUMED.value,
            "added_module_cost_usd_m2": ProvenanceTag.ASSUMED.value,
            "annual_degradation_rate": ProvenanceTag.ASSUMED.value,
            "baseline_si_lcoe_cents_kwh": ProvenanceTag.COMPUTED_HERE.value,
            "breakeven_top_cell_pce_percent": ProvenanceTag.COMPUTED_HERE.value,
        },
    }


def compute_allowable_added_cost_per_eff_point(
    case: str = "utility",
    deg_rate: float = SI_BASELINE_DEG_RATE,
) -> Dict[str, Any]:
    """Compute maximum allowable added module cost (USD/m^2) per percentage point of stack output gain."""
    bos_area = UTILITY_BOS_AREA_COST_USD_M2 if case.lower() == "utility" else ROOFTOP_BOS_AREA_COST_USD_M2
    lcoe_si_baseline = compute_lcoe_cents_kwh(
        equiv_power_mw_cm2=PATH0_BIFACIAL_SI_EQUIV_POWER_MW_CM2,
        module_cost_usd_m2=PATH0_SI_MODULE_COST_USD_M2,
        bos_area_cost_usd_m2=bos_area,
        f_noct=NOCT_DERATING_2L,
        deg_rate=SI_BASELINE_DEG_RATE,
    )
    om_disc = _discounted_om_usd_m2()
    e_unit = _discounted_energy_per_pce_point(NOCT_DERATING_2L, deg_rate)
    marginal_slope_usd_m2_per_pct = (lcoe_si_baseline / 100.0) * e_unit - 10.0 * POWER_SCALING_BOS_USD_PER_W

    # Fixed non-power capex baseline (C_mod,0 + C_BOS,area + D_OM)
    base_fixed_capex = PATH0_SI_MODULE_COST_USD_M2 + bos_area + om_disc
    # At deg_rate == SI_BASELINE_DEG_RATE, marginal_slope == base_fixed_capex / PATH0_BIFACIAL_SI_EQUIV_POWER_MW_CM2
    allowable_for_gains = {
        f"+{gain_pct:.1f}_pct_gain": round(
            (PATH0_BIFACIAL_SI_EQUIV_POWER_MW_CM2 + gain_pct) * marginal_slope_usd_m2_per_pct - base_fixed_capex,
            2,
        )
        for gain_pct in (1.0, 2.0, 3.0, 4.0, 5.0)
    }

    return {
        "case": case.lower(),
        "annual_degradation_rate": round(deg_rate, 5),
        "allowable_added_cost_usd_m2_per_eff_point": round(marginal_slope_usd_m2_per_pct, 2),
        "max_added_module_cost_usd_m2_by_net_gain": allowable_for_gains,
        "provenance": {
            "allowable_added_cost_usd_m2_per_eff_point": ProvenanceTag.COMPUTED_HERE.value,
            "max_added_module_cost_usd_m2_by_net_gain": ProvenanceTag.COMPUTED_HERE.value,
        },
    }


def compute_degradation_sensitivity_table(
    subgap_transmittance_fraction: float = 0.88,
    added_module_cost_usd_m2: float = DEFAULT_ADDED_MODULE_COST_2L_USD_M2,
) -> List[Dict[str, Any]]:
    """Sweep annual degradation rate (0.45%/yr to 1.50%/yr) and report utility/rooftop break-even requirements."""
    rows: List[Dict[str, Any]] = []
    for deg_pct in (0.45, 0.50, 0.60, 0.75, 1.00, 1.25, 1.50):
        deg_rate = deg_pct / 100.0
        util_res = compute_lcoe_breakeven_top_pce(
            subgap_transmittance_fraction=subgap_transmittance_fraction,
            added_module_cost_usd_m2=added_module_cost_usd_m2,
            case="utility",
            deg_rate=deg_rate,
        )
        roof_res = compute_lcoe_breakeven_top_pce(
            subgap_transmittance_fraction=subgap_transmittance_fraction,
            added_module_cost_usd_m2=added_module_cost_usd_m2,
            case="rooftop",
            deg_rate=deg_rate,
        )
        rows.append(
            {
                "annual_degradation_rate_pct_yr": deg_pct,
                "utility_breakeven_top_pce_percent": util_res["breakeven_top_cell_pce_percent"],
                "rooftop_breakeven_top_pce_percent": roof_res["breakeven_top_cell_pce_percent"],
                "provenance": ProvenanceTag.COMPUTED_HERE.value,
            }
        )
    return rows


def generate_requirements_tea_report() -> Dict[str, Any]:
    """Build complete inverted techno-economic requirements report for utility and rooftop cases."""
    optics_grid = [
        compute_optics_only_breakeven_top_pce(t) for t in (0.75, 0.80, 0.85, 0.88, 0.90)
    ]

    utility_breakeven_grid: List[Dict[str, Any]] = []
    rooftop_breakeven_grid: List[Dict[str, Any]] = []
    for t in (0.80, 0.85, 0.88, 0.90):
        for dc in (0.0, 15.0, 23.88, 35.0, 45.0):
            utility_breakeven_grid.append(
                compute_lcoe_breakeven_top_pce(t, dc, case="utility", deg_rate=TANDEM_DEFAULT_DEG_RATE)
            )
            rooftop_breakeven_grid.append(
                compute_lcoe_breakeven_top_pce(t, dc, case="rooftop", deg_rate=TANDEM_DEFAULT_DEG_RATE)
            )

    # Audit sensitivity check table (Top-cell efficiency 6%, 8%, 10%, 11.9%, 15.72%, 15.83% at T=0.88, dC=$23.88/m^2)
    lcoe_p0_util = compute_lcoe_cents_kwh(
        PATH0_BIFACIAL_SI_EQUIV_POWER_MW_CM2,
        PATH0_SI_MODULE_COST_USD_M2,
        UTILITY_BOS_AREA_COST_USD_M2,
        NOCT_DERATING_2L,
        SI_BASELINE_DEG_RATE,
    )
    audit_top_eff_sensitivity: List[Dict[str, Any]] = []
    eta_si_p2_ref = SI_REAR_ALBEDO_20PCT_CONTRIB_MW_CM2 + SI_FRONT_SUBGAP_SLOPE_MW_CM2 * 0.88
    for eta_top in (6.0, 8.0, 10.0, 11.9, 15.72, 15.83):
        lcoe_u = compute_lcoe_cents_kwh(
            eta_top + eta_si_p2_ref,
            PATH0_SI_MODULE_COST_USD_M2 + DEFAULT_ADDED_MODULE_COST_2L_USD_M2,
            UTILITY_BOS_AREA_COST_USD_M2,
            NOCT_DERATING_2L,
            TANDEM_DEFAULT_DEG_RATE,
        )
        rel_vs_si = ((lcoe_u / lcoe_p0_util) - 1.0) * 100.0
        audit_top_eff_sensitivity.append(
            {
                "top_cell_pce_percent": eta_top,
                "utility_lcoe_cents_kwh": round(lcoe_u, 3),
                "vs_silicon_alone_percent": round(rel_vs_si, 1),
            }
        )

    return {
        "optics_only_breakeven_formula": "24.5 - 13.1 * T",
        "optics_only_breakeven_at_t088_percent": compute_optics_only_breakeven_top_pce(0.88)[
            "breakeven_top_cell_pce_percent"
        ],
        "optics_only_breakeven_at_t085_percent": compute_optics_only_breakeven_top_pce(0.85)[
            "breakeven_top_cell_pce_percent"
        ],
        "optics_only_grid": optics_grid,
        "original_utility_model_breakeven_top_pce_percent": compute_lcoe_breakeven_top_pce(
            0.88, DEFAULT_ADDED_MODULE_COST_2L_USD_M2, case="utility", deg_rate=TANDEM_DEFAULT_DEG_RATE
        )["breakeven_top_cell_pce_percent"],
        "original_rooftop_model_breakeven_top_pce_percent": compute_lcoe_breakeven_top_pce(
            0.88, DEFAULT_ADDED_MODULE_COST_2L_USD_M2, case="rooftop", deg_rate=TANDEM_DEFAULT_DEG_RATE
        )["breakeven_top_cell_pce_percent"],
        "utility_allowable_added_cost": compute_allowable_added_cost_per_eff_point(case="utility"),
        "rooftop_allowable_added_cost": compute_allowable_added_cost_per_eff_point(case="rooftop"),
        "degradation_sensitivity": compute_degradation_sensitivity_table(),
        "audit_top_cell_lcoe_sensitivity": audit_top_eff_sensitivity,
        "utility_breakeven_grid": utility_breakeven_grid,
        "rooftop_breakeven_grid": rooftop_breakeven_grid,
    }


def main() -> None:
    report = generate_requirements_tea_report()
    print("=" * 78)
    print("FailSmart-MatEngine Inverted Techno-Economic Requirements Model (T8)")
    print("=" * 78)
    print(
        f"1. Optics-only break-even top-cell PCE (24.5 - 13.1*T): "
        f"T=0.88 -> {report['optics_only_breakeven_at_t088_percent']:.2f}%, "
        f"T=0.85 -> {report['optics_only_breakeven_at_t085_percent']:.2f}%"
    )
    print(
        f"2. Original Utility Model LCOE Break-Even (T=0.88, +$23.88/m^2, deg=0.50%/yr): "
        f"{report['original_utility_model_breakeven_top_pce_percent']:.2f}% "
        f"(Rooftop: {report['original_rooftop_model_breakeven_top_pce_percent']:.2f}%)"
    )
    print(
        f"3. Allowable Added Module Cost per +1% Stack Output Point: "
        f"Utility = ${report['utility_allowable_added_cost']['allowable_added_cost_usd_m2_per_eff_point']:.2f}/m^2/pt, "
        f"Rooftop = ${report['rooftop_allowable_added_cost']['allowable_added_cost_usd_m2_per_eff_point']:.2f}/m^2/pt"
    )
    print("4. Degradation Rate Sensitivity (T=0.88, +$23.88/m^2):")
    for row in report["degradation_sensitivity"]:
        print(
            f"   deg={row['annual_degradation_rate_pct_yr']:.2f}%/yr -> "
            f"Utility break-even top PCE = {row['utility_breakeven_top_pce_percent']:.2f}%, "
            f"Rooftop break-even top PCE = {row['rooftop_breakeven_top_pce_percent']:.2f}%"
        )
    print("=" * 78)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
