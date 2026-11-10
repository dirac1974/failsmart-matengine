"""FailSmart-MatEngine: Physics-Informed Multi-Agent Materials Discovery Package."""

from .independent_verifier import (
    gcd_reduced,
    independently_parse_formula,
    independently_verify_cif_geometry,
    independently_verify_cross_layer_4t_pair,
    independently_verify_energy_quadrature_slme,
    simpson_13,
    verify_candidate_dossier,
)

__version__ = "0.1.0"

