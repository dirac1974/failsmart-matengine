"""FailSmart-MatEngine: Provenance-Tagged Materials Pre-Screening Package."""

from __future__ import annotations

from typing import Any

__version__ = "0.8.0"

# Names re-exported from independent_verifier. They are loaded on first use, so that
# importing the package does not import pvlib, scipy and pymatgen.
_VERIFIER_EXPORTS = frozenset(
    {
        "gcd_reduced",
        "independently_parse_formula",
        "independently_verify_cif_geometry",
        "independently_verify_coherent_tmm_4t_stack",
        "independently_verify_cross_layer_4t_pair",
        "independently_verify_energy_quadrature_slme",
        "independently_verify_graded_arc_and_techno_economics",
        "independently_verify_phase9a_lab_and_defect_dossier",
        "independently_verify_phase9c_oblique_thermal_lcoe",
        "independently_verify_phase10_bifacial_and_string_dossier",
        "independently_verify_spring_and_migration_heuristics",
        "simpson_13",
        "verify_candidate_dossier",
    }
)

__all__ = ["__version__", *sorted(_VERIFIER_EXPORTS)]


def __getattr__(name: str) -> Any:
    if name in _VERIFIER_EXPORTS:
        from . import independent_verifier

        return getattr(independent_verifier, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
