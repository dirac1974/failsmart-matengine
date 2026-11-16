"""FailSmart-MatEngine: Physics-Informed Multi-Agent Materials Discovery Package."""

from __future__ import annotations

from typing import Any

__version__ = "8.0.0"

_VERIFIER_EXPORTS = frozenset(
    {
        "gcd_reduced",
        "independently_parse_formula",
        "independently_verify_atomistic_phonon_and_neb",
        "independently_verify_cif_geometry",
        "independently_verify_coherent_tmm_4t_stack",
        "independently_verify_cross_layer_4t_pair",
        "independently_verify_energy_quadrature_slme",
        "independently_verify_graded_arc_and_techno_economics",
        "independently_verify_phase9a_lab_and_defect_dossier",
        "independently_verify_phase9b_contrastive_audit",
        "independently_verify_phase9c_oblique_thermal_lcoe",
        "independently_verify_phase10_bifacial_and_string_dossier",
        "simpson_13",
        "verify_candidate_dossier",
    }
)

__all__ = ["__version__", *sorted(_VERIFIER_EXPORTS)]


def __getattr__(name: str) -> Any:
    """Lazily expose independent_verifier symbols without eager heavy imports."""
    if name in _VERIFIER_EXPORTS:
        from . import independent_verifier

        return getattr(independent_verifier, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
