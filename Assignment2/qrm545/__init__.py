"""Small, reusable risk-modeling helpers used in QRM 545 assignments.

The package contains the general calculations.  Data loading, plots, and the
problem-specific workflow remain in ``analysis.py``.
"""

from .copulas import (
    gaussian_copula_log_contributions,
    kendall_correlation,
    simulate_gaussian_copula,
    simulate_t_copula,
    t_copula_log_contributions,
    t_tail_dependence,
)
from .covariance import (
    covariance_from_correlation,
    nearest_corr_higham,
    nearest_corr_spectral,
    portfolio_variance,
)
from .distributions import aicc, fit_student_t
from .risk import ew_weights, historical_risk, moments, normal_risk

__all__ = [
    "aicc",
    "covariance_from_correlation",
    "ew_weights",
    "fit_student_t",
    "gaussian_copula_log_contributions",
    "historical_risk",
    "kendall_correlation",
    "moments",
    "nearest_corr_higham",
    "nearest_corr_spectral",
    "normal_risk",
    "portfolio_variance",
    "simulate_gaussian_copula",
    "simulate_t_copula",
    "t_copula_log_contributions",
    "t_tail_dependence",
]

__version__ = "0.1.0"
